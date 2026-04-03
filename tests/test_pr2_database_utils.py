"""Tests for refactor_staging/pr2/live_replacements/database.py.

New module added in this PR. Tests cover:
- Pure utility functions: _safe_float, _normalize_symbol, _safe_json_dumps, _safe_json_loads
- DatabaseManager pure logic: check_alerts, calculate_portfolio_value
- DatabaseManager.get_session returns Optional[Session]
- DatabaseManager.health_check / create_tables guard on unavailable DB
"""
from __future__ import annotations

import json
import sys
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock streamlit before importing the staging module.
# conftest.py handles sqlalchemy, yfinance, etc.
# The real config module is fine to use: DATABASE_URL is unset so
# config.database.is_available evaluates to False in CI.
# ---------------------------------------------------------------------------
if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()

import refactor_staging.pr2.live_replacements.database as pr2_db

# Pull out the private utilities directly
_safe_float = pr2_db._safe_float
_normalize_symbol = pr2_db._normalize_symbol
_safe_json_dumps = pr2_db._safe_json_dumps
_safe_json_loads = pr2_db._safe_json_loads
DatabaseManager = pr2_db.DatabaseManager
DatabaseError = pr2_db.DatabaseError


# ===========================================================================
# _safe_float
# ===========================================================================

class TestSafeFloat:
    def test_integer_input(self):
        assert _safe_float(42) == pytest.approx(42.0)

    def test_float_input(self):
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_string_numeric(self):
        assert _safe_float("2.5") == pytest.approx(2.5)

    def test_none_returns_default(self):
        assert _safe_float(None) == pytest.approx(0.0)

    def test_none_with_custom_default(self):
        assert _safe_float(None, default=-1.0) == pytest.approx(-1.0)

    def test_invalid_string_returns_default(self):
        assert _safe_float("abc") == pytest.approx(0.0)

    def test_invalid_string_with_custom_default(self):
        assert _safe_float("bad", default=99.9) == pytest.approx(99.9)

    def test_zero_value(self):
        assert _safe_float(0) == pytest.approx(0.0)

    def test_negative_number(self):
        assert _safe_float(-5.5) == pytest.approx(-5.5)

    def test_empty_string_returns_default(self):
        assert _safe_float("") == pytest.approx(0.0)

    def test_bool_true_returns_one(self):
        # bool is subclass of int in Python; True == 1
        assert _safe_float(True) == pytest.approx(1.0)

    def test_large_number(self):
        assert _safe_float(1_000_000.0) == pytest.approx(1_000_000.0)


# ===========================================================================
# _normalize_symbol
# ===========================================================================

class TestNormalizeSymbol:
    def test_uppercase_passthrough(self):
        assert _normalize_symbol("AAPL") == "AAPL"

    def test_lowercased_to_upper(self):
        assert _normalize_symbol("aapl") == "AAPL"

    def test_mixed_case(self):
        assert _normalize_symbol("AaPl") == "AAPL"

    def test_leading_trailing_whitespace_stripped(self):
        assert _normalize_symbol("  AAPL  ") == "AAPL"

    def test_special_prefix_symbol(self):
        # e.g. index symbol like ^GSPC
        assert _normalize_symbol("^gspc") == "^GSPC"

    def test_symbol_with_dot(self):
        assert _normalize_symbol("brk.b") == "BRK.B"

    def test_empty_string_stays_empty(self):
        # Edge case: normalizing an empty string
        assert _normalize_symbol("") == ""

    def test_whitespace_only(self):
        assert _normalize_symbol("   ") == ""

    def test_numeric_symbol(self):
        assert _normalize_symbol("1234") == "1234"


# ===========================================================================
# _safe_json_dumps
# ===========================================================================

class TestSafeJsonDumps:
    def test_dict_round_trips(self):
        data = {"key": "value", "num": 42}
        result = _safe_json_dumps(data)
        assert json.loads(result) == data

    def test_list_round_trips(self):
        data = [1, 2, 3]
        result = _safe_json_dumps(data)
        assert json.loads(result) == data

    def test_returns_string(self):
        assert isinstance(_safe_json_dumps({}), str)

    def test_none_value(self):
        result = _safe_json_dumps(None)
        assert json.loads(result) is None

    def test_nested_dict(self):
        data = {"outer": {"inner": [1, 2]}}
        result = _safe_json_dumps(data)
        assert json.loads(result) == data

    def test_non_serializable_uses_str_fallback(self):
        # datetime objects are not JSON serializable by default; _safe_json_dumps uses default=str
        from datetime import datetime
        dt = datetime(2026, 4, 1)
        result = _safe_json_dumps({"ts": dt})
        parsed = json.loads(result)
        assert "ts" in parsed
        assert isinstance(parsed["ts"], str)

    def test_sorted_keys(self):
        data = {"z": 1, "a": 2}
        result = _safe_json_dumps(data)
        # With sort_keys=True the "a" key should come before "z"
        parsed_str = result
        assert parsed_str.index('"a"') < parsed_str.index('"z"')


