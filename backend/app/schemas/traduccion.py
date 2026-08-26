from typing import List, Literal

from pydantic import BaseModel, Field


class TraduccionEntrada(BaseModel):
    # Se aceptan varios textos por llamada porque quien traduce una
    # respuesta traduce sus cuatro fragmentos, y hacerlo en una sola
    # peticion evita gastar cuatro del limite por minuto.
    textos: List[str] = Field(..., min_length=1, max_length=10)
    destino: Literal["es", "en"]


class TraduccionSalida(BaseModel):
    destino: str
    traducciones: List[str]
    ya_estaban_en_destino: int = Field(
        description="Cuantos textos se devolvieron sin tocar por estar ya en "
                    "el idioma pedido."
    )


class EstadoTraductor(BaseModel):
    es_en: bool
    en_es: bool
    cargados: List[str] = Field(
        description="Direcciones ya en memoria. Las demas tardan unos "
                    "segundos la primera vez que se usan."
    )
