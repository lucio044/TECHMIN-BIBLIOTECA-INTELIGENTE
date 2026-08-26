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
| **La aplicación** | https://lucio044.github.io/TECHMIND-BIBLIOTECA-INTELIGENTE/ |
| **La API — documentación interactiva** | https://15-229-103-244.sslip.io/docs |

En Swagger podés clasificar cualquier texto sin instalar nada: abrí
`POST /contenido`, tocá *Try it out* y pegá tu contenido.

> La API corre en el plan gratuito de Render, que apaga el servicio cuando
> nadie lo usa. Un ping cada diez minutos lo mantiene despierto, pero si
> justo lo encontrás dormido, la primera consulta tarda alrededor de un
> minuto en levantarlo.

---

## Levantarla

```bash
git clone https://github.com/lucio044/TECHMIND-BIBLIOTECA-INTELIGENTE.git
cd TECHMIND-BIBLIOTECA-INTELIGENTE

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
curl -X POST https://15-229-103-244.sslip.io/contenido   -H "Content-Type: application/json"   -d '{"titulo":"Despliegue con Docker","texto":"Contenedores, Kubernetes y pipelines de CI/CD en AWS con Terraform"}'
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
curl "https://15-229-103-244.sslip.io/buscar?termino=docker&cantidad=3"
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
curl -X POST https://15-229-103-244.sslip.io/lote   -F "archivo=@contenidos.csv"
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
curl https://15-229-103-244.sslip.io/categorias
```

```json
{
  "categorias": ["Backend", "Bases de Datos", "Ciencia de Datos", "DevOps / Cloud",
                 "Frontend", "Mobile", "Programación General", "Seguridad"]
}
```

### 5 · Entrada inválida

```bash
curl -X POST https://15-229-103-244.sslip.io/contenido   -H "Content-Type: application/json"   -d '{"titulo":"   ","texto":"algo"}'
```

Responde `422` con el detalle del campo que falla, no un error interno.

`GET /sugerencias` devuelve los 15 ejemplos de los botones, sin parámetros.

---

### 6 · Buscar por significado

Es distinto del ejemplo 2. Allí entra un término y salen los documentos que
lo contienen; acá entra una frase en lenguaje corriente y salen los que
hablan de lo mismo, **aunque no compartan ninguna palabra y aunque estén en
otro idioma**.

```bash
curl -G https://15-229-103-244.sslip.io/v1/semantica   --data-urlencode "consulta=cómo protejo las contraseñas de mis usuarios"   --data-urlencode "cantidad=3"
```

```json
{
  "consulta": "cómo protejo las contraseñas de mis usuarios",
  "total": 3,
  "documentos_comparados": 38257,
  "resultados": [
    {
      "titulo": "Contraseña Wikipedia parte 2",
      "categoria": "Seguridad",
      "parecido": 0.68,
      "extracto": "..."
    },
    {
      "titulo": "The Best Password Tips and Tricks",
      "categoria": "Seguridad",
      "parecido": 0.66,
      "extracto": "..."
    }
  ]
}
```

Esa misma consulta en `/buscar` devuelve **cero resultados**: ninguna de sus
palabras aparece en el corpus, que está en inglés al 95,9 %.

`parecido` es el coseno entre significados, de -1 a 1. Por debajo de 0,48 no
se devuelve nada. El corte se buscó midiendo 12 consultas técnicas contra 10
ajenas al corpus; las dos bandas se solapan, así que se prefiere no perder
ninguna consulta legítima antes que rechazar toda la basura.

## Qué hay acá

```
backend/       La API (FastAPI)
nlp/           Módulo de inferencia: clasificador, limpieza, palabras clave
notebooks/     Limpieza y EDA · entrenamiento · sugerencias y relacionados
modelos/       Los artefactos entrenados
index.html     La interfaz: clasificar, biblioteca, mis temas y dashboard
dataset/       Enlace al corpus (no se versiona, pesa 87,8 MB)
```

### Acceso

Las rutas viven bajo **`/v1`**. Las mismas sin prefijo siguen funcionando
por compatibilidad y responden con la cabecera `Deprecation`.

Se puede usar **sin credenciales**, con un límite de **30 peticiones por
minuto**. Con una clave en `X-API-Key` el límite sube a **600**:

```bash
curl -H "X-API-Key: tu-clave" https://15-229-103-244.sslip.io/v1/categorias
```

Las claves se definen en la variable `TECHMIND_API_KEYS`, separadas por
coma. Sin esa variable no hay claves y el servicio queda abierto con el
límite anónimo, que es lo que corresponde a una demo pública.

Cada respuesta trae:

| Cabecera | Para qué |
|---|---|
| `X-Request-ID` | rastrear una petición concreta en los registros |
| `X-Modelo-Version` | saber qué modelo produjo ese resultado |
| `X-RateLimit-Remaining` | cuántas peticiones quedan en el minuto |

### Los endpoints

| Método | Endpoint | Qué hace |
|---|---|---|
| `POST` | **`/contenido`** | Clasifica un contenido técnico |
| `GET` | `/buscar` | Busca en el histórico por palabra clave |
| `GET` | **`/semantica`** | Busca por significado, cruzando idiomas |
| `GET` | `/metricas` | Rendimiento del modelo y composición del corpus |
| `POST` `GET` | `/correcciones` | Reportar una clasificación equivocada |
| `GET` | `/correcciones/resumen` | Dónde se equivoca más el modelo |
| `POST` `GET` | `/modelos` | Entrenar un modelo con categorías propias |
| `POST` | `/modelos/{id}/clasificar` | Clasificar con un modelo propio |
| `DELETE` | `/modelos/{id}` | Descartar un modelo propio |
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

