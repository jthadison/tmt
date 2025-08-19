# System Startup and Shutdown Procedures

## Overview

This document provides detailed procedures for starting up and shutting down the TMT trading system safely. These procedures ensure system integrity, data consistency, and minimal service disruption.

## Prerequisites

### Required Access
- Administrative access to all system components
- Database administrator credentials
- Trading platform API credentials
- Monitoring system access

### Pre-flight Checklist
- [ ] All team members notified of startup/shutdown
- [ ] Market hours confirmed (avoid startup during active trading)
- [ ] Backup systems verified as operational
- [ ] Network connectivity confirmed
- [ ] External dependencies verified (exchanges, data providers)

## System Startup Procedures

### Phase 1: Infrastructure Startup

#### 1.1 Database Services
```bash
# Start PostgreSQL cluster
sudo systemctl start postgresql
sudo systemctl status postgresql

# Start TimescaleDB
sudo systemctl start timescaledb
sudo systemctl status timescaledb

# Start Redis cluster
sudo systemctl start redis
sudo systemctl status redis

# Verify database connectivity
psql -h localhost -U tmt_user -d tmt_production -c "SELECT version();"
redis-cli ping
```

#### 1.2 Message Broker
```bash
# Start Kafka cluster
sudo systemctl start kafka
sudo systemctl status kafka

# Verify Kafka topics
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check topic health
kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic trading-signals
```

#### 1.3 Monitoring Services
```bash
# Start Prometheus
sudo systemctl start prometheus
sudo systemctl status prometheus

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl status grafana-server

# Verify monitoring endpoints
curl -f http://localhost:9090/-/healthy
curl -f http://localhost:3000/api/health
```

### Phase 2: Core System Startup

#### 2.1 Execution Engine (Rust/Go)
```bash
# Navigate to execution engine directory
cd /opt/tmt/execution-engine

# Start execution engine with production config
./target/release/execution-engine --config production.toml

# Verify execution engine health
curl -f http://localhost:8004/health

# Check platform connections
curl -f http://localhost:8004/api/v1/platform-status
```

#### 2.2 Agent Services (Python/FastAPI)
```bash
# Start Circuit Breaker Agent (must be first)
cd /opt/tmt/agents/circuit-breaker
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1

# Verify Circuit Breaker Agent
curl -f http://localhost:8001/health

# Start Market Analysis Agent
cd /opt/tmt/agents/market-analysis
python -m uvicorn main:app --host 0.0.0.0 --port 8002 --workers 2

# Start Risk Management Agent
cd /opt/tmt/agents/risk-management
python -m uvicorn main:app --host 0.0.0.0 --port 8003 --workers 1

# Start remaining agents in order
cd /opt/tmt/agents/anti-correlation
python -m uvicorn main:app --host 0.0.0.0 --port 8004 --workers 1

cd /opt/tmt/agents/personality-engine
python -m uvicorn main:app --host 0.0.0.0 --port 8005 --workers 1

cd /opt/tmt/agents/performance-tracker
python -m uvicorn main:app --host 0.0.0.0 --port 8006 --workers 1

cd /opt/tmt/agents/compliance
python -m uvicorn main:app --host 0.0.0.0 --port 8007 --workers 1

cd /opt/tmt/agents/learning-safety
python -m uvicorn main:app --host 0.0.0.0 --port 8008 --workers 1
```

#### 2.3 Agent Health Verification
```bash
# Check all agent health endpoints
for port in {8001..8008}; do
    echo "Checking agent on port $port"
    curl -f http://localhost:$port/health || echo "FAILED: Port $port"
done

# Verify inter-agent communication
curl -f http://localhost:8001/api/v1/agent-status
```

### Phase 3: Dashboard and UI

#### 3.1 Dashboard Frontend
```bash
# Start Next.js dashboard
cd /opt/tmt/dashboard
npm run start:production

# Verify dashboard accessibility
curl -f http://localhost:3000/api/health
```

#### 3.2 API Gateway
```bash
# Start API Gateway
cd /opt/tmt/api-gateway
./api-gateway --config production.yaml

# Verify gateway health
curl -f http://localhost:8000/health
```

### Phase 4: External Integrations

#### 4.1 Trading Platform Connections
```bash
# Test MetaTrader connections
curl -X POST http://localhost:8004/api/v1/test-connection \
  -H "Content-Type: application/json" \
  -d '{"platform": "metatrader", "account_id": "test_account"}'

# Test TradeLocker connections
curl -X POST http://localhost:8004/api/v1/test-connection \
  -H "Content-Type: application/json" \
  -d '{"platform": "tradelocker", "account_id": "test_account"}'
```

#### 4.2 Market Data Connections
```bash
# Test market data feeds
curl -X POST http://localhost:8002/api/v1/test-market-data \
  -H "Content-Type: application/json" \
  -d '{"provider": "oanda", "instruments": ["EUR_USD", "GBP_USD"]}'
```

### Phase 5: System Validation

#### 5.1 End-to-End Testing
```bash
# Run system health check script
cd /opt/tmt/scripts
./system-health-check.sh

# Run integration tests
python -m pytest tests/integration/ -v --tb=short
```

#### 5.2 Trading Readiness Check
```bash
# Verify all accounts are accessible
curl -f http://localhost:8003/api/v1/account-status

# Check risk parameters are loaded
curl -f http://localhost:8003/api/v1/risk-parameters

# Verify compliance rules are active
curl -f http://localhost:8007/api/v1/compliance-status
```

