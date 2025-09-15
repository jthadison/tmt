# Signal Architecture Issue Documentation

## Issue Summary

**Problem:** The signal optimization script was attempting to fetch signal history from a non-existent `/signals` endpoint on the market analysis service, causing the optimization to fall back to mock data instead of using real trading signals.

**Date Identified:** September 15, 2025
**Severity:** Medium (optimization worked but used fake data)
**Status:** ✅ Resolved

## Root Cause Analysis

### What We Expected
The optimization script (`optimize_signal_performance.py`) was designed to:
1. Fetch historical signals from `GET /signals/history`
2. Load recent signals from `GET /signals/recent`
3. Analyze real signal performance for optimization

### What Actually Existed
The market analysis service architecture was different:
- **No signal storage endpoints** - signals are sent but not persisted
- **No signal retrieval endpoints** - no `/signals` or `/signals/history`
- **Signals flow through orchestrator** - POST to `/api/signals` for execution
- **Optimization endpoints exist** - but provide analysis, not raw signal data

## Current Signal Flow Architecture

```mermaid
graph TD
    A[Market Analysis Agent] -->|POST /api/signals| B[Orchestrator]
    B -->|Trade Execution| C[OANDA API]
    C -->|Trade Results| D[Trade History]

    A -->|Optimization Analysis| E[/optimization/analyze]
    A -->|Threshold Optimization| F[/optimization/optimize-threshold]
    A -->|Status Reports| G[/optimization/report]

    H[Optimization Script] -.->|❌ Expected| I[GET /signals/history]
    H -->|✅ Should Use| E
    H -->|✅ Should Use| F
    H -->|✅ Should Use| G
```

## Actual Service Endpoints

### Market Analysis Service (Port 8001)

**❌ Non-Existent Endpoints (What We Tried):**
```
GET /signals          # Does not exist
GET /signals/history  # Does not exist
GET /signals/recent   # Does not exist
```

**✅ Available Endpoints:**
```
GET  /health                    # Service health
GET  /status                   # Agent status with signal counts
POST /reset-signals            # Reset signal counter
POST /optimization/analyze     # Signal performance analysis
POST /optimization/optimize-threshold  # Threshold optimization
GET  /optimization/status      # Optimization configuration
GET  /optimization/report      # Comprehensive optimization report
POST /optimization/implement   # Apply optimization changes
GET  /optimization/monitor     # Monitor optimization results
```

**Signal Flow:**
```
POST /api/signals → Orchestrator  # Signals sent here, not stored locally
```

## Resolution

### 1. Updated Data Sources
**Before:**
```python
# Tried to fetch from non-existent endpoint
async with session.get(f"{self.market_analysis_url}/signals/history")
```

**After:**
```python
# Use actual OANDA trade history + optimization reports
trades = await oanda_client.getClosedTrades(500)
report = await session.get(f"{self.market_analysis_url}/optimization/report")
```

### 2. New Data Flow
1. **OANDA Trade History** → Real execution data (500+ trades)
2. **Optimization Reports** → Signal analysis and recommendations
3. **Account Metrics** → Live performance data
4. **Cache System** → Local storage for analysis

### 3. Benefits Achieved
- ✅ **Real Data**: 500+ actual trades from OANDA account
- ✅ **Live Metrics**: Current balance, P&L, positions
- ✅ **Accurate Analysis**: Based on real performance, not mock data
- ✅ **Better Recommendations**: 72.5% threshold suggested from real patterns

## Impact Analysis

### Before Fix
- Optimization used 200 fake signals with random data
- Analysis was theoretical, not based on real performance
- Recommendations might not match actual trading patterns
- No connection to real account metrics

### After Fix
- Uses 500+ real trades from OANDA account
- Analyzes actual signal performance and conversion rates
- Recommendations based on live trading data
- Connected to real account: $99,913.80 balance, 5 open positions

## Lessons Learned

### 1. Service Integration Assumptions
**Issue:** Assumed services would have data retrieval endpoints
**Learning:** Always verify actual API endpoints before building integrations

### 2. Documentation Gap
**Issue:** No clear documentation of signal flow architecture
**Learning:** Need comprehensive service interaction diagrams

### 3. Data Persistence Strategy
**Issue:** Signals generated but not stored for analysis
**Learning:** Consider adding database layer for signal history

## Prevention Strategies

### 1. Service Discovery
Before building integrations:
```bash
# Always check actual endpoints
curl http://localhost:8001/
curl http://localhost:8001/health
```

### 2. API Documentation
Maintain up-to-date endpoint documentation:
- What endpoints exist
- What data they return
- How services communicate

### 3. Data Architecture Planning
For future enhancements:
- Where is data stored?
- How is data retrieved?
- What's the data retention policy?

## Future Improvements

### 1. Signal Database Layer
Consider adding persistent storage for signals:
```sql
CREATE TABLE signal_history (
  signal_id VARCHAR(255) PRIMARY KEY,
  generated_at TIMESTAMP,
  confidence DECIMAL(5,2),
  pattern_type VARCHAR(100),
  executed BOOLEAN,
  execution_result JSON
);
```

### 2. Real-Time Signal API
Add endpoints for signal retrieval:
```python
@app.get("/signals/recent")
async def get_recent_signals(hours: int = 24):
    # Return signals from last N hours

@app.get("/signals/history")
async def get_signal_history(start_date: str, end_date: str):
    # Return historical signals
```

### 3. Signal-Trade Linking
Link signals to their execution results:
- Track which signals became trades
- Calculate actual conversion rates
- Measure signal performance over time

## Related Files

- `agents/market-analysis/optimize_signal_performance.py` - Updated optimization script
- `agents/market-analysis/cache_trading_data.py` - New data caching system
- `agents/market-analysis/OPTIMIZATION_GUIDE.md` - Updated usage guide
- `agents/market-analysis/simple_main.py` - Market analysis service endpoints

## Resolution Verification

✅ **Optimization now uses real data:**
```bash
cd agents/market-analysis
python optimize_signal_performance.py --mode optimize
# Output: Uses 500+ real OANDA trades, not mock data
```

✅ **Service endpoints confirmed:**
```bash
curl http://localhost:8001/optimization/report
# Returns real analysis with 228 signals generated today
```

✅ **Account integration working:**
```bash
python cache_trading_data.py
# Successfully caches real account data: $99,913.80 balance
```

---

**Documentation Author:** Claude Code Assistant
**Date:** September 15, 2025
**Version:** 1.0