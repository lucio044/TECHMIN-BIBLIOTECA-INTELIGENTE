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

        # El vocabulario se pide una sola vez: get_feature_names_out()
        # reconstruye el arreglo completo en cada llamada.
        self._vocabulario = self._vectorizador.get_feature_names_out()

    def _pesos(self, vector):
        """Producto punto de la consulta contra todo el historico.

        La matriz esta guardada en float32 y el vectorizador devuelve la
        consulta en float64. Mezclados, scipy sube los 4,2 millones de
        valores de la matriz a float64 antes de multiplicar. Igualar el
        tipo de la consulta evita esa conversion: el producto pasa de 18,4
        a 6,9 ms, y la diferencia en la similitud es del orden de 1e-8, que
        no cambia ni los valores redondeados a tres decimales ni el orden.
        """
        vector = vector.astype(self._matriz.dtype, copy=False)
        return (self._matriz @ vector.T).toarray().ravel()

    def recomendar(self, texto: str, top_n: int = 3, umbral: float = UMBRAL_SIMILITUD_MINIMA) -> List[dict]:
        if not texto or not texto.strip():
            return []

        vector = self._vectorizador.transform([texto])
        similitudes = self._pesos(vector)

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

    def buscar(self, termino: str, top_n: int = 10) -> List[dict]:
        """Busca en el historico los documentos donde ese termino pesa mas.

        Es distinto de `recomendar`: alli entra un texto completo y se
        buscan documentos parecidos en conjunto. Aca entra un termino
        suelto y se devuelven los documentos que mas hablan de el.

        El vector de una sola palabra tiene un solo valor distinto de cero,
        asi que el producto punto solo alcanza a los documentos que
        contienen ese termino. No hay coincidencias por parecido: si el
        documento no lo menciona, no aparece.

        Devuelve lista vacia si el termino no esta en el vocabulario del
        modelo, que es una respuesta legitima y no un error.
        """
        if not termino or not termino.strip():
            return []

        vector = self._vectorizador.transform([termino.strip()])
        if vector.nnz == 0:
            return []

        pesos = self._pesos(vector)

        cantidad = min(top_n, pesos.size)
        candidatos = np.argpartition(pesos, -cantidad)[-cantidad:]
        candidatos = candidatos[np.argsort(pesos[candidatos])[::-1]]

        return [
            {
                "id": int(self._ids[i]),
                "titulo": str(self._titulos[i]),
                "extracto": str(self._extractos[i]) if self._extractos is not None else "",
                "categoria": str(self._categorias[i]),
                "relevancia": round(float(pesos[i]), 3),
            }
            for i in candidatos
            if pesos[i] > 0
        ]

    def termino_conocido(self, termino: str) -> bool:
        """Indica si el termino existe en el vocabulario del modelo."""
        return self._vectorizador.transform([termino.strip()]).nnz > 0

    @property
    def total_documentos(self) -> int:
        """Cuantos documentos hay indexados."""
        return int(self._matriz.shape[0])


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