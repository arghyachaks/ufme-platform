"""Model administration: register, approve (four eyes), block, and bind models to agents.

- Controllers and Finance Directors may propose a model or change bindings; anyone of those may block at once.
- Only a Finance Director who did not propose it may approve a model (segregation of duties), because approving
  a hosted model means tenant data may leave the network.
- Only approved models may be bound. Every change is in the audit trail.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import registry
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models.agents import AgentBinding, AgentModel
from app.models.tenant import Tenant
from app.services import audit
from app.services.workflow import RANK, Actor, PolicyViolation

PROVIDERS = {
    "ollama",
    "openai",
    "anthropic",
    "azure_openai",
    "bedrock_converse",
    "google_genai",
    "google_vertexai",
    "mistralai",
    "openai-compatible-local",
}
ROLES = {"default", "assist", "investigator", "researcher"}
NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
ENV = re.compile(r"^[A-Z][A-Z0-9_]{2,79}$")


def _manager(actor: Actor) -> None:
    if actor.rank < RANK["Controller"]:
        raise ForbiddenError(
            "Only Controllers and Finance Directors can manage agent models.", code="role_required"
        )


def _get(db: Session, tenant: Tenant, name: str) -> AgentModel:
    m = db.scalar(select(AgentModel).where(AgentModel.tenant_id == tenant.id, AgentModel.name == name))
    if m is None:
        raise NotFoundError(f"Model '{name}' is not registered.", code="model_not_found")
    return m


def propose(db: Session, tenant: Tenant, actor: Actor, body: dict[str, Any]) -> AgentModel:
    _manager(actor)
    name = str(body.get("name", "")).strip().lower()
    provider = str(body.get("provider", "")).strip()
    model = str(body.get("model", "")).strip()
    key = (body.get("apiKeyEnv") or "").strip() or None
    if not NAME.match(name) or name in registry.configured():
        raise PolicyViolation("Pick a new short name (letters, digits, dot, dash).", code="bad_name")
    if provider not in PROVIDERS:
        raise PolicyViolation(f"Unknown provider '{provider}'.", code="bad_provider")
    if not model:
        raise PolicyViolation("Give the provider's model id.", code="bad_model")
    if key is not None and not ENV.match(key):
        raise PolicyViolation(
            "API key: give the NAME of the secret / environment variable, not the key.", code="bad_key_ref"
        )
    if db.scalar(select(AgentModel).where(AgentModel.tenant_id == tenant.id, AgentModel.name == name)):
        raise ConflictError(f"'{name}' is already registered.", code="model_exists")
    m = AgentModel(
        tenant_id=tenant.id,
        name=name,
        provider=provider,
        model=model,
        base_url=(body.get("baseUrl") or None),
        api_key_env=key,
        price_in=Decimal(str(body.get("priceIn") or 0)),
        price_out=Decimal(str(body.get("priceOut") or 0)),
        allows_confidential=bool(body.get("allowsConfidential", False)),
        status="pending",
        requested_by=actor.email,
        note=(body.get("note") or None),
    )
    db.add(m)
    db.flush()
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="agent_model.proposed",
        object_type="agent_model",
        object_id=name,
        control="AI-01",
        after=registry.spec_of(m).public(),
    )
    db.commit()
    return m


def approve(db: Session, tenant: Tenant, actor: Actor, name: str) -> AgentModel:
    m = _get(db, tenant, name)
    if actor.role != "Finance Director":
        raise ForbiddenError("A Finance Director approves agent models.", code="role_required")
    if actor.email == m.requested_by:
        raise ForbiddenError(
            "Someone other than the requester must approve (four eyes).", code="sod_violation"
        )
    if m.status != "pending":
        raise ConflictError(f"'{name}' is {m.status}.", code="model_not_pending")
    m.status, m.approved_by, m.approved_at = "approved", actor.email, datetime.now(UTC)
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="agent_model.approved",
        object_type="agent_model",
        object_id=name,
        control="AI-01",
        before={"status": "pending"},
        after={"status": "approved"},
    )
    db.commit()
    return m


def block(db: Session, tenant: Tenant, actor: Actor, name: str) -> AgentModel:
    _manager(actor)
    m = _get(db, tenant, name)
    before = m.status
    m.status = "blocked"
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="agent_model.blocked",
        object_type="agent_model",
        object_id=name,
        control="AI-01",
        before={"status": before},
        after={"status": "blocked"},
    )
    db.commit()
    return m


def bind(db: Session, tenant: Tenant, actor: Actor, role: str, names: list[str]) -> dict[str, list[str]]:
    _manager(actor)
    if role not in ROLES:
        raise PolicyViolation(f"Unknown agent role '{role}'.", code="bad_role")
    reg = registry.models(db, tenant.id)
    bad = [n for n in names if n not in reg or reg[n].status != "approved"]
    if not names or bad:
        raise PolicyViolation(
            f"Only approved models can be used: {', '.join(bad) or 'none given'}.", code="model_not_approved"
        )
    row = db.scalar(
        select(AgentBinding).where(AgentBinding.tenant_id == tenant.id, AgentBinding.role == role)
    )
    before = list(row.models) if row else registry.bindings(db, tenant.id).get(role)
    if row is None:
        row = AgentBinding(tenant_id=tenant.id, role=role, models=names, updated_by=actor.email)
        db.add(row)
    else:
        row.models, row.updated_by = list(names), actor.email
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="agent_binding.changed",
        object_type="agent_binding",
        object_id=role,
        control="AI-01",
        before={"models": before},
        after={"models": names},
    )
    db.commit()
    return registry.bindings(db, tenant.id)


def row(m: AgentModel) -> dict[str, Any]:
    return registry.spec_of(m).public() | {
        "requestedBy": m.requested_by,
        "approvedBy": m.approved_by,
        "approvedAt": m.approved_at,
        "note": m.note,
        "registered": True,
    }
