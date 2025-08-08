"""Simple test runner for Anti-Correlation Engine."""

import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from uuid import uuid4

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_correlation_monitor():
    """Test basic correlation monitoring functionality."""
    print("Testing Correlation Monitor...")
    
    try:
        from correlation_monitor import CorrelationMonitor
        from models import Base
        
        # Create mock database session
        mock_db = Mock()
        monitor = CorrelationMonitor(mock_db)
        
        # Test Pearson correlation calculation
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]  # Perfect positive correlation
        
        correlation, p_value = monitor._calculate_pearson_correlation(x, y)
        
        assert abs(correlation - 1.0) < 0.001, f"Expected correlation ~1.0, got {correlation}"
        assert p_value < 0.05, f"Expected significant p-value, got {p_value}"
        
        print("✓ Pearson correlation calculation works correctly")
        
        # Test risk assessment
        assert monitor._assess_correlation_risk(0.9) == "critical"
        assert monitor._assess_correlation_risk(0.75) == "high"
        assert monitor._assess_correlation_risk(0.55) == "medium"
        assert monitor._assess_correlation_risk(0.3) == "low"
        
        print("✓ Risk assessment works correctly")
        print("✓ Correlation Monitor tests passed\n")
        
    except Exception as e:
        print(f"X Correlation Monitor test failed: {e}\n")
        return False
    
    return True

async def test_alert_manager():
    """Test alert management functionality."""
    print("Testing Alert Manager...")
    
    try:
        from alert_manager import AlertManager
        from models import CorrelationSeverity
        
        # Create mock database session
        mock_db = Mock()
        alert_manager = AlertManager(mock_db)
        
        # Test severity level determination
        assert alert_manager._determine_severity_level(0.95, 0.001) == CorrelationSeverity.CRITICAL
        assert alert_manager._determine_severity_level(0.75, 0.02) == CorrelationSeverity.WARNING
        assert alert_manager._determine_severity_level(0.55, 0.05) == CorrelationSeverity.INFO
        
        print("✓ Severity level determination works correctly")
        
        # Test threshold checking logic
        assert alert_manager._should_trigger_alert(0.95, 0.001) == True
        assert alert_manager._should_trigger_alert(0.4, 0.1) == False
        
        print("✓ Alert threshold logic works correctly")
        print("✓ Alert Manager tests passed\n")
        
    except Exception as e:
        print(f"✗ Alert Manager test failed: {e}\n")
        return False
    
    return True

async def test_position_adjuster():
    """Test position adjustment functionality."""
    print("Testing Position Adjuster...")
    
    try:
        from position_adjuster import PositionAdjuster, AdjustmentStrategy
        
        # Create mock database session
        mock_db = Mock()
        adjuster = PositionAdjuster(mock_db)
        
        # Test strategy selection
        strategy = adjuster._select_adjustment_strategy(0.1)
        assert strategy == AdjustmentStrategy.GRADUAL_REDUCTION
        
        strategy = adjuster._select_adjustment_strategy(0.5)
        assert strategy in [AdjustmentStrategy.ROTATION, AdjustmentStrategy.DIVERSIFICATION]
        
        print("✓ Strategy selection works correctly")
        
        # Test effectiveness calculation
        effectiveness = adjuster._calculate_effectiveness(0.8, 0.6, 'gradual_reduction')
        assert 0.0 <= effectiveness <= 1.0
        assert effectiveness > 0.5  # Should be effective
        
        print("✓ Effectiveness calculation works correctly")
        
        # Test risk assessment
        adjustment = {
            'adjustment_type': 'gradual_reduction',
            'size_change': -0.3,
            'symbol': 'EURUSD'
        }
        risk_level = adjuster._assess_adjustment_risk(adjustment)
        assert risk_level in ['low', 'medium', 'high']
        
        print("✓ Risk assessment works correctly")
        print("✓ Position Adjuster tests passed\n")
        
    except Exception as e:
        print(f"✗ Position Adjuster test failed: {e}\n")
        return False
    
    return True

async def test_execution_delay():
    """Test execution delay functionality."""
    print("Testing Execution Delay Manager...")
    
    try:
        from execution_delay import ExecutionDelayManager, SignalPriority, MarketSession
        
        # Create mock database session
        mock_db = Mock()
        delay_manager = ExecutionDelayManager(mock_db)
        
        # Test delay calculation
        base_delay = delay_manager._calculate_base_delay([5, 25])
        assert 5 <= base_delay <= 25
        
        print("✓ Base delay calculation works correctly")
        
        # Test session adjustments
        adjustment = delay_manager._get_session_adjustment(MarketSession.LONDON_NY_OVERLAP)
        assert 0.8 <= adjustment <= 1.5  # Should be within reasonable range
        
        print("✓ Session adjustment works correctly")
        
        # Test priority adjustments
        priority_adj = delay_manager._get_priority_adjustment(SignalPriority.CRITICAL)
        assert priority_adj < 1.0  # Critical should reduce delay
        
        print("✓ Priority adjustment works correctly")
        print("✓ Execution Delay Manager tests passed\n")
        
    except Exception as e:
        print(f"✗ Execution Delay Manager test failed: {e}\n")
        return False
    
    return True

