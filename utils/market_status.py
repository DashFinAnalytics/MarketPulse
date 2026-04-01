"""
Market status detection — open/closed/pre-market/after-hours
"""
from datetime import datetime, time as dtime
import pytz  # type: ignore[import-untyped]
import logging

logger = logging.getLogger(__name__)

try:
    import pandas_market_calendars as mcal
    _NYSE = mcal.get_calendar('NYSE')
    HAS_CAL = True
except Exception:
    _NYSE = None
    HAS_CAL = False


def get_market_status():
    """
    Return NYSE market status dict:
      status, label, color, is_open, session
    """
    et = pytz.timezone('America/New_York')
    now = datetime.now(et)
    wday = now.weekday()   # 0=Mon … 6=Sun

    if wday >= 5:
        return _status('CLOSED', 'Weekend — Closed', '#ff4444', False, 'weekend')

    # Holiday check
    if HAS_CAL and _NYSE is not None:
        try:
            today = now.strftime('%Y-%m-%d')
            sched = _NYSE.schedule(start_date=today, end_date=today)
            if sched.empty:
                return _status('CLOSED', 'Market Holiday', '#ff4444', False, 'holiday')
        except Exception:
            pass

    t = now.time()
    PRE   = dtime(4, 0)
    OPEN  = dtime(9, 30)
    CLOSE = dtime(16, 0)
    AH    = dtime(20, 0)

    if t < PRE:
        return _status('CLOSED',      'Closed (overnight)',  '#888888', False, 'closed')
    if t < OPEN:
        return _status('PRE-MARKET',  'Pre-Market',          '#ffaa00', True,  'pre-market')
    if t < CLOSE:
        return _status('OPEN',        '● Market Open',       '#00cc66', True,  'regular')
    if t < AH:
        return _status('AFTER-HOURS', 'After-Hours',         '#ffaa00', True,  'after-hours')
    return _status('CLOSED', 'Closed', '#888888', False, 'closed')


def _status(status, label, color, is_open, session):
    return dict(status=status, label=label, color=color,
                is_open=is_open, session=session)


def get_major_market_hours():
    """Returns a summary of each major market's status."""
    et = pytz.timezone('America/New_York')
    now_utc = datetime.now(pytz.utc)
    markets = {
        'NYSE / NASDAQ': {'tz': 'America/New_York',    'open': (9, 30),  'close': (16, 0)},
        'London (LSE)':  {'tz': 'Europe/London',        'open': (8, 0),   'close': (16, 30)},
        'Frankfurt':     {'tz': 'Europe/Berlin',        'open': (9, 0),   'close': (17, 30)},
        'Tokyo (TSE)':   {'tz': 'Asia/Tokyo',           'open': (9, 0),   'close': (15, 30)},
        'Hong Kong':     {'tz': 'Asia/Hong_Kong',       'open': (9, 30),  'close': (16, 0)},
        'Sydney (ASX)':  {'tz': 'Australia/Sydney',     'open': (10, 0),  'close': (16, 0)},
    }
    result = []
    for name, cfg in markets.items():
        try:
            tz = pytz.timezone(cfg['tz'])
            local = now_utc.astimezone(tz)
            wday  = local.weekday()
            t     = local.time()
            op    = dtime(cfg['open'][0],  cfg['open'][1])
            cl    = dtime(cfg['close'][0], cfg['close'][1])
            if wday >= 5:
                status, color = 'CLOSED', '#ff4444'
            elif op <= t < cl:
                status, color = 'OPEN',   '#00cc66'
            else:
                status, color = 'CLOSED', '#ff4444'
            result.append({
                'market': name,
                'status': status,
                'color':  color,
                'local_time': local.strftime('%H:%M %Z')
            })
        except Exception:
            pass
    return result
