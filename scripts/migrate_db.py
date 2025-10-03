#!/usr/bin/env python3
"""
Database Migration Script for TMT Trading System
Handles schema creation and migrations for test and production environments
"""
import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg
from asyncpg import Connection, Pool

# Database schema for trading system
SCHEMA_SQL = """
-- Trading System Core Schema

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'offline',
    port INTEGER,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trading accounts
CREATE TABLE IF NOT EXISTS trading_accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) UNIQUE NOT NULL,
    broker VARCHAR(50) NOT NULL,
    platform VARCHAR(50),
    balance DECIMAL(15, 2) DEFAULT 0,
    equity DECIMAL(15, 2) DEFAULT 0,
    max_drawdown_pct DECIMAL(5, 2),
    daily_loss_limit_pct DECIMAL(5, 2),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR(100) UNIQUE NOT NULL,
    account_id VARCHAR(50) REFERENCES trading_accounts(account_id),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    entry_price DECIMAL(15, 5),
    exit_price DECIMAL(15, 5),
    position_size DECIMAL(15, 2),
    stop_loss DECIMAL(15, 5),
    take_profit DECIMAL(15, 5),
    pnl DECIMAL(15, 2),
    status VARCHAR(20) DEFAULT 'pending',
    opened_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    agent_id VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trade signals
CREATE TABLE IF NOT EXISTS trade_signals (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(100) UNIQUE NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    confidence DECIMAL(5, 4),
    entry_price DECIMAL(15, 5),
    stop_loss DECIMAL(15, 5),
    take_profit DECIMAL(15, 5),
    risk_reward_ratio DECIMAL(5, 2),
    metadata JSONB,
    executed BOOLEAN DEFAULT FALSE,
    trade_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Circuit breaker events
CREATE TABLE IF NOT EXISTS circuit_breaker_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    account_id VARCHAR(50),
    agent_id VARCHAR(50),
    reason TEXT,
    action_taken VARCHAR(100),
    metadata JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15, 5),
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent configurations
CREATE TABLE IF NOT EXISTS agent_configurations (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, config_key, version)
);

-- Audit trail
CREATE TABLE IF NOT EXISTS audit_trail (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    user_id VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    changes JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trades_account_id ON trades(account_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at);

CREATE INDEX IF NOT EXISTS idx_signals_agent_id ON trade_signals(agent_id);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trade_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_executed ON trade_signals(executed);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON trade_signals(created_at);

CREATE INDEX IF NOT EXISTS idx_circuit_breaker_account ON circuit_breaker_events(account_id);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_agent ON circuit_breaker_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_resolved ON circuit_breaker_events(resolved);

CREATE INDEX IF NOT EXISTS idx_metrics_entity ON performance_metrics(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_trail(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_trail(created_at);

-- Enable TimescaleDB hypertables for time-series data (if TimescaleDB extension is available)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        -- Convert performance_metrics to hypertable
        PERFORM create_hypertable('performance_metrics', 'timestamp',
                                  if_not_exists => TRUE);

        -- Convert trades to hypertable
        PERFORM create_hypertable('trades', 'created_at',
                                  if_not_exists => TRUE);
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB extension not available, skipping hypertable creation';
END$$;
"""


async def create_database_if_not_exists(
    admin_url: str, db_name: str
) -> None:
    """Create database if it doesn't exist"""
    try:
        # Connect to postgres database to create target db
        admin_conn = await asyncpg.connect(admin_url)

        # Check if database exists
        exists = await admin_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )

        if not exists:
            print(f"Creating database: {db_name}")
            await admin_conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✓ Database {db_name} created successfully")
        else:
            print(f"✓ Database {db_name} already exists")

        await admin_conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        raise


async def run_migrations(pool: Pool) -> None:
    """Run database migrations"""
    async with pool.acquire() as conn:
        print("Running database migrations...")

        try:
            # Execute schema creation
            await conn.execute(SCHEMA_SQL)
            print("✓ Schema migrations completed successfully")

            # Verify tables were created
            tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            print(f"\n✓ Created {len(tables)} tables:")
            for table in tables:
                print(f"  - {table['table_name']}")

        except Exception as e:
            print(f"✗ Migration failed: {e}")
            raise


