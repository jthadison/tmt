# Position Sizing Rules and Calculations

## Overview

This document defines the position sizing methodology, rules, and calculations used by the TMT trading system to manage risk and optimize returns across all trading accounts.

## Position Sizing Philosophy

### Core Principles

1. **Risk-First Approach**: Position size determined by maximum acceptable risk per trade
2. **Account Protection**: Never risk more than can be afforded to lose
3. **Consistency**: Standardized approach across all accounts and instruments
4. **Adaptability**: Dynamic adjustment based on market conditions and performance
5. **Compliance**: Adherence to prop firm rules and regulatory requirements

### Risk Management Framework
```
Account Balance → Risk per Trade → Position Size → Trade Execution → Performance Monitoring
      ↓              ↓               ↓               ↓                    ↓
   Available     Maximum Loss     Units/Lots    Entry/Exit        Position Impact
   Capital       Amount           to Trade      Execution         Assessment
```

## Base Position Sizing Calculation

### Standard Formula

#### Risk-Based Position Sizing
```python
def calculate_position_size(account_balance, risk_percentage, entry_price, stop_loss_price, instrument_specs):
    """
    Calculate position size based on risk parameters
    
    Args:
        account_balance: Current account balance
        risk_percentage: Maximum risk per trade (e.g., 0.015 for 1.5%)
        entry_price: Planned entry price
        stop_loss_price: Stop loss price
        instrument_specs: Instrument-specific parameters
    
    Returns:
        Position size in units
    """
    # Calculate risk amount in account currency
    risk_amount = account_balance * risk_percentage
    
    # Calculate stop loss distance in pips
    pip_value = instrument_specs['pip_value']
    stop_distance_pips = abs(entry_price - stop_loss_price) / pip_value
    
    # Calculate position size
    if stop_distance_pips == 0:
        return 0
    
    position_size = risk_amount / (stop_distance_pips * instrument_specs['pip_cost'])
    
    # Apply constraints
    position_size = apply_position_constraints(position_size, account_balance, instrument_specs)
    
    return round(position_size, instrument_specs['precision'])
```

### Instrument-Specific Parameters

#### Major Currency Pairs
```yaml
EUR_USD:
  pip_value: 0.0001
  pip_cost: 1.0  # $1 per pip per 10k units
  min_position: 1000
  max_position: 1000000
  precision: 0
  
GBP_USD:
  pip_value: 0.0001
  pip_cost: 1.0
  min_position: 1000
  max_position: 1000000
  precision: 0
  
USD_JPY:
  pip_value: 0.01
  pip_cost: 0.93  # Approximate, varies with rate
  min_position: 1000
  max_position: 1000000
  precision: 0
```

#### Minor Currency Pairs
```yaml
EUR_GBP:
  pip_value: 0.0001
  pip_cost: 1.31  # Approximate GBP to USD conversion
  min_position: 1000
  max_position: 500000
  precision: 0
  
AUD_CAD:
  pip_value: 0.0001
  pip_cost: 0.74  # Approximate conversion factors
  min_position: 1000
  max_position: 500000
  precision: 0
```

## Position Sizing Rules

### Account-Level Rules

#### Risk per Trade Limits
```yaml
account_risk_limits:
  conservative:
    max_risk_per_trade: 0.01      # 1.0% maximum
    recommended_risk: 0.005       # 0.5% recommended
    
  moderate:
    max_risk_per_trade: 0.015     # 1.5% maximum
    recommended_risk: 0.01        # 1.0% recommended
    
  aggressive:
    max_risk_per_trade: 0.02      # 2.0% maximum
    recommended_risk: 0.015       # 1.5% recommended
```

#### Account Size Adjustments
```python
def get_account_risk_multiplier(account_balance):
    """Adjust risk based on account size"""
    if account_balance < 10000:
        return 0.8  # Reduce risk for small accounts
    elif account_balance < 25000:
        return 0.9  # Slightly reduced risk
    elif account_balance < 100000:
        return 1.0  # Standard risk
    else:
        return 1.2  # Slightly increased risk for large accounts
```

### Instrument-Level Rules

#### Position Size Limits by Instrument Type
```yaml
position_limits:
  major_pairs:
    max_position_percent: 0.15    # 15% of account value
    max_single_trade: 100000      # 1 standard lot
    
  minor_pairs:
    max_position_percent: 0.10    # 10% of account value  
    max_single_trade: 50000       # 0.5 standard lot
    
  exotic_pairs:
    max_position_percent: 0.05    # 5% of account value
    max_single_trade: 25000       # 0.25 standard lot
```

