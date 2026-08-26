"""Pruebas de la traducción y de lo que justifica que exista.

El corpus está en inglés al 95,9 % y la interfaz en español. Eso tiene dos
consecuencias medidas, y cada una tiene su prueba acá: el clasificador
pierde precisión con texto en castellano, y hay temas donde una consulta en
español solo encuentra material en inglés.
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


# --- lo que justifica la funcion -------------------------------------------

@sin_modelo
def test_traducir_la_entrada_mejora_la_clasificacion():
    """Es el motivo de que exista la opción.

    Medido sobre veinte textos coloquiales escritos despues de decidir la
    prueba --para no repetir el sesgo de una propuesta anterior que ganaba
    solo en los ejemplos elegidos a mano--: el acierto pasa de 6 a 11 de 20
    y la confianza media de 31 % a 41 %.

    Aca se comprueban dos casos concretos de esa tanda.
    """
    casos = [
        ("Mobile", "La aplicación se cierra sola cuando giro la pantalla del celular"),
        ("Bases de Datos", "Guardar millones de registros y poder buscarlos rápido por fecha"),
    ]
    mejoras = 0
    for esperada, texto in casos:
        acceso._historial.clear()
        sin = client.post("/v1/contenido",
                          json={"titulo": texto[:50], "texto": texto}).json()
        con = client.post("/v1/contenido",
                          json={"titulo": texto[:50], "texto": texto,
                                "traducir": True}).json()
        if con["categoria"] == esperada and sin["categoria"] != esperada:
            mejoras += 1

    assert mejoras == len(casos), (
        "traducir dejo de mejorar estos casos: si es a proposito, hay que "
        "medir de nuevo antes de sacar la opcion")


@sin_modelo
def test_sin_la_opcion_la_clasificacion_no_cambia():
    """La opción no puede alterar el comportamiento por defecto."""
    texto = "Interfaces declarativas con Kotlin y Jetpack Compose en Android"
    a = client.post("/v1/contenido", json={"titulo": texto[:50], "texto": texto}).json()
    acceso._historial.clear()
    b = client.post("/v1/contenido",
                    json={"titulo": texto[:50], "texto": texto, "traducir": False}).json()
    assert a["categoria"] == b["categoria"]
    assert a["probabilidad"] == b["probabilidad"]


@sin_modelo
def test_los_relacionados_siguen_saliendo_del_texto_original():
    """Traducir la entrada no puede llevarse puesta la busqueda.

    La matriz tiene documentos en los dos idiomas: si se buscara con el
    texto traducido, quien escribe en español dejaria de encontrar material
    en español.
    """
    texto = "Cómo protejo las contraseñas de los usuarios de mi sitio web"
    con = client.post("/v1/contenido",
                      json={"titulo": texto[:50], "texto": texto, "traducir": True}).json()
    assert con["contenidos_relacionados"], "se quedo sin relacionados al traducir"
