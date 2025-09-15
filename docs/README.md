# TMT Trading System Documentation

## Overview

This directory contains technical documentation for the TMT (Adaptive/Continuous Learning Autonomous Trading System) addressing key architectural issues and providing integration guidance.

## Documentation Index

### 🚨 **Issue Resolution**
- **[SIGNAL_ARCHITECTURE_ISSUE.md](SIGNAL_ARCHITECTURE_ISSUE.md)** - Documents the signal endpoint architecture issue discovered during optimization script development, including root cause analysis and resolution steps.

### 🔧 **Integration Guides**
- **[SERVICE_INTEGRATION_GUIDE.md](SERVICE_INTEGRATION_GUIDE.md)** - Comprehensive guide for integrating with TMT system services, including communication patterns, endpoint discovery, and best practices.

- **[OPTIMIZATION_ENDPOINTS.md](OPTIMIZATION_ENDPOINTS.md)** - Detailed documentation of Market Analysis service optimization endpoints, including API specifications and usage examples.

## Quick Reference

### Service Ports
- **Dashboard:** 3003 (Next.js)
- **Market Analysis:** 8001 (FastAPI)
- **Execution Engine:** 8082 (FastAPI)
- **Circuit Breaker:** 8084 (FastAPI)
- **Orchestrator:** 8089 (FastAPI)

### Key Endpoints
```
# Health checks
GET  /health                    # All services

# Market Analysis
GET  /status                   # Agent status with signal counts
GET  /optimization/report      # Comprehensive analysis
POST /optimization/analyze     # Trigger analysis

# Orchestrator
POST /api/signals             # Signal routing
GET  /status                  # System status

# OANDA Integration
GET  /v3/accounts/{id}/summary     # Account info
GET  /v3/accounts/{id}/trades      # Trade history
```

### Common Integration Patterns

#### Signal Flow
```
Market Analysis → POST /api/signals → Orchestrator → OANDA
```

#### Data Retrieval
```
OANDA API → Trade History → Dashboard/Scripts
Market Analysis → /optimization/report → Analysis Tools
```

#### Service Health Monitoring
```bash
curl http://localhost:8001/health  # Market Analysis
curl http://localhost:8089/health  # Orchestrator
curl http://localhost:8082/health  # Execution Engine
```

## Issue Summary: Signal Architecture

**Problem:** Optimization scripts were trying to fetch signal history from non-existent `/signals` endpoints.

**Root Cause:** Market Analysis service sends signals to orchestrator but doesn't persist them locally for retrieval.

**Solution:**
- Use OANDA API for real trade history
- Use `/optimization/report` endpoint for signal analysis
- Implement caching system for performance data

**Result:** Optimization now uses 500+ real trades instead of mock data.

## Getting Started

### 1. Verify Services Running
```bash
# Check all services
for port in 8001 8082 8089 8084; do
  echo "Port $port: $(curl -s http://localhost:$port/health | python -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo 'Not responding')"
done
```

### 2. Test OANDA Connectivity
```bash
# Set environment variables
export OANDA_API_KEY="your-api-key"
export OANDA_ACCOUNT_ID="your-account-id"

# Test connection
curl -H "Authorization: Bearer $OANDA_API_KEY" \
  "https://api-fxpractice.oanda.com/v3/accounts/$OANDA_ACCOUNT_ID/summary"
```

### 3. Run Optimization with Real Data
```bash
cd agents/market-analysis
python cache_trading_data.py           # Cache real data
python optimize_signal_performance.py --mode optimize  # Run with real data
```

## Best Practices

### Service Integration
1. **Always verify endpoints exist** before integration
2. **Use graceful fallbacks** when services unavailable
3. **Implement proper error handling** for network issues
4. **Cache data appropriately** to reduce API calls

### Data Flow
1. **Use OANDA API directly** for financial data
2. **Use optimization endpoints** for signal analysis
3. **Implement service discovery** for dynamic endpoint resolution
4. **Monitor service health** continuously

### Development
1. **Check service documentation** before assuming API structure
2. **Test integrations thoroughly** with real services
3. **Document API changes** as they occur
4. **Use proper authentication** for external APIs

## Troubleshooting

### Common Issues

**Service Not Responding:**
```bash
# Check if running
netstat -an | findstr :8001

# Check logs
docker logs service-name  # or service-specific logs
```

**Endpoint Not Found (404):**
```bash
# List available endpoints
curl http://localhost:8001/

# Check service version/branch
git branch -a
```

**Authentication Failures:**
```bash
# Verify API key
echo $OANDA_API_KEY

# Test authentication
curl -H "Authorization: Bearer $OANDA_API_KEY" \
  "https://api-fxpractice.oanda.com/v3/accounts"
```

## Contributing

When adding new documentation:
1. Follow the established format
2. Include practical examples
3. Document both success and error cases
4. Update this README index

## Related Files

### System Configuration
- `.env` - Environment variables and API credentials
- `CLAUDE.md` - Project overview and system status

### Service Code
- `agents/market-analysis/simple_main.py` - Market Analysis service
- `orchestrator/app/main.py` - Orchestrator service
- `dashboard/app/api/trades/history/route.ts` - Dashboard API

### Integration Scripts
- `agents/market-analysis/optimize_signal_performance.py` - Optimization script
- `agents/market-analysis/cache_trading_data.py` - Data caching utility

---

**Last Updated:** September 15, 2025
**System Status:** ✅ Fully Operational - Live Trading Active
**Documentation Version:** 1.0