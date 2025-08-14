"""
Improvement Suggestion Engine

AI-powered system that analyzes trading performance, market conditions, and 
system behavior to automatically generate actionable improvement suggestions.
This is the "brain" that identifies optimization opportunities.

Key Features:
- Performance pattern analysis
- Market regime adaptation suggestions
- Parameter optimization recommendations
- Strategy enhancement ideas
- Risk management improvements
- Data-driven prioritization
- Evidence-based rationale
- Implementation complexity assessment
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import asdict
import json
from collections import defaultdict

from .models import (
    ImprovementSuggestion, ImprovementType, Priority, RiskLevel, 
    ImplementationComplexity, SuggestionStatus, PerformanceMetrics
)

# Import data interfaces
from ...src.shared.python_utils.data_interfaces import (
    PerformanceDataInterface, MockPerformanceDataProvider,
    TradeDataInterface, MockTradeDataProvider,
    MarketDataInterface, MockMarketDataProvider
)

logger = logging.getLogger(__name__)


class ImprovementSuggestionEngine:
    """
    AI-powered improvement suggestion engine.
    
    This engine analyzes various data sources to identify improvement opportunities
    and generates prioritized, actionable suggestions for the trading system.
    It uses multiple analysis techniques including pattern recognition,
    statistical analysis, and machine learning approaches.
    """
    
    def __init__(self,
                 performance_data_provider: Optional[PerformanceDataInterface] = None,
                 trade_data_provider: Optional[TradeDataInterface] = None,
                 market_data_provider: Optional[MarketDataInterface] = None):
        
        # Data providers
        self.performance_data_provider = performance_data_provider or MockPerformanceDataProvider()
        self.trade_data_provider = trade_data_provider or MockTradeDataProvider()
        self.market_data_provider = market_data_provider or MockMarketDataProvider()
        
        # Analysis configuration
        self.config = {
            # Analysis periods
            'short_term_days': 7,
            'medium_term_days': 30,
            'long_term_days': 90,
            
            # Performance thresholds
            'underperformance_threshold': Decimal('-0.02'),  # 2% underperformance
            'improvement_opportunity_threshold': Decimal('0.05'),  # 5% potential improvement
            'min_trade_sample': 50,  # Minimum trades for analysis
            
            # Suggestion limits
            'max_suggestions_per_cycle': 5,
            'min_confidence_threshold': 0.6,  # 60% confidence minimum
            'suggestion_cooldown_hours': 24,  # Hours between similar suggestions
            
            # Analysis weights
            'performance_weight': 0.4,
            'risk_weight': 0.3,
            'market_adaptation_weight': 0.2,
            'implementation_weight': 0.1
        }
        
        # Suggestion tracking
        self._suggestion_history: List[ImprovementSuggestion] = []
        self._analysis_cache: Dict[str, Any] = {}
        self._last_analysis_time = None
        
        # Pattern recognition models
        self._performance_patterns = {}
        self._market_patterns = {}
        
        logger.info("Improvement Suggestion Engine initialized")
    
    async def generate_suggestions(self) -> List[ImprovementSuggestion]:
        """
        Generate improvement suggestions based on comprehensive analysis.
        
        Returns:
            List of prioritized improvement suggestions
        """
        try:
            logger.info("Starting improvement suggestion generation")
            
            # Perform comprehensive analysis
            analysis_results = await self._perform_comprehensive_analysis()
            
            # Generate suggestions from analysis
            suggestions = await self._generate_suggestions_from_analysis(analysis_results)
            
            # Filter and prioritize suggestions
            filtered_suggestions = await self._filter_and_prioritize_suggestions(suggestions)
            
            # Update suggestion history
            self._suggestion_history.extend(filtered_suggestions)
            
            # Cache analysis results
            self._analysis_cache['last_analysis'] = analysis_results
            self._last_analysis_time = datetime.utcnow()
            
            logger.info(f"Generated {len(filtered_suggestions)} improvement suggestions")
            return filtered_suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate improvement suggestions: {e}")
            return []
    
    async def _perform_comprehensive_analysis(self) -> Dict[str, Any]:
        """Perform comprehensive analysis across all data sources"""
        
        analysis_results = {
            'timestamp': datetime.utcnow(),
            'performance_analysis': {},
            'trade_pattern_analysis': {},
            'market_condition_analysis': {},
            'risk_analysis': {},
            'opportunity_analysis': {}
        }
        
        try:
            # Performance analysis
            analysis_results['performance_analysis'] = await self._analyze_performance_trends()
            
            # Trade pattern analysis
            analysis_results['trade_pattern_analysis'] = await self._analyze_trade_patterns()
            
            # Market condition analysis
            analysis_results['market_condition_analysis'] = await self._analyze_market_conditions()
            
            # Risk analysis
            analysis_results['risk_analysis'] = await self._analyze_risk_patterns()
            
            # Opportunity identification
            analysis_results['opportunity_analysis'] = await self._identify_improvement_opportunities()
            
            logger.info("Comprehensive analysis completed")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Comprehensive analysis failed: {e}")
            return analysis_results
    
    async def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends across different time periods"""
        
        analysis = {
            'short_term_trend': {},
            'medium_term_trend': {},
            'long_term_trend': {},
            'performance_degradation': [],
            'underperforming_metrics': [],
            'seasonal_patterns': {}
        }
        
        try:
            # Get performance data for different periods
            periods = {
                'short_term': self.config['short_term_days'],
                'medium_term': self.config['medium_term_days'],
                'long_term': self.config['long_term_days']
            }
            
            for period_name, days in periods.items():
                perf_data = await self.performance_data_provider.get_system_performance('daily', days)
                
                if perf_data:
                    trend_analysis = await self._calculate_performance_trend(perf_data)
                    analysis[f'{period_name}_trend'] = trend_analysis
                    
                    # Identify performance issues
                    if trend_analysis.get('trend_direction') == 'declining':
                        analysis['performance_degradation'].append({
                            'period': period_name,
                            'decline_rate': trend_analysis.get('trend_slope', 0),
                            'severity': self._assess_decline_severity(trend_analysis)
                        })
            
            # Identify underperforming metrics
            analysis['underperforming_metrics'] = await self._identify_underperforming_metrics()
            
            # Detect seasonal patterns
            analysis['seasonal_patterns'] = await self._detect_seasonal_patterns()
            
        except Exception as e:
            logger.error(f"Performance trend analysis failed: {e}")
        
        return analysis
    
    async def _calculate_performance_trend(self, performance_data: PerformanceMetrics) -> Dict[str, Any]:
        """Calculate performance trend from metrics data"""
        
        # Mock implementation - real version would analyze time series data
        trend_analysis = {
            'trend_direction': 'stable',  # stable, improving, declining
            'trend_slope': 0.0,
            'trend_confidence': 0.5,
            'volatility': float(performance_data.volatility) if performance_data.volatility else 0.1,
            'consistency': 0.7,  # Consistency of performance
            'recent_performance': float(performance_data.expectancy) if performance_data.expectancy else 0.0
        }
        
        # Simulate trend detection
        if performance_data.expectancy and performance_data.expectancy < Decimal('-0.01'):
            trend_analysis['trend_direction'] = 'declining'
            trend_analysis['trend_slope'] = float(performance_data.expectancy)
        elif performance_data.expectancy and performance_data.expectancy > Decimal('0.02'):
            trend_analysis['trend_direction'] = 'improving'
            trend_analysis['trend_slope'] = float(performance_data.expectancy)
        
        return trend_analysis
    
    def _assess_decline_severity(self, trend_analysis: Dict[str, Any]) -> str:
        """Assess the severity of performance decline"""
        
        slope = abs(trend_analysis.get('trend_slope', 0))
        
        if slope > 0.05:  # 5%+ decline
            return 'high'
        elif slope > 0.02:  # 2%+ decline
            return 'medium'
        else:
            return 'low'
    
    async def _identify_underperforming_metrics(self) -> List[Dict[str, Any]]:
        """Identify specific metrics that are underperforming"""
        
        underperforming = []
        
        try:
            # Get current system performance
            current_perf = await self.performance_data_provider.get_system_performance('weekly')
            
            if not current_perf:
                return underperforming
            
            # Check each metric against benchmarks
            metrics_to_check = [
                ('win_rate', current_perf.win_rate, Decimal('0.55')),  # 55% benchmark
                ('profit_factor', current_perf.profit_factor, Decimal('1.3')),  # 1.3 benchmark
                ('sharpe_ratio', current_perf.sharpe_ratio, Decimal('0.8')),  # 0.8 benchmark
                ('max_drawdown', current_perf.max_drawdown, Decimal('0.10'))  # 10% max (inverted)
            ]
            
            for metric_name, current_value, benchmark in metrics_to_check:
                if current_value is None:
                    continue
                
                if metric_name == 'max_drawdown':
                    # For drawdown, higher is worse
                    if current_value > benchmark:
                        underperforming.append({
                            'metric': metric_name,
                            'current_value': float(current_value),
                            'benchmark': float(benchmark),
                            'underperformance': float((current_value - benchmark) / benchmark),
                            'priority': 'high' if current_value > benchmark * Decimal('1.5') else 'medium'
                        })
                else:
                    # For other metrics, lower is worse
                    if current_value < benchmark:
                        underperforming.append({
                            'metric': metric_name,
                            'current_value': float(current_value),
                            'benchmark': float(benchmark),
                            'underperformance': float((benchmark - current_value) / benchmark),
                            'priority': 'high' if current_value < benchmark * Decimal('0.8') else 'medium'
                        })
            
        except Exception as e:
            logger.error(f"Failed to identify underperforming metrics: {e}")
        
        return underperforming
    
    async def _detect_seasonal_patterns(self) -> Dict[str, Any]:
        """Detect seasonal and time-based patterns"""
        
        patterns = {
            'time_of_day_patterns': {},
            'day_of_week_patterns': {},
            'monthly_patterns': {},
            'market_session_patterns': {}
        }
        
        try:
            # Get trade data for pattern analysis
            trades = await self.trade_data_provider.get_recent_trades(limit=1000)
            
            if len(trades) < 50:
                return patterns
            
            # Analyze time of day patterns
            hour_performance = defaultdict(list)
            for trade in trades:
                hour = trade.timestamp.hour
                hour_performance[hour].append(float(trade.pnl))
            
            # Calculate average performance by hour
            for hour, pnls in hour_performance.items():
                if len(pnls) >= 5:  # Minimum sample size
                    avg_pnl = np.mean(pnls)
                    patterns['time_of_day_patterns'][hour] = {
                        'average_pnl': avg_pnl,
                        'trade_count': len(pnls),
                        'performance_category': 'good' if avg_pnl > 10 else 'poor' if avg_pnl < -10 else 'neutral'
                    }
            
            # Similar analysis for day of week
            day_performance = defaultdict(list)
            for trade in trades:
                day = trade.timestamp.weekday()  # 0=Monday, 6=Sunday
                day_performance[day].append(float(trade.pnl))
            
            for day, pnls in day_performance.items():
                if len(pnls) >= 5:
                    avg_pnl = np.mean(pnls)
                    patterns['day_of_week_patterns'][day] = {
                        'average_pnl': avg_pnl,
                        'trade_count': len(pnls),
                        'performance_category': 'good' if avg_pnl > 10 else 'poor' if avg_pnl < -10 else 'neutral'
                    }
            
        except Exception as e:
            logger.error(f"Seasonal pattern detection failed: {e}")
        
        return patterns
    
    async def _analyze_trade_patterns(self) -> Dict[str, Any]:
        """Analyze trading patterns and behaviors"""
        
        analysis = {
            'entry_timing_patterns': {},
            'exit_timing_patterns': {},
            'position_sizing_patterns': {},
            'currency_pair_performance': {},
            'trade_duration_analysis': {}
        }
        
        try:
            # Get recent trades for analysis
            trades = await self.trade_data_provider.get_recent_trades(limit=500)
            
            if len(trades) < self.config['min_trade_sample']:
                logger.warning(f"Insufficient trade sample: {len(trades)} < {self.config['min_trade_sample']}")
                return analysis
            
            # Analyze currency pair performance
            pair_performance = defaultdict(lambda: {'trades': [], 'total_pnl': 0})
            
            for trade in trades:
                symbol = getattr(trade, 'symbol', 'UNKNOWN')
                pair_performance[symbol]['trades'].append(trade)
                pair_performance[symbol]['total_pnl'] += float(trade.pnl)
            
            # Calculate performance metrics by pair
            for symbol, data in pair_performance.items():
                if len(data['trades']) >= 10:  # Minimum sample
                    trades_data = data['trades']
                    win_rate = len([t for t in trades_data if t.pnl > 0]) / len(trades_data)
                    avg_pnl = data['total_pnl'] / len(trades_data)
                    
                    analysis['currency_pair_performance'][symbol] = {
                        'trade_count': len(trades_data),
                        'win_rate': win_rate,
                        'average_pnl': avg_pnl,
                        'total_pnl': data['total_pnl'],
                        'performance_category': 'strong' if avg_pnl > 15 else 'weak' if avg_pnl < -5 else 'moderate'
                    }
            
            # Analyze trade duration patterns
            durations = []
            for trade in trades:
                if hasattr(trade, 'exit_time') and hasattr(trade, 'entry_time'):
                    duration = (trade.exit_time - trade.entry_time).total_seconds() / 3600  # Hours
                    durations.append(duration)
            
            if durations:
                analysis['trade_duration_analysis'] = {
                    'average_duration_hours': np.mean(durations),
                    'median_duration_hours': np.median(durations),
                    'std_duration_hours': np.std(durations),
                    'short_trades_performance': await self._analyze_duration_performance(trades, 'short'),
                    'long_trades_performance': await self._analyze_duration_performance(trades, 'long')
                }
            
        except Exception as e:
            logger.error(f"Trade pattern analysis failed: {e}")
        
        return analysis
    
    async def _analyze_duration_performance(self, trades: List, duration_type: str) -> Dict[str, Any]:
        """Analyze performance by trade duration"""
        
        # Define duration thresholds (in hours)
        short_threshold = 4
        long_threshold = 24
        
        if duration_type == 'short':
            filtered_trades = [t for t in trades if hasattr(t, 'exit_time') and 
                             (t.exit_time - t.entry_time).total_seconds() / 3600 <= short_threshold]
        else:
            filtered_trades = [t for t in trades if hasattr(t, 'exit_time') and 
                             (t.exit_time - t.entry_time).total_seconds() / 3600 >= long_threshold]
        
        if not filtered_trades:
            return {'trade_count': 0}
        
        win_rate = len([t for t in filtered_trades if t.pnl > 0]) / len(filtered_trades)
        avg_pnl = np.mean([float(t.pnl) for t in filtered_trades])
        
        return {
            'trade_count': len(filtered_trades),
            'win_rate': win_rate,
            'average_pnl': avg_pnl,
            'performance_category': 'good' if avg_pnl > 10 else 'poor' if avg_pnl < -10 else 'neutral'
        }
    
    async def _analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze market conditions and adaptation opportunities"""
        
        analysis = {
            'current_market_regime': {},
            'regime_performance': {},
            'volatility_analysis': {},
            'correlation_analysis': {},
            'adaptation_opportunities': []
        }
        
        try:
            # Get market data for major pairs
            major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']
            
            for symbol in major_pairs:
                try:
                    market_data = await self.market_data_provider.get_market_data_point(symbol)
                    regime_data = await self.market_data_provider.get_regime_analysis(symbol)
                    
                    if market_data and regime_data:
                        analysis['current_market_regime'][symbol] = {
                            'regime_type': regime_data.regime_type,
                            'confidence': regime_data.confidence,
                            'volatility': float(market_data.volatility),
                            'trend_strength': float(market_data.trend_strength)
                        }
                        
                        # Analyze performance in current regime
                        regime_performance = await self._analyze_regime_performance(symbol, regime_data.regime_type)
                        analysis['regime_performance'][symbol] = regime_performance
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze market conditions for {symbol}: {e}")
            
            # Identify adaptation opportunities
            analysis['adaptation_opportunities'] = await self._identify_market_adaptation_opportunities(analysis)
            
        except Exception as e:
            logger.error(f"Market condition analysis failed: {e}")
        
        return analysis
    
    async def _analyze_regime_performance(self, symbol: str, regime_type: str) -> Dict[str, Any]:
        """Analyze trading performance in specific market regime"""
        
        # Mock implementation - real version would filter trades by regime
        performance = {
            'regime_type': regime_type,
            'trade_count': np.random.randint(20, 100),
            'win_rate': 0.45 + np.random.random() * 0.2,  # 45-65%
            'average_pnl': np.random.normal(5, 15),  # Variable performance
            'performance_category': 'neutral'
        }
        
        # Categorize performance
        if performance['average_pnl'] > 15:
            performance['performance_category'] = 'strong'
        elif performance['average_pnl'] < -5:
            performance['performance_category'] = 'weak'
        
        return performance
    
    async def _identify_market_adaptation_opportunities(self, market_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify opportunities to adapt to market conditions"""
        
        opportunities = []
        
        try:
            # Check for poor performance in specific regimes
            for symbol, regime_perf in market_analysis.get('regime_performance', {}).items():
                if regime_perf.get('performance_category') == 'weak':
                    opportunities.append({
                        'type': 'regime_adaptation',
                        'symbol': symbol,
                        'regime': regime_perf.get('regime_type'),
                        'description': f"Poor performance in {regime_perf.get('regime_type')} markets for {symbol}",
                        'suggested_action': 'parameter_adjustment',
                        'priority': 'medium'
                    })
            
            # Check for high volatility adaptation needs
            for symbol, regime_data in market_analysis.get('current_market_regime', {}).items():
                if regime_data.get('volatility', 0) > 0.025:  # High volatility threshold
                    opportunities.append({
                        'type': 'volatility_adaptation',
                        'symbol': symbol,
                        'volatility': regime_data.get('volatility'),
                        'description': f"High volatility detected for {symbol}",
                        'suggested_action': 'risk_adjustment',
                        'priority': 'high'
                    })
            
        except Exception as e:
            logger.error(f"Failed to identify market adaptation opportunities: {e}")
        
        return opportunities
    
    async def _analyze_risk_patterns(self) -> Dict[str, Any]:
        """Analyze risk management patterns and issues"""
        
        analysis = {
            'drawdown_patterns': {},
            'risk_concentration': {},
            'correlation_risks': {},
            'risk_efficiency': {}
        }
        
        try:
            # Analyze drawdown patterns
            current_perf = await self.performance_data_provider.get_system_performance('monthly')
            
            if current_perf:
                analysis['drawdown_patterns'] = {
                    'current_drawdown': float(current_perf.max_drawdown),
                    'drawdown_frequency': 'monthly',  # Placeholder
                    'recovery_time': 'quick',  # Placeholder
                    'drawdown_severity': 'moderate' if current_perf.max_drawdown < Decimal('0.10') else 'high'
                }
                
                # Risk efficiency analysis
                if current_perf.sharpe_ratio and current_perf.volatility:
                    analysis['risk_efficiency'] = {
                        'risk_adjusted_return': float(current_perf.sharpe_ratio),
                        'volatility': float(current_perf.volatility),
                        'efficiency_category': 'good' if current_perf.sharpe_ratio > Decimal('0.8') else 'poor'
                    }
            
        except Exception as e:
            logger.error(f"Risk pattern analysis failed: {e}")
        
        return analysis
    
    async def _identify_improvement_opportunities(self) -> Dict[str, Any]:
        """Identify specific improvement opportunities from analysis"""
        
        opportunities = {
            'parameter_optimization': [],
            'strategy_enhancements': [],
            'risk_adjustments': [],
            'new_features': [],
            'algorithm_improvements': []
        }
        
        try:
            # Get current performance
            current_perf = await self.performance_data_provider.get_system_performance('weekly')
            
            if current_perf:
                # Parameter optimization opportunities
                if current_perf.win_rate < Decimal('0.55'):
                    opportunities['parameter_optimization'].append({
                        'area': 'entry_criteria',
                        'current_value': float(current_perf.win_rate),
                        'target_improvement': '5-10%',
                        'confidence': 0.7
                    })
                
                # Risk adjustment opportunities
                if current_perf.max_drawdown > Decimal('0.10'):
                    opportunities['risk_adjustments'].append({
                        'area': 'position_sizing',
                        'current_drawdown': float(current_perf.max_drawdown),
                        'target_reduction': '20-30%',
                        'confidence': 0.8
                    })
                
                # Strategy enhancement opportunities
                if current_perf.sharpe_ratio < Decimal('0.8'):
                    opportunities['strategy_enhancements'].append({
                        'area': 'exit_optimization',
                        'current_sharpe': float(current_perf.sharpe_ratio),
                        'target_improvement': '15-25%',
                        'confidence': 0.6
                    })
            
        except Exception as e:
            logger.error(f"Failed to identify improvement opportunities: {e}")
        
        return opportunities
    
    async def _generate_suggestions_from_analysis(self, analysis_results: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """Generate specific improvement suggestions from analysis results"""
        
        suggestions = []
        
        try:
            # Generate suggestions from performance analysis
            perf_suggestions = await self._generate_performance_suggestions(
                analysis_results.get('performance_analysis', {})
            )
            suggestions.extend(perf_suggestions)
            
            # Generate suggestions from trade patterns
            pattern_suggestions = await self._generate_pattern_suggestions(
                analysis_results.get('trade_pattern_analysis', {})
            )
            suggestions.extend(pattern_suggestions)
            
            # Generate suggestions from market analysis
            market_suggestions = await self._generate_market_suggestions(
                analysis_results.get('market_condition_analysis', {})
            )
            suggestions.extend(market_suggestions)
            
            # Generate suggestions from risk analysis
            risk_suggestions = await self._generate_risk_suggestions(
                analysis_results.get('risk_analysis', {})
            )
            suggestions.extend(risk_suggestions)
            
            # Generate suggestions from opportunities
            opportunity_suggestions = await self._generate_opportunity_suggestions(
                analysis_results.get('opportunity_analysis', {})
            )
            suggestions.extend(opportunity_suggestions)
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions from analysis: {e}")
        
        return suggestions
    
    async def _generate_performance_suggestions(self, performance_analysis: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """Generate suggestions from performance analysis"""
        
        suggestions = []
        
        try:
            # Suggestions for declining performance
            for degradation in performance_analysis.get('performance_degradation', []):
                if degradation['severity'] in ['medium', 'high']:
                    suggestion = ImprovementSuggestion(
                        suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
                        category='performance_recovery',
                        title=f"Address {degradation['period']} performance decline",
                        description=f"Performance has declined {abs(degradation['decline_rate']):.1%} over {degradation['period']}",
                        rationale="Sustained performance decline indicates need for parameter adjustment",
                        expected_impact='moderate' if degradation['severity'] == 'medium' else 'significant',
                        risk_level=RiskLevel.MEDIUM,
                        implementation_effort=ImplementationComplexity.MEDIUM,
                        priority=Priority.HIGH if degradation['severity'] == 'high' else Priority.MEDIUM,
                        priority_score=75.0 if degradation['severity'] == 'high' else 60.0,
                        evidence_strength='strong',
                        supporting_data=[degradation]
                    )
                    suggestions.append(suggestion)
            
            # Suggestions for underperforming metrics
            for metric_issue in performance_analysis.get('underperforming_metrics', []):
                if metric_issue['priority'] == 'high':
                    suggestion = ImprovementSuggestion(
                        suggestion_type=ImprovementType.ALGORITHM_ENHANCEMENT,
                        category=metric_issue['metric'],
                        title=f"Improve {metric_issue['metric']} performance",
                        description=f"{metric_issue['metric']} is {metric_issue['underperformance']:.1%} below benchmark",
                        rationale=f"Key performance metric significantly underperforming industry standards",
                        expected_impact='significant',
                        risk_level=RiskLevel.MEDIUM,
                        implementation_effort=ImplementationComplexity.MEDIUM,
                        priority=Priority.HIGH,
                        priority_score=80.0,
                        evidence_strength='strong',
                        supporting_data=[metric_issue]
                    )
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Failed to generate performance suggestions: {e}")
        
        return suggestions
    
    async def _generate_pattern_suggestions(self, pattern_analysis: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """Generate suggestions from trade pattern analysis"""
        
        suggestions = []
        
        try:
            # Currency pair performance suggestions
            for symbol, perf in pattern_analysis.get('currency_pair_performance', {}).items():
                if perf['performance_category'] == 'weak' and perf['trade_count'] >= 20:
                    suggestion = ImprovementSuggestion(
                        suggestion_type=ImprovementType.STRATEGY_MODIFICATION,
                        category='currency_pair_optimization',
                        title=f"Optimize {symbol} trading strategy",
                        description=f"{symbol} showing poor performance with {perf['average_pnl']:.1f} average PnL",
                        rationale="Currency pair underperforming with sufficient sample size",
                        expected_impact='moderate',
                        risk_level=RiskLevel.MEDIUM,
                        implementation_effort=ImplementationComplexity.MEDIUM,
                        priority=Priority.MEDIUM,
                        priority_score=65.0,
                        evidence_strength='strong',
                        supporting_data=[perf]
                    )
                    suggestions.append(suggestion)
            
            # Trade duration optimization
            duration_analysis = pattern_analysis.get('trade_duration_analysis', {})
            if duration_analysis:
                short_perf = duration_analysis.get('short_trades_performance', {})
                long_perf = duration_analysis.get('long_trades_performance', {})
                
                if (short_perf.get('performance_category') == 'good' and 
                    long_perf.get('performance_category') == 'poor'):
                    suggestion = ImprovementSuggestion(
                        suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
                        category='trade_duration',
                        title="Optimize for shorter trade durations",
                        description="Short duration trades outperforming long duration trades",
                        rationale="Data shows better performance with shorter holding periods",
                        expected_impact='moderate',
                        risk_level=RiskLevel.LOW,
                        implementation_effort=ImplementationComplexity.LOW,
                        priority=Priority.MEDIUM,
                        priority_score=55.0,
                        evidence_strength='moderate',
                        supporting_data=[short_perf, long_perf]
                    )
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Failed to generate pattern suggestions: {e}")
        
        return suggestions
    
    async def _generate_market_suggestions(self, market_analysis: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """Generate suggestions from market condition analysis"""
        
        suggestions = []
        
        try:
            # Market adaptation opportunities
            for opportunity in market_analysis.get('adaptation_opportunities', []):
                if opportunity['priority'] == 'high':
                    suggestion = ImprovementSuggestion(
                        suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
                        category='market_adaptation',
                        title=f"Adapt to {opportunity['type']} for {opportunity.get('symbol', 'system')}",
                        description=opportunity['description'],
                        rationale="Market conditions require strategy adaptation",
                        expected_impact='moderate',
                        risk_level=RiskLevel.MEDIUM,
                        implementation_effort=ImplementationComplexity.MEDIUM,
                        priority=Priority.HIGH,
                        priority_score=70.0,
                        evidence_strength='strong',
                        supporting_data=[opportunity]
                    )
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Failed to generate market suggestions: {e}")
        
        return suggestions
    
    async def _generate_risk_suggestions(self, risk_analysis: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """Generate suggestions from risk analysis"""
        
        suggestions = []
        
        try:
            # Drawdown improvement suggestions
            drawdown_patterns = risk_analysis.get('drawdown_patterns', {})
            if drawdown_patterns.get('drawdown_severity') == 'high':
                suggestion = ImprovementSuggestion(
                    suggestion_type=ImprovementType.RISK_ADJUSTMENT,
                    category='drawdown_control',
                    title="Implement enhanced drawdown control",
                    description=f"Current drawdown {drawdown_patterns.get('current_drawdown', 0):.1%} exceeds comfort zone",
                    rationale="High drawdown levels indicate need for improved risk management",
                    expected_impact='significant',
                    risk_level=RiskLevel.LOW,
                    implementation_effort=ImplementationComplexity.MEDIUM,
                    priority=Priority.HIGH,
                    priority_score=85.0,
                    evidence_strength='strong',
                    supporting_data=[drawdown_patterns]
                )
                suggestions.append(suggestion)
            
            # Risk efficiency improvements
            risk_efficiency = risk_analysis.get('risk_efficiency', {})
            if risk_efficiency.get('efficiency_category') == 'poor':
                suggestion = ImprovementSuggestion(
                    suggestion_type=ImprovementType.ALGORITHM_ENHANCEMENT,
                    category='risk_efficiency',
                    title="Improve risk-adjusted returns",
                    description=f"Sharpe ratio {risk_efficiency.get('risk_adjusted_return', 0):.2f} below optimal",
                    rationale="Poor risk efficiency indicates suboptimal risk/return balance",
                    expected_impact='moderate',
                    risk_level=RiskLevel.MEDIUM,
                    implementation_effort=ImplementationComplexity.MEDIUM,
                    priority=Priority.MEDIUM,
                    priority_score=65.0,
                    evidence_strength='moderate',
                    supporting_data=[risk_efficiency]
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Failed to generate risk suggestions: {e}")
        
        return suggestions
    
    async def _generate_opportunity_suggestions(self, opportunity_analysis: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """Generate suggestions from identified opportunities"""
        
        suggestions = []
        
        try:
            # Parameter optimization opportunities
            for opp in opportunity_analysis.get('parameter_optimization', []):
                if opp.get('confidence', 0) >= 0.6:
                    suggestion = ImprovementSuggestion(
                        suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
                        category=opp['area'],
                        title=f"Optimize {opp['area']} parameters",
                        description=f"Potential {opp['target_improvement']} improvement in {opp['area']}",
                        rationale="Statistical analysis indicates optimization opportunity",
                        expected_impact='moderate',
                        risk_level=RiskLevel.LOW,
                        implementation_effort=ImplementationComplexity.LOW,
                        priority=Priority.MEDIUM,
                        priority_score=60.0,
                        evidence_strength='moderate',
                        supporting_data=[opp]
                    )
                    suggestions.append(suggestion)
            
            # Risk adjustment opportunities
            for opp in opportunity_analysis.get('risk_adjustments', []):
                if opp.get('confidence', 0) >= 0.7:
                    suggestion = ImprovementSuggestion(
                        suggestion_type=ImprovementType.RISK_ADJUSTMENT,
                        category=opp['area'],
                        title=f"Adjust {opp['area']} for risk reduction",
                        description=f"Potential {opp['target_reduction']} reduction in risk",
                        rationale="Risk analysis shows opportunity for safer operations",
                        expected_impact='significant',
                        risk_level=RiskLevel.LOW,
                        implementation_effort=ImplementationComplexity.MEDIUM,
                        priority=Priority.HIGH,
                        priority_score=75.0,
                        evidence_strength='strong',
                        supporting_data=[opp]
                    )
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Failed to generate opportunity suggestions: {e}")
        
        return suggestions
    
    async def _filter_and_prioritize_suggestions(self, suggestions: List[ImprovementSuggestion]) -> List[ImprovementSuggestion]:
        """Filter and prioritize suggestions based on various criteria"""
        
        try:
            # Filter out duplicate suggestions
            unique_suggestions = await self._remove_duplicate_suggestions(suggestions)
            
            # Filter out suggestions too similar to recent ones
            recent_filtered = await self._filter_recent_suggestions(unique_suggestions)
            
            # Calculate final priority scores
            for suggestion in recent_filtered:
                suggestion.priority_score = await self._calculate_final_priority_score(suggestion)
            
            # Sort by priority score
            prioritized = sorted(recent_filtered, key=lambda s: s.priority_score, reverse=True)
            
            # Limit to max suggestions per cycle
            max_suggestions = self.config['max_suggestions_per_cycle']
            final_suggestions = prioritized[:max_suggestions]
            
            logger.info(f"Filtered {len(suggestions)} suggestions to {len(final_suggestions)} final suggestions")
            return final_suggestions
            
        except Exception as e:
            logger.error(f"Failed to filter and prioritize suggestions: {e}")
            return suggestions[:self.config['max_suggestions_per_cycle']]
    
    async def _remove_duplicate_suggestions(self, suggestions: List[ImprovementSuggestion]) -> List[ImprovementSuggestion]:
        """Remove duplicate suggestions"""
        
        seen_combinations = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            # Create a key based on type and category
            key = (suggestion.suggestion_type.value, suggestion.category)
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    async def _filter_recent_suggestions(self, suggestions: List[ImprovementSuggestion]) -> List[ImprovementSuggestion]:
        """Filter out suggestions too similar to recent ones"""
        
        cooldown_period = timedelta(hours=self.config['suggestion_cooldown_hours'])
        cutoff_time = datetime.utcnow() - cooldown_period
        
        # Get recent suggestions
        recent_suggestions = [
            s for s in self._suggestion_history
            if s.timestamp >= cutoff_time
        ]
        
        recent_categories = {(s.suggestion_type.value, s.category) for s in recent_suggestions}
        
        # Filter out suggestions in cooldown
        filtered = [
            s for s in suggestions
            if (s.suggestion_type.value, s.category) not in recent_categories
        ]
        
        return filtered
    
    async def _calculate_final_priority_score(self, suggestion: ImprovementSuggestion) -> float:
        """Calculate final priority score with weights"""
        
        # Base score from initial calculation
        base_score = suggestion.priority_score
        
        # Apply weights from configuration
        weights = self.config
        
        # Performance impact weight
        impact_multiplier = {
            'minor': 0.8,
            'moderate': 1.0,
            'significant': 1.3,
            'major': 1.5
        }.get(suggestion.expected_impact, 1.0)
        
        # Risk adjustment
        risk_adjustment = {
            RiskLevel.LOW: 1.1,
            RiskLevel.MEDIUM: 1.0,
            RiskLevel.HIGH: 0.8
        }.get(suggestion.risk_level, 1.0)
        
        # Implementation effort adjustment
        effort_adjustment = {
            ImplementationComplexity.LOW: 1.2,
            ImplementationComplexity.MEDIUM: 1.0,
            ImplementationComplexity.HIGH: 0.7
        }.get(suggestion.implementation_effort, 1.0)
        
        # Calculate final score
        final_score = (base_score * 
                      impact_multiplier * 
                      risk_adjustment * 
                      effort_adjustment)
        
        return min(100.0, max(0.0, final_score))
    
    # Public API methods
    
    async def get_suggestion_pipeline_status(self) -> Dict[str, Any]:
        """Get status of the suggestion generation pipeline"""
        
        return {
            'last_analysis_time': self._last_analysis_time,
            'suggestions_generated_today': len([
                s for s in self._suggestion_history
                if s.timestamp.date() == datetime.utcnow().date()
            ]),
            'total_suggestions_history': len(self._suggestion_history),
            'analysis_cache_size': len(self._analysis_cache),
            'configuration': {
                'max_suggestions_per_cycle': self.config['max_suggestions_per_cycle'],
                'min_confidence_threshold': self.config['min_confidence_threshold'],
                'suggestion_cooldown_hours': self.config['suggestion_cooldown_hours']
            }
        }
    
    async def force_analysis_refresh(self) -> bool:
        """Force refresh of analysis cache"""
        try:
            self._analysis_cache.clear()
            self._last_analysis_time = None
            logger.info("Analysis cache refreshed")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh analysis cache: {e}")
            return False