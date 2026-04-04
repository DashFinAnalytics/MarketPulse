"""Tests for utils/logging_config.py — StructuredLogger and decorators."""

import logging
import pytest
from unittest.mock import patch, MagicMock, call


# ── StructuredLogger ─────────────────────────────────────────────────────────

class TestStructuredLogger:
    """Tests for StructuredLogger class."""

    def _make_logger(self, name="test_logger"):
        from utils.logging_config import StructuredLogger
        return StructuredLogger(name)

    def test_instantiation(self):
        logger = self._make_logger()
        assert logger is not None
        assert logger.logger is not None

    def test_with_context_returns_new_logger(self):
        logger = self._make_logger()
        new_logger = logger.with_context(symbol="SPY", period="1y")
        assert new_logger is not logger
        assert new_logger.context["symbol"] == "SPY"
        assert new_logger.context["period"] == "1y"

    def test_with_context_preserves_existing_context(self):
        logger = self._make_logger()
        logger1 = logger.with_context(key1="val1")
        logger2 = logger1.with_context(key2="val2")
        assert logger2.context["key1"] == "val1"
        assert logger2.context["key2"] == "val2"

    def test_with_context_does_not_mutate_original(self):
        logger = self._make_logger()
        _ = logger.with_context(key="val")
        assert "key" not in logger.context

    def test_info_logs_message(self):
        logger = self._make_logger("test_info")
        with patch.object(logger.logger, "log") as mock_log:
            logger.info("Hello world")
            mock_log.assert_called_once()
            args = mock_log.call_args
            assert "Hello world" in args[0][1]

    def test_debug_logs_at_debug_level(self):
        logger = self._make_logger()
        with patch.object(logger.logger, "log") as mock_log:
            logger.debug("Debug msg")
            assert mock_log.call_args[0][0] == logging.DEBUG

    def test_warning_logs_at_warning_level(self):
        logger = self._make_logger()
        with patch.object(logger.logger, "log") as mock_log:
            logger.warning("Warning msg")
            assert mock_log.call_args[0][0] == logging.WARNING

    def test_error_logs_at_error_level(self):
        logger = self._make_logger()
        with patch.object(logger.logger, "log") as mock_log:
            logger.error("Error msg")
            assert mock_log.call_args[0][0] == logging.ERROR

    def test_critical_logs_at_critical_level(self):
        logger = self._make_logger()
        with patch.object(logger.logger, "log") as mock_log:
            logger.critical("Critical msg")
            assert mock_log.call_args[0][0] == logging.CRITICAL

    def test_context_appended_to_message(self):
        logger = self._make_logger().with_context(symbol="AAPL")
        with patch.object(logger.logger, "log") as mock_log:
            logger.info("Price update")
            logged_msg = mock_log.call_args[0][1]
            assert "AAPL" in logged_msg
            assert "symbol" in logged_msg

    def test_extra_kwargs_appended_to_message(self):
        logger = self._make_logger()
        with patch.object(logger.logger, "log") as mock_log:
            logger.info("Event", user="alice", action="buy")
            logged_msg = mock_log.call_args[0][1]
            assert "alice" in logged_msg
            assert "buy" in logged_msg


# ── get_logger ───────────────────────────────────────────────────────────────

class TestGetLogger:
    """Tests for get_logger()."""

    def test_returns_structured_logger(self):
        from utils.logging_config import get_logger, StructuredLogger
        logger = get_logger("my.module")
        assert isinstance(logger, StructuredLogger)

    def test_name_preserved(self):
        from utils.logging_config import get_logger
        logger = get_logger("my.module")
        assert logger.logger.name == "my.module"


# ── log_execution_time ───────────────────────────────────────────────────────

class TestLogExecutionTime:
    """Tests for log_execution_time() decorator."""

    def test_decorated_function_returns_correctly(self):
        from utils.logging_config import log_execution_time

        @log_execution_time()
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_decorated_function_propagates_exception(self):
        from utils.logging_config import log_execution_time

        @log_execution_time()
        def boom():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            boom()

    def test_function_name_preserved(self):
        from utils.logging_config import log_execution_time

        @log_execution_time()
        def my_func():
            return True

        assert my_func.__name__ == "my_func"

    def test_decorator_with_explicit_logger(self):
        from utils.logging_config import log_execution_time, get_logger
        custom_logger = get_logger("test")

        @log_execution_time(logger=custom_logger)
        def fn():
            return 99

        assert fn() == 99


# ── log_api_call ─────────────────────────────────────────────────────────────

class TestLogApiCall:
    """Tests for log_api_call() decorator."""

    def test_decorated_function_returns_correctly(self):
        from utils.logging_config import log_api_call

        @log_api_call("TestAPI")
        def fetch_data():
            return {"data": 42}

        assert fetch_data() == {"data": 42}

    def test_decorated_function_propagates_exception(self):
        from utils.logging_config import log_api_call

        @log_api_call("BrokenAPI")
        def broken():
            raise RuntimeError("API down")

        with pytest.raises(RuntimeError, match="API down"):
            broken()

    def test_function_name_preserved(self):
        from utils.logging_config import log_api_call

        @log_api_call("SomeAPI")
        def my_api_func():
            pass

        assert my_api_func.__name__ == "my_api_func"


# ── setup_logging ────────────────────────────────────────────────────────────

class TestSetupLogging:
    """Tests for setup_logging()."""

    def test_setup_logging_runs_without_error(self):
        from utils.logging_config import setup_logging
        # Should not raise
        setup_logging()

    def test_setup_logging_configures_root_logger(self):
        from utils.logging_config import setup_logging
        import logging
        setup_logging()
        root = logging.getLogger()
        # Root logger should have at least one handler after setup
        assert len(root.handlers) >= 1

    def test_noisy_loggers_set_to_warning(self):
        from utils.logging_config import setup_logging
        import logging
        setup_logging()
        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("requests").level == logging.WARNING
        assert logging.getLogger("yfinance").level == logging.WARNING