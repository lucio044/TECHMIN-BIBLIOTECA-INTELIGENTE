"""Pruebas de la busqueda semantica.

Lo que se comprueba no es que devuelva un documento concreto --el corpus
puede cambiar-- sino las tres propiedades que la distinguen de la busqueda
por palabras: que cruce idiomas, que encuentre sin terminos compartidos, y
que no invente cuando la consulta es ajena al corpus.

Si el modelo o los vectores no estan en el despliegue, las pruebas se
saltan en vez de fallar: la funcion es opcional a proposito.
"""

import pytest
from fastapi.testclient import TestClient

from app.core import acceso
from app.main import app
from app.ml import semantico

client = TestClient(app)

hay = semantico.cargar_buscador() is not None
sin_semantica = pytest.mark.skipif(not hay, reason="faltan el modelo o los vectores")


@pytest.fixture(autouse=True)
def limite_limpio():
    acceso._historial.clear()
    yield
    acceso._historial.clear()


def _buscar(consulta, cantidad=5):
    r = client.get("/v1/semantica", params={"consulta": consulta, "cantidad": cantidad})
    assert r.status_code == 200, r.text
    return r.json()


# --- cuando no esta disponible ---------------------------------------------

def test_avisa_con_503_si_no_esta_disponible():
    """Sin el modelo, la ruta explica que falta en lugar de romper."""
    if hay:
        pytest.skip("esta disponible en este entorno")
    r = client.get("/v1/semantica", params={"consulta": "cualquier cosa"})
    assert r.status_code == 503
    assert "generar_embeddings" in r.json()["detail"]


# --- lo que la distingue de la busqueda por palabras -----------------------

@sin_semantica
def test_cruza_idiomas():
    """Una consulta en español recupera documentos en ingles.

    Es el caso que justifica la funcion: el corpus esta en ingles al 95,9%
    y la interfaz en español.
    """
    d = _buscar("como protejo las contraseñas de mis usuarios")
    assert d["resultados"], "una consulta razonable no puede quedar vacia"
    assert d["resultados"][0]["parecido"] > 0.3


@sin_semantica
def test_encuentra_sin_compartir_palabras():
    """Al menos un resultado no comparte terminos con la consulta."""
    consulta = "mi aplicacion se cierra sola al girar el telefono"
    palabras = {p for p in consulta.lower().split() if len(p) > 4}

    d = _buscar(consulta)
    assert d["resultados"]

    sin_solape = [
        r for r in d["resultados"]
        if not (palabras & set((r["titulo"] + " " + r["extracto"]).lower().split()))
    ]
    assert sin_solape, "si todos comparten palabras, no aporta sobre /buscar"


@sin_semantica
def test_una_consulta_ajena_puntua_mas_bajo_que_una_tecnica():
    """Lo ajeno al corpus tiene que quedar por debajo de lo tecnico.

    No se exige que devuelva cero. Se midio: las consultas tecnicas dan
    entre 0,498 y 0,721, y las ajenas entre 0,346 y 0,579. Las dos bandas
    se solapan, porque el modelo comprime los cosenos en un rango estrecho.
    Pedir que una receta de cocina devuelva lista vacia seria exigirle al
    sistema algo que esta tecnica no da, y la prueba estaria mal, no el
    codigo.

    Lo que si se sostiene es el orden entre las dos.
    """
    ajena = client.get("/v1/semantica", params={
        "consulta": "receta de sopa de tomate con albahaca y crema de leche"}).json()
    tecnica = _buscar("como protejo las contraseñas de mis usuarios")

    mejor_ajena = ajena["resultados"][0]["parecido"] if ajena["resultados"] else 0.0
    mejor_tecnica = tecnica["resultados"][0]["parecido"]

    assert mejor_tecnica > mejor_ajena, (
        f"lo tecnico ({mejor_tecnica}) no supero a lo ajeno ({mejor_ajena})")


@sin_semantica
def test_el_umbral_deja_pasar_las_consultas_legitimas():
    """Ninguna consulta tecnica razonable puede quedar sin resultados."""
    for consulta in ("como despliego contenedores en la nube",
                     "consultas lentas en una tabla con millones de filas",
                     "autenticacion con tokens en una api rest"):
        d = _buscar(consulta)
        assert d["resultados"], f"«{consulta}» quedo sin resultados"


@sin_semantica
def test_los_resultados_vienen_ordenados():
    d = _buscar("desplegar contenedores en la nube", cantidad=8)
    parecidos = [r["parecido"] for r in d["resultados"]]
    assert parecidos == sorted(parecidos, reverse=True)


@sin_semantica
def test_respeta_la_cantidad_pedida():
    assert len(_buscar("bases de datos relacionales", cantidad=3)["resultados"]) <= 3


@sin_semantica
def test_informa_contra_cuantos_comparo():
    d = _buscar("aprendizaje automatico con python")
    assert d["documentos_comparados"] > 30000


# --- validacion de entrada -------------------------------------------------

@sin_semantica
def test_rechaza_una_consulta_demasiado_corta():
    assert client.get("/v1/semantica", params={"consulta": "ab"}).status_code == 422


@sin_semantica
def test_es_distinta_de_la_busqueda_por_palabras():
    """Las dos rutas existen y responden distinto a la misma consulta."""
    consulta = "como evito que se caiga el servidor con mucha gente"
    sem = _buscar(consulta)

    lex = client.get("/v1/buscar", params={"termino": "servidor", "cantidad": 5})
    assert lex.status_code == 200

    titulos_sem = {r["titulo"] for r in sem["resultados"]}
    titulos_lex = {r["titulo"] for r in lex.json()["resultados"]}
    assert titulos_sem != titulos_lex or not titulos_lex
