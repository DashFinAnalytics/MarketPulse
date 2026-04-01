"""Tests for database.py – covers only the code changed/added in this PR."""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Pure utility functions
# ---------------------------------------------------------------------------

class TestNormalizeSymbol:
    def test_uppercase(self):
        from database import _normalize_symbol
        assert _normalize_symbol("aapl") == "AAPL"

    def test_strips_whitespace(self):
        from database import _normalize_symbol
        assert _normalize_symbol("  msft  ") == "MSFT"

    def test_already_uppercase(self):
        from database import _normalize_symbol
        assert _normalize_symbol("GOOG") == "GOOG"

    def test_mixed_case_and_spaces(self):
        from database import _normalize_symbol
        assert _normalize_symbol(" nVdA ") == "NVDA"

    def test_empty_string(self):
        from database import _normalize_symbol
        # strip().upper() on empty string is still empty
        assert _normalize_symbol("") == ""

    def test_special_characters_preserved(self):
        # Symbols like ^VIX or GC=F should only be stripped/uppercased
        from database import _normalize_symbol
        assert _normalize_symbol("^vix") == "^VIX"


class TestSafeFloat:
    def test_integer_value(self):
        from database import _safe_float
        assert _safe_float(42) == 42.0

    def test_float_value(self):
        from database import _safe_float
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_string_numeric(self):
        from database import _safe_float
        assert _safe_float("2.5") == 2.5

    def test_none_returns_default(self):
        from database import _safe_float
        assert _safe_float(None) == 0.0

    def test_none_with_custom_default(self):
        from database import _safe_float
        assert _safe_float(None, default=99.9) == 99.9

    def test_non_numeric_string_returns_default(self):
        from database import _safe_float
        assert _safe_float("not-a-number") == 0.0

    def test_non_numeric_string_with_custom_default(self):
        from database import _safe_float
        assert _safe_float("bad", default=-1.0) == -1.0

    def test_zero(self):
        from database import _safe_float
        assert _safe_float(0) == 0.0

    def test_negative_value(self):
        from database import _safe_float
        assert _safe_float(-5.5) == pytest.approx(-5.5)

    def test_bool_true(self):
        # bool is a subclass of int in Python; float(True) == 1.0
        from database import _safe_float
        assert _safe_float(True) == 1.0


class TestSafeJsonDumps:
    def test_dict(self):
        from database import _safe_json_dumps
        result = _safe_json_dumps({"a": 1})
        assert json.loads(result) == {"a": 1}

    def test_list(self):
        from database import _safe_json_dumps
        result = _safe_json_dumps(["AAPL", "MSFT"])
        assert json.loads(result) == ["AAPL", "MSFT"]

    def test_empty_dict(self):
        from database import _safe_json_dumps
        result = _safe_json_dumps({})
        assert result == "{}"

    def test_sort_keys(self):
        from database import _safe_json_dumps
        result = _safe_json_dumps({"z": 1, "a": 2})
        parsed = json.loads(result)
        # Keys should be sorted in the output
        assert list(parsed.keys()) == sorted(parsed.keys())

    def test_datetime_serialized_as_string(self):
        from database import _safe_json_dumps
        dt = datetime(2024, 1, 15, 12, 0, 0)
        result = _safe_json_dumps({"ts": dt})
        assert "2024" in result  # datetime converted via default=str

    def test_none_value(self):
        from database import _safe_json_dumps
        result = _safe_json_dumps(None)
        assert result == "null"


class TestSafeJsonLoads:
    def test_valid_json_dict(self):
        from database import _safe_json_loads
        assert _safe_json_loads('{"a": 1}', {}) == {"a": 1}

    def test_valid_json_list(self):
        from database import _safe_json_loads
        assert _safe_json_loads('["AAPL", "GOOG"]', []) == ["AAPL", "GOOG"]

    def test_invalid_json_returns_default(self):
        from database import _safe_json_loads
        assert _safe_json_loads("not json", "fallback") == "fallback"

    def test_none_returns_default(self):
        from database import _safe_json_loads
        assert _safe_json_loads(None, []) == []

    def test_empty_string_returns_default(self):
        from database import _safe_json_loads
        assert _safe_json_loads("", {}) == {}

    def test_partial_json_returns_default(self):
        from database import _safe_json_loads
        assert _safe_json_loads('{"key": ', None) is None

    def test_valid_json_null(self):
        from database import _safe_json_loads
        assert _safe_json_loads("null", "default") is None

    def test_roundtrip(self):
        from database import _safe_json_dumps, _safe_json_loads
        data = {"symbols": ["AAPL", "TSLA"], "count": 2}
        serialized = _safe_json_dumps(data)
        assert _safe_json_loads(serialized, {}) == data


# ---------------------------------------------------------------------------
# _engine_kwargs
# ---------------------------------------------------------------------------

