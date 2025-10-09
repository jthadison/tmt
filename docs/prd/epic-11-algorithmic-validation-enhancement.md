# Epic 11: Algorithmic Validation & Overfitting Prevention

Deploy comprehensive backtesting, validation, and monitoring systems to prevent overfitting and ensure parameter robustness. This epic addresses critical gaps identified in the September 2025 system audit and establishes rigorous validation standards for all trading algorithm modifications.

## Background & Context

**Problem Statement**: The September 2025 comprehensive audit revealed critical vulnerabilities in the trading algorithm validation process:
- **No backtesting framework** exists to validate parameters before live deployment
- **Overfitting crisis** occurred in September 2025 (score: 0.634, 112% above safe threshold)
- **Missing walk-forward validation** to test parameter stability on unseen data
- **No automated overfitting monitoring** to detect parameter drift in real-time
- **Position sizing errors** due to hardcoded account balances and simplified calculations

**Impact**: These gaps created a **MODERATE-HIGH RISK** environment where:
- Parameter changes cannot be validated before affecting live trading
- Historical overfitting may repeat without detection
- Position sizing errors reduce risk management effectiveness
- Configuration changes lack version control and audit trails

**Solution**: Implement a comprehensive validation infrastructure that ensures all algorithm changes are rigorously tested, monitored, and reversible.

## Business Value

- **Risk Reduction**: Prevent $50K+ losses from unvalidated parameter changes
- **Confidence**: Enable safe parameter optimization with automated validation
- **Compliance**: Meet regulatory requirements for algorithm validation and audit trails
- **Performance**: Identify optimal parameters through systematic walk-forward testing
- **Stability**: Detect and prevent overfitting before it impacts live trading

## Success Metrics

1. **Backtesting Coverage**: 100% of parameter changes validated before live deployment
2. **Overfitting Detection**: Real-time monitoring with alerts when score > 0.3
3. **Walk-Forward Performance**: Out-of-sample Sharpe ratio > 70% of in-sample
4. **Position Sizing Accuracy**: <2% error vs. theoretical optimal sizing
5. **Configuration Audit**: 100% of changes tracked with rollback capability
6. **Validation Time**: Parameter changes validated within 24 hours (vs. current weeks)

## Technical Foundation

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│              Backtesting & Validation Layer                  │
├─────────────────────────────────────────────────────────────┤
│  • Historical Data Replay Engine                             │
│  • Walk-Forward Optimization Framework                       │
│  • Monte Carlo Simulation Engine                             │
│  • Overfitting Detection Monitor                             │
│  • Parameter Version Control System                          │
│  • Automated Validation Pipeline                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         Existing Trading System (8 AI Agents)                │
│  Market Analysis → Pattern Detection → Signal Generation     │
│  → Risk Management → Execution → Performance Tracking        │
└─────────────────────────────────────────────────────────────┘
```

### Data Requirements

- **Historical Market Data**: 2+ years of OHLCV data for all trading instruments
- **Execution Data**: All historical trades with slippage, timestamps, P&L
- **Signal History**: Generated signals (executed and rejected) with confidence scores
- **Parameter History**: All configuration changes with timestamps and authors

### Technology Stack

- **Backtesting Framework**: Python + Backtrader or custom framework
- **Data Storage**: TimescaleDB for historical market data
- **Version Control**: Git-based configuration management
- **Monitoring**: Prometheus + Grafana for real-time overfitting metrics
- **Testing**: Pytest + hypothesis for property-based testing

---

## Story 11.1: Historical Data Infrastructure

**As a** backtesting system,
**I want** comprehensive historical market data and execution records,
**So that** I can accurately replay past market conditions for validation.

### Acceptance Criteria

**AC1: Historical Market Data Collection**
- OHLCV data available for all 5 trading instruments (EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CHF)
- Minimum 2 years of historical 1H candle data
- Tick data available for last 6 months (for slippage modeling)
- Data quality validation (no gaps > 1 hour, outlier detection)
- Automated daily data refresh from OANDA API

**AC2: Historical Execution Database**
- All trades from production system stored in TimescaleDB
- Trade schema includes: entry/exit price, slippage, timestamps, P&L, signal_id
- Signal history database (both executed and rejected signals)
- Minimum 3 months of historical execution data for initial validation

**AC3: Data Access Layer**
- REST API endpoints for querying historical data by date range and instrument
- Efficient queries for walk-forward windows (3-month training, 1-month testing)
- Data export functionality for offline analysis
- Performance: Query 1 year of data in < 5 seconds

**AC4: Data Integrity Validation**
- Automated data quality checks on import (completeness, consistency)
- Outlier detection for anomalous price movements
- Gap detection and alerting for missing data periods
- Data backup and recovery procedures documented

### Technical Implementation Notes

```python
class HistoricalDataRepository:
    """Central repository for historical market and execution data"""

    async def get_market_data(
        self,
        instrument: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1H"
    ) -> pd.DataFrame:
        """Retrieve OHLCV data for specified period"""

    async def get_execution_history(
        self,
        start_date: datetime,
        end_date: datetime,
        instrument: str = None
    ) -> List[Trade]:
        """Retrieve historical trades"""

    async def get_signal_history(
        self,
        start_date: datetime,
        end_date: datetime,
        min_confidence: float = 0.0
    ) -> List[Signal]:
        """Retrieve historical signals (executed and rejected)"""
```

### Testing Requirements

- Unit tests for data retrieval API
- Integration tests with TimescaleDB
- Performance tests for large date ranges
- Data quality validation tests

---

## Story 11.2: Backtesting Framework Foundation

**As a** parameter optimizer,
**I want** to replay historical market conditions with different parameters,
**So that** I can validate parameter changes before live deployment.

### Acceptance Criteria

**AC1: Market Replay Engine with Anti-Contamination**
- Accurately replay historical OHLCV data bar-by-bar (no look-ahead bias)
- Support for multiple timeframes (15M, 1H, 4H, 1D)
- Realistic slippage modeling based on historical execution data
- Order execution simulation with proper fill logic (market, limit, stop orders)
- Trading session detection (Sydney, Tokyo, London, New York, Overlap)
- Strictly enforce chronological data access (no future data available at bar time)
- Separate data loaders for training vs. testing data (isolated data sources)
- Automated detection of look-ahead bias (unit test for each signal indicator)
- Walk-forward windows never overlap (training end < testing start - 1 day buffer)
- Log all data access timestamps for audit trail and contamination prevention

**AC2: Signal Generation Replay**
- Recreate Wyckoff pattern detection from historical data
- Recreate VPA analysis from historical volume data
- Generate signals using historical parameters (no data leakage)
- Track signal confidence, entry price, stop loss, take profit
- Support for both session-targeted and universal parameter modes

**AC3: Performance Metrics Calculation**
- Calculate Sharpe ratio, Sortino ratio, maximum drawdown
- Calculate win rate, profit factor, average R:R achieved
- Calculate total return, CAGR, recovery factor
- Per-instrument and per-session performance breakdown
- Risk-adjusted metrics (Calmar ratio, MAR ratio)

**AC4: Backtest Execution API**
- REST API endpoint: `POST /api/backtest/run`
- Input parameters: date range, instruments, parameter set, mode
- Output: Performance metrics, trade list, equity curve
- Support for parallel backtests (compare multiple parameter sets)
- Execution time: 1-year backtest completes in < 2 minutes

**AC5: Production Deployment Controls**
- Canary deployment: Deploy new parameters to 10% of signals for 24 hours before full rollout
- Monitor canary performance vs. baseline in real-time (alert if Sharpe drops >20%)
- Automated rollback if canary live Sharpe drops >30% vs. backtest within first 48h
- Two-person approval required for parameter changes >10% deviation from baseline
- Emergency rollback accessible via dashboard button with <5 minute deployment SLA
- Gradual rollout phases: 10% (24h) → 50% (48h) → 100% (full deployment)
- Deployment log with approval signatures and rollback capability preserved for 90 days

### Technical Implementation Notes

```python
class BacktestEngine:
    """Core backtesting engine for parameter validation"""

    def __init__(self, historical_data: HistoricalDataRepository):
        self.data_repo = historical_data
        self.current_positions = {}
        self.equity_curve = []
        self.trades = []

    async def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        parameters: Dict[str, Any],
        instruments: List[str]
    ) -> BacktestResult:
        """Run backtest with specified parameters"""

        for bar in self._replay_market_data(start_date, end_date):
            # Generate signals using historical data only (no look-ahead)
            signals = await self._generate_signals(bar, parameters)

            # Execute signals with slippage model
            trades = await self._execute_signals(signals, bar)

            # Update positions and equity
            self._update_positions(bar)
            self._update_equity(bar)

        return BacktestResult(
            sharpe_ratio=self._calculate_sharpe(),
            max_drawdown=self._calculate_max_drawdown(),
            trades=self.trades,
            equity_curve=self.equity_curve
        )
