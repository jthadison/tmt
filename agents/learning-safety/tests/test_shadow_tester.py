"""
Unit tests for ShadowTester.

Tests shadow test creation, signal allocation, trade recording, evaluation with
t-tests, and termination with proper statistical significance calculations.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.shadow_tester import ShadowTester
from app.models.suggestion_models import ParameterSuggestion, TestEvaluation


@pytest.fixture
def mock_shadow_test_repository():
    """Create mock shadow test repository."""
    repository = Mock()
    repository.create_test = AsyncMock()
    repository.get_active_tests = AsyncMock(return_value=[])
    repository.get_test_by_id = AsyncMock()
    repository.update_test_metrics = AsyncMock()
    repository.complete_test = AsyncMock()
    repository.terminate_test = AsyncMock()
    repository.get_completed_tests = AsyncMock(return_value=[])
    return repository


@pytest.fixture
def mock_trade_repository():
    """Create mock trade repository."""
    repository = Mock()
    return repository


@pytest.fixture
def sample_suggestion():
    """Create sample parameter suggestion."""
    return ParameterSuggestion(
        session="TOKYO",
        parameter="confidence_threshold",
        current_value=Decimal("85"),
        suggested_value=Decimal("90"),
        reason="Win rate 35% below target 45%",
        expected_improvement=Decimal("0.22"),
        confidence_level=Decimal("0.8")
    )


@pytest.fixture
def shadow_tester(mock_shadow_test_repository, mock_trade_repository):
    """Create ShadowTester instance with mocks."""
    return ShadowTester(
        shadow_test_repository=mock_shadow_test_repository,
        trade_repository=mock_trade_repository,
        allocation_percentage=0.10,
        min_duration_days=7,
        min_sample_size=30,
        max_p_value=0.05,
        min_improvement_pct=20.0
    )


class TestShadowTester:
    """Test suite for ShadowTester."""

    @pytest.mark.asyncio
    async def test_start_test(self, shadow_tester, sample_suggestion, mock_shadow_test_repository):
        """Test starting a shadow test creates database record."""
        # Arrange
        mock_shadow_test_repository.create_test.return_value = Mock(test_id="test-123")

        # Act
        test_id = await shadow_tester.start_test(sample_suggestion)

        # Assert
        assert test_id is not None
        assert isinstance(test_id, str)

        # Verify create_test was called with correct data
        mock_shadow_test_repository.create_test.assert_called_once()
        call_args = mock_shadow_test_repository.create_test.call_args[0][0]

        assert call_args["suggestion_id"] == sample_suggestion.suggestion_id
        assert call_args["parameter_name"] == "confidence_threshold"
        assert call_args["session"] == "TOKYO"
        assert call_args["current_value"] == Decimal("85")
        assert call_args["test_value"] == Decimal("90")
        assert call_args["status"] == "ACTIVE"
        assert call_args["allocation_pct"] == Decimal("10.0")
        assert call_args["min_duration_days"] == 7

        # Verify suggestion status updated
        assert sample_suggestion.status == "TESTING"

    @pytest.mark.asyncio
    async def test_allocate_signal_to_group_10_percent(self, shadow_tester, mock_shadow_test_repository):
        """Test signal allocation is approximately 10% to TEST group."""
        # Arrange
        mock_test = Mock()
        mock_test.session = "TOKYO"
        mock_shadow_test_repository.get_active_tests.return_value = [mock_test]

        signal = {"session": "TOKYO", "symbol": "EUR_USD"}

        # Run 1000 allocations to test probability
        test_count = 0
        control_count = 0

        # Act
        for _ in range(1000):
            group = await shadow_tester.allocate_signal_to_group(signal)
            if group == "TEST":
                test_count += 1
            elif group == "CONTROL":
                control_count += 1

        # Assert
        # With 1000 samples and 10% allocation, expect ~100 TEST (within 2% tolerance: 80-120)
        assert 80 <= test_count <= 120, f"Expected 80-120 TEST allocations, got {test_count}"
        assert 880 <= control_count <= 920, f"Expected 880-920 CONTROL allocations, got {control_count}"
        assert test_count + control_count == 1000

    @pytest.mark.asyncio
    async def test_allocate_signal_no_active_tests(self, shadow_tester, mock_shadow_test_repository):
        """Test signal allocation returns CONTROL when no active tests."""
        # Arrange
        mock_shadow_test_repository.get_active_tests.return_value = []
        signal = {"session": "TOKYO"}

        # Act
        group = await shadow_tester.allocate_signal_to_group(signal)

        # Assert
        assert group == "CONTROL"

    @pytest.mark.asyncio
    async def test_record_trade_result_control(self, shadow_tester, mock_shadow_test_repository):
        """Test recording trade result for control group increments counter."""
        # Arrange
        mock_test = Mock()
        mock_test.control_trades = 10
        mock_test.test_trades = 2
        mock_shadow_test_repository.get_test_by_id.return_value = mock_test

        trade = {"pnl": Decimal("100"), "risk_reward_ratio": Decimal("3.0")}

        # Act
        await shadow_tester.record_trade_result("test-123", "CONTROL", trade)

        # Assert
        mock_shadow_test_repository.update_test_metrics.assert_called_once_with(
            "test-123",
            {"control_trades": 11}
        )

    @pytest.mark.asyncio
    async def test_record_trade_result_test(self, shadow_tester, mock_shadow_test_repository):
        """Test recording trade result for test group increments counter."""
        # Arrange
        mock_test = Mock()
        mock_test.control_trades = 10
        mock_test.test_trades = 2
        mock_shadow_test_repository.get_test_by_id.return_value = mock_test

        trade = {"pnl": Decimal("120"), "risk_reward_ratio": Decimal("3.5")}

        # Act
        await shadow_tester.record_trade_result("test-123", "TEST", trade)

        # Assert
        mock_shadow_test_repository.update_test_metrics.assert_called_once_with(
            "test-123",
            {"test_trades": 3}
        )

    @pytest.mark.asyncio
    async def test_evaluate_test_insufficient_duration(self, shadow_tester, mock_shadow_test_repository):
        """Test evaluation returns NO DEPLOY for insufficient duration."""
        # Arrange
        mock_test = Mock()
        mock_test.test_id = "test-123"
        mock_test.start_date = datetime.now() - timedelta(days=3)  # Only 3 days
        mock_test.min_duration_days = 7
        mock_test.control_trades = 50
        mock_test.test_trades = 50
        mock_shadow_test_repository.get_test_by_id.return_value = mock_test

        # Act
        evaluation = await shadow_tester.evaluate_test("test-123")

        # Assert
        assert evaluation.should_deploy is False
        assert "Insufficient duration" in evaluation.reason
        assert evaluation.sample_size_control == 50
        assert evaluation.sample_size_test == 50

    @pytest.mark.asyncio
    async def test_evaluate_test_insufficient_sample_size(self, shadow_tester, mock_shadow_test_repository):
        """Test evaluation returns NO DEPLOY for insufficient test trades (<30)."""
        # Arrange
        mock_test = Mock()
        mock_test.test_id = "test-123"
        mock_test.start_date = datetime.now() - timedelta(days=7)
        mock_test.min_duration_days = 7
        mock_test.control_trades = 90
        mock_test.test_trades = 25  # Below min_sample_size of 30
        mock_shadow_test_repository.get_test_by_id.return_value = mock_test

        # Act
        evaluation = await shadow_tester.evaluate_test("test-123")

        # Assert
        assert evaluation.should_deploy is False
        assert "Insufficient data" in evaluation.reason
        assert evaluation.sample_size_test == 25

    @pytest.mark.asyncio
    async def test_evaluate_test_20_percent_improvement(self, shadow_tester, mock_shadow_test_repository):
        """Test evaluation with 20% improvement and significant p-value returns DEPLOY."""
        # Arrange
        mock_test = Mock()
        mock_test.test_id = "test-123"
        mock_test.start_date = datetime.now() - timedelta(days=7)
        mock_test.min_duration_days = 7
        mock_test.control_trades = 90
        mock_test.test_trades = 35
        mock_test.control_win_rate = Decimal("50.0")
        mock_test.test_win_rate = Decimal("60.0")
        mock_shadow_test_repository.get_test_by_id.return_value = mock_test

        # Mock _get_trade_pnl_list to return known datasets
        # Control: mean = 100, Test: mean = 120 (20% improvement)
        control_pnl = [100.0, 110.0, 90.0, 95.0, 105.0] * 18  # 90 trades
        test_pnl = [120.0, 130.0, 115.0, 125.0, 110.0] * 7  # 35 trades

        with patch.object(shadow_tester, '_get_trade_pnl_list', new_callable=AsyncMock) as mock_get_pnl:
            mock_get_pnl.side_effect = [control_pnl, test_pnl]

            # Act
            evaluation = await shadow_tester.evaluate_test("test-123")

            # Assert
            assert evaluation.should_deploy is True
            assert abs(evaluation.improvement_pct - Decimal("20")) < Decimal("1")
            assert evaluation.p_value < Decimal("0.05")
            assert "Deploy recommended" in evaluation.reason

    @pytest.mark.asyncio
    async def test_evaluate_test_not_statistically_significant(self, shadow_tester, mock_shadow_test_repository):
        """Test evaluation with high p-value returns NO DEPLOY."""
        # Arrange
        mock_test = Mock()
        mock_test.test_id = "test-123"
        mock_test.start_date = datetime.now() - timedelta(days=7)
        mock_test.min_duration_days = 7
        mock_test.control_trades = 90
        mock_test.test_trades = 35
        mock_test.control_win_rate = Decimal("50.0")
        mock_test.test_win_rate = Decimal("52.0")
        mock_shadow_test_repository.get_test_by_id.return_value = mock_test

        # Mock with similar means (not significant difference)
        control_pnl = [100.0, 105.0, 95.0, 98.0, 102.0] * 18
        test_pnl = [101.0, 106.0, 96.0, 99.0, 103.0] * 7

        with patch.object(shadow_tester, '_get_trade_pnl_list', new_callable=AsyncMock) as mock_get_pnl:
            mock_get_pnl.side_effect = [control_pnl, test_pnl]

            # Act
            evaluation = await shadow_tester.evaluate_test("test-123")

            # Assert
            assert evaluation.should_deploy is False
            assert evaluation.p_value >= Decimal("0.05")
            assert "Not statistically significant" in evaluation.reason

    @pytest.mark.asyncio
    async def test_t_test_calculation(self, shadow_tester, mock_shadow_test_repository):
        """Test t-test calculation with known dataset."""
        # Arrange
        mock_test = Mock()
        mock_test.test_id = "test-123"
        mock_test.start_date = datetime.now() - timedelta(days=7)
        mock_test.min_duration_days = 7
        mock_test.control_trades = 90
        mock_test.test_trades = 35
        mock_test.control_win_rate = Decimal("50.0")
        mock_test.test_win_rate = Decimal("60.0")
        mock_shadow_test_repository.get_test_by_id.return_value = mock_test

        # Use known datasets with expected results
        # Control: mean = 100, std ≈ 7.9
        control_pnl = [100.0, 110.0, 90.0, 95.0, 105.0]
        # Test: mean = 120, std ≈ 8.2
        test_pnl = [120.0, 130.0, 115.0, 125.0, 110.0]

        with patch.object(shadow_tester, '_get_trade_pnl_list', new_callable=AsyncMock) as mock_get_pnl:
            mock_get_pnl.side_effect = [control_pnl, test_pnl]

            # Act
            evaluation = await shadow_tester.evaluate_test("test-123")

            # Assert
            # Expected improvement: (120 - 100) / 100 = 20%
            assert abs(evaluation.improvement_pct - Decimal("20")) < Decimal("0.1")

            # Expected p-value should be very small (highly significant)
            assert evaluation.p_value < Decimal("0.05")

            assert evaluation.control_mean_pnl == Decimal("100")
            assert evaluation.test_mean_pnl == Decimal("120")

    @pytest.mark.asyncio
    async def test_terminate_test(self, shadow_tester, mock_shadow_test_repository):
        """Test terminating shadow test calls repository with reason."""
        # Arrange
        mock_test = Mock()
        mock_test.status = "TERMINATED"
        mock_shadow_test_repository.terminate_test.return_value = mock_test

        # Act
        await shadow_tester.terminate_test("test-123", "Emergency stop")

        # Assert
        mock_shadow_test_repository.terminate_test.assert_called_once_with(
            "test-123",
            "Emergency stop"
        )

    @pytest.mark.asyncio
    async def test_get_completed_tests(self, shadow_tester, mock_shadow_test_repository):
        """Test retrieving completed tests from repository."""
        # Arrange
        mock_tests = [Mock(status="COMPLETED"), Mock(status="COMPLETED")]
        mock_shadow_test_repository.get_completed_tests.return_value = mock_tests

        # Act
        completed_tests = await shadow_tester.get_completed_tests()

        # Assert
        assert len(completed_tests) == 2
        mock_shadow_test_repository.get_completed_tests.assert_called_once()
