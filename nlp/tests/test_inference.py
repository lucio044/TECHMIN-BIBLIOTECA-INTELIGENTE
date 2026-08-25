"""
Pruebas de la fachada `src.inference` — el punto de entrada que realmente
consume la API.

Las pruebas de `test_classifier.py` verifican la lógica de clasificación
inyectando dobles. Estas verifican otra cosa: que la fachada arme bien sus
dependencias, cachee el clasificador, y devuelva un dict serializable con
el contrato acordado. Es la capa que nadie estaba probando.

Para no depender del `.joblib` real (varios MB), se apunta MODELO_PATH a un
Pipeline pequeño serializado en un directorio temporal.
"""

import json
from pathlib import Path

import joblib
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src import inference
from src.exceptions import (
    EntradaInvalidaError,
    ModeloNoDisponibleError,
    TextoVacioError,
)
from src.inference import precargar_modelo, procesar_contenido


def _crear_pipeline_entrenado() -> Pipeline:
    """Mismo criterio de balance que en test_classifier.py: 2 ejemplos por
    categoría, para que un texto desconocido produzca confianza baja de
    forma determinista."""
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(min_df=1)),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    textos = [
        "docker kubernetes container deployment",
        "docker container orchestration cloud",
        "postgresql database index query optimization",
        "database sql query performance",
        "react frontend component hooks",
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
def modelo_temporal(tmp_path: Path, monkeypatch):
    """Apunta la fachada a un modelo de prueba y limpia la caché de
    `_obtener_clasificador` antes y después, para que el estado no se
    filtre entre pruebas."""
    ruta = tmp_path / "modelo_de_prueba.joblib"
    joblib.dump(_crear_pipeline_entrenado(), ruta)

    monkeypatch.setattr(inference, "MODELO_PATH", ruta)
    inference._obtener_clasificador.cache_clear()
    yield ruta
    inference._obtener_clasificador.cache_clear()


@pytest.fixture
def sin_modelo(tmp_path: Path, monkeypatch):
    """Apunta la fachada a una ruta donde no hay ningún modelo."""
    monkeypatch.setattr(inference, "MODELO_PATH", tmp_path / "no_existe.joblib")
    inference._obtener_clasificador.cache_clear()
    yield
    inference._obtener_clasificador.cache_clear()


def test_procesar_contenido_devuelve_el_contrato_base(modelo_temporal):
    resultado = procesar_contenido(
        titulo="Despliegue con contenedores",
        texto="docker kubernetes container deployment",
    )
    assert isinstance(resultado, dict)
    assert set(resultado) == {"categoria", "probabilidad", "informacion_adicional"}
    assert resultado["categoria"] == "DevOps / Cloud"
    assert isinstance(resultado["informacion_adicional"], list)
    # Tipo EXACTO, no isinstance: numpy.float64 hereda de float y numpy.str_
    # de str, así que isinstance los daría por buenos. Ver el test de tipos
    # nativos más abajo para por qué esto importa.
    assert type(resultado["probabilidad"]) is float
    assert type(resultado["categoria"]) is str


def test_procesar_contenido_agrega_alternativa_si_la_confianza_es_baja(modelo_temporal):
    resultado = procesar_contenido(titulo="", texto="xyz completamente desconocido")
    assert resultado["probabilidad"] < 0.5
    assert resultado["categoria_alternativa"] != resultado["categoria"]


def test_procesar_contenido_devuelve_algo_serializable_a_json(modelo_temporal):
    # Es lo que la API hará con esto. ensure_ascii=False porque la respuesta
    # puede llevar acentos (contenido en español).
    resultado = procesar_contenido(
        titulo="Consulta lenta",
        texto="Cómo optimizar una consulta que tarda mucho",
    )
    texto_json = json.dumps(resultado, ensure_ascii=False)
    assert json.loads(texto_json) == resultado


def test_procesar_contenido_devuelve_tipos_nativos_de_python(modelo_temporal):
    """El pipeline debe convertir los tipos de numpy a tipos nativos.

    OJO con probar esto vía json.dumps: en numpy 2.x, numpy.float64 hereda
    de float y numpy.str_ de str, así que json.dumps los serializa sin
    quejarse y una prueba basada solo en eso pasaría igual aunque el
    pipeline dejara escapar tipos de numpy. Otros consumidores (Pydantic
    con validación estricta, algunos serializadores de ORM) sí distinguen,
    por eso aquí se verifica el tipo exacto.
    """
    resultado = procesar_contenido(titulo="", texto="xyz completamente desconocido")

    assert type(resultado["categoria"]) is str
    assert type(resultado["probabilidad"]) is float
    assert all(type(palabra) is str for palabra in resultado["informacion_adicional"])
    assert type(resultado["categoria_alternativa"]) is str


def test_procesar_contenido_reutiliza_el_clasificador_entre_llamadas(modelo_temporal):
    procesar_contenido(titulo="react", texto="frontend component")
    primeras_llamadas = inference._obtener_clasificador.cache_info()

    procesar_contenido(titulo="docker", texto="kubernetes deployment")
    segundas_llamadas = inference._obtener_clasificador.cache_info()

    # La segunda llamada debe salir de caché: leer el .joblib en cada
    # request haría inviable el tiempo de respuesta de la API.
    assert segundas_llamadas.hits > primeras_llamadas.hits
    assert segundas_llamadas.misses == 1


def test_procesar_contenido_propaga_entrada_invalida(modelo_temporal):
    with pytest.raises(EntradaInvalidaError):
        procesar_contenido(titulo=None, texto="algo")  # type: ignore[arg-type]


def test_procesar_contenido_propaga_texto_vacio(modelo_temporal):
    with pytest.raises(TextoVacioError):
        procesar_contenido(titulo="", texto="")


def test_procesar_contenido_falla_si_no_hay_modelo(sin_modelo):
    with pytest.raises(ModeloNoDisponibleError):
        procesar_contenido(titulo="react", texto="frontend component")


def test_precargar_modelo_no_lanza_si_el_modelo_existe(modelo_temporal):
    precargar_modelo()
    # Y después de precargar, clasificar sigue funcionando normalmente.
    resultado = procesar_contenido(titulo="react", texto="frontend component")
    assert resultado["categoria"] == "Frontend"


def test_precargar_modelo_falla_al_arrancar_si_falta_el_modelo(sin_modelo):
    # El valor de la precarga: el error sale aquí, no frente al usuario.
    with pytest.raises(ModeloNoDisponibleError):
        precargar_modelo()
