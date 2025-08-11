"""
Correlation-Based Position Size Adjuster
========================================

This module implements correlation-based position size adjustments that
reduce position sizes when portfolio correlation exceeds safe thresholds,
helping to manage portfolio heat and reduce concentration risk.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import datetime
import statistics

from ..models import PositionSizeRequest, PositionCorrelation

logger = logging.getLogger(__name__)


class Position:
    """Represents an open trading position."""
    
    def __init__(self, symbol: str, size: Decimal, entry_price: Decimal, 
                 direction: str, risk_amount: Decimal, opened_at: datetime.datetime):
        self.symbol = symbol
        self.size = size
        self.entry_price = entry_price
        self.direction = direction  # "long" or "short"
        self.risk_amount = risk_amount
        self.opened_at = opened_at


class PositionTracker:
    """Tracks open positions for correlation analysis."""
    
    def __init__(self):
        # In-memory storage for demo - production would use database
        self._positions: Dict[UUID, List[Position]] = {}
    
    async def get_open_positions(self, account_id: UUID) -> List[Position]:
        """Get all open positions for an account."""
        return self._positions.get(account_id, [])
    
    async def add_position(self, account_id: UUID, position: Position):
        """Add a new position to tracking."""
        if account_id not in self._positions:
            self._positions[account_id] = []
        self._positions[account_id].append(position)
    
    async def remove_position(self, account_id: UUID, symbol: str):
        """Remove a position when closed."""
        if account_id in self._positions:
            self._positions[account_id] = [
                pos for pos in self._positions[account_id] 
                if pos.symbol != symbol
            ]


class CorrelationCalculator:
    """Calculates correlations between currency pairs and instruments."""
    
    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
        
        # Pre-calculated correlation matrix for major currency pairs
        # In production, this would be calculated from real market data
        self._correlation_matrix = {
            ("EURUSD", "GBPUSD"): Decimal("0.75"),
            ("EURUSD", "USDCHF"): Decimal("-0.85"),
            ("EURUSD", "USDJPY"): Decimal("-0.15"),
            ("EURUSD", "AUDUSD"): Decimal("0.65"),
            ("EURUSD", "NZDUSD"): Decimal("0.60"),
            ("EURUSD", "USDCAD"): Decimal("-0.45"),
            
            ("GBPUSD", "USDCHF"): Decimal("-0.70"),
            ("GBPUSD", "USDJPY"): Decimal("-0.10"),
            ("GBPUSD", "AUDUSD"): Decimal("0.70"),
            ("GBPUSD", "NZDUSD"): Decimal("0.65"),
            ("GBPUSD", "USDCAD"): Decimal("-0.35"),
            
            ("USDCHF", "USDJPY"): Decimal("0.25"),
            ("USDCHF", "AUDUSD"): Decimal("-0.80"),
            ("USDCHF", "NZDUSD"): Decimal("-0.75"),
            ("USDCHF", "USDCAD"): Decimal("0.40"),
            
            ("USDJPY", "AUDUSD"): Decimal("-0.05"),
            ("USDJPY", "NZDUSD"): Decimal("-0.05"),
            ("USDJPY", "USDCAD"): Decimal("0.15"),
            
            ("AUDUSD", "NZDUSD"): Decimal("0.85"),
            ("AUDUSD", "USDCAD"): Decimal("-0.30"),
            
            ("NZDUSD", "USDCAD"): Decimal("-0.25"),
        }
    
    async def calculate_correlation(self, symbol1: str, symbol2: str) -> PositionCorrelation:
        """Calculate correlation between two symbols."""
        # Normalize symbol order for lookup
        key1 = (symbol1, symbol2)
        key2 = (symbol2, symbol1)
        
        correlation_coeff = Decimal("0.0")
        
        if key1 in self._correlation_matrix:
            correlation_coeff = self._correlation_matrix[key1]
        elif key2 in self._correlation_matrix:
            correlation_coeff = self._correlation_matrix[key2]
        else:
            # For unknown pairs, calculate based on common currencies
            correlation_coeff = await self._estimate_correlation(symbol1, symbol2)
        
        return PositionCorrelation(
            symbol1=symbol1,
            symbol2=symbol2,
            correlation_coefficient=correlation_coeff,
            lookback_days=self.lookback_days,
            confidence_level=Decimal("0.95")  # 95% confidence
        )
    
    async def _estimate_correlation(self, symbol1: str, symbol2: str) -> Decimal:
        """Estimate correlation for unknown pairs based on common currencies."""
        # Simple heuristic: if pairs share a currency, they have some correlation
        if len(symbol1) >= 6 and len(symbol2) >= 6:
            currency1_base = symbol1[:3]
            currency1_quote = symbol1[3:6]
            currency2_base = symbol2[:3]
            currency2_quote = symbol2[3:6]
            
            # Same pair
            if symbol1 == symbol2:
                return Decimal("1.0")
            
            # Inverse pairs (e.g., EURUSD vs USDEUR)
            if currency1_base == currency2_quote and currency1_quote == currency2_base:
                return Decimal("-1.0")
            
            # Share base currency
            if currency1_base == currency2_base:
                return Decimal("0.6")
            
            # Share quote currency  
            if currency1_quote == currency2_quote:
                return Decimal("0.4")
            
            # One currency appears in both pairs
            common_currencies = set([currency1_base, currency1_quote]) & set([currency2_base, currency2_quote])
            if common_currencies:
                return Decimal("0.3")
        
        # Default low correlation for unrelated instruments
        return Decimal("0.1")


class CorrelationAdjuster:
    """
    Adjusts position sizes based on portfolio correlation to manage concentration risk
    and portfolio heat across multiple positions.
    """
    
    def __init__(self, position_tracker: PositionTracker, correlation_calculator: CorrelationCalculator):
        self.position_tracker = position_tracker
        self.correlation_calculator = correlation_calculator
        self.max_correlation_threshold = Decimal("0.7")  # As per acceptance criteria
        self.max_portfolio_heat = Decimal("0.10")  # 10% maximum portfolio heat
        
        # Correlation-based adjustment factors
        self.correlation_adjustments = {
            Decimal("0.3"): Decimal("1.0"),   # No adjustment for low correlation
            Decimal("0.5"): Decimal("0.9"),   # 10% reduction for moderate correlation
            Decimal("0.7"): Decimal("0.7"),   # 30% reduction for high correlation  
            Decimal("0.9"): Decimal("0.5")    # 50% reduction for very high correlation
        }
    
    async def adjust_size(self, base_size: Decimal, request: PositionSizeRequest) -> Decimal:
        """
        Apply correlation-based size adjustment.
        
        Args:
            base_size: Base position size to adjust
            request: Position size request containing account and symbol info
            
        Returns:
            Correlation-adjusted position size
        """
        try:
            # Get current open positions for the account
            open_positions = await self.position_tracker.get_open_positions(request.account_id)
            
            if not open_positions:
                logger.debug(f"No open positions for account {request.account_id}, no correlation adjustment needed")
                return base_size
            
            # Calculate correlations with existing positions
            correlations = await self._calculate_position_correlations(request.symbol, open_positions)
            
            # Find maximum correlation
            max_correlation = await self._get_maximum_correlation(correlations)
            
            # Apply correlation-based reduction
            correlation_adjustment = await self._calculate_correlation_adjustment(max_correlation)
            correlation_adjusted = base_size * correlation_adjustment
            
            # Check portfolio heat with new position
            portfolio_heat = await self._calculate_portfolio_heat(
                request.account_id, request.symbol, correlation_adjusted, request.account_balance
            )
            
            # Apply portfolio heat reduction if needed
            final_size = correlation_adjusted
            if portfolio_heat > self.max_portfolio_heat:
                heat_adjustment = self.max_portfolio_heat / portfolio_heat
                final_size = correlation_adjusted * heat_adjustment
                logger.warning(f"Portfolio heat {portfolio_heat:.3f} exceeds limit {self.max_portfolio_heat}, "
                              f"reducing size by factor {heat_adjustment:.3f}")
            
            logger.info(f"Correlation adjustment for {request.symbol}: max_corr={max_correlation:.3f}, "
                       f"portfolio_heat={portfolio_heat:.3f}, size: {base_size} -> {final_size}")
            
            return final_size
            
        except Exception as e:
            logger.error(f"Correlation adjustment failed for {request.symbol}: {str(e)}")
            # Conservative approach: apply modest reduction if adjustment fails
            return base_size * Decimal("0.8")
    
    async def _calculate_position_correlations(self, new_symbol: str, 
                                             open_positions: List[Position]) -> List[PositionCorrelation]:
        """Calculate correlations between new symbol and existing positions."""
        correlations = []
        
        for position in open_positions:
            correlation = await self.correlation_calculator.calculate_correlation(
                new_symbol, position.symbol
            )
            correlations.append(correlation)
        
        return correlations
    
    async def _get_maximum_correlation(self, correlations: List[PositionCorrelation]) -> Decimal:
        """Find the maximum absolute correlation from the list."""
        if not correlations:
            return Decimal("0.0")
        
        max_corr = max(abs(corr.correlation_coefficient) for corr in correlations)
        return max_corr
    
    async def _calculate_correlation_adjustment(self, max_correlation: Decimal) -> Decimal:
        """Calculate position size adjustment based on maximum correlation."""
        # Find the appropriate adjustment factor
        for threshold in sorted(self.correlation_adjustments.keys(), reverse=True):
            if max_correlation >= threshold:
                adjustment = self.correlation_adjustments[threshold]
                logger.debug(f"Correlation {max_correlation:.3f} >= {threshold:.3f}, applying factor {adjustment}")
                return adjustment
        
        # No adjustment needed for low correlation
        return Decimal("1.0")
    
    async def _calculate_portfolio_heat(self, account_id: UUID, new_symbol: str, 
                                      new_size: Decimal, account_balance: Decimal) -> Decimal:
        """
        Calculate total portfolio heat including the new position.
        
        Portfolio heat = Total risk amount / Account balance
        """
        # Get existing positions
        open_positions = await self.position_tracker.get_open_positions(account_id)
        
        # Calculate total risk from existing positions
        existing_risk = sum(pos.risk_amount for pos in open_positions)
        
        # Calculate risk for new position (simplified)
        # In production, this would use proper pip value and stop loss calculations
        new_position_risk = new_size * Decimal("100")  # Simplified risk calculation
        
        # Total portfolio risk
        total_risk = existing_risk + new_position_risk
        
        # Portfolio heat percentage
        portfolio_heat = total_risk / account_balance if account_balance > 0 else Decimal("0")
        
        return portfolio_heat
    
    async def get_correlation_matrix(self, symbols: List[str]) -> Dict[Tuple[str, str], Decimal]:
        """Get correlation matrix for a list of symbols."""
        correlation_matrix = {}
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i <= j:  # Avoid duplicate calculations
                    if symbol1 == symbol2:
                        correlation_matrix[(symbol1, symbol2)] = Decimal("1.0")
                    else:
                        corr = await self.correlation_calculator.calculate_correlation(symbol1, symbol2)
                        correlation_matrix[(symbol1, symbol2)] = corr.correlation_coefficient
                        correlation_matrix[(symbol2, symbol1)] = corr.correlation_coefficient
        
        return correlation_matrix
    
    async def analyze_portfolio_risk(self, account_id: UUID) -> Dict[str, any]:
        """
        Analyze current portfolio risk including correlations and heat.
        
        Returns:
            Dictionary with portfolio risk analysis
        """
        open_positions = await self.position_tracker.get_open_positions(account_id)
        
        if not open_positions:
            return {
                'account_id': str(account_id),
                'position_count': 0,
                'portfolio_heat': 0.0,
                'max_correlation': 0.0,
                'risk_analysis': 'No open positions'
            }
        
        # Get symbols
        symbols = [pos.symbol for pos in open_positions]
        
        # Calculate correlation matrix
        correlations = []
        for i, pos1 in enumerate(open_positions):
            for j, pos2 in enumerate(open_positions):
                if i < j:  # Avoid duplicates
                    corr = await self.correlation_calculator.calculate_correlation(pos1.symbol, pos2.symbol)
                    correlations.append(abs(corr.correlation_coefficient))
        
        max_correlation = max(correlations) if correlations else Decimal("0.0")
        
        # Calculate total risk
        total_risk = sum(pos.risk_amount for pos in open_positions)
        
        # Risk analysis
        risk_level = "Low"
        if max_correlation > Decimal("0.7"):
            risk_level = "High - Excessive correlation"
        elif max_correlation > Decimal("0.5"):
            risk_level = "Moderate - Watch correlations"
        elif len(open_positions) > 5:
            risk_level = "Moderate - Many positions"
        
        return {
            'account_id': str(account_id),
            'position_count': len(open_positions),
            'symbols': symbols,
            'total_risk_amount': float(total_risk),
            'max_correlation': float(max_correlation),
            'risk_level': risk_level,
            'correlations': [float(c) for c in correlations]
        }