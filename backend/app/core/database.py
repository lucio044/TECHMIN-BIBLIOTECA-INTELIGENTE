from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

Base = declarative_base()

if settings.db_password:
    SQLALCHEMY_DATABASE_URL = URL.create(
        drivername="mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None


def obtener_db():
    if SessionLocal is None:
        raise RuntimeError(
            "Base de datos no configurada: falta DB_PASSWORD en el entorno."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()