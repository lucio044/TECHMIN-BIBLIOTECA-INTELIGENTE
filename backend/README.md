# TechMind AI — Backend (API REST)

API REST desarrollada con **FastAPI** que clasifica contenido técnico usando un modelo de Machine Learning (TF-IDF + Regresión Logística), con capa conversacional sobre DeepSeek y una Biblioteca personal en memoria identificada por cookie. Integrada con Oracle Cloud Infrastructure (OCI Object Storage) para el almacenamiento del modelo entrenado, la matriz de contenido relacionado y las sugerencias de la interfaz.

**Hackathon ONE — Alura Latam + Oracle · Equipo 46 (G9 LATAM) · Backend Lead: Sebastián Lugo**

Rama activa: `feat/backend`.

---

## Índice

- [Arquitectura](#arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Variables de entorno](#variables-de-entorno)
- [Endpoints](#endpoints)
- [Contenido relacionado](#contenido-relacionado)
- [Modelo de Machine Learning](#modelo-de-machine-learning)
- [Biblioteca personal (identidad por cookie)](#biblioteca-personal-identidad-por-cookie)
- [Autenticación (JWT) — inactiva, preparada para v2](#autenticación-jwt--inactiva-preparada-para-v2)
- [CORS](#cors)
- [Docker](#docker)
- [Pruebas](#pruebas)
- [Dependencias y versiones](#dependencias-y-versiones)
- [Estado y pendientes conocidos](#estado-y-pendientes-conocidos)

---

## Arquitectura

Arquitectura por capas, sin base de datos relacional activa en el flujo principal:

```
Request → routers/ → schemas/ (validación Pydantic) → services/ → ml/ (modelo, matriz y sugerencias cacheados en memoria)
```

- **`routers/`** — define los endpoints HTTP, delega toda la lógica a `services/`.
- **`schemas/`** — contratos de entrada/salida con Pydantic. No se mezclan con los modelos de base de datos.
- **`services/`** — lógica de negocio: clasificación, chat, Biblioteca.
- **`ml/`** — carga del modelo `.joblib`, la matriz de contenido relacionado y las sugerencias (patrón singleton en memoria para las tres), y preprocesamiento de texto.
- **`core/`** — configuración (`Settings` vía `pydantic-settings`), conexión a base de datos (SQLAlchemy, no usada en el flujo activo hoy), y la dependencia de identidad por cookie.
- **`models/`** — modelos SQLAlchemy. Existe `Usuario`, pero está completamente inactivo (ver sección de autenticación).

El modelo, la matriz histórica y las sugerencias se cargan **una sola vez** al arrancar el proceso (`@app.on_event("startup")`) y se mantienen cacheados en memoria durante toda la vida del servidor — no se recargan en cada petición.

---

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py                  # Punto de entrada, CORS, routers, startup, exception handler
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings), lee backend/.env
│   │   ├── database.py          # SQLAlchemy engine + Base (no usado en el flujo activo)
│   │   ├── dependencias.py      # obtener_usuario_actual() — identidad por cookie
│   │   └── seguridad.py         # hashing/JWT — construido, inactivo (v2)
│   ├── models/
│   │   └── usuario.py           # Modelo SQLAlchemy Usuario — inactivo (v2)
│   ├── ml/
│   │   ├── loader.py              # cargar_modelo(), descarga desde OCI si no está local
│   │   ├── preprocesamiento.py    # preparar_entrada_modelo() — réplica exacta del preprocesamiento de entrenamiento
│   │   ├── keywords.py            # ExtractorPalabrasClaveTfidf — filtro de stopwords y ponderación por categoría
│   │   ├── recomendador.py        # cargar_recomendador(), descarga matriz_historica.pkl desde OCI
│   │   ├── sugerencias_loader.py  # cargar_sugerencias(), descarga sugerencias_botones.json desde OCI
│   │   ├── modelo_techmind_v2.joblib   # NO versionado (.gitignore)
│   │   ├── matriz_historica.pkl        # NO versionado (.gitignore), 47 MB
│   │   └── sugerencias_botones.json    # NO versionado (.gitignore)
│   ├── routers/
│   │   ├── health.py            # GET /health
│   │   ├── contenido.py         # POST /contenido
│   │   ├── categorias.py        # GET /categorias
│   │   ├── chat.py              # POST /chat
│   │   ├── modelo.py            # GET /modelo/info
│   │   ├── biblioteca.py        # POST /biblioteca, GET /biblioteca
│   │   └── sugerencias.py       # GET /sugerencias
│   ├── schemas/
│   │   ├── contenido.py         # ContenidoEntrada, ContenidoSalida, CategoriaRanking, ContenidoRelacionado
│   │   ├── categorias.py        # CategoriasSalida
│   │   ├── modelo.py            # ModeloInfo
│   │   ├── biblioteca.py        # BibliotecaEntrada, BibliotecaResultado
│   │   └── auth.py              # UsuarioRegistro, UsuarioLogin, Token — inactivo (v2)
│   └── services/
│       ├── clasificador.py      # clasificar_contenido() — lógica central de predicción
│       ├── biblioteca.py        # Almacenamiento en memoria (dict), guardar/obtener
│       └── chat.py              # Capa conversacional sobre DeepSeek, con fallback local
├── tests/
│   ├── test_contenido.py        # pytest, valida contrato de /contenido
│   └── prueba_manual_clasificacion.py  # script manual ES/EN, 16 casos
├── dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
└── requirements.txt
```

---

## Instalación y ejecución

### Requisitos

- Python 3.11+
- `pip`, `venv`

### Pasos

```bash
git clone https://github.com/No-Country-simulation/G9-LATAM-Team-46.git
cd G9-LATAM-Team-46/backend

python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt

copy .env.example .env         # Windows
cp .env.example .env           # macOS / Linux
```

### Levantar el servidor

```bash
uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

> **Importante — activar el entorno virtual en cada sesión.** Si una terminal muestra errores de `ModuleNotFoundError` para paquetes que sí están en `requirements.txt`, o si `pytest`/`uvicorn` parecen usar versiones distintas a las instaladas en el `venv`, es señal de que se está ejecutando el ejecutable global de Windows en vez del que vive en `venv/Scripts/`. Usar siempre `python -m pytest` en vez de `pytest` a secas evita esta confusión — fuerza a usar el intérprete activo del `venv`.

---

## Variables de entorno

Definidas en `app/core/config.py` (clase `Settings`, vía `pydantic-settings`), leídas desde `backend/.env`.

| Variable | Obligatoria | Descripción |
|---|---|---|
| `MODELO_URL` | Solo si el modelo no está local | URL del `.joblib` en OCI Object Storage. El backend lo descarga automáticamente si no lo encuentra en `app/ml/` |
| `MATRIZ_HISTORICA_URL` | Solo si la matriz no está local | URL del `.pkl` de contenido relacionado en OCI. Si falta, `/contenido` sigue funcionando pero `contenidos_relacionados` viene siempre vacío |
| `SUGERENCIAS_BOTONES_URL` | Solo si el JSON no está local | URL de los términos de sugerencia en OCI. Si falta, `GET /sugerencias` responde `503` |
| `DEEPSEEK_API_KEY` | No (recomendada) | Clave del LLM conversacional. Sin ella, `/chat` responde con un resumen local en vez de conversación real — el resto de la API arranca igual |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | No | Conexión MySQL. La API arranca sin ellas (`db_password: str \| None = None`) |
| `JWT_SECRET_KEY` | No | Clave para firmar JWT. **Opcional a propósito** — el login está inactivo, así que su ausencia no bloquea el arranque del servidor |

`.env` nunca se versiona (`.gitignore`). El equipo mantiene `.env.example` como referencia de qué variables existen, sin valores reales.

---

## Endpoints

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/health` | Estado del servicio | No |
| `POST` | `/contenido` | Clasifica un contenido técnico (endpoint principal) | No |
| `GET` | `/categorias` | Lista las categorías que reconoce el modelo | No |
| `GET` | `/sugerencias` | Términos sugeridos para botones de la pantalla principal | No |
| `POST` | `/chat` | Capa conversacional sobre el mismo motor de clasificación (DeepSeek, con fallback local) | No |
| `GET` | `/modelo/info` | Diagnóstico: algoritmo, categorías, fecha de modificación del `.joblib` activo | No |
| `POST` | `/biblioteca` | Clasifica y guarda una entrada en la Biblioteca del usuario (cookie) | Cookie |
| `GET` | `/biblioteca` | Devuelve el historial guardado para el usuario de la cookie | Cookie |

### `POST /contenido`

**Entrada** (`ContenidoEntrada`)

| Campo | Tipo | Validación |
|---|---|---|
| `titulo` | `str` | `min_length=1`, rechaza strings solo con espacios (`field_validator`) |
| `texto` | `str` | `min_length=1`, rechaza strings solo con espacios (`field_validator`) |

**Salida** (`ContenidoSalida`)

| Campo | Tipo | Descripción |
|---|---|---|
| `categoria` | `str` | Categoría ganadora, mayor probabilidad |
| `probabilidad` | `float` | Confianza de la ganadora, 0.0–1.0 |
| `informacion_adicional` | `list[str]` | Top-4 palabras clave, filtradas (sin stopwords, sin redundancia entre bigramas/unigramas) |
| `ranking_categorias` | `list[{categoria, probabilidad}]` | Otras categorías con probabilidad ≥ 0.05, **máximo 4**, ordenadas de mayor a menor, **nunca incluye la ganadora** |
| `contenidos_relacionados` | `list[{titulo, categoria, similitud}]` | Hasta 3 documentos del histórico con similitud ≥ 0.10. **No incluye el texto completo**, solo título/categoría/similitud |

**Guía de consumo — front:**
- `ranking_categorias` puede venir **vacío** (cuando la categoría ganadora es muy segura) o con 1 a 4 elementos — conviene iterar siempre con `.map()`/loop, nunca asumir posiciones fijas (`[0]`, `[1]`, etc.), porque el tamaño varía según qué tan reñida esté la clasificación.
- `contenidos_relacionados` puede venir vacío — es una respuesta legítima, no un error; conviene ocultar la sección en ese caso en vez de mostrarla vacía.
- Al hacer clic en un contenido relacionado no hay endpoint de detalle: se reenvía su `titulo` como una nueva consulta a este mismo endpoint, igual que si el usuario lo hubiera escrito a mano.

**Errores**

| Código | Causa |
|---|---|
| `422` | Validación fallida (campo vacío o solo espacios) |
| `503` | Modelo no disponible (`clasificar_contenido` verifica `modelo is None`) |
| `500` | Error interno no controlado (capturado por el exception handler global) |

### `GET /sugerencias`

Sin body. Devuelve el JSON de términos para los botones de sugerencia de la pantalla principal, tal cual está en `sugerencias_botones.json` — lectura directa, sin pasar por el modelo. Responde `503` si el archivo no está disponible ni localmente ni en OCI.

### `POST /biblioteca` y `GET /biblioteca`

Ver sección [Biblioteca personal](#biblioteca-personal-identidad-por-cookie) para el detalle completo de diseño.

**`POST /biblioteca`** — entrada `BibliotecaEntrada` (`titulo`, `texto`), reutiliza `clasificar_contenido()` internamente, guarda y devuelve `BibliotecaResultado` (incluye `categoria`, `probabilidad`, `palabras_clave`, `fecha_creacion`). **No incluye `ranking_categorias` ni `contenidos_relacionados`** — decisión consciente: son datos derivados del momento de la consulta, no un atributo permanente de lo guardado. Para verlos actualizados, se reclasifica el contenido guardado contra `POST /contenido`.

**`GET /biblioteca`** — sin body, devuelve `list[BibliotecaResultado]` para el `usuario_id` resuelto desde la cookie.

### `GET /modelo/info`

Devuelve `ModeloInfo`: `algoritmo` (string fijo, descriptivo), `cantidad_categorias`, `categorias` (lista), `fecha_modificacion` (de `RUTA_MODELO.stat().st_mtime`). Reutiliza el mismo caché de `cargar_modelo()` que usa `/contenido` — no dispara una carga adicional del modelo.

Coexiste con `GET /categorias` sin ser estrictamente redundante: `/categorias` da la lista simple para consumo del frontend; `/modelo/info` es diagnóstico técnico del ambiente (qué modelo/versión está corriendo).

---

## Contenido relacionado

**Sin cargar el dataset completo en memoria.** `matriz_historica.pkl` trae los 38.257 documentos del histórico ya vectorizados (TF-IDF), listos para comparar por similitud coseno — se descarga una sola vez al arrancar (`cargar_recomendador()`), igual que el modelo.

Por cada clasificación, se compara el texto de entrada contra la matriz completa y se devuelven hasta 3 documentos con similitud ≥ 0.10, ordenados de mayor a menor. Si `MATRIZ_HISTORICA_URL` no está configurada o la descarga falla, `/contenido` sigue respondiendo normal — solo con `contenidos_relacionados` vacío, sin romper el resto del endpoint.

**Filtro adicional por confianza del clasificador:** el recomendador solo se consulta cuando la categoría ganadora tiene probabilidad ≥ 0.5. Con textos ambiguos o no técnicos, la similitud coseno puede devolver documentos con puntajes moderadamente altos (0.5–0.6) sin relación temática real — el modelo no tiene suficiente señal para saber de qué habla el texto, y el recomendador tampoco. Filtrar por la confianza de la clasificación evita mostrar relacionados falsos en esos casos. `contenidos_relacionados` viene vacío tanto si no hay nada parecido como si la clasificación en sí fue poco confiable — es el comportamiento esperado, no un error.

No se guarda ni expone el texto completo de cada documento relacionado, solo `titulo`, `categoria` y `similitud` — mantiene la respuesta liviana y evita duplicar contenido pesado en cada petición.

---

## Modelo de Machine Learning

| | |
|---|---|
| Técnica | TF-IDF + Regresión Logística (`class_weight='balanced'`) |
| Formato | `Pipeline` de scikit-learn, serializado con `joblib` |
| Archivo activo | `app/ml/modelo_techmind_v2.joblib` (no versionado) |
| Categorías | 8 (Backend, Bases de Datos, Ciencia de Datos, DevOps/Cloud, Frontend, Mobile, Programación General, Seguridad) — sin cambios en la taxonomía |
| F1 macro | 0.7549 en test, validación cruzada 0.7508 ± 0.0019 sobre 5 particiones |
| Idioma | Bilingüe (español/inglés) |

**Carga del modelo** (`app/ml/loader.py`):
- `cargar_modelo()` cachea el modelo en la variable global `_modelo`. Si ya está cargado, devuelve el caché sin tocar disco.
- Si el `.joblib` no existe localmente, intenta descargarlo desde `MODELO_URL` (OCI Object Storage) antes de cargarlo.
- Si la descarga falla o `MODELO_URL` no está configurada, devuelve `None` — los endpoints que dependen del modelo responden `503`, no crashean el proceso.

**Preprocesamiento** (`app/ml/preprocesamiento.py`, función `preparar_entrada_modelo(titulo, texto)`):
Limpia título y texto por separado y los une — réplica exacta del preprocesamiento usado para entrenar el modelo activo. **Conserva mayúsculas y símbolos técnicos** (`C++`, `C#`, `CI/CD`, `node.js`), a diferencia de la versión anterior que los eliminaba. No se aplica ningún ajuste propio por encima de esta función — es intencional, para no desalinear el texto de entrada respecto al que el modelo aprendió a interpretar durante el entrenamiento.

**Predicción** (`app/services/clasificador.py`, función `clasificar_contenido()`):
1. `preparar_entrada_modelo()` sobre título y texto.
2. `modelo.predict_proba()` sobre las 8 categorías, toma la de mayor probabilidad como ganadora.
3. Palabras clave vía `ExtractorPalabrasClaveTfidf` — ponderadas por el aporte de cada término a la categoría ganadora, no solo describen el texto sino que tienden a explicar por qué se clasificó así.
4. `ranking_categorias`: el resto de las 8 categorías, filtrado a probabilidad ≥ 0.05 con tope de 4.

> **Nota de versionado crítica:** `scikit-learn==1.8.0` y `numpy>=2.0.0` en `requirements.txt` deben coincidir con la versión usada para entrenar el `.joblib` activo. Un desajuste de versión no siempre lanza error explícito — puede generar `InconsistentVersionWarning` o alterar resultados de forma silenciosa. Si aparece ese warning al arrancar, revisar primero que el entorno (`venv`, contenedor Docker) tenga las versiones correctas instaladas, no solo que `requirements.txt` las declare.

---

## Biblioteca personal (identidad por cookie)

**Sin base de datos.** Diseño elegido explícitamente para evitar dependencia de MySQL o coordinación de infraestructura en esta entrega — completamente reiniciable, sin persistencia en disco.

### Identidad — `app/core/dependencias.py`

```python
def obtener_usuario_actual(request: Request, response: Response) -> str:
```

Dependencia de FastAPI (`Depends(obtener_usuario_actual)`). Si la petición no trae cookie `usuario_id`, genera un `uuid.uuid4()` nuevo y lo setea en la respuesta. Si ya la trae, la reutiliza.

Configuración de la cookie:

```python
httponly=True
samesite="none"
secure=True
max_age=60 * 60 * 24 * 365  # 1 año
```

`samesite="none"` + `secure=True` es obligatorio porque frontend (Vercel) y backend (AWS) están en dominios distintos — toda comunicación es cross-site, y `"lax"` bloquearía la cookie en peticiones `fetch`/`POST`. Requiere HTTPS estable en ambos extremos.

### Almacenamiento — `app/services/biblioteca.py`

```python
biblioteca_en_memoria: dict[str, list[dict]] = {}
```

Diccionario en memoria del proceso. Clave: `usuario_id` (de la cookie). Valor: lista de entradas de esa persona.

- `guardar_en_biblioteca()` usa `.append()` — nunca sobreescribe entradas previas.
- `obtener_biblioteca()` usa `.get(usuario_id, [])` — lista vacía si el usuario nunca guardó nada, evita error 500 para usuarios nuevos.

Se guarda el **texto como string**, nunca un archivo como objeto — si en el futuro se acepta subir `.txt`, se lee el contenido y se descarta el archivo, evitando la necesidad de un servicio de almacenamiento adicional.

**Limitación conocida y aceptada:** todo el contenido se pierde si el proceso del backend se reinicia (mismo comportamiento que el caché del modelo, la matriz y las sugerencias en `app/ml/`). No se pierde con un refresh de página — la cookie persiste en el navegador independientemente del ciclo de vida del backend.

### Reutilización del clasificador

`POST /biblioteca` no duplica lógica de predicción — instancia un `ContenidoEntrada` con los mismos datos y llama a `clasificar_contenido()`, la misma función que usa `POST /contenido`. Solo persiste el subconjunto de campos relevante para un historial (ver nota en la sección de Endpoints).

---

## Autenticación (JWT) — inactiva, preparada para v2

El equipo decidió posponer el login completo a una versión futura por el peso que agregaba al despliegue en esta etapa. El código existe, está comiteado, pero **no se ejecuta en ningún punto del flujo actual**.

**Piezas construidas:**
- `app/models/usuario.py` — modelo SQLAlchemy `Usuario`, coincide con la tabla real en MySQL (`id`, `email` único, `password_hash` nulable, `proveedor`, `proveedor_id`, `fecha_creacion`).
- `app/schemas/auth.py` — `UsuarioRegistro`, `UsuarioRespuesta`, `UsuarioLogin`, `Token`.
- `app/core/seguridad.py` — `hashear_password()`/`verificar_password()` (passlib + bcrypt), `crear_token()` (JWT vía `python-jose`, `HS256`).

**Verificación de inactividad (3 puntos):**
1. `main.py` no importa ningún router de auth, ni `seguridad.py`, ni `schemas/auth.py`.
2. `requirements.txt` no incluye `passlib`, `python-jose` ni `email-validator` — coherente con que nada los requiere en runtime.
3. No existe `app/models/__init__.py` — no hay importación automática que enganche `usuario.py` con el resto de la app.

`jwt_secret_key` en `Settings` es `str | None = None` a propósito: sin este default, el proceso fallaría al arrancar en cualquier entorno sin esa variable configurada, aunque el login no se use.

Cuando se active login en v2, el identificador de cookie de Biblioteca se reemplaza por el `id` real del usuario autenticado — el resto del diseño (estructura de almacenamiento, endpoints) no requiere rediseño.

---

## CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"https://techmind-frontend.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origin_regex` acepta tanto la URL de producción (`techmind-frontend.vercel.app`) como cualquier URL de preview que Vercel genere para ramas/builds de prueba (sufijos random del tipo `techmind-frontend-git-x.vercel.app`). `allow_credentials=True` es necesario para que las cookies de Biblioteca (y JWT, cuando se active) viajen correctamente en peticiones cross-origin.

---

## Docker

- `dockerfile` y `.dockerignore` en `backend/`.
- `.dockerignore` excluye lo que no debe copiarse al contexto de build (`.env`, `.git`, `__pycache__`, `venv/`) — reduce el tamaño del contexto enviado al daemon y actúa como segunda barrera de seguridad si el `dockerfile` alguna vez cambia a un `COPY` más amplio.
- El modelo, la matriz histórica y las sugerencias **no se versionan ni se copian en build time** — se descargan desde OCI Object Storage al arrancar el contenedor, vía `MODELO_URL`, `MATRIZ_HISTORICA_URL` y `SUGERENCIAS_BOTONES_URL`. Esto permite reemplazar cualquiera de los tres en Object Storage y reiniciar el contenedor sin reconstruir la imagen.

```bash
docker build -t techmind-backend -f dockerfile .
docker run -d -p 8000:8000 --env-file .env --name techmind-backend techmind-backend
```

---

## Pruebas

```bash
cd backend
python -m pytest
```

> Usar `python -m pytest` en vez de `pytest` a secas — en Windows, un `pytest.exe` global en el PATH puede ejecutarse en lugar del que vive dentro del `venv`, aunque el prompt muestre `(venv)` activo, corriendo los tests contra versiones de librerías distintas a las instaladas en el proyecto.

| Archivo | Cubre |
|---|---|
| `tests/test_contenido.py` | Contrato de `/contenido` — estructura de respuesta, no valores fijos (el modelo responde con datos reales). 8/8 pasando |
| `tests/prueba_manual_clasificacion.py` | Script manual, 16 casos (8 categorías × ES/EN), resultados en CSV |

---

## Dependencias y versiones

| Paquete | Versión |
|---|---|
| fastapi | 0.139.2 |
| uvicorn | 0.51.0 |
| pydantic | 2.13.4 |
| pydantic-settings | 2.15.0 |
| scikit-learn | 1.8.0 |
| numpy | >=2.0.0 |
| scipy | >=1.13.0 |
| joblib | 1.5.3 |
| SQLAlchemy | 2.0.51 |
| PyMySQL | 1.2.0 |
| requests | 2.32.4 |
| python-dotenv | 1.2.2 |
| openai | 2.53.0 |

> La versión de `scikit-learn` debe coincidir con la usada para entrenar el modelo activo. Ver nota en la sección de Machine Learning.

---

## Estado y pendientes conocidos

- **`POST /contenido/lote`** — no implementado. Mismo patrón que `/contenido`, aceptando una lista de entradas.
- **HTTPS estable del backend en producción (AWS)** — necesario para que `samesite="none"` en la cookie de Biblioteca funcione fuera de local. Pendiente de confirmación con el equipo de despliegue.
- **Login v2** — diseño cerrado, código construido e inactivo. Implementación (conectar routers, activar dependencias) no iniciada.
- **Fallback en `/chat` sin `DEEPSEEK_API_KEY`** — la API completa arranca igual (antes fallaba entera por creación del cliente a nivel de módulo, ya corregido). El chat responde con categoría, confianza y palabras clave en texto plano en vez de conversación real, en lugar del mensaje de error genérico anterior.
- **Bug conocido, no corregido de este lado a propósito:** el preprocesamiento de texto elimina tildes en mayúscula (`MÉTODO` → `MTODO`). No se parchea porque el modelo se entrenó con ese mismo comportamiento — corregirlo introduciría una inconsistencia nueva entre entrenamiento e inferencia, no la resolvería.