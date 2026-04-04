"""Tests for utils/trend_signals.py — trend signal engine.

Note: trend_signals.py imports streamlit and uses @st.cache_data.
We stub out streamlit before importing the module.
"""

import sys
import types
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ── Streamlit stub ───────────────────────────────────────────────────────────

def _make_st_stub():
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
    original_streamlit = sys.modules.get("streamlit")
    inserted_stub = False
    if original_streamlit is None:
        sys.modules["streamlit"] = _make_st_stub()
        inserted_stub = True
    sys.modules.pop("utils.trend_signals", None)
    yield
    sys.modules.pop("utils.trend_signals", None)
    if inserted_stub:
        sys.modules.pop("streamlit", None)
    elif original_streamlit is not None:
        sys.modules["streamlit"] = original_streamlit

# ── TIMEFRAME_DAYS constant ──────────────────────────────────────────────────

class TestTimeframeDays:
    """Tests for the TIMEFRAME_DAYS constant."""

    def test_is_dict(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        assert isinstance(TIMEFRAME_DAYS, dict)

    def test_has_short_timeframe(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        labels = list(TIMEFRAME_DAYS.keys())
        assert any("week" in label.lower() or "short" in label.lower() for label in labels)

    def test_all_values_are_positive_integers(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        for label, days in TIMEFRAME_DAYS.items():
            assert isinstance(days, int), f"Value for {label!r} is not int"
            assert days > 0, f"Value for {label!r} should be positive"

    def test_values_ordered_ascending(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        values = list(TIMEFRAME_DAYS.values())
        assert values == sorted(values), "TIMEFRAME_DAYS values should be in ascending order"

    def test_short_timeframe_is_5_days(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        # The shortest timeframe should be 5 days (1 week)
        assert min(TIMEFRAME_DAYS.values()) == 5

    def test_has_four_timeframes(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        assert len(TIMEFRAME_DAYS) == 4


# ── _neutral ─────────────────────────────────────────────────────────────────

class TestNeutral:
    """Tests for the _neutral() helper function."""

    def test_returns_dict_with_required_keys(self):
        from utils.trend_signals import _neutral
        result = _neutral("SPY")
        expected_keys = [
            "symbol", "direction", "strength", "score", "emoji",
            "rsi", "momentum_pct", "above_sma20", "above_sma50", "above_sma200",
            "macd_positive", "macd_above_sig", "last_price", "sma20", "sma50",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_direction_is_neutral(self):
        from utils.trend_signals import _neutral
        result = _neutral("SPY")
        assert result["direction"] == "NEUTRAL"

    def test_strength_is_zero(self):
        from utils.trend_signals import _neutral
        result = _neutral("SPY")
        assert result["strength"] == 0

    def test_score_is_zero(self):
        from utils.trend_signals import _neutral
        result = _neutral("SPY")
        assert result["score"] == 0

    def test_emoji_is_white_circle(self):
        from utils.trend_signals import _neutral
        result = _neutral("SPY")
        assert result["emoji"] == "⚪"

    def test_symbol_preserved(self):
        from utils.trend_signals import _neutral
        result = _neutral("BTC-USD")
        assert result["symbol"] == "BTC-USD"

    def test_rsi_is_50(self):
        from utils.trend_signals import _neutral
        result = _neutral("SPY")
        assert result["rsi"] == 50

    def test_sma_values_are_zero(self):
        from utils.trend_signals import _neutral
        result = _neutral("SPY")
        assert result["sma20"] == 0
        assert result["sma50"] == 0
        assert result["last_price"] == 0

    def test_none_fields_are_none(self):
        from utils.trend_signals import _neutral
        result = _neutral("SPY")
        assert result["above_sma20"] is None
        assert result["above_sma50"] is None
        assert result["above_sma200"] is None
        assert result["macd_positive"] is None
        assert result["macd_above_sig"] is None


# ── compute_trend_signal ──────────────────────────────────────────────────────

class TestComputeTrendSignal:
    """Tests for compute_trend_signal() with mocked yfinance."""

    def _make_price_series(self, n=252, start=100.0, drift=0.001, volatility=0.01, seed=42):
        rng = np.random.default_rng(seed)
        returns = rng.normal(drift, volatility, n)
        prices = start * np.cumprod(1 + returns)
        dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
        df = pd.DataFrame({"Close": prices}, index=dates)
        df["Open"] = prices * 0.999
        df["High"] = prices * 1.001
        df["Low"] = prices * 0.998
        df["Volume"] = 1_000_000
        return df

    def _mock_ticker(self, df):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        return mock_ticker

    def test_returns_neutral_on_empty_data(self):
        from utils.trend_signals import compute_trend_signal
        empty_df = pd.DataFrame()
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = empty_df
            result = compute_trend_signal("SPY")
        assert result["direction"] == "NEUTRAL"
        assert result["strength"] == 0

    def test_returns_neutral_on_insufficient_data(self):
        from utils.trend_signals import compute_trend_signal
        small_df = self._make_price_series(n=10)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = small_df
            result = compute_trend_signal("SPY")
        assert result["direction"] == "NEUTRAL"

    def test_returns_dict_with_required_keys_on_valid_data(self):
        from utils.trend_signals import compute_trend_signal
        df = self._make_price_series(n=252)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = df
            result = compute_trend_signal("SPY", lookback_days=21)
        expected_keys = [
            "symbol", "direction", "strength", "score", "emoji",
            "rsi", "momentum_pct", "above_sma20", "above_sma50", "above_sma200",
            "macd_positive", "last_price", "sma20", "sma50",
        ]
        for key in expected_keys:
            assert key in result

    def test_direction_values_valid(self):
        from utils.trend_signals import compute_trend_signal
        df = self._make_price_series(n=252)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = df
            result = compute_trend_signal("SPY")
        assert result["direction"] in ("UP", "DOWN", "NEUTRAL")

    def test_emoji_matches_direction(self):
        from utils.trend_signals import compute_trend_signal
        df = self._make_price_series(n=252)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = df
            result = compute_trend_signal("SPY")
        emoji_map = {"UP": "🟢", "DOWN": "🔴", "NEUTRAL": "⚪"}
        assert result["emoji"] == emoji_map[result["direction"]]

    def test_strength_between_0_and_100(self):
        from utils.trend_signals import compute_trend_signal
        df = self._make_price_series(n=252)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = df
            result = compute_trend_signal("SPY")
        assert 0 <= result["strength"] <= 100

    def test_returns_neutral_on_exception(self):
        from utils.trend_signals import compute_trend_signal
        with patch("utils.trend_signals.yf.Ticker", side_effect=Exception("network error")):
            result = compute_trend_signal("SPY")
        assert result["direction"] == "NEUTRAL"
        assert result["symbol"] == "SPY"

    def test_uptrend_detected_on_monotonic_increase(self):
        from utils.trend_signals import compute_trend_signal
        # Strictly increasing price series → should detect UP trend
        n = 252
        prices = np.linspace(50, 200, n)  # Steadily rising
        dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
        df = pd.DataFrame({
            "Close": prices, "Open": prices, "High": prices,
            "Low": prices, "Volume": 1_000_000
        }, index=dates)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = df
            result = compute_trend_signal("SPY", lookback_days=21)
        assert result["direction"] == "UP"
        assert result["above_sma20"] is True
        assert result["above_sma50"] is True

    def test_downtrend_detected_on_monotonic_decrease(self):
        from utils.trend_signals import compute_trend_signal
        # Strictly decreasing price series → should detect DOWN trend
        n = 252
        prices = np.linspace(200, 50, n)
        dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
        df = pd.DataFrame({
            "Close": prices, "Open": prices, "High": prices,
            "Low": prices, "Volume": 1_000_000
        }, index=dates)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = df
            result = compute_trend_signal("SPY", lookback_days=21)
        assert result["direction"] == "DOWN"
        assert result["above_sma20"] is False

    def test_symbol_preserved_in_result(self):
        from utils.trend_signals import compute_trend_signal
        df = self._make_price_series(n=252)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = df
            result = compute_trend_signal("BTC-USD")
        assert result["symbol"] == "BTC-USD"

    def test_rsi_between_0_and_100(self):
        from utils.trend_signals import compute_trend_signal
        df = self._make_price_series(n=252)
        with patch("utils.trend_signals.yf.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = df
            result = compute_trend_signal("SPY")
        if result["rsi"] != 50:  # Not default neutral
            assert 0 <= result["rsi"] <= 100


# ── batch_trend_signals ───────────────────────────────────────────────────────

class TestBatchTrendSignals:
    """Tests for batch_trend_signals()."""

    def test_returns_list(self):
        from utils.trend_signals import batch_trend_signals
        with patch("utils.trend_signals.compute_trend_signal") as mock_compute:
            mock_compute.return_value = {"symbol": "SPY", "direction": "UP"}
            result = batch_trend_signals(["SPY"])
        assert isinstance(result, list)

    def test_returns_one_result_per_symbol(self):
        from utils.trend_signals import batch_trend_signals
        symbols = ["SPY", "QQQ", "DIA"]
        with patch("utils.trend_signals.compute_trend_signal") as mock_compute:
            mock_compute.side_effect = lambda sym, **kwargs: {"symbol": sym, "direction": "UP"}
            result = batch_trend_signals(symbols)
        assert len(result) == 3

    def test_processes_symbols_in_order(self):
        from utils.trend_signals import batch_trend_signals
        symbols = ["SPY", "QQQ", "DIA"]
        with patch("utils.trend_signals.compute_trend_signal") as mock_compute:
            mock_compute.side_effect = lambda sym, **kwargs: {"symbol": sym, "direction": "UP"}
            result = batch_trend_signals(symbols)
        result_symbols = [r["symbol"] for r in result]
        assert result_symbols == symbols

    def test_empty_list_returns_empty(self):
        from utils.trend_signals import batch_trend_signals
        result = batch_trend_signals([])
        assert result == []

    def test_passes_lookback_days(self):
        from utils.trend_signals import batch_trend_signals
        with patch("utils.trend_signals.compute_trend_signal") as mock_compute:
            mock_compute.return_value = {"symbol": "SPY", "direction": "UP"}
            batch_trend_signals(["SPY"], lookback_days=63)
            mock_compute.assert_called_once_with("SPY", 63)

    def test_handles_neutral_results(self):
        from utils.trend_signals import batch_trend_signals, _neutral
        with patch("utils.trend_signals.compute_trend_signal") as mock_compute:
            mock_compute.return_value = _neutral("SPY")
            result = batch_trend_signals(["SPY"])
        assert len(result) == 1
        assert result[0]["direction"] == "NEUTRAL"