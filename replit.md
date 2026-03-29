# Global Finance Dashboard

## Overview

A comprehensive 18-page Streamlit financial dashboard with real-time market data, technical analysis, risk management, crypto, forex, futures, options, AI-powered fundamental analysis, trend signals, SEC filings, backtesting, portfolio optimization, and news sentiment scoring.

## System Architecture

**Frontend**: 18-page Streamlit application with interactive Plotly charts and real-time data.

Pages:
1. **Live Dashboard** — Market status badge, scrolling live ticker, global market hours panel, top gainers/losers, global indices, VIX gauge, yield curve, sector ETFs, correlation heatmap, market breadth
2. **Historical Data** — Price charts for all instrument types with multiple time intervals
3. **Technical Analysis** — RSI, MACD, BB, SMAs, EMA multi-panel charts + OHLCV+indicator CSV export
4. **Fundamental Analysis** — AI valuation (GPT-5), earnings history, financial statements
5. **Forex & Currencies** — 12 currency pairs, rate table, price charts
6. **Futures** — Equity index, metals, energy, bond, agricultural futures
7. **Options Flow** — P/C ratio, IV smile, OI charts, full option chain
8. **Risk Analysis** — Beta, Alpha, Sharpe, Sortino, Calmar, VaR, CVaR, Max DD, correlation matrix, CSV export
9. **Earnings & Events** — Earnings calendar, analyst recommendations, dividends, splits, price targets
10. **Crypto Markets** — BTC, ETH, 15+ coins with TA charts
11. **Economic Indicators** — Macro proxies (dollar, credit spreads, inflation ETFs, cycle indicators)
12. **Trend Signals** — Unified trend direction (UP/DOWN/NEUTRAL) + strength score 0-100 across any asset group; multi-indicator composite (SMA/EMA/MACD/RSI/momentum); CSV export
13. **SEC & Insider Activity** — SEC EDGAR filings browser (10-K/10-Q/8-K), insider Form 4 transactions, full-text search; CSV export
14. **Backtesting** — SMA Crossover, RSI Mean Reversion, Bollinger Band strategies; equity curves vs Buy & Hold; trade log; Monte Carlo simulation (500 paths); CSV export
15. **Market Alerts** — Database-backed price alerts for all instrument types
16. **News** — RSS news with TextBlob sentiment scoring, aggregate bullish/bearish/neutral metrics, sentiment filter, article display with per-article polarity
17. **Portfolio** — Holdings tracker, allocation pie, normalised performance, Portfolio Optimizer (mean-variance: max Sharpe / min vol / equal weight), efficient frontier chart, optimal weights CSV export
18. **Database Stats** — Storage metrics and management

**Backend**: Python data layer
- `utils/data_fetcher.py` — Market data, risk metrics, earnings, breadth, top movers, portfolio optimization (scipy mean-variance)
- `utils/charts.py` — All chart types including equity curves, Monte Carlo fan chart, trade distribution, trend signal bar, efficient frontier, optimal weights pie
- `utils/fundamentals.py` — Financial statements via yfinance
- `utils/ai_valuation.py` — OpenAI GPT-5 valuation analysis
- `utils/news_fetcher.py` — RSS news aggregation
- `utils/intervals.py` — Standard finance time intervals
- `utils/market_status.py` — NYSE market open/closed/pre-market/after-hours detection; global market hours (NYSE, LSE, Frankfurt, Tokyo, HK, Sydney)
- `utils/trend_signals.py` — Composite trend scoring (SMA20/50/200, EMA, MACD, RSI, momentum); batch scanning
- `utils/sec_fetcher.py` — SEC EDGAR API: company filings, insider Form 4 transactions, full-text search (no API key required)
- `utils/backtester.py` — SMA crossover, RSI, Bollinger Band, buy-and-hold strategies; Monte Carlo simulation
- `database.py` — SQLAlchemy PostgreSQL ORM (lazy-initialized)
- `page_modules/fundamental_analysis.py` — Fundamental analysis page module

**Database**: PostgreSQL (lazy-initialized, app works without it)
- financial_data, market_alerts, news_articles, portfolios, holdings, transactions

## Port Configuration

**Port 8080** — Port 5000 has a broken detection loop in this Replit environment.
- Workflow: `streamlit run app.py --server.port 8080 --browser.gatherUsageStats false`

## Key Chart Types

- Candlestick + OHLCV, multi-panel TA (RSI/MACD/BB)
- Equity curve (strategy vs benchmark), trade P&L distribution
- Monte Carlo fan chart (P10/median/P90)
- Trend signal bar chart (colour-coded -100 to +100 score)
- Portfolio efficient frontier + optimal weights pie
- Correlation heatmap, yield curve, VIX gauge, market breadth
- Options OI / IV smile, drawdown, rolling volatility
- Portfolio allocation pie, normalised performance, forex/crypto bars

## Changelog

- July 05, 2025. Initial setup
- July 05, 2025. Added PostgreSQL database integration
- July 05, 2025. Added news and portfolio tracking
- October 04, 2025. Added Fundamental Analysis with GPT-5 AI valuation
- March 12, 2026. Fixed startup: lazy DB/OpenAI init, port 8080
- March 12, 2026. Added Forex, Futures, Options, Risk Analysis, Earnings pages
- March 13, 2026. Added Technical Analysis, Crypto, Economic Indicators; portfolio analytics
- March 29, 2026. Added Trend Signals page, SEC & Insider Activity page, Backtesting page, Portfolio Optimizer (mean-variance), news sentiment scoring (TextBlob), Live Dashboard market status banner + scrolling ticker + global hours + top movers, CSV export buttons throughout (TA, Risk, Backtest, Trend Signals, SEC filings, Portfolio weights), data freshness timestamps

## User Preferences

Preferred communication style: Simple, everyday language.
