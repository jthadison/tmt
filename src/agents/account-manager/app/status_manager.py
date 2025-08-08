"""
Account status management with state machine and automatic transitions.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from uuid import UUID

from .models import (
    AccountConfiguration, AccountStatus, AccountStatusTransition,
    AccountHealthStatus
)

logger = logging.getLogger(__name__)


class StatusTransitionRule(Enum):
    """Rules that can trigger status transitions."""
    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"
    MAX_DRAWDOWN_EXCEEDED = "max_drawdown_exceeded"
    MANUAL_SUSPENSION = "manual_suspension"
    MANUAL_ACTIVATION = "manual_activation"
    MANUAL_TERMINATION = "manual_termination"
    DRAWDOWN_RECOVERY = "drawdown_recovery"
    DAILY_RESET = "daily_reset"
    CONNECTION_LOST = "connection_lost"
    VIOLATION_THRESHOLD = "violation_threshold"
    INACTIVITY_TIMEOUT = "inactivity_timeout"


class StatusTransitionError(Exception):
    """Error in status transition."""
    pass


class AccountStatusManager:
    """
    Manages account status transitions and business rules.
    
    Implements state machine for account status management with
    automatic transitions based on trading conditions and manual overrides.
    """
    
    def __init__(self):
        """Initialize status manager."""
        self.transition_history = {}  # account_id -> List[AccountStatusTransition]
        self.status_listeners = {}  # status -> List[callback]
        self.monitoring_active = False
        self.health_cache = {}  # account_id -> AccountHealthStatus
        
        # Define valid transitions
        self.valid_transitions = {
            AccountStatus.ACTIVE: {
                AccountStatus.SUSPENDED,
                AccountStatus.IN_DRAWDOWN,
                AccountStatus.TERMINATED
            },
            AccountStatus.SUSPENDED: {
                AccountStatus.ACTIVE,
                AccountStatus.TERMINATED
            },
            AccountStatus.IN_DRAWDOWN: {
                AccountStatus.ACTIVE,
                AccountStatus.SUSPENDED,
                AccountStatus.TERMINATED
            },
            AccountStatus.TERMINATED: set()  # No transitions from terminated
        }
        
        # Status-based restrictions
        self.status_restrictions = {
            AccountStatus.ACTIVE: {
                "can_trade": True,
                "can_open_positions": True,
                "can_close_positions": True,
                "can_modify_positions": True
            },
            AccountStatus.SUSPENDED: {
                "can_trade": False,
                "can_open_positions": False,
                "can_close_positions": True,  # Allow closing existing
                "can_modify_positions": False
            },
            AccountStatus.IN_DRAWDOWN: {
                "can_trade": True,
                "can_open_positions": False,  # Close-only mode
                "can_close_positions": True,
                "can_modify_positions": False
            },
            AccountStatus.TERMINATED: {
                "can_trade": False,
                "can_open_positions": False,
                "can_close_positions": False,
                "can_modify_positions": False
            }
        }
    
    async def transition_status(
        self,
        account: AccountConfiguration,
        new_status: AccountStatus,
        reason: str,
        triggered_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountStatusTransition:
        """
        Transition account to new status.
        
        Args:
            account: Account to transition
            new_status: Target status
            reason: Reason for transition
            triggered_by: Who/what triggered the transition
            metadata: Additional transition data
            
        Returns:
            Status transition record
            
        Raises:
            StatusTransitionError: If transition is invalid
        """
        try:
            old_status = account.status
            
            # Validate transition
            if not self._is_valid_transition(old_status, new_status):
                raise StatusTransitionError(
                    f"Invalid transition from {old_status.value} to {new_status.value}"
                )
            
            # Create transition record
            transition = AccountStatusTransition(
                account_id=account.account_id,
                from_status=old_status,
                to_status=new_status,
                reason=reason,
                triggered_by=triggered_by,
                metadata=metadata or {}
            )
            
            # Update account status
            account.status = new_status
            account.updated_at = datetime.utcnow()
            
            # Store transition history
            if account.account_id not in self.transition_history:
                self.transition_history[account.account_id] = []
            
            self.transition_history[account.account_id].append(transition)
            
            # Trigger status-specific actions
            await self._handle_status_change(account, transition)
            
            # Notify listeners
            await self._notify_status_change(account, transition)
            
            logger.info(
                f"Account {account.account_id} status changed: "
                f"{old_status.value} -> {new_status.value} (reason: {reason})"
            )
            
            return transition
            
        except Exception as e:
            logger.error(f"Status transition failed for account {account.account_id}: {e}")
            raise StatusTransitionError(f"Transition failed: {str(e)}")
    
    def _is_valid_transition(self, from_status: AccountStatus, to_status: AccountStatus) -> bool:
        """
        Check if status transition is valid.
        
        Args:
            from_status: Current status
            to_status: Target status
            
        Returns:
            True if transition is allowed
        """
        if from_status == to_status:
            return True  # Same status is always valid
        
        return to_status in self.valid_transitions.get(from_status, set())
    
    async def check_automatic_transitions(self, account: AccountConfiguration) -> Optional[AccountStatusTransition]:
        """
        Check if account should automatically transition status.
        
        Args:
            account: Account to check
            
        Returns:
            Status transition if one was triggered, None otherwise
        """
        try:
            current_status = account.status
            
            # Skip if terminated
            if current_status == AccountStatus.TERMINATED:
                return None
            
            # Check daily loss limit
            daily_loss_transition = await self._check_daily_loss_limit(account)
            if daily_loss_transition:
                return daily_loss_transition
            
            # Check max drawdown
            drawdown_transition = await self._check_max_drawdown(account)
            if drawdown_transition:
                return drawdown_transition
            
            # Check recovery conditions
            recovery_transition = await self._check_recovery_conditions(account)
            if recovery_transition:
                return recovery_transition
            
            # Check connection health
            connection_transition = await self._check_connection_health(account)
            if connection_transition:
                return connection_transition
            
            # Check inactivity
            inactivity_transition = await self._check_inactivity(account)
            if inactivity_transition:
                return inactivity_transition
            
            return None
            
        except Exception as e:
            logger.error(f"Automatic transition check failed for account {account.account_id}: {e}")
            return None
    
    async def _check_daily_loss_limit(self, account: AccountConfiguration) -> Optional[AccountStatusTransition]:
        """Check if daily loss limit exceeded."""
        try:
            # Calculate current daily loss percentage
            daily_loss = abs(min(Decimal('0'), account.balance - account.initial_balance))
            daily_loss_pct = (daily_loss / account.initial_balance) * 100
            
            # Check against risk limits
            if daily_loss_pct >= account.risk_limits.max_daily_loss_percent:
                if account.status != AccountStatus.IN_DRAWDOWN:
                    return await self.transition_status(
                        account,
                        AccountStatus.IN_DRAWDOWN,
                        f"Daily loss limit exceeded: {daily_loss_pct:.2f}%",
                        "system_automatic",
                        {
                            "rule": StatusTransitionRule.DAILY_LOSS_EXCEEDED.value,
                            "daily_loss_percent": float(daily_loss_pct),
                            "limit_percent": float(account.risk_limits.max_daily_loss_percent)
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Daily loss check failed for account {account.account_id}: {e}")
            return None
    
    async def _check_max_drawdown(self, account: AccountConfiguration) -> Optional[AccountStatusTransition]:
        """Check if maximum drawdown exceeded."""
        try:
            # Calculate total drawdown
            current_equity = account.balance  # Simplified - would include unrealized P&L
            total_drawdown = account.initial_balance - current_equity
            drawdown_pct = (total_drawdown / account.initial_balance) * 100
            
            # Check against risk limits
            if drawdown_pct >= account.risk_limits.max_total_loss_percent:
                if account.status != AccountStatus.TERMINATED:
                    return await self.transition_status(
                        account,
                        AccountStatus.TERMINATED,
                        f"Maximum drawdown exceeded: {drawdown_pct:.2f}%",
                        "system_automatic",
                        {
                            "rule": StatusTransitionRule.MAX_DRAWDOWN_EXCEEDED.value,
                            "drawdown_percent": float(drawdown_pct),
                            "limit_percent": float(account.risk_limits.max_total_loss_percent)
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Max drawdown check failed for account {account.account_id}: {e}")
            return None
    
    async def _check_recovery_conditions(self, account: AccountConfiguration) -> Optional[AccountStatusTransition]:
        """Check if account can recover from drawdown status."""
        try:
            if account.status != AccountStatus.IN_DRAWDOWN:
                return None
            
            # Check if it's a new trading day (daily loss reset)
            # Simplified - would check actual market hours and trading day
            last_transition = self.get_last_transition(account.account_id)
            if last_transition:
                hours_since_transition = (datetime.utcnow() - last_transition.timestamp).total_seconds() / 3600
                
                # If it's been more than 18 hours (new trading day), allow recovery
                if hours_since_transition >= 18:
                    # Check if account is healthy enough to resume
                    current_equity = account.balance
                    loss_from_initial = (account.initial_balance - current_equity) / account.initial_balance * 100
                    
                    # Only recover if loss is less than 80% of max drawdown limit
                    recovery_threshold = account.risk_limits.max_total_loss_percent * Decimal('0.8')
                    
                    if loss_from_initial <= recovery_threshold:
                        return await self.transition_status(
                            account,
                            AccountStatus.ACTIVE,
                            "Daily reset - recovered from drawdown",
                            "system_automatic",
                            {
                                "rule": StatusTransitionRule.DRAWDOWN_RECOVERY.value,
                                "hours_since_drawdown": hours_since_transition,
                                "current_loss_percent": float(loss_from_initial)
                            }
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Recovery check failed for account {account.account_id}: {e}")
            return None
    
    async def _check_connection_health(self, account: AccountConfiguration) -> Optional[AccountStatusTransition]:
        """Check broker connection health."""
        try:
            # Get health status from cache
            health = self.health_cache.get(account.account_id)
            if not health:
                return None
            
            # If connection has been down for more than 30 minutes, suspend
            if health.last_heartbeat:
                time_since_heartbeat = datetime.utcnow() - health.last_heartbeat
                if time_since_heartbeat > timedelta(minutes=30):
                    if account.status == AccountStatus.ACTIVE:
                        return await self.transition_status(
                            account,
                            AccountStatus.SUSPENDED,
                            f"Connection lost for {time_since_heartbeat}",
                            "system_automatic",
                            {
                                "rule": StatusTransitionRule.CONNECTION_LOST.value,
                                "minutes_since_heartbeat": time_since_heartbeat.total_seconds() / 60
                            }
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Connection health check failed for account {account.account_id}: {e}")
            return None
    
    async def _check_inactivity(self, account: AccountConfiguration) -> Optional[AccountStatusTransition]:
        """Check for account inactivity."""
        try:
            if not account.last_activity:
                return None
            
            # Suspend after 30 days of inactivity
            days_inactive = (datetime.utcnow() - account.last_activity).days
            
            if days_inactive >= 30 and account.status == AccountStatus.ACTIVE:
                return await self.transition_status(
                    account,
                    AccountStatus.SUSPENDED,
                    f"Account inactive for {days_inactive} days",
                    "system_automatic",
                    {
                        "rule": StatusTransitionRule.INACTIVITY_TIMEOUT.value,
                        "days_inactive": days_inactive
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Inactivity check failed for account {account.account_id}: {e}")
            return None
    
    async def _handle_status_change(self, account: AccountConfiguration, transition: AccountStatusTransition) -> None:
        """Handle actions when status changes."""
        try:
            new_status = transition.to_status
            
            if new_status == AccountStatus.TERMINATED:
                # TODO: Trigger credential purge
                logger.critical(f"Account {account.account_id} terminated - credentials should be purged")
            
            elif new_status == AccountStatus.SUSPENDED:
                # TODO: Notify trading engine to halt all operations
                logger.warning(f"Account {account.account_id} suspended - halt trading operations")
            
            elif new_status == AccountStatus.IN_DRAWDOWN:
                # TODO: Enable close-only mode in trading engine
                logger.warning(f"Account {account.account_id} in drawdown - enable close-only mode")
            
            elif new_status == AccountStatus.ACTIVE:
                if transition.from_status != AccountStatus.ACTIVE:
                    # TODO: Resume full trading operations
                    logger.info(f"Account {account.account_id} activated - resume full trading")
            
        except Exception as e:
            logger.error(f"Status change handling failed for account {account.account_id}: {e}")
    
    async def _notify_status_change(self, account: AccountConfiguration, transition: AccountStatusTransition) -> None:
        """Notify listeners of status change."""
        try:
            # Get listeners for this status
            listeners = self.status_listeners.get(transition.to_status, [])
            
            for listener in listeners:
                try:
                    await listener(account, transition)
                except Exception as e:
                    logger.error(f"Status listener failed: {e}")
            
        except Exception as e:
            logger.error(f"Status change notification failed: {e}")
    
    def get_status_restrictions(self, status: AccountStatus) -> Dict[str, bool]:
        """
        Get trading restrictions for a status.
        
        Args:
            status: Account status
            
        Returns:
            Dictionary of restrictions
        """
        return self.status_restrictions.get(status, {}).copy()
    
    def can_perform_action(self, account: AccountConfiguration, action: str) -> Tuple[bool, str]:
        """
        Check if account can perform an action.
        
        Args:
            account: Account to check
            action: Action to validate (trade, open_position, etc.)
            
        Returns:
            Tuple of (allowed, reason)
        """
        restrictions = self.get_status_restrictions(account.status)
        
        action_key = f"can_{action}"
        if action_key in restrictions:
            allowed = restrictions[action_key]
            
            if not allowed:
                return False, f"Action '{action}' not allowed in status '{account.status.value}'"
            
            return True, "Action allowed"
        
        return False, f"Unknown action '{action}'"
    
    def get_transition_history(self, account_id: UUID, limit: int = 50) -> List[AccountStatusTransition]:
        """
        Get status transition history for account.
        
        Args:
            account_id: Account identifier
            limit: Maximum number of transitions to return
            
        Returns:
            List of status transitions (most recent first)
        """
        history = self.transition_history.get(account_id, [])
        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_last_transition(self, account_id: UUID) -> Optional[AccountStatusTransition]:
        """
        Get last status transition for account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Last transition or None
        """
        history = self.get_transition_history(account_id, limit=1)
        return history[0] if history else None
    
    def add_status_listener(self, status: AccountStatus, callback) -> None:
        """
        Add listener for status changes.
        
        Args:
            status: Status to listen for
            callback: Async callback function
        """
        if status not in self.status_listeners:
            self.status_listeners[status] = []
        
        self.status_listeners[status].append(callback)
    
    def remove_status_listener(self, status: AccountStatus, callback) -> None:
        """
        Remove status change listener.
        
        Args:
            status: Status to stop listening for
            callback: Callback function to remove
        """
        if status in self.status_listeners:
            try:
                self.status_listeners[status].remove(callback)
            except ValueError:
                pass
    
    def update_health_status(self, account_id: UUID, health: AccountHealthStatus) -> None:
        """
        Update health status for account.
        
        Args:
            account_id: Account identifier
            health: Health status information
        """
        self.health_cache[account_id] = health
    
    def get_health_status(self, account_id: UUID) -> Optional[AccountHealthStatus]:
        """
        Get cached health status for account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Health status or None
        """
        return self.health_cache.get(account_id)
    
    async def start_monitoring(self, accounts: List[AccountConfiguration]) -> None:
        """
        Start automatic status monitoring.
        
        Args:
            accounts: Accounts to monitor
        """
        self.monitoring_active = True
        logger.info(f"Starting status monitoring for {len(accounts)} accounts")
        
        while self.monitoring_active:
            try:
                for account in accounts:
                    if account.status != AccountStatus.TERMINATED:
                        await self.check_automatic_transitions(account)
                
                # Wait 30 seconds between checks
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Status monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def stop_monitoring(self) -> None:
        """Stop automatic status monitoring."""
        self.monitoring_active = False
        logger.info("Status monitoring stopped")
    
    def get_status_statistics(self, accounts: List[AccountConfiguration]) -> Dict[str, Any]:
        """
        Get status statistics across all accounts.
        
        Args:
            accounts: List of accounts to analyze
            
        Returns:
            Status statistics
        """
        try:
            status_counts = {}
            total_accounts = len(accounts)
            
            # Count accounts by status
            for status in AccountStatus:
                status_counts[status.value] = sum(1 for acc in accounts if acc.status == status)
            
            # Calculate health metrics
            healthy_accounts = sum(1 for acc in accounts if acc.status == AccountStatus.ACTIVE)
            unhealthy_accounts = sum(1 for acc in accounts if acc.status in [AccountStatus.SUSPENDED, AccountStatus.TERMINATED])
            
            # Get recent transitions
            recent_transitions = 0
            for account in accounts:
                history = self.get_transition_history(account.account_id, limit=5)
                recent_transitions += len([t for t in history if (datetime.utcnow() - t.timestamp).days <= 7])
            
            return {
                "total_accounts": total_accounts,
                "status_breakdown": status_counts,
                "healthy_accounts": healthy_accounts,
                "unhealthy_accounts": unhealthy_accounts,
                "health_percentage": (healthy_accounts / total_accounts * 100) if total_accounts > 0 else 0,
                "recent_transitions_7days": recent_transitions,
                "monitoring_active": self.monitoring_active,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Status statistics calculation failed: {e}")
            return {
                "error": str(e),
                "total_accounts": 0,
                "monitoring_active": False
            }