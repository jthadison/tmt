"""TimescaleDB client for efficient time-series market data storage."""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool, Connection

from agents.market_analysis.app.market_data.data_normalizer import MarketTick

logger = logging.getLogger(__name__)


class TimescaleClient:
    """
    TimescaleDB client for market data storage and retrieval.
    
    Provides high-performance time-series storage with automatic partitioning,
    compression, and optimized queries for trading applications.
    """
    
    def __init__(
        self,
        database_url: str,
        min_connections: int = 5,
        max_connections: int = 20,
        command_timeout: int = 60
    ):
        """
        Initialize TimescaleDB client.
        
        @param database_url: PostgreSQL connection URL
        @param min_connections: Minimum pool connections
        @param max_connections: Maximum pool connections
        @param command_timeout: Query timeout in seconds
        """
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.command_timeout = command_timeout
        self.pool: Optional[Pool] = None
        
        # Batch insertion settings
        self.batch_size = 1000
        self.batch_timeout = 5.0  # seconds
        self.pending_inserts: List[MarketTick] = []
        self.last_batch_time = datetime.now()
        
        # Performance metrics
        self.insert_count = 0
        self.batch_count = 0
        self.query_count = 0
        
    async def connect(self):
        """Initialize connection pool to TimescaleDB."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=self.command_timeout
            )
            logger.info("Connected to TimescaleDB")
            
            # Initialize database schema if needed
            await self._initialize_schema()
            
        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")
            raise
            
    async def disconnect(self):
        """Close connection pool and cleanup resources."""
        if self.pool:
            # Flush any pending inserts
            if self.pending_inserts:
                await self._flush_batch()
                
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from TimescaleDB")
            
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool with proper cleanup."""
        if not self.pool:
            raise RuntimeError("Database not connected")
            
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
            
    async def _initialize_schema(self):
        """Initialize TimescaleDB schema with hypertables and indexes."""
        schema_sql = """
        -- Create market_data table if not exists
        CREATE TABLE IF NOT EXISTS market_data (
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            open DECIMAL(15,8) NOT NULL,
            high DECIMAL(15,8) NOT NULL,
            low DECIMAL(15,8) NOT NULL,
            close DECIMAL(15,8) NOT NULL,
            volume BIGINT NOT NULL,
            source VARCHAR(20) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create hypertable (idempotent)
        SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');
        
        -- Create indexes for efficient queries
        CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data (symbol, time DESC);
        CREATE INDEX IF NOT EXISTS idx_market_data_timeframe ON market_data (timeframe, time DESC);
        CREATE INDEX IF NOT EXISTS idx_market_data_source ON market_data (source, time DESC);
        CREATE INDEX IF NOT EXISTS idx_market_data_created_at ON market_data (created_at);
        
        -- Create continuous aggregate for 5-minute data
        CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_5m
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('5 minutes', time) AS bucket,
            symbol,
            source,
            FIRST(open, time) AS open,
            MAX(high) AS high,
            MIN(low) AS low,
            LAST(close, time) AS close,
            SUM(volume) AS volume,
            COUNT(*) AS tick_count
        FROM market_data
        WHERE timeframe = '1m'
        GROUP BY bucket, symbol, source
        WITH NO DATA;
        
        -- Enable compression on chunks older than 7 days
        SELECT add_compression_policy('market_data', INTERVAL '7 days', if_not_exists => TRUE);
        
        -- Set retention policy (optional - keep 2 years)
        SELECT add_retention_policy('market_data', INTERVAL '2 years', if_not_exists => TRUE);
        """
        
        try:
            async with self.get_connection() as conn:
                await conn.execute(schema_sql)
            logger.info("TimescaleDB schema initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise
            
    async def insert_tick(self, tick: MarketTick, batch: bool = True):
        """
        Insert market tick with optional batching.
        
        @param tick: MarketTick to insert
        @param batch: Use batching for better performance
        """
        if batch:
            self.pending_inserts.append(tick)
            
            # Check if batch should be flushed
            should_flush = (
                len(self.pending_inserts) >= self.batch_size or
                (datetime.now() - self.last_batch_time).total_seconds() > self.batch_timeout
            )
            
            if should_flush:
                await self._flush_batch()
        else:
            await self._insert_single_tick(tick)
            
    async def _insert_single_tick(self, tick: MarketTick):
        """Insert single tick directly."""
        insert_sql = """
        INSERT INTO market_data (time, symbol, timeframe, open, high, low, close, volume, source)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT DO NOTHING
        """
        
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    insert_sql,
                    tick.timestamp, tick.symbol, tick.timeframe,
                    tick.open, tick.high, tick.low, tick.close,
                    tick.volume, tick.source
                )
            self.insert_count += 1
            
        except Exception as e:
            logger.error(f"Failed to insert tick for {tick.symbol}: {e}")
            raise
            
    async def _flush_batch(self):
        """Flush pending inserts as a batch."""
        if not self.pending_inserts:
            return
            
        insert_sql = """
        INSERT INTO market_data (time, symbol, timeframe, open, high, low, close, volume, source)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT DO NOTHING
        """
        
        try:
            async with self.get_connection() as conn:
                # Prepare batch data
                batch_data = [
                    (
                        tick.timestamp, tick.symbol, tick.timeframe,
                        tick.open, tick.high, tick.low, tick.close,
                        tick.volume, tick.source
                    )
                    for tick in self.pending_inserts
                ]
                
                await conn.executemany(insert_sql, batch_data)
                
            logger.debug(f"Flushed batch of {len(self.pending_inserts)} ticks")
            self.insert_count += len(self.pending_inserts)
            self.batch_count += 1
            
            # Clear batch
            self.pending_inserts.clear()
            self.last_batch_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to flush batch: {e}")
            # Don't clear pending_inserts on error - they can be retried
            raise
            
    async def get_latest_price(self, symbol: str, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get latest price for a symbol.
        
        @param symbol: Symbol to query
        @param source: Optional data source filter
        @returns: Latest price data or None
        """
        query = """
        SELECT time, symbol, timeframe, open, high, low, close, volume, source
        FROM market_data
        WHERE symbol = $1
        """
        params = [symbol]
        
        if source:
            query += " AND source = $2"
            params.append(source)
            
        query += " ORDER BY time DESC LIMIT 1"
        
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow(query, *params)
                
            self.query_count += 1
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest price for {symbol}: {e}")
            raise
            
    async def get_historical_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        timeframe: str = "1m",
        source: Optional[str] = None,
        limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Get historical market data for a time range.
        
        @param symbol: Symbol to query
        @param start_time: Start of time range
        @param end_time: End of time range
        @param timeframe: Data timeframe filter
        @param source: Optional data source filter
        @param limit: Maximum records to return
        @returns: List of historical data records
        """
        query = """
        SELECT time, symbol, timeframe, open, high, low, close, volume, source
        FROM market_data
        WHERE symbol = $1 AND time >= $2 AND time <= $3
        """
        params = [symbol, start_time, end_time]
        
        if timeframe:
            query += f" AND timeframe = ${len(params) + 1}"
            params.append(timeframe)
            
        if source:
            query += f" AND source = ${len(params) + 1}"
            params.append(source)
            
        query += f" ORDER BY time ASC LIMIT ${len(params) + 1}"
        params.append(limit)
        
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch(query, *params)
                
            self.query_count += 1
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            raise
            
    async def get_data_gaps(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        expected_interval: timedelta = timedelta(minutes=1)
    ) -> List[Tuple[datetime, datetime]]:
        """
        Detect gaps in stored data for a symbol.
        
        @param symbol: Symbol to check
        @param start_time: Start of time range
        @param end_time: End of time range
        @param expected_interval: Expected interval between data points
        @returns: List of gap periods (start, end)
        """
        query = """
        WITH gaps AS (
            SELECT
                time,
                LEAD(time) OVER (ORDER BY time) AS next_time,
                LEAD(time) OVER (ORDER BY time) - time AS gap_duration
            FROM market_data
            WHERE symbol = $1 AND time >= $2 AND time <= $3
            ORDER BY time
        )
        SELECT time, next_time
        FROM gaps
        WHERE gap_duration > $4
        ORDER BY time
        """
        
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch(
                    query, symbol, start_time, end_time, expected_interval
                )
                
            gaps = [(row['time'], row['next_time']) for row in rows if row['next_time']]
            return gaps
            
        except Exception as e:
            logger.error(f"Failed to detect gaps for {symbol}: {e}")
            raise
            
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics and performance metrics.
        
        @returns: Dictionary with storage statistics
        """
        stats_query = """
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            MIN(time) as earliest_data,
            MAX(time) as latest_data,
            pg_size_pretty(pg_total_relation_size('market_data')) as table_size
        FROM market_data;
        """
        
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow(stats_query)
                
            stats = dict(row) if row else {}
            
            # Add performance metrics
            stats.update({
                'insert_count': self.insert_count,
                'batch_count': self.batch_count,
                'query_count': self.query_count,
                'pending_inserts': len(self.pending_inserts)
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            raise
            
    async def optimize_storage(self):
        """Run storage optimization tasks."""
        try:
            async with self.get_connection() as conn:
                # Update continuous aggregate
                await conn.execute("CALL refresh_continuous_aggregate('market_data_5m', NULL, NULL)")
                
                # Analyze table for query optimization
                await conn.execute("ANALYZE market_data")
                
            logger.info("Storage optimization completed")
            
        except Exception as e:
            logger.error(f"Storage optimization failed: {e}")
            raise