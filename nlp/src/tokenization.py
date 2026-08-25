"""
Tokenización y eliminación de stopwords.

ALCANCE — leer antes de usar
----------------------------
Estas funciones NO se aplican antes del clasificador. El modelo se entrenó
sobre texto que conserva stopwords (su vocabulario contiene `the`, `of`,
`que`, `para`), así que filtrarlas en inferencia desalinearía el texto
respecto al vocabulario aprendido y bajaría la exactitud sin lanzar ningún
error. Ver el contrato en `src/cleaning.py`.

Su lugar es el análisis: inspeccionar qué términos entran o no al modelo,
depurar por qué una palabra clave aparece, y alimentar cualquier extracción
que no dependa del vectorizador.

Sobre lematización: no se implementa a propósito. El corpus es bilingüe y
`WordNetLemmatizer` de NLTK solo tiene lexicón en inglés, así que degradaría
la mitad del contenido. Además, para TF-IDF + Regresión Logística el propio
IDF ya neutraliza los términos vacíos (el IDF de `the` en este modelo es
1.07 frente a 5.35 de `kubernetes`), que es la función que la lematización y
el filtrado de stopwords cumplirían.
"""

import re
from typing import List, Optional, Set

from src.keywords import es_termino_util

#: Mismo patrón que usa TfidfVectorizer por defecto: `(?u)\b\w\w+\b`.
PATRON_TOKEN_SKLEARN = re.compile(r"(?u)\b\w\w+\b")

#: Patrón extendido: mantiene unidos los términos técnicos con símbolos
#: (`c++`, `ci/cd`, `node.js`), que el patrón de sklearn parte en pedazos.
PATRON_TOKEN_TECNICO = re.compile(r"(?u)[a-záéíóúüñ0-9][a-záéíóúüñ0-9\+\#\.\_\-\/]*")


def tokenizar(texto: str, conservar_tecnicos: bool = True) -> List[str]:
    """Divide un texto en tokens en minúsculas.

    Args:
        texto: Texto de entrada, idealmente ya pasado por `limpiar_texto`.
        conservar_tecnicos: Si es True usa el patrón extendido que mantiene
            `c++` y `ci/cd` como un solo token. Si es False replica
            exactamente la tokenización interna de scikit-learn, útil para
            depurar por qué un término entró o no al vocabulario del modelo.

    Returns:
        Lista de tokens en minúsculas, en el orden original del texto.

    Ejemplo:
        >>> tokenizar("Aprende C++ y CI/CD en Docker")
        ['aprende', 'c++', 'ci/cd', 'en', 'docker']
        >>> tokenizar("Aprende CI/CD", conservar_tecnicos=False)
        ['aprende', 'ci', 'cd']
    """
    if not isinstance(texto, str):
        return []

    patron = PATRON_TOKEN_TECNICO if conservar_tecnicos else PATRON_TOKEN_SKLEARN
    tokens = patron.findall(texto.lower())
    # El patrón técnico puede dejar puntos o guiones colgando al final
    # ("django." -> "django"); se recortan sin tocar el interior del token.
    return [t.strip("._-/") for t in tokens if t.strip("._-/")]


def eliminar_stopwords(tokens: List[str], extra: Optional[Set[str]] = None) -> List[str]:
    """Filtra stopwords, ruido de foros y tokens sin significado.

    Reutiliza `es_termino_util` de `keywords.py` para que el criterio sea
    uno solo en todo el proyecto: si un término no merece mostrarse como
    palabra clave, tampoco debería contarse en un análisis de frecuencias.

    Args:
        tokens: Tokens producidos por `tokenizar`.
        extra: Conjunto adicional de términos a descartar.

    Returns:
        Lista filtrada, conservando el orden y las repeticiones (la
        frecuencia se necesita después para cualquier conteo).

    Ejemplo:
        >>> eliminar_stopwords(['the', 'django', 'orm', 'es', 'lento'])
        ['django', 'orm', 'lento']
    """
    descartes = extra or set()
    return [t for t in tokens if t not in descartes and es_termino_util(t)]


def tokenizar_y_filtrar(texto: str) -> List[str]:
    """Atajo de uso frecuente: tokeniza y elimina stopwords en un paso."""
    return eliminar_stopwords(tokenizar(texto))
