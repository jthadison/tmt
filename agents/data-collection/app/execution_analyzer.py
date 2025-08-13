"""
Execution quality monitoring and analysis system.

This module implements comprehensive execution quality tracking including
slippage analysis, latency measurement, fill quality, and market impact assessment.
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
import statistics
import logging
from dataclasses import dataclass, field
from collections import defaultdict

from .data_models import (
    ComprehensiveTradeRecord,
    ExecutionQualityMetrics,
    SlippageAnalysis,
    ExecutionTiming,
    FillQuality,
    MarketImpact,
)


logger = logging.getLogger(__name__)


class SlippageMeasurement:
    """Implements sophisticated slippage measurement algorithms."""
    
    def calculate_slippage(
        self,
        expected_price: Decimal,
        actual_price: Decimal,
        symbol: str,
        direction: str
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate slippage in pips and percentage.
        
        Returns:
            Tuple of (slippage_pips, slippage_percentage)
        """
        # Get pip value for symbol
        pip_value = self._get_pip_value(symbol)
        
        # Calculate raw price difference
        price_diff = actual_price - expected_price
        
        # Adjust for trade direction
        if direction == "short":
            price_diff = -price_diff  # Reverse for short positions
        
        # Convert to pips
        slippage_pips = price_diff / pip_value
        
        # Calculate percentage slippage
        slippage_percentage = (price_diff / expected_price) * Decimal("100")
        
        return slippage_pips, slippage_percentage
    
    def analyze_slippage_distribution(
        self,
        records: List[ComprehensiveTradeRecord],
        timeframe_start: datetime,
        timeframe_end: datetime
    ) -> SlippageAnalysis:
        """Analyze slippage distribution across multiple trades."""
        
        if not records:
            return self._create_empty_slippage_analysis()
        
        slippages = [r.execution_quality.slippage for r in records]
        slippage_percentages = [r.execution_quality.slippage_percentage for r in records]
        
        # Calculate basic statistics
        float_slippages = [float(s) for s in slippages]
        average_slippage = Decimal(str(statistics.mean(float_slippages)))
        
        try:
            slippage_std = Decimal(str(statistics.stdev(float_slippages)))
        except statistics.StatisticsError:
            slippage_std = Decimal("0")
        
        # Create slippage distribution histogram
        distribution = self._create_slippage_histogram(slippages)
        
        # Calculate positive vs negative slippage percentages
        positive_slippage_count = len([s for s in slippages if s > 0])
        negative_slippage_count = len([s for s in slippages if s < 0])
        total_count = len(slippages)
        
        positive_percentage = Decimal(str(positive_slippage_count / total_count * 100)) if total_count > 0 else Decimal("0")
        negative_percentage = Decimal(str(negative_slippage_count / total_count * 100)) if total_count > 0 else Decimal("0")
        
        # Analyze by symbol
        slippage_by_symbol = self._analyze_slippage_by_symbol(records)
        
        # Analyze by session
        slippage_by_session = self._analyze_slippage_by_session(records)
        
        return SlippageAnalysis(
            average_slippage=average_slippage,
            slippage_standard_deviation=slippage_std,
            slippage_distribution=distribution,
            positive_slippage=positive_percentage,
            negative_slippage=negative_percentage,
            slippage_by_symbol=slippage_by_symbol,
            slippage_by_session=slippage_by_session
        )
    
    def _get_pip_value(self, symbol: str) -> Decimal:
        """Get pip value for currency pair."""
        # Standard pip values for major pairs
        pip_values = {
            "EURUSD": Decimal("0.0001"),
            "GBPUSD": Decimal("0.0001"),
            "USDJPY": Decimal("0.01"),
            "USDCHF": Decimal("0.0001"),
            "AUDUSD": Decimal("0.0001"),
            "USDCAD": Decimal("0.0001"),
            "NZDUSD": Decimal("0.0001"),
        }
        
        return pip_values.get(symbol, Decimal("0.0001"))  # Default to 0.0001
    
    def _create_slippage_histogram(self, slippages: List[Decimal]) -> Dict[str, int]:
        """Create histogram of slippage distribution."""
        histogram = defaultdict(int)
        
        for slippage in slippages:
            # Create buckets: <-5, -5 to -2, -2 to -1, -1 to 0, 0 to 1, 1 to 2, 2 to 5, >5
            if slippage < -5:
                histogram["< -5 pips"] += 1
            elif slippage < -2:
                histogram["-5 to -2 pips"] += 1
            elif slippage < -1:
                histogram["-2 to -1 pips"] += 1
            elif slippage < 0:
                histogram["-1 to 0 pips"] += 1
            elif slippage < 1:
                histogram["0 to 1 pips"] += 1
            elif slippage < 2:
                histogram["1 to 2 pips"] += 1
            elif slippage < 5:
                histogram["2 to 5 pips"] += 1
            else:
                histogram["> 5 pips"] += 1
        
        return dict(histogram)
    
    def _analyze_slippage_by_symbol(self, records: List[ComprehensiveTradeRecord]) -> Dict[str, Decimal]:
        """Analyze average slippage by trading symbol."""
        symbol_slippages = defaultdict(list)
        
        for record in records:
            symbol = record.trade_details.symbol
            symbol_slippages[symbol].append(record.execution_quality.slippage)
        
        symbol_averages = {}
        for symbol, slippages in symbol_slippages.items():
            if slippages:
                float_slippages = [float(s) for s in slippages]
                symbol_averages[symbol] = Decimal(str(statistics.mean(float_slippages)))
        
        return symbol_averages
    
    def _analyze_slippage_by_session(self, records: List[ComprehensiveTradeRecord]) -> Dict[str, Decimal]:
        """Analyze average slippage by trading session."""
        session_slippages = defaultdict(list)
        
        for record in records:
            session = record.market_conditions.session.value
            session_slippages[session].append(record.execution_quality.slippage)
        
        session_averages = {}
        for session, slippages in session_slippages.items():
            if slippages:
                float_slippages = [float(s) for s in slippages]
                session_averages[session] = Decimal(str(statistics.mean(float_slippages)))
        
        return session_averages
    
    def _create_empty_slippage_analysis(self) -> SlippageAnalysis:
        """Create empty slippage analysis."""
        return SlippageAnalysis(
            average_slippage=Decimal("0"),
            slippage_standard_deviation=Decimal("0"),
            slippage_distribution={},
            positive_slippage=Decimal("0"),
            negative_slippage=Decimal("0"),
            slippage_by_symbol={},
            slippage_by_session={}
        )


