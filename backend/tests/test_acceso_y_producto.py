"""Pruebas de lo que convierte la API en un producto.

Versionado, control de acceso, reporte de errores y modelos propios.
"""

import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.core import acceso
from app.main import app

client = TestClient(app)

TECNICO = {
    "titulo": "Despliegue con Docker",
    "texto": "Contenedores, Kubernetes y pipelines de CI/CD en AWS con Terraform",
}


@pytest.fixture(autouse=True)
def limite_limpio():
    """Cada prueba arranca con el contador en cero.

    Sin esto, una prueba que gasta el cupo hace fallar a las siguientes por
    un 429 que no tiene nada que ver con lo que se esta probando.
    """
    acceso._historial.clear()
    yield
    acceso._historial.clear()


# --- versionado -----------------------------------------------------------

def test_las_rutas_viven_bajo_v1():
    assert client.post("/v1/contenido", json=TECNICO).status_code == 200


def test_la_ruta_sin_prefijo_sigue_funcionando():
    # Hay clientes apuntando ahi. Quitarla de golpe los deja sin servicio.
    assert client.post("/contenido", json=TECNICO).status_code == 200


def test_la_ruta_sin_prefijo_avisa_que_esta_obsoleta():
    r = client.post("/contenido", json=TECNICO)
    assert r.headers.get("deprecation") == "true"
    assert "/v1/contenido" in r.headers.get("link", "")


def test_solo_las_rutas_v1_estan_en_la_documentacion():
    paths = client.get("/openapi.json").json()["paths"]
    assert all(p.startswith("/v1") for p in paths)


# --- cabeceras de servicio ------------------------------------------------

def test_cada_respuesta_trae_identificador_y_version_del_modelo():
    r = client.post("/v1/contenido", json=TECNICO)
    assert len(r.headers["x-request-id"]) == 16
    assert r.headers["x-modelo-version"]
    assert r.headers["x-api-version"]


def test_dos_peticiones_traen_identificadores_distintos():
    a = client.post("/v1/contenido", json=TECNICO).headers["x-request-id"]
    b = client.post("/v1/contenido", json=TECNICO).headers["x-request-id"]
    assert a != b


def test_las_cabeceras_de_limite_van_bajando():
    primera = client.post("/v1/contenido", json=TECNICO)
    segunda = client.post("/v1/contenido", json=TECNICO)
    assert int(primera.headers["x-ratelimit-remaining"]) > int(
        segunda.headers["x-ratelimit-remaining"]
    )


# --- control de acceso ----------------------------------------------------

def test_se_puede_usar_sin_credenciales():
    # La demo publica tiene que funcionar sin que nadie pida una clave.
    r = client.post("/v1/contenido", json=TECNICO)
    assert r.status_code == 200
    assert int(r.headers["x-ratelimit-limit"]) == acceso.LIMITE_ANONIMO


def test_una_clave_inventada_se_rechaza():
    # Se rechaza en vez de tratarse como anonima: quien la manda cree tener
    # acceso, y dejarlo pasar le daria un error confuso mas adelante.
    r = client.post("/v1/contenido", json=TECNICO, headers={"X-API-Key": "inventada"})
    assert r.status_code == 401


def test_una_clave_valida_da_un_limite_mas_alto(monkeypatch):
    monkeypatch.setenv("TECHMIND_API_KEYS", "clave-de-prueba")
    r = client.post("/v1/contenido", json=TECNICO, headers={"X-API-Key": "clave-de-prueba"})
    assert r.status_code == 200
    assert int(r.headers["x-ratelimit-limit"]) == acceso.LIMITE_CON_CLAVE


def test_el_limite_corta_y_dice_cuando_reintentar():
    cliente = acceso.Cliente("prueba", autenticado=False)
    for _ in range(acceso.LIMITE_ANONIMO):
        acceso._consumir(cliente)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        acceso._consumir(cliente)

    assert e.value.status_code == 429
    assert "Retry-After" in e.value.headers


def test_health_no_consume_cupo():
    # Un monitor que pregunta cada minuto no puede gastarle el limite a
    # quien de verdad usa el servicio.
    antes = client.post("/v1/contenido", json=TECNICO).headers["x-ratelimit-remaining"]
    for _ in range(5):
        client.get("/v1/health")
    despues = client.post("/v1/contenido", json=TECNICO).headers["x-ratelimit-remaining"]
    assert int(antes) - int(despues) == 1


