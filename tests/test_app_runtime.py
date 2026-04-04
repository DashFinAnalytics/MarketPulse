"""Tests for refactor_staging/pr3/app_runtime.py.

This is a new file added in the PR. Tests cover the helper functions that
do not require a live Streamlit session: database_is_ready, cleanup_service_cache,
and render_ui_error (with streamlit mocked).
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# Streamlit must be mocked before the module is imported.
# conftest.py injects the mock at collection time, but we guard here too.
if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.cache_resource = lambda fn=None, **kw: (fn if fn else lambda f: f)
    sys.modules["streamlit"] = _st_mock


# ---------------------------------------------------------------------------
# We import the module under test after ensuring streamlit is mocked.
# ---------------------------------------------------------------------------
import refactor_staging.pr3.app_runtime as app_runtime_module

# Re-expose the functions we're testing for convenience
from refactor_staging.pr3.app_runtime import (
    database_is_ready,
    cleanup_service_cache,
    render_ui_error,
)


# ---------------------------------------------------------------------------
# database_is_ready
# ---------------------------------------------------------------------------

class TestDatabaseIsReady:
    def test_health_true_returns_true(self):
        status = {"database": {"health": True, "status": "initialized"}}
        assert database_is_ready(status) is True

    def test_health_false_returns_false(self):
        status = {"database": {"health": False, "status": "degraded"}}
        assert database_is_ready(status) is False

    def test_status_initialized_without_health_key_returns_true(self):
        status = {"database": {"status": "initialized"}}
        assert database_is_ready(status) is True

    def test_empty_database_dict_returns_false(self):
        status = {"database": {}}
        assert database_is_ready(status) is False

    def test_missing_database_key_returns_false(self):
        status = {}
        assert database_is_ready(status) is False

    def test_status_disabled_returns_false(self):
        status = {"database": {"health": False, "status": "disabled_or_unconfigured"}}
        assert database_is_ready(status) is False

    def test_health_none_returns_false(self):
        # health=None is falsy
        status = {"database": {"health": None, "status": "unknown"}}
        assert database_is_ready(status) is False

    # Boundary: health="unknown" – the function checks `health is True` (identity),
    # so a non-bool truthy value does not qualify as ready
    def test_health_string_unknown_returns_false(self):
        status = {"database": {"health": "unknown"}}
        # "unknown" is not `True` by identity check
        assert database_is_ready(status) is False

    def test_degraded_with_health_true(self):
        status = {"database": {"health": True, "status": "degraded"}}
        # health=True takes precedence
        assert database_is_ready(status) is True


# ---------------------------------------------------------------------------
# cleanup_service_cache
# ---------------------------------------------------------------------------

class TestCleanupServiceCache:
    def test_returns_count_from_periodic_cleanup(self):
        with patch(
            "refactor_staging.pr3.app_runtime.periodic_cleanup", return_value=5
        ):
            result = cleanup_service_cache()
        assert result == 5

    def test_returns_zero_when_periodic_cleanup_raises(self):
        with patch(
            "refactor_staging.pr3.app_runtime.periodic_cleanup",
            side_effect=RuntimeError("cleanup failed"),
        ):
            result = cleanup_service_cache()
        assert result == 0

    def test_returns_none_when_periodic_cleanup_returns_none(self):
        # The function signature says `-> int` but passes through whatever
        # periodic_cleanup returns. When it returns None, the function returns None.
        with patch(
            "refactor_staging.pr3.app_runtime.periodic_cleanup", return_value=None
        ):
            result = cleanup_service_cache()
        assert result is None

    def test_handles_zero_cleaned(self):
        with patch(
            "refactor_staging.pr3.app_runtime.periodic_cleanup", return_value=0
        ):
            result = cleanup_service_cache()
        assert result == 0


# ---------------------------------------------------------------------------
# render_ui_error
# ---------------------------------------------------------------------------

class TestRenderUiError:
    def test_calls_st_error_with_message(self):
        st_mock = sys.modules["streamlit"]
        with patch.object(st_mock, "error") as mock_error:
            render_ui_error("Something went wrong")
        mock_error.assert_called_once_with("Something went wrong")

    def test_does_not_raise_without_error_arg(self):
        st_mock = sys.modules["streamlit"]
        with patch.object(st_mock, "error"):
            try:
                render_ui_error("Plain message")
            except Exception as exc:
                pytest.fail(f"render_ui_error raised unexpectedly: {exc}")

    def test_calls_st_error_when_error_provided_non_debug(self):
        st_mock = sys.modules["streamlit"]
        with patch.object(st_mock, "error") as mock_error, \
             patch("refactor_staging.pr3.app_runtime.config") as mock_config:
            mock_config.app.debug = False
            render_ui_error("DB error", ValueError("something"))
        mock_error.assert_called_once()

    def test_calls_st_exception_in_debug_mode(self):
        st_mock = sys.modules["streamlit"]
        exc = ValueError("detail")
        with patch.object(st_mock, "error"), \
             patch.object(st_mock, "exception") as mock_exc, \
             patch("refactor_staging.pr3.app_runtime.config") as mock_config:
            mock_config.app.debug = True
            render_ui_error("error with detail", exc)
        mock_exc.assert_called_once_with(exc)

    def test_no_st_exception_in_non_debug_mode(self):
        st_mock = sys.modules["streamlit"]
        with patch.object(st_mock, "error"), \
             patch.object(st_mock, "exception") as mock_exc, \
             patch("refactor_staging.pr3.app_runtime.config") as mock_config:
            mock_config.app.debug = False
            render_ui_error("non-debug error", RuntimeError("x"))
        mock_exc.assert_not_called()