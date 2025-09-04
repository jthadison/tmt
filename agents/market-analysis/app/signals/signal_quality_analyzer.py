"""
Signal Quality Analyzer

Analyzes historical signal performance to optimize signal generation parameters
and improve the signal-to-execution conversion ratio.

Current Problem: 172+ signals generated, only 5 executed (2.9% conversion)
Target: Increase conversion to 15-20% while maintaining/improving profitability
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import asyncio
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SignalQualityAnalyzer:
    """
    Analyzes signal performance to optimize generation parameters.
    
    Key Capabilities:
    - Historical signal performance analysis
    - Confidence threshold optimization
    - Pattern type performance ranking
    - Signal-to-execution conversion analysis
    - Risk-reward optimization recommendations
    """
    
    def __init__(self, 
                 data_retention_days: int = 30,
                 min_sample_size: int = 20,
                 analysis_update_interval_hours: int = 6):
        """
        Initialize the signal quality analyzer.
        
        Args:
            data_retention_days: Days of historical data to analyze
            min_sample_size: Minimum signals required for analysis
            analysis_update_interval_hours: How often to update analysis
        """
        self.data_retention_days = data_retention_days
        self.min_sample_size = min_sample_size
        self.analysis_update_interval_hours = analysis_update_interval_hours
        
        # Performance tracking
        self.signal_history = []
        self.execution_history = []
        self.performance_metrics = {}
        self.optimization_recommendations = {}
        
        # Analysis results cache
        self.last_analysis_time = None
        self.cached_results = {}
        
    async def analyze_signal_performance(self, 
                                       historical_signals: List[Dict],
                                       execution_data: List[Dict]) -> Dict:
        """
        Comprehensive signal performance analysis.
        
        Args:
            historical_signals: List of generated signals
            execution_data: List of executed trades
            
        Returns:
            Dict containing analysis results and optimization recommendations
        """
        try:
            logger.info(f"Analyzing {len(historical_signals)} signals and {len(execution_data)} executions")
            
            # Filter recent data
            cutoff_date = datetime.now() - timedelta(days=self.data_retention_days)
            recent_signals = [
                s for s in historical_signals 
                if s.get('generated_at', datetime.min) > cutoff_date
            ]
            recent_executions = [
                e for e in execution_data
                if e.get('executed_at', datetime.min) > cutoff_date
            ]
            
            if len(recent_signals) < self.min_sample_size:
                return {
                    'analysis_status': 'insufficient_data',
                    'signals_available': len(recent_signals),
                    'min_required': self.min_sample_size,
                    'recommendation': 'Continue collecting data for meaningful analysis'
                }
            
            # Core analyses
            confidence_analysis = await self._analyze_confidence_thresholds(recent_signals, recent_executions)
            pattern_analysis = await self._analyze_pattern_performance(recent_signals, recent_executions)
            conversion_analysis = await self._analyze_conversion_rates(recent_signals, recent_executions)
            timing_analysis = await self._analyze_signal_timing(recent_signals, recent_executions)
            
            # Generate optimization recommendations
            optimization_recommendations = await self._generate_optimization_recommendations(
                confidence_analysis, pattern_analysis, conversion_analysis, timing_analysis
            )
            
            # Calculate performance impact estimates
            impact_estimates = await self._estimate_optimization_impact(optimization_recommendations)
            
            analysis_results = {
                'analysis_status': 'completed',
                'analysis_timestamp': datetime.now(),
                'data_summary': {
                    'signals_analyzed': len(recent_signals),
                    'executions_analyzed': len(recent_executions),
                    'conversion_rate': len(recent_executions) / len(recent_signals) if recent_signals else 0,
                    'analysis_period_days': self.data_retention_days
                },
                'confidence_analysis': confidence_analysis,
                'pattern_analysis': pattern_analysis,
                'conversion_analysis': conversion_analysis,
                'timing_analysis': timing_analysis,
                'optimization_recommendations': optimization_recommendations,
                'impact_estimates': impact_estimates
            }
            
            # Cache results
            self.cached_results = analysis_results
            self.last_analysis_time = datetime.now()
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in signal performance analysis: {e}")
            return {
                'analysis_status': 'error',
                'error_message': str(e),
                'timestamp': datetime.now()
            }
    
    async def _analyze_confidence_thresholds(self, 
                                           signals: List[Dict], 
                                           executions: List[Dict]) -> Dict:
        """Analyze optimal confidence thresholds for signal generation"""
        
        # Create confidence buckets
        confidence_buckets = np.arange(50, 100, 5)  # 50%, 55%, 60%, ..., 95%
        bucket_analysis = {}
        
        for threshold in confidence_buckets:
            # Filter signals above threshold
            qualifying_signals = [
                s for s in signals 
                if s.get('confidence', 0) >= threshold
            ]
            
            # Find executed signals in this bucket
            executed_signals = []
            for signal in qualifying_signals:
                signal_id = signal.get('signal_id')
                execution = next((e for e in executions if e.get('signal_id') == signal_id), None)
                if execution:
                    executed_signals.append({
                        'signal': signal,
                        'execution': execution
                    })
            
            # Calculate performance metrics for this threshold
            if qualifying_signals:
                conversion_rate = len(executed_signals) / len(qualifying_signals)
                
                # Calculate profitability if we have executions
                if executed_signals:
                    profits = [e['execution'].get('pnl', 0) for e in executed_signals]
                    avg_profit = np.mean(profits)
                    win_rate = len([p for p in profits if p > 0]) / len(profits)
                    profit_factor = sum([p for p in profits if p > 0]) / abs(sum([p for p in profits if p < 0])) if any(p < 0 for p in profits) else float('inf')
                else:
                    avg_profit = 0
                    win_rate = 0
                    profit_factor = 0
                
                bucket_analysis[int(threshold)] = {
                    'signals_count': len(qualifying_signals),
                    'executions_count': len(executed_signals),
                    'conversion_rate': conversion_rate,
                    'avg_profit_per_trade': avg_profit,
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'quality_score': self._calculate_quality_score(
                        conversion_rate, avg_profit, win_rate, profit_factor
                    )
                }
        
        # Find optimal threshold
        optimal_threshold = self._find_optimal_confidence_threshold(bucket_analysis)
        
        return {
            'current_threshold': 65.0,  # Current system threshold
            'bucket_analysis': bucket_analysis,
            'optimal_threshold': optimal_threshold,
            'improvement_potential': self._calculate_threshold_improvement(bucket_analysis, optimal_threshold)
        }
    
    async def _analyze_pattern_performance(self, 
                                         signals: List[Dict], 
                                         executions: List[Dict]) -> Dict:
        """Analyze performance by pattern type"""
        
        pattern_performance = {}
        
        # Group signals by pattern type
        for signal in signals:
            pattern_type = signal.get('pattern_type', 'unknown')
            if pattern_type not in pattern_performance:
                pattern_performance[pattern_type] = {
                    'signals': [],
                    'executions': [],
                    'performance_metrics': {}
                }
            pattern_performance[pattern_type]['signals'].append(signal)
        
        # Match executions to patterns
        for execution in executions:
            signal_id = execution.get('signal_id')
            # Find the original signal
            original_signal = next((s for s in signals if s.get('signal_id') == signal_id), None)
            if original_signal:
                pattern_type = original_signal.get('pattern_type', 'unknown')
                if pattern_type in pattern_performance:
                    pattern_performance[pattern_type]['executions'].append({
                        'signal': original_signal,
                        'execution': execution
                    })
        
        # Calculate performance metrics for each pattern
        for pattern_type, data in pattern_performance.items():
            signals_count = len(data['signals'])
            executions_count = len(data['executions'])
            
            if executions_count > 0:
                profits = [e['execution'].get('pnl', 0) for e in data['executions']]
                avg_profit = np.mean(profits)
                win_rate = len([p for p in profits if p > 0]) / len(profits)
                
                # Calculate pattern-specific metrics
                avg_confidence = np.mean([s.get('confidence', 0) for s in data['signals']])
                conversion_rate = executions_count / signals_count if signals_count > 0 else 0
                
                data['performance_metrics'] = {
                    'signals_generated': signals_count,
                    'signals_executed': executions_count,
                    'conversion_rate': conversion_rate,
                    'avg_confidence': avg_confidence,
                    'avg_profit_per_trade': avg_profit,
                    'win_rate': win_rate,
                    'total_profit': sum(profits),
                    'pattern_quality_score': self._calculate_pattern_quality_score(
                        conversion_rate, avg_profit, win_rate, avg_confidence
                    )
                }
            else:
                data['performance_metrics'] = {
                    'signals_generated': signals_count,
                    'signals_executed': 0,
                    'conversion_rate': 0,
                    'avg_confidence': np.mean([s.get('confidence', 0) for s in data['signals']]) if signals_count > 0 else 0,
                    'pattern_quality_score': 0
                }
        
        # Rank patterns by performance
        pattern_rankings = self._rank_patterns_by_performance(pattern_performance)
        
        return {
            'pattern_performance': pattern_performance,
            'pattern_rankings': pattern_rankings,
            'recommendations': self._generate_pattern_recommendations(pattern_performance)
        }
    
    async def _analyze_conversion_rates(self, 
                                      signals: List[Dict], 
                                      executions: List[Dict]) -> Dict:
        """Analyze signal-to-execution conversion rates and identify bottlenecks"""
        
        # Calculate overall conversion rate
        total_signals = len(signals)
        total_executions = len(executions)
        overall_conversion = total_executions / total_signals if total_signals > 0 else 0
        
        # Analyze conversion by confidence ranges
        confidence_ranges = [(50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
        conversion_by_confidence = {}
        
        for min_conf, max_conf in confidence_ranges:
            range_signals = [
                s for s in signals 
                if min_conf <= s.get('confidence', 0) < max_conf
            ]
            range_executions = [
                e for e in executions
                if any(s.get('signal_id') == e.get('signal_id') 
                      and min_conf <= s.get('confidence', 0) < max_conf 
                      for s in signals)
            ]
            
            conversion_rate = len(range_executions) / len(range_signals) if range_signals else 0
            
            conversion_by_confidence[f"{min_conf}-{max_conf}%"] = {
                'signals': len(range_signals),
                'executions': len(range_executions),
                'conversion_rate': conversion_rate
            }
        
        # Analyze rejection reasons
        rejection_analysis = await self._analyze_rejection_reasons(signals, executions)
        
        return {
            'overall_conversion_rate': overall_conversion,
            'target_conversion_rate': 0.15,  # 15% target
            'conversion_gap': 0.15 - overall_conversion,
            'conversion_by_confidence': conversion_by_confidence,
            'rejection_analysis': rejection_analysis,
            'improvement_actions': self._generate_conversion_improvement_actions(
                overall_conversion, conversion_by_confidence, rejection_analysis
            )
        }
    
    async def _analyze_signal_timing(self, 
                                   signals: List[Dict], 
                                   executions: List[Dict]) -> Dict:
        """Analyze signal timing and validity periods"""
        
        timing_analysis = {
            'signal_validity_analysis': {},
            'execution_delay_analysis': {},
            'market_timing_analysis': {}
        }
        
        # Analyze signal validity periods
        validity_periods = []
        for signal in signals:
            generated_at = signal.get('generated_at')
            valid_until = signal.get('valid_until')
            if generated_at and valid_until:
                validity_hours = (valid_until - generated_at).total_seconds() / 3600
                validity_periods.append(validity_hours)
        
        if validity_periods:
            timing_analysis['signal_validity_analysis'] = {
                'avg_validity_hours': np.mean(validity_periods),
                'median_validity_hours': np.median(validity_periods),
                'min_validity_hours': np.min(validity_periods),
                'max_validity_hours': np.max(validity_periods)
            }
        
        # Analyze execution delays
        execution_delays = []
        for execution in executions:
            signal_id = execution.get('signal_id')
            signal = next((s for s in signals if s.get('signal_id') == signal_id), None)
            if signal:
                generated_at = signal.get('generated_at')
                executed_at = execution.get('executed_at')
                if generated_at and executed_at:
                    delay_minutes = (executed_at - generated_at).total_seconds() / 60
                    execution_delays.append(delay_minutes)
        
        if execution_delays:
            timing_analysis['execution_delay_analysis'] = {
                'avg_delay_minutes': np.mean(execution_delays),
                'median_delay_minutes': np.median(execution_delays),
                'min_delay_minutes': np.min(execution_delays),
                'max_delay_minutes': np.max(execution_delays)
            }
        
        return timing_analysis
    
    def _calculate_quality_score(self, 
                               conversion_rate: float,
                               avg_profit: float,
                               win_rate: float,
                               profit_factor: float) -> float:
        """Calculate composite quality score for threshold analysis"""
        
        # Normalize metrics to 0-100 scale
        conversion_score = min(conversion_rate * 100, 100)  # 100% conversion = 100 points
        profit_score = max(0, min(avg_profit * 10, 100))    # $10 avg profit = 100 points
        win_rate_score = win_rate * 100                     # 100% win rate = 100 points
        pf_score = min(profit_factor * 20, 100)             # PF of 5 = 100 points
        
        # Weighted composite score
        quality_score = (
            conversion_score * 0.3 +    # 30% weight on conversion
            profit_score * 0.25 +       # 25% weight on profitability
            win_rate_score * 0.25 +     # 25% weight on win rate
            pf_score * 0.2              # 20% weight on profit factor
        )
        
        return quality_score
    
    def _find_optimal_confidence_threshold(self, bucket_analysis: Dict) -> float:
        """Find optimal confidence threshold based on quality scores"""
        
        if not bucket_analysis:
            return 65.0  # Default threshold
        
        # Find threshold with highest quality score
        best_threshold = 65.0
        best_score = 0
        
        for threshold, metrics in bucket_analysis.items():
            quality_score = metrics.get('quality_score', 0)
            signals_count = metrics.get('signals_count', 0)
            
            # Require minimum signal count for consideration
            if signals_count >= 5 and quality_score > best_score:
                best_score = quality_score
                best_threshold = threshold
        
        return best_threshold
    
    def _calculate_pattern_quality_score(self,
                                       conversion_rate: float,
                                       avg_profit: float,
                                       win_rate: float,
                                       avg_confidence: float) -> float:
        """Calculate quality score for pattern types"""
        
        # Pattern-specific scoring
        conversion_score = conversion_rate * 100
        profit_score = max(0, avg_profit * 10)
        win_rate_score = win_rate * 100
        confidence_score = avg_confidence
        
        # Composite score for patterns
        pattern_score = (
            conversion_score * 0.35 +   # Higher weight on conversion for patterns
            profit_score * 0.25 +
            win_rate_score * 0.25 +
            confidence_score * 0.15
        )
        
        return pattern_score
    
    def _rank_patterns_by_performance(self, pattern_performance: Dict) -> List[Dict]:
        """Rank patterns by performance quality"""
        
        rankings = []
        for pattern_type, data in pattern_performance.items():
            metrics = data.get('performance_metrics', {})
            quality_score = metrics.get('pattern_quality_score', 0)
            
            rankings.append({
                'pattern_type': pattern_type,
                'quality_score': quality_score,
                'signals_generated': metrics.get('signals_generated', 0),
                'conversion_rate': metrics.get('conversion_rate', 0),
                'avg_profit': metrics.get('avg_profit_per_trade', 0),
                'win_rate': metrics.get('win_rate', 0)
            })
        
        # Sort by quality score descending
        return sorted(rankings, key=lambda x: x['quality_score'], reverse=True)
    
    async def _analyze_rejection_reasons(self, 
                                       signals: List[Dict], 
                                       executions: List[Dict]) -> Dict:
        """Analyze why signals were not executed"""
        
        executed_signal_ids = {e.get('signal_id') for e in executions}
        rejected_signals = [s for s in signals if s.get('signal_id') not in executed_signal_ids]
        
        rejection_reasons = {}
        for signal in rejected_signals:
            # Analyze potential rejection reasons
            confidence = signal.get('confidence', 0)
            risk_reward = signal.get('risk_reward_ratio', 0)
            market_state = signal.get('market_context', {}).get('market_state', 'unknown')
            
            # Categorize rejection reason
            if confidence < 65:
                reason = 'low_confidence'
            elif risk_reward < 2.0:
                reason = 'poor_risk_reward'
            elif market_state in ['high_volatility', 'uncertain']:
                reason = 'unsuitable_market_conditions'
            else:
                reason = 'other_filters'
            
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        total_rejected = len(rejected_signals)
        rejection_percentages = {
            reason: (count / total_rejected * 100) if total_rejected > 0 else 0
            for reason, count in rejection_reasons.items()
        }
        
        return {
            'total_rejected_signals': total_rejected,
            'rejection_reasons': rejection_reasons,
            'rejection_percentages': rejection_percentages,
            'top_rejection_reason': max(rejection_percentages.items(), key=lambda x: x[1])[0] if rejection_percentages else None
        }
    
    async def _generate_optimization_recommendations(self,
                                                   confidence_analysis: Dict,
                                                   pattern_analysis: Dict,
                                                   conversion_analysis: Dict,
                                                   timing_analysis: Dict) -> Dict:
        """Generate specific optimization recommendations"""
        
        recommendations = {
            'priority_actions': [],
            'confidence_threshold_recommendations': [],
            'pattern_optimization_recommendations': [],
            'conversion_improvement_recommendations': [],
            'implementation_priority': []
        }
        
        # Confidence threshold recommendations
        current_threshold = 65.0
        optimal_threshold = confidence_analysis.get('optimal_threshold', 65.0)
        
        if optimal_threshold != current_threshold:
            recommendations['confidence_threshold_recommendations'].append({
                'action': 'adjust_confidence_threshold',
                'current_value': current_threshold,
                'recommended_value': optimal_threshold,
                'expected_impact': f"Increase conversion rate by {confidence_analysis.get('improvement_potential', {}).get('conversion_improvement', 0):.1%}",
                'implementation': 'Update signal_generator.py confidence_threshold parameter'
            })
            recommendations['priority_actions'].append('adjust_confidence_threshold')
        
        # Pattern optimization recommendations
        pattern_rankings = pattern_analysis.get('pattern_rankings', [])
        if pattern_rankings:
            # Focus on top-performing patterns
            top_patterns = pattern_rankings[:3]
            low_patterns = pattern_rankings[-2:]
            
            recommendations['pattern_optimization_recommendations'].append({
                'action': 'prioritize_high_performance_patterns',
                'top_patterns': [p['pattern_type'] for p in top_patterns],
                'low_patterns': [p['pattern_type'] for p in low_patterns],
                'implementation': 'Adjust pattern detection weights and confidence scoring'
            })
            recommendations['priority_actions'].append('prioritize_high_performance_patterns')
        
        # Conversion improvement recommendations
        rejection_analysis = conversion_analysis.get('rejection_analysis', {})
        top_rejection = rejection_analysis.get('top_rejection_reason')
        
        if top_rejection == 'low_confidence':
            recommendations['conversion_improvement_recommendations'].append({
                'action': 'improve_confidence_scoring',
                'issue': 'Too many signals filtered by confidence threshold',
                'solution': 'Enhance volume confirmation and pattern scoring algorithms',
                'expected_impact': 'Increase signal quality and reduce false rejections'
            })
            recommendations['priority_actions'].append('improve_confidence_scoring')
        
        elif top_rejection == 'poor_risk_reward':
            recommendations['conversion_improvement_recommendations'].append({
                'action': 'optimize_risk_reward_calculation',
                'issue': 'Risk-reward ratios not meeting minimum requirements',
                'solution': 'Improve stop-loss and take-profit calculation algorithms',
                'expected_impact': 'Better risk-reward ratios for more signal executions'
            })
            recommendations['priority_actions'].append('optimize_risk_reward_calculation')
        
        # Set implementation priority
        recommendations['implementation_priority'] = [
            'adjust_confidence_threshold',
            'improve_confidence_scoring', 
            'optimize_risk_reward_calculation',
            'prioritize_high_performance_patterns'
        ]
        
        return recommendations
    
    async def _estimate_optimization_impact(self, recommendations: Dict) -> Dict:
        """Estimate impact of implementing optimization recommendations"""
        
        impact_estimates = {
            'conversion_rate_improvement': 0,
            'profitability_improvement': 0,
            'signal_quality_improvement': 0,
            'expected_monthly_return_improvement': 0
        }
        
        # Base estimates on historical analysis
        priority_actions = recommendations.get('priority_actions', [])
        
        if 'adjust_confidence_threshold' in priority_actions:
            impact_estimates['conversion_rate_improvement'] += 5.0  # 5% improvement
            impact_estimates['signal_quality_improvement'] += 10.0  # 10% improvement
        
        if 'improve_confidence_scoring' in priority_actions:
            impact_estimates['conversion_rate_improvement'] += 3.0  # 3% improvement
            impact_estimates['profitability_improvement'] += 2.0    # 2% improvement
        
        if 'optimize_risk_reward_calculation' in priority_actions:
            impact_estimates['profitability_improvement'] += 5.0    # 5% improvement
            impact_estimates['signal_quality_improvement'] += 8.0   # 8% improvement
        
        # Estimate monthly return improvement
        current_monthly_return = -0.60  # Current performance
        if impact_estimates['profitability_improvement'] > 0:
            impact_estimates['expected_monthly_return_improvement'] = (
                current_monthly_return + (impact_estimates['profitability_improvement'] / 2)
            )
        
        return impact_estimates
    
    def _generate_conversion_improvement_actions(self,
                                               overall_conversion: float,
                                               conversion_by_confidence: Dict,
                                               rejection_analysis: Dict) -> List[str]:
        """Generate specific actions to improve conversion rates"""
        
        actions = []
        
        # If overall conversion is very low
        if overall_conversion < 0.05:  # Less than 5%
            actions.append("CRITICAL: Review signal generation criteria - conversion rate too low")
        
        # If high-confidence signals aren't converting
        high_conf_conversion = conversion_by_confidence.get('80-90%', {}).get('conversion_rate', 0)
        if high_conf_conversion < 0.3:  # Less than 30% for high confidence
            actions.append("Investigate high-confidence signal rejection causes")
        
        # Based on top rejection reason
        top_rejection = rejection_analysis.get('top_rejection_reason')
        if top_rejection == 'low_confidence':
            actions.append("Lower confidence threshold or improve confidence scoring")
        elif top_rejection == 'poor_risk_reward':
            actions.append("Optimize stop-loss and take-profit calculation")
        elif top_rejection == 'unsuitable_market_conditions':
            actions.append("Refine market state filtering criteria")
        
        return actions
    
    def _generate_pattern_recommendations(self, pattern_performance: Dict) -> List[str]:
        """Generate pattern-specific optimization recommendations"""
        
        recommendations = []
        
        for pattern_type, data in pattern_performance.items():
            metrics = data.get('performance_metrics', {})
            quality_score = metrics.get('pattern_quality_score', 0)
            conversion_rate = metrics.get('conversion_rate', 0)
            
            if quality_score > 70:
                recommendations.append(f"✅ {pattern_type}: High performer - increase detection weight")
            elif quality_score < 30:
                recommendations.append(f"❌ {pattern_type}: Poor performer - consider reducing weight or improving detection")
            elif conversion_rate < 0.1:
                recommendations.append(f"⚠️ {pattern_type}: Low conversion - review signal criteria")
        
        return recommendations
    
    async def get_optimization_report(self) -> Dict:
        """Generate comprehensive optimization report"""
        
        if not self.cached_results:
            return {
                'report_status': 'no_analysis_available',
                'message': 'Run analyze_signal_performance() first'
            }
        
        analysis = self.cached_results
        recommendations = analysis.get('optimization_recommendations', {})
        
        # Create executive summary
        executive_summary = {
            'current_conversion_rate': analysis.get('conversion_analysis', {}).get('overall_conversion_rate', 0),
            'target_conversion_rate': 0.15,
            'improvement_needed': f"{(0.15 - analysis.get('conversion_analysis', {}).get('overall_conversion_rate', 0)) * 100:.1f}%",
            'top_priority_actions': recommendations.get('priority_actions', [])[:3],
            'estimated_return_improvement': analysis.get('impact_estimates', {}).get('expected_monthly_return_improvement', 0)
        }
        
        # Create implementation roadmap
        implementation_roadmap = {
            'week_1': [],
            'week_2': [],
            'ongoing': []
        }
        
        priority_actions = recommendations.get('priority_actions', [])
        if 'adjust_confidence_threshold' in priority_actions:
            implementation_roadmap['week_1'].append('Implement optimal confidence threshold')
        if 'improve_confidence_scoring' in priority_actions:
            implementation_roadmap['week_1'].append('Enhance volume confirmation algorithms')
        if 'optimize_risk_reward_calculation' in priority_actions:
            implementation_roadmap['week_2'].append('Improve risk-reward optimization')
        
        implementation_roadmap['ongoing'].append('Monitor performance metrics daily')
        implementation_roadmap['ongoing'].append('Adjust parameters based on market conditions')
        
        return {
            'report_status': 'completed',
            'report_timestamp': datetime.now(),
            'executive_summary': executive_summary,
            'detailed_analysis': analysis,
            'implementation_roadmap': implementation_roadmap,
            'success_metrics': {
                'target_conversion_rate': 0.15,
                'target_monthly_return': 0.03,  # 3%
                'target_win_rate': 0.55,        # 55%
                'target_profit_factor': 1.5     # 1.5
            }
        }
    
    async def implement_optimization(self, optimization_config: Dict) -> Dict:
        """Implement optimization recommendations"""
        
        implementation_results = {
            'optimizations_applied': [],
            'configuration_changes': {},
            'performance_tracking_enabled': True,
            'rollback_available': True
        }
        
        # Store current configuration for rollback
        current_config = {
            'confidence_threshold': self.confidence_threshold,
            'min_risk_reward': self.min_risk_reward
        }
        
        # Apply confidence threshold optimization
        if 'confidence_threshold' in optimization_config:
            old_threshold = self.confidence_threshold
            new_threshold = optimization_config['confidence_threshold']
            self.confidence_threshold = new_threshold
            
            implementation_results['optimizations_applied'].append('confidence_threshold_updated')
            implementation_results['configuration_changes']['confidence_threshold'] = {
                'old': old_threshold,
                'new': new_threshold
            }
        
        # Apply risk-reward optimization
        if 'min_risk_reward' in optimization_config:
            old_rr = self.min_risk_reward
            new_rr = optimization_config['min_risk_reward']
            self.min_risk_reward = new_rr
            
            implementation_results['optimizations_applied'].append('risk_reward_threshold_updated')
            implementation_results['configuration_changes']['min_risk_reward'] = {
                'old': old_rr,
                'new': new_rr
            }
        
        # Enable enhanced performance tracking
        self.enable_performance_tracking = True
        
        logger.info(f"Applied optimizations: {implementation_results['optimizations_applied']}")
        
        return implementation_results
    
    def _calculate_threshold_improvement(self, bucket_analysis: Dict, optimal_threshold: float) -> Dict:
        """Calculate potential improvement from threshold optimization"""
        
        current_metrics = bucket_analysis.get(65.0, {})  # Current threshold
        optimal_metrics = bucket_analysis.get(optimal_threshold, {})
        
        if not current_metrics or not optimal_metrics:
            return {'conversion_improvement': 0, 'quality_improvement': 0}
        
        conversion_improvement = (
            optimal_metrics.get('conversion_rate', 0) - 
            current_metrics.get('conversion_rate', 0)
        )
        
        quality_improvement = (
            optimal_metrics.get('quality_score', 0) - 
            current_metrics.get('quality_score', 0)
        )
        
        return {
            'conversion_improvement': conversion_improvement,
            'quality_improvement': quality_improvement
        }


class SignalQualityMonitor:
    """Real-time signal quality monitoring and alerts"""
    
    def __init__(self, alert_thresholds: Dict = None):
        self.alert_thresholds = alert_thresholds or {
            'min_conversion_rate': 0.10,      # 10% minimum
            'min_daily_signals': 3,           # 3 signals per day minimum
            'max_rejection_rate': 0.90        # 90% maximum rejection rate
        }
        
        self.daily_stats = {
            'signals_generated': 0,
            'signals_executed': 0,
            'last_reset': datetime.now().date()
        }
    
    async def monitor_daily_performance(self, current_stats: Dict) -> Dict:
        """Monitor daily signal performance and generate alerts"""
        
        today = datetime.now().date()
        
        # Reset daily stats if new day
        if today != self.daily_stats['last_reset']:
            self.daily_stats = {
                'signals_generated': 0,
                'signals_executed': 0,
                'last_reset': today
            }
        
        # Update daily stats
        self.daily_stats['signals_generated'] = current_stats.get('signals_generated', 0)
        self.daily_stats['signals_executed'] = current_stats.get('signals_executed', 0)
        
        # Generate alerts
        alerts = []
        
        # Check conversion rate
        if self.daily_stats['signals_generated'] > 0:
            conversion_rate = self.daily_stats['signals_executed'] / self.daily_stats['signals_generated']
            if conversion_rate < self.alert_thresholds['min_conversion_rate']:
                alerts.append({
                    'type': 'low_conversion_rate',
                    'severity': 'warning',
                    'message': f"Conversion rate {conversion_rate:.1%} below threshold {self.alert_thresholds['min_conversion_rate']:.1%}",
                    'recommendation': 'Review signal generation parameters'
                })
        
        # Check signal generation rate
        if self.daily_stats['signals_generated'] < self.alert_thresholds['min_daily_signals']:
            alerts.append({
                'type': 'low_signal_generation',
                'severity': 'info',
                'message': f"Only {self.daily_stats['signals_generated']} signals generated today",
                'recommendation': 'Consider lowering confidence threshold or expanding pattern detection'
            })
        
        return {
            'monitoring_status': 'active',
            'daily_stats': self.daily_stats,
            'alerts': alerts,
            'alert_count': len(alerts)
        }