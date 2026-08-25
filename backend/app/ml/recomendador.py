import logging
from pathlib import Path
from typing import List

import joblib
import numpy as np
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

RUTA_MATRIZ = Path(__file__).resolve().parent / "matriz_historica.pkl"

_recomendador = None  # cache en memoria, mismo patron que _modelo en loader.py

UMBRAL_SIMILITUD_MINIMA = 0.10
_CLAVES_REQUERIDAS = ("vectorizador", "matriz", "ids", "categorias", "titulos")


def _descargar_archivo(url: str, ruta_destino: Path) -> Path:
    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    respuesta = requests.get(url, stream=True)
    respuesta.raise_for_status()
    with open(ruta_destino, "wb") as archivo:
        for pedazo in respuesta.iter_content(chunk_size=8192):
            archivo.write(pedazo)
    return ruta_destino


class RecomendadorContenido:
    def __init__(self, paquete: dict) -> None:
        self._vectorizador = paquete["vectorizador"]
        self._ids = paquete["ids"]
        self._categorias = paquete["categorias"]
        self._titulos = paquete["titulos"]
        # La matriz trae extractos desde la version con la clave "extractos".
        # Se lee con .get() para que una matriz anterior, que no la tiene,
        # siga cargando: en ese caso el extracto viaja vacio y la tarjeta
        # muestra solo el titulo, como antes.
        self._extractos = paquete.get("extractos")
        matriz = paquete["matriz"]
        self._matriz = matriz.tocsr() if matriz.format != "csr" else matriz

    def recomendar(self, texto: str, top_n: int = 3, umbral: float = UMBRAL_SIMILITUD_MINIMA) -> List[dict]:
        if not texto or not texto.strip():
            return []

        vector = self._vectorizador.transform([texto])
        similitudes = (self._matriz @ vector.T).toarray().ravel()

        cantidad = min(top_n, similitudes.size)
        candidatos = np.argpartition(similitudes, -cantidad)[-cantidad:]
        candidatos = candidatos[np.argsort(similitudes[candidatos])[::-1]]

        return [
            {
                "id": int(self._ids[i]),
                "titulo": str(self._titulos[i]),
                "extracto": str(self._extractos[i]) if self._extractos is not None else "",
                "categoria": str(self._categorias[i]),
                "similitud": round(float(similitudes[i]), 3),
            }
            for i in candidatos
            if similitudes[i] >= umbral
        ]


def cargar_recomendador():
    global _recomendador
    if _recomendador is not None:
        return _recomendador

    if not RUTA_MATRIZ.exists():
        if not settings.matriz_historica_url:
            logger.warning("Matriz historica no encontrada localmente y falta MATRIZ_HISTORICA_URL")
            return None
        try:
            logger.info("Matriz historica no encontrada localmente, descargando desde OCI...")
            _descargar_archivo(settings.matriz_historica_url, RUTA_MATRIZ)
        except requests.exceptions.RequestException as e:
            logger.error(f"Fallo al descargar la matriz historica: {e}")
            return None

    try:
        paquete = joblib.load(RUTA_MATRIZ)
        faltantes = [c for c in _CLAVES_REQUERIDAS if c not in paquete]
        if faltantes:
            logger.error(f"Matriz historica invalida, faltan claves: {faltantes}")
            return None
        _recomendador = RecomendadorContenido(paquete)
    except Exception as e:
        logger.error(f"Fallo al cargar la matriz historica: {e}")
        return None

    return _recomendador