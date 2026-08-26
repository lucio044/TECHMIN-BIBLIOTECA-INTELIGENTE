"""Pruebas de model_repository.RepositorioModelo."""

from pathlib import Path
from unittest.mock import patch

import joblib
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from techmind_nlp.exceptions import ModeloInvalidoError, ModeloNoDisponibleError
from techmind_nlp.model_repository import RepositorioModelo


def _crear_pipeline_entrenado() -> Pipeline:
    """Pipeline real pequeño, entrenado en memoria — evita depender del
    modelo de producción (varios MB) para las pruebas."""
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(min_df=1)),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    textos = ["docker kubernetes", "postgresql database", "react frontend"]
    categorias = ["DevOps / Cloud", "Bases de Datos", "Frontend"]
    pipeline.fit(textos, categorias)
    return pipeline


def test_obtener_pipeline_lanza_error_si_archivo_no_existe(tmp_path: Path):
    repositorio = RepositorioModelo(tmp_path / "no_existe.joblib")
    with pytest.raises(ModeloNoDisponibleError):
        repositorio.obtener_pipeline()


def test_obtener_pipeline_lanza_error_si_objeto_no_es_pipeline(tmp_path: Path):
    ruta = tmp_path / "no_es_pipeline.joblib"
    joblib.dump({"esto": "no es un pipeline"}, ruta)

    repositorio = RepositorioModelo(ruta)
    with pytest.raises(ModeloInvalidoError):
        repositorio.obtener_pipeline()


def test_obtener_pipeline_lanza_error_si_falta_paso_tfidf(tmp_path: Path):
    pipeline_sin_tfidf = Pipeline([("clf", LogisticRegression())])
    pipeline_sin_tfidf.fit([[1], [2]], ["A", "B"])  # entrenado, pero sin paso 'tfidf'

    ruta = tmp_path / "sin_tfidf.joblib"
    joblib.dump(pipeline_sin_tfidf, ruta)

    repositorio = RepositorioModelo(ruta)
    with pytest.raises(ModeloInvalidoError):
        repositorio.obtener_pipeline()


def test_obtener_pipeline_lanza_error_si_pipeline_no_esta_entrenado(tmp_path: Path):
    # Pipeline con la forma correcta pero sin fit() -> no tiene classes_.
    pipeline_sin_entrenar = Pipeline([
        ("tfidf", TfidfVectorizer()),
        ("clf", LogisticRegression()),
    ])

    ruta = tmp_path / "sin_entrenar.joblib"
    joblib.dump(pipeline_sin_entrenar, ruta)

    repositorio = RepositorioModelo(ruta)
    with pytest.raises(ModeloInvalidoError):
        repositorio.obtener_pipeline()


def test_obtener_pipeline_lanza_error_si_falta_predict_proba(tmp_path: Path):
    # LinearSVC no expone predict_proba. El clasificador lo necesita tanto
    # para el campo 'probabilidad' como para la categoría alternativa, así
    # que el modelo debe rechazarse al cargar, no al primer request.
    pipeline_sin_proba = Pipeline([
        ("tfidf", TfidfVectorizer(min_df=1)),
        ("clf", LinearSVC()),
    ])
    pipeline_sin_proba.fit(
        ["docker kubernetes", "postgresql database", "react frontend"],
        ["DevOps / Cloud", "Bases de Datos", "Frontend"],
    )

    ruta = tmp_path / "sin_predict_proba.joblib"
    joblib.dump(pipeline_sin_proba, ruta)

    repositorio = RepositorioModelo(ruta)
    with pytest.raises(ModeloInvalidoError):
        repositorio.obtener_pipeline()


def test_obtener_pipeline_lanza_error_si_archivo_esta_corrupto(tmp_path: Path):
    # Un .joblib truncado o corrupto hace explotar a joblib.load con un
    # error genérico; el repositorio debe traducirlo al error del dominio.
    ruta = tmp_path / "corrupto.joblib"
    ruta.write_bytes(b"esto no es un archivo joblib valido \x00\x01\x02")

    repositorio = RepositorioModelo(ruta)
    with pytest.raises(ModeloNoDisponibleError):
        repositorio.obtener_pipeline()


def test_obtener_pipeline_carga_correctamente(tmp_path: Path):
    ruta = tmp_path / "modelo_valido.joblib"
    joblib.dump(_crear_pipeline_entrenado(), ruta)

    repositorio = RepositorioModelo(ruta)
    pipeline = repositorio.obtener_pipeline()

    assert isinstance(pipeline, Pipeline)
    assert "tfidf" in pipeline.named_steps


def test_obtener_pipeline_solo_lee_disco_una_vez(tmp_path: Path):
    ruta = tmp_path / "modelo_valido.joblib"
    joblib.dump(_crear_pipeline_entrenado(), ruta)

    repositorio = RepositorioModelo(ruta)
    with patch("techmind_nlp.model_repository.joblib.load", wraps=joblib.load) as mock_load:
        repositorio.obtener_pipeline()
        repositorio.obtener_pipeline()
        repositorio.obtener_pipeline()

    assert mock_load.call_count == 1
