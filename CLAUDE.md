# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Adaptive/Continuous Learning Autonomous Trading System - a sophisticated AI platform for prop firm traders. The system uses 8 specialized AI agents to manage multiple prop firm accounts simultaneously, employing Wyckoff methodology with Volume Price Analysis and Smart Money Concepts while maintaining compliance and avoiding detection.

## Project Status

**🔥 LIVE TRADING SYSTEM - FULLY OPERATIONAL & ACTIVELY TRADING**

The system is now fully operational with complete 8-agent AI trading ecosystem running in production. The system is **actively monitoring markets and generating trading signals** on OANDA practice account. All core infrastructure and agent services are implemented, running, and capable of automated trade execution:

**Current Status (as of 2025-09-22):**
- **Trading Enabled**: ✅ Active with ENABLE_TRADING=true
- **Advanced Features**: ✅ Session-targeted trading with instant rollback capability
- **Session Detection**: ✅ GMT-based trading session optimization (Sydney, Tokyo, London, NY, Overlap)
- **Pattern Recognition**: ✅ Comprehensive recalibration with backtest validation suite
- **Signal Optimization**: ✅ Enhanced execution pipeline with comprehensive improvements
- **All 8 Agents Connected**: 100% healthy with optimized response times
- **OANDA Data Integration**: ✅ Real-time live account data with enhanced signal processing
- **Trading Session Analysis**: ✅ Complete system with session-specific parameter optimization

### ✅ **Fully Operational - All Services Running:**

**Core Infrastructure:**
- **Orchestrator Service** (Port 8089) - Trading orchestration with ENABLE_TRADING=true
- **Circuit Breaker Agent** (Port 8084) - Real-time safety monitoring with comprehensive risk thresholds
- **Execution Engine** (Port 8082) - Order placement and trade execution with paper/live trading modes  
- **Dashboard** (Port 3003) - Next.js monitoring interface with real-time health monitoring

**Complete 8-Agent AI Ecosystem:**
- **Market Analysis** (Port 8001) - Market scanning, signal generation, trend analysis
- **Strategy Analysis** (Port 8002) - Performance tracking and regime detection
- **Parameter Optimization** (Port 8003) - Risk parameter tuning and optimization
- **Learning Safety** (Port 8004) - Circuit breakers, anomaly detection, rollback systems
- **Disagreement Engine** (Port 8005) - Decision disagreement system for risk diversification
- **Data Collection** (Port 8006) - Pipeline metrics tracking and data management
- **Continuous Improvement** (Port 8007) - Performance analysis and gradual rollout
- **Pattern Detection** (Port 8008) - Wyckoff patterns and VPA analysis

**Live Trading Infrastructure:**
- **OANDA Integration** - ✅ **LIVE** practice account connectivity and automated trade execution
- **Signal-to-Trade Pipeline** - ✅ **ACTIVE** end-to-end automated trading from signal generation to order placement
- **Real Trade Execution** - ✅ **CONFIRMED** system placing actual trades with stop-loss and take-profit orders
- **Position Management** - ✅ **OPERATIONAL** automated position monitoring and exit condition management
- **Safety Infrastructure** - Multi-layer circuit breakers and emergency controls
- **Emergency Stop Systems** - Automated position closing and system halt mechanisms
- **Real-time Monitoring** - Dashboard health checks and system status tracking

### 📋 **Documentation:**
- Project Brief (docs/brief.md) - Complete system vision and requirements
- Product Requirements Document (docs/prd.md) - Detailed technical and functional requirements
- Brainstorming session results (docs/brainstorming-session-results.md)

## Architecture Implementation

**Production Architecture (Fully Deployed):**
- **Monorepo structure**: `/agents`, `/execution-engine`, `/dashboard`, `/orchestrator` - ✅ **FULLY OPERATIONAL**
- **Event-driven microservices** with 8 specialized AI agents - ✅ **ALL AGENTS RUNNING**
- **Python 3.11+ with FastAPI** for all services - ✅ **PRODUCTION READY**
- **Next.js 14+ with TypeScript** for dashboard - ✅ **LIVE MONITORING**  
- **OANDA REST API integration** for trade execution - ✅ **CONNECTED & ACTIVE**
- **Real-time monitoring** and circuit breaker patterns - ✅ **100% OPERATIONAL**
- **Health monitoring system** for all 11 services - ✅ **ACTIVE MONITORING**

