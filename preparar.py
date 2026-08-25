"""Coloca los artefactos donde el backend los busca.

Los cuatro archivos viven en modelos/ y la API los espera en
backend/app/ml/. En vez de duplicarlos en el control de versiones, se
copian al preparar el entorno.

    python preparar.py
"""

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ORIGEN = RAIZ / "modelos"
DESTINO = RAIZ / "backend" / "app" / "ml"

ARTEFACTOS = (
    "modelo_techmind_v2.joblib",
    "matriz_historica.pkl",
    "sugerencias_botones.json",
)


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    faltantes = []

    for nombre in ARTEFACTOS:
        origen = ORIGEN / nombre
        if not origen.exists():
            faltantes.append(nombre)
            continue
        shutil.copy2(origen, DESTINO / nombre)
        print(f"  {nombre:32} {origen.stat().st_size / 1048576:6.1f} MB")

    if faltantes:
        print("\nNo se encontraron en modelos/:", ", ".join(faltantes))
        return 1

    print(f"\nListos en {DESTINO}")
    print("Ahora:  cd backend  &&  python -m uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
