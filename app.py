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
from utils.charts import create_price_chart, create_performance_chart, create_enhanced_price_chart, create_chart_from_db_data
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
page = st.sidebar.selectbox("Navigate", ["Live Dashboard", "Historical Data", "Fundamental Analysis", "Market Alerts", "News", "Portfolio", "Database Stats"])

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
        # VIX Chart
        if vix_data:
            vix_chart = create_enhanced_price_chart('^VIX', '30d', use_yfinance=True)
            if vix_chart:
                st.plotly_chart(vix_chart, use_container_width=True)

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
    all_sectors = data_fetcher.get_sector_etfs(['XLK', 'XLV', 'XLE', 'XLF'])
    if all_sectors:
        sector_chart = create_performance_chart(all_sectors)
        if sector_chart:
            st.plotly_chart(sector_chart, use_container_width=True)

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
            ['SPY', 'QQQ', 'DIA', 'GLD', 'SLV', 'USO', 'UNG', '^VIX', 'XLK', 'XLV', 'XLE', 'XLF']
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
                ['SPY', 'QQQ', 'DIA', 'GLD', 'SLV', 'USO', 'UNG', '^VIX', 'XLK', 'XLV', 'XLE', 'XLF']
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
            all_symbols = ['SPY', 'QQQ', 'DIA', 'GLD', 'SLV', 'USO', 'UNG', '^VIX', 'XLK', 'XLV', 'XLE', 'XLF']
            
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
                ['SPY', 'QQQ', 'DIA', 'GLD', 'SLV', 'USO', 'UNG', '^VIX', 'XLK', 'XLV', 'XLE', 'XLF']
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
                buy_symbol = st.selectbox(
                    "Symbol",
                    ['SPY', 'QQQ', 'DIA', 'GLD', 'SLV', 'USO', 'UNG', '^VIX', 'XLK', 'XLV', 'XLE', 'XLF'] +
                    [h['symbol'] for h in holdings if h['symbol'] not in ['SPY', 'QQQ', 'DIA', 'GLD', 'SLV', 'USO', 'UNG', '^VIX', 'XLK', 'XLV', 'XLE', 'XLF']]
                )
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