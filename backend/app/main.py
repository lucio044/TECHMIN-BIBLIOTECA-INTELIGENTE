from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routers import (health, contenido, categorias, chat, modelo, biblioteca,
                         sugerencias, busqueda, lote, metricas, correcciones,
                         modelos_propios)
from app.core.config import settings
from app.ml.loader import cargar_modelo
from app.ml.recomendador import cargar_recomendador
from app.ml.sugerencias_loader import cargar_sugerencias
from app.core.database import crear_tablas, hay_base
import logging
import uuid

logging.basicConfig(level=logging.INFO)

# Identifica al modelo que produjo cada respuesta. Se actualiza cuando se
# reentrena, y viaja en la cabecera X-Modelo-Version.
MODELO_VERSION = "techmind-v2-balanced"

DESCRIPCION = """
Clasifica contenido tecnico en 8 categorias y devuelve palabras clave,
categorias candidatas y contenido relacionado.

Las rutas viven bajo **`/v1`**. Las mismas rutas sin prefijo siguen
funcionando por compatibilidad, y responden con la cabecera `Deprecation`.

**Acceso.** Se puede usar sin credenciales, con un limite de 30 peticiones
por minuto. Con una clave en la cabecera `X-API-Key` el limite sube a 600.

Cada respuesta trae `X-Request-ID` para rastrearla en los registros y
`X-Modelo-Version` para saber que modelo la produjo.
"""

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=DESCRIPCION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5500",          # Live Server de VS Code
        "https://lucio044.github.io",     # la pagina en GitHub Pages
    ],
    allow_origin_regex=r"https://([\w\-]+\.)?(vercel\.app|onrender\.com|netlify\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Las rutas se publican bajo /v1 y tambien sin prefijo.
#
# El prefijo es lo que permite cambiar la forma de una respuesta el dia de
# manana sin romperle la integracion a quien ya la esta usando: se publica
# /v2 y /v1 sigue como esta.
#
# Las rutas sin prefijo se mantienen porque hay clientes apuntando ahi
# --la pagina, entre otros-- y quitarlas de golpe los dejaria sin servicio.
# Quedan como compatibilidad y responden con la cabecera Deprecation.
ROUTERS = (
    health.router, contenido.router, categorias.router, chat.router,
    modelo.router, biblioteca.router, sugerencias.router, busqueda.router,
    lote.router, metricas.router, correcciones.router, modelos_propios.router,
)

for r in ROUTERS:
    app.include_router(r, prefix="/v1")
    app.include_router(r, include_in_schema=False)


@app.middleware("http")
async def cabeceras_de_servicio(request: Request, call_next):
    """Agrega a cada respuesta lo que un cliente necesita para operar.

    El identificador permite rastrear una peticion concreta en los registros
    cuando alguien reporta un problema. La version del modelo evita la
    discusion de "a mi me daba otra cosa": queda escrito cual respondio.
    Las cabeceras de limite dejan que el cliente se regule solo en vez de
    descubrir el tope a fuerza de errores 429.
    """
    respuesta = await call_next(request)

    respuesta.headers["X-Request-ID"] = uuid.uuid4().hex[:16]
    respuesta.headers["X-Modelo-Version"] = MODELO_VERSION
    respuesta.headers["X-API-Version"] = settings.app_version

    if not request.url.path.startswith(("/v1", "/docs", "/redoc", "/openapi")):
        respuesta.headers["Deprecation"] = "true"
        respuesta.headers["Link"] = '</v1' + request.url.path + '>; rel="successor-version"'

    for k, v in getattr(request.state, "limite_cabeceras", {}).items():
        respuesta.headers[k] = v

    return respuesta


@app.on_event("startup")
def iniciar_modelo():
    # Las tablas primero: si la base esta configurada pero inalcanzable,
    # conviene enterarse al arrancar y no en la primera correccion.
    crear_tablas()
    if not hay_base():
        logging.getLogger(__name__).warning(
            "Sin DATABASE_URL: las correcciones y los modelos propios se "
            "pierden al reiniciar. Ver README para configurarla."
        )
    cargar_modelo()
    cargar_recomendador()
    cargar_sugerencias()


@app.exception_handler(Exception)
async def manejador_errores_generales(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error interno inesperado. El equipo ya fue notificado."},
    )