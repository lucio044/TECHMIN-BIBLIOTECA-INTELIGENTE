"""Pruebas de que cada modelo propio tiene dueño.

Antes no lo tenía: la identidad del cliente se calculaba para el límite de
peticiones y se descartaba. Cualquiera podía listar los modelos de los
demás, usarlos y borrarlos.

Cada prueba de acá corresponde a una de esas tres cosas.
"""

import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.core import acceso
from app.main import app

client = TestClient(app)

CLAVE_A = "clave-de-prueba-A"
CLAVE_B = "clave-de-prueba-B"


@pytest.fixture(autouse=True)
def dos_clientes(monkeypatch):
    """Dos claves válidas, para poder ser dos personas distintas."""
    monkeypatch.setenv("TECHMIND_API_KEYS", f"{CLAVE_A},{CLAVE_B}")
    acceso._historial.clear()
    yield
    acceso._historial.clear()


def _csv_valido() -> bytes:
    filas = io.StringIO()
    escritor = csv.writer(filas)
    escritor.writerow(["texto", "categoria"])
    for i in range(25):
        escritor.writerow([f"documento sobre bases de datos indices y consultas numero {i}", "Datos"])
    for i in range(25):
        escritor.writerow([f"documento sobre interfaces web componentes y estilos numero {i}", "Web"])
    return filas.getvalue().encode()


def _entrenar(clave: str, nombre: str = "modelo de prueba"):
    r = client.post(
        "/v1/modelos",
        files={"archivo": ("datos.csv", _csv_valido(), "text/csv")},
        data={"nombre": nombre},
        headers={"X-API-Key": clave},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _borrar(clave: str, modelo_id: str):
    return client.delete(f"/v1/modelos/{modelo_id}", headers={"X-API-Key": clave})


# --- los tres aislamientos ------------------------------------------------

def test_no_se_listan_los_modelos_de_otro():
    """Los nombres y las taxonomías dicen a qué se dedica cada cliente."""
    mio = _entrenar(CLAVE_A, "taxonomía de A")
    try:
        ajenos = client.get("/v1/modelos", headers={"X-API-Key": CLAVE_B}).json()
        assert mio["id"] not in [m["id"] for m in ajenos]

        propios = client.get("/v1/modelos", headers={"X-API-Key": CLAVE_A}).json()
        assert mio["id"] in [m["id"] for m in propios]
    finally:
        _borrar(CLAVE_A, mio["id"])


def test_no_se_clasifica_con_el_modelo_de_otro():
    mio = _entrenar(CLAVE_A)
    try:
        cuerpo = {"texto": "consultas con indices sobre una tabla muy grande"}

        ajeno = client.post(f"/v1/modelos/{mio['id']}/clasificar", json=cuerpo,
                            headers={"X-API-Key": CLAVE_B})
        assert ajeno.status_code == 404, "un modelo ajeno tiene que ser inexistente"

        propio = client.post(f"/v1/modelos/{mio['id']}/clasificar", json=cuerpo,
                             headers={"X-API-Key": CLAVE_A})
        assert propio.status_code == 200
    finally:
        _borrar(CLAVE_A, mio["id"])


def test_no_se_borra_el_modelo_de_otro():
    mio = _entrenar(CLAVE_A)
    try:
        assert _borrar(CLAVE_B, mio["id"]).status_code == 404

        # y sigue estando
        sigue = client.get("/v1/modelos", headers={"X-API-Key": CLAVE_A}).json()
        assert mio["id"] in [m["id"] for m in sigue]
    finally:
        _borrar(CLAVE_A, mio["id"])


def test_el_dueno_si_puede_borrar_el_suyo():
    mio = _entrenar(CLAVE_A)
    assert _borrar(CLAVE_A, mio["id"]).status_code == 204
    despues = client.get("/v1/modelos", headers={"X-API-Key": CLAVE_A}).json()
    assert mio["id"] not in [m["id"] for m in despues]


# --- lo que llega del CSV no puede volver como marcado -------------------

def test_las_etiquetas_html_no_sobreviven_al_entrenamiento():
    """El nombre y las categorías salen del CSV de quien sube y se pintan
    después en una página. La API no tiene por qué devolver algo que sólo
    sirve para inyectar."""
    filas = io.StringIO()
    escritor = csv.writer(filas)
    escritor.writerow(["texto", "categoria"])
    for i in range(25):
        escritor.writerow([f"documento sobre bases de datos numero {i}", "<img src=x onerror=alert(1)>"])
    for i in range(25):
        escritor.writerow([f"documento sobre interfaces web numero {i}", "Normal"])

    r = client.post(
        "/v1/modelos",
        files={"archivo": ("x.csv", filas.getvalue().encode(), "text/csv")},
        data={"nombre": "<b>nombre con etiquetas</b>"},
        headers={"X-API-Key": CLAVE_A},
    )
    assert r.status_code == 201, r.text
    j = r.json()
    try:
        for prohibido in "<>\"'`":
            assert prohibido not in j["nombre"], f"el nombre devolvio «{prohibido}»"
            for c in j["categorias"]:
                assert prohibido not in c, f"la categoria «{c}» devolvio «{prohibido}»"
    finally:
        _borrar(CLAVE_A, j["id"])
