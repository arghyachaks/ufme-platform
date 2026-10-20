from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentTenant, DbSession
from app.core.errors import NotFoundError
from app.models import MatchRule
from app.schemas.read import PolicyOut, RuleOut, ScenarioOut
from app.services import audit, read

router = APIRouter()


@router.get("/rules", response_model=list[RuleOut], response_model_exclude_none=True)
def list_rules(db: DbSession, tenant: CurrentTenant) -> list[RuleOut]:
    return read.rules(db, tenant)


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(db: DbSession, tenant: CurrentTenant) -> list[PolicyOut]:
    return read.policies(db, tenant)


@router.get("/rules/simulations", response_model=list[ScenarioOut])
def list_scenarios(db: DbSession, tenant: CurrentTenant) -> list[ScenarioOut]:
    results: dict[str, Any] = read.snapshot(db, tenant, "simulation.results")
    return [ScenarioOut(key=key, label=value["scenario"]) for key, value in results.items()]


@router.post("/rules/simulations/{key}/run")
def run_simulation(key: str, db: DbSession, tenant: CurrentTenant) -> Any:
    """Stage 1 returns the recorded result; Stage 3 runs the matching engine against the dataset."""
    results: dict[str, Any] = read.snapshot(db, tenant, "simulation.results")
    if key not in results:
        raise NotFoundError(f"Unknown simulation scenario '{key}'.", code="scenario_not_found")
    return results[key]


@router.get("/workflow/stages")
def workflow_stages(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "workflow.stages")


class RuleToggle(BaseModel):
    enabled: bool


@router.patch("/rules/{code}", response_model=RuleOut, response_model_exclude_none=True)
def set_rule_enabled(code: str, body: RuleToggle, db: DbSession, tenant: CurrentTenant) -> RuleOut:
    """Enable/disable a rule; the next matching run uses the new rule set (recorded on the run for audit)."""
    rule = db.scalar(select(MatchRule).where(MatchRule.tenant_id == tenant.id, MatchRule.code == code))
    if rule is None:
        raise NotFoundError(f"Rule '{code}' not found.", code="rule_not_found")
    before = rule.enabled
    rule.enabled = body.enabled
    audit.record(
        db,
        tenant_id=tenant.id,
        actor="api",
        action="rule.enabled" if body.enabled else "rule.disabled",
        object_type="match_rule",
        object_id=code,
        control="CHG-01",
        before={"enabled": before},
        after={"enabled": rule.enabled},
    )
    db.flush()
    return next(r for r in read.rules(db, tenant) if r.id == code)
