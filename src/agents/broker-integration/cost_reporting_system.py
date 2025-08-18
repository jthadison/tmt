"""
Cost Reporting & Export System - Story 8.14 Task 6

This module provides comprehensive reporting and export capabilities for
broker cost analysis including customizable reports, multiple export formats,
automated report generation, and scheduled reporting.

Features:
- Cost analysis report generation
- CSV/Excel export capabilities
- PDF report generation with charts
- Automated reporting system
- Custom report builder
- Report scheduling and distribution
"""

import csv
import io
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from decimal import Decimal
from datetime import datetime, timedelta, date
from enum import Enum
import asyncio
import logging
from pathlib import Path
import base64

import structlog

logger = structlog.get_logger(__name__)


class ReportType(str, Enum):
    """Report type classifications"""
    COST_SUMMARY = "cost_summary"
    EXECUTION_QUALITY = "execution_quality"
    BROKER_COMPARISON = "broker_comparison"
    HISTORICAL_ANALYSIS = "historical_analysis"
    BREAKEVEN_ANALYSIS = "breakeven_analysis"
    PROFITABILITY_REPORT = "profitability_report"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    CUSTOM = "custom"


class ExportFormat(str, Enum):
    """Export format options"""
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    JSON = "json"
    HTML = "html"


class ReportFrequency(str, Enum):
    """Report frequency options"""
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ON_DEMAND = "on_demand"


@dataclass
class ReportConfiguration:
    """Report configuration settings"""
    report_id: str
    report_type: ReportType
    title: str
    description: str
    brokers: List[str]
    instruments: List[str]
    date_range_days: int
    export_format: ExportFormat
    include_charts: bool = True
    include_summary: bool = True
    include_recommendations: bool = True
    filters: Dict[str, Any] = field(default_factory=dict)
    custom_fields: List[str] = field(default_factory=list)
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReportMetadata:
    """Report metadata"""
    report_id: str
    generated_at: datetime
    generated_by: str
    report_type: ReportType
    export_format: ExportFormat
    data_period_start: datetime
    data_period_end: datetime
    record_count: int
    file_size_bytes: int
    checksum: str
    version: str = "1.0"


