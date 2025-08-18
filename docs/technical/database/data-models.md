# Data Models and Relationships

## Overview

This document defines the complete data model for the TMT trading system, including entity relationships, data types, constraints, and business rules implemented at the database level.

## Database Architecture

### Database Systems

#### Primary Database (PostgreSQL 15+)
- **Purpose**: Transactional data, user management, configuration
- **Consistency**: ACID compliance for financial data integrity
- **Backup**: Streaming replication with point-in-time recovery

#### Time-Series Database (TimescaleDB)
- **Purpose**: Market data, performance metrics, system monitoring
- **Optimization**: Time-based partitioning and compression
- **Retention**: Automated data lifecycle management

#### Cache Layer (Redis 7+)
- **Purpose**: Session management, real-time data, message queuing
- **Persistence**: RDB + AOF for durability
- **Clustering**: Redis Cluster for high availability

## Core Data Models

### Trading Account Management

#### accounts
```sql
CREATE TABLE accounts (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_name VARCHAR(100) NOT NULL,
    broker VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('demo', 'live', 'paper')),
    prop_firm VARCHAR(50),
    base_currency CHAR(3) NOT NULL DEFAULT 'USD',
    initial_balance DECIMAL(15,2) NOT NULL,
    current_balance DECIMAL(15,2) NOT NULL,
    available_balance DECIMAL(15,2) NOT NULL,
    margin_used DECIMAL(15,2) DEFAULT 0.00,
    equity DECIMAL(15,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active' 
        CHECK (status IN ('active', 'suspended', 'closed', 'risk_halt')),
    risk_profile VARCHAR(20) NOT NULL DEFAULT 'moderate'
        CHECK (risk_profile IN ('conservative', 'moderate', 'aggressive')),
    max_daily_loss DECIMAL(10,4) NOT NULL,
    max_total_drawdown DECIMAL(10,4) NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_trade_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT positive_balances CHECK (
        initial_balance > 0 AND 
        current_balance >= 0 AND 
        available_balance >= 0
    ),
    CONSTRAINT valid_drawdown CHECK (max_total_drawdown BETWEEN 0.01 AND 0.50)
);

-- Indexes
CREATE INDEX idx_accounts_status ON accounts(status);
CREATE INDEX idx_accounts_broker ON accounts(broker);
CREATE INDEX idx_accounts_prop_firm ON accounts(prop_firm);
CREATE INDEX idx_accounts_updated_at ON accounts(updated_at);
```

#### account_credentials
```sql
CREATE TABLE account_credentials (
    credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    credential_type VARCHAR(50) NOT NULL,
    encrypted_data BYTEA NOT NULL,
    encryption_key_id VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(account_id, credential_type)
);
```

### Trading Operations

#### trades
```sql
CREATE TABLE trades (
    trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(account_id),
    signal_id UUID REFERENCES signals(signal_id),
    
    -- Trade Details
    instrument VARCHAR(20) NOT NULL,
    trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('BUY', 'SELL')),
    position_size DECIMAL(12,2) NOT NULL,
    entry_price DECIMAL(10,5) NOT NULL,
    exit_price DECIMAL(10,5),
    
    -- Risk Management
    stop_loss DECIMAL(10,5),
    take_profit DECIMAL(10,5),
    risk_amount DECIMAL(12,2) NOT NULL,
    risk_percentage DECIMAL(5,4) NOT NULL,
    
    -- P&L Tracking
    gross_pnl DECIMAL(12,2),
    net_pnl DECIMAL(12,2),
    commission DECIMAL(8,2) DEFAULT 0.00,
    swap_fee DECIMAL(8,2) DEFAULT 0.00,
    slippage DECIMAL(8,4) DEFAULT 0.0000,
    
    -- Timing
    signal_time TIMESTAMP WITH TIME ZONE,
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Status and Classification
    status VARCHAR(20) NOT NULL DEFAULT 'open' 
        CHECK (status IN ('open', 'closed', 'cancelled', 'partial')),
    close_reason VARCHAR(50),
    trade_session VARCHAR(20),
    
    -- Platform Integration
    platform_trade_id VARCHAR(100),
    platform_order_ids JSONB DEFAULT '[]',
    execution_venue VARCHAR(50),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT positive_position_size CHECK (position_size > 0),
    CONSTRAINT valid_risk_percentage CHECK (risk_percentage BETWEEN 0.001 AND 0.10),
    CONSTRAINT valid_prices CHECK (entry_price > 0 AND (exit_price IS NULL OR exit_price > 0))
);

-- Indexes for performance
CREATE INDEX idx_trades_account_id ON trades(account_id);
CREATE INDEX idx_trades_instrument ON trades(instrument);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_entry_time ON trades(entry_time);
CREATE INDEX idx_trades_signal_id ON trades(signal_id);
CREATE INDEX idx_trades_pnl ON trades(net_pnl) WHERE net_pnl IS NOT NULL;
```

