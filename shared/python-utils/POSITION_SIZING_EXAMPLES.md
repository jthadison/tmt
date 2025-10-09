# Position Sizing Examples

This document provides comprehensive examples of using the EnhancedPositionSizer for accurate position sizing calculations.

## Quick Start

```python
from position_sizing import EnhancedPositionSizer
from decimal import Decimal

# Initialize with OANDA client
sizer = EnhancedPositionSizer(
    oanda_client=oanda_client,
    account_currency="USD",
    min_account_balance=Decimal("5000"),
    max_per_trade_pct=Decimal("0.05"),  # 5%
    max_portfolio_heat_pct=Decimal("0.15"),  # 15%
    max_per_instrument_pct=Decimal("0.10")  # 10%
)

# Calculate position size
result = await sizer.calculate_position_size(
    instrument="EUR_USD",
    entry_price=Decimal("1.0850"),
    stop_loss=Decimal("1.0800"),
    account_id="your-account-id",
    direction="BUY",
    risk_percent=Decimal("0.02")  # 2% risk
)

print(f"Position Size: {result.position_size} units")
print(f"Risk Amount: ${result.risk_amount}")
print(f"Stop Distance: {result.stop_distance_pips} pips")
```

## Example 1: EUR_USD Long Trade

### Scenario
- **Account Balance**: $10,000
- **Risk Per Trade**: 2%
- **Entry Price**: 1.0850
- **Stop Loss**: 1.0800
- **Direction**: BUY (long)

### Calculation

```python
result = await sizer.calculate_position_size(
    instrument="EUR_USD",
    entry_price=Decimal("1.0850"),
    stop_loss=Decimal("1.0800"),
    account_id="account-123",
    direction="BUY",
    risk_percent=Decimal("0.02")
)
```

### Detailed Breakdown

1. **Risk Amount**: $10,000 × 2% = $200
2. **Pip Value**: 0.0001 (standard forex pair)
3. **Stop Distance**: (1.0850 - 1.0800) / 0.0001 = 50 pips
4. **Position Size**: $200 / (50 pips × $1 per pip per 10k units)
   - = $200 / $50
   - = 4 units of 10,000
   - = **40,000 units**

### Result
```python
{
    "position_size": 40000,  # Positive for long
    "risk_amount": 200.00,
    "stop_distance_pips": 50,
    "pip_value_account": 40.00,  # For full position
    "account_balance": 10000.00,
    "constraints_applied": [],
    "warnings": []
}
```

## Example 2: USD_JPY Short Trade

### Scenario
- **Account Balance**: $10,000
- **Risk Per Trade**: 2%
- **Entry Price**: 149.50
- **Stop Loss**: 150.00
- **Direction**: SELL (short)

### Calculation

```python
result = await sizer.calculate_position_size(
    instrument="USD_JPY",
    entry_price=Decimal("149.50"),
    stop_loss=Decimal("150.00"),
    account_id="account-123",
    direction="SELL",
    risk_percent=Decimal("0.02")
)
```

### Detailed Breakdown

1. **Risk Amount**: $10,000 × 2% = $200
2. **Pip Value**: 0.01 (JPY pair)
3. **Stop Distance**: (150.00 - 149.50) / 0.01 = 50 pips
4. **Pip Value in USD**: 0.01 / 149.50 = $0.000067 per unit
   - Per 10k units = $0.67
5. **Position Size**: $200 / (50 pips × $0.67)
   - = $200 / $33.50
   - = 5.97 units → **60,000 units** (rounded)

### Result
```python
{
    "position_size": -60000,  # Negative for short
    "risk_amount": 200.00,
    "stop_distance_pips": 50,
    "pip_value_account": 40.20,
    "account_balance": 10000.00,
    "constraints_applied": [],
    "warnings": []
}
```

## Example 3: XAU_USD (Gold) Trade

### Scenario
- **Account Balance**: $10,000
- **Risk Per Trade**: 1.5%
- **Entry Price**: 1950.00
- **Stop Loss**: 1945.00
- **Direction**: BUY

