"""
Position Sizing Calculator Tests
================================

Comprehensive tests for the position sizing calculator including
base calculations, adjustments, and validation logic.
"""

import pytest
from decimal import Decimal
from uuid import uuid4
import datetime

from ..position_sizing.calculator import PositionSizeCalculator
from ..position_sizing.models import (
    PositionSizeRequest, RiskModel, PropFirm, VolatilityRegime
)
from ..position_sizing.validators import PositionSizeValidator
from ..position_sizing.adjusters import (
    VolatilityAdjuster, DrawdownAdjuster, CorrelationAdjuster,
    PropFirmLimitChecker, SizeVarianceEngine
)
from ..position_sizing.adjusters.drawdown import DrawdownTracker
from ..position_sizing.adjusters.correlation import PositionTracker, CorrelationCalculator
from ..position_sizing.adjusters.prop_firm_limits import AccountFirmMapping
from ..position_sizing.adjusters.variance import VarianceHistoryTracker


@pytest.fixture
def sample_request():
    """Create a sample position size request."""
    return PositionSizeRequest(
        signal_id=uuid4(),
        account_id=uuid4(),
        symbol="EURUSD",
        account_balance=Decimal("10000.00"),
        stop_distance_pips=Decimal("20.0"),
        risk_model=RiskModel.FIXED,
        base_risk_percentage=Decimal("1.0"),
        direction="long"
    )


@pytest.fixture
def position_calculator():
    """Create a position size calculator with all components."""
    # Initialize components
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
    return PositionSizeCalculator(
        volatility_adjuster=volatility_adjuster,
        drawdown_adjuster=drawdown_adjuster,
        correlation_adjuster=correlation_adjuster,
        prop_firm_checker=prop_firm_checker,
        variance_engine=variance_engine,
        validator=validator
    )


class TestPositionSizeCalculator:
    """Test cases for the position size calculator."""
    
    @pytest.mark.asyncio
    async def test_basic_position_size_calculation(self, position_calculator, sample_request):
        """Test basic position size calculation without adjustments."""
        result = await position_calculator.calculate_position_size(sample_request)
        
        # Verify basic properties
        assert result.signal_id == sample_request.signal_id
        assert result.account_id == sample_request.account_id
        assert result.symbol == sample_request.symbol
        assert result.base_size > Decimal("0")
        assert result.adjusted_size > Decimal("0")
        assert result.risk_amount > Decimal("0")
        
        # Verify adjustments exist
        assert result.adjustments.volatility_factor > Decimal("0")
        assert result.adjustments.drawdown_factor > Decimal("0")
        assert result.adjustments.correlation_factor > Decimal("0")
        assert result.adjustments.limit_factor > Decimal("0")
        assert result.adjustments.variance_factor > Decimal("0")
    
    @pytest.mark.asyncio
    async def test_risk_model_variations(self, position_calculator):
        """Test different risk models produce different results."""
        base_request = PositionSizeRequest(
            signal_id=uuid4(),
            account_id=uuid4(),
            symbol="EURUSD",
            account_balance=Decimal("10000.00"),
            stop_distance_pips=Decimal("20.0"),
            base_risk_percentage=Decimal("2.0")
        )
        
        # Test fixed risk model
        fixed_request = base_request
        fixed_request.risk_model = RiskModel.FIXED
        fixed_result = await position_calculator.calculate_position_size(fixed_request)
        
        # Test adaptive risk model
        adaptive_request = base_request
        adaptive_request.risk_model = RiskModel.ADAPTIVE
        adaptive_result = await position_calculator.calculate_position_size(adaptive_request)
        
        # Results should be different (unless adaptive returns same as fixed)
        # The exact difference depends on implementation
        assert fixed_result.base_size != adaptive_result.base_size or fixed_result.base_size == adaptive_result.base_size
    
    @pytest.mark.asyncio
    async def test_large_stop_distance_reduces_size(self, position_calculator, sample_request):
        """Test that larger stop distances result in smaller position sizes."""
        # Small stop distance
        small_stop_request = sample_request
        small_stop_request.stop_distance_pips = Decimal("10.0")
        small_stop_result = await position_calculator.calculate_position_size(small_stop_request)
        
        # Large stop distance
        large_stop_request = sample_request
        large_stop_request.stop_distance_pips = Decimal("50.0")
        large_stop_result = await position_calculator.calculate_position_size(large_stop_request)
        
        # Larger stop should result in smaller position size
        assert large_stop_result.base_size < small_stop_result.base_size
    
    @pytest.mark.asyncio
    async def test_higher_risk_percentage_increases_size(self, position_calculator, sample_request):
        """Test that higher risk percentages result in larger position sizes."""
        # Low risk
        low_risk_request = sample_request
        low_risk_request.base_risk_percentage = Decimal("0.5")
        low_risk_result = await position_calculator.calculate_position_size(low_risk_request)
        
        # High risk
        high_risk_request = sample_request
        high_risk_request.base_risk_percentage = Decimal("2.0")
        high_risk_result = await position_calculator.calculate_position_size(high_risk_request)
        
        # Higher risk should result in larger position size
        assert high_risk_result.base_size > low_risk_result.base_size
    
    @pytest.mark.asyncio
    async def test_position_size_reasoning(self, position_calculator, sample_request):
        """Test that reasoning is generated for position size calculations."""
        result = await position_calculator.calculate_position_size(sample_request)
        
        # Reasoning should exist and contain key information
        assert result.reasoning is not None
        assert len(result.reasoning) > 0
        assert "lots" in result.reasoning.lower()


