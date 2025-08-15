"""
Tests for US Regulatory Compliance Module
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from ..app.us_regulatory import (
    FIFOComplianceEngine,
    AntiHedgingValidator,
    LeverageLimitValidator,
    USRegulatoryComplianceEngine,
    ComplianceResult,
    ComplianceViolationType,
    Position,
    OrderRequest
)


@pytest.fixture
def fifo_engine():
    """Create FIFO compliance engine for testing"""
    return FIFOComplianceEngine()


@pytest.fixture
def sample_position():
    """Create sample position for testing"""
    return Position(
        id="pos_1",
        instrument="EUR_USD",
        units=10000,
        side="BUY",
        entry_price=Decimal("1.2000"),
        timestamp=datetime.utcnow() - timedelta(hours=1),
        account_id="test_account"
    )


@pytest.fixture
def sample_order():
    """Create sample order for testing"""
    return OrderRequest(
        instrument="EUR_USD",
        units=5000,
        side="SELL",
        order_type="CLOSE",
        price=Decimal("1.2010"),
        account_id="test_account",
        account_region="US"
    )


class TestFIFOComplianceEngine:
    """Test FIFO compliance engine"""
    
    @pytest.mark.asyncio
    async def test_non_us_account_bypass(self, fifo_engine):
        """Test that non-US accounts bypass FIFO validation"""
        order = OrderRequest(
            instrument="EUR_USD",
            units=10000,
            side="BUY",
            order_type="MARKET",
            account_region="EU"
        )
        
        result = await fifo_engine.validate_order(order)
        assert result.valid is True
        assert result.violation_type is None
    
    @pytest.mark.asyncio
    async def test_fifo_close_no_positions(self, fifo_engine):
        """Test FIFO close validation when no positions exist"""
        order = OrderRequest(
            instrument="EUR_USD",
            units=5000,
            side="SELL",
            order_type="CLOSE",
            account_id="test_account",
            account_region="US"
        )
        
        result = await fifo_engine.validate_order(order)
        assert result.valid is False
        assert result.violation_type == ComplianceViolationType.FIFO_VIOLATION
        assert "No positions to close" in result.reason
    
    @pytest.mark.asyncio
    async def test_fifo_close_valid(self, fifo_engine, sample_position):
        """Test valid FIFO close operation"""
        # Add position to queue
        fifo_engine.add_position(sample_position)
        
        order = OrderRequest(
            instrument="EUR_USD",
            units=5000,  # Partial close
            side="SELL",  # Opposite of position
            order_type="CLOSE",
            account_id="test_account",
            account_region="US"
        )
        
        result = await fifo_engine.validate_order(order)
        assert result.valid is True
        assert "oldest position first" in result.suggested_action
    
    @pytest.mark.asyncio
    async def test_fifo_close_insufficient_size(self, fifo_engine, sample_position):
        """Test FIFO close with insufficient position size"""
        # Add position to queue
        fifo_engine.add_position(sample_position)
        
        order = OrderRequest(
            instrument="EUR_USD",
            units=15000,  # More than position size
            side="SELL",
            order_type="CLOSE",
            account_id="test_account",
            account_region="US"
        )
        
        result = await fifo_engine.validate_order(order)
        assert result.valid is False
        assert result.violation_type == ComplianceViolationType.FIFO_VIOLATION
        assert "Insufficient position size" in result.reason
    
    def test_auto_select_fifo_positions_full_close(self, fifo_engine):
        """Test automatic FIFO position selection for full close"""
        # Add multiple positions
        pos1 = Position(
            id="pos_1",
            instrument="EUR_USD",
            units=5000,
            side="BUY",
            entry_price=Decimal("1.2000"),
            timestamp=datetime.utcnow() - timedelta(hours=2),
            account_id="test_account"
        )
        pos2 = Position(
            id="pos_2",
            instrument="EUR_USD",
            units=3000,
            side="BUY",
            entry_price=Decimal("1.2010"),
            timestamp=datetime.utcnow() - timedelta(hours=1),
            account_id="test_account"
        )
        
        fifo_engine.add_position(pos1)
        fifo_engine.add_position(pos2)
        
        # Select positions for closing 8000 units
        selected = fifo_engine.auto_select_fifo_positions(
            "test_account", "EUR_USD", 8000, "SELL"
        )
        
        assert len(selected) == 2
        assert selected[0].id == "pos_1"  # Oldest first
        assert selected[0].units == 5000
        assert selected[1].id == "pos_2"  # Full close of second position
        assert selected[1].units == 3000
    
    def test_auto_select_fifo_positions_partial_close(self, fifo_engine):
        """Test automatic FIFO position selection for partial close"""
        pos1 = Position(
            id="pos_1",
            instrument="EUR_USD",
            units=10000,
            side="BUY",
            entry_price=Decimal("1.2000"),
            timestamp=datetime.utcnow() - timedelta(hours=1),
            account_id="test_account"
        )
        
        fifo_engine.add_position(pos1)
        
        # Select positions for closing 3000 units
        selected = fifo_engine.auto_select_fifo_positions(
            "test_account", "EUR_USD", 3000, "SELL"
        )
        
        assert len(selected) == 1
        assert selected[0].id == "pos_1_partial"
        assert selected[0].units == 3000
    
    def test_position_management(self, fifo_engine, sample_position):
        """Test position addition, removal, and updates"""
        # Add position
        fifo_engine.add_position(sample_position)
        queue_key = f"{sample_position.account_id}:{sample_position.instrument}"
        assert len(fifo_engine.position_queues[queue_key]) == 1
        
        # Update position size
        fifo_engine.update_position_size(
            sample_position.account_id,
            sample_position.instrument,
            sample_position.id,
            5000
        )
        assert fifo_engine.position_queues[queue_key][0].units == 5000
        
        # Remove position
        fifo_engine.remove_position(
            sample_position.account_id,
            sample_position.instrument,
            sample_position.id
        )
        assert len(fifo_engine.position_queues[queue_key]) == 0


class TestAntiHedgingValidator:
    """Test anti-hedging validator"""
    
    @pytest.fixture
    def anti_hedging_validator(self, fifo_engine):
        return AntiHedgingValidator(fifo_engine)
    
    @pytest.mark.asyncio
    async def test_non_us_account_bypass(self, anti_hedging_validator):
        """Test that non-US accounts bypass anti-hedging validation"""
        order = OrderRequest(
            instrument="EUR_USD",
            units=10000,
            side="BUY",
            order_type="MARKET",
            account_region="EU"
        )
        
        result = await anti_hedging_validator.validate_no_hedging(order)
        assert result.valid is True
    
    @pytest.mark.asyncio
    async def test_hedging_violation_detected(self, anti_hedging_validator, sample_position):
        """Test hedging violation detection"""
        # Add existing BUY position
        anti_hedging_validator.fifo_engine.add_position(sample_position)
        
        # Try to open opposite SELL position
        order = OrderRequest(
            instrument="EUR_USD",
            units=5000,
            side="SELL",  # Opposite direction
            order_type="MARKET",
            account_id="test_account",
            account_region="US"
        )
        
        result = await anti_hedging_validator.validate_no_hedging(order)
        assert result.valid is False
        assert result.violation_type == ComplianceViolationType.HEDGING_VIOLATION
        assert "Hedging violation" in result.reason
        assert "Close existing BUY position first" in result.suggested_action
    
    @pytest.mark.asyncio
    async def test_same_direction_allowed(self, anti_hedging_validator, sample_position):
        """Test that same direction positions are allowed"""
        # Add existing BUY position
        anti_hedging_validator.fifo_engine.add_position(sample_position)
        
        # Try to open same direction BUY position
        order = OrderRequest(
            instrument="EUR_USD",
            units=5000,
            side="BUY",  # Same direction
            order_type="MARKET",
            account_id="test_account",
            account_region="US"
        )
        
        result = await anti_hedging_validator.validate_no_hedging(order)
        assert result.valid is True
    
    @pytest.mark.asyncio
    async def test_close_order_not_hedging(self, anti_hedging_validator, sample_position):
        """Test that close orders are not considered hedging"""
        # Add existing BUY position
        anti_hedging_validator.fifo_engine.add_position(sample_position)
        
        # Try to close with SELL order
        order = OrderRequest(
            instrument="EUR_USD",
            units=5000,
            side="SELL",
            order_type="CLOSE",  # Close order, not new position
            account_id="test_account",
            account_region="US"
        )
        
        result = await anti_hedging_validator.validate_no_hedging(order)
        assert result.valid is True
    
    def test_would_create_hedge(self, anti_hedging_validator, sample_position):
        """Test hedge detection logic"""
        # Test hedge scenario
        hedge_order = OrderRequest(
            instrument="EUR_USD",
            units=5000,
            side="SELL",  # Opposite to position
            order_type="MARKET",
            account_id="test_account"
        )
        
        assert anti_hedging_validator.would_create_hedge(sample_position, hedge_order) is True
        
        # Test non-hedge scenario (same direction)
        same_direction_order = OrderRequest(
            instrument="EUR_USD",
            units=5000,
            side="BUY",  # Same as position
            order_type="MARKET",
            account_id="test_account"
        )
        
        assert anti_hedging_validator.would_create_hedge(sample_position, same_direction_order) is False


class TestLeverageLimitValidator:
    """Test leverage limit validator"""
    
    @pytest.fixture
    def leverage_validator(self):
        return LeverageLimitValidator()
    
    @pytest.mark.asyncio
    async def test_non_us_account_bypass(self, leverage_validator):
        """Test that non-US accounts bypass leverage validation"""
        order = OrderRequest(
            instrument="EUR_USD",
            units=100000,
            side="BUY",
            order_type="MARKET",
            price=Decimal("1.2000"),
            account_region="EU"
        )
        
        result = await leverage_validator.validate_leverage(
            order, Decimal("1000"), Decimal("0")
        )
        assert result.valid is True
    
    @pytest.mark.asyncio
    async def test_major_pair_leverage_limit(self, leverage_validator):
        """Test leverage limit for major currency pairs"""
        order = OrderRequest(
            instrument="EUR_USD",  # Major pair
            units=100000,
            side="BUY",
            order_type="MARKET",
            price=Decimal("1.2000"),
            account_id="test_account",
            account_region="US"
        )
        
        # Account balance: $10,000, Position value: $120,000
        # Required margin at 50:1 = $2,400, should pass
        result = await leverage_validator.validate_leverage(
            order, Decimal("10000"), Decimal("0")
        )
        assert result.valid is True
        assert result.metadata["pair_type"] == "major"
        assert result.metadata["max_leverage"] == "50"
    
    @pytest.mark.asyncio
    async def test_minor_pair_leverage_limit(self, leverage_validator):
        """Test leverage limit for minor currency pairs"""
        order = OrderRequest(
            instrument="EUR_GBP",  # Minor pair
            units=100000,
            side="BUY",
            order_type="MARKET",
            price=Decimal("0.8500"),
            account_id="test_account",
            account_region="US"
        )
        
        # Account balance: $5,000, Position value: $85,000
        # Required margin at 20:1 = $4,250, should pass
        result = await leverage_validator.validate_leverage(
            order, Decimal("5000"), Decimal("0")
        )
        assert result.valid is True
        assert result.metadata["pair_type"] == "minor"
        assert result.metadata["max_leverage"] == "20"
    
    @pytest.mark.asyncio
    async def test_leverage_violation_major_pair(self, leverage_validator):
        """Test leverage violation for major pairs"""
        order = OrderRequest(
            instrument="EUR_USD",  # Major pair
            units=500000,  # Large position
            side="BUY",
            order_type="MARKET",
            price=Decimal("1.2000"),
            account_id="test_account",
            account_region="US"
        )
        
        # Account balance: $5,000, Position value: $600,000
        # Required margin at 50:1 = $12,000, exceeds balance
        result = await leverage_validator.validate_leverage(
            order, Decimal("5000"), Decimal("0")
        )
        assert result.valid is False
        assert result.violation_type == ComplianceViolationType.LEVERAGE_VIOLATION
        assert "Leverage limit exceeded" in result.reason
        assert "Reduce position size" in result.suggested_action
    
    @pytest.mark.asyncio
    async def test_leverage_violation_minor_pair(self, leverage_validator):
        """Test leverage violation for minor pairs"""
        order = OrderRequest(
            instrument="EUR_GBP",  # Minor pair
            units=200000,  # Large position
            side="BUY",
            order_type="MARKET",
            price=Decimal("0.8500"),
            account_id="test_account",
            account_region="US"
        )
        
        # Account balance: $5,000, Position value: $170,000
        # Required margin at 20:1 = $8,500, exceeds balance
        result = await leverage_validator.validate_leverage(
            order, Decimal("5000"), Decimal("0")
        )
        assert result.valid is False
        assert result.violation_type == ComplianceViolationType.LEVERAGE_VIOLATION
        assert "minor pairs limited to 20:1" in result.reason
    
    @pytest.mark.asyncio
    async def test_leverage_with_existing_margin(self, leverage_validator):
        """Test leverage calculation with existing margin usage"""
        order = OrderRequest(
            instrument="EUR_USD",
            units=100000,
            side="BUY",
            order_type="MARKET",
            price=Decimal("1.2000"),
            account_id="test_account",
            account_region="US"
        )
        
        # Account balance: $10,000, Already using $7,000 margin
        # Available margin: $3,000, Required: $2,400, should pass
        result = await leverage_validator.validate_leverage(
            order, Decimal("10000"), Decimal("7000")
        )
        assert result.valid is True
    
    def test_calculate_max_position_size(self, leverage_validator):
        """Test maximum position size calculation"""
        # Major pair with $5,000 available margin
        max_units = leverage_validator.calculate_max_position_size(
            "EUR_USD", Decimal("1.2000"), Decimal("5000")
        )
        # Max position value = $5,000 * 50 = $250,000
        # Max units = $250,000 / $1.2000 = 208,333
        assert max_units == 208333
        
        # Minor pair with $5,000 available margin
        max_units = leverage_validator.calculate_max_position_size(
            "EUR_GBP", Decimal("0.8500"), Decimal("5000")
        )
        # Max position value = $5,000 * 20 = $100,000
        # Max units = $100,000 / $0.8500 = 117,647
        assert max_units == 117647


class TestUSRegulatoryComplianceEngine:
    """Test comprehensive US regulatory compliance engine"""
    
    @pytest.fixture
    def compliance_engine(self):
        return USRegulatoryComplianceEngine()
    
    @pytest.mark.asyncio
    async def test_non_us_account_bypass(self, compliance_engine):
        """Test that non-US accounts bypass all validations"""
        order = OrderRequest(
            instrument="EUR_USD",
            units=100000,
            side="BUY",
            order_type="MARKET",
            price=Decimal("1.2000"),
            account_region="EU"
        )
        
        result = await compliance_engine.validate_order_compliance(
            order, Decimal("1000")
        )
        assert result.valid is True
    
    @pytest.mark.asyncio
    async def test_comprehensive_validation_pass(self, compliance_engine):
        """Test comprehensive validation that passes all checks"""
        order = OrderRequest(
            instrument="EUR_USD",
            units=10000,
            side="BUY",
            order_type="MARKET",
            price=Decimal("1.2000"),
            account_id="test_account",
            account_region="US"
        )
        
        result = await compliance_engine.validate_order_compliance(
            order, Decimal("10000")
        )
        assert result.valid is True
        assert "FIFO" in result.metadata["validations_passed"]
        assert "ANTI_HEDGING" in result.metadata["validations_passed"]
        assert "LEVERAGE" in result.metadata["validations_passed"]
    
    @pytest.mark.asyncio
    async def test_comprehensive_validation_hedging_fail(self, compliance_engine, sample_position):
        """Test comprehensive validation failing on hedging"""
        # Add existing position
        compliance_engine.fifo_engine.add_position(sample_position)
        
        # Try to hedge
        order = OrderRequest(
            instrument="EUR_USD",
            units=5000,
            side="SELL",  # Opposite to existing position
            order_type="MARKET",
            price=Decimal("1.2000"),
            account_id="test_account",
            account_region="US"
        )
        
        result = await compliance_engine.validate_order_compliance(
            order, Decimal("10000")
        )
        assert result.valid is False
        assert result.violation_type == ComplianceViolationType.HEDGING_VIOLATION
    
    @pytest.mark.asyncio
    async def test_comprehensive_validation_leverage_fail(self, compliance_engine):
        """Test comprehensive validation failing on leverage"""
        order = OrderRequest(
            instrument="EUR_USD",
            units=500000,  # Excessive size
            side="BUY",
            order_type="MARKET",
            price=Decimal("1.2000"),
            account_id="test_account",
            account_region="US"
        )
        
        result = await compliance_engine.validate_order_compliance(
            order, Decimal("5000")  # Small balance
        )
        assert result.valid is False
        assert result.violation_type == ComplianceViolationType.LEVERAGE_VIOLATION
    
    def test_compliance_summary(self, compliance_engine, sample_position):
        """Test compliance summary generation"""
        compliance_engine.fifo_engine.add_position(sample_position)
        
        summary = compliance_engine.get_compliance_summary("test_account")
        assert summary["account_id"] == "test_account"
        assert summary["compliance_status"] == "ACTIVE"
        assert summary["fifo_positions"] >= 1
        assert isinstance(summary["total_compliance_checks"], int)
        assert isinstance(summary["recent_violations"], list)


if __name__ == "__main__":
    pytest.main([__file__])