# --- correcciones ---------------------------------------------------------

CORRECCION = {
    "titulo": "Optimizar consultas",
    "texto": "Como mejorar el rendimiento de una base con indices y planes de ejecucion",
    "categoria_predicha": "Backend",
    "categoria_correcta": "Bases de Datos",
}


def test_se_puede_reportar_que_el_modelo_se_equivoco():
    r = client.post("/v1/correcciones", json=CORRECCION)
    assert r.status_code == 201
    assert r.json()["registrada"]


def test_se_rechaza_una_correccion_que_no_corrige_nada():
    igual = {**CORRECCION, "categoria_correcta": "Backend"}
    assert client.post("/v1/correcciones", json=igual).status_code == 422


def test_el_resumen_agrupa_las_confusiones_repetidas():
    for _ in range(3):
        client.post("/v1/correcciones", json=CORRECCION)
    resumen = client.get("/v1/correcciones/resumen").json()
    assert resumen["total"] >= 3
    assert "Backend -> Bases de Datos" in resumen["confusiones"]


# --- modelos propios ------------------------------------------------------

def _csv_juridico(por_categoria=20):
    filas = []
    # Cada categoria necesita vocabulario propio para que el modelo tenga de
    # donde agarrarse; con textos identicos salvo un numero no aprenderia nada.
    plantillas = {
        "Laboral": "despido {n} del trabajador indemnizacion contrato jornada vacaciones",
        "Tributario": "impuesto renta {n} tercera categoria fiscalizacion credito fiscal igv",
        "Societario": "junta {n} accionistas quorum acuerdos capital social directorio fusion",
    }
    for cat, p in plantillas.items():
        for i in range(por_categoria):
            filas.append({"texto": p.format(n=i), "categoria": cat})
    buf = io.StringIO()
    w = csv.DictWriter(buf, ["texto", "categoria"])
    w.writeheader()
    w.writerows(filas)
    return {"archivo": ("juridico.csv", io.BytesIO(buf.getvalue().encode()), "text/csv")}


def test_se_entrena_un_modelo_con_categorias_propias():
    r = client.post("/v1/modelos", files=_csv_juridico(), data={"nombre": "Estudio"})
    assert r.status_code == 201
    d = r.json()
    assert set(d["categorias"]) == {"Laboral", "Tributario", "Societario"}
    assert 0 <= d["f1_macro"] <= 1
    client.delete(f"/v1/modelos/{d['id']}")


def test_el_modelo_propio_clasifica_con_sus_etiquetas():
    # El de fabrica no conoce estas categorias: solo el propio puede.
    creado = client.post("/v1/modelos", files=_csv_juridico(), data={"nombre": "Estudio"}).json()
    r = client.post(
        f"/v1/modelos/{creado['id']}/clasificar",
        json={"texto": "despido arbitrario del trabajador y calculo de la indemnizacion"},
    )
    assert r.status_code == 200
    assert r.json()["categoria"] in {"Laboral", "Tributario", "Societario"}
    client.delete(f"/v1/modelos/{creado['id']}")


def test_se_rechaza_un_csv_con_una_sola_categoria():
    buf = io.StringIO()
    w = csv.DictWriter(buf, ["texto", "categoria"])
    w.writeheader()
    w.writerows([{"texto": f"texto de ejemplo numero {i}", "categoria": "Unica"} for i in range(50)])
    archivo = {"archivo": ("uno.csv", io.BytesIO(buf.getvalue().encode()), "text/csv")}
    r = client.post("/v1/modelos", files=archivo)
    assert r.status_code == 400
    assert "sola categoria" in r.json()["detail"]


def test_se_rechaza_un_csv_con_muy_pocas_filas():
    r = client.post("/v1/modelos", files=_csv_juridico(por_categoria=2))
    assert r.status_code == 400


def test_clasificar_con_un_modelo_que_no_existe_da_404():
    r = client.post(
        "/v1/modelos/noexiste/clasificar",
        json={"texto": "un texto cualquiera con largo suficiente para pasar"},
    )
    assert r.status_code == 404
