"""
Correlation Monitor - Real-time tracking of account correlations.
Implements AC6: Correlation coefficient maintained below 0.7 between any two accounts.
"""
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, deque

from .models import (
    CorrelationAlert, CorrelationDataPoint, AccountPair, 
    CorrelationThresholds, AlertSeverity, CorrelationAdjustmentStrategy
)

logger = logging.getLogger(__name__)


class CorrelationMonitor:
    """
    Real-time correlation monitoring system.
    
    Tracks correlation coefficients between account pairs and triggers
    alerts when thresholds are exceeded.
    """
    
    def __init__(self, correlation_window: int = 100):
        self.correlation_window = correlation_window
        self.thresholds = CorrelationThresholds()
        
        # Data storage
        self.account_pairs: List[AccountPair] = []
        self.trade_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=correlation_window))
        self.current_correlations: Dict[str, float] = {}
        self.correlation_history: List[CorrelationDataPoint] = []
        self.alerts: List[CorrelationAlert] = []
        
        # Adjustment strategies
        self.adjustment_strategies: List[CorrelationAdjustmentStrategy] = [
            CorrelationAdjustmentStrategy(
                name="force_disagreement",
                description="Force one account to skip or modify signal",
                trigger_threshold=0.65,
                adjustment_strength=0.8
            ),
            CorrelationAdjustmentStrategy(
                name="timing_spread",
                description="Increase timing spread between entries",
                trigger_threshold=0.6,
                adjustment_strength=0.5
            ),
            CorrelationAdjustmentStrategy(
                name="size_variance",
                description="Increase position size variance",
                trigger_threshold=0.6,
                adjustment_strength=0.3
            )
        ]
        
        self.last_update = datetime.utcnow()
        logger.info(f"CorrelationMonitor initialized with {correlation_window}-trade window")

    def register_account_pairs(self, account_ids: List[str]) -> None:
        """Register all possible account pairs for monitoring."""
        self.account_pairs = []
        
        for i, account1 in enumerate(account_ids):
            for account2 in account_ids[i+1:]:
                pair = AccountPair(
                    account1_id=account1,
                    account2_id=account2,
                    pair_id=f"{account1}_{account2}"
                )
                self.account_pairs.append(pair)
        
        logger.info(f"Registered {len(self.account_pairs)} account pairs for correlation monitoring")

    def record_trade_outcome(self, account_id: str, return_pct: float, timestamp: datetime) -> None:
        """Record a trade outcome for correlation calculation."""
        trade_data = {
            'timestamp': timestamp,
            'return_pct': return_pct,
            'account_id': account_id
        }
        
        self.trade_history[account_id].append(trade_data)
        logger.debug(f"Recorded trade for {account_id}: {return_pct:.2%} return")

    def update_correlations(self) -> Dict[str, float]:
        """Update correlation calculations for all account pairs."""
        logger.debug("Updating correlation calculations")
        
        new_correlations = {}
        alerts_generated = []
        
        for pair in self.account_pairs:
            correlation = self._calculate_pair_correlation(pair)
            
            if correlation is not None:
                new_correlations[pair.pair_id] = correlation
                
                # Record historical data point
                self._record_correlation_datapoint(pair, correlation)
                
                # Check for threshold violations
                alert = self._check_correlation_thresholds(pair, correlation)
                if alert:
                    alerts_generated.append(alert)
        
        self.current_correlations = new_correlations
        self.alerts.extend(alerts_generated)
        self.last_update = datetime.utcnow()
        
        if alerts_generated:
            logger.warning(f"Generated {len(alerts_generated)} correlation alerts")
        
        logger.info(f"Updated correlations for {len(new_correlations)} pairs")
        return new_correlations

    def get_current_correlations(self) -> Dict[str, float]:
        """Get current correlation coefficients."""
        return self.current_correlations.copy()

    def get_high_correlation_pairs(self, threshold: float = 0.65) -> List[Tuple[str, float]]:
        """Get account pairs with correlation above threshold."""
        high_pairs = [
            (pair_id, corr) for pair_id, corr in self.current_correlations.items()
            if corr > threshold
        ]
        
        if high_pairs:
            logger.info(f"Found {len(high_pairs)} pairs above {threshold:.2f} threshold")
        
        return high_pairs

    def get_recent_alerts(self, hours: int = 24) -> List[CorrelationAlert]:
        """Get correlation alerts from the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_alerts = [alert for alert in self.alerts if alert.timestamp >= cutoff]
        
        logger.debug(f"Retrieved {len(recent_alerts)} alerts from last {hours} hours")
        return recent_alerts

    def trigger_emergency_protocols(self) -> List[str]:
        """Trigger emergency protocols for critical correlations."""
        critical_pairs = [
            (pair_id, corr) for pair_id, corr in self.current_correlations.items()
            if corr >= self.thresholds.emergency
        ]
        
        if not critical_pairs:
            return []
        
        logger.critical(f"EMERGENCY: {len(critical_pairs)} pairs exceed {self.thresholds.emergency:.2f} correlation")
        
        emergency_actions = []
        for pair_id, correlation in critical_pairs:
            account1, account2 = pair_id.split('_')
            
            # Force immediate disagreement
            action = f"HALT_TRADING_PAIR_{account1}_{account2}"
            emergency_actions.append(action)
            
            # Generate critical alert
            alert = CorrelationAlert(
                account_pair=pair_id,
                correlation=correlation,
                severity=AlertSeverity.EMERGENCY,
                recommended_action="Halt coordinated trading immediately"
            )
            self.alerts.append(alert)
        
        return emergency_actions

    def _calculate_pair_correlation(self, pair: AccountPair) -> Optional[float]:
        """Calculate correlation coefficient between two accounts."""
        account1_trades = self.trade_history.get(pair.account1_id, deque())
        account2_trades = self.trade_history.get(pair.account2_id, deque())
        
        if len(account1_trades) < 10 or len(account2_trades) < 10:
            logger.debug(f"Insufficient data for pair {pair.pair_id}: "
                        f"{len(account1_trades)}/{len(account2_trades)} trades")
            return None
        
        # Align trades by timestamp (within 1-hour window)
        aligned_returns1, aligned_returns2 = self._align_trade_returns(
            list(account1_trades), list(account2_trades)
        )
        
        if len(aligned_returns1) < 5:
            logger.debug(f"Insufficient aligned trades for {pair.pair_id}: {len(aligned_returns1)}")
            return None
        
        # Calculate correlation coefficient
        try:
            correlation = np.corrcoef(aligned_returns1, aligned_returns2)[0, 1]
            
            # Handle NaN results
            if np.isnan(correlation):
                logger.warning(f"NaN correlation for {pair.pair_id}")
                return 0.0
            
            logger.debug(f"Calculated correlation for {pair.pair_id}: {correlation:.3f}")
            return float(correlation)
            
        except Exception as e:
            logger.error(f"Error calculating correlation for {pair.pair_id}: {e}")
            return None

    def _align_trade_returns(
        self, 
        trades1: List[Dict], 
        trades2: List[Dict],
        time_window_hours: int = 1
    ) -> Tuple[List[float], List[float]]:
        """Align trade returns between two accounts within time window."""
        aligned_returns1 = []
        aligned_returns2 = []
        time_window = timedelta(hours=time_window_hours)
        
        # Create time-indexed lookups
        trades2_by_time = {trade['timestamp']: trade for trade in trades2}
        
        for trade1 in trades1:
            timestamp1 = trade1['timestamp']
            
            # Find matching trade in account2 within time window
            best_match = None
            best_time_diff = time_window
            
            for trade2 in trades2:
                timestamp2 = trade2['timestamp']
                time_diff = abs(timestamp1 - timestamp2)
                
                if time_diff <= time_window and time_diff < best_time_diff:
                    best_match = trade2
                    best_time_diff = time_diff
            
            if best_match:
                aligned_returns1.append(trade1['return_pct'])
                aligned_returns2.append(best_match['return_pct'])
        
        logger.debug(f"Aligned {len(aligned_returns1)} trade pairs from "
                    f"{len(trades1)}/{len(trades2)} total trades")
        
        return aligned_returns1, aligned_returns2

    def _record_correlation_datapoint(self, pair: AccountPair, correlation: float) -> None:
        """Record a correlation data point for historical tracking."""
        # Count recent signals for this period
        signal_count = min(len(self.trade_history[pair.account1_id]), 
                          len(self.trade_history[pair.account2_id]))
        
        # Calculate agreement rate (simplified)
        agreement_rate = (correlation + 1.0) / 2.0  # Convert -1 to 1 range to 0 to 1
        
        datapoint = CorrelationDataPoint(
            timestamp=datetime.utcnow(),
            account_pair=pair.pair_id,
            correlation=correlation,
            signal_count=signal_count,
            agreement_rate=agreement_rate
        )
        
        self.correlation_history.append(datapoint)
        
        # Limit history size
        if len(self.correlation_history) > 10000:
            self.correlation_history = self.correlation_history[-5000:]

    def _check_correlation_thresholds(
        self, 
        pair: AccountPair, 
        correlation: float
    ) -> Optional[CorrelationAlert]:
        """Check if correlation exceeds thresholds and generate alerts."""
        
        if correlation >= self.thresholds.emergency:
            severity = AlertSeverity.EMERGENCY
            action = "Halt coordinated trading immediately"
        elif correlation >= self.thresholds.critical:
            severity = AlertSeverity.CRITICAL
            action = "Force immediate disagreement on next signal"
        elif correlation >= self.thresholds.warning:
            severity = AlertSeverity.WARNING
            action = "Increase disagreement rate and timing spread"
        else:
            return None
        
        alert = CorrelationAlert(
            account_pair=pair.pair_id,
            correlation=correlation,
            severity=severity,
            recommended_action=action
        )
        
        logger.warning(f"{severity.value.upper()} correlation alert: {pair.pair_id} = {correlation:.3f}")
        return alert

    def get_correlation_statistics(self) -> Dict[str, float]:
        """Get summary statistics about current correlations."""
        if not self.current_correlations:
            return {}
        
        correlations = list(self.current_correlations.values())
        
        return {
            "mean_correlation": np.mean(correlations),
            "max_correlation": np.max(correlations),
            "min_correlation": np.min(correlations),
            "std_correlation": np.std(correlations),
            "pairs_above_warning": sum(1 for c in correlations if c > self.thresholds.warning),
            "pairs_above_critical": sum(1 for c in correlations if c > self.thresholds.critical),
            "total_pairs": len(correlations)
        }

    def cleanup_old_data(self, days: int = 30) -> None:
        """Clean up old correlation history and alerts."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Clean correlation history
        old_count = len(self.correlation_history)
        self.correlation_history = [
            dp for dp in self.correlation_history 
            if dp.timestamp >= cutoff
        ]
        
        # Clean old alerts
        old_alert_count = len(self.alerts)
        self.alerts = [
            alert for alert in self.alerts
            if alert.timestamp >= cutoff
        ]
        
        logger.info(f"Cleaned up {old_count - len(self.correlation_history)} old correlation points "
                   f"and {old_alert_count - len(self.alerts)} old alerts")