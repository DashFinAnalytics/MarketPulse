"""Conservative runtime helpers for wiring app.py into the PR1 scaffold.

These helpers are intentionally narrow. They centralize startup, status,
cache cleanup, and user-facing error rendering without changing page logic.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from app_init import get_app_status, initialize_app
from config import config
from utils.cache import periodic_cleanup
from utils.logging_config import get_logger

logger = get_logger(__name__)


@st.cache_resource
def initialize_application() -> Dict[str, Any]:
    """Initialize the app once per Streamlit process.

    Guardrail: failures should degrade the app rather than crash startup.
    """
    try:
        status = initialize_app()
        logger.info("Application initialized", status=status.get("status", "unknown"))
        return status
    except Exception as exc:
        logger.error("Application initialization failed", error=str(exc))
        return {
            "status": "degraded",
            "initialization_error": str(exc),
            "database": {"status": "degraded", "health": False},
            "cache": {"status": "degraded"},
            "health_checks": {
                "database": False,
                "cache": False,
                "openai": False,
            },
        }


def database_is_ready(init_status: Dict[str, Any]) -> bool:
    database = init_status.get("database", {})
    return bool(database.get("health") is True or database.get("status") == "initialized")


def cleanup_service_cache() -> int:
    """Run best-effort cleanup of the service-layer cache."""
    try:
        cleaned = periodic_cleanup()
        if cleaned and config.app.debug:
            logger.info("Expired service cache entries removed", removed=cleaned)
        return cleaned
    except Exception as exc:
        logger.warning("Service cache cleanup failed", error=str(exc))
        return 0


def render_system_status_sidebar() -> None:
    """Render compact runtime status in the Streamlit sidebar."""
    if not config.app.show_system_status:
        return

    try:
        app_status = get_app_status()
        init_status = app_status.get("initialization_status", {})
        database = init_status.get("database", {})
        cache = init_status.get("cache", {})
        health = init_status.get("health_checks", {})
        warnings = init_status.get("configuration", {}).get("warnings", [])

        with st.sidebar.expander("System Status", expanded=False):
            st.caption(f"Environment: {app_status.get('environment', 'unknown')}")
            st.write(f"Database: {database.get('status', 'unknown')}")
            st.write(f"Cache: {cache.get('status', 'unknown')}")
            st.write(f"OpenAI: {health.get('openai', 'unknown')}")
            if warnings:
                st.warning("\n".join(f"- {warning}" for warning in warnings[:3]))
    except Exception as exc:
        logger.warning("Failed to render system status sidebar", error=str(exc))


def render_ui_error(message: str, error: Exception | None = None) -> None:
    """Render predictable UI errors and log full detail centrally."""
    if error is not None:
        logger.error(message, error=str(error))
    else:
        logger.error(message)

    if config.app.debug and error is not None:
        st.error(message)
        st.exception(error)
    else:
        st.error(message)
