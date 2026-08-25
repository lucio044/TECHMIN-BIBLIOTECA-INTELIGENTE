from pydantic import BaseModel
from datetime import datetime


class BibliotecaEntrada(BaseModel):
    titulo: str
    texto: str


class BibliotecaResultado(BaseModel):
    titulo: str
    texto: str
    categoria: str
    probabilidad: float
    palabras_clave: list[str]
    fecha_creacion: datetime