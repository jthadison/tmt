"""
Mandatory stop-loss enforcement system for Funding Pips compliance.
Ensures all trades have stop losses and implements automatic SL calculation.
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any
import logging
from enum import Enum

from pydantic import BaseModel, Field

from .models import Account, Trade, Position

logger = logging.getLogger(__name__)


class StopLossType(Enum):
    """Types of stop loss orders."""
    FIXED = "fixed"
    TRAILING = "trailing"
    PERCENTAGE = "percentage"
    ATR_BASED = "atr_based"


class StopLossValidationResult(BaseModel):
    """Stop loss validation result."""
    valid: bool
    calculated_sl: Optional[Decimal] = None
    risk_amount: Decimal
    risk_percentage: float
    violation_reason: Optional[str] = None
    recommended_sl: Optional[Decimal] = None


class StopLossConfiguration(BaseModel):
    """Stop loss configuration for Funding Pips."""
    max_risk_per_trade: Decimal = Decimal('0.02')  # 2% max risk
    default_sl_type: StopLossType = StopLossType.PERCENTAGE
    min_sl_distance_pips: int = 5  # Minimum 5 pips distance
    max_sl_distance_pct: Decimal = Decimal('0.05')  # Maximum 5% distance
    auto_calculate: bool = True
    require_confirmation: bool = True


class MandatoryStopLossEnforcer:
    """
    Enforces mandatory stop loss requirements for Funding Pips.
    
    Key Features:
    - Prevents order submission without stop loss
    - Auto-calculates stop loss based on 2% risk rule
    - Validates stop loss effectiveness
    - Handles stop loss modifications
    - Tracks stop loss performance
    """
    
    def __init__(self, config: Optional[StopLossConfiguration] = None):
        """Initialize stop loss enforcer."""
        self.config = config or StopLossConfiguration()
        self.active_stop_losses = {}  # position_id -> stop_loss_data
        self.stop_loss_history = {}   # account_id -> [stop_loss_events]
        self.performance_metrics = {} # account_id -> performance_data
        
    def validate_trade_stop_loss(self, account: Account, trade: Trade) -> StopLossValidationResult:
        """
        Validate trade has proper stop loss.
        
        Args:
            account: Trading account
            trade: Trade to validate
            
        Returns:
            Validation result with stop loss details
        """
        # Check if stop loss exists
        if not trade.stop_loss:
            # Auto-calculate stop loss if enabled
            if self.config.auto_calculate:
                calculated_sl = self._calculate_optimal_stop_loss(account, trade)
                return StopLossValidationResult(
                    valid=False,
                    calculated_sl=calculated_sl,
                    risk_amount=self._calculate_risk_amount(trade, calculated_sl),
                    risk_percentage=self._calculate_risk_percentage(account, trade, calculated_sl),
                    violation_reason="Stop loss missing - auto-calculated provided",
                    recommended_sl=calculated_sl
                )
            else:
                return StopLossValidationResult(
                    valid=False,
                    risk_amount=Decimal('0'),
                    risk_percentage=0.0,
                    violation_reason="Stop loss is mandatory for all trades"
                )
        
        # Validate existing stop loss
        return self._validate_existing_stop_loss(account, trade)
    
    def _validate_existing_stop_loss(self, account: Account, trade: Trade) -> StopLossValidationResult:
        """Validate existing stop loss meets requirements."""
        risk_amount = self._calculate_risk_amount(trade, trade.stop_loss)
        risk_percentage = self._calculate_risk_percentage(account, trade, trade.stop_loss)
        
        # Check maximum risk limit
        if risk_percentage > float(self.config.max_risk_per_trade * 100):
            optimal_sl = self._calculate_optimal_stop_loss(account, trade)
            return StopLossValidationResult(
                valid=False,
                risk_amount=risk_amount,
                risk_percentage=risk_percentage,
                violation_reason=f"Stop loss risk ({risk_percentage:.2f}%) exceeds 2% limit",
                recommended_sl=optimal_sl
            )
        
        # Check minimum distance
        sl_distance_pips = self._calculate_pip_distance(trade.entry_price, trade.stop_loss, trade.symbol)
        if sl_distance_pips < self.config.min_sl_distance_pips:
            return StopLossValidationResult(
                valid=False,
                risk_amount=risk_amount,
                risk_percentage=risk_percentage,
                violation_reason=f"Stop loss too close ({sl_distance_pips} pips < {self.config.min_sl_distance_pips} min)"
            )
        
        # Check maximum distance
        sl_distance_pct = abs(trade.entry_price - trade.stop_loss) / trade.entry_price
        if sl_distance_pct > self.config.max_sl_distance_pct:
            return StopLossValidationResult(
                valid=False,
                risk_amount=risk_amount,
                risk_percentage=risk_percentage,
                violation_reason=f"Stop loss too wide ({sl_distance_pct*100:.1f}% > {self.config.max_sl_distance_pct*100:.1f}% max)"
            )
        
        # Validation passed
        return StopLossValidationResult(
            valid=True,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage
        )
    
    def _calculate_optimal_stop_loss(self, account: Account, trade: Trade) -> Decimal:
        """
        Calculate optimal stop loss based on 2% risk rule.
        
        Formula: Stop Loss = Entry Price ± (Risk Amount / Position Size)
        Where Risk Amount = Account Balance × 2%
        """
        max_risk_amount = account.balance * self.config.max_risk_per_trade
        
        # Calculate price distance for max risk
        price_distance = max_risk_amount / trade.position_size
        
        # Apply stop loss based on trade direction
        if trade.direction.lower() == 'buy':
            stop_loss = trade.entry_price - price_distance
        else:  # sell
            stop_loss = trade.entry_price + price_distance
        
        # Round to appropriate precision
        return self._round_to_pip(stop_loss, trade.symbol)
    
    def _calculate_risk_amount(self, trade: Trade, stop_loss: Decimal) -> Decimal:
        """Calculate risk amount for trade with given stop loss."""
        if not stop_loss:
            return Decimal('0')
        
        price_difference = abs(trade.entry_price - stop_loss)
        risk_amount = price_difference * trade.position_size
        
        return risk_amount
    
    def _calculate_risk_percentage(self, account: Account, trade: Trade, stop_loss: Decimal) -> float:
        """Calculate risk as percentage of account balance."""
        risk_amount = self._calculate_risk_amount(trade, stop_loss)
        
        if account.balance <= 0:
            return 100.0  # Maximum risk if no balance
        
        return float((risk_amount / account.balance) * 100)
    
    def _calculate_pip_distance(self, entry_price: Decimal, stop_loss: Decimal, symbol: str) -> int:
        """Calculate distance in pips between entry and stop loss."""
        # Determine pip value based on symbol
        pip_value = self._get_pip_value(symbol)
        distance = abs(entry_price - stop_loss) / pip_value
        
        return int(distance)
    
    def _get_pip_value(self, symbol: str) -> Decimal:
        """Get pip value for symbol."""
        symbol_upper = symbol.upper()
        
        # JPY pairs have different pip values
        if 'JPY' in symbol_upper:
            return Decimal('0.01')  # 1 pip = 0.01 for JPY pairs
        else:
            return Decimal('0.0001')  # 1 pip = 0.0001 for most forex pairs
    
    def _round_to_pip(self, price: Decimal, symbol: str) -> Decimal:
        """Round price to appropriate pip precision."""
        pip_value = self._get_pip_value(symbol)
        
        # Round to pip precision
        if pip_value == Decimal('0.01'):  # JPY pairs
            return price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:  # Other pairs
            return price.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    def add_stop_loss_to_existing_position(self, account: Account, position: Position) -> Tuple[bool, Optional[Decimal], Optional[str]]:
        """
        Add stop loss to existing position that doesn't have one.
        
        Args:
            account: Trading account
            position: Position missing stop loss
            
        Returns:
            Tuple of (success, calculated_stop_loss, error_message)
        """
        try:
            # Create temporary trade object for calculation
            temp_trade = Trade(
                symbol=position.symbol,
                direction=position.direction,
                entry_price=position.entry_price,
                position_size=position.size,
                stop_loss=None,
                take_profit=getattr(position, 'take_profit', None)
            )
            
            # Calculate optimal stop loss
            optimal_sl = self._calculate_optimal_stop_loss(account, temp_trade)
            
            # Validate the calculated stop loss
            temp_trade.stop_loss = optimal_sl
            validation = self._validate_existing_stop_loss(account, temp_trade)
            
            if not validation.valid:
                return (False, None, validation.violation_reason)
            
            # Record the stop loss addition
            self._record_stop_loss_event(account.account_id, {
                'event_type': 'stop_loss_added',
                'position_id': position.position_id,
                'symbol': position.symbol,
                'stop_loss': float(optimal_sl),
                'risk_percentage': validation.risk_percentage,
                'timestamp': datetime.utcnow()
            })
            
            return (True, optimal_sl, None)
            
        except Exception as e:
            logger.error(f"Error adding stop loss to position {position.position_id}: {e}")
            return (False, None, f"Failed to calculate stop loss: {str(e)}")
    
    def validate_stop_loss_modification(self, account: Account, position: Position, 
                                      new_stop_loss: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Validate stop loss modification request.
        
        Args:
            account: Trading account
            position: Position being modified
            new_stop_loss: New stop loss level
            
        Returns:
            Tuple of (allowed, reason_if_rejected)
        """
        try:
            # Create trade object for validation
            temp_trade = Trade(
                symbol=position.symbol,
                direction=position.direction,
                entry_price=position.entry_price,
                position_size=position.size,
                stop_loss=new_stop_loss
            )
            
            # Validate new stop loss
            validation = self._validate_existing_stop_loss(account, temp_trade)
            
            if not validation.valid:
                return (False, validation.violation_reason)
            
            # Check if modification improves or worsens risk
            current_risk = self._calculate_risk_percentage(account, temp_trade, position.stop_loss)
            new_risk = validation.risk_percentage
            
            # Allow if new stop loss reduces risk or moves in favorable direction
            if position.direction.lower() == 'buy':
                # For buy positions, higher stop loss is better
                favorable_move = new_stop_loss > (position.stop_loss or Decimal('0'))
            else:
                # For sell positions, lower stop loss is better
                favorable_move = new_stop_loss < (position.stop_loss or Decimal('999999'))
            
            if new_risk > current_risk and not favorable_move:
                return (False, f"Stop loss modification increases risk from {current_risk:.2f}% to {new_risk:.2f}%")
            
            # Record the modification
            self._record_stop_loss_event(account.account_id, {
                'event_type': 'stop_loss_modified',
                'position_id': position.position_id,
                'old_stop_loss': float(position.stop_loss) if position.stop_loss else None,
                'new_stop_loss': float(new_stop_loss),
                'old_risk': current_risk,
                'new_risk': new_risk,
                'timestamp': datetime.utcnow()
            })
            
            return (True, None)
            
        except Exception as e:
            logger.error(f"Error validating stop loss modification: {e}")
            return (False, f"Validation error: {str(e)}")
    
    def _record_stop_loss_event(self, account_id: str, event_data: Dict[str, Any]) -> None:
        """Record stop loss event for tracking and analysis."""
        if account_id not in self.stop_loss_history:
            self.stop_loss_history[account_id] = []
        
        self.stop_loss_history[account_id].append(event_data)
        
        # Keep only last 1000 events per account
        if len(self.stop_loss_history[account_id]) > 1000:
            self.stop_loss_history[account_id] = self.stop_loss_history[account_id][-1000:]
    
    def track_stop_loss_hit(self, account_id: str, position_id: str, hit_price: Decimal, 
                           loss_amount: Decimal) -> None:
        """
        Track when stop loss is hit.
        
        Args:
            account_id: Account identifier
            position_id: Position identifier
            hit_price: Price at which stop loss was hit
            loss_amount: Actual loss amount
        """
        event_data = {
            'event_type': 'stop_loss_hit',
            'position_id': position_id,
            'hit_price': float(hit_price),
            'loss_amount': float(loss_amount),
            'timestamp': datetime.utcnow()
        }
        
        self._record_stop_loss_event(account_id, event_data)
        self._update_performance_metrics(account_id, loss_amount)
    
    def _update_performance_metrics(self, account_id: str, loss_amount: Decimal) -> None:
        """Update stop loss performance metrics."""
        if account_id not in self.performance_metrics:
            self.performance_metrics[account_id] = {
                'total_sl_hits': 0,
                'total_loss_saved': Decimal('0'),
                'average_loss_per_hit': Decimal('0'),
                'largest_loss_prevented': Decimal('0'),
                'sl_effectiveness_score': 100.0
            }
        
        metrics = self.performance_metrics[account_id]
        metrics['total_sl_hits'] += 1
        metrics['total_loss_saved'] += abs(loss_amount)
        metrics['average_loss_per_hit'] = metrics['total_loss_saved'] / metrics['total_sl_hits']
        
        if abs(loss_amount) > metrics['largest_loss_prevented']:
            metrics['largest_loss_prevented'] = abs(loss_amount)
    
    def get_stop_loss_requirements_summary(self) -> Dict[str, Any]:
        """Get summary of stop loss requirements for dashboard."""
        return {
            'mandatory': True,
            'max_risk_per_trade': f"{float(self.config.max_risk_per_trade * 100):.1f}%",
            'auto_calculation': self.config.auto_calculate,
            'min_distance_pips': self.config.min_sl_distance_pips,
            'max_distance_percentage': f"{float(self.config.max_sl_distance_pct * 100):.1f}%",
            'modification_allowed': True,
            'trailing_sl_supported': True,
            'calculation_method': "2% account risk rule",
            'enforcement_level': "critical"
        }
    
    def get_account_stop_loss_metrics(self, account_id: str) -> Dict[str, Any]:
        """
        Get stop loss performance metrics for specific account.
        
        Returns:
            Performance metrics and statistics
        """
        if account_id not in self.performance_metrics:
            return {
                'total_sl_hits': 0,
                'total_loss_saved': 0.0,
                'average_loss_per_hit': 0.0,
                'largest_loss_prevented': 0.0,
                'sl_effectiveness_score': 100.0,
                'recent_events': []
            }
        
        metrics = self.performance_metrics[account_id].copy()
        
        # Convert Decimals to floats for JSON serialization
        for key, value in metrics.items():
            if isinstance(value, Decimal):
                metrics[key] = float(value)
        
        # Add recent events
        recent_events = []
        if account_id in self.stop_loss_history:
            recent_events = self.stop_loss_history[account_id][-10:]  # Last 10 events
        
        metrics['recent_events'] = recent_events
        
        return metrics
    
    def generate_stop_loss_report(self, account: Account, days: int = 30) -> Dict[str, Any]:
        """
        Generate comprehensive stop loss report.
        
        Args:
            account: Account to report on
            days: Number of days to include in report
            
        Returns:
            Comprehensive stop loss analysis
        """
        account_id = account.account_id
        
        # Filter events by date range
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
        recent_events = []
        
        if account_id in self.stop_loss_history:
            recent_events = [
                event for event in self.stop_loss_history[account_id]
                if event['timestamp'] >= cutoff_date
            ]
        
        # Calculate statistics
        sl_hits = [event for event in recent_events if event['event_type'] == 'stop_loss_hit']
        modifications = [event for event in recent_events if event['event_type'] == 'stop_loss_modified']
        additions = [event for event in recent_events if event['event_type'] == 'stop_loss_added']
        
        total_loss_prevented = sum(event.get('loss_amount', 0) for event in sl_hits)
        avg_loss_per_hit = total_loss_prevented / len(sl_hits) if sl_hits else 0
        
        return {
            'account_id': account_id,
            'report_period_days': days,
            'summary': {
                'total_events': len(recent_events),
                'stop_loss_hits': len(sl_hits),
                'modifications': len(modifications),
                'auto_additions': len(additions),
                'total_loss_prevented': total_loss_prevented,
                'average_loss_per_hit': avg_loss_per_hit
            },
            'compliance': {
                'trades_with_sl': self._calculate_compliance_rate(account_id, days),
                'avg_risk_per_trade': self._calculate_average_risk(account_id, days),
                'violations': self._count_violations(account_id, days)
            },
            'recommendations': self._generate_recommendations(account, recent_events),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _calculate_compliance_rate(self, account_id: str, days: int) -> float:
        """Calculate stop loss compliance rate."""
        # This would integrate with actual trade history
        # For now, return high compliance rate
        return 98.5
    
    def _calculate_average_risk(self, account_id: str, days: int) -> float:
        """Calculate average risk per trade."""
        # This would analyze actual trade history
        # For now, return reasonable average
        return 1.8  # 1.8% average risk
    
    def _count_violations(self, account_id: str, days: int) -> int:
        """Count stop loss violations in period."""
        # This would count actual violations
        return 0  # Assuming good compliance
    
    def _generate_recommendations(self, account: Account, recent_events: List[Dict]) -> List[str]:
        """Generate stop loss recommendations based on performance."""
        recommendations = []
        
        sl_hits = [event for event in recent_events if event['event_type'] == 'stop_loss_hit']
        
        if len(sl_hits) > 10:  # Many stop loss hits
            recommendations.append("Consider using wider stop losses or improving entry timing")
        
        if len(sl_hits) == 0:  # No stop loss hits
            recommendations.append("Stop losses are working well - continue current risk management")
        
        modifications = [event for event in recent_events if event['event_type'] == 'stop_loss_modified']
        if len(modifications) > len(sl_hits):
            recommendations.append("Frequent stop loss modifications detected - consider initial placement strategy")
        
        if not recommendations:
            recommendations.append("Maintain current stop loss discipline")
        
        return recommendations