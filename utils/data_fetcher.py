import logging
from typing import Any, cast

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from numpy.typing import NDArray

from database import db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self):
        self.cache_duration = 300

    @st.cache_data(ttl=300)
    def _fetch_ticker_data(_self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="2d")
            if hist.empty:
                return None
            current_price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
            return {
                "symbol": symbol,
                "price": float(current_price),
                "change": float(change),
                "change_pct": float(change_pct),
                "volume": float(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0,
                "info": info,
            }
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def get_indices_data(self, symbols):
        indices_data = {}
        for symbol in symbols:
            data = self._fetch_ticker_data(symbol)
            if data:
                indices_data[symbol] = data
                try:
                    db_manager.store_financial_data(symbol, data, "index")
                except Exception as e:
                    logger.warning(f"Failed to store data for {symbol}: {str(e)}")
        return indices_data

    def get_commodities_data(self, symbols):
        commodities_data = {}
        for symbol in symbols:
            data = self._fetch_ticker_data(symbol)
            if data:
                commodities_data[symbol] = data
                try:
                    db_manager.store_financial_data(symbol, data, "commodity")
                except Exception as e:
                    logger.warning(f"Failed to store data for {symbol}: {str(e)}")
        return commodities_data

    def get_bond_data(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            current_yield = hist["Close"].iloc[-1]
            prev_yield = hist["Close"].iloc[-2] if len(hist) > 1 else current_yield
            change = current_yield - prev_yield
            return {"symbol": symbol, "price": float(current_yield), "change": float(change)}
        except Exception as e:
            logger.error(f"Error fetching bond data for {symbol}: {str(e)}")
            return None

    @st.cache_data(ttl=1800)
    def get_bond_yields(_self):
        """Fetch full US Treasury yield curve data"""
        symbols = {"3M": "^IRX", "5Y": "^FVX", "10Y": "^TNX", "30Y": "^TYX"}
        yields = {}
        for label, symbol in symbols.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if not hist.empty:
                    val = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else val
                    yields[label] = {"yield": val, "change": val - prev, "symbol": symbol}
            except Exception as e:
                logger.warning(f"Failed to fetch {label} yield: {str(e)}")
        return yields

    def get_vix_data(self):
        data = self._fetch_ticker_data("^VIX")
        if data:
            try:
                db_manager.store_financial_data("^VIX", data, "vix")
            except Exception as e:
                logger.warning(f"Failed to store VIX data: {str(e)}")
        return data

    def get_sector_etfs(self, symbols):
        sector_data = {}
        for symbol in symbols:
            data = self._fetch_ticker_data(symbol)
            if data:
                sector_data[symbol] = data
                try:
                    db_manager.store_financial_data(symbol, data, "sector")
                except Exception as e:
                    logger.warning(f"Failed to store data for {symbol}: {str(e)}")
        return sector_data

    @st.cache_data(ttl=300)
    def get_historical_data(_self, symbol, period="1mo"):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            if hist.empty:
                return None
            return hist
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None

    def get_market_summary(self):
        try:
            key_symbols = ["^GSPC", "^IXIC", "^DJI", "^VIX", "GLD", "USO"]
            summary = {}
            for symbol in key_symbols:
                data = self._fetch_ticker_data(symbol)
                if data:
                    summary[symbol] = {"price": data["price"], "change_pct": data["change_pct"]}
            return summary
        except Exception as e:
            logger.error(f"Error getting market summary: {str(e)}")
            return {}

    def get_top_movers(self, symbols, limit=5):
        try:
            movers = []
            for symbol in symbols:
                data = self._fetch_ticker_data(symbol)
                if data:
                    movers.append(
                        {"symbol": symbol, "price": data["price"], "change_pct": data["change_pct"]}
                    )
            movers.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
            return movers[:limit]
        except Exception as e:
            logger.error(f"Error getting top movers: {str(e)}")
            return []

    @st.cache_data(ttl=300)
    def get_forex_data(_self, pairs=None):
        """Fetch Forex / currency pair data"""
        if pairs is None:
            pairs = [
                "EURUSD=X",
                "GBPUSD=X",
                "USDJPY=X",
                "USDCHF=X",
                "AUDUSD=X",
                "USDCAD=X",
                "NZDUSD=X",
                "USDCNY=X",
                "USDINR=X",
                "USDMXN=X",
                "USDBRL=X",
                "USDSGD=X",
            ]
        forex_data = {}
        for pair in pairs:
            data = _self._fetch_ticker_data(pair)
            if data:
                forex_data[pair] = data
        return forex_data

    @st.cache_data(ttl=300)
    def get_futures_data(_self, contracts=None):
        """Fetch futures contracts data"""
        if contracts is None:
            contracts = [
                "ES=F",
                "NQ=F",
                "YM=F",
                "RTY=F",
                "GC=F",
                "SI=F",
                "HG=F",
                "CL=F",
                "NG=F",
                "RB=F",
                "ZB=F",
                "ZN=F",
                "ZT=F",
                "ZC=F",
                "ZW=F",
                "ZS=F",
            ]
        futures_data = {}
        for contract in contracts:
            data = _self._fetch_ticker_data(contract)
            if data:
                futures_data[contract] = data
        return futures_data

    @st.cache_data(ttl=3600)
    def get_options_summary(_self, symbol):
        """Fetch options summary: P/C ratio, total OI, volume, ATM IV"""
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                return None

            total_call_oi = 0
            total_put_oi = 0
            total_call_vol = 0
            total_put_vol = 0

            for exp in expirations[:4]:
                try:
                    chain = ticker.option_chain(exp)
                    calls, puts = chain.calls, chain.puts
                    if not calls.empty:
                        total_call_oi += int(calls["openInterest"].fillna(0).sum())
                        total_call_vol += int(calls["volume"].fillna(0).sum())
                    if not puts.empty:
                        total_put_oi += int(puts["openInterest"].fillna(0).sum())
                        total_put_vol += int(puts["volume"].fillna(0).sum())
                except Exception:
                    continue

            pc_ratio_oi = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else None
            pc_ratio_vol = round(total_put_vol / total_call_vol, 3) if total_call_vol > 0 else None

            info = cast(dict[str, object], ticker.info)

            current_price: float | None = None

            current_price_candidate: Any = info.get("currentPrice", None)
            if current_price_candidate is None:
                current_price_candidate = info.get("regularMarketPrice", None)

            if isinstance(current_price_candidate, (int, float, np.number)):
                current_price = float(current_price_candidate)

            atm_iv = None
            if current_price is not None and expirations:
                try:
                    chain = ticker.option_chain(expirations[0])
                    calls = chain.calls
                    if not calls.empty:
                        idx = (calls["strike"] - current_price).abs().idxmin()
                        iv_val = calls.loc[idx, "impliedVolatility"]
                        atm_iv = round(float(iv_val) * 100, 2) if iv_val else None
                except Exception:
                    pass

            return {
                "symbol": symbol,
                "expirations": list(expirations[:8]),
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "total_call_vol": total_call_vol,
                "total_put_vol": total_put_vol,
                "pc_ratio_oi": pc_ratio_oi,
                "pc_ratio_vol": pc_ratio_vol,
                "atm_iv": atm_iv,
                "next_expiration": expirations[0] if expirations else None,
            }
        except Exception as e:
            logger.error("Error fetching options data for %r: %s", symbol, e)
            return None

    @st.cache_data(ttl=3600)
    def get_option_chain(_self, symbol, expiration=None):
        """Get full option chain for a symbol and expiration"""
        try:
            ticker = yf.Ticker(symbol)
            if not expiration:
                expirations = ticker.options
                if not expirations:
                    return None
                expiration = expirations[0]
            chain = ticker.option_chain(expiration)
            return {"calls": chain.calls, "puts": chain.puts, "expiration": expiration}
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {str(e)}")
            return None

    @st.cache_data(ttl=3600)
    def get_risk_metrics(_self, symbol, benchmark="^GSPC", period="1y"):
        """
        Calculate comprehensive risk metrics: Beta, Sharpe, Sortino,
        VaR, CVaR, Max Drawdown, Alpha.
        """
        try:
            sym_hist = yf.download(symbol, period=period, progress=False, auto_adjust=True)
            bench_hist = yf.download(benchmark, period=period, progress=False, auto_adjust=True)

            if sym_hist.empty or bench_hist.empty:
                return None

            if (
                sym_hist is None
                or bench_hist is None
                or "Close" not in sym_hist.columns
                or "Close" not in bench_hist.columns
            ):
                logger.error(
                    f"Missing 'Close' column in historical data for {symbol} or {benchmark}"
                )
                return None
            sym_close = sym_hist["Close"].squeeze()
            bench_close = bench_hist["Close"].squeeze()

            if not isinstance(sym_close, pd.Series):
                sym_close = pd.Series(sym_close)
            if not isinstance(bench_close, pd.Series):
                bench_close = pd.Series(bench_close)

            sym_returns = sym_close.pct_change().dropna()
            bench_returns = bench_close.pct_change().dropna()

            aligned = pd.concat([sym_returns, bench_returns], axis=1).dropna()
            aligned.columns = ["symbol", "benchmark"]

            if len(aligned) < 30:
                return None

            trading_days = 252
            ann_return = float(aligned["symbol"].mean() * trading_days)
            ann_vol = float(aligned["symbol"].std() * np.sqrt(trading_days))
            risk_free = 0.05

            cov_matrix = aligned.cov()
            raw_cov_val: Any = cov_matrix.loc["symbol", "benchmark"]
            raw_var_val: Any = aligned["benchmark"].var()

            if isinstance(raw_cov_val, np.generic):
                cov_val = float(raw_cov_val.item())
            elif isinstance(raw_cov_val, (int, float, np.number)):
                cov_val = float(raw_cov_val)
            else:
                logger.error(
                    "Covariance value is not numeric: %r (type: %s)",
                    raw_cov_val,
                    type(raw_cov_val),
                )
                return None

            if isinstance(raw_var_val, np.generic):
                var_val = float(raw_var_val.item())
            elif isinstance(raw_var_val, (int, float, np.number)):
                var_val = float(raw_var_val)
            else:
                logger.error(
                    "Variance value is not numeric: %r (type: %s)",
                    raw_var_val,
                    type(raw_var_val),
                )
                return None

            if np.isnan(cov_val) or np.isinf(cov_val):
                logger.error("Invalid covariance value for benchmark: %r", cov_val)
                return None

            if np.isnan(var_val) or np.isinf(var_val) or var_val == 0.0:
                logger.error("Invalid variance value for benchmark: %r", var_val)
                return None

            beta = float(cov_val) / float(var_val)
            alpha = ann_return - (
                risk_free + beta * (float(aligned["benchmark"].mean()) * trading_days - risk_free)
            )

            sharpe = (ann_return - risk_free) / ann_vol if ann_vol else 0
            downside = aligned["symbol"][aligned["symbol"] < 0].std() * np.sqrt(trading_days)
            sortino = (ann_return - risk_free) / float(downside) if downside else 0

            var_95 = float(np.percentile(aligned["symbol"], 5))
            var_99 = float(np.percentile(aligned["symbol"], 1))
            cvar_95 = float(aligned["symbol"][aligned["symbol"] <= var_95].mean())

            cum = (1 + aligned["symbol"]).cumprod()
            roll_max = cum.expanding().max()
            max_dd = float(((cum - roll_max) / roll_max).min())

            calmar = ann_return / abs(max_dd) if max_dd else 0
            corr = float(aligned["symbol"].corr(aligned["benchmark"]))

            rolling_vol = sym_returns.rolling(30).std() * np.sqrt(trading_days)

            return {
                "symbol": symbol,
                "benchmark": benchmark,
                "period": period,
                "beta": round(beta, 3),
                "alpha": round(alpha * 100, 2),
                "sharpe_ratio": round(sharpe, 3),
                "sortino_ratio": round(sortino, 3),
                "calmar_ratio": round(calmar, 3),
                "annual_return": round(ann_return * 100, 2),
                "annual_volatility": round(ann_vol * 100, 2),
                "var_95": round(var_95 * 100, 2),
                "var_99": round(var_99 * 100, 2),
                "cvar_95": round(cvar_95 * 100, 2),
                "max_drawdown": round(max_dd * 100, 2),
                "correlation": round(corr, 3),
                "rolling_vol": rolling_vol,
            }
        except Exception as e:
            logger.error(f"Error calculating risk metrics for {symbol}: {str(e)}")
            return None

    @st.cache_data(ttl=3600)
    def get_earnings_calendar(_self, symbol):
        """Get earnings calendar, history, and analyst recommendations"""
        try:
            ticker = yf.Ticker(symbol)
            result = {"symbol": symbol}

            try:
                result["earnings_dates"] = ticker.earnings_dates
            except Exception:
                result["earnings_dates"] = None

            try:
                result["calendar"] = ticker.calendar
            except Exception:
                result["calendar"] = None

            try:
                result["earnings_history"] = ticker.earnings_history
            except Exception:
                result["earnings_history"] = None

            try:
                recs = ticker.recommendations
                if (
                    recs is not None
                    and hasattr(recs, "empty")
                    and hasattr(recs, "tail")
                    and not recs.empty
                    and isinstance(recs, pd.DataFrame)
                ):
                    result["recommendations"] = recs.tail(15)
                else:
                    result["recommendations"] = None
            except Exception:
                result["recommendations"] = None

            try:
                result["analyst_price_targets"] = ticker.analyst_price_targets
            except Exception:
                result["analyst_price_targets"] = None

            return result
        except Exception as e:
            logger.error(f"Error fetching earnings calendar for {symbol!r}: {e}")
            return None

    @st.cache_data(ttl=3600)
    def get_dividends_splits(_self, symbol):
        """Get dividend and stock split history"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            divs = ticker.dividends
            splits = ticker.splits

            return {
                "symbol": symbol,
                "dividends": divs.tail(20) if divs is not None and not divs.empty else None,
                "splits": splits.tail(10) if splits is not None and not splits.empty else None,
                "dividend_yield": info.get("dividendYield"),
                "ex_dividend_date": info.get("exDividendDate"),
                "payout_ratio": info.get("payoutRatio"),
                "forward_annual_dividend": info.get("dividendRate"),
            }
        except Exception as e:
            logger.error(f"Error fetching dividend data for {symbol}: {str(e)}")
            return None

    @st.cache_data(ttl=300)
    def get_crypto_data(_self, symbols=None):
        """Fetch cryptocurrency price data via yfinance."""
        if symbols is None:
            symbols = [
                "BTC-USD",
                "ETH-USD",
                "BNB-USD",
                "XRP-USD",
                "ADA-USD",
                "SOL-USD",
                "DOGE-USD",
                "MATIC-USD",
                "DOT-USD",
                "AVAX-USD",
                "LINK-USD",
                "UNI7083-USD",
            ]
        crypto_data = {}
        for sym in symbols:
            data = _self._fetch_ticker_data(sym)
            if data:
                crypto_data[sym] = data
        return crypto_data

    @st.cache_data(ttl=1800)
    def get_economic_indicators(_self):
        """
        Fetch macro / economic proxy indicators available via yfinance.
        Returns a list of dicts with label, symbol, price, change, change_pct, category.
        """
        indicators = [
            {"symbol": "DX-Y.NYB", "label": "US Dollar Index (DXY)", "category": "Currency"},
            {"symbol": "TIP", "label": "TIPS ETF (Inflation)", "category": "Inflation"},
            {"symbol": "RINF", "label": "Inflation Expectations ETF", "category": "Inflation"},
            {"symbol": "HYG", "label": "High-Yield Bond ETF", "category": "Credit"},
            {"symbol": "LQD", "label": "Investment-Grade Bond ETF", "category": "Credit"},
            {"symbol": "JNK", "label": "Junk Bond ETF", "category": "Credit"},
            {"symbol": "TLT", "label": "20Y+ Treasury ETF", "category": "Rates"},
            {"symbol": "SHY", "label": "1-3Y Treasury ETF", "category": "Rates"},
            {"symbol": "BIL", "label": "1-3M T-Bill ETF", "category": "Rates"},
            {"symbol": "XLY", "label": "Consumer Discretionary ETF", "category": "Cycle"},
            {"symbol": "XLP", "label": "Consumer Staples ETF", "category": "Cycle"},
            {"symbol": "XLI", "label": "Industrials ETF", "category": "Cycle"},
            {"symbol": "DJP", "label": "Bloomberg Commodity ETN", "category": "Commodities"},
            {"symbol": "PDBC", "label": "Diversified Commodity ETF", "category": "Commodities"},
            {"symbol": "EEM", "label": "Emerging Markets ETF", "category": "Global"},
            {"symbol": "VEA", "label": "Developed Markets ETF", "category": "Global"},
        ]
        results = []
        for ind in indicators:
            data = _self._fetch_ticker_data(ind["symbol"])
            if data:
                results.append(
                    {
                        "symbol": ind["symbol"],
                        "label": ind["label"],
                        "category": ind["category"],
                        "price": data["price"],
                        "change": data["change"],
                        "change_pct": data["change_pct"],
                    }
                )
        return results

    @st.cache_data(ttl=600)
    def get_market_breadth(_self):
        """
        Calculate a market breadth score using sector ETF performance.
        Score 0-100: higher = broader market participation.
        """
        sector_etfs = ["XLK", "XLV", "XLE", "XLF", "XLI", "XLU", "XLB", "XLRE", "XLY", "XLP", "XLC"]
        advancing = 0
        declining = 0
        changes = []
        for sym in sector_etfs:
            data = _self._fetch_ticker_data(sym)
            if data:
                changes.append({"symbol": sym, "change_pct": data["change_pct"]})
                if data["change_pct"] >= 0:
                    advancing += 1
                else:
                    declining += 1

        total = advancing + declining
        if total == 0:
            return None

        score = (advancing / total) * 100
        avg_change = sum(c["change_pct"] for c in changes) / len(changes) if changes else 0

        return {
            "score": round(score, 1),
            "advancing": advancing,
            "declining": declining,
            "total": total,
            "avg_sector_change": round(avg_change, 2),
            "sector_changes": changes,
            "label": (
                "Extreme Fear"
                if score < 20
                else "Fear"
                if score < 40
                else "Neutral"
                if score < 60
                else "Greed"
                if score < 80
                else "Extreme Greed"
            ),
        }

    @st.cache_data(ttl=300)
    def get_top_movers_broad(_self, limit=10):
        """
        Fetch top gainers and losers from a broad watchlist.
        Returns {'gainers': [...], 'losers': [...]}
        """
        symbols = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "NVDA",
            "TSLA",
            "META",
            "BRK-B",
            "JPM",
            "JNJ",
            "V",
            "UNH",
            "XOM",
            "WMT",
            "PG",
            "MA",
            "LLY",
            "HD",
            "ABBV",
            "CVX",
            "BAC",
            "PFE",
            "KO",
            "COST",
            "DIS",
            "NFLX",
            "AMD",
            "INTC",
            "MRK",
            "T",
            "SPY",
            "QQQ",
            "IWM",
            "XLK",
            "XLE",
            "XLF",
            "GLD",
            "SLV",
            "TLT",
            "HYG",
            "BTC-USD",
            "ETH-USD",
            "SOL-USD",
            "EURUSD=X",
            "GBPUSD=X",
            "GC=F",
            "CL=F",
            "ES=F",
            "NQ=F",
            "^VIX",
        ]
        movers = []
        for sym in symbols:
            d = _self._fetch_ticker_data(sym)
            if d:
                movers.append(
                    {
                        "symbol": sym,
                        "price": d["price"],
                        "change": d["change"],
                        "change_pct": d["change_pct"],
                    }
                )
        gainers = sorted(movers, key=lambda x: x["change_pct"], reverse=True)[:limit]
        losers = sorted(movers, key=lambda x: x["change_pct"])[:limit]
        return {"gainers": gainers, "losers": losers}

    @st.cache_data(ttl=3600)
    def get_portfolio_optimization(_self, symbols, period="1y", method="max_sharpe"):
        """
        Mean-variance portfolio optimization using scipy.
        method: 'max_sharpe' | 'min_vol' | 'equal_weight'
        Returns weights list aligned to symbols.
        """
        try:
            import scipy.optimize as sco
            import yfinance as yf

            prices: dict[str, pd.Series[Any]] = {}
            for sym in symbols:
                t = yf.download(sym, period=period, progress=False, auto_adjust=True)
                if t is not None and not t.empty:
                    close_series = t["Close"]
                    if isinstance(close_series, pd.DataFrame):
                        close_series = close_series
                    prices[str(sym)] = cast(pd.Series[Any], close_series)

            if len(prices) < 2:
                return None

            df = pd.DataFrame(prices).dropna()
            rets = df.pct_change().dropna()
            n = len(df.columns)
            valid_syms = [str(col) for col in df.columns]

            mu: NDArray[np.float64] = (
                np.asarray(rets.mean().to_numpy(dtype=float), dtype=float) * 252.0
            )
            sigma: NDArray[np.float64] = (
                np.asarray(rets.cov().to_numpy(dtype=float), dtype=float) * 252.0
            )

            def neg_sharpe(w: NDArray[np.float64]) -> float:
                port_ret = float(np.dot(w, mu))
                port_vol = float(np.sqrt(np.dot(w, np.dot(sigma, w))))
                return -((port_ret - 0.05) / port_vol) if port_vol > 0 else 0.0

            def port_vol(w: NDArray[np.float64]) -> float:
                return float(np.sqrt(np.dot(w, np.dot(sigma, w))))

            bounds = cast(Any, [(0.0, 1.0)] * n)
            constraints = cast(
                Any,
                [{"type": "eq", "fun": lambda w: float(np.sum(np.asarray(w, dtype=float)) - 1.0)}],
            )
            w0: NDArray[np.float64] = np.full(n, 1.0 / n, dtype=float)

            if method == "equal_weight":
                weights = w0.tolist()
            elif method == "min_vol":
                res = sco.minimize(
                    cast(Any, port_vol),
                    w0,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints,
                    options=cast(Any, {"ftol": 1e-9, "maxiter": 1000}),
                )
                weights = np.asarray(res.x, dtype=float).tolist()
            else:
                res = sco.minimize(
                    cast(Any, neg_sharpe),
                    w0,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints,
                    options=cast(Any, {"ftol": 1e-9, "maxiter": 1000}),
                )
                weights = np.asarray(res.x, dtype=float).tolist()

            w: NDArray[np.float64] = np.asarray(weights, dtype=float)
            pr = float(np.dot(w, mu))
            pv = float(np.sqrt(np.dot(w, np.dot(sigma, w))))
            sh = (pr - 0.05) / pv if pv > 0 else 0.0

            target_rets: NDArray[np.float64] = np.linspace(float(mu.min()), float(mu.max()), 40)
            ef_vols: list[float] = []
            ef_rets: list[float] = []
            max_sh_vol: float | None = None
            max_sh_ret: float | None = None
            best_sh = -np.inf

            for tr in target_rets:
                cons = cast(
                    Any,
                    [
                        {
                            "type": "eq",
                            "fun": lambda w, tr=tr: float(
                                np.dot(np.asarray(w, dtype=float), mu) - float(tr)
                            ),
                        },
                        {
                            "type": "eq",
                            "fun": lambda w: float(np.sum(np.asarray(w, dtype=float)) - 1.0),
                        },
                    ],
                )
                r = sco.minimize(
                    cast(Any, port_vol),
                    w0,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=cons,
                    options=cast(Any, {"ftol": 1e-9, "maxiter": 500}),
                )
                if r.success:
                    r_x = np.asarray(r.x, dtype=float)
                    v = float(port_vol(r_x))
                    ef_vols.append(v)
                    ef_rets.append(float(tr))
                    sh_i = (float(tr) - 0.05) / v if v > 0 else -np.inf
                    if sh_i > best_sh:
                        best_sh = sh_i
                        max_sh_vol, max_sh_ret = v, float(tr)

            return {
                "symbols": valid_syms,
                "weights": weights,
                "method": method,
                "port_return": round(pr * 100, 2),
                "port_vol": round(pv * 100, 2),
                "sharpe": round(sh, 3),
                "frontier": {
                    "vols": ef_vols,
                    "rets": ef_rets,
                    "sharpe_vols": max_sh_vol,
                    "sharpe_rets": max_sh_ret,
                },
            }
        except Exception as e:
            logger.error(f"Portfolio optimization error: {e}")
            return None