**Planned Extensions:**
- **CrewAI** for enhanced agent orchestration
- **Rust/Go execution engine** for <100ms critical path performance  
- **PostgreSQL 15+** for transactional data, **TimescaleDB** for market data
- **Kafka/NATS** for inter-agent communication
- **MetaTrader 4/5 integration** expansion

## Recent Major Enhancements (September 2025)

### Reversible Session-Targeted Trading System (LATEST)
- **Feature**: Complete session-targeted trading with instant rollback capability
- **Implementation**: TradingSession enum with 5 sessions (Sydney, Tokyo, London, NY, Overlap)
- **Capability**: Zero-downtime switching between session-targeted and universal modes
- **Benefits**: Session-optimized parameters with proven risk-reward ratios per session
- **Safety**: Instant rollback to universal Cycle 4 configuration via toggle switch

### Comprehensive Trading Session Analysis (NEW)
- **Feature**: Complete trading session analysis system with GMT/UTC timezone handling
- **Implementation**: Session-specific confidence thresholds and risk-reward requirements
- **Optimization**: London (72% confidence, 3.2 R:R), NY (70%, 2.8 R:R), Tokyo (85%, 4.0 R:R)
- **Integration**: Real-time session detection with dynamic parameter application

### Backtest Validation Suite for Pattern Recognition (NEW)
- **Feature**: Comprehensive validation suite for pattern recognition improvements
- **Implementation**: Enhanced pattern detection with rigorous backtesting framework
- **Validation**: Systematic testing of pattern recognition algorithms against historical data
- **Quality Assurance**: Ensures pattern detection accuracy before live deployment

### Pattern Recognition & Risk Management Recalibration (NEW)
- **Feature**: Comprehensive recalibration of pattern recognition and risk management
- **Enhancement**: Improved accuracy in Wyckoff methodology and VPA analysis
- **Risk Management**: Enhanced stop-loss and take-profit calculation algorithms
- **Performance**: Optimized signal quality and execution timing

### Signal Execution Optimization (ENHANCED)
- **Feature**: Comprehensive signal execution optimization improvements
- **Performance**: Enhanced latency and execution speed in signal-to-trade pipeline
- **Reliability**: Improved error handling and recovery mechanisms
- **Monitoring**: Enhanced logging and performance metrics tracking

## Key Technical Challenges

1. **Multi-Agent Coordination**: 8 AI agents must collaborate through event-driven messaging
2. **Sub-100ms Latency**: Signal-to-execution pipeline requires ultra-low latency
3. **Compliance Engine**: Real-time validation against varying prop firm rules
4. **Anti-Detection System**: Trading personalities and variance to avoid AI detection
5. **Learning Circuit Breakers**: Preventing adaptation during suspicious market conditions
6. **99.5% Uptime Requirement**: Mission-critical availability for live trading

## Security & Compliance Requirements

- End-to-end encryption for all data transmission
- API key encryption at rest using HashiCorp Vault
- 7-year audit trail retention
- SOC 2 Type II compliance roadmap
- GDPR compliance for EU users
- Legal entity separation per trading account

## Development Notes & Current System

**✅ Production Safety Infrastructure:**
- ✅ Complete safety and compliance infrastructure operational
- ✅ Multi-layer circuit breakers implemented across all agents
- ✅ Real-time risk monitoring with automatic emergency detection
- ✅ Emergency stop mechanisms with automated position closing
- ✅ Comprehensive health monitoring for all 11 services
- ✅ Paper trading validation capabilities integrated
- ✅ Learning safety systems with rollback capabilities
- ✅ Anomaly detection and manual override systems

