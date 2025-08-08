"""
Static drawdown monitoring for Funding Pips compliance.
Unlike trailing drawdown, static drawdown is calculated from initial balance.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import asyncio
import logging
from enum import Enum

from pydantic import BaseModel

from .models import Account, Trade, Position

logger = logging.getLogger(__name__)


class DrawdownSeverity(Enum):
    """Drawdown severity levels."""
    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    VIOLATION = "violation"


class DrawdownAlert(BaseModel):
    """Drawdown alert model."""
    account_id: str
    current_drawdown: Decimal
    drawdown_percentage: float
    severity: DrawdownSeverity
    message: str
    timestamp: datetime
    requires_immediate_action: bool
    projected_violation_time: Optional[datetime] = None


class StaticDrawdownMonitor:
    """
    Monitors static drawdown for Funding Pips accounts.
    
    Static drawdown = (Initial Balance - Current Equity) / Initial Balance
    Maximum allowed: 8% of initial balance
    """
    
    def __init__(self):
        self.max_drawdown = Decimal('0.08')  # 8% maximum drawdown
        self.warning_thresholds = {
            DrawdownSeverity.CAUTION: Decimal('0.05'),   # 5% - 62.5% of limit
            DrawdownSeverity.WARNING: Decimal('0.065'),  # 6.5% - 81.25% of limit
            DrawdownSeverity.CRITICAL: Decimal('0.076'), # 7.6% - 95% of limit
        }
        self.blocked_accounts = set()
        self.monitoring_active = {}  # account_id -> monitoring_data
        self.historical_peaks = {}   # account_id -> peak_equity
        
    async def monitor_drawdown(self, account: Account) -> Optional[DrawdownAlert]:
        """
        Monitor static drawdown continuously.
        
        Args:
            account: Trading account to monitor
            
        Returns:
            Alert if drawdown thresholds are breached
        """
        current_drawdown = self._calculate_static_drawdown(account)
        drawdown_percentage = float(current_drawdown * 100)
        
        # Update historical peak tracking
        current_equity = account.balance + account.unrealized_pnl
        if account.account_id not in self.historical_peaks:
            self.historical_peaks[account.account_id] = current_equity
        else:
            self.historical_peaks[account.account_id] = max(
                self.historical_peaks[account.account_id], 
                current_equity
            )
        
        # Check severity level
        severity = self._determine_severity(current_drawdown)
        
        # Create alert if needed
        if severity != DrawdownSeverity.SAFE:
            alert = DrawdownAlert(
                account_id=account.account_id,
                current_drawdown=current_drawdown,
                drawdown_percentage=drawdown_percentage,
                severity=severity,
                message=self._generate_alert_message(severity, drawdown_percentage),
                timestamp=datetime.utcnow(),
                requires_immediate_action=(severity in [DrawdownSeverity.CRITICAL, DrawdownSeverity.VIOLATION]),
                projected_violation_time=self._estimate_violation_time(account, current_drawdown)
            )
            
            # Handle critical situations
            if severity == DrawdownSeverity.VIOLATION:
                self.blocked_accounts.add(account.account_id)
                await self._trigger_emergency_procedures(account, alert)
            elif severity == DrawdownSeverity.CRITICAL:
                await self._trigger_risk_reduction(account, alert)
            
            return alert
        
        return None
    
    def _calculate_static_drawdown(self, account: Account) -> Decimal:
        """
        Calculate static drawdown from initial balance.
        
        Static Drawdown = (Initial Balance - Current Equity) / Initial Balance
        """
        initial_balance = account.initial_balance
        current_equity = account.balance + account.unrealized_pnl
        
        if current_equity >= initial_balance:
            return Decimal('0.0')  # No drawdown if equity is above initial
        
        drawdown = (initial_balance - current_equity) / initial_balance
        return max(Decimal('0.0'), drawdown)
    
    def _determine_severity(self, drawdown: Decimal) -> DrawdownSeverity:
        """Determine drawdown severity based on thresholds."""
        if drawdown >= self.max_drawdown:
            return DrawdownSeverity.VIOLATION
        
        for severity, threshold in sorted(self.warning_thresholds.items(), 
                                        key=lambda x: x[1], reverse=True):
            if drawdown >= threshold:
                return severity
        
        return DrawdownSeverity.SAFE
    
    def _generate_alert_message(self, severity: DrawdownSeverity, drawdown_pct: float) -> str:
        """Generate appropriate alert message."""
        messages = {
            DrawdownSeverity.CAUTION: f"Static drawdown at {drawdown_pct:.2f}% - monitor closely",
            DrawdownSeverity.WARNING: f"Static drawdown at {drawdown_pct:.2f}% - reduce risk exposure",
            DrawdownSeverity.CRITICAL: f"CRITICAL: Static drawdown at {drawdown_pct:.2f}% - immediate risk reduction required",
            DrawdownSeverity.VIOLATION: f"VIOLATION: Static drawdown limit exceeded ({drawdown_pct:.2f}%) - trading blocked"
        }
        return messages.get(severity, f"Drawdown alert: {drawdown_pct:.2f}%")
    
    def _estimate_violation_time(self, account: Account, current_drawdown: Decimal) -> Optional[datetime]:
        """
        Estimate when drawdown limit might be reached based on current trend.
        
        Returns:
            Estimated datetime of violation, or None if trend is positive
        """
        if not hasattr(account, 'recent_pnl_changes') or not account.recent_pnl_changes:
            return None
        
        # Calculate average loss rate from recent changes
        recent_changes = account.recent_pnl_changes[-10:]  # Last 10 changes
        negative_changes = [change for change in recent_changes if change < 0]
        
        if not negative_changes:
            return None  # No negative trend
        
        avg_loss_rate = sum(negative_changes) / len(negative_changes)
        remaining_buffer = (self.max_drawdown - current_drawdown) * account.initial_balance
        
        if avg_loss_rate == 0:
            return None
        
        # Estimate time to violation (assuming loss rate continues)
        time_to_violation_hours = float(remaining_buffer / abs(avg_loss_rate))
        
        if time_to_violation_hours > 168:  # More than 1 week
            return None
        
        return datetime.utcnow() + timedelta(hours=time_to_violation_hours)
    
    async def _trigger_emergency_procedures(self, account: Account, alert: DrawdownAlert) -> None:
        """Trigger emergency procedures for drawdown violations."""
        logger.critical(f"EMERGENCY: Static drawdown violation for account {account.account_id}")
        
        # Block all new trades immediately
        self.blocked_accounts.add(account.account_id)
        
        # Log emergency action
        emergency_log = {
            'account_id': account.account_id,
            'trigger': 'static_drawdown_violation',
            'drawdown_percentage': alert.drawdown_percentage,
            'timestamp': datetime.utcnow(),
            'actions_taken': [
                'blocked_new_trades',
                'emergency_notification_sent',
                'immediate_review_required'
            ]
        }
        
        # TODO: Integrate with emergency notification system
        # TODO: Trigger immediate position review
        # TODO: Connect to circuit breaker system
        
        logger.critical(f"Emergency procedures activated: {emergency_log}")
    
    async def _trigger_risk_reduction(self, account: Account, alert: DrawdownAlert) -> None:
        """Trigger risk reduction measures for critical drawdown."""
        logger.warning(f"Risk reduction triggered for account {account.account_id}")
        
        # Implement risk reduction measures
        risk_measures = {
            'reduce_position_sizes': True,
            'tighten_stop_losses': True,
            'limit_new_trades': True,
            'increase_monitoring_frequency': True
        }
        
        # Store risk reduction state
        self.monitoring_active[account.account_id] = {
            'risk_reduction_active': True,
            'triggered_at': datetime.utcnow(),
            'measures': risk_measures,
            'drawdown_when_triggered': alert.drawdown_percentage
        }
        
        # TODO: Integrate with risk management system
        # TODO: Send alerts to dashboard
        
        logger.warning(f"Risk reduction measures activated: {risk_measures}")
    
    def validate_trade_impact(self, account: Account, trade: Trade) -> Tuple[bool, Optional[str]]:
        """
        Validate if trade would dangerously impact drawdown.
        
        Args:
            account: Trading account
            trade: Proposed trade
            
        Returns:
            Tuple of (trade_allowed, reason_if_rejected)
        """
        # Check if account is blocked
        if account.account_id in self.blocked_accounts:
            return (False, "Account blocked due to static drawdown violation")
        
        # Calculate current drawdown
        current_drawdown = self._calculate_static_drawdown(account)
        
        # Calculate potential additional loss from trade
        if not trade.stop_loss:
            return (False, "Stop loss required for drawdown calculation")
        
        potential_loss = abs(trade.entry_price - trade.stop_loss) * trade.position_size
        
        # Calculate projected drawdown if stop loss is hit
        projected_equity = (account.balance + account.unrealized_pnl) - potential_loss
        projected_drawdown = (account.initial_balance - projected_equity) / account.initial_balance
        
        # Check if trade would exceed limits
        if projected_drawdown >= self.max_drawdown:
            return (False, f"Trade would exceed static drawdown limit (projected: {projected_drawdown*100:.2f}%)")
        
        # Check if trade would push into critical zone
        if projected_drawdown >= self.warning_thresholds[DrawdownSeverity.CRITICAL]:
            return (False, f"Trade would create critical drawdown risk (projected: {projected_drawdown*100:.2f}%)")
        
        # Check if risk reduction is active
        if account.account_id in self.monitoring_active:
            risk_data = self.monitoring_active[account.account_id]
            if risk_data.get('risk_reduction_active', False):
                # Apply stricter limits during risk reduction
                if projected_drawdown >= self.warning_thresholds[DrawdownSeverity.WARNING]:
                    return (False, "Risk reduction active - trade exceeds reduced risk tolerance")
        
        return (True, None)
    
    def get_drawdown_status(self, account: Account) -> Dict[str, Any]:
        """
        Get current static drawdown status for dashboard.
        
        Returns:
            Comprehensive drawdown status dictionary
        """
        current_drawdown = self._calculate_static_drawdown(account)
        drawdown_percentage = float(current_drawdown * 100)
        max_drawdown_pct = float(self.max_drawdown * 100)
        
        # Determine status
        severity = self._determine_severity(current_drawdown)
        
        # Calculate remaining buffer
        remaining_buffer = max(0, max_drawdown_pct - drawdown_percentage)
        
        # Get historical peak
        peak_equity = self.historical_peaks.get(account.account_id, account.initial_balance)
        
        return {
            'type': 'static',
            'current_drawdown': drawdown_percentage,
            'max_allowed': max_drawdown_pct,
            'remaining_buffer': remaining_buffer,
            'severity': severity.value,
            'color': self._get_status_color(severity),
            'initial_balance': float(account.initial_balance),
            'current_equity': float(account.balance + account.unrealized_pnl),
            'peak_equity': float(peak_equity),
            'blocked': account.account_id in self.blocked_accounts,
            'risk_reduction_active': self._is_risk_reduction_active(account.account_id),
            'thresholds': {
                'caution': float(self.warning_thresholds[DrawdownSeverity.CAUTION] * 100),
                'warning': float(self.warning_thresholds[DrawdownSeverity.WARNING] * 100),
                'critical': float(self.warning_thresholds[DrawdownSeverity.CRITICAL] * 100),
            },
            'projected_violation': self._get_projected_violation_info(account),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _get_status_color(self, severity: DrawdownSeverity) -> str:
        """Get appropriate color for drawdown severity."""
        color_map = {
            DrawdownSeverity.SAFE: "green",
            DrawdownSeverity.CAUTION: "yellow",
            DrawdownSeverity.WARNING: "orange",
            DrawdownSeverity.CRITICAL: "red",
            DrawdownSeverity.VIOLATION: "dark-red"
        }
        return color_map.get(severity, "gray")
    
    def _is_risk_reduction_active(self, account_id: str) -> bool:
        """Check if risk reduction measures are active."""
        if account_id not in self.monitoring_active:
            return False
        return self.monitoring_active[account_id].get('risk_reduction_active', False)
    
    def _get_projected_violation_info(self, account: Account) -> Optional[Dict]:
        """Get projected violation information."""
        violation_time = self._estimate_violation_time(
            account, 
            self._calculate_static_drawdown(account)
        )
        
        if not violation_time:
            return None
        
        return {
            'estimated_time': violation_time.isoformat(),
            'hours_remaining': (violation_time - datetime.utcnow()).total_seconds() / 3600,
            'confidence': 'medium'  # Based on recent trend analysis
        }
    
    def get_recovery_metrics(self, account: Account) -> Dict[str, Any]:
        """
        Get drawdown recovery metrics.
        
        Returns:
            Recovery analysis and targets
        """
        current_drawdown = self._calculate_static_drawdown(account)
        current_equity = account.balance + account.unrealized_pnl
        
        # Recovery targets
        break_even_target = account.initial_balance
        recovery_needed = max(0, break_even_target - current_equity)
        
        # Calculate recovery percentage needed
        recovery_pct_needed = 0.0 if current_equity <= 0 else float(recovery_needed / current_equity * 100)
        
        return {
            'current_drawdown_pct': float(current_drawdown * 100),
            'recovery_needed_amount': float(recovery_needed),
            'recovery_percentage_needed': recovery_pct_needed,
            'break_even_target': float(break_even_target),
            'current_equity': float(current_equity),
            'recovery_difficulty': self._assess_recovery_difficulty(current_drawdown),
            'suggested_daily_target': float(recovery_needed / 30) if recovery_needed > 0 else 0.0,  # 30-day recovery
            'max_daily_risk_budget': float((self.max_drawdown - current_drawdown) * account.initial_balance * 0.2)  # 20% of remaining buffer
        }
    
    def _assess_recovery_difficulty(self, drawdown: Decimal) -> str:
        """Assess difficulty of recovery based on drawdown level."""
        if drawdown <= Decimal('0.02'):  # 2%
            return "easy"
        elif drawdown <= Decimal('0.04'):  # 4%
            return "moderate"
        elif drawdown <= Decimal('0.06'):  # 6%
            return "challenging"
        else:
            return "difficult"
    
    async def start_continuous_monitoring(self, account: Account, update_interval: int = 5) -> None:
        """
        Start continuous drawdown monitoring.
        
        Args:
            account: Account to monitor
            update_interval: Update interval in seconds
        """
        logger.info(f"Starting static drawdown monitoring for account {account.account_id}")
        
        while True:
            try:
                alert = await self.monitor_drawdown(account)
                
                if alert:
                    # Log significant alerts
                    if alert.severity in [DrawdownSeverity.WARNING, DrawdownSeverity.CRITICAL, DrawdownSeverity.VIOLATION]:
                        logger.warning(f"Drawdown alert: {alert.message}")
                
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Error in drawdown monitoring: {e}")
                await asyncio.sleep(30)  # Wait longer on error