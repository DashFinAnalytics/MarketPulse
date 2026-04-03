"""Tests for utils/logging_config.py — StructuredLogger, decorators, setup_logging."""
import logging
import pytest
from unittest.mock import patch, MagicMock, call
import sys


# ---------------------------------------------------------------------------
# StructuredLogger
# ---------------------------------------------------------------------------

class TestStructuredLogger:
    """Tests for StructuredLogger class."""

    def setup_method(self):
        from utils.logging_config import StructuredLogger
        self.StructuredLogger = StructuredLogger

    def test_instantiation(self):
        logger = self.StructuredLogger("test.module")
        assert logger is not None

    def test_has_logger_attribute(self):
        logger = self.StructuredLogger("test.module")
        assert hasattr(logger, "logger")
        assert isinstance(logger.logger, logging.Logger)

    def test_logger_name_set_correctly(self):
        logger = self.StructuredLogger("myapp.service")
        assert logger.logger.name == "myapp.service"

    def test_context_starts_empty(self):
        logger = self.StructuredLogger("test")
        assert logger.context == {}

    def test_with_context_returns_new_logger(self):
        logger = self.StructuredLogger("test")
        child = logger.with_context(request_id="abc123")
        assert child is not logger

    def test_with_context_merges_contexts(self):
        logger = self.StructuredLogger("test")
        child = logger.with_context(a=1)
        grandchild = child.with_context(b=2)
        assert grandchild.context == {"a": 1, "b": 2}

    def test_with_context_original_unchanged(self):
        logger = self.StructuredLogger("test")
        logger.with_context(a=1)
        assert logger.context == {}

    def test_with_context_overrides_existing_key(self):
        logger = self.StructuredLogger("test")
        child = logger.with_context(a=1)
        child2 = child.with_context(a=99)
        assert child2.context["a"] == 99

    def test_info_logs_message(self):
        logger = self.StructuredLogger("test")
        with patch.object(logger.logger, "log") as mock_log:
            logger.info("hello world")
            mock_log.assert_called_once()
            args = mock_log.call_args[0]
            assert args[0] == logging.INFO
            assert "hello world" in args[1]

    def test_debug_logs_at_debug_level(self):
        logger = self.StructuredLogger("test")
        with patch.object(logger.logger, "log") as mock_log:
            logger.debug("debug msg")
            args = mock_log.call_args[0]
            assert args[0] == logging.DEBUG

    def test_warning_logs_at_warning_level(self):
        logger = self.StructuredLogger("test")
        with patch.object(logger.logger, "log") as mock_log:
            logger.warning("warn msg")
            args = mock_log.call_args[0]
            assert args[0] == logging.WARNING

    def test_error_logs_at_error_level(self):
        logger = self.StructuredLogger("test")
        with patch.object(logger.logger, "log") as mock_log:
            logger.error("error msg")
            args = mock_log.call_args[0]
            assert args[0] == logging.ERROR

    def test_critical_logs_at_critical_level(self):
        logger = self.StructuredLogger("test")
        with patch.object(logger.logger, "log") as mock_log:
            logger.critical("critical msg")
            args = mock_log.call_args[0]
            assert args[0] == logging.CRITICAL

    def test_context_appended_to_message(self):
        logger = self.StructuredLogger("test").with_context(symbol="SPY")
        with patch.object(logger.logger, "log") as mock_log:
            logger.info("price updated")
            logged_message = mock_log.call_args[0][1]
            assert "SPY" in logged_message
            assert "symbol" in logged_message

    def test_kwargs_appended_to_message(self):
        logger = self.StructuredLogger("test")
        with patch.object(logger.logger, "log") as mock_log:
            logger.info("test", user="alice")
            logged_message = mock_log.call_args[0][1]
            assert "alice" in logged_message
            assert "user" in logged_message

    def test_no_context_no_pipe_suffix(self):
        logger = self.StructuredLogger("test")
        with patch.object(logger.logger, "log") as mock_log:
            logger.info("clean message")
            logged_message = mock_log.call_args[0][1]
            assert "|" not in logged_message


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------

class TestGetLogger:
    """Tests for get_logger factory function."""

    def test_returns_structured_logger(self):
        from utils.logging_config import get_logger, StructuredLogger
        result = get_logger("mymodule")
        assert isinstance(result, StructuredLogger)

    def test_name_is_passed_through(self):
        from utils.logging_config import get_logger
        result = get_logger("app.service")
        assert result.logger.name == "app.service"


# ---------------------------------------------------------------------------
# log_execution_time decorator
# ---------------------------------------------------------------------------

