# Learning Safety Agent

AI-powered learning safety and circuit breaker management system with autonomous learning capabilities.

## Features

### Core Capabilities
- **Circuit Breakers**: Automated safety mechanisms for trading system protection
- **Anomaly Detection**: Real-time performance anomaly monitoring
- **Rollback Systems**: Safe parameter rollback capabilities
- **Manual Override**: Emergency manual intervention controls
- **A/B Testing Framework**: Systematic parameter testing
- **Data Quarantine**: Suspicious data isolation
- **News Monitoring**: Market event tracking

### Autonomous Learning (Story 13.1)
- **24-Hour Learning Cycle**: Automatic performance analysis every 24 hours
- **Multi-Dimensional Analysis**: Performance tracking across:
  - Trading sessions (Tokyo, London, NY, Sydney, Overlap)
  - Pattern types (Spring, Upthrust, Accumulation, Distribution)
  - Confidence buckets (50-60%, 60-70%, 70-80%, 80-90%, 90-100%)
- **Statistical Significance**: Minimum 20 trades required for suggestions
- **Audit Trail**: Complete JSON logging of all learning cycles
- **Feature Flag Control**: Easy enable/disable without code changes

## Configuration

### Environment Variables

#### Required
- `OANDA_API_KEY`: OANDA API key for account monitoring
- `OANDA_ACCOUNT_ID`: OANDA account ID

#### Optional (Autonomous Learning)
- `ENABLE_AUTONOMOUS_LEARNING`: Enable/disable learning loop (default: `true`)
- `LEARNING_CYCLE_INTERVAL`: Cycle interval in seconds (default: `86400` = 24 hours)
- `LEARNING_MIN_TRADES`: Minimum trades for significance (default: `20`)
- `TRADING_DB_PATH`: Path to trade history database (default: `orchestrator/data/trading_system.db`)