class TestEngineKwargs:
    def test_sqlite_url_returns_check_same_thread(self):
        from database import _engine_kwargs
        with patch("database._database_url", return_value="sqlite:///:memory:"), \
             patch("database.config") as mock_cfg:
            mock_cfg.database.echo = False
            mock_cfg.database.pool_size = 5
            mock_cfg.database.max_overflow = 10
            mock_cfg.database.pool_timeout = 30
            mock_cfg.database.pool_recycle = 3600
            result = _engine_kwargs()

        assert result["connect_args"] == {"check_same_thread": False}
        assert "pool_size" not in result

    def test_postgres_url_includes_pool_settings(self):
        from database import _engine_kwargs
        with patch("database._database_url",
                   return_value="postgresql://user:pass@localhost/db"), \
             patch("database.config") as mock_cfg:
            mock_cfg.database.echo = False
            mock_cfg.database.pool_size = 5
            mock_cfg.database.max_overflow = 10
            mock_cfg.database.pool_timeout = 30
            mock_cfg.database.pool_recycle = 3600
            result = _engine_kwargs()

        assert result["pool_size"] == 5
        assert result["max_overflow"] == 10
        assert result["pool_timeout"] == 30
        assert result["pool_recycle"] == 3600
        assert "connect_args" not in result

    def test_echo_setting_propagated(self):
        from database import _engine_kwargs
        with patch("database._database_url", return_value="sqlite:///test.db"), \
             patch("database.config") as mock_cfg:
            mock_cfg.database.echo = True
            result = _engine_kwargs()

        assert result["echo"] is True


# ---------------------------------------------------------------------------
# get_engine
# ---------------------------------------------------------------------------

class TestGetEngine:
    def setup_method(self):
        """Reset module-level globals before each test."""
        import database
        database.engine = None
        database.SessionLocal = None

    def teardown_method(self):
        import database
        if database.engine is not None:
            try:
                database.engine.dispose()
            except Exception:
                pass
        database.engine = None
        database.SessionLocal = None

    def test_returns_none_when_database_unavailable(self):
        import database
        with patch("database.config") as mock_cfg:
            mock_cfg.database.is_available = False
            mock_cfg.database.is_configured = False
            mock_cfg.database.enabled = False
            result = database.get_engine()
        assert result is None

    def test_returns_none_for_asyncpg_url(self):
        import database
        with patch("database.config") as mock_cfg:
            mock_cfg.database.is_available = True
            mock_cfg.database.url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_cfg.database.echo = False
            with patch("database._database_url",
                       return_value="postgresql+asyncpg://user:pass@localhost/db"):
                result = database.get_engine()
        assert result is None

    def test_creates_engine_for_sqlite(self):
        import database
        with patch("database.config") as mock_cfg:
            mock_cfg.database.is_available = True
            mock_cfg.database.echo = False
            mock_cfg.database.pool_size = 5
            mock_cfg.database.max_overflow = 10
            mock_cfg.database.pool_timeout = 30
            mock_cfg.database.pool_recycle = 3600
            with patch("database._database_url",
                       return_value="sqlite:///:memory:"):
                result = database.get_engine()
        assert result is not None
        result.dispose()

    def test_returns_existing_engine_without_recreating(self):
        import database
        from sqlalchemy import create_engine as _ce
        sentinel = _ce("sqlite:///:memory:", future=True)
        database.engine = sentinel
        result = database.get_engine()
        assert result is sentinel
        sentinel.dispose()
        database.engine = None

    def test_force_refresh_disposes_old_engine(self):
        import database
        mock_old_engine = MagicMock()
        database.engine = mock_old_engine
        with patch("database.config") as mock_cfg:
            mock_cfg.database.is_available = False
            mock_cfg.database.is_configured = False
            mock_cfg.database.enabled = False
            database.get_engine(force_refresh=True)
        mock_old_engine.dispose.assert_called_once()
        assert database.engine is None

    def test_returns_none_when_url_is_none(self):
        import database
        with patch("database.config") as mock_cfg:
            mock_cfg.database.is_available = True
            with patch("database._database_url", return_value=None):
                result = database.get_engine()
        assert result is None


# ---------------------------------------------------------------------------
# get_session_factory
# ---------------------------------------------------------------------------

class TestGetSessionFactory:
    def setup_method(self):
        import database
        database.engine = None
        database.SessionLocal = None

    def teardown_method(self):
        import database
        if database.engine is not None:
            try:
                database.engine.dispose()
            except Exception:
                pass
        database.engine = None
        database.SessionLocal = None

    def test_returns_none_when_engine_unavailable(self):
        import database
        with patch("database.get_engine", return_value=None):
            result = database.get_session_factory()
        assert result is None

    def test_returns_sessionmaker_when_engine_available(self):
        import database
        from sqlalchemy import create_engine as _ce
        from sqlalchemy.orm import sessionmaker as _sm
        mock_engine = _ce("sqlite:///:memory:", future=True)
        with patch("database.get_engine", return_value=mock_engine):
            result = database.get_session_factory()
        assert result is not None
        assert isinstance(result, _sm)
        mock_engine.dispose()

    def test_returns_cached_session_local(self):
        import database
        from sqlalchemy.orm import sessionmaker as _sm
        mock_factory = MagicMock(spec=_sm)
        database.SessionLocal = mock_factory
        result = database.get_session_factory()
        assert result is mock_factory
        database.SessionLocal = None


