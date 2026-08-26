"""Pruebas del sintetizador de respuestas.

Lo que importa no es que devuelva un documento concreto --el corpus puede
cambiar-- sino las dos propiedades que lo hacen confiable: que cada palabra
de la respuesta esté en un documento real, y que calle cuando el corpus no
cubre la pregunta.

Lo segundo es lo difícil. Un sistema que siempre responde algo es peor que
uno que a veces dice que no sabe, porque no se puede saber cuándo creerle.
"""

import pytest
from fastapi.testclient import TestClient

from app.core import acceso
from app.main import app
from app.ml import semantico
from app.services import sintetizador

client = TestClient(app)

_buscador = semantico.cargar_buscador()
hay = _buscador is not None and _buscador.hay_pasajes
sin_material = pytest.mark.skipif(not hay, reason="faltan los pasajes o el modelo")

# El corpus las cubre: son artículos partidos en varios fragmentos.
CUBIERTAS = [
    "que es una base de datos relacional",
    "como se protege una aplicacion de ataques",
    "que es cross site scripting",
]

# El corpus no las cubre, o solo tiene un documento suelto que puntúa alto
# por casualidad.
AJENAS = [
    "receta de sopa de tomate con albahaca",
    "cual es la capital de mongolia",
    "como podar un rosal en primavera",
]


@pytest.fixture(autouse=True)
def limite_limpio():
    acceso._historial.clear()
    yield
    acceso._historial.clear()


# --- lo que responde -------------------------------------------------------

@sin_material
@pytest.mark.parametrize("pregunta", CUBIERTAS)
def test_responde_lo_que_el_corpus_cubre(pregunta):
    r = sintetizador.responder(pregunta)
    assert r is not None, f"«{pregunta}» deberia tener respuesta"
    assert r["fragmentos"], "una respuesta sin fragmentos no es una respuesta"
    assert r["parecido"] >= sintetizador.UMBRAL


@sin_material
@pytest.mark.parametrize("pregunta", AJENAS)
def test_calla_cuando_no_sabe(pregunta):
    assert sintetizador.responder(pregunta) is None, (
        f"invento una respuesta para «{pregunta}»")


# --- lo que la hace confiable ---------------------------------------------

@sin_material
def test_cada_fragmento_es_texto_real_del_corpus():
    """Nada de la respuesta puede estar redactado.

    Es la propiedad que separa esto de un modelo generativo: se puede ir al
    documento y comprobar cada linea.
    """
    r = sintetizador.responder("que es una base de datos relacional")
    buscador = semantico.cargar_buscador()

    todos = {buscador.documento(i)["texto"] for i in range(buscador.total_documentos)
             if buscador.documento(i)["texto"]}
    for f in r["fragmentos"]:
        assert f["texto"] in todos, "un fragmento no corresponde a ningun documento"


@sin_material
def test_los_fragmentos_vienen_en_el_orden_del_original():
    """Se ordenan por numero de parte, no por parecido.

    Un articulo leido en el orden en que fue escrito se entiende; los
    mismos parrafos barajados por su puntaje, no.
    """
    r = sintetizador.responder("como se protege una aplicacion de ataques")
    numeros = [f["parte"] for f in r["fragmentos"]]
    assert numeros == sorted(numeros)


@sin_material
def test_hace_falta_mas_de_un_fragmento():
    """Un documento suelto no alcanza, por alto que puntue.

    Medido: las preguntas que el corpus cubre traen entre 3 y 8 fragmentos
    del mismo documento; las que no, exactamente uno. El parecido solo no
    las separa, porque las dos bandas se solapan.
    """
    assert sintetizador.MIN_FRAGMENTOS >= 2

    r = sintetizador.responder("que es una base de datos relacional")
    # La respuesta se recorta a 4, pero el grupo tenia mas.
    assert len(r["fragmentos"]) >= 2


@sin_material
def test_dice_de_donde_lo_saco():
    r = sintetizador.responder("que es cross site scripting")
    assert r["fuente"], "una respuesta sin fuente no se puede comprobar"
    assert r["documentos_consultados"] > 30000


# --- el endpoint -----------------------------------------------------------

@sin_material
def test_el_asistente_devuelve_la_respuesta_del_historico():
    j = client.post("/v1/chat", json={"texto": "que es una base de datos relacional"}).json()
    assert j["del_historico"] is not None
    assert j["del_historico"]["fragmentos"]
    assert j["del_historico"]["fuente"] in j["respuesta"]


@sin_material
def test_sin_respuesta_del_historico_explica_la_clasificacion():
    """El modo anterior sigue ahi para lo que no es una pregunta."""
    j = client.post("/v1/chat", json={"texto": "receta de sopa de tomate con albahaca"}).json()
    assert j["del_historico"] is None
    assert j["categoria"], "tiene que seguir clasificando"
    assert len(j["respuesta"]) > 50
