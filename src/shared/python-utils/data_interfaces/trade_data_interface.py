"""
Trade Data Interface

Abstract interface for trade data providers, allowing seamless switching
between mock data and real trade history from databases or brokers.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class TradeStatus(Enum):
    """Trade status enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"


@dataclass
class Trade:
    """Represents a single trade"""
    id: str
    account_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    size: Decimal
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    entry_time: datetime = datetime.now()
    exit_time: Optional[datetime] = None
    pnl: Optional[Decimal] = None
    status: TradeStatus = TradeStatus.OPEN
    execution_delay_ms: Optional[int] = None


@dataclass
class AccountPerformance:
    """Account performance metrics"""
    account_id: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: Decimal
    win_rate: float
    average_win: Decimal
    average_loss: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Optional[float] = None


class TradeDataInterface(ABC):
    """Abstract interface for trade data providers"""
    
    @abstractmethod
    async def get_trades_by_account(self, account_id: str, limit: Optional[int] = None) -> List[Trade]:
        """Get trades for a specific account"""
        pass
    
    @abstractmethod
    async def get_trades_by_timeframe(self, account_id: str, start_time: datetime, end_time: datetime) -> List[Trade]:
        """Get trades within a specific timeframe"""
        pass
    
    @abstractmethod
    async def get_account_performance(self, account_id: str) -> AccountPerformance:
        """Get performance metrics for an account"""
        pass
    
    @abstractmethod
    async def get_correlation_data(self, account_ids: List[str]) -> Dict[str, List[Decimal]]:
        """Get daily returns for correlation analysis"""
        pass
    
    @abstractmethod
    async def store_trade(self, trade: Trade) -> bool:
        """Store a new trade record"""
        pass


class MockTradeDataProvider(TradeDataInterface):
    """Mock implementation for development and testing"""
    
    def __init__(self):
        self._mock_trades = self._generate_mock_trades()
    
    def _generate_mock_trades(self) -> List[Trade]:
        """Generate mock trade data"""
        trades = []
        base_time = datetime.now() - timedelta(days=30)
        
        account_ids = ["ACC001", "ACC002", "ACC003"]
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        
        for i in range(100):
            account_id = account_ids[i % len(account_ids)]
            symbol = symbols[i % len(symbols)]
            side = "buy" if i % 2 == 0 else "sell"
            
            # Generate realistic price and PnL
            entry_price = Decimal('1.1000') + Decimal(str((i % 20 - 10) * 0.001))
            exit_price = entry_price + Decimal(str((i % 10 - 5) * 0.0001))
            
            size = Decimal('1.0')
            pnl = (exit_price - entry_price) * size if side == "buy" else (entry_price - exit_price) * size
            
            trade = Trade(
                id=f"TRADE_{i:03d}",
                account_id=account_id,
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                exit_price=exit_price,
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i, minutes=30),
                pnl=pnl,
                status=TradeStatus.CLOSED,
                execution_delay_ms=500 + (i % 1000)
            )
            trades.append(trade)
        
        return trades
    
    async def get_trades_by_account(self, account_id: str, limit: Optional[int] = None) -> List[Trade]:
        """Get mock trades for account"""
        account_trades = [t for t in self._mock_trades if t.account_id == account_id]
        if limit:
            account_trades = account_trades[:limit]
        return account_trades
    
    async def get_trades_by_timeframe(self, account_id: str, start_time: datetime, end_time: datetime) -> List[Trade]:
        """Get mock trades within timeframe"""
        account_trades = await self.get_trades_by_account(account_id)
        return [
            t for t in account_trades 
            if start_time <= t.entry_time <= end_time
        ]
    
    async def get_account_performance(self, account_id: str) -> AccountPerformance:
        """Calculate mock performance metrics"""
        trades = await self.get_trades_by_account(account_id)
        
        if not trades:
            return AccountPerformance(
                account_id=account_id,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_pnl=Decimal('0'),
                win_rate=0.0,
                average_win=Decimal('0'),
                average_loss=Decimal('0'),
                max_drawdown=Decimal('0')
            )
        
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in trades if t.pnl)
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else Decimal('0')
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else Decimal('0')
        
        return AccountPerformance(
            account_id=account_id,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            total_pnl=total_pnl,
            win_rate=win_rate,
            average_win=avg_win,
            average_loss=avg_loss,
            max_drawdown=Decimal('50.0')  # Mock max drawdown
        )
    
    async def get_correlation_data(self, account_ids: List[str]) -> Dict[str, List[Decimal]]:
        """Generate mock correlation data"""
        correlation_data = {}
        
        for account_id in account_ids:
            # Generate mock daily returns for correlation analysis
            daily_returns = [Decimal(str(0.001 * (i % 10 - 5))) for i in range(30)]
            correlation_data[account_id] = daily_returns
        
        return correlation_data
    
    async def store_trade(self, trade: Trade) -> bool:
        """Store mock trade (just add to list)"""
        self._mock_trades.append(trade)
        return True