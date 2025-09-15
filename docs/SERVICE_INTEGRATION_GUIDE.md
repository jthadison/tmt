# Service Integration Guide

## Overview

This guide documents how the different services in the TMT trading system communicate with each other and how to properly integrate with existing endpoints.

## Service Architecture Map

```mermaid
graph TB
    subgraph "Dashboard (Port 3003)"
        D[Next.js Dashboard]
        D1[/api/trades/history]
        D2[/api/debug/oanda]
        D3[/api/prices/live]
    end

    subgraph "Orchestrator (Port 8089)"
        O[Trading Orchestrator]
        O1[POST /api/signals]
        O2[GET /health]
        O3[GET /status]
    end

    subgraph "Market Analysis (Port 8001)"
        MA[Market Analysis Agent]
        MA1[GET /status]
        MA2[POST /optimization/*]
        MA3[GET /optimization/report]
    end

    subgraph "Execution Engine (Port 8082)"
        EE[Execution Engine]
        EE1[GET /health]
        EE2[GET /journal/summary]
    end

    subgraph "Circuit Breaker (Port 8084)"
        CB[Circuit Breaker Agent]
        CB1[GET /health]
    end

    subgraph "External APIs"
        OANDA[OANDA API]
        OANDA1[GET /v3/accounts/{id}/summary]
        OANDA2[GET /v3/accounts/{id}/trades]
        OANDA3[GET /v3/accounts/{id}/pricing]
    end

    %% Signal Flow
    MA -->|POST /api/signals| O1
    O -->|Trade Execution| OANDA

    %% Data Retrieval
    D1 -->|Account Data| OANDA
    D1 -->|Trade History| O
    D3 -->|Live Prices| OANDA

    %% Health Monitoring
    D -->|Health Checks| MA1
    D -->|Health Checks| O2
    D -->|Health Checks| EE1
    D -->|Health Checks| CB1
```

## Service Communication Patterns

### 1. Signal Generation & Execution

**Flow:** Market Analysis → Orchestrator → OANDA

```python
# Market Analysis sends signals
signal_data = {
    "signal_id": "MA_1694845200",
    "symbol": "EUR_USD",
    "signal_type": "buy",
    "confidence": 75,
    "entry_price": 1.1000,
    "stop_loss": 1.0950,
    "take_profit": 1.1050
}

# POST to orchestrator
async with aiohttp.ClientSession() as session:
    await session.post(
        "http://localhost:8089/api/signals",
        json=signal_data
    )
```

### 2. Trade History Retrieval

**Sources:** OANDA API → Dashboard API → Frontend

```python
# Dashboard fetches from OANDA directly
oandaClient.getClosedTrades(500)  # Get trade history
oandaClient.getOpenTrades()       # Get open positions

# Orchestrator provides metadata
fetch("http://localhost:8089/trades")  # AI signal metadata
```

### 3. Optimization Analysis

**Flow:** Optimization Script → Market Analysis Service

```python
# Get optimization report
async with aiohttp.ClientSession() as session:
    response = await session.get(
        "http://localhost:8001/optimization/report"
    )
    data = await response.json()
    # Returns real analysis with signal performance
```

## Endpoint Discovery Guide

### Before Building Integrations

Always verify available endpoints:

```bash
# 1. Check service root
curl http://localhost:8001/

# 2. Check health endpoint
curl http://localhost:8001/health

# 3. Check status for detailed info
curl http://localhost:8001/status

# 4. Test specific endpoints
curl -X POST http://localhost:8001/optimization/analyze
```

### Common Integration Mistakes

❌ **Wrong:** Assuming endpoints exist
```python
# This will fail - endpoint doesn't exist
response = await session.get("/signals/history")
```

✅ **Right:** Use actual available endpoints
```python
# This works - endpoint exists and returns real data
response = await session.get("/optimization/report")
```

## Service-Specific Integration Notes

### Market Analysis Service (Port 8001)

**Available Data Sources:**
- `/status` → Signal generation statistics
- `/optimization/report` → Performance analysis
- `/optimization/analyze` → Trigger new analysis

**Data NOT Available:**
- Raw signal history (signals sent to orchestrator, not stored)
- Individual signal details
- Real-time signal feed

**Integration Pattern:**
```python
# Get signal statistics
status = await get_market_analysis_status()
signals_today = status['signals_generated_today']

# Get performance analysis
report = await get_optimization_report()
conversion_rate = report['signal_performance']['conversion_rate']
```

### Orchestrator Service (Port 8089)

**Primary Role:** Signal routing and execution coordination

