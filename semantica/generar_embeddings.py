# -*- coding: utf-8 -*-
"""Vectoriza el histórico para la búsqueda semántica.

    python semantica/generar_embeddings.py

Se ejecuta una vez, o cada vez que cambie la matriz histórica. Tarda unos
20 minutos sobre los 38.257 documentos y produce `modelos/embeddings.npy`.

POR QUÉ HACE FALTA, SI YA HAY BÚSQUEDA POR SIMILITUD

La que ya existe compara palabras: encuentra un documento si comparte
términos con la consulta. Sobre este corpus eso deja fuera un caso
frecuente, porque el 95,9 % de los documentos está en inglés y la interfaz
está en español. Quien escribe «cómo protejo las contraseñas» no tiene con
qué emparejarse contra un documento que dice *password hashing*.

Se probó antes la vía barata —LSA sobre la matriz TF-IDF que ya existía— y
no sirve: su dimensión dominante separa idiomas, no temas. Una consulta en
español devolvía el 100 % de resultados en español cuando el corpus tiene
apenas 2,7 %, y como esos documentos están sesgados a Seguridad, todo caía
ahí sin importar de qué hablara la consulta.

Este modelo sí cruza los dos idiomas. Medido sobre pares equivalentes:

    «cómo protejo las contraseñas»  ↔  how to hash passwords      0,747
    «guardar datos de forma permanente»  ↔  persist data          0,749
    «cómo protejo las contraseñas»  ↔  recipe for tomato soup    -0,146

QUÉ SE VECTORIZA

El título más el extracto que ya guarda la matriz histórica. No se usa el
texto completo del dataset porque los identificadores de la matriz no
mapean contra el CSV crudo --se descartaron filas en la limpieza-- y
emparejar por título solo funciona en la mitad de los casos. Título más
extracto son unos 260 caracteres, que es lo que el usuario ve en pantalla
y entra holgado en la ventana de 128 tokens del modelo.
"""
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
MATRIZ = RAIZ / "modelos" / "matriz_historica.pkl"
DESTINO = RAIZ / "modelos" / "embeddings.npy"
MODELO = AQUI / "modelo" / "modelo.onnx"
TOKENIZADOR = AQUI / "modelo" / "tokenizer.json"

LOTE = 16
HEBRAS = max(1, (os.cpu_count() or 2) - 1)


def main() -> int:
    for ruta in (MATRIZ, MODELO, TOKENIZADOR):
        if not ruta.exists():
            print(f"Falta {ruta}")
            if ruta in (MODELO, TOKENIZADOR):
                print("Descargarlo con: python semantica/descargar_modelo.py")
            return 1

    sys.path.insert(0, str(AQUI))
    from codificador import Codificador

    paquete = joblib.load(MATRIZ)
    titulos, extractos = paquete["titulos"], paquete["extractos"]
    textos = [f"{t}. {e}" for t, e in zip(titulos, extractos)]
    print(f"{len(textos):,} documentos")

    codificador = Codificador(str(MODELO), str(TOKENIZADOR), hebras=HEBRAS)
    print(f"modelo cargado · {HEBRAS} hebras\n")

    t0 = time.time()
    partes = []
    for i in range(0, len(textos), 512):
        partes.append(codificador(textos[i:i + 512], lote=LOTE))
        hechos = min(i + 512, len(textos))
        transcurrido = time.time() - t0
        resta = transcurrido / hechos * (len(textos) - hechos)
        print(f"  {hechos:>6,}/{len(textos):,}  "
              f"{transcurrido/60:5.1f} min transcurridos · faltan {resta/60:4.1f}",
              flush=True)

    vectores = np.vstack(partes)

    # Se guardan en float16: la mitad de espacio y una diferencia en el
    # coseno del orden de 1e-3, que no altera el orden de los resultados.
    np.save(DESTINO, vectores.astype(np.float16))

    print(f"\n{DESTINO.name}: {vectores.shape} · "
          f"{DESTINO.stat().st_size/1048576:.0f} MB · {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
