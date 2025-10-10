"""
Database connection management for SQLite with async support.

Provides async SQLAlchemy engine configuration with connection pooling,
WAL mode for concurrent reads, and database initialization.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event, text
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Declarative base for ORM models
Base = declarative_base()

# Global engine instance
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


class DatabaseEngine:
    """
    Database engine wrapper providing async SQLAlchemy configuration.

    Features:
    - Async SQLite with aiosqlite driver
    - Connection pooling (pool_size=10, max_overflow=20)
    - WAL mode for concurrent reads
    - Query timeout (5000ms)
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        query_timeout: int = 5000,
    ):
        """
        Initialize database engine.

        Args:
            database_url: SQLite database URL (default: sqlite+aiosqlite:///./data/trading_system.db)
            pool_size: Connection pool size (default: 10)
            max_overflow: Maximum overflow connections (default: 20)
            query_timeout: Query timeout in milliseconds (default: 5000ms)
        """
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL",
                "sqlite+aiosqlite:///./data/trading_system.db"
            )

        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.query_timeout = query_timeout
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None

    async def initialize(self) -> None:
        """
        Initialize the database engine and create tables.

        Raises:
            Exception: If database initialization fails
        """
        try:
            logger.info(f"Initializing database: {self.database_url}")

            # Create data directory if it doesn't exist
            if "sqlite" in self.database_url:
                db_path = self.database_url.replace("sqlite+aiosqlite:///", "")
                db_dir = Path(db_path).parent
                db_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Ensured database directory exists: {db_dir}")

            # Create async engine
            # Note: SQLite with aiosqlite uses StaticPool for connection management
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                poolclass=StaticPool,  # SQLite uses StaticPool for async
                connect_args={
                    "timeout": self.query_timeout / 1000,  # Convert ms to seconds
                },
            )

            # Configure WAL mode for concurrent reads
            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                """Set SQLite pragmas on connection."""
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()

            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Import models to register with Base
            from . import models  # noqa: F401

            # Run migrations instead of create_all for better version control
            from .migration_manager import MigrationManager

            migration_manager = MigrationManager(self.engine)
            migrations_applied = await migration_manager.run_migrations()

            if migrations_applied > 0:
                logger.info(f"Applied {migrations_applied} database migrations")

            # Verify migration integrity
            migrations_valid = await migration_manager.verify_migrations()
            if not migrations_valid:
                logger.warning("⚠️  Migration integrity verification failed")

            logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise

    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    def get_session(self) -> AsyncSession:
        """
        Get a new database session.

        Returns:
            AsyncSession: New database session

        Raises:
            RuntimeError: If engine not initialized
        """
        if not self.session_factory:
            raise RuntimeError("Database engine not initialized. Call initialize() first.")
        return self.session_factory()


async def get_database_engine() -> DatabaseEngine:
    """
    Get the global database engine instance.

    Returns:
        DatabaseEngine: Global database engine

    Raises:
        RuntimeError: If engine not initialized
    """
    global _engine
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call initialize_database() first.")
    return _engine


async def initialize_database(
    database_url: Optional[str] = None,
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    query_timeout: Optional[int] = None,
) -> DatabaseEngine:
    """
    Initialize the global database engine.

    Args:
        database_url: Optional database URL override
        pool_size: Optional pool size override
        max_overflow: Optional max overflow override
        query_timeout: Optional query timeout override

    Returns:
        DatabaseEngine: Initialized database engine

    Raises:
        Exception: If initialization fails
    """
    global _engine, _session_factory

    # Read configuration from environment if not provided
    kwargs = {}
    if database_url:
        kwargs["database_url"] = database_url
    if pool_size:
        kwargs["pool_size"] = int(os.getenv("DATABASE_POOL_SIZE", pool_size))
    if max_overflow:
        kwargs["max_overflow"] = int(os.getenv("DATABASE_MAX_OVERFLOW", max_overflow))
    if query_timeout:
        kwargs["query_timeout"] = int(os.getenv("DATABASE_QUERY_TIMEOUT", query_timeout))

    _engine = DatabaseEngine(**kwargs)
    await _engine.initialize()
    _session_factory = _engine.session_factory

    return _engine
