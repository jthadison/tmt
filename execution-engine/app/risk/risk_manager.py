"""
Risk Management System

Comprehensive risk management with pre-trade validation, position limits,
and real-time risk monitoring. Prevents over-leveraging and enforces risk controls.
"""

from decimal import Decimal
from typing import Dict, List, Optional, NamedTuple
from dataclasses import dataclass

import structlog

from ..core.models import Order, Position, RiskLimits, AccountSummary
from ..integrations.oanda_client import OandaExecutionClient

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of order validation."""
    is_valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class RiskMetrics(NamedTuple):
    """Risk metrics for an account."""
    current_leverage: Decimal
    margin_utilization: Decimal
    position_count: int
    daily_pl: Decimal
    max_position_size: Decimal
    risk_score: float  # 0-100 scale


class RiskManager:
    """
    Comprehensive risk management system.
    
    Features:
    - Pre-trade order validation
    - Position size limits
    - Leverage and margin controls
    - Daily loss limits
    - Kill switch functionality
    - Real-time risk monitoring
    """
    
    def __init__(
        self,
        oanda_client: OandaExecutionClient,
        default_risk_limits: Optional[RiskLimits] = None,
    ) -> None:
        self.oanda_client = oanda_client
        
        # Risk limits per account
        self.account_limits: Dict[str, RiskLimits] = {}
        
        # Default risk limits
        self.default_limits = default_risk_limits or RiskLimits(
            max_position_size=Decimal("100000"),  # 100k units
            max_positions_per_instrument=3,
            max_leverage=Decimal("30"),
            max_daily_loss=Decimal("1000"),  # $1000
            max_drawdown=Decimal("5000"),  # $5000
            required_margin_ratio=Decimal("0.02"),  # 2%
        )
        
        # Kill switch state
        self.kill_switch_active: Dict[str, bool] = {}
        
        # Risk monitoring cache
        self.risk_metrics_cache: Dict[str, RiskMetrics] = {}
        
        logger.info("RiskManager initialized")
    
    async def validate_order(self, order: Order) -> ValidationResult:
        """
        Comprehensive order validation.
        
        Checks:
        1. Account status and kill switch
        2. Position size limits
        3. Leverage limits
        4. Margin requirements
        5. Maximum positions per instrument
        6. Daily loss limits
        """
        try:
            account_id = order.account_id
            
            # Check kill switch
            if self.kill_switch_active.get(account_id, False):
                return ValidationResult(
                    is_valid=False,
                    error_code="KILL_SWITCH_ACTIVE",
                    error_message="Trading disabled by kill switch"
                )
            
            # Get risk limits for account
            limits = self.get_risk_limits(account_id)
            
            # Get current account state
            account_summary = await self.oanda_client.get_account_summary(account_id)
            if not account_summary:
                return ValidationResult(
                    is_valid=False,
                    error_code="ACCOUNT_NOT_FOUND",
                    error_message="Unable to retrieve account information"
                )
            
            # Validation checks
            validations = []
            
            # 1. Position size validation
            position_check = await self._validate_position_size(order, limits)
            validations.append(position_check)
            
            # 2. Leverage validation
            leverage_check = await self._validate_leverage(order, account_summary, limits)
            validations.append(leverage_check)
            
            # 3. Margin validation
            margin_check = await self._validate_margin_requirements(order, account_summary, limits)
            validations.append(margin_check)
            
            # 4. Position count validation
            position_count_check = await self._validate_position_count(order, limits)
            validations.append(position_count_check)
            
            # 5. Daily loss limit validation
            daily_loss_check = await self._validate_daily_loss_limit(order, account_summary, limits)
            validations.append(daily_loss_check)
            
            # 6. Instrument-specific validation
            instrument_check = await self._validate_instrument(order)
            validations.append(instrument_check)
            
            # Compile results
            failed_validations = [v for v in validations if not v.is_valid]
            all_warnings = []
            for v in validations:
                all_warnings.extend(v.warnings)
            
            if failed_validations:
                # Return first failure
                first_failure = failed_validations[0]
                return ValidationResult(
                    is_valid=False,
                    error_code=first_failure.error_code,
                    error_message=first_failure.error_message,
                    warnings=all_warnings
                )
            else:
                return ValidationResult(
                    is_valid=True,
                    warnings=all_warnings
                )
                
        except Exception as e:
            logger.error("Order validation error", order_id=order.id, error=str(e))
            return ValidationResult(
                is_valid=False,
                error_code="VALIDATION_ERROR",
                error_message=f"Validation failed: {str(e)}"
            )
    
    async def calculate_position_size(
        self,
        account_id: str,
        instrument: str,
        risk_amount: Decimal,
        stop_loss_distance: Decimal
    ) -> Decimal:
        """
        Calculate optimal position size based on risk parameters.
        
        Formula: Position Size = Risk Amount / Stop Loss Distance
        """
        try:
            if stop_loss_distance <= 0:
                logger.warning("Invalid stop loss distance", distance=stop_loss_distance)
                return Decimal("0")
            
            # Get account balance
            account_summary = await self.oanda_client.get_account_summary(account_id)
            if not account_summary:
                return Decimal("0")
            
            # Calculate position size
            position_size = risk_amount / stop_loss_distance
            
            # Apply position size limits
            limits = self.get_risk_limits(account_id)
            if limits.max_position_size:
                position_size = min(position_size, limits.max_position_size)
            
            # Apply account balance limits (e.g., max 10% of balance per trade)
            max_position_by_balance = account_summary.balance * Decimal("0.10")
            position_size = min(position_size, max_position_by_balance)
            
            logger.info("Position size calculated",
                       account_id=account_id,
                       instrument=instrument,
                       calculated_size=position_size,
                       risk_amount=risk_amount,
                       stop_distance=stop_loss_distance)
            
            return position_size
            
        except Exception as e:
            logger.error("Position size calculation error", error=str(e))
            return Decimal("0")
    
    async def check_risk_limits(self, account_id: str) -> RiskMetrics:
        """Calculate and return current risk metrics."""
        try:
            # Get account information
            account_summary = await self.oanda_client.get_account_summary(account_id)
            positions = await self.oanda_client.get_positions(account_id)
            
            if not account_summary:
                return RiskMetrics(
                    current_leverage=Decimal("0"),
                    margin_utilization=Decimal("0"),
                    position_count=0,
                    daily_pl=Decimal("0"),
                    max_position_size=Decimal("0"),
                    risk_score=0.0
                )
            
            # Calculate leverage
            total_notional = Decimal("0")
            for position in positions:
                if position.is_open():
                    current_price = await self.oanda_client.get_current_price(position.instrument)
                    if current_price:
                        notional = abs(position.units) * current_price
                        total_notional += notional
            
            current_leverage = total_notional / account_summary.balance if account_summary.balance > 0 else Decimal("0")
            
            # Calculate margin utilization
            margin_utilization = (account_summary.margin_used / account_summary.balance * 100) if account_summary.balance > 0 else Decimal("0")
            
            # Position count
            open_position_count = len([p for p in positions if p.is_open()])
            
            # Daily P&L (simplified - would need daily tracking)
            daily_pl = account_summary.unrealized_pl  # Placeholder
            
            # Max position size among current positions
            max_position_size = max([abs(p.units) for p in positions if p.is_open()], default=Decimal("0"))
            
            # Calculate risk score (0-100)
            risk_score = self._calculate_risk_score(
                current_leverage,
                margin_utilization,
                open_position_count,
                daily_pl,
                account_summary.balance
            )
            
            metrics = RiskMetrics(
                current_leverage=current_leverage,
                margin_utilization=margin_utilization,
                position_count=open_position_count,
                daily_pl=daily_pl,
                max_position_size=max_position_size,
                risk_score=risk_score
            )
            
            # Cache metrics
            self.risk_metrics_cache[account_id] = metrics
            
            return metrics
            
        except Exception as e:
            logger.error("Risk limit check error", account_id=account_id, error=str(e))
            return RiskMetrics(
                current_leverage=Decimal("0"),
                margin_utilization=Decimal("0"),
                position_count=0,
                daily_pl=Decimal("0"),
                max_position_size=Decimal("0"),
                risk_score=100.0  # Max risk on error
            )
    
    def activate_kill_switch(self, account_id: str, reason: str) -> None:
        """Activate emergency kill switch to stop all trading."""
        self.kill_switch_active[account_id] = True
        logger.critical("Kill switch activated", 
                       account_id=account_id, 
                       reason=reason)
    
    def deactivate_kill_switch(self, account_id: str, reason: str) -> None:
        """Deactivate kill switch to resume trading."""
        self.kill_switch_active[account_id] = False
        logger.warning("Kill switch deactivated", 
                      account_id=account_id, 
                      reason=reason)
    
    def is_kill_switch_active(self, account_id: str) -> bool:
        """Check if kill switch is active for an account."""
        return self.kill_switch_active.get(account_id, False)
    
    def set_risk_limits(self, account_id: str, limits: RiskLimits) -> None:
        """Set custom risk limits for an account."""
        self.account_limits[account_id] = limits
        logger.info("Risk limits updated", account_id=account_id, limits=limits)
    
    def get_risk_limits(self, account_id: str) -> RiskLimits:
        """Get risk limits for an account."""
        return self.account_limits.get(account_id, self.default_limits)
    
    # Private validation methods
    
    async def _validate_position_size(self, order: Order, limits: RiskLimits) -> ValidationResult:
        """Validate order position size against limits."""
        if limits.max_position_size and abs(order.units) > limits.max_position_size:
            return ValidationResult(
                is_valid=False,
                error_code="POSITION_SIZE_EXCEEDED",
                error_message=f"Order size {abs(order.units)} exceeds maximum {limits.max_position_size}"
            )
        
        return ValidationResult(is_valid=True)
    
    async def _validate_leverage(self, order: Order, account: AccountSummary, limits: RiskLimits) -> ValidationResult:
        """Validate that order won't exceed leverage limits."""
        if not limits.max_leverage:
            return ValidationResult(is_valid=True)
        
        try:
            # Estimate order notional value
            current_price = await self.oanda_client.get_current_price(order.instrument)
            if not current_price:
                return ValidationResult(
                    is_valid=True,
                    warnings=["Could not validate leverage - price unavailable"]
                )
            
            order_notional = abs(order.units) * current_price
            
            # Calculate current total notional
            positions = await self.oanda_client.get_positions(order.account_id)
            current_notional = Decimal("0")
            
            for position in positions:
                if position.is_open():
                    pos_price = await self.oanda_client.get_current_price(position.instrument)
                    if pos_price:
                        current_notional += abs(position.units) * pos_price
            
            # Calculate new leverage
            total_notional = current_notional + order_notional
            new_leverage = total_notional / account.balance if account.balance > 0 else Decimal("999")
            
            if new_leverage > limits.max_leverage:
                return ValidationResult(
                    is_valid=False,
                    error_code="LEVERAGE_EXCEEDED",
                    error_message=f"Order would result in leverage {new_leverage:.2f}x, max allowed {limits.max_leverage}x"
                )
            
            # Warning at 80% of limit
            if new_leverage > limits.max_leverage * Decimal("0.8"):
                return ValidationResult(
                    is_valid=True,
                    warnings=[f"High leverage warning: {new_leverage:.2f}x (limit: {limits.max_leverage}x)"]
                )
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.error("Leverage validation error", error=str(e))
            return ValidationResult(
                is_valid=True,
                warnings=["Could not validate leverage due to error"]
            )
    
    async def _validate_margin_requirements(self, order: Order, account: AccountSummary, limits: RiskLimits) -> ValidationResult:
        """Validate sufficient margin for order."""
        try:
            # Get margin requirement for order
            margin_info = await self.oanda_client.get_margin_info(
                account_id=order.account_id,
                instrument=order.instrument,
                units=abs(order.units)
            )
            
            if not margin_info:
                return ValidationResult(
                    is_valid=True,
                    warnings=["Could not validate margin requirements"]
                )
            
            required_margin = margin_info.margin_used
            available_margin = account.margin_available
            
            if required_margin > available_margin:
                return ValidationResult(
                    is_valid=False,
                    error_code="INSUFFICIENT_MARGIN",
                    error_message=f"Required margin {required_margin} exceeds available {available_margin}"
                )
            
            # Check minimum margin ratio if specified
            if limits.required_margin_ratio:
                margin_ratio = available_margin / account.balance if account.balance > 0 else Decimal("0")
                if margin_ratio < limits.required_margin_ratio:
                    return ValidationResult(
                        is_valid=False,
                        error_code="MARGIN_RATIO_TOO_LOW",
                        error_message=f"Margin ratio {margin_ratio:.4f} below required {limits.required_margin_ratio:.4f}"
                    )
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.error("Margin validation error", error=str(e))
            return ValidationResult(
                is_valid=True,
                warnings=["Could not validate margin requirements due to error"]
            )
    
    async def _validate_position_count(self, order: Order, limits: RiskLimits) -> ValidationResult:
        """Validate maximum positions per instrument."""
        if not limits.max_positions_per_instrument:
            return ValidationResult(is_valid=True)
        
        try:
            positions = await self.oanda_client.get_positions(order.account_id)
            instrument_positions = [p for p in positions if p.instrument == order.instrument and p.is_open()]
            
            current_count = len(instrument_positions)
            if current_count >= limits.max_positions_per_instrument:
                return ValidationResult(
                    is_valid=False,
                    error_code="MAX_POSITIONS_EXCEEDED",
                    error_message=f"Maximum {limits.max_positions_per_instrument} positions per instrument exceeded for {order.instrument}"
                )
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.error("Position count validation error", error=str(e))
            return ValidationResult(
                is_valid=True,
                warnings=["Could not validate position count due to error"]
            )
    
    async def _validate_daily_loss_limit(self, order: Order, account: AccountSummary, limits: RiskLimits) -> ValidationResult:
        """Validate daily loss limits."""
        if not limits.max_daily_loss:
            return ValidationResult(is_valid=True)
        
        try:
            # This would need daily P&L tracking - simplified for MVP
            current_daily_loss = abs(account.unrealized_pl) if account.unrealized_pl < 0 else Decimal("0")
            
            if current_daily_loss >= limits.max_daily_loss:
                return ValidationResult(
                    is_valid=False,
                    error_code="DAILY_LOSS_LIMIT_EXCEEDED",
                    error_message=f"Daily loss limit of {limits.max_daily_loss} exceeded (current: {current_daily_loss})"
                )
            
            # Warning at 80% of limit
            if current_daily_loss >= limits.max_daily_loss * Decimal("0.8"):
                return ValidationResult(
                    is_valid=True,
                    warnings=[f"Daily loss warning: {current_daily_loss} (limit: {limits.max_daily_loss})"]
                )
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.error("Daily loss validation error", error=str(e))
            return ValidationResult(
                is_valid=True,
                warnings=["Could not validate daily loss limit due to error"]
            )
    
    async def _validate_instrument(self, order: Order) -> ValidationResult:
        """Validate instrument-specific rules."""
        # Basic instrument validation
        if not order.instrument or '_' not in order.instrument:
            return ValidationResult(
                is_valid=False,
                error_code="INVALID_INSTRUMENT",
                error_message=f"Invalid instrument format: {order.instrument}"
            )
        
        # Check if instrument is tradeable
        try:
            instrument_info = await self.oanda_client.get_instrument_info(order.instrument)
            if not instrument_info or not instrument_info.tradeable:
                return ValidationResult(
                    is_valid=False,
                    error_code="INSTRUMENT_NOT_TRADEABLE",
                    error_message=f"Instrument {order.instrument} is not tradeable"
                )
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.error("Instrument validation error", error=str(e))
            return ValidationResult(
                is_valid=True,
                warnings=["Could not validate instrument status due to error"]
            )
    
    def _calculate_risk_score(
        self,
        leverage: Decimal,
        margin_utilization: Decimal,
        position_count: int,
        daily_pl: Decimal,
        balance: Decimal
    ) -> float:
        """Calculate overall risk score (0-100, higher is more risky)."""
        score = 0.0
        
        # Leverage component (0-40 points)
        leverage_score = min(float(leverage) * 2, 40)
        
        # Margin utilization component (0-30 points)
        margin_score = min(float(margin_utilization) * 0.3, 30)
        
        # Position count component (0-15 points)
        position_score = min(position_count * 2, 15)
        
        # Daily P&L component (0-15 points)
        if balance > 0:
            pl_ratio = abs(float(daily_pl)) / float(balance)
            pl_score = min(pl_ratio * 100, 15)
        else:
            pl_score = 15
        
        score = leverage_score + margin_score + position_score + pl_score
        
        return min(score, 100.0)