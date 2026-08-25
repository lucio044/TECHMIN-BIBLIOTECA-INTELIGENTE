# -*- coding: utf-8 -*-
"""Arma la muestra que usa la pestaña de categorías propias.

    python dataset/preparar_muestra.py

La taxonomía no está inventada: sale de la columna `fuente` del corpus.
StackOverflow son preguntas de alguien que está atascado; Medium son
artículos escritos para explicar algo. Es una distinción de formato, no de
tema.

Lo importante es que sea ortogonal a las 8 categorías de fábrica: las dos
fuentes cubren las 8 por igual, así que ningún reagrupamiento de las
etiquetas de fábrica puede producir esta. Eso es lo que la hace un caso
legítimo para mostrar el entrenamiento con categorías propias, en vez de
fusionar categorías existentes, que se resolvería con una tabla de
equivalencias y sin modelo.

Se usan solo las dos fuentes en inglés. Sumar las fuentes en español
(freecodecamp_es, wikipedia_es, corpus_es_*) dejaría que el modelo acierte
mirando el idioma en lugar del tipo de texto, y el número saldría inflado.
"""
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
ORIGEN = AQUI / "techmind_dataset_v2.csv"
DESTINO = AQUI / "muestra_tipo_contenido.csv"

POR_CLASE = 300
PALABRAS_MAX = 120
PALABRAS_MIN = 25
SEMILLA = 42

ETIQUETAS = {"stackoverflow": "Pregunta", "medium": "Artículo"}


def main() -> int:
    if not ORIGEN.exists():
        print(f"Falta {ORIGEN.name}. Descargarlo con el enlace del README de esta carpeta.")
        return 1

    df = pd.read_csv(ORIGEN)
    df = df[df["fuente"].isin(ETIQUETAS)].copy()
    df["tipo"] = df["fuente"].map(ETIQUETAS)

    # Los textos de Medium llegan a 33.000 palabras. Se recortan a algo que
    # tenga sentido mandar por la red desde el navegador.
    df["texto"] = df["texto"].astype(str).str.split().str[:PALABRAS_MAX].str.join(" ")
    df = df[df["texto"].str.split().str.len() >= PALABRAS_MIN]

    # Estratificado por tipo Y por categoría. Sin esto, si una clase quedara
    # cargada de textos de Frontend, el modelo aprendería el tema en vez del
    # formato y el F1 mentiría.
    partes = []
    for _, g in df.groupby("tipo"):
        por_categoria = max(1, POR_CLASE // g["categoria"].nunique())
        partes.append(
            g.groupby("categoria", group_keys=False)[g.columns]
             .apply(lambda x: x.sample(min(len(x), por_categoria), random_state=SEMILLA))
        )

    muestra = (pd.concat(partes)
                 .sample(frac=1, random_state=SEMILLA)
                 .reset_index(drop=True))

    salida = muestra[["titulo", "texto", "tipo"]].rename(columns={"tipo": "categoria"})
    salida.to_csv(DESTINO, index=False, encoding="utf-8")

    print(f"{DESTINO.name}: {len(salida)} filas · {DESTINO.stat().st_size / 1024:.0f} KB")
    print(muestra.groupby(["tipo", "categoria"]).size().unstack(fill_value=0).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