# ===========================================================================
# _safe_json_loads
# ===========================================================================

class TestSafeJsonLoads:
    def test_valid_json_dict(self):
        assert _safe_json_loads('{"key": "val"}', {}) == {"key": "val"}

    def test_valid_json_list(self):
        assert _safe_json_loads('[1,2,3]', []) == [1, 2, 3]

    def test_invalid_json_returns_default(self):
        assert _safe_json_loads("not-json", "fallback") == "fallback"

    def test_none_input_returns_default(self):
        assert _safe_json_loads(None, []) == []  # type: ignore[arg-type]

    def test_empty_string_returns_default(self):
        # Empty string is invalid JSON
        assert _safe_json_loads("", {}) == {}

    def test_valid_null_json(self):
        assert _safe_json_loads("null", "fallback") is None

    def test_valid_number_json(self):
        assert _safe_json_loads("42", 0) == 42


# ===========================================================================
# DatabaseManager.get_session
# ===========================================================================

class TestDatabaseManagerGetSession:
    def test_returns_none_when_factory_unavailable(self):
        manager = DatabaseManager()
        with patch.object(pr2_db, "get_session_factory", return_value=None):
            assert manager.get_session() is None

    def test_returns_session_when_factory_available(self):
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        manager = DatabaseManager()
        with patch.object(pr2_db, "get_session_factory", return_value=mock_factory):
            assert manager.get_session() is mock_session


# ===========================================================================
# DatabaseManager.health_check
# ===========================================================================

class TestDatabaseManagerHealthCheck:
    def test_returns_false_when_db_unavailable(self):
        manager = DatabaseManager()
        with patch.object(pr2_db, "get_db_session", side_effect=DatabaseError("unavailable")):
            assert manager.health_check() is False

    def test_returns_true_when_db_available(self):
        manager = DatabaseManager()

        @contextmanager
        def _fake_session():
            mock_sess = MagicMock()
            mock_sess.execute.return_value = None
            yield mock_sess

        with patch.object(pr2_db, "get_db_session", _fake_session):
            assert manager.health_check() is True


# ===========================================================================
# DatabaseManager.create_tables
# ===========================================================================

class TestCreateTables:
    def test_returns_false_when_engine_none(self):
        manager = DatabaseManager()
        with patch.object(pr2_db, "get_engine", return_value=None):
            result = manager.create_tables()
        assert result is False

    def test_returns_true_when_engine_available(self):
        manager = DatabaseManager()
        mock_engine = MagicMock()
        with patch.object(pr2_db, "get_engine", return_value=mock_engine), \
             patch.object(pr2_db.Base.metadata, "create_all"):
            result = manager.create_tables()
        assert result is True


# ===========================================================================
# DatabaseManager.check_alerts (pure logic test)
# ===========================================================================

