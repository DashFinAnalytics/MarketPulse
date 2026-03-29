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


def create_technical_analysis_chart(symbol, period="3mo", interval="1d",
                                     show_bb=True, show_rsi=True, show_macd=True,
                                     show_volume=True, sma_periods=None):
    """
    Multi-panel technical analysis chart with:
    Price + Bollinger Bands + SMAs | Volume | RSI | MACD
    """
    try:
        from plotly.subplots import make_subplots

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty or len(hist) < 20:
            return None

        close = hist['Close']
        high  = hist['High']
        low   = hist['Low']
        vol   = hist['Volume']

        # ── Indicators ─────────────────────────────────────
        if sma_periods is None:
            sma_periods = [20, 50, 200]
        smas = {p: close.rolling(p).mean() for p in sma_periods if len(close) >= p}
        ema20 = close.ewm(span=20, adjust=False).mean()

        # Bollinger Bands (20-period, 2σ)
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_upper = sma20 + 2 * std20
        bb_lower = sma20 - 2 * std20

        # RSI (14)
        delta = close.diff()
        gain  = delta.clip(lower=0)
        loss  = (-delta).clip(lower=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs  = avg_gain / avg_loss.replace(0, float('nan'))
        rsi = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema12    = close.ewm(span=12, adjust=False).mean()
        ema26    = close.ewm(span=26, adjust=False).mean()
        macd     = ema12 - ema26
        signal   = macd.ewm(span=9, adjust=False).mean()
        macd_hist= macd - signal

        # ── Subplot layout ─────────────────────────────────
        rows, heights = 1, [0.5]
        if show_volume: rows += 1; heights.append(0.1)
        if show_rsi:    rows += 1; heights.append(0.15)
        if show_macd:   rows += 1; heights.append(0.2)

        specs = [[{"secondary_y": False}]] * rows
        row_titles = ['']
        if show_volume: row_titles.append('Volume')
        if show_rsi:    row_titles.append('RSI')
        if show_macd:   row_titles.append('MACD')

        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                            vertical_spacing=0.03, row_heights=heights)

        # ── Price + Candlestick ─────────────────────────────
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist['Open'], high=high,
            low=low, close=close, name='Price',
            increasing_line_color='green', decreasing_line_color='red'
        ), row=1, col=1)

        # SMAs
        colours = ['orange', 'blue', 'purple', 'brown']
        for i, (p, sma_val) in enumerate(smas.items()):
            fig.add_trace(go.Scatter(x=hist.index, y=sma_val,
                                     mode='lines', name=f'SMA{p}',
                                     line=dict(color=colours[i % len(colours)], width=1.2),
                                     opacity=0.8), row=1, col=1)

        fig.add_trace(go.Scatter(x=hist.index, y=ema20,
                                  mode='lines', name='EMA20',
                                  line=dict(color='cyan', width=1.2, dash='dot'),
                                  opacity=0.8), row=1, col=1)

        # Bollinger Bands
        if show_bb:
            fig.add_trace(go.Scatter(x=hist.index, y=bb_upper,
                                      mode='lines', name='BB Upper',
                                      line=dict(color='gray', width=1, dash='dash'),
                                      showlegend=False), row=1, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=bb_lower,
                                      mode='lines', name='BB Lower',
                                      line=dict(color='gray', width=1, dash='dash'),
                                      fill='tonexty',
                                      fillcolor='rgba(128,128,128,0.08)',
                                      showlegend=False), row=1, col=1)

        cur_row = 2

        # ── Volume ─────────────────────────────────────────
        if show_volume:
            vol_colors = ['green' if c >= o else 'red'
                          for c, o in zip(hist['Close'], hist['Open'])]
            fig.add_trace(go.Bar(x=hist.index, y=vol,
                                  name='Volume', marker_color=vol_colors,
                                  opacity=0.6, showlegend=False),
                           row=cur_row, col=1)
            fig.update_yaxes(title_text="Vol", row=cur_row, col=1)
            cur_row += 1

        # ── RSI ────────────────────────────────────────────
        if show_rsi:
            rsi_colors = [
                'green' if v < 30 else ('red' if v > 70 else 'royalblue')
                for v in rsi.fillna(50)
            ]
            fig.add_trace(go.Scatter(x=hist.index, y=rsi,
                                      mode='lines', name='RSI(14)',
                                      line=dict(color='royalblue', width=1.5)),
                           row=cur_row, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red",   opacity=0.5, row=cur_row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=cur_row, col=1)
            fig.add_hline(y=50, line_dash="dot",  line_color="gray",  opacity=0.3, row=cur_row, col=1)
            fig.update_yaxes(title_text="RSI", range=[0, 100], row=cur_row, col=1)
            cur_row += 1

        # ── MACD ───────────────────────────────────────────
        if show_macd:
            hist_colors = ['green' if v >= 0 else 'red' for v in macd_hist.fillna(0)]
            fig.add_trace(go.Bar(x=hist.index, y=macd_hist,
                                  name='MACD Hist', marker_color=hist_colors,
                                  opacity=0.6, showlegend=False),
                           row=cur_row, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=macd,
                                      mode='lines', name='MACD',
                                      line=dict(color='blue', width=1.5)),
                           row=cur_row, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=signal,
                                      mode='lines', name='Signal',
                                      line=dict(color='orange', width=1.5)),
                           row=cur_row, col=1)
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5,
                          row=cur_row, col=1)
            fig.update_yaxes(title_text="MACD", row=cur_row, col=1)

        fig.update_layout(
            title=f"{symbol} — Technical Analysis ({period})",
            template="plotly_white", height=700,
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1.02, x=0)
        )
        return fig

    except Exception as e:
        logger.error(f"Error creating technical analysis chart for {symbol}: {str(e)}")
        return None