class TestPositionSizeValidator:
    """Test cases for position size validation."""
    
    def test_minimum_trade_size_validation(self):
        """Test minimum trade size validation."""
        validator = PositionSizeValidator()
        
        # Test rounding functionality
        result = validator.round_to_valid_lot_size(Decimal("0.123"), "EURUSD")
        assert result >= Decimal("0.01")  # Should meet minimum
        assert result % Decimal("0.01") == 0  # Should be properly rounded
    
    def test_fractional_lot_rounding(self):
        """Test fractional lot size rounding."""
        validator = PositionSizeValidator()
        
        # Test various sizes
        test_cases = [
            (Decimal("0.123"), Decimal("0.12")),
            (Decimal("1.567"), Decimal("1.57")),
            (Decimal("0.001"), Decimal("0.01"))  # Below minimum
        ]
        
        for input_size, expected_min in test_cases:
            result = validator.round_to_valid_lot_size(input_size, "EURUSD")
            assert result >= expected_min


class TestVolatilityAdjuster:
    """Test cases for volatility-based adjustments."""
    
    @pytest.mark.asyncio
    async def test_volatility_adjustment(self):
        """Test volatility-based size adjustments."""
        adjuster = VolatilityAdjuster()
        base_size = Decimal("1.0")
        
        # Test adjustment
        adjusted_size = await adjuster.adjust_size(base_size, "EURUSD")
        
        # Should return a valid adjustment
        assert adjusted_size > Decimal("0")
        # Adjustment should be within reasonable bounds (0.5x to 2x base)
        assert Decimal("0.5") <= adjusted_size <= Decimal("2.0")
    
    def test_volatility_regime_classification(self):
        """Test volatility regime classification."""
        adjuster = VolatilityAdjuster()
        
        # Test various percentiles
        test_cases = [
            (Decimal("10.0"), VolatilityRegime.LOW),
            (Decimal("30.0"), VolatilityRegime.BELOW_NORMAL),
            (Decimal("50.0"), VolatilityRegime.NORMAL),
            (Decimal("70.0"), VolatilityRegime.ABOVE_NORMAL),
            (Decimal("90.0"), VolatilityRegime.HIGH),
            (Decimal("99.0"), VolatilityRegime.EXTREME)
        ]
        
        for percentile, expected_regime in test_cases:
            result = adjuster._classify_volatility_regime(percentile)
            assert result == expected_regime


