# Adaptive Trading System

[![CI Pipeline](https://github.com/jthadison/tmt/workflows/CI%20Pipeline/badge.svg)](https://github.com/jthadison/tmt/actions/workflows/ci.yml)
[![Staging Deployment](https://github.com/jthadison/tmt/workflows/Staging%20Deployment/badge.svg)](https://github.com/jthadison/tmt/actions/workflows/staging-deploy.yml)
[![codecov](https://codecov.io/gh/jthadison/tmt/branch/main/graph/badge.svg)](https://codecov.io/gh/jthadison/tmt)
[![Security Scan](https://img.shields.io/badge/security-semgrep-green)](https://github.com/jthadison/tmt/actions)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Python 3.11.8](https://img.shields.io/badge/python-3.11.8-blue.svg)](https://python.org)
[![TypeScript 5.3.3](https://img.shields.io/badge/typescript-5.3.3-blue.svg)](https://typescriptlang.org)
[![Rust 1.75.0](https://img.shields.io/badge/rust-1.75.0-orange.svg)](https://rust-lang.org)

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

## 🚀 CI/CD Pipeline

### Pipeline Overview

Our CI/CD pipeline ensures code quality, security, and reliable deployments through automated workflows.

#### **Continuous Integration**
- **Triggers:** Pull requests and pushes to `main` branch
- **Multi-language Support:** Python, TypeScript, and Rust testing in parallel
- **Security Scanning:** Semgrep SAST, Trivy vulnerability scanning
- **Code Quality:** 80% test coverage requirement, linting, and formatting checks
- **Build Validation:** Docker image builds for all services

#### **Continuous Deployment**
- **Staging:** Automatic deployment on merge to `main`
- **Production:** Manual approval with blue-green deployment
- **Rollback:** Automated rollback on health check failures

### Workflow Badges

| Workflow | Status | Description |
|----------|--------|-------------|
| CI Pipeline | [![CI Pipeline](https://github.com/jthadison/tmt/workflows/CI%20Pipeline/badge.svg)](https://github.com/jthadison/tmt/actions/workflows/ci.yml) | Runs tests, security scans, and builds |
| Staging Deploy | [![Staging Deployment](https://github.com/jthadison/tmt/workflows/Staging%20Deployment/badge.svg)](https://github.com/jthadison/tmt/actions/workflows/staging-deploy.yml) | Deploys to staging environment |
| Code Coverage | [![codecov](https://codecov.io/gh/jthadison/tmt/branch/main/graph/badge.svg)](https://codecov.io/gh/jthadison/tmt) | Test coverage reporting |

### Pipeline Stages

#### 1. **Security & Quality Gates**
```bash
# Security scanning
- Semgrep SAST (Static Application Security Testing)
- Trivy vulnerability scanning
- Dependency security analysis
- Secret detection

# Code quality
- Multi-language linting (Black, ESLint, Clippy)
- Type checking (mypy, TypeScript, Rust)
- Test coverage enforcement (80% minimum)
```

#### 2. **Testing Strategy**
```bash
# Unit Tests (parallel execution)
- Python: pytest with 80% coverage requirement
- TypeScript: Jest with React Testing Library
- Rust: Built-in test framework with comprehensive coverage

# Integration Tests
- End-to-end API testing
- Database integration tests
- Message queue integration tests
- Cross-service communication tests

# Performance Tests
- k6 load testing (1000 concurrent users)
- Response time validation (<100ms p95)
- Resource usage monitoring
```

#### 3. **Build & Package**
```bash
# Docker builds (parallel)
./scripts/deployment/build-all.sh

# Image security scanning
- Base image vulnerability assessment
- Multi-arch builds (linux/amd64)
- Container optimization and best practices
```

#### 4. **Deployment Pipeline**

##### **Staging Environment**
```bash
# Automatic on main branch merge
./scripts/deployment/deploy-staging.sh

# Infrastructure provisioning
- GKE cluster with PostgreSQL + TimescaleDB
- Redis for caching and real-time state
- Kafka for event streaming
- Monitoring stack (Prometheus + Grafana)

# Application deployment
- Blue-green deployment strategy  
- Health check validation
- Smoke tests execution
- Performance validation
```

##### **Production Environment**
```bash
# Manual approval required
# Canary deployment with gradual traffic shift
# Automated rollback on failure
# Real-time monitoring and alerting
```

### Deployment Environments

| Environment | URL | Purpose | Auto-Deploy |
|-------------|-----|---------|-------------|
| **Development** | `http://localhost:3000` | Local development | Manual |
| **Staging** | `https://staging.trading-system.com` | Pre-production testing | ✅ On merge to main |
| **Production** | `https://trading-system.com` | Live trading system | Manual approval |

### Rollback Capabilities

#### **Automated Rollback Triggers**
- Error rate > 1%
- Response latency > 500ms
- Health check failures
- Circuit breaker activations

#### **Manual Rollback**
```bash
# Emergency rollback workflow
gh workflow run rollback.yml \
  -f environment=staging \
  -f rollback_to=previous-stable-tag \
  -f reason="Critical issue detected"

# Or use deployment script
./scripts/deployment/rollback.sh --environment=staging --to=v1.2.3
```

#### **Recovery Time Objectives**
- **Application Rollback:** <60 seconds
- **Database Rollback:** <5 minutes  
- **Full System Recovery:** <15 minutes

### Monitoring & Observability

#### **Build Metrics**
- Build success rate and duration
- Test execution time and coverage trends
- Security vulnerability trends
- Deployment frequency and lead time

#### **Deployment Health**
- Real-time application metrics
- Infrastructure resource utilization
- Error rates and response times
- Business metrics (trade execution latency)

### CI/CD Best Practices

#### **Pull Request Workflow**
1. **Branch Protection:** `main` branch requires PR reviews and status checks
2. **Automated Checks:** All CI tests must pass before merge
3. **Security Review:** Automated security scanning on every PR
4. **Performance Impact:** Automated performance regression detection

#### **Release Management**
```bash
# Version tagging
git tag -a v1.2.3 -m "Release v1.2.3: Add risk management features"

# Release notes generation
gh release create v1.2.3 --auto-notes --latest

# Deployment validation
./scripts/deployment/validate-release.sh v1.2.3
```

#### **Troubleshooting CI/CD Issues**

| Issue | Solution |
|-------|----------|
| **Build Failures** | Check workflow logs, validate dependencies |
| **Test Failures** | Review test output, check for flaky tests |
| **Security Scan Failures** | Review security report, update dependencies |
| **Deployment Failures** | Check health endpoints, validate configurations |
| **Rollback Issues** | Verify backup integrity, check manual procedures |

For detailed troubleshooting, see [CI/CD Troubleshooting Guide](docs/cicd-troubleshooting.md).

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