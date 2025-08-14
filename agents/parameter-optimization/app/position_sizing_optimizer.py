"""
Position Sizing Optimizer

Implements Kelly Criterion-based position sizing optimization with confidence-based
adjustments and drawdown-aware constraints.
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from .models import (
    ParameterAdjustment, ParameterCategory, KellyCriterionAnalysis,
    PerformanceMetrics, MarketRegime, generate_id
)
from .performance_calculator import TradeRecord, PerformancePeriod

logger = logging.getLogger(__name__)


class PositionSizingOptimizer:
    """
    Optimizes position sizing based on Kelly Criterion and performance metrics
    """
    
    def __init__(self):
        self.min_position_size = 0.005  # 0.5% minimum
        self.max_position_size = 0.030  # 3.0% maximum
        self.default_kelly_multiplier = 0.25  # Conservative quarter Kelly
        self.min_sample_size = 20  # Minimum trades for optimization
        self.confidence_threshold = 0.7  # Minimum confidence for changes
        
    def optimize_position_sizing(self, account_id: str, 
                                current_parameters: Dict[str, float],
                                performance_data: PerformanceMetrics,
                                trade_history: List[TradeRecord]) -> Optional[ParameterAdjustment]:
        """
        Optimize position sizing parameters based on performance data
        
        Args:
            account_id: Account identifier
            current_parameters: Current position sizing parameters
            performance_data: Performance metrics for analysis
            trade_history: Historical trade records
            
        Returns:
            Parameter adjustment recommendation or None
        """
        try:
            if len(trade_history) < self.min_sample_size:
                logger.warning(f"Insufficient trade history for {account_id}: {len(trade_history)} < {self.min_sample_size}")
                return None
            
            # Calculate Kelly Criterion
            kelly_analysis = self._calculate_kelly_criterion(account_id, trade_history)
            
            if kelly_analysis.implementation_confidence < self.confidence_threshold:
                logger.info(f"Kelly analysis confidence too low for {account_id}: {kelly_analysis.implementation_confidence}")
                return None
            
            # Get current position size
            current_size = current_parameters.get("base_risk_per_trade", 0.01)
            
            # Calculate recommended size with adjustments
            recommended_size = self._calculate_recommended_size(
                kelly_analysis, performance_data, current_size
            )
            
            # Apply safety constraints
            recommended_size = self._apply_safety_constraints(
                recommended_size, current_size, performance_data
            )
            
            # Check if change is significant enough
            change_percentage = abs(recommended_size - current_size) / current_size
            if change_percentage < 0.05:  # Less than 5% change
                logger.info(f"Position size change too small for {account_id}: {change_percentage:.3f}")
                return None
            
            # Create parameter adjustment
            adjustment = ParameterAdjustment(
                adjustment_id=generate_id(),
                timestamp=datetime.utcnow(),
                parameter_name="base_risk_per_trade",
                category=ParameterCategory.POSITION_SIZING,
                current_value=current_size,
                proposed_value=recommended_size,
                change_percentage=(recommended_size - current_size) / current_size,
                change_reason=self._generate_change_reason(kelly_analysis, performance_data),
                analysis={
                    "performance_impact": self._estimate_performance_impact(
                        kelly_analysis, recommended_size, current_size
                    ),
                    "risk_impact": self._estimate_risk_impact(
                        recommended_size, current_size, performance_data
                    ),
                    "confidence_level": kelly_analysis.implementation_confidence,
                    "sample_size": len(trade_history),
                    "p_value": self._calculate_statistical_significance(kelly_analysis)
                }
            )
            
            logger.info(f"Position sizing optimization for {account_id}: {current_size:.3f} -> {recommended_size:.3f}")
            return adjustment
            
        except Exception as e:
            logger.error(f"Failed to optimize position sizing for {account_id}: {e}")
            raise
    
    def _calculate_kelly_criterion(self, account_id: str, 
                                 trades: List[TradeRecord]) -> KellyCriterionAnalysis:
        """Calculate Kelly Criterion with confidence analysis"""
        try:
            # Separate wins and losses
            wins = [t.pnl for t in trades if t.pnl > 0]
            losses = [t.pnl for t in trades if t.pnl < 0]
            
            # Basic statistics
            total_trades = len(trades)
            win_count = len(wins)
            loss_count = len(losses)
            
            win_rate = win_count / total_trades if total_trades > 0 else 0.0
            avg_win = statistics.mean(wins) if wins else 0.0
            avg_loss = abs(statistics.mean(losses)) if losses else 0.0
            
            # Kelly formula: f = (bp - q) / b
            # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
            if avg_loss == 0:
                kelly_percentage = 0.0
            else:
                b = avg_win / avg_loss
                p = win_rate
                q = 1 - win_rate
                kelly_percentage = (b * p - q) / b
            
            # Cap Kelly at reasonable maximum (10%)
            kelly_percentage = max(0.0, min(0.10, kelly_percentage))
            
            # Calculate confidence interval using bootstrap method
            confidence_interval = self._bootstrap_kelly_confidence(trades)
            
            # Conservative multiplier based on trade count and consistency
            recommended_multiplier = self._calculate_kelly_multiplier(trades, kelly_percentage)
            
            # Risk assessment
            risk_assessment = self._assess_kelly_risk(kelly_percentage, trades)
            
            # Implementation confidence based on sample size and consistency
            implementation_confidence = self._calculate_implementation_confidence(
                trades, kelly_percentage, confidence_interval
            )
            
            # Final position size recommendation
            recommended_position_size = kelly_percentage * recommended_multiplier
            recommended_position_size = max(self.min_position_size, 
                                          min(self.max_position_size, recommended_position_size))
            
            analysis_period = timedelta(days=30)  # Assuming 30-day analysis
            
            return KellyCriterionAnalysis(
                analysis_id=generate_id(),
                timestamp=datetime.utcnow(),
                account_id=account_id,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                sample_size=total_trades,
                analysis_period=analysis_period,
                kelly_percentage=kelly_percentage,
                recommended_multiplier=recommended_multiplier,
                confidence_interval=confidence_interval,
                risk_assessment=risk_assessment,
                recommended_position_size=recommended_position_size,
                size_change_required=0.0,  # Will be calculated later
                implementation_confidence=implementation_confidence
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate Kelly criterion for {account_id}: {e}")
            raise
    
    def _bootstrap_kelly_confidence(self, trades: List[TradeRecord], 
                                  iterations: int = 1000) -> Tuple[float, float]:
        """Calculate Kelly confidence interval using bootstrap method"""
        import random
        
        try:
            kelly_values = []
            
            for _ in range(iterations):
                # Bootstrap sample
                bootstrap_sample = random.choices(trades, k=len(trades))
                
                # Calculate Kelly for this sample
                wins = [t.pnl for t in bootstrap_sample if t.pnl > 0]
                losses = [t.pnl for t in bootstrap_sample if t.pnl < 0]
                
                if not wins or not losses:
                    continue
                
                win_rate = len(wins) / len(bootstrap_sample)
                avg_win = statistics.mean(wins)
                avg_loss = abs(statistics.mean(losses))
                
                if avg_loss > 0:
                    b = avg_win / avg_loss
                    p = win_rate
                    q = 1 - win_rate
                    kelly = (b * p - q) / b
                    kelly_values.append(max(0.0, min(0.10, kelly)))
            
            if kelly_values:
                kelly_values.sort()
                lower_idx = int(0.025 * len(kelly_values))  # 2.5th percentile
                upper_idx = int(0.975 * len(kelly_values))  # 97.5th percentile
                
                return (kelly_values[lower_idx], kelly_values[upper_idx])
            else:
                return (0.0, 0.0)
                
        except Exception as e:
            logger.warning(f"Bootstrap confidence calculation failed: {e}")
            return (0.0, 0.0)
    
    def _calculate_kelly_multiplier(self, trades: List[TradeRecord], 
                                  kelly_percentage: float) -> float:
        """Calculate conservative Kelly multiplier based on trade consistency"""
        try:
            # Base multiplier
            multiplier = self.default_kelly_multiplier
            
            # Adjust based on sample size
            sample_size = len(trades)
            if sample_size < 50:
                multiplier *= 0.5  # Very conservative for small samples
            elif sample_size < 100:
                multiplier *= 0.75  # Somewhat conservative
            
            # Adjust based on Kelly value
            if kelly_percentage > 0.05:  # High Kelly suggests high volatility
                multiplier *= 0.8
            elif kelly_percentage < 0.02:  # Low Kelly suggests low edge
                multiplier *= 1.2
            
            # Adjust based on trade consistency (coefficient of variation)
            pnl_values = [t.pnl for t in trades]
            if pnl_values:
                pnl_mean = statistics.mean(pnl_values)
                pnl_stdev = statistics.stdev(pnl_values) if len(pnl_values) > 1 else 0
                
                if pnl_mean != 0:
                    cv = abs(pnl_stdev / pnl_mean)
                    if cv > 2.0:  # High variability
                        multiplier *= 0.7
                    elif cv < 1.0:  # Low variability
                        multiplier *= 1.1
            
            return max(0.1, min(0.5, multiplier))  # Keep between 10% and 50%
            
        except Exception as e:
            logger.warning(f"Kelly multiplier calculation failed: {e}")
            return self.default_kelly_multiplier
    
    def _assess_kelly_risk(self, kelly_percentage: float, 
                          trades: List[TradeRecord]) -> Dict[str, float]:
        """Assess risk metrics for Kelly-based sizing"""
        try:
            # Calculate volatility
            pnl_values = [t.pnl for t in trades]
            volatility = statistics.stdev(pnl_values) if len(pnl_values) > 1 else 0.0
            
            # Estimate maximum expected drawdown (simplified)
            # Using Kelly formula approximation for drawdown
            max_expected_drawdown = kelly_percentage * 2.0 if kelly_percentage > 0 else 0.0
            
            # Estimate time to recovery (days)
            avg_pnl = statistics.mean(pnl_values) if pnl_values else 0.0
            time_to_recovery = max_expected_drawdown / avg_pnl if avg_pnl > 0 else float('inf')
            
            # Simplified risk of ruin calculation
            win_rate = len([t for t in trades if t.pnl > 0]) / len(trades) if trades else 0.0
            risk_of_ruin = (1 - win_rate) ** 10 if win_rate < 1.0 else 0.0  # Simplified
            
            return {
                "volatility": volatility,
                "max_expected_drawdown": max_expected_drawdown,
                "time_to_recovery": time_to_recovery,
                "risk_of_ruin": risk_of_ruin
            }
            
        except Exception as e:
            logger.warning(f"Risk assessment calculation failed: {e}")
            return {
                "volatility": 0.0,
                "max_expected_drawdown": 0.0,
                "time_to_recovery": 0.0,
                "risk_of_ruin": 0.0
            }
    
    def _calculate_implementation_confidence(self, trades: List[TradeRecord],
                                           kelly_percentage: float,
                                           confidence_interval: Tuple[float, float]) -> float:
        """Calculate confidence in the Kelly-based recommendation"""
        try:
            confidence = 0.0
            
            # Sample size confidence (0-0.4)
            sample_size = len(trades)
            if sample_size >= 100:
                confidence += 0.4
            elif sample_size >= 50:
                confidence += 0.3
            elif sample_size >= 30:
                confidence += 0.2
            else:
                confidence += 0.1
            
            # Kelly value confidence (0-0.3)
            if 0.01 <= kelly_percentage <= 0.05:  # Reasonable range
                confidence += 0.3
            elif 0.005 <= kelly_percentage <= 0.08:  # Acceptable range
                confidence += 0.2
            else:
                confidence += 0.1
            
            # Confidence interval tightness (0-0.3)
            ci_width = confidence_interval[1] - confidence_interval[0]
            if ci_width < 0.01:  # Very tight
                confidence += 0.3
            elif ci_width < 0.02:  # Reasonably tight
                confidence += 0.2
            else:
                confidence += 0.1
            
            return min(1.0, confidence)
            
        except Exception as e:
            logger.warning(f"Implementation confidence calculation failed: {e}")
            return 0.5  # Default moderate confidence
    
    def _calculate_recommended_size(self, kelly_analysis: KellyCriterionAnalysis,
                                  performance_data: PerformanceMetrics,
                                  current_size: float) -> float:
        """Calculate recommended position size with adjustments"""
        try:
            base_size = kelly_analysis.recommended_position_size
            
            # Performance-based adjustment
            performance_multiplier = self._calculate_performance_multiplier(performance_data)
            
            # Drawdown-based adjustment
            drawdown_multiplier = self._calculate_drawdown_multiplier(performance_data)
            
            # Market regime adjustment
            regime_multiplier = self._calculate_regime_multiplier(performance_data.market_regime)
            
            # Apply adjustments
            adjusted_size = base_size * performance_multiplier * drawdown_multiplier * regime_multiplier
            
            # Gradual change constraint (max 20% change at once)
            max_change = current_size * 0.20
            if abs(adjusted_size - current_size) > max_change:
                if adjusted_size > current_size:
                    adjusted_size = current_size + max_change
                else:
                    adjusted_size = current_size - max_change
            
            return adjusted_size
            
        except Exception as e:
            logger.warning(f"Recommended size calculation failed: {e}")
            return current_size
    
    def _calculate_performance_multiplier(self, performance_data: PerformanceMetrics) -> float:
        """Calculate performance-based size multiplier"""
        try:
            # Base multiplier on Sharpe ratio
            sharpe = performance_data.sharpe_ratio
            
            if sharpe > 2.0:  # Excellent performance
                return 1.2
            elif sharpe > 1.5:  # Good performance
                return 1.1
            elif sharpe > 1.0:  # Decent performance
                return 1.0
            elif sharpe > 0.5:  # Poor performance
                return 0.9
            else:  # Very poor performance
                return 0.8
                
        except Exception:
            return 1.0
    
    def _calculate_drawdown_multiplier(self, performance_data: PerformanceMetrics) -> float:
        """Calculate drawdown-based size multiplier"""
        try:
            current_dd = performance_data.current_drawdown
            max_dd = performance_data.max_drawdown
            
            # Reduce size significantly if in large drawdown
            if current_dd > 0.15:  # 15% drawdown
                return 0.5
            elif current_dd > 0.10:  # 10% drawdown
                return 0.7
            elif current_dd > 0.05:  # 5% drawdown
                return 0.85
            else:
                return 1.0
                
        except Exception:
            return 1.0
    
    def _calculate_regime_multiplier(self, market_regime: MarketRegime) -> float:
        """Calculate market regime-based size multiplier"""
        try:
            regime_multipliers = {
                MarketRegime.TRENDING: 1.1,     # Trending markets favor momentum
                MarketRegime.RANGING: 0.9,      # Ranging markets are harder
                MarketRegime.VOLATILE: 0.8,     # Volatile markets increase risk
                MarketRegime.LOW_VOLATILITY: 1.0,
                MarketRegime.UNKNOWN: 1.0
            }
            
            return regime_multipliers.get(market_regime, 1.0)
            
        except Exception:
            return 1.0
    
    def _apply_safety_constraints(self, recommended_size: float, current_size: float,
                                performance_data: PerformanceMetrics) -> float:
        """Apply safety constraints to recommended position size"""
        try:
            # Absolute bounds
            constrained_size = max(self.min_position_size, min(self.max_position_size, recommended_size))
            
            # Additional constraints during poor performance
            if performance_data.sharpe_ratio < 0:  # Negative Sharpe
                constrained_size = min(constrained_size, current_size * 0.8)  # Max 20% reduction
            
            # Additional constraints during high drawdown
            if performance_data.current_drawdown > 0.10:  # 10% drawdown
                constrained_size = min(constrained_size, 0.015)  # Cap at 1.5%
            
            return constrained_size
            
        except Exception as e:
            logger.warning(f"Safety constraints application failed: {e}")
            return current_size
    
    def _generate_change_reason(self, kelly_analysis: KellyCriterionAnalysis,
                              performance_data: PerformanceMetrics) -> str:
        """Generate human-readable reason for position size change"""
        try:
            reasons = []
            
            # Kelly-based reason
            kelly_pct = kelly_analysis.kelly_percentage * 100
            reasons.append(f"Kelly Criterion suggests {kelly_pct:.1f}% optimal sizing")
            
            # Performance-based reason
            sharpe = performance_data.sharpe_ratio
            if sharpe > 1.5:
                reasons.append("strong recent performance supports increased sizing")
            elif sharpe < 0.5:
                reasons.append("weak recent performance suggests reduced sizing")
            
            # Drawdown-based reason
            if performance_data.current_drawdown > 0.05:
                reasons.append(f"current drawdown of {performance_data.current_drawdown:.1%} requires size reduction")
            
            # Sample size note
            if kelly_analysis.sample_size < 50:
                reasons.append(f"conservative adjustment due to limited sample size ({kelly_analysis.sample_size} trades)")
            
            return "; ".join(reasons)
            
        except Exception:
            return "Position sizing optimization based on Kelly Criterion and performance analysis"
    
    def _estimate_performance_impact(self, kelly_analysis: KellyCriterionAnalysis,
                                   recommended_size: float, current_size: float) -> float:
        """Estimate expected performance impact of size change"""
        try:
            # Simple approximation: impact proportional to size change and Kelly edge
            size_change_ratio = recommended_size / current_size if current_size > 0 else 1.0
            kelly_edge = kelly_analysis.kelly_percentage
            
            # Estimate Sharpe ratio improvement
            estimated_impact = (size_change_ratio - 1.0) * kelly_edge * 10  # Simplified formula
            
            return max(-0.5, min(0.5, estimated_impact))  # Cap at ±0.5 Sharpe
            
        except Exception:
            return 0.0
    
    def _estimate_risk_impact(self, recommended_size: float, current_size: float,
                            performance_data: PerformanceMetrics) -> float:
        """Estimate expected risk impact of size change"""
        try:
            size_change_ratio = recommended_size / current_size if current_size > 0 else 1.0
            
            # Risk scales roughly with position size
            risk_change = (size_change_ratio - 1.0) * performance_data.max_drawdown
            
            return risk_change
            
        except Exception:
            return 0.0
    
    def _calculate_statistical_significance(self, kelly_analysis: KellyCriterionAnalysis) -> float:
        """Calculate statistical significance of Kelly recommendation"""
        try:
            # Simple approximation based on sample size and confidence interval
            sample_size = kelly_analysis.sample_size
            ci_width = kelly_analysis.confidence_interval[1] - kelly_analysis.confidence_interval[0]
            
            # Larger samples and tighter confidence intervals = more significant
            if sample_size >= 100 and ci_width < 0.01:
                return 0.01  # Very significant
            elif sample_size >= 50 and ci_width < 0.02:
                return 0.05  # Significant
            else:
                return 0.10  # Moderately significant
                
        except Exception:
            return 0.10  # Default moderate significance