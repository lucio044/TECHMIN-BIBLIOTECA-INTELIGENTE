# Dataset

El corpus no se versiona acá: pesa **87,8 MB** y ya vive en el repositorio
del proyecto.

**Descargar:**
https://github.com/No-Country-simulation/G9-LATAM-Team-46/raw/main/dataset/processed/techmind_dataset_v2.csv

Guardarlo en esta carpeta como `techmind_dataset_v2.csv` si se van a correr
los notebooks. Para levantar la API no hace falta.

## Qué contiene

Corpus técnico bilingüe construido por el equipo a partir de fuentes
públicas.

| | |
|---|---|
| Registros | 38.276 |
| Categorías | 8 |
| Duplicados | 0 |
| Columnas | `titulo`, `texto`, `categoria`, `palabras_clave`, `fuente`, `idioma` |

| Fuente | Registros | % |
|---|--:|--:|
| StackOverflow | 25.574 | 66,8 % |
| Medium | 11.140 | 29,1 % |
| freeCodeCamp (ES) | 659 | 1,7 % |
| Wikipedia (ES) | 379 | 1,0 % |
| Corpus propio ES (PDF/OCR) | 524 | 1,4 % |

Predomina el inglés (95,9 %). La clasificación se apoya en el vocabulario
técnico, que es común a los dos idiomas —`docker`, `python`, `api`, `jwt`—
así que el modelo responde bien también en español. El corpus en español se
incorporó justamente para reforzar ese caso.

La documentación completa está en
[`dataset/processed/README.md`](https://github.com/No-Country-simulation/G9-LATAM-Team-46/blob/main/dataset/processed/README.md)
del repositorio del proyecto.