### Calculation

```python
result = await sizer.calculate_position_size(
    instrument="XAU_USD",
    entry_price=Decimal("1950.00"),
    stop_loss=Decimal("1945.00"),
    account_id="account-123",
    direction="BUY",
    risk_percent=Decimal("0.015")
)
```

### Detailed Breakdown

1. **Risk Amount**: $10,000 × 1.5% = $150
2. **Pip Value**: 0.01 (gold)
3. **Stop Distance**: (1950.00 - 1945.00) / 0.01 = 500 pips
4. **Position Size**: $150 / (500 pips × $0.01 per unit)
   - = $150 / $5.00
   - = **30 units**

### Result
```python
{
    "position_size": 30,
    "risk_amount": 150.00,
    "stop_distance_pips": 500,
    "pip_value_account": 0.30,
    "account_balance": 10000.00,
    "constraints_applied": [],
    "warnings": []
}
```

## Example 4: Position Limit Application

### Scenario
- **Account Balance**: $10,000
- **Risk Per Trade**: 2%
- **Entry Price**: 1.0850
- **Stop Loss**: 1.0849 (only 1 pip!)
- **Direction**: BUY

### What Happens

With only 1 pip stop, the raw calculation would be:
- Position Size = $200 / (1 pip × $0.0001) = 2,000,000 units
- Position Value = 2,000,000 × 1.0850 = $2,170,000

But this exceeds the 5% per-trade limit:
- Max Allowed = $10,000 × 5% = $500
- Limited Position = $500 / 1.0850 = **460 units**

### Result
```python
{
    "position_size": 460,
    "risk_amount": 200.00,
    "stop_distance_pips": 1,
    "pip_value_account": 0.46,
    "account_balance": 10000.00,
    "constraints_applied": ["per_trade_limit_5pct"],
    "warnings": []
}
```

## Example 5: Low Account Balance Warning

### Scenario
- **Account Balance**: $3,000 (below $5,000 minimum)
- **Risk Per Trade**: 2%
- **Entry Price**: 1.0850
- **Stop Loss**: 1.0800

### Result
```python
{
    "position_size": 12000,
    "risk_amount": 60.00,
    "stop_distance_pips": 50,
    "pip_value_account": 12.00,
    "account_balance": 3000.00,
    "constraints_applied": [],
    "warnings": [
        "Account balance $3000.00 < minimum $5000.00"
    ]
}
```

## Example 6: Portfolio Heat Reduction

### Scenario
- **Current Open Positions**:
  - GBP_USD: 50,000 units @ 1.25 = $62,500
  - AUD_USD: 30,000 units @ 0.65 = $19,500
  - Total Exposure: $82,000 on $10,000 account
- **Portfolio Heat**: 82% (very high!)
- **New Trade**: EUR_USD

### What Happens

The system detects high portfolio heat (> 12% threshold) and reduces the new position by 50%:

```python
{
    "position_size": 20000,  # Reduced from 40,000
    "risk_amount": 200.00,
    "stop_distance_pips": 50,
    "pip_value_account": 20.00,
    "account_balance": 10000.00,
    "constraints_applied": ["portfolio_heat_high"],
    "warnings": [
        "Portfolio heat 82.0% high, reducing position by 50%"
    ]
}
```

## Performance Metrics

### Calculation Time

All calculations target < 50ms performance:

```python
result = await sizer.calculate_position_size(...)
print(f"Calculation time: {result.calculation_time_ms:.2f}ms")
# Expected: 5-15ms with caching
```

### Cache Hit Rates

Account balance and exchange rates are cached for 5 minutes:

```python
stats = sizer.get_statistics()
print(stats)
# {
#     "balance_cache_entries": 3,
#     "currency_converter_stats": {
#         "total_entries": 5,
#         "valid_entries": 5,
#         "cache_ttl_minutes": 5
#     }
# }
```

