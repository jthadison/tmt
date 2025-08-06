# Tech Stack

## Cloud Infrastructure
- **Provider:** Google Cloud Platform
- **Key Services:** GKE (Kubernetes), Cloud SQL, Pub/Sub, Secret Manager
- **Deployment Regions:** us-central1 (primary), us-east1 (failover)

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **Language** | Python | 3.11.8 | AI agents, API services | Stable LTS, extensive ML ecosystem, CrewAI compatibility |
| **Language** | Rust | 1.75.0 | Execution engine | Guaranteed memory safety, <100ms latency requirements |
| **Language** | TypeScript | 5.3.3 | Frontend, shared types | Type safety, team productivity, ecosystem maturity |
| **Runtime** | Node.js | 20.11.0 | Dashboard backend | LTS version, proven stability, extensive ecosystem |
| **AI Framework** | CrewAI | 0.28.8 | Agent orchestration | Multi-agent coordination, as specified in PRD |
| **Backend Framework** | FastAPI | 0.109.1 | Python API services | High performance, automatic docs, async support |
| **Frontend Framework** | Next.js | 14.1.0 | Trading dashboard | Server-side rendering, excellent DX, proven at scale |
| **Database** | PostgreSQL | 15.6 | Transactional data | ACID compliance, proven reliability for financial data |
| **Time-Series DB** | TimescaleDB | 2.14.2 | Market data storage | PostgreSQL extension, optimized for time-series |
| **Cache/State** | Redis | 7.2.4 | Real-time state, sessions | Sub-millisecond latency, battle-tested |
| **Message Queue** | Apache Kafka | 3.6.1 | Event streaming | Durability guarantees, exactly-once semantics |
| **Monitoring** | Prometheus | 2.49.1 | Metrics collection | Industry standard, extensive ecosystem |
| **Visualization** | Grafana | 10.3.3 | Dashboards, alerting | Proven monitoring solution |
| **Secrets** | HashiCorp Vault | 1.15.6 | Secrets management | Enterprise-grade security, as specified in PRD |
| **Container** | Docker | 25.0.3 | Application packaging | Industry standard, proven stability |
| **Orchestration** | Kubernetes | 1.29.1 | Container orchestration | Battle-tested, Google Cloud native |
| **Testing** | pytest | 8.0.1 | Python testing | Most mature Python testing framework |
| **Testing** | Jest | 29.7.0 | JavaScript testing | React/Next.js standard, extensive mocking |
| **Linting** | Black | 24.2.0 | Python formatting | Deterministic, zero-config |
| **Linting** | ESLint | 8.56.0 | TypeScript/JS linting | Industry standard, extensive rules |
