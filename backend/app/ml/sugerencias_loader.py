import json
import logging
from pathlib import Path

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

RUTA_SUGERENCIAS = Path(__file__).resolve().parent / "sugerencias_botones.json"

_sugerencias = None


def _descargar_archivo(url: str, ruta_destino: Path) -> Path:
    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    respuesta = requests.get(url, stream=True)
    respuesta.raise_for_status()
    with open(ruta_destino, "wb") as archivo:
        for pedazo in respuesta.iter_content(chunk_size=8192):
            archivo.write(pedazo)
    return ruta_destino


def cargar_sugerencias():
    global _sugerencias
    if _sugerencias is not None:
        return _sugerencias

    if not RUTA_SUGERENCIAS.exists():
        if not settings.sugerencias_botones_url:
            logger.warning("Sugerencias no encontradas localmente y falta SUGERENCIAS_BOTONES_URL")
            return None
        try:
            logger.info("Sugerencias no encontradas localmente, descargando desde OCI...")
            _descargar_archivo(settings.sugerencias_botones_url, RUTA_SUGERENCIAS)
        except requests.exceptions.RequestException as e:
            logger.error(f"Fallo al descargar sugerencias: {e}")
            return None

    try:
        with open(RUTA_SUGERENCIAS, encoding="utf-8") as f:
            _sugerencias = json.load(f)
    except Exception as e:
        logger.error(f"Fallo al leer sugerencias: {e}")
        return None

    return _sugerencias