# Risk Parameters and Limits

## Overview

This document defines all risk parameters, limits, and thresholds used throughout the TMT trading system. These parameters are critical for maintaining system safety and regulatory compliance.

## System-Wide Risk Parameters

### Global Risk Limits

#### Maximum Exposure Limits
```yaml
global_limits:
  max_total_exposure: 0.50          # 50% of total capital
  max_single_instrument: 0.20       # 20% per instrument
  max_correlated_positions: 0.30    # 30% for correlated pairs
  max_account_correlation: 0.25     # 25% correlation between accounts
```

#### Drawdown Limits
```yaml
drawdown_limits:
  warning_threshold: 0.05           # 5% account drawdown warning
  critical_threshold: 0.08          # 8% account drawdown critical
  emergency_stop: 0.10              # 10% emergency stop
  daily_loss_limit: 0.02            # 2% daily loss limit
  weekly_loss_limit: 0.05           # 5% weekly loss limit
  monthly_loss_limit: 0.08          # 8% monthly loss limit
```

#### Position Sizing Limits
```yaml
position_sizing:
  max_risk_per_trade: 0.015         # 1.5% risk per trade
  min_risk_reward_ratio: 2.0        # Minimum 1:2 risk/reward
  max_position_size: 0.10           # 10% of account per position
  max_daily_trades: 10              # Maximum trades per day per account
  max_concurrent_positions: 5       # Maximum open positions per account
```

### Currency Pair Specific Limits

#### Major Pairs (EUR/USD, GBP/USD, USD/JPY, AUD/USD)
```yaml
major_pairs:
  max_exposure: 0.15                # 15% per major pair
  max_position_size: 100000         # 1 standard lot maximum
  min_stop_distance: 20             # 20 pip minimum stop loss
  max_stop_distance: 100            # 100 pip maximum stop loss
  slippage_tolerance: 2             # 2 pip slippage tolerance
```

#### Minor Pairs (Cross currencies)
```yaml
minor_pairs:
  max_exposure: 0.10                # 10% per minor pair
  max_position_size: 50000          # 0.5 standard lot maximum
  min_stop_distance: 30             # 30 pip minimum stop loss
  max_stop_distance: 150            # 150 pip maximum stop loss
  slippage_tolerance: 3             # 3 pip slippage tolerance
```

#### Exotic Pairs (Emerging market currencies)
```yaml
exotic_pairs:
  max_exposure: 0.05                # 5% per exotic pair
  max_position_size: 25000          # 0.25 standard lot maximum
  min_stop_distance: 50             # 50 pip minimum stop loss
  max_stop_distance: 200            # 200 pip maximum stop loss
  slippage_tolerance: 5             # 5 pip slippage tolerance
```

## Account-Level Risk Parameters

### Account Classification

#### Conservative Accounts
```yaml
conservative_accounts:
  max_risk_per_trade: 0.01          # 1% risk per trade
  max_daily_risk: 0.02              # 2% daily risk
  max_drawdown: 0.05                # 5% maximum drawdown
  max_leverage: 20                  # 20:1 maximum leverage
  required_win_rate: 0.60           # 60% required win rate
```

#### Moderate Accounts
```yaml
moderate_accounts:
  max_risk_per_trade: 0.015         # 1.5% risk per trade
  max_daily_risk: 0.03              # 3% daily risk
  max_drawdown: 0.08                # 8% maximum drawdown
  max_leverage: 50                  # 50:1 maximum leverage
  required_win_rate: 0.55           # 55% required win rate
```

#### Aggressive Accounts
```yaml
aggressive_accounts:
  max_risk_per_trade: 0.02          # 2% risk per trade
  max_daily_risk: 0.04              # 4% daily risk
  max_drawdown: 0.12                # 12% maximum drawdown
  max_leverage: 100                 # 100:1 maximum leverage
  required_win_rate: 0.50           # 50% required win rate
```

### Account Size Adjustments

#### Small Accounts ($10,000 - $25,000)
```yaml
small_accounts:
  position_size_multiplier: 0.5     # 50% of standard position size
  max_concurrent_positions: 3       # Maximum 3 open positions
  max_daily_trades: 5               # Maximum 5 trades per day
  emergency_stop_buffer: 0.02       # 2% buffer before emergency stop
```

#### Medium Accounts ($25,000 - $100,000)
```yaml
medium_accounts:
  position_size_multiplier: 1.0     # Standard position sizing
  max_concurrent_positions: 5       # Maximum 5 open positions
  max_daily_trades: 8               # Maximum 8 trades per day
  emergency_stop_buffer: 0.015      # 1.5% buffer before emergency stop
```

