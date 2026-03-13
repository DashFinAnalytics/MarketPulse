import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import logging
from utils.data_fetcher import DataFetcher
from utils.charts import (
    create_price_chart, create_performance_chart, create_enhanced_price_chart,
    create_chart_from_db_data, create_vix_interpretation_chart, create_yield_curve_chart,
    create_correlation_heatmap, create_volume_chart, create_risk_metrics_chart,
    create_drawdown_chart, create_rolling_volatility_chart,
    create_options_oi_chart, create_options_iv_smile,
    create_forex_heatmap, create_futures_comparison_chart,
    create_technical_analysis_chart, create_portfolio_allocation_chart,
    create_portfolio_performance_chart, create_crypto_market_chart,
    create_economic_dashboard_chart, create_market_breadth_chart
)
from utils.intervals import FinanceIntervals
from utils.news_fetcher import news_fetcher
from database import db_manager
import json

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Global Finance Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database and data fetcher
@st.cache_resource
def initialize_database():
    """Initialize database tables"""
    try:
        db_manager.create_tables()
        return True
    except Exception as e:
        logger.warning(f"Database initialization failed: {str(e)}")
        return False

@st.cache_resource
def get_data_fetcher():
    return DataFetcher()

# Initialize database (don't fail app if it errors)
try:
    db_initialized = initialize_database()
except:
    db_initialized = False

data_fetcher = get_data_fetcher()

# Main title
st.title("🌍 Global Finance Dashboard")
st.markdown("---")

# Sidebar for controls
st.sidebar.header("Dashboard Controls")

# Navigation
page = st.sidebar.selectbox("Navigate", [
    "Live Dashboard", "Historical Data", "Technical Analysis",
    "Fundamental Analysis", "Forex & Currencies", "Futures",
    "Options Flow", "Risk Analysis", "Earnings & Events",
    "Crypto Markets", "Economic Indicators",
    "Market Alerts", "News", "Portfolio", "Database Stats"
])

# Auto-refresh controls (only for live dashboard)
if page == "Live Dashboard":
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    refresh_button = st.sidebar.button("🔄 Refresh Data")
else:
    auto_refresh = False
    refresh_button = False

# Auto-refresh logic
if auto_refresh:
    time.sleep(30)
    st.rerun()

# Manual refresh
if refresh_button:
    st.cache_data.clear()
    st.rerun()

