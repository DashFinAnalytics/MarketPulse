# Roadmap

This document details the full phased feature roadmap for MarketPulse. The roadmap is organized by functional domain within each phase.

> Features marked _(advanced module)_ are planned but lower priority within their phase.

---

## Table of Contents

- [Phase 1 — Core Market & Portfolio MVP](#phase-1--core-market--portfolio-mvp)
- [Phase 2 — Intelligence Layer](#phase-2--intelligence-layer)
- [Phase 3 — Advanced Analytics](#phase-3--advanced-analytics)
- [Phase 4 — Enterprise Expansion](#phase-4--enterprise-expansion)
- [Full Feature Reference](#full-feature-reference)

---

## Phase 1 — Core Market & Portfolio MVP

**Goal:** Deliver a functional market dashboard and basic portfolio tracking as the foundation for all subsequent phases.

### Market Dashboard

- [ ] Live overview of major indices (US, Europe, Asia)
- [ ] Market open/closed status by exchange
- [ ] Intraday price and percentage changes
- [ ] Volatility indicators (VIX and equivalents)
- [ ] Advance/decline breadth indicators
- [ ] Market sentiment composite score
- [ ] Top gainers and losers
- [ ] Most active securities

### Instrument Detail Page

- [ ] Interactive OHLC chart (candlestick and line)
- [ ] Volume overlay
- [ ] Moving averages
- [ ] RSI
- [ ] MACD
- [ ] Bollinger Bands
- [ ] Multi-timeframe switching
- [ ] Indicator value panel

### Portfolio Tracking

- [ ] Holdings view
- [ ] Transaction history
- [ ] Realized and unrealized P&L
- [ ] Dividend tracking
- [ ] Multi-currency support

### Fundamentals Explorer

- [ ] Valuation ratios
- [ ] Profitability metrics
- [ ] Financial health ratios
- [ ] Capital structure metrics
- [ ] Dividend metrics
- [ ] Growth metrics
- [ ] Risk metrics (beta, volatility, drawdown)

### Basic Alerts

- [ ] Price alerts
- [ ] Alert notification delivery

---

## Phase 2 — Intelligence Layer

**Goal:** Add event-driven intelligence, news sentiment, and enhanced risk analytics.

### Economic Calendar

- [ ] Global macro events
- [ ] Importance levels
- [ ] Country and category filters
- [ ] Actual vs forecast vs prior
- [ ] Surprise calculation

### News Sentiment

- [ ] Multi-source news aggregation
- [ ] Deduplication and clustering
- [ ] Symbol and topic tagging
- [ ] Sentiment scoring (NLP model-based)
- [ ] Relevance ranking

### Macro Interpretation Layer

- [ ] Plain-language event impact summaries
- [ ] Cross-asset reaction analysis
- [ ] AI-generated contextual commentary
- [ ] Regime change detection

### Trend Signal Engine

- [ ] Cross-asset trend classification (Up / Down / Neutral)
- [ ] Multi-timeframe configurable
- [ ] Trend strength scoring
- [ ] Confidence metric
- [ ] Single global timeframe control
- [ ] Signal API for reuse across modules

### Advanced Risk Analytics

- [ ] Volatility
- [ ] Sharpe ratio
- [ ] Sortino ratio
- [ ] Maximum drawdown
- [ ] Downside deviation
- [ ] Value at Risk (VaR)
- [ ] Conditional VaR (CVaR)
- [ ] Correlation matrix
- [ ] Factor exposure
- [ ] Sector and geographic concentration

### Earnings Intelligence

- [ ] Earnings calendar with date/symbol/sector/market-cap filters
- [ ] EPS actual vs estimate
- [ ] Surprise percentage
- [ ] Revenue surprise
- [ ] Historical surprise trends

### Regulatory Intelligence

- [ ] SEC filings (10-K, 10-Q, 8-K, proxy)
- [ ] Metadata indexing and filing summaries
- [ ] Insider transactions (buy/sell direction, value, role)
- [ ] Aggregated insider sentiment indicator

### Alerts (Extended)

- [ ] Economic event alerts
- [ ] Earnings alerts

---

## Phase 3 — Advanced Analytics

**Goal:** Deliver professional-grade backtesting, portfolio optimization, and comprehensive reporting.

### Strategy Backtesting

- [ ] Entry/exit rule definition
- [ ] Indicator-based conditions
- [ ] Multi-asset testing
- [ ] Stop-loss, take-profit, trailing stops
- [ ] Position sizing models
- [ ] Monte Carlo simulation
- [ ] Stress testing
- [ ] Benchmark comparison
- [ ] Attribution analysis

### Portfolio Optimization & Rebalancing

- [ ] Mean-variance optimization
- [ ] Risk parity option
- [ ] Target volatility portfolio construction
- [ ] Rebalancing recommendations

### Multi-Company Comparison

- [ ] Side-by-side metrics
- [ ] Relative valuation view
- [ ] Normalized financial comparison
- [ ] Peer benchmarking

### Reporting & Exporting

- [ ] CSV export
- [ ] Excel workbook export
- [ ] PDF reporting
- [ ] Portfolio reports
- [ ] Performance reports
- [ ] Scheduled report distribution
- [ ] Compliance-oriented templates

### Export Automation

- [ ] Scheduled report generation
- [ ] Report delivery via email/webhook

---

## Phase 4 — Enterprise Expansion

**Goal:** Add team collaboration, enterprise governance, compliance controls, and workspace features.

### Team Workspaces

- [ ] Team workspace creation and management
- [ ] Shared dashboards
- [ ] Shared portfolios
- [ ] Role-based permissions (RBAC)
- [ ] Approval workflows
- [ ] Threaded comments
- [ ] Mentions
- [ ] Team usage analytics

### Governance & Compliance

- [ ] Multi-factor authentication (TOTP)
- [ ] Encryption in transit and at rest
- [ ] Audit trail
- [ ] Activity logging
- [ ] Policy acknowledgment tracking
- [ ] Multi-jurisdiction compliance readiness

### Custom Dashboard Builder

- [ ] Drag-and-drop widget layout
- [ ] Saved layouts
- [ ] Role-based templates
- [ ] Cross-device responsiveness
- [ ] Widget library (charts, heatmaps, tables, metrics, news blocks)

### Mobile & Offline

- [ ] Progressive Web App (PWA)
- [ ] Installable mobile experience
- [ ] Offline mode with cached data
- [ ] Background sync

### Advanced Permissions

- [ ] Fine-grained resource-level permissions
- [ ] External integrator API keys

---

## Full Feature Reference

### Market Overview & Monitoring

#### Global Market Dashboard

- Live overview of major indices (US, Europe, Asia)
- Market open/closed status by exchange
- Intraday price and percentage changes
- Volatility indicators (VIX and equivalents)
- Advance/decline breadth indicators
- Market sentiment composite score

#### Live Ticker Tape

- Configurable scrolling ticker
- Watchlist-based ticker option
- Color-coded performance indicators

#### Top Movers

- Top gainers and losers
- Most active securities
- Volume anomalies
- Breakout detection _(advanced module)_

#### Sector Performance

- Heatmap visualization
- Sector rotation tracking
- Relative strength vs index
- Multi-timeframe comparison

---

### Multi-Asset Terminal Views

#### Equities & Indices

- Regional performance heatmaps
- Index constituents drilldown
- Cross-index comparison
- Market capitalization segmentation

#### Volatility

- VIX term structure
- Historical volatility comparison
- Implied vs realized spread

#### Rates & Bonds

- US Treasury yield curve (full maturity range)
- Global 10-year sovereign yields
- Yield curve spread analysis (2s10s, 3m10y, etc.)
- Historical yield regime view

#### Foreign Exchange

- Major currency pairs
- Trade-weighted indices
- Trend direction and volatility regime
- Relative currency strength model

#### Commodities

- Precious metals
- Energy markets
- Industrial metals
- Agricultural benchmarks
- Futures term structure view _(advanced module)_

---

### Real-Time & Reliability Framework

- Data freshness indicators
- Live vs cached distinction
- Fallback data providers
- Graceful degradation
- Background refresh jobs
- Observability and alerting
