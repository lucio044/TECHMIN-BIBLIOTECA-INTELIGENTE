"""Metricas del modelo y del corpus, para el tablero.

Casi todo se calcula de los artefactos que la API ya tiene cargados: la
distribucion del corpus sale de la matriz historica, y los terminos mas
decisivos de los coeficientes del clasificador.

Lo unico que no se puede calcular en vivo es el rendimiento por categoria
--precision, recall y F1-- porque se mide contra el conjunto de prueba
durante el entrenamiento. Eso viene de metricas_modelo.json, que produce el
notebook.
"""

import json
import logging
from collections import Counter
from functools import lru_cache

import numpy as np
from fastapi import HTTPException, status

from app.ml.loader import RUTA_MODELO, cargar_modelo
from app.ml.recomendador import cargar_recomendador

logger = logging.getLogger(__name__)

RUTA_METRICAS = RUTA_MODELO.parent / "metricas_modelo.json"

# Cuantos terminos decisivos se muestran por categoria.
TERMINOS_POR_CATEGORIA = 8


@lru_cache(maxsize=1)
def _metricas_entrenamiento() -> dict:
    """Lee el rendimiento medido durante el entrenamiento.

    Si el archivo no esta, se devuelve vacio en vez de fallar: el tablero
    puede mostrar el resto igual.
    """
    try:
        with open(RUTA_METRICAS, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        logger.warning("No se pudo leer %s: %s", RUTA_METRICAS, error)
        return {}


@lru_cache(maxsize=1)
def _terminos_decisivos() -> dict:
    """Los terminos con mas peso para cada categoria.

    Son los coeficientes de la Regresion Logistica: cuanto empuja cada
    termino hacia esa categoria. Es la forma mas directa de mostrar que
    aprendio el modelo, y de comprobar que decide por vocabulario tecnico
    real y no por rarezas del corpus.
    """
    modelo = cargar_modelo()
    if modelo is None:
        return {}

    vocabulario = modelo.named_steps["tfidf"].get_feature_names_out()
    coeficientes = modelo.named_steps["clf"].coef_

    return {
        str(categoria): [
            str(vocabulario[i])
            for i in np.argsort(coeficientes[fila])[::-1][:TERMINOS_POR_CATEGORIA]
        ]
        for fila, categoria in enumerate(modelo.classes_)
    }


@lru_cache(maxsize=1)
def _distribucion_corpus() -> dict:
    """Cuantos documentos del historico hay en cada categoria."""
    recomendador = cargar_recomendador()
    if recomendador is None:
        return {}
    return dict(Counter(str(c) for c in recomendador._categorias).most_common())


def obtener_metricas() -> dict:
    """Arma el panel completo: modelo, rendimiento, corpus y vocabulario."""
    modelo = cargar_modelo()
    if modelo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El modelo no esta disponible en este momento.",
        )

    entrenamiento = _metricas_entrenamiento()
    corpus = _distribucion_corpus()
    tfidf = modelo.named_steps["tfidf"]
    clf = modelo.named_steps["clf"]

    return {
        "modelo": {
            "algoritmo": "TF-IDF + Regresión Logística",
            "categorias": len(modelo.classes_),
            "vocabulario": len(tfidf.get_feature_names_out()),
            "ngramas": list(tfidf.ngram_range),
            "regularizacion_C": float(clf.C),
            "pesos_balanceados": clf.class_weight == "balanced",
        },
        "rendimiento": {
            "f1_macro": entrenamiento.get("f1_macro"),
            "accuracy": entrenamiento.get("accuracy"),
            "validacion_cruzada": entrenamiento.get("validacion_cruzada"),
            "linea_base_f1_macro": entrenamiento.get("linea_base_f1_macro"),
            "textos_de_prueba": entrenamiento.get("soporte_test"),
            "por_categoria": entrenamiento.get("por_categoria", {}),
        },
        "corpus": {
            "documentos_indexados": sum(corpus.values()),
            "por_categoria": corpus,
        },
        "terminos_decisivos": _terminos_decisivos(),
    }