```

### Anti-Patterns to Avoid

**❌ Look-Ahead Bias**:
```python
# BAD: Using full candle data before candle closes
if current_candle.high > resistance:
    signal = "long"  # This knows the future!
```

**✅ Proper Implementation**:
```python
# GOOD: Only use data available at decision time
if previous_candle.close > resistance:
    signal = "long"  # Decision based on closed candle
```

### Testing Requirements

- Unit tests for market replay (no look-ahead bias)
- Validation tests against known historical performance
- Performance tests for backtest execution speed
- Integration tests with signal generation

---

## Story 11.3: Walk-Forward Optimization System

**As a** parameter validation system,
**I want** to test parameters on rolling out-of-sample windows,
**So that** I can detect overfitting and ensure parameter robustness.

### Acceptance Criteria

**AC1: Walk-Forward Framework**
- Configurable training window (default: 3 months)
- Configurable testing window (default: 1 month)
- Configurable step size (default: 1 month - rolling window)
- Support for anchored and rolling window approaches
- Minimum 12 walk-forward iterations for validation

**AC2: Parameter Optimization**
- Grid search over parameter ranges:
  - Confidence threshold: 50-90% (step: 5%)
  - Min risk-reward: 1.5-4.0 (step: 0.5)
  - VPA threshold: 0.5-0.8 (step: 0.1)
- Optimize on training window using Sharpe ratio as objective
- Validate on testing window (out-of-sample)
- Track in-sample vs. out-of-sample performance degradation

**AC3: Overfitting Detection**
- Calculate overfitting score: `(in_sample_sharpe - out_sample_sharpe) / in_sample_sharpe`
- Alert if out-of-sample Sharpe < 70% of in-sample Sharpe
- Alert if parameter deviation from universal baseline > 20%
- Calculate stability score across all walk-forward windows
- Reject parameters if overfitting detected

**AC4: Walk-Forward Reporting**
- Generate comprehensive report with:
  - Performance by walk-forward window
  - Parameter stability analysis
  - Overfitting score and alerts
  - Equity curve comparison (optimized vs. baseline)
- Export results to JSON and CSV formats
- Visualization of rolling performance metrics

**AC5: Performance Attribution Analysis**
- Track which parameters caused validation failures (confidence vs. R:R vs. VPA threshold)
- Generate sensitivity analysis report (±10% parameter variation impact on Sharpe)
- Validate session-specific parameters independently (Tokyo, London, NY, Sydney, Overlap)
- Detect market regime changes and re-validate parameters per regime
- Feature importance ranking showing which parameters drive performance most
- Root cause analysis report for failed validations with recommendations

### Technical Implementation Notes

```python
class WalkForwardOptimizer:
    """Walk-forward optimization for parameter validation"""

    def __init__(
        self,
        backtest_engine: BacktestEngine,
        training_window_days: int = 90,
        testing_window_days: int = 30,
        step_size_days: int = 30
    ):
        self.engine = backtest_engine
        self.training_window = timedelta(days=training_window_days)
        self.testing_window = timedelta(days=testing_window_days)
        self.step_size = timedelta(days=step_size_days)

    async def run_walk_forward(
        self,
        start_date: datetime,
        end_date: datetime,
        parameter_ranges: Dict[str, tuple]
    ) -> WalkForwardResult:
        """Run walk-forward optimization"""

        results = []
        current_date = start_date

        while current_date + self.training_window + self.testing_window <= end_date:
            # Training period
            train_start = current_date
            train_end = current_date + self.training_window

            # Testing period
            test_start = train_end
            test_end = test_start + self.testing_window

            # Optimize on training data
            best_params = await self._optimize_parameters(
                train_start, train_end, parameter_ranges
            )

            # Validate on testing data (out-of-sample)
            test_performance = await self.engine.run_backtest(
                test_start, test_end, best_params
            )

            # Calculate overfitting metrics
            overfitting_score = self._calculate_overfitting(
                train_performance, test_performance
            )

            results.append({
                "train_period": (train_start, train_end),
                "test_period": (test_start, test_end),
                "optimized_params": best_params,
                "train_sharpe": train_performance.sharpe_ratio,
                "test_sharpe": test_performance.sharpe_ratio,
                "overfitting_score": overfitting_score
            })

            # Move to next window
            current_date += self.step_size

        return WalkForwardResult(
            iterations=results,
            avg_overfitting_score=np.mean([r["overfitting_score"] for r in results]),
            stability_score=self._calculate_stability(results)
        )
```

### Walk-Forward Validation Criteria

**Accept Parameters If**:
- ✅ Avg out-of-sample Sharpe > 1.0
- ✅ Out-of-sample Sharpe > 70% of in-sample Sharpe
- ✅ Overfitting score < 0.3
- ✅ Max drawdown in testing < 20%
- ✅ Win rate stability variance < 10%

**Reject Parameters If**:
- ❌ Out-of-sample Sharpe < 0.5
- ❌ Out-of-sample Sharpe < 50% of in-sample Sharpe
- ❌ Overfitting score > 0.5
- ❌ Any testing period has max drawdown > 30%

### Testing Requirements

- Unit tests for walk-forward logic
- Validation tests with synthetic data (known results)
- Integration tests with backtest engine
- Performance tests for optimization speed

---

## Story 11.4: Real-Time Overfitting Monitor

**As a** trading system operator,
**I want** continuous monitoring of parameter drift and overfitting risk,
**So that** I can detect and respond to overfitting before it impacts performance.

### Acceptance Criteria

**AC1: Real-Time Overfitting Calculation**
- Calculate overfitting score every hour using current parameters
- Compare current parameters against universal baseline
- Track parameter drift over time (7-day, 30-day trends)
- Calculate deviation score for each session's parameters
- Store overfitting scores in time-series database

**AC2: Overfitting Alerts & Automated Responses**
- Alert when overfitting score > 0.3 (warning threshold) → Notify operators via Slack
- Critical alert when overfitting score > 0.5 → Auto-pause new parameter deployments
- Alert when parameter drift > 15% in 7 days → Require validation review
- Alert when out-of-sample performance degrades > 20% → Notify team lead
- Auto-rollback to baseline if live Sharpe < 50% of backtest for 3 consecutive days
- Emergency "safe mode" parameters pre-validated for crisis periods (max drawdown <10%)
- Escalation path defined: P3 (team lead/Slack) → P2 (director/email+call) → P1 (emergency stop trading)
- Manual override capability to pause automated parameter updates from dashboard
- Integrate alerts with Slack/email notifications with severity-based routing

**AC3: Performance Degradation Detection**
- Compare live performance vs. backtest expectations
- Track rolling 7-day Sharpe ratio
- Alert when live Sharpe < 70% of backtest Sharpe
- Monitor win rate, profit factor, average R:R
- Detect regime changes affecting parameter validity

**AC4: Monitoring Dashboard**
- Real-time overfitting score gauge (green/yellow/red zones)
- Historical overfitting score trend chart (30 days)
- Parameter drift visualization (deviation from baseline)
- Live vs. backtest performance comparison
- Recent alerts and recommendations panel

### Technical Implementation Notes

```python
class OverfittingMonitor:
    """Real-time overfitting detection and alerting"""

    def __init__(self, alert_service: AlertService):
        self.alert_service = alert_service
        self.baseline_params = UNIVERSAL_PARAMETERS

    async def calculate_overfitting_score(
        self,
        current_params: Dict[TradingSession, Dict]
    ) -> float:
        """Calculate overfitting score for current parameters"""

        deviations = []
        for session, params in current_params.items():
            # Confidence deviation (normalized by 50%)
            conf_dev = abs(
                params["confidence_threshold"] -
                self.baseline_params["confidence_threshold"]
            ) / 50.0

            # Risk-reward deviation (normalized by 3.0)
            rr_dev = (
                params["min_risk_reward"] -
                self.baseline_params["min_risk_reward"]
            ) / 3.0

            # Combined deviation
            combined_dev = conf_dev + rr_dev
            deviations.append(combined_dev)

        # Calculate score (40% avg, 40% max, 20% std dev)
        avg_dev = np.mean(deviations)
        max_dev = np.max(deviations)
        std_dev = np.std(deviations)

        overfitting_score = min(
            1.0,
            avg_dev * 0.4 + max_dev * 0.4 + std_dev * 0.2
        )

        # Store in time-series database
        await self._store_score(overfitting_score)

        # Check alert thresholds
        await self._check_alerts(overfitting_score)

        return overfitting_score

    async def _check_alerts(self, score: float):
        """Check overfitting score against thresholds"""
        if score > 0.5:
            await self.alert_service.send_critical_alert(
                "CRITICAL: Overfitting score {:.3f} > 0.5. "
                "Immediate parameter review required.".format(score)
            )
        elif score > 0.3:
            await self.alert_service.send_warning_alert(
                "WARNING: Overfitting score {:.3f} > 0.3. "
                "Parameter validation recommended.".format(score)
            )
