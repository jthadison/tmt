# TMT Trading System - Postman Import Guide

## 📦 Quick Import Instructions

### Step 1: Import Collection
1. Open Postman
2. Click **"Import"** button (top left)
3. Select **"Files"** tab
4. Drag & drop or browse to select: `TMT_Trading_System_Complete.postman_collection.json`
5. Click **"Import"**

### Step 2: Import Environment
1. In the Import dialog (or click Import again)
2. Select **"Files"** tab  
3. Drag & drop or browse to select: `TMT_Local_Development.postman_environment.json`
4. Click **"Import"**

### Step 3: Activate Environment
1. Click the **environment dropdown** (top right, says "No Environment")
2. Select **"TMT Local Development"**
3. ✅ You should now see all variables populated

## 🔧 Configuration Setup

### Required Environment Variables
Set these in your environment (click the eye icon next to environment name):

| Variable | Value | Description |
|----------|--------|-------------|
| `oanda_api_key` | `your-practice-key` | OANDA practice account API key |
| `auth_token` | `your-token` | (Optional) Authentication token |

### Getting OANDA Practice API Key
1. Go to [OANDA Practice Account](https://fxtrade.oanda.com/your_account/api_access)
2. Generate a new API key
3. Copy the key to `oanda_api_key` environment variable

## 🚀 System Startup Checklist

Before testing, ensure all services are running:

### Core Infrastructure ✅
```bash
# Terminal 1 - Orchestrator (Port 8089)
cd orchestrator && OANDA_API_KEY=your_key OANDA_ACCOUNT_IDS=101-001-21040028-001 ENABLE_TRADING=true PORT=8089 python -m app.main

# Terminal 2 - Execution Engine (Port 8082)  
cd execution-engine && PORT=8082 python simple_main.py

# Terminal 3 - Circuit Breaker (Port 8084)
cd agents/circuit-breaker && PORT=8084 python main.py

# Terminal 4 - Dashboard (Port 3003)
cd dashboard && npm run dev
```

### 8-Agent AI Ecosystem ✅
```bash
# Market Analysis (8001)
cd agents/market-analysis && PORT=8001 python simple_main.py

# Strategy Analysis (8002) 
cd agents/strategy-analysis && PORT=8002 python start_agent_simple.py

# Parameter Optimization (8003)
cd agents/parameter-optimization && PORT=8003 python start_agent.py

# Learning Safety (8004)
cd agents/learning-safety && PORT=8004 python start_agent.py

# Disagreement Engine (8005)
cd agents/disagreement-engine && PORT=8005 python start_agent.py

# Data Collection (8006)
cd agents/data-collection && PORT=8006 python start_agent.py

# Continuous Improvement (8007)
cd agents/continuous-improvement && PORT=8007 python start_agent.py

# Pattern Detection (8008)
cd agents/pattern-detection && PORT=8008 python start_agent_simple.py
```

## 🧪 Testing Workflow

### 1. Health Check All Services
**Folder: 🏗️ Core Infrastructure**
- Run "System Health" for Orchestrator, Execution Engine, Circuit Breaker
- ✅ All should return `200 OK` with healthy status

**Folder: 🤖 8-Agent AI Ecosystem**  
- Run "Agent Health" for all 8 agents (ports 8001-8008)
- ✅ All should return `200 OK` status

### 2. Test Trading Pipeline
**Signal Generation → Execution:**
1. **Orchestrator** → "Process Trading Signal"
2. **Execution Engine** → "Place Market Order" 
3. **Circuit Breaker** → "Evaluate Trade"
4. Check account status and positions

### 3. Test Analytics & Monitoring
**Dashboard API:**
1. "Real-time P&L Analytics"
2. "Trade History"
3. "Analytics - Agents Performance"

### 4. Advanced Features
**Pattern Detection:**
1. "Detect Wyckoff Patterns"
2. "Analyze Volume Price Action"
3. "Get Pattern Alerts"

## 📊 Expected Results

### ✅ Successful Responses
- **Health Checks**: `200 OK` with service status
- **Trading Signals**: `200/201/202` with processing confirmation
- **Market Orders**: `200 OK` with trade details
- **Analytics**: `200 OK` with data (or `500` with mock data fallback)

### ⚠️ Common Issues
- **404 Not Found**: Service not running on expected port
- **Connection Refused**: Service not started or wrong port
- **500 Internal Error**: Service error (check logs)
- **Mock Data Responses**: Normal when OANDA/Redis not connected

## 🔒 Security Notes

- **Practice Account Only**: All examples use OANDA practice account
- **API Key Safety**: Never commit API keys, use environment only  
- **Rate Limiting**: OANDA has rate limits, avoid rapid-fire requests
- **Emergency Controls**: Circuit breakers will block risky trades

## 🎯 Collection Structure

```
TMT Trading System Complete
├── 🏗️ Core Infrastructure
│   ├── 🎛️ Orchestrator Service (Port 8089)
│   ├── ⚡ Execution Engine (Port 8082) 
│   └── 🛡️ Circuit Breaker Agent (Port 8084)
├── 🤖 8-Agent AI Ecosystem
│   ├── 📈 Market Analysis Agent (Port 8001)
│   ├── 📊 Strategy Analysis Agent (Port 8002)
│   ├── 🎯 Parameter Optimization Agent (Port 8003)
│   ├── 🛡️ Learning Safety Agent (Port 8004)
│   ├── ⚖️ Disagreement Engine (Port 8005)
│   ├── 📊 Data Collection Agent (Port 8006)
│   ├── 🔄 Continuous Improvement Agent (Port 8007)
│   └── 🔍 Pattern Detection Agent (Port 8008)
└── 📱 Dashboard API
    ├── Real-time P&L Analytics
    ├── Trade History  
    ├── Analytics - Trades
    ├── Analytics - Agents Performance
    └── Analytics - Historical Data
```

## 🛟 Troubleshooting

### Services Not Starting
1. Check Python/Node.js dependencies installed
2. Verify ports not in use: `netstat -an | findstr :8089`
3. Check environment variables set correctly
4. Review service logs for errors

### API Calls Failing
1. Verify environment selected in Postman
2. Check service health endpoints first  
3. Confirm OANDA API key valid and active
4. Review request body format matches examples

### Authentication Issues  
1. Verify `oanda_api_key` set in environment
2. Check API key permissions in OANDA
3. Ensure using practice account endpoints
4. Review OANDA API documentation for changes

## 📞 Support Resources

- **TMT System Docs**: `/docs/` directory
- **OANDA API Docs**: https://developer.oanda.com/rest-live-v20/introduction/
- **Postman Docs**: https://learning.postman.com/docs/
- **Issue Tracking**: Check system logs and service health

---

🎉 **You're all set!** Start with health checks, then explore the complete trading system API.