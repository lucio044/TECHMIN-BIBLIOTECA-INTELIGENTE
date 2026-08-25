"""Conexion a la base de datos.

Acepta dos formas de configurarse, en este orden:

    DATABASE_URL     una cadena completa, que es como la entregan Neon,
                     Supabase y casi todos los servicios gestionados
    DB_USER, DB_...  las variables sueltas, como estaba antes

Y funciona sin ninguna de las dos. Esa es la parte importante: el servicio
tiene que levantar igual sin base configurada, porque la demo publica no la
necesita y porque las pruebas no deberian depender de un servidor externo.
Lo que se pierde en ese caso es solo la persistencia, y cada servicio lo
resuelve guardando en memoria.
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


def _construir_url():
    """Arma la cadena de conexion con lo que haya configurado."""
    if settings.database_url:
        url = settings.database_url
        # Neon y otros entregan la cadena con el prefijo antiguo. SQLAlchemy 2
        # espera postgresql://, y con postgres:// falla al arrancar con un
        # error que no dice que el problema es el prefijo.
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    if settings.db_password:
        return URL.create(
            drivername="mysql+pymysql",
            username=settings.db_user,
            password=settings.db_password,
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
        )
    return None


_url = _construir_url()

if _url is not None:
    # pool_pre_ping evita el error de "conexion cerrada" tipico de las bases
    # serverless, que cortan las conexiones ociosas: antes de usar una del
    # pool se comprueba que siga viva.
    #
    # pool_recycle la renueva cada media hora, por si el corte ocurre sin
    # que el ping alcance a notarlo.
    engine = create_engine(_url, pool_pre_ping=True, pool_recycle=1800)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Base de datos configurada")
else:
    engine = None
    SessionLocal = None
    logger.info(
        "Sin base de datos configurada: las correcciones y los modelos "
        "propios se guardan en memoria y se pierden al reiniciar."
    )


def hay_base() -> bool:
    """Si el servicio puede persistir o solo trabaja en memoria."""
    return SessionLocal is not None


def crear_tablas() -> None:
    """Crea las tablas que falten. Se llama al arrancar.

    Con create_all alcanza mientras el esquema solo crezca. Para cambios que
    modifiquen tablas existentes hace falta una herramienta de migraciones
    tipo Alembic, y esa decision se toma cuando aparezca el primer cambio
    incompatible, no antes.
    """
    if engine is None:
        return
    # Los modelos tienen que estar importados para que Base los conozca.
    from app.models import correccion, modelo_propio  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Tablas verificadas")


def obtener_db():
    """Dependencia de FastAPI: entrega una sesion y la cierra al terminar."""
    if SessionLocal is None:
        raise RuntimeError("Base de datos no configurada.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
