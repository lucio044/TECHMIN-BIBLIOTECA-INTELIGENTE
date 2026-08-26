"""Pruebas de la traducción a pedido.

El corpus está en inglés al 95,9 % y la interfaz en español, así que hay
temas donde una consulta en castellano solo encuentra material en inglés.
Para eso está el botón «Ver en español» sobre los resultados.

Es lo único que traduce: la clasificación no pasa por acá y no puede
empezar a hacerlo sin que estas pruebas se quejen.
"""

import pytest
from fastapi.testclient import TestClient

from app.core import acceso
from app.main import app
from app.ml import traductor

client = TestClient(app)

hay = traductor.hay_traductor("es-en") and traductor.hay_traductor("en-es")
sin_modelo = pytest.mark.skipif(not hay, reason="faltan los modelos de traducción")


@pytest.fixture(autouse=True)
def limite_limpio():
    acceso._historial.clear()
    yield
    acceso._historial.clear()


# --- detección de idioma ---------------------------------------------------

def test_reconoce_en_que_idioma_esta_escrito():
    """No es detección seria: alcanza para elegir la dirección."""
    for texto in ("Cómo protejo las contraseñas de mis usuarios",
                  "El servidor se cae cuando entran muchas personas",
                  "Guardar millones de registros y buscarlos por fecha"):
        assert traductor.idioma_de(texto) == "es", texto

    for texto in ("How do I hash passwords for user accounts",
                  "The server crashes when many people connect",
                  "Storing millions of records and querying them by date"):
        assert traductor.idioma_de(texto) == "en", texto


def test_ante_la_duda_supone_ingles():
    """Es lo que domina el corpus: equivocarse hacia ahí cuesta menos."""
    assert traductor.idioma_de("docker kubernetes nginx") == "en"


# --- traducir --------------------------------------------------------------

@sin_modelo
def test_un_texto_que_ya_esta_en_el_idioma_pedido_no_se_toca():
    """Traducir de un idioma a sí mismo estropea el texto."""
    original = "Esto ya está escrito en español y no hay nada que traducir"
    r = client.post("/v1/traducir", json={"textos": [original], "destino": "es"})
    assert r.status_code == 200
    assert r.json()["traducciones"][0] == original
    assert r.json()["ya_estaban_en_destino"] == 1


@sin_modelo
def test_traduce_del_ingles_al_espanol():
    r = client.post("/v1/traducir", json={
        "textos": ["How to hash passwords for user accounts"], "destino": "es"})
    assert r.status_code == 200
    t = r.json()["traducciones"][0]
    assert t.lower() != "how to hash passwords for user accounts"
    assert "contraseñas" in t.lower() or "claves" in t.lower()


@sin_modelo
def test_traduce_del_espanol_al_ingles():
    r = client.post("/v1/traducir", json={
        "textos": ["¿Cómo protejo las contraseñas de mis usuarios?"], "destino": "en"})
    assert r.status_code == 200
    assert "password" in r.json()["traducciones"][0].lower()


@sin_modelo
def test_acepta_varios_textos_en_una_llamada():
    """Traducir una respuesta son sus cuatro fragmentos: en una peticion
    gasta uno del limite por minuto y no cuatro."""
    r = client.post("/v1/traducir", json={
        "textos": ["The server is down", "Check the logs", "Restart the service"],
        "destino": "es"})
    assert r.status_code == 200
    assert len(r.json()["traducciones"]) == 3


def test_rechaza_un_idioma_que_no_existe():
    r = client.post("/v1/traducir", json={"textos": ["hola"], "destino": "fr"})
    assert r.status_code == 422


def test_rechaza_una_lista_vacia():
    assert client.post("/v1/traducir", json={"textos": [], "destino": "es"}).status_code == 422


def test_el_estado_dice_que_hay_disponible():
    r = client.get("/v1/traducir/estado")
    assert r.status_code == 200
    assert set(r.json()) >= {"es_en", "en_es", "cargados"}


# --- la traduccion no toca la clasificacion --------------------------------

def test_clasificar_no_acepta_pedidos_de_traduccion():
    """Hubo una opción para traducir la entrada antes de clasificar.

    Se sacó: ganaba precisión a cambio de dos segundos por petición y de una
    respuesta que dependía de si una casilla estaba marcada. Si alguien la
    reintroduce sin querer, esta prueba lo dice.
    """
    texto = "Cómo protejo las contraseñas de los usuarios de mi sitio web"
    a = client.post("/v1/contenido", json={"titulo": texto[:50], "texto": texto}).json()
    acceso._historial.clear()
    b = client.post("/v1/contenido",
                    json={"titulo": texto[:50], "texto": texto, "traducir": True}).json()

    # Pydantic ignora lo que no esta en el esquema: el campo no existe y el
    # resultado tiene que ser identico.
    assert a["categoria"] == b["categoria"]
    assert a["probabilidad"] == b["probabilidad"]


def test_clasificar_no_depende_del_traductor():
    """Una clasificación tiene que responder rápido y sin modelos de 342 MB.

    Se comprueba por el tiempo: traducir cuesta alrededor de un segundo y
    medio, y clasificar unos 130 ms.
    """
    import time
    texto = "Cómo protejo las contraseñas de los usuarios de mi sitio web"
    inicio = time.perf_counter()
    r = client.post("/v1/contenido", json={"titulo": texto[:50], "texto": texto})
    assert r.status_code == 200
    assert time.perf_counter() - inicio < 1.0, (
        "clasificar tardo mas de un segundo: revisar si volvio a colgarse "
        "de la traduccion")
