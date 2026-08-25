# TechMind — Biblioteca Inteligente de Conocimiento Técnico

Recibe contenido técnico —artículos, documentación, tutoriales, apuntes— y
devuelve en JSON lo necesario para organizarlo solo: **categoría**, **nivel
de confianza**, **palabras clave**, **otras categorías candidatas** y
**contenido relacionado** del histórico.

Pensada para plataformas educativas, comunidades técnicas y equipos que
necesitan clasificar y reutilizar grandes volúmenes de conocimiento sin
catalogarlo a mano.

**Hackathon ONE — Alura Latam + Oracle · Equipo 46 (G9 LATAM)**

---

## Probalo

| | |
|---|---|
| **La aplicación** | https://lucio044.github.io/TECHMIN-BIBLIOTECA-INTELIGENTE/ |
| **La API — documentación interactiva** | https://techmind-api-24gg.onrender.com/docs |

En Swagger podés clasificar cualquier texto sin instalar nada: abrí
`POST /contenido`, tocá *Try it out* y pegá tu contenido.

> La API corre en el plan gratuito de Render, que apaga el servicio cuando
> nadie lo usa. Un ping cada diez minutos lo mantiene despierto, pero si
> justo lo encontrás dormido, la primera consulta tarda alrededor de un
> minuto en levantarlo.

---

## Levantarla

