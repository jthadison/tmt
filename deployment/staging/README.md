# TMT Trading System - Staging Environment

Complete staging environment for the TMT (Adaptive/Continuous Learning Autonomous Trading System) with comprehensive monitoring, testing, and validation capabilities.

## 🎯 Overview

The staging environment provides:

- **Full System Deployment**: All 8 AI agents + infrastructure
- **Production-like Configuration**: Mirrors production setup with staging-specific settings
- **Comprehensive Monitoring**: Prometheus, Grafana, AlertManager with custom dashboards
- **Automated Testing**: Integration, performance, and load testing
- **Safety Features**: Paper trading mode, circuit breakers, compliance validation
- **Developer Tools**: Database admin, message queue management, log analysis

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM (16GB recommended)
- 20GB+ free disk space
- Linux/macOS (Windows with WSL2)

### Deploy Staging Environment

```bash
# Clone repository and navigate to staging
cd deployment/staging

# Full deployment with all features
sudo ./deploy-staging.sh

# Quick deployment (skip image builds and extensive testing)
sudo ./deploy-staging.sh --quick

# Force redeploy over existing environment
sudo ./deploy-staging.sh --force

# Deploy without running tests
sudo ./deploy-staging.sh --skip-tests
```

### Deployment Options

| Flag | Description |
|------|-------------|
| `--force` | Override existing deployment |
| `--cleanup-volumes` | Remove data volumes on failure |
| `--skip-tests` | Skip integration and performance tests |
| `--quick` | Fast deployment without full builds/tests |

## 📊 Access Points

After successful deployment:

### 🏗️ Core Services
- **API Gateway**: http://localhost:8000
- **Trading Dashboard**: http://localhost:3001
- **Health Check**: http://localhost:8000/health

### 📈 Monitoring
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3001 (admin/staging_admin_password)
- **AlertManager**: http://localhost:9094

### 🔧 Administration Tools
- **pgAdmin**: http://localhost:5051 (admin@tmt-staging.local/staging_pgadmin_password)
- **Kafka UI**: http://localhost:8081
- **Redis Commander**: http://localhost:8082

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     TMT Staging Environment                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Trading   │  │    Risk     │  │ Compliance  │            │
│  │ Dashboard   │  │ Management  │  │   Engine    │            │
│  │             │  │   (ARIA)    │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │                 │                 │                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              API Gateway                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                 │                 │                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Wyckoff    │  │ Circuit     │  │ Execution   │            │
│  │  Analysis   │  │ Breaker     │  │  Engine     │            │
│  │             │  │             │  │(Paper Mode) │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │                 │                 │                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    Anti-    │  │   Human     │  │ Continuous  │            │
│  │ Correlation │  │  Behavior   │  │Improvement  │            │
│  │             │  │             │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                         │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ PostgreSQL  │  │ TimescaleDB │  │    Redis    │            │
│  │ (Trading)   │  │  (Market)   │  │  (Cache)    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Kafka     │  │ Prometheus  │  │   Grafana   │            │
│  │ (Messages)  │  │ (Metrics)   │  │(Dashboards) │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🧪 Testing Framework

### Integration Testing

```bash
# Run full integration test suite
docker-compose --profile testing up integration-tester

# View test results
docker logs tmt-integration-tester-staging
```

### Performance Testing

```bash
# Run performance validation
docker-compose --profile testing up performance-validator

# Run load testing
docker-compose --profile testing up load-tester

# Check performance metrics
curl http://localhost:9091/api/v1/query?query=tmt_signal_execution_duration_seconds
```

### Load Testing

```bash
# Start continuous load testing
docker-compose --profile testing up -d load-tester

# Monitor load test progress
docker logs -f tmt-load-tester-staging

# Stop load testing
docker-compose --profile testing stop load-tester
```

## 📊 Monitoring & Observability

### Key Metrics Monitored

- **Latency**: Signal-to-execution pipeline (<100ms SLA)
- **Uptime**: System availability (99.5% SLA)
- **Throughput**: Trade execution success rate
- **Resource Usage**: CPU, memory, disk, network
- **Business Metrics**: P&L, risk metrics, compliance

### Alerts Configured

- **Critical**: Latency breaches, system downtime, circuit breaker activations
- **Warning**: Performance degradation, resource constraints
- **Info**: System events, report generation

### Custom Dashboards

1. **System Overview**: Health status, uptime, key metrics
2. **Performance Monitoring**: Latency distribution, throughput trends
3. **Trading Operations**: P&L tracking, trade volume, success rates
4. **Risk Management**: Drawdown levels, circuit breaker status
5. **Infrastructure Health**: Resource utilization, service status

## 🔧 Management Commands

### Service Management

```bash
# View all services status
docker-compose ps

# View logs for specific service
docker-compose logs -f circuit-breaker-staging

# Restart service
docker-compose restart wyckoff-staging

# Scale service (e.g., 3 instances)
docker-compose up -d --scale aria-risk-staging=3

# Stop all services
docker-compose down

# Full cleanup (removes data)
docker-compose down -v --remove-orphans
```

