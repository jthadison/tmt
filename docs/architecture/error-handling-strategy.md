# Error Handling Strategy

## General Approach

- **Error Model:** Domain-specific exception hierarchy with structured error codes
- **Exception Hierarchy:** Base `TradingSystemError` with specialized subclasses for each domain (MarketDataError, ExecutionError, RiskError, etc.)
- **Error Propagation:** Errors bubble up through Kafka events with full context, circuit breakers monitor error rates per service

## Logging Standards

- **Library:** Python: structlog 24.1.0, Rust: tracing 0.1.40, TypeScript: winston 3.11.0
- **Format:** JSON structured logging with correlation IDs
- **Levels:** ERROR (system failures), WARN (degraded performance), INFO (state changes), DEBUG (detailed flow)
- **Required Context:**
  - Correlation ID: UUID v4 propagated through all services
  - Service Context: agent_type, version, instance_id
  - User Context: account_id (never log credentials or personal data)

## Error Handling Patterns

### External API Errors

- **Retry Policy:** Exponential backoff with jitter: 1s, 2s, 4s, 8s, then circuit breaker
- **Circuit Breaker:** Trip after 5 consecutive failures, half-open after 30s, reset after 3 successes
- **Timeout Configuration:** REST APIs: 5s default, WebSocket connect: 10s, Market data streams: no timeout
- **Error Translation:** Map external errors to internal error codes (e.g., OANDA 429 → RATE_LIMIT_ERROR)

### Business Logic Errors

- **Custom Exceptions:** `InsufficientMarginError`, `PropFirmRuleViolation`, `SignalConfidenceTooLow`
- **User-Facing Errors:** Sanitized messages with error codes, no internal details exposed
- **Error Codes:** TRADE-001 through TRADE-999 for trading errors, RISK-001 through RISK-999 for risk violations

### Data Consistency

- **Transaction Strategy:** PostgreSQL transactions with SERIALIZABLE isolation for critical operations
- **Compensation Logic:** Saga pattern with compensating transactions for distributed operations
- **Idempotency:** All trade operations use idempotency keys (UUID v4) with 24-hour retention
