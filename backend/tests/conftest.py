"""Shared in-memory SQLite fixtures for tests (no Postgres needed)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.db.session import Base

# pgvector's Vector type has no SQLite dialect — map it to TEXT for tests
try:
    from pgvector.sqlalchemy import Vector

    @compiles(Vector, "sqlite")
    def _vector_sqlite(type_, compiler, **kw):
        return "TEXT"
except ImportError:
    pass


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()
