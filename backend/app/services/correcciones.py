"""Correcciones que reporta quien usa la API.

Cuando el modelo se equivoca, quien lo nota es el cliente. Este servicio le
da un lugar donde decirlo, y cada aviso queda como un ejemplo etiquetado a
mano: exactamente el material que hace falta para reentrenar.

Es la diferencia entre un modelo que se degrada en silencio y uno que
mejora con el uso.

Con base de datos configurada las correcciones persisten. Sin ella se
guardan en memoria y se pierden al reiniciar, para que la demo publica
funcione igual sin depender de un servidor externo.
"""

import logging
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Deque, List

from sqlalchemy import func, select

from app.core.database import SessionLocal, hay_base
from app.models.correccion import Correccion
from app.schemas.correcciones import CorreccionEntrada, CorreccionGuardada

logger = logging.getLogger(__name__)

# Tope de la copia en memoria. No aplica cuando hay base.
MAXIMO_EN_MEMORIA = 500

_memoria: Deque[CorreccionGuardada] = deque(maxlen=MAXIMO_EN_MEMORIA)


def _a_esquema(fila: Correccion) -> CorreccionGuardada:
    return CorreccionGuardada(
        titulo=fila.titulo,
        texto=fila.texto,
        categoria_predicha=fila.categoria_predicha,
        categoria_correcta=fila.categoria_correcta,
        comentario=fila.comentario,
        registrada=fila.registrada.isoformat(timespec="seconds"),
    )


def registrar(entrada: CorreccionEntrada) -> CorreccionGuardada:
    """Anota que el modelo se equivoco en un caso concreto."""
    # Queda tambien en el registro del servidor. Si la base falla, el aviso
    # no se pierde del todo: queda en los logs, que se pueden recuperar.
    logger.info(
        "CORRECCION predicha=%s correcta=%s titulo=%r",
        entrada.categoria_predicha, entrada.categoria_correcta, entrada.titulo[:80],
    )

    if not hay_base():
        guardada = CorreccionGuardada(
            **entrada.model_dump(),
            registrada=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        _memoria.append(guardada)
        return guardada

    with SessionLocal() as db:
        fila = Correccion(**entrada.model_dump())
        db.add(fila)
        db.commit()
        db.refresh(fila)
        return _a_esquema(fila)


def listar(limite: int) -> List[CorreccionGuardada]:
    """Las ultimas correcciones, de la mas reciente a la mas antigua."""
    if not hay_base():
        return list(_memoria)[-limite:][::-1]

    with SessionLocal() as db:
        filas = db.scalars(
            select(Correccion).order_by(Correccion.registrada.desc()).limit(limite)
        ).all()
        return [_a_esquema(f) for f in filas]


def resumen() -> dict:
    """Donde se equivoca mas el modelo, segun quienes lo usan.

    El par predicha -> correcta es lo mas util: si un mismo cruce se repite,
    esas dos categorias comparten frontera y conviene mirarlas juntas antes
    de reentrenar.
    """
    if not hay_base():
        if not _memoria:
            return {"total": 0, "confusiones": {}, "categorias_perdidas": {}}
        confusiones = Counter(
            f"{c.categoria_predicha} -> {c.categoria_correcta}" for c in _memoria
        )
        perdidas = Counter(c.categoria_correcta for c in _memoria)
        return {
            "total": len(_memoria),
            "confusiones": dict(confusiones.most_common(10)),
            "categorias_perdidas": dict(perdidas.most_common()),
        }

    # Se agrupa en la base y no en Python: con miles de correcciones,
    # traerlas todas para contarlas seria traer un dataset entero por una
    # consulta que el motor resuelve en milisegundos.
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(Correccion)) or 0
        if not total:
            return {"total": 0, "confusiones": {}, "categorias_perdidas": {}}

        cruces = db.execute(
            select(
                Correccion.categoria_predicha,
                Correccion.categoria_correcta,
                func.count().label("n"),
            )
            .group_by(Correccion.categoria_predicha, Correccion.categoria_correcta)
            .order_by(func.count().desc())
            .limit(10)
        ).all()

        perdidas = db.execute(
            select(Correccion.categoria_correcta, func.count().label("n"))
            .group_by(Correccion.categoria_correcta)
            .order_by(func.count().desc())
        ).all()

        return {
            "total": total,
            "confusiones": {f"{p} -> {c}": n for p, c, n in cruces},
            "categorias_perdidas": {c: n for c, n in perdidas},
        }
