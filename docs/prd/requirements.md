# Requirements

## Functional

- FR1: The system shall support automated trading across TradeLocker and DXtrade platforms for forex majors (EUR/USD, GBP/USD, USD/JPY) and major indices (US30, NAS100, SPX500)
- FR2: Eight specialized AI agents shall collaborate through event-driven communication to identify, execute, and manage trades
- FR3: The system shall identify Wyckoff accumulation/distribution phases with >75% confidence before generating trade signals
- FR4: Each prop firm account shall operate with unique trading personality profiles including distinct timing preferences, risk appetites, and pair preferences
- FR5: The system shall validate all trades against prop firm-specific rules for DNA Funded, Funding Pips, and The Funded Trader (drawdown limits, news restrictions, position hold times) before execution
- FR6: The Circuit Breaker Agent shall implement three-tier safety controls: agent-level, account-level, and system-level emergency stops
- FR7: The system shall maintain separate legal entity configurations for each account with proper disclosures and audit trails
- FR8: The Adaptive Risk Intelligence Agent (ARIA) shall dynamically adjust position sizes based on volatility, performance, and remaining risk budget
- FR9: The system shall support both prop firm challenge mode and live funded account mode with appropriate strategy adjustments
- FR10: A shadow paper-trading mode shall validate all agent decisions before enabling live trading
- FR11: The system shall provide manual override capability for all automated trading decisions within 60 seconds
- FR12: Anti-correlation engine shall ensure no suspicious synchronization patterns across multiple accounts
- FR13: Platform abstraction layer shall provide unified interface for TradeLocker, DXtrade, and future trading platforms with hot-swappable implementations

## Non Functional

- NFR1: Signal-to-execution latency shall not exceed 150ms under normal market conditions (accounting for TradeLocker/DXtrade API latency)
- NFR2: System uptime shall maintain 99.5% availability during market hours (maximum 24 hours downtime annually)
- NFR3: All trading decisions shall be logged with retrievable audit trails for 7 years
- NFR4: The platform shall process 1000+ price updates per second without performance degradation
- NFR5: System shall support concurrent management of up to 6 prop firm accounts in production, 3 accounts in MVP
- NFR6: End-to-end encryption shall protect all data transmission with API keys encrypted at rest
- NFR7: Learning model rollback shall complete within 60 seconds when performance degrades
- NFR8: Dashboard shall update account status and P&L in real-time with <2 second delay
- NFR9: System shall maintain compliance with GDPR for EU users and SOC 2 Type II standards
- NFR10: Resource usage shall not exceed 8GB RAM and 4 CPU cores for standard operation
