"""
Test suite for Risk Calculation Engine.

Tests risk scoring algorithms, performance requirements,
and integration with portfolio analytics.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.core.models import (
    RiskLimits,
    Position,
    AssetClass,
    RiskLevel
)
from app.risk.risk_calculator import RiskCalculationEngine


class TestRiskCalculationEngine:
    """Test cases for risk calculation engine."""
    
    @pytest.fixture
    def risk_limits(self):
        """Create test risk limits."""
        return RiskLimits(
            max_position_size=Decimal("100000"),
            max_positions_per_instrument=3,
            max_leverage=Decimal("30"),
            max_daily_loss=Decimal("1000"),
            max_drawdown=Decimal("5000"),
            required_margin_ratio=Decimal("0.02"),
            max_risk_score=80.0,
            risk_score_warning_threshold=70.0,
            max_var_95=Decimal("2500")
        )
    
    @pytest.fixture
    def risk_calculator(self, risk_limits):
        """Create risk calculation engine."""
        return RiskCalculationEngine(risk_limits)
    
    @pytest.fixture
    def sample_positions(self):
        """Create sample positions for testing."""
        positions = [
            Position(
                account_id="test_account",
                instrument="EUR_USD",
                asset_class=AssetClass.FOREX,
                units=Decimal("10000"),
                average_price=Decimal("1.1000"),
                current_price=Decimal("1.1050"),
                market_value=Decimal("11050"),
                unrealized_pl=Decimal("50"),
                realized_pl=Decimal("0"),
                daily_pl=Decimal("25"),
                opened_at=datetime.now() - timedelta(hours=2)
            ),
            Position(
                account_id="test_account",
                instrument="GBP_USD",
                asset_class=AssetClass.FOREX,
                units=Decimal("-5000"),
                average_price=Decimal("1.2500"),
                current_price=Decimal("1.2450"),
                market_value=Decimal("-6225"),
                unrealized_pl=Decimal("25"),
                realized_pl=Decimal("0"),
                daily_pl=Decimal("15"),
                opened_at=datetime.now() - timedelta(hours=1)
            )
        ]
        return positions
    
    @pytest.mark.asyncio
    async def test_calculate_real_time_risk_performance(self, risk_calculator, sample_positions):
        """Test risk calculation meets < 50ms performance requirement."""
        account_balance = Decimal("10000")
        margin_available = Decimal("9000")
        current_prices = {"EUR_USD": Decimal("1.1050"), "GBP_USD": Decimal("1.2450")}
        
        # Measure calculation time
        import time
        start_time = time.perf_counter()
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=sample_positions,
            account_balance=account_balance,
            margin_available=margin_available,
            current_prices=current_prices
        )
        
        end_time = time.perf_counter()
        calculation_time_ms = (end_time - start_time) * 1000
        
        # Assert performance requirement
        assert calculation_time_ms < 50.0, f"Risk calculation took {calculation_time_ms:.2f}ms, exceeds 50ms target"
        
        # Assert valid risk metrics
        assert risk_metrics.account_id == "test_account"
        assert 0 <= risk_metrics.risk_score <= 100
        assert risk_metrics.risk_level in [level.value for level in RiskLevel]
        assert risk_metrics.total_exposure > 0
        assert risk_metrics.instrument_count == 2
    
    @pytest.mark.asyncio
    async def test_risk_score_calculation(self, risk_calculator, sample_positions):
        """Test risk score calculation logic."""
        account_balance = Decimal("10000")
        margin_available = Decimal("9000")
        current_prices = {"EUR_USD": Decimal("1.1050"), "GBP_USD": Decimal("1.2450")}
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=sample_positions,
            account_balance=account_balance,
            margin_available=margin_available,
            current_prices=current_prices
        )
        
        # Risk score should be reasonable for these positions
        assert 0 <= risk_metrics.risk_score <= 100
        assert risk_metrics.risk_level == RiskLevel.LOW  # Small positions should be low risk
    
    @pytest.mark.asyncio
    async def test_high_risk_position_detection(self, risk_calculator, risk_limits):
        """Test detection of high-risk positions."""
        # Create high-risk position that exceeds limits
        high_risk_positions = [
            Position(
                account_id="test_account",
                instrument="EUR_USD",
                asset_class=AssetClass.FOREX,
                units=Decimal("200000"),  # Exceeds max position size
                average_price=Decimal("1.1000"),
                current_price=Decimal("1.0900"),  # Underwater position
                market_value=Decimal("218000"),
                unrealized_pl=Decimal("-2000"),  # Large loss
                realized_pl=Decimal("0"),
                daily_pl=Decimal("-2000"),  # Exceeds daily loss limit
                opened_at=datetime.now() - timedelta(minutes=5)  # New position
            )
        ]
        
        account_balance = Decimal("10000")
        margin_available = Decimal("2000")  # Low margin
        current_prices = {"EUR_USD": Decimal("1.0900")}
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=high_risk_positions,
            account_balance=account_balance,
            margin_available=margin_available,
            current_prices=current_prices
        )
        
        # Should detect high risk
        assert risk_metrics.risk_score > 70  # High risk score
        assert risk_metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(risk_metrics.risk_limit_breaches) > 0  # Should have breaches
        
        # Check specific breaches
        breach_types = [breach.split(':')[0] for breach in risk_metrics.risk_limit_breaches]
        assert "position_size_exceeded" in breach_types
        assert "daily_loss_exceeded" in breach_types
    
    @pytest.mark.asyncio
    async def test_leverage_calculation(self, risk_calculator, sample_positions):
        """Test leverage calculation accuracy."""
        account_balance = Decimal("1000")  # Small balance for high leverage
        margin_available = Decimal("500")
        current_prices = {"EUR_USD": Decimal("1.1050"), "GBP_USD": Decimal("1.2450")}
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=sample_positions,
            account_balance=account_balance,
            margin_available=margin_available,
            current_prices=current_prices
        )
        
        # Calculate expected leverage
        total_exposure = sum(pos.notional_value for pos in sample_positions)
        expected_leverage = total_exposure / account_balance
        
        assert abs(risk_metrics.current_leverage - expected_leverage) < Decimal("0.01")
        
        # High leverage should increase risk score
        assert risk_metrics.risk_score > 50  # Should be elevated due to leverage
    
    @pytest.mark.asyncio
    async def test_correlation_risk_assessment(self, risk_calculator):
        """Test correlation risk assessment."""
        # Create highly correlated positions (same currency pair)
        correlated_positions = [
            Position(
                account_id="test_account",
                instrument="EUR_USD",
                asset_class=AssetClass.FOREX,
                units=Decimal("10000"),
                average_price=Decimal("1.1000"),
                current_price=Decimal("1.1050"),
                market_value=Decimal("11050"),
                unrealized_pl=Decimal("50"),
                realized_pl=Decimal("0"),
                daily_pl=Decimal("25"),
                opened_at=datetime.now()
            ),
            Position(
                account_id="test_account",
                instrument="EUR_USD",
                asset_class=AssetClass.FOREX,
                units=Decimal("15000"),
                average_price=Decimal("1.1020"),
                current_price=Decimal("1.1050"),
                market_value=Decimal("16575"),
                unrealized_pl=Decimal("45"),
                realized_pl=Decimal("0"),
                daily_pl=Decimal("30"),
                opened_at=datetime.now()
            )
        ]
        
        account_balance = Decimal("10000")
        margin_available = Decimal("9000")
        current_prices = {"EUR_USD": Decimal("1.1050")}
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=correlated_positions,
            account_balance=account_balance,
            margin_available=margin_available,
            current_prices=current_prices
        )
        
        # High correlation should increase risk
        assert risk_metrics.correlation_risk > 0.8  # Should detect high correlation
        assert risk_metrics.sector_diversification < 0.5  # Low diversification
    
    @pytest.mark.asyncio
    async def test_var_calculation(self, risk_calculator, sample_positions):
        """Test Value at Risk calculation."""
        account_balance = Decimal("10000")
        margin_available = Decimal("9000")
        current_prices = {"EUR_USD": Decimal("1.1050"), "GBP_USD": Decimal("1.2450")}
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=sample_positions,
            account_balance=account_balance,
            margin_available=margin_available,
            current_prices=current_prices
        )
        
        # VaR should be calculated
        assert risk_metrics.var_95 >= Decimal("0")
        
        # VaR should be reasonable relative to position size
        total_exposure = sum(pos.notional_value for pos in sample_positions)
        assert risk_metrics.var_95 <= total_exposure * Decimal("0.1")  # Max 10% of exposure
    
    @pytest.mark.asyncio
    async def test_risk_limit_breach_detection(self, risk_calculator, risk_limits):
        """Test comprehensive risk limit breach detection."""
        # Create positions that breach multiple limits
        breach_positions = [
            Position(
                account_id="test_account",
                instrument="EUR_USD",
                asset_class=AssetClass.FOREX,
                units=Decimal("150000"),  # Exceeds max position size
                average_price=Decimal("1.1000"),
                current_price=Decimal("1.1000"),
                market_value=Decimal("165000"),
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                daily_pl=Decimal("-1500"),  # Exceeds daily loss limit
                opened_at=datetime.now()
            )
        ]
        
        account_balance = Decimal("5000")  # Creates high leverage
        margin_available = Decimal("1000")
        current_prices = {"EUR_USD": Decimal("1.1000")}
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=breach_positions,
            account_balance=account_balance,
            margin_available=margin_available,
            current_prices=current_prices
        )
        
        # Should detect multiple breaches
        assert len(risk_metrics.risk_limit_breaches) >= 2
        
        breach_types = [breach.split(':')[0] for breach in risk_metrics.risk_limit_breaches]
        assert "position_size_exceeded" in breach_types
        assert "daily_loss_exceeded" in breach_types
        assert "leverage_exceeded" in breach_types
    
    def test_performance_metrics_tracking(self, risk_calculator, sample_positions):
        """Test performance metrics are tracked correctly."""
        # Initial state
        initial_metrics = risk_calculator.get_performance_metrics()
        assert initial_metrics['total_calculations'] == 0
        
        # Perform calculations
        asyncio.run(self._run_multiple_calculations(risk_calculator, sample_positions, 5))
        
        # Check updated metrics
        updated_metrics = risk_calculator.get_performance_metrics()
        assert updated_metrics['total_calculations'] == 5
        assert updated_metrics['avg_calculation_time_ms'] > 0
        assert updated_metrics['performance_target_met'] >= 0  # Percentage
        
        # All calculations should be under 50ms for passing grade
        if updated_metrics['max_calculation_time_ms'] < 50:
            assert updated_metrics['performance_target_met'] == 1.0
    
    async def _run_multiple_calculations(self, risk_calculator, positions, count):
        """Helper to run multiple risk calculations."""
        for _ in range(count):
            await risk_calculator.calculate_real_time_risk(
                account_id="test_account",
                positions=positions,
                account_balance=Decimal("10000"),
                margin_available=Decimal("9000"),
                current_prices={"EUR_USD": Decimal("1.1050"), "GBP_USD": Decimal("1.2450")}
            )
    
    def test_risk_score_history_tracking(self, risk_calculator):
        """Test risk score history tracking."""
        account_id = "test_account"
        
        # Initially no history
        trends = risk_calculator.get_risk_trends(account_id)
        assert trends['trend'] == 0.0
        
        # Add some history manually
        import time
        for i, score in enumerate([30, 35, 40, 45, 50]):
            risk_calculator._update_risk_score_history(account_id, score)
            time.sleep(0.001)  # Small delay
        
        # Check trends
        trends = risk_calculator.get_risk_trends(account_id)
        assert trends['trend'] > 0  # Should detect upward trend
        assert trends['avg_risk_score'] == 40.0  # Average of scores
        assert trends['min_risk_score'] == 30.0
        assert trends['max_risk_score'] == 50.0
    
    @pytest.mark.asyncio
    async def test_empty_portfolio_handling(self, risk_calculator):
        """Test handling of empty portfolios."""
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=[],  # No positions
            account_balance=Decimal("10000"),
            margin_available=Decimal("10000"),
            current_prices={}
        )
        
        # Should handle gracefully
        assert risk_metrics.risk_score == 0.0
        assert risk_metrics.risk_level == RiskLevel.LOW
        assert risk_metrics.total_exposure == Decimal("0")
        assert risk_metrics.instrument_count == 0
        assert len(risk_metrics.risk_limit_breaches) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, risk_calculator):
        """Test error handling in risk calculations."""
        # Test with invalid data
        invalid_positions = [
            Position(
                account_id="test_account",
                instrument="INVALID",
                asset_class=AssetClass.FOREX,
                units=Decimal("0"),  # Zero units
                average_price=Decimal("0"),  # Zero price
                current_price=Decimal("0"),
                market_value=Decimal("0"),
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                daily_pl=Decimal("0"),
                opened_at=datetime.now()
            )
        ]
        
        # Should not crash
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=invalid_positions,
            account_balance=Decimal("0"),  # Zero balance
            margin_available=Decimal("0"),
            current_prices={}
        )
        
        # Should return safe defaults
        assert risk_metrics is not None
        assert isinstance(risk_metrics.risk_score, float)
    
    @pytest.mark.performance
    async def test_stress_calculation_performance(self, risk_calculator):
        """Stress test risk calculation performance with many positions."""
        # Create many positions
        positions = []
        current_prices = {}
        
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", 
                      "USD_CHF", "NZD_USD", "EUR_GBP", "EUR_JPY", "GBP_JPY"]
        
        for i in range(50):  # 50 positions
            instrument = instruments[i % len(instruments)]
            positions.append(
                Position(
                    account_id="test_account",
                    instrument=instrument,
                    asset_class=AssetClass.FOREX,
                    units=Decimal(str(1000 + i * 100)),
                    average_price=Decimal("1.1000"),
                    current_price=Decimal("1.1050"),
                    market_value=Decimal(str(1105 + i * 110)),
                    unrealized_pl=Decimal(str(5 + i)),
                    realized_pl=Decimal("0"),
                    daily_pl=Decimal(str(2 + i)),
                    opened_at=datetime.now() - timedelta(hours=i)
                )
            )
            current_prices[instrument] = Decimal("1.1050")
        
        # Measure performance with many positions
        import time
        start_time = time.perf_counter()
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=positions,
            account_balance=Decimal("100000"),
            margin_available=Decimal("90000"),
            current_prices=current_prices
        )
        
        end_time = time.perf_counter()
        calculation_time_ms = (end_time - start_time) * 1000
        
        # Should still meet performance target even with many positions
        assert calculation_time_ms < 100.0, f"Risk calculation with 50 positions took {calculation_time_ms:.2f}ms"
        
        # Should handle complex portfolio correctly
        assert risk_metrics.instrument_count == len(set(pos.instrument for pos in positions))
        assert risk_metrics.total_exposure > Decimal("0")
        assert 0 <= risk_metrics.risk_score <= 100


@pytest.mark.asyncio
class TestRiskCalculationIntegration:
    """Integration tests for risk calculation with other components."""
    
    @pytest.fixture
    def risk_limits(self):
        return RiskLimits()
    
    @pytest.fixture
    def risk_calculator(self, risk_limits):
        return RiskCalculationEngine(risk_limits)
    
    async def test_risk_calculation_with_mock_market_data(self, risk_calculator):
        """Test risk calculation with mock market data integration."""
        # Mock market data that affects volatility calculations
        positions = [
            Position(
                account_id="test_account",
                instrument="EUR_USD",
                asset_class=AssetClass.FOREX,
                units=Decimal("10000"),
                average_price=Decimal("1.1000"),
                current_price=Decimal("1.1050"),
                market_value=Decimal("11050"),
                unrealized_pl=Decimal("50"),
                realized_pl=Decimal("0"),
                daily_pl=Decimal("25"),
                opened_at=datetime.now()
            )
        ]
        
        # Simulate high volatility market conditions
        current_prices = {"EUR_USD": Decimal("1.1050")}
        
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id="test_account",
            positions=positions,
            account_balance=Decimal("10000"),
            margin_available=Decimal("9000"),
            current_prices=current_prices
        )
        
        # Risk calculation should complete successfully
        assert risk_metrics is not None
        assert risk_metrics.account_id == "test_account"
        
        # Volatility should affect risk score
        assert risk_metrics.risk_score >= 0