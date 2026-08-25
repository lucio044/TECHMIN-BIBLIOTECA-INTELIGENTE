from pydantic import BaseModel
from typing import Literal


class MensajeChat(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str


class ChatEntrada(BaseModel):
    texto: str
    historial: list[MensajeChat] = []


class ChatSalida(BaseModel):
    respuesta: str