def create_portfolio_allocation_chart(holdings_data):
    """Pie chart of portfolio allocation by market value."""
    try:
        if not holdings_data:
            return None
        symbols = [h['symbol'] for h in holdings_data if h.get('market_value', 0) > 0]
        values  = [h['market_value'] for h in holdings_data if h.get('market_value', 0) > 0]
        if not symbols:
            return None
        fig = go.Figure(go.Pie(
            labels=symbols, values=values,
            hole=0.4, textinfo='label+percent',
            hovertemplate='%{label}<br>$%{value:,.2f}<br>%{percent}<extra></extra>'
        ))
        fig.update_layout(title="Portfolio Allocation", height=400,
                          template="plotly_white")
        return fig
    except Exception as e:
        logger.error(f"Error creating portfolio allocation chart: {str(e)}")
        return None


def create_portfolio_performance_chart(holdings_data, period="3mo"):
    """Normalised price performance of all portfolio holdings."""
    try:
        if not holdings_data:
            return None
        symbols = list(set(h['symbol'] for h in holdings_data))
        fig = go.Figure()
        for sym in symbols:
            try:
                t = yf.Ticker(sym)
                h = t.history(period=period)
                if h.empty:
                    continue
                norm = h['Close'] / h['Close'].iloc[0] * 100
                fig.add_trace(go.Scatter(x=h.index, y=norm,
                                          mode='lines', name=sym))
            except Exception:
                continue
        fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(title=f"Holding Performance (normalised, {period})",
                          yaxis_title="Indexed (base=100)",
                          template="plotly_white", height=400)
        return fig
    except Exception as e:
        logger.error(f"Error creating portfolio performance chart: {str(e)}")
        return None


