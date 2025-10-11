-- Migration 003: Extend parameter_history for deployment tracking
-- Description: Adds deployment tracking fields to parameter_history table
-- Author: Learning Safety Agent
-- Date: 2025-10-10

-- Add deployment tracking columns to parameter_history table
ALTER TABLE parameter_history ADD COLUMN deployment_id TEXT;
ALTER TABLE parameter_history ADD COLUMN deployment_stage INTEGER CHECK (deployment_stage BETWEEN 1 AND 4);
ALTER TABLE parameter_history ADD COLUMN baseline_metrics TEXT; -- JSON encoded metrics
ALTER TABLE parameter_history ADD COLUMN status TEXT CHECK (status IN ('PENDING', 'ACTIVE', 'COMPLETED', 'ROLLED_BACK'));

-- Create index for deployment queries
CREATE INDEX IF NOT EXISTS idx_parameter_history_deployment_id ON parameter_history(deployment_id);
CREATE INDEX IF NOT EXISTS idx_parameter_history_status ON parameter_history(status);

-- Create approval_requests table for manual approval workflow
CREATE TABLE IF NOT EXISTS approval_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_request_id TEXT UNIQUE NOT NULL,
    suggestion_id TEXT NOT NULL,
    parameter TEXT NOT NULL,
    current_value DECIMAL(5,2),
    suggested_value DECIMAL(5,2),
    change_pct DECIMAL(5,2),
    improvement_pct DECIMAL(5,2),
    p_value DECIMAL(6,4),
    status TEXT CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')) NOT NULL DEFAULT 'PENDING',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by TEXT,
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for approval request queries
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_suggestion_id ON approval_requests(suggestion_id);
