"""
Pruebas de la limpieza de texto.

Estas pruebas custodian el CONTRATO con el entrenamiento del modelo v2:
cada aserción corresponde a una característica verificada en el
vocabulario guardado dentro del .joblib. Si alguna falla, el texto que
llega al vectorizador dejó de parecerse al que se usó para entrenarlo, y
la exactitud cae sin que aparezca ningún error en tiempo de ejecución.
"""

from src.cleaning import (
    corregir_ortografia,
    limpiar_texto,
    preparar_entrada_modelo,
)


# --- Lo que la limpieza SÍ debe eliminar -----------------------------------


def test_limpiar_texto_elimina_urls():
    resultado = limpiar_texto("Mira https://ejemplo.com/ruta para el detalle")
    assert "http" not in resultado
    assert "ejemplo" not in resultado
    assert "Mira" in resultado


def test_limpiar_texto_elimina_encabezado_published():
    resultado = limpiar_texto("Published on: 12 de marzo\nContenido real")
    assert "Published" not in resultado
    assert "Contenido real" in resultado


def test_limpiar_texto_elimina_signos_no_tecnicos():
    resultado = limpiar_texto("¿Qué es esto? ¡Increíble! (de verdad)")
    for simbolo in ("¿", "?", "¡", "!", "(", ")"):
        assert simbolo not in resultado


def test_limpiar_texto_normaliza_espacios_y_saltos():
    assert limpiar_texto("uno\n\ndos   tres\r") == "uno dos tres"


# --- Lo que la limpieza NO debe eliminar (contrato con el entrenamiento) ---


def test_conserva_caracteres_tecnicos():
    """El vocabulario del modelo distingue C++ de C y CI/CD de CI.

    Esta es la prueba que la versión anterior del módulo no pasaba: al
    eliminar todo carácter no alfanumérico, `c++` quedaba en `c` y
    `ci/cd` en `ci cd`.
    """
    resultado = limpiar_texto("Aprende C++, C# y CI/CD con front-end y node.js")
    for fragmento in ("C++", "C#", "CI/CD", "front-end", "node.js"):
        assert fragmento in resultado


def test_conserva_digitos():
    """El vocabulario del modelo tiene 987 términos con dígitos.

    `s3`, `ec2`, `ubuntu 24` son señal real de DevOps / Cloud. Eliminar
    los números la borra por completo.
    """
    resultado = limpiar_texto("Desplegar en AWS S3 y EC2 con Ubuntu 24")
    for fragmento in ("S3", "EC2", "24"):
        assert fragmento in resultado


def test_conserva_palabras_de_dos_letras():
    """El vocabulario del modelo tiene 497 términos de dos letras."""
    resultado = limpiar_texto("Uso js y go en mi stack")
    palabras = resultado.split()
    assert "js" in palabras
    assert "go" in palabras


def test_no_pasa_a_minusculas():
    """El paso a minúsculas lo hace el propio TfidfVectorizer.

    Hacerlo aquí impide recuperar la grafía original de las palabras
    clave que se devuelven al usuario ("Spring Boot" en vez de
    "spring boot").
    """
    resultado = limpiar_texto("Spring Boot con Java")
    assert "Spring Boot" in resultado


def test_conserva_stopwords():
    """El entrenamiento NO eliminó stopwords: el vocabulario tiene `the`.

    El IDF ya las neutraliza (IDF de `the` = 1.07). Quitarlas en
    inferencia desalinea el texto respecto al vocabulario aprendido.
    """
    resultado = limpiar_texto("This is the way to do it")
    for palabra in ("the", "is", "to"):
        assert palabra in resultado.split()


def test_conserva_acentos_enie_y_dieresis():
    resultado = limpiar_texto("Cómo optimizar el diseño de un pingüino en español")
    for palabra in ("Cómo", "diseño", "pingüino", "español"):
        assert palabra in resultado.split()


# --- Corrección ortográfica ------------------------------------------------


def test_corrige_letras_repetidas():
    assert corregir_ortografia("holaaaaa") == "holaa"


def test_corrige_puntuacion_repetida():
    assert corregir_ortografia("qué???") == "qué?"


def test_corrige_erratas_conocidas():
    assert corregir_ortografia("teh funtion is wierd") == "the function is weird"


# --- Entradas no válidas ---------------------------------------------------


def test_input_no_string_retorna_vacio():
    assert limpiar_texto(None) == ""
    assert limpiar_texto(123) == ""
    assert corregir_ortografia(None) == ""


def test_solo_simbolos_retorna_vacio():
    assert limpiar_texto("¡¡¡ ¿¿¿ ***") == ""


# --- Ensamblado de la entrada del modelo -----------------------------------


def test_preparar_entrada_une_titulo_y_texto():
    assert preparar_entrada_modelo("Docker", "contenedores") == "Docker contenedores"


def test_preparar_entrada_funciona_sin_titulo():
    assert preparar_entrada_modelo("", "solo texto") == "solo texto"


def test_preparar_entrada_limpia_cada_campo_por_separado():
    """Una URL al final del título no debe pegarse a la primera palabra
    del texto: por eso se limpia campo por campo y luego se une."""
    resultado = preparar_entrada_modelo("Ver https://foo.com", "Spring Boot")
    assert resultado == "Ver Spring Boot"


def test_preparar_entrada_sin_contenido_util_retorna_vacio():
    assert preparar_entrada_modelo("", "¡¡¡ ???") == ""
