from fastapi import Depends, APIRouter

from app.core.acceso import identificar
from app.services.metricas import obtener_metricas

router = APIRouter()


@router.get("/metricas")
def metricas(_=Depends(identificar)):
    """Metricas del modelo y del corpus, para el tablero.

    Casi todo se calcula de los artefactos cargados. El rendimiento por
    categoria viene del entrenamiento, porque se mide contra el conjunto de
    prueba y no se puede recalcular en vivo.
    """
    return obtener_metricas()
