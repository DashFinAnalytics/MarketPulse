"""Tests for utils/backtester.py — strategy backtester functions."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


# ── Synthetic OHLCV DataFrame factory ───────────────────────────────────────

def _make_ohlcv(n=300, start_price=100.0, drift=0.0003, volatility=0.02, seed=42):
    """Generate a synthetic price series as a yfinance-like DataFrame."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, volatility, n)
    prices = start_price * np.cumprod(1 + returns)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
    df = pd.DataFrame(
        {
            "Open": prices * 0.999,
            "High": prices * 1.002,
            "Low": prices * 0.997,
            "Close": prices,
            "Volume": rng.integers(1_000_000, 10_000_000, n),
        },
        index=dates,
    )
    return df


# ── _stats ───────────────────────────────────────────────────────────────────

class TestStats:
    """Tests for the internal _stats() function."""

    def _import_stats(self):
        from utils.backtester import _stats
        return _stats

    def test_returns_required_keys(self):
        _stats = self._import_stats()
        df = _make_ohlcv(100)
        trades = [
            {"entry": 100, "exit": 110, "pnl": 1000, "pnl_pct": 10.0},
            {"entry": 110, "exit": 105, "pnl": -500, "pnl_pct": -4.5},
        ]
        equity = [10000, 11000, 10500]
        result = _stats(trades, equity, 10000, df, "Test Strategy", "SPY")
        required_keys = [
            "strategy", "symbol", "total_return", "annual_return",
            "volatility", "max_drawdown", "sharpe_ratio", "profit_factor",
            "final_capital", "num_trades", "win_rate", "avg_win_pct",
            "avg_loss_pct", "equity_curve", "trade_log",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_no_trades_zero_win_rate(self):
        _stats = self._import_stats()
        df = _make_ohlcv(100)
        result = _stats([], [10000, 10000], 10000, df, "Strategy", "SPY")
        assert result["win_rate"] == 0
        assert result["num_trades"] == 0

    def test_all_winning_trades(self):
        _stats = self._import_stats()
        df = _make_ohlcv(100)
        trades = [
            {"entry": 100, "exit": 110, "pnl": 1000, "pnl_pct": 10.0},
            {"entry": 90, "exit": 100, "pnl": 500, "pnl_pct": 11.1},
        ]
        equity = [10000, 11000, 12000]
        result = _stats(trades, equity, 10000, df, "Strategy", "SPY")
        assert result["win_rate"] == 100.0

    def test_all_losing_trades(self):
        _stats = self._import_stats()
        df = _make_ohlcv(100)
        trades = [
            {"entry": 100, "exit": 90, "pnl": -500, "pnl_pct": -10.0},
        ]
        equity = [10000, 9500]
        result = _stats(trades, equity, 10000, df, "Strategy", "SPY")
        assert result["win_rate"] == 0.0
        assert result["profit_factor"] == 999  # No wins → infinity capped at 999

    def test_total_return_calculation(self):
        _stats = self._import_stats()
        df = _make_ohlcv(100)
        equity = [10000, 12000]
        result = _stats([], equity, 10000, df, "Strategy", "SPY")
        assert result["total_return"] == pytest.approx(20.0, abs=0.01)

    def test_max_drawdown_is_negative_or_zero(self):
        _stats = self._import_stats()
        df = _make_ohlcv(100)
        equity = [10000, 12000, 9000, 11000]
        result = _stats([], equity, 10000, df, "Strategy", "SPY")
        assert result["max_drawdown"] <= 0

    def test_final_capital_matches_last_equity(self):
        _stats = self._import_stats()
        df = _make_ohlcv(100)
        equity = [10000, 9999.99]
        result = _stats([], equity, 10000, df, "Strategy", "SPY")
        assert result["final_capital"] == pytest.approx(9999.99, abs=0.01)

    def test_profit_factor_with_balanced_trades(self):
        _stats = self._import_stats()
        df = _make_ohlcv(100)
        trades = [
            {"entry": 100, "exit": 120, "pnl": 2000, "pnl_pct": 20.0},
            {"entry": 100, "exit": 90, "pnl": -1000, "pnl_pct": -10.0},
        ]
        equity = [10000, 12000, 11000]
        result = _stats(trades, equity, 10000, df, "Strategy", "SPY")
        assert result["profit_factor"] == pytest.approx(2.0, abs=0.01)


# ── run_monte_carlo ──────────────────────────────────────────────────────────

class TestRunMonteCarlo:
    """Tests for run_monte_carlo()."""

    def test_returns_required_keys(self):
        from utils.backtester import run_monte_carlo
        returns = pd.Series(np.random.normal(0.001, 0.02, 500))
        result = run_monte_carlo(returns, initial_capital=10_000, n_simulations=100, n_days=50)
        assert result is not None
        for key in ("median", "p10", "p25", "p75", "p90", "prob_profit", "paths"):
            assert key in result, f"Missing key: {key}"

    def test_paths_shape(self):
        from utils.backtester import run_monte_carlo
        returns = pd.Series(np.random.normal(0.001, 0.02, 500))
        n_sim, n_days = 50, 30
        result = run_monte_carlo(returns, n_simulations=n_sim, n_days=n_days)
        assert result["paths"].shape == (n_sim, n_days + 1)

    def test_percentile_ordering(self):
        from utils.backtester import run_monte_carlo
        returns = pd.Series(np.random.normal(0.0005, 0.01, 500))
        result = run_monte_carlo(returns, n_simulations=200, n_days=100)
        assert result["p10"] <= result["p25"] <= result["median"] <= result["p75"] <= result["p90"]

    def test_prob_profit_between_0_and_100(self):
        from utils.backtester import run_monte_carlo
        returns = pd.Series(np.random.normal(0.001, 0.02, 500))
        result = run_monte_carlo(returns, n_simulations=100, n_days=50)
        assert 0.0 <= result["prob_profit"] <= 100.0

    def test_initial_capital_in_first_column(self):
        from utils.backtester import run_monte_carlo
        returns = pd.Series(np.random.normal(0.001, 0.02, 500))
        cap = 5000
        result = run_monte_carlo(returns, initial_capital=cap, n_simulations=50, n_days=20)
        assert np.all(result["paths"][:, 0] == cap)

    def test_returns_none_on_empty_series(self):
        from utils.backtester import run_monte_carlo
        empty = pd.Series([], dtype=float)
        result = run_monte_carlo(empty)
        assert result is None

    def test_consistent_with_positive_drift(self):
        """Positive drift → median final value > initial capital."""
        from utils.backtester import run_monte_carlo
        np.random.seed(0)
        returns = pd.Series(np.full(252, 0.005))  # 0.5% daily gain
        result = run_monte_carlo(returns, initial_capital=10_000, n_simulations=200, n_days=100)
        assert result["median"] > 10_000

    def test_consistent_with_negative_drift(self):
        """Strong negative drift → median final value < initial capital."""
        from utils.backtester import run_monte_carlo
        np.random.seed(0)
        returns = pd.Series(np.full(252, -0.005))
        result = run_monte_carlo(returns, initial_capital=10_000, n_simulations=200, n_days=100)
        assert result["median"] < 10_000


# ── run_buy_and_hold (with mocked yfinance) ──────────────────────────────────

class TestRunBuyAndHold:
    """Tests for run_buy_and_hold() with mocked _fetch."""

    def _make_mock_fetch(self, df):
        return patch("utils.backtester._fetch", return_value=df)

    def test_returns_required_keys(self):
        from utils.backtester import run_buy_and_hold
        df = _make_ohlcv(200)
        with self._make_mock_fetch(df):
            result = run_buy_and_hold("SPY", period="2y", initial_capital=10_000)
        for key in ("strategy", "symbol", "total_return", "annual_return",
                    "volatility", "max_drawdown", "sharpe_ratio", "final_capital",
                    "num_trades", "win_rate", "avg_pnl_pct", "equity_curve", "trade_log"):
            assert key in result

    def test_empty_dataframe_returns_error(self):
        from utils.backtester import run_buy_and_hold
        with self._make_mock_fetch(pd.DataFrame()):
            result = run_buy_and_hold("SPY")
        assert "error" in result

    def test_num_trades_is_1(self):
        from utils.backtester import run_buy_and_hold
        df = _make_ohlcv(200)
        with self._make_mock_fetch(df):
            result = run_buy_and_hold("SPY")
        assert result["num_trades"] == 1

    def test_trade_log_is_empty(self):
        from utils.backtester import run_buy_and_hold
        df = _make_ohlcv(200)
        with self._make_mock_fetch(df):
            result = run_buy_and_hold("SPY")
        assert result["trade_log"] == []

    def test_positive_return_on_uptrend(self):
        from utils.backtester import run_buy_and_hold
        # Create strictly increasing price series
        n = 200
        prices = np.linspace(100, 150, n)
        dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
        df = pd.DataFrame({"Close": prices, "Open": prices, "High": prices, "Low": prices, "Volume": 1}, index=dates)
        with self._make_mock_fetch(df):
            result = run_buy_and_hold("SPY")
        assert result["total_return"] > 0

    def test_win_rate_100_on_uptrend(self):
        from utils.backtester import run_buy_and_hold
        n = 200
        prices = np.linspace(100, 150, n)
        dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
        df = pd.DataFrame({"Close": prices, "Open": prices, "High": prices, "Low": prices, "Volume": 1}, index=dates)
        with self._make_mock_fetch(df):
            result = run_buy_and_hold("SPY")
        assert result["win_rate"] == 100.0

    def test_symbol_preserved_in_result(self):
        from utils.backtester import run_buy_and_hold
        df = _make_ohlcv(200)
        with self._make_mock_fetch(df):
            result = run_buy_and_hold("AAPL")
        assert result["symbol"] == "AAPL"


# ── run_sma_crossover (with mocked data) ────────────────────────────────────

class TestRunSmaCrossover:
    """Tests for run_sma_crossover() with mocked _fetch."""

    def test_insufficient_data_returns_error(self):
        from utils.backtester import run_sma_crossover
        # Create a DataFrame too small for SMA(50) + 5
        df = _make_ohlcv(30)
        with patch("utils.backtester._fetch", return_value=df):
            result = run_sma_crossover("SPY", fast=20, slow=50)
        assert "error" in result

    def test_empty_dataframe_returns_error(self):
        from utils.backtester import run_sma_crossover
        with patch("utils.backtester._fetch", return_value=pd.DataFrame()):
            result = run_sma_crossover("SPY")
        assert "error" in result

    def test_sufficient_data_returns_stats(self):
        from utils.backtester import run_sma_crossover
        df = _make_ohlcv(300)
        with patch("utils.backtester._fetch", return_value=df):
            result = run_sma_crossover("SPY", fast=20, slow=50)
        assert "error" not in result
        assert "total_return" in result
        assert "strategy" in result

    def test_strategy_name_contains_periods(self):
        from utils.backtester import run_sma_crossover
        df = _make_ohlcv(300)
        with patch("utils.backtester._fetch", return_value=df):
            result = run_sma_crossover("SPY", fast=10, slow=30)
        assert "10" in result["strategy"]
        assert "30" in result["strategy"]


# ── run_rsi_strategy (with mocked data) ─────────────────────────────────────

class TestRunRsiStrategy:
    """Tests for run_rsi_strategy() with mocked _fetch."""

    def test_insufficient_data_returns_error(self):
        from utils.backtester import run_rsi_strategy
        df = _make_ohlcv(10)  # Too small
        with patch("utils.backtester._fetch", return_value=df):
            result = run_rsi_strategy("SPY", rsi_period=14)
        assert "error" in result

    def test_sufficient_data_returns_stats(self):
        from utils.backtester import run_rsi_strategy
        df = _make_ohlcv(300)
        with patch("utils.backtester._fetch", return_value=df):
            result = run_rsi_strategy("SPY")
        assert "error" not in result
        assert "num_trades" in result
        assert result["num_trades"] >= 0

    def test_win_rate_between_0_and_100(self):
        from utils.backtester import run_rsi_strategy
        df = _make_ohlcv(300)
        with patch("utils.backtester._fetch", return_value=df):
            result = run_rsi_strategy("SPY")
        if "win_rate" in result:
            assert 0 <= result["win_rate"] <= 100


# ── run_bollinger_band_strategy (with mocked data) ───────────────────────────

class TestRunBollingerBandStrategy:
    """Tests for run_bollinger_band_strategy() with mocked _fetch."""

    def test_insufficient_data_returns_error(self):
        from utils.backtester import run_bollinger_band_strategy
        df = _make_ohlcv(10)
        with patch("utils.backtester._fetch", return_value=df):
            result = run_bollinger_band_strategy("SPY", bb_period=20)
        assert "error" in result

    def test_sufficient_data_returns_stats(self):
        from utils.backtester import run_bollinger_band_strategy
        df = _make_ohlcv(300)
        with patch("utils.backtester._fetch", return_value=df):
            result = run_bollinger_band_strategy("SPY")
        assert "error" not in result
        assert "strategy" in result
        assert "Bollinger" in result["strategy"]

    def test_strategy_name_contains_period_and_sigma(self):
        from utils.backtester import run_bollinger_band_strategy
        df = _make_ohlcv(300)
        with patch("utils.backtester._fetch", return_value=df):
            result = run_bollinger_band_strategy("SPY", bb_period=15, std_mult=1.5)
        assert "15" in result["strategy"]
        assert "1.5" in result["strategy"]