## Error Handling

### Invalid Stop Distance

```python
result = await sizer.calculate_position_size(
    instrument="EUR_USD",
    entry_price=Decimal("1.0850"),
    stop_loss=Decimal("1.0850"),  # Same as entry!
    account_id="account-123",
    direction="BUY"
)

# Returns zero position with error
# {
#     "position_size": 0,
#     "constraints_applied": ["calculation_error"],
#     "warnings": ["Calculation error: Invalid stop distance: 0 pips"]
# }
```

### Missing Account Data

```python
try:
    result = await sizer.calculate_position_size(
        instrument="EUR_USD",
        entry_price=Decimal("1.0850"),
        stop_loss=Decimal("1.0800"),
        account_id="invalid-account",
        direction="BUY"
    )
except Exception as e:
    print(f"Error: {e}")
    # Error: Failed to fetch account balance for invalid-account
```

## Audit Trail

All position sizing decisions are logged for audit purposes:

```python
from position_sizing import PositionSizingAuditLogger

audit_logger = PositionSizingAuditLogger(
    enable_file_logging=True,
    audit_file_path="logs/position_sizing_audit.log"
)

# Calculate position
result = await sizer.calculate_position_size(...)

# Log for audit
audit_logger.log_position_sizing_decision(
    account_id="account-123",
    instrument="EUR_USD",
    direction="BUY",
    entry_price=Decimal("1.0850"),
    stop_loss=Decimal("1.0800"),
    take_profit=None,
    account_balance=result.account_balance,
    risk_percent=Decimal("0.02"),
    stop_distance_pips=result.stop_distance_pips,
    pip_value_account=result.pip_value_account,
    calculated_position_size=result.position_size,
    final_position_size=result.position_size,
    risk_amount=result.risk_amount,
    constraints_applied=result.constraints_applied,
    warnings=result.warnings,
    calculation_time_ms=result.calculation_time_ms
)
```

## Alert Integration

Alerts are generated for important events:

```python
from position_sizing import PositionSizingAlertService

alert_service = PositionSizingAlertService(
    min_balance_threshold=Decimal("5000"),
    portfolio_heat_warning_threshold=Decimal("0.12"),
    portfolio_heat_critical_threshold=Decimal("0.15")
)

# Check account balance
alert = await alert_service.check_account_balance(
    account_id="account-123",
    balance=Decimal("3000")
)

if alert:
    print(f"ALERT: {alert['message']}")
    # ALERT: Account account-123 balance $3000.00 < $5000.00

# Get recent alerts
recent_alerts = alert_service.get_recent_alerts(limit=10)
```

## Best Practices

1. **Always Use Decimal**: Never use float for monetary values or prices
2. **Cache Wisely**: Default 5-minute cache is good for most use cases
3. **Monitor Performance**: Check `calculation_time_ms` in production
4. **Review Constraints**: Check `constraints_applied` to understand sizing decisions
5. **Heed Warnings**: Don't ignore warnings - they indicate potential issues
6. **Audit Everything**: Enable audit logging in production
7. **Test Thoroughly**: Validate calculations against manual calculations

## Testing Examples

```python
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_position_sizing_accuracy():
    """Test position sizing accuracy vs manual calculation"""
    result = await sizer.calculate_position_size(
        instrument="EUR_USD",
        entry_price=Decimal("1.0850"),
        stop_loss=Decimal("1.0800"),
        account_id="test-account",
        direction="BUY",
        risk_percent=Decimal("0.02")
    )

    # Manual calculation
    account_balance = Decimal("10000")
    risk_amount = account_balance * Decimal("0.02")  # $200
    stop_pips = Decimal("50")
    pip_value_per_unit = Decimal("0.0001")

    expected_size = int(risk_amount / (stop_pips * pip_value_per_unit))

    # Allow < 2% error
    error_pct = abs(result.position_size - expected_size) / expected_size
    assert error_pct < 0.02, f"Position size error: {error_pct:.1%}"
```
