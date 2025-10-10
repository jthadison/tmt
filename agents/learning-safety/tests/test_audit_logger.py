"""
Unit tests for AuditLogger class.

Tests structured logging, file rotation, and event tracking.
"""

import pytest
import json
import tempfile
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

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
def temp_log_file():
    """Create temporary log file for testing."""
    import time
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
    yield temp_file.name
    # Cleanup - add small delay for Windows file locks
    time.sleep(0.1)
    try:
        Path(temp_file.name).unlink()
    except PermissionError:
        # Windows file lock - try once more
        time.sleep(0.2)
        try:
            Path(temp_file.name).unlink()
        except:
            pass  # Ignore cleanup errors in tests


@pytest.fixture
def audit_logger(temp_log_file):
    """Create AuditLogger instance with temporary file."""
    logger = AuditLogger(log_file_path=temp_log_file)
    yield logger
    # Cleanup: close all handlers to release file locks on Windows
    for handler in logger.logger.handlers[:]:
        handler.close()
        logger.logger.removeHandler(handler)


@pytest.fixture
def sample_performance_analysis():
    """Create sample PerformanceAnalysis for testing."""
    return PerformanceAnalysis(
        session_metrics={
            "TOKYO": SessionMetrics(
                session="TOKYO",
                total_trades=50,
                winning_trades=30,
                losing_trades=20,
                win_rate=Decimal("60.0"),
                avg_rr=Decimal("2.5"),
                profit_factor=Decimal("1.8"),
                total_pnl=Decimal("1500.00")
            ),
            "LONDON": SessionMetrics(
                session="LONDON",
                total_trades=50,
                winning_trades=35,
                losing_trades=15,
                win_rate=Decimal("70.0"),
                avg_rr=Decimal("3.0"),
                profit_factor=Decimal("2.2"),
                total_pnl=Decimal("2000.00")
            )
        },
        pattern_metrics={
            "Spring": PatternMetrics(
                pattern_type="Spring",
                sample_size=50,
                winning_trades=32,
                losing_trades=18,
                win_rate=Decimal("64.0"),
                avg_rr=Decimal("2.7")
            )
        },
        confidence_metrics={
            "70-80%": ConfidenceMetrics(
                bucket="70-80%",
                sample_size=60,
                win_rate=Decimal("65.0"),
                avg_rr=Decimal("2.8")
            )
        },
        analysis_timestamp=datetime(2025, 10, 10, 8, 30, 0),
        trade_count=100,
        best_session="LONDON",
        worst_session="SYDNEY"
    )


# ============================================================================
# Tests: Initialization
# ============================================================================

def test_initialization_creates_logger(temp_log_file):
    """Test AuditLogger initialization creates logger instance."""
    logger = AuditLogger(log_file_path=temp_log_file)
    assert logger.logger is not None
    assert logger.logger.name == "audit_trail"


def test_initialization_creates_log_file(temp_log_file):
    """Test log file is created on initialization."""
    AuditLogger(log_file_path=temp_log_file)
    assert Path(temp_log_file).exists()


def test_initialization_creates_directory(tmp_path):
    """Test logger creates directory structure if it doesn't exist."""
    log_path = tmp_path / "nested" / "dir" / "audit.log"
    AuditLogger(log_file_path=str(log_path))
    assert log_path.parent.exists()


# ============================================================================
# Tests: log_cycle_start
# ============================================================================

