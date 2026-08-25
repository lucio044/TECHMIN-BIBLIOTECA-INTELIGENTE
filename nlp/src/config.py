"""
Configuración centralizada del pipeline: rutas y umbrales.

Concentrar estos valores aquí (en vez de tenerlos repartidos como
literales dentro de la lógica de negocio) es lo que permite ajustarlos
sin tocar código, y evita que el mismo número aparezca "mágicamente"
en varios archivos a la vez.
"""

import os
from pathlib import Path

# Raíz del módulo, calculada a partir de la ubicación de este archivo
# (src/config.py -> src/ -> raíz). Anclar las rutas aquí, en vez de usar
# rutas relativas al directorio de trabajo, evita que el modelo "desaparezca"
# cuando la API se levanta desde otra carpeta (ej. `uvicorn` lanzado desde
# el directorio del backend, o un contenedor con otro WORKDIR).
RAIZ_PROYECTO: Path = Path(__file__).resolve().parent.parent

# El módulo se usa en dos disposiciones distintas: dentro del repositorio los
# artefactos están en `nlp/models/`, y en la carpeta de entrega están en
# `modelos/`, junto a los notebooks que los generan. Se prueba una y después
# la otra, en vez de fijar una sola, para que el mismo código sirva en las dos
# sin que nadie tenga que acordarse de cambiar esta línea al mover archivos.
_UBICACIONES = (
    RAIZ_PROYECTO / "models",
    RAIZ_PROYECTO.parent / "modelos",
)


def _resolver_dir_modelos() -> Path:
    """Devuelve el directorio de artefactos que se va a usar.

    `TECHMIND_MODELOS` tiene prioridad y se respeta aunque no exista: en
    producción el backend descarga los archivos de Object Storage a ese
    directorio, y puede hacerlo después de que este módulo se importe.

    Si ninguna ubicación conocida existe se devuelve la primera igual, para
    que el error mencione una ruta concreta en lugar de fallar acá.
    """
    configurado = os.environ.get("TECHMIND_MODELOS")
    if configurado:
        return Path(configurado)
    return next((d for d in _UBICACIONES if d.is_dir()), _UBICACIONES[0])


DIR_MODELOS: Path = _resolver_dir_modelos()

# Pipeline serializado: TF-IDF + clasificador en un solo objeto.
MODELO_PATH: Path = DIR_MODELOS / "modelo_techmind_v2.joblib"

# Vectorizador + matriz del histórico, para el contenido relacionado.
MATRIZ_HISTORICA_PATH: Path = DIR_MODELOS / "matriz_historica.pkl"

# Términos que la interfaz muestra como botones de sugerencia.
SUGERENCIAS_PATH: Path = DIR_MODELOS / "sugerencias_botones.json"

# Si la probabilidad de la predicción principal cae por debajo de este
# umbral, la respuesta incluye una categoría alternativa (recomendación
# del equipo de modelado documentada en el notebook v2).
UMBRAL_CATEGORIA_ALTERNATIVA: float = 0.5

# Cantidad de palabras clave a devolver por defecto en la respuesta.
# El vectorizador se entrenó con ngram_range=(1, 2), así que estos "términos"
# pueden ser unigramas ("docker") o bigramas ("apis rest").
TOP_N_PALABRAS_CLAVE: int = 5