# ---------------------------------------------------------------------------
# get_db_session context manager
# ---------------------------------------------------------------------------

class TestGetDbSession:
    def test_raises_database_error_when_factory_none(self):
        from database import get_db_session
        from utils.exceptions import DatabaseError
        with patch("database.get_session_factory", return_value=None):
            with pytest.raises(DatabaseError, match="Database session unavailable"):
                with get_db_session():
                    pass

    def test_commits_on_success(self):
        from database import get_db_session
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        with patch("database.get_session_factory", return_value=mock_factory):
            with get_db_session() as session:
                assert session is mock_session
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_rolls_back_on_generic_exception(self):
        from database import get_db_session
        from utils.exceptions import DatabaseError
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        with patch("database.get_session_factory", return_value=mock_factory):
            with pytest.raises(DatabaseError):
                with get_db_session():
                    raise ValueError("boom")
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_re_raises_database_error_directly(self):
        from database import get_db_session
        from utils.exceptions import DatabaseError
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        with patch("database.get_session_factory", return_value=mock_factory):
            with pytest.raises(DatabaseError, match="original"):
                with get_db_session():
                    raise DatabaseError("original")
        mock_session.rollback.assert_called_once()

    def test_session_always_closed(self):
        from database import get_db_session
        from utils.exceptions import DatabaseError
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        with patch("database.get_session_factory", return_value=mock_factory):
            try:
                with get_db_session():
                    raise RuntimeError("any error")
            except DatabaseError:
                pass
        mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# DatabaseManager.health_check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_returns_true_on_success(self, db_manager):
        assert db_manager.health_check() is True

    def test_returns_false_on_error(self):
        from database import DatabaseManager
        from utils.exceptions import DatabaseError
        mgr = DatabaseManager()
        with patch("database.get_db_session",
                   side_effect=DatabaseError("db down")):
            assert mgr.health_check() is False


# ---------------------------------------------------------------------------
# DatabaseManager.store_financial_data
# ---------------------------------------------------------------------------

class TestStoreFinancialData:
    def test_stores_record(self, db_manager, patched_db_session):
        from database import FinancialData
        result = db_manager.store_financial_data(
            "aapl",
            {"price": 150.0, "change": 1.5, "change_pct": 1.0, "volume": 1000000.0},
            "index",
        )
        assert result is True
        patched_db_session.flush()
        record = patched_db_session.query(FinancialData).first()
        assert record is not None
        assert record.symbol == "AAPL"  # normalized
        assert record.price == pytest.approx(150.0)

    def test_normalizes_symbol(self, db_manager, patched_db_session):
        from database import FinancialData
        db_manager.store_financial_data(
            " msft ", {"price": 300.0, "change": 0.0, "change_pct": 0.0}, "index"
        )
        patched_db_session.flush()
        record = patched_db_session.query(FinancialData).first()
        assert record.symbol == "MSFT"

    def test_handles_missing_optional_fields(self, db_manager, patched_db_session):
        from database import FinancialData
        result = db_manager.store_financial_data(
            "GOOG", {"price": 2800.0, "change": 0.0, "change_pct": 0.0}, "index"
        )
        assert result is True
        patched_db_session.flush()
        record = patched_db_session.query(FinancialData).first()
        assert record.volume == pytest.approx(0.0)  # default

    def test_returns_false_on_db_error(self):
        from database import DatabaseManager
        from utils.exceptions import DatabaseError
        mgr = DatabaseManager()
        with patch("database.get_db_session",
                   side_effect=DatabaseError("write failed")):
            result = mgr.store_financial_data(
                "ERR", {"price": 1.0, "change": 0.0, "change_pct": 0.0}, "index"
            )
        assert result is False

    def test_none_price_uses_safe_default(self, db_manager, patched_db_session):
        from database import FinancialData
        db_manager.store_financial_data(
            "XYZ", {"price": None, "change": None, "change_pct": None}, "index"
        )
        patched_db_session.flush()
        record = patched_db_session.query(FinancialData).first()
        assert record.price == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# DatabaseManager.get_historical_data
# ---------------------------------------------------------------------------

