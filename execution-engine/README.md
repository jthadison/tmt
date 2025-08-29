# TMT Execution Engine MVP

High-performance execution engine with sub-100ms order placement for automated trading systems.

## Overview

The Execution Engine MVP provides comprehensive order and position management with real-time risk controls, designed to meet demanding performance requirements for professional trading operations.

### Key Features

✅ **Sub-100ms Execution**: Market orders executed within 100ms (95th percentile)  
✅ **8 Order Types**: Market, Limit, Stop, Stop-Limit, Trailing Stop, MIT, FOK, IOC  
✅ **Real-time Risk Management**: Position limits, leverage controls, kill switches  
✅ **High Throughput**: 100 orders/second sustained, 1000 orders/second burst  
✅ **OANDA Integration**: Full v20 API integration with connection pooling  
✅ **Production Monitoring**: Comprehensive Prometheus metrics and alerting  

## Performance Targets

| Metric | Target | Maximum |
|--------|--------|---------|
| Market Order Execution | < 100ms (95th percentile) | < 200ms |
| Order Modification | < 50ms | < 100ms |
| Order Cancellation | < 50ms | < 100ms |
| Position Close | < 100ms | < 200ms |
| Sustained Throughput | 100 orders/second | - |
| Burst Throughput | 1000 orders/second | 10 seconds |
| Memory Usage | < 500MB | < 1GB |
| CPU Usage | < 10% (50 concurrent) | < 20% |

## Quick Start

### Prerequisites

- Python 3.11+
- OANDA API credentials
- Redis (optional, for caching)
- Prometheus (optional, for monitoring)

### Installation

```bash
cd execution-engine
pip install -e .
```

### Configuration

Create `.env` file:

```bash
# OANDA Configuration
OANDA_API_KEY=your_oanda_api_key
OANDA_ACCOUNT_ID=your_account_id
OANDA_ENVIRONMENT=practice  # or 'live'

# Performance Configuration
MAX_CONCURRENT_ORDERS=50
MAX_POSITION_SIZE=100000
MAX_LEVERAGE=30

# Monitoring
PROMETHEUS_PORT=8091
LOG_LEVEL=info
```

### Running the Service

```bash
# Development
python -m app.main

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8004 --workers 1
```

The API will be available at `http://localhost:8004`

## API Documentation

### Order Management

#### Submit Order
```http
POST /api/v1/orders
Content-Type: application/json

{
  "account_id": "account_123",
  "instrument": "EUR_USD",
  "units": 10000,
  "side": "buy",
  "type": "market",
  "stop_loss": {
    "price": 1.0950,
    "guaranteed": false
  },
  "take_profit": {
    "price": 1.1050
  }
}
```

#### Modify Order
```http
PUT /api/v1/orders/{order_id}/modify
Content-Type: application/json

{
  "price": 1.0960,
  "units": 15000
}
```

#### Cancel Order
```http
PUT /api/v1/orders/{order_id}/cancel
```

### Position Management

#### Get Positions
```http
GET /api/v1/positions?account_id=account_123
```

#### Close Position
```http
POST /api/v1/positions/close
Content-Type: application/json

{
  "instrument": "EUR_USD",
  "units": 5000,
  "reason": "take_profit"
}
```

### Risk Management

#### Validate Order
```http
POST /api/v1/risk/validate
Content-Type: application/json

{
  "account_id": "account_123",
  "instrument": "EUR_USD",
  "units": 10000,
  "side": "buy",
  "type": "market"
}
```

#### Activate Kill Switch
```http
POST /api/v1/risk/{account_id}/kill-switch?reason=emergency_stop
```

### Monitoring

#### Performance Metrics
```http
GET /api/v1/performance/metrics
```

#### Health Check
```http
GET /health
```

## Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Order Manager  │    │Position Manager │    │  Risk Manager   │
│                 │    │                 │    │                 │
│ • Order Queue   │    │ • P&L Tracking  │    │ • Validation    │
│ • Execution     │    │ • Margin Calc   │    │ • Kill Switch   │
│ • State Mgmt    │    │ • Price Updates │    │ • Limits        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  OANDA Client   │
                    │                 │
                    │ • Connection    │
                    │   Pool (10x)    │
                    │ • Rate Limiting │
                    │ • Retry Logic   │
                    └─────────────────┘
                                 │
                         ┌──────────────┐
                         │ Prometheus   │
                         │  Metrics     │
                         │ Port 8091    │
                         └──────────────┘