### Startup Completion Checklist
- [ ] All infrastructure services operational
- [ ] All 8 agents healthy and communicating
- [ ] Execution engine connected to trading platforms
- [ ] Dashboard accessible and displaying data
- [ ] Market data feeds active
- [ ] Risk parameters loaded and validated
- [ ] Compliance rules active
- [ ] End-to-end test passed
- [ ] All monitoring alerts cleared
- [ ] Trading accounts accessible

## System Shutdown Procedures

### Phase 1: Trading Halt

#### 1.1 Initiate Trading Stop
```bash
# Trigger graceful trading halt via Circuit Breaker Agent
curl -X POST http://localhost:8001/api/v1/trading-halt \
  -H "Content-Type: application/json" \
  -d '{"reason": "scheduled_shutdown", "grace_period": 300}'

# Monitor active positions
curl -f http://localhost:8003/api/v1/active-positions
```

#### 1.2 Position Management
```bash
# Wait for all pending orders to complete or timeout
# Monitor execution queue
curl -f http://localhost:8004/api/v1/execution-queue

# Verify no trades are in progress
curl -f http://localhost:8004/api/v1/active-executions
```

### Phase 2: Agent Shutdown

#### 2.1 Graceful Agent Shutdown
```bash
# Signal shutdown to all agents (they will complete current operations)
curl -X POST http://localhost:8001/api/v1/system-shutdown \
  -H "Content-Type: application/json" \
  -d '{"shutdown_type": "graceful", "timeout": 120}'

# Monitor agent shutdown status
for port in {8001..8008}; do
    curl -f http://localhost:$port/shutdown-status 2>/dev/null || echo "Agent $port shutdown"
done
```

#### 2.2 Force Shutdown (if graceful fails)
```bash
# Force terminate agent processes
pkill -f "uvicorn.*main:app"

# Verify all agent processes stopped
ps aux | grep uvicorn
```

### Phase 3: Core System Shutdown

#### 3.1 Execution Engine Shutdown
```bash
# Signal graceful shutdown to execution engine
curl -X POST http://localhost:8004/api/v1/shutdown

# Wait for graceful shutdown or force kill
sleep 30
pkill -f execution-engine
```

#### 3.2 Dashboard Shutdown
```bash
# Stop dashboard
pkill -f "npm.*start"
pkill -f "next.*start"
```

### Phase 4: Infrastructure Shutdown

#### 4.1 Database Services
```bash
# Stop application connections first
# Then shutdown databases
sudo systemctl stop redis
sudo systemctl stop timescaledb
sudo systemctl stop postgresql

# Verify services stopped
sudo systemctl status postgresql timescaledb redis
```

#### 4.2 Message Broker
```bash
# Stop Kafka
sudo systemctl stop kafka

# Verify Kafka stopped
sudo systemctl status kafka
```

#### 4.3 Monitoring Services
```bash
# Stop monitoring (last to capture shutdown metrics)
sudo systemctl stop grafana-server
sudo systemctl stop prometheus

# Verify monitoring stopped
sudo systemctl status prometheus grafana-server
```

### Shutdown Completion Checklist
- [ ] All trading activity halted
- [ ] All pending orders completed or cancelled
- [ ] All agent processes stopped gracefully
- [ ] Execution engine shutdown cleanly
- [ ] Dashboard and API gateway stopped
- [ ] Database connections closed properly
- [ ] All infrastructure services stopped
- [ ] No orphaned processes remaining
- [ ] Shutdown logged and documented

## Emergency Procedures

### Emergency Shutdown
```bash
# Immediate emergency stop (bypasses graceful shutdown)
curl -X POST http://localhost:8001/api/v1/emergency-stop \
  -H "Content-Type: application/json" \
  -d '{"reason": "emergency", "triggered_by": "operator"}'

# Force kill all TMT processes
pkill -f tmt
pkill -f execution-engine
pkill -f uvicorn
```

### Recovery from Failed Startup
1. Check system logs: `journalctl -u tmt-* -f`
2. Verify database integrity: Run database consistency checks
3. Check network connectivity: Verify external service accessibility
4. Review configuration: Validate all configuration files
5. Restart from Phase 1: Follow startup procedure from beginning

## Monitoring and Logging

### Startup Logs
- All startup activities logged to `/var/log/tmt/startup.log`
- Agent startup logs in `/var/log/tmt/agents/`
- Infrastructure logs in `/var/log/tmt/infrastructure/`

### Key Metrics During Startup
- Startup time per component
- Memory usage during initialization
- Database connection establishment time
- External API connection success rate

### Alerts During Startup/Shutdown
- Component startup failures
- Database connection failures
- External service unavailability
- Memory or CPU threshold exceeded
- Unexpected process termination

## Troubleshooting Common Issues

### Database Connection Failures
```bash
# Check database status
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"

# Check network connectivity
telnet localhost 5432

# Verify credentials
psql -h localhost -U tmt_user -d tmt_production -c "\conninfo"
```

### Agent Communication Failures
```bash
# Check Kafka status
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Verify agent network connectivity
curl -f http://localhost:8001/health

# Check agent logs
tail -f /var/log/tmt/agents/circuit-breaker.log
```

### Trading Platform Connection Issues
```bash
# Test platform API connectivity
curl -f https://api-fxtrade.oanda.com/v3/accounts

# Check API credentials
./verify-credentials.sh

# Review platform-specific logs
tail -f /var/log/tmt/platforms/oanda.log
```

For additional troubleshooting procedures, see the [Troubleshooting Guide](../user-guide/troubleshooting.md).