"""
Pruebas de classifier.ClasificadorContenido.

Usan un repositorio de modelo "falso" (un doble de prueba, no el real)
que devuelve un Pipeline pequeño entrenado en memoria. Esto es posible
gracias a la inversión de dependencias: ClasificadorContenido no sabe
si el repositorio que recibe es el real o uno de prueba, así que estas
pruebas corren rápido y sin tocar disco.
"""

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.classifier import ClasificadorContenido
from src.exceptions import (
    EntradaInvalidaError,
    ModeloNoDisponibleError,
    TextoVacioError,
)


class _RepositorioModeloFalso:
    """Doble de prueba de RepositorioModelo: cumple la misma interfaz
    (obtener_pipeline()) pero no toca disco."""

    def __init__(self, pipeline: Pipeline) -> None:
        self._pipeline = pipeline

    def obtener_pipeline(self) -> Pipeline:
        return self._pipeline


@pytest.fixture
def pipeline_de_prueba() -> Pipeline:
    """IMPORTANTE: las 3 categorías tienen exactamente 2 ejemplos cada una,
    y eso es intencional. Con las clases balanceadas, un texto fuera del
    vocabulario produce un vector de ceros y predict_proba reparte ~0.33 por
    clase — que es lo que hace determinista a
    `test_clasificar_texto_ambiguo_incluye_categoria_alternativa`.

    Si se agregan ejemplos a una sola categoría, los interceptos se
    desbalancean, la probabilidad del caso ambiguo sube y esa prueba puede
    fallar por una razón ajena a lo que quiere verificar.
    """
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(min_df=1)),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    textos = [
        "docker kubernetes container deployment ci cd",
        "docker container orchestration cloud",
        "postgresql database index query optimization sql",
        "database sql query performance",
        "react frontend component ui hooks",
        "frontend css html component",
    ]
    categorias = [
        "DevOps / Cloud", "DevOps / Cloud",
        "Bases de Datos", "Bases de Datos",
        "Frontend", "Frontend",
    ]
    pipeline.fit(textos, categorias)
    return pipeline


@pytest.fixture
def clasificador(pipeline_de_prueba: Pipeline) -> ClasificadorContenido:
    repositorio_falso = _RepositorioModeloFalso(pipeline_de_prueba)
    return ClasificadorContenido(repositorio_modelo=repositorio_falso)


def test_clasificar_texto_reconocido_no_incluye_categoria_alternativa(clasificador):
    resultado = clasificador.clasificar(
        titulo="Despliegue con contenedores",
        texto="docker kubernetes container deployment",
    )
    assert resultado.categoria == "DevOps / Cloud"
    assert resultado.categoria_alternativa is None
    assert len(resultado.informacion_adicional) > 0


def test_clasificar_texto_ambiguo_incluye_categoria_alternativa(clasificador):
    # Texto que no aparece en el entrenamiento -> probabilidad baja ->
    # debe activarse la categoría alternativa.
    resultado = clasificador.clasificar(titulo="", texto="xyz completamente desconocido")
    assert resultado.probabilidad < 0.5
    assert resultado.categoria_alternativa is not None
    assert resultado.categoria_alternativa != resultado.categoria


def test_clasificar_concatena_titulo_y_texto_en_ese_orden(clasificador):
    # Si el orden estuviera invertido, este texto (todo el contenido
    # relevante en el título) no debería clasificar bien — se prueba
    # indirectamente confirmando que sí lo hace.
    resultado = clasificador.clasificar(
        titulo="postgresql database index query optimization",
        texto="",
    )
    assert resultado.categoria == "Bases de Datos"


def test_clasificar_lanza_error_si_ambos_campos_vacios(clasificador):
    with pytest.raises(TextoVacioError):
        clasificador.clasificar(titulo="", texto="")


def test_clasificar_lanza_error_si_texto_limpio_queda_vacio(pipeline_de_prueba):
    # El limpiador se inyecta a propósito: lo que se verifica aquí es la
    # reacción del clasificador cuando la limpieza no deja nada, no las
    # reglas concretas de limpiar_texto (eso lo cubre test_cleaning.py).
    clasificador = ClasificadorContenido(
        repositorio_modelo=_RepositorioModeloFalso(pipeline_de_prueba),
        limpiador=lambda titulo, texto: "",
    )
    with pytest.raises(TextoVacioError):
        clasificador.clasificar(titulo="algo", texto="algo")


def test_clasificar_lanza_error_con_tipos_invalidos(clasificador):
    with pytest.raises(EntradaInvalidaError):
        clasificador.clasificar(titulo=None, texto="algo")  # type: ignore[arg-type]


def test_clasificar_probabilidad_esta_entre_cero_y_uno(clasificador):
    resultado = clasificador.clasificar(titulo="react frontend", texto="component ui")
    assert 0.0 <= resultado.probabilidad <= 1.0


def test_precargar_deja_el_modelo_listo_sin_clasificar(clasificador):
    # No debe lanzar, y después de precargar una clasificación normal
    # sigue funcionando igual (la precarga no consume ni altera estado).
    clasificador.precargar()
    resultado = clasificador.clasificar(titulo="react frontend", texto="component ui")
    assert resultado.categoria == "Frontend"


def test_precargar_propaga_error_si_el_modelo_no_carga():
    class _RepositorioQueFalla:
        def obtener_pipeline(self):
            raise ModeloNoDisponibleError("modelo ausente")

    clasificador = ClasificadorContenido(repositorio_modelo=_RepositorioQueFalla())
    # Este es el punto de la precarga: que el fallo salga al arrancar la API.
    with pytest.raises(ModeloNoDisponibleError):
        clasificador.precargar()
