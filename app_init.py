"""Application initialization scaffold for MarketPulse.

Guardrail: application startup should report degraded services rather than
failing outright when optional dependencies are missing.
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict

from config import config
from utils.cache import cache
from utils.exceptions import ConfigurationError
from utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def _get_git_sha() -> str:
    """Return the short git SHA of HEAD, or 'unknown' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return "unknown"


_APP_VERSION = _get_git_sha()


class AppInitializer:
    """Handles startup sequencing and service health reporting."""

    def __init__(self) -> None:
        self.initialization_status: Dict[str, Any] = {}

    def initialize(self) -> Dict[str, Any]:
        try:
            self._setup_logging()
        except Exception as exc:  # pragma: no cover - logging setup is foundational
            raise ConfigurationError(f"Logging setup failed: {exc}") from exc

        self._validate_configuration()
        self._setup_cache()
        self._initialize_database()
        self._perform_health_checks()
        self.initialization_status["status"] = "ready"
        return self.initialization_status

    def _setup_logging(self) -> None:
        setup_logging()
        self.initialization_status["logging"] = "configured"
        logger.info("Logging configured")

    def _validate_configuration(self) -> None:
        self.initialization_status["configuration"] = {
            "environment": config.app.environment,
            "debug": config.app.debug,
            "database_enabled": config.database.enabled,
            "database_configured": config.database.is_configured,
            "ai_enabled": config.app.enable_ai_analysis,
            "ai_available": config.api.ai_available,
            "warnings": config.get_warning_summary(),
        }
        if config.get_warning_summary():
            logger.warning("Configuration warnings present", warnings=config.get_warning_summary())

    def _setup_cache(self) -> None:
        try:
            cache.clear()
            self.initialization_status["cache"] = {
                "status": "initialized",
                "default_ttl": config.cache.default_ttl,
            }
        except Exception as exc:
            logger.warning("Cache setup degraded", error=str(exc))
            self.initialization_status["cache"] = {"status": "degraded", "error": str(exc)}

    def _initialize_database(self) -> None:
        if not config.database.is_available:
            self.initialization_status["database"] = {
                "status": "disabled_or_unconfigured",
            }
            return

        try:
            from database import db_manager

            db_manager.create_tables()
            health = False
            if hasattr(db_manager, "health_check"):
                health = bool(db_manager.health_check())
            self.initialization_status["database"] = {
                "status": "initialized" if health or not hasattr(db_manager, "health_check") else "degraded",
                "health": health if hasattr(db_manager, "health_check") else "unknown",
            }
        except Exception as exc:
            logger.warning("Database initialization degraded", error=str(exc))
            self.initialization_status["database"] = {
                "status": "degraded",
                "error": str(exc),
            }

    def _perform_health_checks(self) -> None:
        health_status: Dict[str, Any] = {}

        try:
            cache.set("health_check", "ok", 10)
            health_status["cache"] = cache.get("health_check") == "ok"
            cache.delete("health_check")
        except Exception as exc:
            logger.warning("Cache health check failed", error=str(exc))
            health_status["cache"] = False

        if config.database.is_available:
            try:
                from database import db_manager

                health_status["database"] = bool(
                    db_manager.health_check() if hasattr(db_manager, "health_check") else True
                )
            except Exception as exc:
                logger.warning("Database health check failed", error=str(exc))
                health_status["database"] = False
        else:
            health_status["database"] = "not_configured"

        health_status["openai"] = config.api.ai_available if config.app.enable_ai_analysis else "disabled"
        self.initialization_status["health_checks"] = health_status

    def get_system_info(self) -> Dict[str, Any]:
        return {
            "app_version": _APP_VERSION,
            "environment": config.app.environment,
            "initialization_status": self.initialization_status,
            "features": {
                "ai_analysis": config.app.enable_ai_analysis,
                "news_fetching": config.app.enable_news_fetching,
                "real_time_updates": config.app.enable_real_time_updates,
            },
            "cache_stats": cache.stats(),
        }


app_initializer = AppInitializer()


def initialize_app() -> Dict[str, Any]:
    return app_initializer.initialize()


def get_app_status() -> Dict[str, Any]:
    return app_initializer.get_system_info()
