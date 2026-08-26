from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.acceso import identificar
from app.ml import semantico
from app.schemas.semantica import BusquedaSemanticaSalida

router = APIRouter()


@router.get("/semantica", response_model=BusquedaSemanticaSalida)
def buscar_por_significado(
    consulta: str = Query(..., min_length=3, max_length=300,
                          description="Lo que se busca, en lenguaje corriente"),
    cantidad: int = Query(5, ge=1, le=25),
    _=Depends(identificar),
):
    """Busca en el historico por significado, no por palabras compartidas.

    Es lo que distingue esta ruta de `/buscar`: alli un documento aparece si
    contiene el termino, aca aparece si habla de lo mismo aunque no comparta
    ni una palabra.

    Sobre este corpus la diferencia se nota sobre todo entre idiomas. El
    95,9% de los documentos esta en ingles, asi que una consulta en español
    encuentra poco por coincidencia de terminos. El modelo es multilingue:
    «como protejo las contraseñas» recupera documentos sobre *password
    hashing*.

    El campo `parecido` es el coseno entre significados, de -1 a 1. Por
    debajo de 0,25 no se devuelve nada, porque a partir de ahi lo mas
    parecido del historico ya no se parece.
    """
    buscador = semantico.cargar_buscador()
    if buscador is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La busqueda semantica no esta disponible en este despliegue: "
                   "faltan el modelo de embeddings o los vectores del historico. "
                   "Se generan con semantica/generar_embeddings.py.",
        )

    resultados = buscador.buscar(consulta, top_n=cantidad)
    return BusquedaSemanticaSalida(
        consulta=consulta,
        total=len(resultados),
        documentos_comparados=buscador.total_documentos,
        resultados=resultados,
    )
