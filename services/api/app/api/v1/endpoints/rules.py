from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentTenant, DbSession
from app.core.errors import NotFoundError
from app.schemas.read import PolicyOut, RuleOut, ScenarioOut
from app.services import read

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
