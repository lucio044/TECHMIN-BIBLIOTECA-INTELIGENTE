from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.acceso import Cliente, identificar
from app.schemas.modelos_propios import (ClasificacionPropia, ModeloEntrenado,
                                         TextoAClasificar)
from app.services import modelos_propios as servicio

router = APIRouter(prefix="/modelos", tags=["modelos propios"])


@router.post("", response_model=ModeloEntrenado, status_code=status.HTTP_201_CREATED)
async def entrenar(
    archivo: UploadFile = File(..., description="CSV con columnas de texto y categoria"),
    nombre: str = Form("sin nombre", max_length=80),
    cliente: Cliente = Depends(identificar),
):
    """Entrena un modelo con las categorias del propio cliente.

    El modelo de fabrica clasifica en 8 categorias tecnicas, que sirven a
    quien organiza contenido de programacion y a nadie mas. Aca cada uno
    sube su CSV con sus etiquetas y se queda con un modelo suyo.

    Devuelve el F1 macro medido sobre el 20% que se aparta antes de
    entrenar, no sobre los mismos textos con los que aprendio.

    El modelo queda a nombre de quien lo entrena: con clave de API, de esa
    clave; sin clave, de la IP. Solo esa identidad puede listarlo, usarlo o
    borrarlo despues.
    """
    return await servicio.entrenar(archivo, nombre, cliente.identificador)


@router.get("", response_model=List[ModeloEntrenado])
def listar(cliente: Cliente = Depends(identificar)):
    """Los modelos entrenados por quien pregunta.

    No devuelve los de otros clientes: sus nombres y sus taxonomias dicen
    a que se dedica cada uno.
    """
    return servicio.listar(cliente.identificador)


@router.post("/{modelo_id}/clasificar", response_model=ClasificacionPropia)
def clasificar(
    modelo_id: str,
    entrada: TextoAClasificar,
    cliente: Cliente = Depends(identificar),
):
    """Clasifica un texto con un modelo propio.

    Un modelo de otro cliente responde 404, igual que uno inexistente.
    """
    return servicio.clasificar(modelo_id, cliente.identificador, entrada.texto)


@router.delete("/{modelo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(modelo_id: str, cliente: Cliente = Depends(identificar)):
    """Descarta un modelo propio y libera su memoria."""
    servicio.eliminar(modelo_id, cliente.identificador)
