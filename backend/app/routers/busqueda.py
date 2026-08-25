from fastapi import APIRouter, Depends, Query

from app.schemas.busqueda import BusquedaSalida
from app.services.busqueda import buscar_documentos
from app.core.acceso import identificar

router = APIRouter()


@router.get("/buscar", response_model=BusquedaSalida)
def buscar(
    termino: str = Query(..., min_length=2, max_length=60, description="Palabra o par de palabras a buscar"),
    cantidad: int = Query(10, ge=1, le=50),
    _=Depends(identificar),
):
    """Busca en el historico los documentos donde ese termino pesa mas.

    Es distinto del contenido relacionado: alli entra un texto completo y
    se buscan documentos parecidos en conjunto. Aca entra un termino suelto
    y se devuelven los documentos que mas hablan de el.

    Devuelve una lista vacia si el termino no aparece en el corpus.
    """
    return buscar_documentos(termino, cantidad)
