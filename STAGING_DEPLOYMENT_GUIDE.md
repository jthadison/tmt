# TMT Trading System - Staging Deployment Guide

## Overview

This guide will help you deploy your TMT Trading System to a staging environment using Docker containers. The staging environment mimics production but with conservative settings and safety mechanisms.

## Prerequisites

### Required Software
- **Docker** (20.10+)
- **Docker Compose** (2.0+)
- **Git** (for code deployment)

### Required Credentials
- **OANDA Practice Account** credentials
- **Slack Webhook URL** (optional but recommended)

## Quick Start

### 1. Download Trading System from GitHub

**Yes, you download the trading system from GitHub.** Here's how to get the code:

```bash
# Create project directory
mkdir -p ~/trading-system
cd ~/trading-system

# === OPTION 1: HTTPS with Personal Access Token (Recommended for Private Repos) ===
# Generate token at: https://github.com/settings/tokens
# Grant "repo" permissions
git clone https://your-username:your-personal-access-token@github.com/yourusername/tmt.git .

# === OPTION 2: HTTPS (Public repositories or when prompted for credentials) ===
git clone https://github.com/yourusername/tmt.git .

# === OPTION 3: SSH (If you have SSH key set up) ===
git clone git@github.com:yourusername/tmt.git .

# Verify download was successful
ls -la
git remote -v
echo "Repository cloned successfully!"
```

**Software Installation Prerequisites:**
```bash
# Install Docker (required)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose (required)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git (if not already installed)
sudo apt update && sudo apt install -y git

# Verify installations
docker --version
docker-compose --version
git --version
```

### 2. Prepare Environment Configuration

```bash
# Copy staging environment template (this creates your config file)
cp .env.staging.template .env.staging

# Edit with your credentials using your preferred editor
nano .env.staging
# OR use: vim .env.staging
# OR use: code .env.staging
```

**Required Environment Variables to Configure:**
```env
# OANDA Practice Account Credentials (Required)
OANDA_API_KEY=your_practice_api_key_here
OANDA_ACCOUNT_ID=your_practice_account_id_here

# Slack Notifications (Optional but recommended)
SLACK_WEBHOOK_URL=your_slack_webhook_url_here
SLACK_CHANNEL=staging-trade-alerts
```

**Important Notes:**
- Use your **OANDA Practice Account** credentials (not live account)
- Get OANDA credentials from: https://developer.oanda.com/
- Get Slack webhook from: https://api.slack.com/apps → Your App → Incoming Webhooks
- Trading starts **disabled** by default (`ENABLE_TRADING=false`)

### 3. Deploy to Staging

```bash
# Make deploy script executable
chmod +x scripts/staging-deploy.sh

# Run deployment
./scripts/staging-deploy.sh
```

### 4. Verify Deployment

Check service status:
```bash
docker-compose -f docker-compose.staging.yml ps
```

Access services:
- **Dashboard**: http://localhost:3003
- **Orchestrator API**: http://localhost:8089
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Architecture

### Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| **orchestrator** | 8089 | Main trading coordination |
| **execution-engine** | 8082 | Trade execution |
| **circuit-breaker** | 8084 | Risk management |
| **market-analysis** | 8001 | Market scanning |
| **strategy-analysis** | 8002 | Performance tracking |
| **parameter-optimization** | 8003 | Risk optimization |
| **learning-safety** | 8004 | Safety systems |
| **disagreement-engine** | 8005 | Decision validation |
| **data-collection** | 8006 | Data management |
| **continuous-improvement** | 8007 | Performance analysis |
| **pattern-detection** | 8008 | Pattern recognition |
| **dashboard** | 3003 | Web interface |
| **redis** | 6379 | Message broker |
| **prometheus** | 9090 | Metrics collection |
| **grafana** | 3000 | Monitoring dashboards |

### Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Host Machine                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │              Docker Network (tmt-network)           ││
│  │                                                     ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ││
│  │  │ Orchestrator│  │ Exec Engine │  │   Dashboard │  ││
│  │  │    :8089    │  │    :8082    │  │    :3003    │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  ││
│  │                                                     ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ││
│  │  │8x AI Agents │  │    Redis    │  │ Monitoring  │  ││
│  │  │ :8001-8008  │  │    :6379    │  │ :3000,9090  │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## Safety Features

### Built-in Safety Mechanisms

1. **Trading Disabled by Default**
   - `ENABLE_TRADING=false` initially
   - Must be manually enabled after verification

2. **Conservative Risk Settings**
   - Max 1 concurrent trade
   - 0.1% risk per trade
   - 0.5% max daily loss
   - Small position sizes (1000 units max)

3. **Practice Account Only**
   - `OANDA_ENVIRONMENT=practice`
   - No real money at risk

4. **Circuit Breakers**
   - Automatic position closing on losses
   - Emergency stop mechanisms
   - Real-time monitoring

5. **Health Checks**
   - All services monitored
   - Automatic restart on failure
   - Dependency management

## Configuration Management

### Environment-Specific Settings

**Staging Configuration (.env.staging):**
- Conservative risk parameters
- Enhanced logging
- Trading disabled by default
- Practice account only
- Separate Slack channel

**Key Differences from Production:**
- Lower position sizes
- More frequent health checks
- Debug logging enabled
- Additional safety thresholds

### Feature Flags

Control features via environment variables:
```env
FEATURE_SESSION_TRADING=false      # Advanced session targeting
FEATURE_PATTERN_RECOGNITION=true   # Pattern detection
FEATURE_RISK_MANAGEMENT=true       # Risk management
FEATURE_AUTO_RECOVERY=false        # Automatic recovery
```

## Monitoring & Observability

### Built-in Monitoring Stack

