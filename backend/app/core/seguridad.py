from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hashear_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return pwd_context.verify(password_plano, password_hash)


def crear_token(datos: dict) -> str:
    datos_copia = datos.copy()
    expira = datetime.utcnow() + timedelta(minutes=settings.jwt_minutos_expiracion)
    datos_copia.update({"exp": expira})
    return jwt.encode(datos_copia, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)