#### Large Accounts ($100,000+)
```yaml
large_accounts:
  position_size_multiplier: 1.5     # 150% of standard position size
  max_concurrent_positions: 8       # Maximum 8 open positions
  max_daily_trades: 12              # Maximum 12 trades per day
  emergency_stop_buffer: 0.01       # 1% buffer before emergency stop
```

## Time-Based Risk Controls

### Market Session Controls

#### Asian Session (00:00-09:00 UTC)
```yaml
asian_session:
  reduced_position_size: 0.8        # 80% of normal position size
  max_risk_per_trade: 0.01          # 1% maximum risk per trade
  allowed_instruments:              # Limited instrument set
    - "USD_JPY"
    - "AUD_USD"
    - "NZD_USD"
  volatility_adjustment: 1.2        # 20% higher volatility expectation
```

#### London Session (08:00-17:00 UTC)
```yaml
london_session:
  normal_position_size: 1.0         # Normal position sizing
  max_risk_per_trade: 0.015         # 1.5% maximum risk per trade
  allowed_instruments:              # Full instrument set
    - "EUR_USD"
    - "GBP_USD"
    - "EUR_GBP"
    - "USD_CHF"
  volatility_adjustment: 1.0        # Normal volatility expectation
```

#### New York Session (13:00-22:00 UTC)
```yaml
new_york_session:
  enhanced_position_size: 1.1       # 110% of normal position size
  max_risk_per_trade: 0.02          # 2% maximum risk per trade
  allowed_instruments:              # Full instrument set with USD focus
    - "EUR_USD"
    - "GBP_USD"
    - "USD_JPY"
    - "USD_CAD"
  volatility_adjustment: 0.9        # 10% lower volatility expectation
```

### Economic Event Risk Controls

#### High Impact Events
```yaml
high_impact_events:
  pre_event_window: 30              # 30 minutes before event
  post_event_window: 60             # 60 minutes after event
  position_reduction: 0.5           # 50% position size reduction
  new_position_block: true          # Block new positions
  stop_loss_tightening: 0.8         # Tighten stops to 80% of normal
```

#### Medium Impact Events
```yaml
medium_impact_events:
  pre_event_window: 15              # 15 minutes before event
  post_event_window: 30             # 30 minutes after event
  position_reduction: 0.8           # 80% position size reduction
  new_position_block: false         # Allow new positions
  stop_loss_tightening: 0.9         # Tighten stops to 90% of normal
```

## Correlation Risk Management

### Correlation Thresholds

#### Currency Correlation Limits
```yaml
correlation_limits:
  high_correlation: 0.80            # 80% correlation threshold
  medium_correlation: 0.60          # 60% correlation threshold
  low_correlation: 0.40             # 40% correlation threshold
  
  max_high_corr_exposure: 0.20      # 20% max exposure to highly correlated pairs
  max_medium_corr_exposure: 0.35    # 35% max exposure to medium correlated pairs
  correlation_lookback: 60          # 60 days correlation calculation period
```

#### Account Correlation Controls
```yaml
account_correlation:
  max_account_correlation: 0.30     # 30% maximum correlation between accounts
  correlation_measurement_period: 30 # 30 days measurement period
  rebalancing_threshold: 0.35       # Trigger rebalancing at 35% correlation
  
  correlation_reduction_methods:
    - timing_variance              # Vary entry/exit timing
    - size_variance               # Vary position sizes
    - instrument_rotation         # Rotate trading instruments
    - strategy_diversification    # Use different strategy variants
```

## Volatility-Based Risk Adjustments

### ATR-Based Position Sizing
```yaml
atr_position_sizing:
  atr_period: 14                    # 14-period ATR calculation
  atr_multiplier: 1.5               # 1.5x ATR for stop loss distance
  
  volatility_bands:
    low_volatility:                 # ATR < 0.5% of price
      position_multiplier: 1.2      # 20% larger positions
      stop_multiplier: 1.0          # Normal stop distance
    
    normal_volatility:              # ATR 0.5% - 1.5% of price
      position_multiplier: 1.0      # Normal position size
      stop_multiplier: 1.0          # Normal stop distance
    
    high_volatility:                # ATR > 1.5% of price
      position_multiplier: 0.7      # 30% smaller positions
      stop_multiplier: 1.5          # 50% wider stops
```

### VIX-Based Adjustments
```yaml
vix_adjustments:
  vix_thresholds:
    low_fear: 15                    # VIX below 15
    normal_fear: 25                 # VIX 15-25
    high_fear: 35                   # VIX above 25
  
  risk_adjustments:
    low_fear:
      risk_multiplier: 1.1          # 10% higher risk tolerance
      position_multiplier: 1.0      # Normal position sizes
    
    normal_fear:
      risk_multiplier: 1.0          # Normal risk tolerance
      position_multiplier: 1.0      # Normal position sizes
    
    high_fear:
      risk_multiplier: 0.8          # 20% lower risk tolerance
      position_multiplier: 0.7      # 30% smaller positions
```

