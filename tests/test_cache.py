"""Tests for utils/cache.py — MemoryCache, cached decorator, key helpers."""
import time
import threading
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# MemoryCache
# ---------------------------------------------------------------------------

class TestMemoryCache:
    """Tests for MemoryCache class."""

    def setup_method(self):
        from utils.cache import MemoryCache
        self.cache = MemoryCache()

    def test_set_and_get_basic_value(self):
        self.cache.set("key1", "value1", ttl=60)
        assert self.cache.get("key1") == "value1"

    def test_get_returns_none_for_missing_key(self):
        assert self.cache.get("nonexistent") is None

    def test_get_returns_none_after_ttl_expires(self):
        self.cache.set("expiring", "data", ttl=1)
        # Simulate TTL expiry by manipulating the internal cache entry
        with self.cache._lock:
            self.cache._cache["expiring"]["expires_at"] = time.monotonic() - 1
        assert self.cache.get("expiring") is None

    def test_get_removes_expired_entry(self):
        self.cache.set("toexpire", "data", ttl=1)
        with self.cache._lock:
            self.cache._cache["toexpire"]["expires_at"] = time.monotonic() - 1
        self.cache.get("toexpire")
        with self.cache._lock:
            assert "toexpire" not in self.cache._cache

    def test_set_overwrites_existing_key(self):
        self.cache.set("k", "v1", ttl=60)
        self.cache.set("k", "v2", ttl=60)
        assert self.cache.get("k") == "v2"

    def test_delete_existing_key_returns_true(self):
        self.cache.set("del_key", "val", ttl=60)
        result = self.cache.delete("del_key")
        assert result is True
        assert self.cache.get("del_key") is None

    def test_delete_nonexistent_key_returns_false(self):
        result = self.cache.delete("does_not_exist")
        assert result is False

    def test_clear_removes_all_entries(self):
        self.cache.set("a", 1, ttl=60)
        self.cache.set("b", 2, ttl=60)
        self.cache.clear()
        assert self.cache.get("a") is None
        assert self.cache.get("b") is None

    def test_cleanup_expired_returns_count_of_removed(self):
        self.cache.set("live", "data", ttl=60)
        self.cache.set("dead1", "data", ttl=60)
        self.cache.set("dead2", "data", ttl=60)
        # Manually expire two entries
        with self.cache._lock:
            self.cache._cache["dead1"]["expires_at"] = time.monotonic() - 1
            self.cache._cache["dead2"]["expires_at"] = time.monotonic() - 1
        removed = self.cache.cleanup_expired()
        assert removed == 2

    def test_cleanup_expired_does_not_remove_live_entries(self):
        self.cache.set("live", "data", ttl=60)
        self.cache.cleanup_expired()
        assert self.cache.get("live") == "data"

    def test_stats_returns_correct_counts(self):
        self.cache.set("a", 1, ttl=60)
        self.cache.set("b", 2, ttl=60)
        # Expire one entry
        with self.cache._lock:
            self.cache._cache["b"]["expires_at"] = time.monotonic() - 1
        stats = self.cache.stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 1

    def test_stats_empty_cache(self):
        stats = self.cache.stats()
        assert stats["total_entries"] == 0
        assert stats["active_entries"] == 0
        assert stats["expired_entries"] == 0

    def test_stores_various_types(self):
        self.cache.set("list_val", [1, 2, 3], ttl=60)
        self.cache.set("dict_val", {"a": 1}, ttl=60)
        self.cache.set("int_val", 42, ttl=60)
        self.cache.set("none_val", None, ttl=60)  # None is stored as None
        assert self.cache.get("list_val") == [1, 2, 3]
        assert self.cache.get("dict_val") == {"a": 1}
        assert self.cache.get("int_val") == 42
        # None stored value — get returns None but that's also cache-miss sentinel
        # This is a known limitation; cache treats None as miss

    def test_thread_safety_concurrent_set_get(self):
        errors = []

        def worker(i):
            try:
                key = f"thread_{i}"
                self.cache.set(key, i, ttl=60)
                result = self.cache.get(key)
                assert result == i
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []

    def test_uses_default_ttl_from_config_when_ttl_is_none(self):
        """When ttl=None, the cache should use config.cache.default_ttl."""
        with patch("utils.cache.config") as mock_config:
            mock_config.cache.default_ttl = 300
            from utils.cache import MemoryCache
            c = MemoryCache()
            c.set("key", "val")  # ttl defaults to None
            entry = c._cache["key"]
            # expires_at should be roughly now + 300 seconds
            assert entry["expires_at"] > time.monotonic() + 290


# ---------------------------------------------------------------------------
# cached decorator
# ---------------------------------------------------------------------------

