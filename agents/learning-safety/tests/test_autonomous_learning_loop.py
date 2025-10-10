"""
Unit tests for AutonomousLearningAgent class.

Tests learning cycle execution, state management, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.autonomous_learning_loop import AutonomousLearningAgent
from app.performance_analyzer import PerformanceAnalyzer
from app.audit_logger import AuditLogger
from app.models.performance_models import (
    PerformanceAnalysis,
    SessionMetrics,
    PatternMetrics,
    ConfidenceMetrics
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_trade_repository():
    """Create mock trade repository."""
    repo = Mock()
    repo.get_recent_trades = AsyncMock()
    return repo


@pytest.fixture
def mock_performance_analyzer():
    """Create mock performance analyzer."""
    analyzer = Mock(spec=PerformanceAnalyzer)

    # Create mock analysis result
    analysis = PerformanceAnalysis(
        session_metrics={
            "TOKYO": SessionMetrics(
                session="TOKYO",
                total_trades=20,
                winning_trades=12,
                losing_trades=8,
                win_rate=Decimal("60.0"),
                avg_rr=Decimal("2.5"),
                profit_factor=Decimal("1.8"),
                total_pnl=Decimal("500.00")
            )
        },
        pattern_metrics={
            "Spring": PatternMetrics(
                pattern_type="Spring",
                sample_size=25,
                winning_trades=15,
                losing_trades=10,
                win_rate=Decimal("60.0"),
                avg_rr=Decimal("2.5")
            )
        },
        confidence_metrics={
            "70-80%": ConfidenceMetrics(
                bucket="70-80%",
                sample_size=30,
                win_rate=Decimal("65.0"),
                avg_rr=Decimal("2.8")
            )
        },
        analysis_timestamp=datetime.now(),
        trade_count=100,
        best_session="TOKYO",
        worst_session="SYDNEY"
    )

    analyzer.analyze_performance = Mock(return_value=analysis)
    return analyzer


@pytest.fixture
def mock_audit_logger():
    """Create mock audit logger."""
    logger = Mock(spec=AuditLogger)
    logger.log_cycle_start = Mock()
    logger.log_cycle_complete = Mock()
    logger.log_cycle_failed = Mock()
    logger.log_insufficient_data = Mock()
    return logger


@pytest.fixture
def learning_agent(mock_trade_repository, mock_performance_analyzer, mock_audit_logger):
    """Create AutonomousLearningAgent instance with mocked dependencies."""
    agent = AutonomousLearningAgent(
        trade_repository=mock_trade_repository,
        performance_analyzer=mock_performance_analyzer,
        audit_logger=mock_audit_logger,
        cycle_interval=1  # 1 second for fast testing
    )
    return agent


@pytest.fixture
def mock_trades():
    """Create mock trades list."""
    trades = []
    for i in range(50):
        trade = Mock()
        trade.trade_id = f"trade_{i}"
        trade.session = "TOKYO"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("75.0")
        trade.pnl = Decimal("100.00") if (i % 2) == 0 else Decimal("-50.00")
        trade.risk_reward_ratio = Decimal("2.5")
        trade.entry_time = datetime.now()
        trades.append(trade)
    return trades


# ============================================================================
# Tests: Initialization
# ============================================================================

def test_initialization(learning_agent):
    """Test agent initialization with default values."""
    assert learning_agent.cycle_state == "IDLE"
    assert learning_agent.last_run_timestamp is None
    assert learning_agent.next_run_timestamp is None
    assert learning_agent.suggestions_generated_count == 0
    assert learning_agent.active_tests_count == 0
    assert learning_agent.cycle_interval == 1


def test_initialization_custom_interval():
    """Test initialization with custom cycle interval."""
    repo = Mock()
    agent = AutonomousLearningAgent(
        trade_repository=repo,
        cycle_interval=3600
    )
    assert agent.cycle_interval == 3600


def test_initialization_from_env_var():
    """Test initialization reads LEARNING_CYCLE_INTERVAL from environment."""
    with patch.dict('os.environ', {'LEARNING_CYCLE_INTERVAL': '7200'}):
        repo = Mock()
        agent = AutonomousLearningAgent(trade_repository=repo)
        assert agent.cycle_interval == 7200


# ============================================================================
# Tests: get_cycle_status
# ============================================================================

def test_get_cycle_status_initial(learning_agent):
    """Test get_cycle_status returns initial state."""
    status = learning_agent.get_cycle_status()

    assert status["cycle_state"] == "IDLE"
    assert status["last_run_timestamp"] is None
    assert status["next_run_timestamp"] is None
    assert status["suggestions_generated_count"] == 0
    assert status["active_tests_count"] == 0
    assert status["cycle_interval_seconds"] == 1
    assert status["running"] is False


def test_get_cycle_status_after_run(learning_agent):
    """Test get_cycle_status after setting timestamps."""
    learning_agent.last_run_timestamp = datetime(2025, 10, 10, 8, 0, 0)
    learning_agent.next_run_timestamp = datetime(2025, 10, 11, 8, 0, 0)
    learning_agent.cycle_state = "COMPLETED"

    status = learning_agent.get_cycle_status()

    assert status["cycle_state"] == "COMPLETED"
    assert status["last_run_timestamp"] == "2025-10-10T08:00:00"
    assert status["next_run_timestamp"] == "2025-10-11T08:00:00"


# ============================================================================
# Tests: continuous_learning_loop (single cycle)
# ============================================================================

@pytest.mark.asyncio
async def test_continuous_learning_loop_successful_cycle(
    learning_agent,
    mock_trade_repository,
    mock_audit_logger,
    mock_trades
):
    """Test successful learning cycle execution."""
    # Setup
    mock_trade_repository.get_recent_trades.return_value = mock_trades

    # Run single cycle with timeout
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    # Wait for first cycle to complete
    await asyncio.sleep(0.5)

    # Stop the loop
    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify cycle executed
    assert learning_agent.cycle_state in ["COMPLETED", "RUNNING"]
    assert learning_agent.last_run_timestamp is not None

    # Verify methods called
    mock_trade_repository.get_recent_trades.assert_called_once_with(limit=100)
    mock_audit_logger.log_cycle_start.assert_called_once()
    mock_audit_logger.log_cycle_complete.assert_called_once()


@pytest.mark.asyncio
async def test_continuous_learning_loop_insufficient_trades(
    learning_agent,
    mock_trade_repository,
    mock_audit_logger
):
    """Test cycle skips analysis when insufficient trades."""
    # Setup - return only 5 trades (below minimum of 10)
    mock_trade_repository.get_recent_trades.return_value = [Mock() for _ in range(5)]

    # Run single cycle
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    await asyncio.sleep(0.5)

    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify insufficient data logged
    mock_audit_logger.log_insufficient_data.assert_called_once()
    assert learning_agent.cycle_state == "COMPLETED"


@pytest.mark.asyncio
async def test_continuous_learning_loop_handles_database_error(
    learning_agent,
    mock_trade_repository,
    mock_audit_logger
):
    """Test cycle handles database errors gracefully."""
    # Setup - database error
    mock_trade_repository.get_recent_trades.side_effect = Exception("Database connection failed")

    # Run single cycle
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    await asyncio.sleep(0.5)

    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify error handled
    assert learning_agent.cycle_state == "FAILED"
    mock_audit_logger.log_cycle_failed.assert_called_once()


@pytest.mark.asyncio
async def test_continuous_learning_loop_handles_analysis_error(
    learning_agent,
    mock_trade_repository,
    mock_performance_analyzer,
    mock_audit_logger,
    mock_trades
):
    """Test cycle handles analysis errors gracefully."""
    # Setup
    mock_trade_repository.get_recent_trades.return_value = mock_trades
    mock_performance_analyzer.analyze_performance.side_effect = Exception("Analysis failed")

    # Run single cycle
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    await asyncio.sleep(0.5)

    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify error handled
    assert learning_agent.cycle_state == "FAILED"
    mock_audit_logger.log_cycle_failed.assert_called_once()


# ============================================================================
# Tests: start/stop
# ============================================================================

@pytest.mark.asyncio
async def test_start_creates_background_task(learning_agent):
    """Test start() creates background task."""
    await learning_agent.start()

    assert learning_agent._task is not None
    assert not learning_agent._task.done()
    assert learning_agent._running is True

    # Cleanup
    await learning_agent.stop()


@pytest.mark.asyncio
async def test_start_idempotent(learning_agent):
    """Test calling start() twice doesn't create duplicate tasks."""
    await learning_agent.start()
    task1 = learning_agent._task

    await learning_agent.start()
    task2 = learning_agent._task

    # Should be same task
    assert task1 is task2

    # Cleanup
    await learning_agent.stop()


