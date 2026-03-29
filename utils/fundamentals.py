import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FundamentalsFetcher:
    """
    Fetch fundamental financial data including earnings history, financial statements
    """
    
    def __init__(self):
        self.cache_duration = 3600  # 1 hour cache for fundamental data
    
    @st.cache_data(ttl=3600)
    def get_earnings_history(_self, symbol, period='quarterly'):
        """
        Get earnings history for a stock
        Args:
            symbol: Stock ticker symbol
            period: 'quarterly' or 'annual'
        Returns:
            DataFrame with earnings history
        """
        try:
            ticker = yf.Ticker(symbol)
            
            if period == 'quarterly':
                income_stmt = ticker.quarterly_income_stmt
            else:
                income_stmt = ticker.income_stmt
            
            if income_stmt is None or income_stmt.empty:
                logger.warning(f"No {period} income statement data for {symbol}")
                return None
            
            return income_stmt
            
        except Exception as e:
            logger.error(f"Error fetching earnings for {symbol}: {str(e)}")
            return None
    
    @st.cache_data(ttl=3600)
    def get_balance_sheet(_self, symbol, period='quarterly'):
        """
        Get balance sheet for a stock
        Args:
            symbol: Stock ticker symbol
            period: 'quarterly' or 'annual'
        Returns:
            DataFrame with balance sheet data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            if period == 'quarterly':
                balance_sheet = ticker.quarterly_balance_sheet
            else:
                balance_sheet = ticker.balance_sheet
            
            if balance_sheet is None or balance_sheet.empty:
                logger.warning(f"No {period} balance sheet data for {symbol}")
                return None
            
            return balance_sheet
            
        except Exception as e:
            logger.error(f"Error fetching balance sheet for {symbol}: {str(e)}")
            return None
    
    @st.cache_data(ttl=3600)
    def get_cash_flow(_self, symbol, period='quarterly'):
        """
        Get cash flow statement for a stock
        Args:
            symbol: Stock ticker symbol
            period: 'quarterly' or 'annual'
        Returns:
            DataFrame with cash flow data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            if period == 'quarterly':
                cashflow = ticker.quarterly_cashflow
            else:
                cashflow = ticker.cashflow
            
            if cashflow is None or cashflow.empty:
                logger.warning(f"No {period} cash flow data for {symbol}")
                return None
            
            return cashflow
            
        except Exception as e:
            logger.error(f"Error fetching cash flow for {symbol}: {str(e)}")
            return None
    
    @st.cache_data(ttl=3600)
    def get_company_info(_self, symbol):
        """
        Get company information
        Args:
            symbol: Stock ticker symbol
        Returns:
            Dictionary with company info
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                logger.warning(f"No company info for {symbol}")
                return None
            
            return info
            
        except Exception as e:
            logger.error(f"Error fetching company info for {symbol}: {str(e)}")
            return None
    
    def extract_key_metrics(self, symbol, period='quarterly', years=5):
        """
        Extract key financial metrics from statements
        Args:
            symbol: Stock ticker symbol
            period: 'quarterly' or 'annual'
            years: Number of years of data to extract
        Returns:
            Dictionary with key metrics over time
        """
        try:
            income_stmt = self.get_earnings_history(symbol, period)
            balance_sheet = self.get_balance_sheet(symbol, period)
            cashflow = self.get_cash_flow(symbol, period)
            company_info = self.get_company_info(symbol)
            
            if income_stmt is None:
                return None
            
            # Limit to requested number of periods
            if period == 'quarterly':
                max_periods = years * 4  # 4 quarters per year
            else:
                max_periods = years
            
            income_stmt = income_stmt.iloc[:, :min(max_periods, income_stmt.shape[1])]
            if balance_sheet is not None:
                balance_sheet = balance_sheet.iloc[:, :min(max_periods, balance_sheet.shape[1])]
            if cashflow is not None:
                cashflow = cashflow.iloc[:, :min(max_periods, cashflow.shape[1])]
            
            metrics = {
                'symbol': symbol,
                'period': period,
                'dates': income_stmt.columns.tolist(),
                'company_name': company_info.get('longName', symbol) if company_info else symbol,
                'sector': company_info.get('sector', 'N/A') if company_info else 'N/A',
                'industry': company_info.get('industry', 'N/A') if company_info else 'N/A'
            }
            
            # Extract income statement metrics
            if 'Total Revenue' in income_stmt.index:
                metrics['revenue'] = income_stmt.loc['Total Revenue'].tolist()
            elif 'Total_Revenue' in income_stmt.index:
                metrics['revenue'] = income_stmt.loc['Total_Revenue'].tolist()
            
            if 'Net Income' in income_stmt.index:
                metrics['net_income'] = income_stmt.loc['Net Income'].tolist()
            elif 'Net_Income' in income_stmt.index:
                metrics['net_income'] = income_stmt.loc['Net_Income'].tolist()
            
            if 'Gross Profit' in income_stmt.index:
                metrics['gross_profit'] = income_stmt.loc['Gross Profit'].tolist()
            elif 'Gross_Profit' in income_stmt.index:
                metrics['gross_profit'] = income_stmt.loc['Gross_Profit'].tolist()
            
            if 'Operating Income' in income_stmt.index:
                metrics['operating_income'] = income_stmt.loc['Operating Income'].tolist()
            elif 'Operating_Income' in income_stmt.index:
                metrics['operating_income'] = income_stmt.loc['Operating_Income'].tolist()
            
            if 'EBITDA' in income_stmt.index:
                metrics['ebitda'] = income_stmt.loc['EBITDA'].tolist()
            
            # Extract balance sheet metrics
            if balance_sheet is not None:
                if 'Total Assets' in balance_sheet.index:
                    metrics['total_assets'] = balance_sheet.loc['Total Assets'].tolist()
                elif 'Total_Assets' in balance_sheet.index:
                    metrics['total_assets'] = balance_sheet.loc['Total_Assets'].tolist()
                
                if 'Total Liabilities Net Minority Interest' in balance_sheet.index:
                    metrics['total_liabilities'] = balance_sheet.loc['Total Liabilities Net Minority Interest'].tolist()
                elif 'Total_Liabilities' in balance_sheet.index:
                    metrics['total_liabilities'] = balance_sheet.loc['Total_Liabilities'].tolist()
                
                if 'Stockholders Equity' in balance_sheet.index:
                    metrics['stockholders_equity'] = balance_sheet.loc['Stockholders Equity'].tolist()
                elif 'Stockholders_Equity' in balance_sheet.index:
                    metrics['stockholders_equity'] = balance_sheet.loc['Stockholders_Equity'].tolist()
            
            # Extract cash flow metrics
            if cashflow is not None:
                if 'Operating Cash Flow' in cashflow.index:
                    metrics['operating_cashflow'] = cashflow.loc['Operating Cash Flow'].tolist()
                elif 'Operating_Cash_Flow' in cashflow.index:
                    metrics['operating_cashflow'] = cashflow.loc['Operating_Cash_Flow'].tolist()
                
                if 'Free Cash Flow' in cashflow.index:
                    metrics['free_cashflow'] = cashflow.loc['Free Cash Flow'].tolist()
                elif 'Free_Cash_Flow' in cashflow.index:
                    metrics['free_cashflow'] = cashflow.loc['Free_Cash_Flow'].tolist()
                
                if 'Capital Expenditure' in cashflow.index:
                    metrics['capex'] = cashflow.loc['Capital Expenditure'].tolist()
                elif 'Capital_Expenditure' in cashflow.index:
                    metrics['capex'] = cashflow.loc['Capital_Expenditure'].tolist()
            
            # Add current stock price
            if company_info:
                metrics['current_price'] = company_info.get('currentPrice')
                metrics['market_cap'] = company_info.get('marketCap')
                metrics['pe_ratio'] = company_info.get('trailingPE')
                metrics['forward_pe'] = company_info.get('forwardPE')
                metrics['peg_ratio'] = company_info.get('pegRatio')
                metrics['price_to_book'] = company_info.get('priceToBook')
                metrics['dividend_yield'] = company_info.get('dividendYield')
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error extracting metrics for {symbol}: {str(e)}")
            return None
    
    def calculate_growth_rates(self, metrics):
        """
        Calculate year-over-year and compound growth rates
        Args:
            metrics: Dictionary with financial metrics
        Returns:
            Dictionary with growth rates
        """
        growth_rates = {}
        
        try:
            # Calculate revenue growth
            if 'revenue' in metrics and len(metrics['revenue']) > 1:
                revenue = [float(r) for r in metrics['revenue'] if r is not None and pd.notna(r)]
                if len(revenue) > 1:
                    revenue.reverse()  # Oldest to newest
                    yoy_growth = [(revenue[i] - revenue[i-1]) / revenue[i-1] * 100 
                                  for i in range(1, len(revenue))]
                    growth_rates['revenue_yoy_growth'] = yoy_growth
                    
                    # CAGR
                    if len(revenue) > 2:
                        years = len(revenue) - 1
                        cagr = ((revenue[-1] / revenue[0]) ** (1/years) - 1) * 100
                        growth_rates['revenue_cagr'] = cagr
            
            # Calculate net income growth
            if 'net_income' in metrics and len(metrics['net_income']) > 1:
                net_income = [float(ni) for ni in metrics['net_income'] if ni is not None and pd.notna(ni)]
                if len(net_income) > 1:
                    net_income.reverse()
                    yoy_growth = [(net_income[i] - net_income[i-1]) / abs(net_income[i-1]) * 100 
                                  for i in range(1, len(net_income)) if net_income[i-1] != 0]
                    growth_rates['net_income_yoy_growth'] = yoy_growth
            
            # Calculate margins
            if 'revenue' in metrics and 'net_income' in metrics:
                revenue = [float(r) for r in metrics['revenue'] if r is not None and pd.notna(r)]
                net_income = [float(ni) for ni in metrics['net_income'] if ni is not None and pd.notna(ni)]
                
                if len(revenue) == len(net_income):
                    profit_margins = [(net_income[i] / revenue[i] * 100) 
                                     for i in range(len(revenue)) if revenue[i] != 0]
                    growth_rates['profit_margins'] = profit_margins
            
        except Exception as e:
            logger.error(f"Error calculating growth rates: {str(e)}")
        
        return growth_rates

fundamentals_fetcher = FundamentalsFetcher()
