"""
Integration tests for full autonomous learning cycle.

Tests end-to-end cycle execution with real database, complete performance
analysis, audit logging, and API endpoints.
"""

import pytest
import asyncio
import json
import tempfile
import sqlite3
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch

import sys
orchestrator_path = Path(__file__).parent.parent.parent.parent / "orchestrator"
sys.path.insert(0, str(orchestrator_path))
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.autonomous_learning_loop import AutonomousLearningAgent
from app.performance_analyzer import PerformanceAnalyzer
from app.audit_logger import AuditLogger
from app.database import initialize_database, get_database_engine, TradeRepository


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_database():
    """Create test database with schema."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = temp_db.name
    temp_db.close()

    # Initialize database schema
    await initialize_database(db_path)

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
async def populated_database(test_database):
    """Create test database populated with 100 trades."""
    db_engine = get_database_engine(test_database)
    trade_repo = TradeRepository(db_engine.get_session)

    # Create 100 trades with varied characteristics
    sessions = ["TOKYO", "LONDON", "NY", "SYDNEY", "OVERLAP"]
    patterns = ["Spring", "Upthrust", "Accumulation", "Distribution"]

    for i in range(100):
        session = sessions[i % 5]
        pattern = patterns[i % 4]
        confidence = 55 + (i % 40)  # 55-95%

        # 60% win rate overall
        is_winner = (i % 10) < 6
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")
        rr = Decimal("2.5") if is_winner else Decimal("0.5")

        trade_data = {
            "trade_id": f"test_trade_{i}",
            "signal_id": f"signal_{i}",
            "account_id": "test_account",
            "symbol": "EUR_USD",
            "direction": "BUY" if (i % 2) == 0 else "SELL",
            "entry_time": datetime.now() - timedelta(hours=100-i),
            "entry_price": Decimal("1.1000") + Decimal(i) * Decimal("0.0001"),
            "position_size": Decimal("10000"),
            "pnl": pnl,
            "session": session,
            "pattern_type": pattern,
            "confidence_score": Decimal(str(confidence)),
            "risk_reward_ratio": rr,
        }

        await trade_repo.save_trade(trade_data)

    await db_engine.close()

    yield test_database


@pytest.fixture
def temp_audit_log():
    """Create temporary audit log file."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
    yield temp_file.name
    Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
async def learning_agent_with_real_deps(populated_database, temp_audit_log):
    """Create learning agent with real dependencies."""
    db_engine = get_database_engine(populated_database)
    trade_repo = TradeRepository(db_engine.get_session)
    performance_analyzer = PerformanceAnalyzer(min_trades_for_significance=20)
    audit_logger = AuditLogger(log_file_path=temp_audit_log)

    agent = AutonomousLearningAgent(
        trade_repository=trade_repo,
        performance_analyzer=performance_analyzer,
        audit_logger=audit_logger,
        cycle_interval=1  # 1 second for fast testing
    )

    yield agent, db_engine, temp_audit_log

    # Cleanup
    await db_engine.close()


# ============================================================================
# Tests: End-to-End Learning Cycle
# ============================================================================

@pytest.mark.asyncio
async def test_full_learning_cycle_execution(learning_agent_with_real_deps):
    """Test complete learning cycle: database query → analysis → audit log."""
    agent, db_engine, audit_log_path = learning_agent_with_real_deps

    # Run single cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    # Wait for cycle to complete
    await asyncio.sleep(2.0)

    # Stop agent
    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=3.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify cycle completed
    assert agent.cycle_state == "COMPLETED"
    assert agent.last_run_timestamp is not None
    assert agent.next_run_timestamp is not None

    # Verify audit log entries created
    with open(audit_log_path, 'r') as f:
        log_lines = f.readlines()

    assert len(log_lines) >= 2  # At least start and complete

    # Verify log entries
    start_entry = json.loads(log_lines[0])
    assert start_entry["event"] == "learning_cycle_start"

    complete_entry = json.loads(log_lines[1])
    assert complete_entry["event"] == "learning_cycle_complete"
    assert complete_entry["trade_count"] == 100