class ExecutionLatencyTracker:
    """Tracks and analyzes execution latency metrics."""
    
    def analyze_execution_timing(
        self,
        records: List[ComprehensiveTradeRecord]
    ) -> ExecutionTiming:
        """Analyze execution timing across multiple trades."""
        
        if not records:
            return self._create_empty_timing_analysis()
        
        latencies = [r.execution_quality.execution_latency for r in records if r.execution_quality.execution_latency > 0]
        
        if not latencies:
            return self._create_empty_timing_analysis()
        
        # Calculate basic latency statistics
        average_latency = Decimal(str(statistics.mean(latencies)))
        
        try:
            latency_std = Decimal(str(statistics.stdev(latencies)))
        except statistics.StatisticsError:
            latency_std = Decimal("0")
        
        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        percentiles = self._calculate_percentiles(sorted_latencies)
        
        # Calculate failure rates
        total_orders = len(records)
        timeouts = len([r for r in records if r.execution_quality.execution_latency > 30000])  # > 30 seconds
        rejections = sum(r.execution_quality.rejection_count for r in records)
        requotes = sum(r.execution_quality.requote_count for r in records)
        
        timeout_rate = Decimal(str(timeouts / total_orders)) if total_orders > 0 else Decimal("0")
        rejection_rate = Decimal(str(rejections / total_orders)) if total_orders > 0 else Decimal("0")
        requote_rate = Decimal(str(requotes / total_orders)) if total_orders > 0 else Decimal("0")
        
        return ExecutionTiming(
            average_latency=average_latency,
            latency_standard_deviation=latency_std,
            latency_percentiles=percentiles,
            timeout_rate=timeout_rate,
            rejection_rate=rejection_rate,
            requote_rate=requote_rate
        )
    
    def _calculate_percentiles(self, sorted_latencies: List[int]) -> Dict[str, Decimal]:
        """Calculate latency percentiles."""
        if not sorted_latencies:
            return {"50th": Decimal("0"), "90th": Decimal("0"), "99th": Decimal("0")}
        
        def percentile(data: List[int], p: int) -> Decimal:
            index = int(len(data) * p / 100)
            index = min(index, len(data) - 1)
            return Decimal(str(data[index]))
        
        return {
            "50th": percentile(sorted_latencies, 50),
            "90th": percentile(sorted_latencies, 90),
            "99th": percentile(sorted_latencies, 99)
        }
    
    def _create_empty_timing_analysis(self) -> ExecutionTiming:
        """Create empty timing analysis."""
        return ExecutionTiming(
            average_latency=Decimal("0"),
            latency_standard_deviation=Decimal("0"),
            latency_percentiles={"50th": Decimal("0"), "90th": Decimal("0"), "99th": Decimal("0")},
            timeout_rate=Decimal("0"),
            rejection_rate=Decimal("0"),
            requote_rate=Decimal("0")
        )


