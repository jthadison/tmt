# Trading System Configuration Management

This directory contains version-controlled trading system parameter configurations with full audit trails and rollback capabilities.

## Directory Structure

```
config/
├── parameters/
│   ├── schema.json                      # JSON Schema for validation
│   ├── session_targeted_v1.0.0.yaml    # Version 1.0.0 configuration
│   ├── session_targeted_v2.0.0.yaml    # Version 2.0.0 configuration (example)
│   └── active.yaml -> session_targeted_v1.0.0.yaml  # Symlink to active config
└── README.md                            # This file
```

## Configuration File Format

All configuration files must:
1. Follow the JSON Schema defined in `parameters/schema.json`
2. Use semantic versioning (vX.Y.Z)
3. Include author, reason, and validation metrics
4. Pass pre-commit validation hooks

### YAML Structure

```yaml
version: "1.0.0"                    # Semantic version (required)
effective_date: "2025-10-09"        # When config becomes active (required)
author: "System Administrator"       # Who made the change (required)
reason: "Description of change"      # Why the change was made (required)

validation:                          # Validation metrics (recommended)
  backtest_sharpe: 1.45
  out_of_sample_sharpe: 1.32
  overfitting_score: 0.091
  max_drawdown: 0.08
  approved_by: "QA Engineer"
  approved_date: "2025-10-09"

baseline:                            # Universal baseline parameters (required)
  confidence_threshold: 55.0         # 0-100%
  min_risk_reward: 1.8              # > 0
  max_risk_reward: 5.0
  source: "universal_cycle_4"

session_parameters:                  # Session-specific overrides (required)
  tokyo:
    confidence_threshold: 85.0
    min_risk_reward: 4.0
    max_risk_reward: 6.0
    volatility_adjustment: 0.20
    justification: "Tokyo shows high precision"
    deviation_from_baseline:
      confidence: +30.0
      risk_reward: +2.2

  london:
    # ... similar structure

  new_york:
    # ... similar structure

constraints:                         # Safety constraints (required)
  max_confidence_deviation: 35.0     # Max % deviation from baseline
  max_risk_reward_deviation: 2.5     # Max absolute deviation
  max_overfitting_score: 0.3         # Max acceptable overfitting
  min_backtest_sharpe: 1.2
  min_out_of_sample_ratio: 0.7

alerts:                              # Alert thresholds (optional)
  overfitting_warning: 0.3
  overfitting_critical: 0.5
```

## Version Control Workflow

### 1. Creating a New Configuration

```bash
# Create a new configuration file
cp config/parameters/session_targeted_v1.0.0.yaml \
   config/parameters/session_targeted_v1.1.0.yaml

# Edit the new configuration
# - Update version number
# - Update effective_date
# - Update author and reason
# - Modify parameters as needed

# Validate the configuration
python -m agents.config_manager.validator \
  config/parameters/session_targeted_v1.1.0.yaml

# Commit the new configuration
git add config/parameters/session_targeted_v1.1.0.yaml
git commit -m "feat: config v1.1.0 - Updated Tokyo session parameters

- Increased Tokyo confidence threshold from 85% to 87%
- Reason: Walk-forward optimization results Q4 2025
- Backtest Sharpe: 1.52
- Out-of-sample Sharpe: 1.41
- Overfitting score: 0.125

Approved-by: Quinn (QA Architect)"
```

### 2. Activating a Configuration

```bash
# Update the active symlink
python -m agents.config_manager.cli activate v1.1.0

# This will:
# - Validate the new configuration
# - Update the active.yaml symlink
# - Create a Git commit
# - Send Slack notification
# - Trigger system reload
```

### 3. Rolling Back a Configuration

```bash
# Emergency rollback to previous version
python -m agents.config_manager.cli rollback

# Rollback to specific version
python -m agents.config_manager.cli rollback --version v1.0.0

# This preserves audit trail (creates new commit, doesn't rewrite history)
```

## Validation Rules

All configurations must pass:

1. **Schema Validation**: Matches `schema.json`
2. **Value Ranges**:
   - confidence_threshold: 0-100
   - min_risk_reward: > 0
   - max_risk_reward > min_risk_reward
3. **Cross-Field Validation**:
   - Deviations within constraints
   - Out-of-sample ratio meets minimum
4. **Overfitting Check**: Score < max_overfitting_score

## Approval Requirements

| Change Type | Approval Required |
|-------------|------------------|
| Automated (walk-forward) | Validation metrics only |
| Manual minor (<15% deviation) | 1 reviewer |
| Manual major (>15% deviation) | 2 reviewers (CODEOWNERS) |
| Emergency rollback | Post-incident review |

