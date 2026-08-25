"""
Punto de entrada simple del pipeline de inferencia para la API.

Este módulo expone dos funciones de conveniencia — procesar_contenido()
y precargar_modelo() — que arman internamente el RepositorioModelo y el
ClasificadorContenido (ver model_repository.py y classifier.py) y los
reutilizan entre llamadas mediante caché. Quien integra esto en la API
(ej. un endpoint de FastAPI) no necesita conocer ninguna clase interna.

Para pruebas unitarias del comportamiento de clasificación en sí, se debe
probar ClasificadorContenido directamente, inyectando un RepositorioModelo
de prueba — ver tests/test_classifier.py.
"""

from functools import lru_cache
from typing import Any, Dict

from src.classifier import ClasificadorContenido
from src.config import MODELO_PATH
from src.model_repository import RepositorioModelo


@lru_cache(maxsize=1)
def _obtener_clasificador() -> ClasificadorContenido:
    """Crea (una sola vez, cacheado) el ClasificadorContenido por defecto,
    apuntando al modelo de producción configurado en config.MODELO_PATH."""
    repositorio_modelo = RepositorioModelo(MODELO_PATH)
    return ClasificadorContenido(repositorio_modelo=repositorio_modelo)


def precargar_modelo() -> None:
    """Carga el modelo por adelantado, sin clasificar nada.

    Llamar esto en el evento de arranque de la API (ej. el `lifespan` o
    `@app.on_event("startup")` de FastAPI) tiene dos efectos: el primer
    request no paga el costo de leer el `.joblib`, y si el modelo falta o
    está corrupto el servicio falla al levantar — que es cuando alguien
    lo puede arreglar — en vez de fallar frente al usuario.

    Raises:
        ModeloNoDisponibleError: si el modelo no se pudo cargar desde disco.
        ModeloInvalidoError: si el modelo cargado no tiene la forma esperada.
    """
    _obtener_clasificador().precargar()


def procesar_contenido(titulo: str, texto: str) -> Dict[str, Any]:
    """Pipeline de inferencia completo: texto crudo -> JSON de respuesta.

    Args:
        titulo: Título del contenido técnico.
        texto: Cuerpo del contenido técnico.

    Returns:
        Diccionario listo para json.dumps(), con el contrato:
        {
            "categoria": str,
            "probabilidad": float,
            "informacion_adicional": list[str],
            "categoria_alternativa": str  # solo si probabilidad es baja
        }

    Raises:
        EntradaInvalidaError: si titulo o texto no son str.
        TextoVacioError: si no queda texto procesable tras la limpieza.
        ModeloNoDisponibleError: si el modelo no se pudo cargar desde disco.
        ModeloInvalidoError: si el modelo cargado no tiene la forma esperada.

        La API debe capturar estas excepciones (todas heredan de
        TechMindNLPError, ver exceptions.py) y traducirlas a respuestas
        HTTP apropiadas (ej. 400 para EntradaInvalidaError/TextoVacioError,
        503 para ModeloNoDisponibleError).
    """
    clasificador = _obtener_clasificador()
    resultado = clasificador.clasificar(titulo, texto)
    return resultado.to_dict()
