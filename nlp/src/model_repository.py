"""
Carga y caché del Pipeline serializado (.joblib).

Responsabilidad única: dado un path, entregar un Pipeline de scikit-learn
listo para usar, cacheado en memoria para no releer disco en cada
request. No sabe nada de limpieza de texto, palabras clave, ni del
contrato de salida de la API.
"""

from pathlib import Path
from typing import Optional

import joblib
from sklearn.pipeline import Pipeline

from src.exceptions import ModeloInvalidoError, ModeloNoDisponibleError


class RepositorioModelo:
    """Carga el Pipeline entrenado desde disco y lo mantiene en memoria
    tras la primera carga.

    Se inyecta (no se usa como singleton global) para que las pruebas
    puedan crear un `RepositorioModelo` apuntando a un modelo de prueba,
    sin depender del archivo real en `models/`.
    """

    def __init__(self, ruta_modelo: Path) -> None:
        """
        Args:
            ruta_modelo: Ruta al archivo .joblib del Pipeline entrenado.
        """
        self._ruta_modelo = ruta_modelo
        self._pipeline: Optional[Pipeline] = None

    def obtener_pipeline(self) -> Pipeline:
        """Devuelve el Pipeline cargado, cargándolo de disco solo la
        primera vez que se llama.

        Returns:
            El Pipeline de scikit-learn (TF-IDF + clasificador) listo
            para predecir.

        Raises:
            ModeloNoDisponibleError: si el archivo no existe o no se
                pudo deserializar.
            ModeloInvalidoError: si el objeto cargado no tiene la forma
                esperada de un Pipeline entrenado.
        """
        if self._pipeline is None:
            self._pipeline = self._cargar_desde_disco()
        return self._pipeline

    def _cargar_desde_disco(self) -> Pipeline:
        if not self._ruta_modelo.exists():
            raise ModeloNoDisponibleError(
                f"No se encontró el modelo en '{self._ruta_modelo}'. "
                "Verifica que el archivo .joblib esté en esa ruta."
            )

        try:
            pipeline = joblib.load(self._ruta_modelo)
        except Exception as excepcion_original:
            # Se traduce cualquier error de deserialización (archivo
            # corrupto, incompatibilidad de versión de scikit-learn, etc.)
            # a una excepción propia del dominio, para que quien llama no
            # tenga que conocer los detalles internos de joblib/pickle.
            raise ModeloNoDisponibleError(
                f"No se pudo cargar el modelo desde '{self._ruta_modelo}': "
                f"{excepcion_original}"
            ) from excepcion_original

        self._validar_pipeline(pipeline)
        return pipeline

    @staticmethod
    def _validar_pipeline(pipeline: object) -> None:
        """Verifica que el objeto cargado sea un Pipeline entrenado con
        los pasos que el resto del sistema espera encontrar."""
        if not isinstance(pipeline, Pipeline):
            raise ModeloInvalidoError(
                f"Se esperaba un sklearn.pipeline.Pipeline, se cargó "
                f"{type(pipeline).__name__}."
            )
        if not hasattr(pipeline, "classes_"):
            raise ModeloInvalidoError(
                "El Pipeline cargado no está entrenado (no tiene 'classes_')."
            )
        # ClasificadorContenido depende de predict_proba tanto para el campo
        # 'probabilidad' como para elegir la categoría alternativa. Si el
        # equipo de modelado cambiara a un clasificador que no lo expone
        # (LinearSVC, por ejemplo), sin esta comprobación el fallo aparecería
        # como un AttributeError crudo en pleno request, en vez de como un
        # error propio del dominio traducible a un 503.
        if not hasattr(pipeline, "predict_proba"):
            raise ModeloInvalidoError(
                "El Pipeline no expone 'predict_proba' — se requiere un "
                "clasificador probabilístico (ej. LogisticRegression, o un "
                "modelo envuelto en CalibratedClassifierCV)."
            )
        if "tfidf" not in pipeline.named_steps:
            raise ModeloInvalidoError(
                "El Pipeline no tiene un paso llamado 'tfidf' — no se "
                "pueden extraer palabras clave sin el vectorizador."
            )
