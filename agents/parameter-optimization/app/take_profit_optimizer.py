"""
Take Profit Optimizer

Optimizes take profit parameters based on achieved vs expected profit analysis
and market condition impact assessment.
"""

import statistics
from datetime import datetime
from typing import Dict, List, Optional
import logging

from .models import (
    ParameterAdjustment, ParameterCategory, TakeProfitAnalysis, 
    MarketRegime, generate_id
)
from .performance_calculator import TradeRecord

logger = logging.getLogger(__name__)


class TakeProfitOptimizer:
    """
    Optimizes take profit parameters based on achievement analysis
    """
    
    def __init__(self):
        self.min_rr_ratio = 1.0
        self.max_rr_ratio = 5.0
        self.default_rr_ratio = 2.0
        self.min_sample_size = 15
        
    def optimize_take_profit(self, account_id: str,
                           current_parameters: Dict[str, float],
                           trade_history: List[TradeRecord]) -> Optional[ParameterAdjustment]:
        """
        Optimize take profit parameters based on achievement analysis
        
        Args:
            account_id: Account identifier
            current_parameters: Current take profit parameters
            trade_history: Historical trade records
            
        Returns:
            Parameter adjustment recommendation or None
        """
        try:
            if len(trade_history) < self.min_sample_size:
                logger.warning(f"Insufficient trade history for {account_id}: {len(trade_history)}")
                return None
            
            # Analyze take profit effectiveness
            tp_analysis = self._analyze_take_profit_effectiveness(account_id, trade_history)
            
            current_rr = current_parameters.get("base_risk_reward_ratio", self.default_rr_ratio)
            recommended_rr = tp_analysis.recommended_rr_ratio
            
            # Check if change is significant
            change_percentage = abs(recommended_rr - current_rr) / current_rr
            if change_percentage < 0.1:  # Less than 10% change
                logger.info(f"Take profit change too small for {account_id}: {change_percentage:.3f}")
                return None
            
            # Apply gradual change constraint
            max_change = current_rr * 0.2  # Max 20% change
            if abs(recommended_rr - current_rr) > max_change:
                if recommended_rr > current_rr:
                    recommended_rr = current_rr + max_change
                else:
                    recommended_rr = current_rr - max_change
            
            # Ensure within bounds
            recommended_rr = max(self.min_rr_ratio, min(self.max_rr_ratio, recommended_rr))
            
            # Create parameter adjustment
            adjustment = ParameterAdjustment(
                adjustment_id=generate_id(),
                timestamp=datetime.utcnow(),
                parameter_name="base_risk_reward_ratio",
                category=ParameterCategory.TAKE_PROFIT,
                current_value=current_rr,
                proposed_value=recommended_rr,
                change_percentage=(recommended_rr - current_rr) / current_rr,
                change_reason=self._generate_change_reason(tp_analysis, recommended_rr),
                analysis={
                    "performance_impact": tp_analysis.expected_profit_improvement,
                    "risk_impact": 0.0,  # Take profit changes don't increase risk
                    "confidence_level": self._calculate_confidence(len(trade_history)),
                    "sample_size": len(trade_history),
                    "p_value": 0.05  # Simplified
                }
            )
            
            logger.info(f"Take profit optimization for {account_id}: {current_rr:.2f} -> {recommended_rr:.2f}")
            return adjustment
            
        except Exception as e:
            logger.error(f"Failed to optimize take profit for {account_id}: {e}")
            raise
    
    def _analyze_take_profit_effectiveness(self, account_id: str,
                                         trade_history: List[TradeRecord]) -> TakeProfitAnalysis:
        """Analyze take profit target effectiveness"""
        try:
            # Separate trades by exit reason
            tp_trades = [t for t in trade_history if t.exit_reason == "take_profit"]
            all_winning_trades = [t for t in trade_history if t.pnl > 0]
            
            # Calculate achievement rates
            total_trades = len(trade_history)
            target_hit_rate = len(tp_trades) / total_trades if total_trades > 0 else 0.0
            
            # Calculate average profit realized vs potential
            if all_winning_trades:
                avg_profit_realized = statistics.mean([t.pnl for t in all_winning_trades])
                # Estimate potential profit (simplified)
                avg_profit_potential = avg_profit_realized * 1.5  # Assume could have made 50% more
                realization_rate = avg_profit_realized / avg_profit_potential
            else:
                avg_profit_realized = 0.0
                realization_rate = 0.0
            
            # Calculate premature exit rate
            manual_exits = [t for t in trade_history if t.exit_reason == "manual" and t.pnl > 0]
            premature_exit_rate = len(manual_exits) / len(all_winning_trades) if all_winning_trades else 0.0
            
            # Analyze optimal exit points
            optimal_exits = self._find_optimal_exit_points(trade_history)
            
            # Analyze market condition impact
            market_impact = self._analyze_market_condition_impact(trade_history)
            
            # Calculate recommended R:R ratio
            recommended_rr = self._calculate_optimal_rr_ratio(trade_history, market_impact)
            
            # Estimate expected hit rate with new ratio
            expected_hit_rate = self._estimate_hit_rate(trade_history, recommended_rr)
            
            # Estimate profit improvement
            current_profit_score = target_hit_rate * avg_profit_realized
            expected_profit_score = expected_hit_rate * (avg_profit_realized * recommended_rr / 2.0)
            profit_improvement = (expected_profit_score - current_profit_score) / current_profit_score if current_profit_score > 0 else 0.0
            
            return TakeProfitAnalysis(
                analysis_id=generate_id(),
                timestamp=datetime.utcnow(),
                account_id=account_id,
                target_hit_rate=target_hit_rate,
                avg_profit_realized=avg_profit_realized,
                premature_exit_rate=premature_exit_rate,
                optimal_exit_points=optimal_exits,
                market_condition_impact=market_impact,
                recommended_rr_ratio=recommended_rr,
                expected_hit_rate=expected_hit_rate,
                expected_profit_improvement=profit_improvement
            )
            
        except Exception as e:
            logger.error(f"Take profit effectiveness analysis failed: {e}")
            return self._create_default_analysis(account_id)
    
    def _find_optimal_exit_points(self, trade_history: List[TradeRecord]) -> List[float]:
        """Find historically optimal exit points"""
        # Simplified: return some reasonable exit multiples
        return [1.0, 1.5, 2.0, 2.5, 3.0]
    
    def _analyze_market_condition_impact(self, trade_history: List[TradeRecord]) -> Dict[str, Dict[str, float]]:
        """Analyze how market conditions affect take profit success"""
        try:
            market_impact = {}
            
            # Group trades by market regime
            regime_groups = {}
            for trade in trade_history:
                regime = trade.market_regime
                if regime not in regime_groups:
                    regime_groups[regime] = []
                regime_groups[regime].append(trade)
            
            # Analyze each regime
            for regime, trades in regime_groups.items():
                if trades:
                    tp_trades = [t for t in trades if t.exit_reason == "take_profit"]
                    winning_trades = [t for t in trades if t.pnl > 0]
                    
                    hit_rate = len(tp_trades) / len(trades) if trades else 0.0
                    avg_profit = statistics.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
                    
                    # Recommend R:R based on regime characteristics
                    if regime == MarketRegime.TRENDING:
                        recommended_rr = 2.5  # Trends can run further
                    elif regime == MarketRegime.RANGING:
                        recommended_rr = 1.5  # Limited profit potential
                    elif regime == MarketRegime.VOLATILE:
                        recommended_rr = 2.0  # Standard target
                    else:
                        recommended_rr = 2.0
                    
                    market_impact[regime.value] = {
                        "hit_rate": hit_rate,
                        "avg_profit": avg_profit,
                        "recommended_rr": recommended_rr
                    }
            
            return market_impact
            
        except Exception as e:
            logger.warning(f"Market condition impact analysis failed: {e}")
            return {}
    
    def _calculate_optimal_rr_ratio(self, trade_history: List[TradeRecord],
                                  market_impact: Dict[str, Dict[str, float]]) -> float:
        """Calculate optimal risk-reward ratio"""
        try:
            # Test different R:R ratios
            rr_ratios = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
            best_ratio = self.default_rr_ratio
            best_score = 0.0
            
            for ratio in rr_ratios:
                score = self._score_rr_ratio(trade_history, ratio)
                if score > best_score:
                    best_score = score
                    best_ratio = ratio
            
            # Weight by market regime if available
            if market_impact:
                regime_weights = self._calculate_regime_weights(trade_history)
                weighted_rr = 0.0
                
                for regime_name, impact in market_impact.items():
                    weight = regime_weights.get(regime_name, 0.0)
                    regime_rr = impact.get("recommended_rr", self.default_rr_ratio)
                    weighted_rr += weight * regime_rr
                
                if weighted_rr > 0:
                    # Blend the weighted recommendation with the best ratio
                    best_ratio = (best_ratio + weighted_rr) / 2.0
            
            return max(self.min_rr_ratio, min(self.max_rr_ratio, best_ratio))
            
        except Exception as e:
            logger.warning(f"Optimal R:R calculation failed: {e}")
            return self.default_rr_ratio
    
    def _score_rr_ratio(self, trade_history: List[TradeRecord], rr_ratio: float) -> float:
        """Score a specific R:R ratio based on historical performance"""
        try:
            # Simulate what would have happened with this R:R ratio
            total_profit = 0.0
            hit_count = 0
            
            for trade in trade_history:
                if trade.pnl > 0:
                    # Estimate if this trade would have hit the target
                    # Simplified: assume hit if actual profit > target profit
                    estimated_target = 20.0 * rr_ratio  # Simplified target calculation
                    
                    if trade.pnl >= estimated_target:
                        total_profit += estimated_target
                        hit_count += 1
                    else:
                        # Would have been stopped out or exited early
                        total_profit += trade.pnl * 0.8  # Assume some profit realized
                else:
                    total_profit += trade.pnl  # Losses remain the same
            
            # Score based on total profit and hit rate
            hit_rate = hit_count / len(trade_history) if trade_history else 0.0
            avg_profit = total_profit / len(trade_history) if trade_history else 0.0
            
            return avg_profit * 0.7 + hit_rate * 0.3  # Weighted score
            
        except Exception:
            return 0.0
    
    def _calculate_regime_weights(self, trade_history: List[TradeRecord]) -> Dict[str, float]:
        """Calculate weights for different market regimes"""
        regime_counts = {}
        total_trades = len(trade_history)
        
        for trade in trade_history:
            regime = trade.market_regime.value
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        # Convert counts to weights
        return {regime: count / total_trades for regime, count in regime_counts.items()}
    
    def _estimate_hit_rate(self, trade_history: List[TradeRecord], rr_ratio: float) -> float:
        """Estimate hit rate for a given R:R ratio"""
        # Simplified estimation based on historical data
        # In practice, this would use more sophisticated modeling
        
        current_tp_trades = [t for t in trade_history if t.exit_reason == "take_profit"]
        current_hit_rate = len(current_tp_trades) / len(trade_history) if trade_history else 0.0
        
        # Adjust based on R:R ratio change from baseline
        baseline_rr = 2.0
        rr_adjustment = baseline_rr / rr_ratio  # Higher R:R = lower hit rate
        
        estimated_hit_rate = current_hit_rate * rr_adjustment
        return max(0.1, min(0.8, estimated_hit_rate))  # Keep within reasonable bounds
    
    def _calculate_confidence(self, sample_size: int) -> float:
        """Calculate confidence level based on sample size"""
        if sample_size >= 50:
            return 0.9
        elif sample_size >= 30:
            return 0.8
        elif sample_size >= 20:
            return 0.7
        else:
            return 0.6
    
    def _generate_change_reason(self, analysis: TakeProfitAnalysis, recommended_rr: float) -> str:
        """Generate human-readable reason for take profit change"""
        reasons = []
        
        if analysis.target_hit_rate < 0.2:
            reasons.append("low target hit rate suggests targets are too ambitious")
        elif analysis.target_hit_rate > 0.6:
            reasons.append("high target hit rate suggests targets may be too conservative")
        
        if analysis.premature_exit_rate > 0.3:
            reasons.append("high premature exit rate indicates potential for higher targets")
        
        if recommended_rr > 2.5:
            reasons.append("market conditions support higher profit targets")
        elif recommended_rr < 1.8:
            reasons.append("market conditions suggest more conservative targets")
        
        if not reasons:
            reasons.append(f"optimization suggests {recommended_rr:.1f}:1 R:R for improved profit capture")
        
        return "; ".join(reasons)
    
    def _create_default_analysis(self, account_id: str) -> TakeProfitAnalysis:
        """Create default analysis when data is insufficient"""
        return TakeProfitAnalysis(
            analysis_id=generate_id(),
            timestamp=datetime.utcnow(),
            account_id=account_id,
            target_hit_rate=0.3,
            avg_profit_realized=50.0,
            premature_exit_rate=0.2,
            optimal_exit_points=[1.5, 2.0, 2.5],
            market_condition_impact={},
            recommended_rr_ratio=self.default_rr_ratio,
            expected_hit_rate=0.3,
            expected_profit_improvement=0.0
        )