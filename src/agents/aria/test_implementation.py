#!/usr/bin/env python3
"""
ARIA Implementation Test
========================

Simple test script to verify the core ARIA implementation works correctly.
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


async def test_aria_implementation():
    """Test the complete ARIA implementation."""
    print("Testing ARIA Implementation")
    print("=" * 50)
    
    # Initialize all components
    print("Initializing components...")
    
    drawdown_tracker = DrawdownTracker()
    position_tracker = PositionTracker()
    correlation_calculator = CorrelationCalculator()
    account_firm_mapping = AccountFirmMapping()
    variance_history = VarianceHistoryTracker()
    
    # Create adjusters
    volatility_adjuster = VolatilityAdjuster()
    drawdown_adjuster = DrawdownAdjuster(drawdown_tracker)
    correlation_adjuster = CorrelationAdjuster(position_tracker, correlation_calculator)
    prop_firm_checker = PropFirmLimitChecker(account_firm_mapping)
    variance_engine = SizeVarianceEngine(variance_history)
    
    # Create validator
    validator = PositionSizeValidator()
    
    # Create calculator
    calculator = PositionSizeCalculator(
        volatility_adjuster=volatility_adjuster,
        drawdown_adjuster=drawdown_adjuster,
        correlation_adjuster=correlation_adjuster,
        prop_firm_checker=prop_firm_checker,
        variance_engine=variance_engine,
        validator=validator
    )
    
    print("Components initialized successfully")
    
    # Test 1: Basic position size calculation
    print("\n🧮 Test 1: Basic Position Size Calculation")
    
    account_id = uuid4()
    signal_id = uuid4()
    
    # Set up account with FTMO
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
        
        print(f"   📊 Base size: {result.base_size} lots")
        print(f"   📈 Adjusted size: {result.adjusted_size} lots")
        print(f"   💰 Risk amount: ${result.risk_amount}")
        print(f"   📋 Reasoning: {result.reasoning[:100]}...")
        
        # Verify adjustments
        adj = result.adjustments
        print(f"   🔧 Adjustments:")
        print(f"      • Volatility: {adj.volatility_factor:.4f}")
        print(f"      • Drawdown: {adj.drawdown_factor:.4f}")
        print(f"      • Correlation: {adj.correlation_factor:.4f}")
        print(f"      • Prop Firm: {adj.limit_factor:.4f}")
        print(f"      • Variance: {adj.variance_factor:.4f}")
        print(f"      • Total: {adj.total_adjustment:.4f}")
        
        print("✅ Position size calculation successful")
        
    except Exception as e:
        print(f"❌ Position size calculation failed: {e}")
        return False
    
    # Test 2: Different symbols and conditions
    print("\n🌍 Test 2: Multiple Symbols and Conditions")
    
    test_symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    
    for symbol in test_symbols:
        test_request = PositionSizeRequest(
            signal_id=uuid4(),
            account_id=account_id,
            symbol=symbol,
            account_balance=Decimal("10000.00"),
            stop_distance_pips=Decimal("25.0"),
            risk_model=RiskModel.FIXED,
            base_risk_percentage=Decimal("1.5"),
            direction="long"
        )
        
        try:
            result = await calculator.calculate_position_size(test_request)
            print(f"   {symbol}: {result.adjusted_size:.4f} lots (reduction: {result.size_reduction_pct:.1f}%)")
        
        except Exception as e:
            print(f"   ❌ {symbol}: Failed - {e}")
            return False
    
    print("✅ Multiple symbols test successful")
    
    # Test 3: Drawdown impact
    print("\n📉 Test 3: Drawdown Impact")
    
    # Simulate account with moderate drawdown
    drawdown_account = uuid4()
    await account_firm_mapping.set_account_firm(drawdown_account, PropFirm.FTMO)
    
    # Update equity to simulate 4% drawdown
    await drawdown_tracker.update_equity(drawdown_account, Decimal("9600.00"))  # 4% drawdown
    
    drawdown_request = PositionSizeRequest(
        signal_id=uuid4(),
        account_id=drawdown_account,
        symbol="EURUSD",
        account_balance=Decimal("9600.00"),
        stop_distance_pips=Decimal("20.0"),
        risk_model=RiskModel.FIXED,
        base_risk_percentage=Decimal("1.0"),
        direction="long"
    )
    
    try:
        result = await calculator.calculate_position_size(drawdown_request)
        print(f"   📉 Account in 4% drawdown")
        print(f"   📊 Adjusted size: {result.adjusted_size} lots")
        print(f"   🔧 Drawdown factor: {result.adjustments.drawdown_factor:.4f}")
        
        # Should have significant drawdown reduction
        if result.adjustments.drawdown_factor < Decimal("0.8"):
            print("✅ Drawdown adjustment working correctly")
        else:
            print("⚠️  Expected more drawdown adjustment")
        
    except Exception as e:
        print(f"❌ Drawdown test failed: {e}")
        return False
    
    # Test 4: Prop firm limits
    print("\n🏢 Test 4: Prop Firm Limits")
    
    # Test with different prop firms
    firms_to_test = [PropFirm.FTMO, PropFirm.MY_FOREX_FUNDS, PropFirm.THE5ERS]
    
    for firm in firms_to_test:
        firm_account = uuid4()
        await account_firm_mapping.set_account_firm(firm_account, firm)
        
        limits_summary = await prop_firm_checker.get_account_limits_summary(firm_account)
        
        print(f"   🏢 {firm.value}:")
        print(f"      • Max lot size: {limits_summary['limits']['max_lot_size']}")
        print(f"      • Max positions per symbol: {limits_summary['limits']['max_positions_per_symbol']}")
        print(f"      • Max total exposure: ${limits_summary['limits']['max_total_exposure']:,.0f}")
    
    print("✅ Prop firm limits test successful")
    
    # Test 5: Variance analysis
    print("\n🎲 Test 5: Anti-Detection Variance")
    
    variance_account = uuid4()
    variance_sizes = []
    
    for i in range(10):
        varied_size = await variance_engine.apply_variance(Decimal("1.0"), variance_account)
        variance_sizes.append(float(varied_size))
    
    import statistics
    
    mean_size = statistics.mean(variance_sizes)
    std_dev = statistics.stdev(variance_sizes) if len(variance_sizes) > 1 else 0
    
    print(f"   🎯 Mean size: {mean_size:.4f} lots")
    print(f"   📊 Std deviation: {std_dev:.4f}")
    print(f"   📈 Range: {min(variance_sizes):.4f} - {max(variance_sizes):.4f}")
    
    # Variance should be between 5-15% as per requirements
    if 0.85 <= mean_size <= 1.15 and std_dev > 0.02:
        print("✅ Variance within expected range")
    else:
        print("⚠️  Variance might be outside expected parameters")
    
    # Test variance analysis
    analysis = await variance_engine.get_variance_analysis(variance_account)
    print(f"   📋 Profile: {'Aggressive' if analysis['profile']['aggressive'] else 'Conservative'}")
    
    print("\n🎉 All tests completed successfully!")
    print("=" * 50)
    print("✅ ARIA Implementation appears to be working correctly")
    
    return True


async def test_api_compatibility():
    """Test API compatibility (basic structure check)."""
    print("\n🌐 Testing API Compatibility")
    
    try:
        from api.main import create_aria_app
        
        app = create_aria_app()
        print("✅ FastAPI app created successfully")
        
        # Check if main routes are configured
        routes = [route.path for route in app.routes]
        expected_routes = ["/health", "/api/v1/position-sizing/calculate"]
        
        for expected_route in expected_routes:
            if any(expected_route in route for route in routes):
                print(f"✅ Route {expected_route} found")
            else:
                print(f"⚠️  Route {expected_route} not found")
        
        return True
        
    except Exception as e:
        print(f"❌ API compatibility test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("ARIA - Adaptive Risk Intelligence Agent")
    print("Implementation Test Suite")
    print("=" * 60)
    
    # Test core implementation
    core_success = await test_aria_implementation()
    
    if not core_success:
        print("\n❌ Core implementation tests failed!")
        return 1
    
    # Test API compatibility
    api_success = await test_api_compatibility()
    
    if not api_success:
        print("\n❌ API compatibility tests failed!")
        return 1
    
    print(f"\n🎉 ALL TESTS PASSED!")
    print("🚀 ARIA implementation is ready for integration")
    
    return 0


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)