"""
Stop Loss Optimizer

Optimizes stop loss parameters based on volatility analysis and effectiveness tracking.
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from .models import (
    ParameterAdjustment, ParameterCategory, VolatilityAnalysis, 
    StopLossEffectiveness, MarketRegime, generate_id
)
from .performance_calculator import TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class ATRData:
    """ATR (Average True Range) data point"""
    timestamp: datetime
    symbol: str
    atr_value: float
    high: float
    low: float
    close: float


class StopLossOptimizer:
    """
    Optimizes stop loss parameters based on volatility and effectiveness analysis
    """
    
    def __init__(self):
        self.min_atr_multiplier = 1.0
        self.max_atr_multiplier = 4.0
        self.default_atr_multiplier = 2.0
        self.min_sample_size = 15  # Minimum trades for optimization
        self.atr_period = 14  # Standard ATR period
        
    def optimize_stop_loss(self, account_id: str, symbol: str,
                          current_parameters: Dict[str, float],
                          trade_history: List[TradeRecord],
                          market_data: List[ATRData]) -> Optional[ParameterAdjustment]:
        """
        Optimize stop loss parameters based on volatility and effectiveness
        
        Args:
            account_id: Account identifier
            symbol: Trading symbol
            current_parameters: Current stop loss parameters
            trade_history: Historical trade records
            market_data: ATR and price data
            
        Returns:
            Parameter adjustment recommendation or None
        """
        try:
            if len(trade_history) < self.min_sample_size:
                logger.warning(f"Insufficient trade history for {account_id}: {len(trade_history)}")
                return None
            
            # Analyze volatility
            volatility_analysis = self._analyze_volatility(symbol, market_data, trade_history)
            
            # Analyze stop loss effectiveness
            effectiveness = self._analyze_stop_effectiveness(account_id, symbol, trade_history)
            
            # Calculate optimal ATR multiplier
            optimal_multiplier = self._calculate_optimal_atr_multiplier(
                volatility_analysis, effectiveness, trade_history
            )
            
            current_multiplier = current_parameters.get("atr_multiplier", self.default_atr_multiplier)
            
            # Check if change is significant
            change_percentage = abs(optimal_multiplier - current_multiplier) / current_multiplier
            if change_percentage < 0.1:  # Less than 10% change
                logger.info(f"Stop loss change too small for {account_id}: {change_percentage:.3f}")
                return None
            
            # Apply gradual change constraint
            max_change = current_multiplier * 0.25  # Max 25% change
            if abs(optimal_multiplier - current_multiplier) > max_change:
                if optimal_multiplier > current_multiplier:
                    optimal_multiplier = current_multiplier + max_change
                else:
                    optimal_multiplier = current_multiplier - max_change
            
            # Ensure within bounds
            optimal_multiplier = max(self.min_atr_multiplier, 
                                   min(self.max_atr_multiplier, optimal_multiplier))
            
            # Create parameter adjustment
            adjustment = ParameterAdjustment(
                adjustment_id=generate_id(),
                timestamp=datetime.utcnow(),
                parameter_name="atr_multiplier",
                category=ParameterCategory.STOP_LOSS,
                current_value=current_multiplier,
                proposed_value=optimal_multiplier,
                change_percentage=(optimal_multiplier - current_multiplier) / current_multiplier,
                change_reason=self._generate_change_reason(
                    volatility_analysis, effectiveness, optimal_multiplier
                ),
                analysis={
                    "performance_impact": effectiveness.expected_improvement,
                    "risk_impact": self._estimate_risk_impact(optimal_multiplier, current_multiplier),
                    "confidence_level": effectiveness.confidence_level,
                    "sample_size": len(trade_history),
                    "p_value": 0.05  # Simplified
                }
            )
            
            logger.info(f"Stop loss optimization for {account_id}/{symbol}: {current_multiplier:.2f} -> {optimal_multiplier:.2f}")
            return adjustment
            
        except Exception as e:
            logger.error(f"Failed to optimize stop loss for {account_id}: {e}")
            raise
    
    def _analyze_volatility(self, symbol: str, market_data: List[ATRData],
                          trade_history: List[TradeRecord]) -> VolatilityAnalysis:
        """Analyze market volatility patterns"""
        try:
            if not market_data:
                logger.warning(f"No market data for volatility analysis: {symbol}")
                return self._create_default_volatility_analysis(symbol)
            
            # Sort by timestamp
            sorted_data = sorted(market_data, key=lambda x: x.timestamp)
            
            # Calculate current and average ATR
            current_atr = sorted_data[-1].atr_value if sorted_data else 0.0
            atr_values = [d.atr_value for d in sorted_data[-20:]]  # Last 20 periods
            atr_20_avg = statistics.mean(atr_values) if atr_values else current_atr
            
            # Determine ATR trend
            if len(atr_values) >= 10:
                recent_atr = statistics.mean(atr_values[-5:])
                older_atr = statistics.mean(atr_values[-10:-5])
                
                if recent_atr > older_atr * 1.1:
                    atr_trend = "increasing"
                elif recent_atr < older_atr * 0.9:
                    atr_trend = "decreasing"
                else:
                    atr_trend = "stable"
            else:
                atr_trend = "stable"
            
            # Analyze regime-based volatility
            regime_volatility = self._calculate_regime_volatility(trade_history, atr_values)
            
            # Time-of-day volatility (simplified)
            time_volatility = self._calculate_time_volatility(market_data)
            
            # Calculate percentiles
            all_atr_values = [d.atr_value for d in sorted_data]
            volatility_percentiles = self._calculate_percentiles(all_atr_values)
            
            # Determine current market regime
            current_regime = self._determine_current_regime(trade_history[-10:] if len(trade_history) >= 10 else trade_history)
            
            return VolatilityAnalysis(
                analysis_id=generate_id(),
                timestamp=datetime.utcnow(),
                symbol=symbol,
                current_atr=current_atr,
                atr_20_day_avg=atr_20_avg,
                atr_trend=atr_trend,
                regime_volatility=regime_volatility,
                time_of_day_volatility=time_volatility,
                volatility_percentiles=volatility_percentiles,
                current_regime=current_regime,
                regime_confidence=0.8  # Simplified
            )
            
        except Exception as e:
            logger.error(f"Volatility analysis failed for {symbol}: {e}")
            return self._create_default_volatility_analysis(symbol)
    
    def _analyze_stop_effectiveness(self, account_id: str, symbol: str,
                                  trade_history: List[TradeRecord]) -> StopLossEffectiveness:
        """Analyze effectiveness of current stop loss settings"""
        try:
            # Filter trades that hit stop loss
            stop_trades = [t for t in trade_history if t.exit_reason == "stop_loss"]
            total_trades = len(trade_history)
            
            # Calculate stop hit rate
            stop_hit_rate = len(stop_trades) / total_trades if total_trades > 0 else 0.0
            
            # Calculate average slippage
            avg_slippage = statistics.mean([t.slippage for t in stop_trades]) if stop_trades else 0.0
            
            # Analyze premature stops (stops that immediately reverse)
            premature_stops = self._analyze_premature_stops(stop_trades, trade_history)
            premature_rate = len(premature_stops) / len(stop_trades) if stop_trades else 0.0
            
            # Calculate current average stop distance
            stop_distances = []
            for trade in trade_history:
                if hasattr(trade, 'stop_distance_pips'):
                    stop_distances.append(trade.stop_distance_pips)
                else:
                    # Estimate from entry/exit if available
                    estimated_distance = abs(trade.entry_price - trade.exit_price) * 10000  # Rough pip conversion
                    stop_distances.append(estimated_distance)
            
            current_avg_stop = statistics.mean(stop_distances) if stop_distances else 20.0
            
            # Test different ATR multipliers
            multiplier_analysis = self._test_atr_multipliers(trade_history)
            
            # Find optimal multiplier
            optimal_multiplier = self._find_optimal_multiplier(multiplier_analysis)
            
            # Estimate improvement
            current_performance = self._calculate_stop_performance(trade_history, 2.0)  # Assume 2.0 current
            optimal_performance = multiplier_analysis.get(optimal_multiplier, current_performance)
            expected_improvement = optimal_performance - current_performance
            
            return StopLossEffectiveness(
                analysis_id=generate_id(),
                timestamp=datetime.utcnow(),
                account_id=account_id,
                symbol=symbol,
                current_atr_multiplier=2.0,  # Will be updated with actual
                current_avg_stop_distance=current_avg_stop,
                stop_hit_rate=stop_hit_rate,
                avg_stop_slippage=avg_slippage,
                premature_stop_rate=premature_rate,
                optimal_atr_multiplier=optimal_multiplier,
                expected_improvement=expected_improvement,
                confidence_level=self._calculate_confidence_level(len(trade_history)),
                stop_distance_analysis=self._format_distance_analysis(multiplier_analysis)
            )
            
        except Exception as e:
            logger.error(f"Stop effectiveness analysis failed for {account_id}: {e}")
            return self._create_default_effectiveness(account_id, symbol)
    
    def _test_atr_multipliers(self, trade_history: List[TradeRecord]) -> Dict[float, float]:
        """Test different ATR multipliers on historical data"""
        try:
            multipliers = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
            results = {}
            
            for multiplier in multipliers:
                performance = self._calculate_stop_performance(trade_history, multiplier)
                results[multiplier] = performance
            
            return results
            
        except Exception as e:
            logger.warning(f"ATR multiplier testing failed: {e}")
            return {2.0: 0.0}  # Default
    
    def _calculate_stop_performance(self, trades: List[TradeRecord], atr_multiplier: float) -> float:
        """Calculate performance score for a given ATR multiplier"""
        try:
            # Simulate trades with this ATR multiplier
            wins = 0
            total_pnl = 0.0
            
            for trade in trades:
                # Estimate if this trade would have been stopped out
                # This is a simplified simulation
                estimated_stop_distance = 20.0 * atr_multiplier  # Simplified
                
                if trade.pnl < 0 and abs(trade.pnl) > estimated_stop_distance:
                    # Would have been stopped out earlier
                    simulated_pnl = -estimated_stop_distance
                else:
                    simulated_pnl = trade.pnl
                
                if simulated_pnl > 0:
                    wins += 1
                total_pnl += simulated_pnl
            
            # Score based on profit factor and win rate
            win_rate = wins / len(trades) if trades else 0.0
            avg_pnl = total_pnl / len(trades) if trades else 0.0
            
            return win_rate * 0.5 + avg_pnl * 0.5  # Simplified scoring
            
        except Exception:
            return 0.0
    
    def _find_optimal_multiplier(self, multiplier_analysis: Dict[float, float]) -> float:
        """Find the optimal ATR multiplier from analysis results"""
        if not multiplier_analysis:
            return self.default_atr_multiplier
        
        # Find multiplier with best performance
        best_multiplier = max(multiplier_analysis.items(), key=lambda x: x[1])[0]
        return best_multiplier
    
    def _calculate_optimal_atr_multiplier(self, volatility_analysis: VolatilityAnalysis,
                                        effectiveness: StopLossEffectiveness,
                                        trade_history: List[TradeRecord]) -> float:
        """Calculate optimal ATR multiplier considering all factors"""
        try:
            # Start with effectiveness-based optimal
            base_multiplier = effectiveness.optimal_atr_multiplier
            
            # Adjust for volatility trend
            if volatility_analysis.atr_trend == "increasing":
                base_multiplier *= 1.1  # Wider stops in increasing volatility
            elif volatility_analysis.atr_trend == "decreasing":
                base_multiplier *= 0.9  # Tighter stops in decreasing volatility
            
            # Adjust for market regime
            regime_adjustments = {
                MarketRegime.TRENDING: 1.1,     # Wider stops for trends
                MarketRegime.RANGING: 0.9,      # Tighter stops for ranges
                MarketRegime.VOLATILE: 1.2,     # Much wider stops for volatility
                MarketRegime.LOW_VOLATILITY: 0.8,
                MarketRegime.UNKNOWN: 1.0
            }
            
            regime_adj = regime_adjustments.get(volatility_analysis.current_regime, 1.0)
            base_multiplier *= regime_adj
            
            # Adjust for stop hit rate
            if effectiveness.stop_hit_rate > 0.3:  # Too many stops hit
                base_multiplier *= 1.15
            elif effectiveness.stop_hit_rate < 0.1:  # Too few stops hit
                base_multiplier *= 0.9
            
            # Adjust for premature stop rate
            if effectiveness.premature_stop_rate > 0.2:  # Too many premature stops
                base_multiplier *= 1.1
            
            # Ensure within bounds
            return max(self.min_atr_multiplier, min(self.max_atr_multiplier, base_multiplier))
            
        except Exception as e:
            logger.warning(f"Optimal ATR calculation failed: {e}")
            return self.default_atr_multiplier
    
    def _analyze_premature_stops(self, stop_trades: List[TradeRecord],
                               all_trades: List[TradeRecord]) -> List[TradeRecord]:
        """Identify trades that were prematurely stopped out"""
        # Simplified implementation - in practice would need price data
        # to check if price reversed after stop
        premature = []
        
        for trade in stop_trades:
            # Simple heuristic: if the trade was stopped out but market moved favorably after
            # This would require additional market data in a real implementation
            if trade.pnl < -10:  # Arbitrary threshold
                premature.append(trade)
        
        return premature
    
    def _calculate_regime_volatility(self, trades: List[TradeRecord], atr_values: List[float]) -> Dict[str, float]:
        """Calculate volatility by market regime"""
        regime_volatility = {}
        
        # Group trades by regime
        regime_groups = {}
        for trade in trades:
            regime = trade.market_regime
            if regime not in regime_groups:
                regime_groups[regime] = []
            regime_groups[regime].append(trade)
        
        # Calculate average volatility for each regime
        for regime, regime_trades in regime_groups.items():
            if regime_trades:
                # Simplified: use ATR average for now
                regime_volatility[regime.value] = statistics.mean(atr_values) if atr_values else 0.0
        
        return regime_volatility
    
    def _calculate_time_volatility(self, market_data: List[ATRData]) -> Dict[str, float]:
        """Calculate volatility by time of day"""
        # Simplified implementation
        return {
            "asian": statistics.mean([d.atr_value for d in market_data[:8]]) if market_data else 0.0,
            "london": statistics.mean([d.atr_value for d in market_data[8:16]]) if len(market_data) > 8 else 0.0,
            "ny": statistics.mean([d.atr_value for d in market_data[16:]]) if len(market_data) > 16 else 0.0
        }
    
    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate volatility percentiles"""
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            "p25": sorted_values[int(0.25 * n)] if n > 0 else 0.0,
            "p50": sorted_values[int(0.50 * n)] if n > 0 else 0.0,
            "p75": sorted_values[int(0.75 * n)] if n > 0 else 0.0,
            "p90": sorted_values[int(0.90 * n)] if n > 0 else 0.0
        }
    
    def _determine_current_regime(self, recent_trades: List[TradeRecord]) -> MarketRegime:
        """Determine current market regime from recent trades"""
        if not recent_trades:
            return MarketRegime.UNKNOWN
        
        # Count regime occurrences
        regime_counts = {}
        for trade in recent_trades:
            regime = trade.market_regime
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        # Return most common regime
        if regime_counts:
            return max(regime_counts.items(), key=lambda x: x[1])[0]
        
        return MarketRegime.UNKNOWN
    
    def _calculate_confidence_level(self, sample_size: int) -> float:
        """Calculate confidence level based on sample size"""
        if sample_size >= 50:
            return 0.9
        elif sample_size >= 30:
            return 0.8
        elif sample_size >= 20:
            return 0.7
        else:
            return 0.6
    
    def _format_distance_analysis(self, multiplier_analysis: Dict[float, float]) -> List[Dict[str, float]]:
        """Format distance analysis for output"""
        return [
            {
                "atr_multiplier": multiplier,
                "performance_score": score,
                "estimated_stop_distance": multiplier * 20.0  # Simplified
            }
            for multiplier, score in multiplier_analysis.items()
        ]
    
    def _generate_change_reason(self, volatility_analysis: VolatilityAnalysis,
                              effectiveness: StopLossEffectiveness,
                              optimal_multiplier: float) -> str:
        """Generate human-readable reason for stop loss change"""
        reasons = []
        
        # Effectiveness-based reasons
        if effectiveness.stop_hit_rate > 0.3:
            reasons.append("high stop hit rate suggests stops are too tight")
        elif effectiveness.stop_hit_rate < 0.1:
            reasons.append("low stop hit rate suggests stops may be too wide")
        
        if effectiveness.premature_stop_rate > 0.2:
            reasons.append("high premature stop rate indicates need for wider stops")
        
        # Volatility-based reasons
        if volatility_analysis.atr_trend == "increasing":
            reasons.append("increasing volatility supports wider stop distances")
        elif volatility_analysis.atr_trend == "decreasing":
            reasons.append("decreasing volatility allows for tighter stops")
        
        # Regime-based reasons
        regime = volatility_analysis.current_regime
        if regime == MarketRegime.VOLATILE:
            reasons.append("volatile market conditions require wider stops")
        elif regime == MarketRegime.RANGING:
            reasons.append("ranging market allows for tighter stop placement")
        
        if not reasons:
            reasons.append(f"optimization suggests {optimal_multiplier:.1f}x ATR for improved risk management")
        
        return "; ".join(reasons)
    
    def _estimate_risk_impact(self, new_multiplier: float, current_multiplier: float) -> float:
        """Estimate risk impact of stop loss change"""
        # Wider stops = higher risk per trade but potentially lower stop hit rate
        multiplier_change = new_multiplier / current_multiplier - 1.0
        
        # Simplified risk estimation
        return multiplier_change * 0.5  # 50% of multiplier change translates to risk change
    
    def _create_default_volatility_analysis(self, symbol: str) -> VolatilityAnalysis:
        """Create default volatility analysis when data is insufficient"""
        return VolatilityAnalysis(
            analysis_id=generate_id(),
            timestamp=datetime.utcnow(),
            symbol=symbol,
            current_atr=0.0015,  # Default ATR
            atr_20_day_avg=0.0015,
            atr_trend="stable",
            regime_volatility={},
            time_of_day_volatility={},
            volatility_percentiles={},
            current_regime=MarketRegime.UNKNOWN,
            regime_confidence=0.5
        )
    
    def _create_default_effectiveness(self, account_id: str, symbol: str) -> StopLossEffectiveness:
        """Create default effectiveness analysis when data is insufficient"""
        return StopLossEffectiveness(
            analysis_id=generate_id(),
            timestamp=datetime.utcnow(),
            account_id=account_id,
            symbol=symbol,
            current_atr_multiplier=self.default_atr_multiplier,
            current_avg_stop_distance=20.0,
            stop_hit_rate=0.2,
            avg_stop_slippage=0.5,
            premature_stop_rate=0.15,
            optimal_atr_multiplier=self.default_atr_multiplier,
            expected_improvement=0.0,
            confidence_level=0.5,
            stop_distance_analysis=[]
        )


from dataclasses import dataclass