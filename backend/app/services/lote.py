"""Clasificacion de muchos contenidos de una vez, desde un CSV.

El modelo tarda unos milisegundos por texto, asi que el cuello de botella
no es clasificar sino leer y validar el archivo. Por eso el limite de filas
es generoso: mil textos se resuelven en pocos segundos.

Una fila mal formada no tumba el lote. Se anota su error y se sigue con las
demas, para que quien sube un archivo de mil filas con tres rotas reciba
las 997 buenas y sepa exactamente cuales fallaron.
"""

import csv
import io
import logging
from collections import Counter
from typing import List

from fastapi import HTTPException, UploadFile, status

from app.schemas.contenido import ContenidoEntrada
from app.schemas.lote import FilaClasificada, LoteSalida
from app.services.clasificador import clasificar_contenido

logger = logging.getLogger(__name__)

MAX_FILAS = 1000
MAX_BYTES = 5 * 1024 * 1024

COLUMNAS_TITULO = ("titulo", "título", "title")
COLUMNAS_TEXTO = ("texto", "contenido", "text", "content")


def _elegir_columna(cabeceras: List[str], candidatas: tuple) -> str | None:
    """Devuelve el nombre real de la columna, sin importar mayusculas.

    Se aceptan varios nombres porque un CSV exportado de otra herramienta
    rara vez usa exactamente los que uno espera.
    """
    normalizadas = {c.strip().lower(): c for c in cabeceras if c}
    for candidata in candidatas:
        if candidata in normalizadas:
            return normalizadas[candidata]
    return None


async def clasificar_lote(archivo: UploadFile) -> LoteSalida:
    """Clasifica cada fila de un CSV con columnas de titulo y texto."""
    if not archivo.filename or not archivo.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo tiene que ser un CSV.",
        )

    crudo = await archivo.read()
    if len(crudo) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera los {MAX_BYTES // 1024 // 1024} MB.",
        )

    # Se prueba UTF-8 y se cae a Latin-1, que es lo que suele salir de Excel
    # en Windows. Con errors='replace' un byte suelto no tira todo el lote.
    try:
        texto = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = crudo.decode("latin-1", errors="replace")

    lector = csv.DictReader(io.StringIO(texto))
    if not lector.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El CSV no tiene fila de cabeceras.",
        )

    col_titulo = _elegir_columna(lector.fieldnames, COLUMNAS_TITULO)
    col_texto = _elegir_columna(lector.fieldnames, COLUMNAS_TEXTO)

    if not col_titulo or not col_texto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El CSV necesita una columna de titulo y otra de texto. "
                f"Se aceptan {', '.join(COLUMNAS_TITULO)} y "
                f"{', '.join(COLUMNAS_TEXTO)}. "
                f"Se encontraron: {', '.join(lector.fieldnames)}"
            ),
        )

    resultados: List[FilaClasificada] = []
    categorias: Counter = Counter()

    for numero, fila in enumerate(lector, start=1):
        if numero > MAX_FILAS:
            logger.warning("CSV con mas de %s filas, se corto", MAX_FILAS)
            break

        titulo = (fila.get(col_titulo) or "").strip()
        cuerpo = (fila.get(col_texto) or "").strip()

        # Se revisa antes de llamar al modelo para poder explicar el
        # problema en castellano. El error de Pydantic dice lo mismo, pero
        # en un formato que no le sirve a quien subio el archivo.
        if not titulo and not cuerpo:
            faltante = "la fila esta vacia"
        elif not titulo:
            faltante = "falta el titulo"
        elif not cuerpo:
            faltante = "falta el texto"
        else:
            faltante = None

        if faltante:
            resultados.append(
                FilaClasificada(fila=numero, titulo=titulo[:120], error=faltante)
            )
            continue

        try:
            salida = clasificar_contenido(ContenidoEntrada(titulo=titulo, texto=cuerpo))
        except Exception as error:
            detalle = getattr(error, "detail", None) or "no se pudo clasificar"
            resultados.append(
                FilaClasificada(
                    fila=numero,
                    titulo=titulo[:120],
                    error=str(detalle)[:160],
                )
            )
            continue

        categorias[salida.categoria] += 1
        resultados.append(
            FilaClasificada(
                fila=numero,
                titulo=titulo[:120],
                categoria=salida.categoria,
                probabilidad=salida.probabilidad,
                palabras_clave=salida.informacion_adicional,
            )
        )

    con_error = sum(1 for r in resultados if r.error)

    return LoteSalida(
        archivo=archivo.filename,
        total=len(resultados),
        clasificadas=len(resultados) - con_error,
        con_error=con_error,
        resumen_por_categoria=dict(categorias.most_common()),
        resultados=resultados,
    )
