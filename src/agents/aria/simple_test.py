#!/usr/bin/env python3
"""
ARIA Simple Test
================

Basic test script to verify the core ARIA functionality.
"""

import asyncio
import sys
from decimal import Decimal
from uuid import uuid4

# Add the current directory to Python path for imports
sys.path.insert(0, '.')

from position_sizing.calculator import PositionSizeCalculator
from position_sizing.models import PositionSizeRequest, RiskModel, PropFirm
from position_sizing.validators import PositionSizeValidator
from position_sizing.adjusters import (
    VolatilityAdjuster, DrawdownAdjuster, CorrelationAdjuster,
    PropFirmLimitChecker, SizeVarianceEngine
)
from position_sizing.adjusters.drawdown import DrawdownTracker
from position_sizing.adjusters.correlation import PositionTracker, CorrelationCalculator
from position_sizing.adjusters.prop_firm_limits import AccountFirmMapping
from position_sizing.adjusters.variance import VarianceHistoryTracker


async def main():
    """Test the basic ARIA functionality."""
    print("ARIA Implementation Test")
    print("=" * 40)
    
    # Initialize components
    print("Initializing components...")
    
    drawdown_tracker = DrawdownTracker()
    position_tracker = PositionTracker()
    correlation_calculator = CorrelationCalculator()
    account_firm_mapping = AccountFirmMapping()
    variance_history = VarianceHistoryTracker()
    
    volatility_adjuster = VolatilityAdjuster()
    drawdown_adjuster = DrawdownAdjuster(drawdown_tracker)
    correlation_adjuster = CorrelationAdjuster(position_tracker, correlation_calculator)
    prop_firm_checker = PropFirmLimitChecker(account_firm_mapping)
    variance_engine = SizeVarianceEngine(variance_history)
    validator = PositionSizeValidator()
    
    calculator = PositionSizeCalculator(
        volatility_adjuster=volatility_adjuster,
        drawdown_adjuster=drawdown_adjuster,
        correlation_adjuster=correlation_adjuster,
        prop_firm_checker=prop_firm_checker,
        variance_engine=variance_engine,
        validator=validator
    )
    
    print("Components initialized successfully!")
    
    # Test basic calculation
    print("\nTesting position size calculation...")
    
    account_id = uuid4()
    signal_id = uuid4()
    
    # Set up account
    await account_firm_mapping.set_account_firm(account_id, PropFirm.FTMO)
    
    request = PositionSizeRequest(
        signal_id=signal_id,
        account_id=account_id,
        symbol="EURUSD",
        account_balance=Decimal("10000.00"),
        stop_distance_pips=Decimal("20.0"),
        risk_model=RiskModel.FIXED,
        base_risk_percentage=Decimal("1.0"),
        direction="long"
    )
    
    try:
        result = await calculator.calculate_position_size(request)
        
        print(f"SUCCESS: Position size calculated!")
        print(f"Base size: {result.base_size} lots")
        print(f"Adjusted size: {result.adjusted_size} lots")
        print(f"Risk amount: ${result.risk_amount}")
        print(f"Reduction: {result.size_reduction_pct:.1f}%")
        
        # Test adjustments
        adj = result.adjustments
        print(f"\nAdjustment factors:")
        print(f"  Volatility: {adj.volatility_factor:.4f}")
        print(f"  Drawdown: {adj.drawdown_factor:.4f}")
        print(f"  Correlation: {adj.correlation_factor:.4f}")
        print(f"  Prop Firm: {adj.limit_factor:.4f}")
        print(f"  Variance: {adj.variance_factor:.4f}")
        print(f"  Total: {adj.total_adjustment:.4f}")
        
        print("\nAll tests PASSED!")
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print(f"\nTest completed with exit code: {exit_code}")
    sys.exit(exit_code)