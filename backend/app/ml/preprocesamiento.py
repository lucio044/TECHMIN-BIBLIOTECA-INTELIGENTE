import re

_PATRON_PUBLISHED = re.compile(r"Published.*?:.*", re.IGNORECASE)
_PATRON_URL = re.compile(r"http\S+|www\S+|https\S+", flags=re.MULTILINE)
_PATRON_SALTOS = re.compile(r"\n|\r")
_PATRON_NO_PERMITIDOS = re.compile(r"[^áéíóúüñA-Za-z0-9\s\+\#\.\_\-\/]")
_PATRON_ESPACIOS = re.compile(r"\s+")
_PATRON_LETRAS_REPETIDAS = re.compile(r"(.)\1{2,}")
_PATRON_PUNTUACION_REPETIDA = re.compile(r"([!?.,])\1{1,}")

CORRECCIONES_COMUNES = {
    r"\bteh\b": "the", r"\brecieve\b": "receive", r"\bwich\b": "which",
    r"\bwierd\b": "weird", r"\bthier\b": "their", r"\baltough\b": "although",
    r"\bfuntion\b": "function", r"\bfuncion\b": "función",
    r"\bcompatibilty\b": "compatibility",
}
_CORRECCIONES_COMPILADAS = [
    (re.compile(p, re.IGNORECASE), r) for p, r in CORRECCIONES_COMUNES.items()
]


def limpiar_texto(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    texto = _PATRON_PUBLISHED.sub("", texto)
    texto = _PATRON_URL.sub("", texto)
    texto = _PATRON_SALTOS.sub(" ", texto)
    texto = _PATRON_NO_PERMITIDOS.sub("", texto)
    return _PATRON_ESPACIOS.sub(" ", texto).strip()


def corregir_ortografia(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    texto = _PATRON_LETRAS_REPETIDAS.sub(r"\1\1", texto)
    texto = _PATRON_PUNTUACION_REPETIDA.sub(r"\1", texto)
    for patron, reemplazo in _CORRECCIONES_COMPILADAS:
        texto = patron.sub(reemplazo, texto)
    return _PATRON_ESPACIOS.sub(" ", texto).strip()


def preparar_entrada_modelo(titulo: str, texto: str) -> str:
    titulo_limpio = corregir_ortografia(limpiar_texto(titulo))
    texto_limpio = corregir_ortografia(limpiar_texto(texto))
    entrada = f"{titulo_limpio} {texto_limpio}".strip()
    return _PATRON_ESPACIOS.sub(" ", entrada)