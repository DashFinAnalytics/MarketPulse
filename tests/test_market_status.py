"""Tests for utils/market_status.py — get_market_status, _status, get_major_market_hours."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, time as dtime
import pytz


# ---------------------------------------------------------------------------
# _status helper
# ---------------------------------------------------------------------------

class TestStatusHelper:
    """Tests for the _status internal helper function."""

    def setup_method(self):
        from utils.market_status import _status
        self._status = _status

    def test_returns_dict_with_required_keys(self):
        result = self._status("OPEN", "Market Open", "#00cc66", True, "regular")
        assert "status" in result
        assert "label" in result
        assert "color" in result
        assert "is_open" in result
        assert "session" in result

    def test_values_are_passed_correctly(self):
        result = self._status("CLOSED", "Weekend — Closed", "#ff4444", False, "weekend")
        assert result["status"] == "CLOSED"
        assert result["label"] == "Weekend — Closed"
        assert result["color"] == "#ff4444"
        assert result["is_open"] is False
        assert result["session"] == "weekend"

    def test_open_status(self):
        result = self._status("OPEN", "● Market Open", "#00cc66", True, "regular")
        assert result["is_open"] is True
        assert result["status"] == "OPEN"

    def test_pre_market_status(self):
        result = self._status("PRE-MARKET", "Pre-Market", "#ffaa00", True, "pre-market")
        assert result["is_open"] is True
        assert result["session"] == "pre-market"

    def test_after_hours_status(self):
        result = self._status("AFTER-HOURS", "After-Hours", "#ffaa00", True, "after-hours")
        assert result["is_open"] is True
        assert result["session"] == "after-hours"


# ---------------------------------------------------------------------------
# get_market_status
# ---------------------------------------------------------------------------

class TestGetMarketStatus:
    """Tests for get_market_status function using time mocking."""

    def _make_et_datetime(self, weekday, hour, minute):
        """Create a datetime in Eastern time for the given weekday (0=Mon) and time."""
        et = pytz.timezone("America/New_York")
        # Find a reference Monday and offset
        # Use a fixed Monday: Jan 6, 2025 is a Monday
        base = datetime(2025, 1, 6, tzinfo=et)
        target = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Offset by weekday days
        from datetime import timedelta
        target += timedelta(days=weekday)
        return target

    def _patch_now(self, dt):
        return patch("utils.market_status.datetime")

    def test_weekend_returns_closed(self):
        """Saturday should always return CLOSED."""
        et = pytz.timezone("America/New_York")
        from datetime import timedelta
        # Saturday = weekday 5
        saturday_et = datetime(2025, 1, 4, 12, 0, tzinfo=et)  # Jan 4, 2025 is Saturday

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = saturday_et
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            from utils.market_status import get_market_status
            result = get_market_status()

        assert result["status"] == "CLOSED"
        assert result["is_open"] is False
        assert result["session"] == "weekend"

    def test_sunday_returns_closed(self):
        """Sunday should return CLOSED."""
        et = pytz.timezone("America/New_York")
        sunday_et = datetime(2025, 1, 5, 14, 0, tzinfo=et)  # Jan 5, 2025 is Sunday

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = sunday_et
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            from utils.market_status import get_market_status
            result = get_market_status()

        assert result["status"] == "CLOSED"
        assert result["session"] == "weekend"

    def test_regular_hours_returns_open(self):
        """Weekday 10:00 ET should return OPEN."""
        et = pytz.timezone("America/New_York")
        monday_10am = datetime(2025, 1, 6, 10, 0, tzinfo=et)  # Monday

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = monday_10am
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            # Also need to patch HAS_CAL to skip holiday check
            with patch("utils.market_status.HAS_CAL", False):
                from utils.market_status import get_market_status
                result = get_market_status()

        assert result["status"] == "OPEN"
        assert result["is_open"] is True
        assert result["session"] == "regular"

    def test_pre_market_hours(self):
        """Weekday 5:00 ET should return PRE-MARKET."""
        et = pytz.timezone("America/New_York")
        monday_5am = datetime(2025, 1, 6, 5, 0, tzinfo=et)  # Monday

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = monday_5am
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with patch("utils.market_status.HAS_CAL", False):
                from utils.market_status import get_market_status
                result = get_market_status()

        assert result["status"] == "PRE-MARKET"
        assert result["is_open"] is True
        assert result["session"] == "pre-market"

    def test_after_hours(self):
        """Weekday 17:00 ET should return AFTER-HOURS."""
        et = pytz.timezone("America/New_York")
        monday_5pm = datetime(2025, 1, 6, 17, 0, tzinfo=et)  # Monday

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = monday_5pm
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with patch("utils.market_status.HAS_CAL", False):
                from utils.market_status import get_market_status
                result = get_market_status()

        assert result["status"] == "AFTER-HOURS"
        assert result["is_open"] is True
        assert result["session"] == "after-hours"

    def test_overnight_closed(self):
        """Weekday 2:00 ET (before pre-market) should return CLOSED."""
        et = pytz.timezone("America/New_York")
        monday_2am = datetime(2025, 1, 6, 2, 0, tzinfo=et)  # Monday

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = monday_2am
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with patch("utils.market_status.HAS_CAL", False):
                from utils.market_status import get_market_status
                result = get_market_status()

        assert result["status"] == "CLOSED"
        assert result["is_open"] is False

    def test_after_8pm_closed(self):
        """Weekday after 20:00 ET should return CLOSED."""
        et = pytz.timezone("America/New_York")
        monday_9pm = datetime(2025, 1, 6, 21, 0, tzinfo=et)  # Monday

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = monday_9pm
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with patch("utils.market_status.HAS_CAL", False):
                from utils.market_status import get_market_status
                result = get_market_status()

        assert result["status"] == "CLOSED"
        assert result["is_open"] is False

    def test_returns_all_required_keys(self):
        """get_market_status should always return a dict with required keys."""
        et = pytz.timezone("America/New_York")
        monday_10am = datetime(2025, 1, 6, 10, 0, tzinfo=et)

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = monday_10am
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with patch("utils.market_status.HAS_CAL", False):
                from utils.market_status import get_market_status
                result = get_market_status()

        assert "status" in result
        assert "label" in result
        assert "color" in result
        assert "is_open" in result
        assert "session" in result

    def test_holiday_returns_closed_when_cal_available(self):
        """When market calendar is available and schedule is empty (holiday), return CLOSED."""
        et = pytz.timezone("America/New_York")
        monday_10am = datetime(2025, 1, 6, 10, 0, tzinfo=et)

        mock_nyse = MagicMock()
        mock_nyse.schedule.return_value = MagicMock()
        mock_nyse.schedule.return_value.empty = True  # holiday

        with patch("utils.market_status.datetime") as mock_dt:
            mock_dt.now.return_value = monday_10am
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with patch("utils.market_status.HAS_CAL", True):
                with patch("utils.market_status._NYSE", mock_nyse):
                    from utils.market_status import get_market_status
                    result = get_market_status()

        assert result["status"] == "CLOSED"
        assert result["session"] == "holiday"


# ---------------------------------------------------------------------------
# get_major_market_hours
# ---------------------------------------------------------------------------

class TestGetMajorMarketHours:
    """Tests for get_major_market_hours function."""

    def test_returns_list(self):
        from utils.market_status import get_major_market_hours
        result = get_major_market_hours()
        assert isinstance(result, list)

    def test_returns_all_six_markets(self):
        from utils.market_status import get_major_market_hours
        result = get_major_market_hours()
        assert len(result) == 6

    def test_each_entry_has_required_keys(self):
        from utils.market_status import get_major_market_hours
        result = get_major_market_hours()
        required_keys = {"market", "status", "color", "local_time"}
        for entry in result:
            assert required_keys.issubset(entry.keys()), f"Missing keys in {entry}"

    def test_market_names_present(self):
        from utils.market_status import get_major_market_hours
        result = get_major_market_hours()
        market_names = [entry["market"] for entry in result]
        assert "NYSE / NASDAQ" in market_names
        assert "London (LSE)" in market_names
        assert "Tokyo (TSE)" in market_names

    def test_status_values_are_valid(self):
        from utils.market_status import get_major_market_hours
        result = get_major_market_hours()
        valid_statuses = {"OPEN", "CLOSED"}
        for entry in result:
            assert entry["status"] in valid_statuses

    def test_color_values_are_hex(self):
        from utils.market_status import get_major_market_hours
        result = get_major_market_hours()
        for entry in result:
            assert entry["color"].startswith("#")

    def test_local_time_format(self):
        from utils.market_status import get_major_market_hours
        result = get_major_market_hours()
        for entry in result:
            # local_time should contain a colon (HH:MM)
            assert ":" in entry["local_time"]

    def test_weekend_all_markets_closed(self):
        """On a Saturday UTC, all markets should be closed."""
        utc = pytz.utc
        # Saturday UTC: Jan 4, 2025 is a Saturday
        saturday_utc = datetime(2025, 1, 4, 12, 0, tzinfo=utc)

        with patch("utils.market_status.datetime") as mock_dt:
            # get_major_market_hours uses datetime.now(et) and datetime.now(pytz.utc)
            mock_dt.now.side_effect = lambda tz=None: saturday_utc.astimezone(tz) if tz else saturday_utc
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            from utils.market_status import get_major_market_hours
            result = get_major_market_hours()

        for entry in result:
            assert entry["status"] == "CLOSED", f"{entry['market']} should be CLOSED on Saturday"