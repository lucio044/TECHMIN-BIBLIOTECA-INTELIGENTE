from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.ml.loader import cargar_modelo, RUTA_MODELO
from app.schemas.modelo import ModeloInfo

router = APIRouter()


@router.get("/modelo/info", response_model=ModeloInfo)
def obtener_info_modelo():
    modelo = cargar_modelo()
    if modelo is None:
        raise HTTPException(status_code=503, detail="El modelo no está disponible")

    fecha_modificacion = datetime.fromtimestamp(RUTA_MODELO.stat().st_mtime)

    return ModeloInfo(
        algoritmo="TF-IDF + Regresión Logística",
        cantidad_categorias=len(modelo.classes_),
        categorias=list(modelo.classes_),
        fecha_modificacion=fecha_modificacion,
    )