class FillQualityMetrics:
    """Analyzes order fill quality and completion rates."""
    
    def analyze_fill_quality(
        self,
        records: List[ComprehensiveTradeRecord]
    ) -> FillQuality:
        """Analyze fill quality across multiple trades."""
        
        if not records:
            return self._create_empty_fill_quality()
        
        total_orders = len(records)
        
        # Calculate fill rates
        full_fills = len([r for r in records if r.execution_quality.partial_fill_count == 0])
        partial_fills = total_orders - full_fills
        
        full_fill_rate = Decimal(str(full_fills / total_orders)) if total_orders > 0 else Decimal("0")
        partial_fill_rate = Decimal(str(partial_fills / total_orders)) if total_orders > 0 else Decimal("0")
        
        # Calculate average fill ratio
        # For this example, we'll assume full fills have ratio 1.0 and estimate partial fills
        fill_ratios = []
        for record in records:
            if record.execution_quality.partial_fill_count == 0:
                fill_ratios.append(1.0)
            else:
                # Estimate fill ratio based on partial fill count (simplified)
                estimated_ratio = max(0.5, 1.0 - (record.execution_quality.partial_fill_count * 0.1))
                fill_ratios.append(estimated_ratio)
        
        average_fill_ratio = Decimal(str(statistics.mean(fill_ratios))) if fill_ratios else Decimal("0")
        
        # Create fill time distribution
        fill_time_distribution = self._create_fill_time_distribution(records)
        
        return FillQuality(
            full_fill_rate=full_fill_rate,
            partial_fill_rate=partial_fill_rate,
            average_fill_ratio=average_fill_ratio,
            fill_time_distribution=fill_time_distribution
        )
    
    def _create_fill_time_distribution(self, records: List[ComprehensiveTradeRecord]) -> Dict[str, int]:
        """Create distribution of fill times."""
        distribution = defaultdict(int)
        
        for record in records:
            latency = record.execution_quality.execution_latency
            
            # Create time buckets
            if latency < 100:
                distribution["< 100ms"] += 1
            elif latency < 500:
                distribution["100-500ms"] += 1
            elif latency < 1000:
                distribution["500ms-1s"] += 1
            elif latency < 5000:
                distribution["1-5s"] += 1
            elif latency < 30000:
                distribution["5-30s"] += 1
            else:
                distribution["> 30s"] += 1
        
        return dict(distribution)
    
    def _create_empty_fill_quality(self) -> FillQuality:
        """Create empty fill quality analysis."""
        return FillQuality(
            full_fill_rate=Decimal("0"),
            partial_fill_rate=Decimal("0"),
            average_fill_ratio=Decimal("0"),
            fill_time_distribution={}
        )


