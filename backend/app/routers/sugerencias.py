from fastapi import Depends, APIRouter, HTTPException, status
from app.core.acceso import identificar
from app.ml.sugerencias_loader import cargar_sugerencias

router = APIRouter()


@router.get("/sugerencias")
def obtener_sugerencias(_=Depends(identificar)):
    sugerencias = cargar_sugerencias()
    if sugerencias is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Las sugerencias aún no están disponibles.",
        )
    return sugerencias