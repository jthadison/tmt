# Trading System Orchestrator

## Overview

The Trading System Orchestrator is the central coordination service that manages the 8 specialized AI agents and coordinates their interactions to execute automated trading strategies on OANDA accounts.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                 Trading System Orchestrator                 │
├─────────────────────────────────────────────────────────────┤
│  Agent Manager  │  Event Router  │  Safety Monitor  │  API  │
├─────────────────────────────────────────────────────────────┤
│           Message Broker (Event Bus)                        │
├─────────────────────────────────────────────────────────────┤
│  Market    │  Strategy │  Param   │  Learning │  Disagree  │
│  Analysis  │  Analysis │  Optim   │  Safety   │  Engine    │
├─────────────────────────────────────────────────────────────┤
│  Data      │  Continuous│  Pattern │  Execution│           │
│  Collection│  Improve   │  Detection│  Engine   │           │
├─────────────────────────────────────────────────────────────┤
│              OANDA API Integration                          │
└─────────────────────────────────────────────────────────────┘
```

### Agent Integration Flow

1. **Market Analysis Agent** → Generates trading signals
2. **Disagreement Engine** → Applies anti-correlation logic
3. **Strategy Analysis** → Validates signal quality
4. **Parameter Optimization** → Calculates position sizing
5. **Learning Safety** → Applies circuit breakers
6. **Execution Engine** → Places trades via OANDA
7. **Data Collection** → Records outcomes
8. **Pattern Detection** → Monitors for detection
9. **Continuous Improvement** → Optimizes performance

## Key Features

### 1. Agent Lifecycle Management
- **Service Discovery**: Automatic agent registration
- **Health Monitoring**: Real-time agent health checks
- **Load Balancing**: Request distribution across agent instances
- **Graceful Shutdown**: Coordinated system shutdown

### 2. Event-Driven Communication
- **Signal Processing**: Trading signal routing and processing
- **State Synchronization**: Agent state coordination
- **Error Propagation**: Error handling and recovery
- **Audit Trail**: Complete event logging

### 3. Safety Systems
- **Circuit Breakers**: Multi-level circuit breaker implementation
- **Emergency Stop**: Immediate trading halt capability
- **Risk Limits**: Real-time risk monitoring and enforcement
- **Manual Override**: Human intervention capabilities

### 4. OANDA Integration
- **Multi-Account Support**: Manage multiple OANDA accounts
- **Real-Time Data**: Live market data streaming
- **Order Management**: Complete order lifecycle management
- **Position Monitoring**: Real-time position tracking

## Configuration

### Environment Variables

```bash
# OANDA Configuration
OANDA_API_KEY=your_api_key
OANDA_ACCOUNT_IDS=account1,account2,account3
OANDA_ENVIRONMENT=practice  # or live
OANDA_BASE_URL=https://api-fxpractice.oanda.com

# Agent Configuration
AGENT_DISCOVERY_PORT=8000
AGENT_HEALTH_CHECK_INTERVAL=30
AGENT_STARTUP_TIMEOUT=60

# Safety Configuration
MAX_CONCURRENT_TRADES=3
RISK_PER_TRADE=0.02
MAX_DAILY_LOSS=0.06
CIRCUIT_BREAKER_THRESHOLD=0.10

# Message Broker
MESSAGE_BROKER_URL=redis://localhost:6379
EVENT_RETENTION_HOURS=24

# Database
DATABASE_URL=postgresql://user:pass@localhost/trading_system
TIMESCALE_URL=postgresql://user:pass@localhost/market_data
```

## API Endpoints

### System Control
- `GET /health` - System health status
- `POST /start` - Start trading system
- `POST /stop` - Stop trading system
- `POST /emergency-stop` - Emergency shutdown

### Agent Management
- `GET /agents` - List registered agents
- `GET /agents/{agent_id}/health` - Agent health status
- `POST /agents/{agent_id}/restart` - Restart specific agent

### Trading Control
- `GET /accounts` - List OANDA accounts
- `GET /accounts/{account_id}/status` - Account status
- `POST /accounts/{account_id}/enable` - Enable trading on account
- `POST /accounts/{account_id}/disable` - Disable trading on account

### Monitoring
- `GET /metrics` - System metrics
- `GET /events` - Recent system events
- `GET /trades` - Recent trades
- `GET /positions` - Current positions

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  orchestrator:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OANDA_API_KEY=${OANDA_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
      - postgres
      - timescaledb

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trading_system
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: market_data
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD}
```

## Safety Features

### Circuit Breakers
- **Account Level**: Per-account loss limits
- **System Level**: Overall system risk limits
- **Time-Based**: Trading hour restrictions
- **Market Condition**: Volatile market detection

### Emergency Protocols
- **Immediate Stop**: All trading halted within 100ms
- **Position Liquidation**: Automatic position closure
- **Alert System**: Instant notifications
- **Audit Logging**: Complete action trail

### Risk Management
- **Real-Time Monitoring**: Continuous risk assessment
- **Dynamic Limits**: Adaptive risk parameters
- **Correlation Control**: Account correlation limits
- **Drawdown Protection**: Drawdown-based restrictions

## Monitoring and Alerting

### Key Metrics
- Trading performance (win rate, profit factor, Sharpe ratio)
- System performance (latency, throughput, uptime)
- Risk metrics (drawdown, exposure, correlation)
- Agent health (response time, error rate, availability)

### Alert Conditions
- Circuit breaker activation
- Agent failures or timeouts
- Risk limit breaches
- Unusual market conditions
- Performance degradation

## Development

### Local Setup

```bash
# Clone and setup
git clone <repo>
cd orchestrator

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Start development server
python -m uvicorn app.main:app --reload --port 8000
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/test_orchestrator.py -v

# Run with coverage
pytest --cov=app tests/
```

## Architecture Decisions

### Event-Driven Design
- **Rationale**: Decoupled agent communication, scalability
- **Implementation**: Redis pub/sub with structured events
- **Benefits**: Fault tolerance, auditability, real-time processing

### FastAPI Framework
- **Rationale**: High performance, automatic OpenAPI docs, type safety
- **Implementation**: Async/await throughout, dependency injection
- **Benefits**: Developer experience, performance, maintainability

### Circuit Breaker Pattern
- **Rationale**: System stability, risk management, fault isolation
- **Implementation**: Multi-level breakers with configurable thresholds
- **Benefits**: Automatic recovery, controlled degradation, safety

### Multi-Account Architecture
- **Rationale**: Risk distribution, scalability, prop firm requirements
- **Implementation**: Account-specific routing and state management
- **Benefits**: Isolation, compliance, performance optimization

## Security Considerations

- **API Key Encryption**: Vault integration for credential management
- **Network Security**: TLS encryption for all communications
- **Access Control**: Role-based access with JWT authentication
- **Audit Logging**: Complete audit trail for compliance
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: API rate limiting and DDoS protection

## Performance Targets

- **Signal to Trade Latency**: < 100ms (p99)
- **System Availability**: 99.5% uptime
- **Throughput**: 1000+ signals/minute
- **Recovery Time**: < 30 seconds from failure
- **Memory Usage**: < 2GB per orchestrator instance
- **CPU Usage**: < 50% under normal load