"""
TimescaleDB Schema and Database Operations - Story 11.4, Task 7

Time-series database schema for overfitting monitoring data.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import text
import structlog

from .models import OverfittingScore, ParameterDrift, PerformanceMetrics

logger = structlog.get_logger()


class Database:
    """Database connection and schema management"""

    def __init__(self, database_url: str):
        """
        Initialize database

        @param database_url: PostgreSQL/TimescaleDB connection URL
        """
        self.database_url = database_url
        self.engine = None
        self.async_session_maker = None

    async def connect(self):
        """Initialize database connection"""
        logger.info("Connecting to TimescaleDB", url=self.database_url)

        engine_options = {
            "echo": False,
            "pool_pre_ping": True,
        }

        if "sqlite" not in self.database_url:
            engine_options["pool_size"] = 10
            engine_options["max_overflow"] = 20

        self.engine = create_async_engine(
            self.database_url,
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

    async def initialize_schema(self):
        """Create TimescaleDB hypertables and indexes"""
        logger.info("Initializing overfitting monitor schema")

        schema_sql = """
        -- Enable TimescaleDB extension
        CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

        -- Overfitting scores table
        CREATE TABLE IF NOT EXISTS overfitting_scores (
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            score DECIMAL(5,3) NOT NULL,
            avg_deviation DECIMAL(5,3),
            max_deviation DECIMAL(5,3),
            session_deviations JSONB,
            alert_level VARCHAR(20) NOT NULL,
            PRIMARY KEY (time)
        );

        -- Convert to hypertable (idempotent)
        SELECT create_hypertable(
            'overfitting_scores',
            'time',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );

        -- Parameter drift table
        CREATE TABLE IF NOT EXISTS parameter_drift (
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            parameter_name VARCHAR(100) NOT NULL,
            current_value DECIMAL(10,3) NOT NULL,
            baseline_value DECIMAL(10,3) NOT NULL,
            deviation_pct DECIMAL(8,3) NOT NULL,
            drift_7d_pct DECIMAL(8,3),
            drift_30d_pct DECIMAL(8,3),
            PRIMARY KEY (time, parameter_name)
        );

        -- Convert to hypertable
        SELECT create_hypertable(
            'parameter_drift',
            'time',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );

        -- Performance tracking table
        CREATE TABLE IF NOT EXISTS performance_tracking (
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            live_sharpe DECIMAL(8,2),
            backtest_sharpe DECIMAL(8,2),
            sharpe_ratio DECIMAL(8,2),
            live_win_rate DECIMAL(5,2),
            backtest_win_rate DECIMAL(5,2),
            live_profit_factor DECIMAL(8,2),
            backtest_profit_factor DECIMAL(8,2),
            degradation_score DECIMAL(5,2),
            PRIMARY KEY (time)
        );

        -- Convert to hypertable
        SELECT create_hypertable(
            'performance_tracking',
            'time',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );

        -- Create indexes for efficient queries
        CREATE INDEX IF NOT EXISTS idx_overfitting_scores_time
            ON overfitting_scores (time DESC);
        CREATE INDEX IF NOT EXISTS idx_overfitting_scores_alert_level
            ON overfitting_scores (alert_level, time DESC);

        CREATE INDEX IF NOT EXISTS idx_parameter_drift_name_time
            ON parameter_drift (parameter_name, time DESC);
        CREATE INDEX IF NOT EXISTS idx_parameter_drift_time
            ON parameter_drift (time DESC);

        CREATE INDEX IF NOT EXISTS idx_performance_tracking_time
            ON performance_tracking (time DESC);

        -- Add compression policy (compress data older than 30 days)
        SELECT add_compression_policy(
            'overfitting_scores',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );

        SELECT add_compression_policy(
            'parameter_drift',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );

        SELECT add_compression_policy(
            'performance_tracking',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );

        -- Add retention policy (keep data for 90 days)
        SELECT add_retention_policy(
            'overfitting_scores',
            INTERVAL '90 days',
            if_not_exists => TRUE
        );

        SELECT add_retention_policy(
            'parameter_drift',
            INTERVAL '90 days',
            if_not_exists => TRUE
        );

        SELECT add_retention_policy(
            'performance_tracking',
            INTERVAL '90 days',
            if_not_exists => TRUE
        );
        """

        async with self.engine.begin() as conn:
            await conn.execute(text(schema_sql))

        logger.info("Overfitting monitor schema initialized")

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

    async def store_overfitting_score(self, score: OverfittingScore):
        """
        Store overfitting score in TimescaleDB

        @param score: OverfittingScore to store
        """
        import json

        insert_sql = """
        INSERT INTO overfitting_scores (
            time, score, avg_deviation, max_deviation,
            session_deviations, alert_level
        )
        VALUES (:time, :score, :avg_deviation, :max_deviation,
                :session_deviations, :alert_level)
        ON CONFLICT (time) DO UPDATE SET
            score = EXCLUDED.score,
            avg_deviation = EXCLUDED.avg_deviation,
            max_deviation = EXCLUDED.max_deviation,
            session_deviations = EXCLUDED.session_deviations,
            alert_level = EXCLUDED.alert_level
        """

        async with self.engine.begin() as conn:
            await conn.execute(
                text(insert_sql),
                {
                    "time": score.time,
                    "score": float(score.score),
                    "avg_deviation": float(score.avg_deviation),
                    "max_deviation": float(score.max_deviation),
                    "session_deviations": json.dumps(score.session_deviations),
                    "alert_level": score.alert_level.value
                }
            )

        logger.debug(f"Stored overfitting score: {score.score:.3f} at {score.time}")

    async def store_parameter_drift(self, drift: ParameterDrift):
        """
        Store parameter drift data

        @param drift: ParameterDrift to store
        """
        insert_sql = """
        INSERT INTO parameter_drift (
            time, parameter_name, current_value, baseline_value,
            deviation_pct, drift_7d_pct, drift_30d_pct
        )
        VALUES (:time, :parameter_name, :current_value, :baseline_value,
                :deviation_pct, :drift_7d_pct, :drift_30d_pct)
        ON CONFLICT (time, parameter_name) DO UPDATE SET
            current_value = EXCLUDED.current_value,
            baseline_value = EXCLUDED.baseline_value,
            deviation_pct = EXCLUDED.deviation_pct,
            drift_7d_pct = EXCLUDED.drift_7d_pct,
            drift_30d_pct = EXCLUDED.drift_30d_pct
        """

        async with self.engine.begin() as conn:
            await conn.execute(
                text(insert_sql),
                {
                    "time": drift.time,
                    "parameter_name": drift.parameter_name,
                    "current_value": float(drift.current_value),
                    "baseline_value": float(drift.baseline_value),
                    "deviation_pct": float(drift.deviation_pct),
                    "drift_7d_pct": float(drift.drift_7d_pct),
                    "drift_30d_pct": float(drift.drift_30d_pct)
                }
            )

        logger.debug(f"Stored parameter drift for '{drift.parameter_name}'")

    async def store_performance_metrics(self, metrics: PerformanceMetrics):
        """
        Store performance tracking metrics

        @param metrics: PerformanceMetrics to store
        """
        insert_sql = """
        INSERT INTO performance_tracking (
            time, live_sharpe, backtest_sharpe, sharpe_ratio,
            live_win_rate, backtest_win_rate, live_profit_factor,
            backtest_profit_factor, degradation_score
        )
        VALUES (:time, :live_sharpe, :backtest_sharpe, :sharpe_ratio,
                :live_win_rate, :backtest_win_rate, :live_profit_factor,
                :backtest_profit_factor, :degradation_score)
        ON CONFLICT (time) DO UPDATE SET
            live_sharpe = EXCLUDED.live_sharpe,
            backtest_sharpe = EXCLUDED.backtest_sharpe,
            sharpe_ratio = EXCLUDED.sharpe_ratio,
            live_win_rate = EXCLUDED.live_win_rate,
            backtest_win_rate = EXCLUDED.backtest_win_rate,
            live_profit_factor = EXCLUDED.live_profit_factor,
            backtest_profit_factor = EXCLUDED.backtest_profit_factor,
            degradation_score = EXCLUDED.degradation_score
        """

        async with self.engine.begin() as conn:
            await conn.execute(
                text(insert_sql),
                {
                    "time": metrics.time,
                    "live_sharpe": float(metrics.live_sharpe),
                    "backtest_sharpe": float(metrics.backtest_sharpe),
                    "sharpe_ratio": float(metrics.sharpe_ratio),
                    "live_win_rate": float(metrics.live_win_rate),
                    "backtest_win_rate": float(metrics.backtest_win_rate),
                    "live_profit_factor": float(metrics.live_profit_factor),
                    "backtest_profit_factor": float(metrics.backtest_profit_factor),
                    "degradation_score": float(metrics.degradation_score)
                }
            )

        logger.debug("Stored performance metrics")

    async def get_overfitting_history(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get overfitting scores for time range

        @param start_time: Start of range
        @param end_time: End of range
        @returns: List of overfitting score records
        """
        query = """
        SELECT time, score, avg_deviation, max_deviation,
               session_deviations, alert_level
        FROM overfitting_scores
        WHERE time >= :start_time AND time <= :end_time
        ORDER BY time ASC
        """

        async with self.engine.begin() as conn:
            result = await conn.execute(
                text(query),
                {"start_time": start_time, "end_time": end_time}
            )
            rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def get_latest_overfitting_score(self) -> Optional[Dict[str, Any]]:
        """
        Get most recent overfitting score

        @returns: Latest score record or None
        """
        query = """
        SELECT time, score, avg_deviation, max_deviation,
               session_deviations, alert_level
        FROM overfitting_scores
        ORDER BY time DESC
        LIMIT 1
        """

        async with self.engine.begin() as conn:
            result = await conn.execute(text(query))
            row = result.fetchone()

        return dict(row._mapping) if row else None

    async def get_parameter_drift_history(
        self,
        parameter_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get parameter drift history for a specific parameter

        @param parameter_name: Parameter to query
        @param start_time: Start of range
        @param end_time: End of range
        @returns: List of drift records
        """
        query = """
        SELECT time, parameter_name, current_value, baseline_value,
               deviation_pct, drift_7d_pct, drift_30d_pct
        FROM parameter_drift
        WHERE parameter_name = :parameter_name
          AND time >= :start_time
          AND time <= :end_time
        ORDER BY time ASC
        """

        async with self.engine.begin() as conn:
            result = await conn.execute(
                text(query),
                {
                    "parameter_name": parameter_name,
                    "start_time": start_time,
                    "end_time": end_time
                }
            )
            rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def get_performance_history(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get performance tracking history

        @param start_time: Start of range
        @param end_time: End of range
        @returns: List of performance records
        """
        query = """
        SELECT time, live_sharpe, backtest_sharpe, sharpe_ratio,
               live_win_rate, backtest_win_rate, live_profit_factor,
               backtest_profit_factor, degradation_score
        FROM performance_tracking
        WHERE time >= :start_time AND time <= :end_time
        ORDER BY time ASC
        """

        async with self.engine.begin() as conn:
            result = await conn.execute(
                text(query),
                {"start_time": start_time, "end_time": end_time}
            )
            rows = result.fetchall()

        return [dict(row._mapping) for row in rows]


# Global database instance
db: Optional[Database] = None


async def get_database() -> Database:
    """Get global database instance"""
    global db
    if db is None:
        raise RuntimeError("Database not initialized")
    return db


async def init_database(database_url: str):
    """
    Initialize global database instance

    @param database_url: PostgreSQL/TimescaleDB connection URL
    """
    global db
    db = Database(database_url)
    await db.connect()
    await db.initialize_schema()
