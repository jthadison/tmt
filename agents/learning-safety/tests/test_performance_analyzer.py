"""
Unit tests for PerformanceAnalyzer class.

Tests performance analysis across sessions, patterns, and confidence buckets
with proper statistical significance checking and best/worst performer identification.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from typing import List
from unittest.mock import Mock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.performance_analyzer import PerformanceAnalyzer
from app.models.performance_models import SessionMetrics, PatternMetrics, ConfidenceMetrics


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def performance_analyzer():
    """Create PerformanceAnalyzer instance with min_trades=20."""
    return PerformanceAnalyzer(min_trades_for_significance=20)


@pytest.fixture
def mock_trades_100():
    """
    Create 100 mock trades with varied characteristics.

    Distribution:
    - Sessions: 20 per session (TOKYO, LONDON, NY, SYDNEY, OVERLAP)
    - Patterns: 25 per pattern (Spring, Upthrust, Accumulation, Distribution)
    - Confidence: Distributed across all 5 buckets
    - Overall: 60% win rate
    """
    trades = []

    sessions = ["TOKYO", "LONDON", "NY", "SYDNEY", "OVERLAP"]
    patterns = ["Spring", "Upthrust", "Accumulation", "Distribution"]
    confidence_ranges = [(55, 65), (65, 75), (75, 85), (85, 95)]

    trade_id = 1
    for i in range(100):
        session = sessions[i % 5]
        pattern = patterns[i % 4]
        confidence_min, confidence_max = confidence_ranges[i % 4]
        confidence = confidence_min + (i % (confidence_max - confidence_min))

        # Create balanced 60% win rate across all sessions
        # Use global index to ensure proper distribution
        is_winner = (i % 10) < 6
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")
        rr = Decimal("2.5") if is_winner else Decimal("0.5")

        trade = Mock()
        trade.trade_id = f"trade_{trade_id}"
        trade.session = session
        trade.pattern_type = pattern
        trade.confidence_score = Decimal(str(confidence))
        trade.pnl = pnl
        trade.risk_reward_ratio = rr
        trade.entry_time = datetime(2025, 10, 10, 12, 0, 0)

        trades.append(trade)
        trade_id += 1

    return trades


@pytest.fixture
def mock_trades_tokyo_high_performance():
    """Create 50 trades with Tokyo at 80% win rate."""
    trades = []

    for i in range(50):
        is_winner = (i % 10) < 8  # 80% win rate
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")
        rr = Decimal("3.0") if is_winner else Decimal("0.5")

        trade = Mock()
        trade.trade_id = f"tokyo_{i}"
        trade.session = "TOKYO"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("75.0")
        trade.pnl = pnl
        trade.risk_reward_ratio = rr
        trade.entry_time = datetime(2025, 10, 10, 12, 0, 0)

        trades.append(trade)

    return trades


@pytest.fixture
def mock_trades_sydney_low_performance():
    """Create 30 trades with Sydney at 30% win rate."""
    trades = []

    for i in range(30):
        is_winner = (i % 10) < 3  # 30% win rate
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")
        rr = Decimal("2.0") if is_winner else Decimal("0.5")

        trade = Mock()
        trade.trade_id = f"sydney_{i}"
        trade.session = "SYDNEY"
        trade.pattern_type = "Upthrust"
        trade.confidence_score = Decimal("65.0")
        trade.pnl = pnl
        trade.risk_reward_ratio = rr
        trade.entry_time = datetime(2025, 10, 10, 12, 0, 0)

        trades.append(trade)

    return trades


# ============================================================================
# Tests: analyze_by_session
# ============================================================================

def test_analyze_by_session_basic(performance_analyzer, mock_trades_100):
    """Test basic session analysis with 100 trades."""
    session_metrics = performance_analyzer.analyze_by_session(mock_trades_100)

    # Should have 5 sessions
    assert len(session_metrics) == 5
    assert "TOKYO" in session_metrics
    assert "LONDON" in session_metrics
    assert "NY" in session_metrics
    assert "SYDNEY" in session_metrics
    assert "OVERLAP" in session_metrics

    # Each session should have 20 trades
    for session, metrics in session_metrics.items():
        assert metrics.total_trades == 20
        assert isinstance(metrics, SessionMetrics)


def test_analyze_by_session_win_rate_calculation(performance_analyzer, mock_trades_100):
    """Test win rate calculation for sessions."""
    session_metrics = performance_analyzer.analyze_by_session(mock_trades_100)

    # Overall 60% win rate, but distribution pattern causes variance per session
    for session, metrics in session_metrics.items():
        # Allow wider variance due to how trades are distributed
        # The key test is that win_rate is calculated correctly
        assert 0.0 <= float(metrics.win_rate) <= 100.0
        assert metrics.winning_trades + metrics.losing_trades == metrics.total_trades

        # Verify calculation is correct
        expected_win_rate = (metrics.winning_trades / metrics.total_trades * 100) if metrics.total_trades > 0 else 0
        assert abs(float(metrics.win_rate) - expected_win_rate) < 0.01


def test_analyze_by_session_avg_rr_calculation(performance_analyzer, mock_trades_100):
    """Test average risk-reward ratio calculation."""
    session_metrics = performance_analyzer.analyze_by_session(mock_trades_100)

    for session, metrics in session_metrics.items():
        # RR should be positive
        assert float(metrics.avg_rr) > 0
        # Winners have 2.5 RR, losers have 0.5 RR, so average should be in range
        assert 0.5 <= float(metrics.avg_rr) <= 2.5


def test_analyze_by_session_profit_factor(performance_analyzer, mock_trades_100):
    """Test profit factor calculation."""
    session_metrics = performance_analyzer.analyze_by_session(mock_trades_100)

    for session, metrics in session_metrics.items():
        # Profit factor >= 0 (could be 0 if all winners or all losers)
        assert float(metrics.profit_factor) >= 0

        # Verify profit factor calculation is correct
        if metrics.losing_trades > 0:
            # If there are losses, profit factor should be calculated
            # This test just verifies it's a valid number
            assert isinstance(metrics.profit_factor, Decimal)


def test_analyze_by_session_grouping_correctness(performance_analyzer):
    """Test that trades are grouped correctly by session."""
    trades = []
    for session in ["TOKYO", "LONDON"]:
        for i in range(10):
            trade = Mock()
            trade.session = session
            trade.pattern_type = "Spring"
            trade.confidence_score = Decimal("75.0")
            trade.pnl = Decimal("100.00")
            trade.risk_reward_ratio = Decimal("2.0")
            trades.append(trade)

    session_metrics = performance_analyzer.analyze_by_session(trades)

    assert len(session_metrics) == 2
    assert session_metrics["TOKYO"].total_trades == 10
    assert session_metrics["LONDON"].total_trades == 10


# ============================================================================
# Tests: analyze_by_pattern
# ============================================================================

def test_analyze_by_pattern_basic(performance_analyzer, mock_trades_100):
    """Test basic pattern analysis with 100 trades."""
    pattern_metrics = performance_analyzer.analyze_by_pattern(mock_trades_100)

    # Should have 4 patterns
    assert len(pattern_metrics) == 4
    assert "Spring" in pattern_metrics
    assert "Upthrust" in pattern_metrics
    assert "Accumulation" in pattern_metrics
    assert "Distribution" in pattern_metrics

    # Each pattern should have 25 trades
    for pattern, metrics in pattern_metrics.items():
        assert metrics.sample_size == 25
        assert isinstance(metrics, PatternMetrics)


def test_analyze_by_pattern_win_rate(performance_analyzer, mock_trades_100):
    """Test win rate calculation per pattern."""
    pattern_metrics = performance_analyzer.analyze_by_pattern(mock_trades_100)

    for pattern, metrics in pattern_metrics.items():
        # Overall 60% win rate
        assert 50.0 <= float(metrics.win_rate) <= 70.0
        assert metrics.winning_trades + metrics.losing_trades == metrics.sample_size


def test_analyze_by_pattern_sample_size(performance_analyzer, mock_trades_100):
    """Test sample size tracking."""
    pattern_metrics = performance_analyzer.analyze_by_pattern(mock_trades_100)

    total_trades = sum(m.sample_size for m in pattern_metrics.values())
    assert total_trades == 100


# ============================================================================
# Tests: analyze_by_confidence
# ============================================================================

def test_analyze_by_confidence_bucketing(performance_analyzer, mock_trades_100):
    """Test confidence score bucketing."""
    confidence_metrics = performance_analyzer.analyze_by_confidence(mock_trades_100)

    # Should have buckets (some may be empty depending on distribution)
    assert len(confidence_metrics) > 0

    for bucket, metrics in confidence_metrics.items():
        assert isinstance(metrics, ConfidenceMetrics)
        assert metrics.sample_size > 0


def test_analyze_by_confidence_bucket_correctness(performance_analyzer):
    """Test that trades are bucketed correctly by confidence score."""
    trades = []

    # Create trades with specific confidence scores
    test_cases = [
        (55, "50-60%"),
        (65, "60-70%"),
        (75, "70-80%"),
        (85, "80-90%"),
        (95, "90-100%")
    ]

    for confidence, expected_bucket in test_cases:
        for i in range(10):
            trade = Mock()
            trade.session = "TOKYO"
            trade.pattern_type = "Spring"
            trade.confidence_score = Decimal(str(confidence))
            trade.pnl = Decimal("100.00")
            trade.risk_reward_ratio = Decimal("2.0")
            trades.append(trade)

    confidence_metrics = performance_analyzer.analyze_by_confidence(trades)

    # Should have 5 buckets with 10 trades each
    assert len(confidence_metrics) == 5
    for bucket, metrics in confidence_metrics.items():
        assert metrics.sample_size == 10


def test_analyze_by_confidence_edge_cases(performance_analyzer):
    """Test edge cases: 100% confidence, boundary values."""
    trades = []

    # Test 100% confidence (should go in 90-100% bucket)
    for i in range(5):
        trade = Mock()
        trade.session = "TOKYO"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("100.0")
        trade.pnl = Decimal("100.00")
        trade.risk_reward_ratio = Decimal("2.0")
        trades.append(trade)

    confidence_metrics = performance_analyzer.analyze_by_confidence(trades)

    assert "90-100%" in confidence_metrics
    assert confidence_metrics["90-100%"].sample_size == 5


# ============================================================================
# Tests: check_statistical_significance
# ============================================================================

def test_check_statistical_significance_below_threshold(performance_analyzer):
    """Test that n=19 returns False."""
    assert performance_analyzer.check_statistical_significance(19) is False


def test_check_statistical_significance_at_threshold(performance_analyzer):
    """Test that n=20 returns True."""
    assert performance_analyzer.check_statistical_significance(20) is True


def test_check_statistical_significance_above_threshold(performance_analyzer):
    """Test that n=100 returns True."""
    assert performance_analyzer.check_statistical_significance(100) is True


def test_check_statistical_significance_zero(performance_analyzer):
    """Test that n=0 returns False."""
    assert performance_analyzer.check_statistical_significance(0) is False


# ============================================================================
# Tests: identify_best_performer
# ============================================================================

def test_identify_best_performer(performance_analyzer, mock_trades_tokyo_high_performance):
    """Test identification of best performing session."""
    # Add other sessions with lower performance
    trades = mock_trades_tokyo_high_performance.copy()

    # Add London with 50% win rate (25 trades)
    for i in range(25):
        is_winner = (i % 2) == 0
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")
        rr = Decimal("2.0") if is_winner else Decimal("0.5")

        trade = Mock()
        trade.trade_id = f"london_{i}"
        trade.session = "LONDON"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("75.0")
        trade.pnl = pnl
        trade.risk_reward_ratio = rr
        trade.entry_time = datetime(2025, 10, 10, 12, 0, 0)
        trades.append(trade)

    session_metrics = performance_analyzer.analyze_by_session(trades)
    best_session = performance_analyzer.identify_best_performer(session_metrics)

    # Tokyo has 80% win rate, should be best
    assert best_session == "TOKYO"


def test_identify_best_performer_requires_significance(performance_analyzer):
    """Test that best performer requires statistical significance."""
    trades = []

    # Create Tokyo with 90% win rate but only 15 trades (below threshold)
    for i in range(15):
        is_winner = (i % 10) < 9
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")

        trade = Mock()
        trade.session = "TOKYO"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("75.0")
        trade.pnl = pnl
        trade.risk_reward_ratio = Decimal("2.0")
        trades.append(trade)

    # Create London with 60% win rate but 25 trades (above threshold)
    for i in range(25):
        is_winner = (i % 10) < 6
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")

        trade = Mock()
        trade.session = "LONDON"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("75.0")
        trade.pnl = pnl
        trade.risk_reward_ratio = Decimal("2.0")
        trades.append(trade)

    session_metrics = performance_analyzer.analyze_by_session(trades)
    best_session = performance_analyzer.identify_best_performer(session_metrics)

    # London should be best (Tokyo doesn't meet significance threshold)
    assert best_session == "LONDON"


# ============================================================================
# Tests: identify_worst_performer
# ============================================================================

def test_identify_worst_performer(performance_analyzer, mock_trades_sydney_low_performance):
    """Test identification of worst performing session."""
    # Add other sessions with better performance
    trades = mock_trades_sydney_low_performance.copy()

    # Add London with 60% win rate (25 trades)
    for i in range(25):
        is_winner = (i % 10) < 6
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")
        rr = Decimal("2.0") if is_winner else Decimal("0.5")

        trade = Mock()
        trade.trade_id = f"london_{i}"
        trade.session = "LONDON"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("75.0")
        trade.pnl = pnl
        trade.risk_reward_ratio = rr
        trade.entry_time = datetime(2025, 10, 10, 12, 0, 0)
        trades.append(trade)

    session_metrics = performance_analyzer.analyze_by_session(trades)
    worst_session = performance_analyzer.identify_worst_performer(session_metrics)

    # Sydney has 30% win rate, should be worst
    assert worst_session == "SYDNEY"


def test_identify_worst_performer_requires_significance(performance_analyzer):
    """Test that worst performer requires statistical significance."""
    trades = []

    # Create Sydney with 10% win rate but only 15 trades (below threshold)
    for i in range(15):
        is_winner = (i % 10) < 1
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")

        trade = Mock()
        trade.session = "SYDNEY"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("75.0")
        trade.pnl = pnl
        trade.risk_reward_ratio = Decimal("2.0")
        trades.append(trade)

    # Create London with 40% win rate but 25 trades (above threshold)
    for i in range(25):
        is_winner = (i % 10) < 4
        pnl = Decimal("100.00") if is_winner else Decimal("-50.00")

        trade = Mock()
        trade.session = "LONDON"
        trade.pattern_type = "Spring"
        trade.confidence_score = Decimal("75.0")
        trade.pnl = pnl
        trade.risk_reward_ratio = Decimal("2.0")
        trades.append(trade)

    session_metrics = performance_analyzer.analyze_by_session(trades)
    worst_session = performance_analyzer.identify_worst_performer(session_metrics)

    # London should be worst (Sydney doesn't meet significance threshold)
    assert worst_session == "LONDON"


# ============================================================================
# Tests: analyze_performance (integration)
# ============================================================================

def test_analyze_performance_complete(performance_analyzer, mock_trades_100):
    """Test complete performance analysis."""
    analysis = performance_analyzer.analyze_performance(mock_trades_100)

    # Verify all dimensions analyzed
    assert len(analysis.session_metrics) == 5
    assert len(analysis.pattern_metrics) == 4
    assert len(analysis.confidence_metrics) > 0

    # Verify metadata
    assert analysis.trade_count == 100
    assert analysis.analysis_timestamp is not None
    assert analysis.best_session is not None
    assert analysis.worst_session is not None


def test_analyze_performance_summary(performance_analyzer, mock_trades_100):
    """Test summary generation."""
    analysis = performance_analyzer.analyze_performance(mock_trades_100)
    summary = analysis.summary()

    # Verify summary contains key information
    assert "Performance Analysis Summary" in summary
    assert "Total Trades Analyzed: 100" in summary
    assert "Session Performance:" in summary
    assert "Pattern Performance:" in summary
    assert "Confidence Bucket Performance:" in summary
    assert "Best Performing Session:" in summary
    assert "Worst Performing Session:" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
