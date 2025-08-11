"""
Drawdown-Based Position Size Adjuster
=====================================

This module implements drawdown-based position size adjustments that
progressively reduce position sizes as account drawdown increases,
helping to preserve capital during losing streaks.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID
import datetime

from ..models import DrawdownLevel, AccountContext

logger = logging.getLogger(__name__)


class DrawdownTracker:
    """Tracks account drawdown and peak equity for drawdown calculations."""
    
    def __init__(self):
        # In-memory storage for demo - production would use database
        self._account_data = {}
    
    async def get_current_drawdown(self, account_id: UUID) -> 'DrawdownData':
        """Get current drawdown information for an account."""
        # In production, this would query the database for account equity history
        # For now, simulate realistic drawdown data
        
        if account_id not in self._account_data:
            # Initialize with no drawdown
            self._account_data[account_id] = {
                'peak_equity': Decimal('10000.00'),
                'current_equity': Decimal('10000.00'),
                'last_updated': datetime.datetime.utcnow()
            }
        
        account_data = self._account_data[account_id]
        
        peak_equity = account_data['peak_equity']
        current_equity = account_data['current_equity']
        
        drawdown_amount = peak_equity - current_equity
        drawdown_percentage = (drawdown_amount / peak_equity) * Decimal('100') if peak_equity > 0 else Decimal('0')
        
        return DrawdownData(
            account_id=account_id,
            peak_equity=peak_equity,
            current_equity=current_equity,
            drawdown_amount=drawdown_amount,
            percentage=drawdown_percentage,
            days_in_drawdown=0,  # Simplified for demo
            last_updated=account_data['last_updated']
        )
    
    async def update_equity(self, account_id: UUID, new_equity: Decimal):
        """Update account equity and recalculate peak if needed."""
        if account_id not in self._account_data:
            self._account_data[account_id] = {
                'peak_equity': new_equity,
                'current_equity': new_equity,
                'last_updated': datetime.datetime.utcnow()
            }
        else:
            account_data = self._account_data[account_id]
            account_data['current_equity'] = new_equity
            account_data['last_updated'] = datetime.datetime.utcnow()
            
            # Update peak equity if new high
            if new_equity > account_data['peak_equity']:
                account_data['peak_equity'] = new_equity


class DrawdownData:
    """Data class for drawdown information."""
    
    def __init__(self, account_id: UUID, peak_equity: Decimal, current_equity: Decimal,
                 drawdown_amount: Decimal, percentage: Decimal, days_in_drawdown: int,
                 last_updated: datetime.datetime):
        self.account_id = account_id
        self.peak_equity = peak_equity
        self.current_equity = current_equity
        self.drawdown_amount = drawdown_amount
        self.percentage = percentage
        self.days_in_drawdown = days_in_drawdown
        self.last_updated = last_updated


class DrawdownAdjuster:
    """
    Adjusts position sizes based on account drawdown levels to preserve capital
    during losing streaks and implement progressive risk reduction.
    """
    
    def __init__(self, drawdown_tracker: DrawdownTracker):
        self.drawdown_tracker = drawdown_tracker
        
        # Drawdown thresholds (percentage)
        self.drawdown_thresholds = {
            DrawdownLevel.MINIMAL: Decimal("1.0"),    # < 1%
            DrawdownLevel.SMALL: Decimal("3.0"),      # 1-3%
            DrawdownLevel.MODERATE: Decimal("5.0"),   # 3-5%
            DrawdownLevel.LARGE: Decimal("8.0"),      # 5-8%
            DrawdownLevel.EXTREME: Decimal("15.0")    # > 8%
        }
        
        # Size reduction factors by drawdown level
        self.reduction_factors = {
            DrawdownLevel.MINIMAL: Decimal("1.00"),   # No reduction
            DrawdownLevel.SMALL: Decimal("0.90"),     # 10% reduction
            DrawdownLevel.MODERATE: Decimal("0.50"),  # 50% reduction (as per AC requirement)
            DrawdownLevel.LARGE: Decimal("0.30"),     # 70% reduction
            DrawdownLevel.EXTREME: Decimal("0.10")    # 90% reduction (emergency mode)
        }
        
        # Recovery thresholds - how much drawdown must recover before increasing size
        self.recovery_thresholds = {
            DrawdownLevel.SMALL: Decimal("0.5"),      # 0.5% recovery needed
            DrawdownLevel.MODERATE: Decimal("1.0"),   # 1% recovery needed
            DrawdownLevel.LARGE: Decimal("2.0"),      # 2% recovery needed
            DrawdownLevel.EXTREME: Decimal("4.0")     # 4% recovery needed
        }
    
    async def adjust_size(self, base_size: Decimal, account_id: UUID) -> Decimal:
        """
        Apply drawdown-based size adjustment.
        
        Args:
            base_size: Base position size to adjust
            account_id: Account identifier
            
        Returns:
            Drawdown-adjusted position size
        """
        try:
            # Get current drawdown information
            drawdown_data = await self.drawdown_tracker.get_current_drawdown(account_id)
            
            # Classify drawdown level
            drawdown_level = self._classify_drawdown_level(drawdown_data.percentage)
            
            # Get reduction factor
            reduction_factor = self.reduction_factors[drawdown_level]
            
            # Apply reduction
            adjusted_size = base_size * reduction_factor
            
            # Check for emergency halt conditions
            if await self._should_halt_trading(drawdown_data):
                logger.critical(f"EMERGENCY HALT: Account {account_id} drawdown {drawdown_data.percentage}% "
                               f"exceeds emergency threshold. Setting position size to zero.")
                adjusted_size = Decimal("0")
            
            logger.info(f"Drawdown adjustment for account {account_id}: "
                       f"{drawdown_data.percentage:.2f}% drawdown ({drawdown_level.value}), "
                       f"factor={reduction_factor}, size: {base_size} -> {adjusted_size}")
            
            return adjusted_size
            
        except Exception as e:
            logger.error(f"Drawdown adjustment failed for account {account_id}: {str(e)}")
            # Conservative approach: reduce size significantly if adjustment fails
            return base_size * Decimal("0.5")
    
    def _classify_drawdown_level(self, drawdown_pct: Decimal) -> DrawdownLevel:
        """Classify drawdown level based on percentage."""
        drawdown_float = float(drawdown_pct)
        
        if drawdown_float < 1.0:
            return DrawdownLevel.MINIMAL
        elif drawdown_float < 3.0:
            return DrawdownLevel.SMALL
        elif drawdown_float < 5.0:
            return DrawdownLevel.MODERATE
        elif drawdown_float < 8.0:
            return DrawdownLevel.LARGE
        else:
            return DrawdownLevel.EXTREME
    
    async def _should_halt_trading(self, drawdown_data: DrawdownData) -> bool:
        """
        Determine if trading should be halted due to extreme drawdown.
        
        Emergency halt triggers:
        - Drawdown > 15% (extreme level)
        - Drawdown > 20% (absolute emergency)
        """
        emergency_threshold = Decimal("15.0")
        absolute_emergency = Decimal("20.0")
        
        if drawdown_data.percentage >= absolute_emergency:
            return True
        
        if drawdown_data.percentage >= emergency_threshold:
            # Additional checks could be added here:
            # - Time-based halts (e.g., halt for 24 hours)
            # - Consecutive loss limits
            # - Velocity of drawdown (rapid losses)
            return True
        
        return False
    
    async def get_drawdown_recovery_status(self, account_id: UUID) -> Dict[str, any]:
        """
        Get detailed drawdown and recovery status for monitoring.
        
        Returns:
            Dictionary with drawdown status information
        """
        drawdown_data = await self.drawdown_tracker.get_current_drawdown(account_id)
        drawdown_level = self._classify_drawdown_level(drawdown_data.percentage)
        reduction_factor = self.reduction_factors[drawdown_level]
        
        return {
            'account_id': str(account_id),
            'current_equity': float(drawdown_data.current_equity),
            'peak_equity': float(drawdown_data.peak_equity),
            'drawdown_amount': float(drawdown_data.drawdown_amount),
            'drawdown_percentage': float(drawdown_data.percentage),
            'drawdown_level': drawdown_level.value,
            'size_reduction_factor': float(reduction_factor),
            'days_in_drawdown': drawdown_data.days_in_drawdown,
            'trading_halted': await self._should_halt_trading(drawdown_data),
            'last_updated': drawdown_data.last_updated.isoformat()
        }
    
    async def configure_drawdown_thresholds(self, account_id: UUID, custom_thresholds: Dict[str, Decimal]):
        """
        Configure custom drawdown thresholds for specific accounts.
        
        Some prop firms may have different risk tolerance levels.
        """
        # In production, this would store custom thresholds per account in database
        # For now, just log the configuration
        logger.info(f"Custom drawdown thresholds configured for account {account_id}: {custom_thresholds}")
    
    def get_recommended_recovery_actions(self, drawdown_level: DrawdownLevel) -> List[str]:
        """
        Get recommended recovery actions based on drawdown level.
        
        Returns:
            List of recommended actions for the drawdown level
        """
        recommendations = {
            DrawdownLevel.MINIMAL: [
                "Continue normal trading operations",
                "Monitor for any developing patterns"
            ],
            DrawdownLevel.SMALL: [
                "Review recent trades for improvement opportunities",
                "Consider reducing risk slightly until recovery",
                "Analyze market conditions for adverse factors"
            ],
            DrawdownLevel.MODERATE: [
                "Implement 50% position size reduction immediately",
                "Review and analyze all losing trades",
                "Consider pausing trading in unfavorable market conditions",
                "Focus on high-probability setups only"
            ],
            DrawdownLevel.LARGE: [
                "Implement 70% position size reduction",
                "Comprehensive strategy review required",
                "Consider temporary trading suspension",
                "Seek additional analysis of market conditions"
            ],
            DrawdownLevel.EXTREME: [
                "Emergency protocols activated - 90% size reduction",
                "Full strategy and risk management review required",
                "Consider trading suspension pending review",
                "Immediate consultation with risk management team"
            ]
        }
        
        return recommendations.get(drawdown_level, [])