```bash
git clone https://github.com/lucio044/TECHMIN-BIBLIOTECA-INTELIGENTE.git
cd TECHMIN-BIBLIOTECA-INTELIGENTE

python preparar.py                    # coloca los artefactos donde van
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Abrir **http://127.0.0.1:8000/docs** — cada endpoint tiene un botón
*Try it out* para probarlo sin escribir código.

Arranca sin base de datos y sin clave de DeepSeek.

### La interfaz

`index.html` se abre directo en el navegador, sin instalar nada.

Elige a qué API hablarle según dónde esté corriendo: publicada usa la de
Render, y abierta desde el disco o desde `localhost` usa `127.0.0.1:8000`.
No hay que cambiar nada para desarrollar.

---

## Qué probar

`POST /contenido` es el principal. En *Try it out*, pegar:

```json
{
  "titulo": "Despliegue con Docker",
  "texto": "Contenedores, Kubernetes y pipelines de CI/CD en AWS con Terraform"
}
```

| Entrada | Qué muestra |
|---|---|
| Programar en C++ y C# | Los términos técnicos llegan enteros al modelo |
| Receta de sopa / Poner agua a hervir con sal | Sin relacionados: no inventa resultados |
| Título y texto solo con espacios | Responde `422`, no un error interno |

---

## Ejemplos de uso

### 1 · Clasificar un contenido

```bash
curl -X POST https://techmind-api-24gg.onrender.com/contenido   -H "Content-Type: application/json"   -d '{"titulo":"Despliegue con Docker","texto":"Contenedores, Kubernetes y pipelines de CI/CD en AWS con Terraform"}'
```

```json
{
  "categoria": "DevOps / Cloud",
  "probabilidad": 0.997,
  "informacion_adicional": ["ci cd", "Terraform", "Kubernetes", "AWS", "Docker"],
  "ranking_categorias": [],
  "contenidos_relacionados": [
    {
      "titulo": "Configure Your Machine to Create Resources with Terraform",
      "extracto": "Terraform is an infrastructure as code tool that lets you...",
      "categoria": "DevOps / Cloud",
      "similitud": 0.45
    }
  ]
}
```

### 2 · Buscar por palabra clave

```bash
curl "https://techmind-api-24gg.onrender.com/buscar?termino=docker&cantidad=3"
```

```json
{
  "termino": "docker",
  "total": 3,
  "resultados": [
    {
      "id": 4821,
      "titulo": "Getting started with Jenkins Docker. Part I",
      "extracto": "In this article we will see how to run Jenkins inside a...",
      "categoria": "DevOps / Cloud",
      "relevancia": 0.78
    }
  ]
}
```

Devuelve los documentos donde ese término más pesa. Es distinto del
contenido relacionado: allí entra un texto completo y se buscan documentos
parecidos en conjunto; acá entra un término suelto.

Si el término no aparece en el corpus, la respuesta es una lista vacía —
no el resultado menos malo.

### 3 · Clasificar un CSV entero

```bash
curl -X POST https://techmind-api-24gg.onrender.com/lote   -F "archivo=@contenidos.csv"
```

El CSV necesita una columna de título y otra de texto. Se aceptan varios
nombres —`titulo`/`title`, `texto`/`contenido`/`text`/`content`— porque un
archivo exportado de otra herramienta rara vez usa los que uno espera.

```json
{
  "archivo": "contenidos.csv",
  "total": 10,
  "clasificadas": 8,
  "con_error": 2,
  "resumen_por_categoria": {
    "DevOps / Cloud": 2,
    "Backend": 2,
    "Frontend": 2,
    "Mobile": 1,
    "Seguridad": 1
  },
  "resultados": [
    {"fila": 1, "titulo": "Despliegue con Docker", "categoria": "DevOps / Cloud", "probabilidad": 0.93, "palabras_clave": ["Docker", "Kubernetes"]},
    {"fila": 9, "titulo": "", "error": "falta el titulo"}
  ]
}
```

Una fila mal formada no tumba el lote: se anota su error y se sigue con las
demás. Un archivo de mil filas con tres rotas devuelve las 997 buenas y
dice exactamente cuáles fallaron.

Límite: **1.000 filas** y **5 MB** por archivo.

### 4 · Consultar las categorías

```bash
curl https://techmind-api-24gg.onrender.com/categorias
```

```json
{
  "categorias": ["Backend", "Bases de Datos", "Ciencia de Datos", "DevOps / Cloud",
                 "Frontend", "Mobile", "Programación General", "Seguridad"]
}
```

### 5 · Entrada inválida

```bash
curl -X POST https://techmind-api-24gg.onrender.com/contenido   -H "Content-Type: application/json"   -d '{"titulo":"   ","texto":"algo"}'
```

Responde `422` con el detalle del campo que falla, no un error interno.

`GET /sugerencias` devuelve los 15 ejemplos de los botones, sin parámetros.

---

## Qué hay acá

```
backend/       La API (FastAPI)
nlp/           Módulo de inferencia: clasificador, limpieza, palabras clave
notebooks/     Limpieza y EDA · entrenamiento · sugerencias y relacionados
modelos/       Los artefactos entrenados
index.html     La interfaz
dataset/       Enlace al corpus (no se versiona, pesa 87,8 MB)
```

### Los endpoints

| Método | Endpoint | Qué hace |
|---|---|---|
| `POST` | **`/contenido`** | Clasifica un contenido técnico |
| `GET` | `/buscar` | Busca en el histórico por palabra clave |
| `POST` | `/lote` | Clasifica un CSV entero de una vez |
| `GET` | `/sugerencias` | Términos de ejemplo para los botones |
| `GET` | `/categorias` | Las 8 categorías |
| `GET` | `/modelo/info` | Metadatos del modelo cargado |
| `POST` `GET` | `/biblioteca` | Clasifica y guarda · historial |
| `POST` | `/chat` | Explicación en lenguaje natural |
| `GET` | `/health` | Estado del servicio |

### Respuesta de `/contenido`

```json
{
  "categoria": "Mobile",
  "probabilidad": 0.99,
  "informacion_adicional": ["Jetpack Compose", "Android", "Kotlin"],
  "ranking_categorias": [],
  "contenidos_relacionados": [
    {
      "titulo": "How can I use MapMyIndia in Kotlin with Jetpack compose",
      "extracto": "Ive been trying to integrate MapMyIndia with jetpack compose but...",
      "categoria": "Mobile",
      "similitud": 0.37
    }
  ]
}
```

`ranking_categorias` trae las candidatas con probabilidad ≥ 0.05 cuando la
clasificación fue reñida. `contenidos_relacionados` solo aparece cuando la
confianza supera 0.5 — con textos ambiguos, la similitud puede devolver
documentos sin relación real aunque el puntaje sea alto.

---

## El modelo

| | |
|---|---|
| Técnica | TF-IDF + Regresión Logística (`class_weight='balanced'`) |
| Formato | `Pipeline` de scikit-learn serializado con `joblib` |
| Vectorización | Unigramas y bigramas, 60.000 términos |
| Ajuste | `GridSearchCV` con criterio F1 macro |
| Clases | 8 categorías |

Es un Pipeline completo: recibe texto crudo y devuelve la predicción, con el
vectorizador adentro, de modo que el preprocesamiento no puede
desincronizarse del modelo.

| Métrica | Valor |
|---|---|
| **F1 macro (test)** | 0.7549 |
| **Validación cruzada 5-fold** | 0.7508 ± 0.0019 |
| Accuracy (test) | 0.7530 |
| Línea base (clase más frecuente) | 0.0309 |

Sobre un conjunto de prueba de **7.652 textos** que conserva la distribución
real y no se tocó en ningún momento. El F1 por categoría va de **0.63**
(Backend) a **0.85** (Mobile).

Se eligió por F1 macro —y no por accuracy— para no premiar a un modelo que
acierte solo en las categorías grandes. La coincidencia entre el test y la
validación cruzada confirma que el resultado no depende de cómo cayó la
división.

### Contenido relacionado

`modelos/matriz_historica.pkl` guarda los 38.257 documentos del corpus
vectorizados, con el vectorizador adentro para que un texto nuevo se compare
en el mismo espacio, y un extracto de 200 caracteres de cada uno.

No se almacena la matriz de similitudes entre todos los pares: con 38.257
documentos serían más de mil cuatrocientos millones de valores, casi todos
cercanos a cero. Se guardan los vectores y se compara contra ellos
únicamente el texto de la consulta.

Su vocabulario **excluye las palabras vacías** de los dos idiomas. El
clasificador se entrena sin quitarlas —aportan algo de señal para decidir la
categoría— pero para buscar documentos parecidos son ruido: en una consulta
corta llegan a decidir el resultado. Medido sobre este corpus, un texto
sobre Jetpack Compose traía como primer relacionado un documento de redes
TCP con 0,547 de similitud, y el 85 % de ese número lo aportaba la palabra
`de`.

Un vecino recomendado cae en la misma categoría que la consulta entre el
**31 %** y el **61 %** de las veces según la categoría, contra el 12,5 % que
daría recomendar al azar.

---

## Los notebooks

| | |
|---|---|
| `1_limpieza_y_eda.ipynb` | Explora el corpus crudo, limpia y prepara |
| `2_entrenamiento_modelo.ipynb` | Entrena y compara contra baseline y Naive Bayes |
| `3_sugerencias_y_relacionados.ipynb` | Genera la matriz y los términos de los botones |

Están ejecutados: se ven las salidas, los gráficos y la lectura de cada
resultado sin correr nada.

Para volver a ejecutarlos hace falta el dataset — ver
[`dataset/README.md`](dataset/README.md).

El orden importa: el primero produce `dataset_limpio.csv`, que consumen los
otros dos.

---

## Pruebas

```bash
cd nlp && pytest          # 72 pruebas
cd backend && pytest      # 20 pruebas
```

Ninguna necesita el `.joblib` real: usan datos sintéticos y Pipelines
pequeños en memoria.

---

## Versiones

Los artefactos son pickles creados con Python 3.12:

```
scikit-learn==1.8.0
numpy>=2.0.0
scipy>=1.13.0
```

La versión de scikit-learn debe coincidir con la del entrenamiento: el
formato interno de `TfidfVectorizer` y `LogisticRegression` cambia entre
versiones, y cargar el modelo con otra devuelve resultados distintos sin que
nada falle a la vista. Numpy va fijado porque los pickles llevan arreglos
serializados con numpy 2.x, y cargarlos con 1.x falla con
`No module named 'numpy._core'`.

Si se reentrena hay que regenerar los tres artefactos, no solo el `.joblib`:
la matriz guarda su propio vectorizador y las sugerencias salen del mismo
vocabulario.

---

## En producción

La API está en **Render** y la página en **GitHub Pages**, las dos en sus
planes gratuitos. El paso a paso está en [`DESPLIEGUE.md`](DESPLIEGUE.md).

Los artefactos se copian durante la construcción, desde `modelos/`. Las
variables `MODELO_URL`, `MATRIZ_HISTORICA_URL` y `SUGERENCIAS_BOTONES_URL`
quedan como respaldo: si el archivo no estuviera en disco, la API lo
descarga sola al arrancar. Eso permite reemplazar el modelo sin reconstruir
nada.

---

## Proyecto completo

Este repositorio tiene lo necesario para que la API funcione. El proyecto
con el dataset, el frontend en React, la guía de despliegue y la
documentación del equipo está en
**[G9-LATAM-Team-46](https://github.com/No-Country-simulation/G9-LATAM-Team-46)**.