```

### Monitoring Metrics

**Primary Metrics**:
1. **Overfitting Score**: Real-time calculation, target < 0.3
2. **Parameter Drift**: % change from baseline over 7/30 days
3. **Live vs. Backtest Sharpe**: Ratio of live/backtest performance
4. **Win Rate Stability**: Variance over rolling windows
5. **Drawdown Consistency**: Live vs. backtest max drawdown

**Secondary Metrics**:
6. **Signal Confidence Drift**: Average confidence over time
7. **R:R Achievement**: Actual vs. expected risk-reward
8. **Session Performance**: Per-session profit factor
9. **Instrument Correlation**: Detect over-concentration

### Alert Priorities

| Alert Type | Threshold | Priority | Response Time |
|-----------|-----------|----------|---------------|
| Critical Overfitting | Score > 0.5 | P1 | Immediate |
| Warning Overfitting | Score > 0.3 | P2 | 24 hours |
| Performance Degradation | Sharpe < 70% | P2 | 24 hours |
| Parameter Drift | >15% in 7 days | P3 | 1 week |
| Regime Change | Detected shift | P3 | Review |

### Testing Requirements

- Unit tests for overfitting score calculation
- Integration tests with alert service
- Validation tests with known overfitted parameters
- Performance tests for monitoring overhead

---

## Story 11.5: Enhanced Position Sizing System

**As a** risk management system,
**I want** accurate position sizing based on actual account balance and proper currency conversion,
**So that** risk per trade is consistent and correctly calculated.

### Acceptance Criteria

**AC1: Dynamic Account Balance Integration**
- Query actual account balance from OANDA API before each signal
- Cache account balance (refresh every 5 minutes)
- Use actual balance for position sizing calculations (not hardcoded $100k)
- Handle multiple accounts with different balances
- Alert if account balance < configured minimum ($5k)

**AC2: Accurate Pip Value Calculation**
- Implement proper pip value calculation for all instrument types:
  - Standard forex pairs (EUR_USD, GBP_USD, etc.): 0.0001
  - JPY pairs (USD_JPY, EUR_JPY, etc.): 0.01
  - XAU_USD (gold): 0.01
  - Crypto pairs (BTC_USD): 1.0
- Include currency conversion for non-USD account currencies
- Support for fractional pip pricing (pipettes)

**AC3: Improved Position Sizing Formula**
- Calculate position size using formula:
  ```
  Position Size = (Account Balance × Risk %) / (Stop Loss Pips × Pip Value in Account Currency)
  ```
- Apply maximum position limits:
  - Per-trade: 5% of account balance
  - Total open: 15% of account balance (portfolio heat)
  - Per-instrument: 10% of account balance
- Round position size to broker's minimum lot size requirements

**AC4: Position Sizing Validation**
- Validate calculated position size against broker limits
- Check margin requirements before order submission
- Ensure minimum margin buffer (e.g., $5000) maintained
- Log position sizing decisions for audit
- Alert on position sizing errors or constraints hit

### Technical Implementation Notes

```python
class EnhancedPositionSizer:
    """Accurate position sizing with real account data"""

    def __init__(self, oanda_client: OandaClient, config: Config):
        self.oanda_client = oanda_client
        self.config = config
        self.account_balance_cache = {}
        self.cache_expiry = timedelta(minutes=5)

    async def calculate_position_size(
        self,
        instrument: str,
        entry_price: float,
        stop_loss: float,
        account_id: str,
        risk_percent: float = 0.02
    ) -> int:
        """Calculate position size with accurate pip value and balance"""

        # Get actual account balance
        account_balance = await self._get_account_balance(account_id)

        # Calculate risk amount in account currency
        risk_amount = account_balance * risk_percent

        # Get accurate pip value for instrument
        pip_info = self._get_pip_info(instrument)
        pip_value_base = pip_info["pip_value"]
        precision = pip_info["precision"]

        # Convert pip value to account currency (if needed)
        pip_value_account = await self._convert_pip_value(
            instrument, pip_value_base, account_id
        )

        # Calculate stop distance in pips
        stop_distance_pips = abs(entry_price - stop_loss) / pip_value_base

        # Calculate position size
        position_size = int(risk_amount / (stop_distance_pips * pip_value_account))

        # Apply limits and constraints
        position_size = self._apply_position_limits(
            position_size,
            instrument,
            account_balance,
            account_id
        )

        # Validate margin requirements
        await self._validate_margin(
            instrument,
            position_size,
            entry_price,
            account_id
        )

        logger.info(
            f"Position sizing: {instrument} - "
            f"Balance: ${account_balance:.2f}, "
            f"Risk: {risk_percent:.1%}, "
            f"Stop: {stop_distance_pips:.1f} pips, "
            f"Size: {position_size} units"
        )

        return position_size

    def _get_pip_info(self, instrument: str) -> Dict[str, Any]:
        """Get accurate pip value and precision for instrument"""
        if "JPY" in instrument:
            return {"pip_value": 0.01, "precision": 3}
        elif any(metal in instrument for metal in ["XAU", "XAG", "GOLD", "SILVER"]):
            if "XAU" in instrument or "GOLD" in instrument:
                return {"pip_value": 0.01, "precision": 2}
            else:
                return {"pip_value": 0.001, "precision": 3}
        elif any(crypto in instrument for crypto in ["BTC", "ETH", "LTC"]):
            return {"pip_value": 1.0, "precision": 1}
        else:
            # Standard forex pairs
            return {"pip_value": 0.0001, "precision": 5}

    async def _convert_pip_value(
        self,
        instrument: str,
        pip_value_base: float,
        account_id: str
    ) -> float:
        """Convert pip value to account currency"""

        # Get account currency (USD for most accounts)
        account_info = await self.oanda_client.get_account(account_id)
        account_currency = account_info["currency"]

        # Parse instrument (e.g., "EUR_USD" -> base: EUR, quote: USD)
        base_currency, quote_currency = instrument.split("_")

        # If quote currency matches account currency, no conversion needed
        if quote_currency == account_currency:
            return pip_value_base * 1.0  # Standard lot size

        # Otherwise, need to convert quote currency to account currency
        conversion_rate = await self._get_exchange_rate(
            quote_currency,
            account_currency
        )

        return pip_value_base * conversion_rate

    def _apply_position_limits(
        self,
        position_size: int,
        instrument: str,
        account_balance: float,
        account_id: str
    ) -> int:
        """Apply position size limits and constraints"""

        # Maximum position size (5% of account balance)
        max_position_value = account_balance * 0.05
        max_position_units = int(max_position_value)  # Simplified
        position_size = min(position_size, max_position_units)

        # Check portfolio heat (total open positions risk)
        current_heat = self._calculate_portfolio_heat(account_id)
        if current_heat > 0.12:  # 12% heat, approaching 15% limit
            position_size = int(position_size * 0.5)  # Reduce by 50%
            logger.warning(
                f"Portfolio heat {current_heat:.1%} high, "
                f"reducing position size by 50%"
            )

        # Broker minimum/maximum limits
        min_units = 1000  # OANDA minimum
        max_units = 10000000  # OANDA maximum
        position_size = max(min_units, min(position_size, max_units))

        return position_size
