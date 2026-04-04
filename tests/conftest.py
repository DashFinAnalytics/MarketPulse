"""Test configuration and fixtures for MarketPulse test suite.

Streamlit must be mocked before any module that imports it is loaded,
so the mock is installed here in conftest.py which pytest processes first.
"""

from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# Streamlit stub – must be installed before data_fetcher is imported
# ---------------------------------------------------------------------------

def _make_passthrough_cache(**_kwargs):
    """Return a decorator that simply calls the wrapped function unchanged."""
    def decorator(func):
        return func
    return decorator


_st_stub = types.ModuleType("streamlit")
_st_stub.cache_data = _make_passthrough_cache
_st_stub.cache_resource = _make_passthrough_cache
sys.modules.setdefault("streamlit", _st_stub)


# ---------------------------------------------------------------------------
# SQLite in-memory engine + session fixtures (for DatabaseManager tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sqlite_engine():
    """Create a SQLite in-memory engine for the entire test session."""
    # Import Base after the streamlit stub is in place so imports don't fail
    from database import Base

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )

    # SQLite doesn't enforce foreign-key constraints by default; enable them
    @event.listens_for(eng, "connect")
    def _set_fk_pragma(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(sqlite_engine):
    """Provide a transactional SQLAlchemy session that rolls back after each test."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, autocommit=False, autoflush=False,
                           expire_on_commit=False)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def patched_db_session(db_session):
    """Patch database.get_db_session to yield the SQLite test session."""
    @contextmanager
    def _fake_get_db_session():
        yield db_session
        db_session.flush()

    with patch("database.get_db_session", _fake_get_db_session):
        yield db_session


@pytest.fixture()
def db_manager(patched_db_session):
    """Return a DatabaseManager whose operations target the SQLite test DB."""
    from database import DatabaseManager
    return DatabaseManager()