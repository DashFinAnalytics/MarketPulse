"""Tests for the PR changes in database.py (root module).

Changed in this PR:
- `DeclarativeBase` import removed from sqlalchemy.orm
- `get_session()` now returns Optional[Session] (returns None when factory unavailable)
- `get_stored_news()` signature: `str | None = None` -> `str = None`
- `analysis_result` column handling changed
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# Streamlit mock must be in place before importing database.py
if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_db_module():
    """Import database module fresh, avoiding cached module state issues."""
    import importlib
    import database as db_mod
    return db_mod


# ---------------------------------------------------------------------------
# DatabaseManager.get_session() - key PR change
# ---------------------------------------------------------------------------

def get_session(self) -> Optional[Session]:
        factory = get_session_factory()
        if factory is None:
            return None
        return factory()


    def test_returns_session_when_factory_available(self):
        import database as db_mod
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        manager = db_mod.DatabaseManager()
        with patch("database.get_session_factory", return_value=mock_factory):
            result = manager.get_session()
        assert result is mock_session

    def test_does_not_raise_runtime_error_when_factory_none(self):
        """Regression: old code raised RuntimeError; new code must not."""
        import database as db_mod
        manager = db_mod.DatabaseManager()
        with patch("database.get_session_factory", return_value=None):
            try:
                manager.get_session()
            except RuntimeError as exc:
                pytest.fail(
                    f"get_session() should not raise RuntimeError when factory is None, "
                    f"but got: {exc}"
                )

    def test_return_type_annotation_is_session(self):
        import database as db_mod
        hints = db_mod.DatabaseManager.get_session.__annotations__
        return_hint = hints.get("return")
        assert return_hint is db_mod.Session, "get_session should be annotated to return Session"


# ---------------------------------------------------------------------------
# get_stored_news() - signature change: str | None -> str = None
# ---------------------------------------------------------------------------

class TestGetStoredNewsSignature:
    """get_stored_news() must accept symbol=None (default) and symbol as str."""

    def _make_manager_with_no_session(self):
        import database as db_mod
        manager = db_mod.DatabaseManager()
        return manager

    def test_accepts_no_symbol_argument(self):
        import database as db_mod
        manager = self._make_manager_with_no_session()
        with patch.object(manager, "get_session", return_value=None):
            # Should not raise TypeError about argument type
            result = manager.get_stored_news()
        assert isinstance(result, list)

    def test_accepts_none_symbol_explicitly(self):
        import database as db_mod
        manager = self._make_manager_with_no_session()
        with patch.object(manager, "get_session", return_value=None):
            result = manager.get_stored_news(symbol=None)
        assert isinstance(result, list)

    def test_accepts_string_symbol(self):
        import database as db_mod
        manager = self._make_manager_with_no_session()
        with patch.object(manager, "get_session", return_value=None):
            result = manager.get_stored_news(symbol="AAPL")
        assert isinstance(result, list)

    def test_returns_empty_list_when_session_none(self):
        import database as db_mod
        manager = self._make_manager_with_no_session()
        with patch.object(manager, "get_session", return_value=None):
            result = manager.get_stored_news(limit=10)
        assert result == []

    def test_default_limit_is_20(self):
        """Verify default limit parameter is 20."""
        import database as db_mod
        import inspect
        sig = inspect.signature(db_mod.DatabaseManager.get_stored_news)
        assert sig.parameters["limit"].default == 20


# ---------------------------------------------------------------------------
# DeclarativeBase import removed
# ---------------------------------------------------------------------------

class TestDeclarativeBaseImportRemoved:
    """Verify that the PR correctly removed the dead DeclarativeBase inner class."""

    def test_database_manager_has_no_inner_base_class(self):
        import database as db_mod
        assert not hasattr(db_mod.DatabaseManager, "Base"), (
            "DatabaseManager.Base inner class should have been removed in this PR"
        )

    def test_declarative_base_not_imported_from_orm(self):
        """DeclarativeBase should no longer be imported at module level."""
        import database as db_mod
        # The old code imported DeclarativeBase; new code should not have it
        assert not hasattr(db_mod, "DeclarativeBase"), (
            "DeclarativeBase was supposed to be removed from database.py imports"
        )


# ---------------------------------------------------------------------------
# Module-level db_manager instance
# ---------------------------------------------------------------------------

class TestModuleLevelDbManager:
    def test_db_manager_is_created(self):
        import database as db_mod
        assert db_mod.db_manager is not None

    def test_db_manager_is_database_manager_instance(self):
        import database as db_mod
        assert isinstance(db_mod.db_manager, db_mod.DatabaseManager)