class TestCheckAlerts:
    def setup_method(self):
        self.manager = DatabaseManager()

    def _alert(self, symbol, alert_type, target_price, alert_id=None):
        return {
            "id": alert_id or str(uuid.uuid4()),
            "user_id": "user1",
            "symbol": symbol,
            "alert_type": alert_type,
            "target_price": target_price,
            "created_at": None,
        }

    def test_above_alert_triggered_when_price_exceeds_target(self):
        alerts = [self._alert("AAPL", "above", 150.0, "alert-1")]
        with patch.object(self.manager, "get_active_alerts", return_value=alerts), \
             patch.object(self.manager, "deactivate_alert", return_value=True):
            triggered = self.manager.check_alerts({"AAPL": 155.0})
        assert len(triggered) == 1
        assert triggered[0]["symbol"] == "AAPL"

    def test_above_alert_not_triggered_when_price_below_target(self):
        alerts = [self._alert("AAPL", "above", 200.0)]
        with patch.object(self.manager, "get_active_alerts", return_value=alerts), \
             patch.object(self.manager, "deactivate_alert", return_value=True):
            triggered = self.manager.check_alerts({"AAPL": 150.0})
        assert triggered == []

    def test_below_alert_triggered_when_price_drops_below_target(self):
        alerts = [self._alert("TSLA", "below", 100.0, "alert-2")]
        with patch.object(self.manager, "get_active_alerts", return_value=alerts), \
             patch.object(self.manager, "deactivate_alert", return_value=True):
            triggered = self.manager.check_alerts({"TSLA": 95.0})
        assert len(triggered) == 1

    def test_below_alert_not_triggered_when_price_above_target(self):
        alerts = [self._alert("TSLA", "below", 100.0)]
        with patch.object(self.manager, "get_active_alerts", return_value=alerts), \
             patch.object(self.manager, "deactivate_alert", return_value=True):
            triggered = self.manager.check_alerts({"TSLA": 110.0})
        assert triggered == []

    def test_symbol_not_in_prices_skipped(self):
        alerts = [self._alert("MISSING", "above", 100.0)]
        with patch.object(self.manager, "get_active_alerts", return_value=alerts), \
             patch.object(self.manager, "deactivate_alert", return_value=True):
            triggered = self.manager.check_alerts({"AAPL": 200.0})
        assert triggered == []

    def test_at_exact_target_price_triggers_above_alert(self):
        alerts = [self._alert("AAPL", "above", 150.0, "alert-3")]
        with patch.object(self.manager, "get_active_alerts", return_value=alerts), \
             patch.object(self.manager, "deactivate_alert", return_value=True):
            triggered = self.manager.check_alerts({"AAPL": 150.0})
        assert len(triggered) == 1

    def test_at_exact_target_price_triggers_below_alert(self):
        alerts = [self._alert("TSLA", "below", 100.0, "alert-4")]
        with patch.object(self.manager, "get_active_alerts", return_value=alerts), \
             patch.object(self.manager, "deactivate_alert", return_value=True):
            triggered = self.manager.check_alerts({"TSLA": 100.0})
        assert len(triggered) == 1

    def test_deactivate_called_for_triggered_alert(self):
        alert_id = str(uuid.uuid4())
        alerts = [self._alert("AAPL", "above", 100.0, alert_id)]
        with patch.object(self.manager, "get_active_alerts", return_value=alerts), \
             patch.object(self.manager, "deactivate_alert", return_value=True) as mock_deact:
            self.manager.check_alerts({"AAPL": 150.0})
        mock_deact.assert_called_once_with(alert_id)

    def test_returns_empty_list_when_no_alerts(self):
        with patch.object(self.manager, "get_active_alerts", return_value=[]):
            triggered = self.manager.check_alerts({"AAPL": 150.0})
        assert triggered == []


# ===========================================================================
# DatabaseManager.calculate_portfolio_value (pure math test)
# ===========================================================================

class TestCalculatePortfolioValue:
    def setup_method(self):
        self.manager = DatabaseManager()

    def _holding(self, symbol, quantity, average_cost, notes=""):
        return {
            "id": str(uuid.uuid4()),
            "symbol": symbol,
            "quantity": quantity,
            "average_cost": average_cost,
            "purchase_date": None,
            "notes": notes,
        }

    def test_basic_gain_calculation(self):
        holdings = [self._holding("AAPL", 10.0, 100.0)]
        with patch.object(self.manager, "get_portfolio_holdings", return_value=holdings):
            result = self.manager.calculate_portfolio_value("portfolio-1", {"AAPL": 150.0})
        assert result["total_value"] == pytest.approx(1500.0)
        assert result["total_cost"] == pytest.approx(1000.0)
        assert result["total_gain_loss"] == pytest.approx(500.0)
        assert result["total_gain_loss_pct"] == pytest.approx(50.0)

    def test_loss_calculation(self):
        holdings = [self._holding("TSLA", 5.0, 200.0)]
        with patch.object(self.manager, "get_portfolio_holdings", return_value=holdings):
            result = self.manager.calculate_portfolio_value("portfolio-2", {"TSLA": 150.0})
        assert result["total_gain_loss"] == pytest.approx(-250.0)
        assert result["total_gain_loss_pct"] < 0

    def test_uses_average_cost_when_price_not_in_current_prices(self):
        holdings = [self._holding("UNKNOWN", 10.0, 50.0)]
        with patch.object(self.manager, "get_portfolio_holdings", return_value=holdings):
            result = self.manager.calculate_portfolio_value("portfolio-3", {})
        # Should use average_cost as fallback price
        assert result["total_value"] == pytest.approx(500.0)
        assert result["total_gain_loss"] == pytest.approx(0.0)

    def test_empty_holdings_returns_zeros(self):
        with patch.object(self.manager, "get_portfolio_holdings", return_value=[]):
            result = self.manager.calculate_portfolio_value("portfolio-empty", {"AAPL": 100.0})
        assert result["total_value"] == pytest.approx(0.0)
        assert result["total_cost"] == pytest.approx(0.0)
        assert result["total_gain_loss_pct"] == pytest.approx(0.0)

    def test_multiple_holdings(self):
        holdings = [
            self._holding("AAPL", 10.0, 100.0),
            self._holding("TSLA", 5.0, 200.0),
        ]
        prices = {"AAPL": 150.0, "TSLA": 250.0}
        with patch.object(self.manager, "get_portfolio_holdings", return_value=holdings):
            result = self.manager.calculate_portfolio_value("portfolio-multi", prices)
        # AAPL: 10*150=1500, TSLA: 5*250=1250 → total 2750
        assert result["total_value"] == pytest.approx(2750.0)
        # holdings detail count
        assert len(result["holdings"]) == 2

    def test_returns_error_structure_on_exception(self):
        with patch.object(self.manager, "get_portfolio_holdings", side_effect=RuntimeError("db down")):
            result = self.manager.calculate_portfolio_value("portfolio-bad", {})
        assert result["total_value"] == pytest.approx(0.0)
        assert result["holdings"] == []


