"""Tests for utils/sec_fetcher.py — SEC EDGAR data fetcher."""

import pytest
from unittest.mock import patch, MagicMock


# ── _build_filing_url ────────────────────────────────────────────────────────

class TestBuildFilingUrl:
    """Tests for _build_filing_url()."""

    def test_empty_string_returns_empty(self):
        from utils.sec_fetcher import _build_filing_url
        assert _build_filing_url("") == ""

    def test_none_like_falsy_returns_empty(self):
        from utils.sec_fetcher import _build_filing_url
        # Per the implementation: if not file_id -> return ''
        assert _build_filing_url("") == ""

    def test_valid_id_returns_url_with_id(self):
        from utils.sec_fetcher import _build_filing_url
        url = _build_filing_url("abc123")
        assert "abc123" in url
        assert url.startswith("https://")

    def test_url_contains_efts_domain(self):
        from utils.sec_fetcher import _build_filing_url
        url = _build_filing_url("someid")
        assert "efts.sec.gov" in url


# ── _get (internal HTTP helper) ──────────────────────────────────────────────

class TestGetHelper:
    """Tests for the internal _get() function."""

    def test_successful_json_response(self):
        from utils.sec_fetcher import _get
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"key": "value"}
        mock_resp.raise_for_status.return_value = None
        with patch("utils.sec_fetcher.requests.get", return_value=mock_resp):
            result = _get("https://example.com/api")
        assert result == {"key": "value"}

    def test_request_exception_returns_none(self):
        from utils.sec_fetcher import _get
        import requests as req_module
        with patch("utils.sec_fetcher.requests.get", side_effect=req_module.exceptions.ConnectionError("down")):
            result = _get("https://example.com/api")
        assert result is None

    def test_http_error_returns_none(self):
        from utils.sec_fetcher import _get
        import requests as req_module
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_module.exceptions.HTTPError("404")
        with patch("utils.sec_fetcher.requests.get", return_value=mock_resp):
            result = _get("https://example.com/api")
        assert result is None


# ── search_filings ───────────────────────────────────────────────────────────

class TestSearchFilings:
    """Tests for search_filings()."""

    def _mock_get_response(self, hits=None):
        if hits is None:
            hits = []
        return {
            "hits": {
                "hits": hits
            }
        }

    def test_returns_empty_list_when_no_data(self):
        from utils.sec_fetcher import search_filings
        with patch("utils.sec_fetcher._get", return_value=None):
            result = search_filings("Apple")
        assert result == []

    def test_returns_empty_list_when_no_hits(self):
        from utils.sec_fetcher import search_filings
        with patch("utils.sec_fetcher._get", return_value=self._mock_get_response([])):
            result = search_filings("Apple")
        assert result == []

    def test_parses_hits_correctly(self):
        from utils.sec_fetcher import search_filings
        hits = [
            {
                "_id": "abc",
                "_source": {
                    "entity_name": "Apple Inc.",
                    "form_type": "10-K",
                    "file_date": "2024-01-01",
                    "period_of_report": "2023-12-31",
                    "file_num": "0001-12345",
                }
            }
        ]
        with patch("utils.sec_fetcher._get", return_value=self._mock_get_response(hits)):
            result = search_filings("Apple")
        assert len(result) == 1
        assert result[0]["company"] == "Apple Inc."
        assert result[0]["form_type"] == "10-K"
        assert result[0]["filed_date"] == "2024-01-01"

    def test_result_has_required_keys(self):
        from utils.sec_fetcher import search_filings
        hits = [
            {
                "_id": "xyz",
                "_source": {
                    "entity_name": "Test Corp",
                    "form_type": "8-K",
                    "file_date": "2024-06-01",
                    "period_of_report": "2024-05-31",
                    "file_num": "0002-54321",
                }
            }
        ]
        with patch("utils.sec_fetcher._get", return_value=self._mock_get_response(hits)):
            result = search_filings("Test")
        for key in ("company", "form_type", "filed_date", "period", "file_num", "url"):
            assert key in result[0], f"Missing key: {key}"

    def test_default_form_types_are_10k_10q_8k(self):
        from utils.sec_fetcher import search_filings
        with patch("utils.sec_fetcher._get", return_value=None) as mock_get:
            search_filings("test_query")
        # Check that the params passed include default forms
        call_params = mock_get.call_args[1]["params"]
        assert "10-K" in call_params["forms"]
        assert "10-Q" in call_params["forms"]
        assert "8-K" in call_params["forms"]

    def test_custom_form_types(self):
        from utils.sec_fetcher import search_filings
        with patch("utils.sec_fetcher._get", return_value=None) as mock_get:
            search_filings("test", form_types=["S-1"])
        call_params = mock_get.call_args[1]["params"]
        assert "S-1" in call_params["forms"]

    def test_missing_source_fields_use_na_fallback(self):
        from utils.sec_fetcher import search_filings
        hits = [{"_id": "abc", "_source": {}}]
        with patch("utils.sec_fetcher._get", return_value=self._mock_get_response(hits)):
            result = search_filings("test")
        assert result[0]["company"] == "N/A"
        assert result[0]["form_type"] == "N/A"