if page == "Live Dashboard":
    # Create columns for layout
    col1, col2, col3 = st.columns([1, 1, 1])

    # Display last updated time
    with col3:
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Global Stock Indices Section
    st.header("📊 Global Stock Indices")
    indices_col1, indices_col2 = st.columns(2)

    with indices_col1:
        st.subheader("Major US Indices")
        us_indices = data_fetcher.get_indices_data(['SPY', 'QQQ', 'DIA'])
        if us_indices:
            for symbol, data in us_indices.items():
                price = data['price']
                change = data['change']
                change_pct = data['change_pct']
                
                # Color coding
                color = "🟢" if change >= 0 else "🔴"
                color_style = "color: green;" if change >= 0 else "color: red;"
                
                index_name = {
                    'SPY': 'S&P 500',
                    'QQQ': 'NASDAQ',
                    'DIA': 'Dow Jones'
                }.get(symbol, symbol)
                
                st.markdown(f"""
                **{index_name}** {color}  
                <span style="font-size: 1.2em; font-weight: bold;">${price:.2f}</span>  
                <span style="{color_style}">
                {change:+.2f} ({change_pct:+.2f}%)
                </span>
                """, unsafe_allow_html=True)
        else:
            st.error("Failed to load US indices data")

    with indices_col2:
        st.subheader("International Indices")
        intl_indices = data_fetcher.get_indices_data(['EWU', 'EWG', 'EWJ'])
        if intl_indices:
            for symbol, data in intl_indices.items():
                price = data['price']
                change = data['change']
                change_pct = data['change_pct']
                
                # Color coding
                color = "🟢" if change >= 0 else "🔴"
                color_style = "color: green;" if change >= 0 else "color: red;"
                
                index_name = {
                    'EWU': 'FTSE 100 (UK)',
                    'EWG': 'DAX (Germany)',
                    'EWJ': 'Nikkei (Japan)'
                }.get(symbol, symbol)
                
                st.markdown(f"""
                **{index_name}** {color}  
                <span style="font-size: 1.2em; font-weight: bold;">${price:.2f}</span>  
                <span style="{color_style}">
                {change:+.2f} ({change_pct:+.2f}%)
                </span>
                """, unsafe_allow_html=True)
        else:
            st.error("Failed to load international indices data")

    st.markdown("---")

    # Commodities Section
    st.header("🥇 Commodities")
    commodities_col1, commodities_col2 = st.columns(2)

    with commodities_col1:
        st.subheader("Precious Metals")
        metals = data_fetcher.get_commodities_data(['GLD', 'SLV'])
        if metals:
            for symbol, data in metals.items():
                price = data['price']
                change = data['change']
                change_pct = data['change_pct']
                
                # Color coding
                color = "🟢" if change >= 0 else "🔴"
                color_style = "color: green;" if change >= 0 else "color: red;"
                
                commodity_name = {
                    'GLD': 'Gold (SPDR)',
                    'SLV': 'Silver (iShares)'
                }.get(symbol, symbol)
                
                st.markdown(f"""
                **{commodity_name}** {color}  
                <span style="font-size: 1.2em; font-weight: bold;">${price:.2f}</span>  
                <span style="{color_style}">
                {change:+.2f} ({change_pct:+.2f}%)
                </span>
                """, unsafe_allow_html=True)
        else:
            st.error("Failed to load precious metals data")

    with commodities_col2:
        st.subheader("Energy")
        energy = data_fetcher.get_commodities_data(['USO', 'UNG'])
        if energy:
            for symbol, data in energy.items():
                price = data['price']
                change = data['change']
                change_pct = data['change_pct']
                
                # Color coding
                color = "🟢" if change >= 0 else "🔴"
                color_style = "color: green;" if change >= 0 else "color: red;"
                
                commodity_name = {
                    'USO': 'Oil (USO)',
                    'UNG': 'Natural Gas (UNG)'
                }.get(symbol, symbol)
                
                st.markdown(f"""
                **{commodity_name}** {color}  
                <span style="font-size: 1.2em; font-weight: bold;">${price:.2f}</span>  
                <span style="{color_style}">
                {change:+.2f} ({change_pct:+.2f}%)
                </span>
                """, unsafe_allow_html=True)
        else:
            st.error("Failed to load energy commodities data")

    st.markdown("---")

    # Bond Yields Section
    st.header("📈 Global Bond Yields")
    bonds_col1, bonds_col2, bonds_col3 = st.columns(3)

    with bonds_col1:
        st.subheader("US 10Y Treasury")
        us_10y = data_fetcher.get_bond_data('^TNX')
        if us_10y:
            yield_val = us_10y['price']
            change = us_10y['change']
            color = "🟢" if change >= 0 else "🔴"
            color_style = "color: green;" if change >= 0 else "color: red;"
            
            st.markdown(f"""
            **US 10Y** {color}  
            <span style="font-size: 1.5em; font-weight: bold;">{yield_val:.3f}%</span>  
            <span style="{color_style}">
            {change:+.3f}%
            </span>
            """, unsafe_allow_html=True)
        else:
            st.error("Failed to load US 10Y data")

    with bonds_col2:
        st.subheader("German 10Y Bund")
        de_10y = data_fetcher.get_bond_data('^TNX')  # Using TNX as proxy - in real implementation would use German bund
        if de_10y:
            yield_val = de_10y['price'] - 1.5  # Approximate German yield
            change = de_10y['change']
            color = "🟢" if change >= 0 else "🔴"
            color_style = "color: green;" if change >= 0 else "color: red;"
            
            st.markdown(f"""
            **German 10Y** {color}  
            <span style="font-size: 1.5em; font-weight: bold;">{yield_val:.3f}%</span>  
            <span style="{color_style}">
            {change:+.3f}%
            </span>
            """, unsafe_allow_html=True)
        else:
            st.error("Failed to load German 10Y data")

    with bonds_col3:
        st.subheader("Japanese 10Y")
        jp_10y = data_fetcher.get_bond_data('^TNX')  # Using TNX as proxy - in real implementation would use Japanese bond
        if jp_10y:
            yield_val = max(0.1, jp_10y['price'] - 3.5)  # Approximate Japanese yield
            change = jp_10y['change'] * 0.3
            color = "🟢" if change >= 0 else "🔴"
            color_style = "color: green;" if change >= 0 else "color: red;"
            
            st.markdown(f"""
            **Japanese 10Y** {color}  
            <span style="font-size: 1.5em; font-weight: bold;">{yield_val:.3f}%</span>  
            <span style="{color_style}">
            {change:+.3f}%
            </span>
            """, unsafe_allow_html=True)
        else:
            st.error("Failed to load Japanese 10Y data")

    st.markdown("---")

    # VIX Section
    st.header("😱 VIX Volatility Index")
    vix_col1, vix_col2 = st.columns([1, 2])

    with vix_col1:
        vix_data = data_fetcher.get_vix_data()
        if vix_data:
            vix_val = vix_data['price']
            change = vix_data['change']
            change_pct = vix_data['change_pct']
            
            # VIX interpretation
            if vix_val < 20:
                sentiment = "😌 Low Volatility"
                vix_color = "green"
            elif vix_val < 30:
                sentiment = "😐 Moderate Volatility"
                vix_color = "orange"
            else:
                sentiment = "😰 High Volatility"
                vix_color = "red"
            
            color = "🟢" if change >= 0 else "🔴"
            color_style = f"color: {vix_color};"
            
            st.markdown(f"""
            **VIX Index** {color}  
            <span style="font-size: 2em; font-weight: bold; {color_style}">{vix_val:.2f}</span>  
            <span style="color: {'red' if change >= 0 else 'green'};">
            {change:+.2f} ({change_pct:+.2f}%)
            </span>  
            **{sentiment}**
            """, unsafe_allow_html=True)
        else:
            st.error("Failed to load VIX data")

    with vix_col2:
        if vix_data:
            vix_gauge = create_vix_interpretation_chart(vix_data['price'])
            if vix_gauge:
                st.plotly_chart(vix_gauge, use_container_width=True)

    vix_chart = create_enhanced_price_chart('^VIX', '30d', use_yfinance=True)
    if vix_chart:
        st.plotly_chart(vix_chart, use_container_width=True)

    st.markdown("---")

    # Yield Curve Section
    st.header("📐 US Treasury Yield Curve")
    yc_col1, yc_col2, yc_col3, yc_col4 = st.columns(4)
    bond_yields = data_fetcher.get_bond_yields()
    labels_map = {'3M': '3-Month', '5Y': '5-Year', '10Y': '10-Year', '30Y': '30-Year'}
    for col, key in zip([yc_col1, yc_col2, yc_col3, yc_col4], ['3M', '5Y', '10Y', '30Y']):
        with col:
            if key in bond_yields:
                d = bond_yields[key]
                chg = d['change']
                arrow = "↑" if chg >= 0 else "↓"
                color = "red" if chg >= 0 else "green"
                st.metric(labels_map[key], f"{d['yield']:.2f}%",
                          delta=f"{chg:+.3f}%")
    yc_chart = create_yield_curve_chart(bond_yields)
    if yc_chart:
        st.plotly_chart(yc_chart, use_container_width=True)
    else:
        st.info("Yield curve data loading…")

    st.markdown("---")

    # Sector ETFs Section
    st.header("🏭 Sector ETFs Performance")
    sector_col1, sector_col2 = st.columns(2)

    with sector_col1:
        st.subheader("Technology & Healthcare")
        tech_health = data_fetcher.get_sector_etfs(['XLK', 'XLV'])
        if tech_health:
            for symbol, data in tech_health.items():
                price = data['price']
                change = data['change']
                change_pct = data['change_pct']
                
                # Color coding
                color = "🟢" if change >= 0 else "🔴"
                color_style = "color: green;" if change >= 0 else "color: red;"
                
                sector_name = {
                    'XLK': 'Technology (XLK)',
                    'XLV': 'Healthcare (XLV)'
                }.get(symbol, symbol)
                
                st.markdown(f"""
                **{sector_name}** {color}  
                <span style="font-size: 1.2em; font-weight: bold;">${price:.2f}</span>  
                <span style="{color_style}">
                {change:+.2f} ({change_pct:+.2f}%)
                </span>
                """, unsafe_allow_html=True)
        else:
            st.error("Failed to load Technology & Healthcare ETF data")

    with sector_col2:
        st.subheader("Energy & Finance")
        energy_finance = data_fetcher.get_sector_etfs(['XLE', 'XLF'])
        if energy_finance:
            for symbol, data in energy_finance.items():
                price = data['price']
                change = data['change']
                change_pct = data['change_pct']
                
                # Color coding
                color = "🟢" if change >= 0 else "🔴"
                color_style = "color: green;" if change >= 0 else "color: red;"
                
                sector_name = {
                    'XLE': 'Energy (XLE)',
                    'XLF': 'Finance (XLF)'
                }.get(symbol, symbol)
                
                st.markdown(f"""
                **{sector_name}** {color}  
                <span style="font-size: 1.2em; font-weight: bold;">${price:.2f}</span>  
                <span style="{color_style}">
                {change:+.2f} ({change_pct:+.2f}%)
                </span>
                """, unsafe_allow_html=True)
        else:
            st.error("Failed to load Energy & Finance ETF data")

    # Sector Performance Chart
    st.subheader("📊 Sector Performance Comparison")
    all_sectors = data_fetcher.get_sector_etfs(['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLU', 'XLB', 'XLRE'])
    if all_sectors:
        sector_chart = create_performance_chart(all_sectors)
        if sector_chart:
            st.plotly_chart(sector_chart, use_container_width=True)

    st.markdown("---")

    # Asset Correlation Heatmap
    st.header("🔥 Asset Correlation Heatmap")
    st.caption("3-month daily returns correlation across major asset classes")
    corr_symbols = ['SPY', 'QQQ', 'DIA', 'GLD', 'SLV', 'USO', '^VIX', 'TLT', 'XLK', 'XLE', 'EURUSD=X']
    with st.spinner("Building correlation matrix…"):
        corr_chart = create_correlation_heatmap(corr_symbols, period="3mo")
    if corr_chart:
        st.plotly_chart(corr_chart, use_container_width=True)
    else:
        st.info("Correlation data loading…")

    st.markdown("---")

    # Market Breadth
    st.header("📡 Market Breadth & Sentiment")
    breadth_col1, breadth_col2 = st.columns([1, 2])
    with st.spinner("Calculating market breadth…"):
        breadth = data_fetcher.get_market_breadth()
    if breadth:
        with breadth_col1:
            st.metric("Advancing Sectors", breadth['advancing'])
            st.metric("Declining Sectors",  breadth['declining'])
            st.metric("Avg Sector Change", f"{breadth['avg_sector_change']:+.2f}%")
            st.info(f"**Sentiment: {breadth['label']}**")
        with breadth_col2:
            brd_fig = create_market_breadth_chart(breadth)
            if brd_fig:
                st.plotly_chart(brd_fig, use_container_width=True)

        brd_df = pd.DataFrame(breadth['sector_changes'])
        brd_df['Direction'] = brd_df['change_pct'].apply(lambda x: '🟢' if x >= 0 else '🔴')
        brd_df['change_pct'] = brd_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
        st.dataframe(brd_df[['symbol', 'Direction', 'change_pct']].rename(
            columns={'symbol': 'Sector ETF', 'change_pct': '% Change'}
        ), use_container_width=True, hide_index=True)
    else:
        st.info("Market breadth data loading…")

    st.markdown("---")

    # Footer
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8em; margin-top: 2em;">
        Data provided by Yahoo Finance via yfinance library<br>
        🔄 Dashboard updates every 30 seconds when auto-refresh is enabled
    </div>
    """, unsafe_allow_html=True)

elif page == "Historical Data":
    st.header("📈 Historical Data Analysis")
    
    # Symbol and interval selection
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_symbol = st.selectbox(
            "Select Symbol",
            [
                # US Indices
                'SPY', 'QQQ', 'DIA', 'IWM',
                # Volatility
                '^VIX',
                # Sectors
                'XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLU', 'XLB', 'XLRE', 'XLY', 'XLP', 'XLC',
                # Commodities
                'GLD', 'SLV', 'USO', 'UNG', 'PDBC',
                # Bonds
                'TLT', 'SHY', 'HYG', 'LQD',
                # Crypto
                'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD',
                # Forex
                'EURUSD=X', 'GBPUSD=X', 'USDJPY=X',
                # Futures
                'ES=F', 'NQ=F', 'GC=F', 'CL=F',
                # Individual stocks
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B'
            ]
        )
    with col2:
        # Get available intervals
        intervals = FinanceIntervals.get_available_intervals()
        selected_interval = st.selectbox(
            "Time Interval",
            options=list(intervals.keys()),
            format_func=lambda x: intervals[x],
            index=list(intervals.keys()).index('1d')  # Default to 1 day
        )
    with col3:
        data_source = st.selectbox(
            "Data Source",
            ["Yahoo Finance", "Database (if available)"]
        )
    
    if selected_symbol and selected_interval:
        # Display interval information
        interval_config = FinanceIntervals.get_interval_config(selected_interval)
        if interval_config:
            st.info(f"📊 Showing {intervals[selected_interval]} data for {selected_symbol}")
        
        # Try to get data based on selected source
        chart_created = False
        
        if data_source == "Database (if available)" and db_initialized:
            # Try database first
            lookback_hours = FinanceIntervals.get_db_lookback_hours(selected_interval)
            historical_data = db_manager.get_historical_data(selected_symbol, lookback_hours)
            
            if historical_data and len(historical_data) > 0:
                # Convert to DataFrame for easy plotting
                df = pd.DataFrame(historical_data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                
                # Create chart from database data
                chart = create_chart_from_db_data(df, selected_symbol, intervals[selected_interval])
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
                    chart_created = True
                    
                    # Summary statistics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Current Price", f"${df['price'].iloc[-1]:.2f}")
                    with col2:
                        price_change = df['price'].iloc[-1] - df['price'].iloc[0]
                        st.metric("Price Change", f"${price_change:.2f}")
                    with col3:
                        st.metric("Max Price", f"${df['price'].max():.2f}")
                    with col4:
                        st.metric("Min Price", f"${df['price'].min():.2f}")
                    
                    # Show data source info
                    st.caption(f"📊 Data from database: {len(df)} data points over {lookback_hours} hours")
                    
                    # Data table
                    with st.expander("Recent Data Points"):
                        st.dataframe(df.tail(20), use_container_width=True)
        
        # Fallback to Yahoo Finance if database didn't work or wasn't selected
        if not chart_created:
            try:
                chart = create_enhanced_price_chart(selected_symbol, selected_interval, use_yfinance=True)
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
                    chart_created = True
                    
                    # Get current data for metrics
                    current_data = data_fetcher._fetch_ticker_data(selected_symbol)
                    if current_data:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Current Price", f"${current_data['price']:.2f}")
                        with col2:
                            st.metric("Change", f"${current_data['change']:+.2f}")
                        with col3:
                            st.metric("Change %", f"{current_data['change_pct']:+.2f}%")
                        with col4:
                            st.metric("Volume", f"{current_data['volume']:,.0f}")
                    
                    # Show data source info
                    st.caption("📊 Data from Yahoo Finance (real-time)")
                else:
                    st.warning(f"No data available for {selected_symbol} at {intervals[selected_interval]} interval")
            except Exception as e:
                st.error(f"Error fetching data: {str(e)}")
        
        if not chart_created:
            if data_source == "Database (if available)":
                st.info(f"No database data available for {selected_symbol}. Try switching to Yahoo Finance or check the Live Dashboard to populate database.")
            else:
                st.error("Unable to fetch data from any source.")
        
        # Additional interval information
        with st.expander("ℹ️ Interval Information"):
            if interval_config:
                st.write(f"**Period**: {interval_config['period']}")
                st.write(f"**Interval**: {interval_config['interval']}")
                if interval_config['hours']:
                    st.write(f"**Duration**: {interval_config['hours']} hours")
                st.write(f"**Intraday**: {'Yes' if FinanceIntervals.is_intraday(selected_interval) else 'No'}")
    else:
        st.warning("Please select a symbol and interval.")

elif page == "Market Alerts":
    st.header("🚨 Market Alerts")
    
    if not db_initialized:
        st.error("Database not available for alerts functionality.")
        st.stop()
    
    # Create new alert
    st.subheader("Create New Alert")
    with st.form("new_alert"):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            alert_symbol = st.selectbox(
                "Symbol",
                [
                    'SPY', 'QQQ', 'DIA', 'IWM', '^VIX',
                    'GLD', 'SLV', 'USO', 'UNG', 'TLT', 'HYG',
                    'XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLU', 'XLY', 'XLP',
                    'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD',
                    'EURUSD=X', 'GBPUSD=X', 'USDJPY=X',
                    'ES=F', 'NQ=F', 'GC=F', 'CL=F',
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META'
                ]
            )
        with col2:
            alert_type = st.selectbox("Alert Type", ["above", "below"])
        with col3:
            target_price = st.number_input("Target Price", min_value=0.01, value=100.0, step=0.01)
        with col4:
            user_id = st.text_input("User ID", value="default_user")
        
        submit_alert = st.form_submit_button("Create Alert")
        
        if submit_alert:
            success = db_manager.create_market_alert(user_id, alert_symbol, alert_type, target_price)
            if success:
                st.success(f"Alert created: {alert_symbol} {alert_type} ${target_price}")
            else:
                st.error("Failed to create alert")
    
    # Display active alerts
    st.subheader("Active Alerts")
    active_alerts = db_manager.get_active_alerts()
    
    if active_alerts:
        alert_df = pd.DataFrame(active_alerts)
        st.dataframe(alert_df, use_container_width=True)
    else:
        st.info("No active alerts found.")
    
    # Alert checking section
    st.subheader("Check Alerts")
    if st.button("Check All Alerts Against Current Prices"):
        with st.spinner("Checking alerts..."):
            # Get current prices for all symbols
            current_prices = {}
            all_symbols = [
                'SPY', 'QQQ', 'DIA', 'IWM', '^VIX',
                'GLD', 'SLV', 'USO', 'UNG', 'TLT', 'HYG',
                'XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLU', 'XLY', 'XLP',
                'BTC-USD', 'ETH-USD', 'SOL-USD',
                'EURUSD=X', 'GBPUSD=X', 'USDJPY=X',
                'ES=F', 'NQ=F', 'GC=F', 'CL=F',
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META'
            ]
            
            for symbol in all_symbols:
                data = data_fetcher._fetch_ticker_data(symbol)
                if data:
                    current_prices[symbol] = data['price']
            
            triggered_alerts = db_manager.check_alerts(current_prices)
            
            if triggered_alerts:
                st.success(f"🚨 {len(triggered_alerts)} alerts triggered!")
                for alert in triggered_alerts:
                    st.write(f"Alert: {alert['symbol']} {alert['alert_type']} ${alert['target_price']:.2f} - Current: ${alert['current_price']:.2f}")
            else:
                st.info("No alerts triggered.")

elif page == "News":
    st.header("📰 Financial News")
    
    # News controls
    col1, col2, col3 = st.columns(3)
    with col1:
        news_type = st.selectbox(
            "News Type",
            ["Market News", "Symbol News", "Sector News", "Search"]
        )
    with col2:
        if news_type == "Symbol News":
            news_symbol = st.selectbox(
                "Symbol",
                [
                    'SPY', 'QQQ', 'DIA', 'IWM', '^VIX',
                    'GLD', 'SLV', 'USO', 'UNG', 'TLT', 'HYG',
                    'XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLU', 'XLY', 'XLP',
                    'BTC-USD', 'ETH-USD', 'SOL-USD',
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META',
                    'EURUSD=X', 'GC=F', 'CL=F'
                ]
            )
            news_sector = None
            search_query = None
        elif news_type == "Sector News":
            news_sector = st.selectbox(
                "Sector",
                ["Technology", "Healthcare", "Finance", "Energy", "Retail"]
            )
            news_symbol = None
            search_query = None
        elif news_type == "Search":
            search_query = st.text_input("Search Terms", placeholder="e.g., inflation, earnings, fed")
            news_symbol = None
            news_sector = None
        else:
            news_symbol = None
            news_sector = None
            search_query = None
    with col3:
        news_limit = st.slider("Number of Articles", 5, 50, 15)
    
    # Fetch news button
    if st.button("Fetch Latest News"):
        with st.spinner("Fetching news..."):
            try:
                if news_type == "Market News":
                    articles = news_fetcher.get_market_news(limit=news_limit)
                elif news_type == "Symbol News" and news_symbol:
                    articles = news_fetcher.get_symbol_news(news_symbol, limit=news_limit)
                elif news_type == "Sector News" and news_sector:
                    articles = news_fetcher.get_sector_news(news_sector, limit=news_limit)
                elif news_type == "Search" and search_query:
                    articles = news_fetcher.search_news(search_query, limit=news_limit)
                else:
                    articles = []
                
                if articles:
                    st.success(f"Found {len(articles)} articles")
                    
                    # Display articles
                    for i, article in enumerate(articles):
                        with st.expander(f"{article['title'][:80]}..." if len(article['title']) > 80 else article['title']):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.markdown(f"**Source:** {article['source']}")
                                st.markdown(f"**Published:** {article['published'].strftime('%Y-%m-%d %H:%M')}")
                                if article.get('author'):
                                    st.markdown(f"**Author:** {article['author']}")
                            
                            with col2:
                                if st.button("Read More", key=f"read_{i}"):
                                    st.markdown(f"[Open Article]({article['link']})")
                            
                            st.markdown("**Summary:**")
                            st.write(article['summary'])
                            
                            # Store article in database
                            if db_initialized:
                                db_manager.store_news_article(article)
                else:
                    st.info("No articles found for the selected criteria.")
                    
            except Exception as e:
                st.error(f"Error fetching news: {str(e)}")
    
    # Trending topics
    st.subheader("📈 Trending Topics")
    if st.button("Get Trending Topics"):
        with st.spinner("Analyzing trends..."):
            try:
                trending = news_fetcher.get_trending_topics()
                if trending:
                    cols = st.columns(5)
                    for i, topic in enumerate(trending[:10]):
                        with cols[i % 5]:
                            st.metric(
                                topic['topic'].title(),
                                f"{topic['count']} mentions"
                            )
                else:
                    st.info("No trending topics found.")
            except Exception as e:
                st.error(f"Error getting trending topics: {str(e)}")
    
    # Recent stored news
    if db_initialized:
        st.subheader("📚 Recent Stored Articles")
        stored_articles = db_manager.get_stored_news(limit=10)
        if stored_articles:
            for article in stored_articles:
                st.markdown(f"**{article['title']}**")
                st.caption(f"{article['source']} • {article['published_date'].strftime('%Y-%m-%d %H:%M')}")
                st.markdown(f"[Read Article]({article['url']})")
                st.markdown("---")
        else:
            st.info("No stored articles found.")

elif page == "Fundamental Analysis":
    from page_modules.fundamental_analysis import render_fundamental_analysis_page
    render_fundamental_analysis_page()

# ─────────────────────────────────────────────────────────
# FOREX & CURRENCIES
# ─────────────────────────────────────────────────────────
elif page == "Forex & Currencies":
    st.header("💱 Forex & Currency Markets")
    st.caption("Live exchange rates — all quoted against USD")

    all_pairs = {
        'EURUSD=X': 'EUR/USD', 'GBPUSD=X': 'GBP/USD', 'USDJPY=X': 'USD/JPY',
        'USDCHF=X': 'USD/CHF', 'AUDUSD=X': 'AUD/USD', 'USDCAD=X': 'USD/CAD',
        'NZDUSD=X': 'NZD/USD', 'USDCNY=X': 'USD/CNY',
        'USDINR=X': 'USD/INR', 'USDMXN=X': 'USD/MXN',
        'USDBRL=X': 'USD/BRL', 'USDSGD=X': 'USD/SGD'
    }

    with st.spinner("Loading forex data…"):
        forex_data = data_fetcher.get_forex_data(list(all_pairs.keys()))

    if forex_data:
        fx_heatmap = create_forex_heatmap(forex_data)
        if fx_heatmap:
            st.plotly_chart(fx_heatmap, use_container_width=True)

        st.subheader("📋 Rates Table")
        rows = []
        for sym, label in all_pairs.items():
            if sym in forex_data:
                d = forex_data[sym]
                rows.append({
                    'Pair': label,
                    'Rate': round(d['price'], 5),
                    'Change': round(d['change'], 5),
                    'Change %': f"{d['change_pct']:+.3f}%",
                    'Direction': '🟢 Up' if d['change'] >= 0 else '🔴 Down'
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.error("Failed to load forex data")

    st.markdown("---")
    st.subheader("📈 Currency Price Chart")
    fx_symbol = st.selectbox("Select pair", list(all_pairs.keys()),
                              format_func=lambda x: all_pairs[x])
    fx_period = st.select_slider("Period", ['1mo', '3mo', '6mo', '1y', '2y'], value='3mo')
    with st.spinner("Loading chart…"):
        fx_chart = create_price_chart(fx_symbol, all_pairs.get(fx_symbol, fx_symbol),
                                      period=fx_period, interval='1d')
    if fx_chart:
        st.plotly_chart(fx_chart, use_container_width=True)

# ─────────────────────────────────────────────────────────
# FUTURES
# ─────────────────────────────────────────────────────────
elif page == "Futures":
    st.header("📦 Futures Markets")

    futures_groups = {
        'Equity Index Futures': ['ES=F', 'NQ=F', 'YM=F', 'RTY=F'],
        'Precious Metals': ['GC=F', 'SI=F', 'PL=F'],
        'Energy': ['CL=F', 'NG=F', 'RB=F'],
        'Treasury / Bond': ['ZB=F', 'ZN=F', 'ZT=F'],
        'Agricultural': ['ZC=F', 'ZW=F', 'ZS=F']
    }

    futures_names = {
        'ES=F': 'S&P 500', 'NQ=F': 'NASDAQ-100', 'YM=F': 'Dow Jones', 'RTY=F': 'Russell 2000',
        'GC=F': 'Gold', 'SI=F': 'Silver', 'PL=F': 'Platinum',
        'CL=F': 'Crude Oil (WTI)', 'NG=F': 'Natural Gas', 'RB=F': 'RBOB Gasoline',
        'ZB=F': '30Y T-Bond', 'ZN=F': '10Y T-Note', 'ZT=F': '2Y T-Note',
        'ZC=F': 'Corn', 'ZW=F': 'Wheat', 'ZS=F': 'Soybeans'
    }

    all_contracts = [c for group in futures_groups.values() for c in group]
    with st.spinner("Loading futures data…"):
        futures_data = data_fetcher.get_futures_data(all_contracts)

    for group_name, contracts in futures_groups.items():
        st.subheader(f"🔹 {group_name}")
        group_data = {c: futures_data[c] for c in contracts if c in futures_data}
        if not group_data:
            st.info(f"Data unavailable for {group_name}")
            continue

        cols = st.columns(len(group_data))
        for col, (sym, d) in zip(cols, group_data.items()):
            with col:
                label = futures_names.get(sym, sym)
                delta_color = "normal" if d['change'] >= 0 else "inverse"
                st.metric(label, f"{d['price']:.2f}",
                          delta=f"{d['change_pct']:+.2f}%")

        chart = create_futures_comparison_chart(group_data, group_name)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        st.markdown("---")

    st.subheader("📈 Futures Price Chart")
    all_contracts_named = {c: futures_names.get(c, c) for c in all_contracts}
    fut_sym = st.selectbox("Contract", list(all_contracts_named.keys()),
                           format_func=lambda x: all_contracts_named[x])
    fut_period = st.select_slider("Period", ['1mo', '3mo', '6mo', '1y'], value='3mo')
    with st.spinner("Loading chart…"):
        fut_chart = create_price_chart(fut_sym, all_contracts_named.get(fut_sym, fut_sym),
                                       period=fut_period, interval='1d')
    if fut_chart:
        st.plotly_chart(fut_chart, use_container_width=True)

# ─────────────────────────────────────────────────────────
# OPTIONS FLOW
# ─────────────────────────────────────────────────────────
elif page == "Options Flow":
    st.header("🎯 Options Flow & Analysis")

    opt_col1, opt_col2 = st.columns([2, 1])
    with opt_col1:
        opt_symbol = st.text_input("Symbol", value="SPY").upper()
    with opt_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        load_opts = st.button("Load Options Data")

    if opt_symbol:
        with st.spinner(f"Fetching options data for {opt_symbol}…"):
            opts_summary = data_fetcher.get_options_summary(opt_symbol)

        if opts_summary:
            st.subheader("📊 Options Summary")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("P/C Ratio (OI)",  str(opts_summary.get('pc_ratio_oi',  'N/A')))
            m2.metric("P/C Ratio (Vol)", str(opts_summary.get('pc_ratio_vol', 'N/A')))
            m3.metric("ATM IV", f"{opts_summary.get('atm_iv', 'N/A')}%"
                      if opts_summary.get('atm_iv') else 'N/A')
            m4.metric("Next Expiry", str(opts_summary.get('next_expiration', 'N/A')))

            oi_col1, oi_col2 = st.columns(2)
            with oi_col1:
                st.metric("Total Call OI",  f"{opts_summary['total_call_oi']:,}")
                st.metric("Total Call Vol", f"{opts_summary['total_call_vol']:,}")
            with oi_col2:
                st.metric("Total Put OI",   f"{opts_summary['total_put_oi']:,}")
                st.metric("Total Put Vol",  f"{opts_summary['total_put_vol']:,}")

            st.markdown("---")
            st.subheader("📅 Available Expirations")
            exps = opts_summary.get('expirations', [])
            if exps:
                selected_exp = st.selectbox("Expiration date", exps)
                with st.spinner("Loading option chain…"):
                    chain_data = data_fetcher.get_option_chain(opt_symbol, selected_exp)

                if chain_data:
                    chain_tab1, chain_tab2, chain_tab3 = st.tabs(["Open Interest", "IV Smile", "Chain Table"])

                    with chain_tab1:
                        oi_fig = create_options_oi_chart(chain_data)
                        if oi_fig:
                            st.plotly_chart(oi_fig, use_container_width=True)

                    with chain_tab2:
                        iv_fig = create_options_iv_smile(chain_data)
                        if iv_fig:
                            st.plotly_chart(iv_fig, use_container_width=True)

                    with chain_tab3:
                        chain_view = st.radio("Show", ["Calls", "Puts"], horizontal=True)
                        df_chain = chain_data['calls'] if chain_view == "Calls" else chain_data['puts']
                        cols_to_show = [c for c in [
                            'strike', 'lastPrice', 'bid', 'ask', 'volume',
                            'openInterest', 'impliedVolatility', 'delta', 'gamma', 'theta'
                        ] if c in df_chain.columns]
                        st.dataframe(df_chain[cols_to_show].sort_values('strike'),
                                     use_container_width=True, hide_index=True)
        else:
            st.error(f"No options data available for {opt_symbol}")

# ─────────────────────────────────────────────────────────
# RISK ANALYSIS
# ─────────────────────────────────────────────────────────
elif page == "Risk Analysis":
    st.header("⚠️ Risk Analysis & Management")

    risk_col1, risk_col2, risk_col3 = st.columns([2, 2, 1])
    with risk_col1:
        risk_symbol = st.text_input("Symbol to analyse", value="SPY").upper()
    with risk_col2:
        risk_benchmark = st.selectbox("Benchmark", ['^GSPC', '^NDX', '^DJI', '^RUT'],
                                      format_func=lambda x: {'^GSPC': 'S&P 500', '^NDX': 'NASDAQ-100',
                                                              '^DJI': 'Dow Jones', '^RUT': 'Russell 2000'}.get(x, x))
    with risk_col3:
        risk_period = st.selectbox("Period", ['1y', '2y', '3y', '5y'], index=0)

    with st.spinner(f"Calculating risk metrics for {risk_symbol}…"):
        risk_data = data_fetcher.get_risk_metrics(risk_symbol, risk_benchmark, risk_period)

    if risk_data:
        st.subheader("📊 Key Risk Metrics")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Beta", f"{risk_data['beta']:.3f}",
                  help="Sensitivity to benchmark movements. >1 = more volatile.")
        c2.metric("Alpha (Ann.)", f"{risk_data['alpha']:.2f}%",
                  help="Excess return vs benchmark after adjusting for risk.")
        c3.metric("Sharpe Ratio", f"{risk_data['sharpe_ratio']:.3f}",
                  help=">1 good, >2 very good, >3 excellent.")
        c4.metric("Sortino Ratio", f"{risk_data['sortino_ratio']:.3f}",
                  help="Like Sharpe but only penalises downside volatility.")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Ann. Return", f"{risk_data['annual_return']:.2f}%")
        c6.metric("Ann. Volatility", f"{risk_data['annual_volatility']:.2f}%")
        c7.metric("Max Drawdown", f"{risk_data['max_drawdown']:.2f}%")
        c8.metric("Calmar Ratio", f"{risk_data['calmar_ratio']:.3f}",
                  help="Ann. return / Max drawdown. Higher = better risk-adjusted.")

        st.subheader("📉 Value at Risk (VaR)")
        v1, v2, v3 = st.columns(3)
        v1.metric("1-Day VaR 95%", f"{risk_data['var_95']:.2f}%",
                  help="On 95% of days, loss won't exceed this.")
        v2.metric("1-Day VaR 99%", f"{risk_data['var_99']:.2f}%",
                  help="On 99% of days, loss won't exceed this.")
        v3.metric("CVaR 95% (ES)", f"{risk_data['cvar_95']:.2f}%",
                  help="Expected loss on the worst 5% of days.")

        st.metric("Correlation with Benchmark", f"{risk_data['correlation']:.3f}")

        st.markdown("---")
        risk_tab1, risk_tab2, risk_tab3 = st.tabs(["Risk Ratios", "Drawdown", "Rolling Volatility"])
        with risk_tab1:
            ratios_fig = create_risk_metrics_chart(risk_data)
            if ratios_fig:
                st.plotly_chart(ratios_fig, use_container_width=True)
        with risk_tab2:
            with st.spinner("Loading drawdown chart…"):
                dd_fig = create_drawdown_chart(risk_symbol, risk_period)
            if dd_fig:
                st.plotly_chart(dd_fig, use_container_width=True)
        with risk_tab3:
            with st.spinner("Loading volatility chart…"):
                vol_fig = create_rolling_volatility_chart(risk_symbol, risk_period)
            if vol_fig:
                st.plotly_chart(vol_fig, use_container_width=True)
    else:
        st.error(f"Could not calculate risk metrics for {risk_symbol}. Check the symbol and try again.")

    st.markdown("---")
    st.subheader("🔥 Multi-Asset Correlation")
    default_corr = 'SPY, QQQ, GLD, TLT, USO, XLK, XLE, EURUSD=X'
    corr_input = st.text_input("Comma-separated symbols", value=default_corr)
    corr_period_sel = st.selectbox("Lookback period", ['1mo', '3mo', '6mo', '1y'], index=2)
    if st.button("Generate Correlation Matrix"):
        syms = [s.strip().upper() for s in corr_input.split(',') if s.strip()]
        with st.spinner("Building correlation matrix…"):
            corr_fig = create_correlation_heatmap(syms, period=corr_period_sel)
        if corr_fig:
            st.plotly_chart(corr_fig, use_container_width=True)
        else:
            st.error("Could not build correlation matrix. Check the symbols.")

# ─────────────────────────────────────────────────────────
# EARNINGS & EVENTS
# ─────────────────────────────────────────────────────────
elif page == "Earnings & Events":
    st.header("📅 Earnings Calendar & Corporate Events")

    earn_col1, earn_col2 = st.columns([3, 1])
    with earn_col1:
        earn_symbol = st.text_input("Ticker symbol", value="AAPL").upper()
    with earn_col2:
        st.markdown("<br>", unsafe_allow_html=True)

    if earn_symbol:
        with st.spinner(f"Fetching calendar data for {earn_symbol}…"):
            cal_data = data_fetcher.get_earnings_calendar(earn_symbol)
            div_data = data_fetcher.get_dividends_splits(earn_symbol)

        if cal_data:
            earn_tab1, earn_tab2, earn_tab3, earn_tab4 = st.tabs([
                "Earnings Dates", "Analyst Recommendations", "Dividends & Splits", "Price Targets"
            ])

            with earn_tab1:
                st.subheader(f"📆 Earnings Dates — {earn_symbol}")
                if cal_data.get('calendar') is not None:
                    cal = cal_data['calendar']
                    try:
                        st.json(cal)
                    except Exception:
                        st.write(cal)

                ed = cal_data.get('earnings_dates')
                if ed is not None and not ed.empty:
                    st.subheader("Historical Earnings")
                    st.dataframe(ed.head(20), use_container_width=True)
                else:
                    st.info("No upcoming earnings dates found")

                eh = cal_data.get('earnings_history')
                if eh is not None and not eh.empty:
                    st.subheader("Earnings History (EPS)")
                    st.dataframe(eh, use_container_width=True)

            with earn_tab2:
                recs = cal_data.get('recommendations')
                if recs is not None and not recs.empty:
                    st.subheader("Analyst Recommendations")
                    st.dataframe(recs, use_container_width=True)
                else:
                    st.info("No analyst recommendations available")

            with earn_tab3:
                if div_data:
                    d1, d2 = st.columns(2)
                    with d1:
                        st.metric("Dividend Yield",
                                  f"{div_data['dividend_yield']*100:.2f}%"
                                  if div_data.get('dividend_yield') else "N/A")
                        st.metric("Payout Ratio",
                                  f"{div_data['payout_ratio']*100:.1f}%"
                                  if div_data.get('payout_ratio') else "N/A")
                    with d2:
                        st.metric("Annual Dividend",
                                  f"${div_data['forward_annual_dividend']:.2f}"
                                  if div_data.get('forward_annual_dividend') else "N/A")
                        ex_div = div_data.get('ex_dividend_date')
                        st.metric("Ex-Dividend Date",
                                  datetime.fromtimestamp(ex_div).strftime('%Y-%m-%d')
                                  if ex_div else "N/A")

                    divs = div_data.get('dividends')
                    if divs is not None and not divs.empty:
                        st.subheader("Dividend History")
                        div_df = divs.reset_index()
                        div_df.columns = ['Date', 'Dividend ($)']
                        st.dataframe(div_df, use_container_width=True, hide_index=True)

                    splits = div_data.get('splits')
                    if splits is not None and not splits.empty:
                        st.subheader("Stock Split History")
                        split_df = splits.reset_index()
                        split_df.columns = ['Date', 'Split Ratio']
                        st.dataframe(split_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No dividend data available")

            with earn_tab4:
                pt = cal_data.get('analyst_price_targets')
                if pt is not None:
                    try:
                        st.subheader("Analyst Price Targets")
                        if isinstance(pt, dict):
                            targets_df = pd.DataFrame([pt])
                        else:
                            targets_df = pd.DataFrame(pt)
                        st.dataframe(targets_df, use_container_width=True)
                    except Exception:
                        st.write(pt)
                else:
                    st.info("No price target data available")
        else:
            st.error(f"Could not fetch data for {earn_symbol}. Verify the ticker symbol.")

# ─────────────────────────────────────────────────────────
# TECHNICAL ANALYSIS
# ─────────────────────────────────────────────────────────
elif page == "Technical Analysis":
    st.header("📉 Technical Analysis")

    ta_col1, ta_col2, ta_col3 = st.columns([2, 2, 1])
    with ta_col1:
        ta_symbol = st.text_input("Symbol", value="SPY").upper()
    with ta_col2:
        ta_period = st.selectbox("Period",
                                  ['1mo', '3mo', '6mo', '1y', '2y', '5y'],
                                  index=2)
    with ta_col3:
        ta_interval = st.selectbox("Interval",
                                    ['1d', '1wk', '1h', '30m', '15m'],
                                    index=0)

    st.subheader("Indicator Settings")
    ind_col1, ind_col2, ind_col3, ind_col4 = st.columns(4)
    with ind_col1:
        show_bb     = st.checkbox("Bollinger Bands", value=True)
        show_volume = st.checkbox("Volume",          value=True)
    with ind_col2:
        show_rsi  = st.checkbox("RSI (14)",  value=True)
        show_macd = st.checkbox("MACD",      value=True)
    with ind_col3:
        use_sma20  = st.checkbox("SMA 20",  value=True)
        use_sma50  = st.checkbox("SMA 50",  value=True)
    with ind_col4:
        use_sma200 = st.checkbox("SMA 200", value=False)
        use_ema20  = st.checkbox("EMA 20",  value=True)

    sma_list = []
    if use_sma20:  sma_list.append(20)
    if use_sma50:  sma_list.append(50)
    if use_sma200: sma_list.append(200)

    if ta_symbol:
        with st.spinner(f"Building technical chart for {ta_symbol}…"):
            ta_fig = create_technical_analysis_chart(
                ta_symbol, period=ta_period, interval=ta_interval,
                show_bb=show_bb, show_rsi=show_rsi,
                show_macd=show_macd, show_volume=show_volume,
                sma_periods=sma_list if sma_list else [20]
            )
        if ta_fig:
            st.plotly_chart(ta_fig, use_container_width=True)
        else:
            st.error(f"Could not build technical chart for {ta_symbol}. Check the symbol or try a longer period.")

        st.markdown("---")
        st.subheader("📐 Indicator Guide")
        with st.expander("What do these indicators mean?"):
            st.markdown("""
