"""Tests for root database.py changes introduced in this PR.

Key changes tested:
  1. get_session() returns None (not raises) when factory is unavailable
  2. get_stored_news() accepts symbol=None (was str | None, now str = None)
  3. get_fundamental_analysis() uses hasattr(.key) column-object detection
     and single-quoted dict keys in the return value
  4. DatabaseManager no longer has an inner Base(DeclarativeBase) class
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from typing import Optional
from unittest.mock import MagicMock, patch
import pytest

# Load the ROOT database.py explicitly by file path so that even if another
# test module has registered a 'database' module from a different path,
# we always get the correct one.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "root_database",
    os.path.join(_ROOT, "database.py"),
)
_db_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_db_mod)

DatabaseManager = _db_mod.DatabaseManager
get_session_factory = _db_mod.get_session_factory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager():
    return DatabaseManager()


# ---------------------------------------------------------------------------
# get_session() behaviour change
# ---------------------------------------------------------------------------

class TestGetSessionReturnsNoneWhenUnavailable:
    """PR change: get_session() must return None when no factory is available."""

    def test_returns_none_when_no_database_url(self):
        """Without DATABASE_URL configured the session factory is None, so
        get_session() must return None (not raise RuntimeError)."""
        with patch.object(_db_mod, "get_session_factory", return_value=None):
            manager = _make_manager()
            result = manager.get_session()
        assert result is None

    def test_returns_session_when_factory_available(self):
        """When a factory IS available, get_session() returns a session object."""
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        with patch.object(_db_mod, "get_session_factory", return_value=mock_factory):
            manager = _make_manager()
            result = manager.get_session()
        assert result is mock_session

    def test_does_not_raise_runtimeerror(self):
        """The old code raised RuntimeError; the new code must NOT raise it."""
        with patch.object(_db_mod, "get_session_factory", return_value=None):
            manager = _make_manager()
            try:
                result = manager.get_session()
            except RuntimeError:
                pytest.fail("get_session() should not raise RuntimeError anymore")

    def test_return_type_is_none_when_unavailable(self):
        with patch.object(_db_mod, "get_session_factory", return_value=None):
            result = _make_manager().get_session()
        assert result is None


# ---------------------------------------------------------------------------
# get_stored_news() type-hint change (str = None)
# ---------------------------------------------------------------------------

class TestGetStoredNewsSignature:
    """PR change: symbol parameter is str = None instead of str | None.
    Behaviour stays the same; tests confirm both call patterns work.
    """

    def _setup_mock_session(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query
        return mock_session, mock_query

    def _patched_manager(self):
        manager = _make_manager()
        mock_session, mock_query = self._setup_mock_session()
        manager.get_session = MagicMock(return_value=mock_session)
        return manager, mock_session, mock_query

    def test_called_without_symbol_returns_list(self):
        manager, _, _ = self._patched_manager()
        result = manager.get_stored_news()
        assert isinstance(result, list)

    def test_called_with_symbol_none_returns_list(self):
        manager, _, _ = self._patched_manager()
        result = manager.get_stored_news(symbol=None)
        assert isinstance(result, list)

    def test_called_with_symbol_string_returns_list(self):
        manager, _, _ = self._patched_manager()
        result = manager.get_stored_news(symbol="AAPL")
        assert isinstance(result, list)

    def test_no_symbol_filter_when_none(self):
        manager, mock_session, mock_query = self._patched_manager()
        manager.get_stored_news(symbol=None)
        # .filter() should NOT be called when symbol is None
        mock_query.filter.assert_not_called()

    def test_symbol_filter_applied_when_given(self):
        manager, mock_session, mock_query = self._patched_manager()
        manager.get_stored_news(symbol="TSLA")
        # .filter() must be called when symbol is provided
        mock_query.filter.assert_called_once()


# ---------------------------------------------------------------------------
# get_fundamental_analysis() column-object check
# ---------------------------------------------------------------------------

class TestGetFundamentalAnalysisColumnCheck:
    """PR change: uses hasattr(result_str, 'key') to detect Column-like objects."""

    def _mock_analysis(self, analysis_result):
        """Create a mock FundamentalAnalysis ORM record."""
        record = MagicMock()
        record.id = "00000000-0000-0000-0000-000000000001"
        record.symbol = "AAPL"
        record.analysis_type = "growth"
        record.analysis_result = analysis_result
        record.period = "quarterly"
        record.created_at = None
        return record

    def _patched_manager_with_analyses(self, analyses):
        manager = _make_manager()
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = analyses
        mock_session.query.return_value = mock_query
        manager.get_session = MagicMock(return_value=mock_session)
        return manager

    def test_string_result_parsed_as_json(self):
        payload = {"eps": 5.4, "pe": 18.2}
        analysis = self._mock_analysis(json.dumps(payload))
        manager = self._patched_manager_with_analyses([analysis])
        result = manager.get_fundamental_analysis("AAPL")
        assert len(result) == 1
        assert result[0]["analysis_result"] == payload

    def test_column_object_is_stringified(self):
        """When analysis_result has a .key attribute (Column object), it
        should be converted via str() before JSON parsing."""
        payload = {"metric": 42}
        column_mock = MagicMock()
        column_mock.key = "analysis_result"
        # Make str(column_mock) return valid JSON
        column_mock.__str__ = MagicMock(return_value=json.dumps(payload))

        analysis = self._mock_analysis(column_mock)
        manager = self._patched_manager_with_analyses([analysis])
        result = manager.get_fundamental_analysis("AAPL")
        assert len(result) == 1
        assert result[0]["analysis_result"] == payload

    def test_result_uses_single_quote_keys(self):
        """Post-PR the dict uses string keys 'id', 'symbol', etc."""
        payload = {"data": "value"}
        analysis = self._mock_analysis(json.dumps(payload))
        manager = self._patched_manager_with_analyses([analysis])
        result = manager.get_fundamental_analysis("AAPL")
        assert len(result) == 1
        item = result[0]
        assert "id" in item
        assert "symbol" in item
        assert "analysis_type" in item
        assert "analysis_result" in item
        assert "period" in item
        assert "created_at" in item

    def test_empty_result_returns_empty_list(self):
        manager = self._patched_manager_with_analyses([])
        result = manager.get_fundamental_analysis("MSFT")
        assert result == []

    def test_exception_returns_empty_list(self):
        manager = _make_manager()
        manager.get_session = MagicMock(side_effect=Exception("db error"))
        result = manager.get_fundamental_analysis("TSLA")
        assert result == []


# ---------------------------------------------------------------------------
# No inner Base class in DatabaseManager
# ---------------------------------------------------------------------------

class TestNoInnerBaseClass:
    """PR removed the inner Base(DeclarativeBase) class from DatabaseManager."""

    def test_no_base_attribute_on_manager(self):
        manager = _make_manager()
        assert not hasattr(manager, "Base"), (
            "DatabaseManager should not have an inner Base class after the PR change"
        )

    def test_module_level_base_exists(self):
        # The module-level Base (declarative_base()) should still exist
        assert hasattr(_db_mod, "Base")


# ---------------------------------------------------------------------------
# get_session_factory() returns None without a configured database
# ---------------------------------------------------------------------------

class TestGetSessionFactoryWithoutDatabase:
    """When DATABASE_URL is not set, get_session_factory must return None."""

    def test_returns_none_when_no_url(self):
        # Patch the engine and SessionLocal to None so factory re-evaluates,
        # and patch DATABASE_URL to None so get_engine returns None.
        with patch.object(_db_mod, "engine", None), \
             patch.object(_db_mod, "SessionLocal", None), \
             patch.object(_db_mod, "DATABASE_URL", None):
            result = get_session_factory()
        # When get_engine returns None (no DB URL), factory should be None
        assert result is None