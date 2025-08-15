# Epic 8: Retail Broker Integration

Enable TMT system to trade with retail brokers (personal capital) alongside prop firm accounts, starting with OANDA v20 API integration for US and international traders.

## Business Value

- **Market Expansion**: Access traders using personal capital, not just prop firm funded accounts
- **Revenue Growth**: No profit splits with prop firms (traders keep 100%)
- **Simplified Compliance**: Broker accounts have fewer restrictions than prop firms
- **Geographic Coverage**: Support US traders with FIFO/leverage compliance
- **Strategic Positioning**: First-mover advantage in unified broker/prop firm platform

## Success Metrics

- Support 3+ retail brokers within 6 months
- < 100ms average order execution latency
- 99.9% API availability via circuit breaker protection
- 100% US regulatory compliance validation
- Zero compliance violations in production

---

## Story 8.1: Broker Authentication & Connection Management

As a trader with an OANDA account,
I want to securely connect my broker account to TMT,
so that I can execute trades through the platform.

### Acceptance Criteria

1. Secure storage of OANDA API credentials in HashiCorp Vault
2. Support for both practice and live account environments
3. Connection pooling maintains persistent sessions for performance
4. Automatic reconnection within 5 seconds on connection loss
5. Connection status displayed in dashboard (Connected/Disconnected/Reconnecting)
6. API key validation prevents invalid credentials from being saved
7. Support for multiple OANDA accounts per user
8. Session timeout handling with automatic refresh

### Technical Details
- Implement `OandaAuthHandler` with connection pooling
- Use aiohttp for async HTTP operations
- Store credentials encrypted at rest
- Implement health check endpoint

### Story Points: 5

---

## Story 8.2: Account Information & Balance Tracking

As a trader,
I want to see my OANDA account balance and margin in real-time,
so that I can monitor my trading capital and risk exposure.

### Acceptance Criteria

1. Display account balance, unrealized P&L, and realized P&L
2. Show margin used, margin available, and margin closeout percentage
3. List all tradeable instruments with current spreads
4. Update account metrics every 5 seconds or on trade execution
5. Display account currency and leverage settings
6. Show number of open positions and pending orders
7. Calculate account equity (balance + unrealized P&L)
8. Historical balance chart for last 30 days

### Technical Details
- Implement `OandaAccountManager` class
- Cache instrument data with 5-minute TTL
- WebSocket subscription for real-time updates

### Story Points: 3

---

## Story 8.3: Market Order Execution

As a trader,
I want to place market orders through OANDA,
so that I can enter positions immediately at current market prices.

### Acceptance Criteria

1. Execute market buy/sell orders with < 100ms latency
2. Support position sizing in units (not lots)
3. Optional stop loss and take profit on order entry
4. Order fills return execution price and transaction ID
5. Client order ID tracking for TMT signal correlation
6. Slippage tracking (difference between expected and fill price)
7. Partial fill handling for large orders
8. Order rejection messages clearly explain reason

### Technical Details
- Implement `OandaOrderManager.place_order()`
- Map TMT signals to OANDA order format
- Include TMT agent name in client extensions

### Story Points: 5

---

## Story 8.4: US Regulatory Compliance Validation

As a US trader,
I want automatic FIFO and leverage compliance,
so that I never violate NFA regulations.

### Acceptance Criteria

1. Enforce FIFO (First In, First Out) for US accounts
2. Prevent hedging (no simultaneous long/short positions)
3. Limit leverage to 50:1 for major pairs, 20:1 for minors
4. Block orders that would violate FIFO rules
5. Display clear error messages for compliance violations
6. Automatic position selection for FIFO closes
7. Compliance rules configurable per account region
8. Audit log of all compliance checks and results

### Technical Details
- Implement `validate_us_compliance()` method
- Check existing positions before new orders
- Calculate effective leverage per trade

### Story Points: 8

---

## Story 8.5: Real-Time Price Streaming

As a trader,
I want to receive real-time price updates from OANDA,
so that my trading decisions are based on current market data.

### Acceptance Criteria

