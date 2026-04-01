from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional

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

engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None
Base = declarative_base()


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


def _safe_json_loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        logger.warning(f"Failed to parse JSON: {value[:50]}...")
        return default  # Ensure default is the correct type


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

    kwargs.update(
        {
            "pool_size": config.database.pool_size,
            "max_overflow": config.database.max_overflow,
            "pool_timeout": config.database.pool_timeout,
            "pool_recycle": config.database.pool_recycle,
        }
    )
    return kwargs


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

    if not config.database.is_available:
        logger.warning(
            "Database unavailable",
            configured=config.database.is_configured,
            enabled=config.database.enabled,
        )
        return None

    database_url = _database_url()
    if not database_url:
        logger.warning("Database URL is not configured")
        return None

    if "+asyncpg" in database_url:
        logger.error(
            "Async database driver 'asyncpg' is not supported by the synchronous "
            "SQLAlchemy engine. Please use a synchronous driver such as "
            "'psycopg2' in DATABASE_URL.",
            database_url=database_url,
        )
        return None
    try:
        engine = create_engine(database_url, **_engine_kwargs())
        logger.info("Database engine initialized")
    except TypeError:
        try:
            engine = create_engine(
                database_url,
                echo=config.database.echo,
                future=True,
            )
            logger.info("Database engine initialized with fallback kwargs")
        except Exception as exc:
            logger.error(
                "Failed to initialize database engine with fallback kwargs",
                error=str(exc),
            )
            engine = None

    return engine


def get_session_factory() -> Optional[sessionmaker]:
    global SessionLocal

    if SessionLocal is not None:
        return SessionLocal

    db_engine = get_engine()
    if db_engine is None:
        return None

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=db_engine,
    )
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
    except DatabaseError:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error("Database session failed", error=str(exc))
        raise DatabaseError(f"Database operation failed: {exc}") from exc
    finally:
        session.close()


class FinancialData(Base):
    __tablename__ = "financial_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    change = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)
    volume = Column(Float, default=0)
    data_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, unique=True)
    auto_refresh = Column(Boolean, default=False)
    refresh_interval = Column(Integer, default=30)
    favorite_symbols = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketAlerts(Base):
    __tablename__ = "market_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    alert_type = Column(String(20), nullable=False)
    target_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    cash_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PortfolioHolding(Base):
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
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), nullable=False)
    symbol = Column(String(20), nullable=False)
    transaction_type = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    author = Column(String(200))
    published_date = Column(DateTime, nullable=False)
    symbols_mentioned = Column(Text)
    sector = Column(String(50))
    sentiment = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


