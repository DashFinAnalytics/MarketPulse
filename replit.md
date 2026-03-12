# Global Finance Dashboard

## Overview

This is a Streamlit-based financial dashboard that provides real-time market data visualization and analysis. The application fetches financial data from Yahoo Finance and displays interactive charts and metrics for various financial instruments including stocks, indices, and other market data.

## System Architecture

The application follows a modular architecture built on Streamlit for the web framework:

**Frontend**: Multi-page Streamlit web application with interactive widgets and real-time data visualization
- Navigation between Live Dashboard, Historical Data, Fundamental Analysis, Market Alerts, News, Portfolio, and Database Stats
- Plotly charts for interactive financial data visualization with standard finance intervals
- Auto-refresh capability for real-time updates
- AI-powered fundamental analysis with multiple valuation frameworks

**Backend**: Python-based data processing and fetching layer
- Yahoo Finance API integration for market data and fundamental financial statements
- OpenAI GPT-5 integration for AI-powered fundamental analysis
- PostgreSQL database for historical data storage, market alerts, and analysis caching
- Caching layer for performance optimization (5-min for market data, 1-hour for fundamentals)
- Error handling and logging for robustness

**Database**: PostgreSQL database for persistent storage
- Financial data storage with automatic data type conversion
- Market alerts system with price triggers
- User preferences and historical analysis
- Database statistics and management tools

**Data Sources**: 
- Yahoo Finance API via yfinance library for real-time and historical market data
- RSS feeds from major financial news sources (Yahoo Finance, Reuters, MarketWatch, CNBC, Bloomberg)
- Database storage for accumulated historical data, alerts, news articles, and portfolio data

## Key Components

### 1. Main Application (`app.py`)
- Streamlit web interface configuration
- Dashboard layout and controls
- Auto-refresh functionality
- Column-based responsive layout

### 2. Data Fetcher (`utils/data_fetcher.py`)
- Centralized data retrieval from Yahoo Finance
- Caching mechanism with 5-minute TTL
- Error handling and logging
- Price calculation and change percentage logic

### 3. Chart Generator (`utils/charts.py`)
- Plotly-based interactive chart creation
- Candlestick charts for price visualization
- Customizable time periods and styling
- Error handling for chart generation

### 4. Fundamentals Fetcher (`utils/fundamentals.py`)
- Fetch quarterly and annual financial statements using yfinance
- Extract up to 5 years of earnings history
- Calculate growth rates and profit margins
- Support for income statements, balance sheets, and cash flow statements

### 5. AI Valuation Analyzer (`utils/ai_valuation.py`)
- OpenAI GPT-5 powered fundamental analysis
- Multiple valuation frameworks: Comprehensive, Growth Investing, Value Investing, DCF
- Detailed investment recommendations with confidence scores
- Industry comparable analysis

## Data Flow

1. **User Interaction**: User interacts with sidebar controls (refresh, auto-refresh)
2. **Data Fetching**: DataFetcher queries Yahoo Finance API for market data
3. **Data Processing**: Raw data is processed to calculate changes and percentages
4. **Caching**: Processed data is cached for 5 minutes to reduce API calls
5. **Visualization**: Charts are generated using Plotly and displayed in Streamlit
6. **Auto-refresh**: Optional 30-second auto-refresh cycle for real-time updates

## External Dependencies

### Core Libraries
- **Streamlit**: Web application framework
- **yfinance**: Yahoo Finance API client
- **Plotly**: Interactive charting library
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing

### Data Sources
- **Yahoo Finance API**: Primary source for all financial data
- No authentication required for basic market data

## Deployment Strategy

The application is designed for cloud deployment on platforms like:
- Streamlit Cloud (recommended)
- Heroku
- AWS/GCP/Azure container services

**Deployment considerations**:
- Stateless architecture (no database required)
- Environment variables for configuration
- Caching for performance optimization
- Error handling for API rate limits

## Port Configuration Note

**Port 5000 has a broken port-detection loop in this Replit environment** (Replit's health check verifies the port via the external URL before routing is established, creating a circular dependency). The app runs on **port 8080** instead:
- Workflow command: `streamlit run app.py --server.port 8080 --browser.gatherUsageStats false`
- `waitForPort: 8080`, `outputType: "webview"`
- `.streamlit/config.toml` still says 5000 but the CLI flag overrides it

## Changelog

- July 05, 2025. Initial setup
- July 05, 2025. Added PostgreSQL database integration with financial data storage, historical analysis, market alerts, and database statistics pages
- July 05, 2025. Added news and portfolio tracking functionality with RSS feeds from major financial sources and comprehensive portfolio management system
- October 04, 2025. Added Fundamental Analysis page with AI-powered valuation analysis using OpenAI GPT-5, supporting 5 years of earnings history with quarterly/annual data, multiple valuation frameworks (comprehensive, growth, value, DCF), visual trend analysis of key financial metrics, and database caching of AI analysis results
- March 12, 2026. Fixed app startup: lazy database/OpenAI initialization, moved to port 8080 (port 5000 detection broken in this Replit env), fixed workflow configuration

## User Preferences

Preferred communication style: Simple, everyday language.