from pydantic import BaseModel, Field, field_validator
from typing import List


class ContenidoEntrada(BaseModel):
    titulo: str = Field(..., min_length=1)
    texto: str = Field(..., min_length=1)

    @field_validator("titulo", "texto")
    @classmethod
    def no_solo_espacios(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("El campo no puede contener solo espacios en blanco")
        return valor
    
class CategoriaRanking(BaseModel):
    categoria: str
    probabilidad: float
    
class ContenidoRelacionado(BaseModel):
    titulo: str
    # Primeros 200 caracteres del cuerpo del documento. Vacio si la matriz
    # cargada es anterior a la version que incluye la clave "extractos".
    extracto: str = ""
    categoria: str
    similitud: float


class ContenidoSalida(BaseModel):
    categoria: str
    probabilidad: float
    informacion_adicional: List[str]
    ranking_categorias: List[CategoriaRanking]
    contenidos_relacionados: List[ContenidoRelacionado]
    