**🔥 Advanced Live Trading Operations:**
- **SESSION-TARGETED TRADING**: Advanced session-specific optimization with instant rollback capability
- **PATTERN RECOGNITION**: Enhanced Wyckoff methodology with comprehensive recalibration
- **SIGNAL OPTIMIZATION**: Improved execution pipeline with comprehensive performance enhancements
- **BACKTEST VALIDATION**: Rigorous testing framework ensuring pattern recognition accuracy
- **DYNAMIC PARAMETERS**: Real-time session detection with GMT-based parameter optimization
- **Trade Execution**: Confirmed successful market order placement with enhanced stop-loss and take-profit
- **Signal Pipeline**: Enhanced Market Analysis → Orchestrator → Execution Engine → OANDA → Live Trades
- **Position Monitoring**: Real-time position tracking with session-optimized exit conditions
- **Risk Management**: Multi-layer circuit breakers and enhanced safety systems

**📊 Enhanced System Status:**
- ✅ All 11 core services operational and healthy with optimized performance
- ✅ Complete 8-agent AI ecosystem with advanced session-targeted trading
- ✅ **ENHANCED LIVE TRADING** - Session-optimized orders with instant rollback capability
- ✅ Advanced signal pipeline with comprehensive optimization and backtest validation
- ✅ Multi-layer emergency controls and enhanced circuit breakers active
- ✅ Real-time dashboard monitoring with session-specific performance tracking
- ✅ Advanced OANDA integration with session-targeted parameter optimization
- ✅ **NEW**: Reversible session-targeted trading system with zero-downtime switching
- ✅ **NEW**: Comprehensive pattern recognition recalibration with validation suite
- ✅ **NEW**: Enhanced signal execution optimization with improved performance metrics

## MVP Implementation Status

**🚀 MVP FULLY COMPLETED & LIVE TRADING OPERATIONAL:**
1. **✅ LIVE AUTOMATED TRADING** - System actively placing real trades on OANDA practice account
2. **✅ Complete signal-to-trade pipeline** - End-to-end automation from signal generation to order execution
3. **✅ Real trade confirmation** - Verified successful market orders with stop-loss/take-profit placement
4. **Complete safety & compliance foundation** - All circuit breakers and emergency systems operational
5. **Multi-account support** - OANDA integration supporting multiple prop firm accounts
6. **Full trade execution engine** - Paper and live trading with comprehensive order management
7. **Real-time monitoring dashboard** - Complete Next.js interface with live health monitoring
8. **Orchestrator service** - Central coordination of all trading signals and execution
9. **Emergency safety systems** - Multi-layer circuit breakers, emergency stops, and position monitoring
10. **Complete 8-agent AI ecosystem** - All specialized agents running with full capabilities
11. **Advanced signal processing** - Pattern detection, market analysis, and trading intelligence
12. **Automated emergency controls** - Position closing and system halt mechanisms
13. **Learning safety systems** - Anomaly detection, rollback capabilities, and data quarantine
14. **Disagreement engine** - Risk diversification through decision disagreement protocols

**🔄 Post-MVP Enhancement Features (Recently Implemented & Future):**

**✅ Recently Implemented (September 2025):**
- ✅ **Session-Targeted Trading System** - Complete implementation with instant rollback
- ✅ **Advanced Pattern Recognition** - Comprehensive recalibration with backtest validation
- ✅ **Signal Execution Optimization** - Enhanced performance and reliability improvements
- ✅ **Trading Session Analysis** - GMT-based session detection with optimized parameters
- ✅ **Backtest Validation Suite** - Rigorous testing framework for pattern accuracy

**🔄 Future Development Pipeline:**
- Advanced learning capabilities and continuous AI adaptation
- Support for additional prop firms and trading platforms
- Institutional-grade analytics and comprehensive reporting
- Advanced personality engines for trading pattern variance
- Real-time performance optimization and parameter tuning
- Enhanced multi-timeframe analysis integration
- Advanced risk management with machine learning adaptation

## Important Warnings

This system involves:
- Real financial risk and potential for significant losses
- Complex regulatory compliance requirements
- Potential liability for automated trading decisions
- Need for proper legal structure and disclosures
- High-stakes production environment (99.5% uptime requirement)

