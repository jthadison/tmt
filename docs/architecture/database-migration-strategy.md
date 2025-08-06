# Database Migration Strategy

## Overview

This document defines the database migration strategy for the Adaptive Trading System, ensuring safe schema evolution, rollback capabilities, and zero-downtime deployments for both PostgreSQL and TimescaleDB components.

## Migration Framework

**Tool:** Custom Python migration system using SQLAlchemy and psycopg2  
**Location:** `shared/schemas/migrations/`  
**Versioning:** Sequential integer-based versioning (001, 002, 003...)

## Migration Structure

```
shared/schemas/migrations/
├── migration_runner.py          # Migration execution framework
├── rollback_runner.py          # Rollback execution framework
├── versions/
│   ├── 001_initial_schema.sql  # Base schema creation
│   ├── 002_add_timescaledb.sql # TimescaleDB hypertables
│   ├── 003_add_indexes.sql     # Performance indexes
│   └── rollback/
│       ├── 001_rollback.sql    # Rollback for version 001
│       ├── 002_rollback.sql    # Rollback for version 002
│       └── 003_rollback.sql    # Rollback for version 003
└── seeds/
    ├── personality_profiles.sql # Default personality profiles
    └── test_data.sql           # Development test data
```

## Migration Execution Process

### Forward Migration
1. **Pre-Migration Checks**
   - Verify database connectivity
   - Check current schema version in `migration_history` table
   - Validate migration file integrity
   - Ensure sufficient database space

2. **Migration Execution**
   - Begin transaction (where possible)
   - Execute migration SQL
   - Update `migration_history` table
   - Commit transaction
   - Log migration completion

3. **Post-Migration Validation**
   - Verify schema changes applied correctly
   - Run data integrity checks
   - Execute migration-specific tests

### Rollback Process
1. **Pre-Rollback Checks**
   - Verify rollback script exists
   - Check dependencies (no later migrations depend on this version)
   - Backup current state

2. **Rollback Execution**
   - Begin transaction
   - Execute rollback SQL
   - Update `migration_history` table
   - Commit transaction

3. **Post-Rollback Validation**
   - Verify rollback completed successfully
   - Run integrity checks
   - Update application configuration if needed

## Migration Categories

### Safe Migrations (Zero Downtime)
- Adding new tables
- Adding new columns with defaults
- Adding indexes (CONCURRENTLY in PostgreSQL)
- Adding constraints on new columns

### Unsafe Migrations (Require Maintenance Window)
- Dropping columns or tables
- Changing column types
- Adding NOT NULL constraints to existing columns
- Large data migrations

## Migration History Table

```sql
CREATE TABLE migration_history (
    version INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rollback_available BOOLEAN NOT NULL DEFAULT true,
    checksum VARCHAR(64) NOT NULL, -- SHA256 of migration file
    execution_time_ms INTEGER NOT NULL,
    applied_by VARCHAR(100) DEFAULT CURRENT_USER
);
```

## Rollback Strategies

### Application-Level Rollback
- **Trigger:** Application deployment issues
- **Action:** Rollback application code, keep database schema
- **Timeline:** < 60 seconds

### Schema-Level Rollback
- **Trigger:** Migration breaks database functionality
- **Action:** Execute rollback SQL scripts
- **Timeline:** < 5 minutes
- **Requirements:** Rollback script must exist and be tested

### Point-in-Time Recovery
- **Trigger:** Critical data corruption
- **Action:** Restore from backup to specific timestamp
- **Timeline:** 15-30 minutes
- **Requirements:** Regular database backups

## TimescaleDB Specific Considerations

### Hypertable Migrations
```sql
-- Safe: Adding columns to hypertables
ALTER TABLE market_data ADD COLUMN new_column DECIMAL(10,5);

-- Unsafe: Modifying partition key requires recreation
-- Must use CREATE TABLE AS SELECT approach
```

### Chunk Management
- Migrations affecting hypertables may require chunk-by-chunk processing
- Use `timescaledb-parallel-copy` for large data migrations
- Consider compression settings for historical chunks

## Environment-Specific Migration Rules

### Development Environment
- Full forward and rollback testing required
- Seed data automatically loaded
- Migration performance not critical

### Staging Environment
- Production-like data volume testing
- Migration timing validation
- Full rollback testing required

### Production Environment
- Maintenance window coordination required for unsafe migrations
- Blue-green deployment for application changes
- Real-time monitoring during migration execution
- Automatic rollback triggers on error

## Migration Testing Requirements

### Unit Tests
```python
def test_migration_001_forward():
    # Test forward migration
    pass

def test_migration_001_rollback():
    # Test rollback functionality
    pass
```

### Integration Tests
- Full database setup with migration execution
- Seed data loading validation
- Application connectivity after migration

### Performance Tests
- Migration execution timing on production-sized datasets
- Index creation performance
- Memory usage validation

## Monitoring and Alerting

### Migration Metrics
- Migration execution time
- Rollback frequency
- Migration failure rate
- Database downtime during migrations

### Alert Conditions
- Migration execution time > 10 minutes
- Migration failure
- Rollback execution
- Post-migration integrity check failures

## Emergency Procedures

### Failed Migration Recovery
1. Immediately execute rollback if available
2. Restore from backup if rollback unavailable
3. Notify development team and stakeholders
4. Post-mortem analysis and rollback script creation

### Data Corruption Detection
1. Halt all trading operations immediately
2. Activate Circuit Breaker Agent system-wide stop
3. Assess corruption scope and impact
4. Execute point-in-time recovery to last known good state

## Deployment Integration

### CI/CD Pipeline Integration
```yaml
# GitHub Actions workflow step
- name: Run Database Migrations
  run: |
    python shared/schemas/migrations/migration_runner.py --target=latest
    python shared/schemas/migrations/validate_schema.py
```

### Rolling Deployment Support
- Schema changes must be backward compatible during deployment
- Use feature flags for breaking schema changes
- Coordinate with application deployment timeline

## Backup and Recovery Integration

### Pre-Migration Backups
- Automatic backup before any migration execution
- Backup retention: 7 days for development, 30 days for production
- Backup validation: restore test on staging environment

### Recovery Testing
- Monthly recovery drill from backups
- Rollback script testing in staging
- Migration replay testing from clean database

This migration strategy ensures safe database evolution while maintaining the high availability requirements of the trading system.