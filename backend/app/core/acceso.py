"""Control de acceso: claves de API y limite de peticiones.

El limite se lleva en memoria del proceso. Alcanza para un servicio en una
sola instancia, que es el caso: con varias replicas cada una contaria por su
cuenta y el limite real seria el doble o el triple. Para eso hace falta un
almacen compartido tipo Redis, y se anota como deuda, no se simula.

Se permite el uso anonimo a proposito, con un limite bajo. La demo publica
tiene que funcionar sin que nadie pida una clave, y al mismo tiempo un
visitante no puede consumir la capacidad del servicio. Quien tiene clave
recibe un limite mucho mas alto.
"""

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from fastapi import Header, HTTPException, Request, status

VENTANA_SEGUNDOS = 60

# Peticiones por minuto. El limite anonimo deja probar la demo con holgura
# pero no sirve para procesar un corpus entero.
LIMITE_ANONIMO = 30
LIMITE_CON_CLAVE = 600

CABECERA = "X-API-Key"


@dataclass(frozen=True)
class Cliente:
    """Quien esta llamando: una clave concreta o un anonimo por IP."""

    identificador: str
    autenticado: bool

    @property
    def limite(self) -> int:
        return LIMITE_CON_CLAVE if self.autenticado else LIMITE_ANONIMO


def _claves_validas() -> set:
    """Las claves aceptadas, separadas por coma en el entorno.

    Sin la variable configurada no hay claves: el servicio queda en modo
    abierto con el limite anonimo. Es lo que corresponde para una demo
    publica, y basta con definirla para empezar a cobrar acceso.
    """
    crudo = os.environ.get("TECHMIND_API_KEYS", "")
    return {c.strip() for c in crudo.split(",") if c.strip()}


# El historial de cada cliente: los instantes de sus ultimas peticiones.
_historial: Dict[str, Deque[float]] = defaultdict(deque)


def _consumir(cliente: Cliente) -> tuple[int, float]:
    """Registra una peticion y devuelve cuantas quedan y cuando se renueva.

    Es una ventana deslizante, no un contador que se reinicia cada minuto:
    con un contador, alguien podria gastar el limite entero al final de un
    minuto y otro tanto al principio del siguiente.
    """
    ahora = time.monotonic()
    marcas = _historial[cliente.identificador]

    while marcas and ahora - marcas[0] >= VENTANA_SEGUNDOS:
        marcas.popleft()

    if len(marcas) >= cliente.limite:
        espera = VENTANA_SEGUNDOS - (ahora - marcas[0])
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Limite de {cliente.limite} peticiones por minuto alcanzado. "
                f"Reintentar en {espera:.0f} segundos."
                + ("" if cliente.autenticado else
                   " Con una clave de API el limite es de "
                   f"{LIMITE_CON_CLAVE} por minuto.")
            ),
            headers={"Retry-After": str(int(espera) + 1)},
        )

    marcas.append(ahora)
    restantes = cliente.limite - len(marcas)
    renueva = marcas[0] + VENTANA_SEGUNDOS - ahora
    return restantes, renueva


def identificar(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias=CABECERA),
) -> Cliente:
    """Dependencia de FastAPI: identifica al cliente y aplica el limite.

    Una clave que no figura entre las validas se rechaza en vez de tratarse
    como anonima: quien la manda cree tener acceso, y dejarlo pasar con el
    limite bajo le daria un error confuso mas adelante.
    """
    validas = _claves_validas()

    if x_api_key:
        if x_api_key not in validas:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="La clave de API no es valida.",
            )
        # Solo los ultimos caracteres, para no dejar la clave en los registros.
        cliente = Cliente(f"clave:{x_api_key[-6:]}", autenticado=True)
    else:
        ip = request.client.host if request.client else "desconocida"
        cliente = Cliente(f"ip:{ip}", autenticado=False)

    restantes, renueva = _consumir(cliente)

    # Las cabeceras estandar para que un cliente pueda regularse solo en vez
    # de descubrir el limite a fuerza de errores.
    request.state.limite_cabeceras = {
        "X-RateLimit-Limit": str(cliente.limite),
        "X-RateLimit-Remaining": str(restantes),
        "X-RateLimit-Reset": str(int(renueva)),
    }
    request.state.cliente = cliente
    return cliente