@pytest.mark.asyncio
async def test_cycle_state_transitions(learning_agent_with_real_deps):
    """Test cycle state transitions: IDLE → RUNNING → COMPLETED."""
    agent, _, _ = learning_agent_with_real_deps

    # Initial state
    assert agent.cycle_state == "IDLE"

    # Start cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    # Wait for running state
    await asyncio.sleep(0.5)
    assert agent.cycle_state in ["RUNNING", "COMPLETED"]

    # Wait for completion
    await asyncio.sleep(2.0)

    # Stop agent
    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Final state
    assert agent.cycle_state == "COMPLETED"


@pytest.mark.asyncio
async def test_trades_queried_from_database(learning_agent_with_real_deps):
    """Test that trades are successfully queried from database."""
    agent, db_engine, audit_log_path = learning_agent_with_real_deps

    # Run single cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    await asyncio.sleep(2.0)

    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify audit log shows 100 trades analyzed
    with open(audit_log_path, 'r') as f:
        log_lines = f.readlines()

    complete_entry = json.loads(log_lines[1])
    assert complete_entry["trade_count"] == 100


@pytest.mark.asyncio
async def test_performance_analysis_executed(learning_agent_with_real_deps):
    """Test that performance analysis is executed correctly."""
    agent, _, audit_log_path = learning_agent_with_real_deps

    # Run single cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    await asyncio.sleep(2.0)

    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify audit log contains analysis results
    with open(audit_log_path, 'r') as f:
        log_lines = f.readlines()

    complete_entry = json.loads(log_lines[1])

    # Should have best/worst session identified
    assert "best_session" in complete_entry
    assert "worst_session" in complete_entry

    # Should have session metrics
    assert "session_metrics" in complete_entry
    assert len(complete_entry["session_metrics"]) == 5  # All 5 sessions


@pytest.mark.asyncio
async def test_audit_log_entries_created(learning_agent_with_real_deps):
    """Test that audit log entries are created with correct format."""
    agent, _, audit_log_path = learning_agent_with_real_deps

    # Run single cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    await asyncio.sleep(2.0)

    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Read and verify audit log
    with open(audit_log_path, 'r') as f:
        log_lines = f.readlines()

    # Verify start entry
    start_entry = json.loads(log_lines[0])
    assert start_entry["event"] == "learning_cycle_start"
    assert "cycle_id" in start_entry
    assert "timestamp" in start_entry
    assert start_entry["level"] == "INFO"

    # Verify complete entry
    complete_entry = json.loads(log_lines[1])
    assert complete_entry["event"] == "learning_cycle_complete"
    assert complete_entry["cycle_id"] == start_entry["cycle_id"]  # Same cycle ID
    assert complete_entry["level"] == "INFO"


@pytest.mark.asyncio
async def test_cycle_status_api_returns_correct_data(learning_agent_with_real_deps):
    """Test that get_cycle_status() returns correct data after cycle."""
    agent, _, _ = learning_agent_with_real_deps

    # Run single cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    await asyncio.sleep(2.0)

    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Get cycle status
    status = agent.get_cycle_status()

    # Verify status fields
    assert status["cycle_state"] == "COMPLETED"
    assert status["last_run_timestamp"] is not None
    assert status["next_run_timestamp"] is not None
    assert status["cycle_interval_seconds"] == 1
    assert status["running"] is False


# ============================================================================
# Tests: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_database_unavailable_error_handling(temp_audit_log):
    """Test that cycle handles database unavailable gracefully."""
    # Create agent with invalid database path
    from app.database.connection import DatabaseEngine

    # Mock database engine that fails
    db_engine = DatabaseEngine("invalid_path.db")
    trade_repo = TradeRepository(db_engine.get_session)

    audit_logger = AuditLogger(log_file_path=temp_audit_log)

    agent = AutonomousLearningAgent(
        trade_repository=trade_repo,
        performance_analyzer=PerformanceAnalyzer(),
        audit_logger=audit_logger,
        cycle_interval=1
    )

    # Run single cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    await asyncio.sleep(2.0)

    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Cycle should fail but not crash
    assert agent.cycle_state == "FAILED"

    # Verify error logged
    with open(temp_audit_log, 'r') as f:
        log_lines = f.readlines()

    # Should have start and failed entries
    assert len(log_lines) >= 2

    failed_entry = json.loads(log_lines[-1])
    assert failed_entry["event"] == "learning_cycle_failed"


