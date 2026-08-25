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

## `muestra_tipo_contenido.csv`

Esta sí se versiona: son 405 KB y la página la pide en runtime para la
pestaña de categorías propias.

Son 592 documentos del corpus, etiquetados por su columna `fuente`:

| Etiqueta | Origen | Filas |
|---|---|--:|
| `Pregunta` | StackOverflow | 296 |
| `Artículo` | Medium | 296 |

Ninguna fila está inventada. Se regenera con:

```
python dataset/preparar_muestra.py
```

**Por qué esa taxonomía y no otra.** Sirve para demostrar el entrenamiento
con categorías propias sólo si es algo que las 8 de fábrica no pueden dar.
Fusionarlas —Backend y Frontend en «Desarrollo»— no probaría nada: eso se
resuelve con una tabla de equivalencias y sin modelo.

`Pregunta` contra `Artículo` es una distinción de **formato**, no de tema, y
las dos fuentes cubren las 8 categorías por igual. Ninguna reagrupación de
las etiquetas de fábrica puede producirla.

La muestra está estratificada por tipo *y* por categoría —37 documentos de
cada una de las 8 en cada clase— para que el modelo no pueda acertar
mirando el tema.

Se usan sólo las dos fuentes en inglés a propósito: sumar las de español
dejaría que acierte por el idioma, y el F1 saldría inflado.

Entrenada con la API da **F1 macro 0,958** sobre el 20 % apartado antes de
entrenar.
