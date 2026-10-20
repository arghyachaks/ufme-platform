from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UFME API"
    environment: Literal["local", "test", "dev", "staging", "prod"] = "local"
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "postgresql+psycopg://ufme:ufme@localhost:5432/ufme"
    database_echo: bool = False
    redis_url: str = "redis://localhost:6379/0"
    default_page_size: int = 50
    max_page_size: int = 500
    seed_demo: bool = False
    upload_dir: str = "/tmp/ufme-uploads"  # shared volume between api and worker in Docker
    ingest_inline: bool = False  # process uploads in the request (tests / no worker) instead of Celery
    max_upload_mb: int = 200
    ollama_url: str = "http://localhost:11434"  # Docker: http://host.docker.internal:11434
    assist_model: str = "gemma4:e4b-it-qat"
    default_tenant: str = "demo"  # until auth (Stage 5) resolves the tenant from the user

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