Any implementation must prioritize safety, compliance, and risk management above all other considerations.

## Current System Services

**All Production Services Running:**

**Core Infrastructure:**
- **Orchestrator**: `http://localhost:8089` - Trading orchestration with auto-enable trading
- **Circuit Breaker**: `http://localhost:8084` - Risk monitoring and emergency management
- **Execution Engine**: `http://localhost:8082` - Trade execution with paper/live modes
- **Dashboard**: `http://localhost:3003` - Real-time monitoring and control interface

**Complete AI Agent Ecosystem:**
- **Market Analysis**: `http://localhost:8001` - Market scanning and signal generation
- **Strategy Analysis**: `http://localhost:8002` - Performance tracking and regime detection
- **Parameter Optimization**: `http://localhost:8003` - Risk parameter optimization
- **Learning Safety**: `http://localhost:8004` - Safety systems and anomaly detection
- **Disagreement Engine**: `http://localhost:8005` - Decision disagreement protocols
- **Data Collection**: `http://localhost:8006` - Pipeline metrics and data management
- **Continuous Improvement**: `http://localhost:8007` - Performance analysis and rollout
- **Pattern Detection**: `http://localhost:8008` - Wyckoff patterns and VPA analysis

**Production Startup (All Services):**
```bash
# Core Infrastructure
cd execution-engine && PORT=8082 python simple_main.py &
cd orchestrator && OANDA_API_KEY=your_key OANDA_ACCOUNT_IDS=your_account ENABLE_TRADING=true PORT=8089 python -m app.main &
cd agents/circuit-breaker && OANDA_API_KEY=your_key OANDA_ACCOUNT_ID=your_account PORT=8084 python main.py &
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

**Complete System Health Monitoring:**
- Core Services: `http://localhost:8082,8084,8089/health`
- AI Agents: `http://localhost:8001-8008/health`
- Dashboard: `http://localhost:3003` (with real-time health monitoring)
- All services monitored via dashboard with green/red status indicators

## 🎯 ENHANCED LIVE TRADING STATUS (Updated: 2025-09-22)

**System is LIVE with advanced session-targeted trading on OANDA practice account:**

### Current Advanced Trading Features:
- **✅ Session-Targeted Trading**: Active with instant rollback capability and 5-session optimization
- **✅ Enhanced Pattern Recognition**: Comprehensive recalibration with backtest validation suite
- **✅ Optimized Signal Pipeline**: Enhanced Market Analysis → Orchestrator → Execution Engine → OANDA
- **✅ GMT-Based Session Detection**: Real-time session optimization (Sydney, Tokyo, London, NY, Overlap)
- **✅ Dynamic Parameters**: Session-specific confidence thresholds and risk-reward ratios
- **✅ Advanced Markets Monitored**: EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CHF with session optimization

### Current Enhanced Configuration:
- **Session-Specific Generation**: Advanced scanning with session-optimized pattern detection
- **Dynamic Confidence Thresholds**:
  - Tokyo: 85% confidence (4.0 R:R)
  - London: 72% confidence (3.2 R:R)
  - New York: 70% confidence (2.8 R:R)
  - Sydney: 78% confidence (3.5 R:R)
  - Overlap: 70% confidence (2.8 R:R)
- **Enhanced Pattern Detection**: Recalibrated Wyckoff methodology with comprehensive VPA
- **Advanced Risk Management**: Optimized stop-loss and take-profit with session parameters
- **Real-time Monitoring**: Session-aware position tracking with instant rollback capability

### Advanced Trading Configuration:
- **Session-Targeted Mode**: ✅ Active with zero-downtime switching capability
- **Rollback Safety**: ✅ Instant return to universal Cycle 4 configuration available
- **Backtest Validation**: ✅ All pattern recognition improvements validated against historical data
- **Signal Optimization**: ✅ Enhanced execution pipeline with comprehensive performance improvements
- **Trading Mode**: Fully automated with advanced session optimization and manual override

**⚠️ IMPORTANT**: System continues using OANDA practice/demo account for safe testing of advanced features. All session-targeted trading and optimizations are being validated with virtual money before live deployment authorization.