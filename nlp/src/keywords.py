"""
Extracción de palabras clave a partir de los pesos TF-IDF del propio
vectorizador ya entrenado.

Responsabilidad única: dado un texto ya limpio y un vectorizador TF-IDF
ajustado, devolver sus términos de mayor peso. No sabe cómo se limpia
el texto, ni cómo se carga el modelo, ni qué se hace con el resultado.

Este enfoque reemplaza la lematización con NLTK (como se hacía en la v1
del pipeline): WordNetLemmatizer de NLTK solo tiene lexicón en inglés, así
que con el dataset bilingüe (EN + ES) dejaba de tener sentido para la
mitad del contenido. Usar los pesos del vectorizador resuelve esto de
raíz — el vocabulario ya es bilingüe porque así se entrenó — y además
elimina una dependencia externa (nltk + descarga de corpus).
"""

import re
import unicodedata
from typing import List, Optional, Protocol

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

# ---------------------------------------------------------------------------
# Filtro de términos vacíos
#
# Necesario desde la actualización al modelo entregado: ese modelo se entrenó
# SIN eliminar stopwords, así que su vocabulario de 60.000 features está lleno
# de términos como `the`, `of`, `en`, `la creación`, `los conceptos`. Sin este
# filtro, la respuesta de la demo salía así:
#
#   "informacion_adicional": ["spring boot", "java spring", "la creación",
#                             "los conceptos", "creación de"]
#
# Tres de cinco términos son relleno. El modelo clasifica igual de bien (el
# IDF ya neutraliza esas palabras: el IDF de `the` es 1.07), pero lo que se ve
# en pantalla durante la sustentación es esto.
#
# El inglés se cubre con ENGLISH_STOP_WORDS de sklearn (~318 términos) para no
# mantener a mano una lista que ya existe y está probada.
# ---------------------------------------------------------------------------

_STOP_ES = frozenset("""
el la los las un una unos unas lo al del yo tú él ella nosotros ellos ellas
me te se nos os mi mis tu tus su sus nuestro nuestra este esta estos estas
ese esa esos esas aquel aquella algo nada quien quienes cuyo cuya
a ante bajo con contra de desde durante en entre hacia hasta mediante para
por según sin sobre tras vía y e ni o u pero mas sino porque que aunque si
como tan tanto así luego pues soy eres es somos son fui fue fueron sea sean
era eran estoy estás está estamos están esté estén estaba estaban he has ha
hemos han haya hayan había habían ser estar haber tener tiene tienen hay
no sí ya muy más menos también tampoco todo toda todos todas otro otra otros
otras alguno alguna algunos algunas ninguno ninguna poco poca pocos pocas
mucho mucha muchos muchas cuanto cuantos donde cuando además aquí allí acá
allá ahora antes después entonces siempre nunca jamás tal casi solo sólo cada
mismo misma puede pueden hacer hace
quiero quiere queremos quieren saber usando usar uso conviene necesito
necesita tengo estoy debo debe deben sirve funciona manera forma cosa cosas
ejemplo ejemplos pregunta problema ayuda favor gracias hola parte partes vez
veces tema temas
introducción introduccion concepto conceptos básico basico básicos basicos
básica basica creación creacion crear creando utilizando utilizar utiliza
contenido contenidos presenta presentan presentar aprende aprender guía guia
artículo articulo sección seccion capítulo capitulo siguiente siguientes
permite permiten través traves veremos vamos explica explicar muestra mostrar
principales principal general sencillo simple importante diferentes distintos
varios varias intento intenta desarrollar desarrollando desarrolla
implementar implementando implementa
""".split())

#: Ruido de foros y blogs técnicos: no son stopwords clásicas, pero aparecen
#: en casi todo el corpus (Stack Overflow / Medium) y no señalan categoría.
_RUIDO_TECNICO = frozenset("""
using use used uses also like make makes way want need needs see get got
know think thanks thank please help problem issue question answer example
following follow try trying tried work works working something anything
someone anyone one two three first second last next new old good bad best
better sure really actually maybe however instead since much many lot even
still already yet well great post article read look looking find found give
take put let say said seem seems come going go back time times thing things
part case point edit update note content http https www com org html
""".split())

#: Términos técnicos cortos que deben sobrevivir al filtro de longitud.
_TECNICOS_PROTEGIDOS = frozenset("""
js ts go ai ml ui ux qa db os io vm ci cd cs c# c++ r sql api rest xml css
html php aws gcp oci s3 ec2 k8s ssh ssl tls jwt orm mvc sdk cli gui ide npm
git vue npm dom rpc grpc dns cdn vpc iam
""".split())

