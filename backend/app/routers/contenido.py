from fastapi import APIRouter, Depends
from app.schemas.contenido import ContenidoEntrada, ContenidoSalida
from app.services.clasificador import clasificar_contenido
from app.core.acceso import identificar

router = APIRouter()


@router.post("/contenido", response_model=ContenidoSalida)
def procesar_contenido(entrada: ContenidoEntrada, _=Depends(identificar)):
    resultado = clasificar_contenido(entrada)
    return resultado