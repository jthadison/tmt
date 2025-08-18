"""
Execution Quality Analysis System - Story 8.14 Task 2

This module provides comprehensive execution quality analysis including:
- Slippage measurement and tracking
- Fill quality metrics and monitoring  
- Execution speed analysis
- Rejection rate tracking
- Quality scoring algorithms
- Execution quality reporting

Integrates with the broker cost analyzer to provide holistic trading cost analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
import statistics
from collections import defaultdict, deque

import structlog

logger = structlog.get_logger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status types"""
    FILLED = "filled"
    PARTIAL_FILL = "partial_fill"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REQUOTED = "requoted"
    PENDING = "pending"


class OrderType(str, Enum):
    """Order types for execution analysis"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


@dataclass
class ExecutionEvent:
    """Individual execution event tracking"""
    broker: str
    instrument: str
    order_id: str
    trade_id: Optional[str]
    order_type: OrderType
    side: str  # 'buy' or 'sell'
    requested_size: Decimal
    filled_size: Decimal
    requested_price: Optional[Decimal]
    fill_price: Optional[Decimal]
    expected_price: Optional[Decimal]
    status: ExecutionStatus
    timestamp_request: datetime
    timestamp_response: Optional[datetime]
    timestamp_fill: Optional[datetime]
    latency_ms: Optional[float]
    slippage_pips: Optional[Decimal]
    slippage_bps: Optional[Decimal]
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: Optional[str] = None
    requote_count: int = 0
    partial_fills: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class QualityMetrics:
    """Execution quality metrics for a period"""
    broker: str
    instrument: Optional[str]
    period_start: datetime
    period_end: datetime
    total_orders: int
    filled_orders: int
    partial_fills: int
    rejections: int
    cancellations: int
    requotes: int
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    avg_slippage_pips: float
    median_slippage_pips: float
    positive_slippage_rate: float
    fill_rate: float
    rejection_rate: float
    partial_fill_rate: float
    requote_rate: float
    quality_score: float
    execution_efficiency: float
    cost_efficiency: float


@dataclass
class SlippageAnalysis:
    """Detailed slippage analysis"""
    broker: str
    instrument: str
    period_start: datetime
    period_end: datetime
    total_executions: int
    avg_slippage_pips: Decimal
    median_slippage_pips: Decimal
    std_slippage_pips: Decimal
    positive_slippage_count: int
    negative_slippage_count: int
    zero_slippage_count: int
    slippage_distribution: Dict[str, int]  # ranges -> counts
    worst_slippage: Decimal
    best_slippage: Decimal
    slippage_by_size: Dict[str, Decimal]  # size ranges -> avg slippage
    slippage_by_time: Dict[str, Decimal]  # time periods -> avg slippage
    market_impact_analysis: Dict[str, Any]


class SlippageMeasurementSystem:
    """Advanced slippage measurement and analysis"""
    
    def __init__(self):
        self.slippage_data: Dict[str, List[ExecutionEvent]] = defaultdict(list)
        self.benchmark_prices: Dict[str, Dict[str, Decimal]] = defaultdict(dict)
        
    async def record_execution(self, execution: ExecutionEvent) -> None:
        """Record execution event for slippage analysis"""
        # Calculate slippage if not already calculated
        if execution.slippage_pips is None and execution.fill_price and execution.expected_price:
            execution.slippage_pips = await self._calculate_slippage_pips(
                execution.instrument, execution.expected_price, execution.fill_price, execution.side
            )
        
        if execution.slippage_bps is None and execution.fill_price and execution.expected_price:
            execution.slippage_bps = await self._calculate_slippage_bps(
                execution.expected_price, execution.fill_price, execution.side
            )
        
        self.slippage_data[execution.broker].append(execution)
        
        logger.info("Execution recorded for slippage analysis",
                   broker=execution.broker,
                   instrument=execution.instrument,
                   order_id=execution.order_id,
                   slippage_pips=float(execution.slippage_pips) if execution.slippage_pips else None)
    
    async def _calculate_slippage_pips(self, instrument: str, expected_price: Decimal, 
                                     fill_price: Decimal, side: str) -> Decimal:
        """Calculate slippage in pips"""
        pip_size = await self._get_pip_size(instrument)
        price_diff = fill_price - expected_price
        
        # Slippage is negative when execution is worse than expected
        if side.lower() == 'buy':
            slippage = -price_diff / pip_size  # Higher fill price = negative slippage
        else:
            slippage = price_diff / pip_size   # Lower fill price = negative slippage
            
        return slippage
    
    async def _calculate_slippage_bps(self, expected_price: Decimal, 
                                    fill_price: Decimal, side: str) -> Decimal:
        """Calculate slippage in basis points"""
        price_diff = abs(fill_price - expected_price)
        slippage_bps = (price_diff / expected_price) * 10000
        
        # Apply sign based on whether slippage was favorable
        if side.lower() == 'buy':
            if fill_price > expected_price:
                slippage_bps = -slippage_bps  # Unfavorable
        else:
            if fill_price < expected_price:
                slippage_bps = -slippage_bps  # Unfavorable
                
        return slippage_bps
    
    async def _get_pip_size(self, instrument: str) -> Decimal:
        """Get pip size for instrument"""
        # Standard pip sizes for major forex pairs
        pip_sizes = {
            'EUR_USD': Decimal('0.0001'),
            'GBP_USD': Decimal('0.0001'),
            'USD_JPY': Decimal('0.01'),
            'USD_CHF': Decimal('0.0001'),
            'AUD_USD': Decimal('0.0001'),
            'USD_CAD': Decimal('0.0001'),
            'NZD_USD': Decimal('0.0001'),
        }
        
        return pip_sizes.get(instrument, Decimal('0.0001'))
    
    async def analyze_slippage(self, broker: str, instrument: str = None, 
                             period_days: int = 30) -> SlippageAnalysis:
        """Comprehensive slippage analysis"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)
        
        # Filter executions
        executions = [
            ex for ex in self.slippage_data[broker]
            if start_time <= ex.timestamp_fill <= end_time
            and (instrument is None or ex.instrument == instrument)
            and ex.status == ExecutionStatus.FILLED
            and ex.slippage_pips is not None
        ]
        
        if not executions:
            return SlippageAnalysis(
                broker=broker,
                instrument=instrument or "ALL",
                period_start=start_time,
                period_end=end_time,
                total_executions=0,
                avg_slippage_pips=Decimal('0'),
                median_slippage_pips=Decimal('0'),
                std_slippage_pips=Decimal('0'),
                positive_slippage_count=0,
                negative_slippage_count=0,
                zero_slippage_count=0,
                slippage_distribution={},
                worst_slippage=Decimal('0'),
                best_slippage=Decimal('0'),
                slippage_by_size={},
                slippage_by_time={},
                market_impact_analysis={}
            )
        
        slippages = [float(ex.slippage_pips) for ex in executions]
        
        # Basic statistics
        avg_slippage = Decimal(str(statistics.mean(slippages)))
        median_slippage = Decimal(str(statistics.median(slippages)))
        std_slippage = Decimal(str(statistics.stdev(slippages))) if len(slippages) > 1 else Decimal('0')
        
        # Distribution analysis
        positive_count = sum(1 for s in slippages if s > 0)
        negative_count = sum(1 for s in slippages if s < 0)
        zero_count = sum(1 for s in slippages if s == 0)
        
        # Slippage distribution by ranges
        distribution = self._calculate_slippage_distribution(slippages)
        
        # Size-based analysis
        size_analysis = self._analyze_slippage_by_size(executions)
        
        # Time-based analysis
        time_analysis = self._analyze_slippage_by_time(executions)
        
        # Market impact analysis
        market_impact = self._analyze_market_impact(executions)
        
        return SlippageAnalysis(
            broker=broker,
            instrument=instrument or "ALL",
            period_start=start_time,
            period_end=end_time,
            total_executions=len(executions),
            avg_slippage_pips=avg_slippage,
            median_slippage_pips=median_slippage,
            std_slippage_pips=std_slippage,
            positive_slippage_count=positive_count,
            negative_slippage_count=negative_count,
            zero_slippage_count=zero_count,
            slippage_distribution=distribution,
            worst_slippage=Decimal(str(min(slippages))),
            best_slippage=Decimal(str(max(slippages))),
            slippage_by_size=size_analysis,
            slippage_by_time=time_analysis,
            market_impact_analysis=market_impact
        )
    
    def _calculate_slippage_distribution(self, slippages: List[float]) -> Dict[str, int]:
        """Calculate slippage distribution by ranges"""
        ranges = [
            (-float('inf'), -2.0, "< -2.0 pips"),
            (-2.0, -1.0, "-2.0 to -1.0 pips"),
            (-1.0, -0.5, "-1.0 to -0.5 pips"),
            (-0.5, 0.0, "-0.5 to 0.0 pips"),
            (0.0, 0.0, "0.0 pips"),
            (0.0, 0.5, "0.0 to 0.5 pips"),
            (0.5, 1.0, "0.5 to 1.0 pips"),
            (1.0, 2.0, "1.0 to 2.0 pips"),
            (2.0, float('inf'), "> 2.0 pips")
        ]
        
        distribution = {}
        for min_val, max_val, label in ranges:
            if label == "0.0 pips":
                count = sum(1 for s in slippages if s == 0.0)
            else:
                count = sum(1 for s in slippages if min_val < s <= max_val)
            distribution[label] = count
        
        return distribution
    
    def _analyze_slippage_by_size(self, executions: List[ExecutionEvent]) -> Dict[str, Decimal]:
        """Analyze slippage by trade size"""
        size_buckets = defaultdict(list)
        
        for ex in executions:
            size = float(ex.filled_size)
            if size <= 10000:
                bucket = "0-10K"
            elif size <= 50000:
                bucket = "10K-50K"
            elif size <= 100000:
                bucket = "50K-100K"
            elif size <= 500000:
                bucket = "100K-500K"
            else:
                bucket = "500K+"
            
            size_buckets[bucket].append(float(ex.slippage_pips))
        
        return {
            bucket: Decimal(str(statistics.mean(slippages)))
            for bucket, slippages in size_buckets.items()
            if slippages
        }
    
    def _analyze_slippage_by_time(self, executions: List[ExecutionEvent]) -> Dict[str, Decimal]:
        """Analyze slippage by time of day"""
        time_buckets = defaultdict(list)
        
        for ex in executions:
            hour = ex.timestamp_fill.hour
            if 0 <= hour < 6:
                bucket = "00:00-06:00"
            elif 6 <= hour < 12:
                bucket = "06:00-12:00"
            elif 12 <= hour < 18:
                bucket = "12:00-18:00"
            else:
                bucket = "18:00-24:00"
            
            time_buckets[bucket].append(float(ex.slippage_pips))
        
        return {
            bucket: Decimal(str(statistics.mean(slippages)))
            for bucket, slippages in time_buckets.items()
            if slippages
        }
    
    def _analyze_market_impact(self, executions: List[ExecutionEvent]) -> Dict[str, Any]:
        """Analyze market impact on slippage"""
        volatility_impact = defaultdict(list)
        spread_impact = defaultdict(list)
        
        for ex in executions:
            market_data = ex.market_conditions
            
            # Volatility impact
            if 'volatility' in market_data:
                vol = market_data['volatility']
                if vol < 0.01:
                    volatility_impact['low'].append(float(ex.slippage_pips))
                elif vol < 0.02:
                    volatility_impact['medium'].append(float(ex.slippage_pips))
                else:
                    volatility_impact['high'].append(float(ex.slippage_pips))
            
            # Spread impact
            if 'spread' in market_data:
                spread = market_data['spread']
                if spread < 1.0:
                    spread_impact['tight'].append(float(ex.slippage_pips))
                elif spread < 2.0:
                    spread_impact['normal'].append(float(ex.slippage_pips))
                else:
                    spread_impact['wide'].append(float(ex.slippage_pips))
        
        return {
            'volatility_impact': {
                level: statistics.mean(slippages) if slippages else 0
                for level, slippages in volatility_impact.items()
            },
            'spread_impact': {
                level: statistics.mean(slippages) if slippages else 0
                for level, slippages in spread_impact.items()
            }
        }


