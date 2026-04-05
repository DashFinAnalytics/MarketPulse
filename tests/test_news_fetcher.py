"""Tests for utils/news_fetcher.py - FinanceNewsFetcher class.

This module was changed in the PR. Tests focus on non-network methods and
methods whose behaviour can be validated by mocking _fetch_rss_feed.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from typing import Dict, List
from unittest.mock import MagicMock, patch

# Ensure streamlit is mocked before importing news_fetcher
# (conftest.py handles this at collection time; this guard is belt-and-suspenders)
if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()

from utils.news_fetcher import FinanceNewsFetcher, NewsSource


# ---------------------------------------------------------------------------
# NewsSource
# ---------------------------------------------------------------------------

class TestNewsSource:
    def test_basic_construction(self):
        src = NewsSource("Test Source", "http://example.com/rss")
        assert src.name == "Test Source"
        assert src.rss_url == "http://example.com/rss"
        assert src.base_url is None

    def test_construction_with_base_url(self):
        src = NewsSource("Example", "http://example.com/rss", "http://example.com")
        assert src.base_url == "http://example.com"


# ---------------------------------------------------------------------------
# FinanceNewsFetcher instantiation
# ---------------------------------------------------------------------------

class TestFinanceNewsFetcherInit:
    def test_default_cache_duration(self):
        fetcher = FinanceNewsFetcher()
        assert fetcher.cache_duration == 300

    def test_news_sources_populated(self):
        fetcher = FinanceNewsFetcher()
        assert len(fetcher.NEWS_SOURCES) > 0
        assert "yahoo_finance" in fetcher.NEWS_SOURCES

    def test_news_sources_are_newsource_instances(self):
        fetcher = FinanceNewsFetcher()
        for source in fetcher.NEWS_SOURCES.values():
            assert isinstance(source, NewsSource)


# ---------------------------------------------------------------------------
# get_available_sources
# ---------------------------------------------------------------------------

class TestGetAvailableSources:
    def test_returns_dict(self):
        fetcher = FinanceNewsFetcher()
        result = fetcher.get_available_sources()
        assert isinstance(result, dict)

    def test_keys_match_news_sources(self):
        fetcher = FinanceNewsFetcher()
        result = fetcher.get_available_sources()
        assert set(result.keys()) == set(fetcher.NEWS_SOURCES.keys())

    def test_values_are_display_names(self):
        fetcher = FinanceNewsFetcher()
        result = fetcher.get_available_sources()
        assert result["yahoo_finance"] == "Yahoo Finance"


# ---------------------------------------------------------------------------
# _time_ago
# ---------------------------------------------------------------------------

class TestTimeAgo:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def test_just_now(self):
        pub = datetime.now() - timedelta(seconds=10)
        assert self.fetcher._time_ago(pub) == "Just now"

    def test_minutes_ago_singular(self):
        pub = datetime.now() - timedelta(minutes=1, seconds=30)
        result = self.fetcher._time_ago(pub)
        assert "1 minute ago" == result

    def test_minutes_ago_plural(self):
        pub = datetime.now() - timedelta(minutes=5)
        result = self.fetcher._time_ago(pub)
        assert "5 minutes ago" == result

    def test_hours_ago_singular(self):
        pub = datetime.now() - timedelta(hours=1, minutes=30)
        result = self.fetcher._time_ago(pub)
        assert "1 hour ago" == result

    def test_hours_ago_plural(self):
        pub = datetime.now() - timedelta(hours=3)
        result = self.fetcher._time_ago(pub)
        assert "3 hours ago" == result

    def test_days_ago_singular(self):
        pub = datetime.now() - timedelta(days=1, hours=1)
        result = self.fetcher._time_ago(pub)
        assert "1 day ago" == result

    def test_days_ago_plural(self):
        pub = datetime.now() - timedelta(days=4)
        result = self.fetcher._time_ago(pub)
        assert "4 days ago" == result

    # Boundary: exactly 61 seconds is "1 minute ago"
    def test_boundary_just_over_one_minute(self):
        pub = datetime.now() - timedelta(seconds=61)
        result = self.fetcher._time_ago(pub)
        assert "minute" in result


# ---------------------------------------------------------------------------
# format_article_for_display
# ---------------------------------------------------------------------------

class TestFormatArticleForDisplay:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def test_returns_string(self, sample_article):
        result = self.fetcher.format_article_for_display(sample_article)
        assert isinstance(result, str)

    def test_contains_title(self, sample_article):
        result = self.fetcher.format_article_for_display(sample_article)
        assert "Markets Rally on Fed Decision" in result

    def test_contains_source(self, sample_article):
        result = self.fetcher.format_article_for_display(sample_article)
        assert "Yahoo Finance" in result

    def test_contains_summary(self, sample_article):
        result = self.fetcher.format_article_for_display(sample_article)
        assert "rallied" in result

    def test_contains_link(self, sample_article):
        result = self.fetcher.format_article_for_display(sample_article)
        assert "https://example.com/article1" in result


# ---------------------------------------------------------------------------
# get_market_news
# ---------------------------------------------------------------------------

class TestGetMarketNews:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def test_returns_list(self, sample_articles):
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=sample_articles):
            result = self.fetcher.get_market_news()
        assert isinstance(result, list)

    def test_respects_limit(self, sample_articles):
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=sample_articles):
            result = self.fetcher.get_market_news(limit=2)
        assert len(result) <= 2

    def test_unknown_source_skipped(self, sample_articles):
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=sample_articles):
            # Should not raise, just skip the unknown source
            result = self.fetcher.get_market_news(sources=["nonexistent_source"])
        assert result == []

    def test_sorted_newest_first(self, sample_articles):
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=sample_articles):
            result = self.fetcher.get_market_news(sources=["yahoo_finance"])
        if len(result) > 1:
            for i in range(len(result) - 1):
                assert result[i]["published"] >= result[i + 1]["published"]

    def test_empty_when_fetch_returns_nothing(self):
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=[]):
            result = self.fetcher.get_market_news()
        assert result == []


# ---------------------------------------------------------------------------
# get_sector_news
# ---------------------------------------------------------------------------

class TestGetSectorNews:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def _articles_with(self, texts: List[str]) -> List[Dict]:
        return [
            {
                "title": t,
                "summary": "",
                "published": datetime.now(),
                "source": "Test",
                "link": "http://example.com",
                "author": "Test",
            }
            for t in texts
        ]

    def test_technology_sector_filters_ai_articles(self):
        articles = self._articles_with([
            "AI startup raises $100M",
            "Oil prices drop sharply",
            "Tech giants invest in artificial intelligence",
        ])
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.get_sector_news("technology")
        titles = [a["title"] for a in result]
        assert any(
            "AI" in t
            or "Tech" in t
            or "artificial intelligence" in t.lower()
            for t in titles
        )

    def test_unknown_sector_uses_sector_name_as_keyword(self):
        articles = self._articles_with([
            "Fintech revolution in banking",
            "Tech merger news",
        ])
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.get_sector_news("fintech")
        assert len(result) >= 1

    def test_respects_limit(self):
        many_articles = self._articles_with([f"Tech news {i}" for i in range(20)])
        with patch.object(self.fetcher, "get_market_news", return_value=many_articles):
            result = self.fetcher.get_sector_news("technology", limit=3)
        assert len(result) <= 3

    def test_returns_empty_when_no_matching_articles(self):
        articles = self._articles_with(["Completely unrelated sports news"])
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.get_sector_news("healthcare")
        assert result == []


# ---------------------------------------------------------------------------
# search_news
# ---------------------------------------------------------------------------

class TestSearchNews:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def _make_articles(self, count: int = 5) -> List[Dict]:
        return [
            {
                "title": f"AAPL report {i}",
                "summary": "Apple announces quarterly results",
                "published": datetime.now() - timedelta(hours=i),
                "source": "Test",
                "link": f"http://example.com/{i}",
                "author": "Test",
            }
            for i in range(count)
        ]

    def test_returns_matching_articles(self):
        articles = self._make_articles()
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.search_news("AAPL")
        assert len(result) > 0

    def test_returns_empty_for_no_match(self):
        articles = self._make_articles()
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.search_news("TSLA_NOMATCHWHATSOEVER")
        assert result == []

    def test_respects_limit(self):
        articles = self._make_articles(10)
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.search_news("AAPL", limit=3)
        assert len(result) <= 3

    def test_relevance_field_added(self):
        articles = self._make_articles()
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.search_news("AAPL")
        assert all("relevance" in a for a in result)

    def test_case_insensitive_search(self):
        articles = [
            {
                "title": "Apple earnings beat expectations",
                "summary": "apple inc reported strong quarterly results",
                "published": datetime.now(),
                "source": "Test",
                "link": "http://example.com/1",
                "author": "Test",
            }
        ]
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.search_news("APPLE")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_trending_topics
# ---------------------------------------------------------------------------

class TestGetTrendingTopics:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def test_returns_list(self):
        articles = [
            {
                "title": "Federal Reserve raises interest rates interest",
                "summary": "rates rates",
                "published": datetime.now(),
                "source": "Test",
                "link": "http://example.com/1",
                "author": "Test",
            }
        ]
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.get_trending_topics()
        assert isinstance(result, list)

    def test_topics_have_required_fields(self):
        articles = [
            {
                "title": "Federal Reserve monetary policy",
                "summary": "",
                "published": datetime.now(),
                "source": "Test",
                "link": "http://example.com/1",
                "author": "Test",
            }
        ]
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.get_trending_topics()
        for item in result:
            assert "topic" in item
            assert "count" in item

    def test_returns_empty_when_no_articles(self):
        with patch.object(self.fetcher, "get_market_news", return_value=[]):
            result = self.fetcher.get_trending_topics()
        assert result == []

    def test_common_words_excluded(self):
        """Words like 'the', 'and', 'or' should not appear as trending topics."""
        articles = [
            {
                "title": "the and or but in on at",
                "summary": "",
                "published": datetime.now(),
                "source": "Test",
                "link": "http://example.com/1",
                "author": "Test",
            }
        ]
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.get_trending_topics()
        common = {"the", "and", "or", "but", "in", "on", "at"}
        topics = {item["topic"] for item in result}
        assert topics.isdisjoint(common)

    def test_limits_to_ten_topics(self):
        # 11 distinct words, each appearing once
        words = [f"topic{i}" for i in range(11)]
        articles = [
            {
                "title": " ".join(words),
                "summary": "",
                "published": datetime.now(),
                "source": "Test",
                "link": "http://example.com/1",
                "author": "Test",
            }
        ]
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.get_trending_topics()
        assert len(result) <= 10