"""Database session management and initialization."""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models import Base

logger = logging.getLogger(__name__)

# Global session factory and engine
_engine = None
_SessionLocal = None


def init_postgres_db() -> None:
    """Initialize PostgreSQL database."""
    global _engine, _SessionLocal

    if not settings.database_url:
        logger.error("DATABASE_URL not set, cannot initialize PostgreSQL")
        return

    logger.info("Initializing PostgreSQL database...")

    # Create engine with connection pooling
    _engine = create_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,  # Test connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Create all tables
    Base.metadata.create_all(_engine)
    logger.info("PostgreSQL database initialized")

    # Create session factory
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def init_sqlite_db() -> None:
    """Initialize SQLite database for testing."""
    global _engine, _SessionLocal

    logger.info("Initializing SQLite database (in-memory)...")

    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(_engine)
    logger.info("SQLite database initialized")

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_db_session() -> Session:
    """Get a database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_postgres_db() first.")
    return _SessionLocal()


def close_db_session(db: Session) -> None:
    """Close a database session."""
    if db:
        db.close()