class TestGetHistoricalData:
    def test_returns_records_within_window(self, db_manager, patched_db_session):
        from database import FinancialData
        recent = FinancialData(
            symbol="SPY", price=400.0, change=1.0, change_pct=0.25,
            volume=5000000.0, data_type="index",
            timestamp=datetime.utcnow() - timedelta(hours=1),
        )
        old = FinancialData(
            symbol="SPY", price=350.0, change=-1.0, change_pct=-0.3,
            volume=3000000.0, data_type="index",
            timestamp=datetime.utcnow() - timedelta(hours=30),
        )
        patched_db_session.add(recent)
        patched_db_session.add(old)
        patched_db_session.flush()

        result = db_manager.get_historical_data("spy", hours=24)
        assert len(result) == 1
        assert result[0]["symbol"] == "SPY"
        assert result[0]["price"] == pytest.approx(400.0)

    def test_returns_empty_list_when_no_data(self, db_manager):
        result = db_manager.get_historical_data("NONEXISTENT")
        assert result == []

    def test_normalizes_symbol(self, db_manager, patched_db_session):
        from database import FinancialData
        record = FinancialData(
            symbol="NVDA", price=500.0, change=5.0, change_pct=1.0,
            volume=1000000.0, data_type="index",
            timestamp=datetime.utcnow() - timedelta(minutes=10),
        )
        patched_db_session.add(record)
        patched_db_session.flush()

        result = db_manager.get_historical_data(" nvda ")
        assert len(result) == 1

    def test_returns_empty_list_on_db_error(self):
        from database import DatabaseManager
        from utils.exceptions import DatabaseError
        mgr = DatabaseManager()
        with patch("database.get_db_session", side_effect=DatabaseError("read failed")):
            result = mgr.get_historical_data("SPY")
        assert result == []


# ---------------------------------------------------------------------------
# DatabaseManager.save_user_preferences / get_user_preferences
# ---------------------------------------------------------------------------

class TestUserPreferences:
    def test_save_creates_new_preferences(self, db_manager, patched_db_session):
        from database import UserPreferences
        result = db_manager.save_user_preferences(
            "user_1", {"auto_refresh": True, "refresh_interval": 60}
        )
        assert result is True
        patched_db_session.flush()
        prefs = patched_db_session.query(UserPreferences).filter_by(user_id="user_1").first()
        assert prefs is not None
        assert prefs.auto_refresh is True
        assert prefs.refresh_interval == 60

    def test_save_updates_existing_preferences(self, db_manager, patched_db_session):
        from database import UserPreferences
        db_manager.save_user_preferences("user_2", {"auto_refresh": False, "refresh_interval": 30})
        patched_db_session.flush()
        db_manager.save_user_preferences("user_2", {"auto_refresh": True, "refresh_interval": 120})
        patched_db_session.flush()

        prefs = patched_db_session.query(UserPreferences).filter_by(user_id="user_2").all()
        assert len(prefs) == 1
        assert prefs[0].auto_refresh is True
        assert prefs[0].refresh_interval == 120

    def test_get_returns_none_for_unknown_user(self, db_manager):
        result = db_manager.get_user_preferences("nonexistent_user")
        assert result is None

    def test_get_returns_preferences_dict(self, db_manager, patched_db_session):
        db_manager.save_user_preferences(
            "user_3", {"auto_refresh": True, "refresh_interval": 45}
        )
        patched_db_session.flush()
        result = db_manager.get_user_preferences("user_3")
        assert result is not None
        assert result["auto_refresh"] is True
        assert result["refresh_interval"] == 45

    def test_favorite_symbols_serialized_and_deserialized(self, db_manager, patched_db_session):
        symbols = ["AAPL", "GOOG", "MSFT"]
        db_manager.save_user_preferences(
            "user_4", {"favorite_symbols": symbols}
        )
        patched_db_session.flush()
        result = db_manager.get_user_preferences("user_4")
        assert result["favorite_symbols"] == symbols

    def test_save_returns_false_on_error(self):
        from database import DatabaseManager
        from utils.exceptions import DatabaseError
        mgr = DatabaseManager()
        with patch("database.get_db_session", side_effect=DatabaseError("write error")):
            result = mgr.save_user_preferences("u", {"auto_refresh": True})
        assert result is False


# ---------------------------------------------------------------------------
# DatabaseManager.create_market_alert / get_active_alerts / deactivate_alert
# ---------------------------------------------------------------------------