class TestCachedDecorator:
    """Tests for the cached() decorator."""

    def setup_method(self):
        # Use a fresh MemoryCache to avoid cross-test pollution
        from utils.cache import MemoryCache
        self._fresh_cache = MemoryCache()

    def test_caches_function_result(self):
        from utils.cache import cached, cache

        call_count = 0

        @cached(ttl=60)
        def expensive(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        r1 = expensive(5)
        r2 = expensive(5)
        assert r1 == 10
        assert r2 == 10
        assert call_count == 1  # function only called once

    def test_different_args_cached_separately(self):
        from utils.cache import cached

        call_count = 0

        @cached(ttl=60)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x + 1

        func(1)
        func(2)
        assert call_count == 2

    def test_none_result_not_cached(self):
        """Functions returning None should not cache the result."""
        from utils.cache import cached

        call_count = 0

        @cached(ttl=60)
        def returns_none(x):
            nonlocal call_count
            call_count += 1
            return None

        returns_none(1)
        returns_none(1)
        assert call_count == 2  # called twice because None is not cached

    def test_custom_key_func_used(self):
        from utils.cache import cached, cache

        call_count = 0

        @cached(ttl=60, key_func=lambda x: f"custom:{x}")
        def func(x):
            nonlocal call_count
            call_count += 1
            return x

        func(99)
        assert cache.get("custom:99") == 99

    def test_preserves_function_name(self):
        from utils.cache import cached

        @cached(ttl=60)
        def my_function():
            return 42

        assert my_function.__name__ == "my_function"

    def test_kwargs_cached_correctly(self):
        from utils.cache import cached

        call_count = 0

        @cached(ttl=60)
        def func(x, y=10):
            nonlocal call_count
            call_count += 1
            return x + y

        r1 = func(1, y=10)
        r2 = func(1, y=10)
        assert r1 == r2 == 11
        assert call_count == 1


# ---------------------------------------------------------------------------
# Cache key helper functions
# ---------------------------------------------------------------------------

class TestCacheKeyHelpers:
    """Tests for cache_key_for_symbol, cache_key_for_news, cache_key_for_analysis."""

    def setup_method(self):
        from utils.cache import (
            cache_key_for_symbol,
            cache_key_for_news,
            cache_key_for_analysis,
        )
        self.cache_key_for_symbol = cache_key_for_symbol
        self.cache_key_for_news = cache_key_for_news
        self.cache_key_for_analysis = cache_key_for_analysis

    def test_symbol_key_uppercases_symbol(self):
        key = self.cache_key_for_symbol("aapl")
        assert "AAPL" in key

    def test_symbol_key_includes_data_type(self):
        key = self.cache_key_for_symbol("SPY", data_type="ticker")
        assert "ticker" in key

    def test_symbol_key_default_data_type(self):
        key = self.cache_key_for_symbol("SPY")
        assert "asset" in key

    def test_symbol_key_different_types_differ(self):
        k1 = self.cache_key_for_symbol("SPY", data_type="ticker")
        k2 = self.cache_key_for_symbol("SPY", data_type="options")
        assert k1 != k2

    def test_news_key_includes_source_and_limit(self):
        key = self.cache_key_for_news("yahoo", 20)
        assert "yahoo" in key
        assert "20" in key

    def test_news_key_default_values(self):
        key = self.cache_key_for_news()
        assert "all" in key
        assert "10" in key

    def test_news_key_different_sources_differ(self):
        k1 = self.cache_key_for_news("yahoo")
        k2 = self.cache_key_for_news("reuters")
        assert k1 != k2

    def test_analysis_key_uppercases_symbol(self):
        key = self.cache_key_for_analysis("aapl", "dcf")
        assert "AAPL" in key

    def test_analysis_key_includes_analysis_type(self):
        key = self.cache_key_for_analysis("AAPL", "growth")
        assert "growth" in key

    def test_analysis_key_different_types_differ(self):
        k1 = self.cache_key_for_analysis("AAPL", "dcf")
        k2 = self.cache_key_for_analysis("AAPL", "growth")
        assert k1 != k2


# ---------------------------------------------------------------------------
# periodic_cleanup
# ---------------------------------------------------------------------------

class TestPeriodicCleanup:
    """Tests for periodic_cleanup helper."""

    def test_periodic_cleanup_returns_int(self):
        from utils.cache import periodic_cleanup
        result = periodic_cleanup()
        assert isinstance(result, int)
        assert result >= 0

    def test_periodic_cleanup_removes_expired(self):
        from utils.cache import cache, periodic_cleanup
        cache.set("temp_cleanup_test", "data", ttl=60)
        with cache._lock:
            cache._cache["temp_cleanup_test"]["expires_at"] = time.monotonic() - 1
        before_count = len(cache._cache)
        removed = periodic_cleanup()
        assert removed >= 1
        assert cache.get("temp_cleanup_test") is None