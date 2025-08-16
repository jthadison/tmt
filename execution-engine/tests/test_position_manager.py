"""
Comprehensive tests for OANDA Position Manager functionality.

Tests position data fetching, P&L calculation, stop/take profit modification,
and batch operations.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from src.oanda.position_manager import (
    OandaPositionManager,
    PositionInfo,
    PositionSide
)


@pytest.fixture
def mock_client():
    """Mock OANDA client"""
    client = Mock()
    client.account_id = "test_account_123"
    client.get = AsyncMock()
    client.put = AsyncMock()
    client.patch = AsyncMock()
    return client


@pytest.fixture
def mock_price_stream():
    """Mock price stream manager"""
    stream = Mock()
    stream.get_current_price = AsyncMock()
    return stream


@pytest.fixture
def position_manager(mock_client, mock_price_stream):
    """Position manager instance for testing"""
    return OandaPositionManager(mock_client, mock_price_stream)


@pytest.fixture
def sample_position_data():
    """Sample position data from OANDA API"""
    return {
        'instrument': 'EUR_USD',
        'long': {
            'units': '10000',
            'averagePrice': '1.0500',
            'unrealizedPL': '25.50',
            'openTime': '2024-01-15T10:30:00.000000Z'
        },
        'short': {
            'units': '0',
            'averagePrice': '0',
            'unrealizedPL': '0'
        },
        'financing': '1.25',
        'commission': '0.50',
        'marginUsed': '350.00'
    }


@pytest.fixture
def sample_trades_response():
    """Sample trades response for modification"""
    return {
        'trades': [
            {
                'id': 'trade_1',
                'instrument': 'EUR_USD',
                'currentUnits': '10000',
                'price': '1.0500',
                'openTime': '2024-01-15T10:30:00.000000Z',
                'unrealizedPL': '25.50'
            }
        ]
    }


class TestPositionManager:
    """Test suite for position manager core functionality"""
    
    @pytest.mark.asyncio
    async def test_get_open_positions_success(self, position_manager, mock_client, sample_position_data):
        """Test successful fetching of open positions"""
        # Setup mock response
        mock_client.get.return_value = {
            'positions': [sample_position_data]
        }
        
        with patch.object(position_manager, '_get_current_price', return_value=Decimal('1.0525')):
            positions = await position_manager.get_open_positions()
        
        # Verify results
        assert len(positions) == 1
        position = positions[0]
        assert position.instrument == 'EUR_USD'
        assert position.side == PositionSide.LONG
        assert position.units == Decimal('10000')
        assert position.entry_price == Decimal('1.0500')
        assert position.current_price == Decimal('1.0525')
        assert position.unrealized_pl == Decimal('25.50')
        
        # Verify caching
        assert position.position_id in position_manager.position_cache
        
    @pytest.mark.asyncio
    async def test_get_open_positions_short_position(self, position_manager, mock_client):
        """Test parsing of short position"""
        short_position_data = {
            'instrument': 'GBP_USD',
            'long': {
                'units': '0',
                'averagePrice': '0',
                'unrealizedPL': '0'
            },
            'short': {
                'units': '-5000',
                'averagePrice': '1.2500',
                'unrealizedPL': '-15.75',
                'openTime': '2024-01-15T11:00:00.000000Z'
            },
            'financing': '0.50',
            'commission': '0.25',
            'marginUsed': '200.00'
        }
        
        mock_client.get.return_value = {
            'positions': [short_position_data]
        }
        
        with patch.object(position_manager, '_get_current_price', return_value=Decimal('1.2485')):
            positions = await position_manager.get_open_positions()
        
        position = positions[0]
        assert position.side == PositionSide.SHORT
        assert position.units == Decimal('5000')  # Absolute value
        assert position.entry_price == Decimal('1.2500')
        assert position.unrealized_pl == Decimal('-15.75')
        
    @pytest.mark.asyncio
    async def test_get_open_positions_api_error(self, position_manager, mock_client):
        """Test handling of API errors"""
        mock_client.get.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await position_manager.get_open_positions()
            
    @pytest.mark.asyncio
    async def test_position_pl_percentage_calculation(self, position_manager):
        """Test P&L percentage calculation"""
        position = PositionInfo(
            position_id="EUR_USD_long",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=Decimal('1.0525'),
            unrealized_pl=Decimal('25.00'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=2.5
        )
        
        # P&L percentage = (25 / (10000 * 1.0500)) * 100 = 0.238%
        expected_percentage = (Decimal('25') / (Decimal('10000') * Decimal('1.0500'))) * 100
        assert abs(position.pl_percentage - expected_percentage) < Decimal('0.001')
        
    @pytest.mark.asyncio
    async def test_risk_reward_ratio_calculation(self, position_manager):
        """Test risk/reward ratio calculation"""
        position = PositionInfo(
            position_id="EUR_USD_long",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=Decimal('1.0525'),
            unrealized_pl=Decimal('25.00'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=2.5,
            stop_loss=Decimal('1.0450'),  # 50 pip risk
            take_profit=Decimal('1.0600')  # 100 pip reward
        )
        
        # Risk/Reward = (1.0600 - 1.0500) / (1.0500 - 1.0450) = 100/50 = 2.0
        assert position.risk_reward_ratio == Decimal('2.0')


class TestPositionModification:
    """Test suite for position modification functionality"""
    
    @pytest.mark.asyncio
    async def test_modify_stop_loss_success(self, position_manager, mock_client, sample_trades_response):
        """Test successful stop loss modification"""
        position_id = "EUR_USD_long"
        new_stop_loss = Decimal('1.0450')
        
        # Setup position in cache
        position = PositionInfo(
            position_id=position_id,
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=Decimal('1.0525'),
            unrealized_pl=Decimal('25.00'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=2.5
        )
        position_manager.position_cache[position_id] = position
        
        # Setup mock responses
        mock_client.get.return_value = sample_trades_response
        mock_client.put.return_value = {
            'stopLossOrderTransaction': {
                'id': 'sl_order_123',
                'price': '1.0450'
            }
        }
        
        # Execute modification
        success = await position_manager.modify_stop_loss(position_id, new_stop_loss)
        
        # Verify results
        assert success is True
        assert position.stop_loss == new_stop_loss
        
        # Verify API calls
        mock_client.get.assert_called_once()
        mock_client.put.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_modify_stop_loss_invalid_price(self, position_manager):
        """Test stop loss modification with invalid price"""
        position_id = "EUR_USD_long"
        invalid_stop_loss = Decimal('1.0550')  # Above current price for long position
        
        # Setup position in cache
        position = PositionInfo(
            position_id=position_id,
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=Decimal('1.0525'),
            unrealized_pl=Decimal('25.00'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=2.5
        )
        position_manager.position_cache[position_id] = position
        
        # Execute modification
        success = await position_manager.modify_stop_loss(position_id, invalid_stop_loss)
        
        # Should fail due to invalid price
        assert success is False
        
    @pytest.mark.asyncio
    async def test_modify_take_profit_success(self, position_manager, mock_client, sample_trades_response):
        """Test successful take profit modification"""
        position_id = "EUR_USD_long"
        new_take_profit = Decimal('1.0600')
        
        # Setup position in cache
        position = PositionInfo(
            position_id=position_id,
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=Decimal('1.0525'),
            unrealized_pl=Decimal('25.00'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=2.5
        )
        position_manager.position_cache[position_id] = position
        
        # Setup mock responses
        mock_client.get.return_value = sample_trades_response
        mock_client.put.return_value = {
            'takeProfitOrderTransaction': {
                'id': 'tp_order_123',
                'price': '1.0600'
            }
        }
        
        # Execute modification
        success = await position_manager.modify_take_profit(position_id, new_take_profit)
        
        # Verify results
        assert success is True
        assert position.take_profit == new_take_profit
        
    @pytest.mark.asyncio
    async def test_batch_modify_positions(self, position_manager, mock_client, sample_trades_response):
        """Test batch modification of multiple positions"""
        # Setup multiple positions in cache
        positions = [
            PositionInfo(
                position_id="EUR_USD_long",
                instrument="EUR_USD",
                side=PositionSide.LONG,
                units=Decimal('10000'),
                entry_price=Decimal('1.0500'),
                current_price=Decimal('1.0525'),
                unrealized_pl=Decimal('25.00'),
                swap_charges=Decimal('0'),
                commission=Decimal('0'),
                margin_used=Decimal('350'),
                opened_at=datetime.now(timezone.utc),
                age_hours=2.5
            ),
            PositionInfo(
                position_id="GBP_USD_short",
                instrument="GBP_USD",
                side=PositionSide.SHORT,
                units=Decimal('5000'),
                entry_price=Decimal('1.2500'),
                current_price=Decimal('1.2485'),
                unrealized_pl=Decimal('7.50'),
                swap_charges=Decimal('0'),
                commission=Decimal('0'),
                margin_used=Decimal('200'),
                opened_at=datetime.now(timezone.utc),
                age_hours=1.0
            )
        ]
        
        for pos in positions:
            position_manager.position_cache[pos.position_id] = pos
            
        # Setup mock responses
        mock_client.get.return_value = sample_trades_response
        mock_client.put.return_value = {
            'stopLossOrderTransaction': {'id': 'sl_123'},
            'takeProfitOrderTransaction': {'id': 'tp_123'}
        }
        
        # Execute batch modification
        modifications = [
            {
                'position_id': 'EUR_USD_long',
                'stop_loss': '1.0450',
                'take_profit': '1.0600'
            },
            {
                'position_id': 'GBP_USD_short',
                'stop_loss': '1.2520'
            }
        ]
        
        results = await position_manager.batch_modify_positions(modifications)
        
        # Verify results
        assert len(results) == 2
        assert results['EUR_USD_long'] is True
        assert results['GBP_USD_short'] is True
        
        # Verify positions were updated
        assert positions[0].stop_loss == Decimal('1.0450')
        assert positions[0].take_profit == Decimal('1.0600')
        assert positions[1].stop_loss == Decimal('1.2520')


class TestPositionValidation:
    """Test suite for position validation logic"""
    
    @pytest.mark.parametrize("side,current_price,stop_loss,expected", [
        (PositionSide.LONG, Decimal('1.0500'), Decimal('1.0450'), True),   # Valid: below current
        (PositionSide.LONG, Decimal('1.0500'), Decimal('1.0550'), False),  # Invalid: above current
        (PositionSide.SHORT, Decimal('1.2500'), Decimal('1.2550'), True),  # Valid: above current
        (PositionSide.SHORT, Decimal('1.2500'), Decimal('1.2450'), False), # Invalid: below current
    ])
    def test_validate_stop_loss_price(self, position_manager, side, current_price, stop_loss, expected):
        """Test stop loss price validation"""
        position = PositionInfo(
            position_id="test_position",
            instrument="EUR_USD",
            side=side,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=current_price,
            unrealized_pl=Decimal('0'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=1.0
        )
        
        result = position_manager._validate_stop_loss_price(position, stop_loss)
        assert result == expected
        
    @pytest.mark.parametrize("side,current_price,take_profit,expected", [
        (PositionSide.LONG, Decimal('1.0500'), Decimal('1.0550'), True),   # Valid: above current
        (PositionSide.LONG, Decimal('1.0500'), Decimal('1.0450'), False),  # Invalid: below current
        (PositionSide.SHORT, Decimal('1.2500'), Decimal('1.2450'), True),  # Valid: below current
        (PositionSide.SHORT, Decimal('1.2500'), Decimal('1.2550'), False), # Invalid: above current
    ])
    def test_validate_take_profit_price(self, position_manager, side, current_price, take_profit, expected):
        """Test take profit price validation"""
        position = PositionInfo(
            position_id="test_position",
            instrument="EUR_USD",
            side=side,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=current_price,
            unrealized_pl=Decimal('0'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=1.0
        )
        
        result = position_manager._validate_take_profit_price(position, take_profit)
        assert result == expected


class TestPositionLookup:
    """Test suite for position lookup functionality"""
    
    @pytest.mark.asyncio
    async def test_get_position_by_instrument_cached(self, position_manager):
        """Test getting position by instrument from cache"""
        # Setup position in cache
        position = PositionInfo(
            position_id="EUR_USD_long",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=Decimal('1.0525'),
            unrealized_pl=Decimal('25.00'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=2.5
        )
        position_manager.position_cache[position.position_id] = position
        
        # Get position by instrument
        result = await position_manager.get_position_by_instrument("EUR_USD")
        
        assert result is not None
        assert result.instrument == "EUR_USD"
        assert result.position_id == "EUR_USD_long"
        
    @pytest.mark.asyncio
    async def test_get_position_by_instrument_not_found(self, position_manager, mock_client):
        """Test getting position by instrument when not found"""
        # Setup empty cache and API response
        mock_client.get.return_value = {'positions': []}
        
        result = await position_manager.get_position_by_instrument("EUR_USD")
        
        assert result is None
        
    @pytest.mark.asyncio
    async def test_get_position_by_instrument_refresh_cache(self, position_manager, mock_client, sample_position_data):
        """Test getting position by instrument with cache refresh"""
        # Setup API response but empty cache
        mock_client.get.return_value = {
            'positions': [sample_position_data]
        }
        
        with patch.object(position_manager, '_get_current_price', return_value=Decimal('1.0525')):
            result = await position_manager.get_position_by_instrument("EUR_USD")
        
        assert result is not None
        assert result.instrument == "EUR_USD"
        # Should have called API to refresh cache
        mock_client.get.assert_called_once()


class TestEdgeCases:
    """Test suite for edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_positions_response(self, position_manager, mock_client):
        """Test handling of empty positions response"""
        mock_client.get.return_value = {'positions': []}
        
        positions = await position_manager.get_open_positions()
        
        assert len(positions) == 0
        assert len(position_manager.position_cache) == 0
        
    @pytest.mark.asyncio
    async def test_malformed_position_data(self, position_manager, mock_client):
        """Test handling of malformed position data"""
        malformed_data = {
            'instrument': 'EUR_USD',
            # Missing required fields
        }
        
        mock_client.get.return_value = {'positions': [malformed_data]}
        
        # Should handle gracefully without crashing
        with pytest.raises(Exception):
            await position_manager.get_open_positions()
            
    @pytest.mark.asyncio
    async def test_modify_nonexistent_position(self, position_manager):
        """Test modifying a position that doesn't exist"""
        success = await position_manager.modify_stop_loss("nonexistent_position", Decimal('1.0450'))
        assert success is False
        
    @pytest.mark.asyncio
    async def test_price_stream_unavailable(self, position_manager, mock_client, sample_position_data):
        """Test handling when price stream is unavailable"""
        # Price stream returns None
        position_manager.price_stream.get_current_price.return_value = None
        
        # Should fallback to pricing endpoint
        mock_client.get.side_effect = [
            {'positions': [sample_position_data]},  # First call for positions
            {'prices': [{'closeoutAsk': '1.0525', 'closeoutBid': '1.0523'}]}  # Second call for pricing
        ]
        
        positions = await position_manager.get_open_positions()
        
        assert len(positions) == 1
        assert positions[0].current_price == Decimal('1.0525')  # Should use closeoutAsk for long position


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])