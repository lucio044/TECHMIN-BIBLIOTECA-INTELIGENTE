"""Por que el modelo decidio lo que decidio.

La regresion logistica no es una caja negra: la probabilidad de cada
categoria sale de sumar el peso de cada termino del texto. Multiplicar el
vector TF-IDF del documento por los coeficientes de la clase ganadora da,
termino por termino, cuanto empujo cada uno.

Eso es una explicacion calculada, no redactada. Sirve para dos cosas:

  - Alimentar al asistente con evidencia concreta en vez de pedirle que
    invente un motivo a partir de la categoria.
  - Responder igual de bien cuando no hay clave de un proveedor externo,
    que es la situacion normal en el plan gratuito.
"""

import logging
import re
from typing import List, Tuple

from app.ml.loader import cargar_modelo

logger = logging.getLogger(__name__)

# Un termino que aporta menos que esto no dice nada. El corte se busco
# midiendo: por debajo de 0,15 se cuelan preposiciones --«sobre», «un
# poco»-- y un texto ajeno al corpus termina con un motivo inventado; por
# encima de 0,30 se pierden terminos legitimos como «tablas» o «indices».
APORTE_MINIMO = 0.15

# Terminos que nunca deberian presentarse como el motivo de una decision,
# aunque el modelo les haya dado peso. Son palabras de funcion: si aparecen
# arriba, lo que hay que arreglar es el modelo, no la explicacion.
SIN_CONTENIDO = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o",
    "en", "con", "por", "para", "del", "al", "que", "se", "su", "sus", "lo",
    "es", "como", "the", "of", "to", "and", "in", "for", "on", "is", "it",
    "this", "that", "with", "as", "be", "are", "from", "at", "an", "by",
}


def _es_util(termino: str) -> bool:
    partes = termino.split()
    if all(p in SIN_CONTENIDO for p in partes):
        return False
    return bool(re.search(r"[a-z0-9]", termino))


def terminos_decisivos(texto: str, cuantos: int = 6) -> Tuple[str, float, List[dict]]:
    """Devuelve la categoria, su probabilidad y que empujo hacia ella.

    El aporte de cada termino es su valor TF-IDF por el coeficiente que la
    clase ganadora le asigna. Positivo empuja hacia la categoria, negativo
    en contra; aca solo interesan los que empujaron a favor.
    """
    modelo = cargar_modelo()
    if modelo is None:
        return "", 0.0, []

    vectorizador = modelo.named_steps["tfidf"]
    clasificador = modelo.named_steps["clf"]

    x = vectorizador.transform([texto])
    probabilidades = clasificador.predict_proba(x)[0]
    ganadora = int(probabilidades.argmax())

    aportes = x.multiply(clasificador.coef_[ganadora]).tocoo()
    nombres = vectorizador.get_feature_names_out()

    ordenados = sorted(zip(aportes.col, aportes.data), key=lambda par: -par[1])
    utiles = []
    for col, valor in ordenados:
        if valor < APORTE_MINIMO or not _es_util(str(nombres[col])):
            continue
        utiles.append({
            "termino": str(nombres[col]),
            "aporte": round(float(valor), 4),
            # Un termino solo sostiene la decision si la categoria ganadora
            # es tambien la que mas peso le da a el. «backend», por ejemplo,
            # pesa +1,38 en Seguridad y +1,17 en Frontend: aparece en las
            # dos por igual, asi que no inclina nada aunque su aporte sea
            # alto. Presentarlo como el motivo es lo que hace que una
            # respuesta se lea como un disparate.
            "sostiene": bool(int(clasificador.coef_[:, col].argmax()) == ganadora),
        })
        if len(utiles) >= cuantos:
            break

    return str(clasificador.classes_[ganadora]), float(probabilidades[ganadora]), utiles


def _enumerar(cosas: List[str]) -> str:
    if len(cosas) == 1:
        return cosas[0]
    return ", ".join(cosas[:-1]) + " y " + cosas[-1]


