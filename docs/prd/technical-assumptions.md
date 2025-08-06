# Technical Assumptions

## Repository Structure: Monorepo

We'll use a monorepo structure with clear separation: `/agents` for the 8 AI services, `/execution-engine` for critical trading logic, `/dashboard` for the web interface, `/shared` for common utilities, `/ml-models` for trained models, and `/infrastructure` for deployment configs.

## Service Architecture: Microservices

Event-driven microservices architecture allows each of the 8 agents to operate independently while collaborating through message queues. This provides fault isolation - if one agent fails, others continue operating. We'll use Kafka/NATS for event streaming between agents.

## Testing Requirements: Full Testing Pyramid

Given the financial risk and compliance requirements, we need comprehensive testing: unit tests for all agent logic, integration tests for inter-agent communication, end-to-end tests simulating full trading scenarios, and continuous paper trading as a form of production testing. Manual testing convenience methods will allow traders to validate specific scenarios.

## Additional Technical Assumptions and Requests

- **Languages & Frameworks:** Python 3.11+ with FastAPI for agent services, CrewAI for agent orchestration, Next.js 14+ with TypeScript for dashboard, Rust/Go for execution engine (<10ms critical path)
- **Database Strategy:** PostgreSQL 15+ for transactional data, TimescaleDB for time-series market data, Redis for real-time state and caching
- **Deployment Target:** Initial development on DigitalOcean/Vultr VPS, production on Google Cloud Platform with multi-region deployment for redundancy
- **API Integrations:** MetaTrader 4/5 bridge for trade execution, FIX protocol support for institutional brokers, REST/WebSocket APIs for market data (OANDA, Polygon.io)
- **Security Requirements:** HashiCorp Vault for secrets management, end-to-end TLS encryption, API key rotation every 90 days
- **Performance Targets:** <100ms signal-to-execution, 1000+ price updates/second processing, 50+ concurrent WebSocket connections
- **Development Workflow:** GitHub with protected main branch, CI/CD via GitHub Actions, automated testing on every PR, staging environment matching production
- **Monitoring & Observability:** OpenTelemetry for distributed tracing, Prometheus/Grafana for metrics, centralized logging with 30-day retention
- **Disaster Recovery:** 15-minute RTO, 1-hour RPO, automated backups every 4 hours, multi-region failover capability
