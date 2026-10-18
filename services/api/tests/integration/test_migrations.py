"""Migrations must apply cleanly from empty and roll all the way back, and match the ORM models."""

import os

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401
from app.db.base import Base

API_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _config(url: str) -> Config:
    cfg = Config(os.path.join(API_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(API_ROOT, "app/db/migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _url(tmp_path) -> str:  # type: ignore[no-untyped-def]
    env = os.environ.get("MIGRATION_TEST_DATABASE_URL")
    return env or f"sqlite+pysqlite:///{tmp_path / 'migrate.db'}"


def test_upgrade_matches_models_then_downgrades(tmp_path) -> None:  # type: ignore[no-untyped-def]
    url = _url(tmp_path)
    cfg = _config(url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": False}), Base.metadata)
    assert diff == [], f"Models and migrations differ: {diff}"
    assert {
        "tenant",
        "legal_entity",
        "app_user",
        "role",
        "user_role",
        "audit_event",
        "exception_item",
        "recon_case",
        "snapshot",
    } <= set(inspect(engine).get_table_names())
    command.downgrade(cfg, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
