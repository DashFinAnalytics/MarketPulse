from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator, List, Optional, Union

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Engine,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config import config
from utils.exceptions import DatabaseError
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Global state
engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None
Base = declarative_base()

# --- Helper Functions ---

def _database_url() -> Optional[str]:
    return config.database.url

def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default

def _safe_json_dumps(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)

def _safe_json_loads(value: Any, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default

def _engine_kwargs() -> Dict[str, Any]:
    url = _database_url() or ""
    kwargs: Dict[str, Any] = {
        "echo": config.database.echo,
        "future": True,
        "pool_pre_ping": True,
    }
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        return kwargs
    kwargs.update({
        "pool_size": config.database.pool_size,
        "max_overflow": config.database.max_overflow,
        "pool_timeout": config.database.pool_timeout,
        "pool_recycle": config.database.pool_recycle,
    })
    return kwargs

# --- Connection Management ---

def get_engine(force_refresh: bool = False) -> Optional[Engine]:
    global engine, SessionLocal
    if force_refresh and engine is not None:
        try:
            engine.dispose()
        except Exception as exc:
            logger.warning("Failed to dispose database engine", error=str(exc))
        engine = None
        SessionLocal = None

    if engine is not None:
        return engine

    database_url = _database_url()
    if not database_url or not config.database.is_available:
        return None

    engine = _initialize_engine_logic(database_url)
    return engine

def _initialize_engine_logic(url: str) -> Optional[Engine]:
    try:
        new_engine = create_engine(url, **_engine_kwargs())
        logger.info("Database engine initialized")
        return new_engine
    except Exception:
        try:
            new_engine = create_engine(url, echo=config.database.echo, future=True)
            return new_engine
        except Exception as exc:
            logger.error("Failed to initialize database engine", error=str(exc))
            return None

def get_session_factory() -> Optional[sessionmaker]:
    global SessionLocal
    if SessionLocal is not None:
        return SessionLocal
    db_engine = get_engine()
    if db_engine is None:
        return None
    SessionLocal = sessionmaker(bind=db_engine, expire_on_commit=False)
    return SessionLocal

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    factory = get_session_factory()
    if factory is None:
        raise DatabaseError("Database session unavailable")
    session = factory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        raise DatabaseError(f"Database operation failed: {exc}") from exc
    finally:
        session.close()

# --- Models ---

class FinancialData(Base):
    __tablename__ = "financial_data"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    change = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)
    data_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, unique=True)
    auto_refresh = Column(Boolean, default=False)
    refresh_interval = Column(Integer, default=30)
    favorite_symbols = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class MarketAlerts(Base):
    __tablename__ = "market_alerts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    alert_type = Column(String(20), nullable=False)
    target_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    cash_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)
    purchase_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), nullable=False)
    symbol = Column(String(20), nullable=False)
    transaction_type = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    transaction_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    published_date = Column(DateTime, nullable=False)
    symbols_mentioned = Column(Text)

class FundamentalAnalysis(Base):
    __tablename__ = "fundamental_analysis"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)
    analysis_result = Column(Text, nullable=False)
    period = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

# --- Database Manager ---