class TestMarketAlerts:
    def test_create_valid_alert(self, db_manager, patched_db_session):
        from database import MarketAlerts
        result = db_manager.create_market_alert("user_a", "aapl", "above", 200.0)
        assert result is True
        patched_db_session.flush()
        alert = patched_db_session.query(MarketAlerts).first()
        assert alert is not None
        assert alert.symbol == "AAPL"
        assert alert.alert_type == "above"
        assert alert.target_price == pytest.approx(200.0)

    def test_create_alert_normalizes_alert_type(self, db_manager, patched_db_session):
        from database import MarketAlerts
        db_manager.create_market_alert("user_b", "SPY", "BELOW", 300.0)
        patched_db_session.flush()
        alert = patched_db_session.query(MarketAlerts).first()
        assert alert.alert_type == "below"

    def test_create_alert_rejects_invalid_type(self, db_manager):
        result = db_manager.create_market_alert("user_c", "SPY", "sideways", 100.0)
        assert result is False

    def test_get_active_alerts_returns_active_only(self, db_manager, patched_db_session):
        from database import MarketAlerts
        active = MarketAlerts(
            user_id="user_d", symbol="TSLA", alert_type="above",
            target_price=300.0, is_active=True,
        )
        inactive = MarketAlerts(
            user_id="user_d", symbol="TSLA", alert_type="below",
            target_price=100.0, is_active=False,
        )
        patched_db_session.add(active)
        patched_db_session.add(inactive)
        patched_db_session.flush()

        result = db_manager.get_active_alerts()
        assert len(result) == 1
        assert result[0]["alert_type"] == "above"

    def test_get_active_alerts_filtered_by_user(self, db_manager, patched_db_session):
        from database import MarketAlerts
        patched_db_session.add(MarketAlerts(
            user_id="alice", symbol="AMZN", alert_type="above",
            target_price=150.0, is_active=True,
        ))
        patched_db_session.add(MarketAlerts(
            user_id="bob", symbol="AMZN", alert_type="below",
            target_price=80.0, is_active=True,
        ))
        patched_db_session.flush()

        result = db_manager.get_active_alerts(user_id="alice")
        assert len(result) == 1
        assert result[0]["user_id"] == "alice"

    def test_deactivate_alert_sets_is_active_false(self, db_manager, patched_db_session):
        from database import MarketAlerts
        alert = MarketAlerts(
            user_id="user_e", symbol="META", alert_type="above",
            target_price=500.0, is_active=True,
        )
        patched_db_session.add(alert)
        patched_db_session.flush()

        alert_id = str(alert.id)
        result = db_manager.deactivate_alert(alert_id)
        assert result is True
        patched_db_session.flush()
        updated = patched_db_session.query(MarketAlerts).filter_by(id=alert.id).first()
        assert updated.is_active is False

    def test_deactivate_nonexistent_alert_returns_false(self, db_manager):
        result = db_manager.deactivate_alert(str(uuid.uuid4()))
        assert result is False


# ---------------------------------------------------------------------------
# DatabaseManager.check_alerts
# ---------------------------------------------------------------------------

class TestCheckAlerts:
    def test_triggers_above_alert(self, db_manager, patched_db_session):
        from database import MarketAlerts
        alert = MarketAlerts(
            user_id="user_f", symbol="AAPL", alert_type="above",
            target_price=150.0, is_active=True,
        )
        patched_db_session.add(alert)
        patched_db_session.flush()

        triggered = db_manager.check_alerts({"AAPL": 155.0})
        assert len(triggered) == 1
        assert triggered[0]["symbol"] == "AAPL"
        assert triggered[0]["alert_type"] == "above"
        assert triggered[0]["current_price"] == pytest.approx(155.0)

    def test_triggers_below_alert(self, db_manager, patched_db_session):
        from database import MarketAlerts
        alert = MarketAlerts(
            user_id="user_g", symbol="SPY", alert_type="below",
            target_price=400.0, is_active=True,
        )
        patched_db_session.add(alert)
        patched_db_session.flush()

        triggered = db_manager.check_alerts({"SPY": 395.0})
        assert len(triggered) == 1
        assert triggered[0]["alert_type"] == "below"

    def test_does_not_trigger_when_condition_not_met(self, db_manager, patched_db_session):
        from database import MarketAlerts
        patched_db_session.add(MarketAlerts(
            user_id="user_h", symbol="GOOG", alert_type="above",
            target_price=200.0, is_active=True,
        ))
        patched_db_session.flush()
        triggered = db_manager.check_alerts({"GOOG": 190.0})
        assert triggered == []

    def test_skips_symbols_not_in_current_prices(self, db_manager, patched_db_session):
        from database import MarketAlerts
        patched_db_session.add(MarketAlerts(
            user_id="user_i", symbol="NVDA", alert_type="above",
            target_price=100.0, is_active=True,
        ))
        patched_db_session.flush()
        triggered = db_manager.check_alerts({})
        assert triggered == []

    def test_deactivates_alert_after_trigger(self, db_manager, patched_db_session):
        from database import MarketAlerts
        alert = MarketAlerts(
            user_id="user_j", symbol="TSLA", alert_type="above",
            target_price=300.0, is_active=True,
        )
        patched_db_session.add(alert)
        patched_db_session.flush()

        db_manager.check_alerts({"TSLA": 350.0})
        patched_db_session.flush()

        updated = patched_db_session.query(MarketAlerts).filter_by(id=alert.id).first()
        assert updated.is_active is False

    def test_at_exact_target_price_triggers_above(self, db_manager, patched_db_session):
        from database import MarketAlerts
        patched_db_session.add(MarketAlerts(
            user_id="u", symbol="XYZ", alert_type="above",
            target_price=100.0, is_active=True,
        ))
        patched_db_session.flush()
        triggered = db_manager.check_alerts({"XYZ": 100.0})
        assert len(triggered) == 1

    def test_at_exact_target_price_triggers_below(self, db_manager, patched_db_session):
        from database import MarketAlerts
        patched_db_session.add(MarketAlerts(
            user_id="u2", symbol="ABC", alert_type="below",
            target_price=50.0, is_active=True,
        ))
        patched_db_session.flush()
        triggered = db_manager.check_alerts({"ABC": 50.0})
        assert len(triggered) == 1


