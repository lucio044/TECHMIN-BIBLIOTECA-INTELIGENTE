from typing import List, Optional

from pydantic import BaseModel


class FilaClasificada(BaseModel):
    fila: int
    titulo: str
    categoria: Optional[str] = None
    probabilidad: Optional[float] = None
    palabras_clave: List[str] = []
    # Se completa solo cuando la fila no se pudo clasificar. Asi un archivo
    # con algunas filas malas devuelve igual el resto, en vez de fallar
    # entero y obligar a limpiarlo a ciegas.
    error: Optional[str] = None


class LoteSalida(BaseModel):
    archivo: str
    total: int
    clasificadas: int
    con_error: int
    resumen_por_categoria: dict
    resultados: List[FilaClasificada]