#### Correlation-Based Adjustments
```python
def adjust_for_correlation(base_position_size, instrument, existing_positions, correlation_matrix):
    """
    Adjust position size based on existing correlated positions
    """
    correlation_exposure = 0
    
    for existing_pos in existing_positions:
        if existing_pos['instrument'] != instrument:
            correlation = correlation_matrix.get_correlation(instrument, existing_pos['instrument'])
            if abs(correlation) > 0.6:  # High correlation threshold
                correlation_exposure += abs(existing_pos['size']) * abs(correlation)
    
    # Reduce position size if high correlation exposure exists
    if correlation_exposure > base_position_size * 0.5:
        adjustment_factor = 0.5  # Reduce by 50%
        return base_position_size * adjustment_factor
    
    return base_position_size
```

## Dynamic Position Sizing

### Volatility-Based Adjustments

#### ATR (Average True Range) Integration
```python
def volatility_adjusted_position_size(base_size, current_atr, avg_atr, volatility_factor=1.5):
    """
    Adjust position size based on current volatility relative to average
    """
    if avg_atr == 0:
        return base_size
    
    volatility_ratio = current_atr / avg_atr
    
    if volatility_ratio > volatility_factor:
        # High volatility - reduce position size
        adjustment = 1 / (volatility_ratio / volatility_factor)
        return base_size * min(adjustment, 0.5)  # Max 50% reduction
    elif volatility_ratio < (1 / volatility_factor):
        # Low volatility - potentially increase position size
        adjustment = 1 + ((1 / volatility_factor) - volatility_ratio) * 0.5
        return base_size * min(adjustment, 1.5)  # Max 50% increase
    else:
        # Normal volatility
        return base_size
```

### Performance-Based Adjustments

#### Winning/Losing Streak Adjustments
```python
class PerformanceAdjuster:
    def __init__(self):
        self.streak_threshold = 3
        self.max_adjustment = 0.5
    
    def calculate_streak_adjustment(self, recent_trades):
        """
        Adjust position size based on recent trading performance
        """
        if len(recent_trades) < self.streak_threshold:
            return 1.0
        
        # Calculate winning/losing streaks
        current_streak = self.calculate_current_streak(recent_trades)
        
        if current_streak['type'] == 'winning' and current_streak['length'] >= 5:
            # Reduce size after extended winning streak (avoid overconfidence)
            return 1.0 - (min(current_streak['length'] - 4, 3) * 0.1)
        elif current_streak['type'] == 'losing' and current_streak['length'] >= 3:
            # Reduce size after losing streak (preserve capital)
            return 1.0 - (min(current_streak['length'] - 2, 3) * 0.15)
        
        return 1.0
```

### Market Condition Adjustments

#### Session-Based Sizing
```yaml
session_adjustments:
  asian_session:
    time_range: "00:00-09:00 UTC"
    size_multiplier: 0.8
    reason: "Lower volatility and liquidity"
    
  london_session:
    time_range: "08:00-17:00 UTC"  
    size_multiplier: 1.0
    reason: "Standard volatility and liquidity"
    
  new_york_session:
    time_range: "13:00-22:00 UTC"
    size_multiplier: 1.1
    reason: "Higher volatility and liquidity"
    
  overlap_periods:
    london_ny_overlap:
      time_range: "13:00-17:00 UTC"
      size_multiplier: 1.2
      reason: "Highest volatility and liquidity"
```

#### News Event Adjustments
```python
def news_event_adjustment(base_size, upcoming_events, time_to_event):
    """
    Adjust position size based on upcoming high-impact news events
    """
    high_impact_events = [event for event in upcoming_events if event['impact'] == 'HIGH']
    
    if not high_impact_events:
        return base_size
    
    # Find the closest high-impact event
    closest_event_time = min([event['time_minutes'] for event in high_impact_events])
    
    if closest_event_time <= 30:  # 30 minutes before event
        return base_size * 0.5  # Reduce position size by 50%
    elif closest_event_time <= 60:  # 60 minutes before event
        return base_size * 0.7  # Reduce position size by 30%
    
    return base_size
```

## Risk Management Integration

### Multi-Account Position Sizing

#### Account Correlation Limits
```python
def multi_account_position_sizing(accounts, new_trade, correlation_matrix):
    """
    Calculate position size considering correlations across accounts
    """
    total_correlation_exposure = 0
    
    for account in accounts:
        for position in account['positions']:
            correlation = correlation_matrix.get_correlation(
                new_trade['instrument'], 
                position['instrument']
            )
            
            if abs(correlation) > 0.5:  # Significant correlation
                exposure_value = position['size'] * position['current_price']
                total_correlation_exposure += exposure_value * abs(correlation)
    
    # Adjust position size to limit total correlation exposure
    max_correlation_exposure = sum([acc['balance'] for acc in accounts]) * 0.3  # 30% limit
    
    if total_correlation_exposure > max_correlation_exposure:
        reduction_factor = max_correlation_exposure / total_correlation_exposure
        return new_trade['base_position_size'] * reduction_factor
    
    return new_trade['base_position_size']
```

### Portfolio Heat Calculation

