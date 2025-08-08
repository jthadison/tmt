"""Tests for position adjustment system."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from ..app.position_adjuster import PositionAdjuster, AdjustmentStrategy
from ..app.models import CorrelationAdjustment, PositionData


class TestPositionAdjuster:
    """Test cases for PositionAdjuster."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def position_adjuster(self, mock_db_session):
        """Create PositionAdjuster instance."""
        return PositionAdjuster(mock_db_session)
    
    @pytest.fixture
    def sample_account_ids(self):
        """Sample account IDs for testing."""
        return [uuid4(), uuid4()]
    
    @pytest.mark.asyncio
    async def test_adjust_positions_for_correlation_gradual(self, position_adjuster, sample_account_ids):
        """Test gradual reduction adjustment strategy."""
        account1_id, account2_id = sample_account_ids
        current_correlation = 0.85
        target_correlation = 0.5
        
        with patch.object(position_adjuster, '_check_adjustment_rate_limit') as mock_rate_limit:
            with patch.object(position_adjuster, '_get_current_positions') as mock_positions:
                mock_rate_limit.return_value = True  # Allow adjustment
                mock_positions.return_value = [
                    {'symbol': 'EURUSD', 'size': 1.0, 'type': 'long'},
                    {'symbol': 'GBPUSD', 'size': 0.8, 'type': 'long'}
                ]
                
                adjustments = await position_adjuster.adjust_positions_for_correlation(
                    account1_id, account2_id, current_correlation, target_correlation,
                    AdjustmentStrategy.GRADUAL_REDUCTION
                )
                
                assert len(adjustments) > 0
                assert all(adj['adjustment_type'] == 'gradual_reduction' for adj in adjustments)
                assert all(adj['correlation_before'] == current_correlation for adj in adjustments)
                assert all(adj['target_correlation'] == target_correlation for adj in adjustments)
    
    @pytest.mark.asyncio
    async def test_adjust_positions_rate_limited(self, position_adjuster, sample_account_ids):
        """Test adjustment blocked by rate limiting."""
        account1_id, account2_id = sample_account_ids
        
        with patch.object(position_adjuster, '_check_adjustment_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = False  # Block adjustment
            
            adjustments = await position_adjuster.adjust_positions_for_correlation(
                account1_id, account2_id, 0.85, 0.5
            )
            
            assert len(adjustments) == 0
    
    @pytest.mark.asyncio
    async def test_gradual_reduction_strategy(self, position_adjuster, sample_account_ids):
        """Test gradual reduction strategy implementation."""
        account1_id, account2_id = sample_account_ids
        correlation_gap = 0.3  # 0.8 - 0.5
        
        positions = [
            {'symbol': 'EURUSD', 'size': 1.0, 'type': 'long'},
            {'symbol': 'GBPUSD', 'size': -0.5, 'type': 'short'}
        ]
        
        adjustments = await position_adjuster._gradual_reduction_strategy(
            account1_id, account2_id, positions, correlation_gap
        )
        
        assert len(adjustments) == len(positions)
        for adj in adjustments:
            assert adj['adjustment_type'] == 'gradual_reduction'
            assert 'size_reduction' in adj
            assert adj['size_reduction'] > 0  # Should reduce position size
    
    @pytest.mark.asyncio
    async def test_position_hedging_strategy(self, position_adjuster, sample_account_ids):
        """Test position hedging strategy."""
        account1_id, account2_id = sample_account_ids
        correlation_gap = 0.4
        
        positions = [
            {'symbol': 'EURUSD', 'size': 1.0, 'type': 'long'}
        ]
        
        adjustments = await position_adjuster._position_hedging_strategy(
            account1_id, account2_id, positions, correlation_gap
        )
        
        assert len(adjustments) > 0
        hedge_adjustment = adjustments[0]
        assert hedge_adjustment['adjustment_type'] == 'position_hedging'
        assert 'hedge_symbol' in hedge_adjustment
        assert 'hedge_size' in hedge_adjustment
    
    @pytest.mark.asyncio
    async def test_rotation_strategy(self, position_adjuster, sample_account_ids):
        """Test position rotation strategy."""
        account1_id, account2_id = sample_account_ids
        correlation_gap = 0.25
        
        positions = [
            {'symbol': 'EURUSD', 'size': 1.0, 'type': 'long'},
            {'symbol': 'GBPUSD', 'size': 0.8, 'type': 'long'}
        ]
        
        with patch.object(position_adjuster, '_select_rotation_targets') as mock_targets:
            mock_targets.return_value = ['USDJPY', 'AUDUSD']
            
            adjustments = await position_adjuster._rotation_strategy(
                account1_id, account2_id, positions, correlation_gap
            )
            
            assert len(adjustments) > 0
            rotation_adjustment = adjustments[0]
            assert rotation_adjustment['adjustment_type'] == 'rotation'
            assert 'from_symbol' in rotation_adjustment
            assert 'to_symbol' in rotation_adjustment
    
    @pytest.mark.asyncio
    async def test_diversification_strategy(self, position_adjuster, sample_account_ids):
        """Test diversification strategy."""
        account1_id, account2_id = sample_account_ids
        correlation_gap = 0.35
        
        positions = [
            {'symbol': 'EURUSD', 'size': 2.0, 'type': 'long'}
        ]
        
        adjustments = await position_adjuster._diversification_strategy(
            account1_id, account2_id, positions, correlation_gap
        )
        
        assert len(adjustments) > 0
        div_adjustment = adjustments[0]
        assert div_adjustment['adjustment_type'] == 'diversification'
        assert 'split_positions' in div_adjustment
        assert len(div_adjustment['split_positions']) > 1
    
    @pytest.mark.asyncio
    async def test_partial_close_strategy(self, position_adjuster, sample_account_ids):
        """Test partial close strategy."""
        account1_id, account2_id = sample_account_ids
        correlation_gap = 0.2
        
        positions = [
            {'symbol': 'EURUSD', 'size': 1.5, 'type': 'long'},
            {'symbol': 'GBPUSD', 'size': 1.0, 'type': 'long'}
        ]
        
        adjustments = await position_adjuster._partial_close_strategy(
            account1_id, account2_id, positions, correlation_gap
        )
        
        assert len(adjustments) > 0
        close_adjustment = adjustments[0]
        assert close_adjustment['adjustment_type'] == 'partial_close'
        assert 'close_percentage' in close_adjustment
        assert 0 < close_adjustment['close_percentage'] <= 1
    
    @pytest.mark.asyncio
    async def test_get_adjustment_suggestions(self, position_adjuster, sample_account_ids):
        """Test getting adjustment suggestions without execution."""
        account1_id, account2_id = sample_account_ids
        current_correlation = 0.8
        target_correlation = 0.5
        
        with patch.object(position_adjuster, '_get_current_positions') as mock_positions:
            mock_positions.return_value = [
                {'symbol': 'EURUSD', 'size': 1.0, 'type': 'long'}
            ]
            
            suggestions = await position_adjuster.get_adjustment_suggestions(
                account1_id, account2_id, current_correlation, target_correlation
            )
            
            assert len(suggestions) > 0
            for suggestion in suggestions:
                assert 'strategy' in suggestion
                assert 'estimated_effectiveness' in suggestion
                assert 'risk_level' in suggestion
                assert 'description' in suggestion
    
    @pytest.mark.asyncio
    async def test_manual_adjustment(self, position_adjuster, mock_db_session):
        """Test manual position adjustment."""
        from ..app.models import AdjustmentRequest
        
        request = AdjustmentRequest(
            account_id=uuid4(),
            symbol="EURUSD",
            adjustment_type="manual_reduce",
            size_change=-0.3,
            reason="High correlation detected"
        )
        
        result = await position_adjuster.manual_adjustment(request)
        
        assert result['success'] is True
        assert result['adjustment_id'] is not None
        assert result['applied_change'] == -0.3
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_and_adjust(self, position_adjuster):
        """Test continuous monitoring and adjustment."""
        account_pairs = [(uuid4(), uuid4())]
        
        with patch.object(position_adjuster, '_get_current_correlation') as mock_correlation:
            with patch.object(position_adjuster, 'adjust_positions_for_correlation') as mock_adjust:
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    mock_correlation.return_value = 0.8  # High correlation
                    mock_adjust.return_value = [{'adjustment_type': 'test'}]
                    
                    # Run one iteration
                    position_adjuster.monitoring = True
                    
                    await position_adjuster._monitor_pair(account_pairs[0])
                    position_adjuster.monitoring = False
                    
                    # Verify adjustment was triggered
                    mock_adjust.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_adjustment_rate_limit(self, position_adjuster, mock_db_session):
        """Test adjustment rate limiting."""
        account1_id, account2_id = uuid4(), uuid4()
        
        # Mock recent adjustments count
        mock_query = Mock()
        mock_query.filter.return_value.count.return_value = 3  # Below limit
        mock_db_session.query.return_value = mock_query
        
        allowed = await position_adjuster._check_adjustment_rate_limit(account1_id, account2_id)
        assert allowed is True
        
        # Test rate limit exceeded
        mock_query.filter.return_value.count.return_value = 6  # Above limit
        allowed = await position_adjuster._check_adjustment_rate_limit(account1_id, account2_id)
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_strategy_selection(self, position_adjuster):
        """Test automatic strategy selection based on correlation gap."""
        # Small gap - should use gradual reduction
        strategy = position_adjuster._select_adjustment_strategy(0.1)
        assert strategy == AdjustmentStrategy.GRADUAL_REDUCTION
        
        # Medium gap - should use hedging
        strategy = position_adjuster._select_adjustment_strategy(0.3)
        assert strategy == AdjustmentStrategy.POSITION_HEDGING
        
        # Large gap - should use rotation or diversification
        strategy = position_adjuster._select_adjustment_strategy(0.5)
        assert strategy in [AdjustmentStrategy.ROTATION, AdjustmentStrategy.DIVERSIFICATION]
    
    @pytest.mark.asyncio
    async def test_effectiveness_calculation(self, position_adjuster):
        """Test adjustment effectiveness calculation."""
        correlation_before = 0.8
        correlation_after = 0.6
        adjustment_type = 'gradual_reduction'
        
        effectiveness = position_adjuster._calculate_effectiveness(
            correlation_before, correlation_after, adjustment_type
        )
        
        assert 0.0 <= effectiveness <= 1.0
        assert effectiveness > 0.5  # Should be effective given the reduction
    
    @pytest.mark.asyncio
    async def test_get_current_positions(self, position_adjuster, mock_db_session):
        """Test getting current positions for account."""
        account_id = uuid4()
        
        # Mock position data
        mock_positions = [
            Mock(symbol='EURUSD', position_size=1.0, position_type='long'),
            Mock(symbol='GBPUSD', position_size=-0.5, position_type='short')
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_positions
        mock_db_session.query.return_value = mock_query
        
        positions = await position_adjuster._get_current_positions(account_id)
        
        assert len(positions) == 2
        assert positions[0]['symbol'] == 'EURUSD'
        assert positions[0]['size'] == 1.0
        assert positions[1]['symbol'] == 'GBPUSD'
        assert positions[1]['size'] == -0.5
    
    @pytest.mark.asyncio
    async def test_record_adjustment(self, position_adjuster, mock_db_session):
        """Test recording adjustment in database."""
        adjustment_data = {
            'account_id': uuid4(),
            'adjustment_type': 'gradual_reduction',
            'symbol': 'EURUSD',
            'size_change': -0.2,
            'correlation_before': 0.8,
            'correlation_after': 0.6,
            'effectiveness': 0.7
        }
        
        await position_adjuster._record_adjustment(adjustment_data)
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        
        # Verify correct data structure
        added_adjustment = mock_db_session.add.call_args[0][0]
        assert hasattr(added_adjustment, 'account_id')
        assert hasattr(added_adjustment, 'adjustment_type')
    
    @pytest.mark.asyncio
    async def test_risk_assessment(self, position_adjuster):
        """Test risk assessment for adjustments."""
        adjustment = {
            'adjustment_type': 'gradual_reduction',
            'size_change': -0.3,
            'symbol': 'EURUSD'
        }
        
        risk_level = position_adjuster._assess_adjustment_risk(adjustment)
        
        assert risk_level in ['low', 'medium', 'high']
        # Gradual reduction should be low risk
        assert risk_level == 'low'
    
    @pytest.mark.asyncio
    async def test_correlation_threshold_check(self, position_adjuster):
        """Test correlation threshold checking for auto-adjustment."""
        # Below threshold - no adjustment needed
        needs_adjustment = position_adjuster._needs_adjustment(0.6)
        assert needs_adjustment is False
        
        # Above threshold - adjustment needed
        needs_adjustment = position_adjuster._needs_adjustment(0.8)
        assert needs_adjustment is True
        
        # Critical level - immediate adjustment needed
        needs_adjustment = position_adjuster._needs_adjustment(0.95)
        assert needs_adjustment is True