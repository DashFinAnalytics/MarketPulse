"""
Unified trend signal engine.
Computes direction (UP/DOWN/NEUTRAL) and strength score (0-100)
for any yfinance-compatible symbol over configurable timeframes.
"""
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import logging

logger = logging.getLogger(__name__)

TIMEFRAME_DAYS = {
    'Short  (1 week)':  5,
    'Medium (1 month)': 21,
    'Long   (3 months)':63,
    'Extended (6 months)': 126,
}


@st.cache_data(ttl=600)
def compute_trend_signal(_symbol: str, lookback_days: int = 21) -> dict:
    """
    Compute trend direction and strength for a symbol.

    Returns:
        direction:  'UP' | 'DOWN' | 'NEUTRAL'
        strength:   0-100 (100 = very strong trend)
        score:      raw composite -100 to +100
        rsi:        current RSI(14)
        above_sma20: bool
        above_sma50: bool
        above_sma200: bool
        macd_positive: bool
        momentum_pct: % return over lookback
        emoji:  🟢 / 🔴 / ⚪
    """
    try:
        period = '1y'   # always fetch enough history for 200-day SMA
        t = yf.Ticker(_symbol)
        h = t.history(period=period, auto_adjust=True)
        if h.empty or len(h) < 30:
            return _neutral(_symbol)

        close = h['Close']

        # ── Moving averages ──────────────────────────────────
        sma20  = close.rolling(20).mean()
        sma50  = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        ema20  = close.ewm(span=20, adjust=False).mean()

        last     = float(close.iloc[-1])
        s20      = float(sma20.iloc[-1])  if not pd.isna(sma20.iloc[-1])  else last
        s50      = float(sma50.iloc[-1])  if not pd.isna(sma50.iloc[-1])  else last
        s200     = float(sma200.iloc[-1]) if not pd.isna(sma200.iloc[-1]) else last


        above_sma20  = last > s20
        above_sma50  = last > s50
        above_sma200 = last > s200
        sma20_above_sma50  = s20 > s50
        sma50_above_sma200 = s50 > s200 if not pd.isna(sma200.iloc[-1]) else None

        # ── RSI ──────────────────────────────────────────────
        delta = close.diff()
        gain  = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
        loss  = (-delta).clip(lower=0).ewm(com=13, adjust=False).mean()
        rs    = gain / loss.replace(0, np.nan)
        rsi   = float((100 - 100 / (1 + rs)).iloc[-1])

        # ── MACD ─────────────────────────────────────────────
        ema12  = close.ewm(span=12, adjust=False).mean()
        ema26  = close.ewm(span=26, adjust=False).mean()
        macd   = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_positive  = float(macd.iloc[-1])  > 0
        macd_above_sig = float(macd.iloc[-1])  > float(signal.iloc[-1])

        # ── Momentum (% return over lookback) ────────────────
        lookback = min(lookback_days, len(close) - 1)
        momentum_pct = float((last / float(close.iloc[-lookback]) - 1) * 100)

        # ── Composite score (–100 to +100) ───────────────────
        score = 0
        score += 20 if above_sma20  else -20
        score += 20 if above_sma50  else -20
        score += 15 if above_sma200 else -15
        score += 10 if sma20_above_sma50 else -10
        if sma50_above_sma200 is not None:
            score += 10 if sma50_above_sma200 else -10
        score += 15 if macd_positive  else -15
        score += 10 if macd_above_sig else -10
        # RSI contribution
        if rsi > 60:
            score += 10
        elif rsi < 40:
            score -= 10

        # ── Direction & strength ─────────────────────────────
        if score >= 30:
            direction = 'UP'
            emoji     = '🟢'
        elif score <= -30:
            direction = 'DOWN'
            emoji     = '🔴'
        else:
            direction = 'NEUTRAL'
            emoji     = '⚪'

        strength = min(100, abs(score))

        return {
            'symbol':          _symbol,
            'direction':       direction,
            'strength':        strength,
            'score':           score,
            'emoji':           emoji,
            'rsi':             round(rsi, 1),
            'momentum_pct':    round(momentum_pct, 2),
            'above_sma20':     above_sma20,
            'above_sma50':     above_sma50,
            'above_sma200':    above_sma200,
            'macd_positive':   macd_positive,
            'macd_above_sig':  macd_above_sig,
            'last_price':      round(last, 4),
            'sma20':           round(s20, 4),
            'sma50':           round(s50, 4),
        }
    except Exception as e:
        logger.error(f"Trend signal error for {_symbol}: {e}")
        return _neutral(_symbol)


def _neutral(symbol):
    return {
        'symbol': symbol, 'direction': 'NEUTRAL', 'strength': 0,
        'score': 0, 'emoji': '⚪', 'rsi': 50, 'momentum_pct': 0,
        'above_sma20': None, 'above_sma50': None, 'above_sma200': None,
        'macd_positive': None, 'macd_above_sig': None,
        'last_price': 0, 'sma20': 0, 'sma50': 0
    }


def batch_trend_signals(symbols: list, lookback_days: int = 21) -> list:
    """Compute trend signals for a list of symbols."""
    results = []
    for sym in symbols:
        sig = compute_trend_signal(sym, lookback_days)
        results.append(sig)
    return results
