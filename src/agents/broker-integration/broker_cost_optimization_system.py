"""
Broker Cost Optimization System - Story 8.14 Main Integration Module

This is the main integration module that brings together all broker cost analysis
and optimization components into a unified system.

Main Features:
- Complete broker cost analysis and optimization
- Real-time execution quality monitoring
- Intelligent broker routing and recommendations
- Historical analysis and forecasting
- Break-even calculations and profitability optimization
- Comprehensive reporting and export capabilities
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta

import structlog

from .broker_cost_analyzer import BrokerCostAnalyzer
from .execution_quality_analyzer import ExecutionQualityAnalyzer
from .broker_comparison_engine import BrokerComparisonEngine
from .historical_cost_analyzer import HistoricalCostAnalyzer
from .breakeven_calculator import BreakEvenCalculator
from .cost_reporting_system import CostReportingSystem, ReportConfiguration, ReportType, ExportFormat

logger = structlog.get_logger(__name__)


class BrokerCostOptimizationSystem:
    """
    Main broker cost optimization system that integrates all components
    to provide comprehensive cost analysis and optimization capabilities.
    """
    
    def __init__(self):
        # Initialize all subsystems
        self.cost_analyzer = BrokerCostAnalyzer()
        self.quality_analyzer = ExecutionQualityAnalyzer()
        self.comparison_engine = BrokerComparisonEngine()
        self.historical_analyzer = HistoricalCostAnalyzer()
        self.breakeven_calculator = BreakEvenCalculator()
        self.reporting_system = CostReportingSystem()
        
        # System state
        self.initialized = False
        self.brokers_configured = []
        
    async def initialize(self, broker_configs: Dict[str, Dict[str, Any]]) -> None:
        """Initialize the complete broker cost optimization system"""
        
        try:
            # Initialize cost analyzer with broker configurations
            await self.cost_analyzer.initialize(broker_configs)
            
            # Initialize comparison engine
            await self.comparison_engine.initialize(list(broker_configs.keys()))
            
            # Initialize historical analyzer
            await self.historical_analyzer.initialize(
                list(broker_configs.keys()), self.cost_analyzer
            )
            
            # Initialize break-even calculator
            await self.breakeven_calculator.initialize()
            
            # Initialize reporting system
            await self.reporting_system.initialize()
            
            self.brokers_configured = list(broker_configs.keys())
            self.initialized = True
            
            logger.info("Broker cost optimization system initialized successfully",
                       brokers_count=len(self.brokers_configured),
                       brokers=self.brokers_configured)
                       
        except Exception as e:
            logger.error("Failed to initialize broker cost optimization system", error=str(e))
            raise
    
    async def analyze_trade_costs(self, broker: str, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze comprehensive costs for a trade"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        # Calculate trade costs
        trade_cost = await self.cost_analyzer.calculate_trade_cost(broker, trade_data)
        
        # Record execution for quality analysis
        execution_data = {
            'broker': broker,
            'instrument': trade_data['instrument'],
            'order_id': trade_data.get('order_id', trade_data['trade_id']),
            'trade_id': trade_data['trade_id'],
            'order_type': trade_data.get('order_type', 'market'),
            'side': trade_data.get('side', 'buy'),
            'requested_size': trade_data['units'],
            'filled_size': trade_data.get('filled_size', trade_data['units']),
            'requested_price': trade_data.get('requested_price'),
            'fill_price': trade_data.get('fill_price', trade_data.get('price')),
            'expected_price': trade_data.get('expected_price', trade_data.get('price')),
            'status': trade_data.get('status', 'filled'),
            'timestamp_request': trade_data.get('timestamp_request', datetime.utcnow()),
            'timestamp_fill': trade_data.get('timestamp_fill', datetime.utcnow()),
            'latency_ms': trade_data.get('latency_ms'),
            'market_conditions': trade_data.get('market_conditions', {})
        }
        
        execution_event = await self.quality_analyzer.record_execution(execution_data)
        
        return {
            'trade_cost': trade_cost,
            'execution_event': execution_event,
            'cost_breakdown': {
                'spread_cost': float(trade_cost.spread_cost),
                'commission': float(trade_cost.commission),
                'swap_cost': float(trade_cost.swap_cost),
                'slippage_cost': float(trade_cost.slippage_cost),
                'financing_cost': float(trade_cost.financing_cost),
                'total_cost': float(trade_cost.total_cost),
                'cost_basis_points': float(trade_cost.cost_basis_points)
            }
        }
    
    async def get_broker_recommendation(self, instrument: str, trade_size: Decimal,
                                      trade_type: str = 'market') -> Dict[str, Any]:
        """Get intelligent broker recommendation for a trade"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        # Use default balanced routing strategy
        from .broker_comparison_engine import RoutingStrategy
        
        recommendation = await self.comparison_engine.get_broker_recommendation(
            instrument=instrument,
            trade_size=trade_size,
            trade_type=trade_type,
            strategy=RoutingStrategy.BALANCED,
            cost_analyzer=self.cost_analyzer,
            quality_analyzer=self.quality_analyzer
        )
        
        return recommendation
    
    async def get_broker_rankings(self, period_days: int = 30) -> Dict[str, Any]:
        """Get current broker rankings and performance comparison"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        # Get broker rankings
        broker_performances = await self.comparison_engine.ranking_system.calculate_broker_rankings(
            self.brokers_configured,
            self.cost_analyzer,
            self.quality_analyzer,
            period_days
        )
        
        # Convert to serializable format
        rankings = {}
        for broker, performance in broker_performances.items():
            rankings[broker] = {
                'composite_score': performance.composite_score,
                'cost_efficiency': float(performance.avg_cost_bps),
                'quality_score': performance.quality_score,
                'execution_score': performance.execution_score,
                'reliability_score': performance.reliability_score,
                'trend_direction': performance.trend_direction,
                'confidence_score': performance.confidence_score,
                'total_trades': performance.total_trades,
                'total_volume': float(performance.total_volume),
                'total_cost': float(performance.total_cost)
            }
        
        # Sort by composite score
        sorted_rankings = dict(sorted(rankings.items(), 
                                    key=lambda x: x[1]['composite_score'], 
                                    reverse=True))
        
        return {
            'rankings': sorted_rankings,
            'analysis_period_days': period_days,
            'generated_at': datetime.utcnow().isoformat(),
            'top_performer': list(sorted_rankings.keys())[0] if sorted_rankings else None,
            'summary': {
                'brokers_analyzed': len(sorted_rankings),
                'avg_composite_score': sum(r['composite_score'] for r in sorted_rankings.values()) / len(sorted_rankings) if sorted_rankings else 0,
                'cost_spread': max(r['cost_efficiency'] for r in sorted_rankings.values()) - min(r['cost_efficiency'] for r in sorted_rankings.values()) if sorted_rankings else 0
            }
        }
    
    async def get_historical_analysis(self, broker: str, instrument: str = None,
                                    period_days: int = 90) -> Dict[str, Any]:
        """Get comprehensive historical analysis for a broker"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        analysis = await self.historical_analyzer.generate_comprehensive_analysis(
            broker, instrument, period_days, self.cost_analyzer
        )
        
        # Convert to serializable format
        serializable_analysis = {
            'trend_analysis': {
                'trend_direction': analysis['trend_analysis'].trend_direction.value,
                'trend_strength': analysis['trend_analysis'].trend_strength,
                'slope': float(analysis['trend_analysis'].slope),
                'r_squared': analysis['trend_analysis'].r_squared,
                'volatility': analysis['trend_analysis'].volatility,
                'current_value': float(analysis['trend_analysis'].current_value),
                'predicted_next_value': float(analysis['trend_analysis'].predicted_next_value),
                'trend_summary': analysis['trend_analysis'].trend_summary
            },
            'seasonal_patterns': {
                pattern_type.value: {
                    'strength_score': seasonal_analysis.strength_score,
                    'peak_periods': seasonal_analysis.peak_periods,
                    'low_periods': seasonal_analysis.low_periods,
                    'patterns_detected': seasonal_analysis.patterns_detected
                }
                for pattern_type, seasonal_analysis in analysis['seasonal_patterns'].items()
            },
            'forecast': {
                'forecast_accuracy': analysis['forecast'].forecast_accuracy,
                'model_type': analysis['forecast'].model_type,
                'factors_considered': analysis['forecast'].factors_considered,
                'risk_assessment': analysis['forecast'].risk_assessment,
                'forecast_horizon_days': analysis['forecast'].forecast_horizon_days
            },
            'benchmark_comparison': {
                'broker_avg_cost': float(analysis['benchmark_comparison'].broker_avg_cost),
                'industry_benchmark': float(analysis['benchmark_comparison'].industry_benchmark),
                'percentile_ranking': analysis['benchmark_comparison'].percentile_ranking,
                'vs_benchmark_percentage': analysis['benchmark_comparison'].vs_benchmark_percentage,
                'performance_category': analysis['benchmark_comparison'].performance_category,
                'ranking_among_peers': analysis['benchmark_comparison'].ranking_among_peers
            },
            'active_alerts': [
                {
                    'alert_id': alert.alert_id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity.value,
                    'message': alert.message,
                    'triggered_timestamp': alert.triggered_timestamp.isoformat() if alert.triggered_timestamp else None,
                    'current_value': float(alert.current_value),
                    'threshold_value': float(alert.threshold_value)
                }
                for alert in analysis['active_alerts']
            ],
            'analysis_summary': analysis['analysis_summary']
        }
        
        return serializable_analysis
    
    async def calculate_break_even_analysis(self, instrument: str, broker: str,
                                          entry_price: Decimal, trade_size: Decimal,
                                          direction: str) -> Dict[str, Any]:
        """Calculate comprehensive break-even analysis"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        analysis = await self.breakeven_calculator.breakeven_analyzer.analyze_break_even(
            instrument, broker, entry_price, trade_size, direction, self.cost_analyzer
        )
        
        return {
            'break_even_price': float(analysis.break_even_price),
            'break_even_movement_pips': float(analysis.break_even_movement_pips),
            'break_even_movement_bps': float(analysis.break_even_movement_bps),
            'minimum_profit_target': float(analysis.minimum_profit_target),
            'recommended_stop_loss': float(analysis.recommended_stop_loss),
            'recommended_take_profit': float(analysis.recommended_take_profit),
            'minimum_hold_time_minutes': analysis.minimum_hold_time,
            'cost_recovery_scenarios': analysis.cost_recovery_scenarios,
            'current_costs': {
                'spread_cost': float(analysis.current_costs.spread_cost),
                'commission': float(analysis.current_costs.commission),
                'swap_cost': float(analysis.current_costs.swap_cost),
                'slippage_cost': float(analysis.current_costs.slippage_cost),
                'total_cost': float(analysis.current_costs.total_cost),
                'cost_basis_points': float(analysis.current_costs.cost_basis_points)
            }
        }
    
    async def optimize_trade_parameters(self, trade_params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize trade parameters for better profitability"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        # Convert to TradeParameters object
        from .breakeven_calculator import TradeParameters
        
        trade_parameters = TradeParameters(
            instrument=trade_params['instrument'],
            entry_price=Decimal(str(trade_params['entry_price'])),
            stop_loss=Decimal(str(trade_params['stop_loss'])) if trade_params.get('stop_loss') else None,
            take_profit=Decimal(str(trade_params['take_profit'])) if trade_params.get('take_profit') else None,
            trade_size=Decimal(str(trade_params['trade_size'])),
            direction=trade_params['direction'],
            broker=trade_params['broker'],
            holding_period_days=trade_params.get('holding_period_days', 0)
        )
        
        # Get comprehensive analysis
        analysis = await self.breakeven_calculator.comprehensive_trade_analysis(
            trade_parameters, self.cost_analyzer
        )
        
        # Convert to serializable format
        return {
            'profitability_analysis': {
                'gross_profit': float(analysis['profitability_analysis'].gross_profit),
                'net_profit': float(analysis['profitability_analysis'].net_profit),
                'profit_margin': float(analysis['profitability_analysis'].profit_margin),
                'return_on_investment': float(analysis['profitability_analysis'].return_on_investment),
                'break_even_price': float(analysis['profitability_analysis'].break_even_price),
                'risk_reward_ratio': float(analysis['profitability_analysis'].risk_reward_ratio),
                'expected_value': float(analysis['profitability_analysis'].expected_value)
            },
            'risk_reward_optimization': {
                'current_risk_reward': float(analysis['risk_reward_optimization'].current_risk_reward),
                'optimal_risk_reward': float(analysis['risk_reward_optimization'].optimal_risk_reward),
                'recommended_stop_loss': float(analysis['risk_reward_optimization'].recommended_stop_loss),
                'recommended_take_profit': float(analysis['risk_reward_optimization'].recommended_take_profit),
                'win_rate_required': float(analysis['risk_reward_optimization'].win_rate_required),
                'optimization_suggestions': analysis['risk_reward_optimization'].optimization_suggestions
            },
            'summary': analysis['summary'],
            'recommendations': analysis['recommendations']
        }
    
    async def generate_cost_report(self, report_type: str, brokers: List[str],
                                 export_format: str = 'csv',
                                 date_range_days: int = 30,
                                 **kwargs) -> Dict[str, Any]:
        """Generate comprehensive cost analysis report"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        # Create report configuration
        config = await self.reporting_system.create_report_config(
            report_type=report_type,
            brokers=brokers,
            export_format=export_format,
            date_range_days=date_range_days,
            **kwargs
        )
        
        # Prepare analyzers for report generation
        analyzers = {
            'cost_analyzer': self.cost_analyzer,
            'quality_analyzer': self.quality_analyzer,
            'comparison_engine': self.comparison_engine,
            'historical_analyzer': self.historical_analyzer,
            'breakeven_calculator': self.breakeven_calculator
        }
        
        # Generate report
        report_output = await self.reporting_system.generate_report(config, analyzers)
        
        return {
            'report_metadata': {
                'report_id': report_output.metadata.report_id,
                'generated_at': report_output.metadata.generated_at.isoformat(),
                'report_type': report_output.metadata.report_type.value,
                'export_format': report_output.metadata.export_format.value,
                'file_size_bytes': report_output.metadata.file_size_bytes,
                'record_count': report_output.metadata.record_count
            },
            'file_name': report_output.file_name,
            'mime_type': report_output.mime_type,
            'content': report_output.content,
            'summary': report_output.summary,
            'recommendations': report_output.recommendations
        }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and health metrics"""
        
        status = {
            'initialized': self.initialized,
            'brokers_configured': self.brokers_configured,
            'system_health': 'healthy' if self.initialized else 'not_initialized',
            'components': {
                'cost_analyzer': 'active' if self.cost_analyzer else 'inactive',
                'quality_analyzer': 'active' if self.quality_analyzer else 'inactive',
                'comparison_engine': 'active' if self.comparison_engine else 'inactive',
                'historical_analyzer': 'active' if self.historical_analyzer else 'inactive',
                'breakeven_calculator': 'active' if self.breakeven_calculator else 'inactive',
                'reporting_system': 'active' if self.reporting_system else 'inactive'
            },
            'capabilities': {
                'cost_tracking': True,
                'execution_quality_analysis': True,
                'broker_comparison': True,
                'historical_analysis': True,
                'breakeven_calculation': True,
                'profitability_optimization': True,
                'automated_reporting': True
            },
            'last_updated': datetime.utcnow().isoformat()
        }
        
        if self.initialized:
            # Get some basic statistics
            try:
                # Get recent cost comparison
                cost_comparison = await self.cost_analyzer.generate_broker_cost_comparison(7)
                status['recent_activity'] = {
                    'brokers_with_data': len(cost_comparison),
                    'total_trades_last_week': sum(
                        broker_data.get('trade_count', 0) 
                        for broker_data in cost_comparison.values()
                    ),
                    'avg_cost_bps': sum(
                        float(broker_data.get('avg_cost_bps', 0)) 
                        for broker_data in cost_comparison.values()
                    ) / len(cost_comparison) if cost_comparison else 0
                }
            except Exception as e:
                status['recent_activity'] = {'error': str(e)}
        
        return status
    
    async def get_available_features(self) -> Dict[str, Any]:
        """Get available features and capabilities"""
        
        return {
            'cost_analysis': {
                'description': 'Track and analyze trading costs across brokers',
                'features': [
                    'Real-time cost calculation',
                    'Cost categorization (spread, commission, swap, slippage)',
                    'Cost basis points tracking',
                    'Historical cost trends'
                ]
            },
            'execution_quality': {
                'description': 'Monitor and analyze trade execution quality',
                'features': [
                    'Slippage measurement and analysis',
                    'Fill rate tracking',
                    'Execution speed monitoring',
                    'Rejection rate analysis',
                    'Quality scoring algorithms'
                ]
            },
            'broker_comparison': {
                'description': 'Compare brokers and optimize routing',
                'features': [
                    'Multi-factor broker ranking',
                    'Intelligent routing recommendations',
                    'A/B testing framework',
                    'Optimal allocation strategies'
                ]
            },
            'historical_analysis': {
                'description': 'Analyze historical patterns and forecast costs',
                'features': [
                    'Cost trend analysis',
                    'Seasonal pattern detection',
                    'Cost forecasting',
                    'Benchmark comparisons',
                    'Alert system'
                ]
            },
            'profitability_optimization': {
                'description': 'Optimize trade profitability and break-even analysis',
                'features': [
                    'Break-even calculations',
                    'Risk-reward optimization',
                    'Minimum trade size analysis',
                    'Scenario planning',
                    'Profitability recommendations'
                ]
            },
            'reporting': {
                'description': 'Generate comprehensive reports and exports',
                'features': [
                    'Multiple report types',
                    'CSV/JSON/HTML export formats',
                    'Automated report scheduling',
                    'Custom report builder'
                ]
            },
            'supported_brokers': self.brokers_configured,
            'supported_instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD'],
            'api_version': '1.0'
        }


# Convenience functions for easy integration

async def create_broker_cost_system(broker_configs: Dict[str, Dict[str, Any]]) -> BrokerCostOptimizationSystem:
    """Create and initialize a broker cost optimization system"""
    
    system = BrokerCostOptimizationSystem()
    await system.initialize(broker_configs)
    return system


async def quick_cost_analysis(system: BrokerCostOptimizationSystem,
                            broker: str, trade_data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform quick cost analysis for a trade"""
    
    return await system.analyze_trade_costs(broker, trade_data)


async def quick_broker_recommendation(system: BrokerCostOptimizationSystem,
                                    instrument: str, trade_size: float) -> str:
    """Get quick broker recommendation"""
    
    recommendation = await system.get_broker_recommendation(
        instrument, Decimal(str(trade_size))
    )
    return recommendation['recommended_broker']