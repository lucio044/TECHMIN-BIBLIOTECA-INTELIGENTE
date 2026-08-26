"""Pruebas de la forma del proyecto, no de su comportamiento.

Verifican invariantes que se rompen sin que nadie se entere: una ruta nueva
sin control de acceso, un modulo que quedo sin usar, una libreria que
manipula la ruta de importacion.

Son las que evitan que la estructura se degrade de a poco.
"""

import ast
import io
import pathlib
import re

import pytest

APP = pathlib.Path(__file__).resolve().parents[1] / "app"

# /health se deja abierta a proposito: la consultan la supervision y el
# propio systemd. Limitarla es la forma de fabricarse una caida falsa.
SIN_CONTROL_A_PROPOSITO = {"health"}


def _routers():
    return [f for f in sorted((APP / "routers").glob("*.py")) if f.stem != "__init__"]


def _modulos():
    return {
        str(f.relative_to(APP)).replace("\\", "/")[:-3]: io.open(f, encoding="utf-8").read()
        for f in APP.rglob("*.py")
        if not f.name.startswith("__")
    }


# --- control de acceso ----------------------------------------------------

@pytest.mark.parametrize("archivo", _routers(), ids=lambda f: f.stem)
def test_toda_ruta_pide_credenciales(archivo):
    """Una ruta sin `identificar` queda fuera del limite por cliente.

    El producto ofrece 30 peticiones por minuto sin clave y 600 con clave.
    Una ruta que se olvide de la dependencia no cuenta para ese limite y
    puede consumirse sin tope, sin que nada lo indique.
    """
    texto = io.open(archivo, encoding="utf-8").read()
    rutas = len(re.findall(r"@router\.(?:get|post|delete|put)\(", texto))
    if not rutas:
        return

    if archivo.stem in SIN_CONTROL_A_PROPOSITO:
        assert "identificar" not in texto, (
            f"{archivo.stem} figura como excepcion pero ahora pide credenciales: "
            "si el cambio es a proposito, sacarlo de SIN_CONTROL_A_PROPOSITO")
        return

    protegidas = texto.count("Depends(identificar)")
    assert protegidas >= rutas, (
        f"{archivo.stem}: {rutas - protegidas} de {rutas} rutas sin control de acceso")


# --- higiene del paquete --------------------------------------------------

def test_ninguna_libreria_toca_la_ruta_de_importacion():
    """`sys.path` es cosa de un script, no de un modulo importable.

    Un modulo que lo modifica funciona hasta que alguien lo importa desde
    otro sitio, y ahi falla por un motivo que no tiene nada que ver.
    """
    culpables = [n for n, t in _modulos().items() if "sys.path" in t]
    assert not culpables, f"modulos que tocan sys.path: {culpables}"


def test_no_quedan_modulos_sin_usar():
    """Codigo que nadie importa es codigo que nadie mantiene.

    Habia tres modulos de una autenticacion abandonada que ademas
    importaban librerias ausentes de requirements.txt: no fallaban solo
    porque nadie los llamaba.
    """
    modulos = _modulos()
    importado = set()
    for texto in modulos.values():
        for m in re.finditer(r"from app\.([\w.]+) import|import app\.([\w.]+)", texto):
            importado.add((m.group(1) or m.group(2)).replace(".", "/"))

    # Los routers los importa main.py en una sola linea con parentesis, y
    # los servicios a veces se importan como paquete; se resuelven aparte.
    texto_main = modulos["main"]
    for m in re.finditer(r"from app\.routers import \(([^)]+)\)", texto_main):
        for nombre in m.group(1).replace("\n", " ").split(","):
            importado.add("routers/" + nombre.strip())
    for texto in modulos.values():
        for m in re.finditer(r"from app\.(\w+) import (\w+)", texto):
            importado.add(f"{m.group(1)}/{m.group(2)}")

    huerfanos = [n for n in modulos if n != "main" and n not in importado]
    assert not huerfanos, f"modulos que nadie importa: {huerfanos}"


def test_todo_el_paquete_compila():
    for nombre, texto in _modulos().items():
        try:
            ast.parse(texto)
        except SyntaxError as e:
            pytest.fail(f"{nombre}: {e}")


def test_no_se_usa_on_event():
    """`on_event` esta deprecado en FastAPI; el reemplazo es `lifespan`."""
    culpables = [n for n, t in _modulos().items() if "on_event" in t]
    assert not culpables, f"usan on_event: {culpables}"