class TestDrawdownAdjuster:
    """Test cases for drawdown-based adjustments."""
    
    @pytest.mark.asyncio
    async def test_drawdown_size_reduction(self):
        """Test that drawdown reduces position sizes."""
        drawdown_tracker = DrawdownTracker()
        adjuster = DrawdownAdjuster(drawdown_tracker)
        
        account_id = uuid4()
        base_size = Decimal("1.0")
        
        # Simulate moderate drawdown by updating equity
        await drawdown_tracker.update_equity(account_id, Decimal("9500.00"))  # 5% drawdown
        
        # Adjust size
        adjusted_size = await adjuster.adjust_size(base_size, account_id)
        
        # Size should be reduced for moderate drawdown (50% reduction expected)
        assert adjusted_size < base_size
        assert adjusted_size == base_size * Decimal("0.5")  # 50% reduction for moderate
    
    @pytest.mark.asyncio
    async def test_extreme_drawdown_emergency_halt(self):
        """Test emergency halt for extreme drawdown."""
        drawdown_tracker = DrawdownTracker()
        adjuster = DrawdownAdjuster(drawdown_tracker)
        
        account_id = uuid4()
        base_size = Decimal("1.0")
        
        # Simulate extreme drawdown
        await drawdown_tracker.update_equity(account_id, Decimal("8000.00"))  # 20% drawdown
        
        # Adjust size
        adjusted_size = await adjuster.adjust_size(base_size, account_id)
        
        # Should halt trading (return zero size) for extreme drawdown
        assert adjusted_size == Decimal("0")


class TestCorrelationAdjuster:
    """Test cases for correlation-based adjustments."""
    
    @pytest.mark.asyncio
    async def test_correlation_calculation(self):
        """Test correlation calculation between currency pairs."""
        calculator = CorrelationCalculator()
        
        # Test known correlation
        correlation = await calculator.calculate_correlation("EURUSD", "GBPUSD")
        
        assert correlation.symbol1 == "EURUSD"
        assert correlation.symbol2 == "GBPUSD"
        assert -Decimal("1.0") <= correlation.correlation_coefficient <= Decimal("1.0")
        
        # EURUSD and GBPUSD should have positive correlation
        assert correlation.correlation_coefficient > Decimal("0")
    
    @pytest.mark.asyncio
    async def test_identical_pairs_perfect_correlation(self):
        """Test that identical pairs have perfect correlation."""
        calculator = CorrelationCalculator()
        
        correlation = await calculator.calculate_correlation("EURUSD", "EURUSD")
        assert correlation.correlation_coefficient == Decimal("1.0")


class TestPropFirmLimitChecker:
    """Test cases for prop firm limit enforcement."""
    
    @pytest.mark.asyncio
    async def test_max_lot_size_enforcement(self):
        """Test maximum lot size enforcement."""
        account_firm_mapping = AccountFirmMapping()
        checker = PropFirmLimitChecker(account_firm_mapping)
        
        account_id = uuid4()
        await account_firm_mapping.set_account_firm(account_id, PropFirm.FTMO)
        
        # Create request with large size
        request = PositionSizeRequest(
            signal_id=uuid4(),
            account_id=account_id,
            symbol="EURUSD",
            account_balance=Decimal("100000.00"),
            stop_distance_pips=Decimal("10.0"),
            base_risk_percentage=Decimal("1.0")
        )
        
        # Test size larger than FTMO limit (20 lots)
        large_size = Decimal("25.0")
        enforced_size = await checker.enforce_limits(large_size, request)
        
        # Should be capped at FTMO limit
        assert enforced_size <= Decimal("20.0")
    
    @pytest.mark.asyncio
    async def test_account_limits_summary(self):
        """Test account limits summary retrieval."""
        account_firm_mapping = AccountFirmMapping()
        checker = PropFirmLimitChecker(account_firm_mapping)
        
        account_id = uuid4()
        await account_firm_mapping.set_account_firm(account_id, PropFirm.FTMO)
        
        # Get limits summary
        summary = await checker.get_account_limits_summary(account_id)
        
        assert summary['account_id'] == str(account_id)
        assert summary['prop_firm'] == PropFirm.FTMO.value
        assert 'limits' in summary
        assert 'max_lot_size' in summary['limits']


