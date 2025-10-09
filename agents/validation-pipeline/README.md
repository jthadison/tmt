# Parameter Validation Pipeline

**Story 11.7**: Automated Parameter Validation Pipeline

Comprehensive validation pipeline for trading parameter configurations with CI/CD integration.

## Overview

The Validation Pipeline automatically validates all parameter changes before deployment, ensuring only validated, safe parameters reach production.

## Features

### Validation Steps

1. **Schema Validation** - Validates configuration against JSON schema
2. **Overfitting Score** - Calculates and validates overfitting score (< 0.3)
3. **Walk-Forward Backtest** - 6-month walk-forward validation
4. **Monte Carlo Simulation** - 1000 runs with parameter randomization
5. **Stress Testing** - Tests during historical crisis periods
6. **Acceptance Criteria** - Validates all deployment criteria

### Acceptance Criteria (AC2)

Parameters must pass all checks:
- ✅ Schema valid
- ✅ Overfitting score < 0.3
- ✅ Walk-forward out-of-sample Sharpe > 1.0
- ✅ Max drawdown in backtest < 20%
- ✅ Win rate > 45%
- ✅ Profit factor > 1.3
- ✅ Monte Carlo 95% CI lower bound > 0.8
- ✅ Stress tests pass for all crisis periods

## Installation

```bash
cd agents/validation-pipeline
pip install -r requirements.txt
```

## Usage

### CLI (Command Line)

```bash
# Validate configuration
python scripts/validate_parameters.py \
  --config-file config/parameters/active.yaml \
  --output-file validation_results.json

# Custom Monte Carlo runs
python scripts/validate_parameters.py \
  --config-file config/parameters/active.yaml \
  --monte-carlo-runs 500

# Generate Markdown report
python scripts/validate_parameters.py \
  --config-file config/parameters/active.yaml \
  --format markdown
```

### REST API

Start the service:

```bash
cd agents/validation-pipeline
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

Endpoints:

```bash
# Async validation (recommended for long-running validations)
curl -X POST http://localhost:8090/api/validation/run \
  -H "Content-Type: application/json" \
  -d '{
    "config_file": "config/parameters/active.yaml",
    "monte_carlo_runs": 1000
  }'

# Check status
curl http://localhost:8090/api/validation/status/{job_id}

# Get Markdown report
curl http://localhost:8090/api/validation/report/{job_id}/markdown

# Synchronous validation (blocks until complete)
curl -X POST http://localhost:8090/api/validation/run-sync \
  -H "Content-Type: application/json" \
  -d '{
    "config_file": "config/parameters/active.yaml"
  }'
```

### Python API

```python
import asyncio
from app.pipeline import ValidationPipeline
from app.models import MonteCarloConfig

# Create pipeline
mc_config = MonteCarloConfig(num_runs=1000, parallel_workers=4)
pipeline = ValidationPipeline(monte_carlo_config=mc_config)

# Run validation
async def validate():
    report = await pipeline.validate_parameter_change(
        config_file="config/parameters/active.yaml",
        output_file="validation_results.json"
    )

    if report.all_checks_passed:
        print("✅ Validation PASSED")
    else:
        print("❌ Validation FAILED")
        for rec in report.recommendations:
            print(f"  - {rec}")

asyncio.run(validate())
```

## CI/CD Integration

The pipeline integrates with GitHub Actions to automatically validate parameter changes on pull requests.

### Workflow

```yaml
# .github/workflows/validate-parameters.yml
name: Validate Parameter Changes

on:
  pull_request:
    paths:
      - 'config/parameters/**'
```

When a PR modifies parameter configurations:
1. Workflow automatically triggers
2. Validation pipeline runs all checks
3. Results posted as PR comment
4. PR blocked if validation fails

## Monte Carlo Simulation

Tests parameter robustness with randomization:

- **Entry Price Variation**: ±5 pips
- **Exit Timing Variation**: ±2 hours
- **Slippage Variation**: 0-3 pips
- **Runs**: 1000 simulations (configurable)
- **Parallelization**: Multi-core support

Calculates 95% confidence intervals for:
- Sharpe ratio
- Maximum drawdown
- Win rate

## Stress Testing

Tests parameters during historical crisis periods:

1. **2008 Financial Crisis** (Sep-Dec 2008)
2. **2015 CHF Flash Crash** (Jan 15, 2015)
3. **2020 COVID Crash** (Mar 2020)

Validates:
- Max drawdown < 25% during crisis
- Recovery within 90 days post-crisis

## Report Formats

### JSON Report

```json
{
  "job_id": "abc-123",
  "status": "APPROVED",
  "all_checks_passed": true,
  "schema_validation": { ... },
  "overfitting_validation": { ... },
  "walk_forward_validation": { ... },
  "monte_carlo_validation": { ... },
  "stress_test_validation": { ... },
  "acceptance_criteria": { ... }
}
```

### Markdown Report

Formatted for GitHub PR comments with:
- Status summary
- Individual check results
- Metrics tables
- Remediation recommendations

## Performance

- **Target**: < 30 minutes total pipeline execution
- **Optimization**: Parallel Monte Carlo simulations
- **Caching**: Historical data cached for faster loading

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_monte_carlo.py -v
```

## Architecture

```
agents/validation-pipeline/
├── app/
│   ├── main.py              # FastAPI REST API
│   ├── pipeline.py          # Main orchestrator
│   ├── monte_carlo.py       # Monte Carlo simulator
│   ├── stress_tester.py     # Stress testing framework
│   ├── acceptance_validator.py  # Acceptance criteria
│   ├── report_generator.py  # Report generation
│   └── models.py            # Pydantic models
├── tests/                   # Comprehensive tests
├── requirements.txt
├── Dockerfile
└── README.md
```

## Integration Points

### Dependencies

- **Backtesting Framework** (Story 11.2): BacktestEngine
- **Walk-Forward Optimizer** (Story 11.3): WalkForwardOptimizer, OverfittingDetector
- **Config Manager** (Story 11.6): ConfigValidator, JSON Schema

### Data Flow

```
Parameter Change (Git commit)
    ↓
GitHub Actions Triggered
    ↓
Validation Pipeline
    ├── Schema Validation
    ├── Overfitting Score
    ├── Walk-Forward Backtest
    ├── Monte Carlo Simulation
    └── Stress Testing
    ↓
Acceptance Criteria Check
    ↓
Report Generation
    ↓
PR Comment Posted
    ↓
Approve/Block Merge
```

## Exit Codes (CLI)

- `0` - Validation passed (APPROVED)
- `1` - Validation failed (REJECTED)
- `2` - Pipeline error

## Environment Variables

```bash
# Optional: Configure data repository
DATABASE_URL=postgresql://...

# Optional: Parallel workers
MONTE_CARLO_WORKERS=4

# Optional: Number of Monte Carlo runs
MONTE_CARLO_RUNS=1000
```

## Contributing

See [Story 11.7](../../docs/stories/epic-11/11.7.automated-parameter-validation-pipeline.md) for implementation details.

## License

Proprietary - Adaptive/Continuous Learning Autonomous Trading System