class TestLogExecutionTime:
    """Tests for log_execution_time decorator."""

    def test_function_executes_normally(self):
        from utils.logging_config import log_execution_time

        @log_execution_time()
        def add(x, y):
            return x + y

        assert add(2, 3) == 5

    def test_preserves_return_value(self):
        from utils.logging_config import log_execution_time

        @log_execution_time()
        def compute():
            return {"result": 42}

        result = compute()
        assert result == {"result": 42}

    def test_raises_exception_transparently(self):
        from utils.logging_config import log_execution_time

        @log_execution_time()
        def fail():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            fail()

    def test_preserves_function_name(self):
        from utils.logging_config import log_execution_time

        @log_execution_time()
        def my_function():
            return None

        assert my_function.__name__ == "my_function"

    def test_custom_logger_used(self):
        from utils.logging_config import log_execution_time, get_logger

        custom_logger = get_logger("custom_module")
        debug_calls = []

        def capture_debug(msg, **kw):
            debug_calls.append(msg)

        custom_logger.debug = capture_debug

        @log_execution_time(logger=custom_logger)
        def simple():
            return 1

        simple()
        assert len(debug_calls) >= 1

    def test_logs_on_exception(self):
        from utils.logging_config import log_execution_time, get_logger

        custom_logger = get_logger("err_module")
        error_calls = []

        def capture_error(msg, **kw):
            error_calls.append(msg)

        custom_logger.error = capture_error

        @log_execution_time(logger=custom_logger)
        def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            failing()

        assert len(error_calls) >= 1


# ---------------------------------------------------------------------------
# log_api_call decorator
# ---------------------------------------------------------------------------

class TestLogApiCall:
    """Tests for log_api_call decorator."""

    def test_function_executes_normally(self):
        from utils.logging_config import log_api_call

        @log_api_call("TestAPI")
        def fetch_data():
            return [1, 2, 3]

        assert fetch_data() == [1, 2, 3]

    def test_preserves_function_name(self):
        from utils.logging_config import log_api_call

        @log_api_call("TestAPI")
        def my_api_func():
            pass

        assert my_api_func.__name__ == "my_api_func"

    def test_raises_exception_transparently(self):
        from utils.logging_config import log_api_call

        @log_api_call("BadAPI")
        def bad_call():
            raise ConnectionError("no connection")

        with pytest.raises(ConnectionError):
            bad_call()

    def test_logs_api_name_on_call(self):
        from utils.logging_config import log_api_call, get_logger

        custom_logger = get_logger("api_test")
        info_calls = []

        def capture_info(msg, **kw):
            info_calls.append((msg, kw))

        custom_logger.info = capture_info

        @log_api_call("MyExchangeAPI", logger=custom_logger)
        def get_price():
            return 100.0

        get_price()
        api_names = [kw.get("api") for msg, kw in info_calls]
        assert "MyExchangeAPI" in api_names

    def test_logs_on_success(self):
        from utils.logging_config import log_api_call, get_logger

        custom_logger = get_logger("api_success")
        info_calls = []

        def capture_info(msg, **kw):
            info_calls.append(msg)

        custom_logger.info = capture_info

        @log_api_call("TestAPI", logger=custom_logger)
        def success():
            return "ok"

        success()
        assert any("success" in c.lower() or "successful" in c.lower() for c in info_calls)

    def test_logs_on_failure(self):
        from utils.logging_config import log_api_call, get_logger

        custom_logger = get_logger("api_fail")
        error_calls = []

        def capture_error(msg, **kw):
            error_calls.append(msg)

        custom_logger.error = capture_error

        @log_api_call("FailAPI", logger=custom_logger)
        def failing():
            raise RuntimeError("timeout")

        with pytest.raises(RuntimeError):
            failing()

        assert len(error_calls) >= 1


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------

class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_runs_without_error(self):
        from utils.logging_config import setup_logging
        # Should not raise
        setup_logging()

    def test_root_logger_has_handlers_after_setup(self):
        from utils.logging_config import setup_logging
        setup_logging()
        root = logging.getLogger()
        assert len(root.handlers) >= 1

    def test_console_handler_added(self):
        from utils.logging_config import setup_logging
        setup_logging()
        root = logging.getLogger()
        stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1

    def test_noisy_loggers_set_to_warning_or_higher(self):
        from utils.logging_config import setup_logging
        setup_logging()
        for name in ["urllib3", "requests", "yfinance"]:
            level = logging.getLogger(name).level
            assert level >= logging.WARNING, f"{name} should be WARNING or higher, got {level}"

    def test_setup_logging_idempotent(self):
        """Calling setup_logging twice should not crash."""
        from utils.logging_config import setup_logging
        setup_logging()
        setup_logging()
        root = logging.getLogger()
        assert len(root.handlers) >= 1