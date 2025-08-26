# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Adaptive/Continuous Learning Autonomous Trading System - a sophisticated AI platform for prop firm traders. The system uses 8 specialized AI agents to manage multiple prop firm accounts simultaneously, employing Wyckoff methodology with Volume Price Analysis and Smart Money Concepts while maintaining compliance and avoiding detection.

## Project Status

**ACTIVE DEVELOPMENT - MVP IMPLEMENTATION IN PROGRESS**

The system is currently in active development with core autonomous trading infrastructure implemented and running. Current implementation status:

### ✅ **Implemented & Running:**
- **Orchestrator Service** (Port 8083) - Core trading orchestration and signal processing
- **Circuit Breaker Agent** (Port 8084) - Real-time safety monitoring with comprehensive risk thresholds
- **Execution Engine** (Port 8082) - Order placement and trade execution with paper/live trading modes  
- **Dashboard** (Port 3000) - Next.js monitoring interface
- **OANDA Integration** - Live practice account connectivity and position management
- **Safety Infrastructure** - Multi-layer circuit breakers and risk management
- **Agent Architecture** - Event-driven microservices foundation established

### 🚧 **In Development:**
- Emergency stop mechanisms and position closing automation
- Missing agent components (disagreement-engine, parameter-optimization)
- Enhanced trading intelligence and signal optimization
- Comprehensive logging and audit trails

### 📋 **Documentation:**
- Project Brief (docs/brief.md) - Complete system vision and requirements
- Product Requirements Document (docs/prd.md) - Detailed technical and functional requirements
- Brainstorming session results (docs/brainstorming-session-results.md)

## Architecture Implementation

**Current Architecture (Implemented):**
- **Monorepo structure**: `/agents`, `/execution-engine`, `/dashboard`, `/orchestrator` - ✅ **IMPLEMENTED**
- **Event-driven microservices** with specialized agents - ✅ **CORE SERVICES RUNNING**
- **Python 3.11+ with FastAPI** for all services - ✅ **IMPLEMENTED**
- **Next.js 14+ with TypeScript** for dashboard - ✅ **IMPLEMENTED**  
- **OANDA REST API integration** for trade execution - ✅ **IMPLEMENTED**
- **Real-time monitoring** and circuit breaker patterns - ✅ **IMPLEMENTED**

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

**✅ Implemented Safety Measures:**
- ✅ Safety and compliance infrastructure prioritized and operational
- ✅ Comprehensive circuit breakers implemented at multiple levels  
- ✅ Real-time risk monitoring and automatic emergency detection
- ✅ Defensive coding practices with extensive error handling
- ✅ Paper trading validation capabilities integrated

**🚧 Current Development Focus:**
- Emergency stop automation and position closing mechanisms
- Enhanced audit trail logging and trade decision tracking
- Complete agent ecosystem implementation
- Regulatory compliance validation and documentation

**⚠️ Active System Warnings:**
- Circuit breaker detecting position concentration issues (138.6% of balance)
- Emergency stop endpoint missing - high priority safety fix needed
- Position closing automation incomplete - manual intervention may be required

## MVP Implementation Status

**✅ MVP Core Components Completed:**
1. **Safety & compliance foundation** - Circuit Breaker Agent fully operational with real-time risk monitoring
2. **Multi-account support** - OANDA integration supporting multiple prop firm accounts
3. **Trade execution engine** - Paper and live trading capabilities with order management
4. **Web dashboard** - Next.js monitoring interface for system oversight
5. **Orchestrator service** - Central coordination of trading signals and execution
6. **Emergency safety systems** - Multi-layer circuit breakers and position monitoring

**🚧 MVP Components In Progress:**
1. **Enhanced signal processing** - Pattern detection and trading intelligence
2. **Agent ecosystem completion** - Disagreement engine and parameter optimization
3. **Emergency automation** - Automated position closing and system halt mechanisms

**📋 Post-MVP Features (Planned):**
- Advanced learning capabilities and AI adaptation
- Support for 10+ prop firms and trading platforms
- Institutional-grade analytics and reporting
- Full Wyckoff methodology implementation
- Advanced personality engines for trading variance

## Important Warnings

This system involves:
- Real financial risk and potential for significant losses
- Complex regulatory compliance requirements
- Potential liability for automated trading decisions
- Need for proper legal structure and disclosures
- High-stakes production environment (99.5% uptime requirement)

Any implementation must prioritize safety, compliance, and risk management above all other considerations.

## Current System Services

**Running Services:**
- **Orchestrator**: `http://localhost:8083` - Trading signal coordination and execution management
- **Circuit Breaker**: `http://localhost:8084` - Real-time risk monitoring and emergency management
- **Execution Engine**: `http://localhost:8082` - Trade execution with paper/live trading modes
- **Dashboard**: `http://localhost:3000` - Web-based monitoring and control interface

**Quick Start:**
```bash
# Terminal 1 - Execution Engine
cd execution-engine && PORT=8082 python simple_main.py

# Terminal 2 - Orchestrator  
cd orchestrator && OANDA_API_KEY=your_key OANDA_ACCOUNT_IDS=your_account PORT=8083 python -m app.main

# Terminal 3 - Circuit Breaker
cd agents/circuit-breaker && OANDA_API_KEY=your_key OANDA_ACCOUNT_ID=your_account PORT=8084 python main.py

# Terminal 4 - Dashboard
cd dashboard && npm run dev
```

**System Health Check:**
- Orchestrator: `GET http://localhost:8083/health`
- Circuit Breaker: `GET http://localhost:8084/health`  
- Execution Engine: `GET http://localhost:8082/health`
- Dashboard: `GET http://localhost:3000`