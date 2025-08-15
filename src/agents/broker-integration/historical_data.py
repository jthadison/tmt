"""
Historical Data Service
Story 8.2 - Task 4: Build historical data service
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import json
import csv
import io
from collections import defaultdict

logger = logging.getLogger(__name__)

class TimeInterval(Enum):
    ONE_MINUTE = "1M"
    FIVE_MINUTES = "5M"
    FIFTEEN_MINUTES = "15M"
    THIRTY_MINUTES = "30M"
    ONE_HOUR = "1H"
    FOUR_HOURS = "4H"
    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "M"

class TrendDirection(Enum):
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"

@dataclass
class BalanceDataPoint:
    """Single balance data point"""
    timestamp: datetime
    balance: Decimal
    unrealized_pl: Decimal
    realized_pl: Decimal
    equity: Decimal
    margin_used: Decimal
    margin_available: Decimal
    open_positions: int
    pending_orders: int
    drawdown: Optional[Decimal] = None
    
    def to_chart_data(self) -> Dict[str, Any]:
        """Convert to chart-friendly format"""
        return {
            'timestamp': int(self.timestamp.timestamp() * 1000),  # JavaScript timestamp
            'balance': float(self.balance),
            'equity': float(self.equity),
            'unrealized_pl': float(self.unrealized_pl),
            'margin_used': float(self.margin_used),
            'drawdown': float(self.drawdown) if self.drawdown else None
        }

@dataclass
class PerformanceMetrics:
    """Account performance metrics"""
    start_balance: Decimal
    end_balance: Decimal
    total_return: Decimal
    total_return_percent: Decimal
    max_drawdown: Decimal
    max_drawdown_percent: Decimal
    sharpe_ratio: Optional[Decimal]
    profit_factor: Optional[Decimal]
    win_rate: Optional[Decimal]
    average_win: Optional[Decimal]
    average_loss: Optional[Decimal]
    total_trades: int
    winning_trades: int
    losing_trades: int
    best_trade: Optional[Decimal]
    worst_trade: Optional[Decimal]
    consecutive_wins: int
    consecutive_losses: int
    trading_days: int

@dataclass
class BalanceHistoryData:
    """Complete balance history with analysis"""
    data_points: List[BalanceDataPoint]
    start_date: datetime
    end_date: datetime
    interval: TimeInterval
    metrics: PerformanceMetrics
    trend: TrendDirection
    volatility: Decimal
    
    def to_chart_format(self) -> Dict[str, Any]:
        """Convert to chart-ready format"""
        return {
            'labels': [dp.timestamp.isoformat() for dp in self.data_points],
            'datasets': [
                {
                    'label': 'Balance',
                    'data': [float(dp.balance) for dp in self.data_points],
                    'borderColor': '#2563eb',
                    'backgroundColor': '#2563eb33'
                },
                {
                    'label': 'Equity',
                    'data': [float(dp.equity) for dp in self.data_points],
                    'borderColor': '#16a34a',
                    'backgroundColor': '#16a34a33'
                }
            ],
            'chart_data': [dp.to_chart_data() for dp in self.data_points],
            'metrics': asdict(self.metrics)
        }

class HistoricalDataStore:
    """In-memory store for historical data with persistence"""
    
    def __init__(self):
        self.balance_history: Dict[str, List[BalanceDataPoint]] = defaultdict(list)
        self.max_points = 10000  # Limit memory usage
    
    def add_balance_point(self, account_id: str, point: BalanceDataPoint):
        """Add a balance data point"""
        history = self.balance_history[account_id]
        
        # Check if we already have data for this timestamp
        existing_index = None
        for i, existing in enumerate(history):
            if existing.timestamp == point.timestamp:
                existing_index = i
                break
        
        if existing_index is not None:
            # Update existing point
            history[existing_index] = point
        else:
            # Add new point
            history.append(point)
            # Keep sorted by timestamp
            history.sort(key=lambda x: x.timestamp)
        
        # Limit memory usage
        if len(history) > self.max_points:
            history[:] = history[-self.max_points:]
    
    def get_balance_history(self, account_id: str, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[BalanceDataPoint]:
        """Get balance history for date range"""
        history = self.balance_history.get(account_id, [])
        
        if not start_date and not end_date:
            return history
        
        filtered = []
        for point in history:
            if start_date and point.timestamp < start_date:
                continue
            if end_date and point.timestamp > end_date:
                continue
            filtered.append(point)
        
        return filtered
    
    def clear_account_history(self, account_id: str):
        """Clear history for an account"""
        if account_id in self.balance_history:
            del self.balance_history[account_id]

class HistoricalDataService:
    """Service for managing historical account data"""
    
    def __init__(self, account_id: str):
        self.account_id = account_id
        self.data_store = HistoricalDataStore()
        
        # Data collection tracking
        self.last_collection_time: Optional[datetime] = None
        self.collection_interval = timedelta(minutes=5)  # Collect every 5 minutes
        
        # Background task for periodic data collection
        self.collection_task: Optional[asyncio.Task] = None
        self.is_collecting = False
    
    def start_data_collection(self):
        """Start periodic data collection"""
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.collection_task = asyncio.create_task(self._collection_loop())
        logger.info(f"Started historical data collection for account: {self.account_id}")
    
    def stop_data_collection(self):
        """Stop periodic data collection"""
        if not self.is_collecting:
            return
        
        self.is_collecting = False
        if self.collection_task:
            self.collection_task.cancel()
        logger.info("Stopped historical data collection")
    
    async def _collection_loop(self):
        """Background loop for data collection"""
        while self.is_collecting:
            try:
                # This would be called by the real-time update service
                # when account data changes
                await asyncio.sleep(self.collection_interval.total_seconds())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in data collection loop: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    def record_balance_snapshot(self, 
                               balance: Decimal,
                               unrealized_pl: Decimal,
                               realized_pl: Decimal,
                               equity: Decimal,
                               margin_used: Decimal,
                               margin_available: Decimal,
                               open_positions: int,
                               pending_orders: int,
                               timestamp: Optional[datetime] = None):
        """Record a balance snapshot"""
        
        if not timestamp:
            timestamp = datetime.utcnow()
        
        # Calculate drawdown
        history = self.data_store.get_balance_history(self.account_id)
        drawdown = None
        if history:
            peak_equity = max(float(dp.equity) for dp in history)
            if peak_equity > 0:
                current_drawdown = (peak_equity - float(equity)) / peak_equity
                drawdown = Decimal(str(current_drawdown))
        
        point = BalanceDataPoint(
            timestamp=timestamp,
            balance=balance,
            unrealized_pl=unrealized_pl,
            realized_pl=realized_pl,
            equity=equity,
            margin_used=margin_used,
            margin_available=margin_available,
            open_positions=open_positions,
            pending_orders=pending_orders,
            drawdown=drawdown
        )
        
        self.data_store.add_balance_point(self.account_id, point)
        self.last_collection_time = timestamp
    
    async def get_balance_history(self, 
                                 days: int = 30,
                                 interval: TimeInterval = TimeInterval.DAILY) -> BalanceHistoryData:
        """
        Get balance history for specified period
        
        Args:
            days: Number of days to look back
            interval: Time interval for aggregation
            
        Returns:
            BalanceHistoryData with analysis
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get raw data
        raw_data = self.data_store.get_balance_history(self.account_id, start_date, end_date)
        
        if not raw_data:
            # Return empty data if no history
            return BalanceHistoryData(
                data_points=[],
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                metrics=self._calculate_empty_metrics(),
                trend=TrendDirection.SIDEWAYS,
                volatility=Decimal('0')
            )
        
        # Aggregate data by interval if needed
        aggregated_data = await self._aggregate_by_interval(raw_data, interval)
        
        # Calculate metrics
        metrics = self._calculate_metrics(aggregated_data)
        
        # Determine trend
        trend = self._calculate_trend(aggregated_data)
        
        # Calculate volatility
        volatility = self._calculate_volatility(aggregated_data)
        
        return BalanceHistoryData(
            data_points=aggregated_data,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            metrics=metrics,
            trend=trend,
            volatility=volatility
        )
    
    async def _aggregate_by_interval(self, data: List[BalanceDataPoint], 
                                   interval: TimeInterval) -> List[BalanceDataPoint]:
        """Aggregate data points by time interval"""
        if interval == TimeInterval.ONE_MINUTE or len(data) < 100:
            return data
        
        # Simple aggregation - take last point in each interval
        aggregated = []
        interval_seconds = self._get_interval_seconds(interval)
        
        if not data:
            return aggregated
        
        current_bucket_start = data[0].timestamp.replace(second=0, microsecond=0)
        bucket_points = []
        
        for point in data:
            # Check if point belongs to current bucket
            point_bucket_start = self._get_bucket_start(point.timestamp, interval_seconds)
            
            if point_bucket_start == current_bucket_start:
                bucket_points.append(point)
            else:
                # Process previous bucket
                if bucket_points:
                    aggregated_point = self._aggregate_bucket(bucket_points)
                    aggregated.append(aggregated_point)
                
                # Start new bucket
                current_bucket_start = point_bucket_start
                bucket_points = [point]
        
        # Process last bucket
        if bucket_points:
            aggregated_point = self._aggregate_bucket(bucket_points)
            aggregated.append(aggregated_point)
        
        return aggregated
    
    def _get_interval_seconds(self, interval: TimeInterval) -> int:
        """Get interval in seconds"""
        mapping = {
            TimeInterval.ONE_MINUTE: 60,
            TimeInterval.FIVE_MINUTES: 300,
            TimeInterval.FIFTEEN_MINUTES: 900,
            TimeInterval.THIRTY_MINUTES: 1800,
            TimeInterval.ONE_HOUR: 3600,
            TimeInterval.FOUR_HOURS: 14400,
            TimeInterval.DAILY: 86400,
            TimeInterval.WEEKLY: 604800,
            TimeInterval.MONTHLY: 2592000
        }
        return mapping.get(interval, 86400)
    
    def _get_bucket_start(self, timestamp: datetime, interval_seconds: int) -> datetime:
        """Get bucket start time for timestamp"""
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        seconds_since_epoch = (timestamp - epoch).total_seconds()
        bucket_seconds = int(seconds_since_epoch // interval_seconds) * interval_seconds
        return epoch + timedelta(seconds=bucket_seconds)
    
    def _aggregate_bucket(self, points: List[BalanceDataPoint]) -> BalanceDataPoint:
        """Aggregate points in a bucket (use last point with averages for some fields)"""
        if not points:
            raise ValueError("Empty bucket")
        
        # Use the last point as base
        last_point = points[-1]
        
        # Average some fields
        avg_margin_used = sum(float(p.margin_used) for p in points) / len(points)
        avg_open_positions = sum(p.open_positions for p in points) / len(points)
        avg_pending_orders = sum(p.pending_orders for p in points) / len(points)
        
        return BalanceDataPoint(
            timestamp=last_point.timestamp,
            balance=last_point.balance,
            unrealized_pl=last_point.unrealized_pl,
            realized_pl=last_point.realized_pl,
            equity=last_point.equity,
            margin_used=Decimal(str(avg_margin_used)),
            margin_available=last_point.margin_available,
            open_positions=int(avg_open_positions),
            pending_orders=int(avg_pending_orders),
            drawdown=last_point.drawdown
        )
    
    def _calculate_metrics(self, data: List[BalanceDataPoint]) -> PerformanceMetrics:
        """Calculate performance metrics"""
        if not data:
            return self._calculate_empty_metrics()
        
        start_balance = data[0].balance
        end_balance = data[-1].balance
        
        # Basic returns
        total_return = end_balance - start_balance
        total_return_percent = (total_return / start_balance) * 100 if start_balance != 0 else Decimal('0')
        
        # Drawdown calculation
        peak_equity = start_balance
        max_drawdown = Decimal('0')
        max_drawdown_percent = Decimal('0')
        
        for point in data:
            if point.equity > peak_equity:
                peak_equity = point.equity
            
            current_drawdown = peak_equity - point.equity
            current_drawdown_percent = (current_drawdown / peak_equity) * 100 if peak_equity != 0 else Decimal('0')
            
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
                max_drawdown_percent = current_drawdown_percent
        
        # Calculate additional metrics (simplified)
        equity_changes = []
        for i in range(1, len(data)):
            change = data[i].equity - data[i-1].equity
            if change != 0:
                equity_changes.append(change)
        
        winning_changes = [c for c in equity_changes if c > 0]
        losing_changes = [c for c in equity_changes if c < 0]
        
        win_rate = Decimal(len(winning_changes) / len(equity_changes)) * 100 if equity_changes else Decimal('0')
        average_win = sum(winning_changes) / len(winning_changes) if winning_changes else Decimal('0')
        average_loss = sum(abs(c) for c in losing_changes) / len(losing_changes) if losing_changes else Decimal('0')
        
        return PerformanceMetrics(
            start_balance=start_balance,
            end_balance=end_balance,
            total_return=total_return,
            total_return_percent=total_return_percent,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=None,  # Would need risk-free rate calculation
            profit_factor=average_win / average_loss if average_loss != 0 else None,
            win_rate=win_rate,
            average_win=average_win,
            average_loss=average_loss,
            total_trades=len(equity_changes),
            winning_trades=len(winning_changes),
            losing_trades=len(losing_changes),
            best_trade=max(equity_changes) if equity_changes else None,
            worst_trade=min(equity_changes) if equity_changes else None,
            consecutive_wins=self._calculate_consecutive(equity_changes, lambda x: x > 0)[0],
            consecutive_losses=self._calculate_consecutive(equity_changes, lambda x: x < 0)[0],
            trading_days=len(set(point.timestamp.date() for point in data))
        )
    
    def _calculate_empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics"""
        return PerformanceMetrics(
            start_balance=Decimal('0'),
            end_balance=Decimal('0'),
            total_return=Decimal('0'),
            total_return_percent=Decimal('0'),
            max_drawdown=Decimal('0'),
            max_drawdown_percent=Decimal('0'),
            sharpe_ratio=None,
            profit_factor=None,
            win_rate=None,
            average_win=None,
            average_loss=None,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            best_trade=None,
            worst_trade=None,
            consecutive_wins=0,
            consecutive_losses=0,
            trading_days=0
        )
    
    def _calculate_consecutive(self, changes: List[Decimal], condition) -> Tuple[int, int]:
        """Calculate max consecutive wins/losses"""
        if not changes:
            return 0, 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for change in changes:
            if condition(change):
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive, current_consecutive
    
    def _calculate_trend(self, data: List[BalanceDataPoint]) -> TrendDirection:
        """Calculate overall trend direction"""
        if len(data) < 2:
            return TrendDirection.SIDEWAYS
        
        start_equity = data[0].equity
        end_equity = data[-1].equity
        
        change_percent = ((end_equity - start_equity) / start_equity) * 100 if start_equity != 0 else Decimal('0')
        
        if change_percent > 2:  # >2% increase
            return TrendDirection.UP
        elif change_percent < -2:  # >2% decrease
            return TrendDirection.DOWN
        else:
            return TrendDirection.SIDEWAYS
    
    def _calculate_volatility(self, data: List[BalanceDataPoint]) -> Decimal:
        """Calculate equity volatility (standard deviation of returns)"""
        if len(data) < 2:
            return Decimal('0')
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(data)):
            if data[i-1].equity != 0:
                return_pct = (data[i].equity - data[i-1].equity) / data[i-1].equity
                returns.append(float(return_pct))
        
        if not returns:
            return Decimal('0')
        
        # Calculate standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
        
        return Decimal(str(volatility * 100))  # Return as percentage
    
    async def export_history(self, days: int = 30, format: str = 'csv') -> str:
        """
        Export balance history to CSV or JSON
        
        Args:
            days: Number of days to export
            format: 'csv' or 'json'
            
        Returns:
            Formatted string data
        """
        history_data = await self.get_balance_history(days)
        
        if format.lower() == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Timestamp', 'Balance', 'Unrealized P&L', 'Realized P&L', 
                'Equity', 'Margin Used', 'Margin Available', 
                'Open Positions', 'Pending Orders', 'Drawdown %'
            ])
            
            # Write data
            for point in history_data.data_points:
                writer.writerow([
                    point.timestamp.isoformat(),
                    float(point.balance),
                    float(point.unrealized_pl),
                    float(point.realized_pl),
                    float(point.equity),
                    float(point.margin_used),
                    float(point.margin_available),
                    point.open_positions,
                    point.pending_orders,
                    float(point.drawdown * 100) if point.drawdown else None
                ])
            
            return output.getvalue()
        
        elif format.lower() == 'json':
            export_data = {
                'export_date': datetime.utcnow().isoformat(),
                'account_id': self.account_id,
                'period_days': days,
                'data_points': [asdict(point) for point in history_data.data_points],
                'metrics': asdict(history_data.metrics)
            }
            
            return json.dumps(export_data, indent=2, default=str)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_latest_snapshot(self) -> Optional[BalanceDataPoint]:
        """Get the most recent balance snapshot"""
        history = self.data_store.get_balance_history(self.account_id)
        return history[-1] if history else None