class FillQualityTracker:
    """Track and analyze fill quality metrics"""
    
    def __init__(self):
        self.execution_events: Dict[str, List[ExecutionEvent]] = defaultdict(list)
        self.fill_statistics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
    async def record_execution_event(self, execution: ExecutionEvent) -> None:
        """Record execution event for quality tracking"""
        self.execution_events[execution.broker].append(execution)
        await self._update_fill_statistics(execution.broker)
        
        logger.info("Fill quality event recorded",
                   broker=execution.broker,
                   instrument=execution.instrument,
                   status=execution.status.value,
                   fill_rate=execution.filled_size / execution.requested_size if execution.requested_size > 0 else 0)
    
    async def _update_fill_statistics(self, broker: str) -> None:
        """Update running fill statistics"""
        recent_events = [
            ex for ex in self.execution_events[broker]
            if ex.timestamp_request >= datetime.utcnow() - timedelta(hours=24)
        ]
        
        if not recent_events:
            return
        
        total_orders = len(recent_events)
        filled_orders = sum(1 for ex in recent_events if ex.status == ExecutionStatus.FILLED)
        partial_fills = sum(1 for ex in recent_events if ex.status == ExecutionStatus.PARTIAL_FILL)
        rejections = sum(1 for ex in recent_events if ex.status == ExecutionStatus.REJECTED)
        
        self.fill_statistics[broker] = {
            'total_orders': total_orders,
            'fill_rate': filled_orders / total_orders,
            'partial_fill_rate': partial_fills / total_orders,
            'rejection_rate': rejections / total_orders,
            'last_updated': datetime.utcnow()
        }
    
    async def get_fill_quality_metrics(self, broker: str, period_hours: int = 24) -> Dict[str, float]:
        """Get comprehensive fill quality metrics"""
        cutoff = datetime.utcnow() - timedelta(hours=period_hours)
        recent_events = [
            ex for ex in self.execution_events[broker]
            if ex.timestamp_request >= cutoff
        ]
        
        if not recent_events:
            return {}
        
        total = len(recent_events)
        filled = sum(1 for ex in recent_events if ex.status == ExecutionStatus.FILLED)
        partial = sum(1 for ex in recent_events if ex.status == ExecutionStatus.PARTIAL_FILL)
        rejected = sum(1 for ex in recent_events if ex.status == ExecutionStatus.REJECTED)
        requoted = sum(1 for ex in recent_events if ex.requote_count > 0)
        
        # Calculate average fill percentages
        fill_percentages = []
        for ex in recent_events:
            if ex.requested_size > 0:
                fill_pct = float(ex.filled_size / ex.requested_size)
                fill_percentages.append(fill_pct)
        
        avg_fill_percentage = statistics.mean(fill_percentages) if fill_percentages else 0
        
        return {
            'total_orders': total,
            'fill_rate': filled / total,
            'partial_fill_rate': partial / total,
            'rejection_rate': rejected / total,
            'requote_rate': requoted / total,
            'avg_fill_percentage': avg_fill_percentage,
            'complete_fill_rate': sum(1 for pct in fill_percentages if pct >= 1.0) / len(fill_percentages) if fill_percentages else 0
        }


