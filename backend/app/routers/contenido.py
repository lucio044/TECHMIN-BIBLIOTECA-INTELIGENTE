from fastapi import APIRouter
from app.schemas.contenido import ContenidoEntrada, ContenidoSalida
from app.services.clasificador import clasificar_contenido

router = APIRouter()


@router.post("/contenido", response_model=ContenidoSalida)
def procesar_contenido(entrada: ContenidoEntrada):
    resultado = clasificar_contenido(entrada)
    return resultado