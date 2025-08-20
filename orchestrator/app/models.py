"""
Data models for the Trading System Orchestrator
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field


class TradeSignal(BaseModel):
    """Trading signal from market analysis agent"""
    id: str
    instrument: str
    direction: Literal["long", "short"]
    confidence: float = Field(ge=0.0, le=1.0)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    timeframe: Optional[str] = None
    pattern_type: Optional[str] = None
    market_state: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TradeResult(BaseModel):
    """Result of trade execution"""
    success: bool
    signal_id: Optional[str] = None
    trade_id: Optional[str] = None
    executed_price: Optional[float] = None
    executed_units: Optional[float] = None
    pnl: Optional[float] = None
    commission: Optional[float] = None
    financing: Optional[float] = None
    execution_time: datetime = Field(default_factory=datetime.utcnow)
    message: Optional[str] = None
    account_id: Optional[str] = None


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class AgentInfo(BaseModel):
    """Agent information and status"""
    agent_id: str
    agent_type: str
    endpoint: str
    status: AgentStatus
    last_seen: datetime
    capabilities: List[str] = Field(default_factory=list)
    version: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AccountStatus(BaseModel):
    """OANDA account status"""
    account_id: str
    account_name: Optional[str] = None
    currency: str
    balance: float
    equity: float
    margin_used: float
    margin_available: float
    unrealized_pnl: float
    open_positions: int
    open_orders: int
    trading_enabled: bool = True
    last_update: datetime
    health_status: Literal["healthy", "warning", "danger"] = "healthy"


class AccountInfo(BaseModel):
    """Basic account information"""
    account_id: str
    account_name: str
    currency: str
    account_type: Literal["practice", "live"]
    trading_enabled: bool
    created_date: Optional[datetime] = None


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker system status"""
    overall_status: Literal["closed", "open", "half_open"]
    account_breakers: Dict[str, str] = Field(default_factory=dict)
    system_breakers: Dict[str, str] = Field(default_factory=dict)
    triggers_today: int = 0
    last_trigger: Optional[datetime] = None
    can_trade: bool = True


class SystemStatus(BaseModel):
    """Overall system status"""
    running: bool
    trading_enabled: bool
    uptime_seconds: int
    connected_agents: int
    total_agents: int
    circuit_breaker_status: CircuitBreakerStatus
    oanda_connection: bool
    last_update: datetime
    system_health: Literal["healthy", "degraded", "unhealthy"] = "healthy"


class SystemMetrics(BaseModel):
    """System performance metrics"""
    signals_processed: int = 0
    trades_executed: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    average_latency: float = 0.0
    uptime_seconds: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class EmergencyStopRequest(BaseModel):
    """Emergency stop request"""
    reason: str
    force_close_positions: bool = False
    initiated_by: Optional[str] = None


class SystemEvent(BaseModel):
    """System event record"""
    event_id: str
    event_type: str
    timestamp: datetime
    source: str
    severity: Literal["info", "warning", "error", "critical"]
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


class HealthCheckResult(BaseModel):
    """Health check result"""
    component: str
    status: Literal["healthy", "degraded", "unhealthy"]
    response_time_ms: float
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PerformanceMetrics(BaseModel):
    """Performance metrics for a specific component"""
    component: str
    requests_per_second: float = 0.0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TradingParameters(BaseModel):
    """Optimized trading parameters"""
    position_size: float
    stop_loss_pips: Optional[float] = None
    take_profit_pips: Optional[float] = None
    risk_amount: float
    max_risk_percent: float = 0.02
    confidence_threshold: float = 0.75
    account_allocation: Dict[str, float] = Field(default_factory=dict)


class DisagreementResult(BaseModel):
    """Result from disagreement engine"""
    approved: bool
    timing_adjustments: Dict[str, int] = Field(default_factory=dict)  # Account -> delay in seconds
    position_adjustments: Dict[str, float] = Field(default_factory=dict)  # Account -> size multiplier
    correlation_score: float
    reason: Optional[str] = None


class MarketCondition(BaseModel):
    """Current market condition assessment"""
    regime: Literal["trending", "ranging", "breakout", "volatile"]
    volatility_level: Literal["low", "medium", "high"]
    session: Literal["asian", "london", "newyork", "overlap"]
    news_risk: Literal["low", "medium", "high"]
    trading_allowed: bool = True
    confidence: float = Field(ge=0.0, le=1.0)


class PositionInfo(BaseModel):
    """Current position information"""
    position_id: str
    account_id: str
    instrument: str
    direction: Literal["long", "short"]
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    open_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class OrderInfo(BaseModel):
    """Order information"""
    order_id: str
    account_id: str
    instrument: str
    direction: Literal["long", "short"]
    size: float
    order_type: Literal["market", "limit", "stop"]
    price: Optional[float] = None
    status: Literal["pending", "filled", "cancelled", "rejected"]
    created_time: datetime
    filled_time: Optional[datetime] = None


class AgentCapability(BaseModel):
    """Agent capability definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    execution_time_estimate: float  # Seconds


class AgentRegistration(BaseModel):
    """Agent registration request"""
    agent_id: str
    agent_type: str
    version: str
    endpoint: str
    capabilities: List[AgentCapability]
    health_check_endpoint: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemConfiguration(BaseModel):
    """System configuration"""
    trading_hours: Dict[str, Any] = Field(default_factory=dict)
    risk_limits: Dict[str, float] = Field(default_factory=dict)
    circuit_breaker_thresholds: Dict[str, float] = Field(default_factory=dict)
    agent_timeouts: Dict[str, float] = Field(default_factory=dict)
    oanda_settings: Dict[str, Any] = Field(default_factory=dict)


class BacktestRequest(BaseModel):
    """Backtest request"""
    strategy_id: str
    start_date: datetime
    end_date: datetime
    instruments: List[str]
    initial_balance: float = 10000.0
    parameters: Dict[str, Any] = Field(default_factory=dict)


class BacktestResult(BaseModel):
    """Backtest result"""
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_balance: float
    final_balance: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: float
    trades: List[Dict[str, Any]] = Field(default_factory=list)