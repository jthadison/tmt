# Troubleshooting Guide

## Overview

This guide provides step-by-step troubleshooting procedures for common issues encountered with the TMT trading system.

## Common System Issues

### Trading System Not Responding

#### Symptoms
- Dashboard shows connection errors
- API endpoints not responding
- Agents appear offline in monitoring

#### Troubleshooting Steps
1. **Check System Status**
   ```bash
   # Check if main services are running
   systemctl status tmt-agents
   systemctl status tmt-execution-engine
   systemctl status postgresql
   systemctl status redis
   ```

2. **Verify Network Connectivity**
   ```bash
   # Test internal connectivity
   curl -f http://localhost:8001/health  # Circuit Breaker Agent
   curl -f http://localhost:8002/health  # Market Analysis Agent
   
   # Test database connectivity
   psql -h localhost -U tmt_user -d tmt_production -c "SELECT 1;"
   ```

3. **Check Resource Usage**
   ```bash
   # Monitor system resources
   top -p $(pgrep -f "tmt")
   df -h
   free -m
   ```

4. **Review Error Logs**
   ```bash
   # Check system logs
   tail -f /var/log/tmt/system.log
   tail -f /var/log/tmt/errors.log
   journalctl -u tmt-agents -f
   ```

### High Execution Latency

#### Symptoms
- Trades executing slower than 100ms
- Latency alerts in monitoring
- Slippage higher than normal

#### Troubleshooting Steps
1. **Check Network Latency**
   ```bash
   # Test broker connectivity
   ping api-fxtrade.oanda.com
   curl -w "%{time_total}" -s -o /dev/null https://api-fxtrade.oanda.com/v3/accounts
   ```

2. **Monitor System Performance**
   ```bash
   # Check CPU and memory usage
   iostat 1 5
   vmstat 1 5
   ```

3. **Database Performance**
   ```bash
   # Check for slow queries
   psql -d tmt_production -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
   ```

### Database Connection Issues

#### Symptoms
- Connection timeouts
- "Too many connections" errors
- Data not updating

#### Troubleshooting Steps
1. **Check Connection Pool**
   ```bash
   # Monitor active connections
   psql -d tmt_production -c "SELECT count(*) FROM pg_stat_activity;"
   
   # Check connection limits
   psql -d tmt_production -c "SHOW max_connections;"
   ```

2. **Restart Connection Pool**
   ```bash
   # Restart applications to reset connections
   systemctl restart tmt-agents
   systemctl restart tmt-execution-engine
   ```

## Agent-Specific Issues

### Circuit Breaker Agent Problems

#### Agent Not Starting
```bash
# Check agent logs
tail -f /var/log/tmt/agents/circuit-breaker.log

# Verify configuration
cat /etc/tmt/agents/circuit-breaker.conf

# Test agent startup manually
cd /opt/tmt/agents/circuit-breaker
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

#### Emergency Stop Not Working
```bash
# Manual emergency stop
curl -X POST http://localhost:8001/api/v1/emergency-stop \
  -H "Content-Type: application/json" \
  -d '{"reason": "manual_intervention", "triggered_by": "operator"}'

# Verify emergency stop status
curl -f http://localhost:8001/api/v1/emergency-status
```

### Risk Management Agent Issues

#### Risk Calculations Incorrect
```bash
# Check risk parameter configuration
curl -f http://localhost:8003/api/v1/risk-parameters

# Verify account balances
curl -f http://localhost:8003/api/v1/account-balances

# Review risk calculation logs
grep "risk_calculation" /var/log/tmt/agents/risk-management.log
```

## Trading Platform Issues

### MetaTrader Connection Problems

#### Connection Timeouts
```bash
# Check MT4/MT5 connectivity
telnet your-broker-server.com 443

# Verify credentials
curl -X POST https://your-broker-api.com/auth \
  -H "Content-Type: application/json" \
  -d '{"username": "your_user", "password": "your_pass"}'
```

#### Order Execution Failures
```bash
# Check order logs
grep "order_execution" /var/log/tmt/platforms/metatrader.log

# Verify account permissions
./scripts/verify-trading-permissions.sh

# Test manual order placement
./scripts/test-order-execution.sh
```

### Market Data Issues

#### Missing Price Data
```bash
# Check data feed connectivity
curl -f https://api-fxtrade.oanda.com/v3/instruments/EUR_USD/candles

