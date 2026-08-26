# -*- coding: utf-8 -*-
"""Trae los modelos de traducción entre español e inglés.

    python traduccion/descargar.py

Son 342 MB entre las dos direcciones y no se versionan. El servicio los usa
si están; si no, el endpoint responde 503 explicando que faltan y el resto
de la API funciona igual.

QUÉ MODELO

`opus-mt` de Helsinki, en la exportación ONNX de Xenova, cuantizado a int8:
171 MB por dirección en lugar de los ~300 del original.

Se eligió un modelo local y no un servicio de traducción porque un servicio
externo agrega una clave, una factura y un punto de falla que no se
controla. Lo que cuesta es tiempo: alrededor de segundo y medio por texto.

POR QUÉ HACE FALTA

Medido sobre el corpus: el 95,9 % está en inglés y la interfaz en español.
Hay temas donde eso deja al usuario sin material —Mobile tiene 55
documentos en castellano de 5.048— y además el clasificador pierde
precisión con texto en español, porque aprendió de un corpus que casi no lo
tiene.
"""
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent

DIRECCIONES = {
    "es-en": "https://huggingface.co/Xenova/opus-mt-es-en/resolve/main/",
    "en-es": "https://huggingface.co/Xenova/opus-mt-en-es/resolve/main/",
}

ARCHIVOS = [
    "onnx/encoder_model_quantized.onnx",
    "onnx/decoder_model_quantized.onnx",
    "onnx/decoder_with_past_model_quantized.onnx",
    "tokenizer.json",
    "tokenizer_config.json",
    "config.json",
    "generation_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "source.spm",
    "target.spm",
]

REINTENTOS = 5


def bajar(url: str, destino: Path) -> bool:
    """Con reintentos: Hugging Face responde 429 si se le pide muy seguido."""
    for intento in range(REINTENTOS):
        try:
            urllib.request.urlretrieve(url, destino)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < REINTENTOS - 1:
                time.sleep(20 * (intento + 1))
                continue
            print(f"    {e}")
            return False
        except Exception as e:
            if intento < REINTENTOS - 1:
                time.sleep(10)
                continue
            print(f"    {e}")
            return False
    return False


def main() -> int:
    total = 0
    for direccion, repo in DIRECCIONES.items():
        print(f"{direccion}:")
        (AQUI / direccion / "onnx").mkdir(parents=True, exist_ok=True)
        for archivo in ARCHIVOS:
            destino = AQUI / direccion / archivo
            if destino.exists():
                total += destino.stat().st_size
                continue
            print(f"  {archivo}", flush=True)
            if not bajar(repo + archivo, destino):
                print(f"  no se pudo traer {archivo}")
                return 1
            total += destino.stat().st_size

    print(f"\n{total / 1048576:.0f} MB en {AQUI}")
    print("El servicio los carga en el primer uso, no al arrancar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
