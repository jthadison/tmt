"""
Advanced Risk Management Calculator for real-time risk assessment.

Provides comprehensive risk scoring, limit monitoring, and automated
risk controls with sub-50ms calculation performance.
"""

import asyncio
import math
import time
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from scipy.stats import norm

from ..core.models import (
    RiskMetrics,
    RiskLimits,
    Position,
    RiskLevel,
    RiskAlert,
    AlertSeverity
)


class RiskCalculationEngine:
    """
    High-performance risk calculation engine with real-time monitoring
    and automated risk controls for trading portfolios.
    """
    
    def __init__(self, risk_limits: RiskLimits):
        self.risk_limits = risk_limits
        
        # Risk calculation caches
        self.position_correlations: Dict[Tuple[str, str], float] = {}
        self.volatility_cache: Dict[str, Tuple[datetime, float]] = {}
        self.var_cache: Dict[str, Tuple[datetime, Decimal]] = {}
        
        # Performance metrics
        self.calculation_times: List[float] = []
        self.last_calculation_time = 0.0
        
        # Risk state tracking
        self.previous_risk_scores: Dict[str, float] = {}
        self.risk_score_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Alert state
        self.active_alerts: Dict[str, Set[str]] = defaultdict(set)
        self.alert_cooldowns: Dict[str, datetime] = {}
        
    async def calculate_real_time_risk(
        self,
        account_id: str,
        positions: List[Position],
        account_balance: Decimal,
        margin_available: Decimal,
        current_prices: Dict[str, Decimal]
    ) -> RiskMetrics:
        """Calculate comprehensive real-time risk metrics."""
        
        start_time = time.perf_counter()
        
        try:
            # Core risk calculations
            position_risk = await self._calculate_position_risk(positions, current_prices)
            leverage_risk = self._calculate_leverage_risk(positions, account_balance)
            concentration_risk = self._calculate_concentration_risk(positions)
            correlation_risk = await self._calculate_correlation_risk(positions)
            liquidity_risk = self._calculate_liquidity_risk(positions)
            
            # P&L and drawdown analysis
            pl_metrics = self._calculate_pl_metrics(positions)
            var_95 = await self._calculate_portfolio_var(positions, current_prices)
            
            # Composite risk score (0-100)
            risk_score = self._calculate_composite_risk_score(
                position_risk,
                leverage_risk,
                concentration_risk,
                correlation_risk,
                liquidity_risk,
                pl_metrics['daily_pl_risk']
            )
            
            # Risk level determination
            risk_level = self._determine_risk_level(risk_score)
            
            # Identify risk limit breaches
            breaches = self._check_risk_limit_breaches(
                positions, account_balance, margin_available, risk_score, var_95
            )
            
            # Build risk metrics
            risk_metrics = RiskMetrics(
                account_id=account_id,
                timestamp=datetime.now(),
                risk_score=risk_score,
                total_exposure=sum(pos.notional_value for pos in positions),
                max_position_size=max((pos.notional_value for pos in positions), default=Decimal("0")),
                position_concentration=concentration_risk,
                current_leverage=leverage_risk['current_leverage'],
                max_leverage=self.risk_limits.max_leverage,
                margin_utilization=leverage_risk['margin_utilization'],
                margin_available=margin_available,
                unrealized_pl=sum(pos.unrealized_pl for pos in positions),
                daily_pl=sum(pos.daily_pl for pos in positions),
                max_drawdown=pl_metrics['max_drawdown'],
                var_95=var_95,
                correlation_risk=correlation_risk,
                instrument_count=len(set(pos.instrument for pos in positions)),
                sector_diversification=self._calculate_sector_diversification(positions),
                risk_limit_breaches=breaches,
                risk_level=risk_level
            )
            
            # Update performance tracking
            calculation_time = (time.perf_counter() - start_time) * 1000
            self.calculation_times.append(calculation_time)
            self.last_calculation_time = calculation_time
            
            # Keep only last 1000 measurements
            if len(self.calculation_times) > 1000:
                self.calculation_times = self.calculation_times[-1000:]
            
            # Update risk score history
            self._update_risk_score_history(account_id, risk_score)
            
            return risk_metrics
            
        except Exception as e:
            # Emergency fallback - return high risk score
            return RiskMetrics(
                account_id=account_id,
                timestamp=datetime.now(),
                risk_score=100.0,
                risk_level=RiskLevel.CRITICAL,
                risk_limit_breaches=[f"calculation_error: {str(e)}"]
            )
    
    async def _calculate_position_risk(
        self, 
        positions: List[Position], 
        current_prices: Dict[str, Decimal]
    ) -> float:
        """Calculate position-level risk score."""
        if not positions:
            return 0.0
        
        total_risk = 0.0
        total_weight = 0.0
        
        for position in positions:
            # Position size risk
            size_risk = min(
                float(position.notional_value) / float(self.risk_limits.max_position_size),
                1.0
            )
            
            # Price volatility risk
            volatility = await self._get_instrument_volatility(position.instrument)
            vol_risk = min(volatility / 0.5, 1.0)  # Normalize to 50% vol = max risk
            
            # Position age risk (newer positions are riskier)
            age_hours = (datetime.now() - position.opened_at).total_seconds() / 3600
            age_risk = max(0.0, 1.0 - age_hours / 168)  # Risk decreases over 1 week
            
            # Unrealized P&L risk
            if position.market_value != 0:
                pl_ratio = abs(float(position.unrealized_pl) / float(position.market_value))
                pl_risk = min(pl_ratio / 0.2, 1.0)  # 20% loss = max risk
            else:
                pl_risk = 0.0
            
            # Combine position risks
            position_risk = (size_risk * 0.4 + vol_risk * 0.3 + age_risk * 0.1 + pl_risk * 0.2)
            
            # Weight by position size
            weight = float(position.notional_value)
            total_risk += position_risk * weight
            total_weight += weight
        
        return (total_risk / total_weight) if total_weight > 0 else 0.0
    
    def _calculate_leverage_risk(self, positions: List[Position], account_balance: Decimal) -> Dict[str, float]:
        """Calculate leverage and margin risk."""
        total_exposure = sum(pos.notional_value for pos in positions)
        
        if account_balance <= 0:
            return {
                'current_leverage': float(self.risk_limits.max_leverage),
                'leverage_risk': 1.0,
                'margin_utilization': 1.0,
                'margin_risk': 1.0
            }
        
        current_leverage = total_exposure / account_balance
        leverage_risk = min(float(current_leverage) / float(self.risk_limits.max_leverage), 1.0)
        
        # Margin utilization (simplified calculation)
        required_margin = total_exposure * Decimal("0.02")  # 2% margin requirement
        margin_utilization = float(required_margin / account_balance)
        margin_risk = min(margin_utilization / self.risk_limits.max_margin_utilization, 1.0)
        
        return {
            'current_leverage': float(current_leverage),
            'leverage_risk': leverage_risk,
            'margin_utilization': margin_utilization,
            'margin_risk': margin_risk
        }
    
    def _calculate_concentration_risk(self, positions: List[Position]) -> float:
        """Calculate position concentration risk."""
        if not positions:
            return 0.0
        
        total_exposure = sum(pos.notional_value for pos in positions)
        
        if total_exposure == 0:
            return 0.0
        
        # Calculate position weights
        weights = [float(pos.notional_value / total_exposure) for pos in positions]
        
        # Concentration measures
        max_weight = max(weights)
        
        # Herfindahl-Hirschman Index for concentration
        hhi = sum(w**2 for w in weights)
        
        # Combine measures (max weight gets higher priority)
        concentration_risk = max_weight * 0.7 + (hhi - 1/len(positions)) * 0.3
        
        return min(concentration_risk, 1.0)
    
    async def _calculate_correlation_risk(self, positions: List[Position]) -> float:
        """Calculate portfolio correlation risk."""
        if len(positions) < 2:
            return 0.0
        
        instruments = [pos.instrument for pos in positions]
        correlations = []
        
        # Calculate pairwise correlations
        for i, inst1 in enumerate(instruments):
            for j, inst2 in enumerate(instruments[i+1:], i+1):
                correlation = await self._get_correlation(inst1, inst2)
                correlations.append(abs(correlation))
        
        if not correlations:
            return 0.0
        
        # Average absolute correlation
        avg_correlation = sum(correlations) / len(correlations)
        
        # Higher correlation = higher risk
        return min(avg_correlation, 1.0)
    
    def _calculate_liquidity_risk(self, positions: List[Position]) -> float:
        """Calculate liquidity risk based on position sizes and instruments."""
        if not positions:
            return 0.0
        
        liquidity_scores = []
        
        for position in positions:
            # Simplified liquidity scoring
            if position.instrument.startswith(('EUR_USD', 'GBP_USD', 'USD_JPY')):
                # Major pairs - high liquidity
                base_liquidity = 0.1
            elif '_USD' in position.instrument or 'USD_' in position.instrument:
                # USD pairs - medium liquidity
                base_liquidity = 0.3
            else:
                # Exotic pairs - lower liquidity
                base_liquidity = 0.6
            
            # Size impact on liquidity
            size_factor = min(float(position.notional_value) / 1000000, 1.0)  # $1M = max impact
            
            liquidity_score = base_liquidity + (size_factor * 0.4)
            liquidity_scores.append(min(liquidity_score, 1.0))
        
        return sum(liquidity_scores) / len(liquidity_scores)
    
    def _calculate_pl_metrics(self, positions: List[Position]) -> Dict[str, float]:
        """Calculate P&L-based risk metrics."""
        if not positions:
            return {'daily_pl_risk': 0.0, 'max_drawdown': 0.0}
        
        total_daily_pl = sum(pos.daily_pl for pos in positions)
        total_value = sum(pos.market_value for pos in positions if pos.market_value > 0)
        
        # Daily P&L risk
        if total_value > 0:
            daily_pl_ratio = abs(float(total_daily_pl / total_value))
            daily_pl_risk = min(daily_pl_ratio / 0.05, 1.0)  # 5% daily move = max risk
        else:
            daily_pl_risk = 0.0
        
        # Simplified max drawdown calculation
        unrealized_losses = sum(
            pos.unrealized_pl for pos in positions 
            if pos.unrealized_pl < 0
        )
        
        if total_value > 0:
            max_drawdown = abs(float(unrealized_losses / total_value))
        else:
            max_drawdown = 0.0
        
        return {
            'daily_pl_risk': daily_pl_risk,
            'max_drawdown': max_drawdown
        }
    
    async def _calculate_portfolio_var(
        self, 
        positions: List[Position], 
        current_prices: Dict[str, Decimal],
        confidence: float = 0.95
    ) -> Decimal:
        """Calculate portfolio Value at Risk using correlation matrix."""
        if not positions:
            return Decimal("0")
        
        # Individual position VaRs
        position_vars = []
        weights = []
        
        total_value = sum(abs(pos.market_value) for pos in positions if pos.market_value != 0)
        
        if total_value == 0:
            return Decimal("0")
        
        for position in positions:
            if position.market_value == 0:
                continue
                
            # Individual position VaR
            volatility = await self._get_instrument_volatility(position.instrument)
            z_score = norm.ppf(confidence)
            position_var = abs(float(position.market_value)) * volatility * z_score
            
            position_vars.append(position_var)
            weights.append(abs(float(position.market_value)) / float(total_value))
        
        if not position_vars:
            return Decimal("0")
        
        # Simplified portfolio VaR (assuming 50% average correlation)
        individual_var_sum = sum(var**2 for var in position_vars)
        correlation_adjustment = 0.5  # Average correlation assumption
        
        portfolio_var = math.sqrt(individual_var_sum * (1 + correlation_adjustment))
        
        return Decimal(str(round(portfolio_var, 2)))
    
    def _calculate_composite_risk_score(
        self,
        position_risk: float,
        leverage_risk: Dict[str, float],
        concentration_risk: float,
        correlation_risk: float,
        liquidity_risk: float,
        pl_risk: float
    ) -> float:
        """Calculate composite risk score (0-100)."""
        
        # Weight different risk components
        weights = {
            'position': 0.25,
            'leverage': 0.20,
            'concentration': 0.15,
            'correlation': 0.10,
            'liquidity': 0.10,
            'pl': 0.20
        }
        
        # Combine risk components
        composite_risk = (
            position_risk * weights['position'] +
            leverage_risk['leverage_risk'] * weights['leverage'] +
            concentration_risk * weights['concentration'] +
            correlation_risk * weights['correlation'] +
            liquidity_risk * weights['liquidity'] +
            pl_risk * weights['pl']
        )
        
        # Convert to 0-100 scale
        risk_score = composite_risk * 100
        
        # Apply non-linear scaling for extreme risks
        if risk_score > 80:
            risk_score = 80 + (risk_score - 80) * 2
        
        return min(max(risk_score, 0.0), 100.0)
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level based on risk score."""
        if risk_score >= 90:
            return RiskLevel.CRITICAL
        elif risk_score >= 70:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _check_risk_limit_breaches(
        self,
        positions: List[Position],
        account_balance: Decimal,
        margin_available: Decimal,
        risk_score: float,
        var_95: Decimal
    ) -> List[str]:
        """Check for risk limit breaches."""
        breaches = []
        
        # Risk score limits
        if risk_score > self.risk_limits.max_risk_score:
            breaches.append(f"risk_score_exceeded: {risk_score:.1f} > {self.risk_limits.max_risk_score}")
        
        # Position size limits
        for position in positions:
            if position.notional_value > self.risk_limits.max_position_size:
                breaches.append(f"position_size_exceeded: {position.instrument} {position.notional_value}")
        
        # Leverage limits
        total_exposure = sum(pos.notional_value for pos in positions)
        if account_balance > 0:
            current_leverage = total_exposure / account_balance
            if current_leverage > self.risk_limits.max_leverage:
                breaches.append(f"leverage_exceeded: {current_leverage:.2f} > {self.risk_limits.max_leverage}")
        
        # Margin limits
        if account_balance > 0:
            required_margin = total_exposure * Decimal("0.02")  # 2% margin
            margin_utilization = required_margin / account_balance
            if margin_utilization > self.risk_limits.max_margin_utilization:
                breaches.append(f"margin_utilization_exceeded: {margin_utilization:.2f}")
        
        # Daily loss limits
        daily_pl = sum(pos.daily_pl for pos in positions)
        if daily_pl < -self.risk_limits.max_daily_loss:
            breaches.append(f"daily_loss_exceeded: {daily_pl}")
        
        # VaR limits
        if var_95 > self.risk_limits.max_var_95:
            breaches.append(f"var_exceeded: {var_95} > {self.risk_limits.max_var_95}")
        
        # Instrument concentration
        instrument_counts = defaultdict(int)
        for position in positions:
            instrument_counts[position.instrument] += 1
        
        for instrument, count in instrument_counts.items():
            if count > self.risk_limits.max_positions_per_instrument:
                breaches.append(f"instrument_concentration: {instrument} has {count} positions")
        
        return breaches
    
    def _calculate_sector_diversification(self, positions: List[Position]) -> float:
        """Calculate sector diversification score."""
        if not positions:
            return 1.0
        
        # Group by asset class (simplified sector mapping)
        sector_exposure = defaultdict(Decimal)
        total_exposure = Decimal("0")
        
        for position in positions:
            sector = position.asset_class.value
            exposure = abs(position.market_value)
            sector_exposure[sector] += exposure
            total_exposure += exposure
        
        if total_exposure == 0:
            return 1.0
        
        # Calculate diversification using inverse of Herfindahl index
        weights = [float(exposure / total_exposure) for exposure in sector_exposure.values()]
        hhi = sum(w**2 for w in weights)
        
        # Diversification score (1 = perfect diversification, 0 = concentrated)
        diversification = (1 - hhi) / (1 - 1/len(sector_exposure)) if len(sector_exposure) > 1 else 0.0
        
        return max(0.0, min(1.0, diversification))
    
    async def _get_instrument_volatility(self, instrument: str) -> float:
        """Get cached or calculated instrument volatility."""
        now = datetime.now()
        
        # Check cache (1-minute TTL)
        if instrument in self.volatility_cache:
            cached_time, cached_vol = self.volatility_cache[instrument]
            if (now - cached_time).total_seconds() < 60:
                return cached_vol
        
        # Calculate volatility (simplified - in production, use market data)
        if instrument.startswith(('EUR_USD', 'GBP_USD', 'USD_JPY')):
            volatility = 0.15  # Major pairs ~15% annual volatility
        elif '_USD' in instrument or 'USD_' in instrument:
            volatility = 0.20  # USD pairs ~20% annual volatility
        else:
            volatility = 0.30  # Exotic pairs ~30% annual volatility
        
        # Add some random variation (in production, use real market data)
        import random
        volatility *= (0.8 + random.random() * 0.4)  # ±20% variation
        
        # Cache result
        self.volatility_cache[instrument] = (now, volatility)
        
        return volatility
    
    async def _get_correlation(self, instrument1: str, instrument2: str) -> float:
        """Get cached or calculated correlation between instruments."""
        pair = tuple(sorted([instrument1, instrument2]))
        
        if pair in self.position_correlations:
            return self.position_correlations[pair]
        
        # Simplified correlation calculation
        # In production, calculate from historical price data
        
        # Same instrument = perfect correlation
        if instrument1 == instrument2:
            correlation = 1.0
        
        # USD pairs tend to be negatively correlated
        elif ('USD_' in instrument1 and 'USD_' in instrument2) or \
             ('_USD' in instrument1 and '_USD' in instrument2):
            correlation = -0.3
        
        # Mixed USD pairs
        elif ('USD_' in instrument1 and '_USD' in instrument2) or \
             ('_USD' in instrument1 and 'USD_' in instrument2):
            correlation = -0.1
        
        # Same base/quote currency
        elif instrument1.split('_')[0] == instrument2.split('_')[0] or \
             instrument1.split('_')[1] == instrument2.split('_')[1]:
            correlation = 0.4
        
        # Different pairs
        else:
            correlation = 0.1
        
        # Cache result
        self.position_correlations[pair] = correlation
        
        return correlation
    
    def _update_risk_score_history(self, account_id: str, risk_score: float):
        """Update risk score history for trend analysis."""
        now = datetime.now()
        
        # Add to history
        self.risk_score_history[account_id].append((now, risk_score))
        
        # Keep only last 24 hours
        cutoff = now - timedelta(hours=24)
        self.risk_score_history[account_id] = [
            (ts, score) for ts, score in self.risk_score_history[account_id]
            if ts >= cutoff
        ]
        
        # Update previous score
        self.previous_risk_scores[account_id] = risk_score
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get risk calculation engine performance metrics."""
        if not self.calculation_times:
            return {
                'avg_calculation_time_ms': 0.0,
                'max_calculation_time_ms': 0.0,
                'min_calculation_time_ms': 0.0,
                'last_calculation_time_ms': 0.0,
                'total_calculations': 0
            }
        
        return {
            'avg_calculation_time_ms': sum(self.calculation_times) / len(self.calculation_times),
            'max_calculation_time_ms': max(self.calculation_times),
            'min_calculation_time_ms': min(self.calculation_times),
            'last_calculation_time_ms': self.last_calculation_time,
            'total_calculations': len(self.calculation_times),
            'calculations_under_50ms': sum(1 for t in self.calculation_times if t < 50),
            'performance_target_met': sum(1 for t in self.calculation_times if t < 50) / len(self.calculation_times)
        }
    
    def get_risk_trends(self, account_id: str) -> Dict[str, float]:
        """Get risk score trends and patterns."""
        history = self.risk_score_history.get(account_id, [])
        
        if len(history) < 2:
            return {'trend': 0.0, 'volatility': 0.0, 'current_vs_avg': 0.0}
        
        scores = [score for _, score in history]
        
        # Calculate trend (simple linear regression slope)
        n = len(scores)
        x_sum = sum(range(n))
        y_sum = sum(scores)
        xy_sum = sum(i * score for i, score in enumerate(scores))
        x2_sum = sum(i**2 for i in range(n))
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum**2) if n * x2_sum != x_sum**2 else 0.0
        
        # Risk score volatility
        volatility = np.std(scores) if len(scores) > 1 else 0.0
        
        # Current vs average
        avg_score = sum(scores) / len(scores)
        current_score = scores[-1]
        current_vs_avg = (current_score - avg_score) / avg_score if avg_score > 0 else 0.0
        
        return {
            'trend': slope,
            'volatility': volatility,
            'current_vs_avg': current_vs_avg,
            'avg_risk_score': avg_score,
            'min_risk_score': min(scores),
            'max_risk_score': max(scores)
        }