class DatabaseManager:
    def create_tables(self) -> bool:
        try:
            db_engine = get_engine()
            if db_engine:
                Base.metadata.create_all(bind=db_engine)
                return True
            return False
        except Exception as exc:
            logger.error("Failed to create tables", error=str(exc))
            return False

    def health_check(self) -> bool:
        try:
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    # --- Market Data ---

    def store_financial_data(self, symbol: str, data: Dict[str, Any], data_type: str) -> bool:
        norm = _normalize_symbol(symbol)
        try:
            with get_db_session() as session:
                session.add(FinancialData(
                    symbol=norm, price=_safe_float(data.get("price")),
                    change=_safe_float(data.get("change")),
                    change_pct=_safe_float(data.get("change_pct")),
                    volume=_safe_float(data.get("volume")), data_type=data_type
                ))
            return True
        except Exception:
            return False

    def get_historical_data(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        norm = _normalize_symbol(symbol)
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            with get_db_session() as session:
                records = session.query(FinancialData).filter(
                    FinancialData.symbol == norm, FinancialData.timestamp >= cutoff
                ).order_by(FinancialData.timestamp.desc()).all()
                return [{"symbol": r.symbol, "price": r.price, "timestamp": r.timestamp} for r in records]
        except Exception:
            return []

    def get_market_statistics(self) -> Dict[str, Any]:
        try:
            with get_db_session() as session:
                stats = {}
                for dt in ["index", "commodity", "bond", "vix", "sector"]:
                    stats[f"{dt}_records"] = session.query(FinancialData).filter(FinancialData.data_type == dt).count()
                return stats
        except Exception:
            return {}

    # --- Alerts ---

    def create_market_alert(self, user_id: str, symbol: str, alert_type: str, target_price: float) -> bool:
        try:
            with get_db_session() as session:
                session.add(MarketAlerts(
                    user_id=user_id, symbol=_normalize_symbol(symbol),
                    alert_type=alert_type.lower(), target_price=target_price
                ))
            return True
        except Exception:
            return False

    def get_active_alerts(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            with get_db_session() as session:
                query = session.query(MarketAlerts).filter(MarketAlerts.is_active == True)
                if user_id: query = query.filter(MarketAlerts.user_id == user_id)
                return [{"id": str(a.id), "symbol": a.symbol, "target": a.target_price} for a in query.all()]
        except Exception:
            return []

    def check_alerts(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        triggered = []
        try:
            alerts = self.get_active_alerts()
            for alert in alerts:
                symbol = alert["symbol"]
                if symbol in current_prices:
                    price = current_prices[symbol]
                    # Logic for trigger check...
                    triggered.append(alert)
                    self.deactivate_alert(alert["id"])
            return triggered
        except Exception:
            return []

    def deactivate_alert(self, alert_id: str) -> bool:
        try:
            with get_db_session() as session:
                alert = session.query(MarketAlerts).filter(MarketAlerts.id == uuid.UUID(alert_id)).first()
                if alert: alert.is_active = False
            return True
        except Exception:
            return False

    # --- Portfolios ---

    def create_portfolio(self, user_id: str, name: str, description: str = "", cash: float = 0.0) -> Optional[str]:
        try:
            with get_db_session() as session:
                p = Portfolio(user_id=user_id, name=name, description=description, cash_balance=cash)
                session.add(p)
                session.flush()
                return str(p.id)
        except Exception:
            return None

    def get_user_portfolios(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            with get_db_session() as session:
                portfolios = session.query(Portfolio).filter(Portfolio.user_id == user_id).all()
                return [{"id": str(p.id), "name": p.name, "balance": p.cash_balance} for p in portfolios]
        except Exception:
            return []

    def add_holding(self, portfolio_id: str, symbol: str, quantity: float, price: float) -> bool:
        norm = _normalize_symbol(symbol)
        try:
            pid = uuid.UUID(portfolio_id)
            with get_db_session() as session:
                existing = session.query(PortfolioHolding).filter(PortfolioHolding.portfolio_id == pid, PortfolioHolding.symbol == norm).first()
                if existing:
                    new_qty = existing.quantity + quantity
                    existing.average_cost = ((existing.quantity * existing.average_cost) + (quantity * price)) / new_qty
                    existing.quantity = new_qty
                else:
                    session.add(PortfolioHolding(portfolio_id=pid, symbol=norm, quantity=quantity, average_cost=price))
                session.add(Transaction(portfolio_id=pid, symbol=norm, transaction_type="buy", quantity=quantity, price=price, total_amount=quantity*price))
            return True
        except Exception:
            return False

    def sell_holding(self, portfolio_id: str, symbol: str, quantity: float, price: float) -> bool:
        norm = _normalize_symbol(symbol)
        try:
            pid = uuid.UUID(portfolio_id)
            with get_db_session() as session:
                holding = session.query(PortfolioHolding).filter(PortfolioHolding.portfolio_id == pid, PortfolioHolding.symbol == norm).first()
                if not holding or holding.quantity < quantity: return False
                holding.quantity -= quantity
                if holding.quantity <= 0: session.delete(holding)
                session.add(Transaction(portfolio_id=pid, symbol=norm, transaction_type="sell", quantity=quantity, price=price, total_amount=quantity*price))
            return True
        except Exception:
            return False

    def get_portfolio_holdings(self, portfolio_id: str) -> List[Dict[str, Any]]:
        try:
            pid = uuid.UUID(portfolio_id)
            with get_db_session() as session:
                holdings = session.query(PortfolioHolding).filter(PortfolioHolding.portfolio_id == pid).all()
                return [{"symbol": h.symbol, "qty": h.quantity, "cost": h.average_cost} for h in holdings]
        except Exception:
            return []

    def get_portfolio_transactions(self, portfolio_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            pid = uuid.UUID(portfolio_id)
            with get_db_session() as session:
                txs = session.query(Transaction).filter(Transaction.portfolio_id == pid).order_by(Transaction.transaction_date.desc()).limit(limit).all()
                return [{"symbol": t.symbol, "type": t.transaction_type, "amount": t.total_amount} for t in txs]
        except Exception:
            return []

    def calculate_portfolio_value(self, portfolio_id: str, current_prices: Dict[str, float]) -> Dict[str, Any]:
        try:
            holdings = self.get_portfolio_holdings(portfolio_id)
            total_val = 0.0
            for h in holdings:
                total_val += h["qty"] * current_prices.get(h["symbol"], h["cost"])
            return {"total_value": total_val}
        except Exception:
            return {"total_value": 0.0}

    # --- Content ---

    def store_news_article(self, article: Dict[str, Any]) -> bool:
        try:
            with get_db_session() as session:
                if session.query(NewsArticle).filter(NewsArticle.url == article["link"]).first(): return True
                session.add(NewsArticle(title=article["title"], url=article["link"], source=article["source"], published_date=article["published"]))
            return True
        except Exception:
            return False

    def get_stored_news(self, limit: int = 20, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            with get_db_session() as session:
                query = session.query(NewsArticle)
                if symbol: query = query.filter(NewsArticle.symbols_mentioned.contains(symbol))
                return [{"title": n.title, "url": n.url} for n in query.limit(limit).all()]
        except Exception:
            return []

    def store_fundamental_analysis(self, symbol: str, analysis_type: str, result: Dict[str, Any], period: str) -> bool:
        try:
            with get_db_session() as session:
                session.add(FundamentalAnalysis(symbol=_normalize_symbol(symbol), analysis_type=analysis_type, analysis_result=_safe_json_dumps(result), period=period))
            return True
        except Exception:
            return False

    def get_fundamental_analysis(self, symbol: str, analysis_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            norm = _normalize_symbol(symbol)
            with get_db_session() as session:
                query = session.query(FundamentalAnalysis).filter(FundamentalAnalysis.symbol == norm)
                if analysis_type: query = query.filter(FundamentalAnalysis.analysis_type == analysis_type)
                return [{"type": a.analysis_type, "result": a.analysis_result} for a in query.limit(limit).all()]
        except Exception:
            return []

db_manager = DatabaseManager()