def redactar(texto: str, resultado, del_historico=None) -> str:
    """Arma una explicacion en prosa a partir de lo que el modelo calculo.

    No hay ningun proveedor externo detras: todo lo que dice sale del
    modelo, del ranking y del historico. Por eso nunca falla y nunca puede
    inventar nada que el sistema no sepa.

    Cuando el historico tiene material sobre la pregunta, eso pasa primero:
    quien pregunta «que es una base de datos relacional» quiere la
    respuesta, no en que categoria cae su pregunta.
    """
    if del_historico:
        partes = len(del_historico["fragmentos"])
        cabeza = (
            f"Segun **{del_historico['fuente']}**, del historico"
            f"{' (' + str(partes) + ' fragmentos)' if partes > 1 else ''}:"
        )
        cuerpo = " ".join(f["texto"] for f in del_historico["fragmentos"])
        # Se recorta para la prosa; los fragmentos completos viajan aparte
        # en la respuesta, para que el cliente los muestre enteros.
        if len(cuerpo) > 900:
            cuerpo = cuerpo[:900].rsplit(" ", 1)[0] + "…"
        cola = (
            f" Se compararon {del_historico['documentos_consultados']:,} documentos "
            f"y este fue el mas cercano ({del_historico['parecido']:.2f})."
        ).replace(",", ".")
        return f"{cabeza} {cuerpo}{cola}"

    _, _, terminos = terminos_decisivos(texto)

    categoria = resultado.categoria
    confianza = resultado.probabilidad

    if confianza >= 0.75:
        arranque = f"Esto es **{categoria}**, y el modelo lo tiene claro: {confianza:.0%} de confianza."
    elif confianza >= 0.45:
        arranque = f"Esto encaja en **{categoria}**, con {confianza:.0%} de confianza."
    else:
        arranque = (
            f"Lo mas parecido es **{categoria}**, pero con {confianza:.0%} de confianza "
            f"esto no alcanza para clasificar nada: hace falta mas texto."
        )

    partes = [arranque]

    sostienen = [t for t in terminos if t["sostiene"]]
    ambiguos = [t for t in terminos if not t["sostiene"]]

    if sostienen:
        listado = _enumerar([f"«{t['termino']}»" for t in sostienen[:4]])
        partes.append(f"Lo que mas peso fue {listado}.")
    elif ambiguos:
        # Hay terminos con peso, pero ninguno apunta a la categoria que
        # gano: son palabras que el corpus reparte entre varias. Decir «lo
        # que mas peso fue X» cuando X pesa mas en otra categoria es lo que
        # convierte la respuesta en un disparate aparente.
        pocos = ambiguos[:3]
        listado = _enumerar([f"«{t['termino']}»" for t in pocos])
        if len(pocos) > 1:
            partes.append(f"Ningun termino sostiene esa categoria: {listado} "
                          f"aparecen repartidos entre varias, asi que no inclinan la decision.")
        else:
            partes.append(f"Ningun termino sostiene esa categoria: {listado} "
                          f"aparece repartido entre varias, asi que no inclina la decision.")
    else:
        partes.append(
            "No hay en el texto ningun termino con peso suficiente para "
            "decidir; el modelo esta eligiendo casi a ciegas."
        )

    otras = getattr(resultado, "ranking_categorias", None) or []
    if otras:
        rivales = _enumerar([f"{o.categoria} ({o.probabilidad:.0%})" for o in otras[:2]])
        # Si la segunda esta pegada, decir que quedo "bastante atras" seria
        # falso, y ademas esconderia justo el caso que conviene mirar.
        pegada = (confianza - otras[0].probabilidad) < 0.15
        partes.append(
            f"La sigue de cerca {rivales}." if pegada
            else f"Las siguientes candidatas quedaron bastante atras: {rivales}."
        )

    relacionados = getattr(resultado, "contenidos_relacionados", None) or []
    if relacionados:
        primero = relacionados[0]
        cuantos = len(relacionados)
        partes.append(
            (f"En el historico hay un documento parecido: " if cuantos == 1
             else f"En el historico hay {cuantos} documentos parecidos; el mas cercano es ") +
            f"«{primero.titulo}», con una similitud de {primero.similitud:.2f}."
        )
    else:
        partes.append(
            "En el historico no aparecio ningun documento parecido por encima del "
            "umbral de similitud."
        )

    return " ".join(partes)
