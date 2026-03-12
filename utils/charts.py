import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import streamlit as st
import logging

logger = logging.getLogger(__name__)


def create_price_chart(symbol, title, period="1mo", interval="1d"):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return None
        fig = go.Figure()
        if interval in ['1m', '5m', '15m', '30m'] and len(hist) > 100:
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'],
                                     mode='lines', name=symbol,
                                     line=dict(color='blue', width=2)))
        else:
            fig.add_trace(go.Candlestick(
                x=hist.index, open=hist['Open'], high=hist['High'],
                low=hist['Low'], close=hist['Close'], name=symbol))
        fig.update_layout(title=title, xaxis_title="Date/Time",
                          yaxis_title="Price", template="plotly_white",
                          height=400, showlegend=False,
                          xaxis_rangeslider_visible=False)
        return fig
    except Exception as e:
        logger.error(f"Error creating price chart for {symbol}: {str(e)}")
        return None


def create_performance_chart(data_dict):
    try:
        if not data_dict:
            return None
        symbols = list(data_dict.keys())
        changes = [data_dict[s]['change_pct'] for s in symbols]
        colors  = ['green' if c >= 0 else 'red' for c in changes]
        fig = go.Figure(go.Bar(
            x=symbols, y=changes,
            marker_color=colors,
            text=[f"{c:+.2f}%" for c in changes],
            textposition='auto'))
        fig.update_layout(title="Sector Performance Comparison (% Change)",
                          xaxis_title="Sector ETFs", yaxis_title="% Change",
                          template="plotly_white", height=400, showlegend=False)
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.7)
        return fig
    except Exception as e:
        logger.error(f"Error creating performance chart: {str(e)}")
        return None


def create_vix_interpretation_chart(vix_value):
    try:
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=vix_value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "VIX Volatility Level"},
            delta={'reference': 20},
            gauge={
                'axis': {'range': [0, 60]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 15],  'color': "lightgreen"},
                    {'range': [15, 25], 'color': "yellow"},
                    {'range': [25, 35], 'color': "orange"},
                    {'range': [35, 60], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75, 'value': 30
                }
            }
        ))
        fig.update_layout(height=300, template="plotly_white")
        return fig
    except Exception as e:
        logger.error(f"Error creating VIX gauge chart: {str(e)}")
        return None


