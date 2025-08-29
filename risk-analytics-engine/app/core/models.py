"""
Core data models for Risk Management & Portfolio Analytics Engine.

Defines fundamental data structures for risk metrics, portfolio analytics,
and compliance reporting with full type safety and validation.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReportType(str, Enum):
    """Report type enumeration."""
    DAILY_RISK = "daily_risk"
    WEEKLY_PERFORMANCE = "weekly_performance"
    MONTHLY_SUMMARY = "monthly_summary"
    COMPLIANCE_AUDIT = "compliance_audit"
    STRESS_TEST = "stress_test"
    VAR_REPORT = "var_report"


class AssetClass(str, Enum):
    """Asset class enumeration."""
    FOREX = "forex"
    EQUITIES = "equities"
    COMMODITIES = "commodities"
    INDICES = "indices"
    CRYPTO = "crypto"
    FIXED_INCOME = "fixed_income"


# Core Risk Models

class RiskMetrics(BaseModel):
    """Real-time risk metrics for an account or position."""
    
    account_id: str
    timestamp: datetime
    risk_score: float = Field(..., ge=0, le=100, description="Overall risk score 0-100")
    
    # Position Risk
    total_exposure: Decimal = Field(default=Decimal("0"))
    max_position_size: Decimal = Field(default=Decimal("0"))
    position_concentration: float = Field(default=0.0, ge=0, le=1)
    
    # Leverage and Margin
    current_leverage: Decimal = Field(default=Decimal("1"))
    max_leverage: Decimal = Field(default=Decimal("30"))
    margin_utilization: float = Field(default=0.0, ge=0, le=1)
    margin_available: Decimal = Field(default=Decimal("0"))
    
    # P&L Risk
    unrealized_pl: Decimal = Field(default=Decimal("0"))
    daily_pl: Decimal = Field(default=Decimal("0"))
    max_drawdown: Decimal = Field(default=Decimal("0"))
    var_95: Decimal = Field(default=Decimal("0"), description="95% Value at Risk")
    
    # Diversification
    correlation_risk: float = Field(default=0.0, ge=0, le=1)
    instrument_count: int = Field(default=0, ge=0)
    sector_diversification: float = Field(default=0.0, ge=0, le=1)
    
    # Risk Limits
    risk_limit_breaches: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    
    @validator('risk_score')
    def validate_risk_score(cls, v):
        return max(0, min(100, v))


class PortfolioAnalytics(BaseModel):
    """Comprehensive portfolio performance analytics."""
    
    account_id: str
    timestamp: datetime
    
    # Performance Metrics
    total_value: Decimal
    cash_balance: Decimal
    unrealized_pl: Decimal
    realized_pl: Decimal
    total_pl: Decimal
    
    # Returns
    daily_return: float = Field(default=0.0)
    weekly_return: float = Field(default=0.0)
    monthly_return: float = Field(default=0.0)
    ytd_return: float = Field(default=0.0)
    
    # Risk-Adjusted Returns
    sharpe_ratio: float = Field(default=0.0)
    sortino_ratio: float = Field(default=0.0)
    calmar_ratio: float = Field(default=0.0)
    
    # Risk Metrics
    volatility: float = Field(default=0.0, ge=0)
    max_drawdown: float = Field(default=0.0, ge=0)
    var_95: Decimal = Field(default=Decimal("0"))
    expected_shortfall: Decimal = Field(default=Decimal("0"))
    
    # Position Analytics
    total_positions: int = Field(default=0, ge=0)
    long_exposure: Decimal = Field(default=Decimal("0"))
    short_exposure: Decimal = Field(default=Decimal("0"))
    net_exposure: Decimal = Field(default=Decimal("0"))
    
    # Attribution
    performance_attribution: Dict[str, float] = Field(default_factory=dict)
    sector_allocation: Dict[str, float] = Field(default_factory=dict)
    currency_allocation: Dict[str, float] = Field(default_factory=dict)


class Position(BaseModel):
    """Individual position with risk analytics."""
    
    position_id: UUID = Field(default_factory=uuid4)
    account_id: str
    instrument: str
    asset_class: AssetClass
    
    # Position Details
    units: Decimal
    average_price: Decimal
    current_price: Decimal
    market_value: Decimal
    
    # P&L
    unrealized_pl: Decimal
    realized_pl: Decimal = Field(default=Decimal("0"))
    daily_pl: Decimal = Field(default=Decimal("0"))
    
    # Risk Metrics
    position_risk: float = Field(default=0.0, ge=0, le=100)
    var_contribution: Decimal = Field(default=Decimal("0"))
    stress_test_pl: Decimal = Field(default=Decimal("0"))
    
    # Timestamps
    opened_at: datetime
    last_updated: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_long(self) -> bool:
        return self.units > 0
    
    @property
    def is_short(self) -> bool:
        return self.units < 0
    
    @property
    def notional_value(self) -> Decimal:
        return abs(self.units * self.current_price)


class RiskAlert(BaseModel):
    """Risk alert and notification."""
    
    alert_id: UUID = Field(default_factory=uuid4)
    account_id: str
    alert_type: str
    severity: AlertSeverity
    
    # Alert Details
    title: str
    message: str
    details: Dict = Field(default_factory=dict)
    
    # Risk Context
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    affected_positions: List[str] = Field(default_factory=list)
    
    # Alert Lifecycle
    triggered_at: datetime = Field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Actions
    recommended_actions: List[str] = Field(default_factory=list)
    auto_actions_taken: List[str] = Field(default_factory=list)
    
    @property
    def is_active(self) -> bool:
        return self.resolved_at is None
    
    @property
    def duration_minutes(self) -> Optional[float]:
        if self.resolved_at:
            delta = self.resolved_at - self.triggered_at
            return delta.total_seconds() / 60
        return None


class ComplianceRecord(BaseModel):
    """Compliance and audit record."""
    
    record_id: UUID = Field(default_factory=uuid4)
    account_id: str
    record_type: str
    
    # Compliance Details
    regulation: str
    requirement: str
    status: str  # "compliant", "violation", "warning"
    
    # Details
    description: str
    severity: AlertSeverity
    risk_rating: RiskLevel
    
    # Evidence
    evidence: Dict = Field(default_factory=dict)
    supporting_data: List[str] = Field(default_factory=list)
    
    # Timestamps
    recorded_at: datetime = Field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Actions
    remediation_actions: List[str] = Field(default_factory=list)
    responsible_party: Optional[str] = None


class StressTestScenario(BaseModel):
    """Stress test scenario definition."""
    
    scenario_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    
    # Scenario Parameters
    market_shocks: Dict[str, float] = Field(default_factory=dict)  # instrument -> shock %
    volatility_multiplier: float = Field(default=1.0, gt=0)
    correlation_shift: float = Field(default=0.0, ge=-1, le=1)
    
    # Scenario Metadata
    severity: str = Field(default="moderate")  # mild, moderate, severe, extreme
    probability: float = Field(default=0.05, ge=0, le=1)
    historical_precedent: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)


class StressTestResult(BaseModel):
    """Stress test results for a portfolio."""
    
    result_id: UUID = Field(default_factory=uuid4)
    scenario_id: UUID
    account_id: str
    
    # Test Results
    base_portfolio_value: Decimal
    stressed_portfolio_value: Decimal
    total_pl_impact: Decimal
    percentage_impact: float
    
    # Position-Level Results
    position_impacts: Dict[str, Decimal] = Field(default_factory=dict)
    worst_position: Optional[str] = None
    worst_position_impact: Decimal = Field(default=Decimal("0"))
    
    # Risk Metrics
    post_stress_var: Decimal = Field(default=Decimal("0"))
    margin_call_risk: bool = Field(default=False)
    liquidity_risk: RiskLevel = Field(default=RiskLevel.LOW)
    
    # Test Metadata
    executed_at: datetime = Field(default_factory=datetime.now)
    execution_time_ms: float = Field(default=0.0)


class PerformanceAttribution(BaseModel):
    """Performance attribution analysis."""
    
    attribution_id: UUID = Field(default_factory=uuid4)
    account_id: str
    period_start: date
    period_end: date
    
    # Total Return Breakdown
    total_return: float
    
    # Attribution Sources
    asset_allocation_effect: float = Field(default=0.0)
    security_selection_effect: float = Field(default=0.0)
    interaction_effect: float = Field(default=0.0)
    currency_effect: float = Field(default=0.0)
    
    # Sector Attribution
    sector_attribution: Dict[str, float] = Field(default_factory=dict)
    
    # Currency Attribution  
    currency_attribution: Dict[str, float] = Field(default_factory=dict)
    
    # Strategy Attribution
    strategy_attribution: Dict[str, float] = Field(default_factory=dict)
    
    # Top Contributors/Detractors
    top_contributors: List[Dict[str, Union[str, float]]] = Field(default_factory=list)
    top_detractors: List[Dict[str, Union[str, float]]] = Field(default_factory=list)
    
    calculated_at: datetime = Field(default_factory=datetime.now)


# Configuration Models

class RiskLimits(BaseModel):
    """Risk limits configuration."""
    
    # Position Limits
    max_position_size: Decimal = Field(default=Decimal("100000"))
    max_positions_per_instrument: int = Field(default=3, ge=1)
    max_sector_concentration: float = Field(default=0.25, ge=0, le=1)
    
    # Leverage Limits
    max_leverage: Decimal = Field(default=Decimal("30"), gt=0)
    max_margin_utilization: float = Field(default=0.80, ge=0, le=1)
    
    # Loss Limits
    max_daily_loss: Decimal = Field(default=Decimal("1000"))
    max_weekly_loss: Decimal = Field(default=Decimal("5000"))
    max_monthly_loss: Decimal = Field(default=Decimal("15000"))
    max_drawdown: Decimal = Field(default=Decimal("10000"))
    
    # Risk Score Limits
    max_risk_score: float = Field(default=80.0, ge=0, le=100)
    risk_score_warning_threshold: float = Field(default=70.0, ge=0, le=100)
    
    # VaR Limits
    max_var_95: Decimal = Field(default=Decimal("2500"))
    var_utilization_limit: float = Field(default=0.75, ge=0, le=1)


class AnalyticsConfig(BaseModel):
    """Analytics engine configuration."""
    
    # Calculation Settings
    risk_calculation_interval_ms: int = Field(default=100, ge=50)
    portfolio_update_interval_ms: int = Field(default=1000, ge=100)
    var_confidence_level: float = Field(default=0.95, ge=0.9, le=0.99)
    var_lookback_days: int = Field(default=252, ge=30)
    
    # Performance Settings  
    performance_benchmark: str = Field(default="SPY")
    risk_free_rate: float = Field(default=0.02, ge=0)
    business_days_per_year: int = Field(default=252)
    
    # Alert Settings
    alert_cooldown_minutes: int = Field(default=5, ge=1)
    max_alerts_per_hour: int = Field(default=50, ge=1)
    auto_acknowledge_info_alerts: bool = Field(default=True)
    
    # Compliance Settings
    audit_trail_retention_years: int = Field(default=7, ge=1)
    enable_regulatory_reporting: bool = Field(default=True)
    stress_test_frequency_hours: int = Field(default=24, ge=1)