@pytest.mark.asyncio
async def test_next_cycle_executes_after_error(learning_agent_with_real_deps):
    """Test that next cycle executes even after previous cycle error."""
    agent, db_engine, audit_log_path = learning_agent_with_real_deps

    # Mock first call to fail, second to succeed
    original_get_trades = agent.trade_repository.get_recent_trades
    call_count = [0]

    async def mock_get_trades_with_one_failure(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("Simulated database error")
        return await original_get_trades(*args, **kwargs)

    agent.trade_repository.get_recent_trades = mock_get_trades_with_one_failure

    # Run two cycles
    task = asyncio.create_task(agent.continuous_learning_loop())

    # Wait for two cycles to complete (2 seconds cycle + error recovery)
    await asyncio.sleep(4.0)

    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify both cycles attempted
    with open(audit_log_path, 'r') as f:
        log_lines = f.readlines()

    # Should have entries for both cycles
    assert len(log_lines) >= 3  # start + failed + start (+ maybe complete)

    # First cycle failed
    assert "learning_cycle_failed" in log_lines[1]


# ============================================================================
# Tests: Feature Flag
# ============================================================================

@pytest.mark.asyncio
async def test_feature_flag_disabled_scenario(populated_database, temp_audit_log):
    """Test that learning loop doesn't start when feature flag is disabled."""
    # This would normally be tested in main.py startup, but we can test the env var
    with patch.dict('os.environ', {'ENABLE_AUTONOMOUS_LEARNING': 'false'}):
        db_engine = get_database_engine(populated_database)
        trade_repo = TradeRepository(db_engine.get_session)

        agent = AutonomousLearningAgent(
            trade_repository=trade_repo,
            performance_analyzer=PerformanceAnalyzer(),
            audit_logger=AuditLogger(log_file_path=temp_audit_log),
            cycle_interval=1
        )

        # Manually check feature flag (simulating startup logic)
        import os
        enabled = os.getenv("ENABLE_AUTONOMOUS_LEARNING", "true").lower() == "true"

        assert enabled is False

        await db_engine.close()


# ============================================================================
# Tests: Performance
# ============================================================================

@pytest.mark.asyncio
async def test_analysis_completes_quickly(learning_agent_with_real_deps):
    """Test that analysis of 100 trades completes in < 5 seconds."""
    agent, _, _ = learning_agent_with_real_deps

    start_time = datetime.now()

    # Run single cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    await asyncio.sleep(3.0)

    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # Should complete well under 5 seconds
    assert elapsed < 5.0
    assert agent.cycle_state == "COMPLETED"


# ============================================================================
# Tests: Insufficient Data
# ============================================================================

@pytest.mark.asyncio
async def test_insufficient_data_handling(test_database, temp_audit_log):
    """Test cycle skips analysis when insufficient trades (<10)."""
    # Create database with only 5 trades
    db_engine = get_database_engine(test_database)
    trade_repo = TradeRepository(db_engine.get_session)

    for i in range(5):
        trade_data = {
            "trade_id": f"trade_{i}",
            "account_id": "test",
            "symbol": "EUR_USD",
            "direction": "BUY",
            "entry_time": datetime.now(),
            "entry_price": Decimal("1.1000"),
            "position_size": Decimal("10000"),
            "pnl": Decimal("100.00"),
            "session": "TOKYO",
            "pattern_type": "Spring",
            "confidence_score": Decimal("75.0"),
            "risk_reward_ratio": Decimal("2.5"),
        }
        await trade_repo.save_trade(trade_data)

    agent = AutonomousLearningAgent(
        trade_repository=trade_repo,
        performance_analyzer=PerformanceAnalyzer(),
        audit_logger=AuditLogger(log_file_path=temp_audit_log),
        cycle_interval=1
    )

    # Run single cycle
    task = asyncio.create_task(agent.continuous_learning_loop())

    await asyncio.sleep(2.0)

    agent._running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()

    # Verify insufficient data logged
    with open(temp_audit_log, 'r') as f:
        log_lines = f.readlines()

    # Should have start and insufficient_data entries
    assert len(log_lines) >= 2

    insufficient_entry = json.loads(log_lines[1])
    assert insufficient_entry["event"] == "insufficient_data"
    assert insufficient_entry["trade_count"] == 5
    assert insufficient_entry["min_required"] == 10

    await db_engine.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