class ExecutionSpeedMonitor:
    """Monitor and analyze execution speed"""
    
    def __init__(self):
        self.latency_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.speed_stats: Dict[str, Dict[str, float]] = defaultdict(dict)
        
    async def record_execution_latency(self, broker: str, instrument: str, 
                                     order_type: OrderType, latency_ms: float) -> None:
        """Record execution latency"""
        timestamp = datetime.utcnow()
        
        self.latency_data[broker].append({
            'timestamp': timestamp,
            'instrument': instrument,
            'order_type': order_type.value,
            'latency_ms': latency_ms
        })
        
        await self._update_speed_statistics(broker)
        
        logger.info("Execution latency recorded",
                   broker=broker,
                   instrument=instrument,
                   latency_ms=latency_ms)
    
    async def _update_speed_statistics(self, broker: str) -> None:
        """Update running speed statistics"""
        recent_data = [
            entry for entry in self.latency_data[broker]
            if entry['timestamp'] >= datetime.utcnow() - timedelta(hours=1)
        ]
        
        if not recent_data:
            return
        
        latencies = [entry['latency_ms'] for entry in recent_data]
        
        self.speed_stats[broker] = {
            'avg_latency_ms': statistics.mean(latencies),
            'median_latency_ms': statistics.median(latencies),
            'p95_latency_ms': self._percentile(latencies, 95),
            'p99_latency_ms': self._percentile(latencies, 99),
            'max_latency_ms': max(latencies),
            'min_latency_ms': min(latencies),
            'sample_count': len(latencies),
            'last_updated': datetime.utcnow()
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100) * (len(sorted_data) - 1))
        return sorted_data[index]
    
    async def get_speed_metrics(self, broker: str, period_hours: int = 24) -> Dict[str, float]:
        """Get execution speed metrics"""
        cutoff = datetime.utcnow() - timedelta(hours=period_hours)
        recent_data = [
            entry for entry in self.latency_data[broker]
            if entry['timestamp'] >= cutoff
        ]
        
        if not recent_data:
            return {}
        
        latencies = [entry['latency_ms'] for entry in recent_data]
        
        return {
            'avg_latency_ms': statistics.mean(latencies),
            'median_latency_ms': statistics.median(latencies),
            'p95_latency_ms': self._percentile(latencies, 95),
            'p99_latency_ms': self._percentile(latencies, 99),
            'std_latency_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0,
            'sample_count': len(latencies),
            'fast_execution_rate': sum(1 for l in latencies if l < 100) / len(latencies)  # < 100ms
        }


