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


# --- como suena la respuesta ----------------------------------------------

def test_dice_que_no_sabe_en_lugar_de_clasificar_la_pregunta():
    """A quien pregunta algo que el corpus no cubre hay que decirselo.

    Antes contestaba en que categoria caia su pregunta, que no le sirve de
    nada y ademas suena a que el sistema no entendio.
    """
    j = client.post("/v1/chat", json={"texto": "¿Cuál es la capital de Mongolia?"}).json()
    r = j["respuesta"].lower()

    assert "no tengo información" in r or "no tengo informacion" in r
    assert "clasific" not in r.split("el histórico es")[0], (
        "a una pregunta sin respuesta no se le habla de clasificacion")


def test_a_un_contenido_si_le_explica_la_clasificacion():
    """Lo anterior no puede haberse llevado puesto el modo original."""
    j = client.post("/v1/chat", json={
        "texto": "Construccion de interfaces declarativas con Kotlin y Jetpack Compose, "
                 "manejo del estado y ciclo de vida de las actividades"}).json()
    assert j["categoria"] == "Mobile"
    assert j["terminos_decisivos"], "tiene que decir que terminos pesaron"


@sin_material
def test_la_respuesta_dice_de_donde_salio_y_que_no_la_redacto():
    """Sin esa aclaracion, el lector no sabe si leyo una cita o una opinion."""
    j = client.post("/v1/chat", json={"texto": "que es cross site scripting"}).json()
    r = j["respuesta"]
    assert j["del_historico"]["fuente"] in r
    assert "no lo redacté yo" in r.lower()


def test_distingue_una_pregunta_de_un_contenido():
    from app.services.explicacion import parece_pregunta

    for pregunta in ("¿Qué es una botnet?", "que es cross site scripting",
                     "explicame el modelo relacional", "define que es una API"):
        assert parece_pregunta(pregunta), f"«{pregunta}» es una pregunta"

    for contenido in ("quesadilla de queso y jamon",
                      "comodin para buscar archivos",
                      "optimizar consultas con indices en PostgreSQL"):
        assert not parece_pregunta(contenido), f"«{contenido}» no es una pregunta"


# --- mayusculas y documentos largos ---------------------------------------

@sin_material
def test_da_lo_mismo_escribir_en_mayusculas():
    """«BASE DE DATOS» devolvia cero resultados y «base de datos» siete.

    El modelo distingue mayusculas: la version gritada quedaba a 0,451 de
    su mejor documento y la normal a 0,705. Tampoco era solo el grito,
    «Kubernetes» daba 0,409 contra 0,678 de «kubernetes».

    Se normaliza dentro del codificador para que el indice y la consulta no
    puedan tratarse distinto.
    """
    buscador = semantico.cargar_buscador()
    for texto in ("base de datos", "kubernetes", "contraseñas"):
        puntajes = {
            buscador.buscar(v, top_n=1, umbral=-1)[0]["parecido"]
            for v in (texto, texto.upper(), texto.capitalize())
        }
        assert len(puntajes) == 1, f"«{texto}» puntua distinto segun como se escriba"


@sin_material
def test_un_documento_largo_no_gana_por_ser_largo():
    """El parecido solo premiaba la extension.

    Un PDF de 27 partes aporta mas fragmentos que un articulo de 5 y ganaba
    aunque tratara el tema de refilon: a «que sabes de base de datos» se le
    respondia con «DatosIBM», un documento de ciencia de datos.

    Se combina el parecido con la coincidencia de terminos en el titulo.
    """
    r = sintetizador.responder("que sabes de base de datos")
    assert r is not None
    assert "base de datos" in r["fuente"].lower(), (
        f"respondio con «{r['fuente']}» en vez de un documento del tema")


@sin_material
def test_a_un_contenido_no_se_le_busca_respuesta():
    """Buscarle una respuesta a un contenido devolvia disparates.

    Un parrafo sobre Jetpack Compose recuperaba «Fundamentos de Redes y
    TCP»: el texto es largo y se parece un poco a todo, asi que siempre
    encuentra algo. Es el mismo defecto que se le señala a otras
    implementaciones del contenido relacionado.

    Un contenido se clasifica; solo una pregunta se responde.
    """
    j = client.post("/v1/chat", json={
        "texto": "Construccion de interfaces declarativas con Kotlin y Jetpack "
                 "Compose, manejo del estado y ciclo de vida de las actividades"}).json()

    assert j["del_historico"] is None, (
        f"le busco respuesta a un contenido: «{(j['del_historico'] or {}).get('fuente')}»")
    assert j["categoria"] == "Mobile"


def test_no_muestra_evidencia_de_una_clasificacion_que_no_hizo():
    """Decia «no tengo informacion» y al lado ponia los terminos y el
    porcentaje de confianza. Esos datos explican una clasificacion, y
    cuando se responde que no se sabe, no hubo tal decision que explicar.
    """
    j = client.post("/v1/chat", json={"texto": "¿Cuál es la capital de Mongolia?"}).json()
    assert j["tipo"] == "sin_informacion"

    k = client.post("/v1/chat", json={
        "texto": "Construccion de interfaces declarativas con Kotlin y Jetpack Compose, "
                 "manejo del estado y ciclo de vida"}).json()
    assert k["tipo"] == "clasificacion"
    assert k["terminos_decisivos"], "una clasificacion si lleva sus terminos"
