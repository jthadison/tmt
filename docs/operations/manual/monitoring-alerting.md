# Monitoring and Alerting Setup

## Overview

This document provides comprehensive procedures for setting up, configuring, and managing monitoring and alerting systems for the TMT trading platform.

## Monitoring Architecture

### System Components

#### Prometheus (Metrics Collection)
- **Purpose**: Time-series database for system metrics
- **Port**: 9090
- **Configuration**: `/etc/prometheus/prometheus.yml`
- **Retention**: 30 days of metrics data

#### Grafana (Visualization)
- **Purpose**: Metrics visualization and dashboards
- **Port**: 3000
- **Configuration**: `/etc/grafana/grafana.ini`
- **Dashboards**: Pre-configured TMT trading dashboards

#### Alertmanager (Alert Routing)
- **Purpose**: Alert routing and notification management
- **Port**: 9093
- **Configuration**: `/etc/alertmanager/alertmanager.yml`
- **Integrations**: Email, Slack, PagerDuty

## Monitoring Setup Procedures

### Initial Configuration

#### 1. Prometheus Setup
```bash
# Install Prometheus
sudo apt-get install prometheus

# Configure targets
sudo nano /etc/prometheus/prometheus.yml

# Add TMT service targets
global:
  scrape_interval: 15s
  
scrape_configs:
  - job_name: 'tmt-agents'
    static_configs:
      - targets: ['localhost:8001', 'localhost:8002', 'localhost:8003']
  
  - job_name: 'tmt-execution-engine'
    static_configs:
      - targets: ['localhost:8004']
  
  - job_name: 'tmt-dashboard'
    static_configs:
      - targets: ['localhost:3000']

# Start Prometheus
sudo systemctl start prometheus
sudo systemctl enable prometheus
```

#### 2. Grafana Configuration
```bash
# Install Grafana
sudo apt-get install grafana

# Configure data source
curl -X POST http://admin:admin@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TMT-Prometheus",
    "type": "prometheus",
    "url": "http://localhost:9090",
    "access": "proxy",
    "isDefault": true
  }'

# Import TMT dashboards
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @/opt/tmt/monitoring/dashboards/tmt-overview.json
```

#### 3. Alertmanager Setup
```bash
# Configure alert routing
sudo nano /etc/alertmanager/alertmanager.yml

global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@tmt-trading.com'

route:
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'tmt-alerts'

receivers:
  - name: 'tmt-alerts'
    email_configs:
      - to: 'ops@tmt-trading.com'
        subject: '[TMT Alert] {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
```

## Key Metrics to Monitor

### System Health Metrics

#### Agent Health
```yaml
agent_health_metrics:
  - tmt_agent_status{agent="circuit_breaker"}
  - tmt_agent_status{agent="market_analysis"}
  - tmt_agent_status{agent="risk_management"}
  - tmt_agent_status{agent="anti_correlation"}
  - tmt_agent_status{agent="personality_engine"}
  - tmt_agent_status{agent="performance_tracker"}
  - tmt_agent_status{agent="compliance"}
  - tmt_agent_status{agent="learning_safety"}
```

#### Trading Performance
```yaml
trading_metrics:
  - tmt_trades_total
  - tmt_trades_successful_total
  - tmt_trades_failed_total
  - tmt_pnl_total
  - tmt_drawdown_current
  - tmt_risk_exposure_total
```

#### System Performance
```yaml
system_metrics:
  - tmt_execution_latency_seconds
  - tmt_api_requests_total
  - tmt_api_duration_seconds
  - tmt_database_connections
  - tmt_memory_usage_bytes
  - tmt_cpu_usage_percent
```

## Alert Configuration

### Critical Alerts (Immediate Response)

#### Trading System Alerts
```yaml
groups:
  - name: tmt-critical
    rules:
      - alert: TMTSystemDown
        expr: up{job="tmt-agents"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "TMT Agent is down"
          description: "TMT agent {{ $labels.instance }} has been down for more than 1 minute"
      
      - alert: HighDrawdown
        expr: tmt_drawdown_current > 0.08
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "High drawdown detected"
          description: "Account drawdown is {{ $value }}%, exceeding 8% limit"
      
      - alert: ExecutionLatencyHigh
        expr: tmt_execution_latency_seconds > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High execution latency"
          description: "Execution latency is {{ $value }}s, exceeding 100ms limit"
```

#### Infrastructure Alerts
```yaml
  - name: tmt-infrastructure
    rules:
      - alert: HighMemoryUsage
        expr: tmt_memory_usage_percent > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}%"
      
      - alert: DatabaseConnectionsFull
        expr: tmt_database_connections > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connections near limit"
          description: "Database connections: {{ $value }}/100"
```

### Warning Alerts (Review Required)

