"""
Unit tests for EnhancedPositionSizer

Tests position size calculation with all features.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from position_sizing.enhanced_sizer import EnhancedPositionSizer, PositionSizeResult


class MockOandaAccount:
    """Mock OANDA account response"""
    def __init__(self, balance=10000.0, margin_available=9000.0, margin_used=1000.0):
        self.balance = balance
        self.margin_available = margin_available
        self.margin_used = margin_used


class MockOandaPosition:
    """Mock OANDA position"""
    def __init__(self, instrument, units, average_price):
        self.instrument = instrument
        self.units = units
        self.average_price = average_price


class TestEnhancedPositionSizer:
    """Test suite for EnhancedPositionSizer"""

    @pytest.fixture
    def mock_oanda_client(self):
        """Create mock OANDA client"""
        client = AsyncMock()

        # Mock account info
        async def mock_get_account_info(account_id):
            return MockOandaAccount(balance=10000.0)

        # Mock positions
        async def mock_get_positions(account_id):
            return []

        # Mock current price
        async def mock_get_current_price(instrument):
            return {"bid": 1.08, "ask": 1.09, "mid": 1.085}

        client.get_account_info = mock_get_account_info
        client.get_positions = mock_get_positions
        client.get_current_price = mock_get_current_price

        return client

    @pytest.fixture
    def sizer(self, mock_oanda_client):
        """Create EnhancedPositionSizer instance"""
        return EnhancedPositionSizer(
            oanda_client=mock_oanda_client,
            account_currency="USD",
            min_account_balance=Decimal("5000"),
            max_per_trade_pct=Decimal("0.05"),
            max_portfolio_heat_pct=Decimal("0.15"),
            max_per_instrument_pct=Decimal("0.10")
        )

    @pytest.mark.asyncio
    async def test_calculate_position_size_eur_usd_long(self, sizer):
        """Test position size calculation for EUR_USD long trade"""
        result = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY",
            risk_percent=Decimal("0.02")
        )

        # Account balance: $10,000
        # Risk: 2% = $200
        # Stop distance: 50 pips (0.0050)
        # Pip value for EUR_USD: 0.0001
        # Position size = $200 / (50 * $0.0001 per unit) = $200 / $0.005 = 40,000 units

        assert isinstance(result, PositionSizeResult)
        assert result.position_size > 0  # Positive for long
        assert result.account_balance == Decimal("10000.0")
        assert result.stop_distance_pips == Decimal("50")
        assert result.calculation_time_ms > 0

    @pytest.mark.asyncio
    async def test_calculate_position_size_usd_jpy_short(self, sizer):
        """Test position size calculation for USD_JPY short trade"""
        result = await sizer.calculate_position_size(
            instrument="USD_JPY",
            entry_price=Decimal("149.50"),
            stop_loss=Decimal("150.00"),
            account_id="test-account",
            direction="SELL",
            risk_percent=Decimal("0.02")
        )

        # Should return negative position size for short
        assert result.position_size < 0
        assert result.stop_distance_pips == Decimal("50")

    @pytest.mark.asyncio
    async def test_account_balance_caching(self, sizer):
        """Test that account balance is cached"""
        # First call
        result1 = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY"
        )

        # Second call should use cached balance
        result2 = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY"
        )

        assert result1.account_balance == result2.account_balance
        assert len(sizer.account_balance_cache) > 0

    @pytest.mark.asyncio
    async def test_per_trade_limit_applied(self, sizer):
        """Test that per-trade limit (5%) is enforced"""
        # Use very tight stop to force large position size
        result = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0849"),  # Only 1 pip stop
            account_id="test-account",
            direction="BUY",
            risk_percent=Decimal("0.02")
        )

        # Position should be limited by 5% max
        # Max position value = $10,000 * 5% = $500
        # At price 1.0850, max units ≈ 460
        position_value = abs(result.position_size) * Decimal("1.0850")
        max_allowed = Decimal("10000") * Decimal("0.05")

        assert position_value <= max_allowed * Decimal("1.01")  # Allow 1% tolerance

    @pytest.mark.asyncio
    async def test_broker_min_size_enforced(self, sizer):
        """Test that broker minimum size is enforced"""
        # Use very wide stop to force tiny position size
        result = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0000"),  # 850 pip stop
            account_id="test-account",
            direction="BUY",
            risk_percent=Decimal("0.001")  # Very small risk
        )

        # Should enforce minimum 1 unit
        assert abs(result.position_size) >= 1

    @pytest.mark.asyncio
    async def test_invalid_stop_distance_returns_zero(self, sizer):
        """Test that invalid stop distance returns zero position"""
        # Entry price = stop loss (0 pip stop)
        result = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0850"),
            account_id="test-account",
            direction="BUY"
        )

        assert result.position_size == 0
        assert "calculation_error" in result.constraints_applied or len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_warnings_generated_for_low_balance(self, sizer, mock_oanda_client):
        """Test warnings generated when balance is low"""
        # Mock low balance
        async def mock_get_account_info_low_balance(account_id):
            return MockOandaAccount(balance=3000.0)  # Below $5000 minimum

        mock_oanda_client.get_account_info = mock_get_account_info_low_balance

        result = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY"
        )

        # Should have warning about low balance
        assert len(result.warnings) > 0
        assert any("balance" in warning.lower() for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_portfolio_heat_reduction(self, sizer, mock_oanda_client):
        """Test position reduction when portfolio heat is high"""
        # Mock positions showing high portfolio heat
        async def mock_get_positions_high_heat(account_id):
            return [
                MockOandaPosition("GBP_USD", 50000, 1.25),  # $62,500 position
                MockOandaPosition("AUD_USD", 30000, 0.65),  # $19,500 position
            ]
            # Total exposure: ~$82,000 on $10,000 account = high heat

        mock_oanda_client.get_positions = mock_get_positions_high_heat

        result = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY"
        )

        # Should apply portfolio heat constraint
        assert "portfolio_heat_high" in result.constraints_applied or len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_metadata_populated(self, sizer):
        """Test that result metadata is properly populated"""
        result = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY",
            take_profit=Decimal("1.0900")
        )

        assert "instrument" in result.metadata
        assert "entry_price" in result.metadata
        assert "stop_loss" in result.metadata
        assert "take_profit" in result.metadata
        assert "pip_info" in result.metadata
        assert result.metadata["instrument"] == "EUR_USD"

    @pytest.mark.asyncio
    async def test_calculation_performance_target(self, sizer):
        """Test that calculation meets < 50ms performance target"""
        result = await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY"
        )

        # Should meet 50ms target (allowing some tolerance for test environment)
        assert result.calculation_time_ms < 100.0

    @pytest.mark.asyncio
    async def test_clear_caches(self, sizer):
        """Test clearing all caches"""
        # Populate caches
        await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY"
        )

        # Clear caches
        sizer.clear_caches()

        # Caches should be empty
        assert len(sizer.account_balance_cache) == 0

    @pytest.mark.asyncio
    async def test_get_statistics(self, sizer):
        """Test statistics retrieval"""
        # Calculate a position
        await sizer.calculate_position_size(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
            account_id="test-account",
            direction="BUY"
        )

        stats = sizer.get_statistics()

        assert "balance_cache_entries" in stats
        assert "currency_converter_stats" in stats
        assert "configuration" in stats
        assert stats["configuration"]["account_currency"] == "USD"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