#### positions
```sql
CREATE TABLE positions (
    position_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(account_id),
    instrument VARCHAR(20) NOT NULL,
    
    -- Position Details
    position_type VARCHAR(10) NOT NULL CHECK (position_type IN ('LONG', 'SHORT')),
    total_size DECIMAL(12,2) NOT NULL,
    average_entry_price DECIMAL(10,5) NOT NULL,
    current_price DECIMAL(10,5),
    
    -- Risk Management
    stop_loss DECIMAL(10,5),
    take_profit DECIMAL(10,5),
    trailing_stop_distance DECIMAL(10,5),
    
    -- P&L Tracking
    unrealized_pnl DECIMAL(12,2) DEFAULT 0.00,
    realized_pnl DECIMAL(12,2) DEFAULT 0.00,
    daily_pnl DECIMAL(12,2) DEFAULT 0.00,
    
    -- Timing
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'closing', 'closed')),
    
    -- Platform Integration
    platform_position_ids JSONB DEFAULT '[]',
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT positive_size CHECK (total_size > 0),
    CONSTRAINT positive_entry_price CHECK (average_entry_price > 0),
    
    UNIQUE(account_id, instrument, status) 
        DEFERRABLE INITIALLY DEFERRED
);

-- Indexes
CREATE INDEX idx_positions_account_id ON positions(account_id);
CREATE INDEX idx_positions_instrument ON positions(instrument);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_unrealized_pnl ON positions(unrealized_pnl);
```

### Signal Generation

#### signals
```sql
CREATE TABLE signals (
    signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Signal Details
    instrument VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL')),
    confidence DECIMAL(4,3) NOT NULL CHECK (confidence BETWEEN 0.000 AND 1.000),
    
    -- Price Levels
    entry_price DECIMAL(10,5) NOT NULL,
    stop_loss DECIMAL(10,5) NOT NULL,
    take_profit DECIMAL(10,5) NOT NULL,
    risk_reward_ratio DECIMAL(4,2) NOT NULL,
    
    -- Analysis Details
    timeframe VARCHAR(10) NOT NULL,
    wyckoff_phase VARCHAR(50),
    volume_confirmation BOOLEAN DEFAULT false,
    market_structure_break BOOLEAN DEFAULT false,
    
    -- Generated By
    agent_id VARCHAR(50) NOT NULL,
    model_version VARCHAR(20),
    analysis_data JSONB DEFAULT '{}',
    
    -- Timing
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'executed', 'expired', 'cancelled')),
    
    -- Execution Tracking
    execution_count INTEGER DEFAULT 0,
    total_executed_size DECIMAL(12,2) DEFAULT 0.00,
    
    -- Performance Tracking
    signal_performance JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT positive_prices CHECK (
        entry_price > 0 AND 
        stop_loss > 0 AND 
        take_profit > 0
    ),
    CONSTRAINT valid_risk_reward CHECK (risk_reward_ratio >= 1.0)
);

-- Indexes
CREATE INDEX idx_signals_instrument ON signals(instrument);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_generated_at ON signals(generated_at);
CREATE INDEX idx_signals_confidence ON signals(confidence);
CREATE INDEX idx_signals_agent_id ON signals(agent_id);
```

