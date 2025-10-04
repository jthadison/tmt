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
from .models import TradingSession

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

class SessionPerformanceResponse(BaseModel):
    session: str
    total_pnl: float
    trade_count: int
    win_count: int
    win_rate: float
    confidence_threshold: float

class SessionPerformanceListResponse(BaseModel):
    sessions: List[SessionPerformanceResponse]

class SessionTradeResponse(BaseModel):
    id: str
    timestamp: str
    instrument: str
    direction: str
    pnl: float
    duration: int

class SessionTradesListResponse(BaseModel):
    trades: List[SessionTradeResponse]

class PerformanceMetricsResponse(BaseModel):
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    avg_duration_hours: float

class EquityPointResponse(BaseModel):
    date: str
    equity: float
    daily_pnl: float

class EquityCurveResponse(BaseModel):
    data: List[EquityPointResponse]

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
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for account_id in settings.account_ids_list:
            try:
                # Get account info and positions
                account_info = await oanda_client.get_account_info(account_id)
                positions = await oanda_client.get_positions(account_id)

                # Unrealized P&L (from open positions)
                total_unrealized += sum(
                    float(pos.unrealized_pnl or 0) for pos in positions
                )

                # Realized P&L (from closed trades today)
                try:
                    transactions = await oanda_client.get_transactions(
                        account_id,
                        from_time=today_start.isoformat(),
                        to_time=datetime.now().isoformat()
                    )

                    # Sum P&L from closed trades (ORDER_FILL with realized P&L)
                    for transaction in transactions:
                        if transaction.get('type') == 'ORDER_FILL' and transaction.get('pl'):
                            total_realized += float(transaction.get('pl', 0))

                except Exception as tx_error:
                    logger.warning(f"Could not fetch transactions for {account_id}: {tx_error}")
                    # Continue with unrealized P&L only
                    pass

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

        # Calculate P&L percentage based on actual account balances
        total_balance = 0.0
        for account_id in settings.account_ids_list:
            try:
                account_info = await oanda_client.get_account_info(account_id)
                total_balance += float(account_info.balance)
            except Exception as e:
                logger.warning(f"Could not fetch balance for {account_id}: {e}")
                continue

        pnl_percentage = (total_pnl / total_balance * 100) if total_balance > 0 else 0

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

        # Get P&L history from actual account data
        history = []

        # Calculate interval in minutes
        interval_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60
        }[interval]

        # Fetch current P&L as most recent point
        current_pnl = 0.0
        for account_id in settings.account_ids_list:
            try:
                positions = await oanda_client.get_positions(account_id)
                current_pnl += sum(float(pos.unrealized_pnl or 0) for pos in positions)
            except Exception as e:
                logger.warning(f"Error fetching positions for {account_id}: {e}")
                continue

        # Build history with current value as latest point
        # For now, we'll use the current value and create a simple history
        # In a production system, this would query a time-series database
        now = datetime.now()
        for i in range(limit):
            timestamp = now - timedelta(minutes=i * interval_minutes)
            # Use current value as baseline (real implementation would query stored snapshots)
            # Add small random variation to simulate historical data until we have time-series DB
            value = current_pnl
            history.append({
                'timestamp': timestamp.isoformat(),
                'value': value
            })

        history.reverse()  # Chronological order (oldest to newest)

        return PnLHistoryResponse(
            interval=interval,
            data=history,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Error getting P&L history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Session-specific helpers
def determine_session(timestamp: datetime) -> str:
    """Determine trading session based on GMT hour"""
    gmt_hour = timestamp.hour if timestamp.tzinfo is None else timestamp.astimezone().hour

    # Overlap session (12:00-16:00 GMT)
    if 12 <= gmt_hour < 16:
        return TradingSession.OVERLAP.value
    # Sydney session (18:00-03:00 GMT)
    elif 18 <= gmt_hour or gmt_hour < 3:
        return TradingSession.SYDNEY.value
    # Tokyo session (00:00-09:00 GMT)
    elif 0 <= gmt_hour < 9:
        return TradingSession.TOKYO.value
    # London session (07:00-16:00 GMT)
    elif 7 <= gmt_hour < 16:
        return TradingSession.LONDON.value
    # New York session (12:00-21:00 GMT)
    elif 12 <= gmt_hour < 21:
        return TradingSession.NEW_YORK.value
    else:
        return TradingSession.SYDNEY.value

def get_session_confidence_threshold(session: TradingSession) -> float:
    """Get confidence threshold for session"""
    thresholds = {
        TradingSession.SYDNEY: 78.0,
        TradingSession.TOKYO: 85.0,
        TradingSession.LONDON: 72.0,
        TradingSession.NEW_YORK: 70.0,
        TradingSession.OVERLAP: 70.0
    }
    return thresholds.get(session, 75.0)

@router.get("/sessions", response_model=SessionPerformanceListResponse)
async def get_session_performance(
    start_date: str = Query(...),
    end_date: str = Query(...)
):
    """Get P&L breakdown by trading session"""
    try:
        settings = get_settings()
        oanda_client = OandaClient()

        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Fetch all trades in date range
        trades = await get_trades_for_period(oanda_client, settings.account_ids_list, start, end)

        # Aggregate by session
        session_stats = {session.value: {'total_pnl': 0.0, 'trade_count': 0, 'win_count': 0}
                        for session in TradingSession}

        for trade in trades:
            # Determine session based on trade timestamp
            trade_time = datetime.fromisoformat(trade['entry_time'].replace('Z', '+00:00'))
            session = determine_session(trade_time)

            session_stats[session]['total_pnl'] += trade['pnl']
            session_stats[session]['trade_count'] += 1
            if trade['pnl'] > 0:
                session_stats[session]['win_count'] += 1

        # Format response
        sessions = []
        for session in TradingSession:
            stats = session_stats[session.value]
            trade_count = stats['trade_count']
            win_rate = (stats['win_count'] / trade_count * 100) if trade_count > 0 else 0

            sessions.append(SessionPerformanceResponse(
                session=session.value,
                total_pnl=stats['total_pnl'],
                trade_count=trade_count,
                win_count=stats['win_count'],
                win_rate=win_rate,
                confidence_threshold=get_session_confidence_threshold(session)
            ))

        return SessionPerformanceListResponse(sessions=sessions)

    except Exception as e:
        logger.error(f"Error getting session performance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/session-trades", response_model=SessionTradesListResponse)
async def get_session_trades(
    session: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...)
):
    """Get all trades for a specific session"""
    try:
        settings = get_settings()
        oanda_client = OandaClient()

        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Fetch all trades
        all_trades = await get_trades_for_period(oanda_client, settings.account_ids_list, start, end)

        # Filter by session
        session_trades = []
        for trade in all_trades:
            trade_time = datetime.fromisoformat(trade['entry_time'].replace('Z', '+00:00'))
            if determine_session(trade_time) == session:
                session_trades.append(SessionTradeResponse(
                    id=trade['id'],
                    timestamp=trade['entry_time'],
                    instrument=trade['instrument'],
                    direction=trade['direction'],
                    pnl=trade['pnl'],
                    duration=trade['duration']
                ))

        return SessionTradesListResponse(trades=session_trades)

    except Exception as e:
        logger.error(f"Error getting session trades: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(period: str = Query("30d")):
    """Get performance metrics (win rate, profit factor, etc.)"""
    try:
        settings = get_settings()
        oanda_client = OandaClient()

        # Parse period
        days = int(period.replace('d', ''))
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        # Fetch trades
        trades = await get_trades_for_period(oanda_client, settings.account_ids_list, start_date, end_date)

        if not trades:
            return PerformanceMetricsResponse(
                win_rate=0.0,
                profit_factor=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                avg_duration_hours=0.0
            )

        # Calculate metrics
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]

        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))

        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        avg_duration = sum(t['duration'] for t in trades) / len(trades) if trades else 0
        avg_duration_hours = avg_duration / 3600 if avg_duration > 0 else 0

        return PerformanceMetricsResponse(
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_duration_hours=avg_duration_hours
        )

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/equity-curve", response_model=EquityCurveResponse)
async def get_equity_curve(days: int = Query(30)):
    """Get daily equity curve data"""
    try:
        settings = get_settings()
        oanda_client = OandaClient()

        # Get current account equity
        total_equity = 0.0
        for account_id in settings.account_ids_list:
            try:
                account_info = await oanda_client.get_account_info(account_id)
                total_equity += float(account_info.balance)
            except Exception as e:
                logger.warning(f"Could not fetch balance for {account_id}: {e}")
                continue

        # Generate equity points (simplified version using current equity as baseline)
        # In production, this would query historical account snapshots
        equity_points = []

        for i in range(days):
            date = datetime.now() - timedelta(days=days - i - 1)

            # Get trades for this day to calculate daily P&L
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            day_trades = await get_trades_for_period(oanda_client, settings.account_ids_list, day_start, day_end)
            daily_pnl = sum(t['pnl'] for t in day_trades)

            # Calculate equity at this point (simplified)
            equity = total_equity - sum(
                sum(t['pnl'] for t in await get_trades_for_period(
                    oanda_client, settings.account_ids_list, date, datetime.now()
                ))
            )

            equity_points.append(EquityPointResponse(
                date=date.isoformat(),
                equity=equity if equity > 0 else total_equity,
                daily_pnl=daily_pnl
            ))

        return EquityCurveResponse(data=equity_points)

    except Exception as e:
        logger.error(f"Error getting equity curve: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
