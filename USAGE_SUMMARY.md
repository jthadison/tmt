# TMT Trading System - Restart Scripts Summary

## ✅ WORKING SCRIPTS

### 1. restart-infrastructure.py (RECOMMENDED)
**The fully working solution for complete system restart.**

```bash
# Full restart (infrastructure + trading services)
python restart-infrastructure.py

# Infrastructure only (databases, monitoring)
python restart-infrastructure.py --infrastructure-only

# Force mode if needed
python restart-infrastructure.py --force
```

**What it does:**
- ✅ Stops/starts infrastructure services via Docker (PostgreSQL, Redis, Kafka, Prometheus, Grafana)
- ✅ Starts native trading services (Orchestrator, Market Analysis, Execution Engine)
- ✅ Proper startup sequencing with delays
- ✅ Environment variable configuration
- ✅ No psutil issues (Windows-compatible)

### 2. restart-fix.py 
**Simple Docker-only restart (for infrastructure).**

```bash
# Docker infrastructure restart
python restart-fix.py --mode docker
```

### 3. stop-trading-system.py
**Original working stop script.**

```bash
# Stop all services gracefully  
python stop-trading-system.py

# Force kill if needed
python stop-trading-system.py --force
```

## ❌ PROBLEMATIC SCRIPTS

### restart-trading-system.py
**Issues:** psutil Unicode errors on Windows, complex process discovery

### restart-trading-system-clean.py  
**Issues:** Incomplete implementation, psutil timeout issues

## 🎯 RECOMMENDED WORKFLOW

### Daily Operations
```bash
# Quick restart everything
python restart-infrastructure.py

# Just restart infrastructure (if trading services are fine)
python restart-infrastructure.py --infrastructure-only

# Stop everything
python stop-trading-system.py
```

### Infrastructure Services Started
- **PostgreSQL**: localhost:5432 (trading_system database)
- **Redis**: localhost:6379 (caching)
- **Kafka**: localhost:9092 (messaging)
- **Prometheus**: http://localhost:9090 (metrics)
- **Grafana**: http://localhost:3001 (dashboards) - admin/admin

### Trading Services Started (Native)
- **Orchestrator**: http://localhost:8000/health
- **Market Analysis**: http://localhost:8002/health  
- **Execution Engine**: http://localhost:8004/health

## 🔧 TROUBLESHOOTING

### If Services Don't Start
1. Check environment variables are set:
   ```bash
   echo $OANDA_API_KEY
   echo $OANDA_ACCOUNT_IDS
   echo $OANDA_ENVIRONMENT
   ```

2. Check Docker is running:
   ```bash
   docker version
   docker-compose version
   ```

3. Check ports are available:
   ```bash
   netstat -an | findstr ":5432 :6379 :8000 :8002 :8004"
   ```

### If Infrastructure Fails
```bash
# Manual Docker check
docker-compose -f docker-compose-simple.yml ps
docker-compose -f docker-compose-simple.yml logs

# Clean Docker restart
docker-compose -f docker-compose-simple.yml down -v
python restart-infrastructure.py --infrastructure-only
```

### If Trading Services Fail
```bash
# Check individual services
python -m uvicorn orchestrator.app.main:app --host 0.0.0.0 --port 8000
python start-market-analysis.py  
python start-execution-engine.py
```

## 🚀 PRODUCTION NOTES

1. **Environment Variables**: Set these in production:
   ```
   OANDA_API_KEY=your_real_api_key
   OANDA_ACCOUNT_IDS=your_account_ids  
   OANDA_ENVIRONMENT=live  # or practice
   DATABASE_URL=postgresql://user:pass@host:5432/trading_system
   ```

2. **Monitoring**: Access Grafana at http://localhost:3001 for system monitoring

3. **Logs**: Trading service logs go to stdout, infrastructure logs via `docker-compose logs`

4. **Health Checks**: All services have health endpoints at `/health`

## 📝 SUMMARY

**Use `restart-infrastructure.py` for all restart operations.**

It provides:
- ✅ Reliable infrastructure management via Docker
- ✅ Native trading service startup with proper environment
- ✅ Windows compatibility (no psutil issues)
- ✅ Proper service sequencing and health checks
- ✅ Clear status reporting

The original complex restart script had Windows psutil compatibility issues. The new infrastructure approach is simpler, more reliable, and separates concerns between infrastructure (Docker) and trading services (native Python).