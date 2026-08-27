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
    # Dos formas que hay que contemplar, o el detector inventa huerfanos:
    #   from app.services import explicacion, sintetizador   -> varios nombres
    #   from app.services import correcciones as servicio    -> con alias
    for texto in modulos.values():
        for m in re.finditer(r"from app\.(\w+) import ([\w, ]+)", texto):
            for nombre in m.group(2).split(","):
                nombre = nombre.strip().split(" as ")[0].strip()
                if nombre:
                    importado.add(f"{m.group(1)}/{nombre}")

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


# --- una sola implementacion ---------------------------------------------

def test_el_procesamiento_de_texto_no_esta_duplicado():
    """El extractor de terminos vive en techmind-nlp, no aca.

    Estaba el mismo archivo en `nlp/` y en `backend/app/ml/keywords.py`.
    Se comprobo que daban resultados identicos, pero eso solo significa que
    todavia no habian divergido: el primer arreglo en uno de los dos habria
    dejado al otro atras sin que nada avisara.
    """
    assert not (APP / "ml" / "keywords.py").exists(), (
        "reaparecio una copia de keywords en el backend; "
        "el extractor se importa de techmind_nlp")

    clasificador = io.open(APP / "services" / "clasificador.py", encoding="utf-8").read()
    assert "from techmind_nlp.keywords import" in clasificador
    assert "from app.ml.keywords" not in clasificador


# --- lo que no entra en 2 GB ----------------------------------------------

def test_no_se_depende_de_torch_ni_de_optimum():
    """La instancia tiene 2 GB y torch son 800 MB instalados.

    Paso: `optimum[onnxruntime]` parecia la forma corta de correr el modelo
    de traduccion, y traia dos problemas. No instalaba --arrastra
    optimum-onnx, que pide optimum~=2.1.0 contra el 2.3.0 pedido, y pip
    corta con ResolutionImpossible-- y su `generate()` es torch por dentro,
    cosa que aca no se noto porque el entorno de desarrollo lo tenia
    instalado.

    El bucle de decodificacion se escribio a mano sobre onnxruntime. Sale
    24 veces mas rapido y no necesita ninguno de los dos.
    """
    req = io.open(APP.parents[0] / "requirements.txt", encoding="utf-8").read()
    activas = [l.strip() for l in req.splitlines()
               if l.strip() and not l.strip().startswith("#")]
    prohibidas = [l for l in activas
                  if re.match(r"^(torch|optimum)\b", l, re.IGNORECASE)]
    assert not prohibidas, (
        f"volvieron a requirements: {prohibidas}. No entran en 2 GB; "
        f"la traduccion decodifica a mano en app/ml/traductor.py")

    culpables = [n for n, t in _modulos().items()
                 if re.search(r"^\s*(import|from)\s+(torch|optimum)\b", t, re.M)]
    assert not culpables, f"importan torch u optimum: {culpables}"


def test_la_traduccion_no_pide_tensores_de_torch():
    """`return_tensors="pt"` obliga a torch aunque el modelo sea ONNX.

    Es la forma en que esto se colo la primera vez: el tokenizador devolvia
    tensores de PyTorch y nadie lo miro, porque en desarrollo estaba.

    Se mira el arbol y no el texto: el modulo explica en su docstring por
    que no se usa, y una busqueda cruda se tropieza con esa explicacion.
    """
    arbol = ast.parse(io.open(APP / "ml" / "traductor.py", encoding="utf-8").read())
    culpables = [
        n.lineno for n in ast.walk(arbol)
        if isinstance(n, ast.Call)
        for k in n.keywords
        if k.arg == "return_tensors"
    ]
    assert not culpables, (
        f'traductor.py volvio a pedir tensores en la linea {culpables}; '
        f'con "pt" necesita torch y con "np" revienta en generate(). '
        f'El bucle de aca usa listas de Python.')


# --- la pagina -------------------------------------------------------------

PAGINA = APP.parents[1] / "index.html"


def test_la_pagina_no_tiene_caracteres_de_control():
    """Un `\\b` escrito mal deja un retroceso literal, y no se ve.

    Paso de verdad: las dos expresiones que detectan el idioma tenian un
    0x08 en lugar del escape, asi que no matcheaban nada, `pareceIngles()`
    devolvia siempre falso y el boton «Ver en español» no llego a aparecer
    nunca. Un caracter invisible dentro de una expresion regular no rompe
    la sintaxis: la deja sin hacer nada.
    """
    texto = io.open(PAGINA, encoding="utf-8").read()
    culpables = {
        n: repr(linea.strip()[:60])
        for n, linea in enumerate(texto.splitlines(), 1)
        # tabulador y salto de linea son legitimos; el resto de los de
        # control no tienen nada que hacer en un archivo fuente.
        if any(c in linea for c in "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x1b")
    }
    assert not culpables, f"caracteres de control en index.html: {culpables}"


def test_la_pagina_detecta_el_idioma_con_limites_de_palabra():
    """Sin los `\\b`, las listas matchean dentro de las palabras.

    «autenticacion con tokens» daba ingles por el «to» de «tokens» y el
    «on» de «autenticacion»: sobre treinta consultas, 13 aciertos contra
    28 con los limites puestos.
    """
    texto = io.open(PAGINA, encoding="utf-8").read()
    for nombre in ("FUNC_ES", "FUNC_EN"):
        m = re.search(rf"const {nombre}\s*=\s*(/.*?/gi);", texto)
        assert m, f"no se encontro {nombre} en la pagina"
        assert m.group(1).startswith("/\\b") and m.group(1).endswith("\\b/gi"), (
            f"{nombre} perdio los limites de palabra: {m.group(1)[:40]}")
