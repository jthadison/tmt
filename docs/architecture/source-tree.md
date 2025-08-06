# Source Tree

```
adaptive-trading-system/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # GitHub Actions CI/CD pipeline
│   │   ├── staging-deploy.yml         # Staging deployment
│   │   └── production-deploy.yml      # Production deployment
│   └── PULL_REQUEST_TEMPLATE.md       # PR template with checklist
├── .gitignore                         # Git ignore patterns
├── README.md                          # Project overview and setup
├── docker-compose.yml                 # Local development environment
├── docker-compose.prod.yml            # Production docker compose
├── package.json                       # Root package.json for workspaces
├── yarn.lock                          # Yarn lockfile
├── pyproject.toml                     # Python project configuration
├── .pre-commit-config.yaml            # Pre-commit hooks configuration
├── .env.example                       # Environment variables template
│
├── agents/                            # AI Agents (Python microservices)
│   ├── shared/                        # Shared agent utilities
│   │   ├── __init__.py
│   │   ├── base_agent.py              # Base CrewAI agent class
│   │   ├── kafka_client.py            # Kafka integration
│   │   ├── database.py                # Database connection pool
│   │   ├── vault_client.py            # HashiCorp Vault integration
│   │   └── monitoring.py              # OpenTelemetry instrumentation
│   ├── market-analysis/               # Market Analysis Agent
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                # FastAPI app entry point
│   │   │   ├── agent.py               # CrewAI market analysis agent
│   │   │   ├── wyckoff_detector.py    # Wyckoff pattern detection
│   │   │   ├── volume_analyzer.py     # Volume price analysis
│   │   │   └── signal_generator.py    # Trading signal generation
│   │   └── tests/
│   │       ├── test_wyckoff.py
│   │       ├── test_signals.py
│   │       └── conftest.py
│   ├── risk-management/               # Adaptive Risk Intelligence Agent (ARIA)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── agent.py               # ARIA agent implementation
│   │   │   ├── position_sizer.py      # Dynamic position sizing
│   │   │   ├── risk_calculator.py     # Risk metrics calculation
│   │   │   └── parameter_tuner.py     # Adaptive parameter adjustment
│   │   └── tests/
│   ├── personality-engine/            # Personality Engine Agent
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── agent.py
│   │   │   ├── personality_profiles.py # Personality management
│   │   │   ├── variance_engine.py      # Execution variance
│   │   │   └── correlation_detector.py # Anti-correlation monitoring
│   │   └── tests/
│   ├── circuit-breaker/               # Circuit Breaker Agent
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── agent.py
│   │   │   ├── breaker_logic.py       # Three-tier breaker implementation
│   │   │   ├── health_monitor.py      # System health monitoring
│   │   │   └── emergency_stop.py      # Emergency stop procedures
│   │   └── tests/
│   └── learning/                      # Learning Agent
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── agent.py
│       │   ├── model_trainer.py       # ML model training
│       │   ├── performance_analyzer.py # Strategy analysis
│       │   └── learning_breaker.py    # Learning circuit breaker
│       └── tests/
│
├── execution-engine/                  # High-Performance Execution Engine (Rust)
│   ├── Cargo.toml                     # Rust project configuration
│   ├── Cargo.lock
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.rs                    # Main application entry
│   │   ├── lib.rs                     # Library root
│   │   ├── api/                       # HTTP API endpoints
│   │   │   ├── mod.rs
│   │   │   ├── orders.rs              # Order management endpoints
│   │   │   └── health.rs              # Health check endpoint
│   │   ├── execution/
│   │   │   ├── mod.rs
│   │   │   ├── engine.rs              # Core execution logic
│   │   │   ├── mt4_bridge.rs          # MetaTrader 4 bridge
│   │   │   ├── mt5_bridge.rs          # MetaTrader 5 bridge
│   │   │   └── order_manager.rs       # Order state management
│   │   ├── messaging/
│   │   │   ├── mod.rs
│   │   │   ├── kafka.rs               # Kafka integration
│   │   │   └── events.rs              # Event definitions
│   │   └── utils/
│   │       ├── mod.rs
│   │       ├── config.rs              # Configuration management
│   │       └── telemetry.rs           # Metrics and tracing
│   ├── tests/
│   │   ├── integration/
│   │   │   ├── execution_tests.rs
│   │   │   └── bridge_tests.rs
│   │   └── unit/
│   │       └── order_tests.rs
│   └── benches/                       # Performance benchmarks
│       └── execution_bench.rs
│
├── dashboard/                         # Trading Dashboard (Next.js)
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── Dockerfile
│   ├── public/
│   │   ├── favicon.ico
│   │   └── logo.png
│   ├── src/
│   │   ├── app/                       # Next.js 14 App Router
│   │   │   ├── layout.tsx             # Root layout
│   │   │   ├── page.tsx               # Dashboard overview
│   │   │   ├── login/
│   │   │   │   └── page.tsx           # Authentication page
│   │   │   ├── accounts/
│   │   │   │   ├── page.tsx           # Account management
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx       # Account details
│   │   │   ├── positions/
│   │   │   │   └── page.tsx           # Position management
│   │   │   ├── analytics/
│   │   │   │   └── page.tsx           # Performance analytics
│   │   │   └── settings/
│   │   │       └── page.tsx           # System settings
│   │   ├── components/
│   │   │   ├── ui/                    # Base UI components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   └── chart.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── account-grid.tsx   # Multi-account overview
│   │   │   │   ├── position-table.tsx # Position management
│   │   │   │   ├── emergency-stop.tsx # Emergency controls
│   │   │   │   └── performance-chart.tsx
│   │   │   └── layout/
│   │   │       ├── header.tsx
│   │   │       ├── sidebar.tsx
│   │   │       └── footer.tsx
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client configuration
│   │   │   ├── websocket.ts           # WebSocket client
│   │   │   ├── auth.ts                # Authentication utilities
│   │   │   └── types.ts               # TypeScript type definitions
│   │   └── hooks/
│   │       ├── use-accounts.ts        # Account data hook
│   │       ├── use-positions.ts       # Position data hook
│   │       └── use-websocket.ts       # Real-time data hook
│   └── tests/
│       ├── __tests__/
│       │   ├── components/
│       │   └── pages/
│       └── playwright/                # E2E tests
│           ├── auth.spec.ts
│           └── dashboard.spec.ts
│
├── shared/                            # Shared Libraries and Utilities
│   ├── types/                         # TypeScript type definitions
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── trading.ts             # Trading-related types
│   │   │   ├── agents.ts              # Agent communication types
│   │   │   └── api.ts                 # API response types
│   │   └── tests/
│   ├── python-utils/                  # Shared Python utilities
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── database/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py          # SQLAlchemy models
│   │   │   │   └── connection.py      # Database connection
│   │   │   ├── messaging/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── kafka_producer.py
│   │   │   │   └── kafka_consumer.py
│   │   │   └── monitoring/
│   │   │       ├── __init__.py
│   │   │       ├── metrics.py         # Prometheus metrics
│   │   │       └── tracing.py         # OpenTelemetry tracing
│   │   └── tests/
│   └── schemas/                       # Database schemas and migrations
│       ├── migrations/
│       │   ├── 001_initial_schema.sql
│       │   ├── 002_add_timescaledb.sql
│       │   └── 003_add_indexes.sql
│       └── seeds/
│           ├── personality_profiles.sql
│           └── test_data.sql
│
├── infrastructure/                    # Infrastructure as Code
│   ├── terraform/                     # Terraform configurations
│   │   ├── environments/
│   │   │   ├── dev/
│   │   │   │   ├── main.tf
│   │   │   │   ├── variables.tf
│   │   │   │   └── terraform.tfvars
│   │   │   ├── staging/
│   │   │   └── production/
│   │   ├── modules/
│   │   │   ├── gke-cluster/
│   │   │   ├── cloud-sql/
│   │   │   ├── kafka/
│   │   │   └── monitoring/
│   │   └── global/
│   │       ├── vpc.tf
│   │       └── dns.tf
│   ├── kubernetes/                    # Kubernetes manifests
│   │   ├── base/
│   │   │   ├── namespace.yaml
│   │   │   ├── configmap.yaml
│   │   │   └── secrets.yaml
│   │   ├── agents/
│   │   │   ├── market-analysis.yaml
│   │   │   ├── risk-management.yaml
│   │   │   └── circuit-breaker.yaml
│   │   ├── execution-engine/
│   │   │   ├── deployment.yaml
│   │   │   └── service.yaml
│   │   ├── dashboard/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── ingress.yaml
│   │   └── monitoring/
│   │       ├── prometheus.yaml
│   │       ├── grafana.yaml
│   │       └── alertmanager.yaml
│   └── helm/                          # Helm charts
│       ├── trading-system/
│       │   ├── Chart.yaml
│       │   ├── values.yaml
│       │   ├── values-staging.yaml
│       │   ├── values-prod.yaml
│       │   └── templates/
│       └── monitoring/
│
├── scripts/                           # Automation scripts
│   ├── setup/
│   │   ├── install-dependencies.sh    # Development setup
│   │   ├── setup-database.sh          # Database initialization
│   │   └── setup-kafka.sh             # Kafka setup
│   ├── deployment/
│   │   ├── build-all.sh               # Build all services
│   │   ├── deploy-staging.sh          # Staging deployment
│   │   └── deploy-production.sh       # Production deployment
│   ├── testing/
│   │   ├── run-integration-tests.sh   # Integration test runner
│   │   ├── load-test.sh               # Load testing script
│   │   └── backup-test-data.sh        # Test data management
│   └── maintenance/
│       ├── backup-database.sh         # Database backup
│       ├── rotate-secrets.sh          # Secret rotation
│       └── system-health-check.sh     # Health check script
│
└── docs/                              # Documentation
    ├── architecture.md                # This document
    ├── api/
    │   ├── agents.md                  # Agent API documentation
    │   ├── execution-engine.md        # Execution engine API
    │   └── dashboard.md               # Dashboard API
    ├── deployment/
    │   ├── local-development.md       # Local setup guide
    │   ├── staging.md                 # Staging deployment
    │   └── production.md              # Production deployment
    ├── trading/
    │   ├── wyckoff-methodology.md     # Trading strategy docs
    │   ├── risk-management.md         # Risk management guide
    │   └── prop-firm-rules.md         # Prop firm compliance
    └── runbooks/
        ├── incident-response.md       # Emergency procedures
        ├── monitoring.md              # Monitoring guide
        └── troubleshooting.md         # Common issues
```
