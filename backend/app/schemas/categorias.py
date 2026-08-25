from pydantic import BaseModel
from typing import List


class CategoriasSalida(BaseModel):
    categorias: List[str]
