"""Tests for utils/data_fetcher.py – covers only code changed/added in this PR.

The streamlit stub is installed in conftest.py before this module is imported,
so @st.cache_data becomes a no-op passthrough decorator in tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_price_df(closes, volumes=None):
    """Build a minimal DataFrame that looks like yfinance history output."""
    if volumes is None:
        volumes = [0] * len(closes)
    return pd.DataFrame({"Close": closes, "Volume": volumes})


# ---------------------------------------------------------------------------
# DataFetcher._validate_symbol
# ---------------------------------------------------------------------------

class TestValidateSymbol:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_uppercase_normalization(self):
        assert self.fetcher._validate_symbol("aapl") == "AAPL"

    def test_strips_whitespace(self):
        assert self.fetcher._validate_symbol("  msft  ") == "MSFT"

    def test_caret_prefix_accepted(self):
        # ^VIX is a valid yfinance ticker
        assert self.fetcher._validate_symbol("^vix") == "^VIX"

    def test_equals_suffix_accepted(self):
        # EURUSD=X style forex pairs
        assert self.fetcher._validate_symbol("eurusd=x") == "EURUSD=X"

    def test_dot_in_symbol_accepted(self):
        # e.g. BRK.B
        assert self.fetcher._validate_symbol("brk.b") == "BRK.B"

    def test_dash_in_symbol_accepted(self):
        assert self.fetcher._validate_symbol("BF-B") == "BF-B"

    def test_empty_string_raises(self):
        from utils.exceptions import ValidationError
        with pytest.raises(ValidationError):
            self.fetcher._validate_symbol("")

    def test_none_raises(self):
        from utils.exceptions import ValidationError
        with pytest.raises(ValidationError):
            self.fetcher._validate_symbol(None)

    def test_non_string_raises(self):
        from utils.exceptions import ValidationError
        with pytest.raises(ValidationError):
            self.fetcher._validate_symbol(123)

    def test_invalid_chars_raises(self):
        from utils.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Invalid symbol format"):
            self.fetcher._validate_symbol("A@B!")

    def test_slash_accepted(self):
        # e.g. BTC/USD
        result = self.fetcher._validate_symbol("btc/usd")
        assert result == "BTC/USD"


# ---------------------------------------------------------------------------
# DataFetcher._sleep_before_retry
# ---------------------------------------------------------------------------

class TestSleepBeforeRetry:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_sleeps_for_expected_time(self):
        with patch("utils.data_fetcher.time.sleep") as mock_sleep:
            self.fetcher._sleep_before_retry(0)
        mock_sleep.assert_called_once_with(1)  # min(2^0, 4) = 1

    def test_caps_at_four_seconds(self):
        with patch("utils.data_fetcher.time.sleep") as mock_sleep:
            self.fetcher._sleep_before_retry(5)
        mock_sleep.assert_called_once_with(4)  # min(2^5, 4) = 4

    def test_attempt_two(self):
        with patch("utils.data_fetcher.time.sleep") as mock_sleep:
            self.fetcher._sleep_before_retry(2)
        mock_sleep.assert_called_once_with(4)  # min(2^2, 4) = 4


# ---------------------------------------------------------------------------
# DataFetcher._store_data_if_possible
# ---------------------------------------------------------------------------

class TestStoreDataIfPossible:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_calls_db_manager_when_data_present(self):
        data = {"price": 100.0, "change": 1.0, "change_pct": 1.0}
        with patch("utils.data_fetcher.db_manager") as mock_db:
            self.fetcher._store_data_if_possible("AAPL", data, "index")
        mock_db.store_financial_data.assert_called_once_with("AAPL", data, "index")

    def test_skips_when_data_is_none(self):
        with patch("utils.data_fetcher.db_manager") as mock_db:
            self.fetcher._store_data_if_possible("AAPL", None, "index")
        mock_db.store_financial_data.assert_not_called()

    def test_skips_when_data_is_empty_dict(self):
        with patch("utils.data_fetcher.db_manager") as mock_db:
            self.fetcher._store_data_if_possible("AAPL", {}, "index")
        mock_db.store_financial_data.assert_not_called()

    def test_suppresses_db_exception(self):
        data = {"price": 1.0, "change": 0.0, "change_pct": 0.0}
        with patch("utils.data_fetcher.db_manager") as mock_db:
            mock_db.store_financial_data.side_effect = RuntimeError("db error")
            # Should not raise
            self.fetcher._store_data_if_possible("AAPL", data, "index")


# ---------------------------------------------------------------------------
# DataFetcher._download_history
# ---------------------------------------------------------------------------

class TestDownloadHistory:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        obj = DataFetcher()
        obj.retry_attempts = 1
        self.fetcher = obj

    def test_returns_dataframe_on_success(self):
        df = _make_price_df([150.0, 152.0])
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher._download_history("AAPL", "5d")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_returns_empty_dataframe_on_exception(self):
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = RuntimeError("network error")
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher._download_history("AAPL", "5d")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_validates_symbol_before_fetch(self):
        from utils.exceptions import ValidationError
        with pytest.raises(ValidationError):
            self.fetcher._download_history("", "5d")

    def test_retries_on_failure(self):
        fetcher = self._make_fetcher_with_retries(3)
        mock_ticker = MagicMock()
        call_count = 0

        def side_effect(period):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("temporary error")
            return _make_price_df([100.0])

        mock_ticker.history.side_effect = side_effect
        with patch("yfinance.Ticker", return_value=mock_ticker), \
             patch.object(fetcher, "_sleep_before_retry"):
            result = fetcher._download_history("AAPL", "5d")
        assert not result.empty
        assert call_count == 3

    def _make_fetcher_with_retries(self, n):
        from utils.data_fetcher import DataFetcher
        obj = DataFetcher()
        obj.retry_attempts = n
        return obj


# ---------------------------------------------------------------------------
# DataFetcher._fetch_ticker_data
# ---------------------------------------------------------------------------

class TestFetchTickerData:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        obj = DataFetcher()
        obj.retry_attempts = 1
        self.fetcher = obj

    def test_returns_data_dict_on_success(self):
        df = _make_price_df([100.0, 105.0], volumes=[1000, 2000])
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        mock_ticker.info = {"sector": "Technology"}
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher._fetch_ticker_data("AAPL")
        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["price"] == pytest.approx(105.0)
        assert result["change"] == pytest.approx(5.0)
        assert result["change_pct"] == pytest.approx(5.0)
        assert result["volume"] == pytest.approx(2000.0)

    def test_returns_none_for_empty_history(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher._fetch_ticker_data("AAPL")
        assert result is None

    def test_returns_none_for_invalid_symbol(self):
        result = self.fetcher._fetch_ticker_data("@INVALID!")
        assert result is None

    def test_change_pct_zero_when_prev_close_zero(self):
        """If previous close is 0 the change_pct should be 0 (no division)."""
        df = _make_price_df([0.0, 5.0])
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        mock_ticker.info = {}
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher._fetch_ticker_data("ZZZ")
        assert result["change_pct"] == pytest.approx(0.0)

    def test_single_row_history_no_previous(self):
        """When only one row is available, change should be 0."""
        df = _make_price_df([200.0])
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        mock_ticker.info = {}
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher._fetch_ticker_data("SPY")
        assert result["change"] == pytest.approx(0.0)
        assert result["change_pct"] == pytest.approx(0.0)

    def test_info_exception_falls_back_to_empty_dict(self):
        df = _make_price_df([100.0, 102.0])
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        type(mock_ticker).info = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("no info"))
        )
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher._fetch_ticker_data("SPY")
        assert result is not None
        assert result["info"] == {}

    def test_volume_zero_when_column_missing(self):
        df = pd.DataFrame({"Close": [100.0, 105.0]})
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        mock_ticker.info = {}
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher._fetch_ticker_data("NVDA")
        assert result["volume"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# DataFetcher._collect_asset_data
# ---------------------------------------------------------------------------

class TestCollectAssetData:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def _mock_fetch(self, data_map):
        """Return a side-effect function that returns data based on symbol."""
        def _side_effect(symbol):
            return data_map.get(symbol)
        return _side_effect

    def test_collects_multiple_symbols(self):
        data = {
            "AAPL": {"symbol": "AAPL", "price": 150.0, "change": 1.0, "change_pct": 0.67},
            "GOOG": {"symbol": "GOOG", "price": 2800.0, "change": 10.0, "change_pct": 0.36},
        }
        with patch.object(self.fetcher, "_fetch_ticker_data",
                          side_effect=self._mock_fetch(data)):
            result = self.fetcher._collect_asset_data(["AAPL", "GOOG"])
        assert "AAPL" in result
        assert "GOOG" in result

    def test_skips_symbols_with_no_data(self):
        with patch.object(self.fetcher, "_fetch_ticker_data", return_value=None):
            result = self.fetcher._collect_asset_data(["AAPL", "GOOG"])
        assert result == {}

    def test_skips_invalid_symbols(self):
        with patch.object(self.fetcher, "_fetch_ticker_data",
                          return_value={"symbol": "AAPL", "price": 100.0}):
            result = self.fetcher._collect_asset_data(["AAPL", "@INVALID!"])
        assert "AAPL" in result
        assert "@INVALID!" not in result

    def test_stores_data_when_data_type_provided(self):
        data = {"AAPL": {"symbol": "AAPL", "price": 150.0, "change": 1.0, "change_pct": 0.67}}
        with patch.object(self.fetcher, "_fetch_ticker_data",
                          side_effect=self._mock_fetch(data)), \
             patch.object(self.fetcher, "_store_data_if_possible") as mock_store:
            self.fetcher._collect_asset_data(["AAPL"], data_type="index")
        mock_store.assert_called_once_with("AAPL", data["AAPL"], "index")

    def test_does_not_store_when_no_data_type(self):
        data = {"AAPL": {"symbol": "AAPL", "price": 150.0}}
        with patch.object(self.fetcher, "_fetch_ticker_data",
                          side_effect=self._mock_fetch(data)), \
             patch.object(self.fetcher, "_store_data_if_possible") as mock_store:
            self.fetcher._collect_asset_data(["AAPL"])
        mock_store.assert_not_called()


# ---------------------------------------------------------------------------
# DataFetcher.get_indices_data / get_commodities_data / get_sector_etfs
# ---------------------------------------------------------------------------

class TestCollectDataWrappers:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def _data_for(self, *symbols):
        return {s: {"symbol": s, "price": 100.0, "change": 1.0, "change_pct": 1.0}
                for s in symbols}

    def test_get_indices_data(self):
        with patch.object(self.fetcher, "_collect_asset_data",
                          return_value=self._data_for("SPY")) as mock:
            result = self.fetcher.get_indices_data(["SPY"])
        mock.assert_called_once_with(["SPY"], "index")

    def test_get_commodities_data(self):
        with patch.object(self.fetcher, "_collect_asset_data",
                          return_value=self._data_for("GLD")) as mock:
            result = self.fetcher.get_commodities_data(["GLD"])
        mock.assert_called_once_with(["GLD"], "commodity")

    def test_get_sector_etfs(self):
        with patch.object(self.fetcher, "_collect_asset_data",
                          return_value=self._data_for("XLK")) as mock:
            result = self.fetcher.get_sector_etfs(["XLK"])
        mock.assert_called_once_with(["XLK"], "sector")


# ---------------------------------------------------------------------------
# DataFetcher.get_bond_data
# ---------------------------------------------------------------------------

class TestGetBondData:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_returns_bond_data_dict(self):
        df = _make_price_df([4.1, 4.2])
        with patch.object(self.fetcher, "_download_history", return_value=df):
            result = self.fetcher.get_bond_data("^TNX")
        assert result is not None
        assert result["symbol"] == "^TNX"
        assert result["price"] == pytest.approx(4.2)
        assert result["change"] == pytest.approx(0.1)

    def test_returns_none_for_empty_history(self):
        with patch.object(self.fetcher, "_download_history",
                          return_value=pd.DataFrame()):
            result = self.fetcher.get_bond_data("^TNX")
        assert result is None

    def test_returns_none_for_invalid_symbol(self):
        result = self.fetcher.get_bond_data("@BAD!")
        assert result is None

    def test_change_zero_when_single_row(self):
        df = _make_price_df([4.5])
        with patch.object(self.fetcher, "_download_history", return_value=df):
            result = self.fetcher.get_bond_data("^TNX")
        assert result["change"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# DataFetcher.get_bond_yields
# ---------------------------------------------------------------------------

class TestGetBondYields:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_returns_yields_for_available_symbols(self):
        df = _make_price_df([4.0, 4.1])
        with patch.object(self.fetcher, "_download_history", return_value=df):
            result = self.fetcher.get_bond_yields()
        # All four maturities should have data
        assert "3M" in result
        assert "10Y" in result
        assert result["10Y"]["yield"] == pytest.approx(4.1)
        assert result["10Y"]["symbol"] == "^TNX"

    def test_skips_maturity_with_empty_history(self):
        df_good = _make_price_df([4.0, 4.1])
        df_empty = pd.DataFrame()

        call_count = [0]
        def side_effect(symbol, period):
            call_count[0] += 1
            if symbol == "^IRX":
                return df_empty
            return df_good

        with patch.object(self.fetcher, "_download_history", side_effect=side_effect):
            result = self.fetcher.get_bond_yields()
        assert "3M" not in result
        assert "10Y" in result

    def test_change_calculated_correctly(self):
        df = _make_price_df([3.8, 4.0])
        with patch.object(self.fetcher, "_download_history", return_value=df):
            result = self.fetcher.get_bond_yields()
        assert result["10Y"]["change"] == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# DataFetcher.get_vix_data
# ---------------------------------------------------------------------------

class TestGetVixData:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_returns_vix_data(self):
        expected = {"symbol": "^VIX", "price": 18.5, "change": -0.3, "change_pct": -1.6}
        with patch.object(self.fetcher, "_fetch_ticker_data", return_value=expected) as mock_f, \
             patch.object(self.fetcher, "_store_data_if_possible") as mock_s:
            result = self.fetcher.get_vix_data()
        mock_f.assert_called_once_with("^VIX")
        mock_s.assert_called_once_with("^VIX", expected, "vix")
        assert result == expected

    def test_returns_none_when_fetch_fails(self):
        with patch.object(self.fetcher, "_fetch_ticker_data", return_value=None), \
             patch.object(self.fetcher, "_store_data_if_possible") as mock_s:
            result = self.fetcher.get_vix_data()
        assert result is None
        mock_s.assert_called_once_with("^VIX", None, "vix")


# ---------------------------------------------------------------------------
# DataFetcher.get_market_summary
# ---------------------------------------------------------------------------

class TestGetMarketSummary:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_returns_dict_with_known_symbols(self):
        data = {"price": 4000.0, "change_pct": 0.5, "symbol": "^GSPC"}
        with patch.object(self.fetcher, "_fetch_ticker_data", return_value=data):
            result = self.fetcher.get_market_summary()
        # All 6 key symbols should be present
        assert "^GSPC" in result
        assert "^VIX" in result
        assert result["^GSPC"]["price"] == 4000.0
        assert result["^GSPC"]["change_pct"] == 0.5

    def test_omits_symbols_without_data(self):
        def side_effect(symbol):
            if symbol == "^VIX":
                return None
            return {"price": 100.0, "change_pct": 0.1}
        with patch.object(self.fetcher, "_fetch_ticker_data", side_effect=side_effect):
            result = self.fetcher.get_market_summary()
        assert "^VIX" not in result

    def test_returns_empty_dict_when_all_fail(self):
        with patch.object(self.fetcher, "_fetch_ticker_data", return_value=None):
            result = self.fetcher.get_market_summary()
        assert result == {}


# ---------------------------------------------------------------------------
# DataFetcher.get_top_movers
# ---------------------------------------------------------------------------

class TestGetTopMovers:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def _make_data(self, symbol, change_pct):
        return {"symbol": symbol, "price": 100.0, "change_pct": change_pct}

    def test_returns_sorted_by_abs_change(self):
        data_map = {
            "A": self._make_data("A", 1.0),
            "B": self._make_data("B", -5.0),
            "C": self._make_data("C", 3.0),
        }
        with patch.object(self.fetcher, "_fetch_ticker_data",
                          side_effect=lambda s: data_map.get(s)):
            result = self.fetcher.get_top_movers(["A", "B", "C"], limit=3)
        assert result[0]["symbol"] == "B"  # biggest abs change_pct
        assert result[1]["symbol"] == "C"
        assert result[2]["symbol"] == "A"

    def test_respects_limit(self):
        data_map = {f"S{i}": self._make_data(f"S{i}", float(i)) for i in range(10)}
        with patch.object(self.fetcher, "_fetch_ticker_data",
                          side_effect=lambda s: data_map.get(s)):
            result = self.fetcher.get_top_movers(list(data_map.keys()), limit=3)
        assert len(result) == 3

    def test_skips_missing_data(self):
        def side_effect(symbol):
            return None if symbol == "MISSING" else self._make_data(symbol, 2.0)
        with patch.object(self.fetcher, "_fetch_ticker_data", side_effect=side_effect):
            result = self.fetcher.get_top_movers(["AAPL", "MISSING"])
        symbols = [r["symbol"] for r in result]
        assert "MISSING" not in symbols

    def test_empty_list_returns_empty(self):
        result = self.fetcher.get_top_movers([])
        assert result == []


# ---------------------------------------------------------------------------
# DataFetcher.get_forex_data / get_futures_data
# ---------------------------------------------------------------------------

class TestForexAndFutures:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_get_forex_data_with_explicit_pairs(self):
        pairs = ["EURUSD=X", "GBPUSD=X"]
        with patch.object(self.fetcher, "_collect_asset_data",
                          return_value={}) as mock:
            self.fetcher.get_forex_data(pairs=pairs)
        mock.assert_called_once_with(pairs)

    def test_get_forex_data_uses_default_pairs(self):
        with patch.object(self.fetcher, "_collect_asset_data",
                          return_value={}) as mock:
            self.fetcher.get_forex_data()
        args = mock.call_args[0][0]
        assert "EURUSD=X" in args
        assert "GBPUSD=X" in args

    def test_get_futures_data_with_explicit_contracts(self):
        contracts = ["ES=F", "NQ=F"]
        with patch.object(self.fetcher, "_collect_asset_data",
                          return_value={}) as mock:
            self.fetcher.get_futures_data(contracts=contracts)
        mock.assert_called_once_with(contracts)

    def test_get_futures_data_uses_default_contracts(self):
        with patch.object(self.fetcher, "_collect_asset_data",
                          return_value={}) as mock:
            self.fetcher.get_futures_data()
        args = mock.call_args[0][0]
        assert "ES=F" in args
        assert "GC=F" in args


# ---------------------------------------------------------------------------
# DataFetcher.get_options_summary
# ---------------------------------------------------------------------------

class TestGetOptionsSummary:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        obj = DataFetcher()
        obj.retry_attempts = 1
        self.fetcher = obj

    def _make_chain_df(self, oi_calls=100, vol_calls=50, oi_puts=80, vol_puts=40):
        calls = pd.DataFrame({
            "openInterest": [oi_calls], "volume": [vol_calls],
            "strike": [100.0], "impliedVolatility": [0.25],
        })
        puts = pd.DataFrame({
            "openInterest": [oi_puts], "volume": [vol_puts],
            "strike": [100.0], "impliedVolatility": [0.30],
        })
        return MagicMock(calls=calls, puts=puts)

    def test_returns_none_for_invalid_symbol(self):
        result = self.fetcher.get_options_summary("@BAD!")
        assert result is None

    def test_returns_none_when_no_expirations(self):
        mock_ticker = MagicMock()
        mock_ticker.options = []
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_options_summary("AAPL")
        assert result is None

    def test_returns_summary_dict(self):
        # Use a single expiration so OI values are not doubled
        chain = self._make_chain_df()
        mock_ticker = MagicMock()
        mock_ticker.options = ["2024-01-19"]
        mock_ticker.option_chain.return_value = chain
        mock_ticker.info = {"currentPrice": 100.0}
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_options_summary("AAPL")
        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["total_call_oi"] == 100
        assert result["total_put_oi"] == 80
        assert result["pc_ratio_oi"] == pytest.approx(0.8)

    def test_pc_ratio_none_when_no_call_oi(self):
        calls = pd.DataFrame({"openInterest": [0], "volume": [0],
                               "strike": [100.0], "impliedVolatility": [0.2]})
        puts = pd.DataFrame({"openInterest": [50], "volume": [30],
                              "strike": [100.0], "impliedVolatility": [0.25]})
        chain = MagicMock(calls=calls, puts=puts)
        mock_ticker = MagicMock()
        mock_ticker.options = ["2024-01-19"]
        mock_ticker.option_chain.return_value = chain
        mock_ticker.info = {}
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_options_summary("AAPL")
        assert result["pc_ratio_oi"] is None

    def test_returns_none_after_retries_exhausted(self):
        fetcher = self.fetcher
        fetcher.retry_attempts = 2
        mock_ticker = MagicMock()
        mock_ticker.options = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("network fail"))
        )
        with patch("yfinance.Ticker", return_value=mock_ticker), \
             patch.object(fetcher, "_sleep_before_retry"):
            result = fetcher.get_options_summary("AAPL")
        assert result is None


# ---------------------------------------------------------------------------
# DataFetcher.get_option_chain
# ---------------------------------------------------------------------------

class TestGetOptionChain:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        obj = DataFetcher()
        obj.retry_attempts = 1
        self.fetcher = obj

    def test_returns_none_for_invalid_symbol(self):
        result = self.fetcher.get_option_chain("@BAD!")
        assert result is None

    def test_returns_none_when_no_expirations(self):
        mock_ticker = MagicMock()
        mock_ticker.options = []
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_option_chain("AAPL")
        assert result is None

    def test_uses_first_expiration_when_none_specified(self):
        calls_df = pd.DataFrame({"strike": [100.0]})
        puts_df = pd.DataFrame({"strike": [100.0]})
        chain = MagicMock(calls=calls_df, puts=puts_df)
        mock_ticker = MagicMock()
        mock_ticker.options = ["2024-01-19", "2024-02-16"]
        mock_ticker.option_chain.return_value = chain
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_option_chain("AAPL")
        assert result is not None
        assert result["expiration"] == "2024-01-19"

    def test_uses_specified_expiration(self):
        calls_df = pd.DataFrame({"strike": [105.0]})
        puts_df = pd.DataFrame({"strike": [95.0]})
        chain = MagicMock(calls=calls_df, puts=puts_df)
        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = chain
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_option_chain("AAPL", expiration="2024-02-16")
        assert result["expiration"] == "2024-02-16"


# ---------------------------------------------------------------------------
# DataFetcher.get_historical_data
# ---------------------------------------------------------------------------

class TestGetHistoricalData:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_returns_dataframe_on_success(self):
        df = _make_price_df([100.0, 101.0, 102.0])
        with patch.object(self.fetcher, "_download_history", return_value=df):
            result = self.fetcher.get_historical_data("AAPL", "1mo")
        assert result is not None
        assert len(result) == 3

    def test_returns_none_for_empty_history(self):
        with patch.object(self.fetcher, "_download_history",
                          return_value=pd.DataFrame()):
            result = self.fetcher.get_historical_data("AAPL", "1mo")
        assert result is None

    def test_default_period_is_1mo(self):
        df = _make_price_df([100.0])
        with patch.object(self.fetcher, "_download_history",
                          return_value=df) as mock_dl:
            self.fetcher.get_historical_data("AAPL")
        mock_dl.assert_called_once_with("AAPL", "1mo")


# ---------------------------------------------------------------------------
# DataFetcher.get_risk_metrics
# ---------------------------------------------------------------------------

class TestGetRiskMetrics:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def _make_price_series(self, n=252, seed=42):
        rng = np.random.default_rng(seed)
        prices = 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, n))
        return pd.DataFrame({"Close": prices})

    def test_returns_none_for_insufficient_data(self):
        short_df = pd.DataFrame({"Close": [100.0, 101.0]})
        with patch("yfinance.download", return_value=short_df):
            result = self.fetcher.get_risk_metrics("AAPL")
        assert result is None

    def test_returns_none_for_empty_data(self):
        with patch("yfinance.download", return_value=pd.DataFrame()):
            result = self.fetcher.get_risk_metrics("AAPL")
        assert result is None

    def test_returns_none_for_invalid_symbol(self):
        result = self.fetcher.get_risk_metrics("@BAD!")
        assert result is None

    def test_returns_metrics_dict_with_required_keys(self):
        sym_df = self._make_price_series(300)
        bench_df = self._make_price_series(300, seed=99)
        with patch("yfinance.download", side_effect=[sym_df, bench_df]):
            result = self.fetcher.get_risk_metrics("AAPL")
        assert result is not None
        for key in ("beta", "alpha", "sharpe_ratio", "sortino_ratio",
                    "annual_return", "annual_volatility", "var_95",
                    "max_drawdown", "correlation"):
            assert key in result, f"Missing key: {key}"

    def test_symbol_and_benchmark_normalized(self):
        sym_df = self._make_price_series(300)
        bench_df = self._make_price_series(300, seed=99)
        with patch("yfinance.download", side_effect=[sym_df, bench_df]) as mock_dl:
            result = self.fetcher.get_risk_metrics("aapl", benchmark="^gspc")
        calls = mock_dl.call_args_list
        assert calls[0][0][0] == "AAPL"
        assert calls[1][0][0] == "^GSPC"


# ---------------------------------------------------------------------------
# DataFetcher.get_earnings_calendar
# ---------------------------------------------------------------------------

class TestGetEarningsCalendar:
    @pytest.fixture(autouse=True)
    def fetcher(self):
        from utils.data_fetcher import DataFetcher
        self.fetcher = DataFetcher()

    def test_returns_none_for_invalid_symbol(self):
        result = self.fetcher.get_earnings_calendar("@BAD!")
        assert result is None

    def test_returns_dict_with_symbol_key(self):
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = None
        mock_ticker.calendar = None
        mock_ticker.earnings_history = None
        mock_ticker.analyst_price_targets = None
        mock_ticker.recommendations = None
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_earnings_calendar("AAPL")
        assert result is not None
        assert result["symbol"] == "AAPL"

    def test_handles_attribute_errors_gracefully(self):
        """Each ticker attribute that fails should set None rather than raise."""
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = property(
            lambda self: (_ for _ in ()).throw(AttributeError("no attr"))
        )
        mock_ticker.calendar = None
        mock_ticker.earnings_history = None
        mock_ticker.analyst_price_targets = None
        mock_ticker.recommendations = None
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_earnings_calendar("AAPL")
        # Should still return a dict, with the failed key as None
        assert result is not None

    def test_recommendations_trimmed_to_15(self):
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = None
        mock_ticker.calendar = None
        mock_ticker.earnings_history = None
        mock_ticker.analyst_price_targets = None
        recs = pd.DataFrame({"firm": [f"firm_{i}" for i in range(20)]})
        mock_ticker.recommendations = recs
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = self.fetcher.get_earnings_calendar("AAPL")
        assert len(result["recommendations"]) == 15