### Market Data Models

#### market_data (TimescaleDB)
```sql
CREATE TABLE market_data (
    time TIMESTAMPTZ NOT NULL,
    instrument VARCHAR(20) NOT NULL,
    
    -- OHLC Data
    open DECIMAL(10,5) NOT NULL,
    high DECIMAL(10,5) NOT NULL,
    low DECIMAL(10,5) NOT NULL,
    close DECIMAL(10,5) NOT NULL,
    
    -- Volume Data
    volume BIGINT DEFAULT 0,
    tick_count INTEGER DEFAULT 0,
    
    -- Derived Metrics
    typical_price DECIMAL(10,5) GENERATED ALWAYS AS ((high + low + close) / 3) STORED,
    price_change DECIMAL(10,5),
    price_change_pct DECIMAL(8,4),
    
    -- Timeframe
    timeframe VARCHAR(10) NOT NULL,
    
    -- Data Quality
    data_source VARCHAR(50) NOT NULL,
    quality_score DECIMAL(3,2) DEFAULT 1.00,
    
    -- Constraints
    CONSTRAINT valid_ohlc CHECK (
        open > 0 AND high > 0 AND low > 0 AND close > 0 AND
        high >= low AND
        high >= open AND high >= close AND
        low <= open AND low <= close
    ),
    CONSTRAINT valid_volume CHECK (volume >= 0),
    CONSTRAINT valid_quality CHECK (quality_score BETWEEN 0.00 AND 1.00)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('market_data', 'time', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_market_data_instrument_time ON market_data (instrument, time DESC);
CREATE INDEX idx_market_data_timeframe ON market_data (timeframe);
```

### Risk Management Models

#### risk_limits
```sql
CREATE TABLE risk_limits (
    limit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(account_id),
    
    -- Limit Scope
    limit_type VARCHAR(50) NOT NULL,
    limit_scope VARCHAR(20) NOT NULL CHECK (limit_scope IN ('account', 'instrument', 'portfolio', 'system')),
    scope_identifier VARCHAR(100), -- instrument name, portfolio id, etc.
    
    -- Limit Values
    limit_value DECIMAL(15,4) NOT NULL,
    limit_unit VARCHAR(20) NOT NULL, -- 'USD', 'percentage', 'units', etc.
    warning_threshold DECIMAL(15,4),
    
    -- Time Scope
    time_window VARCHAR(20), -- 'daily', 'weekly', 'monthly', 'position'
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Metadata
    description TEXT,
    created_by VARCHAR(100) NOT NULL,
    approved_by VARCHAR(100),
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    effective_until TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT positive_limit_value CHECK (limit_value > 0),
    CONSTRAINT valid_warning_threshold CHECK (
        warning_threshold IS NULL OR 
        warning_threshold <= limit_value
    )
);

CREATE INDEX idx_risk_limits_account_id ON risk_limits(account_id);
CREATE INDEX idx_risk_limits_type_scope ON risk_limits(limit_type, limit_scope);
CREATE INDEX idx_risk_limits_active ON risk_limits(is_active);
```