## Categorías propias

Las 8 categorías de fábrica sirven a quien organiza contenido técnico, y a
nadie más: un estudio jurídico necesita *Laboral, Tributario, Societario*;
una clínica necesita *Cardiología, Pediatría*.

`POST /v1/modelos` recibe un CSV con las etiquetas del cliente y entrena un
modelo suyo en segundos:

```bash
curl -X POST https://15-229-103-244.sslip.io/v1/modelos   -F "archivo=@mis_documentos.csv" -F "nombre=Estudio jurídico"
```

```json
{
  "id": "f9fc37777fb0",
  "nombre": "Estudio jurídico",
  "categorias": ["Laboral", "Penal", "Societario", "Tributario"],
  "ejemplos": 120,
  "f1_macro": 0.94
}
```

El F1 se mide sobre el 20 % que se aparta antes de entrenar, no sobre los
mismos textos con los que aprendió.

La diferencia sobre un texto jurídico real:

```
"despido arbitrario del trabajador y cálculo de la indemnización"

  modelo de fábrica  ->  Seguridad      18%
  modelo propio      ->  Laboral        63%
```

> **Persistencia.** Con base de datos configurada el modelo se guarda
> serializado y sobrevive a los reinicios. Sin base queda en memoria, para
> que la demo pública funcione sin depender de un servidor externo.

## Cuando el modelo se equivoca

`POST /v1/correcciones` deja que quien usa la API avise de un error. Cada
aviso queda como un ejemplo etiquetado a mano, que es justo el material que
hace falta para reentrenar.

`GET /v1/correcciones/resumen` agrupa las confusiones repetidas:

```json
{
  "total": 3,
  "confusiones": {
    "Backend -> Bases de Datos": 2,
    "Frontend -> Mobile": 1
  }
}
```

Si un mismo cruce se repite, esas dos categorías comparten frontera y
conviene mirarlas juntas antes de reentrenar.

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

### Búsqueda semántica

El corpus está en inglés al 95,9 % y la interfaz en español. Quien escribe
«cómo protejo las contraseñas» no tiene con qué emparejarse contra un
documento que dice *password hashing*, así que la búsqueda por palabras
devuelve vacío.

Se resuelve con `paraphrase-multilingual-MiniLM-L12-v2`, que lleva los dos
idiomas al mismo espacio. Se usa en ONNX cuantizado a uint8 —113 MB en vez
de 470— y no vía `sentence-transformers`, porque esa librería arrastra torch:
unos 800 MB instalados que no entran junto al resto en 2 GB de memoria.

| | |
|---|---|
| Documentos vectorizados | 38.257 |
| Dimensiones | 384 |
| Tamaño del archivo | 29 MB en `float16` |
| Codificar una consulta | ~6 ms |

Se regeneran con `python semantica/generar_embeddings.py` cada vez que
cambie la matriz histórica. El servicio comprueba al arrancar que los
vectores correspondan a la matriz y se niega a usar unos que no coincidan,
en lugar de devolver resultados equivocados.

Se probó antes la vía barata —LSA sobre la matriz TF-IDF que ya existía, sin
dependencias nuevas— y no sirve acá: su dimensión dominante separa idiomas,
no temas. Una consulta en español devolvía el 100 % de resultados en español
cuando el corpus tiene 2,7 %.

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
cd backend && pytest      # 40 pruebas
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

## La base de datos

Las correcciones y los modelos propios necesitan sobrevivir a un reinicio.
El servicio funciona sin base —guardando en memoria— pero entonces se pierde
todo cada vez que Render reinicia el contenedor.

### Configurarla

Se usa **[Neon](https://neon.tech)**: PostgreSQL gestionado, plan gratuito
de 0,5 GB, **sin tarjeta**. Se eligió sobre Supabase porque este último
pausa el proyecto tras una semana sin uso, que es justo el peor
comportamiento para algo que se abre cada tanto.

1. Crear cuenta en neon.tech con GitHub
2. Crear un proyecto — entrega la cadena de conexión
3. Ponerla en Render como variable `DATABASE_URL`

Las tablas se crean solas al arrancar.

```
DATABASE_URL=postgresql://usuario:clave@ep-xxx.neon.tech/basededatos
```

### Qué se guarda dónde

| | Dónde | Por qué |
|---|---|---|
| Correcciones | Postgres | filas chicas, se agrupan con `GROUP BY` |
| Metadatos de modelos propios | Postgres | nombre, categorías, F1 |
| El Pipeline entrenado | Postgres, en `bytea` | pesa 1-3 MB, entra en la fila |
| Límite de peticiones | **memoria** | una escritura por petición mataría la base |

Ese último punto es deliberado: un contador de límite escribe en cada
llamada, y contra una base gratuita eso cuesta más que el trabajo real. Si
algún día corren varias réplicas, ahí va Redis —Upstash tiene plan gratuito
sin tarjeta— que está hecho para eso.

### Detalles de la conexión

`pool_pre_ping` comprueba que la conexión siga viva antes de usarla: las
bases serverless cortan las ociosas y sin eso la primera consulta tras un
rato falla. `pool_recycle` las renueva cada media hora por si el corte
ocurre sin que el ping alcance a notarlo.

La cadena se normaliza a `postgresql+psycopg://`. Neon la entrega con el
prefijo `postgres://`, que SQLAlchemy 2 rechaza con un error que no dice
que el problema es el prefijo.

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
