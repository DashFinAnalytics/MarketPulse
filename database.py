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


def _database_url() -> Optional[str]:
    """Retrieves the database URL from config."""
    return config.database.url


def _normalize_symbol(symbol: str) -> str:
    """Standardizes ticker symbols."""
    return symbol.strip().upper()


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely converts a value to float."""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _safe_json_dumps(value: Any) -> str:
    """Safely serializes objects to JSON strings."""
    return json.dumps(value, default=str, sort_keys=True)


def _safe_json_loads(value: Any, default: Any) -> Any:
    """Safely deserializes JSON strings with error logging."""
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        preview = str(value)[:50] if value is not None else "None"
        logger.warning(f"Failed to parse JSON: {preview}...")
        return default


def _engine_kwargs() -> Dict[str, Any]:
    """Generates SQLAlchemy engine arguments based on database type."""
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
    """
    Retrieves or initializes the global SQLAlchemy engine.
    
    If force_refresh is True, disposes of the existing engine and recreates it.
    """
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
            "Async driver 'asyncpg' is not supported by synchronous SQLAlchemy. "
            "Please use 'psycopg2' in DATABASE_URL."
        )
        return None

    engine = _initialize_engine_logic(database_url)
    return engine


def _initialize_engine_logic(url: str) -> Optional[Engine]:
    """Isolated logic for engine creation to handle fallback attempts."""
    try:
        new_engine = create_engine(url, **_engine_kwargs())
        logger.info("Database engine initialized")
        return new_engine
    except (TypeError, Exception) as exc:
        logger.info("Retrying engine initialization with fallback kwargs")
        try:
            new_engine = create_engine(
                url,
                echo=config.database.echo,
                future=True,
            )
            logger.info("Database engine initialized with fallback")
            return new_engine
        except Exception as final_exc:
            logger.error(
                "Failed to initialize database engine",
                error=str(final_exc),
                original_error=str(exc),
            )
            return None


def get_session_factory() -> Optional[sessionmaker]:
    """Returns the global session factory, initializing it if necessary."""
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
    """Context manager for database sessions with automatic commit/rollback."""
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
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )


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
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)
    purchase_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )


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
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FundamentalAnalysis(Base):
    __tablename__ = "fundamental_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)
    analysis_result = Column(Text, nullable=False)
    period = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


# --- Manager ---

class DatabaseManager:
    """High-level interface for database operations used by the application."""

    def create_tables(self) -> bool:
        """Create all database tables if an engine is available."""
        try:
            db_engine = get_engine()
            if db_engine is None:
                logger.warning("Skipping table creation: database unavailable")
                return False

            Base.metadata.create_all(bind=db_engine)
            logger.info("Database tables created successfully")
            return True
        except Exception as exc:
            logger.error("Failed to create tables", error=str(exc))
            return False

    def get_session(self) -> Optional[Session]:
        """Create a new SQLAlchemy session."""
        factory = get_session_factory()
        return factory() if factory is not None else None

    def health_check(self) -> bool:
        """Verify database connectivity."""
        try:
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning("Database health check failed", error=str(exc))
            return False

    def store_financial_data(
        self, symbol: str, data: Dict[str, Any], data_type: str
    ) -> bool:
        """Persist a single market data snapshot."""
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
        self, symbol: str, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Retrieve recent financial data for a symbol."""
        normalized_symbol = _normalize_symbol(symbol)
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
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
                "Failed to load historical data",
                symbol=normalized_symbol,
                error=str(exc),
            )
            return []

    def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Create or update user configuration."""
        try:
            with get_db_session() as session:
                existing = (
                    session.query(UserPreferences)
                    .filter(UserPreferences.user_id == user_id)
                    .first()
                )

                data = dict(preferences)
                if "favorite_symbols" in data:
                    data["favorite_symbols"] = _safe_json_dumps(data["favorite_symbols"])

                if existing:
                    for key, value in data.items():
                        if hasattr(existing, key) and key != "id":
                            setattr(existing, key, value)
                else:
                    session.add(UserPreferences(user_id=user_id, **data))
            return True
        except Exception as exc:
            logger.warning(f"Failed to save preferences for {user_id}: {exc}")
            return False

    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user configuration."""
        try:
            with get_db_session() as session:
                prefs = (
                    session.query(UserPreferences)
                    .filter(UserPreferences.user_id == user_id)
                    .first()
                )
                if not prefs:
                    return None

                favs = _safe_json_loads(prefs.favorite_symbols, [])
                return {
                    "auto_refresh": prefs.auto_refresh,
                    "refresh_interval": prefs.refresh_interval,
                    "favorite_symbols": favs,
                }
        except Exception as exc:
            logger.warning(f"Failed to get preferences for {user_id}: {exc}")
            return None

    def create_market_alert(
        self, user_id: str, symbol: str, alert_type: str, target_price: float
    ) -> bool:
        """Register a new price alert."""
        normalized_symbol = _normalize_symbol(symbol)
        alert_type_clean = alert_type.strip().lower()

        if alert_type_clean not in {"above", "below"}:
            return False

        try:
            with get_db_session() as session:
                session.add(
                    MarketAlerts(
                        user_id=user_id,
                        symbol=normalized_symbol,
                        alert_type=alert_type_clean,
                        target_price=float(target_price),
                    )
                )
            return True
        except Exception as exc:
            logger.warning(f"Failed to create alert for {symbol}: {exc}")
            return False

    def get_active_alerts(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all currently active alerts."""
        try:
            with get_db_session() as session:
                query = session.query(MarketAlerts).filter(MarketAlerts.is_active.is_(True))
                if user_id:
                    query = query.filter(MarketAlerts.user_id == user_id)

                alerts = query.all()
                return [
                    {
                        "id": str(a.id),
                        "user_id": a.user_id,
                        "symbol": a.symbol,
                        "alert_type": a.alert_type,
                        "target_price": a.target_price,
                        "created_at": a.created_at,
                    }
                    for a in alerts
                ]
        except Exception as exc:
            logger.warning(f"Failed to load active alerts: {exc}")
            return []

    def deactivate_alert(self, alert_id: str) -> bool:
        """Disable a triggered alert."""
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
            logger.warning(f"Failed to deactivate alert {alert_id}: {exc}")
            return False

    def store_news_article(self, article: Dict[str, Any]) -> bool:
        """Persist news if it doesn't already exist via URL check."""
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
                        symbols_mentioned=_safe_json_dumps(
                            article.get("symbols_mentioned", [])
                        ),
                        sector=article.get("sector", ""),
                        sentiment=article.get("sentiment", "neutral"),
                    )
                )
            return True
        except Exception as exc:
            logger.warning(f"Failed to store news article: {exc}")
            return False

    def store_fundamental_analysis(
        self,
        symbol: str,
        analysis_type: str,
        analysis_result: Dict[str, Any],
        period: str,
    ) -> bool:
        """Save analysis results for a symbol."""
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
            logger.warning(f"Failed to store analysis for {normalized_symbol}: {exc}")
            return False


db_manager = DatabaseManager()
