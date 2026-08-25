import logging
from pathlib import Path

import joblib
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

RUTA_MODELO = Path(__file__).resolve().parent / "modelo_techmind_v2.joblib"

_modelo = None  # cache en memoria, para no recargar ni redescargar


def descargar_archivo(url: str, ruta_destino: Path) -> Path:
    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    respuesta = requests.get(url, stream=True)
    respuesta.raise_for_status()
    with open(ruta_destino, "wb") as archivo:
        for pedazo in respuesta.iter_content(chunk_size=8192):
            archivo.write(pedazo)
    return ruta_destino


def cargar_modelo():
    global _modelo
    if _modelo is not None:
        return _modelo  # ya está en memoria, no repetir nada

    if not RUTA_MODELO.exists():
        if not settings.modelo_url:
            logger.warning("Modelo no encontrado localmente y falta MODELO_URL en el entorno")
            return None
        try:
            logger.info("Modelo no encontrado localmente, descargando desde OCI...")
            descargar_archivo(settings.modelo_url, RUTA_MODELO)
        except requests.exceptions.RequestException as e:
            logger.error(f"Fallo al descargar el modelo: {e}")
            return None

    _modelo = joblib.load(RUTA_MODELO)
    return _modelo