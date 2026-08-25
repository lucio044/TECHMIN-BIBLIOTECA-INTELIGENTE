from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    proveedor = Column(String(50), default="local")
    proveedor_id = Column(String(255), nullable=True)
    fecha_creacion = Column(TIMESTAMP, server_default=func.now())