class FundamentalAnalysis(Base):
    __tablename__ = "fundamental_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)
    analysis_result = Column(Text, nullable=False)
    period = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class DatabaseManager:
    """High-level interface for database operations used by the app."""
    
    def create_tables(self) -> bool:
        """Create all database tables if a database engine is available.

        Returns:
            bool: True if tables were created successfully, False if the database is
            unavailable or table creation failed.
        """
        try:
            db_engine = get_engine()
            if db_engine is None:
                logger.warning(
                    "Skipping table creation because database is unavailable"
                )
                return False

            Base.metadata.create_all(bind=db_engine)
            logger.info("Database tables created")
            return True
        except Exception as exc:
            logger.error("Failed to create tables", error=str(exc))
            return False

    def get_session(self) -> Optional[Session]:
        """Create a new SQLAlchemy session using the configured session factory.

        Returns:
            Optional[Session]: A new Session if the database is configured, otherwise None.
        """
        factory = get_session_factory()
        return factory() if factory is not None else None

    def health_check(self) -> bool:
        """Verify database connectivity by executing a simple query.

        Returns:
            bool: True if the database query succeeds, otherwise False.
        """
        try:
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning("Database health check failed", error=str(exc))
            return False

    def store_financial_data(
        self,
        symbol: str,
        data: Dict[str, Any],
        data_type: str,
    ) -> bool:
        """Persist a single market data snapshot for a symbol.

        Args:
            symbol: Ticker symbol to store (will be normalized, e.g. uppercased/trimmed).
            data: Market payload containing fields like price, change, change_pct, volume.
            data_type: Category label for the record (e.g. "index", "commodity", "vix").

        Returns:
            bool: True if the record was persisted, otherwise False.
        """
        normalized_symbol = _normalize_symbol(symbol)

        try:
            with get_db_session() as session:
                session.add(
                    FinancialData(
                        symbol=normalized_symbol,
                        price=_safe_float(data.get("price")),
                        change=_safe_float(data.get("change")),
                        change_pct=_safe_float(data.get("change_pct")),
                        volume=_safe_float(data.get("volume")),
                        data_type=data_type,
                    )
                )
            return True
        except Exception as exc:
            logger.warning(
                "Failed to persist financial data",
                symbol=normalized_symbol,
                error=str(exc),
            )
            return False

    def get_historical_data(
        self,
        symbol: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        normalized_symbol = _normalize_symbol(symbol)

        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            with get_db_session() as session:
                records = (
                    session.query(FinancialData)
                    .filter(
                        FinancialData.symbol == normalized_symbol,
                        FinancialData.timestamp >= cutoff,
                    )
                    .order_by(FinancialData.timestamp.desc())
                    .all()
                )
            return [
                {
                    "symbol": r.symbol,
                    "price": r.price,
                    "change": r.change,
                    "change_pct": r.change_pct,
                    "volume": r.volume,
                    "timestamp": r.timestamp,
                }
                for r in records
            ]
        except Exception as exc:
            logger.warning(
                "Failed to load historical financial data",
                symbol=normalized_symbol,
                hours=hours,
                error=str(exc),
            )
            return []

    def save_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
    ) -> bool:
        try:
            with get_db_session() as session:
                existing = (
                    session.query(UserPreferences)
                    .filter(UserPreferences.user_id == user_id)
                    .first()
                )

                serialized_preferences = dict(preferences)
                if "favorite_symbols" in serialized_preferences:
                    serialized_preferences["favorite_symbols"] = _safe_json_dumps(
                        serialized_preferences["favorite_symbols"]
                    )

                if existing:
                    for key, value in serialized_preferences.items():
                        if hasattr(existing, key) and key != "id":
                            setattr(existing, key, value)
                else:
                    session.add(
                        UserPreferences(
                            user_id=user_id,
                            **serialized_preferences,
                        )
                    )
            return True
        except Exception as exc:
            logger.warning(
                "Failed to save user preferences",
                user_id=user_id,
                error=str(exc),
            )
            return False

    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            with get_db_session() as session:
                prefs = (
                    session.query(UserPreferences)
                    .filter(UserPreferences.user_id == user_id)
                    .first()
                )
                if not prefs:
                    return None

                favorite_symbols = prefs.favorite_symbols
                if favorite_symbols:
                    favorite_symbols = _safe_json_loads(favorite_symbols, [])
                else:
                    favorite_symbols = []

                return {
                    "auto_refresh": prefs.auto_refresh,
                    "refresh_interval": prefs.refresh_interval,
                    "favorite_symbols": favorite_symbols,
                }
        except Exception as exc:
            logger.warning(
                "Failed to get user preferences",
                user_id=user_id,
                error=str(exc),
            )
            return None

    def create_market_alert(
        self,
        user_id: str,
        symbol: str,
        alert_type: str,
        target_price: float,
    ) -> bool:
        normalized_symbol = _normalize_symbol(symbol)
        normalized_alert_type = alert_type.strip().lower()

        if normalized_alert_type not in {"above", "below"}:
            logger.warning(
                "Invalid market alert type",
                alert_type=alert_type,
                user_id=user_id,
                symbol=normalized_symbol,
            )
            return False

        try:
            with get_db_session() as session:
                session.add(
                    MarketAlerts(
                        user_id=user_id,
                        symbol=normalized_symbol,
                        alert_type=normalized_alert_type,
                        target_price=float(target_price),
                    )
                )
            return True
        except Exception as exc:
            logger.warning(
                "Failed to create market alert",
                user_id=user_id,
                symbol=normalized_symbol,
                error=str(exc),
            )
            return False

    def get_active_alerts(
        self,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            with get_db_session() as session:
                query = session.query(MarketAlerts).filter(
                    MarketAlerts.is_active.is_(True)
                )
                if user_id:
                    query = query.filter(MarketAlerts.user_id == user_id)

                alerts = query.all()
                return [
                    {
                        "id": str(alert.id),
                        "user_id": alert.user_id,
                        "symbol": alert.symbol,
                        "alert_type": alert.alert_type,
                        "target_price": alert.target_price,
                        "created_at": alert.created_at,
                    }
                    for alert in alerts
                ]
        except Exception as exc:
            logger.warning("Failed to load active alerts", error=str(exc))
            return []

    def check_alerts(
        self,
        current_prices: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        triggered: List[Dict[str, Any]] = []

        try:
            for alert in self.get_active_alerts():
                symbol = alert["symbol"]
                if symbol not in current_prices:
                    continue

                current_price = float(current_prices[symbol])
                target_price = float(alert["target_price"])
                alert_type = alert["alert_type"]

                is_triggered = (
                    alert_type == "above" and current_price >= target_price
                ) or (
                    alert_type == "below" and current_price <= target_price
                )

                if not is_triggered:
                    continue

                triggered.append(
                    {
                        "alert_id": alert["id"],
                        "symbol": symbol,
                        "current_price": current_price,
                        "target_price": target_price,
                        "alert_type": alert_type,
                        "user_id": alert["user_id"],
                    }
                )
                self.deactivate_alert(alert["id"])
        except Exception as exc:
            logger.warning("Failed during alert check", error=str(exc))

        return triggered

    def deactivate_alert(self, alert_id: str) -> bool:
        try:
            with get_db_session() as session:
                alert = (
                    session.query(MarketAlerts)
                    .filter(MarketAlerts.id == uuid.UUID(alert_id))
                    .first()
                )
                if not alert:
                    return False

                alert.is_active = False
            return True
        except Exception as exc:
            logger.warning(
                "Failed to deactivate alert",
                alert_id=alert_id,
                error=str(exc),
            )
            return False

    def get_market_statistics(self) -> Dict[str, Any]:
        try:
            with get_db_session() as session:
                stats: Dict[str, Any] = {}

                for data_type in ["index", "commodity", "bond", "vix", "sector"]:
                    stats[f"{data_type}_records"] = (
                        session.query(FinancialData)
                        .filter(FinancialData.data_type == data_type)
                        .count()
                    )

                volatile = (
                    session.query(
                        FinancialData.symbol,
                        func.avg(func.abs(FinancialData.change_pct)).label(
                            "avg_volatility"
                        ),
                    )
                    .group_by(FinancialData.symbol)
                    .order_by(func.avg(func.abs(FinancialData.change_pct)).desc())
                    .limit(5)
                    .all()
                )

                stats["most_volatile"] = [
                    {
                        "symbol": row.symbol,
                        "avg_volatility": float(row.avg_volatility),
                    }
                    for row in volatile
                ]
                return stats
        except Exception as exc:
            logger.warning("Failed to get market statistics", error=str(exc))
            return {}

    def create_portfolio(
        self,
        user_id: str,
        name: str,
        description: str = "",
        cash_balance: float = 0.0,
    ) -> Optional[str]:
        try:
            with get_db_session() as session:
                portfolio = Portfolio(
                    user_id=user_id,
                    name=name,
                    description=description,
                    cash_balance=float(cash_balance),
                )
                session.add(portfolio)
                session.flush()
                return str(portfolio.id)
        except Exception as exc:
            logger.warning(
                "Failed to create portfolio",
                user_id=user_id,
                name=name,
                error=str(exc),
            )
            return None

    def get_user_portfolios(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            with get_db_session() as session:
                portfolios = (
                    session.query(Portfolio)
                    .filter(Portfolio.user_id == user_id)
                    .order_by(Portfolio.created_at.desc())
                    .all()
                )
                return [
                    {
                        "id": str(portfolio.id),
                        "name": portfolio.name,
                        "description": portfolio.description,
                        "cash_balance": portfolio.cash_balance,
                        "created_at": portfolio.created_at,
                        "updated_at": portfolio.updated_at,
                    }
                    for portfolio in portfolios
                ]
        except Exception as exc:
            logger.warning(
                "Failed to get user portfolios",
                user_id=user_id,
                error=str(exc),
            )
            return []

    def add_holding(
        self,
        portfolio_id: str,
        symbol: str,
        quantity: float,
        price: float,
        notes: str = "",
    ) -> bool:
        normalized_symbol = _normalize_symbol(symbol)

        try:
            with get_db_session() as session:
                existing = (
                    session.query(PortfolioHolding)
                    .filter(
                        PortfolioHolding.portfolio_id == uuid.UUID(portfolio_id),
                        PortfolioHolding.symbol == normalized_symbol,
                    )
                    .first()
                )

                if existing:
                    total_quantity = float(existing.quantity) + float(quantity)
                    total_cost = (
                        float(existing.quantity) * float(existing.average_cost)
                    ) + (float(quantity) * float(price))
                    existing.quantity = total_quantity
                    existing.average_cost = (
                        total_cost / total_quantity
                        if total_quantity > 0
                        else float(price)
                    )
                    existing.updated_at = datetime.utcnow()
                    if notes:
                        existing.notes = notes
                else:
                    session.add(
                        PortfolioHolding(
                            portfolio_id=uuid.UUID(portfolio_id),
                            symbol=normalized_symbol,
                            quantity=float(quantity),
                            average_cost=float(price),
                            notes=notes,
                        )
                    )

                session.add(
                    Transaction(
                        portfolio_id=uuid.UUID(portfolio_id),
                        symbol=normalized_symbol,
                        transaction_type="buy",
                        quantity=float(quantity),
                        price=float(price),
                        total_amount=float(quantity) * float(price),
                        notes=notes,
                    )
                )
            return True
        except Exception as exc:
            logger.warning(
                "Failed to add holding",
                portfolio_id=portfolio_id,
                symbol=normalized_symbol,
                error=str(exc),
            )
            return False

    def sell_holding(
        self,
        portfolio_id: str,
        symbol: str,
        quantity: float,
        price: float,
        notes: str = "",
    ) -> bool:
        normalized_symbol = _normalize_symbol(symbol)

        try:
            with get_db_session() as session:
                holding = (
                    session.query(PortfolioHolding)
                    .filter(
                        PortfolioHolding.portfolio_id == uuid.UUID(portfolio_id),
                        PortfolioHolding.symbol == normalized_symbol,
                    )
                    .first()
                )
                if not holding or float(holding.quantity) < float(quantity):
                    return False

                holding.quantity = float(holding.quantity) - float(quantity)
                holding.updated_at = datetime.utcnow()

                if holding.quantity <= 0:
                    session.delete(holding)

                session.add(
                    Transaction(
                        portfolio_id=uuid.UUID(portfolio_id),
                        symbol=normalized_symbol,
                        transaction_type="sell",
                        quantity=float(quantity),
                        price=float(price),
                        total_amount=float(quantity) * float(price),
                        notes=notes,
                    )
                )
            return True
        except Exception as exc:
            logger.warning(
                "Failed to sell holding",
                portfolio_id=portfolio_id,
                symbol=normalized_symbol,
                error=str(exc),
            )
            return False

    def get_portfolio_holdings(self, portfolio_id: str) -> List[Dict[str, Any]]:
        try:
            with get_db_session() as session:
                holdings = (
                    session.query(PortfolioHolding)
                    .filter(PortfolioHolding.portfolio_id == uuid.UUID(portfolio_id))
                    .all()
                )
                return [
                    {
                        "id": str(holding.id),
                        "symbol": holding.symbol,
                        "quantity": holding.quantity,
                        "average_cost": holding.average_cost,
                        "purchase_date": holding.purchase_date,
                        "notes": holding.notes,
                    }
                    for holding in holdings
                ]
        except Exception as exc:
            logger.warning(
                "Failed to get portfolio holdings",
                portfolio_id=portfolio_id,
                error=str(exc),
            )
            return []

    def get_portfolio_transactions(
        self,
        portfolio_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        try:
            with get_db_session() as session:
                transactions = (
                    session.query(Transaction)
                    .filter(Transaction.portfolio_id == uuid.UUID(portfolio_id))
                    .order_by(Transaction.transaction_date.desc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "id": str(transaction.id),
                        "symbol": transaction.symbol,
                        "type": transaction.transaction_type,
                        "quantity": transaction.quantity,
                        "price": transaction.price,
                        "total_amount": transaction.total_amount,
                        "fees": transaction.fees,
                        "date": transaction.transaction_date,
                        "notes": transaction.notes,
                    }
                    for transaction in transactions
                ]
        except Exception as exc:
            logger.warning(
                "Failed to get portfolio transactions",
                portfolio_id=portfolio_id,
                error=str(exc),
            )
            return []

    def calculate_portfolio_value(
        self,
        portfolio_id: str,
        current_prices: Dict[str, float],
    ) -> Dict[str, Any]:
        try:
            holdings = self.get_portfolio_holdings(portfolio_id)
            total_value = 0.0
            total_cost = 0.0
            details: List[Dict[str, Any]] = []

            for holding in holdings:
                symbol = holding["symbol"]
                quantity = float(holding["quantity"])
                avg_cost = float(holding["average_cost"])
                current_price = float(current_prices.get(symbol, avg_cost))
                market_value = quantity * current_price
                cost_basis = quantity * avg_cost
                gain_loss = market_value - cost_basis
                gain_loss_pct = (
                    (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0
                )

                details.append(
                    {
                        "symbol": symbol,
                        "quantity": quantity,
                        "avg_cost": avg_cost,
                        "current_price": current_price,
                        "market_value": market_value,
                        "cost_basis": cost_basis,
                        "gain_loss": gain_loss,
                        "gain_loss_pct": gain_loss_pct,
                    }
                )
                total_value += market_value
                total_cost += cost_basis

            total_gain_loss = total_value - total_cost
            total_gain_loss_pct = (
                (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
            )
            return {
                "total_value": total_value,
                "total_cost": total_cost,
                "total_gain_loss": total_gain_loss,
                "total_gain_loss_pct": total_gain_loss_pct,
                "holdings": details,
            }
        except Exception as exc:
            logger.warning(
                "Failed to calculate portfolio value",
                portfolio_id=portfolio_id,
                error=str(exc),
            )
            return {
                "total_value": 0.0,
                "total_cost": 0.0,
                "total_gain_loss": 0.0,
                "total_gain_loss_pct": 0.0,
                "holdings": [],
            }

    def store_news_article(self, article: Dict[str, Any]) -> bool:
        try:
            with get_db_session() as session:
                existing = (
                    session.query(NewsArticle)
                    .filter(NewsArticle.url == article["link"])
                    .first()
                )
                if existing:
                    return True

                session.add(
                    NewsArticle(
                        title=article["title"],
                        summary=article.get("summary", ""),
                        url=article["link"],
                        source=article["source"],
                        author=article.get("author", ""),
                        published_date=article["published"],
                        "symbols_mentioned": _safe_json_loads(
                            article.symbols_mentioned,
                            [],
                        ),
                        sector=article.get("sector", ""),
                        sentiment=article.get("sentiment", "neutral"),
                    )
                )
            return True
        except Exception as exc:
            logger.warning("Failed to store news article", error=str(exc))
            return False

    def get_stored_news(
        self,
        limit: int = 20,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized_symbol = _normalize_symbol(symbol) if symbol else None

        try:
            with get_db_session() as session:
                query = session.query(NewsArticle)
                if normalized_symbol:
                    json_symbol = json.dumps(normalized_symbol)
                    query = query.filter(
                        NewsArticle.symbols_mentioned.contains(json_symbol)
                    )

                articles = (
                    query.order_by(NewsArticle.published_date.desc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "id": str(article.id),
                        "title": article.title,
                        "summary": article.summary,
                        "url": article.url,
                        "source": article.source,
                        "author": article.author,
                        "published_date": article.published_date,
                        "symbols_mentioned": _safe_json_loads(
                            article.symbols_mentioned,
                            article.symbols_mentioned,
                        ),
                        "sector": article.sector,
                        "sentiment": article.sentiment,
                    }
                    for article in articles
                ]
        except Exception as exc:
            logger.warning("Failed to get stored news", error=str(exc))
            return []

    def store_fundamental_analysis(
        self,
        symbol: str,
        analysis_type: str,
        analysis_result: Dict[str, Any],
        period: str,
    ) -> bool:
        normalized_symbol = _normalize_symbol(symbol)

        try:
            with get_db_session() as session:
                session.add(
                    FundamentalAnalysis(
                        symbol=normalized_symbol,
                        analysis_type=analysis_type,
                        analysis_result=_safe_json_dumps(analysis_result),
                        period=period,
                    )
                )
            return True
        except Exception as exc:
            logger.warning(
                "Failed to store fundamental analysis",
                symbol=normalized_symbol,
                error=str(exc),
            )
            return False

    def get_fundamental_analysis(
        self,
        symbol: str,
        analysis_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        normalized_symbol = _normalize_symbol(symbol)

        try:
            with get_db_session() as session:
                query = session.query(FundamentalAnalysis).filter(
                    FundamentalAnalysis.symbol == normalized_symbol
                )
                if analysis_type:
                    query = query.filter(
                        FundamentalAnalysis.analysis_type == analysis_type
                    )

                analyses = (
                    query.order_by(FundamentalAnalysis.created_at.desc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "id": str(analysis.id),
                        "symbol": analysis.symbol,
                        "analysis_type": analysis.analysis_type,
                        "analysis_result": _safe_json_loads(
                            analysis.analysis_result,
                            {},
                        ),
                        "period": analysis.period,
                        "created_at": analysis.created_at,
                    }
                    for analysis in analyses
                ]
        except Exception as exc:
            logger.warning(
                "Failed to get fundamental analysis",
                symbol=normalized_symbol,
                error=str(exc),
            )
            return []


db_manager = DatabaseManager()