```

### Position Sizing Formula Examples

**Example 1: EUR_USD Long**
```
Account Balance: $10,000
Risk Per Trade: 2%
Entry Price: 1.0850
Stop Loss: 1.0800
Stop Distance: 50 pips (0.0050)

Risk Amount = $10,000 × 0.02 = $200
Pip Value = 0.0001 (standard)
Position Size = $200 / (50 pips × $1 per pip per 10k units)
             = $200 / $50
             = 4 units of 10,000
             = 40,000 units total
```

**Example 2: USD_JPY Short**
```
Account Balance: $10,000
Risk Per Trade: 2%
Entry Price: 149.50
Stop Loss: 150.00
Stop Distance: 50 pips (0.50 in JPY)

Risk Amount = $10,000 × 0.02 = $200
Pip Value = 0.01 (JPY pair)
Position Size = $200 / (50 pips × $0.67 per pip per 10k units)
             = $200 / $33.50
             = 5.97 units of 10,000
             = 59,700 units (rounded to 60,000)
```

### Testing Requirements

- Unit tests for pip value calculation (all instrument types)
- Unit tests for position sizing formula
- Integration tests with OANDA API (account balance, margin)
- Validation tests with known correct position sizes
- Edge case tests (min/max limits, high portfolio heat)

---

## Story 11.6: Configuration Version Control System

**As a** system administrator,
**I want** version-controlled parameter configurations with audit trails,
**So that** I can track all changes, understand their impact, and rollback if needed.

### Acceptance Criteria

**AC1: Git-Based Configuration Management**
- All parameter configurations stored in YAML/JSON files
- Configuration files tracked in Git repository
- Each parameter change creates a Git commit with:
  - Author (person or automated system)
  - Timestamp
  - Reason for change (e.g., "Walk-forward optimization result")
  - Validation results (backtest metrics, overfitting score)
- Configuration versioning (semantic versioning: v1.0.0, v1.1.0, etc.)

**AC2: Configuration Schema Validation**
- JSON Schema validation for all configuration files
- Required fields enforced (confidence_threshold, min_risk_reward, etc.)
- Value range validation (e.g., confidence 0-100%, R:R > 0)
- Cross-field validation (e.g., max_risk_reward > min_risk_reward)
- Automatic validation on commit (pre-commit hook)

**AC3: Configuration Rollback Capability**
- One-command rollback to any previous configuration version
- Rollback preserves audit trail (creates new commit, doesn't rewrite history)
- Emergency rollback to "last known good" configuration
- Rollback validation (ensure rolled-back config passes current validation)
- Rollback notification to all relevant stakeholders

**AC4: Configuration Change Approval Workflow**
- Automated parameter changes require validation results attached
- Manual parameter changes require approval (code review in Git)
- Critical changes (>15% deviation) require two-person approval
- Configuration change log accessible via dashboard
- Integration with Slack for change notifications

### Technical Implementation Notes

```yaml
# config/parameters/session_targeted_v2.0.0.yaml
version: "2.0.0"
effective_date: "2025-10-08"
author: "WalkForwardOptimizer"
reason: "Optimized based on Q3 2025 walk-forward results"
validation:
  backtest_sharpe: 1.52
  out_of_sample_sharpe: 1.38
  overfitting_score: 0.274
  max_drawdown: 0.12
  approved_by: "Quinn (QA Architect)"
  approved_date: "2025-10-08"

baseline:
  confidence_threshold: 55.0
  min_risk_reward: 1.8
  source: "universal_cycle_4"

session_parameters:
  tokyo:
    confidence_threshold: 68.0
    min_risk_reward: 2.6
    max_risk_reward: 3.4
    volatility_adjustment: 0.15
    justification: "Tokyo session shows higher precision, justified by backtest"
    deviation_from_baseline:
      confidence: +13.0  # +23.6%
      risk_reward: +0.8  # +44.4%

  london:
    confidence_threshold: 66.0
    min_risk_reward: 2.5
    max_risk_reward: 3.2
    volatility_adjustment: 0.10
    justification: "London session high liquidity, moderate parameters"
    deviation_from_baseline:
      confidence: +11.0  # +20.0%
      risk_reward: +0.7  # +38.9%

  # ... other sessions

constraints:
  max_confidence_deviation: 15.0  # Max +15% from baseline
  max_risk_reward_deviation: 1.5  # Max +1.5 from baseline
  max_overfitting_score: 0.3
  min_backtest_sharpe: 1.2
  min_out_of_sample_ratio: 0.7  # Out-of-sample must be >70% of in-sample

alerts:
  overfitting_warning: 0.3
  overfitting_critical: 0.5
  performance_degradation: 0.2  # 20% drop
  parameter_drift_7d: 0.15  # 15% change in 7 days
```

### Configuration Management API

```python
class ConfigurationManager:
    """Version-controlled configuration management"""

    def __init__(self, config_repo_path: str):
        self.repo = git.Repo(config_repo_path)
        self.config_dir = Path(config_repo_path) / "config" / "parameters"

    async def load_current_config(self) -> ParameterConfig:
        """Load the currently active configuration"""
        active_link = self.config_dir / "active.yaml"
        with open(active_link) as f:
            return ParameterConfig.from_yaml(f)

    async def propose_new_config(
        self,
        new_params: Dict[str, Any],
        validation_results: ValidationResults,
        author: str,
        reason: str
    ) -> str:
        """Propose new configuration with validation results"""

        # Create new version
        current_version = await self._get_latest_version()
        new_version = self._increment_version(current_version)

        # Create configuration file
        config_file = self.config_dir / f"session_targeted_{new_version}.yaml"
        config_data = {
            "version": new_version,
            "effective_date": datetime.now().isoformat(),
            "author": author,
            "reason": reason,
            "validation": validation_results.to_dict(),
            "session_parameters": new_params
        }

        # Validate against schema
        self._validate_config_schema(config_data)

        # Write configuration file
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Git commit
        self.repo.index.add([str(config_file)])
        commit = self.repo.index.commit(
            f"Propose parameter config {new_version}\n\n"
            f"Author: {author}\n"
            f"Reason: {reason}\n"
            f"Overfitting Score: {validation_results.overfitting_score:.3f}\n"
            f"Backtest Sharpe: {validation_results.sharpe_ratio:.2f}\n"
        )

        return commit.hexsha

    async def rollback_to_version(
        self,
        version: str,
        reason: str,
        author: str
    ):
        """Rollback to a previous configuration version"""

        # Find configuration file for version
        config_file = self.config_dir / f"session_targeted_{version}.yaml"
        if not config_file.exists():
            raise ValueError(f"Configuration version {version} not found")

        # Create rollback commit (don't rewrite history)
        rollback_version = await self._get_latest_version()
        new_version = self._increment_version(rollback_version)

        # Copy old config to new version
        rollback_file = self.config_dir / f"session_targeted_{new_version}.yaml"
        shutil.copy(config_file, rollback_file)

        # Update metadata
        with open(rollback_file, "r") as f:
            config_data = yaml.safe_load(f)

        config_data["version"] = new_version
        config_data["effective_date"] = datetime.now().isoformat()
        config_data["rollback"] = {
            "from_version": rollback_version,
            "to_version": version,
            "reason": reason,
            "author": author
        }

        with open(rollback_file, "w") as f:
            yaml.dump(config_data, f)

        # Update active link
        active_link = self.config_dir / "active.yaml"
        active_link.unlink()
        active_link.symlink_to(rollback_file)

        # Git commit
        self.repo.index.add([str(rollback_file), str(active_link)])
        self.repo.index.commit(
            f"ROLLBACK: Revert to parameters {version}\n\n"
            f"Reason: {reason}\n"
            f"Author: {author}\n"
            f"Rolling back from {rollback_version} to {version}\n"
        )

        logger.info(f"Configuration rolled back to {version}")

        # Send notifications
        await self._notify_rollback(version, reason)