# ---------------------------------------------------------------------------
# DatabaseManager.create_portfolio / get_user_portfolios
# ---------------------------------------------------------------------------

class TestPortfolio:
    def test_create_portfolio_returns_id(self, db_manager, patched_db_session):
        portfolio_id = db_manager.create_portfolio(
            "user_k", "My Portfolio", description="Test", cash_balance=1000.0
        )
        assert portfolio_id is not None
        # Should be a valid UUID string
        uuid.UUID(portfolio_id)

    def test_get_user_portfolios_returns_created(self, db_manager, patched_db_session):
        db_manager.create_portfolio("user_l", "Portfolio A")
        db_manager.create_portfolio("user_l", "Portfolio B")
        patched_db_session.flush()

        result = db_manager.get_user_portfolios("user_l")
        assert len(result) == 2
        names = {p["name"] for p in result}
        assert "Portfolio A" in names
        assert "Portfolio B" in names

    def test_get_user_portfolios_empty_for_unknown_user(self, db_manager):
        result = db_manager.get_user_portfolios("nobody")
        assert result == []

    def test_create_portfolio_returns_none_on_error(self):
        from database import DatabaseManager
        from utils.exceptions import DatabaseError
        mgr = DatabaseManager()
        with patch("database.get_db_session", side_effect=DatabaseError("db error")):
            result = mgr.create_portfolio("u", "P")
        assert result is None


# ---------------------------------------------------------------------------
# DatabaseManager.add_holding / sell_holding / get_portfolio_holdings
# ---------------------------------------------------------------------------

class TestPortfolioHoldings:
    def _create_portfolio(self, db_manager, patched_db_session, user="test_user"):
        return db_manager.create_portfolio(user, "Test Portfolio")

    def test_add_holding_creates_new_holding(self, db_manager, patched_db_session):
        portfolio_id = self._create_portfolio(db_manager, patched_db_session)
        patched_db_session.flush()

        result = db_manager.add_holding(portfolio_id, "aapl", 10.0, 150.0)
        assert result is True
        patched_db_session.flush()

        holdings = db_manager.get_portfolio_holdings(portfolio_id)
        assert len(holdings) == 1
        assert holdings[0]["symbol"] == "AAPL"
        assert holdings[0]["quantity"] == pytest.approx(10.0)
        assert holdings[0]["average_cost"] == pytest.approx(150.0)

    def test_add_holding_averages_cost_for_existing(self, db_manager, patched_db_session):
        portfolio_id = self._create_portfolio(db_manager, patched_db_session)
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, "AAPL", 10.0, 100.0)  # cost=100
        patched_db_session.flush()
        db_manager.add_holding(portfolio_id, "AAPL", 10.0, 200.0)  # cost=200
        patched_db_session.flush()

        holdings = db_manager.get_portfolio_holdings(portfolio_id)
        assert len(holdings) == 1
        assert holdings[0]["quantity"] == pytest.approx(20.0)
        assert holdings[0]["average_cost"] == pytest.approx(150.0)  # (100+200)/2

    def test_sell_holding_reduces_quantity(self, db_manager, patched_db_session):
        portfolio_id = self._create_portfolio(db_manager, patched_db_session)
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, "MSFT", 20.0, 300.0)
        patched_db_session.flush()

        result = db_manager.sell_holding(portfolio_id, "MSFT", 5.0, 320.0)
        assert result is True
        patched_db_session.flush()

        holdings = db_manager.get_portfolio_holdings(portfolio_id)
        assert holdings[0]["quantity"] == pytest.approx(15.0)

    def test_sell_holding_removes_when_quantity_zero(self, db_manager, patched_db_session):
        portfolio_id = self._create_portfolio(db_manager, patched_db_session)
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, "TSLA", 5.0, 800.0)
        patched_db_session.flush()

        db_manager.sell_holding(portfolio_id, "TSLA", 5.0, 850.0)
        patched_db_session.flush()

        holdings = db_manager.get_portfolio_holdings(portfolio_id)
        assert holdings == []

    def test_sell_holding_returns_false_when_no_holding(self, db_manager, patched_db_session):
        portfolio_id = self._create_portfolio(db_manager, patched_db_session)
        patched_db_session.flush()

        result = db_manager.sell_holding(portfolio_id, "XYZ", 1.0, 100.0)
        assert result is False

    def test_sell_holding_returns_false_when_insufficient_quantity(
        self, db_manager, patched_db_session
    ):
        portfolio_id = self._create_portfolio(db_manager, patched_db_session)
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, "AMZN", 3.0, 100.0)
        patched_db_session.flush()

        result = db_manager.sell_holding(portfolio_id, "AMZN", 10.0, 110.0)
        assert result is False

    def test_add_holding_normalizes_symbol(self, db_manager, patched_db_session):
        portfolio_id = self._create_portfolio(db_manager, patched_db_session)
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, " nvda ", 2.0, 450.0)
        patched_db_session.flush()

        holdings = db_manager.get_portfolio_holdings(portfolio_id)
        assert holdings[0]["symbol"] == "NVDA"


