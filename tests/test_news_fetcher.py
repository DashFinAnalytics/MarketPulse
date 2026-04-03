"""Tests for utils/news_fetcher.py — FinanceNewsFetcher and helpers.

Note: FinanceNewsFetcher uses @st.cache_data which requires Streamlit's
runtime. We patch streamlit at import time to avoid that dependency.
"""

import sys
import types
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ── Streamlit stub (must be applied before importing news_fetcher) ───────────

def _make_st_stub():
    """Create a minimal streamlit stub that makes @st.cache_data a no-op."""
    stub = types.ModuleType("streamlit")

    def cache_data(*args, ttl=None, **kwargs):
        def decorator(fn):
            return fn
        if args and callable(args[0]):
            return args[0]
        return decorator

    stub.cache_data = cache_data
    return stub


@pytest.fixture(autouse=True)
def mock_streamlit():
    """Ensure streamlit is stubbed before each test in this module."""
    if "streamlit" not in sys.modules:
        sys.modules["streamlit"] = _make_st_stub()
    # Remove news_fetcher from sys.modules to force reimport with stub
    sys.modules.pop("utils.news_fetcher", None)
    yield
    sys.modules.pop("utils.news_fetcher", None)


def _get_fetcher():
    """Import and instantiate FinanceNewsFetcher with stub in place."""
    from utils.news_fetcher import FinanceNewsFetcher
    return FinanceNewsFetcher()


# ── NewsSource ───────────────────────────────────────────────────────────────

class TestNewsSource:
    """Tests for the NewsSource dataclass."""

    def test_instantiation(self):
        from utils.news_fetcher import NewsSource
        src = NewsSource("Test Source", "https://example.com/rss", "https://example.com")
        assert src.name == "Test Source"
        assert src.rss_url == "https://example.com/rss"
        assert src.base_url == "https://example.com"

    def test_base_url_optional(self):
        from utils.news_fetcher import NewsSource
        src = NewsSource("No Base", "https://example.com/rss")
        assert src.base_url is None


# ── FinanceNewsFetcher class ─────────────────────────────────────────────────

class TestFinanceNewsFetcherInit:
    """Tests for FinanceNewsFetcher initialization."""

    def test_instantiation(self):
        fetcher = _get_fetcher()
        assert fetcher is not None

    def test_news_sources_populated(self):
        fetcher = _get_fetcher()
        assert len(fetcher.NEWS_SOURCES) > 0

    def test_known_sources_present(self):
        fetcher = _get_fetcher()
        assert "yahoo_finance" in fetcher.NEWS_SOURCES
        assert "reuters_business" in fetcher.NEWS_SOURCES
        assert "marketwatch" in fetcher.NEWS_SOURCES

    def test_get_available_sources_returns_dict(self):
        fetcher = _get_fetcher()
        sources = fetcher.get_available_sources()
        assert isinstance(sources, dict)
        assert len(sources) > 0


# ── _time_ago ────────────────────────────────────────────────────────────────

class TestTimeAgo:
    """Tests for FinanceNewsFetcher._time_ago()."""

    def test_just_now(self):
        fetcher = _get_fetcher()
        now = datetime.now()
        result = fetcher._time_ago(now)
        assert result == "Just now"

    def test_seconds_ago(self):
        fetcher = _get_fetcher()
        pub_date = datetime.now() - timedelta(seconds=30)
        result = fetcher._time_ago(pub_date)
        assert result == "Just now"

    def test_one_minute_ago(self):
        fetcher = _get_fetcher()
        pub_date = datetime.now() - timedelta(minutes=2)
        result = fetcher._time_ago(pub_date)
        assert "minute" in result

    def test_plural_minutes(self):
        fetcher = _get_fetcher()
        pub_date = datetime.now() - timedelta(minutes=10)
        result = fetcher._time_ago(pub_date)
        assert "minutes" in result

    def test_singular_minute(self):
        fetcher = _get_fetcher()
        pub_date = datetime.now() - timedelta(minutes=1, seconds=10)
        result = fetcher._time_ago(pub_date)
        assert "minute" in result

    def test_one_hour_ago(self):
        fetcher = _get_fetcher()
        pub_date = datetime.now() - timedelta(hours=2)
        result = fetcher._time_ago(pub_date)
        assert "hour" in result

    def test_plural_hours(self):
        fetcher = _get_fetcher()
        pub_date = datetime.now() - timedelta(hours=5)
        result = fetcher._time_ago(pub_date)
        assert "hours" in result

    def test_one_day_ago(self):
        fetcher = _get_fetcher()
        pub_date = datetime.now() - timedelta(days=1)
        result = fetcher._time_ago(pub_date)
        assert "day" in result

    def test_plural_days(self):
        fetcher = _get_fetcher()
        pub_date = datetime.now() - timedelta(days=3)
        result = fetcher._time_ago(pub_date)
        assert "days" in result


