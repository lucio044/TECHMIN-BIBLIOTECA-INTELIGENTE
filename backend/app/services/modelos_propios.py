"""Modelos entrenados con las categorias del propio cliente.

El modelo que viene de fabrica clasifica en 8 categorias tecnicas. Sirve
para quien organiza contenido de programacion, y para nadie mas: un estudio
juridico necesita Laboral, Tributario y Societario; una clinica necesita
Cardiologia y Pediatria.

Este servicio deja que cada cliente suba su propio CSV con sus etiquetas y
se quede con un modelo suyo. Es la misma tecnica del modelo principal
--TF-IDF mas Regresion Logistica-- que sobre unos miles de textos entrena
en segundos.

Con base de datos configurada, el Pipeline entrenado se guarda serializado
en la fila y sobrevive a los reinicios. Sin base queda en memoria del
proceso, para que la demo publica funcione igual sin depender de un
servidor externo.
"""

import csv
import io
import logging
import re
import uuid
from collections import Counter
from functools import lru_cache
from datetime import datetime, timezone
from typing import Dict

import joblib
import numpy as np
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.core.database import SessionLocal, hay_base
from app.models.modelo_propio import ModeloPropio

logger = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024
MIN_FILAS = 40
MAX_FILAS = 20000
MIN_POR_CATEGORIA = 5
MAX_MODELOS = 20

COLUMNAS_TEXTO = ("texto", "contenido", "text", "content")
COLUMNAS_CATEGORIA = ("categoria", "categoría", "etiqueta", "label", "category")

_PATRON_PERMITIDO = re.compile(r"[^áéíóúüñÁÉÍÓÚÑA-Za-z0-9\s\+\#\.\_\-\/]")
_PATRON_ESPACIOS = re.compile(r"\s+")

_modelos: Dict[str, dict] = {}


def _limpiar(texto: str) -> str:
    """La misma limpieza del modelo principal: conserva + # . _ - / y los
    digitos, para que C++, CI/CD y HTML5 lleguen enteros al vectorizador."""
    texto = _PATRON_PERMITIDO.sub("", str(texto))
    return _PATRON_ESPACIOS.sub(" ", texto).strip()


def _elegir_columna(cabeceras, candidatas):
    normalizadas = {c.strip().lower(): c for c in cabeceras if c}
    for candidata in candidatas:
        if candidata in normalizadas:
            return normalizadas[candidata]
    return None


async def entrenar(archivo: UploadFile, nombre: str) -> dict:
    """Entrena un modelo con el CSV del cliente y lo deja disponible."""
    if not hay_base() and len(_modelos) >= MAX_MODELOS:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=(f"Se alcanzo el maximo de {MAX_MODELOS} modelos en memoria. "
                    "Con base de datos configurada no hay ese limite."),
        )
    if not archivo.filename or not archivo.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo tiene que ser un CSV.")

    crudo = await archivo.read()
    if len(crudo) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"El archivo supera los {MAX_BYTES // 1024 // 1024} MB.",
        )

    try:
        contenido = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        contenido = crudo.decode("latin-1", errors="replace")

    lector = csv.DictReader(io.StringIO(contenido))
    if not lector.fieldnames:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El CSV no tiene cabeceras.")

    col_texto = _elegir_columna(lector.fieldnames, COLUMNAS_TEXTO)
    col_cat = _elegir_columna(lector.fieldnames, COLUMNAS_CATEGORIA)
    if not col_texto or not col_cat:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El CSV necesita una columna de texto ({', '.join(COLUMNAS_TEXTO)}) "
            f"y otra de categoria ({', '.join(COLUMNAS_CATEGORIA)}). "
            f"Se encontraron: {', '.join(lector.fieldnames)}",
        )

    textos, etiquetas = [], []
    for i, fila in enumerate(lector):
        if i >= MAX_FILAS:
            break
        t = _limpiar(fila.get(col_texto) or "")
        c = (fila.get(col_cat) or "").strip()
        if t and c:
            textos.append(t)
            etiquetas.append(c)

    if len(textos) < MIN_FILAS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Hacen falta al menos {MIN_FILAS} filas utiles; llegaron {len(textos)}.",
        )

    cuenta = Counter(etiquetas)
    if len(cuenta) < 2:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "El CSV tiene una sola categoria: no hay nada que distinguir.",
        )

    escasas = {c: n for c, n in cuenta.items() if n < MIN_POR_CATEGORIA}
    if escasas:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cada categoria necesita al menos {MIN_POR_CATEGORIA} ejemplos. "
            f"Con menos de eso: {', '.join(f'{c} ({n})' for c, n in escasas.items())}",
        )

    # Se separa una parte para medir. Sin esto el F1 que se devuelve seria el
    # de los mismos textos con los que aprendio, que siempre es optimista y no
    # dice nada sobre como se va a comportar con material nuevo.
    x_ent, x_prueba, y_ent, y_prueba = train_test_split(
        textos, etiquetas, test_size=0.2, random_state=42, stratify=etiquetas
    )

    modelo = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=30000)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    modelo.fit(x_ent, y_ent)
    f1 = float(f1_score(y_prueba, modelo.predict(x_prueba), average="macro"))

    identificador = uuid.uuid4().hex[:12]
    ficha = {
        "nombre": nombre,
        "categorias": sorted(cuenta),
        "ejemplos": len(textos),
        "distribucion": dict(cuenta.most_common()),
        "f1_macro": round(f1, 4),
    }
    logger.info("Modelo propio %s: %s categorias, %s ejemplos, F1 %.4f",
                identificador, len(cuenta), len(textos), f1)

    if hay_base():
        buffer = io.BytesIO()
        joblib.dump(modelo, buffer, compress=3)
        with SessionLocal() as db:
            fila = ModeloPropio(id=identificador, artefacto=buffer.getvalue(), **ficha)
            db.add(fila)
            db.commit()
            db.refresh(fila)
            return {"id": identificador, **ficha,
                    "entrenado": fila.entrenado.isoformat(timespec="seconds")}

    _modelos[identificador] = {"modelo": modelo, **ficha}
    return {"id": identificador, **ficha,
            "entrenado": datetime.now(timezone.utc).isoformat(timespec="seconds")}


