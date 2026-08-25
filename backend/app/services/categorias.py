from fastapi import HTTPException, status
from app.schemas.categorias import CategoriasSalida
from app.ml.loader import cargar_modelo

modelo = cargar_modelo()


def obtener_categorias() -> CategoriasSalida:
    if modelo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El modelo de clasificación aún no está disponible. Intenta más tarde.",
        )

    return CategoriasSalida(categorias=list(modelo.classes_))
