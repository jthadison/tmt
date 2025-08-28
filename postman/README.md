# TMT Trading System - Postman API Collections

This directory contains comprehensive Postman collections for testing and interacting with the TMT (Autonomous Trading System) APIs.

## 📁 Collections Overview

### 1. **TMT_Trading_System_Complete.postman_collection.json**
Complete API collection with all services and endpoints organized in a single collection:

#### 🏗️ Core Infrastructure
- **Orchestrator Service (Port 8089)** - Central coordination and signal processing
- **Execution Engine (Port 8082)** - Trade execution and order management  
- **Circuit Breaker Agent (Port 8084)** - Risk monitoring and safety controls

#### 🤖 8-Agent AI Ecosystem
- **Market Analysis Agent (8001)** - Market scanning and signal generation
- **Strategy Analysis Agent (8002)** - Performance tracking and regime detection
- **Parameter Optimization Agent (8003)** - Risk parameter tuning
- **Learning Safety Agent (8004)** - Safety systems and anomaly detection
- **Disagreement Engine (8005)** - Decision disagreement protocols
- **Data Collection Agent (8006)** - Pipeline metrics and data management
- **Continuous Improvement Agent (8007)** - Performance analysis and rollout
- **Pattern Detection Agent (8008)** - Wyckoff patterns and Volume Price Analysis

#### 📱 Dashboard API
- Real-time P&L analytics
- Trade history and analytics
- Agent performance monitoring
- Historical data analysis

## 🌍 Environment Files

### **TMT_Local_Development.postman_environment.json**
Pre-configured environment for local development with:
- All service ports (8001-8008, 8082, 8084, 8089, 3003)
- OANDA practice account configuration
- Base URL and authentication variables

## 🚀 Quick Start

### 1. Import Collections
1. Open Postman
2. Click "Import" → "Files" → Select the collection JSON files
3. Import both the collection and environment files

### 2. Set Up Environment
1. Select "TMT Local Development" environment
2. Set your OANDA API credentials:
   - `oanda_api_key` - Your OANDA practice account API key
   - `auth_token` - Authentication token (if required)

### 3. Start Services
Ensure all TMT services are running locally:

```bash
# Core Infrastructure
cd orchestrator && OANDA_API_KEY=your_key OANDA_ACCOUNT_IDS=your_account ENABLE_TRADING=true PORT=8089 python -m app.main &
cd execution-engine && PORT=8082 python simple_main.py &
cd agents/circuit-breaker && PORT=8084 python main.py &
cd dashboard && npm run dev &

# AI Agent Ecosystem  
cd agents/market-analysis && PORT=8001 python simple_main.py &
cd agents/strategy-analysis && PORT=8002 python start_agent_simple.py &
cd agents/parameter-optimization && PORT=8003 python start_agent.py &
cd agents/learning-safety && PORT=8004 python start_agent.py &
cd agents/disagreement-engine && PORT=8005 python start_agent.py &
cd agents/data-collection && PORT=8006 python start_agent.py &
cd agents/continuous-improvement && PORT=8007 python start_agent.py &
cd agents/pattern-detection && PORT=8008 python start_agent_simple.py &
```

### 4. Test System Health
Start with the health check endpoints to verify all services are running:
1. **Core Infrastructure** → **Orchestrator** → "System Health"
2. **Core Infrastructure** → **Execution Engine** → "System Health" 
3. **Core Infrastructure** → **Circuit Breaker** → "Agent Health"
4. **8-Agent AI Ecosystem** → Test each agent's "Agent Health" endpoint

## 🔧 Key Features

### 🎯 Ready-to-Use Examples
- Pre-configured request bodies with realistic trading data
- Proper authentication headers
- Environment variable usage throughout
- Sample data for all major operations

### 🛡️ Safety First
- All examples use OANDA practice account
- Circuit breaker testing included
- Risk validation endpoints
- Emergency stop procedures

### 📊 Complete Testing Coverage
- **Trading Operations**: Signal processing, order placement, position management
- **Analytics**: Real-time P&L, trade history, performance metrics
- **Agent Management**: Health checks, status monitoring, configuration
- **Safety Systems**: Circuit breakers, risk validation, emergency controls

### 🔄 Automation Features
- Dynamic variables using `{{$timestamp}}` and `{{$isoTimestamp}}`
- Chained requests using response data
- Environment-specific configurations
- Test scripts for automated validation

## 📋 Common Use Cases

### Trading Operations
1. **Generate Trading Signal**: Market Analysis Agent → Generate signal
2. **Process Signal**: Orchestrator → Process Trading Signal  
3. **Execute Trade**: Execution Engine → Place Market Order
4. **Monitor Position**: Get account status and open positions
5. **Emergency Stop**: Circuit Breaker → Emergency controls

### System Monitoring
1. **Health Check All Services**: Run all health endpoints
2. **Check System Status**: Orchestrator system status
3. **Monitor Agent Performance**: Dashboard → Agent analytics
4. **View Trading History**: Dashboard → Trade history

### Testing & Development
1. **Pattern Detection**: Test Wyckoff pattern detection algorithms
2. **Risk Validation**: Validate trades against risk parameters  
3. **Safety Systems**: Test circuit breakers and safety controls
4. **Performance Analytics**: Analyze system and agent performance

## 🔒 Security Notes

- **Never commit API keys**: Use environment variables only
- **Practice Account Only**: All examples use OANDA practice account
- **Rate Limiting**: Be mindful of API rate limits during testing
- **Authentication**: Some endpoints may require authentication tokens

## 📊 Response Examples

All requests include expected response examples for:
- ✅ Successful responses
- ❌ Error responses  
- 📊 Data structures
- 🔍 Status codes

## 🤝 Contributing

When adding new endpoints:
1. Follow the existing naming conventions
2. Add proper descriptions and examples
3. Use environment variables for configuration
4. Include response examples
5. Test with the local development environment

## 📞 Support

For issues with the Postman collections:
1. Verify all services are running locally
2. Check environment variable configuration  
3. Review the TMT system documentation
4. Test individual endpoints before complex workflows

---

**⚠️ Important**: This system handles live trading operations. Always use practice accounts for testing and ensure proper risk management controls are in place.