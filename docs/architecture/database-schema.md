# Database Schema

## PostgreSQL Schema (Transactional Data)

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Legal entities table for compliance
CREATE TABLE legal_entities (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(255) NOT NULL,
    jurisdiction VARCHAR(100) NOT NULL,
    registration_number VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Personality profiles for anti-detection
CREATE TABLE personality_profiles (
    personality_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    risk_appetite DECIMAL(3,2) NOT NULL CHECK (risk_appetite BETWEEN 0.5 AND 2.0),
    preferred_pairs JSONB NOT NULL DEFAULT '[]'::jsonb,
    trading_sessions JSONB NOT NULL DEFAULT '[]'::jsonb,
    aggression_level DECIMAL(3,2) NOT NULL CHECK (aggression_level BETWEEN 0.0 AND 1.0),
    patience_score DECIMAL(3,2) NOT NULL CHECK (patience_score BETWEEN 0.0 AND 1.0),
    favorite_timeframes JSONB NOT NULL DEFAULT '[]'::jsonb,
    position_hold_preference VARCHAR(20) CHECK (position_hold_preference IN ('scalper', 'day_trader', 'swing_trader')),
    variance_tolerance DECIMAL(3,2) NOT NULL DEFAULT 0.1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trading accounts
CREATE TABLE trading_accounts (
    account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prop_firm VARCHAR(50) NOT NULL CHECK (prop_firm IN ('FTMO', 'MyForexFunds', 'FundedNext')),
    account_number VARCHAR(100) NOT NULL,
    legal_entity_id UUID NOT NULL REFERENCES legal_entities(entity_id),
    personality_profile_id UUID REFERENCES personality_profiles(personality_id),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'in_drawdown', 'terminated')),
    balance DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    equity DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    max_daily_loss DECIMAL(12,2) NOT NULL,
    max_total_loss DECIMAL(12,2) NOT NULL,
    current_daily_pnl DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    max_drawdown_reached DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    encrypted_credentials TEXT, -- Encrypted broker credentials
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(prop_firm, account_number)
);

-- Trading signals
CREATE TABLE trading_signals (
    signal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('buy', 'sell')),
    confidence_score DECIMAL(5,2) NOT NULL CHECK (confidence_score BETWEEN 0.00 AND 100.00),
    entry_price DECIMAL(10,5) NOT NULL,
    stop_loss DECIMAL(10,5) NOT NULL,
    take_profit DECIMAL(10,5) NOT NULL,
    risk_reward_ratio DECIMAL(4,2) NOT NULL,
    wyckoff_phase VARCHAR(50),
    pattern_type VARCHAR(100),
    volume_confirmation BOOLEAN NOT NULL DEFAULT false,
    timeframe VARCHAR(10) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'executed', 'expired', 'rejected')),
    created_by_agent VARCHAR(50) NOT NULL
);

-- Positions
CREATE TABLE positions (
    position_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES trading_accounts(account_id),
    signal_id UUID REFERENCES trading_signals(signal_id),
    symbol VARCHAR(20) NOT NULL,
    position_type VARCHAR(10) NOT NULL CHECK (position_type IN ('long', 'short')),
    volume DECIMAL(10,2) NOT NULL,
    entry_price DECIMAL(10,5) NOT NULL,
    current_price DECIMAL(10,5),
    stop_loss DECIMAL(10,5) NOT NULL,
    take_profit DECIMAL(10,5) NOT NULL,
    unrealized_pnl DECIMAL(12,2) DEFAULT 0.00,
    realized_pnl DECIMAL(12,2) DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed', 'partial')),
    entry_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    exit_time TIMESTAMP WITH TIME ZONE,
    wyckoff_phase VARCHAR(50),
    confidence_score DECIMAL(5,2),
    risk_reward_ratio DECIMAL(4,2)
);

-- Agent states for monitoring
CREATE TABLE agent_states (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(50) NOT NULL CHECK (agent_type IN 
        ('market_analysis', 'risk_management', 'execution', 'circuit_breaker', 
         'personality', 'learning', 'compliance', 'correlation')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error', 'maintenance')),
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    performance_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    error_count INTEGER NOT NULL DEFAULT 0,
    version VARCHAR(20) NOT NULL,
    learning_enabled BOOLEAN NOT NULL DEFAULT true,
    circuit_breaker_status VARCHAR(20) NOT NULL DEFAULT 'normal' 
        CHECK (circuit_breaker_status IN ('normal', 'warning', 'tripped')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## TimescaleDB Schema (Time-Series Data)

```sql
-- Market data table (TimescaleDB hypertable)
CREATE TABLE market_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL(10,5) NOT NULL,
    high DECIMAL(10,5) NOT NULL,
    low DECIMAL(10,5) NOT NULL,
    close DECIMAL(10,5) NOT NULL,
    volume BIGINT NOT NULL,
    bid DECIMAL(10,5),
    ask DECIMAL(10,5),
    spread DECIMAL(6,2),
    timeframe VARCHAR(10) NOT NULL -- M1, M5, M15, H1, H4, D1
);

-- Convert to hypertable
SELECT create_hypertable('market_data', 'time', chunk_time_interval => INTERVAL '1 day');

-- Account balance history
CREATE TABLE account_balance_history (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    account_id UUID NOT NULL,
    balance DECIMAL(12,2) NOT NULL,
    equity DECIMAL(12,2) NOT NULL,
    margin_used DECIMAL(12,2) NOT NULL,
    margin_free DECIMAL(12,2) NOT NULL,
    margin_level DECIMAL(6,2) NOT NULL,
    daily_pnl DECIMAL(12,2) NOT NULL,
    drawdown DECIMAL(12,2) NOT NULL
);

SELECT create_hypertable('account_balance_history', 'time', chunk_time_interval => INTERVAL '7 days');
```