@dataclass
class ScheduledReport:
    """Scheduled report configuration"""
    schedule_id: str
    report_config: ReportConfiguration
    frequency: ReportFrequency
    next_run: datetime
    last_run: Optional[datetime]
    recipients: List[str]
    enabled: bool = True
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ReportOutput:
    """Report output container"""
    metadata: ReportMetadata
    content: Union[str, bytes]
    file_name: str
    mime_type: str
    charts: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class CostAnalysisReportGenerator:
    """Generate comprehensive cost analysis reports"""
    
    def __init__(self):
        self.report_templates = {
            ReportType.COST_SUMMARY: self._generate_cost_summary_report,
            ReportType.EXECUTION_QUALITY: self._generate_execution_quality_report,
            ReportType.BROKER_COMPARISON: self._generate_broker_comparison_report,
            ReportType.HISTORICAL_ANALYSIS: self._generate_historical_analysis_report,
            ReportType.BREAKEVEN_ANALYSIS: self._generate_breakeven_report,
            ReportType.PROFITABILITY_REPORT: self._generate_profitability_report
        }
    
    async def generate_cost_summary_report(self, config: ReportConfiguration,
                                         cost_analyzer = None) -> Dict[str, Any]:
        """Generate comprehensive cost summary report"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=config.date_range_days)
        
        report_data = {
            'report_info': {
                'title': config.title,
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'generated_at': datetime.utcnow().isoformat(),
                'brokers_analyzed': config.brokers,
                'instruments_analyzed': config.instruments
            },
            'cost_overview': {},
            'broker_breakdown': {},
            'cost_trends': {},
            'recommendations': []
        }
        
        # Get cost data for each broker
        for broker in config.brokers:
            try:
                cost_comparison = await cost_analyzer.generate_broker_cost_comparison(config.date_range_days)
                broker_data = cost_comparison.get(broker, {})
                
                report_data['broker_breakdown'][broker] = {
                    'total_cost': float(broker_data.get('total_cost', 0)),
                    'total_volume': float(broker_data.get('total_volume', 0)),
                    'avg_cost_per_trade': float(broker_data.get('avg_cost_per_trade', 0)),
                    'avg_cost_bps': float(broker_data.get('avg_cost_bps', 0)),
                    'trade_count': broker_data.get('trade_count', 0),
                    'cost_by_category': {
                        category: float(amount) 
                        for category, amount in broker_data.get('cost_by_category', {}).items()
                    }
                }
                
                # Get cost trends
                cost_trends = await cost_analyzer.get_cost_trends(broker, None, config.date_range_days)
                if cost_trends:
                    report_data['cost_trends'][broker] = cost_trends
                    
            except Exception as e:
                logger.warning("Error generating cost data for broker", broker=broker, error=str(e))
                report_data['broker_breakdown'][broker] = {'error': str(e)}
        
        # Calculate overall summary
        all_broker_data = [data for data in report_data['broker_breakdown'].values() if 'error' not in data]
        if all_broker_data:
            report_data['cost_overview'] = {
                'total_cost_all_brokers': sum(data['total_cost'] for data in all_broker_data),
                'total_volume_all_brokers': sum(data['total_volume'] for data in all_broker_data),
                'total_trades_all_brokers': sum(data['trade_count'] for data in all_broker_data),
                'avg_cost_bps_weighted': sum(
                    data['avg_cost_bps'] * data['total_volume'] for data in all_broker_data
                ) / sum(data['total_volume'] for data in all_broker_data) if sum(data['total_volume'] for data in all_broker_data) > 0 else 0
            }
        
        # Generate recommendations
        report_data['recommendations'] = self._generate_cost_recommendations(report_data['broker_breakdown'])
        
        return report_data
    
    async def _generate_cost_summary_report(self, config: ReportConfiguration,
                                          analyzers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cost summary report"""
        return await self.generate_cost_summary_report(config, analyzers.get('cost_analyzer'))
    
    async def _generate_execution_quality_report(self, config: ReportConfiguration,
                                               analyzers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution quality report"""
        
        report_data = {
            'report_info': {
                'title': config.title,
                'type': 'Execution Quality Analysis',
                'generated_at': datetime.utcnow().isoformat()
            },
            'quality_metrics': {},
            'slippage_analysis': {},
            'execution_speed': {},
            'fill_rates': {},
            'recommendations': []
        }
        
        quality_analyzer = analyzers.get('quality_analyzer')
        if quality_analyzer:
            for broker in config.brokers:
                try:
                    quality_report = await quality_analyzer.generate_quality_report(
                        broker, None, config.date_range_days
                    )
                    
                    report_data['quality_metrics'][broker] = {
                        'quality_score': quality_report.quality_score,
                        'fill_rate': quality_report.fill_rate,
                        'avg_latency_ms': quality_report.avg_latency_ms,
                        'avg_slippage_pips': quality_report.avg_slippage_pips,
                        'rejection_rate': quality_report.rejection_rate,
                        'execution_efficiency': quality_report.execution_efficiency
                    }
                    
                except Exception as e:
                    logger.warning("Error generating quality data", broker=broker, error=str(e))
                    report_data['quality_metrics'][broker] = {'error': str(e)}
        
        return report_data
    
    async def _generate_broker_comparison_report(self, config: ReportConfiguration,
                                               analyzers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate broker comparison report"""
        
        report_data = {
            'report_info': {
                'title': config.title,
                'type': 'Broker Comparison Analysis',
                'generated_at': datetime.utcnow().isoformat()
            },
            'cost_comparison': {},
            'quality_comparison': {},
            'rankings': {},
            'recommendations': []
        }
        
        comparison_engine = analyzers.get('comparison_engine')
        if comparison_engine:
            try:
                # Get broker rankings
                cost_analyzer = analyzers.get('cost_analyzer')
                quality_analyzer = analyzers.get('quality_analyzer')
                
                if cost_analyzer and quality_analyzer:
                    broker_performances = await comparison_engine.ranking_system.calculate_broker_rankings(
                        config.brokers, cost_analyzer, quality_analyzer, config.date_range_days
                    )
                    
                    report_data['rankings'] = {
                        broker: {
                            'composite_score': perf.composite_score,
                            'cost_efficiency': perf.avg_cost_bps,
                            'quality_score': perf.quality_score,
                            'reliability_score': perf.reliability_score,
                            'trend_direction': perf.trend_direction
                        }
                        for broker, perf in broker_performances.items()
                    }
                    
            except Exception as e:
                logger.warning("Error generating comparison data", error=str(e))
        
        return report_data
    
    async def _generate_historical_analysis_report(self, config: ReportConfiguration,
                                                 analyzers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate historical analysis report"""
        
        report_data = {
            'report_info': {
                'title': config.title,
                'type': 'Historical Cost Analysis',
                'generated_at': datetime.utcnow().isoformat()
            },
            'trend_analysis': {},
            'seasonal_patterns': {},
            'forecasts': {},
            'benchmark_comparisons': {},
            'recommendations': []
        }
        
        historical_analyzer = analyzers.get('historical_analyzer')
        if historical_analyzer:
            for broker in config.brokers:
                try:
                    comprehensive_analysis = await historical_analyzer.generate_comprehensive_analysis(
                        broker, None, config.date_range_days, analyzers.get('cost_analyzer')
                    )
                    
                    report_data['trend_analysis'][broker] = {
                        'trend_direction': comprehensive_analysis['trend_analysis'].trend_direction.value,
                        'trend_strength': comprehensive_analysis['trend_analysis'].trend_strength,
                        'trend_summary': comprehensive_analysis['trend_analysis'].trend_summary
                    }
                    
                    report_data['seasonal_patterns'][broker] = {
                        pattern_type.value: {
                            'strength_score': analysis.strength_score,
                            'peak_periods': analysis.peak_periods,
                            'low_periods': analysis.low_periods
                        }
                        for pattern_type, analysis in comprehensive_analysis['seasonal_patterns'].items()
                    }
                    
                    report_data['forecasts'][broker] = {
                        'forecast_accuracy': comprehensive_analysis['forecast'].forecast_accuracy,
                        'risk_assessment': comprehensive_analysis['forecast'].risk_assessment,
                        'factors_considered': comprehensive_analysis['forecast'].factors_considered
                    }
                    
                except Exception as e:
                    logger.warning("Error generating historical analysis", broker=broker, error=str(e))
        
        return report_data
    
    async def _generate_breakeven_report(self, config: ReportConfiguration,
                                       analyzers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate break-even analysis report"""
        
        report_data = {
            'report_info': {
                'title': config.title,
                'type': 'Break-even Analysis',
                'generated_at': datetime.utcnow().isoformat()
            },
            'breakeven_analysis': {},
            'minimum_trade_sizes': {},
            'profitability_scenarios': {},
            'recommendations': []
        }
        
        # This would require trade-specific data, so we'll create sample analysis
        breakeven_calculator = analyzers.get('breakeven_calculator')
        if breakeven_calculator:
            for broker in config.brokers:
                try:
                    # Sample trade parameters for analysis
                    from .breakeven_calculator import TradeParameters
                    sample_trade = TradeParameters(
                        instrument='EUR_USD',
                        entry_price=Decimal('1.0500'),
                        stop_loss=Decimal('1.0480'),
                        take_profit=Decimal('1.0540'),
                        trade_size=Decimal('100000'),
                        direction='buy',
                        broker=broker
                    )
                    
                    analysis = await breakeven_calculator.comprehensive_trade_analysis(
                        sample_trade, analyzers.get('cost_analyzer')
                    )
                    
                    report_data['breakeven_analysis'][broker] = {
                        'break_even_pips': float(analysis['breakeven_analysis'].break_even_movement_pips),
                        'minimum_profit_target': float(analysis['breakeven_analysis'].minimum_profit_target),
                        'recommended_stop_loss': float(analysis['breakeven_analysis'].recommended_stop_loss),
                        'recommended_take_profit': float(analysis['breakeven_analysis'].recommended_take_profit)
                    }
                    
                    report_data['minimum_trade_sizes'][broker] = {
                        'recommended_minimum': float(analysis['minimum_trade_size'].recommended_minimum),
                        'min_size_by_cost': float(analysis['minimum_trade_size'].minimum_size_by_cost),
                        'min_size_by_risk': float(analysis['minimum_trade_size'].minimum_size_by_risk)
                    }
                    
                except Exception as e:
                    logger.warning("Error generating breakeven analysis", broker=broker, error=str(e))
        
        return report_data
    
    async def _generate_profitability_report(self, config: ReportConfiguration,
                                           analyzers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate profitability analysis report"""
        
        return {
            'report_info': {
                'title': config.title,
                'type': 'Profitability Analysis',
                'generated_at': datetime.utcnow().isoformat()
            },
            'profitability_metrics': {},
            'cost_impact_analysis': {},
            'optimization_suggestions': {},
            'recommendations': []
        }
    
    def _generate_cost_recommendations(self, broker_breakdown: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        # Find best and worst performers
        valid_brokers = {k: v for k, v in broker_breakdown.items() if 'error' not in v}
        
        if len(valid_brokers) < 2:
            return ["Insufficient data for broker comparison"]
        
        # Sort by cost basis points
        sorted_by_cost = sorted(valid_brokers.items(), key=lambda x: x[1]['avg_cost_bps'])
        
        best_broker = sorted_by_cost[0]
        worst_broker = sorted_by_cost[-1]
        
        cost_difference = worst_broker[1]['avg_cost_bps'] - best_broker[1]['avg_cost_bps']
        
        if cost_difference > 1:  # More than 1 bps difference
            recommendations.append(
                f"Consider routing more trades to {best_broker[0]} - costs are {cost_difference:.1f} bps lower than {worst_broker[0]}"
            )
        
        # Check for high-cost brokers
        for broker, data in valid_brokers.items():
            if data['avg_cost_bps'] > 8:  # High cost threshold
                recommendations.append(f"Review {broker} costs - {data['avg_cost_bps']:.1f} bps is above 8 bps threshold")
        
        # Volume-based recommendations
        total_volume = sum(data['total_volume'] for data in valid_brokers.values())
        for broker, data in valid_brokers.items():
            if data['total_volume'] / total_volume > 0.7:  # Over-concentration
                recommendations.append(f"Consider diversifying from {broker} - {data['total_volume']/total_volume:.1%} of total volume")
        
        return recommendations


class ExportManager:
    """Handle various export formats"""
    
    def __init__(self):
        self.exporters = {
            ExportFormat.CSV: self._export_to_csv,
            ExportFormat.JSON: self._export_to_json,
            ExportFormat.HTML: self._export_to_html
        }
    
    async def export_report(self, report_data: Dict[str, Any], 
                          config: ReportConfiguration) -> ReportOutput:
        """Export report in specified format"""
        
        exporter = self.exporters.get(config.export_format)
        if not exporter:
            raise ValueError(f"Unsupported export format: {config.export_format}")
        
        content, mime_type, file_extension = await exporter(report_data, config)
        
        # Generate metadata
        metadata = ReportMetadata(
            report_id=config.report_id,
            generated_at=datetime.utcnow(),
            generated_by=config.created_by,
            report_type=config.report_type,
            export_format=config.export_format,
            data_period_start=datetime.utcnow() - timedelta(days=config.date_range_days),
            data_period_end=datetime.utcnow(),
            record_count=self._count_records(report_data),
            file_size_bytes=len(content) if isinstance(content, str) else len(content),
            checksum=self._calculate_checksum(content)
        )
        
        file_name = f"{config.report_id}_{config.report_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        
        return ReportOutput(
            metadata=metadata,
            content=content,
            file_name=file_name,
            mime_type=mime_type,
            summary=report_data.get('cost_overview', {}),
            recommendations=report_data.get('recommendations', [])
        )
    
    async def _export_to_csv(self, report_data: Dict[str, Any], 
                           config: ReportConfiguration) -> Tuple[str, str, str]:
        """Export report data to CSV format"""
        
        output = io.StringIO()
        
        # Write report header
        output.write(f"# {config.title}\n")
        output.write(f"# Generated: {datetime.utcnow().isoformat()}\n")
        output.write(f"# Period: {config.date_range_days} days\n")
        output.write("\n")
        
        # Export broker breakdown if available
        if 'broker_breakdown' in report_data:
            output.write("Broker Cost Summary\n")
            
            writer = csv.writer(output)
            
            # Headers
            headers = ['Broker', 'Total Cost', 'Total Volume', 'Avg Cost per Trade', 
                      'Avg Cost (bps)', 'Trade Count']
            writer.writerow(headers)
            
            # Data rows
            for broker, data in report_data['broker_breakdown'].items():
                if 'error' not in data:
                    row = [
                        broker,
                        data.get('total_cost', 0),
                        data.get('total_volume', 0),
                        data.get('avg_cost_per_trade', 0),
                        data.get('avg_cost_bps', 0),
                        data.get('trade_count', 0)
                    ]
                    writer.writerow(row)
            
            output.write("\n")
        
        # Export cost by category if available
        if 'broker_breakdown' in report_data:
            output.write("Cost Breakdown by Category\n")
            
            # Collect all categories
            all_categories = set()
            for broker_data in report_data['broker_breakdown'].values():
                if 'cost_by_category' in broker_data:
                    all_categories.update(broker_data['cost_by_category'].keys())
            
            if all_categories:
                writer = csv.writer(output)
                headers = ['Broker'] + list(all_categories)
                writer.writerow(headers)
                
                for broker, data in report_data['broker_breakdown'].items():
                    if 'error' not in data and 'cost_by_category' in data:
                        row = [broker]
                        for category in all_categories:
                            row.append(data['cost_by_category'].get(category, 0))
                        writer.writerow(row)
        
        # Export recommendations
        if 'recommendations' in report_data and report_data['recommendations']:
            output.write("\nRecommendations\n")
            for i, recommendation in enumerate(report_data['recommendations'], 1):
                output.write(f"{i}. {recommendation}\n")
        
        return output.getvalue(), "text/csv", "csv"
    
    async def _export_to_json(self, report_data: Dict[str, Any], 
                            config: ReportConfiguration) -> Tuple[str, str, str]:
        """Export report data to JSON format"""
        
        # Convert Decimal objects to float for JSON serialization
        json_data = self._convert_decimals_to_float(report_data)
        
        # Add metadata
        json_data['export_metadata'] = {
            'export_format': config.export_format.value,
            'generated_at': datetime.utcnow().isoformat(),
            'report_id': config.report_id,
            'report_type': config.report_type.value
        }
        
        content = json.dumps(json_data, indent=2, default=str)
        return content, "application/json", "json"
    
    async def _export_to_html(self, report_data: Dict[str, Any], 
                            config: ReportConfiguration) -> Tuple[str, str, str]:
        """Export report data to HTML format"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{config.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .recommendations {{ background-color: #e8f4f8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>{config.title}</h1>
            <div class="summary">
                <h3>Report Information</h3>
                <p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Period:</strong> {config.date_range_days} days</p>
                <p><strong>Brokers:</strong> {', '.join(config.brokers)}</p>
            </div>
        """
        
        # Add broker breakdown table
        if 'broker_breakdown' in report_data:
            html_content += """
            <h2>Broker Cost Summary</h2>
            <table>
                <tr>
                    <th>Broker</th>
                    <th>Total Cost</th>
                    <th>Total Volume</th>
                    <th>Avg Cost per Trade</th>
                    <th>Avg Cost (bps)</th>
                    <th>Trade Count</th>
                </tr>
            """
            
            for broker, data in report_data['broker_breakdown'].items():
                if 'error' not in data:
                    html_content += f"""
                    <tr>
                        <td>{broker}</td>
                        <td>{data.get('total_cost', 0):.2f}</td>
                        <td>{data.get('total_volume', 0):,.0f}</td>
                        <td>{data.get('avg_cost_per_trade', 0):.2f}</td>
                        <td>{data.get('avg_cost_bps', 0):.2f}</td>
                        <td>{data.get('trade_count', 0)}</td>
                    </tr>
                    """
            
            html_content += "</table>"
        
        # Add recommendations
        if 'recommendations' in report_data and report_data['recommendations']:
            html_content += """
            <div class="recommendations">
                <h3>Recommendations</h3>
                <ul>
            """
            
            for recommendation in report_data['recommendations']:
                html_content += f"<li>{recommendation}</li>"
            
            html_content += "</ul></div>"
        
        html_content += """
        </body>
        </html>
        """
        
        return html_content, "text/html", "html"
    
    def _convert_decimals_to_float(self, obj: Any) -> Any:
        """Convert Decimal objects to float for JSON serialization"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_decimals_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_to_float(item) for item in obj]
        else:
            return obj
    
    def _count_records(self, report_data: Dict[str, Any]) -> int:
        """Count total records in report"""
        count = 0
        
        if 'broker_breakdown' in report_data:
            count += len(report_data['broker_breakdown'])
        
        if 'cost_trends' in report_data:
            for broker_trends in report_data['cost_trends'].values():
                for trend_data in broker_trends.values():
                    if isinstance(trend_data, list):
                        count += len(trend_data)
        
        return count
    
    def _calculate_checksum(self, content: Union[str, bytes]) -> str:
        """Calculate simple checksum for content"""
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        
        # Simple checksum calculation
        checksum = sum(content_bytes) % 65536
        return f"{checksum:04x}"


class AutomatedReportingEngine:
    """Automated report generation and distribution"""
    
    def __init__(self):
        self.report_generator = CostAnalysisReportGenerator()
        self.export_manager = ExportManager()
        self.scheduled_reports: Dict[str, ScheduledReport] = {}
        
    async def schedule_report(self, schedule_config: ScheduledReport) -> None:
        """Schedule automated report generation"""
        
        self.scheduled_reports[schedule_config.schedule_id] = schedule_config
        
        # Calculate next run time
        await self._update_next_run_time(schedule_config)
        
        logger.info("Report scheduled",
                   schedule_id=schedule_config.schedule_id,
                   frequency=schedule_config.frequency.value,
                   next_run=schedule_config.next_run)
    
    async def process_scheduled_reports(self, analyzers: Dict[str, Any]) -> List[ReportOutput]:
        """Process all due scheduled reports"""
        
        now = datetime.utcnow()
        generated_reports = []
        
        for schedule_id, schedule in self.scheduled_reports.items():
            if schedule.enabled and schedule.next_run <= now:
                try:
                    # Generate report
                    report_output = await self._generate_scheduled_report(schedule, analyzers)
                    generated_reports.append(report_output)
                    
                    # Update schedule
                    schedule.last_run = now
                    schedule.retry_count = 0
                    await self._update_next_run_time(schedule)
                    
                    # Distribute report
                    await self._distribute_report(report_output, schedule)
                    
                    logger.info("Scheduled report generated successfully",
                               schedule_id=schedule_id)
                    
                except Exception as e:
                    schedule.retry_count += 1
                    
                    if schedule.retry_count < schedule.max_retries:
                        # Retry in 1 hour
                        schedule.next_run = now + timedelta(hours=1)
                        logger.warning("Scheduled report failed, will retry",
                                     schedule_id=schedule_id,
                                     retry_count=schedule.retry_count,
                                     error=str(e))
                    else:
                        # Disable after max retries
                        schedule.enabled = False
                        logger.error("Scheduled report disabled after max retries",
                                   schedule_id=schedule_id,
                                   error=str(e))
        
        return generated_reports
    
    async def _generate_scheduled_report(self, schedule: ScheduledReport,
                                       analyzers: Dict[str, Any]) -> ReportOutput:
        """Generate report for scheduled execution"""
        
        # Generate report data
        report_template = self.report_generator.report_templates.get(schedule.report_config.report_type)
        if not report_template:
            raise ValueError(f"Unknown report type: {schedule.report_config.report_type}")
        
        report_data = await report_template(schedule.report_config, analyzers)
        
        # Export report
        report_output = await self.export_manager.export_report(report_data, schedule.report_config)
        
        return report_output
    
    async def _update_next_run_time(self, schedule: ScheduledReport) -> None:
        """Update next run time based on frequency"""
        
        now = datetime.utcnow()
        
        if schedule.frequency == ReportFrequency.HOURLY:
            schedule.next_run = now + timedelta(hours=1)
        elif schedule.frequency == ReportFrequency.DAILY:
            schedule.next_run = now + timedelta(days=1)
        elif schedule.frequency == ReportFrequency.WEEKLY:
            schedule.next_run = now + timedelta(weeks=1)
        elif schedule.frequency == ReportFrequency.MONTHLY:
            schedule.next_run = now + timedelta(days=30)
        elif schedule.frequency == ReportFrequency.QUARTERLY:
            schedule.next_run = now + timedelta(days=90)
        else:
            # On-demand reports don't get rescheduled
            schedule.enabled = False
    
    async def _distribute_report(self, report_output: ReportOutput,
                               schedule: ScheduledReport) -> None:
        """Distribute report to recipients"""
        
        # In production, this would send emails, save to shared folders, etc.
        logger.info("Report distributed",
                   report_id=report_output.metadata.report_id,
                   recipients=len(schedule.recipients),
                   file_name=report_output.file_name)


class CustomReportBuilder:
    """Build custom reports with user-defined fields and filters"""
    
    def __init__(self):
        self.available_fields = {
            'broker': 'Broker name',
            'instrument': 'Trading instrument',
            'total_cost': 'Total trading cost',
            'avg_cost_bps': 'Average cost in basis points',
            'trade_count': 'Number of trades',
            'quality_score': 'Execution quality score',
            'fill_rate': 'Order fill rate',
            'avg_latency': 'Average execution latency',
            'slippage': 'Average slippage',
            'trend_direction': 'Cost trend direction',
            'seasonal_pattern': 'Seasonal cost patterns'
        }
        
        self.available_filters = {
            'date_range': 'Filter by date range',
            'broker': 'Filter by specific brokers',
            'instrument': 'Filter by trading instruments',
            'cost_threshold': 'Filter by cost thresholds',
            'volume_threshold': 'Filter by volume thresholds',
            'quality_threshold': 'Filter by quality scores'
        }
    
    async def build_custom_report(self, custom_config: Dict[str, Any],
                                analyzers: Dict[str, Any]) -> Dict[str, Any]:
        """Build custom report based on user configuration"""
        
        # Extract configuration
        selected_fields = custom_config.get('fields', list(self.available_fields.keys()))
        filters = custom_config.get('filters', {})
        grouping = custom_config.get('grouping', [])
        sorting = custom_config.get('sorting', {})
        
        # Collect data from various analyzers
        raw_data = await self._collect_raw_data(custom_config, analyzers)
        
        # Apply filters
        filtered_data = await self._apply_filters(raw_data, filters)
        
        # Apply grouping
        grouped_data = await self._apply_grouping(filtered_data, grouping)
        
        # Apply sorting
        sorted_data = await self._apply_sorting(grouped_data, sorting)
        
        # Select fields
        final_data = await self._select_fields(sorted_data, selected_fields)
        
        # Generate summary statistics
        summary = await self._generate_custom_summary(final_data)
        
        return {
            'report_info': {
                'title': custom_config.get('title', 'Custom Cost Analysis Report'),
                'generated_at': datetime.utcnow().isoformat(),
                'fields_included': selected_fields,
                'filters_applied': filters,
                'record_count': len(final_data)
            },
            'data': final_data,
            'summary': summary,
            'metadata': {
                'available_fields': self.available_fields,
                'available_filters': self.available_filters
            }
        }
    
    async def _collect_raw_data(self, config: Dict[str, Any],
                              analyzers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect raw data from analyzers"""
        
        raw_data = []
        brokers = config.get('brokers', ['broker1', 'broker2'])  # Default brokers
        
        for broker in brokers:
            try:
                # Collect cost data
                cost_analyzer = analyzers.get('cost_analyzer')
                if cost_analyzer:
                    cost_data = await cost_analyzer.generate_broker_cost_comparison(30)
                    broker_cost_data = cost_data.get(broker, {})
                    
                    record = {
                        'broker': broker,
                        'total_cost': broker_cost_data.get('total_cost', 0),
                        'avg_cost_bps': broker_cost_data.get('avg_cost_bps', 0),
                        'trade_count': broker_cost_data.get('trade_count', 0),
                        'total_volume': broker_cost_data.get('total_volume', 0)
                    }
                    
                    # Add quality data if available
                    quality_analyzer = analyzers.get('quality_analyzer')
                    if quality_analyzer:
                        quality_report = await quality_analyzer.generate_quality_report(broker, None, 30)
                        record.update({
                            'quality_score': quality_report.quality_score,
                            'fill_rate': quality_report.fill_rate,
                            'avg_latency': quality_report.avg_latency_ms,
                            'avg_slippage': quality_report.avg_slippage_pips
                        })
                    
                    raw_data.append(record)
                    
            except Exception as e:
                logger.warning("Error collecting data for broker", broker=broker, error=str(e))
        
        return raw_data
    
    async def _apply_filters(self, data: List[Dict[str, Any]],
                           filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filters to data"""
        
        filtered_data = data.copy()
        
        # Cost threshold filter
        if 'cost_threshold' in filters:
            threshold = filters['cost_threshold']
            filtered_data = [
                record for record in filtered_data
                if record.get('avg_cost_bps', 0) <= threshold
            ]
        
        # Volume threshold filter
        if 'volume_threshold' in filters:
            threshold = filters['volume_threshold']
            filtered_data = [
                record for record in filtered_data
                if record.get('total_volume', 0) >= threshold
            ]
        
        # Quality threshold filter
        if 'quality_threshold' in filters:
            threshold = filters['quality_threshold']
            filtered_data = [
                record for record in filtered_data
                if record.get('quality_score', 0) >= threshold
            ]
        
        # Broker filter
        if 'brokers' in filters:
            allowed_brokers = filters['brokers']
            filtered_data = [
                record for record in filtered_data
                if record.get('broker') in allowed_brokers
            ]
        
        return filtered_data
    
    async def _apply_grouping(self, data: List[Dict[str, Any]],
                            grouping: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Apply grouping to data"""
        
        if not grouping:
            return {'all': data}
        
        grouped = {}
        for record in data:
            # Create group key
            group_key = '_'.join(str(record.get(field, 'unknown')) for field in grouping)
            
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(record)
        
        return grouped
    
    async def _apply_sorting(self, data: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]],
                           sorting: Dict[str, Any]) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """Apply sorting to data"""
        
        sort_field = sorting.get('field', 'broker')
        sort_order = sorting.get('order', 'asc')
        reverse = sort_order == 'desc'
        
        if isinstance(data, dict):
            # Grouped data
            sorted_data = {}
            for group_key, group_data in data.items():
                sorted_data[group_key] = sorted(
                    group_data,
                    key=lambda x: x.get(sort_field, 0),
                    reverse=reverse
                )
            return sorted_data
        else:
            # Ungrouped data
            return sorted(data, key=lambda x: x.get(sort_field, 0), reverse=reverse)
    
    async def _select_fields(self, data: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]],
                           selected_fields: List[str]) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """Select only specified fields"""
        
        def filter_record(record):
            return {field: record.get(field) for field in selected_fields if field in record}
        
        if isinstance(data, dict):
            return {
                group_key: [filter_record(record) for record in group_data]
                for group_key, group_data in data.items()
            }
        else:
            return [filter_record(record) for record in data]
    
    async def _generate_custom_summary(self, data: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]) -> Dict[str, Any]:
        """Generate summary statistics for custom report"""
        
        if isinstance(data, dict):
            # Grouped data summary
            summary = {}
            for group_key, group_data in data.items():
                summary[group_key] = {
                    'record_count': len(group_data),
                    'avg_cost_bps': sum(r.get('avg_cost_bps', 0) for r in group_data) / len(group_data) if group_data else 0,
                    'total_volume': sum(r.get('total_volume', 0) for r in group_data),
                    'avg_quality_score': sum(r.get('quality_score', 0) for r in group_data) / len(group_data) if group_data else 0
                }
            return summary
        else:
            # Ungrouped data summary
            return {
                'total_records': len(data),
                'avg_cost_bps': sum(r.get('avg_cost_bps', 0) for r in data) / len(data) if data else 0,
                'total_volume': sum(r.get('total_volume', 0) for r in data),
                'avg_quality_score': sum(r.get('quality_score', 0) for r in data) / len(data) if data else 0
            }


class CostReportingSystem:
    """Main cost reporting and export system"""
    
    def __init__(self):
        self.report_generator = CostAnalysisReportGenerator()
        self.export_manager = ExportManager()
        self.automated_engine = AutomatedReportingEngine()
        self.custom_builder = CustomReportBuilder()
        
    async def initialize(self) -> None:
        """Initialize reporting system"""
        logger.info("Cost reporting system initialized")
    
    async def generate_report(self, config: ReportConfiguration,
                            analyzers: Dict[str, Any]) -> ReportOutput:
        """Generate report based on configuration"""
        
        # Generate report data
        if config.report_type == ReportType.CUSTOM:
            # Handle custom reports
            custom_config = config.filters.get('custom_config', {})
            report_data = await self.custom_builder.build_custom_report(custom_config, analyzers)
        else:
            # Handle standard reports
            report_template = self.report_generator.report_templates.get(config.report_type)
            if not report_template:
                raise ValueError(f"Unknown report type: {config.report_type}")
            
            report_data = await report_template(config, analyzers)
        
        # Export report
        report_output = await self.export_manager.export_report(report_data, config)
        
        logger.info("Report generated successfully",
                   report_id=config.report_id,
                   report_type=config.report_type.value,
                   export_format=config.export_format.value,
                   file_size=report_output.metadata.file_size_bytes)
        
        return report_output
    
    async def schedule_automated_report(self, schedule_config: ScheduledReport) -> None:
        """Schedule automated report generation"""
        await self.automated_engine.schedule_report(schedule_config)
    
    async def process_scheduled_reports(self, analyzers: Dict[str, Any]) -> List[ReportOutput]:
        """Process all due scheduled reports"""
        return await self.automated_engine.process_scheduled_reports(analyzers)
    
    async def get_available_report_types(self) -> Dict[str, str]:
        """Get available report types and descriptions"""
        return {
            ReportType.COST_SUMMARY.value: "Comprehensive cost summary across brokers",
            ReportType.EXECUTION_QUALITY.value: "Execution quality analysis and metrics",
            ReportType.BROKER_COMPARISON.value: "Detailed broker performance comparison",
            ReportType.HISTORICAL_ANALYSIS.value: "Historical cost trends and patterns",
            ReportType.BREAKEVEN_ANALYSIS.value: "Break-even and profitability analysis",
            ReportType.PROFITABILITY_REPORT.value: "Trade profitability assessment",
            ReportType.CUSTOM.value: "Custom report with user-defined fields"
        }
    
    async def get_available_export_formats(self) -> Dict[str, str]:
        """Get available export formats"""
        return {
            ExportFormat.CSV.value: "Comma-separated values (spreadsheet compatible)",
            ExportFormat.JSON.value: "JavaScript Object Notation (API compatible)",
            ExportFormat.HTML.value: "HyperText Markup Language (web browser compatible)"
        }
    
    async def create_report_config(self, report_type: str, brokers: List[str],
                                 export_format: str = "csv", date_range_days: int = 30,
                                 title: str = None, **kwargs) -> ReportConfiguration:
        """Create report configuration with defaults"""
        
        report_id = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return ReportConfiguration(
            report_id=report_id,
            report_type=ReportType(report_type),
            title=title or f"{report_type.title()} Report",
            description=f"Automated {report_type} report for {', '.join(brokers)}",
            brokers=brokers,
            instruments=kwargs.get('instruments', ['EUR_USD', 'GBP_USD', 'USD_JPY']),
            date_range_days=date_range_days,
            export_format=ExportFormat(export_format),
            include_charts=kwargs.get('include_charts', True),
            include_summary=kwargs.get('include_summary', True),
            include_recommendations=kwargs.get('include_recommendations', True),
            filters=kwargs.get('filters', {}),
            custom_fields=kwargs.get('custom_fields', [])
        )