#### Performance Warnings
```yaml
  - name: tmt-performance
    rules:
      - alert: LowWinRate
        expr: (tmt_trades_successful_total / tmt_trades_total) < 0.5
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Low win rate detected"
          description: "Win rate is {{ $value }}%, below 50% threshold"
      
      - alert: HighErrorRate
        expr: rate(tmt_api_errors_total[5m]) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High API error rate"
          description: "API error rate is {{ $value }}%, above 5% threshold"
```

## Dashboard Configuration

### Trading Overview Dashboard

#### Key Panels
1. **Account Performance**
   - Current P&L by account
   - Drawdown levels
   - Risk exposure

2. **System Health**
   - Agent status indicators
   - Execution latency trends
   - Error rate monitoring

3. **Trading Activity**
   - Trades per hour
   - Success rate trends
   - Volume analysis

### Risk Management Dashboard

#### Risk Panels
1. **Risk Metrics**
   - Current exposure by instrument
   - Correlation analysis
   - VaR calculations

2. **Compliance Status**
   - Rule violations
   - Position limit utilization
   - Regulatory compliance score

## Alert Response Procedures

### Critical Alert Response

#### Immediate Actions (Within 5 minutes)
1. **Acknowledge Alert**: Acknowledge in monitoring system
2. **Assess Impact**: Determine scope of issue
3. **Initiate Response**: Start appropriate response procedure
4. **Notify Team**: Alert relevant team members

#### Response Escalation
```
Level 1: On-call engineer (0-15 minutes)
Level 2: Senior engineer + Risk manager (15-30 minutes)
Level 3: CTO + Head of Risk (30+ minutes)
```

### Alert Resolution Process

#### Documentation Requirements
1. **Incident Report**: Complete incident documentation
2. **Root Cause Analysis**: Identify underlying cause
3. **Resolution Steps**: Document resolution actions
4. **Prevention Measures**: Implement preventive measures

#### Post-Incident Review
- Conduct post-incident review within 24 hours
- Update monitoring thresholds if needed
- Improve alert definitions based on learnings
- Update response procedures

## Maintenance Procedures

### Daily Monitoring Tasks

#### Morning Checklist (07:00 UTC)
- [ ] Review overnight alerts and incidents
- [ ] Check system health dashboard
- [ ] Verify all agents are operational
- [ ] Review trading performance metrics
- [ ] Check resource utilization levels

#### Evening Checklist (22:00 UTC)
- [ ] Review daily trading performance
- [ ] Check error logs for patterns
- [ ] Verify backup completion
- [ ] Update monitoring documentation if needed

### Weekly Maintenance

#### Alert Review (Wednesdays)
- Review alert frequency and accuracy
- Adjust thresholds based on system behavior
- Remove or modify noisy alerts
- Test alert notification channels

#### Dashboard Updates (Fridays)
- Review dashboard effectiveness
- Add new metrics based on operational needs
- Update visualization based on user feedback
- Test dashboard performance

### Monthly Tasks

#### Monitoring System Health
- Review monitoring system performance
- Clean up old metrics and logs
- Update monitoring system versions
- Validate backup and recovery procedures

#### Alert Optimization
- Analyze alert patterns and trends
- Optimize alert grouping and routing
- Review and update escalation procedures
- Train team on new monitoring features

## Troubleshooting Common Issues

### Prometheus Issues

#### High Memory Usage
```bash
# Check Prometheus memory usage
ps aux | grep prometheus

# Review retention settings
grep retention /etc/prometheus/prometheus.yml

# Adjust retention if needed
--storage.tsdb.retention.time=15d
```

#### Missing Metrics
```bash
# Check scrape targets
curl http://localhost:9090/api/v1/targets

# Verify service endpoints
curl http://localhost:8001/metrics
```

### Grafana Issues

#### Dashboard Not Loading
```bash
# Check Grafana logs
sudo journalctl -u grafana-server -f

# Verify database connection
sudo grafana-cli admin reset-admin-password admin
```

#### Data Source Connection
```bash
# Test Prometheus connection
curl http://localhost:9090/api/v1/query?query=up

# Check Grafana data source configuration
curl -u admin:admin http://localhost:3000/api/datasources
```

### Alertmanager Issues

#### Alerts Not Firing
```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules

# Verify Alertmanager connectivity
curl http://localhost:9093/api/v1/status
```

#### Notification Failures
```bash
# Check Alertmanager logs
sudo journalctl -u alertmanager -f

# Test email configuration
sudo -u alertmanager alertmanager --config.file=/etc/alertmanager/alertmanager.yml --web.external-url=http://localhost:9093 --log.level=debug
```

For additional monitoring setup and configuration, see the [System Interface Guide](../user-guide/system-interface.md).