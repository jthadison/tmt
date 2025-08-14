# TMT Trading System Monitoring Stack

Production-ready monitoring infrastructure for the TMT (Adaptive/Continuous Learning Autonomous Trading System) to ensure compliance with critical SLA requirements:

- **<100ms latency** for signal-to-execution pipeline
- **99.5% uptime** for system availability
- **Real-time alerting** for business and technical metrics

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TMT Trading   │───▶│   Prometheus    │───▶│    Grafana      │
│    System       │    │   (Metrics)     │    │ (Visualization) │
│                 │    │                 │    │                 │
│ • 8 AI Agents   │    │ • Time Series   │    │ • Dashboards    │
│ • Execution     │    │ • Alerting      │    │ • Monitoring    │
│ • Database      │    │ • Storage       │    │ • Analysis      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐             │
         │              │  AlertManager   │             │
         │              │  (Notifications)│             │
         │              │                 │             │
         │              │ • Email         │             │
         │              │ • Slack         │             │
         │              │ • PagerDuty     │             │
         │              └─────────────────┘             │
         │                                              │
         └──────────────────────────────────────────────┘
                        Logs & Traces
```

## Quick Start

### 1. Deploy Monitoring Stack

```bash
# Start monitoring services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Verify services are running
docker-compose -f monitoring/docker-compose.monitoring.yml ps
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/secure_admin_password)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### 3. Configure Trading System Metrics

Add to your trading services:

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Latency tracking
signal_execution_latency = Histogram(
    'tmt_signal_execution_duration_seconds',
    'Time taken for signal-to-execution pipeline',
    ['account_id', 'symbol']
)

# Success rate tracking
trade_execution_total = Counter(
    'tmt_trade_execution_total',
    'Total trade executions',
    ['account_id', 'symbol', 'action']
)

trade_execution_success = Counter(
    'tmt_trade_execution_success_total',
    'Successful trade executions',
    ['account_id', 'symbol', 'action']
)

# Usage example
def execute_trade(signal):
    start_time = time.time()
    
    try:
        # Your trading logic here
        result = perform_trade_execution(signal)
        
        # Record success
        trade_execution_success.labels(
            account_id=signal.account_id,
            symbol=signal.symbol,
            action=signal.action
        ).inc()
        
    except Exception as e:
        # Record failure
        pass
    finally:
        # Record latency
        execution_time = time.time() - start_time
        signal_execution_latency.labels(
            account_id=signal.account_id,
            symbol=signal.symbol
        ).observe(execution_time)
        
        trade_execution_total.labels(
            account_id=signal.account_id,
            symbol=signal.symbol,
            action=signal.action
        ).inc()
```

## Key Metrics Monitored

### Performance Metrics
- **Signal-to-execution latency** (95th percentile < 100ms)
- **Agent communication latency**
- **Database query performance**
- **API response times**

### Reliability Metrics
- **System uptime** (target: 99.5%)
- **Trade execution success rate** (target: >99.5%)
- **Service availability**
- **Error rates by component**

### Business Metrics
- **Daily P&L by account**
- **Trade volume and frequency**
- **Win rate and risk metrics**
- **Account drawdown levels**

### Safety Metrics
- **Circuit breaker activations**
- **Compliance rule violations**
- **Risk threshold breaches**
- **Emergency stop events**

## Alert Severity Levels

### 🚨 CRITICAL (Immediate Response)
- Signal execution latency > 100ms
- System uptime < 99.5%
- Circuit breaker activations
- Trade execution failures > 0.5%

**Response Time**: < 5 minutes
**Notification**: Email + Slack + PagerDuty

### ⚠️ WARNING (Prompt Response)
- Latency trending upward
- Memory usage > 85%
- Compliance violations increasing
- Performance degradation

**Response Time**: < 30 minutes
**Notification**: Email + Slack

### ℹ️ INFO (Monitoring)
- New trading sessions
- Report generation
- System events

**Response Time**: Next business day
**Notification**: Email

## Dashboard Overview

The main Grafana dashboard provides:

1. **System Health Overview**
   - Service status indicators
   - Overall system uptime
   - Active alerts summary

2. **Performance Monitoring**
   - Real-time latency metrics (95th percentile)
   - SLA compliance tracking
   - Performance trends

3. **Trading Operations**
   - Trade execution success rates
   - Daily P&L by account
   - Volume and frequency metrics

4. **Risk Management**
   - Circuit breaker status
   - Account drawdown levels
   - Compliance violations

5. **Infrastructure Health**
   - Resource utilization
   - Database performance
   - Message queue status

## Alert Routing

### Critical Trading Team
- **Latency breaches**: performance-team@company.com
- **Circuit breaker**: risk-team@company.com
- **System failures**: infrastructure@company.com

### Business Team
- **P&L alerts**: business-team@company.com, finance@company.com
- **Risk metrics**: risk-team@company.com

### Security Team
- **Access anomalies**: security@company.com
- **Authentication failures**: security@company.com

## Runbook Links

Critical alerts include runbook links for immediate response:

- **Latency Breach**: https://docs.company.com/runbooks/latency-breach
- **Uptime SLA**: https://docs.company.com/runbooks/uptime-breach
- **Circuit Breaker**: https://docs.company.com/runbooks/circuit-breaker
- **Execution Failures**: https://docs.company.com/runbooks/execution-failures

## Data Retention

- **Prometheus metrics**: 30 days (configurable)
- **Grafana dashboards**: Persistent
- **Alert history**: 90 days
- **Logs (Loki)**: 7 days

## Security Considerations

- **Network isolation**: Monitoring stack on dedicated network
- **Access control**: Role-based dashboard access
- **Data encryption**: TLS for all communications
- **Audit logging**: All configuration changes logged

## Maintenance

### Regular Tasks
- Review alert thresholds monthly
- Update dashboards based on business needs
- Clean up old metrics and logs
- Test alert routing quarterly

### Emergency Procedures
- Circuit breaker manual override
- Alert suppression during maintenance
- Emergency contact escalation
- Backup monitoring activation

## Troubleshooting

### Common Issues

**Metrics not appearing**:
```bash
# Check if services are exposing metrics
curl http://localhost:8000/metrics

# Verify Prometheus is scraping
docker logs tmt-prometheus
```

**Alerts not firing**:
```bash
# Check AlertManager configuration
docker logs tmt-alertmanager

# Verify rule evaluation
curl http://localhost:9090/api/v1/rules
```

**Dashboard not loading**:
```bash
# Check Grafana logs
docker logs tmt-grafana

# Verify data source connectivity
```

## Performance Tuning

### High-Volume Environments
- Increase Prometheus storage retention
- Configure metric federation for multi-region
- Implement query result caching
- Use recording rules for complex queries

### Resource Optimization
- Tune scrape intervals based on criticality
- Configure metric relabeling to reduce cardinality
- Implement alert de-duplication
- Use external storage for long-term retention

For additional support, contact the DevOps team or refer to the [monitoring troubleshooting guide](https://docs.company.com/monitoring/troubleshooting).