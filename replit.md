# Global Finance Dashboard

## Overview

A comprehensive Streamlit-based financial dashboard with real-time market data, technical analysis, risk management, crypto, forex, futures, options, and AI-powered fundamental analysis.

## System Architecture

**Frontend**: 15-page Streamlit application with interactive Plotly charts and real-time data.

Pages:
1. **Live Dashboard** — Global indices, commodities, bonds, VIX gauge, yield curve, sector ETFs, correlation heatmap, market breadth
2. **Historical Data** — Price charts for all instrument types with multiple time intervals
3. **Technical Analysis** — RSI, MACD, Bollinger Bands, SMAs, EMA with multi-panel charts
4. **Fundamental Analysis** — AI-powered valuation (GPT-5), earnings history, financial statements
5. **Forex & Currencies** — 12 currency pairs, rate table, price charts
6. **Futures** — Equity index, metals, energy, bond, agricultural futures
7. **Options Flow** — P/C ratio, IV smile, OI charts, full option chain
8. **Risk Analysis** — Beta, Alpha, Sharpe, Sortino, Calmar, VaR, CVaR, Max Drawdown, custom correlation matrix
9. **Earnings & Events** — Earnings calendar, analyst recommendations, dividends, splits, price targets
10. **Crypto Markets** — BTC, ETH, 15+ coins with TA charts
11. **Economic Indicators** — Macro proxies (dollar, credit spreads, inflation ETFs, cycle indicators)
12. **Market Alerts** — Database-backed price alerts for all instrument types
13. **News** — RSS feeds from major financial sources with symbol/sector search
14. **Portfolio** — Holdings tracker with allocation pie, performance chart, buy/sell/transaction history
15. **Database Stats** — Storage metrics and management

**Backend**: Python data layer
- `utils/data_fetcher.py` — All market data: indices, forex, futures, options, crypto, risk metrics, earnings, economic indicators, market breadth
- `utils/charts.py` — All chart types: candlestick, technical analysis (RSI/MACD/BB), correlation heatmap, yield curve, VIX gauge, risk charts, options OI/IV, forex bar, futures comparison, portfolio allocation/performance, crypto, breadth gauge, economic bar
- `utils/fundamentals.py` — Financial statements via yfinance
- `utils/ai_valuation.py` — OpenAI GPT-5 valuation analysis
- `utils/news_fetcher.py` — RSS news aggregation
- `utils/intervals.py` — Standard finance time intervals
- `database.py` — SQLAlchemy PostgreSQL ORM (lazy-initialized)
- `page_modules/fundamental_analysis.py` — Fundamental analysis page module

**Database**: PostgreSQL (lazy-initialized, app works without it)
- financial_data, market_alerts, news_articles, portfolios, holdings, transactions

## Port Configuration

**Port 8080** — Port 5000 has a broken detection loop in this Replit environment.
- Workflow: `streamlit run app.py --server.port 8080 --browser.gatherUsageStats false`
- `.streamlit/config.toml` says 5000 but CLI flag overrides it

## Key Chart Types

- Candlestick with OHLCV
- Multi-panel technical analysis (price + BB + SMAs, volume, RSI, MACD)
- Correlation heatmap (RdBu colorscale, -1 to +1)
- US Treasury yield curve (live data, inverted curve warning)
- VIX gauge (0-60, colour-coded zones)
- Market breadth gauge (0-100)
- Options OI bar chart + IV smile
- Drawdown chart (filled area)
- Rolling volatility chart
- Portfolio allocation pie
- Normalised performance line chart
- Economic indicators horizontal bar
- Forex % change bar
- Crypto performance bar

## Changelog

- July 05, 2025. Initial setup with Live Dashboard, Historical Data, Portfolio, News, Market Alerts, Database Stats
- July 05, 2025. Added PostgreSQL database integration
- July 05, 2025. Added news and portfolio tracking
- October 04, 2025. Added Fundamental Analysis with GPT-5 AI valuation
- March 12, 2026. Fixed startup: lazy DB/OpenAI init, port 8080
- March 12, 2026. Added Forex & Currencies, Futures, Options Flow, Risk Analysis, Earnings & Events pages; plugged in yield curve, VIX gauge, and correlation heatmap on Live Dashboard
- March 13, 2026. Added Technical Analysis page (RSI/MACD/BB), Crypto Markets, Economic Indicators, Market Breadth on Live Dashboard; expanded symbol lists across all pages; added Portfolio allocation/performance analytics

## User Preferences

Preferred communication style: Simple, everyday language.