class MarketImpactMeasurement:
    """Measures market impact of trade executions."""
    
    def analyze_market_impact(
        self,
        records: List[ComprehensiveTradeRecord]
    ) -> MarketImpact:
        """Analyze market impact across multiple trades."""
        
        if not records:
            return self._create_empty_market_impact()
        
        # Calculate average market impact
        impacts = [r.execution_quality.market_impact for r in records]
        float_impacts = [float(i) for i in impacts if i != 0]
        
        average_impact = Decimal(str(statistics.mean(float_impacts))) if float_impacts else Decimal("0")
        
        # Analyze impact by position size
        impact_by_size = self._analyze_impact_by_size(records)
        
        # Analyze impact by liquidity conditions
        impact_by_liquidity = self._analyze_impact_by_liquidity(records)
        
        # Estimate impact recovery time (simplified)
        impact_recovery_time = self._estimate_impact_recovery_time(records)
        
        return MarketImpact(
            average_impact=average_impact,
            impact_by_size=impact_by_size,
            impact_by_liquidity=impact_by_liquidity,
            impact_recovery_time=impact_recovery_time
        )
    
    def _analyze_impact_by_size(self, records: List[ComprehensiveTradeRecord]) -> Dict[str, Decimal]:
        """Analyze market impact by position size."""
        size_impacts = defaultdict(list)
        
        for record in records:
            size = float(record.trade_details.size)
            impact = record.execution_quality.market_impact
            
            # Categorize by size
            if size < 10000:
                size_impacts["small"].append(impact)
            elif size < 50000:
                size_impacts["medium"].append(impact)
            else:
                size_impacts["large"].append(impact)
        
        size_averages = {}
        for size_category, impacts in size_impacts.items():
            if impacts:
                float_impacts = [float(i) for i in impacts if i != 0]
                if float_impacts:
                    size_averages[size_category] = Decimal(str(statistics.mean(float_impacts)))
        
        return size_averages
    
    def _analyze_impact_by_liquidity(self, records: List[ComprehensiveTradeRecord]) -> Dict[str, Decimal]:
        """Analyze market impact by liquidity conditions."""
        liquidity_impacts = defaultdict(list)
        
        for record in records:
            liquidity = record.execution_quality.liquidity_at_execution
            impact = record.execution_quality.market_impact
            
            # Categorize by liquidity level
            if liquidity > Decimal("0.8"):
                liquidity_impacts["high"].append(impact)
            elif liquidity > Decimal("0.4"):
                liquidity_impacts["medium"].append(impact)
            else:
                liquidity_impacts["low"].append(impact)
        
        liquidity_averages = {}
        for liquidity_category, impacts in liquidity_impacts.items():
            if impacts:
                float_impacts = [float(i) for i in impacts if i != 0]
                if float_impacts:
                    liquidity_averages[liquidity_category] = Decimal(str(statistics.mean(float_impacts)))
        
        return liquidity_averages
    
    def _estimate_impact_recovery_time(self, records: List[ComprehensiveTradeRecord]) -> Decimal:
        """Estimate average time for market impact to recover."""
        # This is a simplified estimation - in reality would need tick data
        # For now, estimate based on volatility and market conditions
        
        recovery_times = []
        for record in records:
            volatility = record.market_conditions.volatility
            impact = record.execution_quality.market_impact
            
            # Estimate recovery time based on volatility (higher volatility = faster recovery)
            if volatility > Decimal("0.8"):
                base_recovery = 30  # 30 seconds
            elif volatility > Decimal("0.4"):
                base_recovery = 120  # 2 minutes
            else:
                base_recovery = 300  # 5 minutes
            
            # Adjust for impact magnitude
            impact_multiplier = float(impact) if impact > 0 else 1.0
            estimated_recovery = base_recovery * impact_multiplier
            recovery_times.append(estimated_recovery)
        
        return Decimal(str(statistics.mean(recovery_times))) if recovery_times else Decimal("60")
    
    def _create_empty_market_impact(self) -> MarketImpact:
        """Create empty market impact analysis."""
        return MarketImpact(
            average_impact=Decimal("0"),
            impact_by_size={},
            impact_by_liquidity={},
            impact_recovery_time=Decimal("60")
        )


