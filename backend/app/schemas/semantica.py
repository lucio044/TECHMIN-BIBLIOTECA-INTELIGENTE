from typing import List

from pydantic import BaseModel, Field


class DocumentoParecido(BaseModel):
    id: int
    titulo: str
    extracto: str = ""
    categoria: str
    parecido: float = Field(
        description="Coseno entre el significado de la consulta y el del documento, "
                    "de -1 a 1. No es un porcentaje: sirve para ordenar."
    )


class BusquedaSemanticaSalida(BaseModel):
    consulta: str
    total: int
    documentos_comparados: int
    resultados: List[DocumentoParecido]
