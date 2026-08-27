"""Traduccion entre español e ingles, sin servicios externos.

Hace falta por una asimetria medida: el corpus esta en ingles al 95,9% y la
interfaz en español. Hay temas --Mobile tiene 55 documentos en castellano de
5.048-- donde una consulta en español solo encuentra material en ingles.

QUE TRADUCE Y QUE NO

Solo lo que alguien pide leer: el boton «Ver en español» sobre resultados
que volvieron en ingles. No traduce lo que se clasifica.

Se probo lo otro --pasar la entrada al ingles antes de clasificar, ya que el
modelo aprendio en ese idioma-- y subia el acierto de 6 a 11 sobre veinte
textos coloquiales. Se descarto igual, porque hacia que el resultado
dependiera de una casilla marcada: una pagina donde el mismo texto da dos
categorias segun una casilla es peor que una que acierta un poco menos.

POR QUE SE DECODIFICA A MANO

Esto empezo usando `optimum.onnxruntime.ORTModelForSeq2SeqLM`, que es la
forma corta. Tiene dos problemas, y el primero es que no se puede instalar:

    optimum[onnxruntime]==2.3.0 arrastra optimum-onnx, que a su vez pide
    optimum~=2.1.0. Ninguna combinacion resuelve, y pip corta con
    ResolutionImpossible.

El segundo es peor y estuvo escondido: `generate()` de transformers es
torch por dentro. Con `return_tensors="np"` revienta en
`'numpy.ndarray' object has no attribute 'numpy'`. Aca las pruebas pasaban
porque hay torch instalado; en la instancia no lo hay, y son 800 MB sobre
los 2 GB que tiene.

Asi que el bucle de decodificacion esta escrito aca: codificador una vez,
decodificador token a token reusando el pasado. Son cuarenta lineas y sale
mejor de las dos formas.

    · sin torch ni optimum, solo onnxruntime y el tokenizador
    · 79 ms por texto contra los 1.857 ms del camino con optimum

Los 24x no son merito del bucle: es que `generate()` convierte tensores en
cada paso. Se comprobo sobre diecisiete textos en las dos direcciones, uno
de ellos de cinco frases, y la salida es identica caracter por caracter.

POR QUE UN MODELO LOCAL Y NO UN SERVICIO DE TRADUCCION

Un servicio externo agrega una clave, una factura y un punto de falla que
no se controla. El modelo cuantizado son 171 MB por direccion y corre en la
misma instancia.

Se carga en el primer uso y no al arrancar: quien nunca traduce no paga la
memoria.
"""

import json
import logging
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
#
# Las mismas listas estan en index.html, que decide si ofrecer el boton.
# Si se tocan aca, se tocan alla: el servidor traduciria en una direccion
# distinta de la que anuncia el boton.
_ACENTOS = re.compile(r"[áéíóúñü¿¡]", re.IGNORECASE)
_FUNCIONALES_ES = re.compile(
    r"\b(de|la|el|los|las|un|una|que|con|para|por|del|al|se|su|es|son|"
    r"como|cuando|donde|pero|mas|muy|todo|este|esta|hay|sobre|entre|"
    r"desde|hasta|sin|cual|cuales|porque|si|no|lo|mi|tiene|puedo|hacer|"
    r"mejor|nuestro)\b", re.IGNORECASE)
_FUNCIONALES_EN = re.compile(
    r"\b(the|of|and|to|in|is|are|for|with|that|this|from|by|on|as|"
    r"you|your|it|be|have|has|can|will|not|how|do|does|did|what|when|"
    r"where|why|which|an|or|if|should|would|could|about|between|over|"
    r"under|than|best|my)\b", re.IGNORECASE)

# Un texto mas largo que esto se parte: el modelo trunca a 384 tokens y lo
# que sobra se perderia en silencio.
MAX_CARACTERES = 1200
_FIN_DE_FRASE = re.compile(r"(?<=[.!?])\s+")

# Tope de tokens generados. Es una red de seguridad, no un limite esperado:
# si el modelo entra en bucle y no emite nunca el token de fin, esto corta.
MAX_TOKENS_NUEVOS = 384

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


