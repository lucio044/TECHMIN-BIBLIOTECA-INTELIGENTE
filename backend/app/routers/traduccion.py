from fastapi import APIRouter, Depends, HTTPException, status

from app.core.acceso import identificar
from app.ml import traductor
from app.schemas.traduccion import (EstadoTraductor, TraduccionEntrada,
                                    TraduccionSalida)

router = APIRouter()


@router.post("/traducir", response_model=TraduccionSalida)
def traducir(entrada: TraduccionEntrada, _=Depends(identificar)):
    """Traduce entre español e ingles, sin servicios externos.

    Existe porque el historico esta en ingles al 95,9% y la interfaz en
    español: hay temas --Mobile tiene 55 documentos en castellano de
    5.048-- donde una consulta en español solo encuentra material en
    ingles.

    Se traduce a pedido y no de entrada: son 79 ms por texto, pero tambien
    171 MB de modelo por direccion, y no hay motivo para cargarlos por
    alguien que lee ingles sin problema.

    Un texto que ya esta en el idioma pedido se devuelve tal cual.
    """
    if not traductor.hay_traductor(f"{traductor.idioma_de(entrada.textos[0])}-{entrada.destino}"):
        # Puede faltar el modelo de esa direccion; se avisa en vez de
        # devolver el original haciendo creer que se tradujo.
        if traductor.idioma_de(entrada.textos[0]) != entrada.destino:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="La traduccion no esta disponible en este despliegue: "
                       "falta el modelo. Se instala con traduccion/descargar.py",
            )

    traducidos, sin_cambio = [], 0
    for texto in entrada.textos:
        resultado = traductor.traducir(texto, entrada.destino)
        if resultado is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo traducir ese texto.",
            )
        if resultado == texto:
            sin_cambio += 1
        traducidos.append(resultado)

    return TraduccionSalida(
        destino=entrada.destino,
        traducciones=traducidos,
        ya_estaban_en_destino=sin_cambio,
    )


@router.get("/traducir/estado", response_model=EstadoTraductor)
def estado(_=Depends(identificar)):
    """Que direcciones estan disponibles y cuales ya estan en memoria.

    Sirve para que el cliente sepa si mostrar el boton de traducir, en vez
    de ofrecerlo y fallar.
    """
    e = traductor.estado()
    return EstadoTraductor(
        es_en=e["es-en"],
        en_es=e["en-es"],
        cargados=e["cargados"],
    )