**Available Endpoints:**
- `GET /health` → System health
- `GET /status` → Trading status and circuit breakers
- `POST /api/signals` → Receive signals for execution

**Integration Pattern:**
```python
# Send signals for execution
await send_signal_to_orchestrator(signal_data)

# Check system status
status = await get_orchestrator_status()
trading_enabled = status['trading_enabled']
```

### OANDA Integration

**Direct Integration:** Dashboard connects directly to OANDA API

**Available Data:**
- Account summary (balance, margin, P&L)
- Trade history (closed trades)
- Open positions
- Live pricing data

**Integration Pattern:**
```python
from lib.oanda_client import getOandaClient

client = getOandaClient()
trades = await client.getClosedTrades(500)
account = await client.getAccountSummary()
```

## Data Flow Patterns

### 1. Real-Time Trading Data

```
Market Analysis → Generate Signal
       ↓
Orchestrator → Receive & Route
       ↓
OANDA API → Execute Trade
       ↓
Dashboard → Display Results
```

### 2. Historical Analysis

```
OANDA API → Provide Trade History
       ↓
Optimization Script → Analyze Performance
       ↓
Market Analysis → Generate Recommendations
       ↓
Dashboard → Display Insights
```

### 3. Live Monitoring

```
Multiple Services → Health Status
       ↓
Dashboard → Aggregate Status
       ↓
Real-time Updates → User Interface
```

## Best Practices

### 1. Endpoint Verification
```python
async def verify_service_available(url: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/health") as response:
                return response.status == 200
    except:
        return False
```

### 2. Graceful Fallbacks
```python
# Try primary source first
try:
    data = await get_from_orchestrator()
except:
    # Fall back to OANDA direct
    data = await get_from_oanda()
```

### 3. Service Discovery
```python
SERVICES = {
    'market_analysis': 'http://localhost:8001',
    'orchestrator': 'http://localhost:8089',
    'execution_engine': 'http://localhost:8082',
    'circuit_breaker': 'http://localhost:8084'
}

async def discover_available_services():
    available = {}
    for name, url in SERVICES.items():
        if await verify_service_available(url):
            available[name] = url
    return available
```

### 4. Error Handling
```python
async def safe_api_call(url: str, timeout: int = 10):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"API call failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"API call error: {e}")
        return None
```

## Testing Service Integrations

### 1. Unit Tests
```python
async def test_market_analysis_status():
    status = await get_market_analysis_status()
    assert 'signals_generated_today' in status
    assert isinstance(status['signals_generated_today'], int)
```

### 2. Integration Tests
```python
async def test_signal_flow():
    # Generate signal
    signal = create_test_signal()

    # Send to orchestrator
    result = await send_signal_to_orchestrator(signal)
    assert result is True

    # Verify in trade history (after delay)
    await asyncio.sleep(5)
    trades = await get_recent_trades()
    assert len(trades) > 0
```

### 3. Health Check Tests
```bash
#!/bin/bash
# test_services.sh

services=("8001" "8082" "8089" "8084")
for port in "${services[@]}"; do
    if curl -f http://localhost:$port/health > /dev/null 2>&1; then
        echo "✅ Service on port $port is healthy"
    else
        echo "❌ Service on port $port is not responding"
    fi
done
```

## Troubleshooting

### Common Issues

1. **Service Not Responding**
   - Check if service is running: `curl http://localhost:PORT/health`
   - Check port conflicts: `netstat -an | findstr PORT`
   - Check logs for startup errors

2. **Endpoint Not Found (404)**
   - Verify endpoint exists: `curl http://localhost:PORT/`
   - Check API documentation
   - Confirm service version/branch

3. **Data Format Mismatch**
   - Check response structure: `curl -s URL | python -m json.tool`
   - Verify data types match expectations
   - Check for API version changes

4. **Authentication Errors**
   - Verify OANDA API key is set
   - Check API key permissions
   - Confirm account ID is correct

### Debug Commands

```bash
# Service health check
for port in 8001 8082 8089 8084; do
  echo "Port $port:"
  curl -s http://localhost:$port/health | python -m json.tool
  echo "---"
done

# Detailed service status
curl -s http://localhost:8001/status | python -m json.tool
curl -s http://localhost:8089/status | python -m json.tool

# Test OANDA connectivity
curl -H "Authorization: Bearer $OANDA_API_KEY" \
  "https://api-fxpractice.oanda.com/v3/accounts/$OANDA_ACCOUNT_ID/summary"
```

---

**Last Updated:** September 15, 2025
**Maintainer:** Development Team