"""Custom exceptions for MarketPulse.

Guardrail: call sites should raise narrow exceptions near the source and
translate them into user-facing messages at the application boundary.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class MarketPulseException(Exception):
    """Base exception for MarketPulse application."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(MarketPulseException):
    """Raised when there is a configuration issue."""


class DataFetchError(MarketPulseException):
    """Raised when market or reference data fetching fails."""


class DatabaseError(MarketPulseException):
    """Raised when database operations fail."""


class APIError(MarketPulseException):
    """Raised when an external API call fails."""


class ExternalServiceError(MarketPulseException):
    """Raised when an optional external service is unavailable."""


class ValidationError(MarketPulseException):
    """Raised when user or application data is invalid."""


class CacheError(MarketPulseException):
    """Raised when cache operations fail."""


class ChartError(MarketPulseException):
    """Raised when chart creation fails."""


class NewsError(MarketPulseException):
    """Raised when news fetching or processing fails."""


class AIAnalysisError(MarketPulseException):
    """Raised when AI analysis fails."""


class BacktestError(MarketPulseException):
    """Raised when backtesting or simulation logic fails."""
