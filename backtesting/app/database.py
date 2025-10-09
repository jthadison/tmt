"""
Database connection and session management
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, StaticPool
import structlog

from .config import get_settings
from .models.market_data import Base

logger = structlog.get_logger()


class Database:
    """Database connection manager"""

    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session_maker = None

    async def connect(self):
        """Initialize database connection"""
        logger.info("Connecting to database", url=self.settings.database_url)

        # Configure engine options based on database type
        engine_options = {
            "echo": False,
            "pool_pre_ping": True,
        }

        # SQLite doesn't support pool_size and max_overflow
        if "sqlite" not in self.settings.database_url:
            engine_options["pool_size"] = self.settings.database_pool_size
            engine_options["max_overflow"] = self.settings.database_max_overflow
        else:
            # Use StaticPool for SQLite to maintain single connection (important for in-memory DBs)
            engine_options["poolclass"] = StaticPool
            # For SQLite, we need connect_args to handle threading
            engine_options["connect_args"] = {"check_same_thread": False}

        self.engine = create_async_engine(
            self.settings.database_url,
            **engine_options,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("Database connection established")

    async def disconnect(self):
        """Close database connection"""
        if self.engine:
            logger.info("Closing database connection")
            await self.engine.dispose()
            logger.info("Database connection closed")

    async def create_tables(self):
        """Create all database tables"""
        logger.info("Creating database tables")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def enable_timescaledb(self):
        """Enable TimescaleDB extension and create hypertables"""
        logger.info("Enabling TimescaleDB extension")

        from sqlalchemy import text

        async with self.engine.begin() as conn:
            # Enable TimescaleDB extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))

            # Convert market_candles to hypertable (time-series optimized)
            # Only create if not already a hypertable
            await conn.execute(text("""
                SELECT create_hypertable(
                    'market_candles',
                    'timestamp',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '7 days'
                )
            """))

            # Create compression policy (compress data older than 30 days)
            await conn.execute(text("""
                SELECT add_compression_policy(
                    'market_candles',
                    INTERVAL '30 days',
                    if_not_exists => TRUE
                )
            """))

            # Create retention policy (keep data for 7 years to match audit requirements)
            await conn.execute(text("""
                SELECT add_retention_policy(
                    'market_candles',
                    INTERVAL '7 years',
                    if_not_exists => TRUE
                )
            """))

        logger.info("TimescaleDB extension enabled and hypertables created")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        if not self.async_session_maker:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()
            finally:
                await session.close()


# Global database instance
db = Database()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session"""
    async with db.get_session() as session:
        yield session
