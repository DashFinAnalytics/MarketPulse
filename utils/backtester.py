"""
Simple strategy backtester — SMA crossover, RSI mean-reversion, BB breakout.
No external library required beyond pandas and numpy.
"""

import logging

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _fetch(symbol: str, period: str = "2y") -> pd.DataFrame:
    try:
        t = yf.Ticker(symbol)
        h = t.history(period=period, auto_adjust=True)
        if h.empty:
            return pd.DataFrame()
        return h
    except Exception as e:
        logger.error(f"Backtester fetch error for {symbol}: {e}")
        return pd.DataFrame()


def run_sma_crossover(
    symbol: str,
    period: str = "2y",
    fast: int = 20,
    slow: int = 50,
    initial_capital: float = 10_000,
    position_size_pct: float = 100,
) -> dict:
    """
    Buy when fast SMA crosses above slow SMA; sell on cross below.
    """
    df = _fetch(symbol, period)
    if df.empty or len(df) < slow + 5:
        return {"error": "Insufficient data"}

    close = df["Close"].copy()
    df["fast"] = close.rolling(fast).mean()
    df["slow"] = close.rolling(slow).mean()
    df = df.dropna()

    signal = (df["fast"] > df["slow"]).astype(int)
    df["signal"] = signal.diff().fillna(0)

    capital = initial_capital
    shares = 0.0
    in_trade = False
    entry_px = 0.0
    trades = []
    equity = [capital]

    for idx, row in df.iterrows():
        px = row["Close"]
        if row["signal"] == 1 and not in_trade:  # BUY
            spend = capital * (position_size_pct / 100)
            shares = spend / px
            capital -= spend
            in_trade = True
            entry_px = px
        elif row["signal"] == -1 and in_trade:  # SELL
            proceeds = shares * px
            capital += proceeds
            pnl = proceeds - shares * entry_px
            trades.append(
                {
                    "entry": entry_px,
                    "exit": px,
                    "pnl": pnl,
                    "pnl_pct": (px - entry_px) / entry_px * 100,
                }
            )
            shares = 0.0
            in_trade = False
        equity.append(capital + shares * px)

    # Close open position at last price
    if in_trade:
        last_px = df["Close"].iloc[-1]
        proceeds = shares * last_px
        capital += proceeds
        trades.append(
            {
                "entry": entry_px,
                "exit": last_px,
                "pnl": proceeds - shares * entry_px,
                "pnl_pct": (last_px - entry_px) / entry_px * 100,
            }
        )

    return _stats(trades, equity, initial_capital, df, f"SMA Crossover ({fast}/{slow})", symbol)


