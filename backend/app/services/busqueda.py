"""Busqueda de documentos del historico por palabra clave."""

import logging

from fastapi import HTTPException, status

from app.ml.recomendador import cargar_recomendador
from app.schemas.busqueda import BusquedaSalida, DocumentoEncontrado

logger = logging.getLogger(__name__)


def buscar_documentos(termino: str, cantidad: int) -> BusquedaSalida:
    """Devuelve los documentos donde ese termino pesa mas.

    La lista vacia es una respuesta valida: significa que el termino no
    aparece en el corpus, o que no esta en el vocabulario del modelo.
    """
    recomendador = cargar_recomendador()
    if recomendador is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La busqueda no esta disponible en este momento.",
        )

    encontrados = recomendador.buscar(termino, top_n=cantidad)

    return BusquedaSalida(
        termino=termino,
        total=len(encontrados),
        resultados=[DocumentoEncontrado(**d) for d in encontrados],
    )
