"""
Advanced Position Sizing Engine with Dynamic Risk Adjustment

Implements intelligent position sizing that considers:
- Current portfolio concentration 
- Account balance and available margin
- Risk per trade based on existing exposure
- Maximum position limits and concentration thresholds
"""

import asyncio
import logging
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass

from .config import get_settings
from .models import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class PositionSizingResult:
    """Result of position sizing calculation"""
    recommended_units: int
    effective_risk_percent: float
    concentration_after_trade: float
    risk_adjustment_factor: float
    warning_messages: List[str]
    is_safe_to_trade: bool
    max_safe_units: int


@dataclass  
class PortfolioAnalysis:
    """Current portfolio analysis"""
    total_exposure: float
    largest_position_percent: float
    total_margin_used: float
    available_margin: float
    position_count: int
    instruments_held: List[str]
    concentration_risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"


class AdvancedPositionSizing:
    """Intelligent position sizing with dynamic risk adjustment"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Position sizing configuration
        self.base_risk_per_trade = self.settings.risk_per_trade  # 2% default
        self.max_position_concentration = 0.30  # 30% max single position
        self.emergency_concentration_threshold = 0.50  # 50% triggers emergency
        self.portfolio_heat_threshold = 0.15  # 15% total portfolio risk
        
        # Dynamic risk adjustment factors
        self.concentration_adjustment = {
            "LOW": 1.0,      # 0-20% largest position: full risk
            "MEDIUM": 0.75,  # 20-30% largest position: reduce risk 25%
            "HIGH": 0.50,    # 30-40% largest position: reduce risk 50% 
            "CRITICAL": 0.25 # 40%+ largest position: reduce risk 75%
        }
        
        logger.info("Advanced Position Sizing Engine initialized")
    
    async def calculate_position_size(
        self, 
        signal: TradeSignal, 
        account_id: str,
        oanda_client,
        current_positions: Optional[List] = None
    ) -> PositionSizingResult:
        """
        Calculate optimal position size with dynamic risk adjustment
        
        Args:
            signal: Trading signal to size
            account_id: OANDA account ID
            oanda_client: OANDA client for account data
            current_positions: Optional current positions (for testing)
            
        Returns:
            PositionSizingResult with recommended size and risk analysis
        """
        try:
            # Get current portfolio analysis
            portfolio = await self._analyze_portfolio(account_id, oanda_client, current_positions)
            
            # Get account information
            account_info = await oanda_client.get_account_info(account_id)
            balance = float(account_info.balance)
            
            # Calculate dynamic risk adjustment
            risk_adjustment = self._calculate_risk_adjustment(portfolio, signal.instrument)
            adjusted_risk_percent = self.base_risk_per_trade * risk_adjustment
            
            # Calculate base position size using risk-based approach
            base_units = await self._calculate_base_position_size(
                signal, balance, adjusted_risk_percent
            )
            
            # Apply concentration limits
            max_safe_units = await self._calculate_max_safe_units(
                signal, account_id, oanda_client, balance, portfolio
            )
            
            # Take the smaller of base calculation and concentration limit
            recommended_units = min(abs(base_units), max_safe_units)
            
            # Apply direction
            if signal.direction in ["SELL", "short", "sell"]:
                recommended_units = -recommended_units
            
            # Calculate concentration after this trade
            position_value = abs(recommended_units * signal.entry_price) if signal.entry_price else 0
            concentration_after = (position_value / balance) * 100
            
            # Generate warnings
            warnings = self._generate_warnings(portfolio, concentration_after, adjusted_risk_percent)
            
            # Determine if trade is safe
            is_safe = (
                recommended_units > 0 and
                concentration_after <= self.max_position_concentration * 100 and
                portfolio.concentration_risk_level != "CRITICAL"
            )
            
            result = PositionSizingResult(
                recommended_units=int(recommended_units),
                effective_risk_percent=adjusted_risk_percent * 100,
                concentration_after_trade=concentration_after,
                risk_adjustment_factor=risk_adjustment,
                warning_messages=warnings,
                is_safe_to_trade=is_safe,
                max_safe_units=max_safe_units
            )
            
            logger.info(f"Position sizing for {signal.instrument}: {result.recommended_units} units "
                       f"({result.effective_risk_percent:.1f}% risk, {result.concentration_after_trade:.1f}% concentration)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return PositionSizingResult(
                recommended_units=0,
                effective_risk_percent=0.0,
                concentration_after_trade=0.0,
                risk_adjustment_factor=0.0,
                warning_messages=[f"Sizing calculation error: {e}"],
                is_safe_to_trade=False,
                max_safe_units=0
            )
    
    async def _analyze_portfolio(
        self, 
        account_id: str, 
        oanda_client,
        current_positions: Optional[List] = None
    ) -> PortfolioAnalysis:
        """Analyze current portfolio for risk assessment"""
        try:
            if current_positions is None:
                current_positions = await oanda_client.get_positions(account_id)
                
            account_info = await oanda_client.get_account_info(account_id)
            balance = float(account_info.balance)
            
            # Calculate portfolio metrics
            total_exposure = 0.0
            largest_position = 0.0
            instruments_held = []
            
            for position in current_positions:
                if abs(position.units) > 0:
                    position_value = abs(position.units * position.average_price)
                    total_exposure += position_value
                    largest_position = max(largest_position, position_value)
                    instruments_held.append(position.instrument)
            
            # Calculate percentages
            largest_position_percent = (largest_position / balance * 100) if balance > 0 else 0
            
            # Determine risk level
            if largest_position_percent < 20:
                risk_level = "LOW"
            elif largest_position_percent < 30:
                risk_level = "MEDIUM"
            elif largest_position_percent < 40:
                risk_level = "HIGH"
            else:
                risk_level = "CRITICAL"
            
            return PortfolioAnalysis(
                total_exposure=total_exposure,
                largest_position_percent=largest_position_percent,
                total_margin_used=account_info.margin_used,
                available_margin=account_info.margin_available,
                position_count=len([p for p in current_positions if abs(p.units) > 0]),
                instruments_held=instruments_held,
                concentration_risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return PortfolioAnalysis(
                total_exposure=0.0,
                largest_position_percent=0.0,
                total_margin_used=0.0,
                available_margin=0.0,
                position_count=0,
                instruments_held=[],
                concentration_risk_level="UNKNOWN"
            )
    
    def _calculate_risk_adjustment(self, portfolio: PortfolioAnalysis, instrument: str) -> float:
        """Calculate risk adjustment factor based on current portfolio"""
        base_adjustment = self.concentration_adjustment.get(
            portfolio.concentration_risk_level, 0.25
        )
        
        # Additional adjustment if adding to existing position
        if instrument in portfolio.instruments_held:
            base_adjustment *= 0.5  # Reduce by 50% for position building
        
        # Adjust for total portfolio positions
        if portfolio.position_count >= 5:
            base_adjustment *= 0.8  # Reduce for over-diversification
        elif portfolio.position_count >= 8:
            base_adjustment *= 0.6  # Further reduction for too many positions
        
        return max(base_adjustment, 0.1)  # Minimum 10% of base risk
    
    async def _calculate_base_position_size(
        self, 
        signal: TradeSignal, 
        balance: float, 
        risk_percent: float
    ) -> int:
        """Calculate base position size using improved risk calculation"""
        try:
            # Risk amount in account currency
            risk_amount = balance * risk_percent
            
            # Calculate stop loss distance
            if signal.stop_loss and signal.entry_price:
                stop_distance = abs(signal.entry_price - signal.stop_loss)
            else:
                # Default to 1% price movement if no stop loss
                stop_distance = signal.entry_price * 0.01 if signal.entry_price else 0
            
            if stop_distance <= 0:
                logger.warning("Invalid stop loss distance, using default position size")
                return int(risk_amount / (signal.entry_price or 1.0))
            
            # Calculate position size: Risk Amount / Stop Distance = Position Size
            position_size = risk_amount / stop_distance
            
            # Ensure reasonable minimums and maximums
            min_units = 100  # Minimum trade size
            max_units = int(balance * 0.1)  # Never risk more than 10% of balance on position size
            
            return max(min_units, min(int(position_size), max_units))
            
        except Exception as e:
            logger.error(f"Error calculating base position size: {e}")
            return 0
    
    async def _calculate_max_safe_units(
        self, 
        signal: TradeSignal, 
        account_id: str, 
        oanda_client, 
        balance: float,
        portfolio: PortfolioAnalysis
    ) -> int:
        """Calculate maximum safe position units based on concentration limits"""
        try:
            # Maximum position value allowed
            max_position_value = balance * self.max_position_concentration
            
            # Current largest position value
            current_largest = balance * (portfolio.largest_position_percent / 100)
            
            # Available concentration space
            available_concentration = max_position_value - current_largest
            
            # If no space available, limit to very small position
            if available_concentration <= 0:
                logger.warning("No concentration space available, limiting position size")
                return min(1000, int(balance * 0.001))  # 0.1% of balance max
            
            # Calculate max units based on available concentration
            if signal.entry_price and signal.entry_price > 0:
                max_units = int(available_concentration / signal.entry_price)
            else:
                max_units = 1000  # Default small size
            
            # Apply margin constraints
            available_margin = portfolio.available_margin
            estimated_margin_per_unit = signal.entry_price * 0.03 if signal.entry_price else 1.0
            margin_limited_units = int(available_margin / estimated_margin_per_unit) if estimated_margin_per_unit > 0 else 0
            
            # Take the more restrictive limit
            final_max_units = min(max_units, margin_limited_units)
            
            # Ensure minimum viable trade size or zero
            return max(0, final_max_units) if final_max_units >= 100 else 0
            
        except Exception as e:
            logger.error(f"Error calculating max safe units: {e}")
            return 0
    
    def _generate_warnings(
        self, 
        portfolio: PortfolioAnalysis, 
        concentration_after: float, 
        adjusted_risk: float
    ) -> List[str]:
        """Generate position sizing warnings"""
        warnings = []
        
        if portfolio.concentration_risk_level == "HIGH":
            warnings.append("Portfolio concentration is HIGH - position size reduced")
        elif portfolio.concentration_risk_level == "CRITICAL":
            warnings.append("Portfolio concentration is CRITICAL - emergency risk reduction applied")
        
        if concentration_after > self.max_position_concentration * 100:
            warnings.append(f"Trade would exceed maximum concentration limit ({self.max_position_concentration*100}%)")
        
        if adjusted_risk < self.base_risk_per_trade * 0.5:
            warnings.append("Risk significantly reduced due to portfolio concentration")
        
        if portfolio.position_count >= 8:
            warnings.append("High number of positions may impact risk management")
        
        if portfolio.available_margin < 1000:
            warnings.append("Low available margin - position size constrained")
        
        return warnings
    
    async def check_pre_trade_concentration(
        self, 
        signal: TradeSignal, 
        account_id: str, 
        oanda_client
    ) -> Tuple[bool, List[str]]:
        """
        Pre-trade check to prevent dangerous concentration levels
        
        Returns:
            Tuple of (is_safe_to_trade, warning_messages)
        """
        try:
            portfolio = await self._analyze_portfolio(account_id, oanda_client)
            
            # Critical concentration check
            if portfolio.largest_position_percent >= self.emergency_concentration_threshold * 100:
                return False, ["BLOCKED: Portfolio concentration exceeds emergency threshold"]
            
            # Check if adding to existing position would be dangerous
            if signal.instrument in portfolio.instruments_held:
                account_info = await oanda_client.get_account_info(account_id)
                balance = float(account_info.balance)
                
                # Find current position size for this instrument
                positions = await oanda_client.get_positions(account_id)
                current_position_value = 0
                for pos in positions:
                    if pos.instrument == signal.instrument:
                        current_position_value = abs(pos.units * pos.average_price)
                        break
                
                current_concentration = (current_position_value / balance) * 100
                if current_concentration >= self.max_position_concentration * 100:
                    return False, [f"BLOCKED: Existing {signal.instrument} position already at concentration limit"]
            
            # Check total portfolio heat
            if portfolio.position_count >= 10:
                return False, ["BLOCKED: Too many open positions for safe risk management"]
            
            # Check margin availability
            if portfolio.available_margin < 5000:  # $5000 minimum buffer
                return False, ["BLOCKED: Insufficient margin buffer for new positions"]
            
            return True, []
            
        except Exception as e:
            logger.error(f"Error in pre-trade concentration check: {e}")
            return False, [f"Pre-trade check error: {e}"]


# Global instance
_position_sizing_engine: Optional[AdvancedPositionSizing] = None


def get_position_sizing_engine() -> AdvancedPositionSizing:
    """Get global position sizing engine instance"""
    global _position_sizing_engine
    if _position_sizing_engine is None:
        _position_sizing_engine = AdvancedPositionSizing()
    return _position_sizing_engine