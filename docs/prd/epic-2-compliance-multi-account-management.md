# Epic 2: Compliance & Multi-Account Management

Implement comprehensive prop firm rule validation and multi-account orchestration capabilities. This epic enables traders to safely manage multiple accounts with different rule sets while maintaining legal compliance and audit trails.

## Story 2.1: Prop Firm Rules Engine

As a funded trader,
I want automatic validation of trades against prop firm rules,
so that I never violate terms that could lose my account.

### Acceptance Criteria

1: Rule configurations for FTMO, Funded Next, and MyForexFunds implemented
2: Pre-trade validation checks: daily loss limit, max loss limit, position size limits
3: Real-time tracking of daily and total P&L against limits
4: News trading restrictions enforced based on economic calendar
5: Minimum holding time requirements validated before closing positions
6: Rule violations logged with detailed explanation and prevented trades

## Story 2.2: Multi-Account Configuration Management

As a trader managing multiple accounts,
I want to configure each account with its specific broker and rules,
so that I can trade appropriately across different prop firms.

### Acceptance Criteria

1: Account configuration API supports adding/editing/removing accounts
2: Each account stores: broker credentials, prop firm rules, risk limits, trading pairs
3: Account credentials encrypted using HashiCorp Vault
4: Configuration changes require 2FA confirmation
5: Account status tracking: active, suspended, in-drawdown, terminated
6: Bulk configuration import/export for backup and migration

## Story 2.3: Legal Entity Separation System

As a compliance officer,
I want each account to operate under separate legal entities,
so that we maintain regulatory compliance and avoid coordination violations.

### Acceptance Criteria

1: Each account tagged with unique legal entity identifier
2: Decision logs demonstrate independent analysis per account
3: Audit trail shows timestamp, entity, rationale for each trade
4: Entity separation report generates compliance documentation
5: Terms of Service acceptance tracked per entity
6: Geographic restrictions enforced based on entity jurisdiction

## Story 2.4: Anti-Correlation Engine

As a risk manager,
I want to prevent suspicious correlation between accounts,
so that we avoid detection of coordinated trading.

### Acceptance Criteria

1: Correlation monitoring across all account positions in real-time
2: Warning triggered when correlation coefficient >0.7 between any two accounts
3: Automatic position adjustment to reduce correlation when threshold exceeded
4: Random delays (1-30 seconds) between similar trades on different accounts
5: Position size variance of 5-15% enforced between accounts
6: Daily correlation report showing all account relationships

## Story 2.5: Account Performance Tracking

As a trader,
I want to see individual and aggregate performance metrics,
so that I can optimize my account allocation and strategies.

### Acceptance Criteria

1: Real-time P&L tracking per account and aggregate
2: Performance metrics: win rate, profit factor, Sharpe ratio, maximum drawdown
3: Daily, weekly, monthly performance reports per account
4: Comparison view between accounts highlighting best/worst performers
5: Export capability for tax reporting and prop firm verification
6: Performance data retained for 2 years minimum
