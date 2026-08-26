# -*- coding: utf-8 -*-
"""Arma el almacén de texto que usa el sintetizador de respuestas.

    python semantica/generar_pasajes.py

La matriz histórica guarda un extracto de 199 caracteres por documento, que
alcanza para mostrar una tarjeta pero no para responder nada: el 99 % queda
cortado a mitad de frase. Este script recupera el texto completo del dataset
y lo deja disponible, recortado a 800 caracteres.

POR QUÉ 800

Es lo que entra en dos o tres párrafos, que es la unidad con la que se
responde. Guardar el texto completo serían 76 MB; a 800 caracteres son unos
21, y lo que se pierde es la cola de artículos largos, que casi nunca
aporta a una respuesta puntual.

EL EMPAREJAMIENTO

Los identificadores de la matriz no corresponden a las filas del dataset
--se descartaron filas en la limpieza-- así que hay que emparejar por
título. Comparándolos tal cual coinciden el 49 %: la matriz les quitó la
puntuación, y «Apache Cordova (Wikipedia, parte 2)» quedó como «Apache
Cordova Wikipedia parte 2». Normalizando acentos y signos, coinciden el
91 %, y el 99 % de los documentos explicativos, que son los que responden.

Los que no emparejan quedan con el extracto corto, y el sintetizador
simplemente no los elige.
"""
import re
import sys
import unicodedata
from pathlib import Path

import joblib
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
MATRIZ = RAIZ / "modelos" / "matriz_historica.pkl"
ORIGEN = RAIZ / "dataset" / "techmind_dataset_v2.csv"
DESTINO = RAIZ / "modelos" / "pasajes.pkl"

TOPE = 800


def normalizar(titulo: str) -> str:
    """Quita acentos y signos, que es donde difieren las dos fuentes."""
    t = unicodedata.normalize("NFKD", str(titulo))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", t)).strip().lower()


def recortar(texto: str, tope: int = TOPE) -> str:
    """Corta en el último punto o espacio, para no dejar palabras partidas."""
    t = re.sub(r"\s+", " ", str(texto)).strip()
    if len(t) <= tope:
        return t
    trozo = t[:tope]
    corte = max(trozo.rfind(". "), trozo.rfind("? "), trozo.rfind("! "))
    if corte > tope * 0.6:
        return trozo[:corte + 1]
    corte = trozo.rfind(" ")
    return (trozo[:corte] if corte > 0 else trozo) + "…"


def main() -> int:
    for ruta in (MATRIZ, ORIGEN):
        if not ruta.exists():
            print(f"Falta {ruta}")
            if ruta is ORIGEN:
                print("Descargarlo con el enlace del README de dataset/")
            return 1

    paquete = joblib.load(MATRIZ)
    titulos = [str(t) for t in paquete["titulos"]]

    df = pd.read_csv(ORIGEN)
    por_titulo = {}
    for i, t in enumerate(df["titulo"]):
        por_titulo.setdefault(normalizar(t), i)

    textos, emparejados = [], 0
    for t in titulos:
        j = por_titulo.get(normalizar(t))
        if j is None:
            textos.append("")
            continue
        textos.append(recortar(df.iloc[j]["texto"]))
        emparejados += 1

    joblib.dump(textos, DESTINO, compress=3)

    largos = [len(t) for t in textos if t]
    print(f"{DESTINO.name}: {DESTINO.stat().st_size / 1048576:.1f} MB")
    print(f"  {emparejados:,} de {len(titulos):,} documentos con texto  ({emparejados/len(titulos):.0%})")
    print(f"  largo medio: {sum(largos)/len(largos):.0f} caracteres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
