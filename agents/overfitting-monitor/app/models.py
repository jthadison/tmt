"""
Data models for Overfitting Monitor - Story 11.4
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class AlertLevel(str, Enum):
    """Alert severity level"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class OverfittingScore(BaseModel):
    """Overfitting score data point"""

    time: datetime = Field(..., description="Timestamp of score calculation")
    score: float = Field(..., description="Overfitting score (0-1+)", ge=0)
    avg_deviation: float = Field(..., description="Average parameter deviation")
    max_deviation: float = Field(..., description="Maximum parameter deviation")
    session_deviations: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-session deviation scores"
    )
    alert_level: AlertLevel = Field(..., description="Alert level for this score")

    class Config:
        json_schema_extra = {
            "example": {
                "time": "2025-10-09T12:00:00Z",
                "score": 0.25,
                "avg_deviation": 0.18,
                "max_deviation": 0.32,
                "session_deviations": {
                    "London": 0.32,
                    "NY": 0.25,
                    "Tokyo": 0.12
                },
                "alert_level": "normal"
            }
        }


class ParameterDrift(BaseModel):
    """Parameter drift tracking"""

    time: datetime = Field(..., description="Timestamp")
    parameter_name: str = Field(..., description="Parameter name")
    current_value: float = Field(..., description="Current parameter value")
    baseline_value: float = Field(..., description="Baseline parameter value")
    deviation_pct: float = Field(..., description="Deviation from baseline %")
    drift_7d_pct: float = Field(..., description="7-day drift percentage")
    drift_30d_pct: float = Field(..., description="30-day drift percentage")


class PerformanceMetrics(BaseModel):
    """Live trading performance metrics"""

    time: datetime = Field(..., description="Timestamp")
    live_sharpe: float = Field(..., description="Live 7-day Sharpe ratio")
    backtest_sharpe: float = Field(..., description="Expected backtest Sharpe")
    sharpe_ratio: float = Field(..., description="Live / Backtest ratio")
    live_win_rate: float = Field(..., description="Live win rate %")
    backtest_win_rate: float = Field(..., description="Expected win rate %")
    live_profit_factor: float = Field(..., description="Live profit factor")
    backtest_profit_factor: float = Field(..., description="Expected profit factor")
    degradation_score: float = Field(
        ...,
        description="Overall performance degradation (0-1, higher = worse)"
    )


class OverfittingAlert(BaseModel):
    """Overfitting alert"""

    id: str = Field(..., description="Alert ID")
    timestamp: datetime = Field(..., description="Alert timestamp")
    severity: AlertLevel = Field(..., description="Alert severity")
    metric: str = Field(..., description="Metric that triggered alert")
    value: float = Field(..., description="Current metric value")
    threshold: float = Field(..., description="Threshold value")
    message: str = Field(..., description="Alert message")
    recommendation: Optional[str] = Field(
        default=None,
        description="Recommended action"
    )
    acknowledged: bool = Field(default=False, description="Alert acknowledged")
    acknowledged_at: Optional[datetime] = Field(
        default=None,
        description="Acknowledgment timestamp"
    )


class MonitoringStatus(BaseModel):
    """Current monitoring status"""

    current_overfitting_score: float = Field(..., description="Current score")
    alert_level: AlertLevel = Field(..., description="Current alert level")
    active_alerts: int = Field(..., description="Number of active alerts")
    parameter_drift_count: int = Field(
        ...,
        description="Number of parameters exceeding drift threshold"
    )
    performance_degradation_detected: bool = Field(
        ...,
        description="Whether performance degradation detected"
    )
    last_calculation: datetime = Field(..., description="Last score calculation time")
    monitoring_healthy: bool = Field(..., description="Monitoring system health")


class OverfittingHistory(BaseModel):
    """Historical overfitting data"""

    start_date: datetime = Field(..., description="Start of period")
    end_date: datetime = Field(..., description="End of period")
    scores: List[OverfittingScore] = Field(..., description="Overfitting scores")
    avg_score: float = Field(..., description="Average score for period")
    max_score: float = Field(..., description="Maximum score in period")
    alerts_count: int = Field(..., description="Total alerts in period")


class ParameterComparison(BaseModel):
    """Current vs baseline parameter comparison"""

    current_parameters: Dict[str, Any] = Field(
        ...,
        description="Current active parameters"
    )
    baseline_parameters: Dict[str, Any] = Field(
        ...,
        description="Universal baseline parameters"
    )
    deviations: Dict[str, float] = Field(
        ...,
        description="Deviation percentages per parameter"
    )
    overfitting_risk: str = Field(
        ...,
        description="Overall risk assessment: LOW, MEDIUM, HIGH, CRITICAL"
    )
