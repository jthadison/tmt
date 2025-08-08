"""
Daily loss tracking system for Funding Pips compliance.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import asyncio
from enum import Enum
import logging

from pydantic import BaseModel

from .models import Account, Trade, Position
from .funding_pips import FundingPipsWarningLevel

logger = logging.getLogger(__name__)


class DailyResetScheduler:
    """Manages daily P&L reset timing."""
    
    def __init__(self, reset_time: str = "00:00", timezone: str = "UTC"):
        self.reset_time = reset_time
        self.timezone = timezone
        self.last_reset = datetime.utcnow().date()
    
    def needs_reset(self) -> bool:
        """Check if daily reset is needed."""
        current_date = datetime.utcnow().date()
        return current_date > self.last_reset
    
    def perform_reset(self, account: Account) -> None:
        """Reset daily P&L counters."""
        account.daily_pnl = Decimal('0.0')
        account.daily_trades_count = 0
        account.daily_volume = Decimal('0.0')
        self.last_reset = datetime.utcnow().date()
        
        logger.info(f"Daily reset performed for account {account.account_id}")


class DailyLossAlert(BaseModel):
    """Daily loss alert model."""
    account_id: str
    current_loss: Decimal
    loss_percentage: float
    warning_level: FundingPipsWarningLevel
    message: str
    timestamp: datetime
    requires_action: bool


class DailyLossTracker:
    """
    Tracks daily loss limits with multi-level warnings.
    Implements Funding Pips 4% daily loss limit with 80%, 90%, 95% warnings.
    """
    
    def __init__(self):
        self.daily_limit = Decimal('0.04')  # 4% daily loss limit
        self.warning_levels = {
            FundingPipsWarningLevel.LEVEL_80: Decimal('0.032'),  # 3.2%
            FundingPipsWarningLevel.LEVEL_90: Decimal('0.036'),  # 3.6% 
            FundingPipsWarningLevel.LEVEL_95: Decimal('0.038'),  # 3.8%
        }
        self.reset_scheduler = DailyResetScheduler()
        self.emergency_overrides = {}  # account_id -> override_data
        self.blocked_accounts = set()
        
    async def update_daily_pnl(self, account: Account, pnl_change: Decimal) -> Optional[DailyLossAlert]:
        """
        Update daily P&L and check for violations.
        
        Args:
            account: Trading account
            pnl_change: Change in P&L (negative for losses)
            
        Returns:
            Alert if warning/violation detected
        """
        # Check if daily reset is needed
        if self.reset_scheduler.needs_reset():
            self.reset_scheduler.perform_reset(account)
        
        # Update daily P&L
        account.daily_pnl += pnl_change
        
        # Calculate loss percentage
        if account.daily_pnl >= 0:
            return None  # No loss, no alert needed
        
        loss_percentage = abs(account.daily_pnl) / account.initial_balance
        
        # Check for violations/warnings
        alert = self._check_daily_loss_levels(account, loss_percentage)
        
        # Update blocked accounts
        if alert and alert.warning_level == FundingPipsWarningLevel.CRITICAL:
            self.blocked_accounts.add(account.account_id)
            
        return alert
    
    def _check_daily_loss_levels(self, account: Account, loss_percentage: Decimal) -> Optional[DailyLossAlert]:
        """Check daily loss against warning levels."""
        
        # Critical - at or above limit
        if loss_percentage >= self.daily_limit:
            return DailyLossAlert(
                account_id=account.account_id,
                current_loss=abs(account.daily_pnl),
                loss_percentage=float(loss_percentage * 100),
                warning_level=FundingPipsWarningLevel.CRITICAL,
                message=f"CRITICAL: Daily loss limit ({self.daily_limit*100}%) exceeded - trading blocked",
                timestamp=datetime.utcnow(),
                requires_action=True
            )
        
        # Check warning levels in descending order
        for level, threshold in sorted(self.warning_levels.items(), 
                                     key=lambda x: x[1], reverse=True):
            if loss_percentage >= threshold:
                return DailyLossAlert(
                    account_id=account.account_id,
                    current_loss=abs(account.daily_pnl),
                    loss_percentage=float(loss_percentage * 100),
                    warning_level=level,
                    message=self._get_warning_message(level, loss_percentage),
                    timestamp=datetime.utcnow(),
                    requires_action=(level == FundingPipsWarningLevel.LEVEL_95)
                )
        
        return None
    
    def _get_warning_message(self, level: FundingPipsWarningLevel, loss_pct: Decimal) -> str:
        """Generate appropriate warning message."""
        messages = {
            FundingPipsWarningLevel.LEVEL_80: f"WARNING: Daily loss at 80% of limit ({loss_pct*100:.2f}%)",
            FundingPipsWarningLevel.LEVEL_90: f"ALERT: Daily loss at 90% of limit ({loss_pct*100:.2f}%)",
            FundingPipsWarningLevel.LEVEL_95: f"URGENT: Daily loss at 95% of limit ({loss_pct*100:.2f}%)"
        }
        return messages.get(level, f"Daily loss warning: {loss_pct*100:.2f}%")
    
    def can_trade(self, account_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if account can trade based on daily loss status.
        
        Returns:
            Tuple of (can_trade, reason_if_blocked)
        """
        # Check emergency override
        if self._has_emergency_override(account_id):
            override_data = self.emergency_overrides[account_id]
            if override_data['expires'] > datetime.utcnow():
                return (True, None)
            else:
                # Override expired, remove it
                del self.emergency_overrides[account_id]
        
        # Check if account is blocked
        if account_id in self.blocked_accounts:
            return (False, "Account blocked due to daily loss limit violation")
        
        return (True, None)
    
    def validate_trade_risk(self, account: Account, trade: Trade) -> Tuple[bool, Optional[str]]:
        """
        Validate if trade would exceed daily loss limits.
        
        Args:
            account: Trading account
            trade: Proposed trade
            
        Returns:
            Tuple of (trade_allowed, reason_if_rejected)
        """
        # Check if account can trade
        can_trade, reason = self.can_trade(account.account_id)
        if not can_trade:
            return (False, reason)
        
        # Calculate potential additional loss
        if not trade.stop_loss:
            return (False, "Stop loss required for risk calculation")
        
        potential_loss = abs(trade.entry_price - trade.stop_loss) * trade.position_size
        projected_daily_loss = abs(account.daily_pnl) + potential_loss
        projected_loss_pct = projected_daily_loss / account.initial_balance
        
        # Check if trade would exceed limit
        if projected_loss_pct >= self.daily_limit:
            return (False, f"Trade would exceed daily loss limit (projected: {projected_loss_pct*100:.2f}%)")
        
        # Check if trade approaches 95% level (requires confirmation)
        if projected_loss_pct >= self.warning_levels[FundingPipsWarningLevel.LEVEL_95]:
            return (False, f"Trade approaches critical loss level (projected: {projected_loss_pct*100:.2f}%) - requires override")
        
        return (True, None)
    
    def create_emergency_override(self, account_id: str, reason: str, 
                                duration_minutes: int = 60, authorized_by: str = None) -> Dict:
        """
        Create emergency trading override for blocked account.
        
        Args:
            account_id: Account to override
            reason: Justification for override
            duration_minutes: Override duration
            authorized_by: User who authorized override
            
        Returns:
            Override details
        """
        override_data = {
            'account_id': account_id,
            'reason': reason,
            'authorized_by': authorized_by or 'system',
            'created_at': datetime.utcnow(),
            'expires': datetime.utcnow() + timedelta(minutes=duration_minutes),
            'used_trades': 0,
            'max_trades': 3  # Limit emergency trades
        }
        
        self.emergency_overrides[account_id] = override_data
        
        # Remove from blocked accounts temporarily
        if account_id in self.blocked_accounts:
            self.blocked_accounts.remove(account_id)
        
        logger.warning(f"Emergency override created for {account_id}: {reason}")
        return override_data
    
    def _has_emergency_override(self, account_id: str) -> bool:
        """Check if account has active emergency override."""
        if account_id not in self.emergency_overrides:
            return False
        
        override = self.emergency_overrides[account_id]
        
        # Check expiry
        if override['expires'] <= datetime.utcnow():
            return False
        
        # Check trade limit
        if override['used_trades'] >= override['max_trades']:
            return False
        
        return True
    
    def get_daily_loss_status(self, account: Account) -> Dict:
        """
        Get current daily loss status for dashboard.
        
        Returns:
            Status dictionary with metrics and warnings
        """
        if account.daily_pnl >= 0:
            loss_pct = 0.0
            status = "profit"
            color = "green"
        else:
            loss_pct = float(abs(account.daily_pnl) / account.initial_balance * 100)
            
            if loss_pct >= 4.0:  # At limit
                status = "blocked"
                color = "red"
            elif loss_pct >= 3.8:  # 95% level
                status = "critical"
                color = "red"
            elif loss_pct >= 3.6:  # 90% level
                status = "warning"
                color = "orange"
            elif loss_pct >= 3.2:  # 80% level
                status = "caution"
                color = "yellow"
            else:
                status = "safe"
                color = "green"
        
        return {
            'current_loss': float(abs(account.daily_pnl)),
            'loss_percentage': loss_pct,
            'limit_percentage': 4.0,
            'remaining_percentage': max(0, 4.0 - loss_pct),
            'status': status,
            'color': color,
            'blocked': account.account_id in self.blocked_accounts,
            'has_override': self._has_emergency_override(account.account_id),
            'warning_levels': {
                '80_percent': 3.2,
                '90_percent': 3.6,
                '95_percent': 3.8
            },
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def get_statistics(self, account: Account) -> Dict:
        """Get daily loss statistics."""
        return {
            'daily_trades': account.daily_trades_count,
            'daily_volume': float(account.daily_volume),
            'daily_pnl': float(account.daily_pnl),
            'average_trade_pnl': float(account.daily_pnl / max(1, account.daily_trades_count)),
            'largest_loss_trade': float(getattr(account, 'largest_daily_loss', Decimal('0.0'))),
            'profit_trades': getattr(account, 'daily_profit_trades', 0),
            'loss_trades': getattr(account, 'daily_loss_trades', 0),
            'win_rate': self._calculate_daily_win_rate(account)
        }
    
    def _calculate_daily_win_rate(self, account: Account) -> float:
        """Calculate daily win rate."""
        profit_trades = getattr(account, 'daily_profit_trades', 0)
        total_trades = account.daily_trades_count
        
        if total_trades == 0:
            return 0.0
        
        return (profit_trades / total_trades) * 100
    
    async def start_monitoring(self, account: Account) -> None:
        """Start real-time daily loss monitoring."""
        logger.info(f"Starting daily loss monitoring for account {account.account_id}")
        
        while True:
            try:
                # Check for daily reset
                if self.reset_scheduler.needs_reset():
                    self.reset_scheduler.perform_reset(account)
                
                # Monitor current status
                status = self.get_daily_loss_status(account)
                
                # Log status changes
                if status['status'] != getattr(self, '_last_status', None):
                    logger.info(f"Daily loss status changed to {status['status']} for account {account.account_id}")
                    self._last_status = status['status']
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in daily loss monitoring: {e}")
                await asyncio.sleep(30)  # Wait longer on error