```

### Configuration Change Workflow

```
┌─────────────────────────────────────────────────────────┐
│  1. Walk-Forward Optimizer generates new parameters      │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  2. Validation Results attached (Sharpe, overfitting)    │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  3. ConfigurationManager.propose_new_config()            │
│     - Creates new version file                           │
│     - Validates schema                                   │
│     - Creates Git commit                                 │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  4. Code Review (for manual changes) or auto-approve     │
│     - Review validation results                          │
│     - Check overfitting score < 0.3                      │
│     - Approve or reject                                  │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  5. Deploy to Production                                 │
│     - Update "active.yaml" symlink                       │
│     - Notify all agents to reload config                 │
│     - Monitor performance closely (first 24h)            │
└─────────────────────────────────────────────────────────┘
```

### Testing Requirements

- Unit tests for configuration loading and validation
- Integration tests with Git repository
- Validation tests for schema enforcement
- Rollback tests (ensure config restored correctly)
- Approval workflow tests

---

## Story 11.7: Automated Parameter Validation Pipeline

**As a** continuous integration system,
**I want** to automatically validate all parameter changes before deployment,
**So that** only validated, safe parameters reach production.

### Acceptance Criteria

**AC1: Pre-Deployment Validation Pipeline**
- Triggered automatically on parameter configuration changes (Git commit)
- Runs comprehensive validation suite:
  1. Schema validation (correct format, required fields)
  2. Range validation (parameters within acceptable bounds)
  3. Overfitting score calculation
  4. Walk-forward backtest (last 6 months)
  5. Monte Carlo simulation (1000 runs)
  6. Stress test (2008 crisis, COVID crash scenarios)
- Pipeline completes within 30 minutes
- Results posted to PR/commit for review

**AC2: Automated Acceptance Criteria**
- Parameters must pass all validation checks to be approved:
  - ✅ Schema valid
  - ✅ Overfitting score < 0.3
  - ✅ Walk-forward out-of-sample Sharpe > 1.0
  - ✅ Max drawdown in backtest < 20%
  - ✅ Win rate > 45%
  - ✅ Profit factor > 1.3
- If all checks pass, mark as "Ready for Deployment"
- If any check fails, block deployment and alert author

**AC3: Monte Carlo Validation**
- Run 1000 Monte Carlo simulations with parameter randomization:
  - Entry price: ±5 pips variation
  - Exit timing: ±2 hour variation
  - Slippage: 0-3 pips variation
- Calculate confidence intervals for performance metrics:
  - 95% CI for Sharpe ratio
  - 95% CI for max drawdown
  - 95% CI for win rate
- Reject if lower bound of 95% CI for Sharpe < 0.8

**AC4: Stress Testing & Benchmarking**
- Replay parameters during historical crisis periods:
  - 2008 Financial Crisis (Sep-Dec 2008)
  - 2015 CHF Flash Crash (Jan 15, 2015)
  - 2020 COVID Crash (Mar 2020)
- Ensure maximum drawdown < 25% during crisis
- Ensure recovery within 90 days post-crisis
- Alert if parameters show fragility to extreme events
- Compare Sharpe ratio against baseline strategy benchmarks:
  - Buy-and-hold S&P 500
  - Simple moving average crossover (50/200)
  - Previous parameter version (regression testing)
- Validate backtest results match at least one third-party platform (e.g., QuantConnect, TradingView)
- Document any discrepancies between platforms with root cause analysis
- Include benchmark comparison in validation report (must exceed baseline by >0.5 Sharpe)

**AC5: Resource Management & Cost Control**
- Limit parallel backtests to 5 concurrent jobs (queue additional jobs with priority ranking)
- Validation pipeline timeout: 45 minutes hard cutoff to prevent runaway jobs
- Automated cleanup: Delete detailed backtest results >6 months old (keep summary metrics only)
- Monthly cost report: Track compute usage, storage costs, API calls
- Alert if monthly infrastructure costs exceed $500 budget
- Backtest queue prioritization: Critical (parameter rollback) > High (production validation) > Low (research)
- Resource allocation limits: Max 8 CPU cores, 16GB RAM per backtest job
- Automatic resource scaling: Increase limits for walk-forward jobs (up to 16 cores, 32GB RAM)

### Technical Implementation Notes

```python
class ValidationPipeline:
    """Automated parameter validation pipeline"""

    def __init__(
        self,
        backtest_engine: BacktestEngine,
        walk_forward: WalkForwardOptimizer,
        monte_carlo: MonteCarloSimulator
    ):
        self.backtest_engine = backtest_engine
        self.walk_forward = walk_forward
        self.monte_carlo = monte_carlo

    async def validate_parameter_change(
        self,
        new_params: Dict[str, Any],
        baseline_params: Dict[str, Any]
    ) -> ValidationResult:
        """Run comprehensive validation pipeline"""

        results = {
            "schema_validation": None,
            "overfitting_score": None,
            "walk_forward_results": None,
            "monte_carlo_results": None,
            "stress_test_results": None,
            "acceptance": None
        }

        # 1. Schema Validation
        logger.info("Running schema validation...")
        schema_valid = self._validate_schema(new_params)
        results["schema_validation"] = schema_valid
        if not schema_valid:
            results["acceptance"] = "REJECTED - Schema validation failed"
            return ValidationResult(**results)

        # 2. Overfitting Score Calculation
        logger.info("Calculating overfitting score...")
        overfitting_score = self._calculate_overfitting_score(
            new_params, baseline_params
        )
        results["overfitting_score"] = overfitting_score
        if overfitting_score > 0.3:
            results["acceptance"] = f"REJECTED - Overfitting score {overfitting_score:.3f} > 0.3"
            return ValidationResult(**results)

        # 3. Walk-Forward Validation (6 months)
        logger.info("Running walk-forward validation...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)

        wf_results = await self.walk_forward.run_walk_forward(
            start_date, end_date, new_params
        )
        results["walk_forward_results"] = wf_results

        # Check walk-forward acceptance criteria
        if wf_results.avg_out_of_sample_sharpe < 1.0:
            results["acceptance"] = (
                f"REJECTED - Out-of-sample Sharpe {wf_results.avg_out_of_sample_sharpe:.2f} < 1.0"
            )
            return ValidationResult(**results)

        if wf_results.max_drawdown > 0.20:
            results["acceptance"] = (
                f"REJECTED - Max drawdown {wf_results.max_drawdown:.1%} > 20%"
            )
            return ValidationResult(**results)

        # 4. Monte Carlo Simulation
        logger.info("Running Monte Carlo simulation (1000 runs)...")
        mc_results = await self.monte_carlo.run_simulation(
            new_params, num_runs=1000
        )
        results["monte_carlo_results"] = mc_results

        # Check confidence intervals
        sharpe_ci_lower = mc_results.sharpe_95ci_lower
        if sharpe_ci_lower < 0.8:
            results["acceptance"] = (
                f"REJECTED - Monte Carlo 95% CI lower bound {sharpe_ci_lower:.2f} < 0.8"
            )
            return ValidationResult(**results)

        # 5. Stress Testing
        logger.info("Running stress tests...")
        stress_results = await self._run_stress_tests(new_params)
        results["stress_test_results"] = stress_results

        if stress_results.max_crisis_drawdown > 0.25:
            results["acceptance"] = (
                f"WARNING - Crisis drawdown {stress_results.max_crisis_drawdown:.1%} > 25%. "
                f"Review recommended but not blocking."
            )

        # All checks passed
        results["acceptance"] = "APPROVED - All validation checks passed"
        return ValidationResult(**results)

    async def _run_stress_tests(
        self,
        params: Dict[str, Any]
    ) -> StressTestResults:
        """Run stress tests on historical crisis periods"""

        crisis_periods = [
            {
                "name": "2008 Financial Crisis",
                "start": datetime(2008, 9, 1),
                "end": datetime(2008, 12, 31)
            },
            {
                "name": "2015 CHF Flash Crash",
                "start": datetime(2015, 1, 10),
                "end": datetime(2015, 1, 20)
            },
            {
                "name": "2020 COVID Crash",
                "start": datetime(2020, 3, 1),
                "end": datetime(2020, 3, 31)
            }
        ]

        crisis_results = []
        for crisis in crisis_periods:
            # Run backtest during crisis period
            result = await self.backtest_engine.run_backtest(
                crisis["start"], crisis["end"], params
            )

            crisis_results.append({
                "name": crisis["name"],
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "total_return": result.total_return
            })

        return StressTestResults(
            crisis_results=crisis_results,
            max_crisis_drawdown=max(r["max_drawdown"] for r in crisis_results)
        )
```

### CI/CD Integration

```yaml
# .github/workflows/validate-parameters.yml
name: Validate Parameter Changes

on:
  pull_request:
    paths:
      - 'config/parameters/**'
  push:
    branches:
      - main
    paths:
      - 'config/parameters/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 45

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run validation pipeline
        run: |
          python scripts/validate_parameters.py \
            --config-file ${{ github.event.pull_request.changed_files }} \
            --output-file validation_results.json

      - name: Post validation results
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('validation_results.json'));

            const comment = `
            ## Parameter Validation Results

            **Status**: ${results.acceptance}

            ### Metrics
            - **Overfitting Score**: ${results.overfitting_score.toFixed(3)} (Target: < 0.3)
            - **Walk-Forward Sharpe**: ${results.walk_forward_results.avg_out_of_sample_sharpe.toFixed(2)}
            - **Max Drawdown**: ${(results.walk_forward_results.max_drawdown * 100).toFixed(1)}%
            - **Monte Carlo 95% CI**: [${results.monte_carlo_results.sharpe_95ci_lower.toFixed(2)}, ${results.monte_carlo_results.sharpe_95ci_upper.toFixed(2)}]

            ### Acceptance Criteria
            - ✅ Schema Valid
            - ${results.overfitting_score < 0.3 ? '✅' : '❌'} Overfitting Score < 0.3
            - ${results.walk_forward_results.avg_out_of_sample_sharpe >= 1.0 ? '✅' : '❌'} Out-of-Sample Sharpe >= 1.0
            - ${results.walk_forward_results.max_drawdown <= 0.20 ? '✅' : '❌'} Max Drawdown <= 20%
            - ${results.monte_carlo_results.sharpe_95ci_lower >= 0.8 ? '✅' : '❌'} Monte Carlo CI Lower >= 0.8

            ${results.acceptance.startsWith('APPROVED') ? '✅ **Ready for Deployment**' : '❌ **Deployment Blocked**'}
            `;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });

      - name: Fail if validation rejected
        if: ${{ !startsWith(fromJSON('validation_results.json').acceptance, 'APPROVED') }}
        run: exit 1
