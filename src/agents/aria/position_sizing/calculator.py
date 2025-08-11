"""
Position Size Calculator
========================

Core position sizing engine that calculates optimal position sizes based on
account balance, risk percentage, stop distance, and multiple adjustment factors
including volatility, drawdown, correlation, prop firm limits, and anti-detection
variance.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional
import datetime

from .models import (
    PositionSizeRequest, PositionSize, SizeAdjustments, RiskModel,
    MarketContext, AccountContext, PropFirm
)
from .validators import PositionSizeValidator
from .adjusters import (
    VolatilityAdjuster, DrawdownAdjuster, CorrelationAdjuster,
    PropFirmLimitChecker, SizeVarianceEngine
)

logger = logging.getLogger(__name__)


class PositionSizeCalculator:
    """
    Main position sizing calculator that orchestrates all adjustment factors
    to produce optimal position sizes.
    """
    
    def __init__(self, 
                 volatility_adjuster: VolatilityAdjuster,
                 drawdown_adjuster: DrawdownAdjuster,
                 correlation_adjuster: CorrelationAdjuster,
                 prop_firm_checker: PropFirmLimitChecker,
                 variance_engine: SizeVarianceEngine,
                 validator: PositionSizeValidator):
        self.volatility_adjuster = volatility_adjuster
        self.drawdown_adjuster = drawdown_adjuster
        self.correlation_adjuster = correlation_adjuster
        self.prop_firm_checker = prop_firm_checker
        self.variance_engine = variance_engine
        self.validator = validator
        
        # Risk model configurations
        self.risk_models = {
            RiskModel.FIXED: self._fixed_risk_calculation,
            RiskModel.ADAPTIVE: self._adaptive_risk_calculation,
            RiskModel.KELLY_CRITERION: self._kelly_criterion_calculation
        }
    
    async def calculate_position_size(self, request: PositionSizeRequest) -> PositionSize:
        """
        Calculate optimal position size with all adjustment factors applied.
        
        Args:
            request: Position size calculation request
            
        Returns:
            PositionSize: Complete position sizing result
            
        Raises:
            ValueError: If request parameters are invalid
            RuntimeError: If calculation fails
        """
        try:
            logger.info(f"Calculating position size for signal {request.signal_id}")
            
            # Step 1: Calculate base position size
            base_size = await self._calculate_base_size(request)
            logger.debug(f"Base position size: {base_size}")
            
            # Step 2: Apply volatility adjustment
            volatility_adjusted = await self.volatility_adjuster.adjust_size(
                base_size, request.symbol
            )
            volatility_factor = volatility_adjusted / base_size if base_size > 0 else Decimal("1.0")
            logger.debug(f"Volatility adjusted size: {volatility_adjusted} (factor: {volatility_factor})")
            
            # Step 3: Apply drawdown reduction
            drawdown_adjusted = await self.drawdown_adjuster.adjust_size(
                volatility_adjusted, request.account_id
            )
            drawdown_factor = drawdown_adjusted / volatility_adjusted if volatility_adjusted > 0 else Decimal("1.0")
            logger.debug(f"Drawdown adjusted size: {drawdown_adjusted} (factor: {drawdown_factor})")
            
            # Step 4: Apply correlation reduction
            correlation_adjusted = await self.correlation_adjuster.adjust_size(
                drawdown_adjusted, request
            )
            correlation_factor = correlation_adjusted / drawdown_adjusted if drawdown_adjusted > 0 else Decimal("1.0")
            logger.debug(f"Correlation adjusted size: {correlation_adjusted} (factor: {correlation_factor})")
            
            # Step 5: Enforce prop firm limits
            limit_enforced = await self.prop_firm_checker.enforce_limits(
                correlation_adjusted, request
            )
            limit_factor = limit_enforced / correlation_adjusted if correlation_adjusted > 0 else Decimal("1.0")
            logger.debug(f"Limit enforced size: {limit_enforced} (factor: {limit_factor})")
            
            # Step 6: Apply anti-detection variance
            final_size = await self.variance_engine.apply_variance(
                limit_enforced, request.account_id
            )
            variance_factor = final_size / limit_enforced if limit_enforced > 0 else Decimal("1.0")
            logger.debug(f"Final size with variance: {final_size} (factor: {variance_factor})")
            
            # Create adjustment factors
            adjustments = SizeAdjustments(
                volatility_factor=volatility_factor,
                drawdown_factor=drawdown_factor,
                correlation_factor=correlation_factor,
                limit_factor=limit_factor,
                variance_factor=variance_factor
            )
            
            # Generate sizing reasoning
            reasoning = await self._generate_sizing_reasoning(request, base_size, final_size, adjustments)
            
            # Calculate risk amount and pip value
            risk_amount = request.account_balance * (request.base_risk_percentage / Decimal("100"))
            pip_value = await self._get_pip_value(request.symbol, request.account_balance)
            
            # Create position size result
            position_size = PositionSize(
                signal_id=request.signal_id,
                account_id=request.account_id,
                symbol=request.symbol,
                base_size=base_size,
                adjusted_size=final_size,
                adjustments=adjustments,
                risk_amount=risk_amount,
                pip_value=pip_value,
                reasoning=reasoning,
                calculated_at=datetime.datetime.utcnow()
            )
            
            # Validate final result
            await self.validator.validate_position_size(position_size, request)
            
            logger.info(f"Position size calculation complete: {final_size} lots (reduction: {position_size.size_reduction_pct}%)")
            return position_size
            
        except Exception as e:
            logger.error(f"Position size calculation failed for signal {request.signal_id}: {str(e)}")
            raise RuntimeError(f"Position size calculation failed: {str(e)}") from e
    
    async def _calculate_base_size(self, request: PositionSizeRequest) -> Decimal:
        """
        Calculate base position size using the selected risk model.
        
        Formula: (Account Balance * Risk %) / (Stop Distance * Pip Value)
        """
        risk_calculation_func = self.risk_models[request.risk_model]
        risk_percentage = await risk_calculation_func(request)
        
        risk_amount = request.account_balance * (risk_percentage / Decimal("100"))
        pip_value = await self._get_pip_value(request.symbol, request.account_balance)
        
        if pip_value <= 0:
            raise ValueError(f"Invalid pip value calculated for {request.symbol}: {pip_value}")
        
        stop_value = request.stop_distance_pips * pip_value
        if stop_value <= 0:
            raise ValueError(f"Invalid stop value calculated: {stop_value}")
        
        position_size = risk_amount / stop_value
        
        logger.debug(f"Base size calculation: risk_amount={risk_amount}, pip_value={pip_value}, "
                    f"stop_distance={request.stop_distance_pips}, position_size={position_size}")
        
        return max(position_size, Decimal("0.01"))  # Minimum position size
    
    async def _fixed_risk_calculation(self, request: PositionSizeRequest) -> Decimal:
        """Fixed risk percentage model."""
        return request.base_risk_percentage
    
    async def _adaptive_risk_calculation(self, request: PositionSizeRequest) -> Decimal:
        """Adaptive risk percentage based on recent performance."""
        # Placeholder for adaptive risk calculation
        # In a full implementation, this would analyze recent trade performance
        # and adjust risk percentage accordingly
        base_risk = request.base_risk_percentage
        
        # Simple adaptive logic: reduce risk if recent performance is poor
        # This would typically query recent trade results from database
        performance_multiplier = Decimal("1.0")  # Placeholder
        
        adaptive_risk = base_risk * performance_multiplier
        return max(adaptive_risk, Decimal("0.1"))  # Minimum 0.1%
    
    async def _kelly_criterion_calculation(self, request: PositionSizeRequest) -> Decimal:
        """Kelly criterion for optimal position sizing."""
        # Placeholder for Kelly criterion calculation
        # In a full implementation, this would calculate:
        # Kelly% = (bp - q) / b
        # where b = odds received, p = probability of winning, q = probability of losing
        
        # For now, return a conservative Kelly estimate
        return request.base_risk_percentage * Decimal("0.5")  # 50% of base risk
    
    async def _get_pip_value(self, symbol: str, account_balance: Decimal) -> Decimal:
        """
        Calculate pip value for the given symbol and account balance.
        
        This is a simplified implementation. In production, this would
        query real-time exchange rates and use proper pip value calculations.
        """
        # Standard pip values for major pairs (simplified)
        pip_values = {
            "EURUSD": Decimal("10.0"),
            "GBPUSD": Decimal("10.0"),
            "USDCHF": Decimal("10.0"),
            "USDJPY": Decimal("10.0"),
            "AUDUSD": Decimal("10.0"),
            "NZDUSD": Decimal("10.0"),
            "USDCAD": Decimal("10.0"),
        }
        
        base_pip_value = pip_values.get(symbol, Decimal("10.0"))
        
        # Adjust for account balance (standard lot is $100,000)
        # This is simplified - real implementation would use current exchange rates
        return base_pip_value
    
    async def _generate_sizing_reasoning(self, 
                                       request: PositionSizeRequest,
                                       base_size: Decimal,
                                       final_size: Decimal,
                                       adjustments: SizeAdjustments) -> str:
        """Generate human-readable reasoning for the position size calculation."""
        reasoning_parts = [
            f"Base calculation: {base_size} lots (Risk: {request.base_risk_percentage}%, "
            f"Stop: {request.stop_distance_pips} pips)"
        ]
        
        if adjustments.volatility_factor != Decimal("1.0"):
            direction = "increased" if adjustments.volatility_factor > 1 else "reduced"
            reasoning_parts.append(f"Volatility adjustment: {direction} by {abs(1 - float(adjustments.volatility_factor)) * 100:.1f}%")
        
        if adjustments.drawdown_factor != Decimal("1.0"):
            direction = "increased" if adjustments.drawdown_factor > 1 else "reduced"
            reasoning_parts.append(f"Drawdown adjustment: {direction} by {abs(1 - float(adjustments.drawdown_factor)) * 100:.1f}%")
        
        if adjustments.correlation_factor != Decimal("1.0"):
            direction = "increased" if adjustments.correlation_factor > 1 else "reduced"
            reasoning_parts.append(f"Correlation adjustment: {direction} by {abs(1 - float(adjustments.correlation_factor)) * 100:.1f}%")
        
        if adjustments.limit_factor != Decimal("1.0"):
            reasoning_parts.append(f"Prop firm limits applied")
        
        if adjustments.variance_factor != Decimal("1.0"):
            reasoning_parts.append(f"Anti-detection variance applied")
        
        total_reduction = (base_size - final_size) / base_size * Decimal("100") if base_size > 0 else Decimal("0")
        reasoning_parts.append(f"Final size: {final_size} lots (Total reduction: {total_reduction:.1f}%)")
        
        return "; ".join(reasoning_parts)