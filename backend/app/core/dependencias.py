import uuid
from fastapi import Request, Response


def obtener_usuario_actual(request: Request, response: Response) -> str:
    identificador = request.cookies.get("usuario_id")

    if identificador is None:
        identificador = str(uuid.uuid4())
        response.set_cookie(
            key="usuario_id",
            value=identificador,
            httponly=True,
            samesite="none",
            secure=True,
            max_age=60 * 60 * 24 * 365,
        )

    return identificador