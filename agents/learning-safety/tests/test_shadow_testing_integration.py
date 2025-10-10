"""
Integration tests for shadow testing lifecycle.

Tests complete end-to-end workflow from performance analysis through
suggestion generation, shadow test execution, and evaluation.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.parameter_optimizer import ParameterSuggestionEngine
from app.shadow_tester import ShadowTester
from app.models.performance_models import (
    SessionMetrics,
    PerformanceAnalysis
)


class MockShadowTestRepository:
    """Mock shadow test repository for integration testing."""

    def __init__(self):
        self.tests = {}
        self.test_counter = 0

    async def create_test(self, test_data):
        """Create test in mock database."""
        test = MagicMock()
        test.test_id = test_data["test_id"]
        test.suggestion_id = test_data["suggestion_id"]
        test.parameter_name = test_data["parameter_name"]
        test.session = test_data.get("session")
        test.current_value = test_data.get("current_value")
        test.test_value = test_data.get("test_value")
        test.start_date = test_data["start_date"]
        test.min_duration_days = test_data.get("min_duration_days", 7)
        test.allocation_pct = test_data.get("allocation_pct", Decimal("10.0"))
        test.control_trades = 0
        test.test_trades = 0
        test.status = test_data.get("status", "ACTIVE")
        test.control_win_rate = None
        test.test_win_rate = None

        self.tests[test.test_id] = test
        return test

    async def get_active_tests(self):
        """Get active tests from mock database."""
        return [test for test in self.tests.values() if test.status == "ACTIVE"]

    async def get_test_by_id(self, test_id):
        """Get test by ID from mock database."""
        return self.tests.get(test_id)

    async def update_test_metrics(self, test_id, metrics):
        """Update test metrics in mock database."""
        if test_id not in self.tests:
            raise ValueError(f"Test not found: {test_id}")

        test = self.tests[test_id]
        for key, value in metrics.items():
            setattr(test, key, value)
        return test

    async def complete_test(self, test_id, evaluation):
        """Complete test in mock database."""
        if test_id not in self.tests:
            raise ValueError(f"Test not found: {test_id}")

        test = self.tests[test_id]
        test.status = "COMPLETED"
        test.end_date = datetime.now()
        test.improvement_pct = evaluation.get("improvement_pct")
        test.p_value = evaluation.get("p_value")
        return test

    async def terminate_test(self, test_id, reason):
        """Terminate test in mock database."""
        if test_id not in self.tests:
            raise ValueError(f"Test not found: {test_id}")

        test = self.tests[test_id]
        test.status = "TERMINATED"
        test.end_date = datetime.now()
        test.termination_reason = reason
        return test

    async def get_completed_tests(self):
        """Get completed tests from mock database."""
        return [test for test in self.tests.values() if test.status == "COMPLETED"]


@pytest.fixture
def mock_repositories():
    """Create mock repositories for integration testing."""
    shadow_test_repo = MockShadowTestRepository()
    trade_repo = Mock()
    return shadow_test_repo, trade_repo


@pytest.mark.asyncio
class TestShadowTestingIntegration:
    """Integration test suite for shadow testing lifecycle."""

    async def test_full_shadow_test_lifecycle(self, mock_repositories):
        """Test complete shadow testing workflow from analysis to evaluation."""
        # Arrange
        shadow_test_repo, trade_repo = mock_repositories

        # Step 1: Create performance analysis with low win rate session
        session_metrics = {
            "TOKYO": SessionMetrics(
                session="TOKYO",
                total_trades=50,
                winning_trades=15,
                losing_trades=35,
                win_rate=Decimal("30.0"),
                avg_rr=Decimal("2.5"),
                profit_factor=Decimal("1.0"),
                total_pnl=Decimal("100")
            )
        }

        analysis = PerformanceAnalysis(
            session_metrics=session_metrics,
            pattern_metrics={},
            confidence_metrics={},
            analysis_timestamp=datetime.now(),
            trade_count=50
        )

        # Step 2: Generate parameter suggestion
        suggestion_engine = ParameterSuggestionEngine(min_sample_size=20)
        suggestions = suggestion_engine.generate_suggestions(analysis, max_suggestions=1)

        assert len(suggestions) == 1
        suggestion = suggestions[0]
        assert suggestion.session == "TOKYO"
        assert suggestion.parameter == "confidence_threshold"

        # Step 3: Start shadow test
        shadow_tester = ShadowTester(
            shadow_test_repository=shadow_test_repo,
            trade_repository=trade_repo,
            allocation_percentage=0.10,
            min_duration_days=0,  # Override for testing
            min_sample_size=30
        )

        test_id = await shadow_tester.start_test(suggestion, duration_days=0)
        assert test_id is not None

        # Verify test created
        test = await shadow_test_repo.get_test_by_id(test_id)
        assert test is not None
        assert test.status == "ACTIVE"

        # Step 4: Simulate 7 days of signal allocation
        # For this test, we'll just verify the allocation logic works
        mock_test = await shadow_test_repo.get_test_by_id(test_id)
        mock_test.session = "TOKYO"

        # Simulate 100 signals
        test_allocations = 0
        control_allocations = 0

        for _ in range(100):
            signal = {"session": "TOKYO"}
            group = await shadow_tester.allocate_signal_to_group(signal)

            if group == "TEST":
                test_allocations += 1
            else:
                control_allocations += 1

        # Verify approximately 10% allocation (within tolerance: 2-18 for 100 signals)
        assert 2 <= test_allocations <= 18

        # Step 5: Simulate recording trade results
        # Update test with simulated trade counters
        await shadow_test_repo.update_test_metrics(
            test_id,
            {
                "control_trades": 90,
                "test_trades": 35,
                "control_win_rate": Decimal("50.0"),
                "test_win_rate": Decimal("60.0")
            }
        )

        # Step 6: Evaluate test after simulated period
        # Mock the start date to be in the past
        test.start_date = datetime.now() - timedelta(days=7)

        # Mock _get_trade_pnl_list to return test data
        control_pnl = [100.0, 110.0, 90.0, 95.0, 105.0] * 18  # 90 trades
        test_pnl = [120.0, 130.0, 115.0, 125.0, 110.0] * 7  # 35 trades

        from unittest.mock import patch
        with patch.object(shadow_tester, '_get_trade_pnl_list', new_callable=AsyncMock) as mock_get_pnl:
            mock_get_pnl.side_effect = [control_pnl, test_pnl]

            evaluation = await shadow_tester.evaluate_test(test_id)

            # Step 7: Verify evaluation results
            assert evaluation is not None
            assert evaluation.test_id == test_id

            # Should deploy due to 20% improvement and significant p-value
            assert evaluation.should_deploy is True
            assert abs(evaluation.improvement_pct - Decimal("20")) < Decimal("1")
            assert evaluation.p_value < Decimal("0.05")

            assert evaluation.sample_size_control == 90
            assert evaluation.sample_size_test == 35

    async def test_shadow_test_allocation_percentage(self, mock_repositories):
        """Test that exactly 10% of signals are allocated to test group over large sample."""
        # Arrange
        shadow_test_repo, trade_repo = mock_repositories

        shadow_tester = ShadowTester(
            shadow_test_repository=shadow_test_repo,
            trade_repository=trade_repo,
            allocation_percentage=0.10
        )

        # Create active test
        test_data = {
            "test_id": "test-123",
            "suggestion_id": "suggestion-123",
            "parameter_name": "confidence_threshold",
            "session": "TOKYO",
            "start_date": datetime.now(),
            "status": "ACTIVE"
        }
        await shadow_test_repo.create_test(test_data)

        # Act - Generate 1000 signals
        test_count = 0
        control_count = 0

        for _ in range(1000):
            signal = {"session": "TOKYO"}
            group = await shadow_tester.allocate_signal_to_group(signal)

            if group == "TEST":
                test_count += 1
            else:
                control_count += 1

        # Assert - Should be ~10% (within 8-12% tolerance)
        test_percentage = (test_count / 1000) * 100
        assert 8.0 <= test_percentage <= 12.0

    async def test_early_termination_scenario(self, mock_repositories):
        """Test early termination of shadow test."""
        # Arrange
        shadow_test_repo, trade_repo = mock_repositories

        shadow_tester = ShadowTester(
            shadow_test_repository=shadow_test_repo,
            trade_repository=trade_repo
        )

        # Create active test
        test_data = {
            "test_id": "test-456",
            "suggestion_id": "suggestion-456",
            "parameter_name": "min_risk_reward",
            "session": "LONDON",
            "start_date": datetime.now(),
            "status": "ACTIVE"
        }
        await shadow_test_repo.create_test(test_data)

        # Verify test is active
        active_tests = await shadow_test_repo.get_active_tests()
        assert len(active_tests) == 1

        # Act - Terminate test
        await shadow_tester.terminate_test("test-456", "Manual override - emergency stop")

        # Assert
        test = await shadow_test_repo.get_test_by_id("test-456")
        assert test.status == "TERMINATED"
        assert test.termination_reason == "Manual override - emergency stop"

        # Verify no longer active
        active_tests = await shadow_test_repo.get_active_tests()
        assert len(active_tests) == 0

    async def test_insufficient_data_evaluation(self, mock_repositories):
        """Test evaluation with insufficient sample size returns NO DEPLOY."""
        # Arrange
        shadow_test_repo, trade_repo = mock_repositories

        shadow_tester = ShadowTester(
            shadow_test_repository=shadow_test_repo,
            trade_repository=trade_repo,
            min_duration_days=0,
            min_sample_size=30
        )

        # Create test with insufficient data
        test_data = {
            "test_id": "test-789",
            "suggestion_id": "suggestion-789",
            "parameter_name": "confidence_threshold",
            "session": "NY",
            "start_date": datetime.now() - timedelta(days=7),
            "min_duration_days": 0,
            "status": "ACTIVE"
        }
        await shadow_test_repo.create_test(test_data)

        # Update with only 20 test trades (< 30 minimum)
        await shadow_test_repo.update_test_metrics(
            "test-789",
            {
                "control_trades": 90,
                "test_trades": 20,  # Below minimum
                "control_win_rate": Decimal("50.0"),
                "test_win_rate": Decimal("60.0")
            }
        )

        # Act
        evaluation = await shadow_tester.evaluate_test("test-789")

        # Assert
        assert evaluation.should_deploy is False
        assert "Insufficient data" in evaluation.reason
        assert evaluation.sample_size_test == 20
