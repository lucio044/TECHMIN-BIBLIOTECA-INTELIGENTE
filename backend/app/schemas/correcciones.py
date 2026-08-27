from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CorreccionEntrada(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=300)
    texto: str = Field(..., min_length=20, max_length=20000)
    categoria_predicha: str = Field(..., min_length=1, max_length=60)
    categoria_correcta: str = Field(..., min_length=1, max_length=60)
    comentario: Optional[str] = Field(None, max_length=500)

    # `min_length` no alcanza: una cadena de espacios lo cumple y llega al
    # servicio igual. Aca hoy salta antes otro campo obligatorio, pero la
    # proteccion tiene que estar en el campo y no depender del orden.
    @field_validator("titulo", "texto")
    @classmethod
    def no_solo_espacios(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("El campo no puede contener solo espacios en blanco")
        return valor

    @field_validator("categoria_correcta")
    @classmethod
    def distinta_de_la_predicha(cls, v, info):
        predicha = info.data.get("categoria_predicha")
        if predicha and v.strip().lower() == predicha.strip().lower():
            raise ValueError(
                "La categoria correcta es la misma que la predicha: "
                "no hay nada que corregir"
            )
        return v


class CorreccionGuardada(BaseModel):
    titulo: str
    texto: str
    categoria_predicha: str
    categoria_correcta: str
    comentario: Optional[str] = None
    registrada: str


class CorreccionesSalida(BaseModel):
    total: int
    correcciones: List[CorreccionGuardada]
