# Overfitting Monitor Agent - Story 11.4

Real-time monitoring of parameter drift and overfitting risk for the TMT trading system.

## Overview

The Overfitting Monitor continuously tracks trading parameters against a universal baseline, detecting overfitting risk before it impacts live performance. The system provides real-time alerts via Slack and email when parameters drift excessively or performance degrades.

## Features

### Core Monitoring
- **Hourly Overfitting Calculation**: Automatic calculation every hour comparing current vs baseline parameters
- **Parameter Drift Tracking**: 7-day and 30-day trend analysis for all parameters
- **Performance Degradation Detection**: Rolling 7-day Sharpe ratio comparison vs backtest expectations
- **Regime Change Detection**: Automatic detection of volatility shifts and market condition changes

### Alert System
- **Multi-level Alerts**:
  - Normal: Overfitting score < 0.3
  - Warning: Overfitting score 0.3 - 0.5
  - Critical: Overfitting score > 0.5
- **Alert Channels**:
  - Slack webhook integration
  - Email via SendGrid API
- **Smart Recommendations**: Each alert includes actionable recommendations

### Dashboard Components
- **Overfitting Score Gauge**: Real-time gauge with color-coded zones
- **Trend Chart**: 30-day historical overfitting scores
- **Parameter Drift Visualization**: Session-specific parameter deviations
- **Performance Comparison**: Live vs backtest metrics
- **Alerts Panel**: Recent alerts with acknowledgment capability

## Architecture

```
agents/overfitting-monitor/
├── app/
│   ├── main.py                  # FastAPI application
│   ├── monitor.py               # Core overfitting calculation
│   ├── alert_service.py         # Alert management
│   ├── performance_tracker.py   # Performance degradation detection
│   ├── scheduler.py             # Scheduled monitoring jobs
│   ├── database.py              # TimescaleDB integration
│   ├── config.py                # Configuration
│   └── models.py                # Pydantic models
├── tests/                       # Unit tests (45 tests, 100% passing)
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container definition
└── README.md                    # This file
```

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL with TimescaleDB extension
- Redis (optional, for caching)
- Slack webhook URL (optional)
- SendGrid API key (optional, for email)

### Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment** (`.env`):
   ```bash
   PORT=8010
   DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_system

   # Baseline parameters
   BASELINE_CONFIDENCE_THRESHOLD=55.0
   BASELINE_MIN_RISK_REWARD=1.8
   BASELINE_VPA_THRESHOLD=0.6

   # Thresholds
   OVERFITTING_WARNING_THRESHOLD=0.3
   OVERFITTING_CRITICAL_THRESHOLD=0.5
   MAX_PARAMETER_DRIFT_PCT=15.0

   # Alerts
   NOTIFICATIONS_ENABLED=true
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   EMAIL_ENABLED=false
   SENDGRID_API_KEY=your_key_here
   ALERT_RECIPIENTS=email1@example.com,email2@example.com
   ```

3. **Initialize database**:
   ```bash
   # Database initialization happens automatically on startup
   # Tables created: overfitting_scores, parameter_drift, performance_tracking
   ```

4. **Run the service**:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
   ```

### Docker Deployment

```bash
docker build -t overfitting-monitor .
docker run -p 8010:8010 --env-file .env overfitting-monitor
```

## API Endpoints

### Health Check
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed component status

### Monitoring
- `GET /api/monitoring/status` - Current monitoring status
- `GET /api/monitoring/overfitting/current` - Latest overfitting score
- `GET /api/monitoring/overfitting/history` - Historical scores (30 days)
- `GET /api/monitoring/performance-comparison` - Live vs backtest comparison
- `GET /api/monitoring/parameter-drift/{param_name}` - Parameter drift history

### Alerts
- `GET /api/monitoring/alerts` - Get active alerts
- `POST /api/monitoring/alerts/{alert_id}/acknowledge` - Acknowledge alert

### Manual Triggers
- `POST /api/monitoring/trigger/calculate` - Manually trigger calculation

## Overfitting Score Formula

```python
# Calculate deviation for each session's parameters
session_deviation = mean([
    abs(param - baseline) / normalization_factor
    for param in session_params
])

# Combined score (weighted)
overfitting_score = (
    avg_deviation * 0.4 +      # Average across sessions
    max_deviation * 0.4 +      # Worst-case session
    std_deviation * 0.2        # Parameter stability
)
```

**Normalization factors:**
- `confidence_threshold`: divide by 50 (half of 0-100 range)
- `min_risk_reward`: divide by 3 (typical range 1-4)
- `vpa_threshold`: already in 0-1 range

## Performance Metrics

### Degradation Detection
- Calculates rolling 7-day Sharpe ratio
- Compares against backtest expectations
- Alerts when live < 70% of backtest Sharpe

### Regime Change Detection
- Monitors volatility changes (2x spike or 0.5x collapse)
- Tracks win rate shifts (> 30% change)
- Automatic alerts with recommended actions

## Testing

Run unit tests:
```bash
pytest tests/ -v
```

**Test Coverage:**
- 45 unit tests
- 100% passing
- Coverage: monitor.py, alert_service.py, performance_tracker.py

## Monitoring Schedule

- **Overfitting Calculation**: Every hour (top of the hour)
- **Parameter Drift Tracking**: Every 6 hours
- **Performance Degradation Check**: Every 4 hours

## Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Overfitting Score | > 0.3 | > 0.5 |
| Parameter Drift | > 15% in 7 days | > 15% in 7 days |
| Performance Degradation | Live < 70% of backtest | Live < 50% of backtest |

## Dashboard Integration

React components available in `dashboard/components/monitoring/`:
- `OverfittingScoreGauge.tsx` - Real-time score gauge
- `OverfittingTrendChart.tsx` - Historical trend chart
- `AlertsPanel.tsx` - Alert management panel

Example usage:
```typescript
import { OverfittingScoreGauge } from '@/components/monitoring/OverfittingScoreGauge'

<OverfittingScoreGauge
  score={0.25}
  alertLevel="normal"
  lastUpdated="2025-10-09T12:00:00Z"
/>
```

## Troubleshooting

### Service Won't Start
- Check DATABASE_URL is correct
- Ensure TimescaleDB extension is installed
- Verify port 8010 is available

### No Alerts Received
- Verify NOTIFICATIONS_ENABLED=true
- Check SLACK_WEBHOOK_URL is valid
- Test webhook manually

### High Overfitting Scores
- Review parameter deviations in dashboard
- Compare current vs baseline parameters
- Consider running walk-forward optimization
- Check for regime changes

## License

Copyright © 2025 TMT Trading System. All rights reserved.
