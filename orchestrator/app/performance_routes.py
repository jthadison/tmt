"""
Performance API Routes for P&L Ticker and Dashboard Integration
Provides historical P&L, trade statistics, and best/worst trade data
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from .oanda_client import OandaClient
from .config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/performance", tags=["performance"])

# Response Models
class DailyPnLResponse(BaseModel):
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    timestamp: str

class PeriodPnLResponse(BaseModel):
    period: str
    total_pnl: float
    pnl_percentage: float
    trade_count: int
    win_rate: float
    avg_pnl: float
    start_date: str
    end_date: str

class TradeInfoResponse(BaseModel):
    id: str
    account_id: str
    instrument: str
    direction: str
    pnl: float
    entry_price: float
    exit_price: float
    units: int
    entry_time: str
    exit_time: str
    duration: int

class BestWorstTradesResponse(BaseModel):
    best_trade: Optional[TradeInfoResponse]
    worst_trade: Optional[TradeInfoResponse]

class PnLHistoryResponse(BaseModel):
    interval: str
    data: List[Dict[str, Any]]
    timestamp: str

# Helper function to calculate date ranges
def get_date_range(period: str) -> tuple[datetime, datetime]:
    """Calculate start and end dates for a period"""
    end_date = datetime.now()

    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "all":
        start_date = datetime(2020, 1, 1)  # Arbitrary early date
    else:  # today
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    return start_date, end_date

# Helper function to fetch trades from OANDA
async def get_trades_for_period(
    oanda_client: OandaClient,
    account_ids: List[str],
    start_date: datetime,
    end_date: datetime
) -> List[Dict[str, Any]]:
    """Fetch all trades for the specified period from OANDA"""
    all_trades = []

    for account_id in account_ids:
        try:
            # Get transactions/trades from OANDA
            transactions = await oanda_client.get_transactions(
                account_id,
                from_time=start_date.isoformat(),
                to_time=end_date.isoformat()
            )

            # Filter for completed trades and extract P&L
            for transaction in transactions:
                if transaction.get('type') in ['ORDER_FILL', 'TRADE_CLOSE']:
                    trade = {
                        'id': transaction.get('id', ''),
                        'account_id': account_id,
                        'instrument': transaction.get('instrument', 'UNKNOWN'),
                        'direction': 'long' if float(transaction.get('units', 0)) > 0 else 'short',
                        'pnl': float(transaction.get('pl', 0)),
                        'entry_price': float(transaction.get('price', 0)),
                        'exit_price': float(transaction.get('price', 0)),
                        'units': abs(int(float(transaction.get('units', 0)))),
                        'entry_time': transaction.get('time', datetime.now().isoformat()),
                        'exit_time': transaction.get('time', datetime.now().isoformat()),
                        'duration': 0  # Calculate if we have entry/exit times
                    }
                    all_trades.append(trade)

        except Exception as e:
            logger.warning(f"Error fetching trades for account {account_id}: {e}")
            continue

    return all_trades

@router.get("/pnl/daily", response_model=DailyPnLResponse)
async def get_daily_pnl():
    """Get today's P&L breakdown (realized + unrealized)"""
    try:
        settings = get_settings()
        oanda_client = OandaClient()

        total_realized = 0.0
        total_unrealized = 0.0

        # Aggregate P&L from all OANDA accounts
        for account_id in settings.account_ids_list:
            try:
                account_info = await oanda_client.get_account_info(account_id)
                positions = await oanda_client.get_positions(account_id)

                # Realized P&L (from closed trades today)
                # Note: This is simplified - proper implementation would query transactions
                total_realized += 0  # Would need to sum closed trade P&L for today

                # Unrealized P&L (from open positions)
                total_unrealized += sum(
                    float(pos.unrealized_pnl or 0) for pos in positions
                )

            except Exception as e:
                logger.warning(f"Error fetching P&L for account {account_id}: {e}")
                continue

        return DailyPnLResponse(
            realized_pnl=total_realized,
            unrealized_pnl=total_unrealized,
            total_pnl=total_realized + total_unrealized,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Error getting daily P&L: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/pnl/period", response_model=PeriodPnLResponse)
async def get_period_pnl(period: str = Query(..., pattern="^(today|week|month|all)$")):
    """Get P&L for specified period with comparison metrics"""
    try:
        settings = get_settings()
        oanda_client = OandaClient()

        start_date, end_date = get_date_range(period)

        # Fetch trades for the period
        trades = await get_trades_for_period(
            oanda_client,
            settings.account_ids_list,
            start_date,
            end_date
        )

        # Calculate metrics
        total_pnl = sum(trade['pnl'] for trade in trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
        avg_pnl = total_pnl / len(trades) if trades else 0

        # Calculate P&L percentage (simplified - would need initial balance)
        pnl_percentage = (total_pnl / 100000) * 100  # Assuming 100k base

        return PeriodPnLResponse(
            period=period,
            total_pnl=total_pnl,
            pnl_percentage=pnl_percentage,
            trade_count=len(trades),
            win_rate=win_rate,
            avg_pnl=avg_pnl,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

    except Exception as e:
        logger.error(f"Error getting period P&L: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/trades/best-worst", response_model=BestWorstTradesResponse)
async def get_best_worst_trades(period: str = Query("today")):
    """Get best and worst performing trades for period"""
    try:
        settings = get_settings()
        oanda_client = OandaClient()

        start_date, end_date = get_date_range(period)

        # Fetch trades for the period
        trades = await get_trades_for_period(
            oanda_client,
            settings.account_ids_list,
            start_date,
            end_date
        )

        if not trades:
            return BestWorstTradesResponse(
                best_trade=None,
                worst_trade=None
            )

        # Sort by P&L
        sorted_trades = sorted(trades, key=lambda t: t['pnl'], reverse=True)

        # Convert to response models
        best_trade = TradeInfoResponse(**sorted_trades[0]) if sorted_trades else None
        worst_trade = TradeInfoResponse(**sorted_trades[-1]) if sorted_trades else None

        return BestWorstTradesResponse(
            best_trade=best_trade,
            worst_trade=worst_trade
        )

    except Exception as e:
        logger.error(f"Error getting best/worst trades: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/pnl/history", response_model=PnLHistoryResponse)
async def get_pnl_history(
    interval: str = Query("1m", pattern="^(1m|5m|15m|1h)$"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get P&L history for sparkline (last N data points)"""
    try:
        settings = get_settings()
        oanda_client = OandaClient()

        # Generate historical P&L snapshots
        # Note: This is simplified - proper implementation would query actual snapshots
        history = []
        base_pnl = 0.0

        # Get current unrealized P&L
        for account_id in settings.account_ids_list:
            try:
                positions = await oanda_client.get_positions(account_id)
                base_pnl += sum(float(pos.unrealized_pnl or 0) for pos in positions)
            except Exception as e:
                logger.warning(f"Error fetching positions for {account_id}: {e}")
                continue

        # Generate historical points (mock data for now)
        for i in range(limit):
            history.append({
                'timestamp': (datetime.now() - timedelta(minutes=i)).isoformat(),
                'value': base_pnl + (i * 5.0)  # Mock variation
            })

        history.reverse()  # Chronological order

        return PnLHistoryResponse(
            interval=interval,
            data=history,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Error getting P&L history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
