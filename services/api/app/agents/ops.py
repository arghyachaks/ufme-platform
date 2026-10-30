"""Agent Operations: usage, models in use, anomalies and InfoSec / model-risk views, from the recorded runs.

Visibility: Controllers, Finance Directors and Auditors see every run in the tenant; others see their own."""

from __future__ import annotations

import statistics
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import registry
from app.core.config import settings
from app.models.agents import AgentEvent, AgentRun
from app.models.tenant import Tenant
from app.services.workflow import Actor


def sees_all(actor: Actor) -> bool:
    return actor.rank >= 2 or actor.role == "Auditor"


def _runs(db: Session, tenant: Tenant, actor: Actor, since: datetime) -> list[AgentRun]:
    q = select(AgentRun).where(AgentRun.tenant_id == tenant.id, AgentRun.started_at >= since)
    if not sees_all(actor):
        q = q.where(AgentRun.actor == actor.email)
    return list(db.scalars(q.order_by(AgentRun.started_at.desc())))


def run_row(r: AgentRun) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "agent": r.agent,
        "actor": r.actor,
        "question": r.question[:200],
        "model": r.model,
        "provider": r.provider,
        "status": r.status,
        "startedAt": r.started_at,
        "ms": (r.summary or {}).get("ms"),
        "tokensIn": r.tokens_in,
        "tokensOut": r.tokens_out,
        "costUsd": float(r.cost_usd),
        "toolCalls": r.tool_calls,
        "subagents": r.subagents,
        "egress": r.egress,
        "error": r.error,
    }


