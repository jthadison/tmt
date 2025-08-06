# Next Steps

## UX Expert Prompt

Please review the attached PRD (docs/prd.md) for the Adaptive/Continuous Learning Autonomous Trading System and create comprehensive UX/UI designs. Focus on the dashboard interface that enables traders to monitor multiple prop firm accounts with "glanceable compliance" - instant visual assessment of account health, risk status, and rule compliance. Design for desktop-first (1920x1080) with dark mode default, incorporating traffic light status indicators and one-click emergency controls. The interface must balance information density for professional traders with clarity to reduce cognitive load during extended monitoring sessions.

## Architect Prompt

Please review the attached PRD (docs/prd.md) for the Adaptive/Continuous Learning Autonomous Trading System and create a detailed technical architecture. Design an event-driven microservices architecture supporting 8 specialized AI agents using Python/FastAPI with CrewAI orchestration, a Rust/Go execution engine for <100ms latency, and Next.js dashboard. Address critical technical challenges: multi-agent coordination via Kafka/NATS, MetaTrader 4/5 integration, three-tier circuit breaker implementation, and anti-correlation engine for detection avoidance. Ensure the architecture supports 99.5% uptime, processes 1000+ price updates/second, and maintains complete audit trails. Pay special attention to the learning circuit breaker system that prevents adaptation during suspicious market conditions.