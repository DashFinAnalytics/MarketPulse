"""Caching utilities for MarketPulse.

This cache is complementary to Streamlit caching. Use it for service-layer
state and logic that should not depend on Streamlit runtime semantics.
"""

from __future__ import annotations

import hashlib
import logging
import pickle
import threading
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from config import config

_log = logging.getLogger(__name__)


class MemoryCache:
    """Simple thread-safe in-memory TTL cache."""

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry["expires_at"]:
                del self._cache[key]
                return None
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_in = ttl if ttl is not None else config.cache.default_ttl
        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.monotonic() + expires_in,
                "created_at": time.time(),
            }

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        with self._lock:
            now = time.monotonic()
            expired = [key for key, value in self._cache.items() if now > value["expires_at"]]
            for key in expired:
                del self._cache[key]
            return len(expired)

    def stats(self) -> Dict[str, int]:
        with self._lock:
            now = time.monotonic()
            active_entries = sum(1 for value in self._cache.values() if now <= value["expires_at"])
            return {
                "total_entries": len(self._cache),
                "active_entries": active_entries,
                "expired_entries": len(self._cache) - active_entries,
            }


cache = MemoryCache()


def cached(ttl: Optional[int] = None, key_func: Optional[Callable[..., str]] = None) -> Callable:
    """Cache decorator for pure-ish service functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                func_id = f"{func.__module__}.{func.__qualname__}"
                try:
                    args_hash = hashlib.sha256(
                        pickle.dumps((args, sorted(kwargs.items())))
                    ).hexdigest()
                except (pickle.PickleError, TypeError, AttributeError) as exc:
                    _log.warning(
                        "cache: pickle serialisation failed for %s; falling back to repr. Error: %s",
                        func_id,
                        exc,
                    )
                    args_hash = hashlib.sha256(
                        repr((args, sorted(kwargs.items()))).encode()
                    ).hexdigest()
                cache_key = f"{func_id}:{args_hash}"

            result = cache.get(cache_key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


def cache_key_for_symbol(symbol: str, data_type: str = "asset") -> str:
    return f"symbol:{data_type}:{symbol.upper()}"


def cache_key_for_news(source: str = "all", limit: int = 10) -> str:
    return f"news:{source}:{limit}"


def cache_key_for_analysis(symbol: str, analysis_type: str) -> str:
    return f"analysis:{analysis_type}:{symbol.upper()}"


def periodic_cleanup() -> int:
    return cache.cleanup_expired()