async def seed_test_data(pool: Pool) -> None:
    """Seed database with test data"""
    async with pool.acquire() as conn:
        print("\nSeeding test data...")

        try:
            # Insert test agents
            await conn.execute("""
                INSERT INTO agents (agent_id, name, type, status, port)
                VALUES
                    ('market-analysis', 'Market Analysis Agent', 'analysis', 'online', 8001),
                    ('strategy-analysis', 'Strategy Analysis Agent', 'analysis', 'online', 8002),
                    ('parameter-optimization', 'Parameter Optimization Agent', 'optimization', 'online', 8003),
                    ('learning-safety', 'Learning Safety Agent', 'safety', 'online', 8004),
                    ('disagreement-engine', 'Disagreement Engine', 'coordination', 'online', 8005),
                    ('data-collection', 'Data Collection Agent', 'data', 'online', 8006),
                    ('continuous-improvement', 'Continuous Improvement Agent', 'improvement', 'online', 8007),
                    ('pattern-detection', 'Pattern Detection Agent', 'analysis', 'online', 8008)
                ON CONFLICT (agent_id) DO NOTHING
            """)

            # Insert test trading account
            await conn.execute("""
                INSERT INTO trading_accounts (account_id, broker, platform, balance, equity, max_drawdown_pct, daily_loss_limit_pct)
                VALUES ('ACC001', 'OANDA', 'REST_API', 100000.00, 100000.00, 5.00, 2.00)
                ON CONFLICT (account_id) DO NOTHING
            """)

            print("✓ Test data seeded successfully")

        except Exception as e:
            print(f"✗ Seeding failed: {e}")
            raise


async def reset_database(pool: Pool) -> None:
    """Drop all tables and recreate schema (WARNING: destructive)"""
    async with pool.acquire() as conn:
        print("⚠️  Resetting database (dropping all tables)...")

        try:
            # Drop all tables
            await conn.execute("""
                DROP TABLE IF EXISTS audit_trail CASCADE;
                DROP TABLE IF EXISTS agent_configurations CASCADE;
                DROP TABLE IF EXISTS performance_metrics CASCADE;
                DROP TABLE IF EXISTS circuit_breaker_events CASCADE;
                DROP TABLE IF EXISTS trade_signals CASCADE;
                DROP TABLE IF EXISTS trades CASCADE;
                DROP TABLE IF EXISTS trading_accounts CASCADE;
                DROP TABLE IF EXISTS agents CASCADE;
            """)

            print("✓ All tables dropped")

        except Exception as e:
            print(f"✗ Reset failed: {e}")
            raise


async def main():
    parser = argparse.ArgumentParser(description="TMT Trading System Database Migration")
    parser.add_argument(
        "--database-url",
        default="postgresql://postgres:postgres@localhost:5432/trading_system_test",
        help="Database connection URL",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run migrations for test database",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database (drop all tables and recreate)",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed database with test data",
    )

    args = parser.parse_args()

    # Parse database URL to get admin connection
    from urllib.parse import urlparse
    parsed = urlparse(args.database_url)
    db_name = parsed.path.lstrip('/')
    admin_url = args.database_url.replace(f'/{db_name}', '/postgres')

    print(f"TMT Trading System Database Migration")
    print(f"{'=' * 60}")
    print(f"Target Database: {db_name}")
    print(f"{'=' * 60}\n")

    try:
        # Create database if needed
        await create_database_if_not_exists(admin_url, db_name)

        # Connect to target database
        pool = await asyncpg.create_pool(args.database_url, min_size=1, max_size=5)

        try:
            if args.reset:
                await reset_database(pool)

            await run_migrations(pool)

            if args.seed or args.test:
                await seed_test_data(pool)

            print("\n✅ Database migration completed successfully!\n")

        finally:
            await pool.close()

    except Exception as e:
        print(f"\n❌ Migration failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
