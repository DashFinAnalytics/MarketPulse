import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import logging
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
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
            return {
                'symbol': symbol,
                'price': float(current_price),
                'change': float(change),
                'change_pct': float(change_pct),
                'volume': float(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                'info': info
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
                    db_manager.store_financial_data(symbol, data, 'index')
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
                    db_manager.store_financial_data(symbol, data, 'commodity')
                except Exception as e:
                    logger.warning(f"Failed to store data for {symbol}: {str(e)}")
        return commodities_data

    def get_bond_data(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            current_yield = hist['Close'].iloc[-1]
            prev_yield = hist['Close'].iloc[-2] if len(hist) > 1 else current_yield
            change = current_yield - prev_yield
            return {'symbol': symbol, 'price': float(current_yield), 'change': float(change)}
        except Exception as e:
            logger.error(f"Error fetching bond data for {symbol}: {str(e)}")
            return None

    @st.cache_data(ttl=1800)
    def get_bond_yields(_self):
        """Fetch full US Treasury yield curve data"""
        symbols = {
            '3M': '^IRX', '5Y': '^FVX',
            '10Y': '^TNX', '30Y': '^TYX'
        }
        yields = {}
        for label, symbol in symbols.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if not hist.empty:
                    val = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[-2]) if len(hist) > 1 else val
                    yields[label] = {'yield': val, 'change': val - prev, 'symbol': symbol}
            except Exception as e:
                logger.warning(f"Failed to fetch {label} yield: {str(e)}")
        return yields

    def get_vix_data(self):
        data = self._fetch_ticker_data('^VIX')
        if data:
            try:
                db_manager.store_financial_data('^VIX', data, 'vix')
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
                    db_manager.store_financial_data(symbol, data, 'sector')
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
            key_symbols = ['^GSPC', '^IXIC', '^DJI', '^VIX', 'GLD', 'USO']
            summary = {}
            for symbol in key_symbols:
                data = self._fetch_ticker_data(symbol)
                if data:
                    summary[symbol] = {'price': data['price'], 'change_pct': data['change_pct']}
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
                    movers.append({'symbol': symbol, 'price': data['price'], 'change_pct': data['change_pct']})
            movers.sort(key=lambda x: abs(x['change_pct']), reverse=True)
            return movers[:limit]
        except Exception as e:
            logger.error(f"Error getting top movers: {str(e)}")
            return []

    @st.cache_data(ttl=300)
    def get_forex_data(_self, pairs=None):
        """Fetch Forex / currency pair data"""
        if pairs is None:
            pairs = [
                'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'USDCHF=X',
                'AUDUSD=X', 'USDCAD=X', 'NZDUSD=X', 'USDCNY=X',
                'USDINR=X', 'USDMXN=X', 'USDBRL=X', 'USDSGD=X'
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
                'ES=F', 'NQ=F', 'YM=F', 'RTY=F',
                'GC=F', 'SI=F', 'HG=F',
                'CL=F', 'NG=F', 'RB=F',
                'ZB=F', 'ZN=F', 'ZT=F',
                'ZC=F', 'ZW=F', 'ZS=F'
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
            total_put_oi  = 0
            total_call_vol = 0
            total_put_vol  = 0

            for exp in expirations[:4]:
                try:
                    chain = ticker.option_chain(exp)
                    calls, puts = chain.calls, chain.puts
                    if not calls.empty:
                        total_call_oi  += int(calls['openInterest'].fillna(0).sum())
                        total_call_vol += int(calls['volume'].fillna(0).sum())
                    if not puts.empty:
                        total_put_oi   += int(puts['openInterest'].fillna(0).sum())
                        total_put_vol  += int(puts['volume'].fillna(0).sum())
                except Exception:
                    continue

            pc_ratio_oi  = round(total_put_oi  / total_call_oi,  3) if total_call_oi  > 0 else None
            pc_ratio_vol = round(total_put_vol / total_call_vol, 3) if total_call_vol > 0 else None

            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            atm_iv = None
            if current_price and expirations:
                try:
                    chain = ticker.option_chain(expirations[0])
                    calls = chain.calls
                    if not calls.empty:
                        idx = (calls['strike'] - current_price).abs().idxmin()
                        iv_val = calls.loc[idx, 'impliedVolatility']
                        atm_iv = round(float(iv_val) * 100, 2) if iv_val else None
                except Exception:
                    pass

            return {
                'symbol': symbol,
                'expirations': list(expirations[:8]),
                'total_call_oi': total_call_oi,
                'total_put_oi':  total_put_oi,
                'total_call_vol': total_call_vol,
                'total_put_vol':  total_put_vol,
                'pc_ratio_oi':  pc_ratio_oi,
                'pc_ratio_vol': pc_ratio_vol,
                'atm_iv': atm_iv,
                'next_expiration': expirations[0] if expirations else None
            }
        except Exception as e:
            logger.error(f"Error fetching options data for {symbol}: {str(e)}")
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
            return {'calls': chain.calls, 'puts': chain.puts, 'expiration': expiration}
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {str(e)}")
            return None

    @st.cache_data(ttl=3600)
    def get_risk_metrics(_self, symbol, benchmark='^GSPC', period='1y'):
        """Calculate comprehensive risk metrics: Beta, Sharpe, Sortino, VaR, CVaR, Max Drawdown, Alpha"""
        try:
            sym_hist   = yf.download(symbol,    period=period, progress=False, auto_adjust=True)
            bench_hist = yf.download(benchmark, period=period, progress=False, auto_adjust=True)

            if sym_hist.empty or bench_hist.empty:
                return None

            sym_close   = sym_hist['Close'].squeeze()
            bench_close = bench_hist['Close'].squeeze()

            sym_returns   = sym_close.pct_change().dropna()
            bench_returns = bench_close.pct_change().dropna()

            aligned = pd.concat([sym_returns, bench_returns], axis=1).dropna()
            aligned.columns = ['symbol', 'benchmark']

            if len(aligned) < 30:
                return None

            trading_days = 252
            ann_return = float(aligned['symbol'].mean() * trading_days)
            ann_vol    = float(aligned['symbol'].std()  * np.sqrt(trading_days))
            risk_free  = 0.05

            cov_matrix = aligned.cov()
            beta  = float(cov_matrix.loc['symbol', 'benchmark'] / aligned['benchmark'].var())
            alpha = ann_return - (risk_free + beta * (float(aligned['benchmark'].mean()) * trading_days - risk_free))

            sharpe  = (ann_return - risk_free) / ann_vol if ann_vol else 0
            downside = aligned['symbol'][aligned['symbol'] < 0].std() * np.sqrt(trading_days)
            sortino = (ann_return - risk_free) / float(downside) if downside else 0

            var_95 = float(np.percentile(aligned['symbol'], 5))
            var_99 = float(np.percentile(aligned['symbol'], 1))
            cvar_95 = float(aligned['symbol'][aligned['symbol'] <= var_95].mean())

            cum = (1 + aligned['symbol']).cumprod()
            roll_max = cum.expanding().max()
            max_dd = float(((cum - roll_max) / roll_max).min())

            calmar = ann_return / abs(max_dd) if max_dd else 0
            corr   = float(aligned['symbol'].corr(aligned['benchmark']))

            # Rolling 30-day volatility
            rolling_vol = sym_returns.rolling(30).std() * np.sqrt(trading_days)

            return {
                'symbol': symbol,
                'benchmark': benchmark,
                'period': period,
                'beta': round(beta, 3),
                'alpha': round(alpha * 100, 2),
                'sharpe_ratio': round(sharpe, 3),
                'sortino_ratio': round(sortino, 3),
                'calmar_ratio': round(calmar, 3),
                'annual_return': round(ann_return * 100, 2),
                'annual_volatility': round(ann_vol * 100, 2),
                'var_95': round(var_95 * 100, 2),
                'var_99': round(var_99 * 100, 2),
                'cvar_95': round(cvar_95 * 100, 2),
                'max_drawdown': round(max_dd * 100, 2),
                'correlation': round(corr, 3),
                'rolling_vol': rolling_vol
            }
        except Exception as e:
            logger.error(f"Error calculating risk metrics for {symbol}: {str(e)}")
            return None

    @st.cache_data(ttl=3600)
    def get_earnings_calendar(_self, symbol):
        """Get earnings calendar, history, and analyst recommendations"""
        try:
            ticker = yf.Ticker(symbol)
            result = {'symbol': symbol}

            try:
                result['earnings_dates'] = ticker.earnings_dates
            except Exception:
                result['earnings_dates'] = None

            try:
                result['calendar'] = ticker.calendar
            except Exception:
                result['calendar'] = None

            try:
                result['earnings_history'] = ticker.earnings_history
            except Exception:
                result['earnings_history'] = None

            try:
                recs = ticker.recommendations
                result['recommendations'] = recs.tail(15) if recs is not None and not recs.empty else None
            except Exception:
                result['recommendations'] = None

            try:
                result['analyst_price_targets'] = ticker.analyst_price_targets
            except Exception:
                result['analyst_price_targets'] = None

            return result
        except Exception as e:
            logger.error(f"Error fetching earnings calendar for {symbol}: {str(e)}")
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
                'symbol': symbol,
                'dividends': divs.tail(20) if divs is not None and not divs.empty else None,
                'splits': splits.tail(10) if splits is not None and not splits.empty else None,
                'dividend_yield': info.get('dividendYield'),
                'ex_dividend_date': info.get('exDividendDate'),
                'payout_ratio': info.get('payoutRatio'),
                'forward_annual_dividend': info.get('dividendRate')
            }
        except Exception as e:
            logger.error(f"Error fetching dividend data for {symbol}: {str(e)}")
            return None
