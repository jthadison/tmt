"""
API routes for historical trades and signals data.

Provides endpoints for querying trade history, signals, and filtering
by various parameters like session, pattern, date range, etc.
"""

import logging
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from .database import TradeRepository, SignalRepository, get_database_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["history"])


# Response models
class TradeResponse(BaseModel):
    """Trade response model"""
    trade_id: str
    signal_id: Optional[str]
    account_id: str
    symbol: str
    direction: str
    entry_time: datetime
    entry_price: Decimal
    exit_time: Optional[datetime]
    exit_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    position_size: Decimal
    pnl: Optional[Decimal]
    pnl_percentage: Optional[Decimal]
    session: Optional[str]
    pattern_type: Optional[str]
    confidence_score: Optional[Decimal]
    risk_reward_ratio: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SignalResponse(BaseModel):
    """Signal response model"""
    signal_id: str
    symbol: str
    timeframe: Optional[str]
    signal_type: str
    confidence: Decimal
    entry_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    session: Optional[str]
    pattern_type: Optional[str]
    generated_at: datetime
    executed: bool
    execution_status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedTradesResponse(BaseModel):
    """Paginated trades response"""
    data: List[TradeResponse]
    total: int
    limit: int
    offset: int
    error: Optional[str] = None
    correlation_id: str = Field(default_factory=lambda: f"corr_{datetime.utcnow().timestamp()}")


class PaginatedSignalsResponse(BaseModel):
    """Paginated signals response"""
    data: List[SignalResponse]
    total: int
    limit: int
    offset: int
    error: Optional[str] = None
    correlation_id: str = Field(default_factory=lambda: f"corr_{datetime.utcnow().timestamp()}")


class SingleTradeResponse(BaseModel):
    """Single trade response"""
    data: Optional[TradeResponse]
    error: Optional[str] = None
    correlation_id: str = Field(default_factory=lambda: f"corr_{datetime.utcnow().timestamp()}")


# Dependency to get repositories
async def get_trade_repository() -> TradeRepository:
    """Get trade repository dependency"""
    try:
        db_engine = await get_database_engine()
        return TradeRepository(db_engine.session_factory)
    except Exception as e:
        logger.error(f"Failed to get trade repository: {e}")
        raise HTTPException(status_code=503, detail="Database not available")


async def get_signal_repository() -> SignalRepository:
    """Get signal repository dependency"""
    try:
        db_engine = await get_database_engine()
        return SignalRepository(db_engine.session_factory)
    except Exception as e:
        logger.error(f"Failed to get signal repository: {e}")
        raise HTTPException(status_code=503, detail="Database not available")


@router.get("/trades/history", response_model=PaginatedTradesResponse)
async def get_trade_history(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601 format)"),
    symbol: Optional[str] = Query(None, description="Trading symbol filter"),
    session: Optional[str] = Query(None, description="Trading session filter"),
    pattern_type: Optional[str] = Query(None, description="Pattern type filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("entry_time", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    trade_repo: TradeRepository = Depends(get_trade_repository),
):
    """
    Get trade history with filtering and pagination.

    Args:
        start_date: Filter trades after this date
        end_date: Filter trades before this date
        symbol: Filter by trading symbol
        session: Filter by trading session (TOKYO, LONDON, NY, SYDNEY, OVERLAP)
        pattern_type: Filter by pattern type
        limit: Maximum results to return
        offset: Pagination offset
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)
        trade_repo: Trade repository dependency

    Returns:
        PaginatedTradesResponse: Paginated list of trades
    """
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Get trades based on filters
        if session:
            trades = await trade_repo.get_trades_by_session(session, start_dt, end_dt)
        elif pattern_type:
            trades = await trade_repo.get_trades_by_pattern(pattern_type, start_dt, end_dt)
        else:
            trades = await trade_repo.get_recent_trades(limit=limit + offset)

        # Apply additional filters if needed
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]

        # Apply pagination
        total = len(trades)
        trades = trades[offset : offset + limit]

        # Convert to response models
        trade_responses = [TradeResponse.model_validate(trade) for trade in trades]

        return PaginatedTradesResponse(
            data=trade_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/{trade_id}", response_model=SingleTradeResponse)
async def get_trade_by_id(
    trade_id: str,
    trade_repo: TradeRepository = Depends(get_trade_repository),
):
    """
    Get a specific trade by ID.

    Args:
        trade_id: Unique trade identifier
        trade_repo: Trade repository dependency

    Returns:
        SingleTradeResponse: Trade details or 404 if not found
    """
    try:
        trade = await trade_repo.get_trade_by_id(trade_id)

        if not trade:
            raise HTTPException(status_code=404, detail=f"Trade not found: {trade_id}")

        trade_response = TradeResponse.model_validate(trade)

        return SingleTradeResponse(data=trade_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trade by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/history", response_model=PaginatedSignalsResponse)
async def get_signal_history(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601 format)"),
    symbol: Optional[str] = Query(None, description="Trading symbol filter"),
    executed: Optional[bool] = Query(None, description="Filter by execution status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    signal_repo: SignalRepository = Depends(get_signal_repository),
):
    """
    Get signal history with filtering and pagination.

    Args:
        start_date: Filter signals after this date
        end_date: Filter signals before this date
        symbol: Filter by trading symbol
        executed: Filter by execution status
        limit: Maximum results to return
        offset: Pagination offset
        signal_repo: Signal repository dependency

    Returns:
        PaginatedSignalsResponse: Paginated list of signals
    """
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Get signals based on filters
        if executed is not None:
            signals = await signal_repo.get_signals_by_status(executed)
        elif symbol:
            signals = await signal_repo.get_signals_by_symbol(symbol, start_dt, end_dt)
        else:
            signals = await signal_repo.get_recent_signals(limit=limit + offset)

        # Apply date filters if not already applied
        if start_dt or end_dt:
            filtered_signals = []
            for sig in signals:
                if start_dt and sig.generated_at < start_dt:
                    continue
                if end_dt and sig.generated_at > end_dt:
                    continue
                filtered_signals.append(sig)
            signals = filtered_signals

        # Apply pagination
        total = len(signals)
        signals = signals[offset : offset + limit]

        # Convert to response models
        signal_responses = [SignalResponse.model_validate(signal) for signal in signals]

        return PaginatedSignalsResponse(
            data=signal_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error fetching signal history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