```

### Testing Requirements

- Unit tests for each validation step
- Integration tests for full pipeline
- Mock data tests with known pass/fail scenarios
- Performance tests (pipeline completes < 30 min)

---

## Story 11.8: Validation Dashboard & Reporting

**As a** trading system operator,
**I want** a comprehensive dashboard showing validation metrics and parameter history,
**So that** I can monitor system health and make informed decisions.

### Acceptance Criteria

**AC1: Real-Time Validation Dashboard**
- Dashboard page: `/dashboard/validation`
- Key metrics displayed:
  - Current overfitting score (gauge with green/yellow/red zones)
  - Live vs. backtest performance comparison
  - Rolling 30-day Sharpe ratio trend
  - Parameter drift visualization (vs. baseline)
  - Recent validation results (last 10 parameter changes)
- Auto-refresh every 60 seconds

**AC2: Parameter History Timeline**
- Interactive timeline showing all parameter changes
- Each change displays:
  - Version number and date
  - Author and reason
  - Validation metrics (Sharpe, overfitting score, drawdown)
  - Performance impact (before/after comparison)
- Click to view detailed validation report
- Ability to compare any two versions side-by-side

**AC3: Walk-Forward Validation Reports**
- Detailed report for each walk-forward validation run
- Includes:
  - Equity curve visualization (in-sample vs. out-of-sample)
  - Performance by session (Tokyo, London, NY, etc.)
  - Parameter stability table (variations across windows)
  - Overfitting score history
  - Trade distribution analysis
- Export to PDF for record-keeping

**AC4: Alert Dashboard**
- Centralized view of all validation alerts
- Alert types:
  - Overfitting warnings (score > 0.3)
  - Performance degradation (live < 70% of backtest)
  - Parameter drift (>15% change in 7 days)
  - Validation pipeline failures
- Alert history with resolution tracking
- Integration with Slack/email notifications

### Technical Implementation Notes

```typescript
// Dashboard component (React/Next.js)
interface ValidationDashboardProps {
  currentOverfittingScore: number;
  livePerformance: PerformanceMetrics;
  backtestPerformance: PerformanceMetrics;
  parameterHistory: ParameterVersion[];
  recentAlerts: Alert[];
}

export function ValidationDashboard({
  currentOverfittingScore,
  livePerformance,
  backtestPerformance,
  parameterHistory,
  recentAlerts
}: ValidationDashboardProps) {
  return (
    <div className="validation-dashboard">
      <h1>Algorithm Validation & Monitoring</h1>

      {/* Real-time metrics */}
      <div className="metrics-row">
        <OverfittingScoreGauge
          score={currentOverfittingScore}
          thresholds={{ warning: 0.3, critical: 0.5 }}
        />

        <PerformanceComparison
          live={livePerformance}
          backtest={backtestPerformance}
        />

        <SharpeRatioTrend
          data={livePerformance.rollingSharpeTrend}
          period={30}
        />
      </div>

      {/* Parameter history */}
      <ParameterHistoryTimeline
        versions={parameterHistory}
        onVersionClick={showDetailedReport}
      />

      {/* Recent alerts */}
      <AlertsPanel
        alerts={recentAlerts}
        onAlertClick={showAlertDetails}
      />

      {/* Walk-forward reports */}
      <WalkForwardReportsTable
        reports={getRecentWalkForwardReports()}
      />
    </div>
  );
}
```

### Dashboard API Endpoints

```python
# Validation dashboard API
@router.get("/api/validation/current-metrics")
async def get_current_validation_metrics() -> ValidationMetrics:
    """Get current validation metrics for dashboard"""
    return {
        "overfitting_score": await overfitting_monitor.get_current_score(),
        "live_performance": await performance_tracker.get_live_metrics(days=30),
        "backtest_performance": await backtest_cache.get_latest_results(),
        "parameter_drift": await config_manager.calculate_parameter_drift(),
        "last_updated": datetime.now().isoformat()
    }

@router.get("/api/validation/parameter-history")
async def get_parameter_history(limit: int = 50) -> List[ParameterVersion]:
    """Get parameter change history"""
    return await config_manager.get_version_history(limit=limit)

@router.get("/api/validation/walk-forward-reports")
async def get_walk_forward_reports(limit: int = 10) -> List[WalkForwardReport]:
    """Get recent walk-forward validation reports"""
    return await walk_forward_service.get_recent_reports(limit=limit)

@router.get("/api/validation/alerts")
async def get_validation_alerts(
    status: str = "active",
    limit: int = 50
) -> List[Alert]:
    """Get validation alerts"""
    return await alert_service.get_alerts(
        category="validation",
        status=status,
        limit=limit
    )