def _sin_acentos(palabra: str) -> str:
    """Quita tildes conservando la ñ.

    El corpus viene parcialmente sin acentuar (se ve en las pruebas tipo
    jurado: "creacion", "basicos"), y la lista de stopwords tiene unas
    entradas con tilde y otras sin ella. Comparar en forma normalizada
    evita mantener las dos variantes de cada término. La ñ se preserva
    porque no es un acento: "año" y "ano" son palabras distintas.
    """
    protegida = palabra.replace("ñ", "\0")
    descompuesta = unicodedata.normalize("NFD", protegida)
    sin_marcas = "".join(c for c in descompuesta if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", sin_marcas).replace("\0", "ñ")


_STOP_ES_NORMALIZADO = frozenset(_sin_acentos(p) for p in _STOP_ES)



def _es_componente_util(palabra: str) -> bool:
    """Indica si una palabra aporta significado como parte de un término."""
    # El chequeo de técnicos va PRIMERO a propósito: "go" también está en
    # _RUIDO_TECNICO, y sin este orden el lenguaje Go quedaría filtrado.
    if palabra in _TECNICOS_PROTEGIDOS:
        return True
    if (
        _sin_acentos(palabra) in _STOP_ES_NORMALIZADO
        or palabra in ENGLISH_STOP_WORDS
        or palabra in _RUIDO_TECNICO
    ):
        return False
    return len(palabra) > 2


def es_termino_util(termino: str) -> bool:
    """Indica si un término (unigrama o bigrama) merece mostrarse al usuario.

    Se exige que TODOS los componentes aporten significado, no solo uno. Con
    un criterio laxo sobrevive "la creación" (porque "creación" pasa el
    filtro) y la lista vuelve a llenarse de relleno.

    Ejemplo:
        >>> es_termino_util("spring boot")
        True
        >>> es_termino_util("la creación")
        False
    """
    palabras = termino.split()
    return bool(palabras) and all(_es_componente_util(p) for p in palabras)


class ExtractorPalabrasClave(Protocol):
    """Contrato mínimo que cualquier extractor de palabras clave debe
    cumplir. Definirlo como Protocol (en vez de una clase base abstracta)
    permite sustituir la implementación (ej. por una basada en otro
    algoritmo) sin modificar quien la usa (ClasificadorContenido),
    siempre que respete esta firma - principio de sustitucion de Liskov
    aplicado a un lenguaje sin herencia obligatoria.
    """

    def extraer(
        self, texto_limpio: str, top_n: int, categoria: Optional[str] = None
    ) -> List[str]:
        """Extrae las top_n palabras clave más relevantes de un texto
        ya limpio. `categoria` es opcional: quien no la use sigue
        cumpliendo el contrato."""
        ...


class ExtractorPalabrasClaveTfidf:
    """Extrae palabras clave usando los pesos TF-IDF que el vectorizador
    le asigna al texto de entrada — los términos con mayor peso son los
    más "distintivos" para ese texto según el vocabulario del corpus de
    entrenamiento.
    """

    def __init__(self, vectorizador: TfidfVectorizer, clasificador=None) -> None:
        """
        Args:
            vectorizador: TfidfVectorizer ya entrenado (fit), normalmente
                el paso 'tfidf' del Pipeline serializado del modelo.
            clasificador: Estimador ya entrenado (paso 'clf' del Pipeline).
                Opcional. Si se pasa, las palabras clave se ponderan por el
                aporte de cada término a la categoría predicha, lo que hace
                que los términos devueltos EXPLIQUEN la clasificación en vez
                de solo describir el texto. Sin él, el extractor sigue
                funcionando con TF-IDF puro.
        """
        self._vectorizador = vectorizador
        self._clasificador = clasificador
        # Caché del vocabulario: get_feature_names_out() reconstruye y ordena
        # las 60.000 features en CADA llamada — medido, ~40 ms, frente a ~1 ms
        # de predict_proba. Como el vectorizador ya está ajustado y no cambia,
        # se calcula una sola vez por proceso.
        self._vocabulario = None
        self._clases = list(getattr(clasificador, "classes_", []))

    def _obtener_vocabulario(self):
        """Devuelve las features del vectorizador, calculadas una sola vez."""
        if self._vocabulario is None:
            self._vocabulario = self._vectorizador.get_feature_names_out()
        return self._vocabulario

    @staticmethod
    def _restaurar_capitalizacion(terminos: List[str], texto_original: str) -> List[str]:
        """Devuelve cada término con la grafía que tenía en el texto.

        El vectorizador trabaja en minúsculas, así que sus features salen
        como "spring boot". Para lo que ve el usuario final conviene
        devolver "Spring Boot": es el mismo dato, pero deja de parecer un
        volcado interno del modelo. Si un término no aparece literalmente,
        se devuelve tal cual.
        """
        resultado = []
        for termino in terminos:
            patron = re.compile(r"\b" + re.escape(termino) + r"\b", re.IGNORECASE)
            encontrado = patron.search(texto_original)
            resultado.append(encontrado.group(0) if encontrado else termino)
        return resultado

    def extraer(
        self, texto_limpio: str, top_n: int, categoria: Optional[str] = None
    ) -> List[str]:
        """Extrae las top_n palabras clave más relevantes del texto.

        Args:
            texto_limpio: Texto ya procesado por cleaning.preparar_entrada_modelo.
            top_n: Cantidad máxima de palabras clave a devolver.
            categoria: Categoría predicha. Si se indica y el extractor se
                construyó con un clasificador, cada término se pondera por
                su aporte a esa categoría:

                    relevancia = TF-IDF x (1 + max(0, coeficiente en la clase))

                Solo cuenta el aporte positivo: un coeficiente negativo
                significa que el término apunta a OTRA categoría y no debe
                presentarse como palabra clave de esta.

        Returns:
            Lista de términos (pueden incluir bigramas), ordenados de mayor
            a menor relevancia, con la capitalización del texto original.
            Lista vacía si ningún término del texto está en el vocabulario.
        """
        if not texto_limpio:
            return []

        # .tocsr() permite recorrer solo las posiciones con valor (~25 de
        # 60.000) en vez de densificar el vector completo con toarray().
        vector = self._vectorizador.transform([texto_limpio]).tocsr()
        if vector.nnz == 0:
            return []

        vocabulario = self._obtener_vocabulario()
        coeficientes = self._obtener_coeficientes(categoria)

        # indices y data son arreglos paralelos del CSR: la posición k de
        # data corresponde a la columna indices[k], no a la columna k.
        puntuados = []
        for indice, peso in zip(vector.indices, vector.data):
            termino = str(vocabulario[indice])
            if not es_termino_util(termino):
                continue
            relevancia = float(peso)
            if coeficientes is not None:
                relevancia *= 1.0 + max(0.0, float(coeficientes[indice]))
            puntuados.append((relevancia, termino))

        puntuados.sort(key=lambda par: -par[0])
        candidatos = [termino for _, termino in puntuados[: top_n * self._FACTOR_CANDIDATOS]]

        # Los n-gramas largos se evalúan primero para que "ganen" sobre sus
        # partes. Al ponderar por coeficiente de clase, "spring" y "boot"
        # puntúan alto por separado y el filtro de redundancia los tomaba
        # antes que "spring boot", devolviendo ['Spring', 'Boot'] en vez del
        # término que el usuario reconoce. El recorte por relevancia ya se
        # hizo arriba, así que aquí solo se reordena entre finalistas.
        candidatos.sort(key=lambda termino: -len(termino.split()))

        seleccionados = self._filtrar_redundantes(candidatos, top_n)
        return self._restaurar_capitalizacion(seleccionados, texto_limpio)

    def _obtener_coeficientes(self, categoria: Optional[str]):
        """Devuelve la fila de coeficientes de la categoría, o None."""
        if self._clasificador is None or categoria is None:
            return None
        if categoria not in self._clases:
            return None
        coef = getattr(self._clasificador, "coef_", None)
        if coef is None:
            return None
        return coef[self._clases.index(categoria)]

    # Se piden más candidatos de los necesarios porque el filtro de
    # redundancia descarta varios; con bigramas se descartan bastantes.
    # Se amplía desde 4: el filtro de stopwords descarta muchos más candidatos
    # ahora que el vocabulario del modelo incluye términos vacíos.
    _FACTOR_CANDIDATOS = 10

    @staticmethod
    def _filtrar_redundantes(candidatos: List[str], top_n: int) -> List[str]:
        """Descarta términos que no aportan ninguna palabra nueva.

        Con ngram_range=(1, 2) el vectorizador puntúa alto tanto al bigrama
        como a sus partes, así que la lista sale repetitiva: por ejemplo
        ["apis rest", "java spring", "spring boot", "boot", "spring"] son
        cinco términos que cubren solo cinco palabras distintas. "boot" y
        "spring" ya están contenidos en los bigramas anteriores y ocupan
        lugares que podrían llevar información nueva.

        Se conserva el orden por peso: un término entra si aporta al menos
        una palabra que ningún término ya aceptado contenía.
        """
        seleccionados: List[str] = []
        palabras_cubiertas: set = set()

        for termino in candidatos:
            palabras = set(termino.split())
            if palabras - palabras_cubiertas:
                seleccionados.append(termino)
                palabras_cubiertas |= palabras
            if len(seleccionados) == top_n:
                break

        return seleccionados
