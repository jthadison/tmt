"""
Comprehensive tests for Partial Close Manager functionality.

Tests partial position closing, FIFO compliance, bulk closing,
and criteria-based closing operations.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from src.oanda.partial_close_manager import (
    PartialCloseManager,
    CloseResult,
    CloseType
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
    manager.get_open_positions = AsyncMock()
    manager.client = Mock()
    manager.client.account_id = "test_account_123"
    manager.client.put = AsyncMock()
    return manager


@pytest.fixture
def mock_compliance_engine():
    """Mock compliance engine"""
    engine = Mock()
    engine.validate_fifo_close = AsyncMock()
    engine.is_us_account = AsyncMock(return_value=True)
    return engine


@pytest.fixture
def partial_close_manager(mock_position_manager, mock_compliance_engine):
    """Partial close manager instance for testing"""
    return PartialCloseManager(mock_position_manager, mock_compliance_engine)


@pytest.fixture
def sample_position():
    """Sample position for testing"""
    return PositionInfo(
        position_id="EUR_USD_long",
        instrument="EUR_USD",
        side=PositionSide.LONG,
        units=Decimal('10000'),
        entry_price=Decimal('1.0500'),
        current_price=Decimal('1.0525'),
        unrealized_pl=Decimal('25.00'),
        swap_charges=Decimal('1.25'),
        commission=Decimal('0.50'),
        margin_used=Decimal('350'),
        opened_at=datetime.now(timezone.utc),
        age_hours=2.5
    )


@pytest.fixture
def fifo_result_valid():
    """Valid FIFO compliance result"""
    result = Mock()
    result.valid = True
    result.reason = None
    return result


@pytest.fixture
def fifo_result_invalid():
    """Invalid FIFO compliance result"""
    result = Mock()
    result.valid = False
    result.reason = "FIFO violation: must close oldest position first"
    return result


class TestPartialCloseCalculations:
    """Test suite for unit calculation and validation"""
    
    def test_calculate_units_to_close_decimal(self, partial_close_manager, sample_position):
        """Test calculating units from decimal value"""
        units = partial_close_manager._calculate_units_to_close(sample_position, Decimal('5000'))
        assert units == Decimal('5000')
        
    def test_calculate_units_to_close_percentage(self, partial_close_manager, sample_position):
        """Test calculating units from percentage"""
        units = partial_close_manager._calculate_units_to_close(sample_position, "50%")
        assert units == Decimal('5000')  # 50% of 10000
        
    def test_calculate_units_to_close_percentage_decimal(self, partial_close_manager, sample_position):
        """Test calculating units from percentage with decimal"""
        units = partial_close_manager._calculate_units_to_close(sample_position, "25.5%")
        assert units == Decimal('2550')  # 25.5% of 10000
        
    def test_calculate_units_to_close_string_decimal(self, partial_close_manager, sample_position):
        """Test calculating units from string decimal"""
        units = partial_close_manager._calculate_units_to_close(sample_position, "7500")
        assert units == Decimal('7500')
        
    def test_calculate_units_to_close_invalid_percentage(self, partial_close_manager, sample_position):
        """Test handling of invalid percentage"""
        units = partial_close_manager._calculate_units_to_close(sample_position, "invalid%")
        assert units == Decimal('0')
        
    def test_calculate_units_to_close_invalid_string(self, partial_close_manager, sample_position):
        """Test handling of invalid string"""
        units = partial_close_manager._calculate_units_to_close(sample_position, "not_a_number")
        assert units == Decimal('0')


class TestPartialCloseExecution:
    """Test suite for partial close execution"""
    
    @pytest.mark.asyncio
    async def test_partial_close_position_success(
        self,
        partial_close_manager,
        mock_position_manager,
        sample_position
    ):
        """Test successful partial position close"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_position.position_id: sample_position}
        
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '5000',
                'pl': '12.50'
            }
        }
        
        # Execute partial close
        result = await partial_close_manager.partial_close_position(
            sample_position.position_id,
            Decimal('5000'),
            validate_fifo=False
        )
        
        # Verify result
        assert result.success is True
        assert result.close_type == CloseType.PARTIAL
        assert result.units_requested == Decimal('5000')
        assert result.units_closed == Decimal('5000')
        assert result.transaction_id == 'txn_123'
        assert result.realized_pl == Decimal('12.50')
        
        # Verify position updated
        assert sample_position.units == Decimal('5000')  # Remaining units
        
    @pytest.mark.asyncio
    async def test_partial_close_position_full_close(
        self,
        partial_close_manager,
        mock_position_manager,
        sample_position
    ):
        """Test closing entire position (marked as full close)"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_position.position_id: sample_position}
        
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '10000',
                'pl': '25.00'
            }
        }
        
        # Execute full close
        result = await partial_close_manager.partial_close_position(
            sample_position.position_id,
            Decimal('10000'),
            validate_fifo=False
        )
        
        # Verify result
        assert result.success is True
        assert result.close_type == CloseType.FULL
        assert result.units_closed == Decimal('10000')
        
        # Verify position removed from cache
        assert sample_position.position_id not in mock_position_manager.position_cache
        
    @pytest.mark.asyncio
    async def test_partial_close_position_not_found(
        self,
        partial_close_manager,
        mock_position_manager
    ):
        """Test partial close of non-existent position"""
        # Empty cache
        mock_position_manager.position_cache = {}
        mock_position_manager.get_open_positions.return_value = []
        
        result = await partial_close_manager.partial_close_position(
            "nonexistent_position",
            Decimal('5000')
        )
        
        assert result.success is False
        assert "not found" in result.error_message
        
    @pytest.mark.asyncio
    async def test_partial_close_invalid_units(
        self,
        partial_close_manager,
        mock_position_manager,
        sample_position
    ):
        """Test partial close with invalid unit amount"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_position.position_id: sample_position}
        
        # Test negative units
        result = await partial_close_manager.partial_close_position(
            sample_position.position_id,
            Decimal('-1000')
        )
        
        assert result.success is False
        assert "Invalid close amount" in result.error_message
        
        # Test units exceeding position size
        result = await partial_close_manager.partial_close_position(
            sample_position.position_id,
            Decimal('15000')
        )
        
        assert result.success is False
        assert "exceeds position size" in result.error_message


