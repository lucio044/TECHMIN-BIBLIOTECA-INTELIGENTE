from fastapi import APIRouter, Depends
from datetime import datetime

from app.core.acceso import identificar
from app.core.dependencias import obtener_usuario_actual
from app.schemas.contenido import ContenidoEntrada
from app.schemas.biblioteca import BibliotecaEntrada, BibliotecaResultado
from app.services.clasificador import clasificar_contenido
from app.services.biblioteca import guardar_en_biblioteca, obtener_biblioteca

router = APIRouter()


@router.post("/biblioteca", response_model=BibliotecaResultado)
def guardar_contenido(
    entrada: BibliotecaEntrada,
    usuario_id: str = Depends(obtener_usuario_actual),
    _=Depends(identificar),
):
    resultado_clasificacion = clasificar_contenido(
        ContenidoEntrada(titulo=entrada.titulo, texto=entrada.texto)
    )

    entrada_completa = BibliotecaResultado(
        titulo=entrada.titulo,
        texto=entrada.texto,
        categoria=resultado_clasificacion.categoria,
        probabilidad=resultado_clasificacion.probabilidad,
        palabras_clave=resultado_clasificacion.informacion_adicional,
        fecha_creacion=datetime.now(),
    )

    guardar_en_biblioteca(usuario_id, entrada_completa.model_dump())
    return entrada_completa


@router.get("/biblioteca", response_model=list[BibliotecaResultado])
def listar_biblioteca(
    usuario_id: str = Depends(obtener_usuario_actual),
    _=Depends(identificar),
):
    return obtener_biblioteca(usuario_id)