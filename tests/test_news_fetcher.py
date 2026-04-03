"""Tests for utils/news_fetcher.py (changed in this PR).

Covers: NewsSource, FinanceNewsFetcher - focusing on pure/mockable methods:
_time_ago, get_available_sources, format_article_for_display,
get_trending_topics, search_news, get_sector_news, get_symbol_news.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# conftest.py installs streamlit mock, so this import should work
from utils.news_fetcher import FinanceNewsFetcher, NewsSource


def _make_article(
    title: str = "Test headline",
    summary: str = "A summary",
    link: str = "http://example.com/1",
    source: str = "TestSource",
    published: datetime | None = None,
) -> dict:
    return {
        "title": title,
        "summary": summary,
        "link": link,
        "source": source,
        "published": published or datetime.now(),
        "author": "Author",
    }


class TestNewsSource:
    def test_init_stores_fields(self):
        ns = NewsSource("TestName", "http://example.com/rss", "http://example.com")
        assert ns.name == "TestName"
        assert ns.rss_url == "http://example.com/rss"
        assert ns.base_url == "http://example.com"

    def test_base_url_optional(self):
        ns = NewsSource("Name", "http://example.com/rss")
        assert ns.base_url is None


class TestGetAvailableSources:
    def test_returns_dict(self):
        fetcher = FinanceNewsFetcher()
        sources = fetcher.get_available_sources()
        assert isinstance(sources, dict)

    def test_contains_expected_sources(self):
        fetcher = FinanceNewsFetcher()
        sources = fetcher.get_available_sources()
        assert "yahoo_finance" in sources
        assert "reuters_business" in sources
        assert "marketwatch" in sources
        assert "cnbc" in sources
        assert "bloomberg" in sources

    def test_values_are_strings(self):
        fetcher = FinanceNewsFetcher()
        sources = fetcher.get_available_sources()
        for key, name in sources.items():
            assert isinstance(name, str), f"Source {key!r} name should be str"

    def test_yahoo_finance_display_name(self):
        fetcher = FinanceNewsFetcher()
        sources = fetcher.get_available_sources()
        assert sources["yahoo_finance"] == "Yahoo Finance"


class TestTimeAgo:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def test_just_now(self):
        pub = datetime.now() - timedelta(seconds=30)
        assert self.fetcher._time_ago(pub) == "Just now"

    def test_minutes_singular(self):
        pub = datetime.now() - timedelta(seconds=90)
        result = self.fetcher._time_ago(pub)
        assert result == "1 minute ago"

    def test_minutes_plural(self):
        pub = datetime.now() - timedelta(seconds=180)
        result = self.fetcher._time_ago(pub)
        assert result == "3 minutes ago"

    def test_one_hour(self):
        pub = datetime.now() - timedelta(seconds=3700)
        result = self.fetcher._time_ago(pub)
        assert result == "1 hour ago"

    def test_multiple_hours(self):
        pub = datetime.now() - timedelta(seconds=7300)
        result = self.fetcher._time_ago(pub)
        assert result == "2 hours ago"

    def test_one_day(self):
        pub = datetime.now() - timedelta(days=1)
        result = self.fetcher._time_ago(pub)
        assert result == "1 day ago"

    def test_multiple_days(self):
        pub = datetime.now() - timedelta(days=5)
        result = self.fetcher._time_ago(pub)
        assert result == "5 days ago"

    def test_boundary_exactly_61_seconds_is_minutes(self):
        pub = datetime.now() - timedelta(seconds=61)
        result = self.fetcher._time_ago(pub)
        assert "minute" in result


class TestFormatArticleForDisplay:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def test_contains_title(self):
        article = _make_article(title="Big market news")
        result = self.fetcher.format_article_for_display(article)
        assert "Big market news" in result

    def test_contains_source(self):
        article = _make_article(source="Reuters")
        result = self.fetcher.format_article_for_display(article)
        assert "Reuters" in result

    def test_contains_link(self):
        article = _make_article(link="http://example.com/story")
        result = self.fetcher.format_article_for_display(article)
        assert "http://example.com/story" in result

    def test_contains_summary(self):
        article = _make_article(summary="A detailed summary here")
        result = self.fetcher.format_article_for_display(article)
        assert "A detailed summary here" in result

    def test_returns_string(self):
        article = _make_article()
        result = self.fetcher.format_article_for_display(article)
        assert isinstance(result, str)


class TestGetMarketNews:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def test_unknown_source_is_skipped(self):
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=[]):
            # Should not raise; unknown source just warns
            result = self.fetcher.get_market_news(sources=["nonexistent_source"])
        assert result == []

    def test_limit_applied(self):
        sample_articles = [_make_article(title=f"Article {i}") for i in range(10)]
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=sample_articles):
            result = self.fetcher.get_market_news(sources=["yahoo_finance"], limit=3)
        assert len(result) <= 3

    def test_articles_sorted_newest_first(self):
        now = datetime.now()
        articles = [
            _make_article(title="Old", published=now - timedelta(hours=5)),
            _make_article(title="New", published=now - timedelta(hours=1)),
        ]
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=articles):
            result = self.fetcher.get_market_news(sources=["yahoo_finance"], limit=10)
        if len(result) >= 2:
            assert result[0]["published"] >= result[1]["published"]

    def test_default_sources_used_when_none(self):
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=[]) as mock_fetch:
            self.fetcher.get_market_news()
        # Should have been called at least once (for each default source)
        assert mock_fetch.call_count >= 1


class TestGetTrendingTopics:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def _patch_market_news(self, articles):
        return patch.object(self.fetcher, "get_market_news", return_value=articles)

    def test_returns_list(self):
        articles = [_make_article(title="stock market rally today")]
        with self._patch_market_news(articles):
            result = self.fetcher.get_trending_topics()
        assert isinstance(result, list)

    def test_each_item_has_topic_and_count(self):
        articles = [_make_article(title="stock rally markets crash")]
        with self._patch_market_news(articles):
            result = self.fetcher.get_trending_topics()
        for item in result:
            assert "topic" in item
            assert "count" in item

    def test_empty_news_returns_empty(self):
        with self._patch_market_news([]):
            result = self.fetcher.get_trending_topics()
        assert result == []

    def test_common_words_excluded(self):
        articles = [_make_article(title="the and or but in on at")]
        with self._patch_market_news(articles):
            result = self.fetcher.get_trending_topics()
        topics = [item["topic"] for item in result]
        for word in {"the", "and", "or", "but", "in", "on", "at"}:
            assert word not in topics

    def test_short_words_excluded(self):
        articles = [_make_article(title="hi by it is go big rally")]
        with self._patch_market_news(articles):
            result = self.fetcher.get_trending_topics()
        topics = [item["topic"] for item in result]
        # Words with 3 chars or fewer should be excluded
        for topic in topics:
            assert len(topic) > 3

    def test_top_10_limit(self):
        # 15 unique words all length > 3
        words = [f"word{i}abcd" for i in range(15)]
        title = " ".join(words)
        articles = [_make_article(title=title)]
        with self._patch_market_news(articles):
            result = self.fetcher.get_trending_topics()
        assert len(result) <= 10

    def test_count_reflects_frequency(self):
        # "rally" appears 3 times across different articles
        articles = [
            _make_article(title="market rally continues"),
            _make_article(title="stocks rally again"),
            _make_article(title="rally extends gains"),
        ]
        with self._patch_market_news(articles):
            result = self.fetcher.get_trending_topics()
        rally_items = [item for item in result if item["topic"] == "rally"]
        assert len(rally_items) == 1
        assert rally_items[0]["count"] == 3

    def test_error_handling_returns_empty(self):
        with patch.object(self.fetcher, "get_market_news", side_effect=RuntimeError("boom")):
            result = self.fetcher.get_trending_topics()
        assert result == []


class TestSearchNews:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def _articles(self):
        return [
            _make_article(title="Apple stock surges", summary="Apple beats earnings"),
            _make_article(title="Google results announced", summary="Alphabet quarterly results"),
            _make_article(title="Apple Watch new features", summary="New product from Apple"),
        ]

    def test_returns_list(self):
        with patch.object(self.fetcher, "get_market_news", return_value=self._articles()):
            result = self.fetcher.search_news("apple")
        assert isinstance(result, list)

    def test_only_matching_articles_returned(self):
        with patch.object(self.fetcher, "get_market_news", return_value=self._articles()):
            result = self.fetcher.search_news("google")
        assert len(result) == 1
        assert "Google" in result[0]["title"]

    def test_case_insensitive(self):
        with patch.object(self.fetcher, "get_market_news", return_value=self._articles()):
            result_lower = self.fetcher.search_news("apple")
            result_upper = self.fetcher.search_news("APPLE")
        assert len(result_lower) == len(result_upper)

    def test_limit_applied(self):
        with patch.object(self.fetcher, "get_market_news", return_value=self._articles()):
            result = self.fetcher.search_news("apple", limit=1)
        assert len(result) <= 1

    def test_articles_have_relevance_score(self):
        with patch.object(self.fetcher, "get_market_news", return_value=self._articles()):
            result = self.fetcher.search_news("apple")
        for article in result:
            assert "relevance" in article

    def test_title_matches_weigh_more(self):
        articles = [
            _make_article(title="apple apple apple", summary="no match here"),
            _make_article(title="unrelated title", summary="apple in summary"),
        ]
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.search_news("apple")
        # First article has title_matches=3 -> relevance=6, second has summary_matches=1 -> relevance=1
        assert result[0]["title"] == "apple apple apple"

    def test_no_match_returns_empty(self):
        with patch.object(self.fetcher, "get_market_news", return_value=self._articles()):
            result = self.fetcher.search_news("zzznomatch")
        assert result == []

    def test_error_handling_returns_empty(self):
        with patch.object(self.fetcher, "get_market_news", side_effect=RuntimeError("oops")):
            result = self.fetcher.search_news("anything")
        assert result == []


class TestGetSectorNews:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def _tech_articles(self):
        return [
            _make_article(title="AI software startup raises funds", summary="Technology sector"),
            _make_article(title="Oil prices rise", summary="Energy commodity"),
            _make_article(title="New tech chip released", summary="Silicon technology"),
        ]

    def test_filters_by_sector_keywords(self):
        with patch.object(self.fetcher, "get_market_news", return_value=self._tech_articles()):
            result = self.fetcher.get_sector_news("technology")
        titles = [a["title"] for a in result]
        assert any("AI" in t or "tech" in t.lower() for t in titles)

    def test_unknown_sector_uses_sector_name_as_keyword(self):
        articles = [
            _make_article(title="aerospace sector grows", summary="rockets and planes"),
            _make_article(title="unrelated news today", summary="no match"),
        ]
        with patch.object(self.fetcher, "get_market_news", return_value=articles):
            result = self.fetcher.get_sector_news("aerospace")
        assert len(result) == 1

    def test_limit_applied(self):
        many_articles = [
            _make_article(title=f"tech news {i}", summary="software technology") for i in range(20)
        ]
        with patch.object(self.fetcher, "get_market_news", return_value=many_articles):
            result = self.fetcher.get_sector_news("technology", limit=3)
        assert len(result) <= 3

    def test_returns_list(self):
        with patch.object(self.fetcher, "get_market_news", return_value=[]):
            result = self.fetcher.get_sector_news("energy")
        assert isinstance(result, list)


class TestGetSymbolNews:
    def setup_method(self):
        self.fetcher = FinanceNewsFetcher()

    def test_filters_out_non_matching_articles(self):
        articles = [
            _make_article(title="AAPL beats earnings", summary="Apple does well"),
            _make_article(title="TSLA crashes today", summary="Tesla stock down"),
        ]
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=articles):
            result = self.fetcher.get_symbol_news("AAPL")
        assert all("AAPL" in a["title"].upper() or "AAPL" in a["summary"].upper() for a in result)

    def test_limit_applied(self):
        articles = [
            _make_article(title=f"MSFT news {i}", summary="Microsoft update") for i in range(15)
        ]
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=articles):
            result = self.fetcher.get_symbol_news("MSFT", limit=3)
        assert len(result) <= 3

    def test_error_returns_empty(self):
        with patch.object(self.fetcher, "_fetch_rss_feed", side_effect=RuntimeError("fail")):
            result = self.fetcher.get_symbol_news("AAPL")
        assert result == []

    def test_returns_list(self):
        with patch.object(self.fetcher, "_fetch_rss_feed", return_value=[]):
            result = self.fetcher.get_symbol_news("GOOG")
        assert isinstance(result, list)