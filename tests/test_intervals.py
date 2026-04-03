"""Tests for utils/intervals.py — FinanceIntervals class."""
import pytest
from datetime import datetime


class TestFinanceIntervalsGetIntervalConfig:
    """Tests for FinanceIntervals.get_interval_config."""

    def setup_method(self):
        from utils.intervals import FinanceIntervals
        self.FI = FinanceIntervals

    def test_returns_dict_for_valid_key(self):
        config = self.FI.get_interval_config("1d")
        assert isinstance(config, dict)

    def test_returns_none_for_invalid_key(self):
        result = self.FI.get_interval_config("invalid_key")
        assert result is None

    def test_all_known_interval_keys_return_config(self):
        known_keys = [
            "1m", "5m", "15m", "30m", "60m", "2hr", "4hr", "8hr", "12hr",
            "1d", "7d", "30d", "3m", "6m", "ytd", "1yr", "5yr", "10yr",
            "20yr", "50yr"
        ]
        for key in known_keys:
            config = self.FI.get_interval_config(key)
            assert config is not None, f"Expected config for key {key!r}"

    def test_config_has_required_fields(self):
        config = self.FI.get_interval_config("1d")
        assert "period" in config
        assert "interval" in config
        assert "name" in config
        assert "hours" in config

    def test_1d_config_values(self):
        config = self.FI.get_interval_config("1d")
        assert config["period"] == "1y"
        assert config["interval"] == "1d"
        assert config["hours"] == 24

    def test_ytd_config_has_none_hours(self):
        config = self.FI.get_interval_config("ytd")
        assert config["hours"] is None

    def test_empty_string_returns_none(self):
        assert self.FI.get_interval_config("") is None


class TestFinanceIntervalsGetAvailableIntervals:
    """Tests for FinanceIntervals.get_available_intervals."""

    def setup_method(self):
        from utils.intervals import FinanceIntervals
        self.FI = FinanceIntervals

    def test_returns_dict(self):
        result = self.FI.get_available_intervals()
        assert isinstance(result, dict)

    def test_all_keys_are_strings(self):
        intervals = self.FI.get_available_intervals()
        for k, v in intervals.items():
            assert isinstance(k, str)
            assert isinstance(v, str)

    def test_contains_1d(self):
        intervals = self.FI.get_available_intervals()
        assert "1d" in intervals

    def test_names_are_human_readable(self):
        intervals = self.FI.get_available_intervals()
        assert intervals["1d"] == "1 Day"
        assert intervals["1m"] == "1 Minute"
        assert intervals["1yr"] == "1 Year"

    def test_count_matches_intervals_dict(self):
        intervals = self.FI.get_available_intervals()
        assert len(intervals) == len(self.FI.INTERVALS)


class TestFinanceIntervalsGetYfinanceParams:
    """Tests for FinanceIntervals.get_yfinance_params."""

    def setup_method(self):
        from utils.intervals import FinanceIntervals
        self.FI = FinanceIntervals

    def test_returns_dict_for_valid_key(self):
        params = self.FI.get_yfinance_params("1d")
        assert isinstance(params, dict)

    def test_returns_none_for_invalid_key(self):
        assert self.FI.get_yfinance_params("bogus") is None

    def test_params_have_period_and_interval_keys(self):
        params = self.FI.get_yfinance_params("1d")
        assert "period" in params
        assert "interval" in params

    def test_1d_yfinance_params(self):
        params = self.FI.get_yfinance_params("1d")
        assert params["period"] == "1y"
        assert params["interval"] == "1d"

    def test_intraday_1m_params(self):
        params = self.FI.get_yfinance_params("1m")
        assert params["period"] == "1d"
        assert params["interval"] == "1m"

    def test_weekly_7d_params(self):
        params = self.FI.get_yfinance_params("7d")
        assert params["period"] == "2y"
        assert params["interval"] == "1wk"