def create_yield_curve_chart(yields_dict=None):
    """
    Create a live US Treasury yield curve chart using real data.
    yields_dict: {'3M': {'yield': x, ...}, '5Y': ..., '10Y': ..., '30Y': ...}
    Supplements the provided data with 2Y and 1Y fetched on the fly when needed.
    """
    try:
        # Always try to fetch a rich curve from yfinance directly
        symbols = {
            '3M': '^IRX', '2Y': '^UST2Y', '5Y': '^FVX',
            '10Y': '^TNX', '30Y': '^TYX'
        }
        live_yields = {}
        for label, sym in symbols.items():
            try:
                t = yf.Ticker(sym)
                h = t.history(period="5d")
                if not h.empty:
                    live_yields[label] = float(h['Close'].iloc[-1])
            except Exception:
                pass

        # Fall back to passed-in dict for any missing
        if yields_dict:
            for label, d in yields_dict.items():
                if label not in live_yields:
                    live_yields[label] = d['yield'] if isinstance(d, dict) else d

        if not live_yields:
            return None

        order  = ['3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']
        labels = [m for m in order if m in live_yields]
        values = [live_yields[m] for m in labels]

        # Colour: inverted curve = red, normal = blue gradient
        is_inverted = len(values) >= 2 and values[0] > values[-1]
        line_color  = 'red' if is_inverted else 'royalblue'
        title_suffix = " ⚠️ INVERTED" if is_inverted else ""

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=labels, y=values, mode='lines+markers',
            name='US Treasury Yield Curve',
            line=dict(color=line_color, width=3),
            marker=dict(size=9, color=line_color),
            hovertemplate='%{x}: %{y:.2f}%<extra></extra>'
        ))
        fig.update_layout(
            title=f"US Treasury Yield Curve{title_suffix}",
            xaxis_title="Maturity", yaxis_title="Yield (%)",
            template="plotly_white", height=400, showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating yield curve chart: {str(e)}")
        return None


def create_correlation_heatmap(symbols, period="3mo"):
    try:
        data = {}
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            if not hist.empty:
                data[symbol] = hist['Close'].pct_change().dropna()
        if not data:
            return None
        df = pd.DataFrame(data)
        corr = df.corr()
        fig = px.imshow(
            corr, text_auto=".2f", aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1,
            title="Asset Correlation Matrix"
        )
        fig.update_layout(height=500, template="plotly_white")
        return fig
    except Exception as e:
        logger.error(f"Error creating correlation heatmap: {str(e)}")
        return None


def create_volume_chart(symbol, period="1mo"):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty or 'Volume' not in hist.columns:
            return None
        fig = go.Figure(go.Bar(x=hist.index, y=hist['Volume'],
                               name='Volume', marker_color='lightblue'))
        fig.update_layout(title=f"{symbol} Trading Volume",
                          xaxis_title="Date", yaxis_title="Volume",
                          template="plotly_white", height=300, showlegend=False)
        return fig
    except Exception as e:
        logger.error(f"Error creating volume chart for {symbol}: {str(e)}")
        return None


def create_chart_from_db_data(df, symbol, interval_name):
    try:
        if df.empty:
            return None
        fig = go.Figure(go.Scatter(
            x=df['timestamp'], y=df['price'],
            mode='lines+markers', name=f'{symbol} Price',
            line=dict(color='blue', width=2), marker=dict(size=4)))
        fig.update_layout(
            title=f"{symbol} - {interval_name} (From Database)",
            xaxis_title="Time", yaxis_title="Price ($)",
            template="plotly_white", height=400, showlegend=False,
            xaxis=dict(type='date', tickformat='%Y-%m-%d %H:%M'))
        return fig
    except Exception as e:
        logger.error(f"Error creating chart from database data: {str(e)}")
        return None


def create_enhanced_price_chart(symbol, interval_key, use_yfinance=True):
    try:
        from utils.intervals import FinanceIntervals
        params = FinanceIntervals.get_yfinance_params(interval_key)
        title  = FinanceIntervals.get_chart_title(symbol, interval_key)
        if not params or not use_yfinance:
            return None
        return create_price_chart(symbol=symbol, title=title,
                                   period=params['period'], interval=params['interval'])
    except Exception as e:
        logger.error(f"Error creating enhanced price chart for {symbol}: {str(e)}")
        return None


def create_risk_metrics_chart(risk_data):
    """
    Create a visual summary of risk metrics using gauge + bar charts.
    """
    try:
        if not risk_data:
            return None

        fig = go.Figure()

        metrics = {
            'Beta': risk_data.get('beta', 0),
            'Sharpe': risk_data.get('sharpe_ratio', 0),
            'Sortino': risk_data.get('sortino_ratio', 0),
            'Calmar': risk_data.get('calmar_ratio', 0),
        }
        labels = list(metrics.keys())
        values = list(metrics.values())
        colors = ['green' if v > 0 else 'red' for v in values]

        fig.add_trace(go.Bar(
            x=labels, y=values,
            marker_color=colors,
            text=[f"{v:.3f}" for v in values],
            textposition='auto'
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)
        fig.update_layout(
            title=f"Risk Ratios — {risk_data.get('symbol', '')} vs {risk_data.get('benchmark', '^GSPC')}",
            yaxis_title="Value", template="plotly_white",
            height=350, showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating risk metrics chart: {str(e)}")
        return None


def create_drawdown_chart(symbol, period='1y'):
    """Create a rolling drawdown chart for a symbol."""
    try:
        hist = yf.download(symbol, period=period, progress=False, auto_adjust=True)
        if hist.empty:
            return None
        prices = hist['Close'].squeeze()
        returns = prices.pct_change().dropna()
        cum = (1 + returns).cumprod()
        roll_max = cum.expanding().max()
        drawdown = (cum - roll_max) / roll_max * 100

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=drawdown.index, y=drawdown.values,
            fill='tozeroy', mode='lines',
            line=dict(color='red', width=1),
            fillcolor='rgba(255,0,0,0.2)',
            name='Drawdown'
        ))
        fig.update_layout(
            title=f"{symbol} Rolling Drawdown",
            xaxis_title="Date", yaxis_title="Drawdown (%)",
            template="plotly_white", height=350, showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating drawdown chart: {str(e)}")
        return None


def create_rolling_volatility_chart(symbol, period='1y'):
    """Create a 30-day rolling annualised volatility chart."""
    try:
        hist = yf.download(symbol, period=period, progress=False, auto_adjust=True)
        if hist.empty:
            return None
        prices  = hist['Close'].squeeze()
        returns = prices.pct_change().dropna()
        roll_vol = returns.rolling(30).std() * np.sqrt(252) * 100

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=roll_vol.index, y=roll_vol.values,
            mode='lines', line=dict(color='orange', width=2), name='30d Vol'
        ))
        fig.update_layout(
            title=f"{symbol} 30-Day Rolling Volatility (Ann.)",
            xaxis_title="Date", yaxis_title="Volatility (%)",
            template="plotly_white", height=350, showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating rolling volatility chart: {str(e)}")
        return None


def create_options_oi_chart(option_chain_data):
    """Create an open-interest chart split by calls vs puts across strikes."""
    try:
        if not option_chain_data:
            return None
        calls = option_chain_data.get('calls')
        puts  = option_chain_data.get('puts')
        if calls is None or puts is None:
            return None

        calls = calls[calls['openInterest'] > 0].copy()
        puts  = puts[puts['openInterest']  > 0].copy()
        calls = calls.nlargest(20, 'openInterest')
        puts  = puts.nlargest(20,  'openInterest')

        fig = go.Figure()
        fig.add_trace(go.Bar(x=calls['strike'], y=calls['openInterest'],
                             name='Calls OI', marker_color='green', opacity=0.7))
        fig.add_trace(go.Bar(x=puts['strike'],  y=puts['openInterest'],
                             name='Puts OI',  marker_color='red',   opacity=0.7))
        fig.update_layout(
            title=f"Options Open Interest — {option_chain_data.get('expiration', '')}",
            xaxis_title="Strike", yaxis_title="Open Interest",
            template="plotly_white", height=400, barmode='group'
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating options OI chart: {str(e)}")
        return None


def create_options_iv_smile(option_chain_data):
    """Create an implied-volatility smile/skew chart."""
    try:
        if not option_chain_data:
            return None
        calls = option_chain_data.get('calls')
        puts  = option_chain_data.get('puts')
        if calls is None or puts is None:
            return None

        calls = calls[calls['impliedVolatility'] > 0].copy()
        puts  = puts[puts['impliedVolatility']  > 0].copy()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=calls['strike'], y=calls['impliedVolatility'] * 100,
            mode='lines+markers', name='Call IV', line=dict(color='green')))
        fig.add_trace(go.Scatter(
            x=puts['strike'],  y=puts['impliedVolatility'] * 100,
            mode='lines+markers', name='Put IV',  line=dict(color='red')))
        fig.update_layout(
            title=f"IV Smile / Skew — {option_chain_data.get('expiration', '')}",
            xaxis_title="Strike", yaxis_title="Implied Volatility (%)",
            template="plotly_white", height=400
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating IV smile chart: {str(e)}")
        return None


def create_forex_heatmap(forex_data):
    """Create a coloured heatmap of % changes for all currency pairs."""
    try:
        if not forex_data:
            return None
        pairs   = list(forex_data.keys())
        changes = [forex_data[p]['change_pct'] for p in pairs]

        clean_labels = [p.replace('=X', '').replace('USD', '/USD').replace('EUR', 'EUR/') for p in pairs]

        fig = go.Figure(go.Bar(
            x=clean_labels, y=changes,
            marker_color=['green' if c >= 0 else 'red' for c in changes],
            text=[f"{c:+.3f}%" for c in changes],
            textposition='auto'
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(
            title="Forex % Change vs USD",
            xaxis_title="Currency Pair", yaxis_title="% Change",
            template="plotly_white", height=400, showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating forex heatmap: {str(e)}")
        return None


def create_futures_comparison_chart(futures_data, group_label="Futures"):
    """Bar chart of % change for a group of futures contracts."""
    try:
        if not futures_data:
            return None
        symbols = list(futures_data.keys())
        changes = [futures_data[s]['change_pct'] for s in symbols]
        fig = go.Figure(go.Bar(
            x=symbols, y=changes,
            marker_color=['green' if c >= 0 else 'red' for c in changes],
            text=[f"{c:+.2f}%" for c in changes],
            textposition='auto'
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(
            title=f"{group_label} Performance (% Change)",
            xaxis_title="Contract", yaxis_title="% Change",
            template="plotly_white", height=380, showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating futures comparison chart: {str(e)}")
        return None
