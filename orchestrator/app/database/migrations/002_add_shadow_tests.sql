-- Migration 002: Add shadow_tests table for parameter A/B testing
-- Description: Creates shadow_tests table for tracking parameter optimization experiments
-- Author: Trading System
-- Date: 2025-10-10

-- Table: shadow_tests
-- Stores active and completed shadow test metadata with performance metrics
CREATE TABLE IF NOT EXISTS shadow_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id TEXT UNIQUE NOT NULL,
    suggestion_id TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    session TEXT,
    current_value DECIMAL(5,2),
    test_value DECIMAL(5,2),
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    min_duration_days INTEGER DEFAULT 7,
    allocation_pct DECIMAL(4,2) DEFAULT 10.0,
    control_trades INTEGER DEFAULT 0,
    test_trades INTEGER DEFAULT 0,
    control_win_rate DECIMAL(5,2),
    test_win_rate DECIMAL(5,2),
    control_avg_rr DECIMAL(4,2),
    test_avg_rr DECIMAL(4,2),
    improvement_pct DECIMAL(5,2),
    p_value DECIMAL(6,4),
    status TEXT CHECK(status IN ('ACTIVE', 'COMPLETED', 'TERMINATED', 'DEPLOYED')),
    termination_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_shadow_tests_status ON shadow_tests(status);
CREATE INDEX IF NOT EXISTS idx_shadow_tests_start_date ON shadow_tests(start_date);
CREATE INDEX IF NOT EXISTS idx_shadow_tests_test_id ON shadow_tests(test_id);
