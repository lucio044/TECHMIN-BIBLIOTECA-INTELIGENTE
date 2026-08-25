from fastapi import APIRouter, Depends

from app.core.acceso import identificar
from app.schemas.chat import ChatEntrada, ChatSalida
from app.services.chat import responder_chat

router = APIRouter()


@router.post("/chat", response_model=ChatSalida)
def chat(entrada: ChatEntrada, _=Depends(identificar)):
    """Explica una clasificacion en lenguaje natural.

    Devuelve tambien la evidencia que sostiene la explicacion: la categoria,
    su probabilidad y los terminos del texto que mas empujaron la decision,
    con cuanto aporto cada uno.

    El campo `fuente` dice quien redacto. Con `modelo`, la respuesta se armo
    con lo que el clasificador calculo, sin proveedor externo: es el modo
    normal cuando no hay clave configurada, y no es un modo degradado.
    """
    return ChatSalida(**responder_chat(entrada.texto, entrada.historial))