# Verify data storage
psql -d tmt_production -c "SELECT COUNT(*) FROM market_data WHERE timestamp > NOW() - INTERVAL '1 hour';"

# Restart data collection
systemctl restart tmt-market-data-collector
```

## Performance Issues

### Memory Leaks

#### Symptoms
- Gradually increasing memory usage
- System becoming unresponsive
- Out of memory errors

#### Resolution Steps
```bash
# Monitor memory usage by process
ps aux --sort=-%mem | head -20

# Check for memory leaks in agents
valgrind --tool=memcheck python -m uvicorn main:app

# Restart affected services
systemctl restart tmt-agents
```

### CPU Overload

#### Symptoms
- High CPU usage (>80%)
- System sluggishness
- Delayed responses

#### Resolution Steps
```bash
# Identify CPU-intensive processes
top -o %CPU

# Check for infinite loops or stuck processes
strace -p [PID]

# Scale down non-critical processes
systemctl stop tmt-analytics
systemctl stop tmt-reporting
```

## Security Issues

### Suspicious Trading Activity

#### Detection
```bash
# Check for unusual trading patterns
psql -d tmt_production -c "
SELECT account_id, COUNT(*), AVG(position_size) 
FROM trades 
WHERE timestamp > NOW() - INTERVAL '1 hour' 
GROUP BY account_id 
HAVING COUNT(*) > 20;"
```

#### Response Actions
```bash
# Immediate trading halt
curl -X POST http://localhost:8001/api/v1/emergency-stop \
  -d '{"reason": "suspicious_activity"}'

# Generate incident report
./scripts/generate-security-incident-report.sh

# Notify security team
./scripts/notify-security-team.sh
```

### API Key Compromise

#### Immediate Actions
```bash
# Rotate compromised keys
./scripts/rotate-api-keys.sh

# Check for unauthorized access
grep "authentication_failure" /var/log/tmt/security.log

# Update all services with new keys
./scripts/update-service-credentials.sh
```

## Data Issues

### Data Corruption

#### Detection
```bash
# Check data integrity
psql -d tmt_production -c "SELECT * FROM data_integrity_checks WHERE status = 'FAILED';"

# Verify backup integrity
./scripts/verify-backup-integrity.sh
```

#### Recovery
```bash
# Restore from backup
./scripts/restore-from-backup.sh [backup_timestamp]

# Validate restored data
./scripts/validate-data-restoration.sh
```

### Missing Transaction Records

#### Investigation
```bash
# Check transaction logs
grep "transaction_id" /var/log/tmt/transactions.log

# Compare with broker records
./scripts/reconcile-broker-transactions.sh

# Generate discrepancy report
./scripts/generate-transaction-discrepancy-report.sh
```

## Escalation Procedures

### When to Escalate

#### Immediate Escalation (Call within 5 minutes)
- Complete system failure
- Potential financial loss >$1,000
- Security breach suspected
- Regulatory compliance issue

#### Standard Escalation (Email within 30 minutes)
- Performance degradation >50%
- Single agent failure
- Data synchronization issues
- Non-critical system errors

### Escalation Contacts
```yaml
escalation_contacts:
  level_1:
    role: "On-call Engineer"
    phone: "+1-555-0100"
    email: "oncall@tmt-trading.com"
    
  level_2:
    role: "System Administrator"
    phone: "+1-555-0101"
    email: "sysadmin@tmt-trading.com"
    
  level_3:
    role: "CTO"
    phone: "+1-555-0102"
    email: "cto@tmt-trading.com"
```

## Recovery Procedures

### System Recovery Checklist
```bash
# 1. Stop all trading activity
curl -X POST http://localhost:8001/api/v1/trading-halt

# 2. Backup current state
./scripts/emergency-backup.sh

# 3. Identify root cause
./scripts/diagnose-system-issue.sh

# 4. Apply fix
./scripts/apply-fix.sh [issue_type]

# 5. Validate system health
./scripts/system-health-check.sh

# 6. Gradually resume operations
./scripts/gradual-resume-trading.sh
```

### Post-Issue Documentation
Always document:
1. Issue description and symptoms
2. Root cause analysis
3. Resolution steps taken
4. Prevention measures implemented
5. Lessons learned

For detailed system recovery procedures, see [Disaster Recovery](../manual/disaster-recovery.md).