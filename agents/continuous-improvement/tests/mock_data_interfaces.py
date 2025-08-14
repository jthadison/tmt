"""
Mock data interfaces for testing the continuous improvement pipeline
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from unittest.mock import Mock
import random

# Mock the data interfaces that the app modules depend on
class TradeDataInterface(ABC):
    """Abstract interface for trade data access"""
    
    @abstractmethod
    async def get_trades(self, account_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        pass
    
    @abstractmethod
    async def get_account_trades(self, account_ids: List[str], start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        pass

class MockTradeDataProvider(TradeDataInterface):
    """Mock implementation for testing"""
    
    async def get_trades(self, account_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        # Generate mock trade data
        num_trades = random.randint(20, 100)
        trades = []
        
        for i in range(num_trades):
            trade_date = start_date + timedelta(hours=random.randint(0, int((end_date - start_date).total_seconds() // 3600)))
            profit = random.uniform(-50, 150)
            
            trades.append({
                'trade_id': f'{account_id}_T{i:04d}',
                'account_id': account_id,
                'symbol': random.choice(['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']),
                'entry_time': trade_date,
                'exit_time': trade_date + timedelta(hours=random.randint(1, 24)),
                'entry_price': random.uniform(1.0, 2.0),
                'exit_price': random.uniform(1.0, 2.0),
                'volume': random.uniform(0.1, 2.0),
                'profit_loss': profit,
                'pips': profit * random.uniform(0.8, 1.2),
                'trade_type': random.choice(['buy', 'sell']),
                'duration_minutes': random.randint(60, 1440)
            })
        
        return trades
    
    async def get_account_trades(self, account_ids: List[str], start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        result = {}
        for account_id in account_ids:
            result[account_id] = await self.get_trades(account_id, start_date, end_date)
        return result

class PerformanceDataInterface(ABC):
    """Abstract interface for performance data access"""
    
    @abstractmethod
    async def get_account_performance(self, account_id: str, start_date: datetime, end_date: datetime) -> Dict:
        pass
    
    @abstractmethod
    async def get_system_performance(self, start_date: datetime, end_date: datetime) -> Dict:
        pass

class MockPerformanceDataProvider(PerformanceDataInterface):
    """Mock implementation for testing"""
    
    async def get_account_performance(self, account_id: str, start_date: datetime, end_date: datetime) -> Dict:
        # Generate realistic mock performance data
        total_trades = random.randint(50, 200)
        winning_trades = int(total_trades * random.uniform(0.45, 0.75))
        
        total_return = random.uniform(-0.05, 0.25)
        max_dd = random.uniform(0.02, 0.15)
        
        return {
            'account_id': account_id,
            'period_start': start_date,
            'period_end': end_date,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': Decimal(str(winning_trades / total_trades)),
            'total_return': Decimal(str(total_return)),
            'profit_factor': Decimal(str(random.uniform(0.8, 2.5))),
            'sharpe_ratio': Decimal(str(random.uniform(0.2, 1.8))),
            'max_drawdown': Decimal(str(max_dd)),
            'expectancy': Decimal(str(random.uniform(-0.01, 0.03))),
            'average_win': Decimal(str(random.uniform(15, 80))),
            'average_loss': Decimal(str(random.uniform(-15, -50))),
            'volatility': Decimal(str(random.uniform(0.08, 0.25)))
        }
    
    async def get_system_performance(self, start_date: datetime, end_date: datetime) -> Dict:
        # Generate system-wide performance
        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_accounts': random.randint(5, 50),
            'active_accounts': random.randint(3, 40),
            'total_trades': random.randint(500, 5000),
            'total_return': Decimal(str(random.uniform(-0.02, 0.30))),
            'average_win_rate': Decimal(str(random.uniform(0.48, 0.72))),
            'average_profit_factor': Decimal(str(random.uniform(0.9, 2.2))),
            'average_sharpe_ratio': Decimal(str(random.uniform(0.3, 1.5))),
            'system_max_drawdown': Decimal(str(random.uniform(0.03, 0.18))),
            'system_expectancy': Decimal(str(random.uniform(-0.005, 0.025)))
        }

class MarketDataInterface(ABC):
    """Abstract interface for market data access"""
    
    @abstractmethod
    async def get_market_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        pass

class MockMarketDataProvider(MarketDataInterface):
    """Mock implementation for testing"""
    
    async def get_market_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        # Generate mock market data
        hours = int((end_date - start_date).total_seconds() // 3600)
        data = []
        
        base_price = random.uniform(1.0, 2.0)
        
        for i in range(min(hours, 1000)):  # Limit to avoid excessive data
            timestamp = start_date + timedelta(hours=i)
            volatility = random.uniform(0.0001, 0.01)
            
            data.append({
                'symbol': symbol,
                'timestamp': timestamp,
                'open': base_price + random.uniform(-volatility, volatility),
                'high': base_price + random.uniform(0, volatility * 2),
                'low': base_price - random.uniform(0, volatility * 2),
                'close': base_price + random.uniform(-volatility, volatility),
                'volume': random.randint(1000, 50000)
            })
            
            base_price += random.uniform(-volatility/2, volatility/2)
        
        return data