### Health Monitoring

```bash
# Run health check
./scripts/health-check.sh

# View system resource usage
docker stats

# Check endpoint health
curl http://localhost:8000/health
curl http://localhost:9091/-/healthy
```

### Data Management

```bash
# Generate test data
docker-compose --profile data-generation up data-generator

# Backup staging data
./scripts/backup-staging.sh

# Access database
docker exec -it tmt-postgres-staging psql -U trading_user -d trading_staging

# Access TimescaleDB
docker exec -it tmt-timescaledb-staging psql -U timescale_user -d market_data_staging
```

## 🎛️ Configuration

### Environment Variables

Key staging-specific configurations:

```bash
# Safety Settings
PAPER_TRADING=true           # No real money
SIMULATION_MODE=true         # Use simulated data
MT4_ENABLED=false           # Disable broker connections

# Performance Settings
CIRCUIT_BREAKER_THRESHOLDS_LOOSE=true  # More permissive
RISK_MULTIPLIER=0.5                     # Reduced risk
COMPLIANCE_MODE=lenient                 # Less strict rules

# Testing Settings
LOAD_TESTING_ENABLED=true              # Enable load testing
IMPROVEMENT_CYCLE_FAST=true            # Accelerated cycles
DETECTION_INTERVAL=60                  # More frequent checks
```

### Service Configuration

Each service has staging-specific configuration in:
- `config/[service]-staging.yml`
- Environment variables in `docker-compose.staging.yml`
- Runtime parameters for testing scenarios

## 🚨 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check service logs
docker-compose logs [service-name]

# Check resource usage
docker stats

# Verify network connectivity
docker network ls
docker network inspect tmt-staging
```

**Performance issues:**
```bash
# Check system resources
htop
df -h
free -m

# Monitor container resources
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

**Database connection issues:**
```bash
# Test database connectivity
docker exec tmt-postgres-staging pg_isready -U trading_user
docker exec tmt-timescaledb-staging pg_isready -U timescale_user

# Check database logs
docker logs tmt-postgres-staging
```

**Monitoring not working:**
```bash
# Check Prometheus targets
curl http://localhost:9091/api/v1/targets

# Verify Grafana datasource
curl http://localhost:3001/api/health

# Check AlertManager
curl http://localhost:9094/api/v1/status
```

### Log Analysis

```bash
# View all logs with timestamps
docker-compose logs -t

# Filter for errors
docker-compose logs 2>&1 | grep -i error

# Monitor real-time logs
docker-compose logs -f --tail=100

# Export logs for analysis
docker-compose logs > staging-logs-$(date +%Y%m%d_%H%M%S).log
```

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
name: Deploy Staging
on:
  push:
    branches: [develop]
  
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to staging
        run: |
          cd deployment/staging
          sudo ./deploy-staging.sh --quick
      - name: Run tests
        run: |
          cd deployment/staging
          docker-compose --profile testing up integration-tester
```

### Deployment Pipeline

1. **Code Push** → Trigger staging deployment
2. **Build Images** → Create staging-specific images
3. **Deploy Services** → Roll out infrastructure and applications
4. **Run Tests** → Integration, performance, and load tests
5. **Validate** → Health checks and monitoring validation
6. **Report** → Generate deployment report and metrics

## 📈 Performance Benchmarks

### Target Performance

- **API Response Time**: < 100ms (95th percentile)
- **Database Query Time**: < 10ms (average)
- **Signal Processing**: < 50ms (end-to-end)
- **System Uptime**: 99.5%
- **Memory Usage**: < 8GB total
- **CPU Usage**: < 70% average

### Load Testing Results

Typical staging environment can handle:
- **Concurrent Users**: 50+
- **Requests per Second**: 1000+
- **Database Connections**: 100+
- **Message Throughput**: 10,000 msgs/sec

## 🔐 Security

### Staging Security Features

- **Network Isolation**: Dedicated Docker network
- **Access Control**: Service-specific authentication
- **Data Encryption**: TLS for inter-service communication
- **Secrets Management**: Environment-based secrets
- **Audit Logging**: Comprehensive activity logs

### Security Best Practices

- Regular security scans
- Updated base images
- Minimal service privileges
- Network segmentation
- Secure defaults

## 📚 Additional Resources

- [Production Deployment Guide](../production/README.md)
- [Development Setup](../../docs/development.md)
- [Architecture Documentation](../../docs/architecture/README.md)
- [API Documentation](../../docs/api/README.md)
- [Monitoring Runbooks](../../docs/runbooks/README.md)

## 📞 Support

For staging environment issues:

1. **Check Health**: Run `./scripts/health-check.sh`
2. **View Logs**: `docker-compose logs [service]`
3. **Monitor Dashboards**: Grafana at http://localhost:3001
4. **Contact Team**: Create issue in project repository

---

**Last Updated**: 2025-08-14  
**Version**: 1.0.0  
**Environment**: Staging