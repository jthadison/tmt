"""
Walk-Forward Optimization Data Models - Story 11.3

Pydantic models for walk-forward configuration, results, and related data structures.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from decimal import Decimal


class WindowType(str, Enum):
    """Walk-forward window type"""
    ROLLING = "rolling"      # Fixed training window that moves forward
    ANCHORED = "anchored"    # Expanding training window


class OptimizationMethod(str, Enum):
    """Parameter optimization method"""
    GRID_SEARCH = "grid_search"          # Exhaustive grid search
    BAYESIAN = "bayesian"                # Bayesian optimization (fast mode)
    RANDOM_SEARCH = "random_search"      # Random search sampling


class WalkForwardConfig(BaseModel):
    """
    Walk-forward optimization configuration

    Defines all parameters needed for walk-forward validation including:
    - Date range and window configuration
    - Instruments and capital settings
    - Parameter ranges for optimization
    - Baseline parameters for comparison
    - Optimization method selection
    """

    # Date range
    start_date: datetime = Field(..., description="Walk-forward start date (UTC)")
    end_date: datetime = Field(..., description="Walk-forward end date (UTC)")

    # Window configuration
    training_window_days: int = Field(
        default=90,
        description="Training period duration in days",
        ge=30,
        le=365
    )
    testing_window_days: int = Field(
        default=30,
        description="Testing period duration in days",
        ge=7,
        le=90
    )
    step_size_days: int = Field(
        default=30,
        description="Step size for rolling window in days",
        ge=1,
        le=90
    )
    window_type: WindowType = Field(
        default=WindowType.ROLLING,
        description="Window type: rolling or anchored"
    )

    # Instruments
    instruments: List[str] = Field(
        ...,
        description="Trading instruments (e.g., ['EUR_USD', 'GBP_USD'])",
        min_length=1
    )
    initial_capital: float = Field(
        default=100000.0,
        description="Starting capital",
        gt=0
    )
    risk_percentage: float = Field(
        default=0.02,
        description="Risk per trade as decimal (0.02 = 2%)",
        gt=0,
        le=0.1
    )

    # Parameter ranges for optimization
    # Format: {"param_name": (min, max, step)}
    parameter_ranges: Dict[str, Tuple[float, float, float]] = Field(
        ...,
        description="Parameter ranges for grid search (min, max, step)"
    )

    # Baseline parameters for comparison
    baseline_parameters: Dict[str, Any] = Field(
        ...,
        description="Universal baseline parameters for comparison"
    )

    # Optimization settings
    optimization_method: OptimizationMethod = Field(
        default=OptimizationMethod.BAYESIAN,
        description="Optimization method to use"
    )
    max_iterations: Optional[int] = Field(
        default=None,
        description="Max iterations for Bayesian/Random optimization (None = all combinations)"
    )

    # Parallel processing
    n_workers: int = Field(
        default=4,
        description="Number of parallel workers for optimization",
        ge=1,
        le=16
    )

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v):
        """Ensure dates are timezone-aware UTC"""
        if v.tzinfo is None:
            raise ValueError("Dates must be timezone-aware (UTC)")
        return v

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure end_date is after start_date"""
        if 'start_date' in info.data:
            total_days = (v - info.data['start_date']).days
            if total_days <= 0:
                raise ValueError("end_date must be after start_date")

            # Validate minimum data for walk-forward
            min_window = info.data.get('training_window_days', 90) + info.data.get('testing_window_days', 30)
            if total_days < min_window:
                raise ValueError(
                    f"Date range ({total_days} days) must be at least "
                    f"{min_window} days (training + testing windows)"
                )
        return v

    @field_validator('parameter_ranges')
    @classmethod
    def validate_parameter_ranges(cls, v):
        """Validate parameter ranges format and values"""
        for param_name, range_tuple in v.items():
            if len(range_tuple) != 3:
                raise ValueError(
                    f"Parameter range for '{param_name}' must be (min, max, step)"
                )

            min_val, max_val, step = range_tuple
            if min_val >= max_val:
                raise ValueError(
                    f"Parameter '{param_name}': min ({min_val}) must be < max ({max_val})"
                )
            if step <= 0:
                raise ValueError(
                    f"Parameter '{param_name}': step ({step}) must be positive"
                )
            if step > (max_val - min_val):
                raise ValueError(
                    f"Parameter '{param_name}': step ({step}) too large for range"
                )

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2023-01-01T00:00:00Z",
                "end_date": "2024-01-01T00:00:00Z",
                "training_window_days": 90,
                "testing_window_days": 30,
                "step_size_days": 30,
                "window_type": "rolling",
                "instruments": ["EUR_USD", "GBP_USD"],
                "initial_capital": 100000.0,
                "risk_percentage": 0.02,
                "parameter_ranges": {
                    "confidence_threshold": (50.0, 90.0, 5.0),
                    "min_risk_reward": (1.5, 4.0, 0.5),
                    "vpa_threshold": (0.5, 0.8, 0.1)
                },
                "baseline_parameters": {
                    "confidence_threshold": 55.0,
                    "min_risk_reward": 1.8,
                    "vpa_threshold": 0.6
                },
                "optimization_method": "bayesian",
                "max_iterations": 100,
                "n_workers": 4
            }
        }


