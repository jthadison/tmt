# Prop Firm Specifications and Rules

## Overview
This document outlines the complete rule specifications for the three prop firms supported by the trading system: DNA Funded, Funding Pips, and The Funded Trader. Each firm has unique requirements that must be enforced by the Compliance Agent.

## DNA Funded

### Account Types
- **Challenge Phase 1:** Initial evaluation (30 days)
- **Challenge Phase 2:** Verification (60 days)
- **Funded Account:** Live trading with firm capital

### Trading Rules

#### Risk Management
- **Daily Loss Limit:** 5% of initial balance
- **Maximum Drawdown:** 10% of initial balance (trailing)
- **Minimum Trading Days:** 5 days in Phase 1, 5 days in Phase 2
- **Profit Target:** 
  - Phase 1: 8%
  - Phase 2: 5%
  - Funded: No target

#### Position Management
- **Maximum Lot Size:** Based on account size
  - $10k account: 2 lots max
  - $25k account: 5 lots max
  - $50k account: 10 lots max
  - $100k account: 20 lots max
- **Maximum Positions:** 5 concurrent positions
- **Leverage:** 1:100 maximum

#### Trading Restrictions
- **News Trading:** No trading 2 minutes before and after high-impact news
- **Weekend Holding:** Allowed with reduced position size
- **Prohibited Strategies:**
  - Grid trading
  - Martingale
  - High-frequency trading (>100 trades/day)
  - Arbitrage

#### Consistency Rules
- **Daily Profit Cap:** No single day can exceed 30% of total profit
- **Lot Size Consistency:** Maximum 3x variance between trades

### Platform Support
- **Primary:** TradeLocker
- **Secondary:** DXtrade

### Payout Structure
- **Profit Split:** 80/20 (trader/firm)
- **First Payout:** After 30 days
- **Subsequent Payouts:** Bi-weekly

---

## Funding Pips

### Account Types
- **Evaluation:** Single phase challenge (30 days)
- **Funded Account:** Live trading account

### Trading Rules

#### Risk Management
- **Daily Loss Limit:** 4% of initial balance
- **Maximum Drawdown:** 8% of initial balance (static)
- **Minimum Trading Days:** 3 days
- **Profit Target:**
  - Evaluation: 8%
  - Funded: No target

#### Position Management
- **Maximum Lot Size:** Risk-based calculation
  - Max 2% risk per trade
  - Automatic lot size calculation required
- **Maximum Positions:** No limit (within risk parameters)
- **Leverage:** 1:30 for forex, 1:20 for indices

#### Trading Restrictions
- **News Trading:** Allowed but monitored
- **Weekend Holding:** Not allowed - all positions must be closed
- **Hold Time:** Minimum 1 minute for all positions
- **Prohibited Strategies:**
  - Copy trading from other accounts
  - Tick scalping
  - Latency arbitrage

#### Special Requirements
- **Stop Loss:** Mandatory for all trades
- **Trading Hours:** No restrictions
- **Symbols:** Forex majors and minor pairs, major indices

### Platform Support
- **Primary:** DXtrade
- **Secondary:** TradeLocker

### Payout Structure
- **Profit Split:** 85/15 (trader/firm)
- **First Payout:** After 14 days
- **Subsequent Payouts:** Weekly

---

## The Funded Trader

### Account Types
- **Standard Challenge:** Two-phase evaluation
- **Rapid Challenge:** Single phase (15 days)
- **Knight Challenge:** One phase with higher targets
- **Funded Account:** Multiple tiers with scaling

### Trading Rules

#### Risk Management
- **Daily Loss Limit:** 5% of initial or current balance (whichever is higher)
- **Maximum Drawdown:** 10% of initial balance (trailing)
- **Minimum Trading Days:** 
  - Standard: 5 days per phase
  - Rapid: 3 days
  - Knight: 5 days
- **Profit Target:**
  - Standard Phase 1: 10%
  - Standard Phase 2: 5%
  - Rapid: 8%
  - Knight: 15%

#### Position Management
- **Maximum Lot Size:** Account-based with scaling
  - Tier 1 ($10k-$25k): 5 lots max
  - Tier 2 ($50k): 10 lots max
  - Tier 3 ($100k): 20 lots max
  - Tier 4 ($200k+): 40 lots max
- **Maximum Positions:** 10 concurrent positions
- **Leverage:** 1:100 standard, 1:200 for experienced traders