def test_log_cycle_start(audit_logger, temp_log_file):
    """Test log_cycle_start creates correct log entry."""
    timestamp = datetime(2025, 10, 10, 8, 0, 0)
    cycle_id = "test-cycle-123"

    audit_logger.log_cycle_start(timestamp, cycle_id)

    # Read log file
    with open(temp_log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event"] == "learning_cycle_start"
    assert log_entry["cycle_id"] == "test-cycle-123"
    assert log_entry["timestamp"] == "2025-10-10T08:00:00"
    assert log_entry["level"] == "INFO"


# ============================================================================
# Tests: log_cycle_complete
# ============================================================================

def test_log_cycle_complete(audit_logger, temp_log_file, sample_performance_analysis):
    """Test log_cycle_complete creates correct log entry."""
    cycle_id = "test-cycle-456"

    audit_logger.log_cycle_complete(cycle_id, sample_performance_analysis)

    # Read log file
    with open(temp_log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event"] == "learning_cycle_complete"
    assert log_entry["cycle_id"] == "test-cycle-456"
    assert log_entry["level"] == "INFO"
    assert log_entry["trade_count"] == 100
    assert log_entry["best_session"] == "LONDON"
    assert log_entry["worst_session"] == "SYDNEY"
    assert log_entry["suggestions_count"] == 0


def test_log_cycle_complete_includes_session_metrics(
    audit_logger,
    temp_log_file,
    sample_performance_analysis
):
    """Test log_cycle_complete includes session metrics in log."""
    cycle_id = "test-cycle-789"

    audit_logger.log_cycle_complete(cycle_id, sample_performance_analysis)

    # Read log file
    with open(temp_log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert "session_metrics" in log_entry
    assert "TOKYO" in log_entry["session_metrics"]
    assert "LONDON" in log_entry["session_metrics"]

    tokyo_metrics = log_entry["session_metrics"]["TOKYO"]
    assert tokyo_metrics["total_trades"] == 50
    assert tokyo_metrics["win_rate"] == 60.0
    assert tokyo_metrics["avg_rr"] == 2.5
    assert tokyo_metrics["profit_factor"] == 1.8
    assert tokyo_metrics["total_pnl"] == 1500.0


# ============================================================================
# Tests: log_cycle_failed
# ============================================================================

def test_log_cycle_failed(audit_logger, temp_log_file):
    """Test log_cycle_failed creates correct log entry."""
    cycle_id = "test-cycle-error"
    error = Exception("Database connection failed")

    audit_logger.log_cycle_failed(cycle_id, error)

    # Read log file
    with open(temp_log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event"] == "learning_cycle_failed"
    assert log_entry["cycle_id"] == "test-cycle-error"
    assert log_entry["level"] == "ERROR"
    assert log_entry["error_message"] == "Database connection failed"
    assert log_entry["error_type"] == "Exception"


def test_log_cycle_failed_with_custom_exception(audit_logger, temp_log_file):
    """Test log_cycle_failed handles custom exception types."""
    cycle_id = "test-cycle-custom-error"
    error = ValueError("Invalid parameter value")

    audit_logger.log_cycle_failed(cycle_id, error)

    # Read log file
    with open(temp_log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert log_entry["error_message"] == "Invalid parameter value"
    assert log_entry["error_type"] == "ValueError"


# ============================================================================
# Tests: log_database_unavailable
# ============================================================================

def test_log_database_unavailable(audit_logger, temp_log_file):
    """Test log_database_unavailable creates correct log entry."""
    cycle_id = "test-cycle-db-unavail"
    error = ConnectionError("Could not connect to database")

    audit_logger.log_database_unavailable(cycle_id, error)

    # Read log file
    with open(temp_log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event"] == "database_unavailable"
    assert log_entry["cycle_id"] == "test-cycle-db-unavail"
    assert log_entry["level"] == "WARNING"
    assert log_entry["error_message"] == "Could not connect to database"
    assert log_entry["action"] == "cycle_skipped"


# ============================================================================
# Tests: log_insufficient_data
# ============================================================================

def test_log_insufficient_data(audit_logger, temp_log_file):
    """Test log_insufficient_data creates correct log entry."""
    cycle_id = "test-cycle-no-data"
    trade_count = 5
    min_required = 10

    audit_logger.log_insufficient_data(cycle_id, trade_count, min_required)

    # Read log file
    with open(temp_log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event"] == "insufficient_data"
    assert log_entry["cycle_id"] == "test-cycle-no-data"
    assert log_entry["level"] == "INFO"
    assert log_entry["trade_count"] == 5
    assert log_entry["min_required"] == 10
    assert log_entry["action"] == "analysis_skipped"


# ============================================================================
# Tests: Multiple log entries
# ============================================================================

def test_multiple_log_entries(audit_logger, temp_log_file):
    """Test multiple log entries are written correctly."""
    # Log cycle start
    audit_logger.log_cycle_start(datetime(2025, 10, 10, 8, 0, 0), "cycle-1")

    # Log insufficient data
    audit_logger.log_insufficient_data("cycle-1", 5, 10)

    # Log cycle start again
    audit_logger.log_cycle_start(datetime(2025, 10, 10, 9, 0, 0), "cycle-2")

    # Read all log entries
    with open(temp_log_file, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 3

    # Verify first entry
    entry1 = json.loads(lines[0])
    assert entry1["event"] == "learning_cycle_start"
    assert entry1["cycle_id"] == "cycle-1"

    # Verify second entry
    entry2 = json.loads(lines[1])
    assert entry2["event"] == "insufficient_data"
    assert entry2["cycle_id"] == "cycle-1"

    # Verify third entry
    entry3 = json.loads(lines[2])
    assert entry3["event"] == "learning_cycle_start"
    assert entry3["cycle_id"] == "cycle-2"


# ============================================================================
# Tests: JSON format validation
# ============================================================================

def test_log_entries_are_valid_json(audit_logger, temp_log_file, sample_performance_analysis):
    """Test all log entries are valid JSON."""
    # Create various log entries
    audit_logger.log_cycle_start(datetime.now(), "cycle-1")
    audit_logger.log_cycle_complete("cycle-1", sample_performance_analysis)
    audit_logger.log_cycle_failed("cycle-2", Exception("Test error"))
    audit_logger.log_database_unavailable("cycle-3", ConnectionError("DB error"))
    audit_logger.log_insufficient_data("cycle-4", 5, 10)

    # Verify all entries are valid JSON
    with open(temp_log_file, 'r') as f:
        for line in f:
            # Should not raise JSONDecodeError
            entry = json.loads(line)
            assert isinstance(entry, dict)
            assert "event" in entry
            assert "timestamp" in entry or "level" in entry


# ============================================================================
# Tests: Timestamp format
# ============================================================================

def test_timestamp_format_iso8601(audit_logger, temp_log_file):
    """Test timestamps are in ISO 8601 format."""
    timestamp = datetime(2025, 10, 10, 8, 30, 45)
    audit_logger.log_cycle_start(timestamp, "cycle-1")

    with open(temp_log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    # Verify ISO 8601 format
    assert log_entry["timestamp"] == "2025-10-10T08:30:45"

    # Verify timestamp can be parsed back
    parsed_timestamp = datetime.fromisoformat(log_entry["timestamp"])
    assert parsed_timestamp == timestamp


# ============================================================================
# Tests: Thread safety (basic check)
# ============================================================================

def test_concurrent_logging(audit_logger, temp_log_file):
    """Test logger handles concurrent writes (basic check)."""
    import concurrent.futures

    def write_log(i):
        audit_logger.log_cycle_start(datetime.now(), f"cycle-{i}")

    # Write 10 log entries concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(write_log, i) for i in range(10)]
        concurrent.futures.wait(futures)

    # Verify all entries written
    with open(temp_log_file, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 10

    # Verify all are valid JSON
    for line in lines:
        entry = json.loads(line)
        assert entry["event"] == "learning_cycle_start"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