#### Heat-Based Position Sizing
```python
def calculate_portfolio_heat(positions, risk_per_position):
    """
    Calculate total portfolio heat (total risk if all positions hit stop loss)
    """
    total_heat = sum([pos['size'] * pos['risk_per_pip'] * pos['stop_distance'] 
                      for pos in positions])
    return total_heat

def heat_adjusted_position_size(base_size, current_heat, max_heat_threshold, account_balance):
    """
    Adjust position size based on current portfolio heat
    """
    max_heat = account_balance * max_heat_threshold  # e.g., 10% of account
    
    if current_heat >= max_heat:
        return 0  # No new positions when at heat limit
    
    available_heat = max_heat - current_heat
    
    # Calculate what position size would add to heat
    # This is simplified - actual calculation depends on stop loss distance
    if base_size > available_heat:
        return available_heat * 0.8  # Conservative use of available heat
    
    return base_size
```

## Position Sizing Constraints

### Hard Limits

#### System-Wide Constraints
```yaml
system_constraints:
  max_position_value: 1000000     # $1M maximum position value
  max_account_exposure: 0.5       # 50% maximum account exposure
  max_daily_trades: 10            # 10 trades per day per account
  max_concurrent_positions: 5     # 5 open positions maximum
  
  min_stop_distance: 10           # 10 pip minimum stop distance
  max_stop_distance: 500          # 500 pip maximum stop distance
```

#### Prop Firm Specific Constraints
```yaml
prop_firm_rules:
  ftmo:
    max_daily_loss: 0.05          # 5% daily loss limit
    max_total_loss: 0.10          # 10% total loss limit
    min_trading_days: 10          # Minimum trading days required
    
  my_forex_funds:
    max_daily_loss: 0.04          # 4% daily loss limit
    max_total_loss: 0.08          # 8% total loss limit
    consistency_rule: true        # No single day >40% of total profit
```

### Soft Limits and Warnings

#### Warning Thresholds
```python
def check_position_warnings(position_size, account_state, instrument):
    """
    Check for position sizing warnings
    """
    warnings = []
    
    # Check if position size is unusually large
    avg_position_size = account_state['avg_position_size_30d']
    if position_size > avg_position_size * 2:
        warnings.append("Position size 2x larger than recent average")
    
    # Check risk concentration
    instrument_exposure = account_state['instrument_exposure'].get(instrument, 0)
    if instrument_exposure + position_size > account_state['balance'] * 0.2:
        warnings.append("High concentration in single instrument")
    
    # Check correlation exposure
    correlated_exposure = calculate_correlated_exposure(account_state, instrument)
    if correlated_exposure > account_state['balance'] * 0.4:
        warnings.append("High correlation exposure")
    
    return warnings
```

## Implementation and Automation

### Position Sizing Service

#### API Endpoint
```python
@app.post("/api/v1/calculate-position-size")
async def calculate_position_size_endpoint(request: PositionSizeRequest):
    """
    Calculate appropriate position size for a trade
    """
    try:
        # Get account information
        account = await get_account_info(request.account_id)
        
        # Get market data
        market_data = await get_market_data(request.instrument)
        
        # Calculate base position size
        base_size = calculate_base_position_size(
            account.balance,
            request.risk_percentage,
            request.entry_price,
            request.stop_loss_price,
            market_data.instrument_specs
        )
        
        # Apply adjustments
        adjusted_size = apply_all_adjustments(
            base_size,
            account,
            request.instrument,
            market_data
        )
        
        # Validate constraints
        final_size = validate_and_constrain(adjusted_size, account, request.instrument)
        
        # Generate warnings
        warnings = check_position_warnings(final_size, account, request.instrument)
        
        return PositionSizeResponse(
            position_size=final_size,
            risk_amount=final_size * calculate_risk_per_unit(request),
            warnings=warnings,
            calculation_details={
                "base_size": base_size,
                "adjustments": get_adjustment_details(),
                "constraints_applied": get_constraints_applied()
            }
        )
        
    except Exception as e:
        logger.error(f"Position sizing error: {e}")
        raise HTTPException(status_code=500, detail="Position sizing calculation failed")
```

### Backtesting Integration

#### Position Sizing Validation
```python
class PositionSizeBacktest:
    def __init__(self, historical_data, account_params):
        self.data = historical_data
        self.account = account_params
        
    def run_position_sizing_test(self, strategy_signals):
        """
        Backtest position sizing methodology
        """
        results = {
            'total_return': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'win_rate': 0,
            'trades': []
        }
        
        for signal in strategy_signals:
            position_size = self.calculate_historical_position_size(signal)
            trade_result = self.simulate_trade(signal, position_size)
            results['trades'].append(trade_result)
            
        return self.calculate_performance_metrics(results)
```

For risk parameter configuration, see [Risk Parameters](risk-parameters.md). For real-time risk monitoring, see [Risk Controls](risk-controls.md).