import os
from collections.abc import Iterator

import pytest

# Tests default to an in-memory SQLite DB; CI overrides DATABASE_URL to run the same suite on Postgres.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

DB_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def engine():  # type: ignore[no-untyped-def]
    kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool} if DB_URL.startswith("sqlite") else {}
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
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
