# Signal Performance Optimization Guide

## Overview

The optimization script has been updated to use **real trading data** from your OANDA account and system services instead of hard-coded mock values.

## Key Changes Made

### 1. Real Data Sources
- **OANDA API Integration**: Fetches actual closed trades and account metrics
- **Market Analysis Service**: Retrieves real signal history
- **Orchestrator Integration**: Gets current system configuration and performance
- **Data Caching**: Stores signal and trade data locally for faster analysis

### 2. Removed Hard-Coded Values
- ~~Fixed 65% threshold~~ → Reads from orchestrator config
- ~~Mock 2.9% conversion rate~~ → Calculates from actual signals/trades
- ~~200 fake signals~~ → Real signal history or limited realistic data
- ~~Random execution data~~ → Actual OANDA trade history

## Usage

### Step 1: Set Environment Variables
```bash
set OANDA_API_KEY=your-actual-api-key
set OANDA_ACCOUNT_ID=101-001-21040028-001
```

### Step 2: Cache Trading Data (Optional)
```bash
python cache_trading_data.py
```
This creates:
- `signal_cache.json` - Historical signals
- `trade_cache.json` - Trade execution history

### Step 3: Run Optimization

**Analyze current performance:**
```bash
python optimize_signal_performance.py --mode analyze
```

**Optimize thresholds:**
```bash
python optimize_signal_performance.py --mode optimize
```

**Implement changes:**
```bash
python optimize_signal_performance.py --mode implement --threshold 70.0
```

**Monitor results:**
```bash
python optimize_signal_performance.py --mode monitor --monitoring-hours 24
```

## Data Flow

```
OANDA API → Trade History
     ↓
Market Analysis → Signal History
     ↓
Orchestrator → Current Config
     ↓
Optimization Engine → Recommendations
```

## What It Now Uses

### From OANDA:
- Closed trade history (up to 500 trades)
- Account balance and margin
- Open position count
- Realized/unrealized P&L

### From Orchestrator:
- Current confidence threshold
- Trading enabled status
- Active signal count
- Performance metrics

### From Market Analysis:
- Historical signal data
- Recent signal generation
- Pattern detection results

## Fallback Behavior

If services are unavailable:
1. Checks local cache files first
2. Uses limited realistic mock data (50 signals instead of 200)
3. Logs warnings about data sources

## Next Steps

To get full real data integration:

1. **Ensure services are running:**
   ```bash
   # Market Analysis
   cd agents/market-analysis && PORT=8001 python simple_main.py

   # Orchestrator
   cd orchestrator && PORT=8089 python -m app.main
   ```

2. **Build signal history database:**
   - Signals need to be stored when generated
   - Consider adding SQLite or PostgreSQL for persistence

3. **Link signals to trades:**
   - Track which signals resulted in trades
   - Calculate actual conversion rates

## Troubleshooting

**No signals found:**
- Check if market analysis service is running on port 8001
- Verify signal generation is active

**No trade data:**
- Ensure OANDA_API_KEY is set correctly
- Check if account has trade history

**Connection errors:**
- Verify all services are running
- Check firewall/port accessibility