#### Trading Restrictions
- **News Trading:** 
  - Standard/Rapid: No trading 5 minutes before/after high-impact
  - Knight: No restrictions
- **Weekend Holding:** Allowed with notification
- **Hold Time:** No minimum
- **Prohibited Strategies:**
  - Account management by third parties
  - Reverse arbitrage
  - Exploiting demo server delays

#### Scaling Plan
- **Initial Funded:** $10k - $200k based on challenge
- **Scale Up:** 25% increase every 3 months with 10% profit
- **Maximum Account:** $1,000,000
- **Scale Requirements:**
  - Consistent profitability
  - Risk adherence
  - No rule violations

### Platform Support
- **Primary:** TradeLocker
- **Secondary:** DXtrade

### Payout Structure
- **Profit Split:** 
  - Initial: 80/20 (trader/firm)
  - After scaling: 90/10
- **First Payout:** After 30 days minimum, 5% profit minimum
- **Subsequent Payouts:** Bi-weekly or monthly (trader choice)

---

## Compliance Implementation Requirements

### Real-Time Monitoring
1. **Position Tracking**
   - Current P&L vs daily limit
   - Running drawdown calculation
   - Position count monitoring
   - Lot size validation

2. **News Event Integration**
   - Economic calendar API integration
   - Pre-trade news checks
   - Automatic position closure if required
   - News buffer time enforcement

3. **Consistency Monitoring**
   - Daily profit distribution
   - Lot size variance calculation
   - Trading pattern analysis
   - Strategy classification

### Violation Handling
1. **Warning System**
   - 80% of limit: Yellow warning
   - 90% of limit: Orange warning
   - 95% of limit: Red alert

2. **Automatic Actions**
   - Block new trades when approaching limits
   - Force close positions if required
   - Emergency stop on violations
   - Detailed logging of all actions

3. **Recovery Procedures**
   - Daily reset at market close
   - Drawdown recalculation
   - Trading day counter update
   - Profit target tracking

### Platform-Specific Adaptations

#### TradeLocker Integration
- OAuth2 token management per prop firm
- Account switching for multiple challenges
- Real-time WebSocket monitoring
- Automatic session management

#### DXtrade Integration
- FIX session per account
- Certificate management per prop firm
- Sequence number tracking
- Session schedule adherence

---

## Configuration File Format

```json
{
  "prop_firms": {
    "dna_funded": {
      "daily_loss_limit": 0.05,
      "max_drawdown": 0.10,
      "trailing_drawdown": true,
      "min_trading_days": 5,
      "profit_targets": {
        "phase1": 0.08,
        "phase2": 0.05
      },
      "news_buffer_minutes": 2,
      "platform_preference": "tradelocker"
    },
    "funding_pips": {
      "daily_loss_limit": 0.04,
      "max_drawdown": 0.08,
      "trailing_drawdown": false,
      "min_trading_days": 3,
      "profit_targets": {
        "evaluation": 0.08
      },
      "mandatory_stop_loss": true,
      "platform_preference": "dxtrade"
    },
    "the_funded_trader": {
      "daily_loss_limit": 0.05,
      "max_drawdown": 0.10,
      "trailing_drawdown": true,
      "account_types": ["standard", "rapid", "knight"],
      "scaling_enabled": true,
      "platform_preference": "tradelocker"
    }
  }
}
```

---

## Testing Requirements

### Compliance Testing Scenarios
1. **Drawdown Testing**
   - Approach daily limit
   - Exceed daily limit attempt
   - Trailing drawdown calculation
   - Static drawdown calculation

2. **News Trading Testing**
   - High-impact news blocking
   - Buffer time enforcement
   - Position closure timing
   - News calendar accuracy

3. **Consistency Testing**
   - Daily profit distribution
   - Lot size variance
   - Multi-day consistency
   - Pattern detection

4. **Platform Integration Testing**
   - Account switching
   - Multi-session management
   - Failover between platforms
   - Performance under load

---

## Monitoring Dashboard Requirements

### Key Metrics Display
- Current drawdown (daily and max)
- Profit progress toward target
- Trading days completed
- Active positions and risk
- Time to next news event
- Consistency score
- Rule violation warnings

### Alert System
- SMS/Email for approaching limits
- Dashboard notifications
- Audio alerts for critical warnings
- Slack/Discord integration

---

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2024-01-07 | 1.0 | Initial prop firm specifications | Sarah (PO) |