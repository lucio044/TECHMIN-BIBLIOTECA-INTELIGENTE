"""Pruebas de keywords.ExtractorPalabrasClaveTfidf."""

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from techmind_nlp.keywords import ExtractorPalabrasClaveTfidf


@pytest.fixture
def vectorizador_de_prueba() -> TfidfVectorizer:
    """Vectorizador pequeño y determinista, entrenado en memoria — no
    depende del modelo real, así la prueba es rápida y aislada."""
    corpus = [
        "docker kubernetes container deployment",
        "postgresql database index query optimization",
        "react frontend component ui",
    ]
    vectorizador = TfidfVectorizer(min_df=1)
    vectorizador.fit(corpus)
    return vectorizador


def test_extraer_devuelve_terminos_del_vocabulario(vectorizador_de_prueba):
    extractor = ExtractorPalabrasClaveTfidf(vectorizador_de_prueba)
    resultado = extractor.extraer("docker container deployment", top_n=3)
    assert "docker" in resultado
    assert len(resultado) <= 3


def test_extraer_respeta_top_n(vectorizador_de_prueba):
    extractor = ExtractorPalabrasClaveTfidf(vectorizador_de_prueba)
    resultado = extractor.extraer("docker kubernetes container deployment", top_n=2)
    assert len(resultado) == 2


def test_extraer_texto_vacio_devuelve_lista_vacia(vectorizador_de_prueba):
    extractor = ExtractorPalabrasClaveTfidf(vectorizador_de_prueba)
    assert extractor.extraer("", top_n=5) == []


def test_extraer_texto_sin_vocabulario_conocido_devuelve_lista_vacia(vectorizador_de_prueba):
    extractor = ExtractorPalabrasClaveTfidf(vectorizador_de_prueba)
    # Ninguna de estas palabras existe en el corpus de entrenamiento del fixture.
    resultado = extractor.extraer("elefante jirafa mariposa", top_n=5)
    assert resultado == []


@pytest.fixture
def vectorizador_con_idf_variable() -> TfidfVectorizer:
    """Corpus donde 'docker' aparece en TODOS los documentos (IDF bajo, es
    poco distintivo) y 'kubernetes' en uno solo (IDF alto, muy distintivo).

    El fixture `vectorizador_de_prueba` no sirve para probar el orden: allí
    cada término aparece en un único documento, así que todos tienen el
    mismo peso y no hay orden real que verificar.
    """
    corpus = [
        "docker kubernetes deployment",
        "docker database query",
        "docker react component",
    ]
    vectorizador = TfidfVectorizer(min_df=1)
    vectorizador.fit(corpus)
    return vectorizador


def test_extraer_ordena_de_mayor_a_menor_peso(vectorizador_con_idf_variable):
    extractor = ExtractorPalabrasClaveTfidf(vectorizador_con_idf_variable)
    resultado = extractor.extraer("docker kubernetes", top_n=2)
    # El término más distintivo va primero: es lo que promete el docstring
    # y lo que hace útil la lista de palabras clave en la respuesta.
    assert resultado == ["kubernetes", "docker"]


def test_extraer_puede_devolver_bigramas(): 
    # El modelo v2 se entrenó con ngram_range=(1, 2), así que la respuesta
    # puede incluir bigramas ("apis rest"). Es comportamiento esperado y el
    # contrato documentado debe reflejarlo.
    # El corpus se arma para que el bigrama gane de verdad: "spring" y
    # "boot" aparecen sueltos en varios documentos (IDF bajo) mientras que
    # el par junto sale en uno solo (IDF alto). Si las partes pesaran mas
    # que el bigrama, el filtro de redundancia las tomaria primero y el
    # bigrama nunca entraria — que es el comportamiento correcto.
    corpus = [
        "spring boot para microservicios",
        "spring framework en java",
        "boot loader del sistema",
        "spring cloud config",
        "boot camp de programacion",
    ]
    vectorizador = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    vectorizador.fit(corpus)

    extractor = ExtractorPalabrasClaveTfidf(vectorizador)
    resultado = extractor.extraer("spring boot para microservicios", top_n=5)

    assert any(" " in termino for termino in resultado)


def test_filtrar_redundantes_descarta_terminos_ya_contenidos():
    # Salida real observada con el modelo entrenado con bigramas: "boot" y
    # "spring" no aportan ninguna palabra que no esté ya en los bigramas
    # anteriores, y ocupan lugares que podrían llevar información nueva.
    candidatos = ["apis rest", "java spring", "spring boot", "boot", "spring",
                  "conceptos", "rest api"]
    resultado = ExtractorPalabrasClaveTfidf._filtrar_redundantes(candidatos, 5)

    assert "boot" not in resultado
    assert "spring" not in resultado
    assert "conceptos" in resultado  # entra en el lugar que liberó el filtro


def test_filtrar_redundantes_conserva_el_orden_por_peso():
    candidatos = ["java spring", "spring", "docker", "kubernetes"]
    resultado = ExtractorPalabrasClaveTfidf._filtrar_redundantes(candidatos, 3)
    assert resultado == ["java spring", "docker", "kubernetes"]


def test_filtrar_redundantes_no_altera_una_lista_sin_solapamiento():
    candidatos = ["consulta", "lenta", "tarda", "optimizar", "ejecutarse"]
    resultado = ExtractorPalabrasClaveTfidf._filtrar_redundantes(candidatos, 5)
    assert resultado == candidatos


def test_extraer_no_devuelve_terminos_redundantes(): 
    corpus = ["java spring boot apis rest", "consultas sql", "react componentes"]
    vectorizador = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    vectorizador.fit(corpus)

    resultado = ExtractorPalabrasClaveTfidf(vectorizador).extraer(
        "java spring boot apis rest", top_n=5)

    # Ningún término debe estar completamente contenido en otro anterior.
    cubiertas = set()
    for termino in resultado:
        palabras = set(termino.split())
        assert palabras - cubiertas, f"{termino!r} no aporta nada nuevo"
        cubiertas |= palabras
