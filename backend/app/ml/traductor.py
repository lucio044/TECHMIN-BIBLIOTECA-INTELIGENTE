"""Traduccion entre español e ingles, sin servicios externos.

Hace falta por una asimetria medida: el corpus esta en ingles al 95,9% y la
interfaz en español. Eso se nota en dos lugares distintos.

QUE SE MIDIO

Clasificando cuarenta textos tecnicos escritos en castellano, el acierto
fue 29 de 40. Los mismos conceptos escritos en ingles acertaban el doble
entre los casos dificiles. Con veinte textos coloquiales --«la pantalla se
ve mal desde el celular»-- el acierto cae a 6 de 20.

Traducir la entrada al ingles antes de clasificar sube esos veinte a 11, y
la confianza media de 31% a 41%. Se valido a ciegas, con textos escritos
despues de decidir la prueba, porque una propuesta anterior --clasificar
por vecinos-- ganaba en los ejemplos elegidos a mano y perdia contra el
corpus real.

Cuesta 1,4 segundos por texto, contra los 126 ms de una clasificacion
normal. Por eso no se aplica siempre: se ofrece.

POR QUE ONNX Y NO UN SERVICIO DE TRADUCCION

Un servicio externo agrega una clave, una factura y un punto de falla que
no se controla. El modelo cuantizado son 117 MB por direccion y corre en la
misma instancia.

Se carga en el primer uso y no al arrancar: quien nunca traduce no paga los
250 MB de memoria.
"""

import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[3]
RUTA_MODELOS = RAIZ / "traduccion"

IDIOMAS = ("es", "en")

# Marcas de que un texto esta en castellano. No es deteccion de idioma
# seria: alcanza para decidir en que direccion traducir, y se equivoca
# hacia el lado barato --dejar el texto como esta.
_ACENTOS = re.compile(r"[áéíóúñü¿¡]", re.IGNORECASE)
_FUNCIONALES_ES = re.compile(
    r"\b(de|la|el|los|las|un|una|que|con|para|por|del|al|se|su|es|son|"
    r"como|cuando|donde|pero|mas|muy|todo|este|esta|hay)\b", re.IGNORECASE)
_FUNCIONALES_EN = re.compile(
    r"\b(the|of|and|to|in|is|are|for|with|that|this|from|by|on|as|"
    r"you|your|it|be|have|has|can|will|not)\b", re.IGNORECASE)

# Un texto mas largo que esto se parte: el modelo trunca a 384 tokens y lo
# que sobra se perderia en silencio.
MAX_CARACTERES = 1200
_FIN_DE_FRASE = re.compile(r"(?<=[.!?])\s+")

_modelos = {}


def idioma_de(texto: str) -> str:
    """Devuelve «es» o «en». Ante la duda, «en»: es lo que domina el corpus."""
    if _ACENTOS.search(texto):
        return "es"
    es = len(_FUNCIONALES_ES.findall(texto))
    en = len(_FUNCIONALES_EN.findall(texto))
    return "es" if es > en else "en"


def hay_traductor(direccion: str) -> bool:
    """Si estan los archivos en disco. No los carga."""
    base = RUTA_MODELOS / direccion / "onnx"
    return (base / "encoder_model_quantized.onnx").exists()


def _cargar(direccion: str):
    """Trae el modelo a memoria la primera vez que hace falta."""
    if direccion in _modelos:
        return _modelos[direccion]

    ruta = RUTA_MODELOS / direccion
    if not hay_traductor(direccion):
        logger.warning("Sin traductor %s: falta %s. Ver traduccion/descargar.py",
                       direccion, ruta)
        _modelos[direccion] = None
        return None

    try:
        from optimum.onnxruntime import ORTModelForSeq2SeqLM
        from transformers import AutoTokenizer

        logger.info("Cargando el traductor %s...", direccion)
        tokenizador = AutoTokenizer.from_pretrained(str(ruta))
        modelo = ORTModelForSeq2SeqLM.from_pretrained(
            str(ruta), subfolder="onnx",
            encoder_file_name="encoder_model_quantized.onnx",
            decoder_file_name="decoder_model_quantized.onnx",
            decoder_with_past_file_name="decoder_with_past_model_quantized.onnx",
        )
        _modelos[direccion] = (tokenizador, modelo)
        logger.info("Traductor %s listo", direccion)
    except Exception as e:
        logger.error("No se pudo cargar el traductor %s: %s", direccion, e)
        _modelos[direccion] = None

    return _modelos[direccion]


def _partir(texto: str) -> List[str]:
    """Corta en frases enteras, para no truncar a mitad de idea."""
    texto = texto.strip()
    if len(texto) <= MAX_CARACTERES:
        return [texto]

    trozos, actual = [], ""
    for frase in _FIN_DE_FRASE.split(texto):
        if len(actual) + len(frase) + 1 > MAX_CARACTERES and actual:
            trozos.append(actual.strip())
            actual = frase
        else:
            actual = f"{actual} {frase}".strip()
    if actual:
        trozos.append(actual.strip())
    return trozos


@lru_cache(maxsize=512)
def _traducir_trozo(trozo: str, direccion: str) -> str:
    """Un trozo ya cortado. La cache evita repetir el mismo documento.

    Vale la pena porque los documentos populares se traducen muchas veces:
    quien pregunta por bases de datos recibe casi siempre los mismos.
    """
    cargado = _cargar(direccion)
    if cargado is None:
        return trozo
    tokenizador, modelo = cargado

    entrada = tokenizador(trozo, return_tensors="pt", truncation=True, max_length=384)
    salida = modelo.generate(**entrada, max_new_tokens=384, num_beams=1)
    return tokenizador.decode(salida[0], skip_special_tokens=True)


def traducir(texto: str, destino: str) -> Optional[str]:
    """Traduce si hace falta. Devuelve None si no se pudo.

    Un texto que ya esta en el idioma pedido se devuelve tal cual: traducir
    de un idioma a si mismo lo estropea.
    """
    if destino not in IDIOMAS or not texto or not texto.strip():
        return None

    origen = idioma_de(texto)
    if origen == destino:
        return texto

    direccion = f"{origen}-{destino}"
    if not hay_traductor(direccion):
        return None

    try:
        return " ".join(_traducir_trozo(t, direccion) for t in _partir(texto))
    except Exception as e:
        logger.error("Fallo al traducir: %s", e)
        return None


def estado() -> dict:
    return {
        "es-en": hay_traductor("es-en"),
        "en-es": hay_traductor("en-es"),
        "cargados": [d for d, m in _modelos.items() if m is not None],
    }
