from typing import List

from pydantic import BaseModel


class DocumentoEncontrado(BaseModel):
    id: int
    titulo: str
    extracto: str = ""
    categoria: str
    # Cuanto pesa el termino buscado dentro de ese documento. No es un
    # porcentaje: sirve para ordenar, no para leerlo como probabilidad.
    relevancia: float


class BusquedaSalida(BaseModel):
    termino: str
    total: int
    resultados: List[DocumentoEncontrado]
