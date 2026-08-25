from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routers import (health, contenido, categorias, chat, modelo, biblioteca,
                         sugerencias, busqueda, lote)
from app.core.config import settings
from app.ml.loader import cargar_modelo
from app.ml.recomendador import cargar_recomendador
from app.ml.sugerencias_loader import cargar_sugerencias
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5500",          # Live Server de VS Code
        "https://lucio044.github.io",     # la pagina en GitHub Pages
    ],
    allow_origin_regex=r"https://(techmind-frontend.*\.vercel\.app|.*\.onrender\.com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(contenido.router)
app.include_router(categorias.router)
app.include_router(chat.router)
app.include_router(modelo.router)
app.include_router(biblioteca.router)
app.include_router(sugerencias.router)
app.include_router(busqueda.router)
app.include_router(lote.router)


@app.on_event("startup")
def iniciar_modelo():
    cargar_modelo()
    cargar_recomendador()
    cargar_sugerencias()


@app.exception_handler(Exception)
async def manejador_errores_generales(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error interno inesperado. El equipo ya fue notificado."},
    )