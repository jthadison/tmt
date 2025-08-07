"""
Rules Engine for Prop Firm Compliance

Validates trades against prop firm specific rules and tracks violations.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .models import (
    TradingAccount, TradeOrder, Position, NewsEvent, ValidationRequest,
    ValidationResult, ComplianceViolation, ViolationType, ComplianceStatus
)
from .prop_firm_configs import get_prop_firm_config, PropFirm


logger = logging.getLogger(__name__)


class PropFirmRuleViolation(Exception):
    """Base exception for prop firm rule violations"""
    def __init__(self, violation_type: ViolationType, message: str, details: dict = None):
        self.violation_type = violation_type
        self.details = details or {}
        super().__init__(message)


class RulesEngine:
    """Core rules validation engine"""
    
    def __init__(self):
        self.logger = logger
    
    async def validate_trade(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        current_positions: List[Position] = None,
        upcoming_news: List[NewsEvent] = None
    ) -> ValidationResult:
        """
        Validate a trade order against all prop firm rules
        
        Args:
            account: Trading account with current state
            trade_order: Trade order to validate
            current_positions: Current open positions
            upcoming_news: Upcoming news events
            
        Returns:
            ValidationResult with validation status and any violations
        """
        current_positions = current_positions or []
        upcoming_news = upcoming_news or []
        
        violations = []
        warnings = []
        details = {}
        
        try:
            # Get prop firm configuration
            config = get_prop_firm_config(account.prop_firm)
            
            # Run all validation checks
            await self._validate_daily_loss_limit(account, trade_order, violations, warnings, details)
            await self._validate_max_drawdown(account, trade_order, violations, warnings, details)
            await self._validate_position_limits(account, trade_order, current_positions, violations, warnings, details)
            await self._validate_position_size(account, trade_order, violations, warnings, details)
            await self._validate_news_restrictions(account, trade_order, upcoming_news, violations, warnings, details)
            await self._validate_weekend_restrictions(account, trade_order, violations, warnings, details)
            await self._validate_stop_loss_requirements(account, trade_order, violations, warnings, details)
            await self._validate_hold_time_restrictions(account, trade_order, current_positions, violations, warnings, details)
            await self._validate_consistency_rules(account, trade_order, violations, warnings, details)
            
            # Determine overall compliance status
            if violations:
                if any(v in [ViolationType.DAILY_LOSS_EXCEEDED, ViolationType.MAX_DRAWDOWN_EXCEEDED] for v in violations):
                    status = ComplianceStatus.SUSPENDED
                else:
                    status = ComplianceStatus.VIOLATION
                is_valid = False
                reason = f"Trade violates {len(violations)} rule(s): {', '.join([v.value for v in violations])}"
            elif warnings:
                status = ComplianceStatus.WARNING
                is_valid = True
                reason = f"Trade approved with {len(warnings)} warning(s)"
            else:
                status = ComplianceStatus.COMPLIANT
                is_valid = True
                reason = "Trade complies with all prop firm rules"
            
            return ValidationResult(
                is_valid=is_valid,
                compliance_status=status,
                violations=violations,
                warnings=warnings,
                reason=reason,
                details=details
            )
            
        except Exception as e:
            self.logger.error(f"Error validating trade for account {account.account_id}: {e}")
            return ValidationResult(
                is_valid=False,
                compliance_status=ComplianceStatus.VIOLATION,
                violations=[ViolationType.DAILY_LOSS_EXCEEDED],  # Default to safe violation
                warnings=[],
                reason=f"Validation error: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _validate_daily_loss_limit(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate daily loss limit"""
        config = get_prop_firm_config(account.prop_firm)
        daily_limit = account.initial_balance * config.daily_loss_limit_pct
        
        # Calculate potential P&L impact (simplified - would need real price data)
        potential_loss = abs(trade_order.quantity) * Decimal("50")  # Estimated risk
        projected_daily_pnl = account.daily_pnl - potential_loss
        
        details.update({
            "daily_loss_limit": float(daily_limit),
            "current_daily_pnl": float(account.daily_pnl),
            "projected_daily_pnl": float(projected_daily_pnl),
            "daily_loss_remaining": float(daily_limit + account.daily_pnl)
        })
        
        if account.daily_pnl <= -daily_limit:
            violations.append(ViolationType.DAILY_LOSS_EXCEEDED)
        elif projected_daily_pnl <= -daily_limit:
            warnings.append(f"Trade may exceed daily loss limit")
        elif account.daily_pnl <= -daily_limit * Decimal("0.8"):
            warnings.append(f"Approaching daily loss limit (80% used)")
    
    async def _validate_max_drawdown(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate maximum drawdown limit"""
        config = get_prop_firm_config(account.prop_firm)
        max_drawdown_limit = account.initial_balance * config.max_drawdown_pct
        
        # For trailing drawdown, use peak balance; for static, use initial balance
        if config.trailing_drawdown:
            # Simplified - would track actual peak balance
            reference_balance = max(account.initial_balance, account.current_balance)
        else:
            reference_balance = account.initial_balance
        
        current_drawdown = reference_balance - account.current_balance
        
        details.update({
            "max_drawdown_limit": float(max_drawdown_limit),
            "current_drawdown": float(current_drawdown),
            "drawdown_remaining": float(max_drawdown_limit - current_drawdown),
            "trailing_drawdown": config.trailing_drawdown
        })
        
        if current_drawdown >= max_drawdown_limit:
            violations.append(ViolationType.MAX_DRAWDOWN_EXCEEDED)
        elif current_drawdown >= max_drawdown_limit * Decimal("0.9"):
            warnings.append(f"Approaching maximum drawdown limit (90% used)")
    
    async def _validate_position_limits(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        current_positions: List[Position],
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate maximum concurrent positions"""
        config = get_prop_firm_config(account.prop_firm)
        max_positions = config.max_concurrent_positions
        current_position_count = len(current_positions)
        
        details.update({
            "max_positions_allowed": max_positions,
            "current_positions": current_position_count,
            "positions_remaining": max_positions - current_position_count
        })
        
        if current_position_count >= max_positions:
            violations.append(ViolationType.MAX_POSITIONS_EXCEEDED)
        elif current_position_count >= max_positions * 0.8:
            warnings.append(f"Approaching maximum position limit ({current_position_count}/{max_positions})")
    
    async def _validate_position_size(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate position size against account balance and prop firm limits"""
        config = get_prop_firm_config(account.prop_firm)
        
        # Check against maximum lot size for account balance
        max_lots = None
        
        # Find the appropriate tier (look for the closest match)
        if config.max_lot_sizes:
            for balance_threshold in sorted(config.max_lot_sizes.keys(), key=lambda x: int(x), reverse=True):
                if account.current_balance >= Decimal(balance_threshold):
                    max_lots = config.max_lot_sizes[balance_threshold]
                    break
            
            # If no exact match, use the smallest tier as fallback
            if max_lots is None:
                smallest_tier = min(config.max_lot_sizes.keys(), key=lambda x: int(x))
                max_lots = config.max_lot_sizes[smallest_tier]
        
        if max_lots and trade_order.quantity > max_lots:
            violations.append(ViolationType.POSITION_SIZE_VIOLATION)
        
        # Check risk per trade percentage
        if config.max_risk_per_trade_pct > 0:
            max_risk_amount = account.current_balance * config.max_risk_per_trade_pct
            # Simplified risk calculation - would need actual pip values and stop loss
            estimated_risk = trade_order.quantity * Decimal("100")  # Placeholder
            
            if estimated_risk > max_risk_amount:
                violations.append(ViolationType.POSITION_SIZE_VIOLATION)
        
        details.update({
            "max_lot_size": float(max_lots) if max_lots else None,
            "requested_lot_size": float(trade_order.quantity),
            "max_risk_per_trade": float(config.max_risk_per_trade_pct * 100),
            "account_balance": float(account.current_balance)
        })
    
    async def _validate_news_restrictions(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        upcoming_news: List[NewsEvent],
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate news trading restrictions"""
        config = get_prop_firm_config(account.prop_firm)
        
        if config.news_buffer_minutes == 0:
            return  # News trading allowed
        
        now = datetime.utcnow()
        buffer_time = timedelta(minutes=config.news_buffer_minutes)
        
        # Check for high-impact news within buffer time
        for news_event in upcoming_news:
            if not news_event.is_high_impact():
                continue
            
            time_to_news = news_event.timestamp - now
            if timedelta(0) <= time_to_news <= buffer_time:
                violations.append(ViolationType.NEWS_BLACKOUT_VIOLATION)
                details["blocked_news_event"] = {
                    "title": news_event.title,
                    "time": news_event.timestamp.isoformat(),
                    "minutes_until": time_to_news.total_seconds() / 60
                }
                break
            elif timedelta(0) <= time_to_news <= buffer_time * 2:
                warnings.append(f"High-impact news in {int(time_to_news.total_seconds() / 60)} minutes")
    
    async def _validate_weekend_restrictions(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate weekend holding restrictions"""
        config = get_prop_firm_config(account.prop_firm)
        
        if not config.weekend_closure_required:
            return
        
        now = datetime.utcnow()
        # Check if it's Friday after market close (simplified - would need actual market hours)
        if now.weekday() == 4 and now.hour >= 21:  # Friday after 9 PM UTC
            violations.append(ViolationType.WEEKEND_HOLDING_VIOLATION)
            details["weekend_closure_time"] = "Friday 21:00 UTC"
    
    async def _validate_stop_loss_requirements(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate mandatory stop loss requirements"""
        config = get_prop_firm_config(account.prop_firm)
        
        if config.mandatory_stop_loss and not trade_order.stop_loss:
            violations.append(ViolationType.MISSING_STOP_LOSS)
            details["stop_loss_required"] = True
    
    async def _validate_hold_time_restrictions(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        current_positions: List[Position],
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate minimum hold time for position closure"""
        config = get_prop_firm_config(account.prop_firm)
        
        if config.min_hold_time_seconds == 0:
            return
        
        # This would be used when closing positions
        # For now, just document the requirement
        details.update({
            "min_hold_time_seconds": config.min_hold_time_seconds,
            "min_hold_time_minutes": config.min_hold_time_seconds / 60
        })
    
    async def _validate_consistency_rules(
        self,
        account: TradingAccount,
        trade_order: TradeOrder,
        violations: List[ViolationType],
        warnings: List[str],
        details: dict
    ):
        """Validate consistency rules (lot size variance, daily profit caps)"""
        config = get_prop_firm_config(account.prop_firm)
        consistency_rules = config.consistency_rules
        
        if not consistency_rules:
            return
        
        # Daily profit cap validation (simplified - would need historical data)
        if "daily_profit_cap_pct" in consistency_rules:
            daily_cap_pct = consistency_rules["daily_profit_cap_pct"]
            # This would check against total profit history
            details["daily_profit_cap_pct"] = float(daily_cap_pct * 100)
        
        # Lot size consistency (simplified - would need trade history)
        if "lot_size_variance_max" in consistency_rules:
            max_variance = consistency_rules["lot_size_variance_max"]
            details["max_lot_size_variance"] = max_variance


class ComplianceMonitor:
    """Real-time compliance monitoring"""
    
    def __init__(self, rules_engine: RulesEngine):
        self.rules_engine = rules_engine
        self.logger = logger
    
    async def update_account_pnl(
        self,
        account: TradingAccount,
        realized_pnl: Decimal,
        unrealized_pnl: Decimal
    ) -> bool:
        """
        Update account P&L and check for violations
        
        Returns:
            bool: True if account remains compliant, False if violations detected
        """
        # Update daily P&L
        account.daily_pnl += realized_pnl
        account.current_balance += realized_pnl
        
        # Check for immediate violations
        config = get_prop_firm_config(account.prop_firm)
        daily_limit = account.initial_balance * config.daily_loss_limit_pct
        
        if account.daily_pnl <= -daily_limit:
            account.status = ComplianceStatus.SUSPENDED
            self.logger.critical(f"Account {account.account_id} exceeded daily loss limit")
            return False
        
        max_drawdown_limit = account.initial_balance * config.max_drawdown_pct
        current_drawdown = account.initial_balance - account.current_balance
        
        if current_drawdown >= max_drawdown_limit:
            account.status = ComplianceStatus.SUSPENDED
            self.logger.critical(f"Account {account.account_id} exceeded maximum drawdown")
            return False
        
        return True
    
    async def reset_daily_pnl(self, account: TradingAccount):
        """Reset daily P&L at market close"""
        account.daily_pnl = Decimal("0.0")
        account.last_reset_date = datetime.utcnow()
        account.trading_days_completed += 1
        self.logger.info(f"Reset daily P&L for account {account.account_id}")
    
    async def check_position_hold_time(
        self,
        account: TradingAccount,
        position: Position
    ) -> bool:
        """
        Check if position has met minimum hold time requirement
        
        Returns:
            bool: True if position can be closed, False if hold time not met
        """
        config = get_prop_firm_config(account.prop_firm)
        
        if config.min_hold_time_seconds == 0:
            return True
        
        hold_time = datetime.utcnow() - position.opened_at
        required_hold_time = timedelta(seconds=config.min_hold_time_seconds)
        
        return hold_time >= required_hold_time