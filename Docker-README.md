# 🐳 TMT Trading System - Docker Deployment

## Overview

The TMT Trading System can be fully containerized using Docker, providing consistent deployment across different environments. This setup includes all core services and optional AI agents.

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** installed and running
- **Docker Compose** v3.8 or higher
- **OANDA API credentials** (practice or live account)

### 1. Configure Environment

Copy the Docker environment template:
```bash
cp .env.docker .env.docker.local
```

Edit `.env.docker.local` with your OANDA credentials:
```bash
OANDA_API_KEY=your-actual-oanda-api-key
OANDA_ACCOUNT_IDS=your-account-id
OANDA_ENVIRONMENT=practice
ENABLE_TRADING=true
```

### 2. Start the System

**Windows:**
```cmd
start-docker.bat
```

**Linux/Mac:**
```bash
chmod +x start-docker.sh
./start-docker.sh
```

**Manual:**
```bash
docker-compose -f docker-compose.current.yml --env-file .env.docker.local up --build -d
```

## 📊 Service Architecture

### Core Services (Required)

| Service | Port | Description | Health Check |
|---------|------|-------------|--------------|
| **Dashboard** | 3000 | Next.js web interface | http://localhost:3000 |
| **Orchestrator** | 8089 | Main trading coordinator | http://localhost:8089/health |
| **Market Analysis** | 8001 | Signal generation & analysis | http://localhost:8001/health |
| **Execution Engine** | 8082 | Trade execution & OANDA API | http://localhost:8082/health |

### AI Agent Services (Optional)

| Service | Port | Description |
|---------|------|-------------|
| **Strategy Analysis** | 8002 | Performance tracking |
| **Parameter Optimization** | 8003 | Risk parameter tuning |
| **Learning Safety** | 8004 | Circuit breakers & safety |
| **Disagreement Engine** | 8005 | Decision disagreement system |
| **Data Collection** | 8006 | Pipeline metrics |
| **Continuous Improvement** | 8007 | Performance analysis |
| **Pattern Detection** | 8008 | Wyckoff & VPA patterns |
| **Circuit Breaker** | 8084 | Emergency controls |

## 🔧 Docker Configuration

### Available Compose Files

1. **`docker-compose.current.yml`** - Current system (core + agents)
2. **`docker-compose.yml`** - Full infrastructure (includes databases, monitoring)

### Environment Variables

```bash
# Required
OANDA_API_KEY=your-api-key
OANDA_ACCOUNT_IDS=your-account-id
OANDA_ENVIRONMENT=practice|live

# Optional
ENABLE_TRADING=true
COMPOSE_PROJECT_NAME=trading-system
```

### Volume Mounts

- **Source Code**: Mounted for development with hot reload
- **Logs**: `./logs` → `/app/logs` (persistent logging)
- **Node Modules**: Anonymous volumes for better performance

## 🛠️ Management Commands

### Start Services

```bash
# Core services only
docker-compose -f docker-compose.current.yml up -d orchestrator market-analysis execution-engine dashboard

# All services
docker-compose -f docker-compose.current.yml up -d

# With infrastructure (databases, monitoring)
docker-compose up -d
```

### Stop Services

```bash
# Stop all
docker-compose -f docker-compose.current.yml down

# Stop specific service
docker-compose -f docker-compose.current.yml stop orchestrator
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.current.yml logs -f

# Specific service
docker-compose -f docker-compose.current.yml logs -f market-analysis

# Last 100 lines
docker-compose -f docker-compose.current.yml logs --tail=100 orchestrator
```

### Scale Services

```bash
# Scale market analysis agents
docker-compose -f docker-compose.current.yml up -d --scale market-analysis=3
```

## 🔍 Debugging & Troubleshooting

### Check Service Health

```bash
# All services status
docker-compose -f docker-compose.current.yml ps

# Individual health checks
curl http://localhost:8089/health  # Orchestrator
curl http://localhost:8001/health  # Market Analysis
curl http://localhost:8082/health  # Execution Engine
curl http://localhost:3000         # Dashboard
```

### Container Shell Access

```bash
# Access orchestrator container
docker exec -it trading-orchestrator bash

# Access market analysis container
docker exec -it trading-market-analysis bash

# Access dashboard container
docker exec -it trading-dashboard sh
```

### Resource Monitoring

```bash
# Resource usage
docker stats

# Container inspection
docker inspect trading-orchestrator
```

## 🏭 Production Deployment

### Production Environment

```bash
# Production environment file
cp .env.docker .env.production

# Update for production
OANDA_ENVIRONMENT=live
ENABLE_TRADING=true
NODE_ENV=production
```

### Production Build

```bash
# Build production images
docker-compose -f docker-compose.yml --env-file .env.production build

# Start in production mode
docker-compose -f docker-compose.yml --env-file .env.production up -d
```

### Resource Limits

Add resource constraints in `docker-compose.current.yml`:

```yaml
services:
  orchestrator:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

## 🔐 Security Considerations

### Secrets Management

```bash
# Use Docker secrets for sensitive data
echo "your-oanda-api-key" | docker secret create oanda_api_key -

# Reference in compose file
secrets:
  - oanda_api_key
```

### Network Security

```yaml
networks:
  trading-network:
    driver: bridge
    internal: true  # Prevent external access
```

### Container Security

```dockerfile
# Run as non-root user
RUN addgroup -g 1001 -S trading && adduser -S trading -G trading
USER trading
```

## 📈 Monitoring & Observability

### Health Checks

All services include built-in health checks:
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3-5 times
- **Start Period**: 30 seconds

### Logs

```bash
# Centralized logging
docker-compose -f docker-compose.current.yml logs -f | grep ERROR

# Export logs
docker-compose -f docker-compose.current.yml logs --since="1h" > trading-system.log
```

## 🚨 Emergency Procedures

### Emergency Stop

```bash
# Immediate stop (forceful)
docker-compose -f docker-compose.current.yml kill

# Graceful stop
docker-compose -f docker-compose.current.yml down --timeout 30
```

### Backup & Recovery

```bash
# Export running configuration
docker-compose -f docker-compose.current.yml config > current-config.yml

# Backup volumes
docker run --rm -v trading-system_logs:/data -v $(pwd):/backup alpine tar czf /backup/logs-backup.tar.gz -C /data .
```

## 📝 Development

### Hot Reload

All services are configured with volume mounts for development:
- **Python**: Auto-reload on file changes
- **Next.js**: Fast refresh enabled
- **Node.js**: Nodemon for automatic restarts

### Add New Agent

1. Create Dockerfile in agent directory
2. Add service to `docker-compose.current.yml`
3. Build and start: `docker-compose up -d --build new-agent`

## 🎯 Performance Optimization

### Image Optimization

```dockerfile
# Multi-stage builds
FROM python:3.11-slim AS base
# ... dependencies
FROM base AS development
# ... development setup
```

### Build Cache

```bash
# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker-compose build

# Prune unused images
docker image prune -f
```

## 🆘 Support

For issues with Docker deployment:

1. **Check logs**: `docker-compose logs -f`
2. **Verify health**: Run health check commands
3. **Resource usage**: `docker stats`
4. **Rebuild**: `docker-compose up --build -d`

The Docker setup provides a robust, scalable deployment option for the TMT Trading System with full session-targeted trading capabilities.