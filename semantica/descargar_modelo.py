# -*- coding: utf-8 -*-
"""Trae el modelo de embeddings.

    python semantica/descargar_modelo.py

Son 122 MB que no se versionan en el repositorio. El servicio lo descarga
solo al desplegarse; esto es para tenerlo en local.

QUÉ MODELO Y POR QUÉ

`paraphrase-multilingual-MiniLM-L12-v2`, en su variante ONNX cuantizada a
uint8: 113 MB en lugar de los 470 del original en float32.

Se eligió ONNX y no `sentence-transformers` porque esa librería arrastra
torch, que son unos 800 MB instalados y varios cientos de MB en memoria.
No entra junto al resto en una instancia de 2 GB. Con `onnxruntime` el
modelo ocupa unos 130 MB al cargarse y codifica una consulta en 6 ms.

Se eligió la variante multilingüe porque el corpus está en inglés al
95,9 % y la interfaz en español: sin eso, la búsqueda semántica no cruzaría
los dos idiomas, que es justamente el caso que hay que resolver.
"""
import time
import urllib.request
from pathlib import Path

REPO = ("https://huggingface.co/sentence-transformers/"
        "paraphrase-multilingual-MiniLM-L12-v2/resolve/main/")

DESTINO = Path(__file__).resolve().parent / "modelo"

ARCHIVOS = {
    "onnx/model_quint8_avx2.onnx": "modelo.onnx",
    "tokenizer.json": "tokenizer.json",
    "config.json": "config.json",
}


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for remoto, local in ARCHIVOS.items():
        ruta = DESTINO / local
        if ruta.exists():
            print(f"  ya está: {local} ({ruta.stat().st_size/1048576:.1f} MB)")
            continue
        t0 = time.time()
        print(f"  bajando {local}…", flush=True)
        urllib.request.urlretrieve(REPO + remoto, ruta)
        print(f"  {local:<20} {ruta.stat().st_size/1048576:7.1f} MB   {time.time()-t0:.0f}s")
    print(f"\nen {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
