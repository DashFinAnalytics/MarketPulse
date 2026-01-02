import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FinancialData(Base):
    """Store historical financial data"""
    __tablename__ = "financial_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    change = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)
    volume = Column(Float, default=0)
    data_type = Column(String(50), nullable=False)  # 'index', 'commodity', 'bond', 'vix', 'sector'
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class UserPreferences(Base):
    """Store user dashboard preferences"""
    __tablename__ = "user_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, unique=True)
    auto_refresh = Column(Boolean, default=False)
    refresh_interval = Column(Integer, default=30)  # seconds
    favorite_symbols = Column(Text)  # JSON string of favorite symbols
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketAlerts(Base):
    """Store price alerts for symbols"""
    __tablename__ = "market_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    alert_type = Column(String(20), nullable=False)  # 'above', 'below'
    target_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    """Store portfolio information"""
    __tablename__ = "portfolios"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    cash_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PortfolioHolding(Base):
    """Store individual holdings in portfolios"""
    __tablename__ = "portfolio_holdings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Transaction(Base):
    """Store transaction history"""
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), nullable=False)
    symbol = Column(String(20), nullable=False)
    transaction_type = Column(String(10), nullable=False)  # 'buy', 'sell'
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class NewsArticle(Base):
    """Store news articles for caching and tracking"""
    __tablename__ = "news_articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    author = Column(String(200))
    published_date = Column(DateTime, nullable=False)
    symbols_mentioned = Column(Text)  # JSON string of symbols
    sector = Column(String(50))
    sentiment = Column(String(20))  # 'positive', 'negative', 'neutral'
    created_at = Column(DateTime, default=datetime.utcnow)

