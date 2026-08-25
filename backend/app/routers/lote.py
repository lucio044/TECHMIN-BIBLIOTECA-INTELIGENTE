from fastapi import APIRouter, Depends, File, UploadFile

from app.schemas.lote import LoteSalida
from app.services.lote import clasificar_lote
from app.core.acceso import identificar

router = APIRouter()


@router.post("/lote", response_model=LoteSalida)
async def procesar_lote(
    archivo: UploadFile = File(..., description="CSV con columnas de titulo y texto"),
    _=Depends(identificar),
):
    """Clasifica de una vez todas las filas de un CSV.

    El archivo necesita una fila de cabeceras con una columna de titulo y
    otra de texto. Se aceptan varios nombres --titulo/title,
    texto/contenido/text/content-- porque un CSV exportado de otra
    herramienta rara vez usa los que uno espera.

    Una fila mal formada no tumba el lote: se anota su error y se sigue con
    las demas. La respuesta trae el detalle fila por fila y un resumen de
    cuantas cayeron en cada categoria.
    """
    return await clasificar_lote(archivo)
