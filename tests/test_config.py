"""Tests for config.py — env parsing helpers, dataclasses, and Config validation."""
import os
import warnings
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helper: _env_bool
# ---------------------------------------------------------------------------

class TestEnvBool:
    """Tests for _env_bool helper function."""

    def setup_method(self):
        # Import inside test to get a clean module-level state
        from config import _env_bool
        self._env_bool = _env_bool

    def test_returns_default_when_var_not_set(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_BOOL_VAR", None)
            assert self._env_bool("TEST_BOOL_VAR", True) is True
            assert self._env_bool("TEST_BOOL_VAR", False) is False

    @pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "Yes", "YES", "on", "ON"])
    def test_true_values(self, value):
        with patch.dict(os.environ, {"TEST_BOOL_VAR": value}):
            assert self._env_bool("TEST_BOOL_VAR", False) is True

    @pytest.mark.parametrize("value", ["0", "false", "False", "FALSE", "no", "No", "NO", "off", "OFF"])
    def test_false_values(self, value):
        with patch.dict(os.environ, {"TEST_BOOL_VAR": value}):
            assert self._env_bool("TEST_BOOL_VAR", True) is False

    def test_unrecognized_value_returns_default_and_warns(self):
        with patch.dict(os.environ, {"TEST_BOOL_VAR": "maybe"}):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = self._env_bool("TEST_BOOL_VAR", True)
            assert result is True
            assert any("unrecognized boolean" in str(w.message).lower() for w in caught)

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"TEST_BOOL_VAR": "  true  "}):
            assert self._env_bool("TEST_BOOL_VAR", False) is True


# ---------------------------------------------------------------------------
# Helper: _env_int
# ---------------------------------------------------------------------------

class TestEnvInt:
    """Tests for _env_int helper function."""

    def setup_method(self):
        from config import _env_int
        self._env_int = _env_int

    def test_returns_default_when_not_set(self):
        os.environ.pop("TEST_INT_VAR", None)
        assert self._env_int("TEST_INT_VAR", 42) == 42

    def test_parses_valid_integer(self):
        with patch.dict(os.environ, {"TEST_INT_VAR": "100"}):
            assert self._env_int("TEST_INT_VAR", 0) == 100

    def test_parses_negative_integer(self):
        with patch.dict(os.environ, {"TEST_INT_VAR": "-5"}):
            assert self._env_int("TEST_INT_VAR", 0) == -5

    def test_invalid_value_returns_default_and_warns(self):
        with patch.dict(os.environ, {"TEST_INT_VAR": "notanint"}):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = self._env_int("TEST_INT_VAR", 7)
            assert result == 7
            assert len(caught) >= 1

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"TEST_INT_VAR": "  55  "}):
            assert self._env_int("TEST_INT_VAR", 0) == 55

    def test_float_string_returns_default_and_warns(self):
        with patch.dict(os.environ, {"TEST_INT_VAR": "3.14"}):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = self._env_int("TEST_INT_VAR", 99)
            assert result == 99
            assert len(caught) >= 1


# ---------------------------------------------------------------------------
# Helper: _env_float
# ---------------------------------------------------------------------------

class TestEnvFloat:
    """Tests for _env_float helper function."""

    def setup_method(self):
        from config import _env_float
        self._env_float = _env_float

    def test_returns_default_when_not_set(self):
        os.environ.pop("TEST_FLOAT_VAR", None)
        assert self._env_float("TEST_FLOAT_VAR", 1.5) == 1.5

    def test_parses_valid_float(self):
        with patch.dict(os.environ, {"TEST_FLOAT_VAR": "3.14"}):
            assert self._env_float("TEST_FLOAT_VAR", 0.0) == pytest.approx(3.14)

    def test_parses_integer_as_float(self):
        with patch.dict(os.environ, {"TEST_FLOAT_VAR": "10"}):
            assert self._env_float("TEST_FLOAT_VAR", 0.0) == 10.0

    def test_parses_negative_float(self):
        with patch.dict(os.environ, {"TEST_FLOAT_VAR": "-0.5"}):
            assert self._env_float("TEST_FLOAT_VAR", 0.0) == pytest.approx(-0.5)

    def test_invalid_value_returns_default_and_warns(self):
        with patch.dict(os.environ, {"TEST_FLOAT_VAR": "notafloat"}):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = self._env_float("TEST_FLOAT_VAR", 9.9)
            assert result == 9.9
            assert len(caught) >= 1

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"TEST_FLOAT_VAR": "  2.71  "}):
            assert self._env_float("TEST_FLOAT_VAR", 0.0) == pytest.approx(2.71)