```

### Testing Requirements

- Component tests for dashboard UI
- Integration tests for API endpoints
- E2E tests for user workflows
- Performance tests for dashboard load time

---

## Story 11.9: Data Governance & Retention Policies

**As a** system administrator and compliance officer,
**I want** comprehensive data governance policies with automated retention and recovery procedures,
**So that** we maintain regulatory compliance while managing storage costs effectively.

### Acceptance Criteria

**AC1: Data Retention Policies**
- 7-year audit trail retention for all parameter changes (matches NFR-11.13 and regulatory requirements)
- Historical market data retained for 5 years in hot storage, archived to cold storage thereafter
- Trade execution data retained for 7 years (3 years hot storage, 4 years cold storage)
- Signal history retained for 2 years (executed and rejected signals)
- Backtest detailed results retained for 6 months, summary metrics retained for 5 years
- Walk-forward validation reports retained for 3 years
- Automated archival process runs monthly to migrate old data to cold storage

**AC2: Data Recovery SLAs**
- Hot storage recovery (data <3 years old): RTO <1 hour, RPO <24 hours
- Cold storage recovery (data >3 years old): RTO <4 hours, RPO <7 days
- Critical configuration rollback: RTO <5 minutes (in-memory cache + Git)
- Quarterly recovery drills documented with success/failure metrics
- Automated daily backups with 30-day retention for disaster recovery
- Point-in-time recovery capability for TimescaleDB (7-day window)

**AC3: Data Quality & Integrity**
- Automated data validation on import (schema validation, completeness checks)
- Daily data quality reports with alerts for anomalies:
  - Missing data gaps >1 hour
  - Price outliers (>10 standard deviations)
  - Volume anomalies (>5x average)
  - Duplicate timestamp detection
- Data lineage tracking (source, transformation, destination)
- Cryptographic checksums for archived data integrity verification
- Monthly data quality scorecard (target: >99.5% quality score)

**AC4: Data Anonymization & Privacy**
- Personal trading data (if any) anonymized before archival (GDPR compliance)
- API keys and credentials encrypted at rest using HashiCorp Vault
- Access logs for sensitive data (audit who accessed what, when)
- Data access controls: role-based permissions (Admin, Operator, Read-only)
- Data export capabilities with anonymization for external sharing/analysis
- Compliance with data residency requirements (data stored in US/EU regions only)

**AC5: Storage Cost Management**
- Monthly storage cost tracking and reporting (target: <$200/month)
- Automated cleanup of temporary backtest files (>24 hours old)
- Compression for archived data (target: 5:1 compression ratio)
- Tiered storage strategy:
  - Hot: SSD for data <6 months (fast queries)
  - Warm: HDD for data 6 months - 3 years (moderate queries)
  - Cold: Object storage (S3/Glacier) for data >3 years (rare access)
- Alert if storage growth exceeds 20% month-over-month (investigate data bloat)
- Annual storage audit to identify and purge unnecessary data

### Technical Implementation Notes

```python
class DataGovernanceManager:
    """Data retention, recovery, and quality management"""

    def __init__(
        self,
        timescale_db: TimescaleDB,
        archive_storage: S3Client,
        vault_client: VaultClient
    ):
        self.db = timescale_db
        self.archive = archive_storage
        self.vault = vault_client

    async def apply_retention_policies(self):
        """Apply data retention policies (runs monthly)"""

        current_date = datetime.now()

        # Archive market data >5 years old to cold storage
        archive_cutoff = current_date - timedelta(days=5*365)
        old_market_data = await self.db.query(
            "SELECT * FROM market_data WHERE timestamp < %s",
            (archive_cutoff,)
        )

        if old_market_data:
            # Compress and archive to S3 Glacier
            compressed = self._compress_data(old_market_data)
            await self.archive.upload(
                bucket="trading-data-archive",
                key=f"market_data/{archive_cutoff.year}.parquet.gz",
                data=compressed,
                storage_class="GLACIER"
            )

            # Delete from hot storage after successful archive
            await self.db.execute(
                "DELETE FROM market_data WHERE timestamp < %s",
                (archive_cutoff,)
            )

            logger.info(
                f"Archived {len(old_market_data)} market data records "
                f"from {archive_cutoff}"
            )

        # Delete detailed backtest results >6 months old (keep summaries)
        backtest_cutoff = current_date - timedelta(days=180)
        await self.db.execute(
            "DELETE FROM backtest_trades WHERE backtest_date < %s",
            (backtest_cutoff,)
        )
        await self.db.execute(
            "DELETE FROM backtest_equity_curves WHERE backtest_date < %s",
            (backtest_cutoff,)
        )

        # Keep summary metrics
        logger.info(f"Deleted detailed backtest data older than {backtest_cutoff}")

    async def perform_recovery_drill(self) -> RecoveryDrillResult:
        """Quarterly recovery drill to test backup/restore procedures"""

        drill_start = datetime.now()
        results = {
            "hot_storage_recovery": None,
            "cold_storage_recovery": None,
            "config_rollback": None
        }

        # Test 1: Hot storage recovery (restore last 24h of market data)
        try:
            test_data = await self._simulate_data_loss(hours=24)
            restore_start = datetime.now()
            await self._restore_from_hot_backup(test_data)
            restore_time = (datetime.now() - restore_start).total_seconds()

            results["hot_storage_recovery"] = {
                "status": "PASS" if restore_time < 3600 else "FAIL",
                "rto_seconds": restore_time,
                "target_seconds": 3600
            }
        except Exception as e:
            results["hot_storage_recovery"] = {
                "status": "FAIL",
                "error": str(e)
            }

        # Test 2: Cold storage recovery (restore archived data)
        try:
            restore_start = datetime.now()
            await self._restore_from_cold_storage(year=2020)
            restore_time = (datetime.now() - restore_start).total_seconds()

            results["cold_storage_recovery"] = {
                "status": "PASS" if restore_time < 14400 else "FAIL",
                "rto_seconds": restore_time,
                "target_seconds": 14400
            }
        except Exception as e:
            results["cold_storage_recovery"] = {
                "status": "FAIL",
                "error": str(e)
            }

        # Test 3: Configuration rollback (simulate parameter revert)
        try:
            restore_start = datetime.now()
            await self._test_config_rollback()
            restore_time = (datetime.now() - restore_start).total_seconds()

            results["config_rollback"] = {
                "status": "PASS" if restore_time < 300 else "FAIL",
                "rto_seconds": restore_time,
                "target_seconds": 300
            }
        except Exception as e:
            results["config_rollback"] = {
                "status": "FAIL",
                "error": str(e)
            }

        drill_duration = (datetime.now() - drill_start).total_seconds()

        return RecoveryDrillResult(
            drill_date=drill_start,
            duration_seconds=drill_duration,
            tests=results,
            overall_status="PASS" if all(
                r["status"] == "PASS" for r in results.values()
            ) else "FAIL"
        )

    async def generate_data_quality_report(self) -> DataQualityReport:
        """Generate daily data quality report"""

        # Check for missing data gaps
        gaps = await self.db.query("""
            SELECT instrument, timestamp,
                   LAG(timestamp) OVER (PARTITION BY instrument ORDER BY timestamp) as prev_timestamp
            FROM market_data
            WHERE timestamp >= NOW() - INTERVAL '7 days'
        """)

        significant_gaps = [
            g for g in gaps
            if g["timestamp"] - g["prev_timestamp"] > timedelta(hours=1)
        ]

        # Check for price outliers
        outliers = await self.db.query("""
            SELECT instrument, timestamp, close,
                   AVG(close) OVER (PARTITION BY instrument ORDER BY timestamp ROWS BETWEEN 100 PRECEDING AND CURRENT ROW) as avg_close,
                   STDDEV(close) OVER (PARTITION BY instrument ORDER BY timestamp ROWS BETWEEN 100 PRECEDING AND CURRENT ROW) as stddev_close
            FROM market_data
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            HAVING ABS(close - avg_close) > 10 * stddev_close
        """)

        # Check for volume anomalies
        volume_anomalies = await self.db.query("""
            SELECT instrument, timestamp, volume,
                   AVG(volume) OVER (PARTITION BY instrument ORDER BY timestamp ROWS BETWEEN 100 PRECEDING AND CURRENT ROW) as avg_volume
            FROM market_data
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            HAVING volume > 5 * avg_volume
        """)

        # Calculate quality score
        total_records = await self.db.query_scalar(
            "SELECT COUNT(*) FROM market_data WHERE timestamp >= NOW() - INTERVAL '7 days'"
        )

        quality_issues = len(significant_gaps) + len(outliers) + len(volume_anomalies)
        quality_score = 1.0 - (quality_issues / total_records) if total_records > 0 else 0.0

        return DataQualityReport(
            date=datetime.now(),
            total_records=total_records,
            missing_data_gaps=len(significant_gaps),
            price_outliers=len(outliers),
            volume_anomalies=len(volume_anomalies),
            quality_score=quality_score,
            status="PASS" if quality_score >= 0.995 else "FAIL"
        )

    async def calculate_storage_costs(self) -> StorageCostReport:
        """Calculate monthly storage costs"""

        # Query storage usage by tier
        hot_storage_gb = await self._get_storage_usage("hot")
        warm_storage_gb = await self._get_storage_usage("warm")
        cold_storage_gb = await self._get_storage_usage("cold")

        # Pricing (example rates)
        hot_cost = hot_storage_gb * 0.10  # $0.10/GB/month (SSD)
        warm_cost = warm_storage_gb * 0.05  # $0.05/GB/month (HDD)
        cold_cost = cold_storage_gb * 0.01  # $0.01/GB/month (S3 Glacier)

        total_cost = hot_cost + warm_cost + cold_cost

        return StorageCostReport(
            month=datetime.now().strftime("%Y-%m"),
            hot_storage_gb=hot_storage_gb,
            warm_storage_gb=warm_storage_gb,
            cold_storage_gb=cold_storage_gb,
            hot_cost_usd=hot_cost,
            warm_cost_usd=warm_cost,
            cold_cost_usd=cold_cost,
            total_cost_usd=total_cost,
            budget_usd=200.0,
            status="PASS" if total_cost <= 200.0 else "OVER_BUDGET"
        )
