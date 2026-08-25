"""
Pruebas de schemas.ResultadoClasificacion.

Este archivo cubre EL CONTRATO que consume el equipo de backend. La regla
"`categoria_alternativa` solo aparece cuando la confianza es baja" estaba
documentada en el README e implementada en `to_dict()`, pero sin ninguna
prueba: un cambio accidental dejaba la suite en verde y el error aparecía
recién cuando la API ya estaba integrada.
"""

import json

import pytest

from src.schemas import ResultadoClasificacion

CLAVES_BASE = {"categoria", "probabilidad", "informacion_adicional"}


def test_to_dict_incluye_las_tres_claves_del_contrato_base():
    resultado = ResultadoClasificacion(
        categoria="Backend",
        probabilidad=0.99,
        informacion_adicional=["apis rest", "java spring"],
    )
    assert set(resultado.to_dict()) == CLAVES_BASE


def test_to_dict_omite_categoria_alternativa_cuando_la_confianza_es_alta():
    # Confianza alta -> la clave NO debe existir (no basta con que sea None:
    # el contrato base no debe alterarse en el caso común).
    resultado = ResultadoClasificacion(
        categoria="Backend",
        probabilidad=0.99,
        informacion_adicional=["apis rest"],
        categoria_alternativa=None,
    )
    assert "categoria_alternativa" not in resultado.to_dict()


def test_to_dict_incluye_categoria_alternativa_cuando_esta_presente():
    resultado = ResultadoClasificacion(
        categoria="Backend",
        probabilidad=0.2,
        informacion_adicional=["consulta", "optimizar"],
        categoria_alternativa="Bases de Datos",
    )
    diccionario = resultado.to_dict()
    assert diccionario["categoria_alternativa"] == "Bases de Datos"
    assert set(diccionario) == CLAVES_BASE | {"categoria_alternativa"}


def test_to_dict_es_serializable_a_json():
    resultado = ResultadoClasificacion(
        categoria="Bases de Datos",
        probabilidad=0.87,
        informacion_adicional=["consulta sql", "índice"],
        categoria_alternativa="Backend",
    )
    # ensure_ascii=False porque la respuesta puede llevar acentos en español.
    texto_json = json.dumps(resultado.to_dict(), ensure_ascii=False)
    assert json.loads(texto_json) == resultado.to_dict()


def test_informacion_adicional_por_defecto_es_lista_vacia():
    resultado = ResultadoClasificacion(categoria="Mobile", probabilidad=0.5)
    assert resultado.to_dict()["informacion_adicional"] == []


def test_el_resultado_es_inmutable():
    # frozen=True: el resultado no debe poder mutarse después de creado,
    # para que nadie "parchee" la respuesta a mitad de camino.
    resultado = ResultadoClasificacion(categoria="Frontend", probabilidad=0.8)
    with pytest.raises(Exception):
        resultado.categoria = "Backend"  # type: ignore[misc]
