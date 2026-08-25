"""Tabla de correcciones reportadas por quienes usan la API."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Correccion(Base):
    __tablename__ = "correcciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(300))
    texto: Mapped[str] = mapped_column(Text)
    # Se indexan las dos categorias porque la consulta que importa es
    # agrupar por el par predicha/correcta para ver que fronteras confunde
    # mas el modelo.
    categoria_predicha: Mapped[str] = mapped_column(String(60), index=True)
    categoria_correcta: Mapped[str] = mapped_column(String(60), index=True)
    comentario: Mapped[str | None] = mapped_column(String(500), nullable=True)
    registrada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
