"""Recon Investigator: works an intercompany pair's unmatched items and proposes matches, with a human deciding.

The only action it can take is `propose_match`, and that tool never runs on the agent's say-so: the graph pauses
(HumanInTheLoopMiddleware) and shows the proposal to a person, who approves, edits or rejects it. Even approved,
the proposal only *submits* a manual match into ufme's normal approval matrix (tolerance policy, approver role by
exposure, dual control above 1M, segregation of duties), so every change has at least two people behind it.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.agents import harness, memory, registry, tools
from app.core.config import settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models.agents import AgentRun
from app.models.tenant import Tenant
from app.services import workflow
from app.services.workflow import Actor, require_writer

PROMPT = """You are the ufme Recon Investigator, an agent that clears intercompany breaks for one entity pair.
The person watching you sees every step.

How you work:
1. First call share_thinking with a short summary and a plan of 2 to 5 steps.
2. Look at the unmatched items for the pair with unmatched_items. Use other ufme tools if useful.
3. Find items that belong together: same or similar reference, amounts that agree (after FX, withholding tax,
   bank fees) within the tolerance policy (0.5% of exposure, capped at 500 USD), and close dates.
4. For each match you are confident about, call propose_match with the item ids from BOTH sides and a one-line
   rationale. A person reviews each proposal before anything happens; never claim a match is done.
5. Finish with a short summary: what you proposed, what you could not explain and why.

Rules: never invent ids or amounts; quote ids exactly. Propose at most {max_props} matches per run. Do not use file
tools.
Pair: {pair}"""


def tools_for(db: Session, tenant: Tenant, actor: Actor, pair: str) -> list[Callable[..., str]]:
    read = tools.build(db, tenant, actor)

    def unmatched_items(limit: int = 25) -> str:
        """Open (unmatched) items on both sides of the pair, largest first, with reference, amount (USD and
        original), date and description."""
        data = workflow.unmatched(db, tenant, pair, min(limit, 40), actor)
        return json.dumps(data, default=str)[:9000]

    def propose_match(item_ids: list[str], rationale: str) -> str:
        """Propose matching these items (ids from both sides of the pair). A person must approve this before it
        is submitted; the submitted match then goes through the normal ufme approval matrix."""
        try:
            group, req = workflow.manual_match(
                db, tenant, item_ids, actor, f"[Recon Investigator] {rationale}".strip()[:1000]
            )
            db.commit()
        except Exception as exc:  # policy violations etc. go back to the agent as a result, not a crash
            db.rollback()
            return f"Not submitted: {exc}"
        return (
            f"Submitted {group.code} for approval {req.code}: needs a {req.required_role}"
            f"{' (dual control)' if req.approvals_needed > 1 else ''}."
        )

    return [unmatched_items, propose_match, *read]


def _build(db: Session, tenant: Tenant, actor: Actor, pair: str) -> Callable[[registry.ModelSpec], Any]:
    fns = tools_for(db, tenant, actor, pair)
    saver = memory.required()

    def build(spec: registry.ModelSpec) -> Any:
        from deepagents import create_deep_agent

        model = registry.chat_model(spec)
        return create_deep_agent(
            model=model,
            tools=[harness.share_thinking, *fns],
            system_prompt=PROMPT.format(pair=pair, max_props=settings.agent_max_proposals),
            interrupt_on={"propose_match": {"allowed_decisions": ["approve", "edit", "reject"]}},
            middleware=[
                harness.subagent_cap(settings.agent_max_subagents),
                harness.call_cap("propose_match", 1, "ufme_one_proposal"),
                harness.plan_first(),
            ],
            checkpointer=saver,
            name="ufme-recon-investigator",
        )

    return build


def _pair(actor: Actor, pair: str) -> str:
    p = "-".join(sorted(x.strip().upper() for x in pair.split("-") if x.strip()))
    if p.count("-") != 1:
        raise ConflictError("Give an entity pair like DE03-IN04.", code="bad_pair")
    workflow.require_scope(actor, p)
    return p


def start(db: Session, tenant: Tenant, actor: Actor, pair: str, question: str | None) -> Iterator[str]:
    require_writer(actor)
    pair = _pair(actor, pair)
    ask = question or f"Investigate the unmatched items for {pair} and propose the matches you can support."
    rec = harness.Recorder(db, tenant.id, "investigator", actor.email, ask, f"pair:{pair}")
    thread = f"{tenant.id}:investigator:{rec.run.id}"
    rec.run.summary = {"pair": pair, "thread": thread}
    specs = registry.candidates("investigator", db, tenant.id)
    try:
        yield from harness.run_graph(
            _build(db, tenant, actor, pair),
            specs,
            {"messages": [{"role": "user", "content": ask}]},
            rec,
            settings.agent_max_steps,
            {"thread_id": thread},
        )
    except RuntimeError as exc:
        yield harness.line({"type": "error", "message": f"The investigator could not run: {exc}"})
        yield harness.line(rec.finish("failed", None, None, str(exc)[:500]))


def decide(
    db: Session,
    tenant: Tenant,
    actor: Actor,
    run_id: str,
    decision: str,
    args: dict[str, Any] | None,
    comment: str | None,
) -> Iterator[str]:
    """A person's decision on the paused proposal; the run then continues from where it stopped."""
    require_writer(actor)
    try:
        run = db.get(AgentRun, uuid.UUID(run_id))
    except ValueError as exc:
        raise NotFoundError("Run not found", code="run_not_found") from exc
    if run is None or run.tenant_id != tenant.id or run.agent != "investigator":
        raise NotFoundError("Run not found", code="run_not_found")
    if run.status != "awaiting_approval":
        raise ConflictError(f"This run is {run.status}, not waiting for a decision.", code="run_not_paused")
    pair = str((run.summary or {}).get("pair", ""))
    if not actor.covers(pair):
        raise ForbiddenError(f"You aren't assigned to {pair}.", code="entity_out_of_scope")
    if decision not in ("approve", "edit", "reject"):
        raise ConflictError("Decide approve, edit or reject.", code="bad_decision")
    pending = (run.summary or {}).get("pending") or {}
    if decision == "approve":
        d: dict[str, Any] = {"type": "approve"}
    elif decision == "edit":
        merged = {**(pending.get("args") or {}), **(args or {})}
        d = {"type": "edit", "edited_action": {"name": "propose_match", "args": merged}}
    else:
        d = {"type": "reject", "message": comment or "The reviewer rejected this proposal."}
    from langgraph.types import Command

    held = max(0, int(pending.get("count", 1)) - 1)  # extra proposals from the same turn: one at a time
    decisions = [d] + [
        {
            "type": "reject",
            "message": "Not reviewed: proposals are reviewed one at a time. Propose it again if "
            "it is still relevant.",
        }
    ] * held

    rec = harness.Recorder.resume(db, run, actor.email)
    rec.emit({"type": "decision", "decision": decision, "by": actor.email, "comment": comment, "args": args})
    yield harness.line({"type": "decision", "decision": decision, "by": actor.email})
    spec = registry.models(db, tenant.id).get(run.model)
    specs = [spec] if spec is not None and spec.status == "approved" else []
    try:
        yield from harness.run_graph(
            _build(db, tenant, actor, pair),
            specs,
            Command(resume={"decisions": decisions}),
            rec,
            settings.agent_max_steps,
            {"thread_id": str((run.summary or {}).get("thread"))},
        )
    except RuntimeError as exc:
        yield harness.line({"type": "error", "message": f"The investigator could not continue: {exc}"})
        yield harness.line(rec.finish("failed", None, None, str(exc)[:500]))
