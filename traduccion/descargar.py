# -*- coding: utf-8 -*-
"""Trae los modelos de traducción entre español e inglés.

    python traduccion/descargar.py            # solo en-es, que es lo que usa
    python traduccion/descargar.py --ambas    # las dos direcciones

Por defecto baja una sola dirección: el botón «Ver en español» traduce el
material del histórico, que es inglés, y no hay nada más que traduzca. La
otra son 171 MB de disco y 292 MB de memoria sin nadie que los pida.

Eso importa acá. Medido con todo cargado en la instancia de 2 GB:

    la API mas el clasificador       243 MB
    + la busqueda semantica          724 MB
    + el traductor en-es           1.031 MB
    + el traductor es-en           1.322 MB

La última fila deja unos 700 MB para el sistema operativo y Caddy. Entra,
pero sin margen para nada, y a cambio de una dirección que no se usa.

No se versionan. El servicio los usa si están; si no, el endpoint responde
503 explicando qué falta y el resto de la API funciona igual.

QUÉ MODELO

`opus-mt` de Helsinki, en la exportación ONNX de Xenova, cuantizado a int8:
171 MB por dirección en lugar de los ~300 del original.

Se eligió un modelo local y no un servicio de traducción porque un servicio
externo agrega una clave, una factura y un punto de falla que no se
controla. Cuesta 79 ms por texto, decodificando sobre onnxruntime.

POR QUÉ HACE FALTA

Medido sobre el corpus: el 95,9 % está en inglés y la interfaz en español.
Hay temas donde eso deja al usuario leyendo en un idioma que no eligió
—Mobile tiene 55 documentos en castellano de 5.048—. El botón «Ver en
español» sobre los resultados es para eso, y es lo único que traduce: la
clasificación no pasa por acá.
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
    ambas = "--ambas" in sys.argv
    pedidas = DIRECCIONES if ambas else {"en-es": DIRECCIONES["en-es"]}
    if not ambas:
        print("Solo en-es, que es la direccion que usa el boton.")
        print("Para las dos: python traduccion/descargar.py --ambas\n")

    total = 0
    for direccion, repo in pedidas.items():
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