#### Optional (General)
- `PORT`: Service port (default: `8004`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Configuration Validation

The agent validates configuration on startup:
- `LEARNING_CYCLE_INTERVAL` must be a positive integer
- `LEARNING_MIN_TRADES` must be >= 10
- Database path must be accessible

## API Endpoints

### Health & Status
- `GET /health` - Health check endpoint
- `GET /status` - Current system status

### Learning Safety
- `POST /check_learning_safety` - Check if safe to continue learning
- `POST /trigger_circuit_breaker` - Manually trigger circuit breaker
- `POST /check_performance_anomaly` - Check for performance anomalies
- `POST /manual_override` - Handle manual override requests
- `GET /quarantine_status` - Get data quarantine status

### Autonomous Learning (New)
- `GET /api/v1/learning/status` - Get learning cycle status

#### Learning Status Response Format
```json
{
  "data": {
    "cycle_state": "COMPLETED",
    "last_run_timestamp": "2025-10-10T08:30:00Z",
    "next_run_timestamp": "2025-10-11T08:30:00Z",
    "suggestions_generated_count": 3,
    "active_tests_count": 1,
    "cycle_interval_seconds": 86400,
    "running": true
  },
  "error": null,
  "correlation_id": "uuid-here"
}
```

**Cycle States**:
- `IDLE`: Learning loop initialized but not yet started
- `RUNNING`: Learning cycle currently executing
- `COMPLETED`: Last cycle completed successfully
- `FAILED`: Last cycle failed (see audit logs for details)

## Running the Agent

### Standard Mode
```bash
cd agents/learning-safety
PORT=8004 python -m app.main
```

### Development Mode (5-minute cycles for testing)
```bash
cd agents/learning-safety
ENABLE_AUTONOMOUS_LEARNING=true \
LEARNING_CYCLE_INTERVAL=300 \
LEARNING_MIN_TRADES=10 \
PORT=8004 python -m app.main
```

### Disabled Learning Mode
```bash
cd agents/learning-safety
ENABLE_AUTONOMOUS_LEARNING=false \
PORT=8004 python -m app.main
```

## Audit Trail

All learning cycle events are logged to:
- **File**: `agents/learning-safety/logs/audit_trail.log`
- **Format**: Structured JSON (one event per line)
- **Rotation**: Max 100MB per file, keeps last 10 files

### Event Types

1. **learning_cycle_start**
   ```json
   {
     "event": "learning_cycle_start",
     "cycle_id": "uuid",
     "timestamp": "2025-10-10T08:00:00Z",
     "level": "INFO"
   }
   ```

2. **learning_cycle_complete**
   ```json
   {
     "event": "learning_cycle_complete",
     "cycle_id": "uuid",
     "timestamp": "2025-10-10T08:05:00Z",
     "level": "INFO",
     "trade_count": 100,
     "best_session": "LONDON",
     "worst_session": "SYDNEY",
     "suggestions_count": 0
   }
   ```

3. **learning_cycle_failed**
   ```json
   {
     "event": "learning_cycle_failed",
     "cycle_id": "uuid",
     "timestamp": "2025-10-10T08:05:00Z",
     "level": "ERROR",
     "error_message": "Database connection failed",
     "error_type": "ConnectionError"
   }
   ```

## Testing

### Unit Tests
```bash
cd agents/learning-safety
pytest tests/test_performance_analyzer.py -v
pytest tests/test_autonomous_learning_loop.py -v
pytest tests/test_audit_logger.py -v
```

### Integration Tests
```bash
cd agents/learning-safety
pytest tests/test_learning_cycle_integration.py -v
```

### All Tests
```bash
cd agents/learning-safety
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Architecture

### Components

1. **AutonomousLearningAgent** (`app/autonomous_learning_loop.py`)
   - Manages 24-hour learning cycle
   - Coordinates performance analysis
   - Handles error recovery

2. **PerformanceAnalyzer** (`app/performance_analyzer.py`)
   - Analyzes trades across multiple dimensions
   - Calculates win rates, profit factors, R:R ratios
   - Identifies best/worst performers

3. **AuditLogger** (`app/audit_logger.py`)
   - Structured JSON logging
   - Automatic file rotation
   - Post-mortem analysis support

4. **Performance Models** (`app/models/performance_models.py`)
   - SessionMetrics: Per-session performance
   - PatternMetrics: Per-pattern performance
   - ConfidenceMetrics: Per-confidence-bucket performance
   - PerformanceAnalysis: Aggregated results

### Integration Points

- **Trade History Database** (Epic 12): Source of performance data
- **Orchestrator**: Will consume parameter suggestions (future stories)
- **Market Analysis Agent**: Will receive parameter updates (future stories)
- **Dashboard**: Will display learning status (future stories)

## Dependencies

- Epic 12 (Data Foundation & Observability) must be completed
- Trade history database must exist with required schema
- TradeRepository must be available

## Safety Features

1. **Feature Flag**: Easy enable/disable without code changes
2. **Statistical Significance**: Prevents suggestions on small samples (n<20)
3. **Error Handling**: Failed cycles don't crash the agent
4. **Database Resilience**: Unavailable database skips cycle gracefully
5. **Audit Trail**: Complete logging enables post-mortem analysis
6. **Graceful Shutdown**: Clean task cancellation on agent stop

## Future Enhancements (Post-MVP)

- Parameter suggestion generation (Epic 13.2)
- A/B testing integration (Epic 13.3)
- Automated parameter deployment (Epic 13.4)
- Dashboard visualization (Epic 13.5)
- Machine learning model training (Epic 13.6)

## Troubleshooting

### Learning Loop Not Starting
1. Check `ENABLE_AUTONOMOUS_LEARNING=true` in environment
2. Verify database path exists and is accessible
3. Check logs for import errors
4. Verify Epic 12 dependency is deployed

### No Trades Available
- System requires minimum 10 trades for analysis
- Check trade history database has data
- Verify TradeRepository.get_recent_trades() works

### Cycle Failing
1. Check audit logs: `agents/learning-safety/logs/audit_trail.log`
2. Look for "learning_cycle_failed" events
3. Check error_message and error_type fields
4. Verify database connection

### API Timeout
- Default timeout is 5 seconds
- Check if learning loop is hung
- Restart agent if necessary

## Monitoring

### Key Metrics to Monitor
- Cycle state (should be COMPLETED between cycles)
- Time since last successful cycle
- Failure rate (should be <1%)
- Analysis duration (should be <30s for 100 trades)

### Health Checks
```bash
# Check agent health
curl http://localhost:8004/health

# Check learning status
curl http://localhost:8004/api/v1/learning/status
```

## Support

For issues or questions:
1. Check audit logs first
2. Review this README
3. Check Story 13.1 documentation
4. Contact development team