class WindowResult(BaseModel):
    """Results for a single walk-forward window"""

    window_index: int = Field(..., description="Window number (0-indexed)")

    # Window dates
    train_start: datetime = Field(..., description="Training period start")
    train_end: datetime = Field(..., description="Training period end")
    test_start: datetime = Field(..., description="Testing period start")
    test_end: datetime = Field(..., description="Testing period end")

    # Optimized parameters for this window
    optimized_params: Dict[str, Any] = Field(
        ...,
        description="Best parameters found during optimization"
    )

    # In-sample (training) performance
    in_sample_sharpe: float = Field(..., description="Training Sharpe ratio")
    in_sample_drawdown: float = Field(..., description="Training max drawdown %")
    in_sample_win_rate: float = Field(..., description="Training win rate")
    in_sample_total_return: float = Field(..., description="Training total return %")
    in_sample_total_trades: int = Field(..., description="Training total trades")

    # Out-of-sample (testing) performance
    out_of_sample_sharpe: float = Field(..., description="Testing Sharpe ratio")
    out_of_sample_drawdown: float = Field(..., description="Testing max drawdown %")
    out_of_sample_win_rate: float = Field(..., description="Testing win rate")
    out_of_sample_total_return: float = Field(..., description="Testing total return %")
    out_of_sample_total_trades: int = Field(..., description="Testing total trades")

    # Overfitting metrics
    overfitting_score: float = Field(
        ...,
        description="Overfitting score: (IS_sharpe - OOS_sharpe) / IS_sharpe"
    )
    performance_degradation: float = Field(
        ...,
        description="Performance degradation from in-sample to out-of-sample %"
    )

    # Optimization metadata
    total_param_combinations_tested: int = Field(
        ...,
        description="Number of parameter combinations evaluated"
    )
    optimization_time_seconds: float = Field(
        ...,
        description="Time spent optimizing this window"
    )


class EquityPoint(BaseModel):
    """Single equity curve point"""
    timestamp: datetime
    balance: float
    equity: float


class WalkForwardResult(BaseModel):
    """Complete walk-forward optimization results"""

    # Job metadata
    job_id: str = Field(..., description="Unique job identifier")

    # Configuration
    config: WalkForwardConfig = Field(..., description="Configuration used")

    # Results by window
    windows: List[WindowResult] = Field(..., description="Results for each window")

    # Aggregate metrics
    avg_in_sample_sharpe: float = Field(..., description="Average in-sample Sharpe")
    avg_out_of_sample_sharpe: float = Field(..., description="Average out-of-sample Sharpe")
    avg_overfitting_score: float = Field(..., description="Average overfitting score")
    parameter_stability_score: float = Field(
        ...,
        description="Parameter stability score (0-1, higher is better)"
    )

    # Acceptance criteria results
    acceptance_status: str = Field(
        ...,
        description="Overall validation status: PASS or FAIL"
    )
    acceptance_details: Dict[str, bool] = Field(
        ...,
        description="Detailed acceptance criteria check results"
    )
    acceptance_messages: List[str] = Field(
        default_factory=list,
        description="Human-readable messages about acceptance criteria"
    )

    # Final recommended parameters
    recommended_parameters: Dict[str, Any] = Field(
        ...,
        description="Final recommended parameters based on walk-forward analysis"
    )
    parameter_deviation_from_baseline: Dict[str, float] = Field(
        ...,
        description="Deviation of recommended params from baseline (%)"
    )

    # Visualization data
    equity_curve_optimized: List[EquityPoint] = Field(
        default_factory=list,
        description="Equity curve using optimized parameters"
    )
    equity_curve_baseline: List[EquityPoint] = Field(
        default_factory=list,
        description="Equity curve using baseline parameters"
    )
    parameter_evolution: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Parameter values across windows for stability analysis"
    )
    rolling_sharpe_ratios: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rolling Sharpe ratios (in-sample vs out-of-sample)"
    )
    overfitting_scores_trend: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Overfitting scores across windows"
    )

    # Execution metadata
    total_backtests_run: int = Field(..., description="Total backtests executed")
    total_windows: int = Field(..., description="Total walk-forward windows")
    execution_time_seconds: float = Field(..., description="Total execution time")
    started_at: datetime = Field(..., description="Job start time")
    completed_at: datetime = Field(..., description="Job completion time")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "wf-20251008-123456",
                "acceptance_status": "PASS",
                "avg_out_of_sample_sharpe": 1.25,
                "avg_overfitting_score": 0.22,
                "parameter_stability_score": 0.85,
                "total_windows": 12,
                "total_backtests_run": 1200,
                "execution_time_seconds": 420.5
            }
        }


class OptimizationJob(BaseModel):
    """Represents a walk-forward optimization job"""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(
        ...,
        description="Job status: pending, running, completed, failed"
    )
    config: WalkForwardConfig = Field(..., description="Job configuration")

    # Progress tracking
    progress: float = Field(default=0.0, description="Progress percentage (0-100)")
    current_window: int = Field(default=0, description="Current window being processed")
    total_windows: int = Field(..., description="Total windows to process")

    # Timing
    created_at: datetime = Field(..., description="Job creation time")
    started_at: Optional[datetime] = Field(default=None, description="Job start time")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion time")
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )

    # Results (populated when completed)
    result: Optional[WalkForwardResult] = Field(
        default=None,
        description="Results (available when status=completed)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message (if status=failed)"
    )
