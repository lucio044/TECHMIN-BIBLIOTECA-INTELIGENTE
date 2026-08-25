"""Correcciones que reporta quien usa la API.

Cuando el modelo se equivoca, quien lo nota es el cliente. Este servicio le
da un lugar donde decirlo, y cada aviso queda como un ejemplo etiquetado a
mano: exactamente el material que hace falta para reentrenar.

Es la diferencia entre un modelo que se degrada en silencio y uno que
mejora con el uso.

SOBRE LA PERSISTENCIA
Las correcciones se guardan en memoria y se pierden al reiniciar. En el
plan gratuito de Render el disco es efimero y no hay base de datos, asi que
guardarlas en un archivo daria la misma falsa sensacion de permanencia con
mas trabajo. Para produccion va una tabla, y esta anotado como tal en el
README en vez de simulado aca.
"""

import logging
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Deque, List

from app.schemas.correcciones import CorreccionEntrada, CorreccionGuardada

logger = logging.getLogger(__name__)

# Cuantas correcciones se conservan. Es un tope de memoria, no un limite de
# negocio: con una base detras no haria falta.
MAXIMO = 500

_correcciones: Deque[CorreccionGuardada] = deque(maxlen=MAXIMO)


def registrar(entrada: CorreccionEntrada) -> CorreccionGuardada:
    """Anota que el modelo se equivoco en un caso concreto."""
    guardada = CorreccionGuardada(
        titulo=entrada.titulo,
        texto=entrada.texto,
        categoria_predicha=entrada.categoria_predicha,
        categoria_correcta=entrada.categoria_correcta,
        comentario=entrada.comentario,
        registrada=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    _correcciones.append(guardada)

    # Queda tambien en el registro del servidor, que sobrevive al reinicio
    # del proceso aunque la lista en memoria no.
    logger.info(
        "CORRECCION predicha=%s correcta=%s titulo=%r",
        entrada.categoria_predicha, entrada.categoria_correcta, entrada.titulo[:80],
    )
    return guardada


def listar(limite: int) -> List[CorreccionGuardada]:
    """Las ultimas correcciones, de la mas reciente a la mas antigua."""
    return list(_correcciones)[-limite:][::-1]


def resumen() -> dict:
    """Donde se equivoca mas el modelo, segun quienes lo usan.

    El par predicha -> correcta es lo mas util: si un mismo cruce se repite,
    esas dos categorias comparten frontera y conviene mirarlas juntas antes
    de reentrenar.
    """
    if not _correcciones:
        return {"total": 0, "confusiones": {}, "categorias_perdidas": {}}

    confusiones = Counter(
        f"{c.categoria_predicha} -> {c.categoria_correcta}" for c in _correcciones
    )
    perdidas = Counter(c.categoria_correcta for c in _correcciones)

    return {
        "total": len(_correcciones),
        "confusiones": dict(confusiones.most_common(10)),
        "categorias_perdidas": dict(perdidas.most_common()),
    }
