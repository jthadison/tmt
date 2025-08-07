# Adaptive Trading System

A sophisticated AI-powered trading platform using 8 specialized agents to manage multiple prop firm accounts simultaneously, employing Wyckoff methodology with Volume Price Analysis and Smart Money Concepts.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11.8** or higher
- **Node.js 20.11.0** (LTS) or higher  
- **Rust 1.75.0** or higher
- **Docker 25.0.3** or higher
- **Docker Compose** v2 or higher

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd adaptive-trading-system
   ```

2. **Run setup script:**
   ```bash
   ./scripts/setup/install-dependencies.sh
   ```

3. **Start development environment:**
   ```bash
   docker-compose up -d
   ```

4. **Verify installation:**
   ```bash
   ./scripts/setup/system-health-check.sh
   ```

## 🏗️ Architecture

### Monorepo Structure

```
├── agents/                 # AI agent microservices (Python/FastAPI)
├── execution-engine/       # High-performance execution engine (Rust)
├── dashboard/             # Trading dashboard (Next.js/TypeScript)
├── shared/                # Shared libraries and utilities
├── ml-models/             # Machine learning components
├── infrastructure/        # Infrastructure as Code (Terraform, K8s, Helm)
└── scripts/              # Automation scripts
```

### Technology Stack

- **Languages:** Python 3.11.8, Rust 1.75.0, TypeScript 5.3.3
- **Frameworks:** FastAPI, Next.js 14.1.0, CrewAI 0.28.8
- **Databases:** PostgreSQL 15.6 + TimescaleDB 2.14.2, Redis 7.2.4
- **Messaging:** Apache Kafka 3.6.1
- **Monitoring:** Prometheus 2.49.1, Grafana 10.3.3
- **Cloud:** Google Cloud Platform (GKE, Cloud SQL)

## 🤖 AI Agents

1. **Market Analysis Agent** - Wyckoff pattern detection & signal generation
2. **Risk Management Agent (ARIA)** - Adaptive position sizing & risk controls
3. **Personality Engine** - Trading variance & anti-detection
4. **Circuit Breaker Agent** - Three-tier safety system
5. **Learning Agent** - Strategy optimization & adaptation
6. **Compliance Agent** - Prop firm rule enforcement
7. **Execution Coordinator** - Trade orchestration
8. **Performance Monitor** - Real-time analytics

## 🔒 Security & Compliance

- End-to-end encryption for all data transmission
- API keys encrypted at rest using HashiCorp Vault
- 7-year audit trail retention
- SOC 2 Type II compliance roadmap
- GDPR compliance for EU users

## 📊 Performance Requirements

- **Latency:** <100ms signal-to-execution
- **Uptime:** 99.5% availability requirement
- **Capacity:** Support 10+ prop firm accounts
- **Throughput:** Handle high-frequency trading signals

## 🧪 Development

### Running Tests

```bash
# Python tests
pytest agents/

# TypeScript tests  
cd dashboard && npm test

# Rust tests
cd execution-engine && cargo test

# Integration tests
./scripts/testing/run-integration-tests.sh
```

### Code Standards

- **Python:** Black 24.2.0 formatting, type hints required
- **TypeScript:** ESLint 8.56.0 + Prettier, strict mode
- **Rust:** rustfmt default configuration
- **Commits:** Conventional commits with pre-commit hooks

### Local Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access services
# Dashboard: http://localhost:3000
# API Gateway: http://localhost:8000
# Grafana: http://localhost:3001
```

## 🚨 Important Warnings

⚠️ **This system involves real financial risk and potential for significant losses.**

- Complex regulatory compliance requirements
- Potential liability for automated trading decisions  
- Need for proper legal structure and disclosures
- High-stakes production environment (99.5% uptime requirement)

**Any implementation must prioritize safety, compliance, and risk management above all other considerations.**

## 📖 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Documentation](docs/api/)
- [Deployment Guide](docs/deployment/)
- [Trading Strategy](docs/trading/)
- [Runbooks](docs/runbooks/)

## 🤝 Contributing

1. Read [Contributing Guidelines](docs/CONTRIBUTING.md)
2. Follow coding standards and pre-commit hooks
3. Include comprehensive tests
4. Update documentation as needed

## 📄 License

[License to be determined]

## 📞 Support

For technical issues, please refer to:
- [Troubleshooting Guide](docs/runbooks/troubleshooting.md)
- [Incident Response](docs/runbooks/incident-response.md)

---

**Status:** Documentation-only project in planning phase. No code implementation exists yet.