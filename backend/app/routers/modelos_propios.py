from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.acceso import identificar
from app.schemas.modelos_propios import (ClasificacionPropia, ModeloEntrenado,
                                         TextoAClasificar)
from app.services import modelos_propios as servicio

router = APIRouter(prefix="/modelos", tags=["modelos propios"])


@router.post("", response_model=ModeloEntrenado, status_code=status.HTTP_201_CREATED)
async def entrenar(
    archivo: UploadFile = File(..., description="CSV con columnas de texto y categoria"),
    nombre: str = Form("sin nombre", max_length=80),
    _=Depends(identificar),
):
    """Entrena un modelo con las categorias del propio cliente.

    El modelo de fabrica clasifica en 8 categorias tecnicas, que sirven a
    quien organiza contenido de programacion y a nadie mas. Aca cada uno
    sube su CSV con sus etiquetas y se queda con un modelo suyo.

    Devuelve el F1 macro medido sobre el 20% que se aparta antes de
    entrenar, no sobre los mismos textos con los que aprendio.
    """
    return await servicio.entrenar(archivo, nombre)


@router.get("", response_model=List[ModeloEntrenado])
def listar(_=Depends(identificar)):
    """Los modelos entrenados que siguen en memoria."""
    return servicio.listar()


@router.post("/{modelo_id}/clasificar", response_model=ClasificacionPropia)
def clasificar(modelo_id: str, entrada: TextoAClasificar, _=Depends(identificar)):
    """Clasifica un texto con un modelo propio."""
    return servicio.clasificar(modelo_id, entrada.texto)


@router.delete("/{modelo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(modelo_id: str, _=Depends(identificar)):
    """Descarta un modelo y libera su memoria."""
    servicio.eliminar(modelo_id)