def _sesion(ruta: Path):
    import onnxruntime as ort

    opciones = ort.SessionOptions()
    opciones.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    # La instancia tiene dos nucleos y uvicorn corre con un solo worker.
    opciones.intra_op_num_threads = 2
    return ort.InferenceSession(str(ruta), opciones, providers=["CPUExecutionProvider"])


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
        from transformers import AutoTokenizer

        logger.info("Cargando el traductor %s...", direccion)
        onnx = ruta / "onnx"
        codificador = _sesion(onnx / "encoder_model_quantized.onnx")
        decodificador = _sesion(onnx / "decoder_model_quantized.onnx")
        con_pasado = _sesion(onnx / "decoder_with_past_model_quantized.onnx")

        config = json.loads((ruta / "config.json").read_text(encoding="utf-8"))
        salidas = [s.name for s in decodificador.get_outputs()]
        # El decodificador devuelve logits y cuatro estados por capa: los dos
        # propios y los dos del codificador. De ahi salen las capas, en vez
        # de dejar un 6 escrito que se rompe si cambia el modelo.
        capas = sum(1 for s in salidas if s.endswith(".decoder.key"))

        _modelos[direccion] = {
            "codificador": codificador,
            "decodificador": decodificador,
            "con_pasado": con_pasado,
            "tokenizador": AutoTokenizer.from_pretrained(str(ruta)),
            "salidas_decodificador": salidas,
            "salidas_con_pasado": [s.name for s in con_pasado.get_outputs()],
            "capas": capas,
            "inicio": config["decoder_start_token_id"],
            "fin": config["eos_token_id"],
            "relleno": config["pad_token_id"],
        }
        logger.info("Traductor %s listo, %d capas", direccion, capas)
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


def _decodificar(m, texto: str) -> str:
    """Decodificacion voraz, token a token, reusando el pasado.

    El codificador corre una vez. Despues el decodificador produce un token
    por pasada: la primera con el texto codificado, y las siguientes con los
    estados que devolvio la anterior, que es lo que evita recalcular toda la
    secuencia en cada paso.

    Voraz y no por haces: el modelo trae `num_beams: 4` de fabrica, pero
    cuatro haces son cuatro veces el trabajo y el texto tecnico corto no
    mejora lo suficiente para pagarlo.
    """
    import numpy as np

    entrada = m["tokenizador"](texto, truncation=True, max_length=384)["input_ids"]
    tokens = np.array([entrada], dtype=np.int64)
    mascara = np.ones_like(tokens)

    oculto = m["codificador"].run(
        None, {"input_ids": tokens, "attention_mask": mascara})[0]

    estado = dict(zip(m["salidas_decodificador"], m["decodificador"].run(
        None, {
            "encoder_attention_mask": mascara,
            "input_ids": np.array([[m["inicio"]]], dtype=np.int64),
            "encoder_hidden_states": oculto,
        })))
    logits = estado["logits"]

    generados = []
    for _ in range(MAX_TOKENS_NUEVOS):
        # El relleno esta en `bad_words_ids` del generation_config: si sale
        # elegido, la traduccion queda cortada con basura al final.
        logits[0, -1, m["relleno"]] = -np.inf
        siguiente = int(logits[0, -1].argmax())
        if siguiente == m["fin"]:
            break
        generados.append(siguiente)

        alimentar = {
            "encoder_attention_mask": mascara,
            "input_ids": np.array([[siguiente]], dtype=np.int64),
        }
        for capa in range(m["capas"]):
            for lado in ("decoder", "encoder"):
                for kv in ("key", "value"):
                    alimentar[f"past_key_values.{capa}.{lado}.{kv}"] = \
                        estado[f"present.{capa}.{lado}.{kv}"]

        nuevos = dict(zip(m["salidas_con_pasado"], m["con_pasado"].run(None, alimentar)))
        logits = nuevos["logits"]
        # Lo del codificador no cambia --depende del texto de entrada, que es
        # el mismo-- y por eso este grafo no lo devuelve. Solo se actualiza
        # el pasado propio del decodificador.
        for capa in range(m["capas"]):
            for kv in ("key", "value"):
                estado[f"present.{capa}.decoder.{kv}"] = nuevos[f"present.{capa}.decoder.{kv}"]

    return m["tokenizador"].decode(generados, skip_special_tokens=True)


@lru_cache(maxsize=512)
def _traducir_trozo(trozo: str, direccion: str) -> str:
    """Un trozo ya cortado. La cache evita repetir el mismo documento.

    Vale la pena porque los documentos populares se traducen muchas veces:
    quien pregunta por bases de datos recibe casi siempre los mismos.
    """
    m = _cargar(direccion)
    if m is None:
        return trozo
    return _decodificar(m, trozo)


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
