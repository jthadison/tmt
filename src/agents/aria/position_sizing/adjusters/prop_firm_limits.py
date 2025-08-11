"""
Prop Firm Limits Enforcement
============================

This module implements prop firm specific limit enforcement including
maximum lot sizes, position limits, exposure limits, and margin requirements
to ensure compliance with various prop firm rules and regulations.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

from ..models import PositionSizeRequest, PropFirm, PropFirmLimits

logger = logging.getLogger(__name__)


class AccountFirmMapping:
    """Maps trading accounts to their associated prop firms."""
    
    def __init__(self):
        # In-memory storage for demo - production would use database
        self._account_mappings: Dict[UUID, PropFirm] = {}
    
    async def get_firm_for_account(self, account_id: UUID) -> PropFirm:
        """Get the prop firm associated with an account."""
        firm = self._account_mappings.get(account_id)
        if firm is None:
            # Default to FTMO for demo purposes
            firm = PropFirm.FTMO
            logger.warning(f"No firm mapping found for account {account_id}, defaulting to {firm.value}")
        return firm
    
    async def set_account_firm(self, account_id: UUID, prop_firm: PropFirm):
        """Set the prop firm for an account."""
        self._account_mappings[account_id] = prop_firm
        logger.info(f"Account {account_id} mapped to {prop_firm.value}")


class PropFirmLimitChecker:
    """
    Enforces prop firm specific position limits and trading restrictions
    to ensure compliance with prop firm rules.
    """
    
    def __init__(self, account_firm_mapping: AccountFirmMapping):
        self.account_firm_mapping = account_firm_mapping
        
        # Define limits for each prop firm
        self.firm_limits = {
            PropFirm.FTMO: PropFirmLimits(
                max_lot_size=Decimal("20.0"),           # 20 lots max per trade
                max_positions_per_symbol=3,              # 3 positions per symbol
                max_total_exposure=Decimal("2000000"),   # $2M total exposure
                max_daily_loss=Decimal("5000"),          # $5K daily loss limit
                max_total_drawdown=Decimal("10000"),     # $10K total drawdown
                margin_requirement=Decimal("0.01"),      # 1% margin requirement
                minimum_trade_size=Decimal("0.01")       # 0.01 lots minimum
            ),
            
            PropFirm.MY_FOREX_FUNDS: PropFirmLimits(
                max_lot_size=Decimal("15.0"),           # 15 lots max per trade
                max_positions_per_symbol=2,              # 2 positions per symbol
                max_total_exposure=Decimal("1500000"),   # $1.5M total exposure
                max_daily_loss=Decimal("3000"),          # $3K daily loss limit
                max_total_drawdown=Decimal("6000"),      # $6K total drawdown
                margin_requirement=Decimal("0.01"),      # 1% margin requirement
                minimum_trade_size=Decimal("0.01")       # 0.01 lots minimum
            ),
            
            PropFirm.THE5ERS: PropFirmLimits(
                max_lot_size=Decimal("10.0"),           # 10 lots max per trade
                max_positions_per_symbol=2,              # 2 positions per symbol
                max_total_exposure=Decimal("1000000"),   # $1M total exposure
                max_daily_loss=Decimal("2500"),          # $2.5K daily loss limit
                max_total_drawdown=Decimal("5000"),      # $5K total drawdown
                margin_requirement=Decimal("0.01"),      # 1% margin requirement
                minimum_trade_size=Decimal("0.01")       # 0.01 lots minimum
            ),
            
            PropFirm.FUNDED_NEXT: PropFirmLimits(
                max_lot_size=Decimal("25.0"),           # 25 lots max per trade
                max_positions_per_symbol=5,              # 5 positions per symbol
                max_total_exposure=Decimal("2500000"),   # $2.5M total exposure
                max_daily_loss=Decimal("7500"),          # $7.5K daily loss limit
                max_total_drawdown=Decimal("12000"),     # $12K total drawdown
                margin_requirement=Decimal("0.005"),     # 0.5% margin requirement
                minimum_trade_size=Decimal("0.01")       # 0.01 lots minimum
            ),
            
            PropFirm.TRUE_FOREX_FUNDS: PropFirmLimits(
                max_lot_size=Decimal("12.0"),           # 12 lots max per trade
                max_positions_per_symbol=3,              # 3 positions per symbol
                max_total_exposure=Decimal("1200000"),   # $1.2M total exposure
                max_daily_loss=Decimal("4000"),          # $4K daily loss limit
                max_total_drawdown=Decimal("8000"),      # $8K total drawdown
                margin_requirement=Decimal("0.01"),      # 1% margin requirement
                minimum_trade_size=Decimal("0.01")       # 0.01 lots minimum
            )
        }
    
    async def enforce_limits(self, calculated_size: Decimal, request: PositionSizeRequest) -> Decimal:
        """
        Enforce all prop firm limits and return compliant position size.
        
        Args:
            calculated_size: Position size before prop firm limit enforcement
            request: Original position size request
            
        Returns:
            Position size after prop firm limit enforcement
            
        Raises:
            ValueError: If position cannot be accommodated within limits
        """
        try:
            # Get prop firm for this account
            prop_firm = await self.account_firm_mapping.get_firm_for_account(request.account_id)
            
            # Get limits for this prop firm
            limits = self.firm_limits.get(prop_firm)
            if not limits:
                logger.error(f"No limits configured for prop firm: {prop_firm}")
                raise ValueError(f"Unknown prop firm: {prop_firm}")
            
            enforced_size = calculated_size
            
            # 1. Enforce maximum lot size per trade
            enforced_size = await self._enforce_max_lot_size(enforced_size, limits, prop_firm)
            
            # 2. Check maximum open positions per symbol
            await self._check_max_positions_per_symbol(request, limits, prop_firm)
            
            # 3. Check total exposure limits
            enforced_size = await self._enforce_total_exposure_limit(
                enforced_size, request, limits, prop_firm
            )
            
            # 4. Check margin requirements
            enforced_size = await self._enforce_margin_requirements(
                enforced_size, request, limits, prop_firm
            )
            
            # 5. Enforce minimum trade size
            enforced_size = await self._enforce_minimum_trade_size(enforced_size, limits, prop_firm)
            
            # 6. Additional prop firm specific rules
            enforced_size = await self._enforce_special_rules(enforced_size, request, prop_firm, limits)
            
            if enforced_size != calculated_size:
                reduction_pct = ((calculated_size - enforced_size) / calculated_size) * Decimal("100")
                logger.info(f"Prop firm limits applied for {prop_firm.value}: "
                           f"{calculated_size} -> {enforced_size} ({reduction_pct:.1f}% reduction)")
            
            return enforced_size
            
        except Exception as e:
            logger.error(f"Prop firm limit enforcement failed: {str(e)}")
            raise
    
    async def _enforce_max_lot_size(self, size: Decimal, limits: PropFirmLimits, firm: PropFirm) -> Decimal:
        """Enforce maximum lot size per trade."""
        if size > limits.max_lot_size:
            logger.warning(f"{firm.value} max lot size limit applied: {size} -> {limits.max_lot_size}")
            return limits.max_lot_size
        return size
    
    async def _check_max_positions_per_symbol(self, request: PositionSizeRequest, 
                                            limits: PropFirmLimits, firm: PropFirm):
        """Check if maximum positions per symbol would be exceeded."""
        # Get current open positions count for this symbol
        current_positions = await self._get_open_positions_count(request.account_id, request.symbol)
        
        if current_positions >= limits.max_positions_per_symbol:
            raise ValueError(f"{firm.value} maximum positions per symbol exceeded: "
                           f"{current_positions} >= {limits.max_positions_per_symbol} for {request.symbol}")
    
    async def _enforce_total_exposure_limit(self, size: Decimal, request: PositionSizeRequest,
                                          limits: PropFirmLimits, firm: PropFirm) -> Decimal:
        """Enforce total exposure limits."""
        # Calculate current total exposure
        current_exposure = await self._calculate_current_exposure(request.account_id)
        
        # Calculate new position exposure
        contract_value = await self._get_contract_value(request.symbol)
        new_exposure = size * contract_value
        
        # Check if total exposure would exceed limit
        total_exposure = current_exposure + new_exposure
        if total_exposure > limits.max_total_exposure:
            # Reduce size to fit within exposure limit
            available_exposure = limits.max_total_exposure - current_exposure
            if available_exposure <= 0:
                raise ValueError(f"{firm.value} total exposure limit exceeded, cannot open new position")
            
            max_allowed_size = available_exposure / contract_value
            adjusted_size = min(size, max_allowed_size)
            
            logger.warning(f"{firm.value} total exposure limit applied: "
                          f"size reduced from {size} to {adjusted_size}")
            return adjusted_size
        
        return size
    
    async def _enforce_margin_requirements(self, size: Decimal, request: PositionSizeRequest,
                                         limits: PropFirmLimits, firm: PropFirm) -> Decimal:
        """Enforce margin requirements."""
        # Calculate required margin for this position
        required_margin = await self._calculate_required_margin(request.symbol, size, limits)
        
        # Get available margin
        available_margin = await self._get_available_margin(request.account_id)
        
        if required_margin > available_margin:
            # Reduce size based on available margin with safety buffer
            safety_margin = available_margin * Decimal("0.8")  # 80% of available margin
            margin_per_lot = await self._get_margin_per_lot(request.symbol, limits)
            
            if margin_per_lot > 0:
                max_size_by_margin = safety_margin / margin_per_lot
                adjusted_size = min(size, max_size_by_margin)
                
                logger.warning(f"{firm.value} margin requirement applied: "
                              f"size reduced from {size} to {adjusted_size}")
                return adjusted_size
        
        return size
    
    async def _enforce_minimum_trade_size(self, size: Decimal, limits: PropFirmLimits, firm: PropFirm) -> Decimal:
        """Enforce minimum trade size."""
        if size < limits.minimum_trade_size:
            logger.warning(f"{firm.value} minimum trade size applied: {size} -> {limits.minimum_trade_size}")
            return limits.minimum_trade_size
        return size
    
    async def _enforce_special_rules(self, size: Decimal, request: PositionSizeRequest,
                                   firm: PropFirm, limits: PropFirmLimits) -> Decimal:
        """Enforce special prop firm specific rules."""
        # Each prop firm may have unique rules
        
        if firm == PropFirm.FTMO:
            # FTMO specific rules
            return await self._enforce_ftmo_rules(size, request, limits)
        
        elif firm == PropFirm.MY_FOREX_FUNDS:
            # MyForexFunds specific rules
            return await self._enforce_mff_rules(size, request, limits)
        
        elif firm == PropFirm.THE5ERS:
            # The5ers specific rules
            return await self._enforce_the5ers_rules(size, request, limits)
        
        # Default: no special rules
        return size
    
    async def _enforce_ftmo_rules(self, size: Decimal, request: PositionSizeRequest, 
                                limits: PropFirmLimits) -> Decimal:
        """Enforce FTMO specific rules."""
        # FTMO rule: No trading during news events (simplified implementation)
        # In production, this would check against news calendar
        
        # FTMO rule: Maximum 5% risk per trade
        max_risk_pct = Decimal("5.0")
        risk_pct = (request.base_risk_percentage or Decimal("1.0"))
        
        if risk_pct > max_risk_pct:
            # Reduce size proportionally
            risk_adjustment = max_risk_pct / risk_pct
            adjusted_size = size * risk_adjustment
            logger.warning(f"FTMO risk limit applied: size reduced by factor {risk_adjustment}")
            return adjusted_size
        
        return size
    
    async def _enforce_mff_rules(self, size: Decimal, request: PositionSizeRequest,
                               limits: PropFirmLimits) -> Decimal:
        """Enforce MyForexFunds specific rules."""
        # MFF rule: Conservative position sizing during volatile periods
        # This is a placeholder - real implementation would check market volatility
        return size
    
    async def _enforce_the5ers_rules(self, size: Decimal, request: PositionSizeRequest,
                                   limits: PropFirmLimits) -> Decimal:
        """Enforce The5ers specific rules."""
        # The5ers rule: Maximum 2% risk per trade
        max_risk_pct = Decimal("2.0")
        risk_pct = (request.base_risk_percentage or Decimal("1.0"))
        
        if risk_pct > max_risk_pct:
            risk_adjustment = max_risk_pct / risk_pct
            adjusted_size = size * risk_adjustment
            logger.warning(f"The5ers risk limit applied: size reduced by factor {risk_adjustment}")
            return adjusted_size
        
        return size
    
    async def _get_open_positions_count(self, account_id: UUID, symbol: str) -> int:
        """Get count of open positions for a specific symbol."""
        # Placeholder implementation - would query position tracker in production
        return 0
    
    async def _calculate_current_exposure(self, account_id: UUID) -> Decimal:
        """Calculate current total exposure for the account."""
        # Placeholder implementation - would sum all open position exposures
        return Decimal("0")
    
    async def _get_contract_value(self, symbol: str) -> Decimal:
        """Get contract value for the symbol."""
        # Standard contract values (simplified)
        contract_values = {
            "EURUSD": Decimal("100000"),  # Standard lot
            "GBPUSD": Decimal("100000"),
            "USDJPY": Decimal("100000"),
            "AUDUSD": Decimal("100000"),
            "NZDUSD": Decimal("100000"),
            "USDCHF": Decimal("100000"),
            "USDCAD": Decimal("100000"),
            "XAUUSD": Decimal("100"),     # 100 oz for gold
            "XAGUSD": Decimal("5000")     # 5000 oz for silver
        }
        return contract_values.get(symbol, Decimal("100000"))
    
    async def _calculate_required_margin(self, symbol: str, size: Decimal, limits: PropFirmLimits) -> Decimal:
        """Calculate required margin for the position."""
        contract_value = await self._get_contract_value(symbol)
        return size * contract_value * limits.margin_requirement
    
    async def _get_available_margin(self, account_id: UUID) -> Decimal:
        """Get available margin for the account."""
        # Placeholder implementation - would query account margin in production
        return Decimal("50000")  # Assume $50K available margin
    
    async def _get_margin_per_lot(self, symbol: str, limits: PropFirmLimits) -> Decimal:
        """Get margin requirement per lot for the symbol."""
        contract_value = await self._get_contract_value(symbol)
        return contract_value * limits.margin_requirement
    
    async def get_account_limits_summary(self, account_id: UUID) -> Dict[str, any]:
        """Get comprehensive limits summary for an account."""
        prop_firm = await self.account_firm_mapping.get_firm_for_account(account_id)
        limits = self.firm_limits.get(prop_firm)
        
        if not limits:
            return {'error': f'No limits found for firm: {prop_firm}'}
        
        return {
            'account_id': str(account_id),
            'prop_firm': prop_firm.value,
            'limits': {
                'max_lot_size': float(limits.max_lot_size),
                'max_positions_per_symbol': limits.max_positions_per_symbol,
                'max_total_exposure': float(limits.max_total_exposure),
                'max_daily_loss': float(limits.max_daily_loss),
                'max_total_drawdown': float(limits.max_total_drawdown),
                'margin_requirement': float(limits.margin_requirement),
                'minimum_trade_size': float(limits.minimum_trade_size)
            }
        }