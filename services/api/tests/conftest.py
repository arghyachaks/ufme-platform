import os
from collections.abc import Iterator

import pytest

# Tests default to an in-memory SQLite DB; CI overrides DATABASE_URL to run the same suite on Postgres.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app

DB_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def engine():  # type: ignore[no-untyped-def]
    kwargs = (
        {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
        if DB_URL.startswith("sqlite")
        else {}
    )
    eng = create_engine(DB_URL, **kwargs)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    """Each test runs inside a transaction that is rolled back afterwards."""
    connection = engine.connect()
    trans = connection.begin()
    session = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")()
    yield session
    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=os.environ.get("UFME_RAISE") == "1") as c:
        yield c
    app.dependency_overrides.clear()
