from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "TechMind AI API"
    app_version: str = "0.1.0"
    description: str = "API que clasifica contenido técnico usando NLP y ML."

    # Cadena completa, como la entregan Neon y los servicios gestionados.
    # Tiene prioridad sobre las variables sueltas de abajo.
    database_url: str | None = None

    db_user: str = "root"
    db_password: str | None = None
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "techmind"

    modelo_url: str | None = None
    deepseek_api_key: str | None = None

    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_minutos_expiracion: int = 60
    
    matriz_historica_url: str | None = None
    sugerencias_botones_url: str | None = None

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")


settings = Settings()