#### risk_events
```sql
CREATE TABLE risk_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(account_id),
    
    -- Event Details
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('info', 'warning', 'critical', 'emergency')),
    event_source VARCHAR(50) NOT NULL,
    
    -- Risk Metrics
    risk_measure VARCHAR(50),
    current_value DECIMAL(15,4),
    limit_value DECIMAL(15,4),
    threshold_breached VARCHAR(20),
    
    -- Event Context
    related_trade_id UUID REFERENCES trades(trade_id),
    related_position_id UUID REFERENCES positions(position_id),
    related_limit_id UUID REFERENCES risk_limits(limit_id),
    
    -- Actions Taken
    action_taken VARCHAR(100),
    auto_resolved BOOLEAN DEFAULT false,
    resolution_time TIMESTAMP WITH TIME ZONE,
    
    -- Event Data
    event_data JSONB DEFAULT '{}',
    
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for time-series queries
    CONSTRAINT valid_severity CHECK (severity IN ('info', 'warning', 'critical', 'emergency'))
);

-- Indexes
CREATE INDEX idx_risk_events_account_id ON risk_events(account_id);
CREATE INDEX idx_risk_events_occurred_at ON risk_events(occurred_at);
CREATE INDEX idx_risk_events_severity ON risk_events(severity);
CREATE INDEX idx_risk_events_type ON risk_events(event_type);
```

### System Management

#### agents
```sql
CREATE TABLE agents (
    agent_id VARCHAR(50) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    
    -- Configuration
    config_version VARCHAR(20) NOT NULL,
    config_data JSONB NOT NULL DEFAULT '{}',
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'stopped'
        CHECK (status IN ('running', 'stopped', 'error', 'maintenance')),
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    
    -- Performance Metrics
    uptime_seconds BIGINT DEFAULT 0,
    total_requests BIGINT DEFAULT 0,
    error_count BIGINT DEFAULT 0,
    average_response_time_ms DECIMAL(8,2),
    
    -- Version Info
    version VARCHAR(20) NOT NULL,
    deployment_id VARCHAR(100),
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_last_heartbeat ON agents(last_heartbeat);
```

#### system_events
```sql
CREATE TABLE system_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event Classification
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    
    -- Event Source
    source_agent VARCHAR(50) REFERENCES agents(agent_id),
    source_component VARCHAR(100),
    source_instance VARCHAR(100),
    
    -- Event Details
    event_message TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    
    -- Correlation
    correlation_id UUID,
    parent_event_id UUID REFERENCES system_events(event_id),
    trace_id VARCHAR(100),
    
    -- Timestamps
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Processing
    processed BOOLEAN DEFAULT false,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP WITH TIME ZONE
);

-- Convert to hypertable for time-series performance
SELECT create_hypertable('system_events', 'occurred_at', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_system_events_type ON system_events(event_type);
CREATE INDEX idx_system_events_severity ON system_events(severity);
CREATE INDEX idx_system_events_source ON system_events(source_agent, source_component);
CREATE INDEX idx_system_events_correlation ON system_events(correlation_id);
```

## Data Relationships

### Entity Relationship Diagram

```
accounts (1) ──────── (M) trades
    │                     │
    │                     │
    │                 signal_id
    │                     │
    │                     ▼
    │                 signals (1) ──── (M) signal_executions
    │
    ├── (1:M) positions
    ├── (1:M) risk_limits
    ├── (1:M) risk_events
    ├── (1:1) account_credentials
    └── (1:M) performance_metrics

agents (1) ──────── (M) system_events
    │
    └── (1:M) signals

market_data ── (related by instrument) ── trades/positions/signals
```

### Key Relationships

#### Trading Flow Relationships
1. `signals` → `trades`: One signal can generate multiple trades across accounts
2. `trades` → `positions`: Multiple trades can contribute to a single position
3. `accounts` → `trades/positions`: One account has many trades and positions
4. `accounts` → `risk_limits/risk_events`: Account-specific risk management

#### Audit Trail Relationships
1. `signals` → `trades` → `system_events`: Complete execution audit trail
2. `risk_events` → `trades/positions`: Risk events linked to specific trades
3. `agents` → `signals/system_events`: Agent accountability and monitoring

## Data Integrity Constraints

### Business Rule Constraints

#### Financial Data Integrity
```sql
-- Ensure position P&L consistency
CREATE OR REPLACE FUNCTION check_position_pnl() 
RETURNS TRIGGER AS $$
BEGIN
    -- Verify unrealized P&L calculation
    IF NEW.unrealized_pnl != calculate_unrealized_pnl(NEW.position_id) THEN
        RAISE EXCEPTION 'Position P&L inconsistency detected';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_position_pnl_check 
    BEFORE UPDATE ON positions 
    FOR EACH ROW EXECUTE FUNCTION check_position_pnl();
```