1. **Prometheus** (Metrics Collection)
   - Service health metrics
   - Performance monitoring
   - Trading statistics
   - Custom business metrics

2. **Grafana** (Visualization)
   - Pre-configured dashboards
   - Real-time charts
   - Alert visualization
   - Performance analytics

3. **Health Checks**
   - HTTP health endpoints
   - Docker health checks
   - Service dependency tracking
   - Automatic service recovery

### Key Metrics to Monitor

- **Service Health**: Up/down status, response times
- **Trading Metrics**: Trades executed, P&L, win rate
- **Risk Metrics**: Position sizes, exposure, drawdown
- **Performance**: Latency, throughput, errors

## Deployment Operations

### Starting the System

```bash
# Full deployment
./scripts/staging-deploy.sh

# Start specific services
docker-compose -f docker-compose.staging.yml up -d orchestrator

# Start with logs
docker-compose -f docker-compose.staging.yml up orchestrator
```

### Managing Services

```bash
# View all services
docker-compose -f docker-compose.staging.yml ps

# View logs
docker-compose -f docker-compose.staging.yml logs -f orchestrator

# Restart service
docker-compose -f docker-compose.staging.yml restart orchestrator

# Scale agents (if needed)
docker-compose -f docker-compose.staging.yml up -d --scale market-analysis=2
```

### Updating Code

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.staging.yml build orchestrator
docker-compose -f docker-compose.staging.yml up -d orchestrator
```

### Clean Shutdown

```bash
# Graceful shutdown
docker-compose -f docker-compose.staging.yml down

# Remove volumes (careful!)
docker-compose -f docker-compose.staging.yml down -v
```

## Testing Procedures

### 1. Pre-Trading Verification

Before enabling trading, verify:

```bash
# Check all services are healthy
docker-compose -f docker-compose.staging.yml ps

# Verify OANDA connection
curl http://localhost:8089/health

# Test Slack notifications
curl -X POST http://localhost:8089/test-notification

# Check agent connectivity
for port in {8001..8008}; do
  curl http://localhost:$port/health
done
```

### 2. Gradual Trading Enablement

1. **Start with monitoring only**
   ```env
   ENABLE_TRADING=false
   ```

2. **Enable trading with minimal risk**
   ```env
   ENABLE_TRADING=true
   RISK_PER_TRADE=0.001  # 0.1%
   MAX_POSITION_SIZE=1000
   ```

3. **Monitor for 24-48 hours**

4. **Gradually increase limits if stable**

### 3. Testing Checklist

- [ ] All services start and report healthy
- [ ] OANDA connection established
- [ ] Slack notifications working
- [ ] Dashboard accessible
- [ ] Prometheus metrics collecting
- [ ] Grafana dashboards loading
- [ ] Agent communication verified
- [ ] Circuit breakers functional
- [ ] Emergency stop tested

## Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check logs
docker-compose -f docker-compose.staging.yml logs service-name

# Check environment variables
docker-compose -f docker-compose.staging.yml exec service-name env

# Restart service
docker-compose -f docker-compose.staging.yml restart service-name
```

**OANDA Connection Issues:**
```bash
# Verify credentials in container
docker-compose -f docker-compose.staging.yml exec orchestrator env | grep OANDA

# Test OANDA API directly
curl -H "Authorization: Bearer $OANDA_API_KEY" \
     https://api-fxpractice.oanda.com/v3/accounts
```

**Agent Communication Issues:**
```bash
# Check network connectivity
docker network ls
docker network inspect tmt_tmt-network

# Test agent endpoints
curl http://localhost:8001/health
```

### Log Analysis

**View specific service logs:**
```bash
# Orchestrator
docker-compose -f docker-compose.staging.yml logs -f orchestrator

# All agents
docker-compose -f docker-compose.staging.yml logs -f market-analysis strategy-analysis
```

**Search logs for errors:**
```bash
docker-compose -f docker-compose.staging.yml logs | grep ERROR
```

## Security Considerations

### Staging Security

1. **Network Isolation**
   - Services communicate via Docker network
   - No external database connections
   - Limited port exposure

2. **Credentials Management**
   - Environment variables for secrets
   - No hardcoded credentials
   - Practice account only

3. **Access Control**
   - No external API exposure
   - Local access only
   - Basic authentication on monitoring

### Production Readiness

Before moving to production:
- [ ] Secure credential storage (Vault/Secrets Manager)
- [ ] HTTPS/TLS termination
- [ ] Proper firewall rules
- [ ] Backup and disaster recovery
- [ ] Comprehensive monitoring
- [ ] Security scanning
- [ ] Load testing

## Performance Optimization

### Resource Allocation

**Recommended Staging Resources:**
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD
- **Network**: Stable internet connection

**Service Resource Limits:**
```yaml
# In docker-compose.staging.yml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 256M
```

### Monitoring Performance

- Monitor CPU/memory usage
- Check response times
- Watch for memory leaks
- Monitor disk usage growth

## Next Steps

1. **Deploy and Verify**
   - Run deployment script
   - Verify all services healthy
   - Test basic functionality

2. **Monitor and Tune**
   - Watch logs for errors
   - Monitor performance metrics
   - Adjust resource limits if needed

3. **Enable Trading Gradually**
   - Start with minimal risk
   - Monitor for stability
   - Gradually increase limits

4. **Prepare for Production**
   - Security hardening
   - Performance testing
   - Disaster recovery planning
   - Production environment setup

## Support

For issues or questions:
1. Check logs first: `docker-compose -f docker-compose.staging.yml logs`
2. Review this guide
3. Test individual components
4. Check monitoring dashboards
5. Review Slack notifications for system alerts