def anomalies(runs: list[AgentRun], now: datetime, known: set[str] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not runs:
        return out
    day = Counter(r.started_at.astimezone(UTC).date() for r in runs)
    today = now.date()
    prior = [day.get(today - timedelta(days=i), 0) for i in range(1, 8)]
    mean, sd = statistics.fmean(prior), (statistics.pstdev(prior) or 1.0)
    if day.get(today, 0) >= 5 and day.get(today, 0) > mean + 3 * sd:
        out.append(
            {
                "kind": "Volume spike",
                "severity": "Medium",
                "detail": f"{day[today]} runs today vs {mean:.1f}/day over the last week",
            }
        )
    bad = [r for r in runs if r.status in ("failed", "fallback")]
    if len(runs) >= 5 and len(bad) / len(runs) > 0.2:
        out.append(
            {
                "kind": "Failure rate",
                "severity": "High",
                "detail": f"{len(bad)} of {len(runs)} runs failed or fell back to a plain answer",
            }
        )
    tokens = [r.tokens_in + r.tokens_out for r in runs if r.tokens_in + r.tokens_out]
    if len(tokens) >= 5:
        med = statistics.median(tokens)
        for r in runs:
            if r.tokens_in + r.tokens_out > 4 * med and r.tokens_in + r.tokens_out > 20_000:
                out.append(
                    {
                        "kind": "Token outlier",
                        "severity": "Low",
                        "run": str(r.id),
                        "detail": f"{r.tokens_in + r.tokens_out:,} tokens (median {int(med):,}) by {r.actor}",
                    }
                )
    known = known if known is not None else set(registry.configured())
    for r in runs:
        if r.model not in known and r.model != "-":
            out.append(
                {
                    "kind": "Unregistered model",
                    "severity": "High",
                    "run": str(r.id),
                    "detail": f"Run used {r.model}, which is not in the model registry",
                }
            )
        if r.egress:
            out.append(
                {
                    "kind": "Data egress",
                    "severity": "Medium",
                    "run": str(r.id),
                    "detail": f"{r.actor} ran {r.agent} on hosted model {r.model} ({r.provider})",
                }
            )
        if r.subagents > settings.agent_max_subagents * 2:
            out.append(
                {
                    "kind": "Sub-agent fan-out",
                    "severity": "Low",
                    "run": str(r.id),
                    "detail": f"{r.subagents} sub-agents in one run",
                }
            )
        hour = r.started_at.astimezone(UTC).hour
        if hour < 1 or hour > 17:  # outside 06:30-23:30 IST working window
            out.append(
                {
                    "kind": "Off-hours use",
                    "severity": "Low",
                    "run": str(r.id),
                    "detail": f"{r.actor} at {r.started_at:%H:%M} UTC",
                }
            )
    return out[:50]


def overview(db: Session, tenant: Tenant, actor: Actor, days: int = 7) -> dict[str, Any]:
    now = datetime.now(UTC)
    runs = _runs(db, tenant, actor, now - timedelta(days=days))
    reg = registry.models(db, tenant.id)
    bound = registry.bindings(db, tenant.id)
    by_model: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": 0, "tokens": 0, "costUsd": 0.0})
    by_user: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": 0, "tokens": 0, "costUsd": 0.0})
    by_day: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": 0, "tokens": 0})
    egress: dict[str, int] = defaultdict(int)
    for r in runs:
        t = r.tokens_in + r.tokens_out
        for bucket, key in ((by_model, r.model), (by_user, r.actor)):
            bucket[key]["runs"] += 1
            bucket[key]["tokens"] += t
            bucket[key]["costUsd"] += float(r.cost_usd)
        by_model[r.model]["provider"] = r.provider
        d = r.started_at.astimezone(UTC).date().isoformat()
        by_day[d]["runs"] += 1
        by_day[d]["tokens"] += t
        if r.egress:
            egress[r.provider] += 1
    ms = [(r.summary or {}).get("ms", 0) for r in runs if (r.summary or {}).get("ms")]
    status = Counter(r.status for r in runs)
    return {
        "scope": "tenant" if sees_all(actor) else "mine",
        "days": days,
        "totals": {
            "runs": len(runs),
            "completed": status.get("completed", 0),
            "fallback": status.get("fallback", 0),
            "failed": status.get("failed", 0),
            "tokensIn": sum(r.tokens_in for r in runs),
            "tokensOut": sum(r.tokens_out for r in runs),
            "costUsd": round(sum(float(r.cost_usd) for r in runs), 4),
            "toolCalls": sum(r.tool_calls for r in runs),
            "subagents": sum(r.subagents for r in runs),
            "avgMs": int(statistics.fmean(ms)) if ms else None,
            "egressRuns": sum(egress.values()),
        },
        "byModel": [{"model": k, **v} for k, v in sorted(by_model.items(), key=lambda x: -x[1]["runs"])],
        "byUser": [{"actor": k, **v} for k, v in sorted(by_user.items(), key=lambda x: -x[1]["runs"])][:20],
        "byDay": [{"day": k, **v} for k, v in sorted(by_day.items())],
        "anomalies": anomalies(runs, now, set(reg)),
        "infosec": {
            "egressByProvider": dict(egress),
            "localOnly": not egress,
            "hostedModelsApproved": [m.name for m in reg.values() if not m.local and m.status == "approved"],
            "writeTools": 0,  # agents have no write tools: every change goes through the approval flow
            "autonomousActions": 0,
        },
        "models": [
            m.public() | {"bindings": [r for r, ns in bound.items() if m.name in ns]} for m in reg.values()
        ],
        "recent": [run_row(r) for r in runs[:50]],
    }


def run_detail(db: Session, tenant: Tenant, actor: Actor, run_id: str) -> dict[str, Any]:
    try:
        rid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(404, "Run not found") from exc
    r = db.get(AgentRun, rid)
    if r is None or r.tenant_id != tenant.id or (not sees_all(actor) and r.actor != actor.email):
        raise HTTPException(404, "Run not found")
    events = db.scalars(select(AgentEvent).where(AgentEvent.run_id == r.id).order_by(AgentEvent.seq))
    return run_row(r) | {"question": r.question, "events": [e.payload for e in events]}
