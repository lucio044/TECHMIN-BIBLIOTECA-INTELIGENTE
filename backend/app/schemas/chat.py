from typing import Literal

from pydantic import BaseModel, Field


class MensajeChat(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str


class ChatEntrada(BaseModel):
    texto: str
    historial: list[MensajeChat] = []


class TerminoDecisivo(BaseModel):
    termino: str
    aporte: float = Field(
        description="TF-IDF del termino por el coeficiente de la categoria ganadora. "
                    "Cuanto empujo ese termino hacia la decision."
    )


class ChatSalida(BaseModel):
    respuesta: str

    # La evidencia viaja aparte del texto para que el cliente pueda
    # mostrarla como quiera en vez de tener que leerla de la prosa.
    categoria: str | None = None
    probabilidad: float | None = None
    terminos_decisivos: list[TerminoDecisivo] = []
    fuente: Literal["modelo", "deepseek"] = "modelo"