# ---------------------------------------------------------------------------
# DatabaseManager.calculate_portfolio_value
# ---------------------------------------------------------------------------

class TestCalculatePortfolioValue:
    def test_calculates_correct_values(self, db_manager, patched_db_session):
        portfolio_id = db_manager.create_portfolio("user_m", "Calc Portfolio")
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, "AAPL", 10.0, 100.0)
        patched_db_session.flush()

        result = db_manager.calculate_portfolio_value(portfolio_id, {"AAPL": 120.0})
        assert result["total_value"] == pytest.approx(1200.0)
        assert result["total_cost"] == pytest.approx(1000.0)
        assert result["total_gain_loss"] == pytest.approx(200.0)
        assert result["total_gain_loss_pct"] == pytest.approx(20.0)

    def test_uses_avg_cost_when_price_missing(self, db_manager, patched_db_session):
        portfolio_id = db_manager.create_portfolio("user_n", "Fallback Portfolio")
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, "XYZ", 5.0, 200.0)
        patched_db_session.flush()

        result = db_manager.calculate_portfolio_value(portfolio_id, {})
        # No price for XYZ -> uses avg_cost as current price -> gain_loss = 0
        assert result["total_gain_loss"] == pytest.approx(0.0)
        assert result["total_gain_loss_pct"] == pytest.approx(0.0)

    def test_returns_empty_result_for_no_holdings(self, db_manager, patched_db_session):
        portfolio_id = db_manager.create_portfolio("user_o", "Empty Portfolio")
        patched_db_session.flush()

        result = db_manager.calculate_portfolio_value(portfolio_id, {"SPY": 400.0})
        assert result["total_value"] == pytest.approx(0.0)
        assert result["holdings"] == []

    def test_multiple_holdings(self, db_manager, patched_db_session):
        portfolio_id = db_manager.create_portfolio("user_p", "Multi Portfolio")
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, "AAPL", 5.0, 100.0)
        db_manager.add_holding(portfolio_id, "GOOG", 2.0, 1000.0)
        patched_db_session.flush()

        result = db_manager.calculate_portfolio_value(
            portfolio_id, {"AAPL": 110.0, "GOOG": 1100.0}
        )
        assert result["total_value"] == pytest.approx(5.0 * 110.0 + 2.0 * 1100.0)
        assert len(result["holdings"]) == 2


# ---------------------------------------------------------------------------
# DatabaseManager.store_news_article / get_stored_news
# ---------------------------------------------------------------------------

class TestNewsArticles:
    def _make_article(self, url="http://example.com/news/1", title="Test News"):
        return {
            "title": title,
            "link": url,
            "source": "Reuters",
            "published": datetime(2024, 1, 15, 10, 0, 0),
            "summary": "A summary",
            "author": "John Doe",
            "symbols_mentioned": ["AAPL"],
            "sector": "Technology",
            "sentiment": "positive",
        }

    def test_stores_article(self, db_manager, patched_db_session):
        from database import NewsArticle
        result = db_manager.store_news_article(self._make_article())
        assert result is True
        patched_db_session.flush()
        article = patched_db_session.query(NewsArticle).first()
        assert article is not None
        assert article.title == "Test News"
        assert article.source == "Reuters"

    def test_duplicate_url_returns_true_without_duplicate(
        self, db_manager, patched_db_session
    ):
        from database import NewsArticle
        db_manager.store_news_article(self._make_article())
        patched_db_session.flush()
        result = db_manager.store_news_article(self._make_article())
        assert result is True
        patched_db_session.flush()
        count = patched_db_session.query(NewsArticle).count()
        assert count == 1

    def test_get_stored_news_returns_articles(self, db_manager, patched_db_session):
        db_manager.store_news_article(self._make_article())
        patched_db_session.flush()
        result = db_manager.get_stored_news()
        assert len(result) == 1
        assert result[0]["title"] == "Test News"

    def test_get_stored_news_limit(self, db_manager, patched_db_session):
        for i in range(5):
            db_manager.store_news_article(self._make_article(url=f"http://example.com/{i}"))
        patched_db_session.flush()
        result = db_manager.get_stored_news(limit=3)
        assert len(result) == 3

    def test_symbols_mentioned_serialized(self, db_manager, patched_db_session):
        db_manager.store_news_article(self._make_article())
        patched_db_session.flush()
        result = db_manager.get_stored_news()
        # Should come back as parsed list
        assert isinstance(result[0]["symbols_mentioned"], list)
        assert "AAPL" in result[0]["symbols_mentioned"]


# ---------------------------------------------------------------------------
# DatabaseManager.store_fundamental_analysis / get_fundamental_analysis
# ---------------------------------------------------------------------------