class FundamentalAnalysis(Base):
    """Store AI-powered fundamental analysis results"""
    __tablename__ = "fundamental_analysis"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)  # 'comprehensive', 'growth', 'value', 'dcf'
    analysis_result = Column(Text, nullable=False)  # JSON string of AI analysis
    period = Column(String(20), nullable=False)  # 'quarterly' or 'annual'
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class DatabaseManager:
    """Manage database operations for the finance dashboard"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def store_financial_data(self, symbol: str, data: Dict, data_type: str):
        """Store financial data in database"""
        session = None
        try:
            session = self.get_session()
            
            # Convert numpy types to Python native types
            price = float(data['price']) if data['price'] is not None else 0.0
            change = float(data['change']) if data['change'] is not None else 0.0
            change_pct = float(data['change_pct']) if data['change_pct'] is not None else 0.0
            volume = float(data.get('volume', 0))
            
            financial_record = FinancialData(
                symbol=symbol,
                price=price,
                change=change,
                change_pct=change_pct,
                volume=volume,
                data_type=data_type
            )
            
            session.add(financial_record)
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error storing financial data for {symbol}: {str(e)}")
            if session:
                session.rollback()
                session.close()
    
    def get_historical_data(self, symbol: str, hours: int = 24) -> List[Dict]:
        """Get historical data for a symbol from the last N hours"""
        try:
            session = self.get_session()
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            records = session.query(FinancialData).filter(
                FinancialData.symbol == symbol,
                FinancialData.timestamp >= cutoff_time
            ).order_by(FinancialData.timestamp.desc()).all()
            
            session.close()
            
            return [{
                'symbol': record.symbol,
                'price': record.price,
                'change': record.change,
                'change_pct': record.change_pct,
                'volume': record.volume,
                'timestamp': record.timestamp
            } for record in records]
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return []
    
    def save_user_preferences(self, user_id: str, preferences: Dict):
        """Save user preferences"""
        try:
            session = self.get_session()
            
            # Check if preferences exist
            existing = session.query(UserPreferences).filter(
                UserPreferences.user_id == user_id
            ).first()
            
            if existing:
                # Update existing preferences
                for key, value in preferences.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
            else:
                # Create new preferences
                user_prefs = UserPreferences(
                    user_id=user_id,
                    **preferences
                )
                session.add(user_prefs)
            
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error saving user preferences: {str(e)}")
            if session:
                session.rollback()
                session.close()
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """Get user preferences"""
        try:
            session = self.get_session()
            
            preferences = session.query(UserPreferences).filter(
                UserPreferences.user_id == user_id
            ).first()
            
            session.close()
            
            if preferences:
                return {
                    'auto_refresh': preferences.auto_refresh,
                    'refresh_interval': preferences.refresh_interval,
                    'favorite_symbols': preferences.favorite_symbols
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {str(e)}")
            return None
    
    def create_market_alert(self, user_id: str, symbol: str, alert_type: str, target_price: float):
        """Create a market alert"""
        try:
            session = self.get_session()
            
            alert = MarketAlerts(
                user_id=user_id,
                symbol=symbol,
                alert_type=alert_type,
                target_price=target_price
            )
            
            session.add(alert)
            session.commit()
            session.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating market alert: {str(e)}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def get_active_alerts(self, user_id: str = None) -> List[Dict]:
        """Get active market alerts"""
        try:
            session = self.get_session()
            
            query = session.query(MarketAlerts).filter(MarketAlerts.is_active == True)
            if user_id:
                query = query.filter(MarketAlerts.user_id == user_id)
            
            alerts = query.all()
            session.close()
            
            return [{
                'id': str(alert.id),
                'user_id': alert.user_id,
                'symbol': alert.symbol,
                'alert_type': alert.alert_type,
                'target_price': alert.target_price,
                'created_at': alert.created_at
            } for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {str(e)}")
            return []
    
    def check_alerts(self, current_prices: Dict[str, float]) -> List[Dict]:
        """Check if any alerts should be triggered"""
        triggered_alerts = []
        
        try:
            active_alerts = self.get_active_alerts()
            
            for alert in active_alerts:
                symbol = alert['symbol']
                if symbol in current_prices:
                    current_price = current_prices[symbol]
                    target_price = alert['target_price']
                    alert_type = alert['alert_type']
                    
                    triggered = False
                    if alert_type == 'above' and current_price >= target_price:
                        triggered = True
                    elif alert_type == 'below' and current_price <= target_price:
                        triggered = True
                    
                    if triggered:
                        triggered_alerts.append({
                            'alert_id': alert['id'],
                            'symbol': symbol,
                            'current_price': current_price,
                            'target_price': target_price,
                            'alert_type': alert_type,
                            'user_id': alert['user_id']
                        })
                        
                        # Deactivate the alert
                        self.deactivate_alert(alert['id'])
            
        except Exception as e:
            logger.error(f"Error checking alerts: {str(e)}")
        
        return triggered_alerts
    
    def deactivate_alert(self, alert_id: str):
        """Deactivate a market alert"""
        session = None
        try:
            session = self.get_session()
            
            alert = session.query(MarketAlerts).filter(
                MarketAlerts.id == uuid.UUID(alert_id)
            ).first()
            
            if alert:
                alert.is_active = False
                session.commit()
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error deactivating alert {alert_id}: {str(e)}")
            if session:
                session.rollback()
                session.close()
    
    def get_market_statistics(self) -> Dict:
        """Get market statistics from stored data"""
        try:
            session = self.get_session()
            
            # Get latest data for each symbol type
            stats = {}
            
            # Count of stored records by type
            for data_type in ['index', 'commodity', 'bond', 'vix', 'sector']:
                count = session.query(FinancialData).filter(
                    FinancialData.data_type == data_type
                ).count()
                stats[f'{data_type}_records'] = count
            
            # Most volatile symbols (highest average absolute change)
            from sqlalchemy import func
            volatile_query = session.query(
                FinancialData.symbol,
                func.avg(func.abs(FinancialData.change_pct)).label('avg_volatility')
            ).group_by(FinancialData.symbol).order_by(
                func.avg(func.abs(FinancialData.change_pct)).desc()
            ).limit(5).all()
            
            stats['most_volatile'] = [
                {'symbol': row.symbol, 'avg_volatility': float(row.avg_volatility)}
                for row in volatile_query
            ]
            
            session.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting market statistics: {str(e)}")
            return {}
    
    # Portfolio Management Methods
    def create_portfolio(self, user_id: str, name: str, description: str = "", cash_balance: float = 0.0) -> Optional[str]:
        """Create a new portfolio"""
        session = None
        try:
            session = self.get_session()
            
            portfolio = Portfolio(
                user_id=user_id,
                name=name,
                description=description,
                cash_balance=cash_balance
            )
            
            session.add(portfolio)
            session.commit()
            
            portfolio_id = str(portfolio.id)
            session.close()
            return portfolio_id
            
        except Exception as e:
            logger.error(f"Error creating portfolio: {str(e)}")
            if session:
                session.rollback()
                session.close()
            return None
    
    def get_user_portfolios(self, user_id: str) -> List[Dict]:
        """Get all portfolios for a user"""
        try:
            session = self.get_session()
            
            portfolios = session.query(Portfolio).filter(
                Portfolio.user_id == user_id
            ).order_by(Portfolio.created_at.desc()).all()
            
            session.close()
            
            return [{
                'id': str(portfolio.id),
                'name': portfolio.name,
                'description': portfolio.description,
                'cash_balance': portfolio.cash_balance,
                'created_at': portfolio.created_at,
                'updated_at': portfolio.updated_at
            } for portfolio in portfolios]
            
        except Exception as e:
            logger.error(f"Error getting user portfolios: {str(e)}")
            return []
    
    def add_holding(self, portfolio_id: str, symbol: str, quantity: float, price: float, notes: str = "") -> bool:
        """Add or update a holding in a portfolio"""
        session = None
        try:
            session = self.get_session()
            
            # Check if holding already exists
            existing_holding = session.query(PortfolioHolding).filter(
                PortfolioHolding.portfolio_id == uuid.UUID(portfolio_id),
                PortfolioHolding.symbol == symbol
            ).first()
            
            if existing_holding:
                # Update existing holding (average cost calculation)
                total_quantity = existing_holding.quantity + quantity
                total_cost = (existing_holding.quantity * existing_holding.average_cost) + (quantity * price)
                new_average_cost = total_cost / total_quantity if total_quantity > 0 else price
                
                existing_holding.quantity = total_quantity
                existing_holding.average_cost = new_average_cost
                existing_holding.updated_at = datetime.utcnow()
                if notes:
                    existing_holding.notes = notes
            else:
                # Create new holding
                holding = PortfolioHolding(
                    portfolio_id=uuid.UUID(portfolio_id),
                    symbol=symbol,
                    quantity=quantity,
                    average_cost=price,
                    notes=notes
                )
                session.add(holding)
            
            # Add transaction record
            transaction = Transaction(
                portfolio_id=uuid.UUID(portfolio_id),
                symbol=symbol,
                transaction_type='buy',
                quantity=quantity,
                price=price,
                total_amount=quantity * price,
                notes=notes
            )
            session.add(transaction)
            
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"Error adding holding: {str(e)}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def sell_holding(self, portfolio_id: str, symbol: str, quantity: float, price: float, notes: str = "") -> bool:
        """Sell shares from a holding"""
        session = None
        try:
            session = self.get_session()
            
            # Get existing holding
            holding = session.query(PortfolioHolding).filter(
                PortfolioHolding.portfolio_id == uuid.UUID(portfolio_id),
                PortfolioHolding.symbol == symbol
            ).first()
            
            if not holding:
                logger.error(f"No holding found for {symbol} in portfolio {portfolio_id}")
                session.close()
                return False
            
            if holding.quantity < quantity:
                logger.error(f"Insufficient shares: trying to sell {quantity}, only have {holding.quantity}")
                session.close()
                return False
            
            # Update holding
            holding.quantity -= quantity
            holding.updated_at = datetime.utcnow()
            
            # If quantity becomes 0, remove the holding
            if holding.quantity <= 0:
                session.delete(holding)
            
            # Add transaction record
            transaction = Transaction(
                portfolio_id=uuid.UUID(portfolio_id),
                symbol=symbol,
                transaction_type='sell',
                quantity=quantity,
                price=price,
                total_amount=quantity * price,
                notes=notes
            )
            session.add(transaction)
            
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"Error selling holding: {str(e)}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def get_portfolio_holdings(self, portfolio_id: str) -> List[Dict]:
        """Get all holdings for a portfolio"""
        try:
            session = self.get_session()
            
            holdings = session.query(PortfolioHolding).filter(
                PortfolioHolding.portfolio_id == uuid.UUID(portfolio_id)
            ).all()
            
            session.close()
            
            return [{
                'id': str(holding.id),
                'symbol': holding.symbol,
                'quantity': holding.quantity,
                'average_cost': holding.average_cost,
                'purchase_date': holding.purchase_date,
                'notes': holding.notes
            } for holding in holdings]
            
        except Exception as e:
            logger.error(f"Error getting portfolio holdings: {str(e)}")
            return []
    
    def get_portfolio_transactions(self, portfolio_id: str, limit: int = 50) -> List[Dict]:
        """Get transaction history for a portfolio"""
        try:
            session = self.get_session()
            
            transactions = session.query(Transaction).filter(
                Transaction.portfolio_id == uuid.UUID(portfolio_id)
            ).order_by(Transaction.transaction_date.desc()).limit(limit).all()
            
            session.close()
            
            return [{
                'id': str(transaction.id),
                'symbol': transaction.symbol,
                'type': transaction.transaction_type,
                'quantity': transaction.quantity,
                'price': transaction.price,
                'total_amount': transaction.total_amount,
                'fees': transaction.fees,
                'date': transaction.transaction_date,
                'notes': transaction.notes
            } for transaction in transactions]
            
        except Exception as e:
            logger.error(f"Error getting portfolio transactions: {str(e)}")
            return []
    
    def calculate_portfolio_value(self, portfolio_id: str, current_prices: Dict[str, float]) -> Dict:
        """Calculate portfolio current value and performance"""
        try:
            holdings = self.get_portfolio_holdings(portfolio_id)
            
            total_value = 0.0
            total_cost = 0.0
            holdings_details = []
            
            for holding in holdings:
                symbol = holding['symbol']
                quantity = holding['quantity']
                avg_cost = holding['average_cost']
                
                current_price = current_prices.get(symbol, avg_cost)
                market_value = quantity * current_price
                cost_basis = quantity * avg_cost
                gain_loss = market_value - cost_basis
                gain_loss_pct = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0
                
                holdings_details.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'avg_cost': avg_cost,
                    'current_price': current_price,
                    'market_value': market_value,
                    'cost_basis': cost_basis,
                    'gain_loss': gain_loss,
                    'gain_loss_pct': gain_loss_pct
                })
                
                total_value += market_value
                total_cost += cost_basis
            
            total_gain_loss = total_value - total_cost
            total_gain_loss_pct = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
            
            return {
                'total_value': total_value,
                'total_cost': total_cost,
                'total_gain_loss': total_gain_loss,
                'total_gain_loss_pct': total_gain_loss_pct,
                'holdings': holdings_details
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio value: {str(e)}")
            return {
                'total_value': 0.0,
                'total_cost': 0.0,
                'total_gain_loss': 0.0,
                'total_gain_loss_pct': 0.0,
                'holdings': []
            }
    
    # News Management Methods
    def store_news_article(self, article: Dict) -> bool:
        """Store a news article in the database"""
        session = None
        try:
            session = self.get_session()
            
            # Check if article already exists (by URL)
            existing = session.query(NewsArticle).filter(
                NewsArticle.url == article['link']
            ).first()
            
            if existing:
                session.close()
                return True  # Already stored
            
            news_article = NewsArticle(
                title=article['title'],
                summary=article.get('summary', ''),
                url=article['link'],
                source=article['source'],
                author=article.get('author', ''),
                published_date=article['published'],
                symbols_mentioned=article.get('symbols_mentioned', ''),
                sector=article.get('sector', ''),
                sentiment=article.get('sentiment', 'neutral')
            )
            
            session.add(news_article)
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"Error storing news article: {str(e)}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def get_stored_news(self, limit: int = 20, symbol: str = None) -> List[Dict]:
        """Get stored news articles"""
        try:
            session = self.get_session()
            
            query = session.query(NewsArticle)
            
            if symbol:
                query = query.filter(NewsArticle.symbols_mentioned.contains(symbol))
            
            articles = query.order_by(NewsArticle.published_date.desc()).limit(limit).all()
            
            session.close()
            
            return [{
                'id': str(article.id),
                'title': article.title,
                'summary': article.summary,
                'url': article.url,
                'source': article.source,
                'author': article.author,
                'published_date': article.published_date,
                'symbols_mentioned': article.symbols_mentioned,
                'sector': article.sector,
                'sentiment': article.sentiment
            } for article in articles]
            
        except Exception as e:
            logger.error(f"Error getting stored news: {str(e)}")
            return []
    
    # Fundamental Analysis Methods
    def store_fundamental_analysis(self, symbol: str, analysis_type: str, analysis_result: Dict, period: str) -> bool:
        """Store fundamental analysis result"""
        session = None
        try:
            import json
            session = self.get_session()
            
            analysis = FundamentalAnalysis(
                symbol=symbol,
                analysis_type=analysis_type,
                analysis_result=json.dumps(analysis_result),
                period=period
            )
            
            session.add(analysis)
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"Error storing fundamental analysis: {str(e)}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def get_fundamental_analysis(self, symbol: str, analysis_type: str = None, limit: int = 5) -> List[Dict]:
        """Get stored fundamental analysis results"""
        try:
            import json
            session = self.get_session()
            
            query = session.query(FundamentalAnalysis).filter(
                FundamentalAnalysis.symbol == symbol
            )
            
            if analysis_type:
                query = query.filter(FundamentalAnalysis.analysis_type == analysis_type)
            
            analyses = query.order_by(FundamentalAnalysis.created_at.desc()).limit(limit).all()
            
            session.close()
            
            return [{
                'id': str(analysis.id),
                'symbol': analysis.symbol,
                'analysis_type': analysis.analysis_type,
                'analysis_result': json.loads(analysis.analysis_result),
                'period': analysis.period,
                'created_at': analysis.created_at
            } for analysis in analyses]
            
        except Exception as e:
            logger.error(f"Error getting fundamental analysis: {str(e)}")
            return []

# Initialize database manager
db_manager = DatabaseManager()