"""
Extracción de palabras clave a partir de los pesos TF-IDF del propio
vectorizador ya entrenado.
"""

import re
import unicodedata
from typing import List, Optional, Protocol

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

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

_TECNICOS_PROTEGIDOS = frozenset("""
js ts go ai ml ui ux qa db os io vm ci cd cs c# c++ r sql api rest xml css
html php aws gcp oci s3 ec2 k8s ssh ssl tls jwt orm mvc sdk cli gui ide npm
git vue npm dom rpc grpc dns cdn vpc iam
""".split())


def _sin_acentos(palabra: str) -> str:
    protegida = palabra.replace("ñ", "\0")
    descompuesta = unicodedata.normalize("NFD", protegida)
    sin_marcas = "".join(c for c in descompuesta if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", sin_marcas).replace("\0", "ñ")


_STOP_ES_NORMALIZADO = frozenset(_sin_acentos(p) for p in _STOP_ES)


def _es_componente_util(palabra: str) -> bool:
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
    palabras = termino.split()
    return bool(palabras) and all(_es_componente_util(p) for p in palabras)


class ExtractorPalabrasClave(Protocol):
    def extraer(
        self, texto_limpio: str, top_n: int, categoria: Optional[str] = None
    ) -> List[str]:
        ...


class ExtractorPalabrasClaveTfidf:
    def __init__(self, vectorizador: TfidfVectorizer, clasificador=None) -> None:
        self._vectorizador = vectorizador
        self._clasificador = clasificador
        self._vocabulario = None
        self._clases = list(getattr(clasificador, "classes_", []))

    def _obtener_vocabulario(self):
        if self._vocabulario is None:
            self._vocabulario = self._vectorizador.get_feature_names_out()
        return self._vocabulario

    @staticmethod
    def _restaurar_capitalizacion(terminos: List[str], texto_original: str) -> List[str]:
        resultado = []
        for termino in terminos:
            patron = re.compile(r"\b" + re.escape(termino) + r"\b", re.IGNORECASE)
            encontrado = patron.search(texto_original)
            resultado.append(encontrado.group(0) if encontrado else termino)
        return resultado

    def extraer(
        self, texto_limpio: str, top_n: int, categoria: Optional[str] = None
    ) -> List[str]:
        if not texto_limpio:
            return []

        vector = self._vectorizador.transform([texto_limpio]).tocsr()
        if vector.nnz == 0:
            return []

        vocabulario = self._obtener_vocabulario()
        coeficientes = self._obtener_coeficientes(categoria)

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

        candidatos.sort(key=lambda termino: -len(termino.split()))

        seleccionados = self._filtrar_redundantes(candidatos, top_n)
        return self._restaurar_capitalizacion(seleccionados, texto_limpio)

    def _obtener_coeficientes(self, categoria: Optional[str]):
        if self._clasificador is None or categoria is None:
            return None
        if categoria not in self._clases:
            return None
        coef = getattr(self._clasificador, "coef_", None)
        if coef is None:
            return None
        return coef[self._clases.index(categoria)]

    _FACTOR_CANDIDATOS = 10

    @staticmethod
    def _filtrar_redundantes(candidatos: List[str], top_n: int) -> List[str]:
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