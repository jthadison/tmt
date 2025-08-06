# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Adaptive/Continuous Learning Autonomous Trading System - a sophisticated AI platform for prop firm traders. The system uses 8 specialized AI agents to manage multiple prop firm accounts simultaneously, employing Wyckoff methodology with Volume Price Analysis and Smart Money Concepts while maintaining compliance and avoiding detection.

## Project Status

This is currently a documentation-only project in the planning phase. No code implementation exists yet. The repository contains comprehensive project documentation including:
- Project Brief (docs/brief.md) - Complete system vision and requirements
- Product Requirements Document (docs/prd.md) - Detailed technical and functional requirements
- Brainstorming session results (docs/brainstorming-session-results.md)

## Architecture Vision

The planned system will use:
- **Monorepo structure**: `/agents`, `/execution-engine`, `/dashboard`, `/shared`, `/ml-models`, `/infrastructure`
- **Event-driven microservices** with 8 specialized AI agents
- **Python 3.11+ with FastAPI** for agent services
- **CrewAI** for agent orchestration
- **Rust/Go execution engine** for <100ms critical path performance
- **Next.js 14+ with TypeScript** for dashboard
- **PostgreSQL 15+** for transactional data, **TimescaleDB** for market data
- **Kafka/NATS** for inter-agent communication
- **MetaTrader 4/5 integration** for trade execution

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

## Development Notes

When implementing this system:
- Prioritize safety and compliance infrastructure first
- Implement comprehensive circuit breakers at agent, account, and system levels
- All trading decisions must be logged with audit trails
- Focus on defensive coding practices due to financial risk
- Extensive testing required including paper trading validation
- Consider regulatory implications in all design decisions

## MVP Scope (16 weeks)

The MVP focuses on:
1. Safety & compliance foundation (Circuit Breaker Agent)
2. Basic Wyckoff pattern detection
3. Single/multi-account support (up to 3 accounts)
4. MetaTrader integration
5. Basic personality engine for variance
6. Web dashboard for monitoring

Advanced features (full learning capabilities, 10+ prop firms, institutional-grade analytics) are post-MVP.

## Important Warnings

This system involves:
- Real financial risk and potential for significant losses
- Complex regulatory compliance requirements
- Potential liability for automated trading decisions
- Need for proper legal structure and disclosures
- High-stakes production environment (99.5% uptime requirement)

Any implementation must prioritize safety, compliance, and risk management above all other considerations.