1. Stream bid/ask prices for subscribed instruments
2. Calculate and display spread in pips
3. Show if instrument is currently tradeable
4. Automatic reconnection on stream interruption
5. Price update frequency of at least 1 update/second
6. Subscribe/unsubscribe to instruments dynamically
7. Price data includes timestamp for latency monitoring
8. Handle market closed periods gracefully

### Technical Details
- Implement `OandaStreamManager` with WebSocket
- Use async callbacks for price updates
- Implement heartbeat monitoring

### Story Points: 5

---

## Story 8.6: Position Management & Modification

As a trader,
I want to manage my open OANDA positions,
so that I can adjust stops, targets, and close positions.

### Acceptance Criteria

1. List all open positions with current P&L
2. Modify stop loss and take profit for open positions
3. Partial position closing (e.g., close 50% of position)
4. Close all positions with single command
5. Position details show entry price, current price, swap charges
6. Calculate position P&L in account currency
7. Position age tracking (time since opened)
8. Trailing stop loss modification support

### Technical Details
- Implement position CRUD operations
- Track position modifications in audit log
- Support batch operations for efficiency

### Story Points: 5

---

## Story 8.7: Limit & Stop Order Management

As a trader,
I want to place limit and stop orders,
so that I can enter positions at specific price levels.

### Acceptance Criteria

1. Place limit orders (buy below/sell above market)
2. Place stop orders (buy above/sell below market)
3. Good Till Cancelled (GTC) and Good Till Date (GTD) support
4. View all pending orders with distance from current price
5. Modify pending order price, stop loss, take profit
6. Cancel individual or all pending orders
7. Order expiry handling and notifications
8. Market-if-touched order type support

### Technical Details
- Extend `OandaOrderManager` for pending orders
- Implement order state tracking
- Add order expiry monitoring

### Story Points: 5

---

## Story 8.8: Transaction History & Audit Trail

As a trader/compliance officer,
I want to access complete transaction history,
so that I can audit all trading activity and calculate performance.

### Acceptance Criteria

1. Retrieve transaction history for specified date range
2. Filter transactions by type (order, funding, fee, etc.)
3. Export transactions to CSV for tax reporting
4. Show transaction details: time, type, instrument, P&L
5. Calculate daily/weekly/monthly P&L summaries
6. Track commission and financing charges
7. Audit trail links TMT signals to OANDA transactions
8. 7-year retention of all transaction records

### Technical Details
- Implement transaction streaming endpoint
- Store transactions in TimescaleDB
- Create reporting API endpoints

### Story Points: 3

---

## Story 8.9: Error Handling & Circuit Breaker

As a system administrator,
I want robust error handling with circuit breaker protection,
so that the system remains stable during OANDA API issues.

### Acceptance Criteria

1. Retry failed requests with exponential backoff (max 3 attempts)
2. Circuit breaker opens after 5 consecutive failures
3. Circuit breaker attempts recovery after 60 seconds
4. Rate limiting prevents exceeding 100 requests/second
5. Graceful degradation when API is unavailable
6. Error notifications to ops team for critical failures
7. Detailed error logging with context for debugging
8. Manual circuit breaker reset capability

### Technical Details
- Implement `OandaRetryHandler` and `OandaCircuitBreaker`
- Use backoff library for retry logic
- Add Prometheus metrics for monitoring

### Story Points: 5

---

## Story 8.10: Multi-Account Broker Support Foundation

As a product owner,
I want extensible broker integration architecture,
so that we can easily add more brokers beyond OANDA.

### Acceptance Criteria

1. Abstract `BrokerAdapter` interface defined
2. Broker factory pattern for instantiating adapters
3. Configuration system supports multiple broker types
4. Unified error codes across different brokers
5. Common order/position models with broker-specific mapping
6. Broker capability discovery (supported order types, instruments)
7. A/B testing framework for broker routing
8. Performance metrics comparison across brokers

### Technical Details
- Create abstract base classes
- Implement factory pattern
- Design plugin architecture for new brokers

### Story Points: 8

---

## Story 8.11: Broker Integration Dashboard

