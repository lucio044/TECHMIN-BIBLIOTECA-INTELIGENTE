"""Responde una pregunta con lo que dice el histórico.

No genera texto. Busca por significado entre los 38.257 documentos, reúne
los fragmentos que salieron del mismo original, los ordena por su número de
parte y devuelve lo que dicen. Cada frase de la respuesta está en un
documento que existe.

POR QUÉ ASÍ Y NO CON UN MODELO DE LENGUAJE

Un modelo generativo redacta mejor, pero puede afirmar cosas que el corpus
no dice, y desde afuera no hay forma de distinguir una de otra. Acá la
respuesta *es* el corpus: se puede ir al documento y comprobar cada línea.

Lo que se pierde es fluidez. La respuesta se lee como una cita larga, no
como una explicación escrita para la pregunta. Es un intercambio
deliberado, y por eso la respuesta viene siempre con su fuente al lado.

LO QUE HIZO POSIBLE ARMARLA

Los artículos del corpus están partidos en fragmentos numerados --«Base de
datos relacional Wikipedia parte 1, 2, 4, 5»--. Reunir los del mismo
original y ordenarlos por su número devuelve un texto coherente, que es
justo lo que un fragmento suelto no da.
"""

import logging
import re
from typing import List, Optional

from app.ml import semantico

logger = logging.getLogger(__name__)

# Por debajo de esto, lo mas parecido del historico no habla del tema.
UMBRAL = 0.48

# Y ademas hacen falta al menos dos fragmentos del mismo documento.
#
# El parecido solo no alcanza para decidir: medido sobre once preguntas, las
# que el corpus si podia responder puntuaban entre 0,55 y 0,76, y las que no
# entre 0,35 y 0,57. Se solapan, asi que ninguna linea las separa.
#
# La cuenta de fragmentos si las separa, y limpio:
#
#     deberia responder    3 a 8 fragmentos del mismo documento
#     no deberia           1, en los cinco casos
#
# El motivo es que son corroboraciones independientes: que cuatro partes de
# un mismo articulo aparezcan por separado entre las mas parecidas dice que
# el articulo trata el tema. Un documento suelto que puntua 0,57 puede ser
# una casualidad, y afirmar «segun X» sobre esa base es peor que no
# responder.
MIN_FRAGMENTOS = 2

# Cuantos documentos se miran antes de agrupar. Con menos, las partes de un
# mismo articulo no llegan a juntarse; con muchos mas, se cuelan documentos
# que ya no vienen al caso y solo cuesta tiempo.
CANDIDATOS = 40

# «Base de datos relacional Wikipedia parte 4» -> («Base de datos relacional», 4)
# «Ciberseg Cisco fragmento p. 72»             -> («Ciberseg Cisco», 72)
_PARTE = re.compile(
    r"^(.*?)\s*(?:\(?Wikipedia\)?\s*)?(?:,\s*)?(?:parte|fragmento\s*p\.?)\s*(\d+)\s*$",
    re.IGNORECASE,
)


def _raiz_y_parte(titulo: str):
    m = _PARTE.match(titulo)
    if m and m.group(1).strip():
        return m.group(1).strip(), int(m.group(2))
    return titulo, 0


def responder(pregunta: str, fragmentos: int = 4) -> Optional[dict]:
    """Arma una respuesta, o None si el histórico no tiene nada del tema."""
    buscador = semantico.cargar_buscador()
    if buscador is None or not buscador.hay_pasajes:
        return None

    candidatos = buscador.candidatos(pregunta, CANDIDATOS)
    if not candidatos:
        return None

    # Se agrupa por documento de origen: cuatro partes de un mismo articulo
    # explican mucho mas que cuatro documentos distintos sobre lo mismo.
    grupos = {}
    for indice, parecido in candidatos:
        doc = buscador.documento(indice)
        if not doc["texto"]:
            continue
        raiz, parte = _raiz_y_parte(doc["titulo"])
        grupo = grupos.setdefault(raiz, {"partes": [], "mejor": 0.0,
                                         "categoria": doc["categoria"]})
        grupo["partes"].append({"parte": parte, "texto": doc["texto"],
                                "parecido": round(parecido, 3)})
        grupo["mejor"] = max(grupo["mejor"], parecido)

    if not grupos:
        return None

    # Se ordena por parecido pero solo entre los que tienen corroboracion.
    con_respaldo = {r: g for r, g in grupos.items()
                    if len(g["partes"]) >= MIN_FRAGMENTOS and g["mejor"] >= UMBRAL}
    if not con_respaldo:
        return None

    ordenados = sorted(con_respaldo.items(), key=lambda kv: -kv[1]["mejor"])
    raiz, grupo = ordenados[0]

    # Por numero de parte, no por parecido: asi el texto se lee en el orden
    # en que fue escrito.
    partes = sorted(grupo["partes"], key=lambda p: p["parte"])[:fragmentos]

    return {
        "pregunta": pregunta,
        "fuente": raiz,
        "categoria": grupo["categoria"],
        "parecido": round(grupo["mejor"], 3),
        "fragmentos": partes,
        "otras_fuentes": [r for r, _ in ordenados[1:4]],
        "documentos_consultados": buscador.total_documentos,
    }