```

### Data Retention Schedule

| Data Type | Hot Storage | Warm Storage | Cold Storage | Total Retention |
|-----------|-------------|--------------|--------------|-----------------|
| Parameter Changes | 7 years | - | - | 7 years |
| Market Data (OHLCV) | 6 months | 6mo-5yr | >5 years | Indefinite |
| Trade Execution | 3 years | 3-7 years | >7 years | 7+ years |
| Signal History | 2 years | - | - | 2 years |
| Backtest Details | 6 months | - | - | 6 months |
| Backtest Summaries | 5 years | - | - | 5 years |
| Walk-Forward Reports | 3 years | - | - | 3 years |
| System Logs | 90 days | 90d-1yr | - | 1 year |

### Recovery Time Objectives (RTOs)

| Recovery Scenario | Target RTO | Target RPO | Testing Frequency |
|-------------------|-----------|-----------|-------------------|
| Hot Storage Failure | <1 hour | <24 hours | Quarterly |
| Cold Storage Restore | <4 hours | <7 days | Quarterly |
| Config Rollback | <5 minutes | 0 (Git) | Quarterly |
| Complete System Rebuild | <8 hours | <48 hours | Annually |

### Testing Requirements

- Unit tests for retention policy logic
- Integration tests with TimescaleDB and S3
- Quarterly recovery drill automation
- Data quality validation tests
- Storage cost calculation tests
- Anonymization function tests (GDPR compliance)

---

## Dependencies & Integration Points

### Upstream Dependencies
- **TimescaleDB**: Historical market data storage
- **OANDA API**: Real-time and historical price data
- **Existing Signal Generation**: Market Analysis and Pattern Detection agents
- **Git**: Configuration version control

### Downstream Consumers
- **Orchestrator**: Uses validated parameters for live trading
- **Market Analysis Agent**: Loads current parameters from config system
- **Dashboard**: Displays validation metrics and parameter history
- **Alert System**: Receives overfitting and performance alerts

### Integration Sequence
1. **Phase 1**: Historical data infrastructure (Story 11.1)
2. **Phase 2**: Backtesting framework (Story 11.2)
3. **Phase 3**: Walk-forward optimization (Story 11.3)
4. **Phase 4**: Real-time monitoring (Story 11.4)
5. **Phase 5**: Position sizing enhancement (Story 11.5)
6. **Phase 6**: Configuration management (Story 11.6)
7. **Phase 7**: Validation pipeline (Story 11.7)
8. **Phase 8**: Dashboard & reporting (Story 11.8)
9. **Phase 9**: Data governance & retention (Story 11.9)

---

## Non-Functional Requirements

### Performance
- **NFR-11.1**: Walk-forward optimization (1 year data) completes in < 10 minutes
- **NFR-11.2**: Real-time overfitting calculation overhead < 100ms
- **NFR-11.3**: Validation pipeline completes in < 30 minutes
- **NFR-11.4**: Dashboard page load time < 2 seconds
- **NFR-11.5**: Historical data queries return in < 5 seconds

### Scalability
- **NFR-11.6**: Support 5+ years of historical data without performance degradation
- **NFR-11.7**: Handle 100+ parameter versions in Git repository
- **NFR-11.8**: Support 10+ concurrent backtests

### Reliability
- **NFR-11.9**: Validation pipeline failure rate < 1%
- **NFR-11.10**: Overfitting monitoring uptime > 99.5%
- **NFR-11.11**: Data backup and recovery in < 1 hour

### Security
- **NFR-11.12**: Configuration changes require authentication and authorization
- **NFR-11.13**: Audit trail for all parameter changes (7-year retention)
- **NFR-11.14**: Rollback capability tested quarterly

### Maintainability
- **NFR-11.15**: Code coverage > 80% for all validation components
- **NFR-11.16**: Documentation for all APIs and validation procedures
- **NFR-11.17**: Monitoring alerts with clear remediation steps

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Historical data quality issues | Medium | High | Automated data validation, outlier detection |
| Backtesting framework bugs (look-ahead bias) | Medium | Critical | Rigorous testing, code review, validation against known results |
| Walk-forward optimization too slow | Medium | Medium | Performance optimization, parallel processing, cloud compute |
| Overfitting still occurs despite monitoring | Low | High | Multiple layers of validation, conservative thresholds, human oversight |
| Configuration rollback failures | Low | Critical | Quarterly rollback drills, automated testing, backup configs |
| Validation pipeline overwhelms system | Low | Medium | Rate limiting, resource allocation, queue management |

---

## Success Criteria

Epic 11 is considered successful when:

1. **✅ 100% Parameter Validation**: All parameter changes validated through walk-forward testing before production
2. **✅ Zero Overfitting Incidents**: No overfitting crises (score > 0.5) for 6 months
3. **✅ Improved Parameter Performance**: New parameters show out-of-sample Sharpe > 1.2
4. **✅ Rapid Rollback**: Configuration rollback < 5 minutes from detection to deployment
5. **✅ Operator Confidence**: Operators rate validation tools as "very useful" (4.5/5 survey score)
6. **✅ Audit Compliance**: Pass external audit for algorithm validation procedures
7. **✅ Position Sizing Accuracy**: <2% error in risk-per-trade vs. theoretical target
8. **✅ Reduced Manual Effort**: 80% reduction in time spent manually validating parameters
9. **✅ Data Recovery Success**: Quarterly recovery drills pass with 100% success rate
10. **✅ Storage Cost Control**: Monthly storage costs remain under $200 budget
11. **✅ Data Quality**: >99.5% data quality score maintained consistently

---

## Timeline & Effort Estimates

| Story | Effort (days) | Dependencies | Priority |
|-------|--------------|--------------|----------|
| 11.1: Historical Data Infrastructure | 5 | None | P0 (Critical) |
| 11.2: Backtesting Framework | 10 | 11.1 | P0 (Critical) |
| 11.3: Walk-Forward Optimization | 8 | 11.2 | P0 (Critical) |
| 11.4: Real-Time Overfitting Monitor | 5 | 11.2 | P1 (High) |
| 11.5: Enhanced Position Sizing | 3 | None | P1 (High) |
| 11.6: Configuration Version Control | 5 | None | P1 (High) |
| 11.7: Automated Validation Pipeline | 8 | 11.2, 11.3, 11.6 | P1 (High) |
| 11.8: Validation Dashboard | 5 | 11.4, 11.6 | P2 (Medium) |
| 11.9: Data Governance & Retention | 6 | 11.1 | P1 (High) |

**Total Estimated Effort**: 55 developer-days (~11 weeks with 1 developer, ~6 weeks with 2 developers)

**Recommended Approach**: 2 developers working in parallel
- Developer 1: Data & backtesting (Stories 11.1, 11.2, 11.3, 11.9)
- Developer 2: Monitoring & config (Stories 11.4, 11.5, 11.6)
- Both: Validation pipeline & dashboard (Stories 11.7, 11.8)

---

## Appendix: Glossary

- **Overfitting**: When parameters perform well on historical data but poorly on unseen data
- **Walk-Forward Optimization**: Testing parameters on rolling windows to detect overfitting
- **Sharpe Ratio**: Risk-adjusted return metric (return / volatility)
- **Maximum Drawdown**: Largest peak-to-trough decline in equity
- **Look-Ahead Bias**: Using future information in backtesting (invalidates results)
- **Out-of-Sample**: Data not used during parameter optimization (for validation)
- **Parameter Drift**: Gradual change in parameter values over time
- **Confidence Threshold**: Minimum signal confidence required for trade execution
- **Risk-Reward Ratio**: Expected profit vs. expected loss on a trade
- **Portfolio Heat**: Total risk exposure across all open positions

---

**Document Version**: 1.0
**Created**: 2025-10-08
**Authors**: Quinn (QA Architect), James (Development Lead)
**Status**: Draft - Ready for Story Breakdown
**Next Steps**: Create individual user stories for development sprint planning
