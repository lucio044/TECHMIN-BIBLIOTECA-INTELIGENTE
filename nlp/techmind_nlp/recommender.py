"""
Recomendación de contenido relacionado por similitud del coseno.

Dado un texto, devuelve los documentos del histórico que hablan de lo mismo.
Se apoya en la matriz TF-IDF del corpus, serializada aparte del clasificador
porque son dos artefactos con ciclos de vida distintos: el modelo se reentrena
cuando cambian las categorías, la matriz cuando crece el histórico.

Sobre el cálculo: no se guarda la matriz de similitudes entre todos los pares.
Con 38.000 documentos serían más de mil cuatrocientos millones de valores, casi
todos cercanos a cero. Se guardan los vectores y se compara contra ellos
únicamente el texto que llega, que es una operación por consulta.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

import joblib
import numpy as np

from techmind_nlp.exceptions import ModeloNoDisponibleError, ModeloInvalidoError

# Por debajo de este valor no hay parecido real: es preferible no devolver nada
# a devolver el resultado menos malo. Sale de observar que las consultas con
# material afín en el corpus alcanzan 0,28 o más.
UMBRAL_SIMILITUD_MINIMA: float = 0.10

# Claves que el paquete serializado debe contener para ser utilizable.
_CLAVES_REQUERIDAS = ("vectorizador", "matriz", "ids", "categorias", "titulos")


@dataclass(frozen=True)
class ContenidoRelacionado:
    """Un documento del histórico parecido al texto consultado."""

    id: int
    titulo: str
    categoria: str
    similitud: float


class RecomendadorContenido:
    """Busca en el histórico los documentos más parecidos a un texto.

    El paquete se carga una sola vez, al construir el recomendador, y queda
    en memoria: cargarlo en cada consulta añadiría medio segundo a cada
    petición.
    """

    def __init__(self, ruta_paquete: Path) -> None:
        """
        Args:
            ruta_paquete: Ruta al .pkl con el vectorizador, la matriz y los
                metadatos de cada documento.

        Raises:
            ModeloNoDisponibleError: Si el archivo no existe.
            ModeloInvalidoError: Si el archivo no contiene lo esperado.
        """
        if not ruta_paquete.exists():
            raise ModeloNoDisponibleError(
                f"No se encontró la matriz histórica en {ruta_paquete}"
            )

        paquete = joblib.load(ruta_paquete)

        faltantes = [c for c in _CLAVES_REQUERIDAS if c not in paquete]
        if faltantes:
            raise ModeloInvalidoError(
                f"La matriz histórica no contiene: {', '.join(faltantes)}"
            )

        self._vectorizador = paquete["vectorizador"]
        self._ids = paquete["ids"]
        self._categorias = paquete["categorias"]
        self._titulos = paquete["titulos"]

        # CSR es el formato que hace eficiente el producto matriz-vector. Si el
        # paquete llegara en otro formato (COO, CSC), la multiplicación sería
        # varias veces más lenta sin que nada lo advierta.
        matriz = paquete["matriz"]
        self._matriz = matriz.tocsr() if matriz.format != "csr" else matriz

    def recomendar(
        self,
        texto: str,
        top_n: int = 3,
        umbral: float = UMBRAL_SIMILITUD_MINIMA,
    ) -> List[ContenidoRelacionado]:
        """Devuelve los documentos del histórico más parecidos a `texto`.

        Args:
            texto: Contenido a comparar. Se espera el texto ya concatenado
                (título + cuerpo), igual que recibe el clasificador.
            top_n: Cantidad máxima de resultados.
            umbral: Similitud mínima para considerar que hay parecido real.

        Returns:
            Lista ordenada de mayor a menor similitud. Vacía si nada del
            histórico supera el umbral, que es una respuesta legítima: no
            siempre hay contenido relacionado.
        """
        if not texto or not texto.strip():
            return []

        vector = self._vectorizador.transform([texto])

        # TfidfVectorizer normaliza cada vector a norma 1, así que la
        # similitud del coseno se reduce al producto punto. cosine_similarity
        # recalcularía unas normas que ya valen 1: el producto punto da el
        # mismo resultado y resuelve en 28 ms sobre este corpus.
        similitudes = (self._matriz @ vector.T).toarray().ravel()

        # argpartition ordena solo los top_n en lugar de las 38.000 posiciones.
        cantidad = min(top_n, similitudes.size)
        candidatos = np.argpartition(similitudes, -cantidad)[-cantidad:]
        candidatos = candidatos[np.argsort(similitudes[candidatos])[::-1]]

        return [
            ContenidoRelacionado(
                id=int(self._ids[i]),
                titulo=str(self._titulos[i]),
                categoria=str(self._categorias[i]),
                similitud=round(float(similitudes[i]), 3),
            )
            for i in candidatos
            if similitudes[i] >= umbral
        ]

    @property
    def total_documentos(self) -> int:
        """Cuántos documentos hay en el histórico indexado."""
        return int(self._matriz.shape[0])
