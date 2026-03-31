from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from config import config
from database import db_manager
from utils.exceptions import ValidationError
from utils.logging_config import get_logger, log_api_call, log_execution_time

logger = get_logger(__name__)


class DataFetcher:
    def __init__(self) -> None:
        """Initialize the DataFetcher.

        Reads configuration for Yahoo Finance retry behavior.
        """
        self.retry_attempts = config.api.yfinance_retry_attempts

    def _validate_symbol(self, symbol: str) -> str:
        if not symbol or not isinstance(symbol, str):
            raise ValidationError("Symbol must be a non-empty string")
    
        normalized = symbol.strip().upper()
    
        # More permissive validation for financial symbols
        # Allow common financial symbol patterns
        if not normalized or normalized.isspace():
            raise ValidationError(f"Symbol cannot be empty or whitespace: {symbol}")
    
        # Basic sanity check - symbols shouldn't be excessively long
        if len(normalized) > 50:
            raise ValidationError(f"Symbol too long: {symbol}")
    
        return normalized

    def _sleep_before_retry(self, attempt: int) -> None:
        time.sleep(min(2**attempt, 4))

    def _store_data_if_possible(
        self,
        symbol: str,
        data: Optional[Dict[str, Any]],
        data_type: str,
    ) -> None:
        if not data:
            return
        try:
            db_manager.store_financial_data(symbol, data, data_type)
        except Exception as exc:
            logger.warning(
                "Failed to persist fetched data",
                symbol=symbol,
                data_type=data_type,
                error=str(exc),
            )

    def _download_history(self, symbol: str, period: str) -> pd.DataFrame:
        symbol = self._validate_symbol(symbol)
        for attempt in range(max(1, self.retry_attempts)):
            try:
                ticker = yf.Ticker(symbol)
                history = ticker.history(period=period)
                return (
                    history if isinstance(history, pd.DataFrame) else pd.DataFrame()
                )
            except Exception as exc:
                logger.warning(
                    "History fetch attempt failed",
                    symbol=symbol,
                    period=period,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt < self.retry_attempts - 1:
                    self._sleep_before_retry(attempt)
        return pd.DataFrame()

    # cached: network only
    @st.cache_data(ttl=config.api.yfinance_cache_ttl_seconds)
    @log_api_call("Yahoo Finance")
    @log_execution_time()
    def _fetch_ticker_data(_self, symbol: str) -> Optional[Dict[str, Any]]:
        symbol = _self._validate_symbol(symbol)
        ...  # existing retry + fetch logic
        return data
    
    # NOT cached: persistence decision happens here
    def fetch_ticker_data(
        self,
        symbol: str,
        *,
        persist: bool = False,
        data_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        data = self._fetch_ticker_data(symbol)
        if persist and data and data_type:
            self._store_data_if_possible(self._validate_symbol(symbol), data, data_type)
        return data

        for attempt in range(max(1, _self.retry_attempts)):
            try:
                ticker = yf.Ticker(symbol)
                history = ticker.history(period="2d")
                if history.empty:
                    logger.warning(
                        "Empty history received from Yahoo Finance",
                        symbol=symbol,
                        period="2d",
                        attempt=attempt + 1,
                    )
                    if attempt < _self.retry_attempts - 1:
                        _self._sleep_before_retry(attempt)
                        continue
                    return None

                try:
                    info = ticker.info or {}
                except Exception:
                    info = {}

                current_price = float(history["Close"].iloc[-1])
                prev_close = (
                    float(history["Close"].iloc[-2])
                    if len(history) > 1
                    else current_price
                )
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close != 0 else 0.0
                volume = (
                    float(history["Volume"].iloc[-1])
                    if "Volume" in history.columns
                    else 0.0
                )

                return {
                    "symbol": symbol,
                    "price": current_price,
                    "change": float(change),
                    "change_pct": float(change_pct),
                    "volume": volume,
                    "info": info,
                }
            except Exception as exc:
                logger.warning(
                    "Ticker fetch attempt failed",
                    symbol=symbol,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt < _self.retry_attempts - 1:
                    _self._sleep_before_retry(attempt)

        logger.error("Ticker fetch failed after retries", symbol=symbol)
        return None

    def _collect_asset_data(
        self,
        symbols: Sequence[str],
        data_type: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        collected: Dict[str, Dict[str, Any]] = {}
        for raw_symbol in symbols:
            try:
                symbol = self._validate_symbol(raw_symbol)
            except ValidationError as exc:
                logger.warning(
                    "Symbol validation failed in _collect_asset_data",
                    symbol=raw_symbol,
                    error=str(exc),
                )
                continue

            data = self._fetch_ticker_data(symbol)
            if not data:
                continue

            collected[symbol] = data
            if data_type:
                self._store_data_if_possible(symbol, data, data_type)
        return collected

    @log_execution_time()
    def get_indices_data(self, symbols: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch quote/summary data for market indices.

        Args:
            symbols: Iterable of Yahoo Finance symbols (e.g. ["^GSPC", "^IXIC"]).

        Returns:
            Mapping of normalized symbol -> ticker data dict containing at least
            price/change/change_pct/volume/info for each successfully fetched symbol.
        """
        return self._collect_asset_data(symbols, "index")

    @log_execution_time()
    def get_commodities_data(
        self,
        symbols: Sequence[str],
    ) -> Dict[str, Dict[str, Any]]:
        return self._collect_asset_data(symbols, "commodity")

    @log_execution_time()
    def get_bond_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch recent bond yield data for a single bond/yield symbol.

        Args:
            symbol: Yahoo Finance symbol (e.g. "^TNX").

        Returns:
            Dict with keys "symbol", "price", and "change" if data is available;
            otherwise None.
        """
        try:
            normalized_symbol = self._validate_symbol(symbol)
        except ValidationError as exc:
            logger.warning(
                "Symbol validation failed",
                symbol=symbol,
                error=str(exc),
            )
            return None

        history = self._download_history(normalized_symbol, "5d")
        if history.empty:
            return None

        current_yield = float(history["Close"].iloc[-1])
        prev_yield = (
            float(history["Close"].iloc[-2])
            if len(history) > 1
            else current_yield
        )
        return {
            "symbol": normalized_symbol,
            "price": current_yield,
            "change": current_yield - prev_yield,
        }

    @st.cache_data(ttl=1800)
    @log_execution_time()
    def get_bond_yields(_self) -> Dict[str, Dict[str, Any]]:
        mapping = {
            "3M": "^IRX",
            "5Y": "^FVX",
            "10Y": "^TNX",
            "30Y": "^TYX",
        }
        yields: Dict[str, Dict[str, Any]] = {}
        for label, symbol in mapping.items():
            history = _self._download_history(symbol, "5d")
            if history.empty:
                continue
            value = float(history["Close"].iloc[-1])
            previous = float(history["Close"].iloc[-2]) if len(history) > 1 else value
            yields[label] = {
                "yield": value,
                "change": value - previous,
                "symbol": symbol,
            }
        return yields

    @log_execution_time()
    def get_vix_data(self) -> Optional[Dict[str, Any]]:
        data = self._fetch_ticker_data("^VIX")
        self._store_data_if_possible("^VIX", data, "vix")
        return data

    @log_execution_time()
    def get_sector_etfs(self, symbols: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        return self._collect_asset_data(symbols, "sector")

    @st.cache_data(ttl=300)
    @log_execution_time()
    def get_historical_data(
        _self,
        symbol: str,
        period: str = "1mo",
    ) -> Optional[pd.DataFrame]:
        history = _self._download_history(symbol, period)
        return None if history.empty else history

    @log_execution_time()
    def get_market_summary(self) -> Dict[str, Dict[str, float]]:
        key_symbols = ["^GSPC", "^IXIC", "^DJI", "^VIX", "GLD", "USO"]
        summary: Dict[str, Dict[str, float]] = {}
        for symbol in key_symbols:
            data = self._fetch_ticker_data(symbol)
            if data:
                summary[symbol] = {
                    "price": data["price"],
                    "change_pct": data["change_pct"],
                }
        return summary

    @log_execution_time()
    def get_top_movers(
        self,
        symbols: Sequence[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        movers: List[Dict[str, Any]] = []
        for symbol in symbols:
            data = self._fetch_ticker_data(symbol)
            if data:
                movers.append(
                    {
                        "symbol": data.get("symbol", symbol),
                        "price": data["price"],
                        "change_pct": data["change_pct"],
                    }
                )
        movers.sort(key=lambda item: abs(item["change_pct"]), reverse=True)
        return movers[:limit]

    @st.cache_data(ttl=300)
    @log_execution_time()
    def get_forex_data(
        _self,
        pairs: Optional[Sequence[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
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
        return _self._collect_asset_data(pairs)

    @st.cache_data(ttl=300)
    @log_execution_time()
    def get_futures_data(
        _self,
        contracts: Optional[Sequence[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
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
        return _self._collect_asset_data(contracts)

    @st.cache_data(ttl=3600)
    @log_execution_time()
    def get_options_summary(_self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            symbol = _self._validate_symbol(symbol)
        except ValidationError as exc:
            logger.warning("Invalid options symbol", symbol=symbol, error=str(exc))
            return None

        for attempt in range(max(1, _self.retry_attempts)):
            try:
                ticker = yf.Ticker(symbol)
                expirations = ticker.options
                if not expirations:
                    return None

                total_call_oi = 0
                total_put_oi = 0
                total_call_vol = 0
                total_put_vol = 0

                for expiration in expirations[:4]:
                    try:
                        chain = ticker.option_chain(expiration)
                        calls = chain.calls
                        puts = chain.puts
                        if not calls.empty:
                            total_call_oi += int(calls["openInterest"].fillna(0).sum())
                            total_call_vol += int(calls["volume"].fillna(0).sum())
                        if not puts.empty:
                            total_put_oi += int(puts["openInterest"].fillna(0).sum())
                            total_put_vol += int(puts["volume"].fillna(0).sum())
                    except Exception as exc:
                        logger.warning(
                            "Failed to parse option chain expiration",
                            symbol=symbol,
                            expiration=expiration,
                            error=str(exc),
                        )

                pc_ratio_oi = (
                    round(total_put_oi / total_call_oi, 3)
                    if total_call_oi > 0
                    else None
                )
                pc_ratio_vol = (
                    round(total_put_vol / total_call_vol, 3)
                    if total_call_vol > 0
                    else None
                )

                try:
                    info = ticker.info or {}
                except Exception:
                    info = {}

                current_price = (
                    info.get("currentPrice") or info.get("regularMarketPrice")
                )
                atm_iv = None
                if current_price and expirations:
                    try:
                        chain = ticker.option_chain(expirations[0])
                        calls = chain.calls
                        if not calls.empty:
                            idx = (calls["strike"] - current_price).abs().idxmin()
                            iv_value = calls.loc[idx, "impliedVolatility"]
                            atm_iv = (
                                round(float(iv_value) * 100, 2)
                                if iv_value
                                else None
                            )
                    except Exception as exc:
                        logger.warning(
                            "Failed to compute ATM IV",
                            symbol=symbol,
                            error=str(exc),
                        )

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
            except Exception as exc:
                logger.warning(
                    "Options summary fetch attempt failed",
                    symbol=symbol,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt < _self.retry_attempts - 1:
                    _self._sleep_before_retry(attempt)
        return None

    @st.cache_data(ttl=3600)
    @log_execution_time()
    def get_option_chain(
        _self,
        symbol: str,
        expiration: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            symbol = _self._validate_symbol(symbol)
        except ValidationError as exc:
            logger.warning(
                "Invalid option chain symbol",
                symbol=symbol,
                error=str(exc),
            )
            return None

        for attempt in range(max(1, _self.retry_attempts)):
            try:
                ticker = yf.Ticker(symbol)
                if not expiration:
                    expirations = ticker.options
                    if not expirations:
                        return None
                    expiration = expirations[0]
                chain = ticker.option_chain(expiration)
                return {
                    "calls": chain.calls,
                    "puts": chain.puts,
                    "expiration": expiration,
                }
            except Exception as exc:
                logger.warning(
                    "Option chain fetch attempt failed",
                    symbol=symbol,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt < _self.retry_attempts - 1:
                    _self._sleep_before_retry(attempt)
        return None

    @st.cache_data(ttl=3600)
    @log_execution_time()
    def get_risk_metrics(
        _self,
        symbol: str,
        benchmark: str = "^GSPC",
        period: str = "1y",
    ) -> Optional[Dict[str, Any]]:
        try:
            symbol = _self._validate_symbol(symbol)
            benchmark = _self._validate_symbol(benchmark)
            symbol_history = yf.download(
                symbol,
                period=period,
                progress=False,
                auto_adjust=True,
            )
            benchmark_history = yf.download(
                benchmark,
                period=period,
                progress=False,
                auto_adjust=True,
            )
            if symbol_history.empty or benchmark_history.empty:
                return None

            symbol_close = symbol_history["Close"].squeeze()
            benchmark_close = benchmark_history["Close"].squeeze()
            symbol_returns = symbol_close.pct_change().dropna()
            benchmark_returns = benchmark_close.pct_change().dropna()
            aligned = pd.concat([symbol_returns, benchmark_returns], axis=1).dropna()
            aligned.columns = ["symbol", "benchmark"]
            if len(aligned) < 30:
                return None

            trading_days = 252
            annual_return = float(aligned["symbol"].mean() * trading_days)
            annual_vol = float(aligned["symbol"].std() * np.sqrt(trading_days))
            risk_free = 0.05
            covariance = aligned.cov()
            beta = float(
                covariance.loc["symbol", "benchmark"]
                / aligned["benchmark"].var()
            )
            alpha = annual_return - (
                risk_free
                + beta
                * (float(aligned["benchmark"].mean()) * trading_days - risk_free)
            )
            sharpe = (annual_return - risk_free) / annual_vol if annual_vol else 0.0
            downside = (
                aligned["symbol"][aligned["symbol"] < 0].std()
                * np.sqrt(trading_days)
            )
            sortino = (
                (annual_return - risk_free) / float(downside)
                if downside
                else 0.0
            )
            var_95 = float(np.percentile(aligned["symbol"], 5))
            var_99 = float(np.percentile(aligned["symbol"], 1))
            cvar_95 = float(aligned["symbol"][aligned["symbol"] <= var_95].mean())
            cumulative = (1 + aligned["symbol"]).cumprod()
            rolling_max = cumulative.expanding().max()
            max_drawdown = float(((cumulative - rolling_max) / rolling_max).min())
            calmar = annual_return / abs(max_drawdown) if max_drawdown else 0.0
            correlation = float(aligned["symbol"].corr(aligned["benchmark"]))
            rolling_vol = symbol_returns.rolling(30).std() * np.sqrt(trading_days)

            return {
                "symbol": symbol,
                "benchmark": benchmark,
                "period": period,
                "beta": round(beta, 3),
                "alpha": round(alpha * 100, 2),
                "sharpe_ratio": round(sharpe, 3),
                "sortino_ratio": round(sortino, 3),
                "calmar_ratio": round(calmar, 3),
                "annual_return": round(annual_return * 100, 2),
                "annual_volatility": round(annual_vol * 100, 2),
                "var_95": round(var_95 * 100, 2),
                "var_99": round(var_99 * 100, 2),
                "cvar_95": round(cvar_95 * 100, 2),
                "max_drawdown": round(max_drawdown * 100, 2),
                "correlation": round(correlation, 3),
                "rolling_vol": rolling_vol,
            }
        except Exception as exc:
            logger.warning(
                "Failed to calculate risk metrics",
                symbol=symbol,
                benchmark=benchmark,
                error=str(exc),
            )
            return None

    @st.cache_data(ttl=3600)
    @log_execution_time()
    def get_earnings_calendar(
        _self,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            symbol = _self._validate_symbol(symbol)
            ticker = yf.Ticker(symbol)
            result: Dict[str, Any] = {"symbol": symbol}
            for key, attr in {
                "earnings_dates": "earnings_dates",
                "calendar": "calendar",
                "earnings_history": "earnings_history",
                "analyst_price_targets": "analyst_price_targets",
            }.items():
                try:
                    result[key] = getattr(ticker, attr)
                except Exception:
                    result[key] = None
            try:
                recommendations = ticker.recommendations
                result["recommendations"] = (
                    recommendations.tail(15)
                    if recommendations is not None and not recommendations.empty
                    else None
                )
            except Exception:
                result["recommendations"] = None
            return result
        except Exception as exc:
            logger.warning(
                "Failed to fetch earnings calendar",
                symbol=symbol,
                error=str(exc),
            )
            return None

    @st.cache_data(ttl=3600)
    @log_execution_time()
    def get_dividends_splits(
        _self,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            symbol = _self._validate_symbol(symbol)
            ticker = yf.Ticker(symbol)
            try:
                info = ticker.info or {}
            except Exception:
                info = {}
            dividends = ticker.dividends
            splits = ticker.splits
            return {
                "symbol": symbol,
                "dividends": dividends.tail(20)
                if dividends is not None and not dividends.empty
                else None,
                "splits": splits.tail(10)
                if splits is not None and not splits.empty
                else None,
                "dividend_yield": info.get("dividendYield"),
                "ex_dividend_date": info.get("exDividendDate"),
                "payout_ratio": info.get("payoutRatio"),
                "forward_annual_dividend": info.get("dividendRate"),
            }
        except Exception as exc:
            logger.warning(
                "Failed to fetch dividends and splits",
                symbol=symbol,
                error=str(exc),
            )
            return None

    @st.cache_data(ttl=300)
    @log_execution_time()
    def get_crypto_data(
        _self,
        symbols: Optional[Sequence[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
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
        return _self._collect_asset_data(symbols)

    @st.cache_data(ttl=1800)
    @log_execution_time()
    def get_economic_indicators(_self) -> List[Dict[str, Any]]:
        indicators = [
            {
                "symbol": "DX-Y.NYB",
                "label": "US Dollar Index (DXY)",
                "category": "Currency",
            },
            {
                "symbol": "TIP",
                "label": "TIPS ETF (Inflation)",
                "category": "Inflation",
            },
            {
                "symbol": "RINF",
                "label": "Inflation Expectations ETF",
                "category": "Inflation",
            },
            {
                "symbol": "HYG",
                "label": "High-Yield Bond ETF",
                "category": "Credit",
            },
            {
                "symbol": "LQD",
                "label": "Investment-Grade Bond ETF",
                "category": "Credit",
            },
            {
                "symbol": "JNK",
                "label": "Junk Bond ETF",
                "category": "Credit",
            },
            {
                "symbol": "TLT",
                "label": "20Y+ Treasury ETF",
                "category": "Rates",
            },
            {
                "symbol": "SHY",
                "label": "1-3Y Treasury ETF",
                "category": "Rates",
            },
            {
                "symbol": "BIL",
                "label": "1-3M T-Bill ETF",
                "category": "Rates",
            },
            {
                "symbol": "XLY",
                "label": "Consumer Discretionary ETF",
                "category": "Cycle",
            },
            {
                "symbol": "XLP",
                "label": "Consumer Staples ETF",
                "category": "Cycle",
            },
            {
                "symbol": "XLI",
                "label": "Industrials ETF",
                "category": "Cycle",
            },
            {
                "symbol": "DJP",
                "label": "Bloomberg Commodity ETN",
                "category": "Commodities",
            },
            {
                "symbol": "PDBC",
                "label": "Diversified Commodity ETF",
                "category": "Commodities",
            },
            {
                "symbol": "EEM",
                "label": "Emerging Markets ETF",
                "category": "Global",
            },
            {
                "symbol": "VEA",
                "label": "Developed Markets ETF",
                "category": "Global",
            },
        ]
        results: List[Dict[str, Any]] = []
        for indicator in indicators:
            data = _self._fetch_ticker_data(indicator["symbol"])
            if not data:
                continue
            results.append(
                {
                    "symbol": indicator["symbol"],
                    "label": indicator["label"],
                    "category": indicator["category"],
                    "price": data["price"],
                    "change": data["change"],
                    "change_pct": data["change_pct"],
                }
            )
        return results

    @st.cache_data(ttl=600)
    @log_execution_time()
    def get_market_breadth(_self) -> Optional[Dict[str, Any]]:
        sector_etfs = [
            "XLK",
            "XLV",
            "XLE",
            "XLF",
            "XLI",
            "XLU",
            "XLB",
            "XLRE",
            "XLY",
            "XLP",
            "XLC",
        ]
        changes: List[Dict[str, Any]] = []
        advancing = 0
        declining = 0
        for symbol in sector_etfs:
            data = _self._fetch_ticker_data(symbol)
            if not data:
                continue
            changes.append({"symbol": symbol, "change_pct": data["change_pct"]})
            if data["change_pct"] >= 0:
                advancing += 1
            else:
                declining += 1
        total = advancing + declining
        if total == 0:
            return None
        score = (advancing / total) * 100
        avg_change = (
            sum(item["change_pct"] for item in changes) / len(changes)
            if changes
            else 0.0
        )
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
    @log_execution_time()
    def get_top_movers_broad(
        _self,
        limit: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
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
        movers: List[Dict[str, Any]] = []
        for symbol in symbols:
            data = _self._fetch_ticker_data(symbol)
            if not data:
                continue
            movers.append(
                {
                    "symbol": symbol,
                    "price": data["price"],
                    "change": data["change"],
                    "change_pct": data["change_pct"],
                }
            )
        gainers = sorted(
            movers,
            key=lambda item: item["change_pct"],
            reverse=True,
        )[:limit]
        losers = sorted(movers, key=lambda item: item["change_pct"])[:limit]
        return {"gainers": gainers, "losers": losers}

    @st.cache_data(ttl=3600)
    @log_execution_time()
    def get_portfolio_optimization(
        _self,
        symbols: Sequence[str],
        period: str = "1y",
        method: str = "max_sharpe",
    ) -> Optional[Dict[str, Any]]:
        try:
            import scipy.optimize as sco

            prices: Dict[str, pd.Series] = {}
            for raw_symbol in symbols:
                try:
                    symbol = _self._validate_symbol(raw_symbol)
                except ValidationError as exc:
                    logger.warning(
                        "Skipping invalid optimization symbol",
                        symbol=raw_symbol,
                        error=str(exc),
                    )
                    continue
                history = yf.download(
                    symbol,
                    period=period,
                    progress=False,
                    auto_adjust=True,
                )
                if history.empty:
                    continue
                prices[symbol] = history["Close"].squeeze()

            if len(prices) < 2:
                return None

            frame = pd.DataFrame(prices).dropna()
            returns = frame.pct_change().dropna()
            valid_symbols = list(frame.columns)
            count = len(valid_symbols)
            mean_returns = returns.mean().values * 252
            covariance = returns.cov().values * 252
            risk_free = 0.05

            def portfolio_volatility(weights: np.ndarray) -> float:
                return float(np.sqrt(np.dot(weights, np.dot(covariance, weights))))

            def negative_sharpe(weights: np.ndarray) -> float:
                portfolio_return = float(np.dot(weights, mean_returns))
                portfolio_vol = portfolio_volatility(weights)
                return (
                    -(portfolio_return - risk_free) / portfolio_vol
                    if portfolio_vol > 0
                    else 1e10  # Large penalty to discourage zero-volatility solutions
                )
            constraints = [{"type": "eq", "fun": lambda weights: np.sum(weights) - 1}]
            bounds = [(0, 1)] * count
            starting_weights = np.array([1 / count] * count)

            if method == "equal_weight":
                weights = starting_weights.tolist()
            elif method == "min_vol":
                result = sco.minimize(
                    portfolio_volatility,
                    starting_weights,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints,
                    options={"ftol": 1e-9, "maxiter": 1000},
                )
                weights = result.x.tolist()
            else:
                result = sco.minimize(
                    negative_sharpe,
                    starting_weights,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints,
                    options={"ftol": 1e-9, "maxiter": 1000},
                )
                weights = result.x.tolist()

            weight_array = np.array(weights)
            portfolio_return = float(np.dot(weight_array, mean_returns))
            portfolio_vol = portfolio_volatility(weight_array)
            sharpe = (
                (portfolio_return - risk_free) / portfolio_vol
                if portfolio_vol > 0
                else 0.0
            )

            target_returns = np.linspace(mean_returns.min(), mean_returns.max(), 40)
            frontier_vols: List[float] = []
            frontier_rets: List[float] = []
            max_sharpe_vol = None
            max_sharpe_ret = None
            best_sharpe = -np.inf

            for target_return in target_returns:
                target_constraints = [
                    {
                        "type": "eq",
                        "fun": lambda weights, tr=target_return: np.dot(weights, mean_returns) - tr,
                    },
                    {"type": "eq", "fun": lambda weights: np.sum(weights) - 1},
                ]
                result = sco.minimize(
                    portfolio_volatility,
                    starting_weights,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=target_constraints,
                    options={"ftol": 1e-9, "maxiter": 500},
                )
                if not result.success:
                    continue
                vol = portfolio_volatility(result.x)
                frontier_vols.append(vol)
                frontier_rets.append(float(target_return))
                frontier_sharpe = (
                    (float(target_return) - risk_free) / vol
                    if vol > 0
                    else -np.inf
                )
                if frontier_sharpe > best_sharpe:
                    best_sharpe = frontier_sharpe
                    max_sharpe_vol = vol
                    max_sharpe_ret = float(target_return)

            return {
                "symbols": valid_symbols,
                "weights": weights,
                "method": method,
                "port_return": round(portfolio_return * 100, 2),
                "port_vol": round(portfolio_vol * 100, 2),
                "sharpe": round(sharpe, 3),
                "frontier": {
                    "vols": frontier_vols,
                    "rets": frontier_rets,
                    "sharpe_vols": max_sharpe_vol,
                    "sharpe_rets": max_sharpe_ret,
                },
            }
        except Exception as exc:
            logger.warning(
                "Portfolio optimization failed",
                method=method,
                error=str(exc),
            )
            return None
