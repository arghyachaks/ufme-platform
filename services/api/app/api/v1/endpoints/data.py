from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentTenant, DbSession
from app.core.errors import NotFoundError
from app.schemas.read import ControlOut, QualityIssueOut, SourceOut
from app.services import read

router = APIRouter()


@router.get("/data/sources", response_model=list[SourceOut])
def data_sources(db: DbSession, tenant: CurrentTenant) -> list[SourceOut]:
    return read.sources(db, tenant)


@router.get("/data/quality")
def data_quality(db: DbSession, tenant: CurrentTenant) -> dict[str, Any]:
    issues: list[QualityIssueOut] = read.quality_issues(db, tenant)
    return {
        "issues": [i.model_dump(by_alias=True) for i in issues],
        "dimensions": read.snapshot(db, tenant, "data.quality.dimensions"),
    }


@router.get("/data/lineage")
def lineage_ids(db: DbSession, tenant: CurrentTenant) -> list[str]:
    return list(read.snapshot(db, tenant, "data.lineage").keys())


@router.get("/data/lineage/{txn_id}")
def lineage(txn_id: str, db: DbSession, tenant: CurrentTenant) -> Any:
    steps = read.snapshot(db, tenant, "data.lineage").get(txn_id)
    if steps is None:
        raise NotFoundError(f"No lineage for transaction '{txn_id}'.", code="lineage_not_found")
    return steps


@router.get("/data/features")
def features(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "data.features")


@router.get("/audit/events")
def audit_events(db: DbSession, tenant: CurrentTenant) -> list[dict[str, Any]]:
    return [e.model_dump(by_alias=True) for e in read.audit_events(db, tenant)]


@router.get("/audit/controls", response_model=list[ControlOut])
def audit_controls(db: DbSession, tenant: CurrentTenant) -> list[ControlOut]:
    return read.controls(db, tenant)
