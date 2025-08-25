# TMT Trading System - System Management Scripts

This document describes the system management scripts for starting, stopping, and monitoring the TMT Trading System.

## Overview

The trading system supports two deployment modes:
- **Native Mode**: Services run directly on the host system using Python/Node.js
- **Docker Mode**: Services run in Docker containers using docker-compose

## Quick Start

### For Native Deployment
```bash
# Quick restart (most common)
python quick-restart.py

# Full restart with health checks
python restart-trading-system.py

# Stop all services
python stop-trading-system.py

# Health check
python system-health.py
```

### For Docker Deployment
```bash
# Quick restart
python quick-restart.py docker

# Docker-specific operations
python docker-restart.py restart

# Start services
python docker-restart.py start

# Check status
python docker-restart.py status

# View logs
python docker-restart.py logs
```

## Script Reference

### 1. restart-trading-system.py
**The main comprehensive restart script with full functionality.**

```bash
# Basic restart
python restart-trading-system.py

# Docker mode restart
python restart-trading-system.py --mode docker

# Force kill stubborn processes
python restart-trading-system.py --force

# Skip health validation (faster)
python restart-trading-system.py --skip-health-check
```

**Features:**
- Auto-detects and stops all trading system processes
- Supports both native and Docker deployments
- Graceful shutdown with force-kill fallback
- Port cleanup and resource management
- Service startup orchestration with proper delays
- Comprehensive health validation
- Detailed logging and status reporting

### 2. stop-trading-system.py
**Dedicated script for stopping all trading system services.**

```bash
# Graceful stop
python stop-trading-system.py

# Force kill if needed
python stop-trading-system.py --force
```

**Features:**
- Detects all trading system processes by name and port
- Graceful SIGTERM followed by force kill if needed
- Port cleanup verification
- Comprehensive process discovery

### 3. quick-restart.py
**Simplified wrapper for common restart scenarios.**

```bash
# Native mode (default)
python quick-restart.py

# Docker mode
python quick-restart.py docker

# Force restart
python quick-restart.py native --force
```

**Features:**
- Simplified command-line interface
- Auto-detection of deployment mode
- Sensible defaults for common use cases
- Always includes health checks for safety

### 4. docker-restart.py
**Specialized Docker management with docker-compose integration.**

```bash
# Full restart
python docker-restart.py restart

# Start services
python docker-restart.py start

# Stop services
python docker-restart.py stop

# Show status
python docker-restart.py status

# View logs
python docker-restart.py logs [service_name]

# Clean restart (removes volumes)
python docker-restart.py clean
```

**Features:**
- Native docker-compose integration
- Image building and pulling
- Volume and network management
- Service-specific log viewing
- JSON status parsing
- Clean restart option for troubleshooting

### 5. system-health.py
**Comprehensive health monitoring and system diagnostics.**

```bash
# One-shot health check
python system-health.py

# Continuous monitoring
python system-health.py --monitor

# Monitor every 60 seconds
python system-health.py --monitor --interval 60

# JSON output for automation
python system-health.py --json

# Docker mode health check
python system-health.py --mode docker
```

**Features:**
- Auto-detection of deployment mode
- HTTP endpoint health checks
- Port connectivity testing
- System resource monitoring (CPU, memory, disk)
- Response time measurement
- Issue detection and recommendations
- Continuous monitoring mode
- JSON output for automation
- Service criticality classification

## Service Architecture

### Core Trading Services
- **Orchestrator** (Port 8000): Main coordination service
- **Market Analysis** (Port 8002): Market data and signal generation
- **Execution Engine** (Port 8004): Trade execution and risk management
- **Dashboard** (Port 3000): Web interface

### Infrastructure Services (Docker Mode)
- **PostgreSQL** (Port 5432): Primary database
- **Redis** (Port 6379): Caching and real-time state
- **Kafka** (Port 9092): Event streaming
- **Prometheus** (Port 9090): Metrics collection
- **Grafana** (Port 3001): Monitoring dashboards
- **Jaeger** (Port 16686): Distributed tracing
- **Vault** (Port 8200): Secrets management