@pytest.mark.asyncio
async def test_stop_cancels_task(learning_agent):
    """Test stop() cancels running task."""
    await learning_agent.start()

    assert learning_agent._running is True

    await learning_agent.stop()

    assert learning_agent._running is False
    assert learning_agent._task.cancelled() or learning_agent._task.done()


@pytest.mark.asyncio
async def test_stop_when_not_running(learning_agent):
    """Test stop() when agent not running."""
    # Should not raise error
    await learning_agent.stop()

    assert learning_agent._task is None


# ============================================================================
# Tests: State transitions
# ============================================================================

@pytest.mark.asyncio
async def test_cycle_state_transitions(
    learning_agent,
    mock_trade_repository,
    mock_trades
):
    """Test cycle state transitions: IDLE -> RUNNING -> COMPLETED."""
    mock_trade_repository.get_recent_trades.return_value = mock_trades

    assert learning_agent.cycle_state == "IDLE"

    # Start cycle
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    # Wait for cycle to start
    await asyncio.sleep(0.1)
    assert learning_agent.cycle_state in ["RUNNING", "COMPLETED"]

    # Wait for cycle to complete
    await asyncio.sleep(0.5)

    # Stop
    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    assert learning_agent.cycle_state == "COMPLETED"


@pytest.mark.asyncio
async def test_cycle_state_failed_on_error(
    learning_agent,
    mock_trade_repository
):
    """Test cycle state transitions to FAILED on error."""
    mock_trade_repository.get_recent_trades.side_effect = Exception("Test error")

    # Start cycle
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    await asyncio.sleep(0.5)

    # Stop
    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    assert learning_agent.cycle_state == "FAILED"


