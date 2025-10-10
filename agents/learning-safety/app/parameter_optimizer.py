"""
Parameter suggestion engine for autonomous learning optimization.

Analyzes trading performance and generates intelligent parameter adjustment
suggestions based on win rate, volume, and risk-reward metrics.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from .models.suggestion_models import ParameterSuggestion
from .models.performance_models import PerformanceAnalysis


logger = logging.getLogger(__name__)


class ParameterSuggestionEngine:
    """
    Intelligent parameter suggestion engine.

    Analyzes performance metrics across trading sessions and generates
    data-driven parameter adjustment suggestions to improve win rate,
    trade volume, and risk-reward ratios.
    """

    def __init__(
        self,
        parameter_config: Optional[Dict] = None,
        min_sample_size: int = 20
    ):
        """
        Initialize parameter suggestion engine.

        Args:
            parameter_config: Current parameter values by session
                Example: {
                    "TOKYO": {"confidence_threshold": 85, "min_risk_reward": 4.0},
                    "LONDON": {"confidence_threshold": 72, "min_risk_reward": 3.2}
                }
            min_sample_size: Minimum trades required for statistical significance
        """
        self.parameter_config = parameter_config or self._default_config()
        self.min_sample_size = min_sample_size

        # Suggestion rule configuration
        self.low_win_rate_threshold = Decimal("45")  # Below 45% win rate
        self.high_win_rate_threshold = Decimal("60")  # Above 60% win rate
        self.low_volume_threshold = 5  # Less than 5 trades
        self.low_rr_threshold = Decimal("2.0")  # Below 2.0 R:R

        # Parameter bounds for validation
        self.confidence_threshold_min = Decimal("40")
        self.confidence_threshold_max = Decimal("95")
        self.min_risk_reward_min = Decimal("1.5")
        self.min_risk_reward_max = Decimal("5.0")

        logger.info("✅ ParameterSuggestionEngine initialized")

    def _default_config(self) -> Dict:
        """
        Create default parameter configuration.

        Returns:
            Dict: Default parameter values for all sessions
        """
        return {
            "TOKYO": {"confidence_threshold": Decimal("85"), "min_risk_reward": Decimal("4.0")},
            "LONDON": {"confidence_threshold": Decimal("72"), "min_risk_reward": Decimal("3.2")},
            "NY": {"confidence_threshold": Decimal("70"), "min_risk_reward": Decimal("2.8")},
            "SYDNEY": {"confidence_threshold": Decimal("78"), "min_risk_reward": Decimal("3.5")},
            "OVERLAP": {"confidence_threshold": Decimal("70"), "min_risk_reward": Decimal("2.8")}
        }

    def generate_suggestions(
        self,
        analysis: PerformanceAnalysis,
        max_suggestions: int = 3
    ) -> List[ParameterSuggestion]:
        """
        Generate parameter adjustment suggestions from performance analysis.

        Args:
            analysis: Performance analysis results with session metrics
            max_suggestions: Maximum number of suggestions to return (default: 3)

        Returns:
            List[ParameterSuggestion]: Top N suggestions sorted by expected improvement
        """
        logger.info("🔍 Generating parameter suggestions from performance analysis")

        all_suggestions = []

        # Extract session metrics dictionary
        session_metrics_dict = {}
        for session, metrics in analysis.session_metrics.items():
            session_metrics_dict[session] = {
                "win_rate": metrics.win_rate,
                "total_trades": metrics.total_trades,
                "avg_rr": metrics.avg_rr,
                "sample_size": metrics.total_trades
            }

        # Apply all suggestion rules
        all_suggestions.extend(self.suggest_for_low_win_rate(session_metrics_dict))
        all_suggestions.extend(self.suggest_for_high_win_rate_low_volume(session_metrics_dict))
        all_suggestions.extend(self.suggest_for_low_risk_reward(session_metrics_dict))

        # Sort by expected improvement (descending)
        all_suggestions.sort(key=lambda s: s.expected_improvement, reverse=True)

        # Return top N suggestions
        top_suggestions = all_suggestions[:max_suggestions]

        logger.info(
            f"✅ Generated {len(all_suggestions)} suggestions, "
            f"returning top {len(top_suggestions)}"
        )

        return top_suggestions

    def suggest_for_low_win_rate(
        self,
        session_metrics: Dict
    ) -> List[ParameterSuggestion]:
        """
        Generate suggestions for sessions with low win rate (<45%).

        Suggests increasing confidence threshold to filter out lower-quality signals.

        Args:
            session_metrics: Dictionary of session metrics
                Example: {"TOKYO": {"win_rate": 35.0, "sample_size": 50, ...}}

        Returns:
            List[ParameterSuggestion]: Suggestions for low win rate sessions
        """
        suggestions = []

        for session, metrics in session_metrics.items():
            win_rate = metrics["win_rate"]
            sample_size = metrics["sample_size"]

            # Check if session meets criteria
            if (
                win_rate < self.low_win_rate_threshold
                and sample_size >= self.min_sample_size
            ):
                # Get current confidence threshold
                current_value = self.parameter_config.get(session, {}).get(
                    "confidence_threshold",
                    Decimal("70")
                )

                # Suggest increasing by 5%
                suggested_value = current_value + Decimal("5")

                # Validate bounds
                if not self._validate_confidence_bounds(suggested_value):
                    logger.warning(
                        f"⚠️  Skipping suggestion for {session}: "
                        f"suggested value {suggested_value} out of bounds"
                    )
                    continue

                # Calculate expected improvement (normalized 0-1)
                expected_improvement = (self.low_win_rate_threshold - win_rate) / self.low_win_rate_threshold
                expected_improvement = max(Decimal("0"), min(Decimal("1"), expected_improvement))

                # Confidence level based on sample size
                confidence_level = Decimal("0.8") if sample_size >= 30 else Decimal("0.6")

                suggestion = ParameterSuggestion(
                    session=session,
                    parameter="confidence_threshold",
                    current_value=current_value,
                    suggested_value=suggested_value,
                    reason=f"Win rate {win_rate:.1f}% below target {self.low_win_rate_threshold}% for {session} session",
                    expected_improvement=expected_improvement,
                    confidence_level=confidence_level
                )

                suggestions.append(suggestion)
                logger.info(
                    f"📊 Low win rate suggestion: {session} "
                    f"{current_value}% → {suggested_value}% "
                    f"(expected improvement: {expected_improvement:.2f})"
                )

        return suggestions

    def suggest_for_high_win_rate_low_volume(
        self,
        session_metrics: Dict
    ) -> List[ParameterSuggestion]:
        """
        Generate suggestions for sessions with high win rate (>60%) but low volume (<5 trades).

        Suggests decreasing confidence threshold to generate more signals while
        maintaining quality.

        Args:
            session_metrics: Dictionary of session metrics

        Returns:
            List[ParameterSuggestion]: Suggestions for high win rate low volume sessions
        """
        suggestions = []

        for session, metrics in session_metrics.items():
            win_rate = metrics["win_rate"]
            total_trades = metrics["total_trades"]
            sample_size = metrics["sample_size"]

            # Check if session meets criteria
            if (
                win_rate > self.high_win_rate_threshold
                and total_trades < self.low_volume_threshold
                and sample_size >= self.min_sample_size
            ):
                # Get current confidence threshold
                current_value = self.parameter_config.get(session, {}).get(
                    "confidence_threshold",
                    Decimal("70")
                )

                # Suggest decreasing by 5%
                suggested_value = current_value - Decimal("5")

                # Validate bounds
                if not self._validate_confidence_bounds(suggested_value):
                    logger.warning(
                        f"⚠️  Skipping suggestion for {session}: "
                        f"suggested value {suggested_value} out of bounds"
                    )
                    continue

                # Fixed expected improvement for volume expansion
                expected_improvement = Decimal("0.15")

                # Confidence level
                confidence_level = Decimal("0.7")

                suggestion = ParameterSuggestion(
                    session=session,
                    parameter="confidence_threshold",
                    current_value=current_value,
                    suggested_value=suggested_value,
                    reason=f"High win rate {win_rate:.1f}% with low volume {total_trades} for {session} session - opportunity for more trades",
                    expected_improvement=expected_improvement,
                    confidence_level=confidence_level
                )

                suggestions.append(suggestion)
                logger.info(
                    f"📊 High win rate low volume suggestion: {session} "
                    f"{current_value}% → {suggested_value}% "
                    f"(expected improvement: {expected_improvement:.2f})"
                )

        return suggestions

    def suggest_for_low_risk_reward(
        self,
        session_metrics: Dict
    ) -> List[ParameterSuggestion]:
        """
        Generate suggestions for sessions with low average R:R (<2.0).

        Suggests increasing minimum risk-reward ratio requirement to improve
        trade quality.

        Args:
            session_metrics: Dictionary of session metrics

        Returns:
            List[ParameterSuggestion]: Suggestions for low R:R sessions
        """
        suggestions = []

        for session, metrics in session_metrics.items():
            avg_rr = metrics["avg_rr"]
            sample_size = metrics["sample_size"]

            # Check if session meets criteria
            if (
                avg_rr < self.low_rr_threshold
                and sample_size >= self.min_sample_size
            ):
                # Get current min_risk_reward
                current_value = self.parameter_config.get(session, {}).get(
                    "min_risk_reward",
                    Decimal("2.0")
                )

                # Suggest increasing by 0.2
                suggested_value = current_value + Decimal("0.2")

                # Validate bounds
                if not self._validate_rr_bounds(suggested_value):
                    logger.warning(
                        f"⚠️  Skipping suggestion for {session}: "
                        f"suggested value {suggested_value} out of bounds"
                    )
                    continue

                # Calculate expected improvement (normalized 0-1)
                expected_improvement = (self.low_rr_threshold - avg_rr) / self.low_rr_threshold
                expected_improvement = max(Decimal("0"), min(Decimal("1"), expected_improvement))

                # Confidence level
                confidence_level = Decimal("0.75")

                suggestion = ParameterSuggestion(
                    session=session,
                    parameter="min_risk_reward",
                    current_value=current_value,
                    suggested_value=suggested_value,
                    reason=f"Average R:R {avg_rr:.2f} below minimum {self.low_rr_threshold} for {session} session",
                    expected_improvement=expected_improvement,
                    confidence_level=confidence_level
                )

                suggestions.append(suggestion)
                logger.info(
                    f"📊 Low R:R suggestion: {session} "
                    f"{current_value} → {suggested_value} "
                    f"(expected improvement: {expected_improvement:.2f})"
                )

        return suggestions

    def _validate_confidence_bounds(self, value: Decimal) -> bool:
        """
        Validate confidence threshold is within reasonable bounds.

        Args:
            value: Confidence threshold value to validate

        Returns:
            bool: True if within bounds (40-95%), False otherwise
        """
        return self.confidence_threshold_min <= value <= self.confidence_threshold_max

    def _validate_rr_bounds(self, value: Decimal) -> bool:
        """
        Validate risk-reward ratio is within reasonable bounds.

        Args:
            value: Risk-reward ratio to validate

        Returns:
            bool: True if within bounds (1.5-5.0), False otherwise
        """
        return self.min_risk_reward_min <= value <= self.min_risk_reward_max
