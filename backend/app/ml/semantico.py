"""Busqueda semantica: por significado, no por palabras compartidas.

Es distinta de /buscar y de los contenidos relacionados, que comparan
terminos: alli un documento aparece si comparte palabras con la consulta.
Aca la consulta y los documentos se llevan a un espacio donde la cercania
mide significado, asi que un documento puede salir sin compartir ni una
palabra.

Sobre este corpus eso resuelve un caso concreto y frecuente. El 95,9% de
los documentos esta en ingles y la interfaz esta en español: quien escribe
«como protejo las contraseñas» no tiene con que emparejarse contra un
documento que dice *password hashing*. El modelo es multilingue y cruza los
dos idiomas.

Lo que cuesta: 113 MB de modelo mas 29 MB de vectores. Se carga una sola
vez por proceso y codifica una consulta en unos 6 ms.
"""

import logging
import os
from pathlib import Path
from typing import List

import numpy as np
import requests

logger = logging.getLogger(__name__)

# El corte se busco midiendo 12 consultas tecnicas contra 10 ajenas al
# corpus --recetas, futbol, historia romana-- y mirando el mejor parecido
# de cada una:
#
#              min     mediana    max
#   tecnicas   0,498    0,621    0,721
#   ajenas     0,346    0,445    0,579
#
# En 0,48 pasan las 12 tecnicas y quedan fuera 8 de las 10 ajenas.
#
# Las dos distribuciones se solapan: la peor consulta tecnica puntua por
# debajo de la mejor ajena, asi que ninguna linea las separa del todo. Es
# una propiedad del modelo, que comprime los cosenos en una banda estrecha,
# y no algo que se arregle moviendo el numero. Se prefiere no perder
# ninguna consulta legitima y dejar pasar alguna ajena con puntaje bajo,
# que ademas se muestra en pantalla.
UMBRAL = 0.48

RAIZ = Path(__file__).resolve().parents[3]
RUTA_VECTORES = RAIZ / "modelos" / "embeddings.npy"
RUTA_MODELO = RAIZ / "semantica" / "modelo" / "modelo.onnx"
RUTA_TOKENIZADOR = RAIZ / "semantica" / "modelo" / "tokenizer.json"

# Los 122 MB del modelo no se versionan, asi que si no estan en disco se
# bajan al arrancar. Por defecto desde donde los publica su autor; la
# variable de entorno permite apuntar a otro lado --a un bucket propio, por
# ejemplo-- sin tocar el codigo.
_HF = ("https://huggingface.co/sentence-transformers/"
       "paraphrase-multilingual-MiniLM-L12-v2/resolve/main/")
URLS_POR_DEFECTO = {
    "MODELO_EMB_URL": _HF + "onnx/model_quint8_avx2.onnx",
    "TOKENIZADOR_EMB_URL": _HF + "tokenizer.json",
    "EMBEDDINGS_URL": None,   # los vectores son propios: van en el repositorio
}

_buscador = None


class BuscadorSemantico:
    def __init__(self, vectores: np.ndarray, codificador, titulos, extractos, categorias, ids):
        # Los vectores se guardan en float16 para ocupar la mitad, y se
        # suben a float32 al cargarlos: el producto punto en float16 pierde
        # precision de forma visible cuando se suman 384 terminos.
        self._vectores = vectores.astype(np.float32)
        self._codificar = codificador
        self._titulos = titulos
        self._extractos = extractos
        self._categorias = categorias
        self._ids = ids

    def buscar(self, consulta: str, top_n: int = 5, umbral: float = UMBRAL) -> List[dict]:
        if not consulta or not consulta.strip():
            return []

        vector = self._codificar([consulta])[0]
        # Los dos lados estan normalizados, asi que el producto punto ya es
        # el coseno.
        parecidos = self._vectores @ vector

        cantidad = min(top_n, parecidos.size)
        candidatos = np.argpartition(parecidos, -cantidad)[-cantidad:]
        candidatos = candidatos[np.argsort(parecidos[candidatos])[::-1]]

        return [
            {
                "id": int(self._ids[i]),
                "titulo": str(self._titulos[i]),
                "extracto": str(self._extractos[i]) if self._extractos is not None else "",
                "categoria": str(self._categorias[i]),
                "parecido": round(float(parecidos[i]), 3),
            }
            for i in candidatos
            if parecidos[i] >= umbral
        ]

    @property
    def total_documentos(self) -> int:
        return int(self._vectores.shape[0])


def _descargar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    respuesta = requests.get(url, stream=True, timeout=300)
    respuesta.raise_for_status()
    with open(destino, "wb") as archivo:
        for pedazo in respuesta.iter_content(chunk_size=1 << 16):
            archivo.write(pedazo)


def cargar_buscador():
    """Deja el buscador listo, o None si falta alguna pieza.

    La busqueda semantica es opcional: si el modelo o los vectores no estan,
    el resto de la API funciona igual y el endpoint responde 503 explicando
    que falta. Vale mas eso que impedir que el servicio arranque.
    """
    global _buscador
    if _buscador is not None:
        return _buscador

    for ruta, variable in ((RUTA_VECTORES, "EMBEDDINGS_URL"),
                           (RUTA_MODELO, "MODELO_EMB_URL"),
                           (RUTA_TOKENIZADOR, "TOKENIZADOR_EMB_URL")):
        if ruta.exists():
            continue
        url = os.getenv(variable) or URLS_POR_DEFECTO.get(variable)
        if not url:
            logger.warning("Sin busqueda semantica: falta %s y no hay %s", ruta.name, variable)
            return None
        try:
            logger.info("Descargando %s...", ruta.name)
            _descargar(url, ruta)
        except Exception as e:
            logger.error("No se pudo descargar %s: %s", ruta.name, e)
            return None

    try:
        import sys
        sys.path.insert(0, str(RAIZ / "semantica"))
        from codificador import Codificador

        from app.ml.recomendador import cargar_recomendador
        reco = cargar_recomendador()
        if reco is None:
            logger.error("Sin busqueda semantica: la matriz historica no cargo")
            return None

        vectores = np.load(RUTA_VECTORES)
        if vectores.shape[0] != reco.total_documentos:
            logger.error("Los vectores (%s) no coinciden con la matriz (%s): "
                         "hay que regenerarlos con semantica/generar_embeddings.py",
                         vectores.shape[0], reco.total_documentos)
            return None

        codificador = Codificador(str(RUTA_MODELO), str(RUTA_TOKENIZADOR), hebras=1)
        _buscador = BuscadorSemantico(
            vectores, codificador,
            reco._titulos, reco._extractos, reco._categorias, reco._ids,
        )
        logger.info("Busqueda semantica lista: %s documentos", _buscador.total_documentos)
        return _buscador
    except Exception as e:
        logger.error("No se pudo iniciar la busqueda semantica: %s", e)
        return None


def hay_semantica() -> bool:
    return _buscador is not None
