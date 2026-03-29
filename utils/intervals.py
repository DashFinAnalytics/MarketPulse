from datetime import datetime, timedelta
from typing import Dict, Optional

class FinanceIntervals:
    """
    Finance industry standard intervals for historical data
    """
    
    INTERVALS = {
        '1m': {'period': '1d', 'interval': '1m', 'name': '1 Minute', 'hours': 0.017},
        '5m': {'period': '5d', 'interval': '5m', 'name': '5 Minutes', 'hours': 0.083},
        '15m': {'period': '5d', 'interval': '15m', 'name': '15 Minutes', 'hours': 0.25},
        '30m': {'period': '1mo', 'interval': '30m', 'name': '30 Minutes', 'hours': 0.5},
        '60m': {'period': '1mo', 'interval': '60m', 'name': '1 Hour', 'hours': 1},
        '2hr': {'period': '3mo', 'interval': '1h', 'name': '2 Hours', 'hours': 2},
        '4hr': {'period': '6mo', 'interval': '1h', 'name': '4 Hours', 'hours': 4},
        '8hr': {'period': '6mo', 'interval': '1h', 'name': '8 Hours', 'hours': 8},
        '12hr': {'period': '1y', 'interval': '1d', 'name': '12 Hours', 'hours': 12},
        '1d': {'period': '1y', 'interval': '1d', 'name': '1 Day', 'hours': 24},
        '7d': {'period': '2y', 'interval': '1wk', 'name': '1 Week', 'hours': 168},
        '30d': {'period': '5y', 'interval': '1mo', 'name': '1 Month', 'hours': 720},
        '3m': {'period': '10y', 'interval': '3mo', 'name': '3 Months', 'hours': 2160},
        '6m': {'period': '20y', 'interval': '3mo', 'name': '6 Months', 'hours': 4320},
        'ytd': {'period': 'ytd', 'interval': '1d', 'name': 'Year to Date', 'hours': None},
        '1yr': {'period': '1y', 'interval': '1d', 'name': '1 Year', 'hours': 8760},
        '5yr': {'period': '5y', 'interval': '1wk', 'name': '5 Years', 'hours': 43800},
        '10yr': {'period': '10y', 'interval': '1mo', 'name': '10 Years', 'hours': 87600},
        '20yr': {'period': '20y', 'interval': '3mo', 'name': '20 Years', 'hours': 175200},
        '50yr': {'period': 'max', 'interval': '3mo', 'name': '50 Years', 'hours': 438000}
    }
    
    @classmethod
    def get_interval_config(cls, interval_key: str) -> Optional[Dict]:
        """Get configuration for a specific interval"""
        return cls.INTERVALS.get(interval_key)
    
    @classmethod
    def get_available_intervals(cls) -> Dict[str, str]:
        """Get all available intervals with their display names"""
        return {key: config['name'] for key, config in cls.INTERVALS.items()}
    
    @classmethod
    def calculate_hours_from_now(cls, interval_key: str) -> Optional[float]:
        """Calculate hours from now for database queries"""
        config = cls.get_interval_config(interval_key)
        if not config or config['hours'] is None:
            return None
        return config['hours']
    
    @classmethod
    def get_yfinance_params(cls, interval_key: str) -> Optional[Dict[str, str]]:
        """Get period and interval parameters for yfinance"""
        config = cls.get_interval_config(interval_key)
        if not config:
            return None
        
        return {
            'period': config['period'],
            'interval': config['interval']
        }
    
    @classmethod
    def get_chart_title(cls, symbol: str, interval_key: str) -> str:
        """Generate appropriate chart title"""
        config = cls.get_interval_config(interval_key)
        if not config:
            return f"{symbol} Price Chart"
        
        return f"{symbol} - {config['name']} Chart"
    
    @classmethod
    def is_intraday(cls, interval_key: str) -> bool:
        """Check if interval is intraday (< 1 day)"""
        config = cls.get_interval_config(interval_key)
        if not config or config['hours'] is None:
            return False
        return config['hours'] < 24
    
    @classmethod
    def get_db_lookback_hours(cls, interval_key: str) -> int:
        """Get appropriate lookback hours for database queries"""
        config = cls.get_interval_config(interval_key)
        if not config:
            return 24
        
        # For database queries, we need more data points for longer intervals
        if config['hours'] is None:  # YTD case
            # Calculate YTD hours
            now = datetime.now()
            year_start = datetime(now.year, 1, 1)
            ytd_hours = (now - year_start).total_seconds() / 3600
            return int(ytd_hours)
        
        # Return appropriate multiplier based on interval
        if config['hours'] < 1:  # Minutes
            return max(24, int(config['hours'] * 100))  # Show last day minimum
        elif config['hours'] < 24:  # Hours
            return max(168, int(config['hours'] * 20))  # Show last week minimum
        elif config['hours'] < 720:  # Days/weeks
            return int(config['hours'] * 2)  # Show double the period
        else:  # Months/years
            return int(config['hours'])  # Use the period as-is