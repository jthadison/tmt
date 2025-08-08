"""
Minimum hold time enforcement for Funding Pips compliance.
Ensures all positions are held for at least 1 minute before closure.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import logging
from enum import Enum

from pydantic import BaseModel

from .models import Position, Trade

logger = logging.getLogger(__name__)


class HoldTimeStatus(Enum):
    """Position hold time status."""
    UNDER_MINIMUM = "under_minimum"
    APPROACHING_MINIMUM = "approaching_minimum"
    MEETS_MINIMUM = "meets_minimum"
    EXEMPT = "exempt"


class HoldTimeViolation(BaseModel):
    """Hold time violation model."""
    position_id: str
    symbol: str
    current_hold_time: int  # seconds
    minimum_required: int   # seconds
    time_remaining: int     # seconds
    violation_type: str
    message: str
    timestamp: datetime


class MinimumHoldTimeEnforcer:
    """
    Enforces minimum hold time requirements for Funding Pips.
    
    Requirements:
    - All positions must be held for minimum 1 minute (60 seconds)
    - Early closure attempts are blocked with countdown
    - Exemptions for stop-loss hits and emergency situations
    - Real-time tracking and notifications
    """
    
    def __init__(self, minimum_hold_seconds: int = 60):
        """
        Initialize minimum hold time enforcer.
        
        Args:
            minimum_hold_seconds: Minimum hold time in seconds (default: 60)
        """
        self.minimum_hold_seconds = minimum_hold_seconds
        self.position_timers = {}      # position_id -> open_time
        self.exempted_positions = set() # Positions exempt from hold time
        self.violation_history = {}    # account_id -> [violations]
        self.early_closure_attempts = {}  # position_id -> attempt_count
        self.monitoring_active = True
    
    def track_position_open(self, position: Position) -> None:
        """
        Start tracking hold time for new position.
        
        Args:
            position: Position that was just opened
        """
        self.position_timers[position.position_id] = position.open_time
        
        # Reset any existing early closure attempts
        if position.position_id in self.early_closure_attempts:
            del self.early_closure_attempts[position.position_id]
        
        logger.info(f"Started hold time tracking for position {position.position_id}")
    
    def check_hold_time_compliance(self, position: Position) -> Tuple[bool, Optional[HoldTimeViolation]]:
        """
        Check if position meets minimum hold time requirement.
        
        Args:
            position: Position to check
            
        Returns:
            Tuple of (compliant, violation_details)
        """
        # Check if position is exempt
        if position.position_id in self.exempted_positions:
            return (True, None)
        
        # Get position open time
        open_time = self.position_timers.get(position.position_id, position.open_time)
        current_time = datetime.utcnow()
        
        # Calculate hold time
        hold_duration = (current_time - open_time).total_seconds()
        
        # Check if minimum hold time is met
        if hold_duration >= self.minimum_hold_seconds:
            return (True, None)
        
        # Calculate remaining time
        time_remaining = int(self.minimum_hold_seconds - hold_duration)
        
        # Create violation object
        violation = HoldTimeViolation(
            position_id=position.position_id,
            symbol=position.symbol,
            current_hold_time=int(hold_duration),
            minimum_required=self.minimum_hold_seconds,
            time_remaining=time_remaining,
            violation_type="MINIMUM_HOLD_TIME",
            message=f"Position must be held for {time_remaining} more seconds ({self.minimum_hold_seconds - int(hold_duration)}s remaining)",
            timestamp=current_time
        )
        
        return (False, violation)
    
    def validate_closure_request(self, position: Position, closure_reason: str = "manual") -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Validate position closure request against hold time rules.
        
        Args:
            position: Position to close
            closure_reason: Reason for closure
            
        Returns:
            Tuple of (allowed, rejection_reason, seconds_remaining)
        """
        # Check for exemptions
        exemption_result = self._check_closure_exemptions(position, closure_reason)
        if exemption_result[0]:
            return exemption_result
        
        # Check hold time compliance
        compliant, violation = self.check_hold_time_compliance(position)
        
        if compliant:
            return (True, None, None)
        
        # Record early closure attempt
        self._record_early_closure_attempt(position.position_id)
        
        # Log violation to history
        self._log_violation_attempt(position, violation, closure_reason)
        
        return (False, violation.message, violation.time_remaining)
    
    def _check_closure_exemptions(self, position: Position, closure_reason: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Check if position closure is exempt from hold time requirements.
        
        Args:
            position: Position to check
            closure_reason: Reason for closure
            
        Returns:
            Tuple of (exempt, reason, seconds_remaining)
        """
        # Stop loss hit exemption
        if closure_reason.lower() in ['stop_loss', 'sl_hit', 'stop_loss_triggered']:
            self.exempted_positions.add(position.position_id)
            logger.info(f"Position {position.position_id} exempt from hold time due to stop loss")
            return (True, "Stop loss exemption", None)
        
        # Emergency closure exemption
        if closure_reason.lower() in ['emergency', 'force_close', 'circuit_breaker']:
            self.exempted_positions.add(position.position_id)
            logger.warning(f"Position {position.position_id} exempt from hold time due to emergency")
            return (True, "Emergency closure exemption", None)
        
        # Weekend closure exemption
        if closure_reason.lower() in ['weekend_closure', 'weekend_rule']:
            self.exempted_positions.add(position.position_id)
            logger.info(f"Position {position.position_id} exempt from hold time due to weekend rule")
            return (True, "Weekend closure exemption", None)
        
        # Risk management exemption (drawdown violation, etc.)
        if closure_reason.lower() in ['risk_limit', 'drawdown_violation', 'daily_loss_limit']:
            self.exempted_positions.add(position.position_id)
            logger.warning(f"Position {position.position_id} exempt from hold time due to risk management")
            return (True, "Risk management exemption", None)
        
        return (False, None, None)
    
    def _record_early_closure_attempt(self, position_id: str) -> None:
        """Record early closure attempt for tracking."""
        if position_id not in self.early_closure_attempts:
            self.early_closure_attempts[position_id] = 0
        
        self.early_closure_attempts[position_id] += 1
        
        if self.early_closure_attempts[position_id] > 5:
            logger.warning(f"Multiple early closure attempts for position {position_id}")
    
    def _log_violation_attempt(self, position: Position, violation: HoldTimeViolation, closure_reason: str) -> None:
        """Log violation attempt to history."""
        account_id = getattr(position, 'account_id', 'unknown')
        
        if account_id not in self.violation_history:
            self.violation_history[account_id] = []
        
        violation_record = {
            'position_id': position.position_id,
            'symbol': position.symbol,
            'violation': violation.dict(),
            'closure_reason': closure_reason,
            'timestamp': datetime.utcnow()
        }
        
        self.violation_history[account_id].append(violation_record)
        
        # Keep only last 100 violations per account
        if len(self.violation_history[account_id]) > 100:
            self.violation_history[account_id] = self.violation_history[account_id][-100:]
    
    def create_emergency_override(self, position_id: str, reason: str, authorized_by: str = "system") -> Dict[str, Any]:
        """
        Create emergency override for hold time requirement.
        
        Args:
            position_id: Position to override
            reason: Reason for override
            authorized_by: Who authorized the override
            
        Returns:
            Override details
        """
        override_data = {
            'position_id': position_id,
            'reason': reason,
            'authorized_by': authorized_by,
            'created_at': datetime.utcnow(),
            'override_type': 'emergency_hold_time'
        }
        
        # Add to exempted positions
        self.exempted_positions.add(position_id)
        
        logger.warning(f"Emergency hold time override created for {position_id}: {reason}")
        return override_data
    
    def get_position_hold_status(self, position: Position) -> Dict[str, Any]:
        """
        Get detailed hold time status for position.
        
        Args:
            position: Position to check
            
        Returns:
            Comprehensive hold time status
        """
        open_time = self.position_timers.get(position.position_id, position.open_time)
        current_time = datetime.utcnow()
        
        hold_duration_seconds = int((current_time - open_time).total_seconds())
        time_remaining = max(0, self.minimum_hold_seconds - hold_duration_seconds)
        
        # Determine status
        if position.position_id in self.exempted_positions:
            status = HoldTimeStatus.EXEMPT
            color = "blue"
        elif hold_duration_seconds >= self.minimum_hold_seconds:
            status = HoldTimeStatus.MEETS_MINIMUM
            color = "green"
        elif time_remaining <= 10:  # Less than 10 seconds remaining
            status = HoldTimeStatus.APPROACHING_MINIMUM
            color = "yellow"
        else:
            status = HoldTimeStatus.UNDER_MINIMUM
            color = "red"
        
        return {
            'position_id': position.position_id,
            'symbol': position.symbol,
            'status': status.value,
            'color': color,
            'hold_duration_seconds': hold_duration_seconds,
            'minimum_required_seconds': self.minimum_hold_seconds,
            'time_remaining_seconds': time_remaining,
            'can_close': (status in [HoldTimeStatus.MEETS_MINIMUM, HoldTimeStatus.EXEMPT]),
            'exempt': position.position_id in self.exempted_positions,
            'early_attempts': self.early_closure_attempts.get(position.position_id, 0),
            'opened_at': open_time.isoformat(),
            'elapsed_time_display': self._format_duration(hold_duration_seconds),
            'remaining_time_display': self._format_duration(time_remaining) if time_remaining > 0 else None,
            'last_updated': current_time.isoformat()
        }
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def get_account_hold_time_statistics(self, account_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get hold time statistics for account.
        
        Args:
            account_id: Account to analyze
            days: Number of days to include in analysis
            
        Returns:
            Statistical analysis of hold time compliance
        """
        # Get violation history for account
        violations = self.violation_history.get(account_id, [])
        
        # Filter by date range
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_violations = [
            v for v in violations 
            if v['timestamp'] >= cutoff_date
        ]
        
        # Calculate statistics
        total_attempts = len(recent_violations)
        unique_positions = len(set(v['position_id'] for v in recent_violations))
        
        # Average hold time at violation attempt
        avg_hold_time = 0
        if recent_violations:
            avg_hold_time = sum(v['violation']['current_hold_time'] for v in recent_violations) / len(recent_violations)
        
        # Most common violation times
        violation_times = [v['violation']['current_hold_time'] for v in recent_violations]
        
        return {
            'account_id': account_id,
            'analysis_period_days': days,
            'violation_attempts': total_attempts,
            'affected_positions': unique_positions,
            'average_hold_time_at_violation': avg_hold_time,
            'compliance_rate': self._calculate_compliance_rate(account_id, days),
            'most_common_violation_times': self._get_common_violation_times(violation_times),
            'recommendations': self._generate_hold_time_recommendations(recent_violations),
            'exemptions_used': len([v for v in recent_violations if 'exemption' in v.get('closure_reason', '').lower()])
        }
    
    def _calculate_compliance_rate(self, account_id: str, days: int) -> float:
        """Calculate hold time compliance rate."""
        # This would integrate with actual position history
        # For now, return estimated compliance based on violations
        violations = len(self.violation_history.get(account_id, []))
        if violations == 0:
            return 100.0
        
        # Estimate based on violation frequency
        return max(0, 100 - (violations * 2))  # Each violation reduces score by 2%
    
    def _get_common_violation_times(self, violation_times: List[int]) -> List[Dict[str, Any]]:
        """Get most common violation times."""
        if not violation_times:
            return []
        
        # Group by time ranges
        time_ranges = {
            '0-10s': len([t for t in violation_times if 0 <= t <= 10]),
            '11-20s': len([t for t in violation_times if 11 <= t <= 20]),
            '21-30s': len([t for t in violation_times if 21 <= t <= 30]),
            '31-45s': len([t for t in violation_times if 31 <= t <= 45]),
            '46-59s': len([t for t in violation_times if 46 <= t <= 59])
        }
        
        # Sort by frequency
        sorted_ranges = sorted(time_ranges.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'time_range': time_range, 'count': count}
            for time_range, count in sorted_ranges[:3]
            if count > 0
        ]
    
    def _generate_hold_time_recommendations(self, violations: List[Dict]) -> List[str]:
        """Generate recommendations based on violation patterns."""
        if not violations:
            return ["Hold time compliance is excellent - continue current practices"]
        
        recommendations = []
        
        # Check for frequent violations
        if len(violations) > 10:
            recommendations.append("Consider implementing position hold reminders or alerts")
        
        # Check for very early closure attempts
        very_early = len([v for v in violations if v['violation']['current_hold_time'] < 20])
        if very_early > len(violations) * 0.5:
            recommendations.append("Review trade setup strategy - many positions closed within 20 seconds")
        
        # Check for consistent pattern around 45-50 seconds
        mid_range = len([v for v in violations if 45 <= v['violation']['current_hold_time'] <= 55])
        if mid_range > len(violations) * 0.3:
            recommendations.append("Consider waiting full 60 seconds - many attempts just before minimum")
        
        if not recommendations:
            recommendations.append("Review position management timing to reduce hold time violations")
        
        return recommendations
    
    def cleanup_closed_positions(self, closed_position_ids: List[str]) -> None:
        """
        Clean up tracking data for closed positions.
        
        Args:
            closed_position_ids: List of position IDs that have been closed
        """
        cleaned_count = 0
        
        for position_id in closed_position_ids:
            # Remove from position timers
            if position_id in self.position_timers:
                del self.position_timers[position_id]
                cleaned_count += 1
            
            # Remove from exempted positions
            if position_id in self.exempted_positions:
                self.exempted_positions.remove(position_id)
            
            # Remove from early closure attempts
            if position_id in self.early_closure_attempts:
                del self.early_closure_attempts[position_id]
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up hold time tracking for {cleaned_count} closed positions")
    
    async def start_hold_time_monitoring(self, positions: List[Position]) -> None:
        """
        Start continuous hold time monitoring.
        
        Args:
            positions: List of positions to monitor
        """
        logger.info(f"Starting hold time monitoring for {len(positions)} positions")
        
        while self.monitoring_active:
            try:
                for position in positions:
                    # Check if position is still open
                    if not getattr(position, 'is_open', True):
                        continue
                    
                    # Get hold status
                    status = self.get_position_hold_status(position)
                    
                    # Log approaching minimum
                    if (status['status'] == HoldTimeStatus.APPROACHING_MINIMUM.value and
                        status['time_remaining_seconds'] <= 5):
                        logger.info(f"Position {position.position_id} approaching minimum hold time: {status['time_remaining_seconds']}s remaining")
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in hold time monitoring: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    def stop_hold_time_monitoring(self) -> None:
        """Stop hold time monitoring."""
        self.monitoring_active = False
        logger.info("Hold time monitoring stopped")
    
    def get_real_time_countdown(self, position_id: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time countdown for position.
        
        Args:
            position_id: Position to get countdown for
            
        Returns:
            Real-time countdown data or None if position not found
        """
        if position_id not in self.position_timers:
            return None
        
        open_time = self.position_timers[position_id]
        current_time = datetime.utcnow()
        
        hold_duration = int((current_time - open_time).total_seconds())
        time_remaining = max(0, self.minimum_hold_seconds - hold_duration)
        
        if time_remaining == 0:
            return None  # No countdown needed
        
        return {
            'position_id': position_id,
            'seconds_remaining': time_remaining,
            'countdown_display': f"00:{time_remaining:02d}",
            'percentage_complete': (hold_duration / self.minimum_hold_seconds) * 100,
            'can_close_in': f"{time_remaining}s",
            'timestamp': current_time.isoformat()
        }