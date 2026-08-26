"""El asistente que explica una clasificacion.

Funciona en dos modos, y la diferencia es solo de redaccion:

  MODELO    Sin clave de proveedor. La respuesta se arma con lo que el
            propio sistema calculo: la categoria, los terminos que mas
            empujaron la decision, las candidatas que quedaron atras y los
            documentos parecidos del historico. Nunca falla, no cuesta
            nada y no puede afirmar nada que el sistema no sepa.

  DEEPSEEK  Con clave configurada. Se le pasa esa misma evidencia ya
            calculada y redacta en prosa. Si la llamada falla, se vuelve
            al modo anterior en vez de disculparse.

El orden importa: la evidencia se calcula siempre primero. El proveedor
externo redacta sobre hechos, no los inventa a partir de una etiqueta.
"""

import logging

from openai import OpenAI

from app.core.config import settings
from app.schemas.contenido import ContenidoEntrada
from app.services import explicacion, sintetizador
from app.services.clasificador import clasificar_contenido

logger = logging.getLogger(__name__)

_cliente = None


def hay_proveedor() -> bool:
    return bool(settings.deepseek_api_key)


def _obtener_cliente() -> OpenAI:
    global _cliente
    if _cliente is None:
        _cliente = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
    return _cliente


def construir_prompt(texto_usuario: str, resultado, terminos: list[dict]) -> str:
    """Le da al modelo de lenguaje los hechos, no la tarea de adivinarlos."""
    evidencia = ", ".join(f"{t['termino']} ({t['aporte']:+.2f})" for t in terminos) or "ninguno destacado"
    relacionados = getattr(resultado, "contenidos_relacionados", None) or []
    vecinos = "; ".join(f"{r.titulo} (similitud {r.similitud:.2f})" for r in relacionados[:3]) or "ninguno"

    return (
        f"Contenido del usuario: \"{texto_usuario}\"\n\n"
        f"Nuestro clasificador lo ubico en '{resultado.categoria}' con {resultado.probabilidad:.0%} "
        f"de confianza.\n"
        f"Terminos que mas empujaron esa decision, con su aporte: {evidencia}.\n"
        f"Documentos parecidos en el historico: {vecinos}.\n\n"
        f"Explica el contenido de forma clara y natural en español, apoyandote en esos datos. "
        f"No inventes hechos que no esten arriba y no menciones que provienen de un modelo. "
        f"Varia la forma de abrir la respuesta en lugar de empezar siempre igual."
    )


def responder_chat(texto_usuario: str, historial: list) -> dict:
    entrada = ContenidoEntrada(titulo="Consulta de chat", texto=texto_usuario)
    resultado = clasificar_contenido(entrada)

    # La evidencia se calcula siempre: es la respuesta en un modo y el
    # insumo del prompt en el otro.
    _, _, terminos = explicacion.terminos_decisivos(texto_usuario)

    # Antes que nada, ¿el historico dice algo sobre esto? Si lo dice, eso es
    # una respuesta; la clasificacion sola no lo es.
    del_historico = sintetizador.responder(texto_usuario)

    base = {
        "categoria": resultado.categoria,
        "probabilidad": resultado.probabilidad,
        "terminos_decisivos": terminos,
        "del_historico": del_historico,
    }

    if not hay_proveedor():
        return {**base,
                "respuesta": explicacion.redactar(texto_usuario, resultado, del_historico),
                "fuente": "modelo"}

    mensajes = [{"role": m.rol, "content": m.contenido} for m in historial]
    mensajes.append({"role": "user", "content": construir_prompt(texto_usuario, resultado, terminos)})

    try:
        respuesta = _obtener_cliente().chat.completions.create(
            model="deepseek-chat",
            messages=mensajes,
        )
        return {**base, "respuesta": respuesta.choices[0].message.content, "fuente": "deepseek"}
    except Exception as e:
        # Se degrada al modo modelo, que responde igual de bien. El usuario
        # no tiene por que enterarse de que un proveedor externo fallo.
        logger.warning("DeepSeek no respondio, se explica con el modelo: %s", e)
        return {**base,
                "respuesta": explicacion.redactar(texto_usuario, resultado, del_historico),
                "fuente": "modelo"}
