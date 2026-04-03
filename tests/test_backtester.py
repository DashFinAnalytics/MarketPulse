"""Tests for utils/backtester.py — _stats, run_buy_and_hold, run_monte_carlo, strategies."""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_price_df(prices, start="2022-01-01"):
    """Build a minimal yfinance-like DataFrame with a Close column."""
    dates = pd.date_range(start=start, periods=len(prices), freq="B")
    df = pd.DataFrame({"Close": prices, "Open": prices, "High": prices, "Low": prices,
                        "Volume": [1_000_000] * len(prices)}, index=dates)
    return df


def _make_rising_prices(n=300, start=100.0, step=0.5):
    return [start + i * step for i in range(n)]


def _make_flat_prices(n=300, value=100.0):
    return [value] * n


def _make_zigzag_prices(n=300):
    """Alternating up/down to generate trades."""
    prices = []
    for i in range(n):
        prices.append(100 + (5 if i % 20 < 10 else -5))
    return prices


# ---------------------------------------------------------------------------
# _stats
# ---------------------------------------------------------------------------

class TestStats:
    """Tests for backtester._stats internal function."""

    def setup_method(self):
        # Import the private _stats function
        import importlib
        import utils.backtester as bt
        self._stats = bt._stats

    def _make_df(self, n=252):
        return _make_price_df(_make_rising_prices(n))

    def test_no_trades_returns_dict(self):
        df = self._make_df()
        equity = [10_000.0] * 10
        result = self._stats([], equity, 10_000, df, "TestStrat", "SPY")
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        df = self._make_df()
        equity = [10_000.0, 10_500.0, 11_000.0]
        trades = [{"entry": 100.0, "exit": 110.0, "pnl": 100.0, "pnl_pct": 10.0}]
        result = self._stats(trades, equity, 10_000, df, "TestStrat", "SPY")
        required = [
            "strategy", "symbol", "total_return", "annual_return", "volatility",
            "max_drawdown", "sharpe_ratio", "profit_factor", "final_capital",
            "num_trades", "win_rate", "avg_win_pct", "avg_loss_pct",
            "equity_curve", "trade_log"
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_strategy_name_passed_through(self):
        df = self._make_df()
        result = self._stats([], [10_000], 10_000, df, "My Strategy", "AAPL")
        assert result["strategy"] == "My Strategy"
        assert result["symbol"] == "AAPL"

    def test_win_rate_with_mixed_trades(self):
        df = self._make_df()
        trades = [
            {"entry": 100.0, "exit": 110.0, "pnl": 100.0,  "pnl_pct": 10.0},   # win
            {"entry": 110.0, "exit": 105.0, "pnl": -50.0,  "pnl_pct": -4.5},   # loss
            {"entry": 105.0, "exit": 115.0, "pnl": 100.0,  "pnl_pct": 9.5},    # win
        ]
        equity = [10_000, 10_100, 10_050, 10_150]
        result = self._stats(trades, equity, 10_000, df, "Strat", "SPY")
        # 2 wins out of 3 = 66.7%
        assert result["win_rate"] == pytest.approx(66.7, abs=0.2)
        assert result["num_trades"] == 3

    def test_no_trades_zero_win_rate(self):
        df = self._make_df()
        result = self._stats([], [10_000, 10_000], 10_000, df, "S", "SPY")
        assert result["win_rate"] == 0.0
        assert result["num_trades"] == 0

    def test_profit_factor_all_wins(self):
        df = self._make_df()
        trades = [
            {"entry": 100.0, "exit": 110.0, "pnl": 100.0, "pnl_pct": 10.0},
            {"entry": 100.0, "exit": 115.0, "pnl": 150.0, "pnl_pct": 15.0},
        ]
        result = self._stats(trades, [10_000, 10_100, 10_250], 10_000, df, "S", "SPY")
        # No losses, profit_factor should be 999 (the inf substitute)
        assert result["profit_factor"] == 999

    def test_max_drawdown_is_negative_or_zero(self):
        df = self._make_df()
        # Equity that drops significantly
        equity = [10_000, 12_000, 8_000, 9_000, 10_000]
        result = self._stats([], equity, 10_000, df, "S", "SPY")
        assert result["max_drawdown"] <= 0

    def test_final_capital_equals_last_equity(self):
        df = self._make_df()
        equity = [10_000, 10_500, 11_200.75]
        result = self._stats([], equity, 10_000, df, "S", "SPY")
        assert result["final_capital"] == pytest.approx(11_200.75, abs=0.01)

    def test_total_return_calculation(self):
        df = self._make_df()
        equity = [10_000, 11_000]  # 10% gain
        result = self._stats([], equity, 10_000, df, "S", "SPY")
        assert result["total_return"] == pytest.approx(10.0, abs=0.01)

    def test_total_return_loss(self):
        df = self._make_df()
        equity = [10_000, 9_000]  # -10% loss
        result = self._stats([], equity, 10_000, df, "S", "SPY")
        assert result["total_return"] == pytest.approx(-10.0, abs=0.01)

    def test_equity_curve_stored(self):
        df = self._make_df()
        equity = [10_000, 10_500, 11_000]
        result = self._stats([], equity, 10_000, df, "S", "SPY")
        assert result["equity_curve"] == equity


# ---------------------------------------------------------------------------
# run_buy_and_hold
# ---------------------------------------------------------------------------

class TestRunBuyAndHold:
    """Tests for run_buy_and_hold with mocked yfinance."""

    def _mock_fetch(self, prices):
        df = _make_price_df(prices)

        def fake_fetch(symbol, period="2y"):
            return df

        return fake_fetch

    def test_returns_error_on_empty_data(self):
        with patch("utils.backtester._fetch", return_value=pd.DataFrame()):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("FAKE")
        assert "error" in result

    def test_rising_market_positive_return(self):
        prices = _make_rising_prices(252)
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("SPY")
        assert result["total_return"] > 0

    def test_flat_market_near_zero_return(self):
        prices = _make_flat_prices(252, 100.0)
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("SPY")
        assert abs(result["total_return"]) < 0.01

    def test_required_keys_present(self):
        prices = _make_rising_prices(252)
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("SPY", initial_capital=10_000)
        required = [
            "strategy", "symbol", "total_return", "annual_return", "volatility",
            "max_drawdown", "sharpe_ratio", "final_capital", "num_trades",
            "win_rate", "equity_curve", "trade_log"
        ]
        for k in required:
            assert k in result, f"Missing key: {k}"

    def test_num_trades_is_one(self):
        prices = _make_rising_prices(252)
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("SPY")
        assert result["num_trades"] == 1

    def test_trade_log_is_empty(self):
        prices = _make_rising_prices(252)
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("SPY")
        assert result["trade_log"] == []

    def test_strategy_name_includes_symbol(self):
        prices = _make_rising_prices(252)
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("AAPL")
        assert "AAPL" in result["strategy"]

    def test_declining_market_negative_return(self):
        prices = list(reversed(_make_rising_prices(252)))
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("SPY")
        assert result["total_return"] < 0

    def test_win_rate_positive_when_profitable(self):
        prices = _make_rising_prices(252)
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("SPY")
        assert result["win_rate"] == 100.0

    def test_win_rate_zero_when_unprofitable(self):
        prices = list(reversed(_make_rising_prices(252)))
        fake_fetch = self._mock_fetch(prices)
        with patch("utils.backtester._fetch", side_effect=fake_fetch):
            from utils.backtester import run_buy_and_hold
            result = run_buy_and_hold("SPY")
        assert result["win_rate"] == 0.0


# ---------------------------------------------------------------------------
# run_sma_crossover
# ---------------------------------------------------------------------------

class TestRunSmaCrossover:
    """Tests for run_sma_crossover with mocked yfinance."""

    def test_returns_error_on_empty_data(self):
        with patch("utils.backtester._fetch", return_value=pd.DataFrame()):
            from utils.backtester import run_sma_crossover
            result = run_sma_crossover("FAKE")
        assert "error" in result

    def test_returns_error_when_insufficient_data(self):
        prices = _make_rising_prices(30)  # Too few for default fast=20, slow=50
        df = _make_price_df(prices)
        with patch("utils.backtester._fetch", return_value=df):
            from utils.backtester import run_sma_crossover
            result = run_sma_crossover("SPY")
        assert "error" in result

    def test_returns_dict_with_sufficient_data(self):
        prices = _make_rising_prices(300)
        df = _make_price_df(prices)
        with patch("utils.backtester._fetch", return_value=df):
            from utils.backtester import run_sma_crossover
            result = run_sma_crossover("SPY")
        assert isinstance(result, dict)
        assert "error" not in result

    def test_strategy_name_contains_crossover(self):
        prices = _make_rising_prices(300)
        df = _make_price_df(prices)
        with patch("utils.backtester._fetch", return_value=df):
            from utils.backtester import run_sma_crossover
            result = run_sma_crossover("SPY", fast=20, slow=50)
        assert "20" in result["strategy"]
        assert "50" in result["strategy"]


# ---------------------------------------------------------------------------
# run_rsi_strategy
# ---------------------------------------------------------------------------

class TestRunRsiStrategy:
    """Tests for run_rsi_strategy with mocked yfinance."""

    def test_returns_error_on_empty_data(self):
        with patch("utils.backtester._fetch", return_value=pd.DataFrame()):
            from utils.backtester import run_rsi_strategy
            result = run_rsi_strategy("FAKE")
        assert "error" in result

    def test_returns_dict_with_sufficient_data(self):
        prices = _make_zigzag_prices(300)
        df = _make_price_df(prices)
        with patch("utils.backtester._fetch", return_value=df):
            from utils.backtester import run_rsi_strategy
            result = run_rsi_strategy("SPY")
        assert isinstance(result, dict)
        assert "error" not in result

    def test_strategy_name_includes_rsi_period(self):
        prices = _make_zigzag_prices(300)
        df = _make_price_df(prices)
        with patch("utils.backtester._fetch", return_value=df):
            from utils.backtester import run_rsi_strategy
            result = run_rsi_strategy("SPY", rsi_period=14)
        assert "14" in result["strategy"]


# ---------------------------------------------------------------------------
# run_bollinger_band_strategy
# ---------------------------------------------------------------------------

class TestRunBollingerBandStrategy:
    """Tests for run_bollinger_band_strategy with mocked yfinance."""

    def test_returns_error_on_empty_data(self):
        with patch("utils.backtester._fetch", return_value=pd.DataFrame()):
            from utils.backtester import run_bollinger_band_strategy
            result = run_bollinger_band_strategy("FAKE")
        assert "error" in result

    def test_returns_dict_with_sufficient_data(self):
        prices = _make_zigzag_prices(300)
        df = _make_price_df(prices)
        with patch("utils.backtester._fetch", return_value=df):
            from utils.backtester import run_bollinger_band_strategy
            result = run_bollinger_band_strategy("SPY")
        assert isinstance(result, dict)
        assert "error" not in result

    def test_strategy_name_includes_bb_period(self):
        prices = _make_zigzag_prices(300)
        df = _make_price_df(prices)
        with patch("utils.backtester._fetch", return_value=df):
            from utils.backtester import run_bollinger_band_strategy
            result = run_bollinger_band_strategy("SPY", bb_period=20)
        assert "20" in result["strategy"]


# ---------------------------------------------------------------------------
# run_monte_carlo
# ---------------------------------------------------------------------------

class TestRunMonteCarlo:
    """Tests for run_monte_carlo."""

    def setup_method(self):
        from utils.backtester import run_monte_carlo
        self.run_monte_carlo = run_monte_carlo

    def _make_returns(self, n=252):
        np.random.seed(42)
        return pd.Series(np.random.normal(0.0005, 0.01, n))

    def test_returns_dict(self):
        returns = self._make_returns()
        result = self.run_monte_carlo(returns)
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        returns = self._make_returns()
        result = self.run_monte_carlo(returns)
        assert result is not None
        for key in ["median", "p10", "p25", "p75", "p90", "prob_profit", "paths"]:
            assert key in result

    def test_percentile_ordering(self):
        returns = self._make_returns()
        result = self.run_monte_carlo(returns)
        assert result["p10"] <= result["p25"] <= result["median"] <= result["p75"] <= result["p90"]

    def test_prob_profit_between_0_and_100(self):
        returns = self._make_returns()
        result = self.run_monte_carlo(returns)
        assert 0 <= result["prob_profit"] <= 100

    def test_paths_shape(self):
        returns = self._make_returns()
        n_simulations = 100
        n_days = 50
        result = self.run_monte_carlo(returns, n_simulations=n_simulations, n_days=n_days)
        assert result["paths"].shape == (n_simulations, n_days + 1)

    def test_paths_start_at_initial_capital(self):
        returns = self._make_returns()
        initial = 5_000
        result = self.run_monte_carlo(returns, initial_capital=initial)
        assert np.all(result["paths"][:, 0] == initial)

    def test_positive_returns_high_prob_profit(self):
        """Strongly positive returns distribution should have high prob_profit."""
        returns = pd.Series([0.01] * 252)  # 1% per day
        result = self.run_monte_carlo(returns, n_simulations=200, n_days=252)
        assert result["prob_profit"] > 90

    def test_negative_returns_low_prob_profit(self):
        """Strongly negative returns distribution should have low prob_profit."""
        returns = pd.Series([-0.01] * 252)  # -1% per day
        result = self.run_monte_carlo(returns, n_simulations=200, n_days=252)
        assert result["prob_profit"] < 10

    def test_returns_none_on_exception(self):
        """Passing non-series input should return None (error path)."""
        result = self.run_monte_carlo(None)
        assert result is None

    def test_custom_simulations_and_days(self):
        returns = self._make_returns()
        result = self.run_monte_carlo(returns, n_simulations=50, n_days=30)
        assert result is not None
        assert result["paths"].shape == (50, 31)