# ── get_company_filings ──────────────────────────────────────────────────────

class TestGetCompanyFilings:
    """Tests for get_company_filings()."""

    def _make_mapping(self, ticker="AAPL", cik=12345, title="Apple Inc."):
        return {
            "0": {"ticker": ticker, "cik_str": cik, "title": title}
        }

    def _make_submissions(self, forms, dates, accnums, docs, desc):
        return {
            "filings": {
                "recent": {
                    "form": forms,
                    "filingDate": dates,
                    "accessionNumber": accnums,
                    "primaryDocument": docs,
                    "primaryDocDescription": desc,
                }
            }
        }

    def test_returns_empty_when_ticker_not_in_mapping(self):
        from utils.sec_fetcher import get_company_filings
        mapping = {"0": {"ticker": "MSFT", "cik_str": 789, "title": "Microsoft"}}
        with patch("utils.sec_fetcher._get", return_value=mapping):
            result = get_company_filings("AAPL")
        assert result == []

    def test_returns_empty_when_mapping_returns_none(self):
        from utils.sec_fetcher import get_company_filings
        with patch("utils.sec_fetcher._get", return_value=None):
            result = get_company_filings("AAPL")
        assert result == []

    def test_parses_filings_correctly(self):
        from utils.sec_fetcher import get_company_filings

        mapping = self._make_mapping()
        submissions = self._make_submissions(
            forms=["10-K", "8-K"],
            dates=["2024-01-01", "2024-06-01"],
            accnums=["0001234567-24-000001", "0001234567-24-000002"],
            docs=["aapl-20231231.htm", "aapl-20240601.htm"],
            desc=["Annual Report", "Current Report"],
        )

        def side_effect(url, *args, **kwargs):
            if "company_tickers" in url:
                return mapping
            return submissions

        with patch("utils.sec_fetcher._get", side_effect=side_effect):
            result = get_company_filings("AAPL")

        # Should find 10-K and 8-K (default form_types includes both)
        assert len(result) == 2
        form_types = {r["form_type"] for r in result}
        assert "10-K" in form_types
        assert "8-K" in form_types

    def test_result_has_required_keys(self):
        from utils.sec_fetcher import get_company_filings

        mapping = self._make_mapping()
        submissions = self._make_submissions(
            forms=["10-K"],
            dates=["2024-01-01"],
            accnums=["0001234567-24-000001"],
            docs=["doc.htm"],
            desc=["Annual Report"],
        )

        def side_effect(url, *args, **kwargs):
            if "company_tickers" in url:
                return mapping
            return submissions

        with patch("utils.sec_fetcher._get", side_effect=side_effect):
            result = get_company_filings("AAPL")

        if result:
            for key in ("company", "ticker", "form_type", "filed_date", "description", "url"):
                assert key in result[0]

    def test_respects_limit_parameter(self):
        from utils.sec_fetcher import get_company_filings

        mapping = self._make_mapping()
        # Create many 10-K entries
        n = 20
        submissions = self._make_submissions(
            forms=["10-K"] * n,
            dates=["2024-01-01"] * n,
            accnums=[f"000123456{i:02d}-24-00000{i}" for i in range(n)],
            docs=[f"doc{i}.htm" for i in range(n)],
            desc=["Annual Report"] * n,
        )

        def side_effect(url, *args, **kwargs):
            if "company_tickers" in url:
                return mapping
            return submissions

        with patch("utils.sec_fetcher._get", side_effect=side_effect):
            result = get_company_filings("AAPL", limit=5)

        assert len(result) <= 5


