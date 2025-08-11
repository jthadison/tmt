"""
Position Size Validators
========================

This module contains validation logic for position sizes including minimum
trade sizes, maximum position limits, and prop firm compliance validation.
"""

import logging
from decimal import Decimal
from typing import List, Dict

from .models import (
    PositionSize, PositionSizeRequest, PropFirm, PropFirmLimits
)

logger = logging.getLogger(__name__)


class PositionSizeValidator:
    """Validates position sizes against various constraints and requirements."""
    
    def __init__(self):
        # Standard minimum trade sizes by instrument type
        self.minimum_trade_sizes = {
            "forex": Decimal("0.01"),  # 0.01 lots (1,000 units)
            "metals": Decimal("0.1"),   # 0.1 lots for gold/silver
            "indices": Decimal("0.1"),  # 0.1 lots for indices
            "commodities": Decimal("0.1")  # 0.1 lots for commodities
        }
        
        # Maximum position sizes per instrument (safety limits)
        self.maximum_trade_sizes = {
            "forex": Decimal("100.0"),     # 100 lots max
            "metals": Decimal("50.0"),     # 50 lots max
            "indices": Decimal("20.0"),    # 20 lots max  
            "commodities": Decimal("30.0")  # 30 lots max
        }
    
    async def validate_position_size(self, position_size: PositionSize, request: PositionSizeRequest) -> List[str]:
        """
        Validate a calculated position size against all constraints.
        
        Args:
            position_size: The calculated position size
            request: Original position size request
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Basic size validation
        errors.extend(await self._validate_basic_constraints(position_size))
        
        # Minimum trade size validation
        errors.extend(await self._validate_minimum_trade_size(position_size))
        
        # Maximum position size validation
        errors.extend(await self._validate_maximum_position_size(position_size))
        
        # Fractional lot validation
        errors.extend(await self._validate_fractional_lots(position_size))
        
        # Risk amount validation
        errors.extend(await self._validate_risk_amount(position_size, request))
        
        if errors:
            logger.warning(f"Position size validation failed for {position_size.signal_id}: {errors}")
        else:
            logger.debug(f"Position size validation passed for {position_size.signal_id}")
        
        return errors
    
    async def _validate_basic_constraints(self, position_size: PositionSize) -> List[str]:
        """Validate basic position size constraints."""
        errors = []
        
        if position_size.adjusted_size <= 0:
            errors.append("Position size must be greater than zero")
        
        if position_size.base_size <= 0:
            errors.append("Base position size must be greater than zero")
        
        if position_size.adjusted_size > position_size.base_size * Decimal("10"):
            errors.append("Adjusted position size cannot be more than 10x base size")
        
        return errors
    
    async def _validate_minimum_trade_size(self, position_size: PositionSize) -> List[str]:
        """Validate position size meets minimum trade size requirements."""
        errors = []
        
        instrument_type = await self._get_instrument_type(position_size.symbol)
        min_size = self.minimum_trade_sizes.get(instrument_type, Decimal("0.01"))
        
        if position_size.adjusted_size < min_size:
            errors.append(f"Position size {position_size.adjusted_size} below minimum {min_size} for {instrument_type}")
        
        return errors
    
    async def _validate_maximum_position_size(self, position_size: PositionSize) -> List[str]:
        """Validate position size doesn't exceed maximum limits."""
        errors = []
        
        instrument_type = await self._get_instrument_type(position_size.symbol)
        max_size = self.maximum_trade_sizes.get(instrument_type, Decimal("100.0"))
        
        if position_size.adjusted_size > max_size:
            errors.append(f"Position size {position_size.adjusted_size} exceeds maximum {max_size} for {instrument_type}")
        
        return errors
    
    async def _validate_fractional_lots(self, position_size: PositionSize) -> List[str]:
        """Validate fractional lot size handling and rounding."""
        errors = []
        
        # Check if the position size has appropriate precision
        # Most brokers support 0.01 lot precision
        precision = Decimal("0.01")
        
        # Round to nearest 0.01 and check if significantly different
        rounded_size = (position_size.adjusted_size / precision).quantize(Decimal("1")) * precision
        difference = abs(position_size.adjusted_size - rounded_size)
        
        if difference > precision / 2:
            logger.warning(f"Position size {position_size.adjusted_size} rounded to {rounded_size}")
            # This is not necessarily an error, just a warning
        
        return errors
    
    async def _validate_risk_amount(self, position_size: PositionSize, request: PositionSizeRequest) -> List[str]:
        """Validate risk amount is reasonable."""
        errors = []
        
        # Risk amount should not exceed a reasonable percentage of account
        max_risk_pct = Decimal("10.0")  # 10% max risk per trade
        max_risk_amount = request.account_balance * (max_risk_pct / Decimal("100"))
        
        if position_size.risk_amount > max_risk_amount:
            errors.append(f"Risk amount {position_size.risk_amount} exceeds {max_risk_pct}% of account balance")
        
        # Risk amount should be positive
        if position_size.risk_amount <= 0:
            errors.append("Risk amount must be positive")
        
        return errors
    
    async def _get_instrument_type(self, symbol: str) -> str:
        """Determine instrument type from symbol."""
        # Simplified instrument type detection
        # In production, this would use a proper instrument database
        
        if len(symbol) == 6 and symbol[:3] != symbol[3:]:
            return "forex"
        elif symbol.upper() in ["XAUUSD", "XAGUSD", "GOLD", "SILVER"]:
            return "metals"
        elif symbol.upper() in ["US30", "US500", "NAS100", "GER30", "UK100"]:
            return "indices"
        elif symbol.upper() in ["OIL", "USOIL", "UKOIL", "NATGAS"]:
            return "commodities"
        else:
            return "forex"  # Default to forex
    
    def round_to_valid_lot_size(self, size: Decimal, symbol: str) -> Decimal:
        """
        Round position size to valid lot size for the given symbol.
        
        Args:
            size: Position size to round
            symbol: Trading symbol
            
        Returns:
            Rounded position size
        """
        # Standard lot size precision is 0.01 for most instruments
        precision = Decimal("0.01")
        
        # Some instruments may have different precision requirements
        if symbol.upper() in ["XAUUSD", "XAGUSD"]:
            precision = Decimal("0.1")  # Gold/Silver often use 0.1 precision
        
        # Round to nearest valid increment
        rounded = (size / precision).quantize(Decimal("1")) * precision
        
        # Ensure minimum size
        min_size = self.minimum_trade_sizes.get("forex", Decimal("0.01"))
        return max(rounded, min_size)