def run_rsi_strategy(
    symbol: str,
    period: str = "2y",
    rsi_period: int = 14,
    oversold: float = 30,
    overbought: float = 70,
    initial_capital: float = 10_000,
    position_size_pct: float = 100,
) -> dict:
    """
    Buy when RSI crosses above oversold; sell when crosses above overbought.
    """
    df = _fetch(symbol, period)
    if df.empty or len(df) < rsi_period + 5:
        return {"error": "Insufficient data"}

    close = df["Close"].copy()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=rsi_period - 1, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(com=rsi_period - 1, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
    df = df.dropna()

    capital = initial_capital
    shares = 0.0
    in_trade = False
    entry_px = 0.0
    trades = []
    equity = [capital]
    prev_rsi = None

    for _, row in df.iterrows():
        px = row["Close"]
        rsi = row["rsi"]
        if prev_rsi is not None:
            if prev_rsi < oversold and rsi >= oversold and not in_trade:
                spend = capital * (position_size_pct / 100)
                shares = spend / px
                capital -= spend
                in_trade = True
                entry_px = px
            elif prev_rsi < overbought and rsi >= overbought and in_trade:
                proceeds = shares * px
                capital += proceeds
                trades.append(
                    {
                        "entry": entry_px,
                        "exit": px,
                        "pnl": proceeds - shares * entry_px,
                        "pnl_pct": (px - entry_px) / entry_px * 100,
                    }
                )
                shares = 0.0
                in_trade = False
        equity.append(capital + shares * px)
        prev_rsi = rsi

    if in_trade:
        last_px = df["Close"].iloc[-1]
        proceeds = shares * last_px
        capital += proceeds
        trades.append(
            {
                "entry": entry_px,
                "exit": last_px,
                "pnl": proceeds - shares * entry_px,
                "pnl_pct": (last_px - entry_px) / entry_px * 100,
            }
        )

    return _stats(trades, equity, initial_capital, df, f"RSI ({rsi_period}) Mean Reversion", symbol)


def run_bollinger_band_strategy(
    symbol: str,
    period: str = "2y",
    bb_period: int = 20,
    std_mult: float = 2.0,
    initial_capital: float = 10_000,
    position_size_pct: float = 100,
) -> dict:
    """
    Buy when price touches lower band; sell when it touches upper band.
    """
    df = _fetch(symbol, period)
    if df.empty or len(df) < bb_period + 5:
        return {"error": "Insufficient data"}

    close = df["Close"].copy()
    df["sma"] = close.rolling(bb_period).mean()
    df["std"] = close.rolling(bb_period).std()
    df["upper"] = df["sma"] + std_mult * df["std"]
    df["lower"] = df["sma"] - std_mult * df["std"]
    df = df.dropna()

    capital = initial_capital
    shares = 0.0
    in_trade = False
    entry_px = 0.0
    trades = []
    equity = [capital]

    for _, row in df.iterrows():
        px = row["Close"]
        if px <= row["lower"] and not in_trade:
            spend = capital * (position_size_pct / 100)
            shares = spend / px
            capital -= spend
            in_trade = True
            entry_px = px
        elif px >= row["upper"] and in_trade:
            proceeds = shares * px
            capital += proceeds
            trades.append(
                {
                    "entry": entry_px,
                    "exit": px,
                    "pnl": proceeds - shares * entry_px,
                    "pnl_pct": (px - entry_px) / entry_px * 100,
                }
            )
            shares = 0.0
            in_trade = False
        equity.append(capital + shares * px)

    if in_trade:
        last_px = df["Close"].iloc[-1]
        proceeds = shares * last_px
        capital += proceeds
        trades.append(
            {
                "entry": entry_px,
                "exit": last_px,
                "pnl": proceeds - shares * entry_px,
                "pnl_pct": (last_px - entry_px) / entry_px * 100,
            }
        )

    return _stats(
        trades, equity, initial_capital, df, f"Bollinger Bands ({bb_period}, {std_mult}σ)", symbol
    )


def run_buy_and_hold(symbol: str, period: str = "2y", initial_capital: float = 10_000) -> dict:
    """Benchmark: buy-and-hold from start to end."""
    df = _fetch(symbol, period)
    if df.empty:
        return {"error": "Insufficient data"}
    start_px = df["Close"].iloc[0]
    end_px = df["Close"].iloc[-1]
    shares = initial_capital / start_px
    final = shares * end_px
    total_return = (final - initial_capital) / initial_capital * 100
    n_days = len(df)
    ann_ret = ((final / initial_capital) ** (252 / n_days) - 1) * 100 if n_days > 0 else 0
    prices = df["Close"]
    rets = prices.pct_change().dropna()
    vol = float(rets.std() * np.sqrt(252) * 100)
    cum = (1 + rets).cumprod()
    roll_max = cum.expanding().max()
    mdd = float(((cum - roll_max) / roll_max).min() * 100)
    sharpe = (ann_ret / 100 - 0.05) / (vol / 100) if vol else 0
    return {
        "strategy": f"Buy & Hold {symbol}",
        "symbol": symbol,
        "total_return": round(total_return, 2),
        "annual_return": round(ann_ret, 2),
        "volatility": round(vol, 2),
        "max_drawdown": round(mdd, 2),
        "sharpe_ratio": round(sharpe, 3),
        "final_capital": round(final, 2),
        "num_trades": 1,
        "win_rate": 100.0 if total_return > 0 else 0.0,
        "avg_pnl_pct": round(total_return, 2),
        "equity_curve": [initial_capital] + list(shares * df["Close"].values),
        "trade_log": [],
    }


def _stats(trades, equity, initial_capital, df, strategy_name, symbol):
    final_capital = equity[-1] if equity else initial_capital
    total_return = (final_capital - initial_capital) / initial_capital * 100
    n_days = len(df)
    ann_ret = ((final_capital / initial_capital) ** (252 / n_days) - 1) * 100 if n_days > 1 else 0

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_loss = np.mean([t["pnl_pct"] for t in losses]) if losses else 0
    profit_factor = (
        (sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses)))
        if losses
        else float("inf")
    )

    eq_series = pd.Series(equity)
    rets = eq_series.pct_change().dropna()
    vol = float(rets.std() * np.sqrt(252) * 100) if len(rets) > 1 else 0
    roll_max = eq_series.expanding().max()
    mdd = float(((eq_series - roll_max) / roll_max).min() * 100)
    sharpe = (ann_ret / 100 - 0.05) / (vol / 100) if vol else 0

    return {
        "strategy": strategy_name,
        "symbol": symbol,
        "total_return": round(total_return, 2),
        "annual_return": round(ann_ret, 2),
        "volatility": round(vol, 2),
        "max_drawdown": round(mdd, 2),
        "sharpe_ratio": round(sharpe, 3),
        "profit_factor": round(profit_factor, 3) if profit_factor != float("inf") else 999,
        "final_capital": round(final_capital, 2),
        "num_trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "equity_curve": equity,
        "trade_log": trades,
    }


def run_monte_carlo(returns_series, initial_capital=10_000, n_simulations=500, n_days=252):
    """
    Monte Carlo simulation of equity paths from a returns distribution.
    Returns percentile stats.
    """
    try:
        mu = float(returns_series.mean())
        sigma = float(returns_series.std())
        paths = np.zeros((n_simulations, n_days + 1))
        paths[:, 0] = initial_capital
        daily_rets = np.random.normal(mu, sigma, (n_simulations, n_days))
        for d in range(1, n_days + 1):
            paths[:, d] = paths[:, d - 1] * (1 + daily_rets[:, d - 1])
        final_vals = paths[:, -1]
        return {
            "median": round(float(np.median(final_vals)), 2),
            "p10": round(float(np.percentile(final_vals, 10)), 2),
            "p25": round(float(np.percentile(final_vals, 25)), 2),
            "p75": round(float(np.percentile(final_vals, 75)), 2),
            "p90": round(float(np.percentile(final_vals, 90)), 2),
            "prob_profit": round(float(np.mean(final_vals > initial_capital) * 100), 1),
            "paths": paths,
        }
    except Exception as e:
        logger.error(f"Monte Carlo error: {e}")
        return None
