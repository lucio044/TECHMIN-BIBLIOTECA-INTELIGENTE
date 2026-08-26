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


# Columnas agregadas despues de que la tabla ya existiera en algun
# despliegue. create_all() crea tablas que faltan pero no toca las que ya
# estan, asi que estas hay que agregarlas a mano.
#
# Es un apaño deliberado para un cambio de una sola columna. Al segundo o
# tercero conviene Alembic: esto no sabe deshacer nada ni en que orden
# aplicarse.
COLUMNAS_AGREGADAS = [
    (
        "modelos_propios",
        "duenio",
        "ALTER TABLE modelos_propios ADD COLUMN duenio VARCHAR(80) "
        "NOT NULL DEFAULT 'anterior-a-la-propiedad'",
        "CREATE INDEX IF NOT EXISTS ix_modelos_propios_duenio "
        "ON modelos_propios (duenio)",
    ),
]


def _agregar_columnas_que_falten() -> None:
    """Pone al dia las tablas que ya existian.

    Los modelos entrenados antes de que hubiera dueño quedan con un valor
    que no coincide con el de ningun cliente, asi que dejan de aparecer.
    Es lo correcto: no se puede adivinar de quien era cada uno, y
    asignarselos a cualquiera seria peor que perderlos de vista.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    for tabla, columna, alter, indice in COLUMNAS_AGREGADAS:
        if tabla not in inspector.get_table_names():
            continue
        existentes = {c["name"] for c in inspector.get_columns(tabla)}
        if columna in existentes:
            continue
        logger.warning("Agregando la columna %s.%s, que falta en esta base", tabla, columna)
        with engine.begin() as conexion:
            conexion.execute(text(alter))
            if indice:
                conexion.execute(text(indice))
        logger.info("Columna %s.%s agregada", tabla, columna)


def crear_tablas() -> None:
    """Crea las tablas que falten y pone al dia las que ya estan.

    create_all alcanza mientras el esquema solo crezca con tablas nuevas.
    Cuando se agrega una columna a una tabla que ya existe no hace nada, y
    la aplicacion revienta al primer insert: por eso ademas se revisan las
    columnas de COLUMNAS_AGREGADAS.
    """
    if engine is None:
        return
    # Los modelos tienen que estar importados para que Base los conozca.
    from app.models import correccion, modelo_propio  # noqa: F401

    Base.metadata.create_all(bind=engine)
    try:
        _agregar_columnas_que_falten()
    except Exception as e:
        # Que falle una migracion no puede impedir que el servicio arranque:
        # lo demas sigue funcionando y el error queda en el registro.
        logger.error("No se pudieron agregar las columnas que faltan: %s", e)
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
