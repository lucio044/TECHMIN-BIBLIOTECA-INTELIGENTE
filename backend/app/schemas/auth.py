from pydantic import BaseModel, EmailStr
from datetime import datetime


class UsuarioRegistro(BaseModel):
    email: EmailStr
    password: str


class UsuarioRespuesta(BaseModel):
    id: int
    email: str
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"