@lru_cache(maxsize=8)
def _cargar_de_base(identificador: str):
    """Trae el Pipeline de la base y lo deja en cache.

    Sin la cache, cada clasificacion leeria y deserializaria varios MB. Con
    ocho modelos en memoria alcanza para el uso real, y los que salgan de la
    cache se vuelven a leer sin que nadie lo note.
    """
    with SessionLocal() as db:
        fila = db.get(ModeloPropio, identificador)
        if fila is None:
            return None
        return {"modelo": joblib.load(io.BytesIO(fila.artefacto)), "nombre": fila.nombre}


def clasificar(identificador: str, texto: str, top_n: int = 3) -> dict:
    """Clasifica un texto con el modelo propio del cliente."""
    guardado = _cargar_de_base(identificador) if hay_base() else _modelos.get(identificador)
    if guardado is None:
        detalle = (
            "No existe ese modelo."
            if hay_base()
            else "No existe ese modelo. Sin base de datos configurada los "
                 "modelos viven en memoria y se pierden al reiniciar el "
                 "servicio; hay que volver a entrenarlo."
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, detalle)

    limpio = _limpiar(texto)
    if not limpio:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El texto quedo vacio tras limpiarlo.")

    modelo = guardado["modelo"]
    proba = modelo.predict_proba([limpio])[0]
    orden = np.argsort(proba)[::-1]

    return {
        "modelo_id": identificador,
        "modelo_nombre": guardado["nombre"],
        "categoria": str(modelo.classes_[orden[0]]),
        "probabilidad": round(float(proba[orden[0]]), 3),
        "ranking": [
            {"categoria": str(modelo.classes_[i]), "probabilidad": round(float(proba[i]), 3)}
            for i in orden[1:top_n] if proba[i] >= 0.05
        ],
    }


def listar() -> list:
    if not hay_base():
        return [
            {"id": k,
             "entrenado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             **{x: y for x, y in v.items() if x != "modelo"}}
            for k, v in _modelos.items()
        ]

    # Se piden solo las columnas que se muestran: traer el artefacto de cada
    # modelo para listarlos serian varios MB por consulta.
    with SessionLocal() as db:
        filas = db.execute(
            select(ModeloPropio.id, ModeloPropio.nombre, ModeloPropio.categorias,
                   ModeloPropio.distribucion, ModeloPropio.ejemplos,
                   ModeloPropio.f1_macro, ModeloPropio.entrenado)
        ).all()
        return [
            {"id": f.id, "nombre": f.nombre, "categorias": f.categorias,
             "distribucion": f.distribucion, "ejemplos": f.ejemplos,
             "f1_macro": f.f1_macro,
             "entrenado": f.entrenado.isoformat(timespec="seconds")}
            for f in filas
        ]


def eliminar(identificador: str) -> None:
    if not hay_base():
        if _modelos.pop(identificador, None) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese modelo.")
        return

    with SessionLocal() as db:
        fila = db.get(ModeloPropio, identificador)
        if fila is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese modelo.")
        db.delete(fila)
        db.commit()
    _cargar_de_base.cache_clear()
