from fastapi import APIRouter, Depends, Query, status

from app.core.acceso import identificar
from app.schemas.correcciones import (CorreccionEntrada, CorreccionesSalida,
                                      CorreccionGuardada)
from app.services import correcciones as servicio

router = APIRouter(tags=["correcciones"])


@router.post("/correcciones", response_model=CorreccionGuardada,
             status_code=status.HTTP_201_CREATED)
def reportar(entrada: CorreccionEntrada, _=Depends(identificar)):
    """Reporta que el modelo se equivoco en un caso concreto.

    Cada aviso queda como un ejemplo etiquetado a mano, que es justo el
    material que hace falta para reentrenar. Es la diferencia entre un
    modelo que se degrada en silencio y uno que mejora con el uso.
    """
    return servicio.registrar(entrada)


@router.get("/correcciones", response_model=CorreccionesSalida)
def listar(limite: int = Query(50, ge=1, le=500), _=Depends(identificar)):
    """Las ultimas correcciones reportadas."""
    guardadas = servicio.listar(limite)
    return CorreccionesSalida(total=len(guardadas), correcciones=guardadas)


@router.get("/correcciones/resumen")
def resumen(_=Depends(identificar)):
    """Donde se equivoca mas el modelo, segun quienes lo usan.

    El par predicha -> correcta es lo mas util: si un cruce se repite, esas
    dos categorias comparten frontera y conviene mirarlas juntas.
    """
    return servicio.resumen()
