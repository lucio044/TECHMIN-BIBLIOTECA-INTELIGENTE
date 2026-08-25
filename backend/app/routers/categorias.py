from fastapi import APIRouter
from app.schemas.categorias import CategoriasSalida
from app.services.categorias import obtener_categorias

router = APIRouter()


@router.get("/categorias", response_model=CategoriasSalida)
def listar_categorias():
    return obtener_categorias()