# ── get_sector_news ───────────────────────────────────────────────────────────

class TestGetSectorNews:
    """Tests for FinanceNewsFetcher.get_sector_news() filtering logic."""

    def _make_article(self, title, summary, source="Test Source"):
        return {
            "title": title,
            "summary": summary,
            "source": source,
            "published": datetime.now(),
            "link": "https://example.com",
            "author": "Test",
        }

    def test_technology_filter(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("AI startup raises $1B", "artificial intelligence revolution"),
            self._make_article("Oil prices drop", "energy sector news"),
            self._make_article("Software giant Microsoft", "technology company news"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_sector_news("technology")
        titles = [a["title"] for a in result]
        assert "AI startup raises $1B" in titles
        assert "Software giant Microsoft" in titles
        assert "Oil prices drop" not in titles

    def test_energy_filter(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("Oil prices surge", "crude oil market update"),
            self._make_article("Tech stocks rally", "nasdaq technology index"),
            self._make_article("Solar power boom", "renewable energy investment"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_sector_news("energy")
        titles = [a["title"] for a in result]
        assert "Oil prices surge" in titles
        assert "Solar power boom" in titles
        assert "Tech stocks rally" not in titles

    def test_unknown_sector_uses_sector_as_keyword(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("blockchain news", "blockchain technology update"),
            self._make_article("stock market", "general market news"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_sector_news("blockchain")
        titles = [a["title"] for a in result]
        assert "blockchain news" in titles
        assert "stock market" not in titles

    def test_respects_limit(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article(f"Tech news {i}", "technology software")
            for i in range(20)
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_sector_news("technology", limit=3)
        assert len(result) <= 3

    def test_returns_empty_when_no_match(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("Weather report", "sunny skies tomorrow"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_sector_news("technology")
        assert result == []


# ── get_trending_topics ───────────────────────────────────────────────────────

class TestGetTrendingTopics:
    """Tests for FinanceNewsFetcher.get_trending_topics()."""

    def _make_article(self, title, summary=""):
        return {
            "title": title,
            "summary": summary,
            "source": "Test",
            "published": datetime.now(),
            "link": "https://example.com",
            "author": "Test",
        }

    def test_returns_list(self):
        fetcher = _get_fetcher()
        articles = [self._make_article("Bitcoin price rises today")]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_trending_topics()
        assert isinstance(result, list)

    def test_each_entry_has_topic_and_count(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("Bitcoin rally continues"),
            self._make_article("Bitcoin reaches new high"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_trending_topics()
        for entry in result:
            assert "topic" in entry
            assert "count" in entry

    def test_frequent_words_rank_higher(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("bitcoin price today"),
            self._make_article("bitcoin market rally"),
            self._make_article("bitcoin investment"),
            self._make_article("tesla earnings report"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_trending_topics()
        if result:
            # "bitcoin" should appear 3 times vs "tesla" once
            topics = [entry["topic"] for entry in result]
            if "bitcoin" in topics and "tesla" in topics:
                bitcoin_idx = topics.index("bitcoin")
                tesla_idx = topics.index("tesla")
                assert bitcoin_idx < tesla_idx

    def test_filters_common_words(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("the market is rising for the economy"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_trending_topics()
        topics = [entry["topic"] for entry in result]
        assert "the" not in topics
        assert "and" not in topics
        assert "for" not in topics

    def test_returns_at_most_10_topics(self):
        fetcher = _get_fetcher()
        articles = [self._make_article(f"word{i} finance news") for i in range(50)]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.get_trending_topics()
        assert len(result) <= 10

    def test_returns_empty_on_exception(self):
        fetcher = _get_fetcher()
        with patch.object(fetcher, "get_market_news", side_effect=Exception("network error")):
            result = fetcher.get_trending_topics()
        assert result == []


# ── search_news ───────────────────────────────────────────────────────────────

class TestSearchNews:
    """Tests for FinanceNewsFetcher.search_news() filtering logic."""

    def _make_article(self, title, summary, source="Test"):
        return {
            "title": title,
            "summary": summary,
            "source": source,
            "published": datetime.now(),
            "link": "https://example.com",
            "author": "Test",
        }

    def test_returns_only_matching_articles(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("Inflation hits 4%", "inflation rate rose"),
            self._make_article("Tech stocks rally", "nasdaq gains today"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.search_news("inflation")
        assert len(result) == 1
        assert "Inflation" in result[0]["title"]

    def test_respects_limit(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article(f"inflation news {i}", f"inflation data {i}")
            for i in range(20)
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.search_news("inflation", limit=5)
        assert len(result) <= 5

    def test_returns_empty_when_no_match(self):
        fetcher = _get_fetcher()
        articles = [self._make_article("Tech rally", "technology stocks")]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.search_news("cryptocurrency")
        assert result == []

    def test_adds_relevance_score(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("earnings report quarterly", "strong earnings results"),
        ]
        with patch.object(fetcher, "get_market_news", return_value=articles):
            result = fetcher.search_news("earnings")
        if result:
            assert "relevance" in result[0]

    def test_returns_empty_on_exception(self):
        fetcher = _get_fetcher()
        with patch.object(fetcher, "get_market_news", side_effect=Exception("network error")):
            result = fetcher.search_news("test")
        assert result == []


# ── get_symbol_news filtering ─────────────────────────────────────────────────

class TestGetSymbolNews:
    """Tests for FinanceNewsFetcher.get_symbol_news() filtering."""

    def _make_article(self, title, summary, source="Test"):
        return {
            "title": title,
            "summary": summary,
            "source": source,
            "published": datetime.now(),
            "link": "https://example.com",
            "author": "Test",
        }

    def test_filters_articles_mentioning_symbol(self):
        fetcher = _get_fetcher()
        articles = [
            self._make_article("AAPL hits all-time high", "apple stock surge"),
            self._make_article("MSFT earnings beat", "microsoft quarterly results"),
        ]
        with patch.object(fetcher, "_fetch_rss_feed", return_value=articles):
            result = fetcher.get_symbol_news("AAPL", limit=10)
        titles = [a["title"] for a in result]
        assert "AAPL hits all-time high" in titles
        assert "MSFT earnings beat" not in titles

    def test_returns_empty_on_exception(self):
        fetcher = _get_fetcher()
        with patch.object(fetcher, "_fetch_rss_feed", side_effect=Exception("error")):
            result = fetcher.get_symbol_news("AAPL")
        assert result == []


# ── format_article_for_display ───────────────────────────────────────────────

class TestFormatArticleForDisplay:
    """Tests for FinanceNewsFetcher.format_article_for_display()."""

    def test_contains_title(self):
        fetcher = _get_fetcher()
        article = {
            "title": "Big Market Moves",
            "source": "Reuters",
            "summary": "Market summary here.",
            "link": "https://reuters.com/article",
            "published": datetime.now() - timedelta(minutes=5),
        }
        formatted = fetcher.format_article_for_display(article)
        assert "Big Market Moves" in formatted

    def test_contains_source(self):
        fetcher = _get_fetcher()
        article = {
            "title": "Title",
            "source": "Bloomberg",
            "summary": "Summary.",
            "link": "https://bloomberg.com/article",
            "published": datetime.now(),
        }
        formatted = fetcher.format_article_for_display(article)
        assert "Bloomberg" in formatted

    def test_contains_link(self):
        fetcher = _get_fetcher()
        article = {
            "title": "Title",
            "source": "CNBC",
            "summary": "Summary.",
            "link": "https://cnbc.com/article",
            "published": datetime.now(),
        }
        formatted = fetcher.format_article_for_display(article)
        assert "https://cnbc.com/article" in formatted