# ============================================================================
# Tests: Cycle timing
# ============================================================================

@pytest.mark.asyncio
async def test_timestamps_updated_on_cycle(
    learning_agent,
    mock_trade_repository,
    mock_trades
):
    """Test timestamps are updated on each cycle."""
    mock_trade_repository.get_recent_trades.return_value = mock_trades

    assert learning_agent.last_run_timestamp is None
    assert learning_agent.next_run_timestamp is None

    # Start cycle
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    await asyncio.sleep(0.5)

    # Stop
    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Timestamps should be set
    assert learning_agent.last_run_timestamp is not None
    assert learning_agent.next_run_timestamp is not None

    # Next run should be ~1 second after last run (cycle_interval=1)
    time_diff = (learning_agent.next_run_timestamp - learning_agent.last_run_timestamp).total_seconds()
    assert 0.8 <= time_diff <= 1.2  # Allow slight variance


@pytest.mark.asyncio
async def test_sleep_until_next_cycle(learning_agent):
    """Test _sleep_until_next_cycle waits for configured interval."""
    learning_agent._running = True  # Need to set running flag
    learning_agent.next_run_timestamp = datetime.now() + timedelta(seconds=0.5)

    start_time = datetime.now()
    await learning_agent._sleep_until_next_cycle()
    end_time = datetime.now()

    elapsed = (end_time - start_time).total_seconds()
    assert 0.4 <= elapsed <= 0.7  # Should wait ~0.5 seconds (allow a bit more variance)


# ============================================================================
# Tests: Audit logging integration
# ============================================================================

@pytest.mark.asyncio
async def test_audit_logging_on_successful_cycle(
    learning_agent,
    mock_trade_repository,
    mock_audit_logger,
    mock_trades
):
    """Test audit logger called correctly on successful cycle."""
    mock_trade_repository.get_recent_trades.return_value = mock_trades

    # Run single cycle
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    await asyncio.sleep(0.5)

    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify audit log calls
    mock_audit_logger.log_cycle_start.assert_called_once()
    mock_audit_logger.log_cycle_complete.assert_called_once()

    # Verify cycle_id passed correctly
    start_call_args = mock_audit_logger.log_cycle_start.call_args
    complete_call_args = mock_audit_logger.log_cycle_complete.call_args

    # Cycle IDs should match
    start_cycle_id = start_call_args[0][1]  # Second argument
    complete_cycle_id = complete_call_args[0][0]  # First argument
    assert start_cycle_id == complete_cycle_id


@pytest.mark.asyncio
async def test_audit_logging_on_failed_cycle(
    learning_agent,
    mock_trade_repository,
    mock_audit_logger
):
    """Test audit logger called correctly on failed cycle."""
    mock_trade_repository.get_recent_trades.side_effect = Exception("Test error")

    # Run single cycle
    task = asyncio.create_task(learning_agent.continuous_learning_loop())

    await asyncio.sleep(0.5)

    learning_agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify audit log calls
    mock_audit_logger.log_cycle_start.assert_called_once()
    mock_audit_logger.log_cycle_failed.assert_called_once()

    # Verify error passed to log_cycle_failed
    failed_call_args = mock_audit_logger.log_cycle_failed.call_args
    error_arg = failed_call_args[0][1]  # Second argument
    assert isinstance(error_arg, Exception)
    assert str(error_arg) == "Test error"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
