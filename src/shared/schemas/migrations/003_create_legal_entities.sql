-- Migration: Create Legal Entity Separation Tables
-- Version: 003
-- Date: 2025-01-08
-- Description: Tables for legal entity management, audit trails, and compliance

-- Create UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Legal Entities Table
CREATE TABLE IF NOT EXISTS legal_entities (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(200) NOT NULL,
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('LLC', 'Corporation', 'Trust', 'Partnership', 'Sole_Proprietorship')),
    jurisdiction VARCHAR(100) NOT NULL,
    registration_number VARCHAR(100) UNIQUE,
    tax_id VARCHAR(50),
    registered_address TEXT NOT NULL,
    mailing_address TEXT,
    incorporation_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'terminated', 'pending')),
    tos_accepted_version VARCHAR(20),
    tos_accepted_date TIMESTAMP WITH TIME ZONE,
    tos_accepted_ip INET,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Entity Audit Logs Table (Immutable with hash chaining)
CREATE TABLE IF NOT EXISTS entity_audit_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES legal_entities(entity_id) ON DELETE RESTRICT,
    account_id UUID,
    action_type VARCHAR(50) NOT NULL,
    action_details JSONB NOT NULL,
    decision_rationale TEXT,
    correlation_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    signature VARCHAR(256),
    previous_hash VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Decision Logs Table (For independence tracking)
