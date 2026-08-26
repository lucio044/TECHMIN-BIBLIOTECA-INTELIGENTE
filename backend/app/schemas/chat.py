from typing import Literal

from pydantic import BaseModel, Field


class MensajeChat(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str


class ChatEntrada(BaseModel):
    texto: str
    historial: list[MensajeChat] = []


class TerminoDecisivo(BaseModel):
    termino: str
    aporte: float = Field(
        description="TF-IDF del termino por el coeficiente de la categoria ganadora. "
                    "Cuanto empujo ese termino hacia la decision."
    )


class Fragmento(BaseModel):
    parte: int
    texto: str
    parecido: float


class RespuestaDelHistorico(BaseModel):
    """Lo que dice el corpus sobre la pregunta, sin redactar nada.

    Cada fragmento es texto literal de un documento que existe: se puede ir
    a la fuente y comprobarlo linea por linea.
    """

    fuente: str
    categoria: str
    parecido: float
    fragmentos: list[Fragmento]
    otras_fuentes: list[str] = []
    documentos_consultados: int


class ChatSalida(BaseModel):
    respuesta: str

    # De que clase es la respuesta, para que el cliente sepa que mostrar.
    # Sin esto pintaba las palabras que pesaron y el porcentaje de confianza
    # al lado de un «no tengo informacion sobre eso», que es contradictorio:
    # esos datos explican una clasificacion que justamente no se hizo.
    #
    #   respuesta       el historico tenia material
    #   clasificacion   era un contenido y se clasifico
    #   sin_informacion era una pregunta y el corpus no la cubre
    tipo: Literal["respuesta", "clasificacion", "sin_informacion"] = "clasificacion"

    # La evidencia viaja aparte del texto para que el cliente pueda
    # mostrarla como quiera en vez de tener que leerla de la prosa.
    categoria: str | None = None
    probabilidad: float | None = None
    terminos_decisivos: list[TerminoDecisivo] = []
    fuente: Literal["modelo", "deepseek"] = "modelo"

    # Presente cuando el historico tiene material sobre la pregunta. Es lo
    # que convierte al asistente en algo que responde y no solo clasifica.
    del_historico: RespuestaDelHistorico | None = None
