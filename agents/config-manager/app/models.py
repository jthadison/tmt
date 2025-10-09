"""
Configuration Models

Pydantic models for configuration validation and API responses.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from decimal import Decimal


class SessionConfig(BaseModel):
    """Session-specific trading parameters"""

    confidence_threshold: float = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence threshold percentage (0-100)"
    )
    min_risk_reward: float = Field(
        ...,
        gt=0,
        description="Minimum risk-reward ratio (must be > 0)"
    )
    max_risk_reward: Optional[float] = Field(
        None,
        gt=0,
        description="Maximum risk-reward ratio"
    )
    volatility_adjustment: Optional[float] = Field(
        None,
        description="Volatility adjustment factor"
    )
    justification: Optional[str] = Field(
        None,
        description="Justification for session-specific parameters"
    )
    deviation_from_baseline: Optional[Dict[str, float]] = Field(
        None,
        description="Calculated deviations from baseline"
    )

    @field_validator('max_risk_reward')
    @classmethod
    def validate_max_greater_than_min(cls, v, info):
        """Validate max_risk_reward > min_risk_reward"""
        if v is not None and 'min_risk_reward' in info.data:
            if v <= info.data['min_risk_reward']:
                raise ValueError("max_risk_reward must be greater than min_risk_reward")
        return v


class BaselineConfig(BaseModel):
    """Baseline trading parameters"""

    confidence_threshold: float = Field(
        ...,
        ge=0,
        le=100,
        description="Baseline confidence threshold"
    )
    min_risk_reward: float = Field(
        ...,
        gt=0,
        description="Baseline minimum risk-reward ratio"
    )
    max_risk_reward: Optional[float] = Field(
        None,
        gt=0,
        description="Baseline maximum risk-reward ratio"
    )
    source: Optional[str] = Field(
        None,
        description="Source of baseline parameters"
    )


class ValidationMetrics(BaseModel):
    """Validation metrics from backtesting"""

    backtest_sharpe: Optional[float] = Field(
        None,
        ge=0,
        description="In-sample Sharpe ratio"
    )
    out_of_sample_sharpe: Optional[float] = Field(
        None,
        ge=0,
        description="Out-of-sample Sharpe ratio"
    )
    overfitting_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Overfitting score (0-1, lower is better)"
    )
    max_drawdown: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Maximum drawdown (0-1)"
    )
    approved_by: Optional[str] = Field(
        None,
        description="Person who approved"
    )
    approved_date: Optional[date] = Field(
        None,
        description="Date of approval"
    )


class Constraints(BaseModel):
    """System-wide constraints and thresholds"""

    max_confidence_deviation: float = Field(
        ...,
        ge=0,
        description="Maximum allowed deviation from baseline confidence (%)"
    )
    max_risk_reward_deviation: float = Field(
        ...,
        ge=0,
        description="Maximum allowed deviation from baseline risk-reward"
    )
    max_overfitting_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Maximum acceptable overfitting score"
    )
    min_backtest_sharpe: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum required Sharpe ratio for backtest"
    )
    min_out_of_sample_ratio: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Minimum ratio of out-of-sample to in-sample Sharpe"
    )


class AlertThresholds(BaseModel):
    """Alert thresholds for monitoring"""

    overfitting_warning: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Overfitting score threshold for warning"
    )
    overfitting_critical: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Overfitting score threshold for critical alert"
    )


class TradingConfig(BaseModel):
    """Complete trading system configuration"""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version (e.g., 1.0.0)"
    )
    effective_date: date = Field(
        ...,
        description="Date when configuration becomes effective"
    )
    author: str = Field(
        ...,
        min_length=1,
        description="Author of the configuration change"
    )
    reason: str = Field(
        ...,
        min_length=10,
        description="Justification for the configuration change"
    )
    validation: Optional[ValidationMetrics] = Field(
        None,
        description="Validation metrics from backtesting"
    )
    baseline: BaselineConfig = Field(
        ...,
        description="Baseline parameters"
    )
    session_parameters: Dict[str, SessionConfig] = Field(
        ...,
        description="Session-specific parameter overrides"
    )
    constraints: Constraints = Field(
        ...,
        description="System-wide constraints"
    )
    alerts: Optional[AlertThresholds] = Field(
        None,
        description="Alert thresholds"
    )

    @field_validator('session_parameters')
    @classmethod
    def validate_sessions(cls, v):
        """Validate session parameters"""
        valid_sessions = {'tokyo', 'london', 'new_york', 'sydney', 'overlap'}
        for session_name in v.keys():
            if session_name not in valid_sessions:
                raise ValueError(
                    f"Invalid session '{session_name}'. "
                    f"Must be one of: {', '.join(valid_sessions)}"
                )
        return v

    def validate_constraints(self) -> List[str]:
        """
        Validate configuration against constraints

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check deviation constraints for each session
        for session_name, session in self.session_parameters.items():
            # Confidence deviation
            confidence_deviation = abs(
                session.confidence_threshold - self.baseline.confidence_threshold
            )
            if confidence_deviation > self.constraints.max_confidence_deviation:
                errors.append(
                    f"Session '{session_name}': confidence deviation "
                    f"{confidence_deviation:.1f}% exceeds maximum "
                    f"{self.constraints.max_confidence_deviation:.1f}%"
                )

            # Risk-reward deviation
            rr_deviation = abs(session.min_risk_reward - self.baseline.min_risk_reward)
            if rr_deviation > self.constraints.max_risk_reward_deviation:
                errors.append(
                    f"Session '{session_name}': risk-reward deviation "
                    f"{rr_deviation:.2f} exceeds maximum "
                    f"{self.constraints.max_risk_reward_deviation:.2f}"
                )

        # Check overfitting score if validation provided
        if self.validation and self.validation.overfitting_score:
            if self.validation.overfitting_score > self.constraints.max_overfitting_score:
                errors.append(
                    f"Overfitting score {self.validation.overfitting_score:.3f} "
                    f"exceeds maximum {self.constraints.max_overfitting_score:.3f}"
                )

        # Check minimum Sharpe ratio
        if (self.constraints.min_backtest_sharpe and
            self.validation and
            self.validation.backtest_sharpe):
            if self.validation.backtest_sharpe < self.constraints.min_backtest_sharpe:
                errors.append(
                    f"Backtest Sharpe {self.validation.backtest_sharpe:.2f} "
                    f"below minimum {self.constraints.min_backtest_sharpe:.2f}"
                )

        # Check out-of-sample ratio
        if (self.constraints.min_out_of_sample_ratio and
            self.validation and
            self.validation.backtest_sharpe and
            self.validation.out_of_sample_sharpe):
            ratio = (self.validation.out_of_sample_sharpe /
                    self.validation.backtest_sharpe)
            if ratio < self.constraints.min_out_of_sample_ratio:
                errors.append(
                    f"Out-of-sample ratio {ratio:.2f} "
                    f"below minimum {self.constraints.min_out_of_sample_ratio:.2f}"
                )

        return errors


class ConfigHistoryEntry(BaseModel):
    """Configuration history entry from Git"""

    version: str
    commit_hash: str
    author: str
    timestamp: datetime
    message: str
    file_path: str


class ConfigActivationRequest(BaseModel):
    """Request to activate a configuration version"""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Version to activate"
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for activation"
    )


class ConfigRollbackRequest(BaseModel):
    """Request to rollback configuration"""

    version: Optional[str] = Field(
        None,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Version to rollback to (if None, rollback to previous)"
    )
    reason: str = Field(
        ...,
        min_length=10,
        description="Reason for rollback"
    )
    emergency: bool = Field(
        False,
        description="Emergency rollback flag"
    )


class ConfigProposeRequest(BaseModel):
    """Request to propose a new configuration"""

    config: TradingConfig
    reason: str = Field(
        ...,
        min_length=10,
        description="Reason for proposed change"
    )
    validation_results: Optional[ValidationMetrics] = Field(
        None,
        description="Validation results from testing"
    )


class ConfigValidationResult(BaseModel):
    """Result of configuration validation"""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    schema_valid: bool
    constraints_valid: bool
