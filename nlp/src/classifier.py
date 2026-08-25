"""
Orquestador del pipeline de inferencia: limpieza -> predicción -> palabras
clave -> resultado tipado.

Esta es la única pieza que conoce a todas las demás (RepositorioModelo,
ExtractorPalabrasClave, la función de limpieza). Pero no las crea ella
misma — las recibe inyectadas por constructor (inversión de dependencias),
lo que permite probarla con dobles de prueba (mocks/fakes) sin tocar
disco ni entrenar un modelo real en cada test.
"""

from typing import Callable, Optional

from src.cleaning import preparar_entrada_modelo
from src.config import TOP_N_PALABRAS_CLAVE, UMBRAL_CATEGORIA_ALTERNATIVA
from src.exceptions import EntradaInvalidaError, TextoVacioError
from src.keywords import ExtractorPalabrasClave, ExtractorPalabrasClaveTfidf
from src.model_repository import RepositorioModelo
from src.schemas import ResultadoClasificacion


class ClasificadorContenido:
    """Clasifica contenido técnico y extrae sus palabras clave.

    Ejemplo:
        >>> repositorio = RepositorioModelo(MODELO_PATH)
        >>> clasificador = ClasificadorContenido(repositorio)
        >>> resultado = clasificador.clasificar("Titulo", "Texto de ejemplo")
        >>> resultado.categoria
        'Backend'
    """

    def __init__(
        self,
        repositorio_modelo: RepositorioModelo,
        umbral_categoria_alternativa: float = UMBRAL_CATEGORIA_ALTERNATIVA,
        top_n_palabras_clave: int = TOP_N_PALABRAS_CLAVE,
        limpiador: Callable[[str, str], str] = preparar_entrada_modelo,
    ) -> None:
        """
        Args:
            repositorio_modelo: Fuente del Pipeline entrenado.
            umbral_categoria_alternativa: Probabilidad mínima para NO
                incluir una categoría alternativa en la respuesta.
            top_n_palabras_clave: Cantidad de palabras clave a devolver.
            limpiador: Función de limpieza de texto a usar. Inyectable
                para pruebas o para cambiar de estrategia sin tocar esta
                clase (principio abierto/cerrado).
        """
        self._repositorio_modelo = repositorio_modelo
        self._umbral_categoria_alternativa = umbral_categoria_alternativa
        self._top_n_palabras_clave = top_n_palabras_clave
        self._limpiador = limpiador
        self._extractor_palabras_clave: Optional[ExtractorPalabrasClave] = None

    def precargar(self) -> None:
        """Fuerza la carga del modelo y la construcción del extractor de
        palabras clave, sin clasificar nada.

        Pensado para llamarse al arrancar la API: así el costo de leer el
        `.joblib` (varios MB) lo paga el arranque y no el primer usuario, y
        un modelo faltante o inválido se detecta antes de aceptar tráfico.

        Raises:
            ModeloNoDisponibleError: si el modelo no se pudo cargar.
            ModeloInvalidoError: si el modelo cargado no es válido.
        """
        pipeline = self._repositorio_modelo.obtener_pipeline()
        self._obtener_extractor_palabras_clave(pipeline)

    def clasificar(self, titulo: str, texto: str) -> ResultadoClasificacion:
        """Clasifica un contenido técnico y extrae sus palabras clave.

        Args:
            titulo: Título del contenido.
            texto: Cuerpo del contenido.

        Returns:
            El resultado tipado de la clasificación.

        Raises:
            EntradaInvalidaError: si `titulo` o `texto` no son `str`.
            TextoVacioError: si no queda texto procesable tras la limpieza.
            ModeloNoDisponibleError: si el modelo no se pudo cargar.
            ModeloInvalidoError: si el modelo cargado no es válido.
        """
        self._validar_entrada(titulo, texto)

        # Orden v2: título primero, texto después (ver notebook de modelado).
        # Cada campo se limpia por separado y luego se unen, igual que en
        # el entrenamiento (titulo_limpio + ' ' + texto_limpio). Concatenar
        # antes de limpiar no es equivalente: el título podría terminar en
        # una URL o un símbolo que altere el límite entre ambos campos.
        texto_limpio = self._limpiador(titulo, texto)

        if not texto_limpio.strip():
            raise TextoVacioError(
                "El texto no contiene contenido procesable después de la limpieza."
            )

        pipeline = self._repositorio_modelo.obtener_pipeline()

        probabilidades = pipeline.predict_proba([texto_limpio])[0]
        indices_por_probabilidad = probabilidades.argsort()[::-1]

        indice_principal = indices_por_probabilidad[0]
        categoria = str(pipeline.classes_[indice_principal])
        probabilidad = float(probabilidades[indice_principal])

        # La categoría se pasa al extractor para que pondere cada término
        # por su aporte a esa clase: así las palabras clave explican la
        # clasificación en vez de solo describir el texto.
        palabras_clave = self._obtener_extractor_palabras_clave(pipeline).extraer(
            texto_limpio, self._top_n_palabras_clave, categoria
        )

        categoria_alternativa = None
        if probabilidad < self._umbral_categoria_alternativa:
            indice_alternativo = indices_por_probabilidad[1]
            categoria_alternativa = str(pipeline.classes_[indice_alternativo])

        return ResultadoClasificacion(
            categoria=categoria,
            probabilidad=round(probabilidad, 3),
            informacion_adicional=palabras_clave,
            categoria_alternativa=categoria_alternativa,
        )

    def _obtener_extractor_palabras_clave(self, pipeline) -> ExtractorPalabrasClave:
        # Se construye una sola vez y se reutiliza (el vectorizador no
        # cambia entre llamadas mientras el Pipeline sea el mismo).
        if self._extractor_palabras_clave is None:
            vectorizador = pipeline.named_steps["tfidf"]
            clasificador = pipeline.named_steps.get("clf")
            self._extractor_palabras_clave = ExtractorPalabrasClaveTfidf(
                vectorizador, clasificador
            )
        return self._extractor_palabras_clave

    @staticmethod
    def _validar_entrada(titulo: str, texto: str) -> None:
        if not isinstance(titulo, str) or not isinstance(texto, str):
            raise EntradaInvalidaError("'titulo' y 'texto' deben ser cadenas de texto (str).")
        if not titulo.strip() and not texto.strip():
            raise TextoVacioError("'titulo' y 'texto' no pueden estar ambos vacíos.")
