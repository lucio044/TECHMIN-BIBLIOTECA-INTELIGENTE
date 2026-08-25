"""Tabla de modelos entrenados con las categorias de cada cliente."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModeloPropio(Base):
    __tablename__ = "modelos_propios"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    # El Pipeline serializado. Pesa entre 1 y 3 MB con los limites actuales
    # --20.000 filas y 30.000 terminos-- asi que entra comodo en la fila.
    # Si algun dia los modelos crecieran, va a almacenamiento de objetos y
    # aca queda solo la referencia.
    artefacto: Mapped[bytes] = mapped_column(LargeBinary)
    categorias: Mapped[list] = mapped_column(JSON)
    distribucion: Mapped[dict] = mapped_column(JSON)
    ejemplos: Mapped[int] = mapped_column(Integer)
    f1_macro: Mapped[float] = mapped_column(Float)
    entrenado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
