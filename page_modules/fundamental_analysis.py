import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json

from utils.fundamentals import fundamentals_fetcher
from utils.ai_valuation import ai_valuation_analyzer
from database import db_manager

def create_earnings_trend_chart(metrics, metric_name, title):
    """Create a line chart for earnings metrics over time"""
    try:
        if metric_name not in metrics or not metrics[metric_name]:
            return None
        
        dates = metrics.get('dates', [])
        values = metrics[metric_name]
        
        # Convert to billions for readability
        values_billions = [v/1e9 if v is not None else None for v in values]
        
        # Reverse to show oldest to newest
        dates = list(reversed(dates))
        values_billions = list(reversed(values_billions))
        
        # Convert dates to strings if they're not already
        date_strings = [str(d) if not isinstance(d, str) else d for d in dates]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=date_strings,
            y=values_billions,
            mode='lines+markers',
            name=metric_name,
            line=dict(width=3, color='#1f77b4'),
            marker=dict(size=8),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Period',
            yaxis_title='Amount (Billions $)',
            hovermode='x unified',
            template='plotly_white',
            height=400
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating chart: {str(e)}")
        return None

def create_margin_trend_chart(metrics):
    """Create a chart showing profit margins over time"""
    try:
        if 'revenue' not in metrics or 'net_income' not in metrics:
            return None
        
        dates = metrics.get('dates', [])
        revenue = metrics['revenue']
        net_income = metrics['net_income']
        
        # Calculate margins
        margins = []
        for i in range(len(revenue)):
            if revenue[i] and revenue[i] != 0 and net_income[i]:
                margin = (net_income[i] / revenue[i]) * 100
                margins.append(margin)
            else:
                margins.append(None)
        
        # Reverse to show oldest to newest
        dates = list(reversed(dates))
        margins = list(reversed(margins))
        
        date_strings = [str(d) if not isinstance(d, str) else d for d in dates]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=date_strings,
            y=margins,
            mode='lines+markers',
            name='Profit Margin',
            line=dict(width=3, color='#2ca02c'),
            marker=dict(size=8),
            fill='tozeroy',
            fillcolor='rgba(44, 160, 44, 0.1)'
        ))
        
        fig.update_layout(
            title='Profit Margin Trend',
            xaxis_title='Period',
            yaxis_title='Margin (%)',
            hovermode='x unified',
            template='plotly_white',
            height=400
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating margin chart: {str(e)}")
        return None

def create_metrics_comparison_chart(metrics):
    """Create a multi-metric comparison chart"""
    try:
        dates = metrics.get('dates', [])
        
        # Prepare data
        data_dict = {'Date': [str(d) if not isinstance(d, str) else d for d in reversed(dates)]}
        
        if 'revenue' in metrics and metrics['revenue']:
            data_dict['Revenue'] = [v/1e9 if v else 0 for v in reversed(metrics['revenue'])]
        if 'net_income' in metrics and metrics['net_income']:
            data_dict['Net Income'] = [v/1e9 if v else 0 for v in reversed(metrics['net_income'])]
        if 'operating_income' in metrics and metrics['operating_income']:
            data_dict['Operating Income'] = [v/1e9 if v else 0 for v in reversed(metrics['operating_income'])]
        
        df = pd.DataFrame(data_dict)
        
        fig = go.Figure()
        
        for col in df.columns:
            if col != 'Date':
                fig.add_trace(go.Bar(
                    name=col,
                    x=df['Date'],
                    y=df[col]
                ))
        
        fig.update_layout(
            title='Financial Metrics Comparison',
            xaxis_title='Period',
            yaxis_title='Amount (Billions $)',
            barmode='group',
            template='plotly_white',
            height=500
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating comparison chart: {str(e)}")
        return None

def render_fundamental_analysis_page():
    """Main function to render the fundamental analysis page"""
    
    st.header("📊 Fundamental Analysis & AI Valuation")
    
    # Stock selection
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        stock_symbol = st.text_input(
            "Enter Stock Symbol", 
            value="AAPL",
            help="Enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL)"
        ).upper()
    
    with col2:
        period = st.selectbox(
            "Data Period",
            ["quarterly", "annual"],
            help="Select quarterly for more frequent data or annual for yearly data"
        )
    
    with col3:
        years = st.slider(
            "Years of Data",
            min_value=1,
            max_value=5,
            value=5,
            help="Number of years of historical data to analyze"
        )
    
    if not stock_symbol:
        st.warning("Please enter a stock symbol to begin analysis.")
        return
    
    # Fetch fundamental data
    with st.spinner(f"Fetching fundamental data for {stock_symbol}..."):
        metrics = fundamentals_fetcher.extract_key_metrics(stock_symbol, period=period, years=years)
    
    if not metrics:
        st.error(f"Unable to fetch fundamental data for {stock_symbol}. Please check the symbol and try again.")
        return
    
    # Company Information Section
    st.subheader(f"📋 {metrics.get('company_name', stock_symbol)}")
    
    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
    with info_col1:
        st.metric("Sector", metrics.get('sector', 'N/A'))
    with info_col2:
        st.metric("Industry", metrics.get('industry', 'N/A'))
    with info_col3:
        if metrics.get('current_price'):
            st.metric("Current Price", f"${metrics['current_price']:.2f}")
    with info_col4:
        if metrics.get('market_cap'):
            market_cap_b = metrics['market_cap'] / 1e9
            st.metric("Market Cap", f"${market_cap_b:.2f}B")
    
    st.markdown("---")
    
    # Key Valuation Metrics
    st.subheader("💰 Key Valuation Metrics")
    
    val_col1, val_col2, val_col3, val_col4, val_col5 = st.columns(5)
    with val_col1:
        if metrics.get('pe_ratio'):
            st.metric("P/E Ratio", f"{metrics['pe_ratio']:.2f}")
        else:
            st.metric("P/E Ratio", "N/A")
    with val_col2:
        if metrics.get('forward_pe'):
            st.metric("Forward P/E", f"{metrics['forward_pe']:.2f}")
        else:
            st.metric("Forward P/E", "N/A")
    with val_col3:
        if metrics.get('peg_ratio'):
            st.metric("PEG Ratio", f"{metrics['peg_ratio']:.2f}")
        else:
            st.metric("PEG Ratio", "N/A")
    with val_col4:
        if metrics.get('price_to_book'):
            st.metric("P/B Ratio", f"{metrics['price_to_book']:.2f}")
        else:
            st.metric("P/B Ratio", "N/A")
    with val_col5:
        if metrics.get('dividend_yield'):
            st.metric("Dividend Yield", f"{metrics['dividend_yield']*100:.2f}%")
        else:
            st.metric("Dividend Yield", "N/A")
    
    st.markdown("---")
    
    # Financial Trends Visualization
    st.subheader("📈 5-Year Financial Trends")
    
    # Revenue trend
    if 'revenue' in metrics:
        revenue_chart = create_earnings_trend_chart(metrics, 'revenue', 'Revenue Trend')
        if revenue_chart:
            st.plotly_chart(revenue_chart, use_container_width=True)
    
    # Net Income and Operating Income
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        if 'net_income' in metrics:
            ni_chart = create_earnings_trend_chart(metrics, 'net_income', 'Net Income Trend')
            if ni_chart:
                st.plotly_chart(ni_chart, use_container_width=True)
    
    with chart_col2:
        if 'operating_income' in metrics:
            oi_chart = create_earnings_trend_chart(metrics, 'operating_income', 'Operating Income Trend')
            if oi_chart:
                st.plotly_chart(oi_chart, use_container_width=True)
    
    # Profit Margin Trend
    margin_chart = create_margin_trend_chart(metrics)
    if margin_chart:
        st.plotly_chart(margin_chart, use_container_width=True)
    
    # Cash Flow
    if 'free_cashflow' in metrics:
        fcf_chart = create_earnings_trend_chart(metrics, 'free_cashflow', 'Free Cash Flow Trend')
        if fcf_chart:
            st.plotly_chart(fcf_chart, use_container_width=True)
    
    # Comparison chart
    comparison_chart = create_metrics_comparison_chart(metrics)
    if comparison_chart:
        st.plotly_chart(comparison_chart, use_container_width=True)
    
    st.markdown("---")
    
    # AI-Powered Valuation Analysis
    st.subheader("🤖 AI-Powered Valuation Analysis")
    
    st.markdown("""
    Choose an investment framework for AI-powered analysis. Each model provides unique insights:
    - **Comprehensive**: Balanced analysis covering all aspects
    - **Growth Investing**: Focus on revenue growth, scalability, and future potential
    - **Value Investing**: Focus on intrinsic value, safety, and downside protection
    - **DCF Valuation**: Discounted cash flow analysis with fair value estimation
    """)
    
    analysis_col1, analysis_col2 = st.columns([1, 3])
    
    with analysis_col1:
        valuation_model = st.selectbox(
            "Analysis Framework",
            ["comprehensive", "growth", "value", "dcf"],
            format_func=lambda x: {
                "comprehensive": "📊 Comprehensive",
                "growth": "🚀 Growth Investing",
                "value": "💎 Value Investing",
                "dcf": "🧮 DCF Valuation"
            }[x]
        )
        
        run_analysis = st.button("🔍 Run AI Analysis", type="primary", use_container_width=True)
        
        # Check for cached analysis
        cached_analyses = db_manager.get_fundamental_analysis(stock_symbol, valuation_model, limit=1)
        if cached_analyses and len(cached_analyses) > 0:
            st.caption(f"💾 Cached analysis available from {cached_analyses[0]['created_at'].strftime('%Y-%m-%d %H:%M')}")
            use_cached = st.checkbox("Use cached analysis", value=False)
        else:
            use_cached = False
    
    with analysis_col2:
        if run_analysis or use_cached:
            if use_cached and cached_analyses:
                # Use cached analysis
                analysis_result = cached_analyses[0]['analysis_result']
                st.success("Using cached AI analysis")
            else:
                # Run new AI analysis
                with st.spinner(f"Running {valuation_model} analysis with AI..."):
                    analysis_result = ai_valuation_analyzer.analyze_fundamentals(metrics, valuation_model)
                
                if analysis_result and 'error' not in analysis_result:
                    # Store in database
                    db_manager.store_fundamental_analysis(
                        stock_symbol,
                        valuation_model,
                        analysis_result,
                        period
                    )
                    st.success("AI analysis complete!")
            
            # Display AI Analysis Results
            if analysis_result:
                if 'error' in analysis_result:
                    st.error(f"Analysis error: {analysis_result['error']}")
                else:
                    # Display results based on model type
                    if valuation_model == "comprehensive":
                        display_comprehensive_analysis(analysis_result)
                    elif valuation_model == "growth":
                        display_growth_analysis(analysis_result)
                    elif valuation_model == "value":
                        display_value_analysis(analysis_result)
                    elif valuation_model == "dcf":
                        display_dcf_analysis(analysis_result)
        else:
            st.info("👈 Select an analysis framework and click 'Run AI Analysis' to get AI-powered insights.")
    
    st.markdown("---")
    
    # Growth Rates Section
    st.subheader("📊 Growth Metrics")
    growth_rates = fundamentals_fetcher.calculate_growth_rates(metrics)
    
    if growth_rates:
        growth_col1, growth_col2 = st.columns(2)
        
        with growth_col1:
            if 'revenue_cagr' in growth_rates:
                st.metric("Revenue CAGR", f"{growth_rates['revenue_cagr']:.2f}%")
            
            if 'revenue_yoy_growth' in growth_rates:
                avg_yoy = sum(growth_rates['revenue_yoy_growth']) / len(growth_rates['revenue_yoy_growth'])
                st.metric("Avg YoY Revenue Growth", f"{avg_yoy:.2f}%")
        
        with growth_col2:
            if 'profit_margins' in growth_rates:
                latest_margin = growth_rates['profit_margins'][0] if growth_rates['profit_margins'] else 0
                st.metric("Latest Profit Margin", f"{latest_margin:.2f}%")

def display_comprehensive_analysis(result):
    """Display comprehensive analysis results"""
    st.markdown("### 📊 Comprehensive Investment Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rating = result.get('overall_rating', 'N/A')
        rating_color = {
            'Strong Buy': '🟢', 'Buy': '🟢',
            'Hold': '🟡',
            'Sell': '🔴', 'Strong Sell': '🔴'
        }.get(rating, '⚪')
        st.metric("Overall Rating", f"{rating_color} {rating}")
    
    with col2:
        confidence = result.get('confidence_score', 0)
        st.metric("Confidence Score", f"{confidence}/100")
    
    with col3:
        if 'target_price_range' in result:
            target = result['target_price_range']
            st.metric("Target Price", f"${target.get('mid', 'N/A')}")
    
    # Key insights
    exp_col1, exp_col2 = st.columns(2)
    
    with exp_col1:
        with st.expander("✅ Key Strengths", expanded=True):
            for strength in result.get('key_strengths', []):
                st.markdown(f"• {strength}")
    
    with exp_col2:
        with st.expander("⚠️ Key Weaknesses", expanded=True):
            for weakness in result.get('key_weaknesses', []):
                st.markdown(f"• {weakness}")
    
    # Detailed analysis
    with st.expander("📈 Revenue Analysis", expanded=False):
        st.write(result.get('revenue_analysis', 'N/A'))
    
    with st.expander("💰 Profitability Analysis", expanded=False):
        st.write(result.get('profitability_analysis', 'N/A'))
    
    with st.expander("🎯 Investment Thesis", expanded=True):
        st.write(result.get('investment_thesis', 'N/A'))
    
    with st.expander("⚠️ Risk Factors", expanded=False):
        for risk in result.get('risk_factors', []):
            st.markdown(f"• {risk}")

def display_growth_analysis(result):
    """Display growth investing analysis results"""
    st.markdown("### 🚀 Growth Investing Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rating = result.get('growth_rating', 'N/A')
        st.metric("Growth Rating", rating)
    
    with col2:
        confidence = result.get('confidence_score', 0)
        st.metric("Confidence Score", f"{confidence}/100")
    
    with col3:
        growth_rate = result.get('estimated_annual_growth_rate', 'N/A')
        st.metric("Est. Growth Rate", growth_rate)
    
    with st.expander("🚀 Growth Drivers", expanded=True):
        for driver in result.get('growth_drivers', []):
            st.markdown(f"• {driver}")
    
    with st.expander("📈 Revenue Growth Analysis", expanded=True):
        st.write(result.get('revenue_growth_analysis', 'N/A'))
    
    with st.expander("💡 Investment Recommendation", expanded=True):
        st.write(result.get('investment_recommendation', 'N/A'))

def display_value_analysis(result):
    """Display value investing analysis results"""
    st.markdown("### 💎 Value Investing Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rating = result.get('value_rating', 'N/A')
        st.metric("Value Rating", rating)
    
    with col2:
        margin = result.get('margin_of_safety', 'N/A')
        st.metric("Margin of Safety", margin)
    
    with col3:
        fair_value = result.get('fair_value_estimate', 'N/A')
        st.metric("Fair Value Est.", fair_value)
    
    with st.expander("💎 Intrinsic Value Assessment", expanded=True):
        st.write(result.get('intrinsic_value_assessment', 'N/A'))
    
    with st.expander("🏰 Economic Moat", expanded=True):
        st.write(result.get('economic_moat', 'N/A'))
    
    with st.expander("💡 Investment Recommendation", expanded=True):
        st.write(result.get('investment_recommendation', 'N/A'))

def display_dcf_analysis(result):
    """Display DCF valuation analysis results"""
    st.markdown("### 🧮 DCF Valuation Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rating = result.get('dcf_valuation_rating', 'N/A')
        st.metric("Valuation", rating)
    
    with col2:
        fair_value = result.get('dcf_fair_value', 'N/A')
        st.metric("DCF Fair Value", f"${fair_value}" if isinstance(fair_value, (int, float)) else fair_value)
    
    with col3:
        discount_rate = result.get('discount_rate', 'N/A')
        st.metric("Discount Rate", discount_rate)
    
    with col4:
        terminal_rate = result.get('terminal_growth_rate', 'N/A')
        st.metric("Terminal Growth", terminal_rate)
    
    # Sensitivity analysis
    if 'sensitivity_analysis' in result:
        sensitivity = result['sensitivity_analysis']
        sens_col1, sens_col2, sens_col3 = st.columns(3)
        
        with sens_col1:
            conservative = sensitivity.get('conservative', 'N/A')
            st.metric("Conservative", f"${conservative}" if isinstance(conservative, (int, float)) else conservative)
        with sens_col2:
            base = sensitivity.get('base', 'N/A')
            st.metric("Base Case", f"${base}" if isinstance(base, (int, float)) else base)
        with sens_col3:
            optimistic = sensitivity.get('optimistic', 'N/A')
            st.metric("Optimistic", f"${optimistic}" if isinstance(optimistic, (int, float)) else optimistic)
    
    with st.expander("📊 Cash Flow Analysis", expanded=True):
        st.write(result.get('cash_flow_analysis', 'N/A'))
    
    with st.expander("🎯 Key Value Drivers", expanded=True):
        for driver in result.get('key_value_drivers', []):
            st.markdown(f"• {driver}")
    
    with st.expander("💡 Investment Recommendation", expanded=True):
        st.write(result.get('investment_recommendation', 'N/A'))

# Run the page
if __name__ == "__main__":
    render_fundamental_analysis_page()