CREATE TABLE IF NOT EXISTS decision_logs (
    decision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES legal_entities(entity_id) ON DELETE RESTRICT,
    account_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decision_type VARCHAR(50) NOT NULL,
    analysis JSONB NOT NULL,
    action JSONB NOT NULL,
    independent_factors JSONB NOT NULL,
    personality_profile VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Geographic Restrictions Table
CREATE TABLE IF NOT EXISTS geographic_restrictions (
    restriction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jurisdiction VARCHAR(100) NOT NULL UNIQUE,
    restriction_level VARCHAR(20) NOT NULL CHECK (restriction_level IN ('allowed', 'restricted', 'prohibited')),
    trading_hours JSONB,
    holidays JSONB,
    regulatory_requirements JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Terms of Service Acceptances Table
CREATE TABLE IF NOT EXISTS tos_acceptances (
    acceptance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES legal_entities(entity_id) ON DELETE RESTRICT,
    version VARCHAR(20) NOT NULL,
    accepted_date TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address INET NOT NULL,
    user_agent TEXT,
    device_fingerprint VARCHAR(256),
    acceptance_method VARCHAR(50) DEFAULT 'click',
    document_hash VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Entity Account Mapping Table
CREATE TABLE IF NOT EXISTS entity_account_mappings (
    mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES legal_entities(entity_id) ON DELETE RESTRICT,
    account_id UUID NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    mapped_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active',
    UNIQUE(entity_id, account_id)
);

-- Compliance Reports Table
CREATE TABLE IF NOT EXISTS compliance_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    total_entities INTEGER NOT NULL,
    active_entities INTEGER NOT NULL,
    compliance_score DECIMAL(3,2) CHECK (compliance_score >= 0 AND compliance_score <= 1),
    independence_metrics JSONB NOT NULL,
    trading_patterns JSONB NOT NULL,
    audit_summary JSONB NOT NULL,
    regulatory_compliance JSONB NOT NULL,
    recommendations TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_entity_audit_entity ON entity_audit_logs(entity_id);
CREATE INDEX idx_entity_audit_timestamp ON entity_audit_logs(created_at);
CREATE INDEX idx_entity_audit_correlation ON entity_audit_logs(correlation_id);
CREATE INDEX idx_entity_audit_action ON entity_audit_logs(action_type);

CREATE INDEX idx_decision_entity ON decision_logs(entity_id);
CREATE INDEX idx_decision_timestamp ON decision_logs(timestamp);
CREATE INDEX idx_decision_type ON decision_logs(decision_type);

CREATE INDEX idx_tos_entity ON tos_acceptances(entity_id);
CREATE INDEX idx_tos_version ON tos_acceptances(version);
CREATE INDEX idx_tos_date ON tos_acceptances(accepted_date);

CREATE INDEX idx_entity_status ON legal_entities(status);
CREATE INDEX idx_entity_jurisdiction ON legal_entities(jurisdiction);
CREATE INDEX idx_entity_created ON legal_entities(created_at);

CREATE INDEX idx_mapping_entity ON entity_account_mappings(entity_id);
CREATE INDEX idx_mapping_account ON entity_account_mappings(account_id);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_legal_entities_updated_at 
    BEFORE UPDATE ON legal_entities 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_geographic_restrictions_updated_at 
    BEFORE UPDATE ON geographic_restrictions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to verify audit log integrity
CREATE OR REPLACE FUNCTION verify_audit_log_integrity(
    p_entity_id UUID,
    p_start_date TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_end_date TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS TABLE(
    is_valid BOOLEAN,
    total_logs INTEGER,
    first_break_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
) AS $$
DECLARE
    v_log_count INTEGER := 0;
    v_previous_hash VARCHAR(256);
    v_current_log RECORD;
    v_is_valid BOOLEAN := TRUE;
    v_first_break TIMESTAMP WITH TIME ZONE := NULL;
    v_error_msg TEXT := NULL;
BEGIN
    -- Get logs for the entity
    FOR v_current_log IN
        SELECT log_id, signature, previous_hash, created_at
        FROM entity_audit_logs
        WHERE entity_id = p_entity_id
            AND (p_start_date IS NULL OR created_at >= p_start_date)
            AND (p_end_date IS NULL OR created_at <= p_end_date)
        ORDER BY created_at ASC
    LOOP
        v_log_count := v_log_count + 1;
        
        -- Check hash chain
        IF v_log_count = 1 THEN
            IF v_current_log.previous_hash != 'genesis_block' THEN
                v_is_valid := FALSE;
                v_first_break := v_current_log.created_at;
                v_error_msg := 'First log does not reference genesis block';
                EXIT;
            END IF;
        ELSIF v_current_log.previous_hash != v_previous_hash THEN
            v_is_valid := FALSE;
            v_first_break := v_current_log.created_at;
            v_error_msg := 'Hash chain broken';
            EXIT;
        END IF;
        
        v_previous_hash := v_current_log.signature;
    END LOOP;
    
    RETURN QUERY SELECT v_is_valid, v_log_count, v_first_break, v_error_msg;
END;
$$ LANGUAGE plpgsql;

-- Create function to calculate entity independence score
CREATE OR REPLACE FUNCTION calculate_independence_score(
    p_entity_id UUID,
    p_days INTEGER DEFAULT 7
)
RETURNS DECIMAL AS $$
DECLARE
    v_decision_count INTEGER;
    v_unique_seeds INTEGER;
    v_timing_variance DECIMAL;
    v_independence_score DECIMAL;
BEGIN
    -- Count total decisions
    SELECT COUNT(*) INTO v_decision_count
    FROM decision_logs
    WHERE entity_id = p_entity_id
        AND timestamp > NOW() - INTERVAL '1 day' * p_days;
    
    IF v_decision_count < 2 THEN
        RETURN 1.0;
    END IF;
    
    -- Count unique decision seeds
    SELECT COUNT(DISTINCT independent_factors->>'unique_seed') INTO v_unique_seeds
    FROM decision_logs
    WHERE entity_id = p_entity_id
        AND timestamp > NOW() - INTERVAL '1 day' * p_days;
    
    -- Calculate timing variance (simplified)
    SELECT STDDEV(EXTRACT(EPOCH FROM (timestamp - LAG(timestamp) OVER (ORDER BY timestamp))))
    INTO v_timing_variance
    FROM decision_logs
    WHERE entity_id = p_entity_id
        AND timestamp > NOW() - INTERVAL '1 day' * p_days;
    
    -- Calculate independence score
    v_independence_score := (
        (v_unique_seeds::DECIMAL / v_decision_count) * 0.5 +
        LEAST(1.0, COALESCE(v_timing_variance, 0) / 100) * 0.5
    );
    
    RETURN LEAST(1.0, GREATEST(0.0, v_independence_score));
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE legal_entities IS 'Stores legal entity information for regulatory compliance';
COMMENT ON TABLE entity_audit_logs IS 'Immutable audit trail with cryptographic integrity';
COMMENT ON TABLE decision_logs IS 'Tracks independent decision-making for entity separation';
COMMENT ON TABLE geographic_restrictions IS 'Jurisdiction-based trading restrictions';
COMMENT ON TABLE tos_acceptances IS 'Terms of Service acceptance tracking';
COMMENT ON TABLE entity_account_mappings IS 'Maps trading accounts to legal entities';
COMMENT ON TABLE compliance_reports IS 'Stored compliance report snapshots';

-- Grant permissions (adjust as needed)
GRANT ALL ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO trading_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trading_user;