def create_crypto_market_chart(crypto_data):
    """Bar chart of % change for crypto assets."""
    try:
        if not crypto_data:
            return None
        labels  = list(crypto_data.keys())
        changes = [crypto_data[s]['change_pct'] for s in labels]
        clean   = [l.replace('-USD', '') for l in labels]
        fig = go.Figure(go.Bar(
            x=clean, y=changes,
            marker_color=['green' if c >= 0 else 'red' for c in changes],
            text=[f"{c:+.2f}%" for c in changes],
            textposition='auto'
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(title="Crypto 24h Performance",
                          xaxis_title="Asset", yaxis_title="% Change",
                          template="plotly_white", height=380, showlegend=False)
        return fig
    except Exception as e:
        logger.error(f"Error creating crypto market chart: {str(e)}")
        return None


def create_economic_dashboard_chart(eco_data):
    """Horizontal bar chart for economic indicator snapshot."""
    try:
        if not eco_data:
            return None
        labels  = [d['label']  for d in eco_data if d.get('change_pct') is not None]
        changes = [d['change_pct'] for d in eco_data if d.get('change_pct') is not None]
        if not labels:
            return None
        colors = ['green' if c >= 0 else 'red' for c in changes]
        fig = go.Figure(go.Bar(
            x=changes, y=labels, orientation='h',
            marker_color=colors,
            text=[f"{c:+.2f}%" for c in changes],
            textposition='auto'
        ))
        fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(title="Economic Indicators — 1-Day % Change",
                          xaxis_title="% Change", template="plotly_white",
                          height=420, showlegend=False)
        return fig
    except Exception as e:
        logger.error(f"Error creating economic dashboard chart: {str(e)}")
        return None


def create_market_breadth_chart(breadth_data):
    """Gauge-style chart showing market breadth."""
    try:
        if not breadth_data:
            return None
        score = breadth_data.get('score', 50)
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Market Breadth Score"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 30],  'color': "red"},
                    {'range': [30, 45], 'color': "orange"},
                    {'range': [45, 55], 'color': "yellow"},
                    {'range': [55, 70], 'color': "lightgreen"},
                    {'range': [70, 100],'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 3},
                    'thickness': 0.8, 'value': score
                }
            }
        ))
        fig.update_layout(height=280, template="plotly_white")
        return fig
    except Exception as e:
        logger.error(f"Error creating market breadth chart: {str(e)}")
        return None


