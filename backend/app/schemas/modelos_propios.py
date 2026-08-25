from typing import Dict, List

from pydantic import BaseModel, Field


class ModeloEntrenado(BaseModel):
    id: str
    nombre: str
    categorias: List[str]
    ejemplos: int
    distribucion: Dict[str, int]
    # Medido sobre el 20% que se aparta antes de entrenar, no sobre los
    # mismos textos con los que aprendio.
    f1_macro: float
    entrenado: str


class TextoAClasificar(BaseModel):
    texto: str = Field(..., min_length=20, max_length=20000)


class CategoriaProbable(BaseModel):
    categoria: str
    probabilidad: float


class ClasificacionPropia(BaseModel):
    modelo_id: str
    modelo_nombre: str
    categoria: str
    probabilidad: float
    ranking: List[CategoriaProbable] = []