class PropFirmValidator:
    """Validates position sizes against prop firm specific requirements."""
    
    def __init__(self, firm_limits: Dict[PropFirm, PropFirmLimits]):
        self.firm_limits = firm_limits
    
    async def validate_prop_firm_compliance(self, 
                                          position_size: PositionSize, 
                                          request: PositionSizeRequest,
                                          prop_firm: PropFirm) -> List[str]:
        """
        Validate position size against prop firm specific limits.
        
        Args:
            position_size: Calculated position size
            request: Original request
            prop_firm: Prop firm to validate against
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if prop_firm not in self.firm_limits:
            errors.append(f"Unknown prop firm: {prop_firm}")
            return errors
        
        limits = self.firm_limits[prop_firm]
        
        # Validate maximum lot size
        if position_size.adjusted_size > limits.max_lot_size:
            errors.append(f"Position size {position_size.adjusted_size} exceeds {prop_firm} "
                         f"maximum lot size {limits.max_lot_size}")
        
        # Validate minimum trade size
        if position_size.adjusted_size < limits.minimum_trade_size:
            errors.append(f"Position size {position_size.adjusted_size} below {prop_firm} "
                         f"minimum trade size {limits.minimum_trade_size}")
        
        # Additional prop firm specific validations would go here
        # For example: daily loss limits, total exposure limits, etc.
        
        return errors