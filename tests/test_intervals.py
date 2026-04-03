"""Tests for utils/intervals.py (new file added in this PR).

Covers: FinanceIntervals classmethods - get_interval_config, get_available_intervals,
calculate_hours_from_now, get_yfinance_params, get_chart_title, is_intraday,
get_db_lookback_hours.
"""
from __future__ import annotations

import pytest
from datetime import datetime

from utils.intervals import FinanceIntervals


class TestGetIntervalConfig:
    def test_valid_key_returns_dict(self):
        config = FinanceIntervals.get_interval_config("1d")
        assert isinstance(config, dict)
        assert "period" in config
        assert "interval" in config
        assert "name" in config
        assert "hours" in config

    def test_1m_config_values(self):
        config = FinanceIntervals.get_interval_config("1m")
        assert config["period"] == "1d"
        assert config["interval"] == "1m"
        assert config["hours"] == 0.017

    def test_1d_config_values(self):
        config = FinanceIntervals.get_interval_config("1d")
        assert config["period"] == "1y"
        assert config["interval"] == "1d"
        assert config["hours"] == 24

    def test_ytd_hours_is_none(self):
        config = FinanceIntervals.get_interval_config("ytd")
        assert config["hours"] is None

    def test_invalid_key_returns_none(self):
        assert FinanceIntervals.get_interval_config("invalid") is None

    def test_empty_string_returns_none(self):
        assert FinanceIntervals.get_interval_config("") is None

    def test_all_defined_keys_return_configs(self):
        for key in FinanceIntervals.INTERVALS:
            config = FinanceIntervals.get_interval_config(key)
            assert config is not None, f"Key {key!r} should return a config"


class TestGetAvailableIntervals:
    def test_returns_dict(self):
        result = FinanceIntervals.get_available_intervals()
        assert isinstance(result, dict)

    def test_all_keys_present(self):
        result = FinanceIntervals.get_available_intervals()
        for key in FinanceIntervals.INTERVALS:
            assert key in result

    def test_values_are_display_names(self):
        result = FinanceIntervals.get_available_intervals()
        assert result["1m"] == "1 Minute"
        assert result["1d"] == "1 Day"
        assert result["ytd"] == "Year to Date"

    def test_count_matches_intervals(self):
        result = FinanceIntervals.get_available_intervals()
        assert len(result) == len(FinanceIntervals.INTERVALS)


class TestCalculateHoursFromNow:
    def test_valid_key_returns_float(self):
        hours = FinanceIntervals.calculate_hours_from_now("1d")
        assert hours == 24.0

    def test_1m_returns_small_fraction(self):
        hours = FinanceIntervals.calculate_hours_from_now("1m")
        assert hours == pytest.approx(0.017)

    def test_ytd_returns_none(self):
        assert FinanceIntervals.calculate_hours_from_now("ytd") is None

    def test_invalid_key_returns_none(self):
        assert FinanceIntervals.calculate_hours_from_now("bad_key") is None

    def test_50yr_has_large_value(self):
        hours = FinanceIntervals.calculate_hours_from_now("50yr")
        assert hours == 438000


class TestGetYfinanceParams:
    def test_valid_key_returns_params(self):
        params = FinanceIntervals.get_yfinance_params("1d")
        assert isinstance(params, dict)
        assert "period" in params
        assert "interval" in params

    def test_1m_params(self):
        params = FinanceIntervals.get_yfinance_params("1m")
        assert params["period"] == "1d"
        assert params["interval"] == "1m"

    def test_30d_params(self):
        params = FinanceIntervals.get_yfinance_params("30d")
        assert params["period"] == "5y"
        assert params["interval"] == "1mo"

    def test_invalid_key_returns_none(self):
        assert FinanceIntervals.get_yfinance_params("nonexistent") is None

    def test_ytd_params_present(self):
        params = FinanceIntervals.get_yfinance_params("ytd")
        assert params is not None
        assert params["period"] == "ytd"


class TestGetChartTitle:
    def test_valid_interval_includes_name(self):
        title = FinanceIntervals.get_chart_title("AAPL", "1d")
        assert "AAPL" in title
        assert "1 Day" in title

    def test_invalid_interval_falls_back(self):
        title = FinanceIntervals.get_chart_title("TSLA", "bad_key")
        assert title == "TSLA Price Chart"

    def test_format_is_correct(self):
        title = FinanceIntervals.get_chart_title("SPY", "1m")
        assert title == "SPY - 1 Minute Chart"

    def test_symbol_preserved_exactly(self):
        title = FinanceIntervals.get_chart_title("^GSPC", "1yr")
        assert "^GSPC" in title


class TestIsIntraday:
    def test_1m_is_intraday(self):
        assert FinanceIntervals.is_intraday("1m") is True

    def test_5m_is_intraday(self):
        assert FinanceIntervals.is_intraday("5m") is True

    def test_60m_is_intraday(self):
        assert FinanceIntervals.is_intraday("60m") is True

    def test_12hr_is_intraday(self):
        assert FinanceIntervals.is_intraday("12hr") is True

    def test_1d_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("1d") is False

    def test_7d_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("7d") is False

    def test_1yr_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("1yr") is False

    def test_ytd_is_not_intraday(self):
        # hours is None for ytd, should return False
        assert FinanceIntervals.is_intraday("ytd") is False

    def test_invalid_key_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("bad") is False

    def test_boundary_24h_not_intraday(self):
        # 1d has exactly 24 hours; is_intraday requires strictly < 24
        assert FinanceIntervals.is_intraday("1d") is False


class TestGetDbLookbackHours:
    def test_invalid_key_defaults_to_24(self):
        result = FinanceIntervals.get_db_lookback_hours("nonexistent")
        assert result == 24

    def test_minute_interval_returns_at_least_24(self):
        # 1m has hours=0.017, multiplier gives small value, so clamped to 24
        result = FinanceIntervals.get_db_lookback_hours("1m")
        assert result >= 24

    def test_hour_interval_returns_at_least_168(self):
        # 2hr has hours=2, multiplier gives 40, clamped to 168
        result = FinanceIntervals.get_db_lookback_hours("2hr")
        assert result >= 168

    def test_daily_interval_returns_double(self):
        # 7d has hours=168; since 24 <= 168 < 720 → returns int(168 * 2) = 336
        result = FinanceIntervals.get_db_lookback_hours("7d")
        assert result == 336

    def test_monthly_interval_returns_hours_as_is(self):
        # 30d has hours=720; 720 >= 720 → returns int(720)
        result = FinanceIntervals.get_db_lookback_hours("30d")
        assert result == 720

    def test_long_interval_returns_hours_as_is(self):
        # 1yr has hours=8760 → returns 8760
        result = FinanceIntervals.get_db_lookback_hours("1yr")
        assert result == 8760

    def test_ytd_returns_positive_integer(self):
        result = FinanceIntervals.get_db_lookback_hours("ytd")
        assert isinstance(result, int)
        assert result > 0

    def test_returns_integer(self):
        for key in FinanceIntervals.INTERVALS:
            result = FinanceIntervals.get_db_lookback_hours(key)
            assert isinstance(result, int), f"Key {key!r} should return int, got {type(result)}"