def create_equity_curve_chart(equity_curve, initial_capital, strategy_name,
                               benchmark_curve=None):
    """Plot strategy equity curve vs optional benchmark."""
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=equity_curve, mode='lines', name=strategy_name,
            line=dict(color='royalblue', width=2)
        ))
        if benchmark_curve is not None:
            fig.add_trace(go.Scatter(
                y=benchmark_curve, mode='lines', name='Buy & Hold',
                line=dict(color='orange', width=2, dash='dash')
            ))
        fig.add_hline(y=initial_capital, line_dash='dash',
                      line_color='gray', opacity=0.5)
        fig.update_layout(
            title=f"Equity Curve — {strategy_name}",
            xaxis_title="Bar", yaxis_title="Portfolio Value ($)",
            template="plotly_white", height=400
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating equity curve chart: {e}")
        return None


def create_trade_distribution_chart(trades):
    """Histogram of trade P&L %."""
    try:
        if not trades:
            return None
        pnl = [t['pnl_pct'] for t in trades]
        colors = ['green' if p > 0 else 'red' for p in pnl]
        fig = go.Figure(go.Bar(
            x=list(range(1, len(pnl)+1)), y=pnl,
            marker_color=colors,
            text=[f"{p:+.2f}%" for p in pnl],
            textposition='auto'
        ))
        fig.add_hline(y=0, line_dash='dash', line_color='gray', opacity=0.5)
        fig.update_layout(
            title="Individual Trade P&L",
            xaxis_title="Trade #", yaxis_title="P&L %",
            template="plotly_white", height=350, showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating trade distribution chart: {e}")
        return None


def create_monte_carlo_chart(mc_result, initial_capital):
    """Fan chart from Monte Carlo simulation paths."""
    try:
        if mc_result is None:
            return None
        paths = mc_result['paths']
        n_days = paths.shape[1]
        x = list(range(n_days))
        fig = go.Figure()
        # Plot a random subset of paths (grey)
        n_show = min(100, paths.shape[0])
        for i in range(n_show):
            fig.add_trace(go.Scatter(
                x=x, y=paths[i], mode='lines',
                line=dict(color='rgba(100,100,100,0.08)', width=1),
                showlegend=False
            ))
        # Percentile lines
        for pct, label, color in [(10, 'P10', 'red'), (50, 'Median', 'blue'),
                                   (90, 'P90', 'green')]:
            pct_path = np.percentile(paths, pct, axis=0)
            fig.add_trace(go.Scatter(
                x=x, y=pct_path, mode='lines', name=label,
                line=dict(color=color, width=2)
            ))
        fig.add_hline(y=initial_capital, line_dash='dash',
                      line_color='orange', opacity=0.7,
                      annotation_text='Initial Capital')
        fig.update_layout(
            title="Monte Carlo Simulation (1-Year Paths)",
            xaxis_title="Trading Days", yaxis_title="Portfolio Value ($)",
            template="plotly_white", height=420
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating Monte Carlo chart: {e}")
        return None


def create_trend_signal_heatmap(signals):
    """
    Colour-coded heatmap of trend signals (strength × direction) for all symbols.
    """
    try:
        if not signals:
            return None
        symbols = [s['symbol'] for s in signals]
        scores  = [s['score']  for s in signals]
        fig = go.Figure(go.Bar(
            x=symbols, y=scores,
            marker_color=['green' if sc > 0 else ('red' if sc < 0 else 'gray')
                          for sc in scores],
            text=[f"{s['emoji']} {s['direction']}" for s in signals],
            textposition='auto'
        ))
        fig.add_hline(y=30,  line_dash='dash', line_color='green', opacity=0.5,
                      annotation_text='Strong UP')
        fig.add_hline(y=-30, line_dash='dash', line_color='red',   opacity=0.5,
                      annotation_text='Strong DOWN')
        fig.add_hline(y=0,   line_dash='dot',  line_color='gray',  opacity=0.4)
        fig.update_layout(
            title="Trend Signal Scores (–100 = strong down, +100 = strong up)",
            xaxis_title="Symbol", yaxis_title="Score",
            template="plotly_white", height=400, showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating trend heatmap: {e}")
        return None


def create_portfolio_optimization_chart(weights, symbols, method_name):
    """Pie chart of optimal portfolio weights."""
    try:
        if not weights or not symbols:
            return None
        fig = go.Figure(go.Pie(
            labels=symbols, values=[max(0, w) for w in weights],
            hole=0.4, textinfo='label+percent',
            hovertemplate='%{label}: %{percent}<extra></extra>'
        ))
        fig.update_layout(
            title=f"Optimal Weights — {method_name}",
            height=420, template="plotly_white"
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating optimization chart: {e}")
        return None


def create_efficient_frontier_chart(frontier_data):
    """Plot the efficient frontier curve."""
    try:
        if frontier_data is None:
            return None
        vols   = frontier_data['vols']
        rets   = frontier_data['rets']
        sharpe = frontier_data.get('sharpe_vols'), frontier_data.get('sharpe_rets')
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=vols, y=rets, mode='lines+markers',
            name='Efficient Frontier',
            line=dict(color='royalblue', width=2),
            marker=dict(size=4)
        ))
        if sharpe[0] is not None:
            fig.add_trace(go.Scatter(
                x=[sharpe[0]], y=[sharpe[1]],
                mode='markers', name='Max Sharpe',
                marker=dict(color='gold', size=14, symbol='star')
            ))
        fig.update_layout(
            title="Efficient Frontier",
            xaxis_title="Volatility (Ann.)", yaxis_title="Return (Ann.)",
            template="plotly_white", height=420
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating efficient frontier chart: {e}")
        return None