# ===========================================================================
# DatabaseManager.create_market_alert - invalid alert_type validation
# ===========================================================================

class TestCreateMarketAlertValidation:
    def setup_method(self):
        self.manager = DatabaseManager()

    def test_invalid_alert_type_returns_false(self):
        with patch.object(pr2_db, "get_db_session"):
            result = self.manager.create_market_alert("user1", "AAPL", "invalid_type", 100.0)
        assert result is False

    def test_valid_above_type_proceeds_to_db(self):
        @contextmanager
        def _fake_session():
            mock_sess = MagicMock()
            mock_sess.add = MagicMock()
            yield mock_sess

        with patch.object(pr2_db, "get_db_session", _fake_session), \
             patch.object(pr2_db, "MarketAlerts", MagicMock(return_value=MagicMock())):
            result = self.manager.create_market_alert("user1", "AAPL", "above", 150.0)
        assert result is True

    def test_valid_below_type_proceeds_to_db(self):
        @contextmanager
        def _fake_session():
            mock_sess = MagicMock()
            mock_sess.add = MagicMock()
            yield mock_sess

        with patch.object(pr2_db, "get_db_session", _fake_session), \
             patch.object(pr2_db, "MarketAlerts", MagicMock(return_value=MagicMock())):
            result = self.manager.create_market_alert("user1", "TSLA", "below", 100.0)
        assert result is True

    def test_case_insensitive_alert_type(self):
        """Alert type should be normalized to lowercase."""
        @contextmanager
        def _fake_session():
            yield MagicMock()

        with patch.object(pr2_db, "get_db_session", _fake_session), \
             patch.object(pr2_db, "MarketAlerts", MagicMock(return_value=MagicMock())):
            result = self.manager.create_market_alert("user1", "AAPL", "ABOVE", 150.0)
        assert result is True


# ===========================================================================
# get_db_session context manager
# ===========================================================================

class TestGetDbSession:
    def test_raises_database_error_when_factory_none(self):
        with patch.object(pr2_db, "get_session_factory", return_value=None):
            with pytest.raises(DatabaseError):
                with pr2_db.get_db_session():
                    pass

    def test_commits_on_success(self):
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        with patch.object(pr2_db, "get_session_factory", return_value=mock_factory):
            with pr2_db.get_db_session() as session:
                pass
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_rolls_back_on_exception(self):
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        with patch.object(pr2_db, "get_session_factory", return_value=mock_factory):
            with pytest.raises(DatabaseError):
                with pr2_db.get_db_session() as session:
                    raise ValueError("something bad")
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_reraises_database_error_unchanged(self):
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        original_error = DatabaseError("db error")
        with patch.object(pr2_db, "get_session_factory", return_value=mock_factory):
            with pytest.raises(DatabaseError) as exc_info:
                with pr2_db.get_db_session():
                    raise original_error
        assert exc_info.value is original_error