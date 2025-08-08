"""Tests for correlation monitoring system."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4
import numpy as np

from src.agents.anti_correlation.app.correlation_monitor import CorrelationMonitor
from src.agents.anti_correlation.app.models import CorrelationMetric


class TestCorrelationMonitor:
    """Test cases for CorrelationMonitor."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def correlation_monitor(self, mock_db_session):
        """Create CorrelationMonitor instance."""
        return CorrelationMonitor(mock_db_session)
    
    @pytest.fixture
    def sample_account_ids(self):
        """Sample account IDs for testing."""
        return [uuid4(), uuid4()]
    
    @pytest.mark.asyncio
    async def test_calculate_correlation_basic(self, correlation_monitor, sample_account_ids):
        """Test basic correlation calculation."""
        account1_id, account2_id = sample_account_ids
        time_window = 3600
        
        # Mock position data
        with patch.object(correlation_monitor, '_get_position_data_for_period') as mock_get_positions:
            mock_get_positions.return_value = (
                [1.0, 1.1, 1.2, 1.3],  # Account 1 positions
                [0.9, 1.0, 1.1, 1.2]   # Account 2 positions (highly correlated)
            )
            
            correlation, p_value, components = await correlation_monitor.calculate_correlation(
                account1_id, account2_id, time_window, include_components=True
            )
            
            assert 0.8 <= correlation <= 1.0  # Should be high correlation
            assert p_value < 0.05  # Should be statistically significant
            assert 'position_correlation' in components
            assert 'timing_correlation' in components
    
    @pytest.mark.asyncio
    async def test_calculate_correlation_no_data(self, correlation_monitor, sample_account_ids):
        """Test correlation calculation with no data."""
        account1_id, account2_id = sample_account_ids
        
        with patch.object(correlation_monitor, '_get_position_data_for_period') as mock_get_positions:
            mock_get_positions.return_value = ([], [])  # No data
            
            correlation, p_value, components = await correlation_monitor.calculate_correlation(
                account1_id, account2_id, 3600
            )
            
            assert correlation == 0.0
            assert p_value == 1.0
    
    @pytest.mark.asyncio
    async def test_update_correlation_matrix(self, correlation_monitor):
        """Test correlation matrix update."""
        account_ids = [uuid4(), uuid4(), uuid4()]
        
        with patch.object(correlation_monitor, 'calculate_correlation') as mock_calc:
            mock_calc.return_value = (0.6, 0.02, {})
            
            result = await correlation_monitor.update_correlation_matrix(
                account_ids, time_window=3600
            )
            
            assert len(result.correlation_matrix) == 3
            assert len(result.correlation_matrix[0]) == 3
            assert result.correlation_matrix[0][0] == 1.0  # Self-correlation
            assert 0 <= result.correlation_matrix[0][1] <= 1.0
    
    @pytest.mark.asyncio
    async def test_get_high_correlation_pairs(self, correlation_monitor, mock_db_session):
        """Test getting high correlation pairs."""
        # Mock database query results
        mock_metrics = [
            Mock(
                account_1_id=uuid4(),
                account_2_id=uuid4(),
                correlation_coefficient=0.8,
                calculation_time=datetime.utcnow(),
                p_value=0.01
            )
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_metrics
        mock_db_session.query.return_value = mock_query
        
        pairs = await correlation_monitor.get_high_correlation_pairs(0.7, 3600)
        
        assert len(pairs) == 1
        assert pairs[0]['correlation'] == 0.8
        assert pairs[0]['p_value'] == 0.01
    
    @pytest.mark.asyncio
    async def test_get_correlation_history(self, correlation_monitor, mock_db_session):
        """Test getting correlation history."""
        account1_id, account2_id = uuid4(), uuid4()
        
        # Mock historical data
        mock_metrics = [
            Mock(
                correlation_coefficient=0.6,
                calculation_time=datetime.utcnow() - timedelta(hours=1),
                p_value=0.03
            ),
            Mock(
                correlation_coefficient=0.7,
                calculation_time=datetime.utcnow() - timedelta(hours=2),
                p_value=0.02
            )
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_metrics
        mock_db_session.query.return_value = mock_query
        
        history = await correlation_monitor.get_correlation_history(
            account1_id, account2_id, hours=24
        )
        
        assert len(history) == 2
        assert history[0]['correlation'] == 0.6
        assert history[1]['correlation'] == 0.7
    
    def test_pearson_correlation(self, correlation_monitor):
        """Test Pearson correlation calculation."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]  # Perfect positive correlation
        
        correlation, p_value = correlation_monitor._calculate_pearson_correlation(x, y)
        
        assert abs(correlation - 1.0) < 0.001  # Perfect correlation
        assert p_value < 0.05  # Significant
    
    def test_pearson_correlation_no_variance(self, correlation_monitor):
        """Test Pearson correlation with constant values."""
        x = [1, 1, 1, 1, 1]  # No variance
        y = [2, 3, 4, 5, 6]
        
        correlation, p_value = correlation_monitor._calculate_pearson_correlation(x, y)
        
        assert correlation == 0.0
        assert p_value == 1.0
    
    @pytest.mark.asyncio
    async def test_store_correlation_metric(self, correlation_monitor, mock_db_session):
        """Test storing correlation metric."""
        account1_id, account2_id = uuid4(), uuid4()
        
        await correlation_monitor._store_correlation_metric(
            account1_id, account2_id, 0.75, 0.02, components={}
        )
        
        # Verify database session methods called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_real_time(self, correlation_monitor):
        """Test real-time monitoring loop."""
        account_ids = [uuid4(), uuid4()]
        
        with patch.object(correlation_monitor, 'update_correlation_matrix') as mock_update:
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                # Mock the matrix update to return immediately
                mock_update.return_value = Mock(
                    correlation_matrix=[[1.0, 0.6], [0.6, 1.0]]
                )
                
                # Run one iteration
                correlation_monitor.monitoring = True
                
                # Start monitoring in background (would normally run indefinitely)
                task = correlation_monitor.monitor_real_time(account_ids)
                
                # Stop monitoring after first iteration
                correlation_monitor.monitoring = False
                
                # Verify monitoring was called
                mock_update.assert_called_with(account_ids, 300)  # 5-minute window
    
    @pytest.mark.asyncio
    async def test_component_correlation_calculation(self, correlation_monitor):
        """Test individual component correlation calculations."""
        account1_positions = [1.0, 1.1, 1.2, 1.3]
        account2_positions = [0.9, 1.0, 1.1, 1.2]
        
        # Mock timing and P&L data
        with patch.object(correlation_monitor, '_get_timing_data_for_period') as mock_timing:
            with patch.object(correlation_monitor, '_get_pnl_data_for_period') as mock_pnl:
                mock_timing.return_value = (
                    [10, 11, 12, 13],  # Account 1 timing
                    [9, 10, 11, 12]    # Account 2 timing
                )
                mock_pnl.return_value = (
                    [100, 110, 120, 130],  # Account 1 P&L
                    [90, 100, 110, 120]    # Account 2 P&L
                )
                
                components = await correlation_monitor._calculate_component_correlations(
                    uuid4(), uuid4(), 3600
                )
                
                assert 'position_correlation' in components
                assert 'timing_correlation' in components
                assert 'size_correlation' in components
                assert 'pnl_correlation' in components
                
                # All should be positive correlations given the test data
                for key, (corr, p_val) in components.items():
                    assert corr >= 0.8  # High correlation expected
                    assert p_val < 0.05  # Significant
    
    def test_risk_assessment(self, correlation_monitor):
        """Test correlation risk assessment."""
        # Test different correlation levels
        assert correlation_monitor._assess_correlation_risk(0.9) == "critical"
        assert correlation_monitor._assess_correlation_risk(0.75) == "high" 
        assert correlation_monitor._assess_correlation_risk(0.55) == "medium"
        assert correlation_monitor._assess_correlation_risk(0.3) == "low"
    
    @pytest.mark.asyncio
    async def test_anti_correlation_detection(self, correlation_monitor):
        """Test detection of anti-correlation patterns."""
        # Test with anti-correlated data
        account1_positions = [1.0, 1.1, 1.2, 1.3]
        account2_positions = [1.3, 1.2, 1.1, 1.0]  # Inverse pattern
        
        correlation, p_value = correlation_monitor._calculate_pearson_correlation(
            account1_positions, account2_positions
        )
        
        # Should detect negative correlation
        assert correlation < -0.8
        assert p_value < 0.05