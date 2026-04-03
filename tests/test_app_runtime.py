"""Tests for refactor_staging/pr3/app_runtime.py (new file in this PR).

Covers: database_is_ready, cleanup_service_cache, and the error-degradation
path of initialize_application. render_* functions are verified to not crash
when called with a mocked streamlit.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch
import pytest

# conftest.py installs streamlit mock before any import.
# We also need to mock app_init before importing app_runtime.

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_RUNTIME_PATH = os.path.join(
    _PROJECT_ROOT, "refactor_staging", "pr3", "app_runtime.py"
)

# Mock app_init and utils.cache before importing app_runtime
if "app_init" not in sys.modules:
    mock_app_init = MagicMock()
    mock_app_init.initialize_app.return_value = {"status": "initialized"}
    mock_app_init.get_app_status.return_value = {}
    sys.modules["app_init"] = mock_app_init

if "utils.cache" not in sys.modules:
    mock_cache = MagicMock()
    mock_cache.periodic_cleanup.return_value = 0
    sys.modules["utils.cache"] = mock_cache
    # Also ensure the cache attribute exists
    mock_cache.cache = MagicMock()

# Load the module under a unique name and ALSO register it as 'app_runtime'
# so that patch("app_runtime.XXX") works correctly.
_spec = importlib.util.spec_from_file_location("app_runtime", _APP_RUNTIME_PATH)
_app_runtime = importlib.util.module_from_spec(_spec)
sys.modules["app_runtime"] = _app_runtime  # Register so patch() finds it
_spec.loader.exec_module(_app_runtime)

database_is_ready = _app_runtime.database_is_ready
cleanup_service_cache = _app_runtime.cleanup_service_cache
initialize_application = _app_runtime.initialize_application
render_ui_error = _app_runtime.render_ui_error


# ---------------------------------------------------------------------------
# database_is_ready
# ---------------------------------------------------------------------------

class TestDatabaseIsReady:
    """database_is_ready() is a pure dict-inspection function.

    Implementation: bool(database.get("health") is True or database.get("status") == "initialized")
    The OR means: either health==True OR status=="initialized" → ready.
    """

    def test_health_true_means_ready(self):
        status = {"database": {"health": True, "status": "initialized"}}
        assert database_is_ready(status) is True

    def test_health_false_but_status_initialized_still_ready(self):
        # OR semantics: status=="initialized" alone satisfies readiness
        status = {"database": {"health": False, "status": "initialized"}}
        assert database_is_ready(status) is True

    def test_health_true_but_status_degraded_still_ready(self):
        # OR semantics: health==True alone satisfies readiness
        status = {"database": {"health": True, "status": "degraded"}}
        assert database_is_ready(status) is True

    def test_status_initialized_without_health_key_ready(self):
        # Only status key present, status is "initialized"
        status = {"database": {"status": "initialized"}}
        assert database_is_ready(status) is True

    def test_health_false_and_status_degraded_not_ready(self):
        # Both conditions false → not ready
        status = {"database": {"health": False, "status": "degraded"}}
        assert database_is_ready(status) is False

    def test_missing_database_key_not_ready(self):
        status = {}
        assert database_is_ready(status) is False

    def test_empty_database_dict_not_ready(self):
        status = {"database": {}}
        assert database_is_ready(status) is False

    def test_health_none_and_no_status_not_ready(self):
        status = {"database": {"health": None}}
        assert database_is_ready(status) is False

    def test_health_string_true_not_treated_as_bool_true(self):
        # health must be exactly True (bool), "true" is not
        status = {"database": {"health": "true"}}
        assert database_is_ready(status) is False

    def test_full_ok_status(self):
        status = {
            "database": {"health": True, "status": "initialized"},
            "cache": {"status": "ok"},
        }
        assert database_is_ready(status) is True

    def test_degraded_init_error(self):
        status = {
            "status": "degraded",
            "initialization_error": "some error",
            "database": {"status": "degraded", "health": False},
        }
        assert database_is_ready(status) is False

    def test_returns_bool(self):
        for status in [
            {"database": {"health": True}},
            {"database": {}},
            {},
        ]:
            result = database_is_ready(status)
            assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# cleanup_service_cache
# ---------------------------------------------------------------------------

class TestCleanupServiceCache:
    def test_returns_integer_on_success(self):
        with patch("app_runtime.periodic_cleanup", return_value=5):
            result = cleanup_service_cache()
        assert result == 5

    def test_returns_zero_on_exception(self):
        with patch("app_runtime.periodic_cleanup", side_effect=RuntimeError("fail")):
            result = cleanup_service_cache()
        assert result == 0

    def test_delegates_to_periodic_cleanup(self):
        with patch("app_runtime.periodic_cleanup", return_value=3) as mock_cleanup:
            cleanup_service_cache()
        mock_cleanup.assert_called_once()

    def test_returns_zero_when_cleanup_returns_zero(self):
        with patch("app_runtime.periodic_cleanup", return_value=0):
            result = cleanup_service_cache()
        assert result == 0

    def test_returns_positive_count_when_items_cleaned(self):
        with patch("app_runtime.periodic_cleanup", return_value=10):
            result = cleanup_service_cache()
        assert result == 10

    def test_does_not_propagate_exception(self):
        with patch("app_runtime.periodic_cleanup", side_effect=ValueError("oops")):
            try:
                result = cleanup_service_cache()
            except Exception as exc:
                pytest.fail(f"cleanup_service_cache should not propagate exception: {exc}")


# ---------------------------------------------------------------------------
# initialize_application degradation
# ---------------------------------------------------------------------------

class TestInitializeApplicationDegradation:
    """When initialize_app raises, initialize_application must return a
    degraded status dict rather than propagating the exception."""

    def test_exception_returns_degraded_status(self):
        with patch("app_runtime.initialize_app", side_effect=RuntimeError("init failed")):
            result = initialize_application()
        assert result["status"] == "degraded"

    def test_degraded_contains_database_key(self):
        with patch("app_runtime.initialize_app", side_effect=ValueError("bad config")):
            result = initialize_application()
        assert "database" in result
        assert result["database"]["health"] is False

    def test_degraded_contains_error_message(self):
        with patch("app_runtime.initialize_app", side_effect=RuntimeError("boom")):
            result = initialize_application()
        assert "initialization_error" in result
        assert "boom" in result["initialization_error"]

    def test_successful_init_returns_status(self):
        expected = {"status": "initialized", "database": {"health": True}}
        with patch("app_runtime.initialize_app", return_value=expected):
            result = initialize_application()
        assert result["status"] == "initialized"

    def test_degraded_status_dict_has_health_checks(self):
        with patch("app_runtime.initialize_app", side_effect=Exception("x")):
            result = initialize_application()
        assert "health_checks" in result
        assert "database" in result["health_checks"]
        assert "cache" in result["health_checks"]
        assert "openai" in result["health_checks"]

    def test_degraded_database_health_is_false(self):
        with patch("app_runtime.initialize_app", side_effect=Exception("x")):
            result = initialize_application()
        assert result["database"]["health"] is False


# ---------------------------------------------------------------------------
# render_ui_error
# ---------------------------------------------------------------------------

class TestRenderUiError:
    """render_ui_error must log and call st.error regardless of debug mode."""

    def test_calls_st_error_with_message(self):
        st_mock = sys.modules["streamlit"]
        st_mock.error.reset_mock()
        render_ui_error("something went wrong")
        st_mock.error.assert_called()

    def test_accepts_none_error(self):
        try:
            render_ui_error("msg", error=None)
        except Exception as exc:
            pytest.fail(f"render_ui_error raised with error=None: {exc}")

    def test_accepts_exception_error(self):
        try:
            render_ui_error("msg", error=ValueError("test"))
        except Exception as exc:
            pytest.fail(f"render_ui_error raised unexpectedly: {exc}")

    def test_message_passed_to_st_error(self):
        st_mock = sys.modules["streamlit"]
        st_mock.error.reset_mock()
        render_ui_error("my specific error message")
        call_args = st_mock.error.call_args
        assert "my specific error message" in str(call_args)