class ExecutionQualityReporter:
    """Generates comprehensive execution quality reports."""
    
    def __init__(self):
        self.slippage_analyzer = SlippageMeasurement()
        self.latency_tracker = ExecutionLatencyTracker()
        self.fill_analyzer = FillQualityMetrics()
        self.impact_analyzer = MarketImpactMeasurement()
    
    def generate_execution_quality_report(
        self,
        records: List[ComprehensiveTradeRecord],
        timeframe_start: datetime,
        timeframe_end: datetime
    ) -> ExecutionQualityMetrics:
        """Generate comprehensive execution quality report."""
        
        # Analyze each component
        slippage_analysis = self.slippage_analyzer.analyze_slippage_distribution(
            records, timeframe_start, timeframe_end
        )
        
        timing_analysis = self.latency_tracker.analyze_execution_timing(records)
        
        fill_analysis = self.fill_analyzer.analyze_fill_quality(records)
        
        impact_analysis = self.impact_analyzer.analyze_market_impact(records)
        
        # Create comprehensive report
        return ExecutionQualityMetrics(
            timeframe={"start": timeframe_start, "end": timeframe_end},
            slippage=slippage_analysis,
            timing=timing_analysis,
            fill_quality=fill_analysis,
            market_impact=impact_analysis
        )
    
    def identify_execution_quality_issues(
        self,
        metrics: ExecutionQualityMetrics
    ) -> List[Dict[str, Any]]:
        """Identify execution quality issues and recommendations."""
        issues = []
        
        # Check slippage issues
        if metrics.slippage.average_slippage > Decimal("2.0"):
            issues.append({
                "type": "high_slippage",
                "severity": "high" if metrics.slippage.average_slippage > Decimal("5.0") else "medium",
                "description": f"Average slippage is {metrics.slippage.average_slippage} pips",
                "recommendation": "Review broker execution quality and consider alternative liquidity providers"
            })
        
        # Check latency issues
        if metrics.timing.average_latency > Decimal("1000"):  # > 1 second
            issues.append({
                "type": "high_latency",
                "severity": "high" if metrics.timing.average_latency > Decimal("5000") else "medium",
                "description": f"Average execution latency is {metrics.timing.average_latency}ms",
                "recommendation": "Investigate network connectivity and server location optimization"
            })
        
        # Check rejection rate
        if metrics.timing.rejection_rate > Decimal("0.05"):  # > 5%
            issues.append({
                "type": "high_rejection_rate",
                "severity": "high",
                "description": f"Order rejection rate is {metrics.timing.rejection_rate:.1%}",
                "recommendation": "Review order sizing and market conditions during order placement"
            })
        
        # Check fill quality
        if metrics.fill_quality.full_fill_rate < Decimal("0.8"):  # < 80%
            issues.append({
                "type": "poor_fill_quality",
                "severity": "medium",
                "description": f"Full fill rate is only {metrics.fill_quality.full_fill_rate:.1%}",
                "recommendation": "Consider adjusting order sizes or execution algorithms"
            })
        
        return issues