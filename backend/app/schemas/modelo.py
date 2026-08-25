from pydantic import BaseModel
from datetime import datetime


class ModeloInfo(BaseModel):
    algoritmo: str
    cantidad_categorias: int
    categorias: list[str]
    fecha_modificacion: datetime