# ---------------------------------------------------------------------------
# DatabaseConfig
# ---------------------------------------------------------------------------

class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""

    def test_is_configured_true_when_url_set(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/test"}):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            db = cfg_mod.DatabaseConfig()
            assert db.is_configured is True

    def test_is_configured_false_when_url_not_set(self):
        env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            db = cfg_mod.DatabaseConfig()
            assert db.is_configured is False

    def test_is_available_requires_both_enabled_and_configured(self):
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://localhost/test",
            "ENABLE_DATABASE": "true"
        }):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            db = cfg_mod.DatabaseConfig()
            assert db.is_available is True

    def test_is_available_false_when_disabled(self):
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://localhost/test",
            "ENABLE_DATABASE": "false"
        }):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            db = cfg_mod.DatabaseConfig()
            assert db.is_available is False

    def test_is_available_false_when_no_url(self):
        env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        env["ENABLE_DATABASE"] = "true"
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            db = cfg_mod.DatabaseConfig()
            assert db.is_available is False


# ---------------------------------------------------------------------------
# APIConfig
# ---------------------------------------------------------------------------

class TestAPIConfig:
    """Tests for APIConfig dataclass."""

    def test_ai_available_true_when_key_set(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            api = cfg_mod.APIConfig()
            assert api.ai_available is True

    def test_ai_available_false_when_key_not_set(self):
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            api = cfg_mod.APIConfig()
            assert api.ai_available is False

    def test_default_model(self):
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_MODEL"}
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            api = cfg_mod.APIConfig()
            assert api.openai_model == "gpt-4.1-mini"

    def test_custom_model_from_env(self):
        with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4"}):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            api = cfg_mod.APIConfig()
            assert api.openai_model == "gpt-4"


# ---------------------------------------------------------------------------
# Config (top-level) validation warnings
# ---------------------------------------------------------------------------

class TestConfigValidation:
    """Tests for Config._validate_config and get_warning_summary."""

    def test_warns_when_ai_enabled_but_no_key(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("OPENAI_API_KEY", "ENABLE_AI_ANALYSIS")}
        env["ENABLE_AI_ANALYSIS"] = "true"
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            cfg = cfg_mod.Config()
            summaries = cfg.get_warning_summary()
            assert any("OPENAI_API_KEY" in w for w in summaries)

    def test_warns_when_database_enabled_but_no_url(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("DATABASE_URL", "ENABLE_DATABASE")}
        env["ENABLE_DATABASE"] = "true"
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import config as cfg_mod
            reload(cfg_mod)
            cfg = cfg_mod.Config()
            summaries = cfg.get_warning_summary()
            assert any("DATABASE_URL" in w for w in summaries)

    def test_get_warning_summary_returns_list(self):
        from importlib import reload
        import config as cfg_mod
        reload(cfg_mod)
        cfg = cfg_mod.Config()
        result = cfg.get_warning_summary()
        assert isinstance(result, list)

    def test_get_warning_summary_is_copy(self):
        from importlib import reload
        import config as cfg_mod
        reload(cfg_mod)
        cfg = cfg_mod.Config()
        first = cfg.get_warning_summary()
        first.append("INJECTED")
        second = cfg.get_warning_summary()
        assert "INJECTED" not in second