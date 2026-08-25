"""Pruebas del módulo de tokenización y filtrado de stopwords."""

from src.tokenization import eliminar_stopwords, tokenizar, tokenizar_y_filtrar


def test_tokenizar_pasa_a_minusculas():
    assert tokenizar("Hola MUNDO") == ["hola", "mundo"]


def test_tokenizar_conserva_signos_tecnicos_y_digitos():
    # Cubre los cuatro casos que el patrón por defecto de scikit-learn
    # rompería: signos (+), barra (/), punto (.) y dígitos.
    texto = "Desarrollo con C++, CI/CD, Node.js, S3 y React"

    resultado = tokenizar(texto)

    assert "c++" in resultado
    assert "ci/cd" in resultado
    assert "node.js" in resultado
    assert "s3" in resultado
    assert "react" in resultado


def test_tokenizar_modo_sklearn_replica_el_vectorizador():
    # Sin conservar técnicos, el patrón de scikit-learn parte "ci/cd".
    tokens = tokenizar("Uso CI/CD", conservar_tecnicos=False)
    assert "ci" in tokens and "cd" in tokens
    assert "ci/cd" not in tokens


def test_tokenizar_entrada_no_string_devuelve_lista_vacia():
    assert tokenizar(None) == []
    assert tokenizar(123) == []


def test_eliminar_stopwords_filtra_espanol_e_ingles():
    resultado = eliminar_stopwords(["the", "django", "orm", "es", "lento"])
    assert "django" in resultado and "lento" in resultado
    assert "the" not in resultado and "es" not in resultado


def test_eliminar_stopwords_filtra_interrogativos_y_verbos_de_tutorial():
    # Custodia el hueco visto en la demo: "Cómo" llegó a salir como
    # palabra clave en la respuesta JSON. Los interrogativos y los verbos
    # del registro de tutorial no aportan significado técnico.
    tokens = tokenizar("Cómo desarrollar una API con Python")

    resultado = eliminar_stopwords(tokens)

    assert "api" in resultado
    assert "python" in resultado
    assert "cómo" not in resultado
    assert "desarrollar" not in resultado
    assert "una" not in resultado
    assert "con" not in resultado


def test_eliminar_stopwords_conserva_tecnicos_cortos():
    resultado = eliminar_stopwords(["js", "go", "el"])
    assert "js" in resultado and "go" in resultado
    assert "el" not in resultado


def test_eliminar_stopwords_conserva_repeticiones():
    resultado = eliminar_stopwords(["docker", "docker", "kubernetes"])
    assert resultado.count("docker") == 2


def test_eliminar_stopwords_acepta_descartes_extra():
    resultado = eliminar_stopwords(["django", "flask"], extra={"flask"})
    assert resultado == ["django"]


def test_tokenizar_y_filtrar_encadena_ambos_pasos():
    resultado = tokenizar_y_filtrar("The Django ORM es muy lento")
    assert "django" in resultado
    assert "the" not in resultado
