"""
Backtesting Data Models - Story 11.2

Pydantic models for backtest configuration, results, and related data structures.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal


class TradingSession(str, Enum):
    """Trading session enumeration"""
    SYDNEY = "sydney"
    TOKYO = "tokyo"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP = "overlap"


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class BacktestConfig(BaseModel):
    """
    Backtest configuration model

    Defines all parameters needed to run a backtest including:
    - Date range and instruments
    - Initial capital and risk settings
    - Trading parameters (confidence thresholds, risk-reward ratios)
    - Session-specific parameter overrides
    - Execution settings (slippage model, timeframe)
    """

    # Date range
    start_date: datetime = Field(..., description="Backtest start date (UTC)")
    end_date: datetime = Field(..., description="Backtest end date (UTC)")

    # Instruments to backtest
    instruments: List[str] = Field(
        ...,
        description="Trading instruments (e.g., ['EUR_USD', 'GBP_USD'])",
        min_length=1
    )

    # Capital settings
    initial_capital: float = Field(
        default=100000.0,
        description="Starting balance in account currency",
        gt=0
    )
    risk_percentage: float = Field(
        default=0.02,
        description="Risk per trade as decimal (0.02 = 2%)",
        gt=0,
        le=0.1  # Max 10% risk per trade
    )

    # Trading parameters (universal mode)
    parameters: Dict[str, Any] = Field(
        ...,
        description="Universal trading parameters"
    )

    # Session-specific parameters (optional)
    session_parameters: Optional[Dict[TradingSession, Dict[str, Any]]] = Field(
        default=None,
        description="Session-specific parameter overrides"
    )

    # Execution settings
    slippage_model: str = Field(
        default="historical",
        description="Slippage calculation method: 'historical', 'fixed', 'percentage'"
    )
    timeframe: str = Field(
        default="H1",
        description="Analysis timeframe (H1, H4, D1)"
    )

    # Performance optimization
    enable_parallel: bool = Field(
        default=False,
        description="Enable parallel processing for multi-instrument backtests"
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
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError("end_date must be after start_date")
        return v

    def __repr__(self) -> str:
        """Custom repr to prevent recursion in logging"""
        return (
            f"BacktestConfig(start={self.start_date.date()}, "
            f"end={self.end_date.date()}, "
            f"instruments={self.instruments}, "
            f"capital={self.initial_capital})"
        )

    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v):
        """Validate required parameters are present"""
        required = ['confidence_threshold', 'min_risk_reward']
        for param in required:
            if param not in v:
                raise ValueError(f"Missing required parameter: {param}")

        # Validate ranges
        if not (0 <= v['confidence_threshold'] <= 100):
            raise ValueError("confidence_threshold must be between 0 and 100")
        if v['min_risk_reward'] <= 0:
            raise ValueError("min_risk_reward must be positive")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2023-01-01T00:00:00Z",
                "end_date": "2024-01-01T00:00:00Z",
                "instruments": ["EUR_USD", "GBP_USD"],
                "initial_capital": 100000.0,
                "risk_percentage": 0.02,
                "parameters": {
                    "confidence_threshold": 55.0,
                    "min_risk_reward": 1.8,
                    "max_risk_reward": 3.5
                },
                "session_parameters": {
                    "tokyo": {
                        "confidence_threshold": 68.0,
                        "min_risk_reward": 2.6
                    },
                    "london": {
                        "confidence_threshold": 66.0,
                        "min_risk_reward": 2.5
                    }
                },
                "slippage_model": "historical",
                "timeframe": "H1"
            }
        }


class Trade(BaseModel):
    """
    Individual trade record

    Captures all details of a trade execution including:
    - Entry and exit timing and prices
    - Stop loss and take profit levels
    - P&L calculation
    - Signal metadata for analysis
    """

    # Trade identification
    trade_id: str = Field(..., description="Unique trade identifier")

    # Timing
    entry_time: datetime = Field(..., description="Trade entry timestamp (UTC)")
    exit_time: Optional[datetime] = Field(None, description="Trade exit timestamp (UTC)")

    # Instrument and direction
    symbol: str = Field(..., description="Trading instrument (e.g., EUR_USD)")
    trade_type: str = Field(..., description="Trade direction: 'long' or 'short'")

    # Prices
    entry_price: float = Field(..., description="Actual entry price", gt=0)
    exit_price: Optional[float] = Field(None, description="Actual exit price", gt=0)
    stop_loss: float = Field(..., description="Stop loss price", gt=0)
    take_profit: float = Field(..., description="Take profit price", gt=0)

    # Position sizing
    units: float = Field(..., description="Position size in units", gt=0)
    risk_amount: float = Field(..., description="Dollar risk on trade", gt=0)

    # Performance
    realized_pnl: Optional[float] = Field(None, description="Realized P&L in dollars")
    realized_pnl_pips: Optional[float] = Field(None, description="Realized P&L in pips")
    risk_reward_achieved: Optional[float] = Field(None, description="Actual R:R achieved")

    # Slippage
    entry_slippage_pips: float = Field(default=0.0, description="Entry slippage in pips")
    exit_slippage_pips: float = Field(default=0.0, description="Exit slippage in pips")

    # Signal metadata
    signal_confidence: float = Field(..., description="Signal confidence score (0-100)", ge=0, le=100)
    wyckoff_phase: Optional[str] = Field(None, description="Wyckoff market phase")
    pattern_type: Optional[str] = Field(None, description="Pattern that triggered signal")
    trading_session: TradingSession = Field(..., description="Trading session when entered")

    # Exit reason
    exit_reason: Optional[str] = Field(
        None,
        description="Exit reason: 'stop_loss', 'take_profit', 'time_exit', 'manual'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trade_id": "trade_001",
                "entry_time": "2023-06-15T14:30:00Z",
                "exit_time": "2023-06-16T10:15:00Z",
                "symbol": "EUR_USD",
                "trade_type": "long",
                "entry_price": 1.0850,
                "exit_price": 1.0920,
                "stop_loss": 1.0820,
                "take_profit": 1.0910,
                "units": 10000.0,
                "risk_amount": 300.0,
                "realized_pnl": 700.0,
                "realized_pnl_pips": 70.0,
                "risk_reward_achieved": 2.33,
                "signal_confidence": 72.5,
                "pattern_type": "spring",
                "trading_session": "london",
                "exit_reason": "take_profit"
            }
        }


class EquityPoint(BaseModel):
    """
    Single point on equity curve

    Tracks account balance at a specific timestamp
    """

    timestamp: datetime = Field(..., description="Timestamp (UTC)")
    balance: float = Field(..., description="Account balance", ge=0)
    equity: float = Field(..., description="Total equity (balance + unrealized P&L)", ge=0)
    unrealized_pnl: float = Field(default=0.0, description="Unrealized P&L from open positions")
    drawdown: float = Field(default=0.0, description="Drawdown from peak", le=0)
    drawdown_pct: float = Field(default=0.0, description="Drawdown percentage", le=0)


class SessionMetrics(BaseModel):
    """
    Performance metrics for a specific trading session
    """

    session: TradingSession = Field(..., description="Trading session")

    # Trade statistics
    total_trades: int = Field(default=0, description="Total trades in session", ge=0)
    winning_trades: int = Field(default=0, description="Winning trades", ge=0)
    losing_trades: int = Field(default=0, description="Losing trades", ge=0)

    # Performance metrics
    win_rate: float = Field(default=0.0, description="Win rate (0-1)", ge=0, le=1)
    avg_risk_reward: float = Field(default=0.0, description="Average risk-reward achieved")
    total_pnl: float = Field(default=0.0, description="Total P&L for session")
    profit_factor: float = Field(default=0.0, description="Profit factor", ge=0)

    # Risk metrics
    max_drawdown: float = Field(default=0.0, description="Maximum drawdown", le=0)
    sharpe_ratio: float = Field(default=0.0, description="Sharpe ratio")


class InstrumentMetrics(BaseModel):
    """
    Performance metrics for a specific instrument
    """

    instrument: str = Field(..., description="Trading instrument")

    # Trade statistics
    total_trades: int = Field(default=0, description="Total trades for instrument", ge=0)
    winning_trades: int = Field(default=0, description="Winning trades", ge=0)
    losing_trades: int = Field(default=0, description="Losing trades", ge=0)

    # Performance metrics
    win_rate: float = Field(default=0.0, description="Win rate (0-1)", ge=0, le=1)
    avg_risk_reward: float = Field(default=0.0, description="Average risk-reward achieved")
    total_pnl: float = Field(default=0.0, description="Total P&L for instrument")
    total_pnl_pips: float = Field(default=0.0, description="Total P&L in pips")
    profit_factor: float = Field(default=0.0, description="Profit factor", ge=0)

    # Risk metrics
    max_consecutive_losses: int = Field(default=0, description="Max consecutive losses", ge=0)
    avg_trade_duration_hours: float = Field(default=0.0, description="Average trade duration in hours", ge=0)


class BacktestResult(BaseModel):
    """
    Complete backtest results

    Contains all performance metrics, trade list, equity curve,
    and breakdown by session and instrument.
    """

    # Overall performance metrics
    sharpe_ratio: float = Field(..., description="Sharpe ratio (annualized)")
    sortino_ratio: float = Field(..., description="Sortino ratio (annualized)")
    max_drawdown: float = Field(..., description="Maximum drawdown (negative)", le=0)
    max_drawdown_pct: float = Field(..., description="Maximum drawdown percentage (negative)", le=0)

    # Return metrics
    total_return: float = Field(..., description="Total return (decimal)")
    total_return_pct: float = Field(..., description="Total return percentage")
    cagr: float = Field(..., description="Compound Annual Growth Rate")
    calmar_ratio: float = Field(..., description="CAGR / abs(max_drawdown)")

    # Risk metrics
    win_rate: float = Field(..., description="Overall win rate (0-1)", ge=0, le=1)
    profit_factor: float = Field(..., description="Gross profit / gross loss", ge=0)
    recovery_factor: float = Field(..., description="Net profit / abs(max_drawdown)")

    # Trade statistics
    total_trades: int = Field(..., description="Total number of trades", ge=0)
    winning_trades: int = Field(..., description="Number of winning trades", ge=0)
    losing_trades: int = Field(..., description="Number of losing trades", ge=0)
    avg_risk_reward: float = Field(..., description="Average risk-reward achieved")

    # Expected value
    expectancy: float = Field(..., description="Average profit per trade")
    expectancy_pct: float = Field(..., description="Average profit per trade as % of risk")

    # Detailed data
    trades: List[Trade] = Field(default_factory=list, description="Complete trade list")
    equity_curve: List[EquityPoint] = Field(default_factory=list, description="Equity curve data")

    # Breakdowns
    session_performance: Dict[str, SessionMetrics] = Field(
        default_factory=dict,
        description="Performance by trading session"
    )
    instrument_performance: Dict[str, InstrumentMetrics] = Field(
        default_factory=dict,
        description="Performance by instrument"
    )

    # Backtest metadata
    config: BacktestConfig = Field(..., description="Backtest configuration used")
    execution_time_seconds: float = Field(..., description="Backtest execution time", gt=0)
    bars_processed: int = Field(..., description="Total bars processed", ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "sharpe_ratio": 1.52,
                "sortino_ratio": 2.14,
                "max_drawdown": -0.12,
                "max_drawdown_pct": -12.0,
                "total_return": 0.24,
                "total_return_pct": 24.0,
                "cagr": 0.21,
                "calmar_ratio": 1.75,
                "win_rate": 0.58,
                "profit_factor": 1.85,
                "recovery_factor": 2.0,
                "total_trades": 145,
                "winning_trades": 84,
                "losing_trades": 61,
                "avg_risk_reward": 2.1,
                "expectancy": 165.52,
                "expectancy_pct": 0.55,
                "execution_time_seconds": 45.3,
                "bars_processed": 8760
            }
        }

    def __repr__(self) -> str:
        """Custom repr to prevent recursion in logging"""
        return (
            f"BacktestResult(trades={self.total_trades}, "
            f"sharpe={self.sharpe_ratio:.2f}, "
            f"return={self.total_return_pct:.1f}%, "
            f"time={self.execution_time_seconds:.1f}s)"
        )