#### Risk Limit Enforcement
```sql
-- Prevent trades that would exceed risk limits
CREATE OR REPLACE FUNCTION enforce_risk_limits() 
RETURNS TRIGGER AS $$
DECLARE
    current_exposure DECIMAL(15,2);
    daily_loss DECIMAL(15,2);
    risk_limit DECIMAL(15,2);
BEGIN
    -- Check position size limits
    SELECT SUM(ABS(total_size * current_price)) INTO current_exposure
    FROM positions 
    WHERE account_id = NEW.account_id AND status = 'open';
    
    -- Get account risk limits
    SELECT limit_value INTO risk_limit
    FROM risk_limits 
    WHERE account_id = NEW.account_id 
      AND limit_type = 'max_exposure' 
      AND is_active = true;
    
    IF current_exposure + (NEW.position_size * NEW.entry_price) > risk_limit THEN
        RAISE EXCEPTION 'Trade would exceed maximum exposure limit';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_risk_limit_check 
    BEFORE INSERT ON trades 
    FOR EACH ROW EXECUTE FUNCTION enforce_risk_limits();
```

### Data Quality Constraints

#### Market Data Validation
```sql
-- Validate market data quality
CREATE OR REPLACE FUNCTION validate_market_data() 
RETURNS TRIGGER AS $$
BEGIN
    -- Check for reasonable price movements
    IF EXISTS (
        SELECT 1 FROM market_data 
        WHERE instrument = NEW.instrument 
          AND time < NEW.time 
          AND ABS((NEW.close - close) / close) > 0.10 -- 10% move
        ORDER BY time DESC 
        LIMIT 1
    ) THEN
        NEW.quality_score = NEW.quality_score * 0.5; -- Reduce quality score
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_market_data_validation 
    BEFORE INSERT ON market_data 
    FOR EACH ROW EXECUTE FUNCTION validate_market_data();
```

## Performance Optimization

### Partitioning Strategy

#### Time-Based Partitioning
```sql
-- Partition trades by month for performance
CREATE TABLE trades_y2025m01 PARTITION OF trades 
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE trades_y2025m02 PARTITION OF trades 
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Automatic partition creation
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    table_name TEXT;
BEGIN
    start_date := DATE_TRUNC('month', NOW());
    end_date := start_date + INTERVAL '1 month';
    table_name := 'trades_y' || EXTRACT(year FROM start_date) || 'm' || 
                  LPAD(EXTRACT(month FROM start_date)::TEXT, 2, '0');
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF trades 
                    FOR VALUES FROM (%L) TO (%L)', 
                   table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- Schedule monthly partition creation
SELECT cron.schedule('create-partitions', '0 0 1 * *', 'SELECT create_monthly_partitions();');
```

### Indexing Strategy

#### Composite Indexes for Query Performance
```sql
-- Multi-column indexes for common query patterns
CREATE INDEX idx_trades_account_time_status ON trades(account_id, entry_time, status);
CREATE INDEX idx_positions_account_instrument ON positions(account_id, instrument);
CREATE INDEX idx_signals_instrument_time ON signals(instrument, generated_at DESC);
CREATE INDEX idx_market_data_covering ON market_data(instrument, time DESC) 
    INCLUDE (open, high, low, close, volume);
```

#### Partial Indexes for Filtered Queries
```sql
-- Index only active/open records
CREATE INDEX idx_positions_open ON positions(account_id, instrument) 
    WHERE status = 'open';
    
CREATE INDEX idx_trades_active ON trades(account_id, entry_time) 
    WHERE status IN ('open', 'partial');
```

For database schema migration procedures, see [Database Migration Strategy](../architecture/database-migration-strategy.md). For performance optimization details, see [Database Performance Optimization](optimization.md).