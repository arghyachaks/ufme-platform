"""Conversation memory: a LangGraph checkpointer on our own Postgres, one thread per Assist conversation.

Thread ids are namespaced by tenant and person, so a conversation can only ever be continued by the person who
started it, in the tenant it belongs to. If the checkpointer can't start, agents fall back to the chat history
the browser sends (memory is a convenience, never a dependency).
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from app.core.config import settings

log = logging.getLogger(__name__)
_lock = threading.Lock()
_saver: Any = None
_failed = False


def _url() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def checkpointer() -> Any:
    """The shared Postgres checkpointer, or None when memory is off or unavailable."""
    global _saver, _failed
    if not settings.agent_memory or _failed or not settings.database_url.startswith("postgresql"):
        return None
    if _saver is not None:
        return _saver
    with _lock:
        if _saver is None and not _failed:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver
                from psycopg.rows import dict_row
                from psycopg_pool import ConnectionPool

                pool = ConnectionPool(
                    _url(),
                    min_size=1,
                    max_size=4,
                    kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
                    open=True,
                )
                saver = PostgresSaver(pool)  # type: ignore[arg-type]
                # The tables are created at deploy time (`python -m app.agents.memory`, run after migrations):
                # setup() builds indexes CONCURRENTLY, which would wait forever behind a request's own open
                # transaction if it ran here. Check they exist instead.
                with pool.connection() as conn:
                    ok = conn.execute("SELECT to_regclass('public.checkpoints') AS t").fetchone()
                if not ok or not ok["t"]:  # type: ignore[call-overload]
                    raise RuntimeError("checkpoint tables missing: run python -m app.agents.memory")
                _saver = saver
            except Exception:
                log.warning("agent memory unavailable; using browser history", exc_info=True)
                _failed = True
    return _saver


_local: Any = None


def required() -> Any:
    """A checkpointer agents that pause for approval can't run without: Postgres when available, otherwise an
    in-process one (single API process: fine for local use and tests, not for several API replicas)."""
    global _local
    saver = checkpointer()
    if saver is not None:
        return saver
    if _local is None:
        from langgraph.checkpoint.memory import InMemorySaver

        _local = InMemorySaver()
    return _local


def thread_id(tenant_id: uuid.UUID, actor: str, thread: str | None) -> str | None:
    if not thread:
        return None
    try:
        t = uuid.UUID(thread)
    except ValueError:
        return None
    return f"{tenant_id}:{actor}:{t}"


def has_history(saver: Any, tid: str) -> bool:
    try:
        return saver.get_tuple({"configurable": {"thread_id": tid}}) is not None
    except Exception:
        return False


def setup() -> None:
    """Create / migrate the checkpointer tables. Run once per deploy, after Alembic, with no transaction open."""
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(_url()) as saver:
        saver.setup()


if __name__ == "__main__":
    setup()
    print("agent memory tables ready")