| Indicator | What it shows |
|---|---|
| **SMA / EMA** | Moving average — trend direction; price above = bullish |
| **Bollinger Bands** | Volatility bands; price near upper = overbought, near lower = oversold |
| **RSI (14)** | Momentum oscillator 0–100; >70 overbought, <30 oversold |
| **MACD** | Momentum; histogram above zero = bullish momentum, signal crossover = entry signal |
| **Volume** | Confirms price moves; big move + high volume = stronger conviction |
            """)

# ─────────────────────────────────────────────────────────
# CRYPTO MARKETS
# ─────────────────────────────────────────────────────────
elif page == "Crypto Markets":
    st.header("🪙 Crypto Markets")
    st.caption("Prices via Yahoo Finance")

    crypto_symbols = {
        'BTC-USD': 'Bitcoin',    'ETH-USD': 'Ethereum',   'BNB-USD': 'BNB',
        'XRP-USD': 'XRP',        'ADA-USD': 'Cardano',     'SOL-USD': 'Solana',
        'DOGE-USD': 'Dogecoin',  'DOT-USD': 'Polkadot',    'AVAX-USD': 'Avalanche',
        'LINK-USD': 'Chainlink', 'MATIC-USD': 'Polygon',   'LTC-USD': 'Litecoin',
        'XLM-USD': 'Stellar',    'ATOM-USD': 'Cosmos',     'UNI7083-USD': 'Uniswap'
    }

    with st.spinner("Loading crypto data…"):
        crypto_data = data_fetcher.get_crypto_data(list(crypto_symbols.keys()))

    if crypto_data:
        # Top row metrics
        top_coins = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD']
        metric_cols = st.columns(len(top_coins))
        for col, sym in zip(metric_cols, top_coins):
            if sym in crypto_data:
                d = crypto_data[sym]
                with col:
                    st.metric(
                        crypto_symbols.get(sym, sym),
                        f"${d['price']:,.2f}",
                        delta=f"{d['change_pct']:+.2f}%"
                    )

        st.markdown("---")
        # Performance chart
        crypto_chart = create_crypto_market_chart(crypto_data)
        if crypto_chart:
            st.plotly_chart(crypto_chart, use_container_width=True)

        # Table
        st.subheader("📋 Full Market Table")
        rows = []
        for sym, label in crypto_symbols.items():
            if sym in crypto_data:
                d = crypto_data[sym]
                rows.append({
                    'Asset': label,
                    'Symbol': sym.replace('-USD', ''),
                    'Price ($)': f"${d['price']:,.4f}" if d['price'] < 1 else f"${d['price']:,.2f}",
                    'Change ($)': f"{d['change']:+,.4f}" if abs(d['change']) < 1 else f"{d['change']:+,.2f}",
                    'Change %': f"{d['change_pct']:+.2f}%",
                    'Direction': '🟢' if d['change'] >= 0 else '🔴'
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.error("Failed to load crypto data")

    st.markdown("---")
    st.subheader("📈 Crypto Price Chart")
    crypto_sym = st.selectbox("Select asset", list(crypto_symbols.keys()),
                               format_func=lambda x: crypto_symbols.get(x, x))
    crypto_period = st.select_slider("Period", ['7d', '1mo', '3mo', '6mo', '1y', '2y'], value='3mo')
    with st.spinner("Loading chart…"):
        c_chart = create_price_chart(crypto_sym, crypto_symbols.get(crypto_sym, crypto_sym),
                                     period=crypto_period, interval='1d')
    if c_chart:
        st.plotly_chart(c_chart, use_container_width=True)

    # Technical analysis on crypto
    st.markdown("---")
    st.subheader("🔬 Crypto Technical Analysis")
    ta_crypto_sym = st.selectbox("Symbol for TA", list(crypto_symbols.keys()),
                                  format_func=lambda x: crypto_symbols.get(x, x),
                                  key='crypto_ta')
    ta_crypto_period = st.select_slider("TA Period", ['1mo', '3mo', '6mo', '1y'], value='3mo',
                                         key='crypto_ta_period')
    with st.spinner("Building technical chart…"):
        cta_fig = create_technical_analysis_chart(
            ta_crypto_sym, period=ta_crypto_period, interval='1d',
            show_bb=True, show_rsi=True, show_macd=True, show_volume=True
        )
    if cta_fig:
        st.plotly_chart(cta_fig, use_container_width=True)

# ─────────────────────────────────────────────────────────
# ECONOMIC INDICATORS
# ─────────────────────────────────────────────────────────
elif page == "Economic Indicators":
    st.header("🌐 Economic Indicators & Macro")
    st.caption("Macro proxies sourced from ETF and index data via Yahoo Finance")

    with st.spinner("Loading economic indicators…"):
        eco_data = data_fetcher.get_economic_indicators()

    if eco_data:
        # Group by category
        categories = {}
        for ind in eco_data:
            cat = ind.get('category', 'Other')
            categories.setdefault(cat, []).append(ind)

        # Summary bar chart
        eco_chart = create_economic_dashboard_chart(eco_data)
        if eco_chart:
            st.plotly_chart(eco_chart, use_container_width=True)

        st.markdown("---")

        # Category sections
        for cat_name, inds in categories.items():
            st.subheader(f"🔹 {cat_name}")
            eco_cols = st.columns(min(len(inds), 4))
            for col, ind in zip(eco_cols, inds):
                with col:
                    delta_str = f"{ind['change_pct']:+.2f}%"
                    st.metric(
                        ind['label'],
                        f"${ind['price']:.2f}",
                        delta=delta_str
                    )
            # Full table for this category
            cat_rows = [{
                'Indicator': i['label'],
                'Price': f"${i['price']:.2f}",
                'Change %': f"{i['change_pct']:+.2f}%",
                'Trend': '🟢 Up' if i['change'] >= 0 else '🔴 Down'
            } for i in inds]
            with st.expander(f"View {cat_name} details"):
                st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # Key ratios / spreads
        st.subheader("📐 Key Macro Ratios")
        ratio_col1, ratio_col2, ratio_col3 = st.columns(3)

        # Consumer confidence proxy: XLY / XLP ratio
        xly = next((i for i in eco_data if i['symbol'] == 'XLY'), None)
        xlp = next((i for i in eco_data if i['symbol'] == 'XLP'), None)
        if xly and xlp and xlp['price'] > 0:
            ratio = xly['price'] / xlp['price']
            ratio_col1.metric(
                "Risk Appetite (XLY/XLP)",
                f"{ratio:.3f}",
                help="Above 1 = consumers spending on discretionary (risk-on)"
            )

        # HYG / LQD spread proxy
        hyg = next((i for i in eco_data if i['symbol'] == 'HYG'), None)
        lqd = next((i for i in eco_data if i['symbol'] == 'LQD'), None)
        if hyg and lqd and lqd['price'] > 0:
            spread = hyg['price'] / lqd['price']
            ratio_col2.metric(
                "Credit Risk Proxy (HYG/LQD)",
                f"{spread:.3f}",
                help="Higher = credit spreads tightening (risk-on)"
            )

        # TLT/SHY (duration proxy)
        tlt = next((i for i in eco_data if i['symbol'] == 'TLT'), None)
        shy = next((i for i in eco_data if i['symbol'] == 'SHY'), None)
        if tlt and shy and shy['price'] > 0:
            dur_ratio = tlt['price'] / shy['price']
            ratio_col3.metric(
                "Duration Ratio (TLT/SHY)",
                f"{dur_ratio:.3f}",
                help="High = market expects lower long rates (risk-off)"
            )

        st.markdown("---")
        st.subheader("📈 Indicator Price Chart")
        eco_sym = st.selectbox("Select indicator",
                                [i['symbol'] for i in eco_data],
                                format_func=lambda x: next(
                                    (i['label'] for i in eco_data if i['symbol'] == x), x))
        eco_period = st.select_slider("Period",
                                       ['1mo', '3mo', '6mo', '1y', '2y', '5y'],
                                       value='1y')
        with st.spinner("Loading chart…"):
            eco_fig = create_price_chart(eco_sym, eco_sym, period=eco_period, interval='1d')
        if eco_fig:
            st.plotly_chart(eco_fig, use_container_width=True)
    else:
        st.error("Failed to load economic indicator data")

elif page == "Portfolio":
    st.header("💼 Portfolio Management")
    
    # User ID input
    user_id = st.sidebar.text_input("User ID", value="default_user")
    
    if not db_initialized:
        st.error("Database not available for portfolio functionality.")
        st.stop()
    
    # Get user portfolios
    portfolios = db_manager.get_user_portfolios(user_id)
    
    # Portfolio selection or creation
    col1, col2 = st.columns([2, 1])
    with col1:
        if portfolios:
            selected_portfolio = st.selectbox(
                "Select Portfolio",
                options=[p['id'] for p in portfolios],
                format_func=lambda x: next(p['name'] for p in portfolios if p['id'] == x)
            )
        else:
            selected_portfolio = None
            st.info("No portfolios found. Create one below.")
    
    with col2:
        if st.button("🔄 Refresh Portfolios"):
            st.rerun()
    
    # Create new portfolio
    with st.expander("➕ Create New Portfolio"):
        with st.form("create_portfolio"):
            portfolio_name = st.text_input("Portfolio Name")
            portfolio_description = st.text_area("Description (optional)")
            initial_cash = st.number_input("Initial Cash Balance", min_value=0.0, value=10000.0, step=100.0)
            
            if st.form_submit_button("Create Portfolio"):
                if portfolio_name:
                    portfolio_id = db_manager.create_portfolio(user_id, portfolio_name, portfolio_description, initial_cash)
                    if portfolio_id:
                        st.success(f"Portfolio '{portfolio_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create portfolio")
                else:
                    st.error("Portfolio name is required")
    
    # Portfolio management
    if selected_portfolio:
        portfolio_info = next(p for p in portfolios if p['id'] == selected_portfolio)
        
        st.subheader(f"📊 {portfolio_info['name']}")
        st.markdown(f"*{portfolio_info['description']}*")
        
        # Get current prices for portfolio calculation
        holdings = db_manager.get_portfolio_holdings(selected_portfolio)
        symbols = list(set([h['symbol'] for h in holdings]))
        
        current_prices = {}
        if symbols:
            for symbol in symbols:
                data = data_fetcher._fetch_ticker_data(symbol)
                if data:
                    current_prices[symbol] = data['price']
        
        # Calculate portfolio value
        portfolio_value = db_manager.calculate_portfolio_value(selected_portfolio, current_prices)
        
        # Portfolio summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Value", f"${portfolio_value['total_value']:,.2f}")
        with col2:
            st.metric("Total Cost", f"${portfolio_value['total_cost']:,.2f}")
        with col3:
            gain_loss_color = "normal" if portfolio_value['total_gain_loss'] >= 0 else "inverse"
            st.metric(
                "Gain/Loss", 
                f"${portfolio_value['total_gain_loss']:,.2f}",
                delta=f"{portfolio_value['total_gain_loss_pct']:.2f}%"
            )
        with col4:
            st.metric("Cash Balance", f"${portfolio_info['cash_balance']:,.2f}")
        
        # Portfolio Analytics Tabs
        if portfolio_value['holdings']:
            p_tab1, p_tab2, p_tab3 = st.tabs(["Holdings", "Allocation", "Performance"])
            with p_tab1:
                pass  # filled below
            with p_tab2:
                alloc_fig = create_portfolio_allocation_chart(portfolio_value['holdings'])
                if alloc_fig:
                    st.plotly_chart(alloc_fig, use_container_width=True)
            with p_tab3:
                perf_period = st.selectbox("Performance period", ['1mo', '3mo', '6mo', '1y'], index=1)
                with st.spinner("Loading performance chart…"):
                    perf_fig = create_portfolio_performance_chart(portfolio_value['holdings'], perf_period)
                if perf_fig:
                    st.plotly_chart(perf_fig, use_container_width=True)

        # Holdings table
        st.subheader("📈 Current Holdings")
        if portfolio_value['holdings']:
            holdings_df = pd.DataFrame(portfolio_value['holdings'])
            
            # Format columns for display
            holdings_df['avg_cost'] = holdings_df['avg_cost'].apply(lambda x: f"${x:.2f}")
            holdings_df['current_price'] = holdings_df['current_price'].apply(lambda x: f"${x:.2f}")
            holdings_df['market_value'] = holdings_df['market_value'].apply(lambda x: f"${x:,.2f}")
            holdings_df['cost_basis'] = holdings_df['cost_basis'].apply(lambda x: f"${x:,.2f}")
            holdings_df['gain_loss'] = holdings_df['gain_loss'].apply(lambda x: f"${x:,.2f}")
            holdings_df['gain_loss_pct'] = holdings_df['gain_loss_pct'].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(
                holdings_df[['symbol', 'quantity', 'avg_cost', 'current_price', 'market_value', 'gain_loss', 'gain_loss_pct']],
                use_container_width=True
            )
        else:
            st.info("No holdings in this portfolio.")
        
        # Add/Sell positions
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Buy Position")
            with st.form("buy_position"):
                _default_syms = [
                    'SPY', 'QQQ', 'DIA', 'IWM', 'GLD', 'SLV', 'USO', 'TLT', 'HYG',
                    'XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLU', 'XLY', 'XLP',
                    'BTC-USD', 'ETH-USD', 'SOL-USD',
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B',
                    'ES=F', 'NQ=F', 'GC=F', 'CL=F', 'EURUSD=X', 'GBPUSD=X'
                ]
                _extra = [h['symbol'] for h in holdings if h['symbol'] not in _default_syms]
                buy_symbol = st.selectbox("Symbol", _default_syms + _extra)
                buy_quantity = st.number_input("Quantity", min_value=0.1, value=1.0, step=0.1)
                buy_price = st.number_input("Price per Share", min_value=0.01, value=100.0, step=0.01)
                buy_notes = st.text_input("Notes (optional)")
                
                if st.form_submit_button("Buy"):
                    success = db_manager.add_holding(selected_portfolio, buy_symbol, buy_quantity, buy_price, buy_notes)
                    if success:
                        st.success(f"Added {buy_quantity} shares of {buy_symbol}")
                        st.rerun()
                    else:
                        st.error("Failed to add position")
        
        with col2:
            st.subheader("📉 Sell Position")
            current_symbols = [h['symbol'] for h in holdings if h['quantity'] > 0]
            
            if current_symbols:
                with st.form("sell_position"):
                    sell_symbol = st.selectbox("Symbol", current_symbols)
                    
                    # Get current holding quantity
                    current_holding = next((h for h in holdings if h['symbol'] == sell_symbol), None)
                    max_quantity = current_holding['quantity'] if current_holding else 0
                    
                    sell_quantity = st.number_input(
                        f"Quantity (max: {max_quantity})", 
                        min_value=0.1, 
                        max_value=float(max_quantity), 
                        value=min(1.0, float(max_quantity)), 
                        step=0.1
                    )
                    sell_price = st.number_input("Price per Share", min_value=0.01, value=100.0, step=0.01)
                    sell_notes = st.text_input("Notes (optional)")
                    
                    if st.form_submit_button("Sell"):
                        success = db_manager.sell_holding(selected_portfolio, sell_symbol, sell_quantity, sell_price, sell_notes)
                        if success:
                            st.success(f"Sold {sell_quantity} shares of {sell_symbol}")
                            st.rerun()
                        else:
                            st.error("Failed to sell position")
            else:
                st.info("No positions to sell")
        
        # Transaction history
        st.subheader("📋 Transaction History")
        transactions = db_manager.get_portfolio_transactions(selected_portfolio)
        if transactions:
            transactions_df = pd.DataFrame(transactions)
            transactions_df['date'] = transactions_df['date'].dt.strftime('%Y-%m-%d %H:%M')
            transactions_df['total_amount'] = transactions_df['total_amount'].apply(lambda x: f"${x:,.2f}")
            transactions_df['price'] = transactions_df['price'].apply(lambda x: f"${x:.2f}")
            
            st.dataframe(
                transactions_df[['date', 'symbol', 'type', 'quantity', 'price', 'total_amount', 'notes']],
                use_container_width=True
            )
        else:
            st.info("No transactions found.")

elif page == "Database Stats":
    st.header("📊 Database Statistics")
    
    if not db_initialized:
        st.error("Database not available.")
        st.stop()
    
    # Get market statistics
    stats = db_manager.get_market_statistics()
    
    if stats:
        st.subheader("Data Storage Summary")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Index Records", stats.get('index_records', 0))
        with col2:
            st.metric("Commodity Records", stats.get('commodity_records', 0))
        with col3:
            st.metric("Bond Records", stats.get('bond_records', 0))
        with col4:
            st.metric("VIX Records", stats.get('vix_records', 0))
        with col5:
            st.metric("Sector Records", stats.get('sector_records', 0))
        
        # Most volatile symbols
        if 'most_volatile' in stats and stats['most_volatile']:
            st.subheader("Most Volatile Symbols")
            volatile_df = pd.DataFrame(stats['most_volatile'])
            st.dataframe(volatile_df, use_container_width=True)
    
    # Database connection test
    st.subheader("Database Connection")
    try:
        session = db_manager.get_session()
        session.close()
        st.success("✅ Database connection successful")
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
    
    # Manual data cleanup
    st.subheader("Database Management")
    if st.button("Clean Old Data (>7 days)"):
        session = None
        try:
            session = db_manager.get_session()
            from database import FinancialData
            cutoff_date = datetime.now() - timedelta(days=7)
            
            deleted = session.query(FinancialData).filter(
                FinancialData.timestamp < cutoff_date
            ).delete()
            
            session.commit()
            session.close()
            
            st.success(f"Cleaned {deleted} old records")
        except Exception as e:
            st.error(f"Error cleaning data: {str(e)}")
            if session:
                session.rollback()
                session.close()