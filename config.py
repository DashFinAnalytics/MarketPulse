"""Centralized configuration for MarketPulse.

This module is intentionally conservative:
- Optional services should degrade gracefully.
- Environment parsing is centralized here.
- Validation should surface warnings rather than block app startup,
  unless a setting is truly unsafe.
"""

from __future__ import annotations

import os
import secrets
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


_ENV_PATH = Path(__file__).parent / ".env"
if _ENV_PATH.exists():
    if load_dotenv is not None:
        load_dotenv(_ENV_PATH)
    else:
        warnings.warn(
            f"Config: .env file found at {_ENV_PATH} but python-dotenv is not installed; "
            "environment variables from this file will be ignored.",
            RuntimeWarning,
            stacklevel=2,
        )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    true_values = {"1", "true", "yes", "on"}
    false_values = {"0", "false", "no", "off"}
    if normalized in true_values:
        return True
    if normalized in false_values:
        return False
    warnings.warn(
        f"Config: unrecognized boolean value for {name!r}: {value!r}; using default {default}",
        stacklevel=2,
    )
    return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value.strip())
    except (TypeError, ValueError):
        warnings.warn(
            f"Invalid integer for environment variable {name!r}: {value!r}. Using default {default}.",
            RuntimeWarning,
            stacklevel=2,
        )
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return float(value.strip())
    except (TypeError, ValueError):
        warnings.warn(
            f"Invalid float for environment variable {name!r}: {value!r}. Using default {default}.",
            RuntimeWarning,
            stacklevel=2,
        )
        return default


@dataclass
class DatabaseConfig:
    url: Optional[str] = field(default_factory=lambda: os.getenv("DATABASE_URL"))
    pool_size: int = field(default_factory=lambda: _env_int("DB_POOL_SIZE", 10))
    max_overflow: int = field(default_factory=lambda: _env_int("DB_MAX_OVERFLOW", 20))
    pool_timeout: int = field(default_factory=lambda: _env_int("DB_POOL_TIMEOUT", 30))
    pool_recycle: int = field(default_factory=lambda: _env_int("DB_POOL_RECYCLE", 3600))
    echo: bool = field(default_factory=lambda: _env_bool("DB_ECHO", False))
    enabled: bool = field(default_factory=lambda: _env_bool("ENABLE_DATABASE", True))

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    @property
    def is_available(self) -> bool:
        return self.enabled and self.is_configured


@dataclass
class APIConfig:
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    openai_max_tokens: int = field(default_factory=lambda: _env_int("OPENAI_MAX_TOKENS", 2000))
    openai_temperature: float = field(default_factory=lambda: _env_float("OPENAI_TEMPERATURE", 0.1))
    yfinance_timeout: int = field(default_factory=lambda: _env_int("YFINANCE_TIMEOUT", 10))
    yfinance_retry_attempts: int = field(default_factory=lambda: _env_int("YFINANCE_RETRY_ATTEMPTS", 3))
    news_sources_timeout: int = field(default_factory=lambda: _env_int("NEWS_SOURCES_TIMEOUT", 15))
    max_news_articles: int = field(default_factory=lambda: _env_int("MAX_NEWS_ARTICLES", 50))

    @property
    def ai_available(self) -> bool:
        return bool(self.openai_api_key)


@dataclass
class CacheConfig:
    default_ttl: int = field(default_factory=lambda: _env_int("CACHE_DEFAULT_TTL", 300))
    market_data_ttl: int = field(default_factory=lambda: _env_int("CACHE_MARKET_DATA_TTL", 60))
    news_ttl: int = field(default_factory=lambda: _env_int("CACHE_NEWS_TTL", 900))
    fundamental_data_ttl: int = field(default_factory=lambda: _env_int("CACHE_FUNDAMENTAL_TTL", 3600))
    redis_url: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_URL"))
    redis_db: int = field(default_factory=lambda: _env_int("REDIS_DB", 0))


@dataclass
class AppConfig:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: _env_bool("DEBUG", False))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    title: str = field(default_factory=lambda: os.getenv("APP_TITLE", "MarketPulse"))
    streamlit_host: str = field(default_factory=lambda: os.getenv("STREAMLIT_HOST", "0.0.0.0"))
    streamlit_port: int = field(default_factory=lambda: _env_int("STREAMLIT_PORT", 5000))
    # Random per-process default; sessions are invalidated on restart.
    # Always set SECRET_KEY explicitly in any persistent or production deployment.
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY") or secrets.token_hex(32))
    enable_ai_analysis: bool = field(default_factory=lambda: _env_bool("ENABLE_AI_ANALYSIS", True))
    enable_news_fetching: bool = field(default_factory=lambda: _env_bool("ENABLE_NEWS_FETCHING", True))
    enable_real_time_updates: bool = field(default_factory=lambda: _env_bool("ENABLE_REAL_TIME_UPDATES", False))
    show_system_status: bool = field(default_factory=lambda: _env_bool("SHOW_SYSTEM_STATUS", True))


class Config:
    """Top-level configuration object.

    Guardrail: validation should not block startup merely because optional
    services are unavailable. Instead, warnings are accumulated and exposed.
    """

    def __init__(self) -> None:
        self.database = DatabaseConfig()
        self.api = APIConfig()
        self.cache = CacheConfig()
        self.app = AppConfig()
        self.warnings: List[str] = []
        self._validate_config()

    def _validate_config(self) -> None:
        if self.app.enable_ai_analysis and not self.api.ai_available:
            self.warnings.append(
                "AI analysis is enabled but OPENAI_API_KEY is not configured; AI features should degrade gracefully."
            )

        if self.database.enabled and not self.database.is_configured:
            self.warnings.append(
                "Database support is enabled but DATABASE_URL is not configured; database-backed features should degrade gracefully."
            )

        if self.app.environment.lower() == "development" and not self.app.debug:
            self.warnings.append(
                "ENVIRONMENT=development but DEBUG is false; this is allowed but may hide useful diagnostics."
            )

        if not os.getenv("SECRET_KEY"):
            if self.app.environment.lower() != "development":
                self.warnings.append(
                    "SECRET_KEY is not configured in a non-development environment; this is a security risk."
                )
            else:
                self.warnings.append(
                    "SECRET_KEY is not set; using a randomly generated per-process key for development."
                )

    def get_warning_summary(self) -> List[str]:
        return list(self.warnings)


config = Config()
