"""
Unit tests for ParameterSuggestionEngine.

Tests suggestion generation rules for low win rate, high win rate low volume,
and low risk-reward scenarios with proper validation and sorting.
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.parameter_optimizer import ParameterSuggestionEngine
from app.models.performance_models import (
    SessionMetrics,
    PatternMetrics,
    ConfidenceMetrics,
    PerformanceAnalysis
)
from app.models.suggestion_models import ParameterSuggestion


class TestParameterSuggestionEngine:
    """Test suite for ParameterSuggestionEngine."""

    def test_suggest_for_low_win_rate(self):
        """Test suggestion generation for low win rate (<45%)."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        session_metrics = {
            "TOKYO": {
                "win_rate": Decimal("35.0"),
                "total_trades": 50,
                "avg_rr": Decimal("2.5"),
                "sample_size": 50
            }
        }

        # Act
        suggestions = engine.suggest_for_low_win_rate(session_metrics)

        # Assert
        assert len(suggestions) == 1
        suggestion = suggestions[0]

        assert suggestion.session == "TOKYO"
        assert suggestion.parameter == "confidence_threshold"
        assert suggestion.suggested_value == Decimal("90")  # 85 + 5
        assert "below target 45%" in suggestion.reason
        assert "TOKYO" in suggestion.reason

        # Calculate expected improvement: (45 - 35) / 45 = 0.222...
        expected_improvement = (Decimal("45") - Decimal("35")) / Decimal("45")
        assert abs(suggestion.expected_improvement - expected_improvement) < Decimal("0.01")

        # Confidence level should be 0.8 for sample_size >= 30
        assert suggestion.confidence_level == Decimal("0.8")

    def test_suggest_for_low_win_rate_small_sample(self):
        """Test suggestion with smaller sample size (20-29) gets lower confidence."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        session_metrics = {
            "LONDON": {
                "win_rate": Decimal("30.0"),
                "total_trades": 25,
                "avg_rr": Decimal("3.0"),
                "sample_size": 25
            }
        }

        # Act
        suggestions = engine.suggest_for_low_win_rate(session_metrics)

        # Assert
        assert len(suggestions) == 1
        suggestion = suggestions[0]

        # Confidence level should be 0.6 for sample_size < 30
        assert suggestion.confidence_level == Decimal("0.6")

    def test_suggest_for_high_win_rate_low_volume(self):
        """Test suggestion for high win rate (>60%) with low volume (<5 trades)."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        session_metrics = {
            "LONDON": {
                "win_rate": Decimal("75.0"),
                "total_trades": 3,
                "avg_rr": Decimal("3.2"),
                "sample_size": 30
            }
        }

        # Act
        suggestions = engine.suggest_for_high_win_rate_low_volume(session_metrics)

        # Assert
        assert len(suggestions) == 1
        suggestion = suggestions[0]

        assert suggestion.session == "LONDON"
        assert suggestion.parameter == "confidence_threshold"
        assert suggestion.suggested_value == Decimal("67")  # 72 - 5
        assert "opportunity for more trades" in suggestion.reason
        assert "High win rate" in suggestion.reason

        # Expected improvement is fixed at 0.15 for volume expansion
        assert suggestion.expected_improvement == Decimal("0.15")
        assert suggestion.confidence_level == Decimal("0.7")

    def test_suggest_for_low_risk_reward(self):
        """Test suggestion for low average R:R (<2.0)."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        session_metrics = {
            "NY": {
                "win_rate": Decimal("50.0"),
                "total_trades": 40,
                "avg_rr": Decimal("1.5"),
                "sample_size": 40
            }
        }

        # Act
        suggestions = engine.suggest_for_low_risk_reward(session_metrics)

        # Assert
        assert len(suggestions) == 1
        suggestion = suggestions[0]

        assert suggestion.session == "NY"
        assert suggestion.parameter == "min_risk_reward"
        assert suggestion.suggested_value == Decimal("3.0")  # 2.8 + 0.2
        assert "below minimum 2.0" in suggestion.reason

        # Calculate expected improvement: (2.0 - 1.5) / 2.0 = 0.25
        expected_improvement = (Decimal("2.0") - Decimal("1.5")) / Decimal("2.0")
        assert abs(suggestion.expected_improvement - expected_improvement) < Decimal("0.01")

        assert suggestion.confidence_level == Decimal("0.75")

    def test_suggestion_sorting_by_expected_improvement(self):
        """Test that suggestions are sorted by expected_improvement descending."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        # Create session metrics with multiple issues
        session_metrics_dict = {
            "TOKYO": SessionMetrics(
                session="TOKYO",
                total_trades=50,
                winning_trades=15,
                losing_trades=35,
                win_rate=Decimal("30.0"),  # Low win rate -> high improvement
                avg_rr=Decimal("2.5"),
                profit_factor=Decimal("1.0"),
                total_pnl=Decimal("100")
            ),
            "LONDON": SessionMetrics(
                session="LONDON",
                total_trades=25,
                winning_trades=20,
                losing_trades=5,
                win_rate=Decimal("80.0"),  # High win rate, assume low volume
                avg_rr=Decimal("3.2"),
                profit_factor=Decimal("2.0"),
                total_pnl=Decimal("500")
            ),
            "NY": SessionMetrics(
                session="NY",
                total_trades=40,
                winning_trades=20,
                losing_trades=20,
                win_rate=Decimal("50.0"),
                avg_rr=Decimal("1.8"),  # Low R:R
                profit_factor=Decimal("1.2"),
                total_pnl=Decimal("200")
            )
        }

        analysis = PerformanceAnalysis(
            session_metrics=session_metrics_dict,
            pattern_metrics={},
            confidence_metrics={},
            analysis_timestamp=None,
            trade_count=115
        )

        # Mock low volume for LONDON
        engine.parameter_config["LONDON"]["confidence_threshold"] = Decimal("72")

        # Act
        suggestions = engine.generate_suggestions(analysis, max_suggestions=3)

        # Assert
        assert len(suggestions) > 0

        # Verify sorting (descending by expected_improvement)
        for i in range(len(suggestions) - 1):
            assert suggestions[i].expected_improvement >= suggestions[i + 1].expected_improvement

    def test_suggestion_validation_confidence_bounds(self):
        """Test that suggestions outside confidence threshold bounds are rejected."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        # Set current value near upper bound
        engine.parameter_config["TOKYO"]["confidence_threshold"] = Decimal("92")

        session_metrics = {
            "TOKYO": {
                "win_rate": Decimal("35.0"),
                "total_trades": 50,
                "avg_rr": Decimal("2.5"),
                "sample_size": 50
            }
        }

        # Act
        suggestions = engine.suggest_for_low_win_rate(session_metrics)

        # Assert - suggestion should be skipped because 92 + 5 = 97 > 95 (max bound)
        assert len(suggestions) == 0

    def test_suggestion_validation_rr_bounds(self):
        """Test that R:R suggestions outside bounds are rejected."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        # Set current value near upper bound
        engine.parameter_config["NY"]["min_risk_reward"] = Decimal("4.9")

        session_metrics = {
            "NY": {
                "win_rate": Decimal("50.0"),
                "total_trades": 40,
                "avg_rr": Decimal("1.5"),
                "sample_size": 40
            }
        }

        # Act
        suggestions = engine.suggest_for_low_risk_reward(session_metrics)

        # Assert - suggestion should be skipped because 4.9 + 0.2 = 5.1 > 5.0 (max bound)
        assert len(suggestions) == 0

    def test_suggestion_validation_invalid_expected_improvement(self):
        """Test that ParameterSuggestion validates expected_improvement range."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="expected_improvement must be between 0 and 1"):
            ParameterSuggestion(
                session="TOKYO",
                parameter="confidence_threshold",
                current_value=Decimal("70"),
                suggested_value=Decimal("75"),
                reason="Test",
                expected_improvement=Decimal("1.5"),  # Invalid: > 1
                confidence_level=Decimal("0.8")
            )

    def test_suggestion_validation_invalid_confidence_level(self):
        """Test that ParameterSuggestion validates confidence_level range."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="confidence_level must be between 0 and 1"):
            ParameterSuggestion(
                session="TOKYO",
                parameter="confidence_threshold",
                current_value=Decimal("70"),
                suggested_value=Decimal("75"),
                reason="Test",
                expected_improvement=Decimal("0.2"),
                confidence_level=Decimal("1.2")  # Invalid: > 1
            )

    def test_insufficient_sample_size(self):
        """Test that suggestions are not generated for insufficient sample size."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        session_metrics = {
            "TOKYO": {
                "win_rate": Decimal("35.0"),
                "total_trades": 15,  # Below min_sample_size
                "avg_rr": Decimal("2.5"),
                "sample_size": 15
            }
        }

        # Act
        suggestions = engine.suggest_for_low_win_rate(session_metrics)

        # Assert
        assert len(suggestions) == 0

    def test_max_suggestions_limit(self):
        """Test that generate_suggestions respects max_suggestions parameter."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        # Create analysis with multiple sessions triggering suggestions
        # Use valid session names
        sessions = ["TOKYO", "LONDON", "NY", "SYDNEY", "OVERLAP"]
        session_metrics_dict = {
            session: SessionMetrics(
                session=session,
                total_trades=50,
                winning_trades=15,
                losing_trades=35,
                win_rate=Decimal("30.0"),
                avg_rr=Decimal("2.5"),
                profit_factor=Decimal("1.0"),
                total_pnl=Decimal("100")
            )
            for session in sessions
        }

        analysis = PerformanceAnalysis(
            session_metrics=session_metrics_dict,
            pattern_metrics={},
            confidence_metrics={},
            analysis_timestamp=None,
            trade_count=250
        )

        # Act
        suggestions = engine.generate_suggestions(analysis, max_suggestions=2)

        # Assert
        assert len(suggestions) == 2

    def test_20_percent_improvement_scenario(self):
        """Test suggestion correctly identifies 20% improvement scenario."""
        # Arrange
        engine = ParameterSuggestionEngine(min_sample_size=20)

        # Create scenario where improvement would be ~20%
        session_metrics = {
            "TOKYO": {
                "win_rate": Decimal("36.0"),  # 20% below 45% target
                "total_trades": 50,
                "avg_rr": Decimal("2.5"),
                "sample_size": 50
            }
        }

        # Act
        suggestions = engine.suggest_for_low_win_rate(session_metrics)

        # Assert
        assert len(suggestions) == 1
        suggestion = suggestions[0]

        # Calculate expected improvement: (45 - 36) / 45 = 0.20
        expected_improvement = (Decimal("45") - Decimal("36")) / Decimal("45")
        assert abs(suggestion.expected_improvement - Decimal("0.2")) < Decimal("0.01")
