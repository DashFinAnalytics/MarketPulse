"""Tests for utils/intervals.py — FinanceIntervals class."""

import pytest
from utils.intervals import FinanceIntervals


class TestGetIntervalConfig:
    """Tests for FinanceIntervals.get_interval_config."""

    def test_known_key_returns_dict(self):
        cfg = FinanceIntervals.get_interval_config("1d")
        assert cfg is not None
        assert isinstance(cfg, dict)

    def test_known_key_has_required_fields(self):
        cfg = FinanceIntervals.get_interval_config("1d")
        assert "period" in cfg
        assert "interval" in cfg
        assert "name" in cfg
        assert "hours" in cfg

    def test_unknown_key_returns_none(self):
        assert FinanceIntervals.get_interval_config("invalid_key") is None

    def test_empty_string_returns_none(self):
        assert FinanceIntervals.get_interval_config("") is None

    def test_1m_config(self):
        cfg = FinanceIntervals.get_interval_config("1m")
        assert cfg["period"] == "1d"
        assert cfg["interval"] == "1m"
        assert cfg["hours"] == pytest.approx(0.017)

    def test_1d_config(self):
        cfg = FinanceIntervals.get_interval_config("1d")
        assert cfg["period"] == "1y"
        assert cfg["interval"] == "1d"
        assert cfg["hours"] == 24

    def test_ytd_has_none_hours(self):
        cfg = FinanceIntervals.get_interval_config("ytd")
        assert cfg["hours"] is None

    def test_all_defined_keys_are_retrievable(self):
        for key in FinanceIntervals.INTERVALS:
            assert FinanceIntervals.get_interval_config(key) is not None


class TestGetAvailableIntervals:
    """Tests for FinanceIntervals.get_available_intervals."""

    def test_returns_dict(self):
        result = FinanceIntervals.get_available_intervals()
        assert isinstance(result, dict)

    def test_keys_match_intervals_dict(self):
        result = FinanceIntervals.get_available_intervals()
        assert set(result.keys()) == set(FinanceIntervals.INTERVALS.keys())

    def test_values_are_display_names(self):
        result = FinanceIntervals.get_available_intervals()
        assert result["1d"] == "1 Day"
        assert result["1m"] == "1 Minute"
        assert result["ytd"] == "Year to Date"

    def test_all_values_are_strings(self):
        result = FinanceIntervals.get_available_intervals()
        for v in result.values():
            assert isinstance(v, str)


class TestCalculateHoursFromNow:
    """Tests for FinanceIntervals.calculate_hours_from_now."""

    def test_1d_returns_24(self):
        assert FinanceIntervals.calculate_hours_from_now("1d") == 24

    def test_7d_returns_168(self):
        assert FinanceIntervals.calculate_hours_from_now("7d") == 168

    def test_ytd_returns_none(self):
        assert FinanceIntervals.calculate_hours_from_now("ytd") is None

    def test_invalid_key_returns_none(self):
        assert FinanceIntervals.calculate_hours_from_now("bogus") is None

    def test_1yr_returns_8760(self):
        assert FinanceIntervals.calculate_hours_from_now("1yr") == 8760


class TestGetYfinanceParams:
    """Tests for FinanceIntervals.get_yfinance_params."""

    def test_known_key_returns_period_and_interval(self):
        params = FinanceIntervals.get_yfinance_params("1d")
        assert params is not None
        assert "period" in params
        assert "interval" in params

    def test_unknown_key_returns_none(self):
        assert FinanceIntervals.get_yfinance_params("bogus") is None

    def test_1d_params_correct(self):
        params = FinanceIntervals.get_yfinance_params("1d")
        assert params["period"] == "1y"
        assert params["interval"] == "1d"

    def test_7d_params_correct(self):
        params = FinanceIntervals.get_yfinance_params("7d")
        assert params["period"] == "2y"
        assert params["interval"] == "1wk"

    def test_no_extra_keys_in_result(self):
        params = FinanceIntervals.get_yfinance_params("1d")
        assert set(params.keys()) == {"period", "interval"}


class TestGetChartTitle:
    """Tests for FinanceIntervals.get_chart_title."""

    def test_known_key_returns_formatted_title(self):
        title = FinanceIntervals.get_chart_title("SPY", "1d")
        assert "SPY" in title
        assert "1 Day" in title

    def test_unknown_key_returns_default_title(self):
        title = FinanceIntervals.get_chart_title("SPY", "bogus")
        assert title == "SPY Price Chart"

    def test_symbol_preserved(self):
        title = FinanceIntervals.get_chart_title("BTC-USD", "30d")
        assert "BTC-USD" in title


class TestIsIntraday:
    """Tests for FinanceIntervals.is_intraday."""

    def test_minute_intervals_are_intraday(self):
        assert FinanceIntervals.is_intraday("1m") is True
        assert FinanceIntervals.is_intraday("5m") is True
        assert FinanceIntervals.is_intraday("15m") is True
        assert FinanceIntervals.is_intraday("30m") is True

    def test_hour_intervals_are_intraday(self):
        assert FinanceIntervals.is_intraday("60m") is True
        assert FinanceIntervals.is_intraday("2hr") is True
        assert FinanceIntervals.is_intraday("4hr") is True
        assert FinanceIntervals.is_intraday("8hr") is True
        assert FinanceIntervals.is_intraday("12hr") is True

    def test_daily_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("1d") is False

    def test_weekly_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("7d") is False

    def test_monthly_is_not_intraday(self):
        assert FinanceIntervals.is_intraday("30d") is False

    def test_ytd_is_not_intraday(self):
        # ytd has hours=None, so should return False
        assert FinanceIntervals.is_intraday("ytd") is False

    def test_unknown_key_returns_false(self):
        assert FinanceIntervals.is_intraday("bogus") is False


class TestGetDbLookbackHours:
    """Tests for FinanceIntervals.get_db_lookback_hours."""

    def test_unknown_key_returns_24(self):
        assert FinanceIntervals.get_db_lookback_hours("bogus") == 24

    def test_minute_interval_returns_at_least_24(self):
        result = FinanceIntervals.get_db_lookback_hours("1m")
        assert result >= 24

    def test_hourly_interval_returns_at_least_168(self):
        result = FinanceIntervals.get_db_lookback_hours("60m")
        assert result >= 168

    def test_daily_interval_returns_double_hours(self):
        # 1d has 24 hours, so expect 24 * 2 = 48
        result = FinanceIntervals.get_db_lookback_hours("1d")
        assert result == 48

    def test_weekly_returns_double_hours(self):
        # 7d has 168 hours, expect 168 * 2 = 336
        result = FinanceIntervals.get_db_lookback_hours("7d")
        assert result == 336

    def test_monthly_returns_hours_as_is(self):
        # 30d has 720 hours (>= 720), returns as-is
        result = FinanceIntervals.get_db_lookback_hours("30d")
        assert result == 720

    def test_ytd_returns_positive_integer(self):
        result = FinanceIntervals.get_db_lookback_hours("ytd")
        assert isinstance(result, int)
        assert result > 0

    def test_1yr_returns_8760(self):
        # 1yr has 8760 hours (>= 720), returns as-is
        result = FinanceIntervals.get_db_lookback_hours("1yr")
        assert result == 8760