class RejectionRateTracker:
    """Track and analyze order rejection rates"""
    
    def __init__(self):
        self.rejection_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.rejection_reasons: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
    async def record_rejection(self, broker: str, instrument: str, order_type: OrderType,
                             reason: str, market_conditions: Dict[str, Any] = None) -> None:
        """Record order rejection"""
        timestamp = datetime.utcnow()
        
        rejection_event = {
            'timestamp': timestamp,
            'instrument': instrument,
            'order_type': order_type.value,
            'reason': reason,
            'market_conditions': market_conditions or {}
        }
        
        self.rejection_data[broker].append(rejection_event)
        self.rejection_reasons[broker][reason] += 1
        
        logger.warning("Order rejection recorded",
                      broker=broker,
                      instrument=instrument,
                      reason=reason)
    
    async def get_rejection_analysis(self, broker: str, period_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive rejection analysis"""
        cutoff = datetime.utcnow() - timedelta(hours=period_hours)
        recent_rejections = [
            rej for rej in self.rejection_data[broker]
            if rej['timestamp'] >= cutoff
        ]
        
        if not recent_rejections:
            return {'total_rejections': 0}
        
        # Analyze rejection reasons
        reason_counts = defaultdict(int)
        instrument_rejections = defaultdict(int)
        order_type_rejections = defaultdict(int)
        
        for rejection in recent_rejections:
            reason_counts[rejection['reason']] += 1
            instrument_rejections[rejection['instrument']] += 1
            order_type_rejections[rejection['order_type']] += 1
        
        return {
            'total_rejections': len(recent_rejections),
            'rejection_reasons': dict(reason_counts),
            'rejections_by_instrument': dict(instrument_rejections),
            'rejections_by_order_type': dict(order_type_rejections),
            'top_rejection_reason': max(reason_counts.items(), key=lambda x: x[1])[0] if reason_counts else None
        }


class QualityScoringAlgorithm:
    """Advanced quality scoring algorithm"""
    
    def __init__(self):
        self.scoring_weights = {
            'fill_rate': 0.25,
            'latency': 0.20,
            'slippage': 0.25,
            'rejection_rate': 0.15,
            'partial_fill_rate': 0.10,
            'requote_rate': 0.05
        }
        
    async def calculate_quality_score(self, metrics: Dict[str, float]) -> float:
        """Calculate composite quality score (0-100)"""
        scores = {}
        
        # Fill rate score (higher is better)
        fill_rate = metrics.get('fill_rate', 0)
        scores['fill_rate'] = min(100, fill_rate * 100)
        
        # Latency score (lower is better, penalize after 100ms)
        avg_latency = metrics.get('avg_latency_ms', 1000)
        scores['latency'] = max(0, 100 - (avg_latency - 50) / 5)
        
        # Slippage score (lower absolute slippage is better)
        avg_slippage = abs(metrics.get('avg_slippage_pips', 5))
        scores['slippage'] = max(0, 100 - avg_slippage * 20)
        
        # Rejection rate score (lower is better)
        rejection_rate = metrics.get('rejection_rate', 1)
        scores['rejection_rate'] = max(0, 100 - rejection_rate * 100)
        
        # Partial fill rate score (lower is better for quality)
        partial_fill_rate = metrics.get('partial_fill_rate', 1)
        scores['partial_fill_rate'] = max(0, 100 - partial_fill_rate * 50)
        
        # Requote rate score (lower is better)
        requote_rate = metrics.get('requote_rate', 1)
        scores['requote_rate'] = max(0, 100 - requote_rate * 100)
        
        # Calculate weighted composite score
        composite_score = sum(
            scores[metric] * weight
            for metric, weight in self.scoring_weights.items()
            if metric in scores
        )
        
        return min(100, max(0, composite_score))
    
    async def calculate_execution_efficiency(self, metrics: Dict[str, float]) -> float:
        """Calculate execution efficiency score"""
        fill_rate = metrics.get('fill_rate', 0)
        avg_fill_pct = metrics.get('avg_fill_percentage', 0)
        rejection_rate = metrics.get('rejection_rate', 1)
        
        # Efficiency is based on successful execution without delays
        efficiency = (fill_rate * avg_fill_pct) * (1 - rejection_rate) * 100
        return min(100, max(0, efficiency))
    
    async def calculate_cost_efficiency(self, cost_metrics: Dict[str, float], 
                                      quality_metrics: Dict[str, float]) -> float:
        """Calculate cost efficiency score"""
        # Lower cost with maintained quality is better
        avg_cost_bps = cost_metrics.get('avg_cost_bps', 10)
        quality_score = await self.calculate_quality_score(quality_metrics)
        
        # Normalize cost (assume 5 bps is reasonable baseline)
        cost_score = max(0, 100 - (avg_cost_bps - 5) * 10)
        
        # Weight quality vs cost (70% quality, 30% cost)
        cost_efficiency = (quality_score * 0.7) + (cost_score * 0.3)
        
        return min(100, max(0, cost_efficiency))


class ExecutionQualityAnalyzer:
    """Main execution quality analysis system"""
    
    def __init__(self):
        self.slippage_system = SlippageMeasurementSystem()
        self.fill_tracker = FillQualityTracker()
        self.speed_monitor = ExecutionSpeedMonitor()
        self.rejection_tracker = RejectionRateTracker()
        self.quality_scorer = QualityScoringAlgorithm()
        
    async def record_execution(self, execution_data: Dict[str, Any]) -> ExecutionEvent:
        """Record comprehensive execution data"""
        # Create execution event
        execution = ExecutionEvent(
            broker=execution_data['broker'],
            instrument=execution_data['instrument'],
            order_id=execution_data['order_id'],
            trade_id=execution_data.get('trade_id'),
            order_type=OrderType(execution_data['order_type']),
            side=execution_data['side'],
            requested_size=Decimal(str(execution_data['requested_size'])),
            filled_size=Decimal(str(execution_data.get('filled_size', 0))),
            requested_price=Decimal(str(execution_data['requested_price'])) if execution_data.get('requested_price') else None,
            fill_price=Decimal(str(execution_data['fill_price'])) if execution_data.get('fill_price') else None,
            expected_price=Decimal(str(execution_data['expected_price'])) if execution_data.get('expected_price') else None,
            status=ExecutionStatus(execution_data['status']),
            timestamp_request=execution_data['timestamp_request'],
            timestamp_response=execution_data.get('timestamp_response'),
            timestamp_fill=execution_data.get('timestamp_fill'),
            latency_ms=execution_data.get('latency_ms'),
            rejection_reason=execution_data.get('rejection_reason'),
            requote_count=execution_data.get('requote_count', 0),
            market_conditions=execution_data.get('market_conditions', {})
        )
        
        # Record in all subsystems
        await self.slippage_system.record_execution(execution)
        await self.fill_tracker.record_execution_event(execution)
        
        if execution.latency_ms:
            await self.speed_monitor.record_execution_latency(
                execution.broker, execution.instrument, execution.order_type, execution.latency_ms
            )
        
        if execution.status == ExecutionStatus.REJECTED:
            await self.rejection_tracker.record_rejection(
                execution.broker, execution.instrument, execution.order_type,
                execution.rejection_reason or "Unknown", execution.market_conditions
            )
        
        return execution
    
    async def generate_quality_report(self, broker: str, instrument: str = None, 
                                    period_days: int = 7) -> QualityMetrics:
        """Generate comprehensive quality report"""
        # Get metrics from all subsystems
        fill_metrics = await self.fill_tracker.get_fill_quality_metrics(broker, period_days * 24)
        speed_metrics = await self.speed_monitor.get_speed_metrics(broker, period_days * 24)
        rejection_analysis = await self.rejection_tracker.get_rejection_analysis(broker, period_days * 24)
        slippage_analysis = await self.slippage_system.analyze_slippage(broker, instrument, period_days)
        
        # Combine metrics
        combined_metrics = {
            **fill_metrics,
            **speed_metrics,
            'avg_slippage_pips': float(slippage_analysis.avg_slippage_pips),
            'rejection_count': rejection_analysis.get('total_rejections', 0)
        }
        
        # Calculate composite scores
        quality_score = await self.quality_scorer.calculate_quality_score(combined_metrics)
        execution_efficiency = await self.quality_scorer.calculate_execution_efficiency(combined_metrics)
        
        return QualityMetrics(
            broker=broker,
            instrument=instrument,
            period_start=datetime.utcnow() - timedelta(days=period_days),
            period_end=datetime.utcnow(),
            total_orders=fill_metrics.get('total_orders', 0),
            filled_orders=int(fill_metrics.get('total_orders', 0) * fill_metrics.get('fill_rate', 0)),
            partial_fills=int(fill_metrics.get('total_orders', 0) * fill_metrics.get('partial_fill_rate', 0)),
            rejections=rejection_analysis.get('total_rejections', 0),
            cancellations=0,  # Would need additional tracking
            requotes=int(fill_metrics.get('total_orders', 0) * fill_metrics.get('requote_rate', 0)),
            avg_latency_ms=speed_metrics.get('avg_latency_ms', 0),
            median_latency_ms=speed_metrics.get('median_latency_ms', 0),
            p95_latency_ms=speed_metrics.get('p95_latency_ms', 0),
            avg_slippage_pips=float(slippage_analysis.avg_slippage_pips),
            median_slippage_pips=float(slippage_analysis.median_slippage_pips),
            positive_slippage_rate=slippage_analysis.positive_slippage_count / max(1, slippage_analysis.total_executions),
            fill_rate=fill_metrics.get('fill_rate', 0),
            rejection_rate=fill_metrics.get('rejection_rate', 0),
            partial_fill_rate=fill_metrics.get('partial_fill_rate', 0),
            requote_rate=fill_metrics.get('requote_rate', 0),
            quality_score=quality_score,
            execution_efficiency=execution_efficiency,
            cost_efficiency=0  # Would be calculated with cost data
        )
    
    async def get_execution_insights(self, broker: str, period_days: int = 30) -> Dict[str, Any]:
        """Get actionable insights from execution analysis"""
        # Get detailed analyses
        slippage_analysis = await self.slippage_system.analyze_slippage(broker, None, period_days)
        rejection_analysis = await self.rejection_tracker.get_rejection_analysis(broker, period_days * 24)
        speed_metrics = await self.speed_monitor.get_speed_metrics(broker, period_days * 24)
        
        insights = []
        
        # Slippage insights
        if slippage_analysis.avg_slippage_pips < -1:
            insights.append({
                'type': 'warning',
                'category': 'slippage',
                'message': f"High negative slippage detected: {slippage_analysis.avg_slippage_pips:.2f} pips average",
                'recommendation': "Consider using limit orders or adjusting execution timing"
            })
        
        # Speed insights
        if speed_metrics.get('avg_latency_ms', 0) > 200:
            insights.append({
                'type': 'warning',
                'category': 'latency',
                'message': f"High execution latency: {speed_metrics['avg_latency_ms']:.1f}ms average",
                'recommendation': "Check network connectivity and broker server locations"
            })
        
        # Rejection insights
        if rejection_analysis.get('total_rejections', 0) > 0:
            top_reason = rejection_analysis.get('top_rejection_reason')
            insights.append({
                'type': 'info',
                'category': 'rejections',
                'message': f"Main rejection reason: {top_reason}",
                'recommendation': "Review order parameters and market conditions"
            })
        
        return {
            'insights': insights,
            'summary_stats': {
                'avg_slippage_pips': float(slippage_analysis.avg_slippage_pips),
                'avg_latency_ms': speed_metrics.get('avg_latency_ms', 0),
                'total_rejections': rejection_analysis.get('total_rejections', 0)
            }
        }