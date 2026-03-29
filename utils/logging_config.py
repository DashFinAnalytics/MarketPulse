"""Structured logging for MarketPulse.

Guardrail: service-layer code should log structured context near the source.
UI-layer code should convert exceptions into user messages, not raw traces,
unless debug mode is enabled.
"""

from __future__ import annotations

import logging
import sys
import time
from functools import wraps
from typing import Any, Callable, Optional

from config import config


class StructuredLogger:
    """Thin structured wrapper around stdlib logging."""

    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(name)
        self.context: dict[str, Any] = {}

    def with_context(self, **kwargs: Any) -> "StructuredLogger":
        new_logger = StructuredLogger(self.logger.name)
        new_logger.context = {**self.context, **kwargs}
        return new_logger

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        context = {**self.context, **kwargs}
        if context:
            rendered = " | ".join(f"{key}={value}" for key, value in context.items())
            message = f"{message} | {rendered}"
        self.logger.log(level, message)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)


def log_execution_time(logger: Optional[StructuredLogger] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_logger = logger or get_logger(func.__module__)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                func_logger.debug(func.__name__, execution_time=f"{time.perf_counter() - start:.3f}s")
                return result
            except Exception as exc:
                func_logger.error(
                    f"{func.__name__} failed",
                    error=str(exc),
                    execution_time=f"{time.perf_counter() - start:.3f}s",
                )
                raise

        return wrapper

    return decorator


def log_api_call(api_name: str, logger: Optional[StructuredLogger] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_logger = logger or get_logger(func.__module__)
            func_logger.info("API call started", api=api_name, function=func.__name__)
            try:
                result = func(*args, **kwargs)
                func_logger.info("API call successful", api=api_name, function=func.__name__)
                return result
            except Exception as exc:
                func_logger.error(
                    "API call failed",
                    api=api_name,
                    function=func.__name__,
                    error=str(exc),
                )
                raise

        return wrapper

    return decorator


class StreamlitLogHandler(logging.Handler):
    """Optional Streamlit-aware log handler for UI diagnostics."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            import streamlit as st

            message = self.format(record)
            if record.levelno >= logging.ERROR:
                st.error(f"🚨 {message}")
            elif record.levelno >= logging.WARNING:
                st.warning(f"⚠️ {message}")
            elif record.levelno >= logging.INFO and config.app.debug:
                st.info(f"ℹ️ {message}")
        except Exception:
            print(self.format(record), file=sys.stderr)


def setup_logging() -> None:
    root_logger = logging.getLogger()

    for handler in list(root_logger.handlers):
        try:
            if hasattr(handler, "flush"):
                handler.flush()  # type: ignore[call-arg]
        except Exception as exc:
            root_logger.debug("Failed to flush log handler during cleanup: %s", exc)

        try:
            handler.close()
        except Exception as exc:
            root_logger.debug("Failed to close log handler during cleanup: %s", exc)

        root_logger.removeHandler(handler)

    root_logger.setLevel(getattr(logging, config.app.log_level.upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if not config.app.debug:
        try:
            file_handler = logging.FileHandler("marketpulse.log")
        except OSError as exc:
            root_logger.warning(
                "File logging disabled: could not open log file 'marketpulse.log': %s",
                exc,
            )
        else:
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    if config.app.debug:
        ui_handler = StreamlitLogHandler()
        ui_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root_logger.addHandler(ui_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)

