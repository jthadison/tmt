"""
Real-Time Performance Monitor
Continuous monitoring system to prevent September 2025 style performance degradation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio
from collections import deque
import json
from pathlib import Path
import threading
import time

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class MonitoringMetric(Enum):
    """Monitored performance metrics"""
    DAILY_PNL = "daily_pnl"
    WIN_RATE = "win_rate"
    DRAWDOWN = "drawdown"
    SHARPE_RATIO = "sharpe_ratio"
    TRADE_FREQUENCY = "trade_frequency"
    RISK_REWARD = "risk_reward"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    VOLATILITY = "volatility"
    REGIME_CONSISTENCY = "regime_consistency"

@dataclass
class PerformanceAlert:
    """Performance monitoring alert"""
    metric: MonitoringMetric
    level: AlertLevel
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recommended_action: str = ""
    trade_context: Optional[Dict] = None

@dataclass
class PerformanceSnapshot:
    """Point-in-time performance snapshot"""
    timestamp: datetime
    daily_pnl: float
    cumulative_pnl: float
    win_rate: float
    current_drawdown: float
    max_drawdown: float
    sharpe_ratio: float
    trade_count_today: int
    consecutive_losses: int
    avg_risk_reward: float
    volatility: float
    regime_consistency: float

class RealTimePerformanceMonitor:
    """Real-time performance monitoring system"""

    def __init__(self, config: Dict):
        self.config = config
        self.is_monitoring = False
        self.monitoring_thread = None

        # Performance data storage
        self.trade_history = deque(maxlen=1000)
        self.daily_snapshots = deque(maxlen=90)  # 90 days of daily data
        self.alerts = deque(maxlen=500)
        self.current_snapshot = None

        # Monitoring thresholds (calibrated from September 2025 analysis)
        self.thresholds = {
            MonitoringMetric.DAILY_PNL: {
                AlertLevel.WARNING: -500,    # Daily loss warning
                AlertLevel.CRITICAL: -1000,  # Daily loss critical
                AlertLevel.EMERGENCY: -2000  # Daily loss emergency
            },
            MonitoringMetric.WIN_RATE: {
                AlertLevel.WARNING: 35.0,    # Below 35% win rate
                AlertLevel.CRITICAL: 25.0,   # Below 25% win rate
                AlertLevel.EMERGENCY: 15.0   # Below 15% win rate
            },
            MonitoringMetric.DRAWDOWN: {
                AlertLevel.WARNING: -0.03,   # 3% drawdown
                AlertLevel.CRITICAL: -0.05,  # 5% drawdown
                AlertLevel.EMERGENCY: -0.08  # 8% drawdown
            },
            MonitoringMetric.SHARPE_RATIO: {
                AlertLevel.WARNING: 0.5,     # Below 0.5 Sharpe
                AlertLevel.CRITICAL: 0.2,    # Below 0.2 Sharpe
                AlertLevel.EMERGENCY: -0.1   # Negative Sharpe
            },
            MonitoringMetric.CONSECUTIVE_LOSSES: {
                AlertLevel.WARNING: 5,       # 5 consecutive losses
                AlertLevel.CRITICAL: 8,      # 8 consecutive losses
                AlertLevel.EMERGENCY: 12     # 12 consecutive losses
            },
            MonitoringMetric.TRADE_FREQUENCY: {
                AlertLevel.WARNING: 20,      # More than 20 trades/day
                AlertLevel.CRITICAL: 30,     # More than 30 trades/day
                AlertLevel.EMERGENCY: 50     # More than 50 trades/day
            }
        }

        # Performance baselines (from historical analysis)
        self.baselines = {
            'expected_daily_pnl': 400,
            'expected_win_rate': 45.8,
            'max_acceptable_drawdown': -0.05,
            'target_sharpe_ratio': 1.5,
            'normal_trade_frequency': 8
        }

        # Alert callbacks
        self.alert_callbacks: List[Callable] = []

    def start_monitoring(self):
        """Start real-time monitoring"""
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return

        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Real-time performance monitoring started")

    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Real-time performance monitoring stopped")

    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add callback function for alerts"""
        self.alert_callbacks.append(callback)

    def record_trade(self, trade_data: Dict):
        """Record a completed trade for monitoring"""
        trade_record = {
            'timestamp': datetime.utcnow(),
            'pnl': trade_data.get('pnl', 0),
            'instrument': trade_data.get('instrument', 'Unknown'),
            'trade_type': trade_data.get('trade_type', 'Unknown'),
            'risk_reward': trade_data.get('risk_reward', 0),
            'session': trade_data.get('session', 'Unknown'),
            'confidence': trade_data.get('confidence', 0)
        }

        self.trade_history.append(trade_record)

        # Trigger immediate performance check
        asyncio.create_task(self._check_performance_immediately())

        logger.debug(f"Trade recorded: {trade_record['instrument']} PnL: {trade_record['pnl']}")

    async def _check_performance_immediately(self):
        """Immediate performance check after trade"""
        try:
            # Update current snapshot
            snapshot = self._calculate_current_snapshot()
            self.current_snapshot = snapshot

            # Check all metrics for alerts
            await self._check_all_metrics(snapshot)

            # Update daily snapshot if end of day
            await self._maybe_update_daily_snapshot(snapshot)

        except Exception as e:
            logger.error(f"Immediate performance check failed: {str(e)}")

    def _monitoring_loop(self):
        """Main monitoring loop (runs in background thread)"""
        while self.is_monitoring:
            try:
                # Update performance snapshot
                snapshot = self._calculate_current_snapshot()
                self.current_snapshot = snapshot

                # Run async monitoring checks
                asyncio.run(self._run_monitoring_checks(snapshot))

                # Sleep for monitoring interval
                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Monitoring loop error: {str(e)}")
                time.sleep(30)  # Shorter sleep on error

    async def _run_monitoring_checks(self, snapshot: PerformanceSnapshot):
        """Run all monitoring checks"""
        await self._check_all_metrics(snapshot)
        await self._check_performance_trends()
        await self._check_regime_consistency()
        await self._maybe_update_daily_snapshot(snapshot)

    def _calculate_current_snapshot(self) -> PerformanceSnapshot:
        """Calculate current performance snapshot"""
        now = datetime.utcnow()
        today = now.date()

        # Filter today's trades
        today_trades = [
            trade for trade in self.trade_history
            if trade['timestamp'].date() == today
        ]

        # Calculate metrics
        daily_pnl = sum(trade['pnl'] for trade in today_trades)
        cumulative_pnl = sum(trade['pnl'] for trade in self.trade_history)

        # Win rate calculation
        if today_trades:
            winning_trades = [trade for trade in today_trades if trade['pnl'] > 0]
            win_rate = len(winning_trades) / len(today_trades) * 100
        else:
            win_rate = 0

        # Drawdown calculation
        if self.trade_history:
            pnl_series = pd.Series([trade['pnl'] for trade in self.trade_history])
            cumulative_pnl_series = pnl_series.cumsum()
            running_max = cumulative_pnl_series.expanding().max()
            drawdown_series = cumulative_pnl_series - running_max
            current_drawdown = drawdown_series.iloc[-1] / (abs(running_max.iloc[-1]) + 1e-6)
            max_drawdown = drawdown_series.min() / (abs(running_max[drawdown_series.idxmin()]) + 1e-6)
        else:
            current_drawdown = 0
            max_drawdown = 0

        # Sharpe ratio (last 30 trades)
        recent_trades = list(self.trade_history)[-30:] if len(self.trade_history) >= 30 else list(self.trade_history)
        if recent_trades:
            recent_pnl = [trade['pnl'] for trade in recent_trades]
            mean_pnl = np.mean(recent_pnl)
            std_pnl = np.std(recent_pnl)
            sharpe_ratio = mean_pnl / std_pnl if std_pnl > 0 else 0
        else:
            sharpe_ratio = 0

        # Consecutive losses
        consecutive_losses = self._calculate_consecutive_losses()

        # Average risk-reward
        if today_trades:
            risk_rewards = [trade.get('risk_reward', 0) for trade in today_trades if trade.get('risk_reward', 0) > 0]
            avg_risk_reward = np.mean(risk_rewards) if risk_rewards else 0
        else:
            avg_risk_reward = 0

        # Volatility (standard deviation of recent returns)
        if len(self.trade_history) >= 20:
            recent_pnl = [trade['pnl'] for trade in list(self.trade_history)[-20:]]
            volatility = np.std(recent_pnl)
        else:
            volatility = 0

        # Regime consistency (simplified measure)
        regime_consistency = self._calculate_regime_consistency()

        return PerformanceSnapshot(
            timestamp=now,
            daily_pnl=daily_pnl,
            cumulative_pnl=cumulative_pnl,
            win_rate=win_rate,
            current_drawdown=current_drawdown,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trade_count_today=len(today_trades),
            consecutive_losses=consecutive_losses,
            avg_risk_reward=avg_risk_reward,
            volatility=volatility,
            regime_consistency=regime_consistency
        )

    def _calculate_consecutive_losses(self) -> int:
        """Calculate consecutive losses from end of trade history"""
        consecutive_losses = 0

        for trade in reversed(list(self.trade_history)):
            if trade['pnl'] <= 0:
                consecutive_losses += 1
            else:
                break

        return consecutive_losses

    def _calculate_regime_consistency(self) -> float:
        """Calculate regime consistency score"""
        if len(self.trade_history) < 10:
            return 0.5

        # Group recent trades by session
        recent_trades = list(self.trade_history)[-20:]
        session_performance = {}

        for trade in recent_trades:
            session = trade.get('session', 'Unknown')
            if session not in session_performance:
                session_performance[session] = []
            session_performance[session].append(trade['pnl'])

        # Calculate consistency across sessions
        session_avgs = []
        for session, pnls in session_performance.items():
            if len(pnls) >= 3:  # Minimum trades per session
                session_avgs.append(np.mean(pnls))

        if len(session_avgs) < 2:
            return 0.5

        # Consistency based on standard deviation of session averages
        consistency = 1 - (np.std(session_avgs) / (np.mean(np.abs(session_avgs)) + 1e-6))
        return max(0, min(1, consistency))

    async def _check_all_metrics(self, snapshot: PerformanceSnapshot):
        """Check all metrics against thresholds"""

        # Daily P&L check
        await self._check_metric(
            MonitoringMetric.DAILY_PNL,
            snapshot.daily_pnl,
            f"Daily P&L: ${snapshot.daily_pnl:.2f}",
            snapshot
        )

        # Win rate check (invert logic - lower values trigger alerts)
        await self._check_metric_inverted(
            MonitoringMetric.WIN_RATE,
            snapshot.win_rate,
            f"Win Rate: {snapshot.win_rate:.1f}%",
            snapshot
        )

        # Drawdown check (invert logic - more negative values trigger alerts)
        await self._check_metric_inverted(
            MonitoringMetric.DRAWDOWN,
            snapshot.current_drawdown,
            f"Current Drawdown: {snapshot.current_drawdown:.2%}",
            snapshot
        )

        # Sharpe ratio check (invert logic - lower values trigger alerts)
        await self._check_metric_inverted(
            MonitoringMetric.SHARPE_RATIO,
            snapshot.sharpe_ratio,
            f"Sharpe Ratio: {snapshot.sharpe_ratio:.2f}",
            snapshot
        )

        # Consecutive losses check
        await self._check_metric(
            MonitoringMetric.CONSECUTIVE_LOSSES,
            snapshot.consecutive_losses,
            f"Consecutive Losses: {snapshot.consecutive_losses}",
            snapshot
        )

        # Trade frequency check
        await self._check_metric(
            MonitoringMetric.TRADE_FREQUENCY,
            snapshot.trade_count_today,
            f"Daily Trade Count: {snapshot.trade_count_today}",
            snapshot
        )

    async def _check_metric(self, metric: MonitoringMetric, value: float, description: str, snapshot: PerformanceSnapshot):
        """Check metric against thresholds (higher values trigger alerts)"""

        if metric not in self.thresholds:
            return

        thresholds = self.thresholds[metric]

        # Check emergency level first (highest severity)
        if AlertLevel.EMERGENCY in thresholds and value >= thresholds[AlertLevel.EMERGENCY]:
            await self._create_alert(metric, AlertLevel.EMERGENCY, value, thresholds[AlertLevel.EMERGENCY], description, snapshot)
        elif AlertLevel.CRITICAL in thresholds and value >= thresholds[AlertLevel.CRITICAL]:
            await self._create_alert(metric, AlertLevel.CRITICAL, value, thresholds[AlertLevel.CRITICAL], description, snapshot)
        elif AlertLevel.WARNING in thresholds and value >= thresholds[AlertLevel.WARNING]:
            await self._create_alert(metric, AlertLevel.WARNING, value, thresholds[AlertLevel.WARNING], description, snapshot)

    async def _check_metric_inverted(self, metric: MonitoringMetric, value: float, description: str, snapshot: PerformanceSnapshot):
        """Check metric against thresholds (lower values trigger alerts)"""

        if metric not in self.thresholds:
            return

        thresholds = self.thresholds[metric]

        # Check emergency level first (lowest value)
        if AlertLevel.EMERGENCY in thresholds and value <= thresholds[AlertLevel.EMERGENCY]:
            await self._create_alert(metric, AlertLevel.EMERGENCY, value, thresholds[AlertLevel.EMERGENCY], description, snapshot)
        elif AlertLevel.CRITICAL in thresholds and value <= thresholds[AlertLevel.CRITICAL]:
            await self._create_alert(metric, AlertLevel.CRITICAL, value, thresholds[AlertLevel.CRITICAL], description, snapshot)
        elif AlertLevel.WARNING in thresholds and value <= thresholds[AlertLevel.WARNING]:
            await self._create_alert(metric, AlertLevel.WARNING, value, thresholds[AlertLevel.WARNING], description, snapshot)

    async def _create_alert(self, metric: MonitoringMetric, level: AlertLevel, current_value: float, threshold_value: float, message: str, snapshot: PerformanceSnapshot):
        """Create and process performance alert"""

        # Generate recommended action
        recommended_action = self._get_recommended_action(metric, level, current_value, snapshot)

        alert = PerformanceAlert(
            metric=metric,
            level=level,
            current_value=current_value,
            threshold_value=threshold_value,
            message=message,
            recommended_action=recommended_action,
            trade_context={
                'daily_pnl': snapshot.daily_pnl,
                'cumulative_pnl': snapshot.cumulative_pnl,
                'win_rate': snapshot.win_rate,
                'consecutive_losses': snapshot.consecutive_losses,
                'trade_count_today': snapshot.trade_count_today
            }
        )

        self.alerts.append(alert)

        # Log alert
        logger.log(
            logging.CRITICAL if level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY] else logging.WARNING,
            f"PERFORMANCE ALERT [{level.value.upper()}] {metric.value}: {message} | Action: {recommended_action}"
        )

        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {str(e)}")

        # Auto-execute emergency actions
        if level == AlertLevel.EMERGENCY:
            await self._execute_emergency_action(alert)

    def _get_recommended_action(self, metric: MonitoringMetric, level: AlertLevel, current_value: float, snapshot: PerformanceSnapshot) -> str:
        """Get recommended action for alert"""

        if level == AlertLevel.EMERGENCY:
            if metric == MonitoringMetric.DAILY_PNL:
                return "HALT_TRADING_IMMEDIATELY"
            elif metric == MonitoringMetric.DRAWDOWN:
                return "EMERGENCY_ROLLBACK_TO_CONSERVATIVE"
            elif metric == MonitoringMetric.CONSECUTIVE_LOSSES:
                return "STOP_TRADING_FOR_24H"
            elif metric == MonitoringMetric.WIN_RATE:
                return "EMERGENCY_PARAMETER_REVIEW"
            else:
                return "EMERGENCY_SYSTEM_REVIEW"

        elif level == AlertLevel.CRITICAL:
            if metric == MonitoringMetric.DAILY_PNL:
                return "REDUCE_POSITION_SIZE_50%"
            elif metric == MonitoringMetric.DRAWDOWN:
                return "SWITCH_TO_CONSERVATIVE_PARAMETERS"
            elif metric == MonitoringMetric.WIN_RATE:
                return "INCREASE_SELECTIVITY_20%"
            elif metric == MonitoringMetric.CONSECUTIVE_LOSSES:
                return "PAUSE_TRADING_2H"
            else:
                return "REVIEW_TRADING_CONDITIONS"

        elif level == AlertLevel.WARNING:
            if metric == MonitoringMetric.DAILY_PNL:
                return "MONITOR_CLOSELY_REDUCE_RISK"
            elif metric == MonitoringMetric.WIN_RATE:
                return "REVIEW_SIGNAL_QUALITY"
            elif metric == MonitoringMetric.TRADE_FREQUENCY:
                return "REDUCE_TRADE_FREQUENCY"
            else:
                return "INCREASE_MONITORING_FREQUENCY"

        return "REVIEW_PERFORMANCE"

    async def _execute_emergency_action(self, alert: PerformanceAlert):
        """Execute emergency actions automatically"""

        action = alert.recommended_action

        if action == "HALT_TRADING_IMMEDIATELY":
            # This would integrate with trading system to halt
            logger.critical("EMERGENCY: Trading halted due to excessive daily losses")
            # await self._halt_trading()

        elif action == "EMERGENCY_ROLLBACK_TO_CONSERVATIVE":
            logger.critical("EMERGENCY: Switching to conservative parameters")
            # await self._switch_to_emergency_parameters()

        elif action == "STOP_TRADING_FOR_24H":
            logger.critical("EMERGENCY: Trading stopped for 24 hours due to consecutive losses")
            # await self._pause_trading(hours=24)

        # Note: Actual implementation would integrate with trading system
        logger.info(f"Emergency action would be executed: {action}")

    async def _check_performance_trends(self):
        """Check performance trends over time"""

        if len(self.daily_snapshots) < 7:
            return

        # Check for declining performance trend
        recent_snapshots = list(self.daily_snapshots)[-7:]  # Last 7 days
        daily_pnls = [snapshot.daily_pnl for snapshot in recent_snapshots]

        # Simple trend analysis
        if len(daily_pnls) >= 5:
            # Check if last 3 days are all negative
            last_3_days = daily_pnls[-3:]
            if all(pnl < 0 for pnl in last_3_days):
                await self._create_trend_alert("3 consecutive negative days detected")

            # Check if weekly performance is significantly below baseline
            weekly_pnl = sum(daily_pnls)
            expected_weekly_pnl = self.baselines['expected_daily_pnl'] * 7

            if weekly_pnl < expected_weekly_pnl * 0.3:  # Less than 30% of expected
                await self._create_trend_alert(f"Weekly performance {weekly_pnl:.0f} significantly below expected {expected_weekly_pnl:.0f}")

    async def _create_trend_alert(self, message: str):
        """Create trend-based alert"""

        alert = PerformanceAlert(
            metric=MonitoringMetric.DAILY_PNL,  # Use as proxy for trend
            level=AlertLevel.WARNING,
            current_value=0,
            threshold_value=0,
            message=f"TREND ALERT: {message}",
            recommended_action="REVIEW_RECENT_PERFORMANCE_TRENDS"
        )

        self.alerts.append(alert)
        logger.warning(f"Performance trend alert: {message}")

    async def _check_regime_consistency(self):
        """Check for regime consistency issues"""

        if self.current_snapshot and self.current_snapshot.regime_consistency < 0.3:
            alert = PerformanceAlert(
                metric=MonitoringMetric.REGIME_CONSISTENCY,
                level=AlertLevel.WARNING,
                current_value=self.current_snapshot.regime_consistency,
                threshold_value=0.3,
                message=f"Low regime consistency: {self.current_snapshot.regime_consistency:.2f}",
                recommended_action="REVIEW_SESSION_PARAMETERS"
            )

            self.alerts.append(alert)
            logger.warning("Regime consistency alert triggered")

    async def _maybe_update_daily_snapshot(self, snapshot: PerformanceSnapshot):
        """Update daily snapshot if it's a new day"""

        if not self.daily_snapshots or self.daily_snapshots[-1].timestamp.date() != snapshot.timestamp.date():
            # Create end-of-day snapshot with final values
            daily_snapshot = PerformanceSnapshot(
                timestamp=snapshot.timestamp.replace(hour=23, minute=59, second=59),
                daily_pnl=snapshot.daily_pnl,
                cumulative_pnl=snapshot.cumulative_pnl,
                win_rate=snapshot.win_rate,
                current_drawdown=snapshot.current_drawdown,
                max_drawdown=max(snapshot.max_drawdown, self.daily_snapshots[-1].max_drawdown if self.daily_snapshots else 0),
                sharpe_ratio=snapshot.sharpe_ratio,
                trade_count_today=snapshot.trade_count_today,
                consecutive_losses=snapshot.consecutive_losses,
                avg_risk_reward=snapshot.avg_risk_reward,
                volatility=snapshot.volatility,
                regime_consistency=snapshot.regime_consistency
            )

            self.daily_snapshots.append(daily_snapshot)
            logger.info(f"Daily snapshot saved: P&L ${snapshot.daily_pnl:.2f}, Trades: {snapshot.trade_count_today}")

    def get_current_status(self) -> Dict:
        """Get current monitoring status"""

        if not self.current_snapshot:
            return {'status': 'no_data'}

        recent_alerts = [alert for alert in self.alerts if alert.timestamp > datetime.utcnow() - timedelta(hours=24)]
        critical_alerts = [alert for alert in recent_alerts if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]]

        return {
            'timestamp': self.current_snapshot.timestamp.isoformat(),
            'is_monitoring': self.is_monitoring,
            'performance': {
                'daily_pnl': self.current_snapshot.daily_pnl,
                'cumulative_pnl': self.current_snapshot.cumulative_pnl,
                'win_rate': self.current_snapshot.win_rate,
                'current_drawdown': self.current_snapshot.current_drawdown,
                'sharpe_ratio': self.current_snapshot.sharpe_ratio,
                'trade_count_today': self.current_snapshot.trade_count_today,
                'consecutive_losses': self.current_snapshot.consecutive_losses,
                'avg_risk_reward': self.current_snapshot.avg_risk_reward
            },
            'alerts': {
                'total_24h': len(recent_alerts),
                'critical_24h': len(critical_alerts),
                'latest_critical': critical_alerts[-1].message if critical_alerts else None
            },
            'status': 'healthy' if not critical_alerts else 'critical'
        }

    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts"""

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_alerts = [alert for alert in self.alerts if alert.timestamp > cutoff]

        return [
            {
                'timestamp': alert.timestamp.isoformat(),
                'metric': alert.metric.value,
                'level': alert.level.value,
                'message': alert.message,
                'recommended_action': alert.recommended_action,
                'current_value': alert.current_value,
                'threshold_value': alert.threshold_value
            }
            for alert in sorted(recent_alerts, key=lambda x: x.timestamp, reverse=True)
        ]

    def save_monitoring_data(self, filepath: str):
        """Save monitoring data for analysis"""

        data = {
            'daily_snapshots': [
                {
                    'timestamp': snapshot.timestamp.isoformat(),
                    'daily_pnl': snapshot.daily_pnl,
                    'cumulative_pnl': snapshot.cumulative_pnl,
                    'win_rate': snapshot.win_rate,
                    'current_drawdown': snapshot.current_drawdown,
                    'max_drawdown': snapshot.max_drawdown,
                    'trade_count': snapshot.trade_count_today,
                    'sharpe_ratio': snapshot.sharpe_ratio
                }
                for snapshot in self.daily_snapshots
            ],
            'recent_alerts': self.get_recent_alerts(hours=24 * 7),  # Last week
            'thresholds': {
                metric.value: {level.value: threshold for level, threshold in thresholds.items()}
                for metric, thresholds in self.thresholds.items()
            }
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Monitoring data saved to {filepath}")

# Example usage and integration
def example_alert_callback(alert: PerformanceAlert):
    """Example alert callback function"""
    print(f"🚨 ALERT: {alert.level.value.upper()} - {alert.message}")
    print(f"   Recommended Action: {alert.recommended_action}")

    if alert.level == AlertLevel.EMERGENCY:
        print("   🚨 EMERGENCY ACTION REQUIRED!")

async def main():
    """Example usage of real-time performance monitor"""

    config = {
        'monitoring_interval': 60,
        'alert_history_size': 500
    }

    monitor = RealTimePerformanceMonitor(config)
    monitor.add_alert_callback(example_alert_callback)

    # Start monitoring
    monitor.start_monitoring()

    # Simulate some trades
    test_trades = [
        {'pnl': 150, 'instrument': 'EUR_USD', 'session': 'London', 'confidence': 75},
        {'pnl': -80, 'instrument': 'GBP_USD', 'session': 'London', 'confidence': 65},
        {'pnl': 220, 'instrument': 'USD_JPY', 'session': 'Tokyo', 'confidence': 85},
        {'pnl': -120, 'instrument': 'AUD_USD', 'session': 'Sydney', 'confidence': 70},
        {'pnl': -90, 'instrument': 'USD_CHF', 'session': 'NY', 'confidence': 60}
    ]

    for trade in test_trades:
        monitor.record_trade(trade)
        await asyncio.sleep(1)  # Small delay between trades

    # Let it run for a bit
    await asyncio.sleep(5)

    # Get status
    status = monitor.get_current_status()
    print(f"\nCurrent Status: {status}")

    # Get recent alerts
    alerts = monitor.get_recent_alerts()
    print(f"\nRecent Alerts: {len(alerts)}")

    # Stop monitoring
    monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())