"""
Parameter suggestion and shadow test evaluation data models.

Defines dataclasses for parameter optimization suggestions and shadow test
evaluation results with validation and serialization support.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional


@dataclass
class ParameterSuggestion:
    """
    Parameter optimization suggestion with expected improvement metrics.

    Represents a single parameter change suggestion based on performance
    analysis, including current/suggested values, reasoning, and confidence.
    """

    suggestion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session: str = ""
    parameter: str = ""
    current_value: Decimal = Decimal("0")
    suggested_value: Decimal = Decimal("0")
    reason: str = ""
    expected_improvement: Decimal = Decimal("0")
    confidence_level: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "PENDING"  # PENDING, TESTING, DEPLOYED, REJECTED

    def __post_init__(self):
        """Validate suggestion data after initialization."""
        # Convert to Decimal if needed
        if not isinstance(self.current_value, Decimal):
            self.current_value = Decimal(str(self.current_value))
        if not isinstance(self.suggested_value, Decimal):
            self.suggested_value = Decimal(str(self.suggested_value))
        if not isinstance(self.expected_improvement, Decimal):
            self.expected_improvement = Decimal(str(self.expected_improvement))
        if not isinstance(self.confidence_level, Decimal):
            self.confidence_level = Decimal(str(self.confidence_level))

        # Validate expected_improvement range
        if not (Decimal("0") <= self.expected_improvement <= Decimal("1")):
            raise ValueError(
                f"expected_improvement must be between 0 and 1, got {self.expected_improvement}"
            )

        # Validate confidence_level range
        if not (Decimal("0") <= self.confidence_level <= Decimal("1")):
            raise ValueError(
                f"confidence_level must be between 0 and 1, got {self.confidence_level}"
            )

        # Validate parameter is in allowed list
        allowed_parameters = ["confidence_threshold", "min_risk_reward"]
        if self.parameter and self.parameter not in allowed_parameters:
            raise ValueError(
                f"parameter must be one of {allowed_parameters}, got {self.parameter}"
            )

        # Validate session is in allowed list
        allowed_sessions = ["TOKYO", "LONDON", "NY", "SYDNEY", "OVERLAP", "ALL"]
        if self.session and self.session.upper() not in allowed_sessions:
            raise ValueError(
                f"session must be one of {allowed_sessions}, got {self.session}"
            )

        # Ensure session is uppercase
        if self.session:
            self.session = self.session.upper()

    def to_dict(self) -> Dict:
        """
        Convert suggestion to dictionary for JSON serialization.

        Returns:
            Dict: Dictionary representation of suggestion
        """
        return {
            "suggestion_id": self.suggestion_id,
            "session": self.session,
            "parameter": self.parameter,
            "current_value": float(self.current_value),
            "suggested_value": float(self.suggested_value),
            "reason": self.reason,
            "expected_improvement": float(self.expected_improvement),
            "confidence_level": float(self.confidence_level),
            "created_at": self.created_at.isoformat(),
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ParameterSuggestion":
        """
        Create suggestion from dictionary.

        Args:
            data: Dictionary containing suggestion fields

        Returns:
            ParameterSuggestion: New suggestion instance
        """
        return cls(
            suggestion_id=data.get("suggestion_id", str(uuid.uuid4())),
            session=data["session"],
            parameter=data["parameter"],
            current_value=Decimal(str(data["current_value"])),
            suggested_value=Decimal(str(data["suggested_value"])),
            reason=data["reason"],
            expected_improvement=Decimal(str(data["expected_improvement"])),
            confidence_level=Decimal(str(data["confidence_level"])),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now()),
            status=data.get("status", "PENDING")
        )


@dataclass
class TestEvaluation:
    """
    Shadow test evaluation results with deployment decision.

    Contains comprehensive evaluation metrics comparing control and test groups
    including statistical significance testing and deployment recommendation.
    """

    test_id: str
    should_deploy: bool
    improvement_pct: Decimal
    p_value: Decimal
    control_mean_pnl: Decimal
    test_mean_pnl: Decimal
    control_win_rate: Decimal
    test_win_rate: Decimal
    sample_size_control: int
    sample_size_test: int
    reason: str
    evaluated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate evaluation data after initialization."""
        # Convert to Decimal if needed
        if not isinstance(self.improvement_pct, Decimal):
            self.improvement_pct = Decimal(str(self.improvement_pct))
        if not isinstance(self.p_value, Decimal):
            self.p_value = Decimal(str(self.p_value))
        if not isinstance(self.control_mean_pnl, Decimal):
            self.control_mean_pnl = Decimal(str(self.control_mean_pnl))
        if not isinstance(self.test_mean_pnl, Decimal):
            self.test_mean_pnl = Decimal(str(self.test_mean_pnl))
        if not isinstance(self.control_win_rate, Decimal):
            self.control_win_rate = Decimal(str(self.control_win_rate))
        if not isinstance(self.test_win_rate, Decimal):
            self.test_win_rate = Decimal(str(self.test_win_rate))

    def summary(self) -> str:
        """
        Generate human-readable summary of evaluation results.

        Returns:
            str: Formatted summary string with deployment decision and metrics
        """
        lines = [
            f"Shadow Test Evaluation - {self.test_id}",
            f"Evaluated at: {self.evaluated_at.isoformat()}",
            "",
            f"Deployment Decision: {'✅ DEPLOY' if self.should_deploy else '❌ DO NOT DEPLOY'}",
            f"Reason: {self.reason}",
            "",
            "Performance Comparison:",
            f"  Control Group: {self.sample_size_control} trades, {self.control_win_rate:.1f}% win rate, ${self.control_mean_pnl:.2f} avg P&L",
            f"  Test Group: {self.sample_size_test} trades, {self.test_win_rate:.1f}% win rate, ${self.test_mean_pnl:.2f} avg P&L",
            "",
            f"Improvement: {self.improvement_pct:.1f}%",
            f"Statistical Significance: p-value = {self.p_value:.4f} ({'significant' if self.p_value < Decimal('0.05') else 'not significant'})"
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """
        Convert evaluation to dictionary for JSON serialization.

        Returns:
            Dict: Dictionary representation of evaluation
        """
        return {
            "test_id": self.test_id,
            "should_deploy": self.should_deploy,
            "improvement_pct": float(self.improvement_pct),
            "p_value": float(self.p_value),
            "control_mean_pnl": float(self.control_mean_pnl),
            "test_mean_pnl": float(self.test_mean_pnl),
            "control_win_rate": float(self.control_win_rate),
            "test_win_rate": float(self.test_win_rate),
            "sample_size_control": self.sample_size_control,
            "sample_size_test": self.sample_size_test,
            "reason": self.reason,
            "evaluated_at": self.evaluated_at.isoformat()
        }
