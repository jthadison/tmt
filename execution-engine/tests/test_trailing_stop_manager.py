"""
Comprehensive tests for Trailing Stop Manager functionality.

Tests trailing stop configuration, monitoring, price-based updates,
and different trailing stop types.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from src.oanda.trailing_stop_manager import (
    TrailingStopManager,
    TrailingStopConfig,
    TrailingType
)
from src.oanda.position_manager import (
    OandaPositionManager,
    PositionInfo,
    PositionSide
)


@pytest.fixture
def mock_position_manager():
    """Mock position manager"""
    manager = Mock(spec=OandaPositionManager)
    manager.position_cache = {}
    manager.modify_stop_loss = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def trailing_stop_manager(mock_position_manager):
    """Trailing stop manager instance for testing"""
    return TrailingStopManager(mock_position_manager, update_interval=1)


@pytest.fixture
def sample_long_position():
    """Sample long position for testing"""
    return PositionInfo(
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


@pytest.fixture
def sample_short_position():
    """Sample short position for testing"""
    return PositionInfo(
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


class TestTrailingStopConfiguration:
    """Test suite for trailing stop configuration and setup"""
    
    @pytest.mark.asyncio
    async def test_set_trailing_stop_distance_long_position(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_long_position
    ):
        """Test setting distance-based trailing stop for long position"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_long_position.position_id: sample_long_position}
        
        # Set trailing stop
        success = await trailing_stop_manager.set_trailing_stop(
            sample_long_position.position_id,
            Decimal('20'),  # 20 pips
            TrailingType.DISTANCE
        )
        
        # Verify success
        assert success is True
        
        # Verify configuration stored
        config = trailing_stop_manager.trailing_stops[sample_long_position.position_id]
        assert config.position_id == sample_long_position.position_id
        assert config.instrument == sample_long_position.instrument
        assert config.side == PositionSide.LONG
        assert config.trailing_type == TrailingType.DISTANCE
        assert config.trail_value == Decimal('20')
        assert config.is_active is True  # Should be active immediately
        assert config.highest_price == sample_long_position.current_price
        
        # Verify initial stop was set
        expected_stop = sample_long_position.current_price - (Decimal('20') * Decimal('0.0001'))
        assert abs(config.current_stop - expected_stop) < Decimal('0.00001')
        
        # Verify monitoring started
        assert trailing_stop_manager.is_monitoring is True
        
    @pytest.mark.asyncio
    async def test_set_trailing_stop_distance_short_position(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_short_position
    ):
        """Test setting distance-based trailing stop for short position"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_short_position.position_id: sample_short_position}
        
        # Set trailing stop
        success = await trailing_stop_manager.set_trailing_stop(
            sample_short_position.position_id,
            Decimal('15'),  # 15 pips
            TrailingType.DISTANCE
        )
        
        # Verify success
        assert success is True
        
        # Verify configuration
        config = trailing_stop_manager.trailing_stops[sample_short_position.position_id]
        assert config.side == PositionSide.SHORT
        assert config.trail_value == Decimal('15')
        assert config.lowest_price == sample_short_position.current_price
        
        # Verify initial stop for short position (above current price)
        expected_stop = sample_short_position.current_price + (Decimal('15') * Decimal('0.0001'))
        assert abs(config.current_stop - expected_stop) < Decimal('0.00001')
        
    @pytest.mark.asyncio
    async def test_set_trailing_stop_percentage(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_long_position
    ):
        """Test setting percentage-based trailing stop"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_long_position.position_id: sample_long_position}
        
        # Set percentage trailing stop
        success = await trailing_stop_manager.set_trailing_stop(
            sample_long_position.position_id,
            Decimal('0.5'),  # 0.5%
            TrailingType.PERCENTAGE
        )
        
        # Verify success
        assert success is True
        
        # Verify configuration
        config = trailing_stop_manager.trailing_stops[sample_long_position.position_id]
        assert config.trailing_type == TrailingType.PERCENTAGE
        assert config.trail_value == Decimal('0.5')
        
        # Verify initial stop calculation
        expected_stop = sample_long_position.current_price * (1 - Decimal('0.5') / 100)
        assert abs(config.current_stop - expected_stop) < Decimal('0.00001')
        
    @pytest.mark.asyncio
    async def test_set_trailing_stop_with_activation_level(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_long_position
    ):
        """Test setting trailing stop with activation level"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_long_position.position_id: sample_long_position}
        
        # Set trailing stop with activation level above current price
        activation_level = Decimal('1.0550')
        success = await trailing_stop_manager.set_trailing_stop(
            sample_long_position.position_id,
            Decimal('20'),
            TrailingType.DISTANCE,
            activation_level
        )
        
        # Verify success
        assert success is True
        
        # Verify configuration
        config = trailing_stop_manager.trailing_stops[sample_long_position.position_id]
        assert config.activation_level == activation_level
        assert config.is_active is False  # Should not be active yet
        assert config.current_stop is None  # No stop set yet
        
    @pytest.mark.asyncio
    async def test_set_trailing_stop_position_not_found(
        self,
        trailing_stop_manager,
        mock_position_manager
    ):
        """Test setting trailing stop for non-existent position"""
        # Empty cache
        mock_position_manager.position_cache = {}
        mock_position_manager.get_open_positions = AsyncMock(return_value=[])
        
        success = await trailing_stop_manager.set_trailing_stop(
            "nonexistent_position",
            Decimal('20'),
            TrailingType.DISTANCE
        )
        
        # Should fail
        assert success is False


class TestPipValueCalculation:
    """Test suite for pip value calculations"""
    
    def test_get_pip_value_standard_pair(self, trailing_stop_manager):
        """Test pip value for standard currency pairs"""
        pip_value = trailing_stop_manager._get_pip_value("EUR_USD")
        assert pip_value == Decimal('0.0001')
        
        pip_value = trailing_stop_manager._get_pip_value("GBP_USD")
        assert pip_value == Decimal('0.0001')
        
    def test_get_pip_value_jpy_pair(self, trailing_stop_manager):
        """Test pip value for JPY currency pairs"""
        pip_value = trailing_stop_manager._get_pip_value("USD_JPY")
        assert pip_value == Decimal('0.01')
        
        pip_value = trailing_stop_manager._get_pip_value("EUR_JPY")
        assert pip_value == Decimal('0.01')


class TestInitialStopCalculation:
    """Test suite for initial stop loss calculation"""
    
    def test_calculate_initial_stop_distance_long(self, trailing_stop_manager, sample_long_position):
        """Test initial stop calculation for distance-based long position"""
        initial_stop = trailing_stop_manager._calculate_initial_stop(
            sample_long_position,
            Decimal('20'),
            TrailingType.DISTANCE
        )
        
        # Expected: 1.0525 - (20 * 0.0001) = 1.0505
        expected = Decimal('1.0525') - (Decimal('20') * Decimal('0.0001'))
        assert initial_stop == expected
        
    def test_calculate_initial_stop_distance_short(self, trailing_stop_manager, sample_short_position):
        """Test initial stop calculation for distance-based short position"""
        initial_stop = trailing_stop_manager._calculate_initial_stop(
            sample_short_position,
            Decimal('15'),
            TrailingType.DISTANCE
        )
        
        # Expected: 1.2485 + (15 * 0.0001) = 1.2500
        expected = Decimal('1.2485') + (Decimal('15') * Decimal('0.0001'))
        assert initial_stop == expected
        
    def test_calculate_initial_stop_percentage_long(self, trailing_stop_manager, sample_long_position):
        """Test initial stop calculation for percentage-based long position"""
        initial_stop = trailing_stop_manager._calculate_initial_stop(
            sample_long_position,
            Decimal('0.5'),
            TrailingType.PERCENTAGE
        )
        
        # Expected: 1.0525 * (1 - 0.5/100) = 1.0525 * 0.995
        expected = Decimal('1.0525') * (Decimal('1') - Decimal('0.5') / 100)
        assert abs(initial_stop - expected) < Decimal('0.00001')
        
    def test_calculate_initial_stop_percentage_short(self, trailing_stop_manager, sample_short_position):
        """Test initial stop calculation for percentage-based short position"""
        initial_stop = trailing_stop_manager._calculate_initial_stop(
            sample_short_position,
            Decimal('0.3'),
            TrailingType.PERCENTAGE
        )
        
        # Expected: 1.2485 * (1 + 0.3/100) = 1.2485 * 1.003
        expected = Decimal('1.2485') * (Decimal('1') + Decimal('0.3') / 100)
        assert abs(initial_stop - expected) < Decimal('0.00001')


class TestTrailingStopUpdates:
    """Test suite for trailing stop update logic"""
    
    @pytest.mark.asyncio
    async def test_update_trailing_stop_long_favorable_move(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_long_position
    ):
        """Test trailing stop update for favorable price movement in long position"""
        # Setup trailing stop configuration
        config = TrailingStopConfig(
            position_id=sample_long_position.position_id,
            instrument=sample_long_position.instrument,
            side=PositionSide.LONG,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('20'),
            current_stop=Decimal('1.0505'),
            highest_price=Decimal('1.0525'),
            is_active=True
        )
        trailing_stop_manager.trailing_stops[sample_long_position.position_id] = config
        
        # Update position price (favorable move)
        sample_long_position.current_price = Decimal('1.0550')
        mock_position_manager.position_cache = {sample_long_position.position_id: sample_long_position}
        
        # Update trailing stop
        await trailing_stop_manager._update_trailing_stop(sample_long_position.position_id)
        
        # Verify stop was updated
        expected_new_stop = Decimal('1.0550') - (Decimal('20') * Decimal('0.0001'))
        assert config.current_stop == expected_new_stop
        assert config.highest_price == Decimal('1.0550')
        assert config.update_count == 1
        
        # Verify modify_stop_loss was called
        mock_position_manager.modify_stop_loss.assert_called_once_with(
            sample_long_position.position_id,
            expected_new_stop
        )
        
    @pytest.mark.asyncio
    async def test_update_trailing_stop_long_unfavorable_move(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_long_position
    ):
        """Test trailing stop update for unfavorable price movement in long position"""
        # Setup trailing stop configuration
        config = TrailingStopConfig(
            position_id=sample_long_position.position_id,
            instrument=sample_long_position.instrument,
            side=PositionSide.LONG,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('20'),
            current_stop=Decimal('1.0505'),
            highest_price=Decimal('1.0525'),
            is_active=True
        )
        trailing_stop_manager.trailing_stops[sample_long_position.position_id] = config
        
        # Update position price (unfavorable move)
        sample_long_position.current_price = Decimal('1.0510')
        mock_position_manager.position_cache = {sample_long_position.position_id: sample_long_position}
        
        # Update trailing stop
        await trailing_stop_manager._update_trailing_stop(sample_long_position.position_id)
        
        # Verify stop was NOT updated (price went down)
        assert config.current_stop == Decimal('1.0505')
        assert config.highest_price == Decimal('1.0525')  # Unchanged
        assert config.update_count == 0
        
        # Verify modify_stop_loss was NOT called
        mock_position_manager.modify_stop_loss.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_update_trailing_stop_short_favorable_move(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_short_position
    ):
        """Test trailing stop update for favorable price movement in short position"""
        # Setup trailing stop configuration
        config = TrailingStopConfig(
            position_id=sample_short_position.position_id,
            instrument=sample_short_position.instrument,
            side=PositionSide.SHORT,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('15'),
            current_stop=Decimal('1.2500'),
            lowest_price=Decimal('1.2485'),
            is_active=True
        )
        trailing_stop_manager.trailing_stops[sample_short_position.position_id] = config
        
        # Update position price (favorable move for short = lower price)
        sample_short_position.current_price = Decimal('1.2470')
        mock_position_manager.position_cache = {sample_short_position.position_id: sample_short_position}
        
        # Update trailing stop
        await trailing_stop_manager._update_trailing_stop(sample_short_position.position_id)
        
        # Verify stop was updated
        expected_new_stop = Decimal('1.2470') + (Decimal('15') * Decimal('0.0001'))
        assert config.current_stop == expected_new_stop
        assert config.lowest_price == Decimal('1.2470')
        assert config.update_count == 1
        
    @pytest.mark.asyncio
    async def test_update_trailing_stop_activation(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_long_position
    ):
        """Test trailing stop activation when price reaches activation level"""
        # Setup trailing stop configuration (not active)
        config = TrailingStopConfig(
            position_id=sample_long_position.position_id,
            instrument=sample_long_position.instrument,
            side=PositionSide.LONG,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('20'),
            activation_level=Decimal('1.0550'),
            is_active=False
        )
        trailing_stop_manager.trailing_stops[sample_long_position.position_id] = config
        
        # Update position price to activation level
        sample_long_position.current_price = Decimal('1.0555')
        mock_position_manager.position_cache = {sample_long_position.position_id: sample_long_position}
        
        # Update trailing stop
        await trailing_stop_manager._update_trailing_stop(sample_long_position.position_id)
        
        # Verify trailing stop was activated
        assert config.is_active is True
        assert config.current_stop is not None
        assert config.highest_price == Decimal('1.0555')
        
    @pytest.mark.asyncio
    async def test_update_trailing_stop_position_closed(
        self,
        trailing_stop_manager,
        mock_position_manager
    ):
        """Test trailing stop removal when position is closed"""
        position_id = "EUR_USD_long"
        
        # Setup trailing stop configuration
        config = TrailingStopConfig(
            position_id=position_id,
            instrument="EUR_USD",
            side=PositionSide.LONG,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('20'),
            is_active=True
        )
        trailing_stop_manager.trailing_stops[position_id] = config
        
        # Position not in cache (closed)
        mock_position_manager.position_cache = {}
        
        # Update trailing stop
        await trailing_stop_manager._update_trailing_stop(position_id)
        
        # Verify trailing stop was removed
        assert position_id not in trailing_stop_manager.trailing_stops


class TestTrailingStopMonitoring:
    """Test suite for trailing stop monitoring"""
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_starts_and_stops(self, trailing_stop_manager):
        """Test that monitoring loop starts and stops correctly"""
        # Initially not monitoring
        assert trailing_stop_manager.is_monitoring is False
        
        # Add a trailing stop to trigger monitoring
        trailing_stop_manager.trailing_stops["test_position"] = TrailingStopConfig(
            position_id="test_position",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('20'),
            is_active=True
        )
        
        # Start monitoring
        task = asyncio.create_task(trailing_stop_manager._monitor_trailing_stops())
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        assert trailing_stop_manager.is_monitoring is True
        
        # Remove trailing stop to stop monitoring
        trailing_stop_manager.trailing_stops.clear()
        
        # Give it a moment to detect empty trailing stops
        await asyncio.sleep(0.1)
        
        # Cancel the task
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        
        assert trailing_stop_manager.is_monitoring is False


class TestTrailingStopManagement:
    """Test suite for trailing stop management operations"""
    
    @pytest.mark.asyncio
    async def test_remove_trailing_stop(self, trailing_stop_manager):
        """Test removing a trailing stop"""
        position_id = "EUR_USD_long"
        
        # Setup trailing stop
        config = TrailingStopConfig(
            position_id=position_id,
            instrument="EUR_USD",
            side=PositionSide.LONG,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('20'),
            is_active=True
        )
        trailing_stop_manager.trailing_stops[position_id] = config
        
        # Remove trailing stop
        success = await trailing_stop_manager.remove_trailing_stop(position_id)
        
        assert success is True
        assert position_id not in trailing_stop_manager.trailing_stops
        
    @pytest.mark.asyncio
    async def test_remove_nonexistent_trailing_stop(self, trailing_stop_manager):
        """Test removing a non-existent trailing stop"""
        success = await trailing_stop_manager.remove_trailing_stop("nonexistent_position")
        
        assert success is False
        
    @pytest.mark.asyncio
    async def test_get_trailing_stop_status(self, trailing_stop_manager):
        """Test getting trailing stop status"""
        position_id = "EUR_USD_long"
        created_time = datetime.now(timezone.utc)
        
        # Setup trailing stop
        config = TrailingStopConfig(
            position_id=position_id,
            instrument="EUR_USD",
            side=PositionSide.LONG,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('20'),
            activation_level=Decimal('1.0550'),
            current_stop=Decimal('1.0505'),
            highest_price=Decimal('1.0525'),
            is_active=True,
            created_at=created_time,
            update_count=3
        )
        trailing_stop_manager.trailing_stops[position_id] = config
        
        # Get status
        status = await trailing_stop_manager.get_trailing_stop_status(position_id)
        
        assert status is not None
        assert status['position_id'] == position_id
        assert status['instrument'] == "EUR_USD"
        assert status['side'] == "long"
        assert status['trailing_type'] == "distance"
        assert status['trail_value'] == 20.0
        assert status['activation_level'] == 1.0550
        assert status['current_stop'] == 1.0505
        assert status['highest_price'] == 1.0525
        assert status['is_active'] is True
        assert status['update_count'] == 3
        
    @pytest.mark.asyncio
    async def test_get_nonexistent_trailing_stop_status(self, trailing_stop_manager):
        """Test getting status for non-existent trailing stop"""
        status = await trailing_stop_manager.get_trailing_stop_status("nonexistent_position")
        
        assert status is None
        
    @pytest.mark.asyncio
    async def test_list_all_trailing_stops(self, trailing_stop_manager):
        """Test listing all trailing stops"""
        # Setup multiple trailing stops
        configs = [
            TrailingStopConfig(
                position_id="EUR_USD_long",
                instrument="EUR_USD",
                side=PositionSide.LONG,
                trailing_type=TrailingType.DISTANCE,
                trail_value=Decimal('20'),
                is_active=True
            ),
            TrailingStopConfig(
                position_id="GBP_USD_short",
                instrument="GBP_USD",
                side=PositionSide.SHORT,
                trailing_type=TrailingType.PERCENTAGE,
                trail_value=Decimal('0.5'),
                is_active=False
            )
        ]
        
        for config in configs:
            trailing_stop_manager.trailing_stops[config.position_id] = config
            
        # List all trailing stops
        stops = await trailing_stop_manager.list_all_trailing_stops()
        
        assert len(stops) == 2
        position_ids = [stop['position_id'] for stop in stops]
        assert "EUR_USD_long" in position_ids
        assert "GBP_USD_short" in position_ids


class TestTrailingStopEdgeCases:
    """Test suite for edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_trailing_stop_with_zero_trail_value(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_long_position
    ):
        """Test setting trailing stop with zero trail value"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_long_position.position_id: sample_long_position}
        
        # Set trailing stop with zero value
        success = await trailing_stop_manager.set_trailing_stop(
            sample_long_position.position_id,
            Decimal('0'),
            TrailingType.DISTANCE
        )
        
        # Should still succeed (edge case handling)
        assert success is True
        
        config = trailing_stop_manager.trailing_stops[sample_long_position.position_id]
        assert config.trail_value == Decimal('0')
        
    @pytest.mark.asyncio
    async def test_modify_stop_loss_failure(
        self,
        trailing_stop_manager,
        mock_position_manager,
        sample_long_position
    ):
        """Test handling of stop loss modification failure"""
        # Setup trailing stop configuration
        config = TrailingStopConfig(
            position_id=sample_long_position.position_id,
            instrument=sample_long_position.instrument,
            side=PositionSide.LONG,
            trailing_type=TrailingType.DISTANCE,
            trail_value=Decimal('20'),
            current_stop=Decimal('1.0505'),
            highest_price=Decimal('1.0525'),
            is_active=True
        )
        trailing_stop_manager.trailing_stops[sample_long_position.position_id] = config
        
        # Make modify_stop_loss fail
        mock_position_manager.modify_stop_loss.return_value = False
        
        # Update position price (favorable move)
        sample_long_position.current_price = Decimal('1.0550')
        mock_position_manager.position_cache = {sample_long_position.position_id: sample_long_position}
        
        # Update trailing stop
        await trailing_stop_manager._update_trailing_stop(sample_long_position.position_id)
        
        # Verify stop was NOT updated due to failure
        assert config.current_stop == Decimal('1.0505')  # Unchanged
        assert config.update_count == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])