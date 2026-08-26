from fastapi import Depends, APIRouter
from app.core.acceso import identificar
from app.schemas.categorias import CategoriasSalida
from app.services.categorias import obtener_categorias

router = APIRouter()


@router.get("/categorias", response_model=CategoriasSalida)
def listar_categorias(_=Depends(identificar)):
    return obtener_categorias()