## Pre-commit Hooks

All configuration changes are automatically validated:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-config
      name: Validate Trading Parameters
      entry: python -m agents.config_manager.validator
      files: ^config/parameters/.*\.yaml$
```

## API Endpoints

The configuration manager provides REST API access with authentication.

### Authentication

All API endpoints require authentication via API key:

```bash
# Set API key in environment (recommended)
export CONFIG_MANAGER_API_KEYS_RW="your-read-write-key"
export CONFIG_MANAGER_API_KEYS_RO="your-read-only-key"
export CONFIG_MANAGER_MASTER_KEY="your-master-key"

# Or generate a new API key
curl -X POST http://localhost:8090/api/auth/generate-key \
  -H "X-API-Key: $CONFIG_MANAGER_MASTER_KEY"
```

**API Key Types:**
- **Read-Write Keys** (`CONFIG_MANAGER_API_KEYS_RW`): Full access to all endpoints
- **Read-Only Keys** (`CONFIG_MANAGER_API_KEYS_RO`): Can only GET, cannot modify
- **Master Key** (`CONFIG_MANAGER_MASTER_KEY`): Admin access, can generate new keys

**Multiple Keys**: Comma-separated for multiple keys:
```bash
export CONFIG_MANAGER_API_KEYS_RW="key1,key2,key3"
```

### API Calls

All requests must include `X-API-Key` header:

```bash
# Get current configuration
curl -H "X-API-Key: $CONFIG_MANAGER_API_KEYS_RO" \
  http://localhost:8090/api/config/current

# Get configuration history
curl -H "X-API-Key: $CONFIG_MANAGER_API_KEYS_RO" \
  http://localhost:8090/api/config/history?limit=20

# Get specific version
curl -H "X-API-Key: $CONFIG_MANAGER_API_KEYS_RO" \
  http://localhost:8090/api/config/version/1.0.0

# Activate configuration (requires write key)
curl -X POST http://localhost:8090/api/config/activate \
  -H "X-API-Key: $CONFIG_MANAGER_API_KEYS_RW" \
  -H "Content-Type: application/json" \
  -d '{"version": "1.1.0", "reason": "Deployment"}'

# Rollback configuration (requires write key)
curl -X POST http://localhost:8090/api/config/rollback \
  -H "X-API-Key: $CONFIG_MANAGER_API_KEYS_RW" \
  -H "Content-Type: application/json" \
  -d '{"version": "1.0.0", "reason": "Emergency rollback", "emergency": true}'
```

## Monitoring and Alerts

Configuration changes trigger:

1. **Slack Notification**:
   - Version, author, reason
   - Validation metrics summary
   - Deviations from baseline

2. **Dashboard Update**:
   - Configuration history graph
   - Active version indicator
   - Validation metrics timeline

3. **Audit Log**:
   - All changes logged to database
   - 7-year retention
   - Tamper-evident (Git-based)

## Emergency Procedures

### Emergency Rollback

```bash
# One-command rollback to last known good
python scripts/emergency_rollback.py

# This will:
# 1. Stop all trading
# 2. Rollback to previous config
# 3. Alert all stakeholders
# 4. Create incident ticket
```

### Configuration Freeze

```bash
# Prevent all configuration changes
python -m agents.config_manager.cli freeze

# Resume configuration changes
python -m agents.config_manager.cli unfreeze
```

## Best Practices

1. **Always validate** before committing
2. **Include validation metrics** for all changes
3. **Write clear commit messages** with rationale
4. **Test in staging** before production
5. **Monitor after deployment** for 24 hours
6. **Document deviations** from baseline
7. **Regular rollback drills** (quarterly)

## Troubleshooting

### Validation Failures

```bash
# Check what failed
python -m agents.config_manager.validator config/parameters/new_config.yaml --verbose

# Common issues:
# - Schema mismatch: Check required fields
# - Range violation: Check min/max values
# - Deviation too large: Reduce changes or update constraints
```

### Symlink Issues

```bash
# Verify active configuration
ls -la config/parameters/active.yaml

# Recreate symlink
rm config/parameters/active.yaml
ln -s session_targeted_v1.0.0.yaml config/parameters/active.yaml
```

### Git Conflicts

```bash
# Never force-push configuration changes
# Always merge conflicts manually
# Validate after merge
```

## References

- [Story 11.6 Specification](../../docs/stories/epic-11/11.6.configuration-version-control-system.md)
- [Walk-Forward Optimization](../../docs/stories/epic-11/11.3.walk-forward-optimization-system.md)
- [Overfitting Monitor](../../docs/stories/epic-11/11.4.real-time-overfitting-monitor.md)
