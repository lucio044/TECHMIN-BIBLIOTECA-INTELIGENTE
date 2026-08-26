from pydantic import BaseModel, Field, field_validator
from typing import List


class ContenidoEntrada(BaseModel):
    titulo: str = Field(..., min_length=1)
    texto: str = Field(..., min_length=1)

    # El modelo se entreno sobre un corpus 95,9% en ingles, asi que un texto
    # en castellano acierta menos. Traducirlo antes de clasificar recupera
    # buena parte: medido sobre veinte textos coloquiales nuevos, el acierto
    # paso de 6 a 11 de 20 y la confianza media de 31% a 41%.
    #
    # No viene activado porque cuesta alrededor de un segundo y medio, y a
    # quien escribe en ingles o con vocabulario tecnico no le aporta nada.
    traducir: bool = Field(
        False,
        description="Traducir al ingles antes de clasificar. Mas preciso con "
                    "texto en español, y bastante mas lento.",
    )

    @field_validator("titulo", "texto")
    @classmethod
    def no_solo_espacios(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("El campo no puede contener solo espacios en blanco")
        return valor
    
class CategoriaRanking(BaseModel):
    categoria: str
    probabilidad: float
    
class ContenidoRelacionado(BaseModel):
    titulo: str
    # Primeros 200 caracteres del cuerpo del documento. Vacio si la matriz
    # cargada es anterior a la version que incluye la clave "extractos".
    extracto: str = ""
    categoria: str
    similitud: float


class ContenidoSalida(BaseModel):
    categoria: str
    probabilidad: float
    informacion_adicional: List[str]
    ranking_categorias: List[CategoriaRanking]
    contenidos_relacionados: List[ContenidoRelacionado]
    