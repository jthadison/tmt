"""
Performance Data Interface

Abstract interface for performance data providers, allowing seamless switching
between mock data and real performance analytics from databases or analytics services.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Performance metrics for a trading strategy or account"""
    account_id: str
    strategy_id: Optional[str]
    timeframe: str  # 'daily', 'weekly', 'monthly'
    total_return: Decimal
    sharpe_ratio: Optional[float]
    max_drawdown: Decimal
    win_rate: float
    profit_factor: Optional[float]
    total_trades: int
    avg_trade_duration: Optional[timedelta]
    best_trade: Optional[Decimal]
    worst_trade: Optional[Decimal]
    calculated_at: datetime


@dataclass 
class StrategyPerformance:
    """Strategy-specific performance data"""
    strategy_id: str
    strategy_name: str
    active_accounts: List[str]
    total_return: Decimal
    active_since: datetime
    last_updated: datetime
    confidence_score: float  # 0.0 to 1.0
    recommendation: str  # 'continue', 'modify', 'pause', 'stop'


class PerformanceDataInterface(ABC):
    """Abstract interface for performance data providers"""
    
    @abstractmethod
    async def get_account_performance(self, account_id: str, timeframe: str = 'monthly') -> Optional[PerformanceMetrics]:
        """Get performance metrics for an account"""
        pass
    
    @abstractmethod
    async def get_strategy_performance(self, strategy_id: str) -> Optional[StrategyPerformance]:
        """Get performance data for a specific strategy"""
        pass
    
    @abstractmethod
    async def get_comparative_performance(self, account_ids: List[str]) -> Dict[str, PerformanceMetrics]:
        """Get comparative performance across multiple accounts"""
        pass
    
    @abstractmethod
    async def calculate_correlation_matrix(self, account_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between accounts"""
        pass
    
    @abstractmethod
    async def store_performance_snapshot(self, metrics: PerformanceMetrics) -> bool:
        """Store a performance snapshot"""
        pass


class MockPerformanceDataProvider(PerformanceDataInterface):
    """Mock implementation for development and testing"""
    
    def __init__(self):
        self._mock_performance_data = self._generate_mock_performance_data()
        self._mock_strategy_data = self._generate_mock_strategy_data()
    
    def _generate_mock_performance_data(self) -> List[PerformanceMetrics]:
        """Generate mock performance metrics"""
        metrics = []
        
        for i in range(10):
            account_id = f"ACC{i:03d}"
            
            # Generate realistic but varied performance
            base_return = Decimal(str(0.05 + (i % 5) * 0.02))  # 5% to 13% returns
            win_rate = 0.6 + (i % 3) * 0.1  # 60% to 80% win rates
            max_dd = Decimal(str(0.02 + (i % 4) * 0.01))  # 2% to 5% max drawdown
            
            metric = PerformanceMetrics(
                account_id=account_id,
                strategy_id=f"STRAT_{(i % 3) + 1:03d}",
                timeframe='monthly',
                total_return=base_return,
                sharpe_ratio=1.2 + (i % 4) * 0.3,
                max_drawdown=max_dd,
                win_rate=win_rate,
                profit_factor=1.3 + (i % 3) * 0.2,
                total_trades=50 + i * 10,
                avg_trade_duration=timedelta(hours=2 + i % 8),
                best_trade=Decimal(str(25.0 + i * 5)),
                worst_trade=Decimal(str(-15.0 - i * 2)),
                calculated_at=datetime.now()
            )
            metrics.append(metric)
        
        return metrics
    
    def _generate_mock_strategy_data(self) -> List[StrategyPerformance]:
        """Generate mock strategy performance data"""
        strategies = []
        strategy_names = ["Wyckoff Momentum", "SMC Reversal", "Volume Breakout"]
        
        for i, name in enumerate(strategy_names):
            strategy = StrategyPerformance(
                strategy_id=f"STRAT_{i+1:03d}",
                strategy_name=name,
                active_accounts=[f"ACC{j:03d}" for j in range(i*3, (i+1)*3)],
                total_return=Decimal(str(0.08 + i * 0.03)),
                active_since=datetime.now() - timedelta(days=30 + i * 15),
                last_updated=datetime.now(),
                confidence_score=0.75 + i * 0.1,
                recommendation="continue" if i != 2 else "modify"
            )
            strategies.append(strategy)
        
        return strategies
    
    async def get_account_performance(self, account_id: str, timeframe: str = 'monthly') -> Optional[PerformanceMetrics]:
        """Get mock account performance"""
        for metric in self._mock_performance_data:
            if metric.account_id == account_id and metric.timeframe == timeframe:
                return metric
        return None
    
    async def get_strategy_performance(self, strategy_id: str) -> Optional[StrategyPerformance]:
        """Get mock strategy performance"""
        for strategy in self._mock_strategy_data:
            if strategy.strategy_id == strategy_id:
                return strategy
        return None
    
    async def get_comparative_performance(self, account_ids: List[str]) -> Dict[str, PerformanceMetrics]:
        """Get mock comparative performance"""
        result = {}
        for account_id in account_ids:
            performance = await self.get_account_performance(account_id)
            if performance:
                result[account_id] = performance
        return result
    
    async def calculate_correlation_matrix(self, account_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """Generate mock correlation matrix"""
        matrix = {}
        
        for account1 in account_ids:
            matrix[account1] = {}
            for account2 in account_ids:
                if account1 == account2:
                    matrix[account1][account2] = 1.0
                else:
                    # Generate mock correlation (0.1 to 0.8)
                    correlation = 0.1 + (hash(account1 + account2) % 70) / 100.0
                    matrix[account1][account2] = correlation
        
        return matrix
    
    async def store_performance_snapshot(self, metrics: PerformanceMetrics) -> bool:
        """Store mock performance snapshot"""
        # In mock implementation, just add to list
        self._mock_performance_data.append(metrics)
        return True