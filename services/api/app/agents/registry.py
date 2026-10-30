"""Model registry: any LLM by configuration.

Models are declared in settings (`AGENT_MODELS`, JSON) and bound to agent roles (`AGENT_BINDINGS`). Each binding is
an ordered fallback list. Hosted providers are blocked unless an admin marks the model `approved`, because data
then leaves the machine; their API keys come from the environment / secret store, never from the database.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agents import AgentBinding, AgentModel

LOCAL_PROVIDERS = {"ollama", "openai-compatible-local"}


@dataclass(frozen=True)
class ModelSpec:
    name: str
    provider: (
        str  # ollama | openai | anthropic | azure_openai | bedrock_converse | google_vertexai | mistralai ...
    )
    model: str
    status: str = "approved"  # approved | blocked
    base_url: str | None = None
    api_key_env: str | None = None  # name of the environment variable / secret holding the key
    price_in: Decimal = Decimal(0)  # USD per 1K input tokens
    price_out: Decimal = Decimal(0)
    allows_confidential: bool = True
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def local(self) -> bool:
        return self.provider in LOCAL_PROVIDERS

    def public(self) -> dict[str, Any]:
        """What the dashboard may show (never secrets)."""
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "local": self.local,
            "priceIn": float(self.price_in),
            "priceOut": float(self.price_out),
            "allowsConfidential": self.allows_confidential,
            "keyConfigured": bool(self.api_key_env and os.environ.get(self.api_key_env))
            if self.api_key_env
            else None,
        }

    def cost(self, tokens_in: int, tokens_out: int) -> Decimal:
        return (self.price_in * tokens_in + self.price_out * tokens_out) / 1000


def _default() -> ModelSpec:
    return ModelSpec(
        name="local-default",
        provider="ollama",
        model=settings.assist_model,
        base_url=settings.ollama_url,
        params={"temperature": 0.2, "num_ctx": 16384, "keep_alive": "30m", "reasoning": False},
    )


def models(db: Session | None = None, tenant_id: uuid.UUID | None = None) -> dict[str, ModelSpec]:
    """Configured models plus the tenant's own registered ones (which take precedence by name)."""
    out = dict(configured())
    if db is not None and tenant_id is not None:
        for m in db.scalars(select(AgentModel).where(AgentModel.tenant_id == tenant_id)):
            out[m.name] = spec_of(m)
    return out


def spec_of(m: AgentModel) -> ModelSpec:
    return ModelSpec(
        name=m.name,
        provider=m.provider,
        model=m.model,
        status=m.status,
        base_url=m.base_url,
        api_key_env=m.api_key_env,
        price_in=Decimal(m.price_in or 0),
        price_out=Decimal(m.price_out or 0),
        allows_confidential=m.allows_confidential,
    )


@lru_cache
def configured() -> dict[str, ModelSpec]:
    out = {"local-default": _default()}
    for raw in json.loads(settings.agent_models or "[]"):
        raw = dict(raw)
        for k in ("price_in", "price_out"):
            if k in raw:
                raw[k] = Decimal(str(raw[k]))
        spec = ModelSpec(**raw)
        out[spec.name] = spec
    return out


def bindings(db: Session | None = None, tenant_id: uuid.UUID | None = None) -> dict[str, list[str]]:
    b: dict[str, list[str]] = json.loads(settings.agent_bindings or "{}")
    b.setdefault("default", ["local-default"])
    if db is not None and tenant_id is not None:
        for row in db.scalars(select(AgentBinding).where(AgentBinding.tenant_id == tenant_id)):
            b[row.role] = list(row.models)
    return b


def candidates(role: str, db: Session | None = None, tenant_id: uuid.UUID | None = None) -> list[ModelSpec]:
    """Approved models for a role, in fallback order."""
    bound = bindings(db, tenant_id)
    names = bound.get(role) or bound["default"]
    reg = models(db, tenant_id)
    return [reg[n] for n in names if n in reg and reg[n].status == "approved"]


def chat_model(spec: ModelSpec) -> Any:
    """Build the LangChain chat model for a spec (lazy import: the harness is optional at runtime)."""
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = dict(spec.params)
    if spec.base_url:
        kwargs["base_url"] = spec.base_url
    if spec.api_key_env:
        key = os.environ.get(spec.api_key_env)
        if not key:
            raise RuntimeError(f"API key {spec.api_key_env} is not configured")
        kwargs["api_key"] = key
    provider = "openai" if spec.provider == "openai-compatible-local" else spec.provider
    return init_chat_model(spec.model, model_provider=provider, **kwargs)