class TestFinanceIntervalsIsIntraday:
    """Tests for FinanceIntervals.is_intraday."""

    def setup_method(self):
        from utils.intervals import FinanceIntervals
        self.FI = FinanceIntervals

    def test_minute_intervals_are_intraday(self):
        assert self.FI.is_intraday("1m") is True
        assert self.FI.is_intraday("5m") is True
        assert self.FI.is_intraday("15m") is True
        assert self.FI.is_intraday("30m") is True
        assert self.FI.is_intraday("60m") is True

    def test_hourly_intervals_are_intraday(self):
        assert self.FI.is_intraday("2hr") is True
        assert self.FI.is_intraday("4hr") is True
        assert self.FI.is_intraday("8hr") is True
        assert self.FI.is_intraday("12hr") is True

    def test_daily_is_not_intraday(self):
        assert self.FI.is_intraday("1d") is False

    def test_weekly_is_not_intraday(self):
        assert self.FI.is_intraday("7d") is False

    def test_ytd_is_not_intraday(self):
        assert self.FI.is_intraday("ytd") is False

    def test_invalid_key_returns_false(self):
        assert self.FI.is_intraday("invalid") is False


class TestFinanceIntervalsGetChartTitle:
    """Tests for FinanceIntervals.get_chart_title."""

    def setup_method(self):
        from utils.intervals import FinanceIntervals
        self.FI = FinanceIntervals

    def test_valid_key_returns_formatted_title(self):
        title = self.FI.get_chart_title("SPY", "1d")
        assert "SPY" in title
        assert "1 Day" in title

    def test_invalid_key_returns_generic_title(self):
        title = self.FI.get_chart_title("AAPL", "bogus")
        assert "AAPL" in title
        assert "Price Chart" in title

    def test_title_includes_symbol(self):
        for sym in ["TSLA", "BTC-USD", "EURUSD=X"]:
            title = self.FI.get_chart_title(sym, "1d")
            assert sym in title


class TestFinanceIntervalsGetDbLookbackHours:
    """Tests for FinanceIntervals.get_db_lookback_hours."""

    def setup_method(self):
        from utils.intervals import FinanceIntervals
        self.FI = FinanceIntervals

    def test_invalid_key_returns_24(self):
        result = self.FI.get_db_lookback_hours("invalid_key")
        assert result == 24

    def test_1d_returns_positive_int(self):
        result = self.FI.get_db_lookback_hours("1d")
        assert isinstance(result, int)
        assert result > 0

    def test_minute_intervals_return_at_least_24(self):
        result = self.FI.get_db_lookback_hours("1m")
        assert result >= 24

    def test_hourly_intervals_return_at_least_168(self):
        result = self.FI.get_db_lookback_hours("2hr")
        assert result >= 168

    def test_ytd_returns_positive_int(self):
        result = self.FI.get_db_lookback_hours("ytd")
        assert isinstance(result, int)
        assert result > 0

    def test_longer_intervals_return_larger_lookback(self):
        lookback_1d = self.FI.get_db_lookback_hours("1d")
        lookback_1yr = self.FI.get_db_lookback_hours("1yr")
        assert lookback_1yr > lookback_1d


class TestFinanceIntervalsCalculateHoursFromNow:
    """Tests for FinanceIntervals.calculate_hours_from_now."""

    def setup_method(self):
        from utils.intervals import FinanceIntervals
        self.FI = FinanceIntervals

    def test_returns_hours_for_valid_key(self):
        result = self.FI.calculate_hours_from_now("1d")
        assert result == 24.0

    def test_returns_none_for_ytd(self):
        result = self.FI.calculate_hours_from_now("ytd")
        assert result is None

    def test_returns_none_for_invalid_key(self):
        result = self.FI.calculate_hours_from_now("bogus")
        assert result is None

    def test_1m_has_fractional_hours(self):
        result = self.FI.calculate_hours_from_now("1m")
        assert 0 < result < 1

    def test_1yr_returns_8760_hours(self):
        result = self.FI.calculate_hours_from_now("1yr")
        assert result == 8760