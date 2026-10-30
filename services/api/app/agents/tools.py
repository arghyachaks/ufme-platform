"""Read-only ufme tools for agents.

Agents can look things up but never change data: there is no write tool here. Every tool is bound to the caller's
tenant (row-level security) and entity scope, so an agent never sees more than the person who started it.
SQLAlchemy sessions are not thread-safe and the harness runs parallel tool calls, so database access is serialised.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.matching import MatchRun
from app.models.tenant import Tenant
from app.services import matching_read, read, workflow
from app.services.workflow import Actor

MAX_ROWS = 25


def _dump(obj: Any) -> str:
    return json.dumps(obj, default=str, separators=(",", ":"))[:6000]


def build(db: Session, tenant: Tenant, actor: Actor) -> list[Callable[..., str]]:
    lock = threading.Lock()

    def scoped(entity: str | None) -> bool:
        return entity is None or actor.covers(entity)

    def close_overview() -> str:
        """Period-close overview: completion %, KPIs, work queue, high-risk exceptions and root causes of open
        breaks. Use this first for any question about status, progress or what needs attention."""
        with lock:
            d = read.snapshot(db, tenant, "workspace.dashboard")
        keep = ("closeCompletion", "kpiGroups", "workQueue", "highRiskExceptions", "rootCauses")
        return _dump({k: d.get(k) for k in keep})

    def list_exceptions(entity: str = "", severity: str = "", status: str = "", limit: int = 15) -> str:
        """Open reconciliation exceptions (breaks). Optional filters: entity code (e.g. DE03), severity
        (Critical, High, Medium, Low), status. Returns id, entity, counterparty, type, amount, age, owner, root cause."""
        with lock:
            rows = read.exceptions(db, tenant)
        out = [
            r.model_dump(by_alias=True)
            for r in rows
            if scoped(r.entity)
            and (not entity or entity.upper() in (r.entity.upper(), r.counterparty.upper()))
            and (not severity or r.severity.lower() == severity.lower())
            and (not status or r.status.lower() == status.lower())
        ]
        return _dump({"count": len(out), "items": out[: min(limit, MAX_ROWS)]})

    def list_cases(status: str = "", limit: int = 15) -> str:
        """Investigation cases with owner, status, priority and linked items. Optional status filter."""
        with lock:
            rows = read.cases(db, tenant)
        out = [
            r.model_dump(by_alias=True) for r in rows if not status or str(r.status).lower() == status.lower()
        ]
        return _dump({"count": len(out), "items": out[: min(limit, MAX_ROWS)]})

    def latest_matching_run() -> str:
        """The most recent matching run: status, auto-match rate, suggestions, unmatched and timing metrics."""
        with lock:
            run = db.scalar(
                select(MatchRun).where(MatchRun.tenant_id == tenant.id).order_by(MatchRun.code.desc())
            )
            if run is None:
                return _dump({"run": None})
            return _dump(matching_read.run_out(run).model_dump(by_alias=True))

    def review_queue(entity_pair: str = "", limit: int = 10) -> str:
        """Match suggestions waiting for a reviewer, largest exposure first, with confidence and why amounts
        differ. Optional entity_pair filter like 'DE03-IN04'."""
        with lock:
            rows = matching_read.proposals(db, tenant, status="proposed", limit=200, actor=actor)
        out = [
            {
                "id": p.id,
                "pair": p.entity_pair,
                "confidence": p.confidence,
                "exposureUsd": p.exposure_usd,
                "residualUsd": p.residual_usd,
                "why": matching_read._residual_label(p.explanation),
            }
            for p in rows
            if not entity_pair
            or entity_pair.upper().replace(" ", "") in p.entity_pair.upper().replace(" ", "")
        ]
        return _dump({"count": len(out), "items": out[: min(limit, MAX_ROWS)]})

    def open_approvals(limit: int = 15) -> str:
        """Approval requests waiting for a decision: id, entity, exposure, required role, SLA due."""
        with lock:
            rows = workflow.list_approvals(db, tenant, "open", actor)
        out = [
            {
                "id": a.code,
                "entity": a.entity_code,
                "exposureUsd": a.exposure_usd,
                "match": a.match_code,
                "requiredRole": a.required_role,
                "status": a.status,
                "slaDue": a.sla_due_at,
            }
            for a in rows
        ]
        return _dump({"count": len(out), "items": out[: min(limit, MAX_ROWS)]})

    def close_readiness(entity: str) -> str:
        """Whether one entity (e.g. US01) is ready to sign off the period, and what is blocking it."""
        if not scoped(entity):
            return _dump({"error": f"You don't have access to {entity}."})
        with lock:
            return _dump(workflow.readiness(db, tenant, entity.upper()))

    return [
        close_overview,
        list_exceptions,
        list_cases,
        latest_matching_run,
        review_queue,
        open_approvals,
        close_readiness,
    ]
