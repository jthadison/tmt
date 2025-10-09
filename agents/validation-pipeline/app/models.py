"""
Validation Pipeline Models - Story 11.7

Data models for parameter validation pipeline
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ValidationStatus(str, Enum):
    """Validation result status"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WARNING = "WARNING"
    IN_PROGRESS = "IN_PROGRESS"
    FAILED = "FAILED"


class SchemaValidationResult(BaseModel):
    """Schema validation result"""
    passed: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class OverfittingValidationResult(BaseModel):
    """Overfitting score validation result"""
    passed: bool
    overfitting_score: float
    threshold: float = 0.3
    message: str


class WalkForwardValidationResult(BaseModel):
    """Walk-forward backtest validation result"""
    passed: bool
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int
    avg_out_of_sample_sharpe: float
    message: str


class MonteCarloConfig(BaseModel):
    """Configuration for Monte Carlo simulation"""
    num_runs: int = 1000
    entry_price_variation_pips: float = 5.0
    exit_timing_variation_hours: int = 2
    slippage_range_pips: tuple[float, float] = (0.0, 3.0)
    confidence_level: float = 0.95  # 95% CI
    parallel_workers: int = 4


class MonteCarloValidationResult(BaseModel):
    """Monte Carlo simulation validation result"""
    passed: bool
    num_runs: int
    sharpe_mean: float
    sharpe_std: float
    sharpe_95ci_lower: float
    sharpe_95ci_upper: float
    drawdown_95ci_lower: float
    drawdown_95ci_upper: float
    win_rate_95ci_lower: float
    win_rate_95ci_upper: float
    threshold: float = 0.8  # Lower bound threshold
    message: str


class CrisisPeriod(BaseModel):
    """Definition of a crisis period for stress testing"""
    name: str
    start: datetime
    end: datetime
    max_drawdown_threshold: float = 0.25
    recovery_days_threshold: int = 90


class StressTestResult(BaseModel):
    """Stress test result for a single crisis period"""
    crisis_name: str
    passed: bool
    max_drawdown: float
    max_drawdown_threshold: float
    recovery_days: Optional[int] = None
    recovery_threshold: int = 90
    num_trades: int
    message: str


class StressTestValidationResult(BaseModel):
    """Overall stress testing validation result"""
    passed: bool
    crisis_results: List[StressTestResult]
    message: str


class AcceptanceCriteriaResult(BaseModel):
    """Individual acceptance criterion check result"""
    criterion: str
    passed: bool
    actual_value: float
    threshold: float
    operator: str  # '>', '<', '>=', '<='
    message: str


class AcceptanceCriteriaValidation(BaseModel):
    """Overall acceptance criteria validation"""
    passed: bool
    all_criteria: List[AcceptanceCriteriaResult]
    passed_count: int
    failed_count: int


class ValidationReport(BaseModel):
    """Complete validation report"""
    job_id: str
    config_file: str
    timestamp: datetime
    status: ValidationStatus
    duration_seconds: float

    # Individual validation results
    schema_validation: SchemaValidationResult
    overfitting_validation: OverfittingValidationResult
    walk_forward_validation: WalkForwardValidationResult
    monte_carlo_validation: MonteCarloValidationResult
    stress_test_validation: StressTestValidationResult
    acceptance_criteria: AcceptanceCriteriaValidation

    # Summary
    all_checks_passed: bool
    recommendations: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidationJobStatus(BaseModel):
    """Status of an async validation job"""
    job_id: str
    status: ValidationStatus
    progress_pct: float = 0.0
    current_step: str = ""
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[ValidationReport] = None
