"""
Real-Time P&L Monitoring System for comprehensive portfolio tracking.

Provides continuous P&L analysis, performance attribution, and 
real-time risk assessment with microsecond precision.
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Set

import numpy as np
from dataclasses import dataclass

from ..core.models import (
    Position,
    PortfolioAnalytics,
    RiskAlert,
    AlertSeverity,
    RiskLevel
)


@dataclass
class PLSnapshot:
    """Point-in-time P&L snapshot."""
    timestamp: datetime
    account_id: str
    total_pl: Decimal
    unrealized_pl: Decimal
    realized_pl: Decimal
    daily_pl: Decimal
    position_count: int
    market_value: Decimal


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics."""
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_trade_duration: float
    volatility: float


class RealTimePLMonitor:
    """
    High-frequency P&L monitoring system with real-time analytics,
    performance tracking, and automated alerting capabilities.
    """
    
    def __init__(self, update_interval_ms: int = 100):
        self.update_interval_ms = update_interval_ms
        self.is_running = False
        
        # P&L tracking
        self.pl_snapshots: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.position_pl_history: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1000)))
        self.daily_pl_resets: Dict[str, datetime] = {}
        
        # Performance calculation caches
        self.performance_cache: Dict[str, Tuple[datetime, PerformanceMetrics]] = {}
        self.pl_calculation_times: List[float] = []
        
        # Real-time state
        self.current_positions: Dict[str, List[Position]] = {}
        self.current_prices: Dict[str, Decimal] = {}
        self.account_balances: Dict[str, Decimal] = {}
        
        # Alert management
        self.active_pl_alerts: Dict[str, Set[str]] = defaultdict(set)
        self.alert_thresholds = {
            'daily_loss_warning': Decimal('-500'),
            'daily_loss_critical': Decimal('-1000'),
            'unrealized_loss_warning': Decimal('-750'),
            'unrealized_loss_critical': Decimal('-1500'),
            'drawdown_warning': 0.05,  # 5%
            'drawdown_critical': 0.10  # 10%
        }
        
        # Performance monitoring
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
    async def start_monitoring(self, account_ids: List[str]):
        """Start real-time P&L monitoring for specified accounts."""
        self.is_running = True
        
        for account_id in account_ids:
            if account_id not in self.monitoring_tasks:
                task = asyncio.create_task(self._monitor_account_pl(account_id))
                self.monitoring_tasks[account_id] = task
        
        print(f"Started P&L monitoring for {len(account_ids)} accounts")
    
    async def stop_monitoring(self):
        """Stop all P&L monitoring tasks."""
        self.is_running = False
        
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
        self.monitoring_tasks.clear()
        
        print("Stopped P&L monitoring")
    
    async def _monitor_account_pl(self, account_id: str):
        """Monitor P&L for a specific account continuously."""
        while self.is_running:
            try:
                start_time = time.perf_counter()
                
                # Get current positions
                positions = self.current_positions.get(account_id, [])
                
                if positions:
                    # Calculate current P&L
                    pl_snapshot = await self._calculate_pl_snapshot(account_id, positions)
                    
                    # Store snapshot
                    self.pl_snapshots[account_id].append(pl_snapshot)
                    
                    # Update position-level P&L history
                    await self._update_position_pl_history(account_id, positions)
                    
                    # Check for P&L alerts
                    await self._check_pl_alerts(account_id, pl_snapshot)
                    
                    # Performance tracking
                    calculation_time = (time.perf_counter() - start_time) * 1000
                    self.pl_calculation_times.append(calculation_time)
                    
                    # Keep only last 1000 measurements
                    if len(self.pl_calculation_times) > 1000:
                        self.pl_calculation_times = self.pl_calculation_times[-1000:]
                
                # Sleep for update interval
                await asyncio.sleep(self.update_interval_ms / 1000)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in P&L monitoring for {account_id}: {e}")
                await asyncio.sleep(1)  # Back off on error
    
    async def _calculate_pl_snapshot(self, account_id: str, positions: List[Position]) -> PLSnapshot:
        """Calculate comprehensive P&L snapshot."""
        now = datetime.now()
        
        # Calculate totals
        total_unrealized_pl = sum(pos.unrealized_pl for pos in positions)
        total_realized_pl = sum(pos.realized_pl for pos in positions)
        total_daily_pl = sum(pos.daily_pl for pos in positions)
        total_market_value = sum(abs(pos.market_value) for pos in positions)
        
        # Total P&L
        total_pl = total_unrealized_pl + total_realized_pl
        
        return PLSnapshot(
            timestamp=now,
            account_id=account_id,
            total_pl=total_pl,
            unrealized_pl=total_unrealized_pl,
            realized_pl=total_realized_pl,
            daily_pl=total_daily_pl,
            position_count=len(positions),
            market_value=total_market_value
        )
    
    async def _update_position_pl_history(self, account_id: str, positions: List[Position]):
        """Update position-level P&L history."""
        now = datetime.now()
        
        for position in positions:
            position_key = f"{position.instrument}_{position.position_id}"
            
            # Store position P&L data point
            pl_data = {
                'timestamp': now,
                'unrealized_pl': position.unrealized_pl,
                'realized_pl': position.realized_pl,
                'daily_pl': position.daily_pl,
                'market_value': position.market_value,
                'current_price': position.current_price
            }
            
            self.position_pl_history[account_id][position_key].append(pl_data)
    
    async def _check_pl_alerts(self, account_id: str, snapshot: PLSnapshot):
        """Check for P&L-based alerts and notifications."""
        alerts_triggered = []
        
        # Daily loss alerts
        if snapshot.daily_pl <= self.alert_thresholds['daily_loss_critical']:
            alert_key = f"daily_loss_critical_{account_id}"
            if alert_key not in self.active_pl_alerts[account_id]:
                alerts_triggered.append({
                    'type': 'daily_loss_critical',
                    'severity': AlertSeverity.CRITICAL,
                    'message': f"Critical daily loss: {snapshot.daily_pl}",
                    'details': {'daily_pl': float(snapshot.daily_pl)}
                })
                self.active_pl_alerts[account_id].add(alert_key)
        
        elif snapshot.daily_pl <= self.alert_thresholds['daily_loss_warning']:
            alert_key = f"daily_loss_warning_{account_id}"
            if alert_key not in self.active_pl_alerts[account_id]:
                alerts_triggered.append({
                    'type': 'daily_loss_warning',
                    'severity': AlertSeverity.WARNING,
                    'message': f"Daily loss warning: {snapshot.daily_pl}",
                    'details': {'daily_pl': float(snapshot.daily_pl)}
                })
                self.active_pl_alerts[account_id].add(alert_key)
        
        # Unrealized loss alerts
        if snapshot.unrealized_pl <= self.alert_thresholds['unrealized_loss_critical']:
            alert_key = f"unrealized_loss_critical_{account_id}"
            if alert_key not in self.active_pl_alerts[account_id]:
                alerts_triggered.append({
                    'type': 'unrealized_loss_critical',
                    'severity': AlertSeverity.CRITICAL,
                    'message': f"Critical unrealized loss: {snapshot.unrealized_pl}",
                    'details': {'unrealized_pl': float(snapshot.unrealized_pl)}
                })
                self.active_pl_alerts[account_id].add(alert_key)
        
        elif snapshot.unrealized_pl <= self.alert_thresholds['unrealized_loss_warning']:
            alert_key = f"unrealized_loss_warning_{account_id}"
            if alert_key not in self.active_pl_alerts[account_id]:
                alerts_triggered.append({
                    'type': 'unrealized_loss_warning',
                    'severity': AlertSeverity.WARNING,
                    'message': f"Unrealized loss warning: {snapshot.unrealized_pl}",
                    'details': {'unrealized_pl': float(snapshot.unrealized_pl)}
                })
                self.active_pl_alerts[account_id].add(alert_key)
        
        # Drawdown alerts
        drawdown = await self._calculate_current_drawdown(account_id)
        if drawdown >= self.alert_thresholds['drawdown_critical']:
            alert_key = f"drawdown_critical_{account_id}"
            if alert_key not in self.active_pl_alerts[account_id]:
                alerts_triggered.append({
                    'type': 'drawdown_critical',
                    'severity': AlertSeverity.CRITICAL,
                    'message': f"Critical drawdown: {drawdown:.2%}",
                    'details': {'drawdown': drawdown}
                })
                self.active_pl_alerts[account_id].add(alert_key)
        
        elif drawdown >= self.alert_thresholds['drawdown_warning']:
            alert_key = f"drawdown_warning_{account_id}"
            if alert_key not in self.active_pl_alerts[account_id]:
                alerts_triggered.append({
                    'type': 'drawdown_warning',
                    'severity': AlertSeverity.WARNING,
                    'message': f"Drawdown warning: {drawdown:.2%}",
                    'details': {'drawdown': drawdown}
                })
                self.active_pl_alerts[account_id].add(alert_key)
        
        # Process triggered alerts
        for alert_data in alerts_triggered:
            await self._process_pl_alert(account_id, alert_data)
    
    async def _process_pl_alert(self, account_id: str, alert_data: Dict):
        """Process and handle P&L alerts."""
        # In production, this would integrate with alerting system
        print(f"P&L Alert for {account_id}: {alert_data['message']}")
        
        # Log alert details
        alert_log = {
            'timestamp': datetime.now().isoformat(),
            'account_id': account_id,
            'alert_type': alert_data['type'],
            'severity': alert_data['severity'].value,
            'message': alert_data['message'],
            'details': alert_data['details']
        }
        
        # Could send to external systems (Slack, email, etc.)
    
    async def _calculate_current_drawdown(self, account_id: str) -> float:
        """Calculate current drawdown from peak."""
        snapshots = list(self.pl_snapshots.get(account_id, []))
        
        if len(snapshots) < 2:
            return 0.0
        
        # Find peak portfolio value
        peak_value = Decimal("0")
        current_value = snapshots[-1].total_pl + self.account_balances.get(account_id, Decimal("10000"))
        
        for snapshot in snapshots:
            portfolio_value = snapshot.total_pl + self.account_balances.get(account_id, Decimal("10000"))
            peak_value = max(peak_value, portfolio_value)
        
        if peak_value <= 0:
            return 0.0
        
        # Calculate drawdown
        drawdown = float((peak_value - current_value) / peak_value)
        return max(0.0, drawdown)
    
    async def get_real_time_pl(self, account_id: str) -> Optional[PLSnapshot]:
        """Get the most recent P&L snapshot for an account."""
        snapshots = self.pl_snapshots.get(account_id)
        return snapshots[-1] if snapshots else None
    
    async def get_pl_history(
        self, 
        account_id: str, 
        hours: int = 24
    ) -> List[PLSnapshot]:
        """Get P&L history for specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        snapshots = self.pl_snapshots.get(account_id, [])
        
        return [
            snapshot for snapshot in snapshots 
            if snapshot.timestamp >= cutoff_time
        ]
    
    async def calculate_performance_metrics(self, account_id: str) -> Optional[PerformanceMetrics]:
        """Calculate comprehensive performance metrics."""
        snapshots = list(self.pl_snapshots.get(account_id, []))
        
        if len(snapshots) < 100:  # Need sufficient data
            return None
        
        # Check cache (5-minute TTL)
        now = datetime.now()
        if account_id in self.performance_cache:
            cached_time, cached_metrics = self.performance_cache[account_id]
            if (now - cached_time).total_seconds() < 300:
                return cached_metrics
        
        # Calculate returns
        returns = []
        portfolio_values = []
        
        base_balance = self.account_balances.get(account_id, Decimal("10000"))
        
        for i, snapshot in enumerate(snapshots):
            portfolio_value = float(snapshot.total_pl + base_balance)
            portfolio_values.append(portfolio_value)
            
            if i > 0:
                prev_value = portfolio_values[i-1]
                if prev_value > 0:
                    return_pct = (portfolio_value - prev_value) / prev_value
                    returns.append(return_pct)
        
        if not returns:
            return None
        
        # Sharpe ratio
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0
        else:
            sharpe = 0.0
        
        # Max drawdown
        running_max = []
        current_max = portfolio_values[0]
        
        for value in portfolio_values:
            current_max = max(current_max, value)
            running_max.append(current_max)
        
        drawdowns = [
            (value - running_max[i]) / running_max[i] 
            for i, value in enumerate(portfolio_values)
            if running_max[i] > 0
        ]
        
        max_drawdown = abs(min(drawdowns)) if drawdowns else 0.0
        
        # Win rate
        positive_returns = sum(1 for r in returns if r > 0)
        win_rate = positive_returns / len(returns) if returns else 0.0
        
        # Profit factor
        positive_sum = sum(r for r in returns if r > 0)
        negative_sum = abs(sum(r for r in returns if r < 0))
        profit_factor = positive_sum / negative_sum if negative_sum > 0 else float('inf')
        
        # Volatility
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
        
        # Average trade duration (simplified)
        total_time = (snapshots[-1].timestamp - snapshots[0].timestamp).total_seconds()
        avg_trade_duration = total_time / len(snapshots) if snapshots else 0.0
        
        metrics = PerformanceMetrics(
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_duration=avg_trade_duration,
            volatility=volatility
        )
        
        # Cache results
        self.performance_cache[account_id] = (now, metrics)
        
        return metrics
    
    async def get_position_pl_analysis(
        self, 
        account_id: str, 
        instrument: str
    ) -> Dict[str, float]:
        """Get detailed P&L analysis for a specific position."""
        position_histories = self.position_pl_history.get(account_id, {})
        
        # Find matching positions
        matching_positions = [
            (key, history) for key, history in position_histories.items()
            if key.startswith(instrument)
        ]
        
        if not matching_positions:
            return {}
        
        # Aggregate P&L data
        total_unrealized = Decimal("0")
        total_realized = Decimal("0")
        total_daily = Decimal("0")
        total_market_value = Decimal("0")
        
        pl_changes = []
        
        for key, history in matching_positions:
            if history:
                latest = history[-1]
                total_unrealized += latest['unrealized_pl']
                total_realized += latest['realized_pl']
                total_daily += latest['daily_pl']
                total_market_value += abs(latest['market_value'])
                
                # Calculate P&L changes
                if len(history) > 1:
                    for i in range(1, len(history)):
                        prev_pl = history[i-1]['unrealized_pl']
                        curr_pl = history[i]['unrealized_pl']
                        if abs(prev_pl) > 0:
                            pl_change = float((curr_pl - prev_pl) / abs(prev_pl))
                            pl_changes.append(pl_change)
        
        # Analysis metrics
        analysis = {
            'total_unrealized_pl': float(total_unrealized),
            'total_realized_pl': float(total_realized),
            'total_daily_pl': float(total_daily),
            'total_market_value': float(total_market_value),
            'position_count': len(matching_positions)
        }
        
        if pl_changes:
            analysis.update({
                'avg_pl_change': np.mean(pl_changes),
                'pl_volatility': np.std(pl_changes),
                'max_pl_change': max(pl_changes),
                'min_pl_change': min(pl_changes)
            })
        
        return analysis
    
    def update_positions(self, account_id: str, positions: List[Position]):
        """Update current positions for monitoring."""
        self.current_positions[account_id] = positions
    
    def update_prices(self, price_updates: Dict[str, Decimal]):
        """Update current market prices."""
        self.current_prices.update(price_updates)
    
    def update_account_balance(self, account_id: str, balance: Decimal):
        """Update account balance."""
        self.account_balances[account_id] = balance
    
    def get_monitoring_performance(self) -> Dict[str, float]:
        """Get P&L monitoring system performance metrics."""
        if not self.pl_calculation_times:
            return {
                'avg_calculation_time_ms': 0.0,
                'max_calculation_time_ms': 0.0,
                'calculations_per_second': 0.0,
                'active_accounts': 0
            }
        
        return {
            'avg_calculation_time_ms': sum(self.pl_calculation_times) / len(self.pl_calculation_times),
            'max_calculation_time_ms': max(self.pl_calculation_times),
            'min_calculation_time_ms': min(self.pl_calculation_times),
            'calculations_per_second': 1000 / (sum(self.pl_calculation_times) / len(self.pl_calculation_times)),
            'total_calculations': len(self.pl_calculation_times),
            'active_accounts': len(self.monitoring_tasks),
            'active_alerts': sum(len(alerts) for alerts in self.active_pl_alerts.values())
        }
    
    async def reset_daily_pl(self, account_id: str):
        """Reset daily P&L tracking for new trading day."""
        self.daily_pl_resets[account_id] = datetime.now()
        
        # Clear daily-specific alerts
        daily_alerts = [
            alert for alert in self.active_pl_alerts[account_id]
            if 'daily_' in alert
        ]
        
        for alert in daily_alerts:
            self.active_pl_alerts[account_id].discard(alert)
        
        print(f"Reset daily P&L tracking for account {account_id}")
    
    def set_alert_thresholds(self, thresholds: Dict[str, float]):
        """Update P&L alert thresholds."""
        self.alert_thresholds.update(thresholds)
        print(f"Updated P&L alert thresholds: {thresholds}")