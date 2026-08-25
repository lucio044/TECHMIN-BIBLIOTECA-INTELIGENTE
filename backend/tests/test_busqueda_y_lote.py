"""Pruebas de GET /buscar y POST /lote."""

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CATEGORIAS = {
    "Backend", "Bases de Datos", "Ciencia de Datos", "DevOps / Cloud",
    "Frontend", "Mobile", "Programación General", "Seguridad",
}


# --- GET /buscar ---------------------------------------------------------

def test_buscar_encuentra_documentos_de_un_termino_tecnico():
    cuerpo = client.get("/buscar", params={"termino": "docker"}).json()
    assert cuerpo["termino"] == "docker"
    assert cuerpo["total"] > 0
    for r in cuerpo["resultados"]:
        assert r["categoria"] in CATEGORIAS
        assert r["relevancia"] > 0
        assert r["titulo"]


def test_buscar_ordena_de_mayor_a_menor_relevancia():
    resultados = client.get("/buscar", params={"termino": "kubernetes"}).json()["resultados"]
    valores = [r["relevancia"] for r in resultados]
    assert valores == sorted(valores, reverse=True)


def test_buscar_respeta_la_cantidad_pedida():
    cuerpo = client.get("/buscar", params={"termino": "python", "cantidad": 3}).json()
    assert cuerpo["total"] <= 3


def test_buscar_devuelve_vacio_si_el_termino_no_esta_en_el_corpus():
    # Palabra inventada: la respuesta correcta es ninguna coincidencia, no
    # un error ni el documento menos malo.
    cuerpo = client.get("/buscar", params={"termino": "zzqqxxvv"}).json()
    assert cuerpo["total"] == 0
    assert cuerpo["resultados"] == []


def test_buscar_rechaza_terminos_demasiado_cortos():
    assert client.get("/buscar", params={"termino": "a"}).status_code == 422


def test_buscar_rechaza_cantidad_fuera_de_rango():
    assert client.get("/buscar", params={"termino": "docker", "cantidad": 0}).status_code == 422
    assert client.get("/buscar", params={"termino": "docker", "cantidad": 999}).status_code == 422


# --- POST /lote ----------------------------------------------------------

def _csv(contenido: str):
    return {"archivo": ("prueba.csv", io.BytesIO(contenido.encode("utf-8")), "text/csv")}


CSV_VALIDO = """titulo,texto
Despliegue con Docker,Contenedores y Kubernetes en la nube con pipelines de CI/CD
Consultas SQL lentas,Optimizar indices y subqueries en PostgreSQL con planes
Componentes React,Estado hooks y estilos CSS en una interfaz web moderna
"""


def test_lote_clasifica_todas_las_filas():
    cuerpo = client.post("/lote", files=_csv(CSV_VALIDO)).json()
    assert cuerpo["total"] == 3
    assert cuerpo["clasificadas"] == 3
    assert cuerpo["con_error"] == 0
    for r in cuerpo["resultados"]:
        assert r["categoria"] in CATEGORIAS
        assert 0 < r["probabilidad"] <= 1


def test_lote_devuelve_el_resumen_por_categoria():
    cuerpo = client.post("/lote", files=_csv(CSV_VALIDO)).json()
    resumen = cuerpo["resumen_por_categoria"]
    assert sum(resumen.values()) == cuerpo["clasificadas"]
    assert set(resumen) <= CATEGORIAS


def test_lote_sigue_con_las_demas_cuando_una_fila_falla():
    # El caso que motiva el diseño: un archivo de mil filas con tres rotas
    # tiene que devolver las 997 buenas, no fallar entero.
    csv = CSV_VALIDO + ",fila sin titulo\nFila sin texto,\n"
    cuerpo = client.post("/lote", files=_csv(csv)).json()
    assert cuerpo["clasificadas"] == 3
    assert cuerpo["con_error"] == 2
    errores = [r["error"] for r in cuerpo["resultados"] if r["error"]]
    assert "falta el titulo" in errores
    assert "falta el texto" in errores


def test_lote_acepta_nombres_de_columna_alternativos():
    # Un CSV exportado de otra herramienta rara vez usa los nombres que uno
    # espera, asi que se aceptan varios.
    csv = "title,content\nDocker en produccion,Contenedores y Kubernetes en la nube\n"
    cuerpo = client.post("/lote", files=_csv(csv)).json()
    assert cuerpo["clasificadas"] == 1


def test_lote_rechaza_un_csv_sin_las_columnas_necesarias():
    respuesta = client.post("/lote", files=_csv("nombre,edad\nAna,30\n"))
    assert respuesta.status_code == 400
    assert "columna" in respuesta.json()["detail"].lower()


def test_lote_rechaza_archivos_que_no_son_csv():
    archivo = {"archivo": ("datos.txt", io.BytesIO(b"algo"), "text/plain")}
    assert client.post("/lote", files=archivo).status_code == 400
