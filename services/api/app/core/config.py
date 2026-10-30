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
    # Agent harness: any LLM by configuration. JSON list of model specs (see app/agents/registry.py) and role ->
    # ordered fallback list. The local Ollama model is always registered as "local-default".
    agent_models: str = "[]"
    agent_bindings: str = "{}"
    agent_max_subagents: int = 4  # parallel sub-agents per run
    agent_max_steps: int = 40  # graph recursion limit per run
    agent_harness: bool = True  # False: Assist answers with the single-call model (no plan / tools)
    judge_enabled: bool = True  # 3e: advisory LLM second opinion on suggestions after each run
    judge_max: int = 200  # largest-exposure suggestions judged per run (about 1 s each on a laptop GPU)
    model_dir: str = (
        "/tmp/ufme-models"  # 3f: per-process cache of promoted tenant models (source of truth: DB)
    )
    learning_min_labels: int = 30  # reviewer decisions needed before a tenant model can be trained
    learning_gate_golden: str = "small,medium"  # unshifted holdouts a candidate must not regress on
    # Stage 5 authentication. "dev": the X-Ufme-User header picks a seeded user (tests, quick demos).
    # "oidc": a Bearer access token from the identity provider (Keycloak locally) is required on every call.
    auth_mode: Literal["dev", "oidc"] = "dev"
    oidc_issuer: str = "http://localhost:8081/realms/ufme"  # the `iss` the browser-facing IdP puts in tokens
    oidc_jwks_url: str = ""  # where the API fetches signing keys (inside Docker: http://keycloak:8080/...)
    oidc_audience: str = "ufme-api"
    oidc_tenant_claim: str = "ufme_tenant"
    # Signs evidence packages (HMAC-SHA256). Set from the environment / secret store; never committed.
    evidence_signing_key: str = ""
    rls_enabled: bool = True  # Postgres row-level security: every request is pinned to its tenant
    demo_user: str = "priya.nair@example.com"  # acting user until SSO (Stage 5); X-Ufme-User overrides
    default_tenant: str = "demo"  # until auth (Stage 5) resolves the tenant from the user

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