## Circuit Breaker Parameters

### System-Level Circuit Breakers

#### Loss-Based Circuit Breakers
```yaml
loss_circuit_breakers:
  daily_loss_threshold: 0.03        # 3% daily loss triggers circuit breaker
  weekly_loss_threshold: 0.06       # 6% weekly loss triggers circuit breaker
  monthly_loss_threshold: 0.10      # 10% monthly loss triggers circuit breaker
  
  circuit_breaker_duration:
    daily: 1440                     # 24 hours (1440 minutes)
    weekly: 10080                   # 7 days (10080 minutes)
    monthly: 43200                  # 30 days (43200 minutes)
```

#### Error-Based Circuit Breakers
```yaml
error_circuit_breakers:
  execution_error_rate: 0.05        # 5% execution error rate
  platform_error_rate: 0.10        # 10% platform error rate
  data_error_rate: 0.15             # 15% data error rate
  
  error_measurement_window: 60      # 60 minutes measurement window
  circuit_breaker_duration: 30     # 30 minutes circuit breaker duration
```

### Account-Level Circuit Breakers

#### Performance-Based Circuit Breakers
```yaml
performance_circuit_breakers:
  consecutive_losses: 5             # 5 consecutive losing trades
  win_rate_threshold: 0.30          # 30% win rate over 20 trades
  profit_factor_threshold: 0.8      # Profit factor below 0.8
  
  measurement_period: 20            # 20 trades for win rate calculation
  circuit_breaker_duration: 120    # 2 hours circuit breaker duration
```

## Risk Monitoring and Alerts

### Alert Thresholds

#### Level 1 Alerts (Informational)
```yaml
level_1_alerts:
  account_drawdown: 0.03            # 3% account drawdown
  daily_loss: 0.015                 # 1.5% daily loss
  position_concentration: 0.25      # 25% single instrument exposure
  correlation_increase: 0.25        # 25% correlation between accounts
```

#### Level 2 Alerts (Warning)
```yaml
level_2_alerts:
  account_drawdown: 0.05            # 5% account drawdown
  daily_loss: 0.025                 # 2.5% daily loss
  position_concentration: 0.35      # 35% single instrument exposure
  correlation_increase: 0.35        # 35% correlation between accounts
```

#### Level 3 Alerts (Critical)
```yaml
level_3_alerts:
  account_drawdown: 0.08            # 8% account drawdown
  daily_loss: 0.035                 # 3.5% daily loss
  position_concentration: 0.45      # 45% single instrument exposure
  correlation_increase: 0.45        # 45% correlation between accounts
```

### Automated Risk Responses

#### Automatic Position Reduction
```yaml
automatic_reductions:
  trigger_conditions:
    - account_drawdown > 0.06       # 6% account drawdown
    - daily_loss > 0.03             # 3% daily loss
    - high_correlation > 0.40       # 40% account correlation
  
  reduction_actions:
    position_size_reduction: 0.5    # Reduce position sizes by 50%
    close_weakest_positions: 2      # Close 2 weakest performing positions
    stop_new_positions: true        # Stop opening new positions
```

#### Emergency Stop Triggers
```yaml
emergency_stops:
  immediate_triggers:
    - account_drawdown > 0.10       # 10% account drawdown
    - daily_loss > 0.05             # 5% daily loss
    - platform_disconnect > 300    # 5 minutes platform disconnection
    - execution_latency > 1000      # 1 second execution latency
  
  emergency_actions:
    close_all_positions: true       # Close all open positions
    cancel_all_orders: true         # Cancel all pending orders
    disable_trading: true           # Disable all trading activity
    notify_risk_manager: true       # Immediate notification to risk manager
```

## Configuration Management

### Parameter Updates
- All risk parameter changes require Risk Manager approval
- Changes are version controlled and auditable
- Staging environment testing required before production deployment
- Rollback procedures documented and tested

### Parameter Validation
- All parameters validated against business rules before deployment
- Automated testing of parameter ranges and interactions
- Performance impact assessment for parameter changes
- Compliance verification for regulatory requirements

### Documentation Requirements
- All parameter changes documented with business justification
- Risk impact assessment required for significant changes
- Change approval process includes technical and business review
- Parameter effectiveness monitored and reported monthly

For parameter configuration procedures, see [Risk Management Configuration Guide](../user-guide/risk-configuration.md).