class TestFIFOCompliance:
    """Test suite for FIFO compliance validation"""
    
    @pytest.mark.asyncio
    async def test_partial_close_fifo_compliant(
        self,
        partial_close_manager,
        mock_position_manager,
        mock_compliance_engine,
        sample_position,
        fifo_result_valid
    ):
        """Test partial close with valid FIFO compliance"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_position.position_id: sample_position}
        
        # Setup FIFO compliance
        mock_compliance_engine.validate_fifo_close.return_value = fifo_result_valid
        
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '5000',
                'pl': '12.50'
            }
        }
        
        # Execute partial close
        result = await partial_close_manager.partial_close_position(
            sample_position.position_id,
            Decimal('5000'),
            validate_fifo=True
        )
        
        # Verify FIFO validation was called
        mock_compliance_engine.validate_fifo_close.assert_called_once_with(
            sample_position.instrument,
            Decimal('5000')
        )
        
        # Verify successful close
        assert result.success is True
        
    @pytest.mark.asyncio
    async def test_partial_close_fifo_violation(
        self,
        partial_close_manager,
        mock_position_manager,
        mock_compliance_engine,
        sample_position,
        fifo_result_invalid
    ):
        """Test partial close with FIFO violation"""
        # Setup position in cache
        mock_position_manager.position_cache = {sample_position.position_id: sample_position}
        
        # Setup FIFO compliance failure
        mock_compliance_engine.validate_fifo_close.return_value = fifo_result_invalid
        
        # Execute partial close
        result = await partial_close_manager.partial_close_position(
            sample_position.position_id,
            Decimal('5000'),
            validate_fifo=True
        )
        
        # Verify FIFO violation detected
        assert result.success is False
        assert "FIFO violation" in result.error_message
        
    @pytest.mark.asyncio
    async def test_requires_fifo_compliance_us_account(
        self,
        partial_close_manager,
        mock_compliance_engine,
        sample_position
    ):
        """Test FIFO compliance requirement for US account"""
        mock_compliance_engine.is_us_account.return_value = True
        
        requires_fifo = await partial_close_manager._requires_fifo_compliance(sample_position)
        
        assert requires_fifo is True
        
    @pytest.mark.asyncio
    async def test_requires_fifo_compliance_non_us_account(
        self,
        partial_close_manager,
        mock_compliance_engine,
        sample_position
    ):
        """Test FIFO compliance requirement for non-US account"""
        mock_compliance_engine.is_us_account.return_value = False
        
        requires_fifo = await partial_close_manager._requires_fifo_compliance(sample_position)
        
        assert requires_fifo is False


class TestBulkOperations:
    """Test suite for bulk closing operations"""
    
    @pytest.mark.asyncio
    async def test_close_all_positions_success(
        self,
        partial_close_manager,
        mock_position_manager
    ):
        """Test successful bulk close of all positions"""
        # Setup multiple positions
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
        
        mock_position_manager.get_open_positions.return_value = positions
        
        # Setup cache
        for pos in positions:
            mock_position_manager.position_cache[pos.position_id] = pos
            
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '10000',
                'pl': '25.00'
            }
        }
        
        # Execute bulk close
        results = await partial_close_manager.close_all_positions()
        
        # Verify results
        assert len(results) == 2
        assert all(result.success for result in results.values())
        assert all(result.close_type == CloseType.FULL for result in results.values())
        
    @pytest.mark.asyncio
    async def test_close_all_positions_filtered(
        self,
        partial_close_manager,
        mock_position_manager
    ):
        """Test bulk close filtered by instrument"""
        # Setup multiple positions
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
        
        mock_position_manager.get_open_positions.return_value = positions
        
        # Setup cache
        for pos in positions:
            mock_position_manager.position_cache[pos.position_id] = pos
            
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '10000',
                'pl': '25.00'
            }
        }
        
        # Execute filtered bulk close
        results = await partial_close_manager.close_all_positions(filter_by_instrument="EUR_USD")
        
        # Verify only EUR_USD position was closed
        assert len(results) == 1
        assert "EUR_USD_long" in results
        assert results["EUR_USD_long"].success is True
        
    @pytest.mark.asyncio
    async def test_close_all_positions_emergency(
        self,
        partial_close_manager,
        mock_position_manager
    ):
        """Test emergency bulk close (bypasses FIFO validation)"""
        # Setup position
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
        
        mock_position_manager.get_open_positions.return_value = [position]
        mock_position_manager.position_cache[position.position_id] = position
        
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '10000',
                'pl': '25.00'
            }
        }
        
        # Execute emergency close
        results = await partial_close_manager.close_all_positions(emergency=True)
        
        # Verify emergency close
        assert len(results) == 1
        assert results[position.position_id].close_type == CloseType.EMERGENCY


class TestCriteriaBasedClosing:
    """Test suite for criteria-based closing operations"""
    
    @pytest.mark.asyncio
    async def test_close_positions_by_profit_criteria(
        self,
        partial_close_manager,
        mock_position_manager
    ):
        """Test closing positions based on profit criteria"""
        # Setup positions with different P&L
        positions = [
            PositionInfo(
                position_id="EUR_USD_long",
                instrument="EUR_USD",
                side=PositionSide.LONG,
                units=Decimal('10000'),
                entry_price=Decimal('1.0500'),
                current_price=Decimal('1.0575'),
                unrealized_pl=Decimal('75.00'),  # Above threshold
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
                unrealized_pl=Decimal('7.50'),  # Below threshold
                swap_charges=Decimal('0'),
                commission=Decimal('0'),
                margin_used=Decimal('200'),
                opened_at=datetime.now(timezone.utc),
                age_hours=1.0
            )
        ]
        
        mock_position_manager.get_open_positions.return_value = positions
        
        # Setup cache
        for pos in positions:
            mock_position_manager.position_cache[pos.position_id] = pos
            
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '10000',
                'pl': '75.00'
            }
        }
        
        # Close positions with profit >= 50
        results = await partial_close_manager.close_positions_by_criteria(
            min_profit=Decimal('50')
        )
        
        # Verify only profitable position was closed
        assert len(results) == 1
        assert "EUR_USD_long" in results
        assert results["EUR_USD_long"].success is True
        
    @pytest.mark.asyncio
    async def test_close_positions_by_loss_criteria(
        self,
        partial_close_manager,
        mock_position_manager
    ):
        """Test closing positions based on loss criteria"""
        # Setup positions with different P&L
        positions = [
            PositionInfo(
                position_id="EUR_USD_long",
                instrument="EUR_USD",
                side=PositionSide.LONG,
                units=Decimal('10000'),
                entry_price=Decimal('1.0500'),
                current_price=Decimal('1.0450'),
                unrealized_pl=Decimal('-50.00'),  # At threshold
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
                unrealized_pl=Decimal('7.50'),  # Above threshold
                swap_charges=Decimal('0'),
                commission=Decimal('0'),
                margin_used=Decimal('200'),
                opened_at=datetime.now(timezone.utc),
                age_hours=1.0
            )
        ]
        
        mock_position_manager.get_open_positions.return_value = positions
        
        # Setup cache
        for pos in positions:
            mock_position_manager.position_cache[pos.position_id] = pos
            
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '10000',
                'pl': '-50.00'
            }
        }
        
        # Close positions with loss <= -50
        results = await partial_close_manager.close_positions_by_criteria(
            max_loss=Decimal('-50')
        )
        
        # Verify only losing position was closed
        assert len(results) == 1
        assert "EUR_USD_long" in results
        assert results["EUR_USD_long"].success is True
        
    @pytest.mark.asyncio
    async def test_close_positions_by_age_criteria(
        self,
        partial_close_manager,
        mock_position_manager
    ):
        """Test closing positions based on age criteria"""
        # Setup positions with different ages
        old_time = datetime.now(timezone.utc).replace(hour=0)
        
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
                opened_at=old_time,
                age_hours=26.0  # Above threshold
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
                age_hours=1.0  # Below threshold
            )
        ]
        
        mock_position_manager.get_open_positions.return_value = positions
        
        # Setup cache
        for pos in positions:
            mock_position_manager.position_cache[pos.position_id] = pos
            
        # Setup mock response
        mock_position_manager.client.put.return_value = {
            'longOrderFillTransaction': {
                'id': 'txn_123',
                'units': '10000',
                'pl': '25.00'
            }
        }
        
        # Close positions older than 24 hours
        results = await partial_close_manager.close_positions_by_criteria(
            min_age_hours=24.0
        )
        
        # Verify only old position was closed
        assert len(results) == 1
        assert "EUR_USD_long" in results
        assert results["EUR_USD_long"].success is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])