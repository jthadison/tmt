"""
Signal Confidence Optimizer

Optimizes signal confidence thresholds based on performance analysis
and signal quality improvement tracking.
"""

import statistics
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from .models import (
    ParameterAdjustment, ParameterCategory, SignalConfidenceCalibration,
    generate_id
)
from .performance_calculator import TradeRecord

logger = logging.getLogger(__name__)


class SignalConfidenceOptimizer:
    """
    Optimizes signal confidence thresholds based on performance analysis
    """
    
    def __init__(self):
        self.min_confidence = 0.60
        self.max_confidence = 0.90
        self.default_confidence = 0.75
        self.min_sample_size = 20
        
    def optimize_signal_confidence(self, account_id: str,
                                 current_parameters: Dict[str, float],
                                 trade_history: List[TradeRecord]) -> Optional[ParameterAdjustment]:
        """
        Optimize signal confidence threshold based on performance analysis
        
        Args:
            account_id: Account identifier
            current_parameters: Current signal filtering parameters
            trade_history: Historical trade records with signal confidence
            
        Returns:
            Parameter adjustment recommendation or None
        """
        try:
            if len(trade_history) < self.min_sample_size:
                logger.warning(f"Insufficient trade history for {account_id}: {len(trade_history)}")
                return None
            
            # Analyze signal confidence calibration
            calibration = self._analyze_confidence_calibration(account_id, trade_history)
            
            current_threshold = current_parameters.get("confidence_threshold", self.default_confidence)
            recommended_threshold = calibration.optimal_threshold
            
            # Check if change is significant
            change_percentage = abs(recommended_threshold - current_threshold) / current_threshold
            if change_percentage < 0.05:  # Less than 5% change
                logger.info(f"Confidence threshold change too small for {account_id}: {change_percentage:.3f}")
                return None
            
            # Apply gradual change constraint
            max_change = current_threshold * 0.1  # Max 10% change
            if abs(recommended_threshold - current_threshold) > max_change:
                if recommended_threshold > current_threshold:
                    recommended_threshold = current_threshold + max_change
                else:
                    recommended_threshold = current_threshold - max_change
            
            # Ensure within bounds
            recommended_threshold = max(self.min_confidence, min(self.max_confidence, recommended_threshold))
            
            # Create parameter adjustment
            adjustment = ParameterAdjustment(
                adjustment_id=generate_id(),
                timestamp=datetime.utcnow(),
                parameter_name="confidence_threshold",
                category=ParameterCategory.SIGNAL_FILTERING,
                current_value=current_threshold,
                proposed_value=recommended_threshold,
                change_percentage=(recommended_threshold - current_threshold) / current_threshold,
                change_reason=self._generate_change_reason(calibration, recommended_threshold),
                analysis={
                    "performance_impact": calibration.expected_performance_improvement,
                    "risk_impact": self._estimate_risk_impact(recommended_threshold, current_threshold),
                    "confidence_level": self._calculate_confidence(len(trade_history)),
                    "sample_size": len(trade_history),
                    "p_value": 0.05  # Simplified
                }
            )
            
            logger.info(f"Signal confidence optimization for {account_id}: {current_threshold:.3f} -> {recommended_threshold:.3f}")
            return adjustment
            
        except Exception as e:
            logger.error(f"Failed to optimize signal confidence for {account_id}: {e}")
            raise
    
    def _analyze_confidence_calibration(self, account_id: str,
                                      trade_history: List[TradeRecord]) -> SignalConfidenceCalibration:
        """Analyze signal confidence calibration and performance"""
        try:
            # Get current threshold (estimate from data)
            confidences = [t.signal_confidence for t in trade_history if hasattr(t, 'signal_confidence')]
            if not confidences:
                logger.warning(f"No signal confidence data for {account_id}")
                return self._create_default_calibration(account_id)
            
            # Estimate current threshold
            sorted_confidences = sorted(confidences)
            current_threshold = sorted_confidences[int(len(sorted_confidences) * 0.25)]  # Rough estimate
            
            # Count signals above/below threshold
            signals_above = [c for c in confidences if c >= current_threshold]
            signals_below = [c for c in confidences if c < current_threshold]
            
            # Analyze performance by confidence level
            confidence_performance = self._analyze_performance_by_confidence(trade_history)
            
            # Find optimal threshold
            optimal_threshold = self._find_optimal_threshold(trade_history, confidence_performance)
            
            # Estimate expected signal count with new threshold
            expected_signal_count = len([c for c in confidences if c >= optimal_threshold])
            
            # Calculate performance improvement
            current_performance = self._calculate_threshold_performance(trade_history, current_threshold)
            optimal_performance = self._calculate_threshold_performance(trade_history, optimal_threshold)
            performance_improvement = optimal_performance - current_performance
            
            # Generate calibration curve data
            calibration_data = self._generate_calibration_curve(trade_history)
            
            return SignalConfidenceCalibration(
                analysis_id=generate_id(),
                timestamp=datetime.utcnow(),
                account_id=account_id,
                current_threshold=current_threshold,
                signals_above_threshold=len(signals_above),
                signals_below_threshold=len(signals_below),
                confidence_performance=confidence_performance,
                optimal_threshold=optimal_threshold,
                expected_signal_count=expected_signal_count,
                expected_performance_improvement=performance_improvement,
                calibration_data=calibration_data
            )
            
        except Exception as e:
            logger.error(f"Confidence calibration analysis failed: {e}")
            return self._create_default_calibration(account_id)
    
    def _analyze_performance_by_confidence(self, trade_history: List[TradeRecord]) -> Dict[str, Dict[str, float]]:
        """Analyze trading performance by confidence level bins"""
        try:
            # Define confidence bins
            bins = [
                (0.0, 0.6, "low"),
                (0.6, 0.7, "medium_low"),
                (0.7, 0.8, "medium"),
                (0.8, 0.9, "medium_high"),
                (0.9, 1.0, "high")
            ]
            
            performance = {}
            
            for min_conf, max_conf, bin_name in bins:
                # Filter trades in this confidence range
                bin_trades = [
                    t for t in trade_history 
                    if hasattr(t, 'signal_confidence') and min_conf <= t.signal_confidence < max_conf
                ]
                
                if bin_trades:
                    # Calculate performance metrics for this bin
                    winning_trades = [t for t in bin_trades if t.pnl > 0]
                    win_rate = len(winning_trades) / len(bin_trades)
                    avg_pnl = statistics.mean([t.pnl for t in bin_trades])
                    
                    # Calculate profit factor
                    gross_profit = sum([t.pnl for t in bin_trades if t.pnl > 0])
                    gross_loss = abs(sum([t.pnl for t in bin_trades if t.pnl < 0]))
                    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0
                    
                    performance[bin_name] = {
                        "win_rate": win_rate,
                        "avg_pnl": avg_pnl,
                        "profit_factor": profit_factor,
                        "trade_count": len(bin_trades),
                        "total_pnl": sum([t.pnl for t in bin_trades])
                    }
                else:
                    performance[bin_name] = {
                        "win_rate": 0.0,
                        "avg_pnl": 0.0,
                        "profit_factor": 0.0,
                        "trade_count": 0,
                        "total_pnl": 0.0
                    }
            
            return performance
            
        except Exception as e:
            logger.warning(f"Performance by confidence analysis failed: {e}")
            return {}
    
    def _find_optimal_threshold(self, trade_history: List[TradeRecord],
                              confidence_performance: Dict[str, Dict[str, float]]) -> float:
        """Find optimal confidence threshold"""
        try:
            # Test different thresholds
            thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
            best_threshold = self.default_confidence
            best_score = 0.0
            
            for threshold in thresholds:
                score = self._score_threshold(trade_history, threshold)
                if score > best_score:
                    best_score = score
                    best_threshold = threshold
            
            return best_threshold
            
        except Exception as e:
            logger.warning(f"Optimal threshold calculation failed: {e}")
            return self.default_confidence
    
    def _score_threshold(self, trade_history: List[TradeRecord], threshold: float) -> float:
        """Score a confidence threshold based on performance"""
        try:
            # Filter trades that would pass this threshold
            qualifying_trades = [
                t for t in trade_history 
                if hasattr(t, 'signal_confidence') and t.signal_confidence >= threshold
            ]
            
            if not qualifying_trades:
                return 0.0
            
            # Calculate performance metrics
            winning_trades = [t for t in qualifying_trades if t.pnl > 0]
            win_rate = len(winning_trades) / len(qualifying_trades)
            avg_pnl = statistics.mean([t.pnl for t in qualifying_trades])
            
            # Calculate Sharpe-like ratio
            if len(qualifying_trades) > 1:
                pnl_std = statistics.stdev([t.pnl for t in qualifying_trades])
                sharpe_like = avg_pnl / pnl_std if pnl_std > 0 else 0.0
            else:
                sharpe_like = 0.0
            
            # Penalty for too few trades
            trade_count_penalty = min(1.0, len(qualifying_trades) / 20.0)  # Penalty if < 20 trades
            
            # Combined score
            score = (win_rate * 0.3 + avg_pnl * 0.4 + sharpe_like * 0.3) * trade_count_penalty
            
            return score
            
        except Exception:
            return 0.0
    
    def _calculate_threshold_performance(self, trade_history: List[TradeRecord], threshold: float) -> float:
        """Calculate overall performance for a given threshold"""
        try:
            qualifying_trades = [
                t for t in trade_history 
                if hasattr(t, 'signal_confidence') and t.signal_confidence >= threshold
            ]
            
            if not qualifying_trades:
                return 0.0
            
            # Simple performance metric: average PnL
            return statistics.mean([t.pnl for t in qualifying_trades])
            
        except Exception:
            return 0.0
    
    def _generate_calibration_curve(self, trade_history: List[TradeRecord]) -> List[Dict[str, float]]:
        """Generate calibration curve data"""
        try:
            # Create confidence vs actual performance curve
            calibration_points = []
            
            for confidence_level in [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
                # Get trades at this confidence level (±0.025)
                margin = 0.025
                confidence_trades = [
                    t for t in trade_history 
                    if hasattr(t, 'signal_confidence') and 
                    confidence_level - margin <= t.signal_confidence < confidence_level + margin
                ]
                
                if confidence_trades:
                    actual_win_rate = len([t for t in confidence_trades if t.pnl > 0]) / len(confidence_trades)
                    avg_pnl = statistics.mean([t.pnl for t in confidence_trades])
                    
                    calibration_points.append({
                        "predicted_confidence": confidence_level,
                        "actual_win_rate": actual_win_rate,
                        "avg_pnl": avg_pnl,
                        "trade_count": len(confidence_trades)
                    })
            
            return calibration_points
            
        except Exception as e:
            logger.warning(f"Calibration curve generation failed: {e}")
            return []
    
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
    
    def _estimate_risk_impact(self, new_threshold: float, current_threshold: float) -> float:
        """Estimate risk impact of threshold change"""
        # Higher thresholds generally reduce risk by filtering out weak signals
        threshold_change = new_threshold - current_threshold
        
        # Simplified risk estimation: higher threshold = lower risk
        return -threshold_change * 0.5  # Negative means risk reduction
    
    def _generate_change_reason(self, calibration: SignalConfidenceCalibration,
                              recommended_threshold: float) -> str:
        """Generate human-readable reason for confidence threshold change"""
        reasons = []
        
        # Performance-based reasons
        if calibration.expected_performance_improvement > 0.1:
            reasons.append("higher threshold expected to improve trade quality significantly")
        elif calibration.expected_performance_improvement < -0.05:
            reasons.append("lower threshold may increase profitable signal count")
        
        # Signal count considerations
        current_count = calibration.signals_above_threshold
        expected_count = calibration.expected_signal_count
        
        if expected_count < current_count * 0.7:
            reasons.append("threshold increase may significantly reduce signal count")
        elif expected_count > current_count * 1.3:
            reasons.append("threshold decrease will increase signal opportunities")
        
        # Calibration-based reasons
        if calibration.calibration_data:
            high_conf_performance = [
                p for p in calibration.calibration_data 
                if p["predicted_confidence"] >= 0.8
            ]
            if high_conf_performance and all(p["actual_win_rate"] > 0.6 for p in high_conf_performance):
                reasons.append("high confidence signals show strong performance")
        
        if not reasons:
            reasons.append(f"optimization suggests {recommended_threshold:.1%} threshold for improved signal quality")
        
        return "; ".join(reasons)
    
    def _create_default_calibration(self, account_id: str) -> SignalConfidenceCalibration:
        """Create default calibration when data is insufficient"""
        return SignalConfidenceCalibration(
            analysis_id=generate_id(),
            timestamp=datetime.utcnow(),
            account_id=account_id,
            current_threshold=self.default_confidence,
            signals_above_threshold=15,
            signals_below_threshold=5,
            confidence_performance={},
            optimal_threshold=self.default_confidence,
            expected_signal_count=15,
            expected_performance_improvement=0.0,
            calibration_data=[]
        )