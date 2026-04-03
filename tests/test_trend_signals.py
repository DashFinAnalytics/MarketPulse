"""Tests for utils/trend_signals.py — TIMEFRAME_DAYS, _neutral, compute_trend_signal, batch_trend_signals."""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# TIMEFRAME_DAYS constant
# ---------------------------------------------------------------------------

class TestTimeframeDays:
    """Tests for TIMEFRAME_DAYS module-level constant."""

    def test_is_dict(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        assert isinstance(TIMEFRAME_DAYS, dict)

    def test_has_expected_keys(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        keys = list(TIMEFRAME_DAYS.keys())
        assert len(keys) == 4

    def test_values_are_positive_ints(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        for label, days in TIMEFRAME_DAYS.items():
            assert isinstance(days, int), f"Expected int for {label}"
            assert days > 0

    def test_short_term_less_than_long_term(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        values = list(TIMEFRAME_DAYS.values())
        assert values[0] < values[-1]

    def test_contains_5_day_short_term(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        assert 5 in TIMEFRAME_DAYS.values()

    def test_contains_21_day_medium_term(self):
        from utils.trend_signals import TIMEFRAME_DAYS
        assert 21 in TIMEFRAME_DAYS.values()


# ---------------------------------------------------------------------------
# _neutral helper
# ---------------------------------------------------------------------------

class TestNeutral:
    """Tests for _neutral internal function."""

    def setup_method(self):
        from utils.trend_signals import _neutral
        self._neutral = _neutral

    def test_returns_dict(self):
        result = self._neutral("SPY")
        assert isinstance(result, dict)

    def test_symbol_passed_through(self):
        result = self._neutral("AAPL")
        assert result["symbol"] == "AAPL"

    def test_direction_is_neutral(self):
        result = self._neutral("SPY")
        assert result["direction"] == "NEUTRAL"

    def test_strength_is_zero(self):
        result = self._neutral("SPY")
        assert result["strength"] == 0

    def test_score_is_zero(self):
        result = self._neutral("SPY")
        assert result["score"] == 0

    def test_emoji_is_neutral(self):
        result = self._neutral("SPY")
        assert result["emoji"] == "⚪"

    def test_rsi_is_fifty(self):
        result = self._neutral("SPY")
        assert result["rsi"] == 50

    def test_momentum_pct_is_zero(self):
        result = self._neutral("SPY")
        assert result["momentum_pct"] == 0

    def test_boolean_fields_are_none(self):
        result = self._neutral("SPY")
        assert result["above_sma20"] is None
        assert result["above_sma50"] is None
        assert result["above_sma200"] is None
        assert result["macd_positive"] is None
        assert result["macd_above_sig"] is None

    def test_price_fields_are_zero(self):
        result = self._neutral("SPY")
        assert result["last_price"] == 0
        assert result["sma20"] == 0
        assert result["sma50"] == 0

    def test_required_keys_all_present(self):
        result = self._neutral("TEST")
        required = [
            "symbol", "direction", "strength", "score", "emoji",
            "rsi", "momentum_pct", "above_sma20", "above_sma50",
            "above_sma200", "macd_positive", "macd_above_sig",
            "last_price", "sma20", "sma50"
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# compute_trend_signal
# ---------------------------------------------------------------------------

def _make_history_df(n=252, trend="up"):
    """Create a fake yfinance history DataFrame."""
    if trend == "up":
        closes = [100 + i * 0.5 for i in range(n)]
    elif trend == "down":
        closes = [200 - i * 0.5 for i in range(n)]
    elif trend == "flat":
        closes = [100.0] * n
    else:
        np.random.seed(42)
        closes = [100 + np.random.normal(0, 2) for _ in range(n)]

    dates = pd.date_range(start="2024-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "Close": closes,
        "Open":  closes,
        "High":  [c + 1 for c in closes],
        "Low":   [c - 1 for c in closes],
        "Volume": [1_000_000] * n,
    }, index=dates)


class TestComputeTrendSignal:
    """Tests for compute_trend_signal using mocked yfinance."""

    def _patch_yf(self, df):
        """Return a context manager that patches yf.Ticker to return given history."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        return patch("utils.trend_signals.yf.Ticker", return_value=mock_ticker)

    def _call(self, symbol, df, lookback_days=21):
        """Call compute_trend_signal bypassing the Streamlit cache."""
        # Import the unwrapped function directly
        import utils.trend_signals as ts
        with self._patch_yf(df):
            # Call the underlying function by bypassing @st.cache_data
            # since @st.cache_data wraps the function, access via __wrapped__ if available
            func = getattr(ts.compute_trend_signal, "__wrapped__", ts.compute_trend_signal)
            return func(symbol, lookback_days)

    def test_returns_dict(self):
        df = _make_history_df(252, "up")
        result = self._call("SPY", df)
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        df = _make_history_df(252, "up")
        result = self._call("SPY", df)
        required = [
            "symbol", "direction", "strength", "score", "emoji",
            "rsi", "momentum_pct", "above_sma20", "above_sma50",
            "above_sma200", "macd_positive", "macd_above_sig",
            "last_price", "sma20", "sma50"
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_symbol_passed_through(self):
        df = _make_history_df(252, "up")
        result = self._call("AAPL", df)
        assert result["symbol"] == "AAPL"

    def test_uptrend_returns_up_direction(self):
        df = _make_history_df(252, "up")
        result = self._call("SPY", df)
        assert result["direction"] == "UP"
        assert result["emoji"] == "🟢"

    def test_downtrend_returns_down_direction(self):
        df = _make_history_df(252, "down")
        result = self._call("SPY", df)
        assert result["direction"] == "DOWN"
        assert result["emoji"] == "🔴"

    def test_strength_between_0_and_100(self):
        df = _make_history_df(252, "up")
        result = self._call("SPY", df)
        assert 0 <= result["strength"] <= 100

    def test_rsi_between_0_and_100(self):
        df = _make_history_df(252, "up")
        result = self._call("SPY", df)
        assert 0 <= result["rsi"] <= 100

    def test_uptrend_above_sma20(self):
        df = _make_history_df(252, "up")
        result = self._call("SPY", df)
        assert result["above_sma20"] is True

    def test_downtrend_below_sma20(self):
        df = _make_history_df(252, "down")
        result = self._call("SPY", df)
        assert result["above_sma20"] is False

    def test_empty_data_returns_neutral(self):
        df = pd.DataFrame()
        result = self._call("SPY", df)
        assert result["direction"] == "NEUTRAL"
        assert result["strength"] == 0

    def test_insufficient_data_returns_neutral(self):
        df = _make_history_df(20, "up")  # Only 20 rows, need at least 30
        result = self._call("SPY", df)
        assert result["direction"] == "NEUTRAL"

    def test_exception_returns_neutral(self):
        """If yfinance raises an exception, should return neutral signal."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("network error")
        with patch("utils.trend_signals.yf.Ticker", return_value=mock_ticker):
            import utils.trend_signals as ts
            func = getattr(ts.compute_trend_signal, "__wrapped__", ts.compute_trend_signal)
            result = func("SPY", 21)
        assert result["direction"] == "NEUTRAL"

    def test_score_determines_direction_up(self):
        """Direction UP requires score >= 30."""
        df = _make_history_df(252, "up")
        result = self._call("SPY", df)
        if result["direction"] == "UP":
            assert result["score"] >= 30

    def test_score_determines_direction_down(self):
        """Direction DOWN requires score <= -30."""
        df = _make_history_df(252, "down")
        result = self._call("SPY", df)
        if result["direction"] == "DOWN":
            assert result["score"] <= -30

    def test_momentum_pct_positive_in_uptrend(self):
        df = _make_history_df(252, "up")
        result = self._call("SPY", df, lookback_days=21)
        assert result["momentum_pct"] > 0

    def test_last_price_reasonable(self):
        df = _make_history_df(252, "up")
        result = self._call("SPY", df)
        assert result["last_price"] > 0


# ---------------------------------------------------------------------------
# batch_trend_signals
# ---------------------------------------------------------------------------

class TestBatchTrendSignals:
    """Tests for batch_trend_signals function."""

    def test_returns_list(self):
        from utils.trend_signals import batch_trend_signals
        df = _make_history_df(252, "up")

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df

        with patch("utils.trend_signals.yf.Ticker", return_value=mock_ticker):
            # Bypass Streamlit cache if possible
            import utils.trend_signals as ts
            orig = ts.compute_trend_signal
            func = getattr(orig, "__wrapped__", orig)
            with patch.object(ts, "compute_trend_signal", side_effect=lambda s, d=21: func(s, d)):
                result = batch_trend_signals(["SPY", "QQQ"])

        assert isinstance(result, list)

    def test_returns_one_result_per_symbol(self):
        from utils.trend_signals import batch_trend_signals
        symbols = ["SPY", "QQQ", "AAPL"]
        df = _make_history_df(252, "up")

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df

        with patch("utils.trend_signals.yf.Ticker", return_value=mock_ticker):
            import utils.trend_signals as ts
            orig = ts.compute_trend_signal
            func = getattr(orig, "__wrapped__", orig)
            with patch.object(ts, "compute_trend_signal", side_effect=lambda s, d=21: func(s, d)):
                result = batch_trend_signals(symbols)

        assert len(result) == len(symbols)

    def test_empty_list_returns_empty(self):
        from utils.trend_signals import batch_trend_signals

        import utils.trend_signals as ts
        orig = ts.compute_trend_signal
        func = getattr(orig, "__wrapped__", orig)
        with patch.object(ts, "compute_trend_signal", side_effect=lambda s, d=21: func(s, d)):
            with patch("utils.trend_signals.yf.Ticker"):
                result = batch_trend_signals([])

        assert result == []

    def test_each_result_has_symbol_key(self):
        from utils.trend_signals import batch_trend_signals
        symbols = ["SPY", "GLD"]
        df = _make_history_df(252, "flat")

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df

        with patch("utils.trend_signals.yf.Ticker", return_value=mock_ticker):
            import utils.trend_signals as ts
            orig = ts.compute_trend_signal
            func = getattr(orig, "__wrapped__", orig)
            with patch.object(ts, "compute_trend_signal", side_effect=lambda s, d=21: func(s, d)):
                result = batch_trend_signals(symbols)

        result_symbols = [r["symbol"] for r in result]
        for sym in symbols:
            assert sym in result_symbols

    def test_lookback_days_passed_to_compute(self):
        """batch_trend_signals should pass lookback_days to compute_trend_signal."""
        import utils.trend_signals as ts
        captured = []

        def fake_compute(sym, lookback_days=21):
            captured.append(lookback_days)
            return ts._neutral(sym)

        with patch.object(ts, "compute_trend_signal", side_effect=fake_compute):
            ts.batch_trend_signals(["SPY"], lookback_days=63)

        assert all(d == 63 for d in captured)