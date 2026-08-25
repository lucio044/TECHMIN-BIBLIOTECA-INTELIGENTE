from fastapi import APIRouter
from app.schemas.chat import ChatEntrada, ChatSalida
from app.services.chat import responder_chat

router = APIRouter()


@router.post("/chat", response_model=ChatSalida)
def chat(entrada: ChatEntrada):
    respuesta = responder_chat(entrada.texto, entrada.historial)
    return ChatSalida(respuesta=respuesta)