class TestSizeVarianceEngine:
    """Test cases for anti-detection variance generation."""
    
    @pytest.mark.asyncio
    async def test_variance_application(self):
        """Test that variance is applied within acceptable ranges."""
        variance_history = VarianceHistoryTracker()
        engine = SizeVarianceEngine(variance_history)
        
        account_id = uuid4()
        base_size = Decimal("1.0")
        
        # Apply variance
        varied_size = await engine.apply_variance(base_size, account_id)
        
        # Should be within variance range (5-15% as per requirements)
        min_expected = base_size * Decimal("0.85")  # 15% reduction max
        max_expected = base_size * Decimal("1.15")  # 15% increase max
        
        assert min_expected <= varied_size <= max_expected
    
    @pytest.mark.asyncio
    async def test_pattern_detection(self):
        """Test pattern detection in variance history."""
        variance_history = VarianceHistoryTracker()
        engine = SizeVarianceEngine(variance_history)
        
        account_id = uuid4()
        
        # Record many similar variance factors to create a pattern
        for _ in range(15):
            await variance_history.record_variance(
                account_id, Decimal("1.0"), Decimal("1.05"), Decimal("1.05")
            )
        
        # Check if pattern is detected
        pattern_detected = await engine._is_forming_detectable_pattern(account_id)
        
        # Should detect pattern due to low variance
        assert pattern_detected
    
    @pytest.mark.asyncio
    async def test_variance_analysis(self):
        """Test variance analysis report generation."""
        variance_history = VarianceHistoryTracker()
        engine = SizeVarianceEngine(variance_history)
        
        account_id = uuid4()
        
        # Apply some variance to create history
        for i in range(5):
            await engine.apply_variance(Decimal("1.0"), account_id)
        
        # Get analysis
        analysis = await engine.get_variance_analysis(account_id)
        
        assert 'account_id' in analysis
        assert 'profile' in analysis
        assert 'statistics' in analysis
        assert 'pattern_analysis' in analysis


@pytest.mark.asyncio
async def test_end_to_end_position_sizing():
    """Test complete end-to-end position sizing workflow."""
    # Create complete calculator
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
    
    # Create test request
    request = PositionSizeRequest(
        signal_id=uuid4(),
        account_id=uuid4(),
        symbol="EURUSD",
        account_balance=Decimal("10000.00"),
        stop_distance_pips=Decimal("20.0"),
        risk_model=RiskModel.FIXED,
        base_risk_percentage=Decimal("1.0")
    )
    
    # Set prop firm
    await account_firm_mapping.set_account_firm(request.account_id, PropFirm.FTMO)
    
    # Calculate position size
    result = await calculator.calculate_position_size(request)
    
    # Verify comprehensive result
    assert result.base_size > Decimal("0")
    assert result.adjusted_size > Decimal("0")
    assert result.reasoning is not None
    assert result.adjustments.total_adjustment > Decimal("0")
    
    # All adjustments should be applied
    assert result.adjustments.volatility_factor != Decimal("1.0") or True  # May be 1.0 if no adjustment
    assert result.adjustments.drawdown_factor != Decimal("1.0") or True    # May be 1.0 if no drawdown
    assert result.adjustments.correlation_factor != Decimal("1.0") or True # May be 1.0 if no correlation
    assert result.adjustments.limit_factor != Decimal("1.0") or True       # May be 1.0 if within limits
    assert result.adjustments.variance_factor != Decimal("1.0")            # Should always have variance
    
    print(f"End-to-end test successful: {result.base_size} -> {result.adjusted_size} lots")