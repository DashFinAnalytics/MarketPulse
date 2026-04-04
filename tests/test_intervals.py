"""Tests for utils/intervals.py - FinanceIntervals class.

This module was changed in the PR; tests cover all classmethods.
"""
from __future__ import annotations

import pytest

from utils.intervals import FinanceIntervals


class TestGetIntervalConfig:
    def test_returns_dict_for_valid_key(self):
        cfg = FinanceIntervals.get_interval_config("1d")
        assert isinstance(cfg, dict)
        assert "period" in cfg
        assert "interval" in cfg
        assert "name" in cfg
        assert "hours" in cfg

    def test_returns_none_for_unknown_key(self):
        assert FinanceIntervals.get_interval_config("unknown") is None

    def test_returns_none_for_empty_string(self):
        assert FinanceIntervals.get_interval_config("") is None

    def test_one_minute_config(self):
        cfg = FinanceIntervals.get_interval_config("1m")
        assert cfg["period"] == "1d"
        assert cfg["interval"] == "1m"
        assert cfg["name"] == "1 Minute"
        assert cfg["hours"] == pytest.approx(0.017)

    def test_yearly_config(self):
        cfg = FinanceIntervals.get_interval_config("1yr")
        assert cfg["period"] == "1y"
        assert cfg["interval"] == "1d"
        assert cfg["hours"] == 8760

    def test_ytd_config_has_none_hours(self):
        cfg = FinanceIntervals.get_interval_config("ytd")
        assert cfg is not None
        assert cfg["hours"] is None

    def test_max_period_config(self):
        cfg = FinanceIntervals.get_interval_config("50yr")
        assert cfg["period"] == "max"


class TestGetAvailableIntervals:
    def test_returns_dict(self):
        result = FinanceIntervals.get_available_intervals()
        assert isinstance(result, dict)

    def test_all_keys_present(self):
        result = FinanceIntervals.get_available_intervals()
        expected_keys = {"1m", "5m", "15m", "30m", "60m", "1d", "7d", "30d", "1yr"}
        assert expected_keys.issubset(result.keys())

    def test_values_are_display_names(self):
        result = FinanceIntervals.get_available_intervals()
        assert result["1d"] == "1 Day"
        assert result["1m"] == "1 Minute"
        assert result["ytd"] == "Year to Date"

    def test_count_matches_intervals_dict(self):
        result = FinanceIntervals.get_available_intervals()
        assert len(result) == len(FinanceIntervals.INTERVALS)


class TestCalculateHoursFromNow:
    def test_returns_float_for_known_interval(self):
        result = FinanceIntervals.calculate_hours_from_now("1d")
        assert result == 24.0

    def test_returns_none_for_unknown_interval(self):
        assert FinanceIntervals.calculate_hours_from_now("bogus") is None

    def test_returns_none_for_ytd(self):
        # ytd has hours=None in config
        assert FinanceIntervals.calculate_hours_from_now("ytd") is None

    def test_minute_intervals(self):
        assert FinanceIntervals.calculate_hours_from_now("5m") == pytest.approx(0.083)

    def test_weekly_interval(self):
        assert FinanceIntervals.calculate_hours_from_now("7d") == 168.0


class TestGetYfinanceParams:
    def test_returns_dict_for_valid_key(self):
        result = FinanceIntervals.get_yfinance_params("1d")
        assert result == {"period": "1y", "interval": "1d"}

    def test_returns_none_for_unknown_key(self):
        assert FinanceIntervals.get_yfinance_params("invalid") is None

    def test_intraday_params(self):
        result = FinanceIntervals.get_yfinance_params("5m")
        assert result["period"] == "5d"
        assert result["interval"] == "5m"

    def test_long_term_params(self):
        result = FinanceIntervals.get_yfinance_params("10yr")
        assert result["period"] == "10y"
        assert result["interval"] == "1mo"


class TestGetChartTitle:
    def test_returns_formatted_title(self):
        title = FinanceIntervals.get_chart_title("AAPL", "1d")
        assert "AAPL" in title
        assert "1 Day" in title

    def test_falls_back_to_generic_title_for_unknown_interval(self):
        title = FinanceIntervals.get_chart_title("TSLA", "invalid")
        assert title == "TSLA Price Chart"

    def test_title_contains_symbol(self):
        title = FinanceIntervals.get_chart_title("MSFT", "1m")
        assert "MSFT" in title
        assert "1 Minute" in title


class TestIsIntraday:
    def test_minute_intervals_are_intraday(self):
        for key in ("1m", "5m", "15m", "30m", "60m"):
            assert FinanceIntervals.is_intraday(key) is True, f"{key} should be intraday"

    def test_daily_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("1d") is False

    def test_weekly_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("7d") is False

    def test_unknown_key_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("bogus") is False

    def test_ytd_is_not_intraday(self):
        # ytd has hours=None, treated as non-intraday
        assert FinanceIntervals.is_intraday("ytd") is False

    def test_hourly_intervals_are_intraday(self):
        # 2hr has hours=2, which is < 24
        assert FinanceIntervals.is_intraday("2hr") is True
        assert FinanceIntervals.is_intraday("4hr") is True
        assert FinanceIntervals.is_intraday("8hr") is True


class TestGetDbLookbackHours:
    def test_returns_int(self):
        result = FinanceIntervals.get_db_lookback_hours("1d")
        assert isinstance(result, int)

    def test_unknown_interval_returns_default_24(self):
        assert FinanceIntervals.get_db_lookback_hours("bogus") == 24

    def test_minute_interval_returns_at_least_24(self):
        result = FinanceIntervals.get_db_lookback_hours("1m")
        assert result >= 24

    def test_hourly_returns_at_least_weekly(self):
        result = FinanceIntervals.get_db_lookback_hours("2hr")
        assert result >= 168

    def test_daily_returns_double_period(self):
        # 1d has hours=24; 24*2=48
        result = FinanceIntervals.get_db_lookback_hours("1d")
        assert result == 48

    def test_ytd_returns_positive_hours(self):
        result = FinanceIntervals.get_db_lookback_hours("ytd")
        assert result > 0

    def test_monthly_uses_period_as_is(self):
        # 30d has hours=720
        result = FinanceIntervals.get_db_lookback_hours("30d")
        assert result == 720

    def test_yearly_uses_period_as_is(self):
        # 1yr has hours=8760
        result = FinanceIntervals.get_db_lookback_hours("1yr")
        assert result == 8760

    # Regression: previously this raised AttributeError on None hours
    def test_ytd_does_not_raise(self):
        try:
            FinanceIntervals.get_db_lookback_hours("ytd")
        except Exception as exc:
            pytest.fail(f"get_db_lookback_hours('ytd') raised {exc}")