## Environment Variables

The scripts respect these environment variables:

```bash
# OANDA API Configuration
OANDA_API_KEY=your_api_key_here
OANDA_ACCOUNT_IDS=101-001-21040028-001
OANDA_ENVIRONMENT=practice

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_system
REDIS_URL=redis://localhost:6379
KAFKA_BROKERS=localhost:9092
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Services Won't Start
```bash
# Check if ports are occupied
python system-health.py

# Force kill existing processes
python restart-trading-system.py --force

# Check Docker status (if using Docker)
docker-compose ps
docker-compose logs
```

#### 2. Database Connection Issues
```bash
# For Docker mode
docker-compose restart postgres

# Check database health
python system-health.py --mode docker

# View database logs
python docker-restart.py logs postgres
```

#### 3. Port Already in Use
```bash
# Stop all services first
python stop-trading-system.py --force

# Check what's using the ports
netstat -tulpn | grep :8000
# or
lsof -i :8000

# Clean restart
python restart-trading-system.py --mode docker
```

#### 4. Docker Issues
```bash
# Clean restart with volume removal
python docker-restart.py clean

# Rebuild containers
docker-compose build --no-cache

# Prune Docker system
docker system prune -f
```

#### 5. Health Check Failures
```bash
# Detailed health check
python system-health.py

# Monitor continuously
python system-health.py --monitor --interval 15

# Check specific service logs
python docker-restart.py logs orchestrator
```

### Service Dependencies

**Startup Order:**
1. Infrastructure (PostgreSQL, Redis, Kafka)
2. Orchestrator
3. Market Analysis
4. Execution Engine
5. Dashboard

**Critical Dependencies:**
- Orchestrator requires PostgreSQL and Redis
- Market Analysis requires Orchestrator
- Execution Engine requires Orchestrator and Market Analysis
- Dashboard requires all core services

## Monitoring and Maintenance

### Regular Health Checks
```bash
# Daily health check (can be automated)
python system-health.py --json > health-$(date +%Y%m%d).json

# Monitor during trading hours
python system-health.py --monitor --interval 30
```

### Log Management
```bash
# View recent logs (Docker)
python docker-restart.py logs

# View specific service logs
python docker-restart.py logs orchestrator --tail 100

# Native mode logs are in ./logs/ directory
```

### Performance Monitoring
- System metrics are collected by `system-health.py`
- Docker mode includes Prometheus/Grafana for detailed metrics
- Check CPU, memory, and disk usage regularly
- Monitor service response times

### Backup Considerations
- PostgreSQL data: Backup before major changes
- Configuration files: Keep versioned in Git
- Environment variables: Document and secure
- Log files: Rotate regularly to save disk space

## Integration with CI/CD

The scripts can be integrated into automated deployment pipelines:

```bash
# Health check with exit codes
python system-health.py
if [ $? -eq 0 ]; then
    echo "System is healthy"
else
    echo "System has issues"
    python system-health.py --json
    exit 1
fi

# Automated restart
python restart-trading-system.py --skip-health-check
```

## Security Notes

1. **Environment Variables**: Never commit API keys to version control
2. **Port Access**: Ensure only necessary ports are exposed
3. **Service Authentication**: Use proper authentication for production
4. **Log Sanitization**: Ensure logs don't contain sensitive information
5. **Resource Limits**: Set appropriate memory and CPU limits for Docker containers

## Advanced Usage

### Custom Service Configurations
Scripts can be extended to support additional services by modifying the service configuration dictionaries in each script.

### Monitoring Integration
The health check script outputs JSON that can be integrated with external monitoring systems like Nagios, Zabbix, or DataDog.

### Load Testing
Before production deployment, use the scripts to restart the system and run load tests to ensure stability.

## Support

For issues with these scripts:
1. Check the logs in the `./logs/` directory
2. Run health checks to identify specific problems
3. Review the troubleshooting section above
4. Check Docker status if using Docker mode
5. Consult the main project documentation

---

**Last Updated**: $(date)
**Version**: 1.0.0