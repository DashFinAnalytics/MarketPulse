"""Tests for utils/cache.py — MemoryCache, cached decorator, and key helpers."""

import time
import threading
import pytest
from unittest.mock import patch, MagicMock


# ── MemoryCache ──────────────────────────────────────────────────────────────

class TestMemoryCache:
    """Tests for the MemoryCache class."""

    def _make_cache(self):
        from utils.cache import MemoryCache
        return MemoryCache()

    def test_set_and_get(self):
        c = self._make_cache()
        c.set("key1", "value1", ttl=60)
        assert c.get("key1") == "value1"

    def test_get_missing_key_returns_none(self):
        c = self._make_cache()
        assert c.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        c = self._make_cache()
        c.set("key1", "value1", ttl=0)  # Expires immediately
        time.sleep(0.01)
        assert c.get("key1") is None

    def test_delete_existing_key_returns_true(self):
        c = self._make_cache()
        c.set("key1", "value1", ttl=60)
        assert c.delete("key1") is True
        assert c.get("key1") is None

    def test_delete_missing_key_returns_false(self):
        c = self._make_cache()
        assert c.delete("nonexistent") is False

    def test_clear_removes_all(self):
        c = self._make_cache()
        c.set("a", 1, ttl=60)
        c.set("b", 2, ttl=60)
        c.clear()
        assert c.get("a") is None
        assert c.get("b") is None

    def test_cleanup_expired_removes_stale(self):
        c = self._make_cache()
        c.set("fresh", "ok", ttl=60)
        c.set("stale", "gone", ttl=0)
        time.sleep(0.01)
        removed = c.cleanup_expired()
        assert removed == 1
        assert c.get("fresh") == "ok"
        assert c.get("stale") is None

    def test_stats_returns_dict_with_counts(self):
        c = self._make_cache()
        c.set("a", 1, ttl=60)
        c.set("b", 2, ttl=0)
        time.sleep(0.01)
        stats = c.stats()
        assert "total_entries" in stats
        assert "active_entries" in stats
        assert "expired_entries" in stats
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 1
        assert stats["total_entries"] == 2

    def test_overwrite_existing_key(self):
        c = self._make_cache()
        c.set("key", "first", ttl=60)
        c.set("key", "second", ttl=60)
        assert c.get("key") == "second"

    def test_stores_various_types(self):
        c = self._make_cache()
        c.set("list_val", [1, 2, 3], ttl=60)
        c.set("dict_val", {"a": 1}, ttl=60)
        c.set("int_val", 42, ttl=60)
        c.set("none_val", None, ttl=60)
        assert c.get("list_val") == [1, 2, 3]
        assert c.get("dict_val") == {"a": 1}
        assert c.get("int_val") == 42
        # None is stored but get() would return None for both missing and None stored
        # This is a known limitation of the current implementation

    def test_thread_safety(self):
        c = self._make_cache()
        errors = []

        from concurrent.futures import ThreadPoolExecutor

        def writer():
            for i in range(100):
                c.set(f"key_{i}", i, ttl=30)

        def reader():
            for i in range(100):
                c.get(f"key_{i}")

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(writer) for _ in range(3)] + [
                executor.submit(reader) for _ in range(3)
            ]
            for fut in futures:
                fut.result()


# ── cached decorator ─────────────────────────────────────────────────────────

class TestCachedDecorator:
    """Tests for the cached() decorator."""

    def test_cached_decorator_caches_result(self):
        from utils.cache import cached, cache
        cache.clear()

        call_count = 0

        @cached(ttl=60)
        def expensive_fn(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_fn(5)
        result2 = expensive_fn(5)
        assert result1 == 10
        assert result2 == 10
        assert call_count == 1

    def test_cached_decorator_different_args_called_separately(self):
        from utils.cache import cached, cache
        cache.clear()

        call_count = 0

        @cached(ttl=60)
        def fn(x):
            nonlocal call_count
            call_count += 1
            return x + 1

        fn(1)
        fn(2)
        assert call_count == 2

    def test_cached_decorator_with_custom_key_func(self):
        from utils.cache import cached, cache
        cache.clear()

        call_count = 0

        @cached(ttl=60, key_func=lambda x: f"custom:{x}")
        def fn(x):
            nonlocal call_count
            call_count += 1
            return x

        fn("hello")
        fn("hello")
        assert call_count == 1

    def test_cached_decorator_does_not_cache_none(self):
        """If the function returns None, it should NOT be cached (per implementation)."""
        from utils.cache import cached, cache
        cache.clear()

        call_count = 0

        @cached(ttl=60)
        def fn():
            nonlocal call_count
            call_count += 1
            return None

        fn()
        fn()
        # None result is not cached, so fn should be called twice
        assert call_count == 2

    def test_cached_preserves_function_name(self):
        from utils.cache import cached

        @cached(ttl=60)
        def my_function():
            return 42

        assert my_function.__name__ == "my_function"


# ── cache_key_* helpers ──────────────────────────────────────────────────────

class TestCacheKeyHelpers:
    """Tests for cache key generator functions."""

    def test_cache_key_for_symbol_uppercase(self):
        from utils.cache import cache_key_for_symbol
        key = cache_key_for_symbol("spy")
        assert "SPY" in key

    def test_cache_key_for_symbol_includes_data_type(self):
        from utils.cache import cache_key_for_symbol
        key = cache_key_for_symbol("SPY", data_type="index")
        assert "index" in key
        assert "SPY" in key

    def test_cache_key_for_symbol_default_data_type(self):
        from utils.cache import cache_key_for_symbol
        key = cache_key_for_symbol("SPY")
        assert "asset" in key

    def test_cache_key_for_news(self):
        from utils.cache import cache_key_for_news
        key = cache_key_for_news(source="yahoo", limit=5)
        assert "yahoo" in key
        assert "5" in key

    def test_cache_key_for_news_defaults(self):
        from utils.cache import cache_key_for_news
        key = cache_key_for_news()
        assert "all" in key
        assert "10" in key

    def test_cache_key_for_analysis(self):
        from utils.cache import cache_key_for_analysis
        key = cache_key_for_analysis("aapl", "dcf")
        assert "AAPL" in key
        assert "dcf" in key

    def test_cache_key_for_symbol_different_symbols_different_keys(self):
        from utils.cache import cache_key_for_symbol
        key1 = cache_key_for_symbol("SPY")
        key2 = cache_key_for_symbol("QQQ")
        assert key1 != key2

    def test_cache_key_for_analysis_different_types_different_keys(self):
        from utils.cache import cache_key_for_analysis
        key1 = cache_key_for_analysis("AAPL", "dcf")
        key2 = cache_key_for_analysis("AAPL", "growth")
        assert key1 != key2


# ── periodic_cleanup ─────────────────────────────────────────────────────────

class TestPeriodicCleanup:
    """Tests for periodic_cleanup()."""

    def test_periodic_cleanup_returns_int(self):
        from utils.cache import periodic_cleanup, cache
        cache.clear()
        result = periodic_cleanup()
        assert isinstance(result, int)
        assert result >= 0

    def test_periodic_cleanup_removes_expired(self):
        from utils.cache import periodic_cleanup, cache
        cache.clear()
        cache.set("expire_me", "val", ttl=0)
        time.sleep(0.01)
        removed = periodic_cleanup()
        assert removed >= 1