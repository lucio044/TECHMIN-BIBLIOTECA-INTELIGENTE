from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class BibliotecaEntrada(BaseModel):
    # Los mismos limites que ContenidoEntrada. Sin ellos una cadena vacia
    # pasaba la validacion y reventaba mas abajo: la API devolvia 500 en
    # lugar de decir cual es el campo que falta.
    titulo: str = Field(..., min_length=1)
    texto: str = Field(..., min_length=1)

    @field_validator("titulo", "texto")
    @classmethod
    def no_solo_espacios(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("El campo no puede contener solo espacios en blanco")
        return valor


class BibliotecaResultado(BaseModel):
    titulo: str
    texto: str
    categoria: str
    probabilidad: float
    palabras_clave: list[str]
    fecha_creacion: datetime