async def test_size_variance():
    """Test size variance functionality."""
    print("Testing Size Variance Manager...")
    
    try:
        from size_variance import SizeVarianceManager, SizeVarianceStrategy
        
        # Create mock database session
        mock_db = Mock()
        variance_manager = SizeVarianceManager(mock_db)
        
        # Test percentage-based variance
        variance_factor = variance_manager._percentage_based_variance((0.05, 0.15))
        assert 0.85 <= variance_factor <= 1.15  # Should be within expected range
        
        print("✓ Percentage-based variance works correctly")
        
        # Test personality-based variance
        from models import AccountCorrelationProfile
        profile = AccountCorrelationProfile(
            account_id=uuid4(),
            personality_type="conservative",
            risk_tolerance=0.5,
            typical_delay_range=(5.0, 25.0),
            size_variance_preference=0.1,
            correlation_history=[0.3, 0.4, 0.5],
            adjustment_frequency=3
        )
        
        variance_factor = variance_manager._personality_based_variance(profile, (0.05, 0.15))
        assert 0.90 <= variance_factor <= 1.12  # Conservative should have smaller variance
        
        print("✓ Personality-based variance works correctly")
        print("✓ Size Variance Manager tests passed\n")
        
    except Exception as e:
        print(f"✗ Size Variance Manager test failed: {e}\n")
        return False
    
    return True

async def test_correlation_reporter():
    """Test correlation reporting functionality."""
    print("Testing Correlation Reporter...")
    
    try:
        from correlation_reporter import CorrelationReporter
        
        # Create mock components
        mock_db = Mock()
        mock_correlation_monitor = Mock()
        mock_alert_manager = Mock()
        
        reporter = CorrelationReporter(mock_db, mock_correlation_monitor, mock_alert_manager)
        
        # Test trend calculation
        values = [0.5, 0.6, 0.7, 0.8, 0.9]  # Increasing trend
        trend = reporter._calculate_trend(values)
        assert trend == "increasing"
        
        values = [0.9, 0.8, 0.7, 0.6, 0.5]  # Decreasing trend
        trend = reporter._calculate_trend(values)
        assert trend == "decreasing"
        
        values = [0.6, 0.6, 0.6, 0.6, 0.6]  # Stable
        trend = reporter._calculate_trend(values)
        assert trend == "stable"
        
        print("✓ Trend calculation works correctly")
        
        # Test risk assessment
        assert reporter._assess_pair_risk(0.9) == "critical"
        assert reporter._assess_pair_risk(0.75) == "high"
        assert reporter._assess_pair_risk(0.55) == "medium"
        assert reporter._assess_pair_risk(0.3) == "low"
        
        print("✓ Risk assessment works correctly")
        print("✓ Correlation Reporter tests passed\n")
        
    except Exception as e:
        print(f"✗ Correlation Reporter test failed: {e}\n")
        return False
    
    return True

async def test_integration():
    """Test basic integration between components."""
    print("Testing Component Integration...")
    
    try:
        # Test that all main components can be imported and instantiated
        from correlation_monitor import CorrelationMonitor
        from alert_manager import AlertManager
        from position_adjuster import PositionAdjuster
        from execution_delay import ExecutionDelayManager
        from size_variance import SizeVarianceManager
        from correlation_reporter import CorrelationReporter
        
        mock_db = Mock()
        
        # Instantiate all components
        correlation_monitor = CorrelationMonitor(mock_db)
        alert_manager = AlertManager(mock_db)
        position_adjuster = PositionAdjuster(mock_db)
        execution_delay = ExecutionDelayManager(mock_db)
        size_variance = SizeVarianceManager(mock_db)
        correlation_reporter = CorrelationReporter(mock_db, correlation_monitor, alert_manager)
        
        print("✓ All components instantiate correctly")
        
        # Test that all components have expected methods
        assert hasattr(correlation_monitor, 'calculate_correlation')
        assert hasattr(alert_manager, 'trigger_alert')
        assert hasattr(position_adjuster, 'adjust_positions_for_correlation')
        assert hasattr(execution_delay, 'calculate_execution_delay')
        assert hasattr(size_variance, 'calculate_size_variance')
        assert hasattr(correlation_reporter, 'generate_daily_report')
        
        print("✓ All components have expected interfaces")
        print("✓ Integration tests passed\n")
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}\n")
        return False
    
    return True

async def main():
    """Run all tests."""
    print("=" * 60)
    print("ANTI-CORRELATION ENGINE - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_correlation_monitor,
        test_alert_manager,
        test_position_adjuster,
        test_execution_delay,
        test_size_variance,
        test_correlation_reporter,
        test_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if await test():
            passed += 1
    
    print("=" * 60)
    print(f"TEST RESULTS: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Anti-Correlation Engine is ready for deployment.")
        print("\nNext steps:")
        print("1. Deploy to staging environment")
        print("2. Run integration tests with MetaTrader")
        print("3. Perform load testing")
        print("4. Security audit")
        print("5. Deploy to production")
    else:
        print("❌ Some tests failed. Review and fix issues before deployment.")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())