# ── get_insider_transactions ─────────────────────────────────────────────────

class TestGetInsiderTransactions:
    """Tests for get_insider_transactions()."""

    def test_returns_empty_when_ticker_not_found(self):
        from utils.sec_fetcher import get_insider_transactions
        mapping = {"0": {"ticker": "MSFT", "cik_str": 789, "title": "Microsoft"}}
        with patch("utils.sec_fetcher._get", return_value=mapping):
            result = get_insider_transactions("AAPL")
        assert result == []

    def test_returns_empty_when_no_form4_filings(self):
        from utils.sec_fetcher import get_insider_transactions

        mapping = {"0": {"ticker": "AAPL", "cik_str": 12345, "title": "Apple Inc."}}
        submissions = {
            "filings": {
                "recent": {
                    "form": ["10-K", "8-K"],
                    "filingDate": ["2024-01-01", "2024-06-01"],
                    "accessionNumber": ["0001-1", "0001-2"],
                }
            }
        }

        def side_effect(url, *args, **kwargs):
            if "company_tickers" in url:
                return mapping
            return submissions

        with patch("utils.sec_fetcher._get", side_effect=side_effect):
            result = get_insider_transactions("AAPL")
        assert result == []

    def test_parses_form4_filings(self):
        from utils.sec_fetcher import get_insider_transactions

        mapping = {"0": {"ticker": "AAPL", "cik_str": 12345, "title": "Apple Inc."}}
        submissions = {
            "filings": {
                "recent": {
                    "form": ["4", "10-K", "4"],
                    "filingDate": ["2024-03-01", "2024-01-01", "2024-06-01"],
                    "accessionNumber": ["0001234567-24-000010", "0001234567-24-000001", "0001234567-24-000020"],
                }
            }
        }

        def side_effect(url, *args, **kwargs):
            if "company_tickers" in url:
                return mapping
            return submissions

        with patch("utils.sec_fetcher._get", side_effect=side_effect):
            result = get_insider_transactions("AAPL")

        assert len(result) == 2
        for entry in result:
            assert entry["form_type"] == "4"
            assert entry["ticker"] == "AAPL"

    def test_result_has_required_keys(self):
        from utils.sec_fetcher import get_insider_transactions

        mapping = {"0": {"ticker": "AAPL", "cik_str": 12345, "title": "Apple Inc."}}
        submissions = {
            "filings": {
                "recent": {
                    "form": ["4"],
                    "filingDate": ["2024-03-01"],
                    "accessionNumber": ["0001234567-24-000010"],
                }
            }
        }

        def side_effect(url, *args, **kwargs):
            if "company_tickers" in url:
                return mapping
            return submissions

        with patch("utils.sec_fetcher._get", side_effect=side_effect):
            result = get_insider_transactions("AAPL")

        if result:
            for key in ("ticker", "form_type", "filed_date", "accession", "edgar_url"):
                assert key in result[0]

    def test_respects_limit_parameter(self):
        from utils.sec_fetcher import get_insider_transactions

        mapping = {"0": {"ticker": "AAPL", "cik_str": 12345, "title": "Apple Inc."}}
        n = 20
        submissions = {
            "filings": {
                "recent": {
                    "form": ["4"] * n,
                    "filingDate": ["2024-03-01"] * n,
                    "accessionNumber": [f"0001234567-24-{i:06d}" for i in range(n)],
                }
            }
        }

        def side_effect(url, *args, **kwargs):
            if "company_tickers" in url:
                return mapping
            return submissions

        with patch("utils.sec_fetcher._get", side_effect=side_effect):
            result = get_insider_transactions("AAPL", limit=3)

        assert len(result) <= 3

    def test_ticker_uppercased_in_result(self):
        from utils.sec_fetcher import get_insider_transactions

        mapping = {"0": {"ticker": "aapl", "cik_str": 12345, "title": "Apple Inc."}}
        submissions = {
            "filings": {
                "recent": {
                    "form": ["4"],
                    "filingDate": ["2024-03-01"],
                    "accessionNumber": ["0001234567-24-000010"],
                }
            }
        }

        def side_effect(url, *args, **kwargs):
            if "company_tickers" in url:
                return mapping
            return submissions

        with patch("utils.sec_fetcher._get", side_effect=side_effect):
            result = get_insider_transactions("aapl")

        if result:
            assert result[0]["ticker"] == "AAPL"