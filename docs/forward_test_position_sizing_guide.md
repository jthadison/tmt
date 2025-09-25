# Forward Test-Based Position Sizing Controls

## Overview

The Forward Test Position Sizing system implements dynamic position size controls based on forward testing results, incorporating multiple layers of risk adjustment to address the identified issues in the 6-month backtest analysis.

## Key Issues Addressed

Based on the forward testing analysis, the system addresses these critical concerns:

- **Walk-forward stability**: 34.4/100 (Target: >60/100)
- **Out-of-sample validation**: 17.4/100 (Target: >70/100)
- **Overfitting score**: 0.634 (Target: <0.3)
- **High kurtosis exposure**: 20.316 (tail risk)

## Features

### 1. Dynamic Risk Adjustment

Position sizes are dynamically adjusted based on:

#### Stability Levels
- **CRITICAL** (<30/100): 75% size reduction
- **LOW** (30-50/100): 60% size reduction
- **MEDIUM** (50-70/100): 40% size reduction
- **HIGH** (70-90/100): 15% size reduction
- **EXCELLENT** (>90/100): No reduction

#### Validation Scores
- **POOR** (<30/100): 80% size reduction
- **WEAK** (30-50/100): 65% size reduction
- **MODERATE** (50-70/100): 45% size reduction
- **GOOD** (70-85/100): 20% size reduction
- **STRONG** (>85/100): No reduction

### 2. Kurtosis Protection

Tail risk controls based on kurtosis levels:
- **Normal** (<3.0): No adjustment
- **Moderate** (3.0-7.0): 10% reduction
- **High** (7.0-15.0): 30% reduction
- **Very High** (15.0-25.0): 50% reduction
- **Extreme** (>25.0): 75% reduction

### 3. Phased Capital Allocation

Progressive capital deployment based on performance metrics:

#### Phase 1 (10% Capital)
- Stability: ≥50/100
- Validation: ≥50/100
- Data: ≥8 months

#### Phase 2 (25% Capital)
- Stability: ≥60/100
- Validation: ≥60/100
- Data: ≥9 months

#### Phase 3 (50% Capital)
- Stability: ≥70/100
- Validation: ≥70/100
- Data: ≥10 months

#### Phase 4 (100% Capital)
- Stability: ≥80/100
- Validation: ≥80/100
- Data: ≥12 months

### 4. Session-Specific Limits

Optimized position limits for each trading session:

#### Tokyo Session
- Max Position: 20%
- Max Risk: 1.8%
- Confidence Threshold: 85%
- Risk-Reward: 4.0+

#### London Session
- Max Position: 25%
- Max Risk: 2.2%
- Confidence Threshold: 72%
- Risk-Reward: 3.2+

#### New York Session
- Max Position: 22%
- Max Risk: 2.0%
- Confidence Threshold: 70%
- Risk-Reward: 2.8+

#### Sydney Session
- Max Position: 15%
- Max Risk: 1.5%
- Confidence Threshold: 78%
- Risk-Reward: 3.5+

#### Overlap Periods
- Max Position: 18%
- Max Risk: 1.6%
- Confidence Threshold: 70%
- Risk-Reward: 2.8+

### 5. Volatility Adjustment

Dynamic sizing based on market volatility:
- **Low Volatility**: 20% size increase
- **Normal Volatility**: No adjustment
- **High Volatility**: 30% size reduction
- **Extreme Volatility**: 70% size reduction

## API Endpoints

### Get Position Sizing Status
```
GET /position-sizing/forward-test/status
```

Returns current metrics, levels, and capital allocation phase.

### Update Forward Test Metrics
```
POST /position-sizing/forward-test/update-metrics
Content-Type: application/json

{
  "walk_forward_stability": 65.0,
  "out_of_sample_validation": 72.0,
  "overfitting_score": 0.28,
  "kurtosis_exposure": 8.5,
  "months_of_data": 8
}
```

### Toggle Forward Test Sizing
```
POST /position-sizing/forward-test/toggle
```

Returns instructions for enabling/disabling the system.

## Configuration

### Environment Variables

- `USE_FORWARD_TEST_SIZING`: Enable/disable (default: "true")
- `TRADING_MODE`: "paper" or "live" (default: "paper")

### Current Settings

The system is initialized with current forward test results:
- Walk-forward stability: 34.4/100
- Out-of-sample validation: 17.4/100
- Overfitting score: 0.634
- Kurtosis exposure: 20.316
- Months of data: 6

This results in:
- Phase 1 capital allocation (10%)
- Significant position size reductions
- Enhanced safety controls

## Usage Example

```python
from app.forward_test_position_sizing import get_forward_test_sizing
from app.models import TradingSession

# Get the sizing engine
sizing_engine = get_forward_test_sizing()

# Calculate enhanced position size
result = await sizing_engine.calculate_enhanced_position_size(
    signal=trade_signal,
    account_id="demo-account",
    oanda_client=oanda_client,
    current_session=TradingSession.LONDON
)

# Check results
if result.is_safe_to_trade:
    position_units = result.recommended_units
    print(f"Position: {position_units} units")
    print(f"Phase: {result.current_allocation_phase}")
    print(f"Stability reduction: {result.stability_reduction_factor:.2f}")
else:
    print("Trade blocked by forward test controls")
    print(result.forward_test_warnings)
```

## Monitoring

The system provides comprehensive logging and warnings:

### Critical Warnings
- Walk-forward stability very low
- Out-of-sample validation very poor
- High overfitting risk detected
- High tail risk detected

### Performance Tracking
- Real-time adjustment factor calculations
- Session-specific performance metrics
- Phase progression monitoring
- Risk control effectiveness

## Improvement Path

As forward test metrics improve, the system automatically:

1. **Reduces position size penalties**
2. **Advances to higher capital allocation phases**
3. **Relaxes session-specific restrictions**
4. **Enables more aggressive sizing**

Target metrics for full deployment:
- Walk-forward stability: >80/100
- Out-of-sample validation: >80/100
- Overfitting score: <0.3
- Additional validation data: 12+ months

## Safety Features

### Multiple Safety Layers
1. **Pre-trade concentration checks**
2. **Portfolio heat monitoring**
3. **Margin availability verification**
4. **Signal quality validation**
5. **Session appropriateness checks**

### Emergency Controls
- Automatic sizing reduction on poor metrics
- Phase-based capital limits
- Kurtosis protection mechanisms
- Volatility-based adjustments

### Rollback Capability
The system can instantly revert to standard position sizing by setting:
```
USE_FORWARD_TEST_SIZING=false
```

This provides immediate rollback to the previous Cycle 4 configuration if issues arise.

## Integration

The forward test position sizing integrates seamlessly with:
- Trade Executor
- Risk Management Systems
- Circuit Breakers
- Emergency Rollback
- Dashboard Monitoring

Position size calculations are performed in real-time for each trading signal, with comprehensive logging and monitoring throughout the process.