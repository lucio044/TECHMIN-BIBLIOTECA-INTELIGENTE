"""Pruebas del asistente y de la explicacion que lo sostiene.

Lo que se verifica no es la redaccion --que cambia-- sino que la evidencia
salga del modelo y sea coherente con la clasificacion.
"""

import pytest
from fastapi.testclient import TestClient

from app.core import acceso
from app.main import app
from app.services import explicacion

client = TestClient(app)

MOVIL = ("Construccion de interfaces declarativas con Kotlin y Jetpack Compose, "
         "manejo del estado y ciclo de vida de las actividades")
NUBE = "como configuro un cluster de kubernetes con ingress y certificados tls"
AJENO = "receta de sopa de tomate con albahaca y un poco de crema"


@pytest.fixture(autouse=True)
def limite_limpio():
    acceso._historial.clear()
    yield
    acceso._historial.clear()


# --- terminos decisivos ---------------------------------------------------

def test_los_terminos_salen_del_texto_y_empujan_a_favor():
    categoria, probabilidad, terminos = explicacion.terminos_decisivos(MOVIL)

    assert categoria == "Mobile"
    assert probabilidad > 0.9
    assert terminos, "el texto tiene vocabulario tecnico claro"

    minusculas = MOVIL.lower()
    for t in terminos:
        assert t["termino"] in minusculas, f"«{t['termino']}» no esta en el texto"
        assert t["aporte"] > 0, "solo interesan los que empujaron a favor"


def test_vienen_ordenados_de_mayor_a_menor_aporte():
    _, _, terminos = explicacion.terminos_decisivos(NUBE)
    aportes = [t["aporte"] for t in terminos]
    assert aportes == sorted(aportes, reverse=True)


def test_las_palabras_de_funcion_no_se_presentan_como_motivo():
    """«de» y «con» reciben peso del modelo, pero no explican nada.

    Si aparecieran arriba, la explicacion diria que una clasificacion se
    decidio por una preposicion.
    """
    for texto in (MOVIL, NUBE):
        _, _, terminos = explicacion.terminos_decisivos(texto)
        for t in terminos:
            assert not all(p in explicacion.SIN_CONTENIDO for p in t["termino"].split())


def test_un_texto_ajeno_al_corpus_no_inventa_terminos():
    _, probabilidad, terminos = explicacion.terminos_decisivos(AJENO)
    assert probabilidad < 0.5
    assert terminos == []


# --- el endpoint ----------------------------------------------------------

def test_el_chat_responde_sin_proveedor_externo():
    r = client.post("/v1/chat", json={"texto": MOVIL})
    assert r.status_code == 200

    cuerpo = r.json()
    assert cuerpo["fuente"] == "modelo"
    assert cuerpo["categoria"] == "Mobile"
    assert cuerpo["probabilidad"] > 0.9
    assert len(cuerpo["respuesta"]) > 80


def test_la_respuesta_nombra_la_categoria_y_los_terminos():
    cuerpo = client.post("/v1/chat", json={"texto": MOVIL}).json()

    assert cuerpo["categoria"] in cuerpo["respuesta"]
    for t in cuerpo["terminos_decisivos"][:2]:
        assert t["termino"] in cuerpo["respuesta"].lower()


def test_no_se_disculpa_cuando_no_hay_clave():
    """El modo sin proveedor es normal, no degradado.

    La version anterior contestaba "No pude conectar con el asistente",
    que convertia el funcionamiento habitual en un aviso de error.
    """
    respuesta = client.post("/v1/chat", json={"texto": NUBE}).json()["respuesta"].lower()
    for disculpa in ("no pude", "lo siento", "disculpa", "en este momento"):
        assert disculpa not in respuesta


def test_avisa_cuando_la_decision_es_floja():
    cuerpo = client.post("/v1/chat", json={"texto": AJENO}).json()
    assert cuerpo["probabilidad"] < 0.5
    assert "firme" in cuerpo["respuesta"] or "parecido" in cuerpo["respuesta"]


def test_el_historial_previo_no_rompe_la_llamada():
    r = client.post("/v1/chat", json={
        "texto": MOVIL,
        "historial": [
            {"rol": "user", "contenido": "hola"},
            {"rol": "assistant", "contenido": "hola, en que ayudo"},
        ],
    })
    assert r.status_code == 200
    assert r.json()["categoria"] == "Mobile"
