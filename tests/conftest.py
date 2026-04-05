"""Shared test configuration and fixtures for MarketPulse tests."""
from __future__ import annotations

import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Streamlit mock - injected before any module that imports streamlit is loaded

@pytest.fixture(autouse=True)
mock_st = sys.modules.get("streamlit")
if mock_st is None:
    mock_st = _make_streamlit_mock()
else:
    fresh_mock = _make_streamlit_mock()
    mock_st.cache_data = fresh_mock.cache_data
    mock_st.cache_resource = fresh_mock.cache_resource
    monkeypatch.setitem(sys.modules, "streamlit", mock_st)
    yield mock_st
# ---------------------------------------------------------------------------

def _make_streamlit_mock() -> MagicMock:
    """Return a minimal mock that satisfies the common st.cache_data / st.cache_resource
    usage patterns seen in the codebase.
    """
    mock_st = MagicMock()

    # cache_data(ttl=...) returns a decorator that returns the original function
    def _cache_data_passthrough(**_kwargs):
        def _decorator(fn):
            return fn
        return _decorator

    # cache_resource behaves the same for our tests
    def _cache_resource_passthrough(fn=None, **_kwargs):
        if fn is not None:
            return fn
        def _decorator(inner_fn):
            return inner_fn
        return _decorator

    mock_st.cache_data = _cache_data_passthrough
    mock_st.cache_resource = _cache_resource_passthrough
    mock_st.sidebar = MagicMock()
    mock_st.sidebar.expander = MagicMock(return_value=MagicMock(
        __enter__=lambda s, *a, **k: s,
        __exit__=lambda s, *a, **k: False,
    ))
    return mock_st


# Inject the mock *before* any code in this test suite imports streamlit.
if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = _make_streamlit_mock()
else:
    # Patch in-place so imports that already resolved still see mocked decorators
    st_mock = _make_streamlit_mock()
    st_mod = sys.modules["streamlit"]
    st_mod.cache_data = st_mock.cache_data  # type: ignore[attr-defined]
    st_mod.cache_resource = st_mock.cache_resource  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# SQLAlchemy mock - injected when sqlalchemy is not available in the
# test environment (e.g. running without the full project virtualenv).
# The mock is structural enough to let module-level class bodies parse
# but intentionally thin – tests that need real DB behaviour use fixtures
# that install in-memory SQLite via a real engine.
# ---------------------------------------------------------------------------

def _make_sqlalchemy_mock() -> None:
    """Inject lightweight structural mocks for sqlalchemy and sub-packages."""
    try:
        import sqlalchemy  # noqa: F401
        return  # Real library is installed; use it.
    except ImportError:
        pass

    sa = MagicMock(name="sqlalchemy")
    # Column constructors need to return something usable as a class attribute
    sa.Column = MagicMock(side_effect=lambda *a, **kw: MagicMock())
    sa.String = MagicMock(return_value=MagicMock())
    sa.Float = MagicMock()
    sa.Integer = MagicMock()
    sa.Boolean = MagicMock()
    sa.Text = MagicMock()
    sa.DateTime = MagicMock()
    sa.Engine = MagicMock()
    sa.create_engine = MagicMock(return_value=MagicMock())
    sa.text = MagicMock()
    sa.func = MagicMock()

    orm = MagicMock(name="sqlalchemy.orm")
    # declarative_base() must return a class so that SQLAlchemy model classes
    # can inherit from it.
    _base_cls = type("Base", (), {"metadata": MagicMock(), "__init_subclass__": classmethod(lambda cls, **kw: None)})
    orm.declarative_base = MagicMock(return_value=_base_cls)
    orm.sessionmaker = MagicMock(return_value=MagicMock())
    orm.Session = MagicMock()

    dialects_pg = MagicMock(name="sqlalchemy.dialects.postgresql")
    dialects_pg.UUID = MagicMock(side_effect=lambda *a, **kw: MagicMock())

    ext = MagicMock(name="sqlalchemy.ext")
    ext_declarative = MagicMock(name="sqlalchemy.ext.declarative")
    _legacy_base_cls = type(
        "Base",
        (),
        {"metadata": MagicMock(), "__init_subclass__": classmethod(lambda cls, **kw: None)},
    )
    ext_declarative.declarative_base = MagicMock(return_value=_legacy_base_cls)

    sys.modules["sqlalchemy"] = sa
    sys.modules["sqlalchemy.orm"] = orm
    sys.modules["sqlalchemy.ext"] = ext
    sys.modules["sqlalchemy.ext.declarative"] = ext_declarative
    sys.modules["sqlalchemy.dialects"] = MagicMock()
    sys.modules["sqlalchemy.dialects.postgresql"] = dialects_pg


_make_sqlalchemy_mock()


# ---------------------------------------------------------------------------
# yfinance mock - not installed in the test environment; provide a stub.
# ---------------------------------------------------------------------------
if "yfinance" not in sys.modules:
    sys.modules["yfinance"] = MagicMock(name="yfinance")

# ---------------------------------------------------------------------------
# numpy / pandas - usually available but guard just in case
# ---------------------------------------------------------------------------
try:
    import numpy
    import pandas
    # Ensure real modules are visible even if imported lazily elsewhere
    sys.modules.setdefault("numpy", numpy)
    sys.modules.setdefault("pandas", pandas)
except ImportError:
    sys.modules.setdefault("numpy", MagicMock(name="numpy"))
    sys.modules.setdefault("pandas", MagicMock(name="pandas"))

# ---------------------------------------------------------------------------
# psycopg2 mock
# ---------------------------------------------------------------------------
if "psycopg2" not in sys.modules:
    sys.modules["psycopg2"] = MagicMock(name="psycopg2")

# ---------------------------------------------------------------------------
# feedparser mock
# ---------------------------------------------------------------------------
if "feedparser" not in sys.modules:
    sys.modules["feedparser"] = MagicMock(name="feedparser")


# ---------------------------------------------------------------------------
# Sample article fixture used across news tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_article():
    return {
        "title": "Markets Rally on Fed Decision",
        "link": "https://example.com/article1",
        "summary": "Stock markets rallied today after the Fed announced its decision.",
        "published": datetime(2026, 4, 1, 10, 0, 0),
        "source": "Yahoo Finance",
        "author": "John Doe",
    }


@pytest.fixture
def sample_articles():
    return [
        {
            "title": "Tech stocks surge on AI news",
            "link": "https://example.com/tech1",
            "summary": "Technology stocks rose as artificial intelligence investments increased.",
            "published": datetime(2026, 4, 1, 12, 0, 0),
            "source": "Reuters Business",
            "author": "Jane Smith",
        },
        {
            "title": "Oil prices drop amid supply concerns",
            "link": "https://example.com/energy1",
            "summary": "Energy sector faced pressure as oil supplies increased globally.",
            "published": datetime(2026, 4, 1, 11, 0, 0),
            "source": "MarketWatch",
            "author": "Bob Wilson",
        },
        {
            "title": "Banking sector faces regulatory challenges",
            "link": "https://example.com/finance1",
            "summary": "Banks encountered new finance regulatory requirements today.",
            "published": datetime(2026, 4, 1, 10, 0, 0),
            "source": "CNBC",
            "author": "Alice Brown",
        },
    ]