As a trader,
I want a unified dashboard showing all my broker accounts,
so that I can monitor and manage multiple brokers from one interface.

### Acceptance Criteria

1. Dashboard shows all connected broker accounts
2. Aggregate view of total balance across all brokers
3. Combined P&L tracking across broker accounts
4. Per-broker connection status and health indicators
5. Quick actions: connect/disconnect/reconnect brokers
6. Broker-specific features clearly indicated
7. Performance metrics per broker (latency, fill quality)
8. Mobile-responsive design for on-the-go monitoring

### Technical Details
- Extend existing TMT dashboard
- Create React components for broker widgets
- Implement WebSocket for real-time updates

### Story Points: 8

---

## Story 8.12: Broker Integration Testing Suite

As a QA engineer,
I want comprehensive test coverage for broker integration,
so that we can ensure reliability before production deployment.

### Acceptance Criteria

1. Unit tests achieve > 90% code coverage
2. Integration tests with OANDA practice account
3. Performance tests validate < 100ms order latency
4. Load tests verify 100 concurrent orders handling
5. Failure injection tests for network/API issues
6. Compliance validation test scenarios
7. End-to-end tests for complete trade lifecycle
8. Automated regression test suite in CI/CD

### Technical Details
- Use pytest-asyncio for async testing
- Mock OANDA API responses for unit tests
- Create test data generators

### Story Points: 5

---

## Story 8.13: Production Deployment & Monitoring

As a DevOps engineer,
I want production-ready deployment with monitoring,
so that we can operate the broker integration reliably.

### Acceptance Criteria

1. Docker containers for broker integration services
2. Kubernetes deployment manifests with auto-scaling
3. Prometheus metrics for API latency, errors, throughput
4. Grafana dashboards for broker health monitoring
5. PagerDuty alerts for critical failures
6. Log aggregation in ELK stack
7. Secrets management via HashiCorp Vault
8. Blue-green deployment support for zero downtime

### Technical Details
- Create Dockerfile and k8s manifests
- Implement OpenTelemetry instrumentation
- Configure AlertManager rules

### Story Points: 5

---

## Story 8.14: Broker Cost Analysis & Optimization

As a trader,
I want to see the true cost of trading with each broker,
so that I can optimize my broker selection for profitability.

### Acceptance Criteria

1. Track spreads, commissions, and swap rates per broker
2. Calculate all-in cost per trade including all fees
3. Compare execution quality across brokers
4. Slippage analysis and reporting
5. Optimal broker routing recommendations
6. Historical cost trends and analysis
7. Break-even calculator including broker costs
8. Export cost reports for accounting

### Technical Details
- Create cost calculation engine
- Store historical cost data
- Build analytics API endpoints

### Story Points: 5

---

## Story 8.15: Regulatory Reporting & Compliance

As a compliance officer,
I want automated regulatory reporting for broker trades,
so that we maintain compliance with financial regulations.

### Acceptance Criteria

1. Generate Form 1099 data for US tax reporting
2. Track wash sale violations for tax purposes
3. Pattern day trading (PDT) rule monitoring
4. Large trader reporting thresholds
5. Suspicious activity detection and reporting
6. Data retention meets regulatory requirements (7 years)
7. Audit reports on demand with full trade details
8. GDPR-compliant data handling for EU users

### Technical Details
- Implement regulatory rule engine
- Create report generation system
- Add data retention policies

### Story Points: 8

---

## Epic Summary

**Total Story Points**: 84

**Priority Order**:
1. P0 (Must Have): Stories 8.1, 8.3, 8.4, 8.5, 8.9 - Core functionality
2. P1 (Should Have): Stories 8.2, 8.6, 8.8, 8.11, 8.12 - Essential features
3. P2 (Nice to Have): Stories 8.7, 8.10, 8.13, 8.14, 8.15 - Enhanced capabilities

**Dependencies**:
- Requires existing TMT execution engine
- HashiCorp Vault must be configured
- Dashboard framework must be in place

**Risks**:
- OANDA API changes could break integration
- US regulatory requirements may change
- Network latency could impact performance targets
- Rate limiting might affect high-frequency strategies