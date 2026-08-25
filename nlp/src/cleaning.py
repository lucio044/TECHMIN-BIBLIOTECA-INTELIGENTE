"""
Limpieza de texto — réplica exacta del preprocesamiento del modelo v2
entregado por el equipo de modelado.

Este módulo tiene una única responsabilidad: convertir texto crudo en
texto limpio. No sabe nada del modelo, de palabras clave, ni de cómo se
usa el resultado — eso lo mantiene fácil de probar de forma aislada.

IMPORTANTE — CONTRATO CON EL ENTRENAMIENTO
------------------------------------------
El `TfidfVectorizer` del modelo se ajustó sobre texto que pasó por
`limpiar_texto()` y `corregir_ortografia()` del notebook
`limpieza_y_eda_techmind_v2_final.ipynb`, en ese orden, y por ninguna
otra transformación. Estas funciones son esa réplica.

Se verifica inspeccionando el vocabulario guardado dentro del .joblib:

- contiene `the`, `of`, `to`, `in`  -> el entrenamiento NO quitó stopwords
- contiene 987 términos con dígitos (`s3`, `ec2`, `ubuntu 24`)
  -> el entrenamiento NO eliminó números
- contiene 497 términos de dos letras (`js`, `ci`, `cd`, `go`)
  -> el entrenamiento NO filtró palabras cortas

Por eso aquí NO se pasa a minúsculas (lo hace el propio vectorizador),
NO se eliminan dígitos, NO se filtran palabras cortas y SÍ se conservan
los caracteres técnicos `+ # . _ - /`.

REGLA: no modificar estas funciones sin volver a entrenar el modelo.
Cualquier normalización adicional (stopwords, lematización) pertenece a
la extracción de palabras clave, nunca a la entrada del clasificador.
"""

import re

# Los patrones se compilan una sola vez a nivel de módulo (no en cada
# llamada) por eficiencia — la limpieza se invoca en cada request.
_PATRON_PUBLISHED = re.compile(r"Published.*?:.*", re.IGNORECASE)
_PATRON_URL = re.compile(r"http\S+|www\S+|https\S+", flags=re.MULTILINE)
_PATRON_SALTOS = re.compile(r"\n|\r")
# Conserva los caracteres que distinguen términos técnicos: C++, C#,
# CI/CD, .NET, front-end, node.js. La versión anterior de este módulo
# los eliminaba y perdía esa señal por completo.
_PATRON_NO_PERMITIDOS = re.compile(r"[^áéíóúüñA-Za-z0-9\s\+\#\.\_\-\/]")
_PATRON_ESPACIOS = re.compile(r"\s+")
_PATRON_LETRAS_REPETIDAS = re.compile(r"(.)\1{2,}")
_PATRON_PUNTUACION_REPETIDA = re.compile(r"([!?.,])\1{1,}")

#: Correcciones de erratas frecuentes (paso 3.1 del notebook).
CORRECCIONES_COMUNES = {
    r"\bteh\b": "the",
    r"\brecieve\b": "receive",
    r"\bwich\b": "which",
    r"\bwierd\b": "weird",
    r"\bthier\b": "their",
    r"\baltough\b": "although",
    r"\bfuntion\b": "function",
    r"\bfuncion\b": "función",
    r"\bcompatibilty\b": "compatibility",
}

_CORRECCIONES_COMPILADAS = [
    (re.compile(patron, re.IGNORECASE), reemplazo)
    for patron, reemplazo in CORRECCIONES_COMUNES.items()
]


def limpiar_texto(texto: str) -> str:
    """Aplica la limpieza base del dataset TechMind (paso 3 del notebook).

    Elimina encabezados tipo "Published on:", URLs y saltos de línea,
    descarta los caracteres que no sean alfanuméricos ni técnicos, y
    normaliza los espacios.

    Args:
        texto: Texto crudo de entrada. Cualquier valor que no sea `str`
            se trata como texto vacío.

    Returns:
        Texto limpio, sin espacios sobrantes. Cadena vacía si `texto` no
        es un `str`.

    Ejemplo:
        >>> limpiar_texto("Visita https://foo.com  ¡ya!")
        'Visita ya'
    """
    if not isinstance(texto, str):
        return ""

    texto = _PATRON_PUBLISHED.sub("", texto)
    texto = _PATRON_URL.sub("", texto)
    texto = _PATRON_SALTOS.sub(" ", texto)
    texto = _PATRON_NO_PERMITIDOS.sub("", texto)
    return _PATRON_ESPACIOS.sub(" ", texto).strip()


def corregir_ortografia(texto: str) -> str:
    """Normaliza alargamientos, puntuación repetida y erratas frecuentes.

    Réplica del paso 3.1 del notebook. Colapsa letras repetidas tres o
    más veces ("looool" -> "lool"), reduce puntuación duplicada ("???" ->
    "?") y aplica `CORRECCIONES_COMUNES`.

    Args:
        texto: Texto a corregir.

    Returns:
        Texto corregido. Cadena vacía si `texto` no es un `str`.

    Ejemplo:
        >>> corregir_ortografia("thiiiis funtion is wierd!!!")
        'thiis function is weird!'
    """
    if not isinstance(texto, str):
        return ""

    texto = _PATRON_LETRAS_REPETIDAS.sub(r"\1\1", texto)
    texto = _PATRON_PUNTUACION_REPETIDA.sub(r"\1", texto)
    for patron, reemplazo in _CORRECCIONES_COMPILADAS:
        texto = patron.sub(reemplazo, texto)
    return _PATRON_ESPACIOS.sub(" ", texto).strip()


def preparar_entrada_modelo(titulo: str, texto: str) -> str:
    """Construye la cadena exacta que el modelo espera recibir.

    El notebook de modelado entrenó con `titulo_limpio + \' \' +
    texto_limpio`, aplicando limpieza y corrección a cada campo por
    separado antes de unirlos. Esta función reproduce ese orden.

    Es el único punto por el que debe pasar cualquier texto antes de
    llegar a `pipeline.predict_proba`.

    Args:
        titulo: Título del contenido. Puede ir vacío.
        texto: Cuerpo del contenido.

    Returns:
        Cadena lista para el vectorizador. Cadena vacía si tras la
        limpieza no queda nada procesable (quien llama decide si eso es
        un error — ver ClasificadorContenido).

    Ejemplo:
        >>> preparar_entrada_modelo("Docker", "contenedores en producción")
        'Docker contenedores en producción'
    """
    titulo_limpio = corregir_ortografia(limpiar_texto(titulo))
    texto_limpio = corregir_ortografia(limpiar_texto(texto))

    entrada = f"{titulo_limpio} {texto_limpio}".strip()
    return _PATRON_ESPACIOS.sub(" ", entrada)
