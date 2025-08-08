"""
Weekend closure automation for Funding Pips compliance.
Automatically closes all positions before weekend to comply with prop firm rules.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import logging
from enum import Enum
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from .models import Account, Position, Trade

logger = logging.getLogger(__name__)


class ClosureReason(Enum):
    """Reasons for position closure."""
    WEEKEND_RULE = "weekend_compliance"
    MANUAL_OVERRIDE = "manual_override"
    EMERGENCY_CLOSURE = "emergency"
    PARTIAL_FILL_CLEANUP = "partial_fill"


class ClosureStatus(Enum):
    """Status of closure operations."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WeekendClosureEvent(BaseModel):
    """Weekend closure event model."""
    account_id: str
    position_id: str
    symbol: str
    closure_reason: ClosureReason
    scheduled_time: datetime
    executed_time: Optional[datetime] = None
    closure_price: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    status: ClosureStatus
    error_message: Optional[str] = None


class WeekendClosureAutomation:
    """
    Automates weekend position closure for Funding Pips compliance.
    
    Features:
    - Scheduled closure at 4:50 PM EST Friday
    - Grace period for manual intervention
    - Handles partial fills and pending orders
    - Emergency override capabilities
    - Detailed logging and notifications
    """
    
    def __init__(self, 
                 closure_time: str = "16:50",
                 timezone: str = "America/New_York",
                 grace_period_minutes: int = 5):
        """
        Initialize weekend closure automation.
        
        Args:
            closure_time: Time to close positions (HH:MM format)
            timezone: Timezone for closure time
            grace_period_minutes: Grace period for manual intervention
        """
        self.closure_time = closure_time
        self.timezone = ZoneInfo(timezone)
        self.grace_period_minutes = grace_period_minutes
        self.scheduled_closures = {}  # account_id -> [closure_events]
        self.closure_history = {}     # account_id -> [historical_events]
        self.override_accounts = set()  # Accounts with manual override
        self.is_monitoring = False
        
        # Parse closure time
        hour, minute = map(int, closure_time.split(':'))
        self.closure_hour = hour
        self.closure_minute = minute
    
    async def start_weekend_monitoring(self) -> None:
        """Start weekend closure monitoring service."""
        self.is_monitoring = True
        logger.info("Weekend closure monitoring started")
        
        while self.is_monitoring:
            try:
                await self._check_weekend_closure_schedule()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in weekend monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    def stop_weekend_monitoring(self) -> None:
        """Stop weekend closure monitoring."""
        self.is_monitoring = False
        logger.info("Weekend closure monitoring stopped")
    
    async def _check_weekend_closure_schedule(self) -> None:
        """Check if weekend closure should be triggered."""
        now = datetime.now(self.timezone)
        
        # Only process on Fridays
        if now.weekday() != 4:  # 4 = Friday
            return
        
        # Check if we're at closure time
        closure_time_today = now.replace(
            hour=self.closure_hour,
            minute=self.closure_minute,
            second=0,
            microsecond=0
        )
        
        # Grace period end time
        grace_period_end = closure_time_today + timedelta(minutes=self.grace_period_minutes)
        
        # Check if we're in the closure window
        if closure_time_today <= now <= grace_period_end:
            await self._execute_weekend_closures()
    
    async def schedule_weekend_closure(self, account: Account, positions: List[Position]) -> List[WeekendClosureEvent]:
        """
        Schedule weekend closure for account positions.
        
        Args:
            account: Trading account
            positions: List of open positions
            
        Returns:
            List of scheduled closure events
        """
        # Check if account has override
        if account.account_id in self.override_accounts:
            logger.info(f"Weekend closure override active for account {account.account_id}")
            return []
        
        # Filter positions that need closure
        positions_to_close = self._filter_positions_for_closure(positions)
        
        if not positions_to_close:
            logger.info(f"No positions require weekend closure for account {account.account_id}")
            return []
        
        # Calculate closure time
        now = datetime.now(self.timezone)
        if now.weekday() == 4:  # Friday
            closure_datetime = now.replace(
                hour=self.closure_hour,
                minute=self.closure_minute,
                second=0,
                microsecond=0
            )
            
            # If it's past closure time, schedule for next Friday
            if now >= closure_datetime:
                closure_datetime += timedelta(days=7)
        else:
            # Schedule for next Friday
            days_until_friday = (4 - now.weekday() + 7) % 7
            if days_until_friday == 0:  # Today is Friday but before closure time
                days_until_friday = 7
            
            closure_datetime = (now + timedelta(days=days_until_friday)).replace(
                hour=self.closure_hour,
                minute=self.closure_minute,
                second=0,
                microsecond=0
            )
        
        # Create closure events
        closure_events = []
        for position in positions_to_close:
            event = WeekendClosureEvent(
                account_id=account.account_id,
                position_id=position.position_id,
                symbol=position.symbol,
                closure_reason=ClosureReason.WEEKEND_RULE,
                scheduled_time=closure_datetime,
                status=ClosureStatus.SCHEDULED
            )
            closure_events.append(event)
        
        # Store scheduled closures
        if account.account_id not in self.scheduled_closures:
            self.scheduled_closures[account.account_id] = []
        
        self.scheduled_closures[account.account_id].extend(closure_events)
        
        logger.info(f"Scheduled {len(closure_events)} positions for weekend closure at {closure_datetime}")
        return closure_events
    
    def _filter_positions_for_closure(self, positions: List[Position]) -> List[Position]:
        """
        Filter positions that require weekend closure.
        
        Args:
            positions: All open positions
            
        Returns:
            Positions that need to be closed for weekend
        """
        positions_to_close = []
        
        for position in positions:
            # Skip positions that are already scheduled for closure
            if self._is_position_scheduled_for_closure(position.position_id):
                continue
            
            # Skip positions with pending closure orders
            if getattr(position, 'pending_closure', False):
                continue
            
            # Include all other positions (Funding Pips requires all positions closed)
            positions_to_close.append(position)
        
        return positions_to_close
    
    def _is_position_scheduled_for_closure(self, position_id: str) -> bool:
        """Check if position is already scheduled for closure."""
        for account_closures in self.scheduled_closures.values():
            for event in account_closures:
                if (event.position_id == position_id and 
                    event.status in [ClosureStatus.SCHEDULED, ClosureStatus.IN_PROGRESS]):
                    return True
        return False
    
    async def _execute_weekend_closures(self) -> None:
        """Execute scheduled weekend closures."""
        logger.info("Executing weekend closures...")
        
        for account_id, closure_events in self.scheduled_closures.items():
            # Skip accounts with overrides
            if account_id in self.override_accounts:
                continue
            
            # Process scheduled closures
            scheduled_events = [
                event for event in closure_events 
                if event.status == ClosureStatus.SCHEDULED
            ]
            
            if scheduled_events:
                await self._close_account_positions(account_id, scheduled_events)
    
    async def _close_account_positions(self, account_id: str, closure_events: List[WeekendClosureEvent]) -> None:
        """
        Close positions for a specific account.
        
        Args:
            account_id: Account identifier
            closure_events: List of closure events to process
        """
        logger.info(f"Closing {len(closure_events)} positions for account {account_id}")
        
        for event in closure_events:
            try:
                # Update status to in progress
                event.status = ClosureStatus.IN_PROGRESS
                event.executed_time = datetime.now(self.timezone)
                
                # Execute closure (this would integrate with trading platform)
                success = await self._execute_position_closure(event)
                
                if success:
                    event.status = ClosureStatus.COMPLETED
                    logger.info(f"Successfully closed position {event.position_id}")
                else:
                    event.status = ClosureStatus.FAILED
                    event.error_message = "Closure execution failed"
                    logger.error(f"Failed to close position {event.position_id}")
                
            except Exception as e:
                event.status = ClosureStatus.FAILED
                event.error_message = str(e)
                logger.error(f"Error closing position {event.position_id}: {e}")
        
        # Move completed events to history
        self._archive_completed_events(account_id)
    
    async def _execute_position_closure(self, event: WeekendClosureEvent) -> bool:
        """
        Execute actual position closure.
        
        Args:
            event: Closure event to execute
            
        Returns:
            True if successful, False otherwise
        
        Note: This is a mock implementation. In production, this would
        integrate with the actual trading platform (TradeLocker).
        """
        try:
            # Simulate closure execution
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Mock closure price and P&L calculation
            # In real implementation, this would come from trading platform
            event.closure_price = Decimal('1.0950')  # Mock price
            event.pnl = Decimal('-15.50')  # Mock P&L
            
            return True
            
        except Exception as e:
            logger.error(f"Position closure execution failed: {e}")
            return False
    
    def _archive_completed_events(self, account_id: str) -> None:
        """Archive completed closure events to history."""
        if account_id not in self.scheduled_closures:
            return
        
        # Separate completed events from active ones
        active_events = []
        completed_events = []
        
        for event in self.scheduled_closures[account_id]:
            if event.status in [ClosureStatus.COMPLETED, ClosureStatus.FAILED, ClosureStatus.CANCELLED]:
                completed_events.append(event)
            else:
                active_events.append(event)
        
        # Update scheduled closures with only active events
        self.scheduled_closures[account_id] = active_events
        
        # Add completed events to history
        if completed_events:
            if account_id not in self.closure_history:
                self.closure_history[account_id] = []
            
            self.closure_history[account_id].extend(completed_events)
            
            # Keep only last 100 historical events per account
            if len(self.closure_history[account_id]) > 100:
                self.closure_history[account_id] = self.closure_history[account_id][-100:]
    
    def create_manual_override(self, account_id: str, reason: str, duration_hours: int = 72) -> Dict[str, Any]:
        """
        Create manual override for weekend closure.
        
        Args:
            account_id: Account to override
            reason: Reason for override
            duration_hours: Override duration in hours (default: weekend)
            
        Returns:
            Override details
        """
        override_data = {
            'account_id': account_id,
            'reason': reason,
            'created_at': datetime.now(self.timezone),
            'expires_at': datetime.now(self.timezone) + timedelta(hours=duration_hours),
            'created_by': 'manual'  # In production, this would be user ID
        }
        
        # Add to override accounts
        self.override_accounts.add(account_id)
        
        # Cancel any scheduled closures
        if account_id in self.scheduled_closures:
            for event in self.scheduled_closures[account_id]:
                if event.status == ClosureStatus.SCHEDULED:
                    event.status = ClosureStatus.CANCELLED
                    event.error_message = f"Cancelled due to manual override: {reason}"
        
        logger.warning(f"Manual weekend closure override created for {account_id}: {reason}")
        return override_data
    
    def remove_manual_override(self, account_id: str) -> bool:
        """
        Remove manual override for weekend closure.
        
        Args:
            account_id: Account to remove override for
            
        Returns:
            True if override was removed, False if not found
        """
        if account_id in self.override_accounts:
            self.override_accounts.remove(account_id)
            logger.info(f"Manual weekend closure override removed for {account_id}")
            return True
        return False
    
    def get_weekend_closure_status(self, account_id: str) -> Dict[str, Any]:
        """
        Get weekend closure status for account.
        
        Args:
            account_id: Account to check
            
        Returns:
            Comprehensive weekend closure status
        """
        now = datetime.now(self.timezone)
        
        # Calculate next closure time
        next_friday = now
        while next_friday.weekday() != 4:
            next_friday += timedelta(days=1)
        
        next_closure_time = next_friday.replace(
            hour=self.closure_hour,
            minute=self.closure_minute,
            second=0,
            microsecond=0
        )
        
        # If it's Friday and past closure time, schedule for next week
        if now.weekday() == 4 and now.time() >= next_closure_time.time():
            next_closure_time += timedelta(days=7)
        
        # Get scheduled closures
        scheduled_events = self.scheduled_closures.get(account_id, [])
        active_closures = [
            event for event in scheduled_events 
            if event.status in [ClosureStatus.SCHEDULED, ClosureStatus.IN_PROGRESS]
        ]
        
        # Get recent history
        recent_history = []
        if account_id in self.closure_history:
            recent_history = self.closure_history[account_id][-5:]  # Last 5 events
        
        return {
            'account_id': account_id,
            'next_closure_time': next_closure_time.isoformat(),
            'hours_until_closure': (next_closure_time - now).total_seconds() / 3600,
            'closure_required': True,  # Funding Pips always requires weekend closure
            'manual_override_active': account_id in self.override_accounts,
            'scheduled_closures': len(active_closures),
            'closure_details': {
                'day': 'Friday',
                'time': self.closure_time,
                'timezone': str(self.timezone),
                'grace_period_minutes': self.grace_period_minutes
            },
            'recent_closures': [
                {
                    'date': event.executed_time.date().isoformat() if event.executed_time else None,
                    'positions_closed': 1,
                    'status': event.status.value,
                    'pnl': float(event.pnl) if event.pnl else None
                }
                for event in recent_history
            ],
            'compliance_status': 'compliant' if not active_closures else 'pending_closure',
            'last_updated': now.isoformat()
        }
    
    def get_closure_statistics(self, account_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get weekend closure statistics.
        
        Args:
            account_id: Account to analyze
            days: Number of days to include in analysis
            
        Returns:
            Statistical analysis of weekend closures
        """
        if account_id not in self.closure_history:
            return {
                'total_closures': 0,
                'success_rate': 100.0,
                'average_positions_per_closure': 0,
                'total_pnl_impact': 0.0,
                'compliance_rate': 100.0
            }
        
        # Filter events by date range
        cutoff_date = datetime.now(self.timezone) - timedelta(days=days)
        recent_events = [
            event for event in self.closure_history[account_id]
            if event.executed_time and event.executed_time >= cutoff_date
        ]
        
        if not recent_events:
            return {
                'total_closures': 0,
                'success_rate': 100.0,
                'average_positions_per_closure': 0,
                'total_pnl_impact': 0.0,
                'compliance_rate': 100.0
            }
        
        # Calculate statistics
        successful_closures = len([e for e in recent_events if e.status == ClosureStatus.COMPLETED])
        success_rate = (successful_closures / len(recent_events)) * 100
        
        total_pnl = sum(float(event.pnl) for event in recent_events if event.pnl)
        
        return {
            'total_closures': len(recent_events),
            'success_rate': success_rate,
            'successful_closures': successful_closures,
            'failed_closures': len(recent_events) - successful_closures,
            'total_pnl_impact': total_pnl,
            'average_pnl_per_closure': total_pnl / len(recent_events),
            'compliance_rate': success_rate,  # Same as success rate for weekend closure
            'analysis_period_days': days
        }
    
    def handle_partial_fills(self, account_id: str, partial_positions: List[Position]) -> List[WeekendClosureEvent]:
        """
        Handle partial fills during weekend closure.
        
        Args:
            account_id: Account with partial fills
            partial_positions: Positions with partial fills
            
        Returns:
            List of cleanup closure events
        """
        cleanup_events = []
        
        for position in partial_positions:
            event = WeekendClosureEvent(
                account_id=account_id,
                position_id=position.position_id,
                symbol=position.symbol,
                closure_reason=ClosureReason.PARTIAL_FILL_CLEANUP,
                scheduled_time=datetime.now(self.timezone),
                status=ClosureStatus.SCHEDULED
            )
            cleanup_events.append(event)
        
        # Add to scheduled closures for immediate processing
        if account_id not in self.scheduled_closures:
            self.scheduled_closures[account_id] = []
        
        self.scheduled_closures[account_id].extend(cleanup_events)
        
        logger.info(f"Scheduled {len(cleanup_events)} partial fill cleanup closures for account {account_id}")
        return cleanup_events