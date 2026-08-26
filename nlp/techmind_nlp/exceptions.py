"""
Excepciones propias del pipeline de NLP.

Usar excepciones específicas (en vez de dejar que exploten ValueError,
FileNotFoundError, etc. genéricos desde sklearn/joblib) le da a quien
consume este pipeline (la API) un contrato claro de qué puede salir mal
y le permite decidir qué código HTTP devolver en cada caso, sin tener
que inspeccionar mensajes de texto.
"""


class TechMindNLPError(Exception):
    """Excepción base del pipeline. Todas las excepciones propias heredan
    de esta — permite capturar "cualquier error de este pipeline" con un
    solo `except TechMindNLPError` cuando no importa el detalle."""


class ModeloNoDisponibleError(TechMindNLPError):
    """El modelo serializado (.joblib) no existe en la ruta esperada o no
    se pudo deserializar (archivo corrupto, incompatibilidad de versión, etc.)."""


class ModeloInvalidoError(TechMindNLPError):
    """El objeto cargado desde el .joblib no tiene la forma esperada de un
    Pipeline de scikit-learn entrenado (le faltan métodos o pasos requeridos)."""


class TextoVacioError(TechMindNLPError):
    """El texto de entrada está vacío, o no queda contenido procesable
    después de la limpieza (por ejemplo, un texto de solo símbolos o números)."""


class EntradaInvalidaError(TechMindNLPError):
    """El tipo de dato de una entrada no es el esperado (ej. no es str)."""
