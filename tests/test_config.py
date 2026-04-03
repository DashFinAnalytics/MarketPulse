"""Tests for config.py — environment parsing helpers and Config class."""

import os
import warnings
import pytest
from unittest.mock import patch


# ── Helpers ─────────────────────────────────────────────────────────────────

class TestEnvBool:
    """Tests for _env_bool helper."""

    def test_true_values(self):
        from config import _env_bool
        for val in ("1", "true", "True", "TRUE", "yes", "YES", "on", "ON"):
            with patch.dict(os.environ, {"TEST_FLAG": val}):
                assert _env_bool("TEST_FLAG", False) is True

    def test_false_values(self):
        from config import _env_bool
        for val in ("0", "false", "False", "FALSE", "no", "NO", "off", "OFF"):
            with patch.dict(os.environ, {"TEST_FLAG": val}):
                assert _env_bool("TEST_FLAG", True) is False

    def test_missing_key_returns_default_true(self):
        from config import _env_bool
        env = {k: v for k, v in os.environ.items() if k != "MISSING_FLAG"}
        with patch.dict(os.environ, env, clear=True):
            assert _env_bool("MISSING_FLAG", True) is True

    def test_missing_key_returns_default_false(self):
        from config import _env_bool
        env = {k: v for k, v in os.environ.items() if k != "MISSING_FLAG"}
        with patch.dict(os.environ, env, clear=True):
            assert _env_bool("MISSING_FLAG", False) is False

    def test_invalid_value_warns_and_returns_default(self):
        from config import _env_bool
        with patch.dict(os.environ, {"TEST_FLAG": "maybe"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = _env_bool("TEST_FLAG", True)
                assert result is True
                assert len(w) == 1
                assert "unrecognized boolean value" in str(w[0].message).lower()

    def test_whitespace_stripped(self):
        from config import _env_bool
        with patch.dict(os.environ, {"TEST_FLAG": "  true  "}):
            assert _env_bool("TEST_FLAG", False) is True


class TestEnvInt:
    """Tests for _env_int helper."""

    def test_valid_int(self):
        from config import _env_int
        with patch.dict(os.environ, {"MY_INT": "42"}):
            assert _env_int("MY_INT", 0) == 42

    def test_missing_key_returns_default(self):
        from config import _env_int
        env = {k: v for k, v in os.environ.items() if k != "MISSING_INT"}
        with patch.dict(os.environ, env, clear=True):
            assert _env_int("MISSING_INT", 99) == 99

    def test_invalid_value_warns_and_returns_default(self):
        from config import _env_int
        with patch.dict(os.environ, {"MY_INT": "not_a_number"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = _env_int("MY_INT", 7)
                assert result == 7
                assert len(w) == 1

    def test_whitespace_stripped(self):
        from config import _env_int
        with patch.dict(os.environ, {"MY_INT": " 5 "}):
            assert _env_int("MY_INT", 0) == 5

    def test_negative_value(self):
        from config import _env_int
        with patch.dict(os.environ, {"MY_INT": "-10"}):
            assert _env_int("MY_INT", 0) == -10


class TestEnvFloat:
    """Tests for _env_float helper."""

    def test_valid_float(self):
        from config import _env_float
        with patch.dict(os.environ, {"MY_FLOAT": "3.14"}):
            assert _env_float("MY_FLOAT", 0.0) == pytest.approx(3.14)

    def test_missing_key_returns_default(self):
        from config import _env_float
        env = {k: v for k, v in os.environ.items() if k != "MISSING_FLOAT"}
        with patch.dict(os.environ, env, clear=True):
            assert _env_float("MISSING_FLOAT", 1.5) == pytest.approx(1.5)

    def test_invalid_value_warns_and_returns_default(self):
        from config import _env_float
        with patch.dict(os.environ, {"MY_FLOAT": "abc"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = _env_float("MY_FLOAT", 2.0)
                assert result == pytest.approx(2.0)
                assert len(w) == 1

    def test_integer_string_accepted(self):
        from config import _env_float
        with patch.dict(os.environ, {"MY_FLOAT": "10"}):
            assert _env_float("MY_FLOAT", 0.0) == pytest.approx(10.0)


# ── DatabaseConfig ───────────────────────────────────────────────────────────

class TestDatabaseConfig:
    """Tests for DatabaseConfig properties."""

    def test_is_configured_false_when_no_url(self):
        from config import DatabaseConfig
        cfg = DatabaseConfig(url=None)
        assert cfg.is_configured is False

    def test_is_configured_true_when_url_set(self):
        from config import DatabaseConfig
        cfg = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        assert cfg.is_configured is True

    def test_is_available_requires_enabled_and_url(self):
        from config import DatabaseConfig
        cfg_both = DatabaseConfig(url="postgresql://x", enabled=True)
        assert cfg_both.is_available is True

        cfg_no_url = DatabaseConfig(url=None, enabled=True)
        assert cfg_no_url.is_available is False

        cfg_disabled = DatabaseConfig(url="postgresql://x", enabled=False)
        assert cfg_disabled.is_available is False


# ── APIConfig ────────────────────────────────────────────────────────────────

class TestAPIConfig:
    """Tests for APIConfig properties."""

    def test_ai_available_false_when_no_key(self):
        from config import APIConfig
        cfg = APIConfig(openai_api_key=None)
        assert cfg.ai_available is False

    def test_ai_available_true_when_key_set(self):
        from config import APIConfig
        cfg = APIConfig(openai_api_key="sk-test")
        assert cfg.ai_available is True


# ── Config (top-level) ───────────────────────────────────────────────────────

class TestConfig:
    """Tests for the top-level Config class."""

    def test_config_instantiates(self):
        from config import Config
        cfg = Config()
        assert cfg.database is not None
        assert cfg.api is not None
        assert cfg.cache is not None
        assert cfg.app is not None

    def test_get_warning_summary_returns_list(self):
        from config import Config
        cfg = Config()
        warnings_list = cfg.get_warning_summary()
        assert isinstance(warnings_list, list)

    def test_warning_when_ai_enabled_but_no_key(self):
        env_overrides = {
            "ENABLE_AI_ANALYSIS": "true",
            "OPENAI_API_KEY": "",
        }
        # Remove actual key if set
        clean_env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        clean_env.update(env_overrides)
        with patch.dict(os.environ, clean_env, clear=True):
            from config import Config
            cfg = Config()
            summary = cfg.get_warning_summary()
            ai_warnings = [w for w in summary if "AI" in w or "OPENAI" in w or "ai" in w.lower()]
            # Expect at least one AI-related warning
            assert len(ai_warnings) >= 1

    def test_warning_when_db_enabled_but_no_url(self):
        clean_env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        clean_env["ENABLE_DATABASE"] = "true"
        with patch.dict(os.environ, clean_env, clear=True):
            from config import Config
            cfg = Config()
            summary = cfg.get_warning_summary()
            db_warnings = [w for w in summary if "database" in w.lower() or "DATABASE" in w]
            assert len(db_warnings) >= 1

    def test_config_module_singleton(self):
        """The module-level config object should be a Config instance."""
        import config as config_module
        from config import Config
        assert isinstance(config_module.config, Config)