class TestFundamentalAnalysis:
    def test_store_and_retrieve(self, db_manager, patched_db_session):
        result = db_manager.store_fundamental_analysis(
            "aapl",
            "comprehensive",
            {"revenue": 1e9, "eps": 6.5},
            "annual",
        )
        assert result is True
        patched_db_session.flush()

        analyses = db_manager.get_fundamental_analysis("AAPL")
        assert len(analyses) == 1
        assert analyses[0]["symbol"] == "AAPL"
        assert analyses[0]["analysis_result"] == {"eps": 6.5, "revenue": 1e9}
        assert analyses[0]["period"] == "annual"

    def test_normalizes_symbol(self, db_manager, patched_db_session):
        db_manager.store_fundamental_analysis("msft", "dcf", {"value": 300}, "quarterly")
        patched_db_session.flush()

        analyses = db_manager.get_fundamental_analysis("MSFT")
        assert len(analyses) == 1
        assert analyses[0]["symbol"] == "MSFT"

    def test_filter_by_analysis_type(self, db_manager, patched_db_session):
        db_manager.store_fundamental_analysis("GOOG", "comprehensive", {"x": 1}, "annual")
        db_manager.store_fundamental_analysis("GOOG", "dcf", {"y": 2}, "annual")
        patched_db_session.flush()

        result = db_manager.get_fundamental_analysis("GOOG", analysis_type="dcf")
        assert len(result) == 1
        assert result[0]["analysis_type"] == "dcf"

    def test_limit_parameter(self, db_manager, patched_db_session):
        for i in range(7):
            db_manager.store_fundamental_analysis(
                "TSLA", "comprehensive", {"i": i}, "quarterly"
            )
        patched_db_session.flush()

        result = db_manager.get_fundamental_analysis("TSLA", limit=3)
        assert len(result) == 3

    def test_returns_empty_list_for_unknown_symbol(self, db_manager):
        result = db_manager.get_fundamental_analysis("ZZZZZ")
        assert result == []

    def test_store_returns_false_on_error(self):
        from database import DatabaseManager
        from utils.exceptions import DatabaseError
        mgr = DatabaseManager()
        with patch("database.get_db_session", side_effect=DatabaseError("error")):
            result = mgr.store_fundamental_analysis("X", "type", {}, "annual")
        assert result is False


# ---------------------------------------------------------------------------
# DatabaseManager.get_market_statistics
# ---------------------------------------------------------------------------

class TestMarketStatistics:
    def test_returns_record_counts_by_type(self, db_manager, patched_db_session):
        from database import FinancialData
        patched_db_session.add(
            FinancialData(symbol="SPY", price=400.0, change=1.0,
                          change_pct=0.25, volume=5e6, data_type="index")
        )
        patched_db_session.add(
            FinancialData(symbol="GLD", price=1800.0, change=5.0,
                          change_pct=0.28, volume=1e6, data_type="commodity")
        )
        patched_db_session.flush()

        stats = db_manager.get_market_statistics()
        assert stats["index_records"] == 1
        assert stats["commodity_records"] == 1
        assert stats["bond_records"] == 0

    def test_returns_most_volatile(self, db_manager, patched_db_session):
        from database import FinancialData
        patched_db_session.add(
            FinancialData(symbol="VOLATILE", price=100.0, change=10.0,
                          change_pct=10.0, volume=1e6, data_type="index")
        )
        patched_db_session.add(
            FinancialData(symbol="STABLE", price=100.0, change=0.1,
                          change_pct=0.1, volume=1e6, data_type="index")
        )
        patched_db_session.flush()

        stats = db_manager.get_market_statistics()
        assert "most_volatile" in stats
        assert len(stats["most_volatile"]) > 0
        # Highest volatility should come first
        assert stats["most_volatile"][0]["symbol"] == "VOLATILE"

    def test_returns_empty_dict_on_error(self):
        from database import DatabaseManager
        from utils.exceptions import DatabaseError
        mgr = DatabaseManager()
        with patch("database.get_db_session", side_effect=DatabaseError("error")):
            result = mgr.get_market_statistics()
        assert result == {}


# ---------------------------------------------------------------------------
# DatabaseManager.get_portfolio_transactions
# ---------------------------------------------------------------------------

class TestPortfolioTransactions:
    def test_returns_transactions_after_add_and_sell(self, db_manager, patched_db_session):
        portfolio_id = db_manager.create_portfolio("user_q", "Txn Portfolio")
        patched_db_session.flush()

        db_manager.add_holding(portfolio_id, "AAPL", 10.0, 100.0)
        patched_db_session.flush()
        db_manager.sell_holding(portfolio_id, "AAPL", 5.0, 110.0)
        patched_db_session.flush()

        txns = db_manager.get_portfolio_transactions(portfolio_id)
        assert len(txns) == 2
        types = {t["type"] for t in txns}
        assert "buy" in types
        assert "sell" in types

    def test_respects_limit(self, db_manager, patched_db_session):
        portfolio_id = db_manager.create_portfolio("user_r", "Limit Portfolio")
        patched_db_session.flush()

        for i in range(10):
            db_manager.add_holding(portfolio_id, f"S{i}", 1.0, float(i + 1))
            patched_db_session.flush()

        txns = db_manager.get_portfolio_transactions(portfolio_id, limit=5)
        assert len(txns) == 5