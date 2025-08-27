# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Adaptive/Continuous Learning Autonomous Trading System - a sophisticated AI platform for prop firm traders. The system uses 8 specialized AI agents to manage multiple prop firm accounts simultaneously, employing Wyckoff methodology with Volume Price Analysis and Smart Money Concepts while maintaining compliance and avoiding detection.

## Project Status

**PRODUCTION READY - MVP FULLY OPERATIONAL**

The system is now fully operational with complete 8-agent AI trading ecosystem running in production. All core infrastructure and agent services are implemented and actively running:

### ✅ **Fully Operational - All Services Running:**

**Core Infrastructure:**
- **Orchestrator Service** (Port 8083) - Trading orchestration and signal processing
- **Circuit Breaker Agent** (Port 8084) - Real-time safety monitoring with comprehensive risk thresholds
- **Execution Engine** (Port 8082) - Order placement and trade execution with paper/live trading modes  
- **Dashboard** (Port 3000) - Next.js monitoring interface with real-time health monitoring

**Complete 8-Agent AI Ecosystem:**
- **Market Analysis** (Port 8001) - Market scanning, signal generation, trend analysis
- **Strategy Analysis** (Port 8002) - Performance tracking and regime detection
- **Parameter Optimization** (Port 8003) - Risk parameter tuning and optimization
- **Learning Safety** (Port 8004) - Circuit breakers, anomaly detection, rollback systems
- **Disagreement Engine** (Port 8005) - Decision disagreement system for risk diversification
- **Data Collection** (Port 8006) - Pipeline metrics tracking and data management
- **Continuous Improvement** (Port 8007) - Performance analysis and gradual rollout
- **Pattern Detection** (Port 8008) - Wyckoff patterns and VPA analysis

**Additional Systems:**
- **OANDA Integration** - Live practice account connectivity and position management
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

**🎯 Current Operational Focus:**
- System monitoring and performance optimization
- Enhanced signal generation and pattern recognition
- Advanced learning capabilities and AI adaptation
- Regulatory compliance validation and documentation
- Real-time system health and performance tracking

**📊 System Status:**
- ✅ All 11 core services operational and healthy
- ✅ Complete 8-agent AI ecosystem running
- ✅ Emergency controls and circuit breakers active
- ✅ Real-time dashboard monitoring all systems
- ✅ OANDA integration connected and functional

## MVP Implementation Status

**✅ MVP Fully Completed & Operational:**
1. **Complete safety & compliance foundation** - All circuit breakers and emergency systems operational
2. **Multi-account support** - OANDA integration supporting multiple prop firm accounts
3. **Full trade execution engine** - Paper and live trading with comprehensive order management
4. **Real-time monitoring dashboard** - Complete Next.js interface with live health monitoring
5. **Orchestrator service** - Central coordination of all trading signals and execution
6. **Emergency safety systems** - Multi-layer circuit breakers, emergency stops, and position monitoring
7. **Complete 8-agent AI ecosystem** - All specialized agents running with full capabilities
8. **Advanced signal processing** - Pattern detection, market analysis, and trading intelligence
9. **Automated emergency controls** - Position closing and system halt mechanisms
10. **Learning safety systems** - Anomaly detection, rollback capabilities, and data quarantine
11. **Disagreement engine** - Risk diversification through decision disagreement protocols

**🚀 Production Enhancement Features (Active Development):**
- Advanced learning capabilities and continuous AI adaptation
- Support for additional prop firms and trading platforms
- Institutional-grade analytics and comprehensive reporting
- Enhanced Wyckoff methodology and volume price analysis
- Advanced personality engines for trading pattern variance
- Real-time performance optimization and parameter tuning

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
- **Orchestrator**: `http://localhost:8083` - Trading orchestration and signal processing
- **Circuit Breaker**: `http://localhost:8084` - Risk monitoring and emergency management
- **Execution Engine**: `http://localhost:8082` - Trade execution with paper/live modes
- **Dashboard**: `http://localhost:3000` - Real-time monitoring and control interface

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
cd orchestrator && OANDA_API_KEY=your_key OANDA_ACCOUNT_IDS=your_account PORT=8083 python -m app.main &
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
- Core Services: `http://localhost:8082-8084/health`
- AI Agents: `http://localhost:8001-8008/health`
- Dashboard: `http://localhost:3000` (with real-time health monitoring)
- All services monitored via dashboard with green/red status indicators