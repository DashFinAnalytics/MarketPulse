"""
Market status detection — open/closed/pre-market/after-hours.
"""

import logging
from datetime import datetime
from datetime import time as dtime
from typing import Literal, TypedDict

import pytz

logger = logging.getLogger(__name__)

try:
    import pandas_market_calendars as mcal  # type: ignore

    _NYSE = mcal.get_calendar("NYSE")
    HAS_CAL = True
except Exception:
    _NYSE = None
    HAS_CAL = False


class MarketStatus(TypedDict):
    status: str
    label: str
    color: str
    is_open: bool
    session: str


class MarketHoursConfig(TypedDict):
    tz: str
    open: tuple[int, int]
    close: tuple[int, int]


class MajorMarketStatus(TypedDict):
    market: str
    status: Literal["OPEN", "CLOSED"]
    color: str
    local_time: str


def get_market_status() -> MarketStatus:
    """
    Return NYSE market status dict:
      status, label, color, is_open, session
    """
    et = pytz.timezone("America/New_York")
    now = datetime.now(et)
    wday = now.weekday()  # 0=Mon … 6=Sun

    if wday >= 5:
        return _status("CLOSED", "Weekend — Closed", "#ff4444", False, "weekend")

    # Holiday check
    if HAS_CAL and _NYSE is not None:
        try:
            today = now.strftime("%Y-%m-%d")
            sched = _NYSE.schedule(start_date=today, end_date=today)
            if sched.empty:
                return _status("CLOSED", "Market Holiday", "#ff4444", False, "holiday")
        except Exception:
            pass

    current_time = now.time()
    pre_market = dtime(4, 0)
    market_open = dtime(9, 30)
    market_close = dtime(16, 0)
    after_hours_close = dtime(20, 0)

    if current_time < pre_market:
        return _status("CLOSED", "Closed (overnight)", "#888888", False, "closed")
    if current_time < market_open:
        return _status("PRE-MARKET", "Pre-Market", "#ffaa00", True, "pre-market")
    if current_time < market_close:
        return _status("OPEN", "● Market Open", "#00cc66", True, "regular")
    if current_time < after_hours_close:
        return _status("AFTER-HOURS", "After-Hours", "#ffaa00", True, "after-hours")
    return _status("CLOSED", "Closed", "#888888", False, "closed")


def _status(
    status: str,
    label: str,
    color: str,
    is_open: bool,
    session: str,
) -> MarketStatus:
    return {
        "status": status,
        "label": label,
        "color": color,
        "is_open": is_open,
        "session": session,
    }


def get_major_market_hours() -> list[MajorMarketStatus]:
    """Return a summary of major market open/closed status."""
    now_utc = datetime.now(pytz.utc)
    markets: dict[str, MarketHoursConfig] = {
        "NYSE / NASDAQ": {
            "tz": "America/New_York",
            "open": (9, 30),
            "close": (16, 0),
        },
        "London (LSE)": {
            "tz": "Europe/London",
            "open": (8, 0),
            "close": (16, 30),
        },
        "Frankfurt": {
            "tz": "Europe/Berlin",
            "open": (9, 0),
            "close": (17, 30),
        },
        "Tokyo (TSE)": {
            "tz": "Asia/Tokyo",
            "open": (9, 0),
            "close": (15, 30),
        },
        "Hong Kong": {
            "tz": "Asia/Hong_Kong",
            "open": (9, 30),
            "close": (16, 0),
        },
        "Sydney (ASX)": {
            "tz": "Australia/Sydney",
            "open": (10, 0),
            "close": (16, 0),
        },
    }

    result: list[MajorMarketStatus] = []

    for name, cfg in markets.items():
        try:
            tz_name = cfg["tz"]
            open_hour, open_minute = cfg["open"]
            close_hour, close_minute = cfg["close"]

            tz = pytz.timezone(tz_name)
            local = now_utc.astimezone(tz)
            wday = local.weekday()
            local_time = local.time()
            market_open = dtime(open_hour, open_minute)
            market_close = dtime(close_hour, close_minute)

            if wday >= 5:
                status: Literal["OPEN", "CLOSED"] = "CLOSED"
                color = "#ff4444"
            elif market_open <= local_time < market_close:
                status = "OPEN"
                color = "#00cc66"
            else:
                status = "CLOSED"
                color = "#ff4444"

            result.append(
                {
                    "market": name,
                    "status": status,
                    "color": color,
                    "local_time": local.strftime("%H:%M %Z"),
                }
            )
        except Exception:
            pass

    return result