```

### Data Flow

1. **Order Submission** → Risk Validation → Queue → OANDA Execution
2. **Position Updates** → Real-time P&L → Risk Monitoring → Alerts
3. **Market Data** → Price Updates → Position Valuation → Metrics

## Risk Controls

### Pre-Trade Validation
- Position size limits
- Leverage restrictions
- Margin requirements
- Daily loss limits
- Instrument restrictions

### Real-Time Monitoring
- Risk score calculation (0-100)
- Margin utilization tracking
- P&L monitoring
- Kill switch activation

### Example Risk Configuration
```python
risk_limits = RiskLimits(
    max_position_size=Decimal("100000"),
    max_positions_per_instrument=3,
    max_leverage=Decimal("30"),
    max_daily_loss=Decimal("1000"),
    required_margin_ratio=Decimal("0.02")
)
```

## Performance Optimization

### Connection Pooling
- 10 persistent HTTPS connections to OANDA
- Keep-alive connections with 30s expiry
- Rate limiting: 100 requests/second

### Async Processing
- Non-blocking order execution
- Concurrent order processing
- Background position monitoring

### Caching Strategy
- Instrument info: 5-minute TTL
- Margin calculations: 2-second TTL
- Position data: 1-second TTL

### Memory Management
- LRU cache for completed orders
- Periodic garbage collection
- Memory usage monitoring

## Monitoring & Alerting

### Prometheus Metrics

#### Execution Performance
```
execution_order_duration_seconds{order_type, instrument, result}
execution_orders_total{order_type, instrument, status, result}
execution_slippage_basis_points{instrument, order_type}
```

#### System Health
```
execution_active_orders{account_id}
execution_open_positions{account_id, instrument}
execution_memory_usage_bytes{component}
execution_cpu_usage_percent{component}
```

#### Risk Metrics
```
execution_risk_violations_total{account_id, violation_type}
execution_kill_switch_activations_total{account_id, reason}
```

### Alerting Rules

#### Critical Alerts (Immediate Response)
- Kill switch activation
- Order execution failures > 5%
- Memory usage > 1GB
- API connection failures

#### Warning Alerts (Monitor)
- P95 execution time > 100ms
- Risk score > 80
- Memory usage > 500MB
- High slippage detected

## Testing

### Performance Tests
```bash
# Run performance test suite
pytest tests/test_performance.py -m performance -v

# Run specific performance test
pytest tests/test_performance.py::test_market_order_latency_95th_percentile -v

# Run stress tests
pytest tests/test_performance.py -m slow -v
```

### Load Testing
```bash
# Sustained load test (100 orders/second for 60 seconds)
python scripts/load_test.py --rate 100 --duration 60

# Burst test (1000 orders/second for 10 seconds)
python scripts/load_test.py --rate 1000 --duration 10 --burst
```

## Deployment

### Production Checklist

- [ ] OANDA production credentials configured
- [ ] Risk limits properly set
- [ ] Monitoring and alerting configured
- [ ] Performance benchmarks validated
- [ ] Load testing completed
- [ ] Backup procedures tested
- [ ] Kill switch procedures documented

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
EXPOSE 8004 8091

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OANDA_API_KEY` | - | OANDA API key (required) |
| `OANDA_ACCOUNT_ID` | - | OANDA account ID (required) |
| `OANDA_ENVIRONMENT` | practice | OANDA environment |
| `MAX_CONCURRENT_ORDERS` | 50 | Maximum concurrent orders |
| `MAX_POSITION_SIZE` | 100000 | Maximum position size |
| `PROMETHEUS_PORT` | 8091 | Prometheus metrics port |
| `LOG_LEVEL` | info | Logging level |

## Troubleshooting

### Common Issues

#### High Execution Latency
1. Check OANDA API connectivity
2. Monitor system resources
3. Review connection pool utilization
4. Check rate limiting

#### Order Rejections
1. Verify risk limits configuration
2. Check account margin availability
3. Validate instrument tradability
4. Review OANDA account status

#### Memory Leaks
1. Monitor order cache size
2. Check for unclosed connections
3. Review position update frequency
4. Force garbage collection

### Debug Endpoints

```bash
# Detailed health check
curl http://localhost:8004/health/detailed

# Performance metrics
curl http://localhost:8004/api/v1/performance/metrics

# Risk metrics for account
curl http://localhost:8004/api/v1/risk/account_123/metrics
```

## Support

### Documentation
- API Reference: http://localhost:8004/docs
- Metrics: http://localhost:8091/metrics
- Health: http://localhost:8004/health

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Request/response tracing
- Performance metrics logging

## License

MIT License - See LICENSE file for details.

---

**Version**: 1.0.0  
**Last Updated**: 2025-08-21  
**Minimum Python**: 3.11+