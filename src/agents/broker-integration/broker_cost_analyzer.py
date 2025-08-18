"""
Broker Cost Analysis & Optimization System - Story 8.14

This module provides comprehensive cost tracking, execution quality analysis,
and broker optimization recommendations for trading operations.

Features:
- Real-time cost tracking (spreads, commissions, swaps, slippage)
- Execution quality analysis and scoring
- Broker comparison and routing recommendations  
- Historical cost trends and analysis
- Break-even calculators and optimization
- Cost reporting and export capabilities
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta, date
from enum import Enum
import asyncio
import logging
from collections import defaultdict

import aiohttp
from pydantic import BaseModel, Field, validator
import structlog

logger = structlog.get_logger(__name__)


class CostCategory(str, Enum):
    """Cost categorization for analysis"""
    SPREAD = "spread"
    COMMISSION = "commission"
    SWAP = "swap"
    SLIPPAGE = "slippage"
    FINANCING = "financing"
    OTHER = "other"


class ExecutionPhase(str, Enum):
    """Trade execution phases for quality tracking"""
    ORDER_PLACEMENT = "order_placement"
    ORDER_FILL = "order_fill"
    POSITION_MANAGEMENT = "position_management"
    POSITION_CLOSE = "position_close"


@dataclass
class TradeCost:
    """Comprehensive trade cost tracking"""
    broker: str
    instrument: str
    trade_id: str
    timestamp: datetime
    spread_cost: Decimal
    commission: Decimal
    swap_cost: Decimal
    slippage_cost: Decimal
    financing_cost: Decimal
    total_cost: Decimal
    trade_size: Decimal
    cost_per_unit: Decimal
    cost_basis_points: Decimal
    cost_category: Dict[CostCategory, Decimal] = field(default_factory=dict)
    execution_phase: ExecutionPhase = ExecutionPhase.ORDER_FILL
    market_conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionQuality:
    """Execution quality metrics"""
    broker: str
    period_start: datetime
    period_end: datetime
    total_executions: int
    successful_executions: int
    success_rate: float
    avg_latency_ms: float
    avg_slippage_pips: float
    avg_slippage_bps: float
    quality_score: float
    rejection_rate: float
    partial_fill_rate: float
    requote_rate: float
    execution_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class BrokerScore:
    """Broker scoring for routing decisions"""
    broker: str
    estimated_cost: Decimal
    cost_score: float
    quality_score: float
    composite_score: float
    confidence: float
    cost_breakdown: Dict[CostCategory, Decimal] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class BrokerRecommendation:
    """Broker routing recommendation"""
    instrument: str
    trade_size: Decimal
    trade_type: str
    recommended_broker: str
    all_options: List[BrokerScore]
    confidence: float
    reasoning: str
    cost_savings: Decimal
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SpreadTracker:
    """Real-time spread tracking by instrument and time"""
    
    def __init__(self):
        self.spread_data: Dict[str, Dict[str, List[Tuple[datetime, Decimal]]]] = defaultdict(lambda: defaultdict(list))
        self.session_spreads: Dict[str, Dict[str, Dict[str, Decimal]]] = defaultdict(lambda: defaultdict(dict))
        
    async def record_spread(self, broker: str, instrument: str, spread: Decimal, 
                          timestamp: Optional[datetime] = None) -> None:
        """Record spread data for analysis"""
        if timestamp is None:
            timestamp = datetime.utcnow()
            
        self.spread_data[broker][instrument].append((timestamp, spread))
        
        # Track session-based spreads
        session = self._get_market_session(timestamp)
        if session not in self.session_spreads[broker][instrument]:
            self.session_spreads[broker][instrument][session] = {
                'min': spread,
                'max': spread,
                'avg': spread,
                'count': 1,
                'total': spread
            }
        else:
            stats = self.session_spreads[broker][instrument][session]
            stats['min'] = min(stats['min'], spread)
            stats['max'] = max(stats['max'], spread)
            stats['count'] += 1
            stats['total'] += spread
            stats['avg'] = stats['total'] / stats['count']
            
        logger.info("Spread recorded",
                   broker=broker,
                   instrument=instrument, 
                   spread=float(spread),
                   session=session)
    
    def _get_market_session(self, timestamp: datetime) -> str:
        """Determine market session from timestamp"""
        hour = timestamp.hour
        if 22 <= hour or hour < 8:
            return "asian"
        elif 8 <= hour < 13:
            return "london"
        elif 13 <= hour < 22:
            return "ny"
        else:
            return "overlap"
    
    async def get_average_spread(self, broker: str, instrument: str, 
                               period_minutes: int = 60) -> Optional[Decimal]:
        """Get average spread for recent period"""
        cutoff = datetime.utcnow() - timedelta(minutes=period_minutes)
        
        if broker not in self.spread_data or instrument not in self.spread_data[broker]:
            return None
            
        recent_spreads = [
            spread for timestamp, spread in self.spread_data[broker][instrument]
            if timestamp >= cutoff
        ]
        
        if not recent_spreads:
            return None
            
        return sum(recent_spreads) / len(recent_spreads)
    
    async def get_session_spread_stats(self, broker: str, instrument: str) -> Dict[str, Dict[str, Decimal]]:
        """Get spread statistics by market session"""
        return dict(self.session_spreads[broker][instrument])


class CommissionTracker:
    """Commission structure tracking and calculation"""
    
    def __init__(self):
        self.commission_structures: Dict[str, Dict[str, Any]] = {}
        self.commission_history: Dict[str, List[Tuple[datetime, str, Decimal, Decimal]]] = defaultdict(list)
    
    async def register_commission_structure(self, broker: str, structure: Dict[str, Any]) -> None:
        """Register broker commission structure"""
        self.commission_structures[broker] = {
            'fixed_per_lot': structure.get('fixed_per_lot', Decimal('0')),
            'percentage': structure.get('percentage', Decimal('0')),
            'minimum': structure.get('minimum', Decimal('0')),
            'maximum': structure.get('maximum', None),
            'tier_based': structure.get('tier_based', False),
            'tiers': structure.get('tiers', []),
            'instrument_overrides': structure.get('instrument_overrides', {}),
            'updated': datetime.utcnow()
        }
        
        logger.info("Commission structure registered",
                   broker=broker,
                   structure=structure)
    
    async def calculate_commission(self, broker: str, instrument: str, 
                                 trade_size: Decimal, notional_value: Decimal) -> Decimal:
        """Calculate commission for a trade"""
        if broker not in self.commission_structures:
            logger.warning("No commission structure for broker", broker=broker)
            return Decimal('0')
        
        structure = self.commission_structures[broker]
        
        # Check for instrument-specific overrides
        if instrument in structure['instrument_overrides']:
            override = structure['instrument_overrides'][instrument]
            commission = self._calculate_from_structure(override, trade_size, notional_value)
        else:
            commission = self._calculate_from_structure(structure, trade_size, notional_value)
        
        # Record commission
        self.commission_history[broker].append((
            datetime.utcnow(), instrument, trade_size, commission
        ))
        
        return commission
    
    def _calculate_from_structure(self, structure: Dict[str, Any], 
                                trade_size: Decimal, notional_value: Decimal) -> Decimal:
        """Calculate commission from structure"""
        commission = Decimal('0')
        
        # Fixed per lot
        if 'fixed_per_lot' in structure:
            commission += structure['fixed_per_lot'] * abs(trade_size)
        
        # Percentage based
        if 'percentage' in structure and structure['percentage'] > 0:
            commission += notional_value * (structure['percentage'] / 100)
        
        # Tier-based calculation
        if structure.get('tier_based', False) and 'tiers' in structure:
            for tier in structure['tiers']:
                if notional_value >= tier['min_notional']:
                    if 'max_notional' not in tier or notional_value <= tier['max_notional']:
                        commission = tier['commission']
                        break
        
        # Apply minimum/maximum
        if 'minimum' in structure:
            commission = max(commission, structure['minimum'])
        if 'maximum' in structure and structure['maximum'] is not None:
            commission = min(commission, structure['maximum'])
        
        return commission


class SwapRateTracker:
    """Swap/rollover rate tracking"""
    
    def __init__(self):
        self.swap_rates: Dict[str, Dict[str, Dict[str, Decimal]]] = defaultdict(lambda: defaultdict(dict))
        self.swap_history: Dict[str, List[Tuple[datetime, str, str, Decimal]]] = defaultdict(list)
    
    async def update_swap_rates(self, broker: str, rates: Dict[str, Dict[str, Decimal]]) -> None:
        """Update swap rates for broker"""
        timestamp = datetime.utcnow()
        
        for instrument, rate_data in rates.items():
            self.swap_rates[broker][instrument] = {
                'long': rate_data.get('long', Decimal('0')),
                'short': rate_data.get('short', Decimal('0')),
                'updated': timestamp
            }
            
            # Record history
            self.swap_history[broker].append((
                timestamp, instrument, 'long', rate_data.get('long', Decimal('0'))
            ))
            self.swap_history[broker].append((
                timestamp, instrument, 'short', rate_data.get('short', Decimal('0'))
            ))
        
        logger.info("Swap rates updated",
                   broker=broker,
                   instruments=len(rates))
    
    async def calculate_swap_cost(self, broker: str, instrument: str, 
                                position_side: str, position_size: Decimal,
                                days_held: int) -> Decimal:
        """Calculate swap cost for position"""
        if broker not in self.swap_rates or instrument not in self.swap_rates[broker]:
            return Decimal('0')
        
        rates = self.swap_rates[broker][instrument]
        side_key = 'long' if position_side.upper() in ['BUY', 'LONG'] else 'short'
        
        if side_key not in rates:
            return Decimal('0')
        
        # Swap rate is typically per lot per day
        daily_swap = rates[side_key] * abs(position_size)
        total_swap = daily_swap * days_held
        
        return total_swap
    
    async def get_current_rates(self, broker: str, instrument: str) -> Optional[Dict[str, Decimal]]:
        """Get current swap rates for instrument"""
        if broker in self.swap_rates and instrument in self.swap_rates[broker]:
            return dict(self.swap_rates[broker][instrument])
        return None


class SlippageAnalyzer:
    """Slippage analysis and tracking"""
    
    def __init__(self):
        self.slippage_data: Dict[str, List[Tuple[datetime, str, Decimal, Dict[str, Any]]]] = defaultdict(list)
        self.slippage_stats: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    
    async def record_slippage(self, broker: str, instrument: str, slippage_pips: Decimal,
                            trade_data: Dict[str, Any]) -> None:
        """Record slippage data"""
        timestamp = datetime.utcnow()
        
        self.slippage_data[broker].append((
            timestamp, instrument, slippage_pips, trade_data
        ))
        
        # Update running statistics
        self._update_slippage_stats(broker, instrument, slippage_pips)
        
        logger.info("Slippage recorded",
                   broker=broker,
                   instrument=instrument,
                   slippage_pips=float(slippage_pips))
    
    def _update_slippage_stats(self, broker: str, instrument: str, slippage_pips: Decimal) -> None:
        """Update running slippage statistics"""
        if instrument not in self.slippage_stats[broker]:
            self.slippage_stats[broker][instrument] = {
                'count': 0,
                'total': 0.0,
                'min': float(slippage_pips),
                'max': float(slippage_pips),
                'avg': float(slippage_pips)
            }
        
        stats = self.slippage_stats[broker][instrument]
        stats['count'] += 1
        stats['total'] += float(slippage_pips)
        stats['min'] = min(stats['min'], float(slippage_pips))
        stats['max'] = max(stats['max'], float(slippage_pips))
        stats['avg'] = stats['total'] / stats['count']
    
    async def get_slippage_stats(self, broker: str, instrument: str = None, 
                               period_days: int = 30) -> Dict[str, Any]:
        """Get slippage statistics"""
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        
        if instrument:
            # Single instrument stats
            recent_data = [
                slippage for timestamp, instr, slippage, _ in self.slippage_data[broker]
                if instr == instrument and timestamp >= cutoff
            ]
        else:
            # All instruments for broker
            recent_data = [
                slippage for timestamp, _, slippage, _ in self.slippage_data[broker]
                if timestamp >= cutoff
            ]
        
        if not recent_data:
            return {}
        
        return {
            'count': len(recent_data),
            'avg_slippage': float(sum(recent_data) / len(recent_data)),
            'min_slippage': float(min(recent_data)),
            'max_slippage': float(max(recent_data)),
            'total_slippage': float(sum(recent_data))
        }


class BrokerCostAnalyzer:
    """Main broker cost analysis system"""
    
    def __init__(self):
        self.spread_tracker = SpreadTracker()
        self.commission_tracker = CommissionTracker()
        self.swap_tracker = SwapRateTracker()
        self.slippage_analyzer = SlippageAnalyzer()
        self.cost_cache: Dict[str, TradeCost] = {}
        self.analysis_cache: Dict[str, Any] = {}
        
    async def initialize(self, broker_configs: Dict[str, Dict[str, Any]]) -> None:
        """Initialize cost analyzer with broker configurations"""
        for broker, config in broker_configs.items():
            # Initialize commission structures
            if 'commission_structure' in config:
                await self.commission_tracker.register_commission_structure(
                    broker, config['commission_structure']
                )
            
            # Initialize swap rates if provided
            if 'swap_rates' in config:
                await self.swap_tracker.update_swap_rates(
                    broker, config['swap_rates']
                )
        
        logger.info("Broker cost analyzer initialized", brokers=list(broker_configs.keys()))
    
    async def calculate_trade_cost(self, broker: str, trade_data: Dict[str, Any]) -> TradeCost:
        """Calculate comprehensive cost for a trade"""
        instrument = trade_data['instrument']
        trade_size = abs(Decimal(str(trade_data['units'])))
        notional_value = trade_size * Decimal(str(trade_data.get('price', trade_data.get('fill_price', 0))))
        
        # Calculate spread cost
        spread_cost = await self._calculate_spread_cost(trade_data)
        
        # Calculate commission
        commission = await self.commission_tracker.calculate_commission(
            broker, instrument, trade_size, notional_value
        )
        
        # Calculate swap cost if position held overnight
        swap_cost = await self._calculate_swap_cost(broker, trade_data)
        
        # Calculate slippage cost
        slippage_cost = await self._calculate_slippage_cost(trade_data)
        
        # Calculate financing cost
        financing_cost = Decimal(str(trade_data.get('financing', 0)))
        
        # Total cost
        total_cost = spread_cost + commission + swap_cost + slippage_cost + financing_cost
        
        # Cost categorization
        cost_category = {
            CostCategory.SPREAD: spread_cost,
            CostCategory.COMMISSION: commission,
            CostCategory.SWAP: swap_cost,
            CostCategory.SLIPPAGE: slippage_cost,
            CostCategory.FINANCING: financing_cost
        }
        
        trade_cost = TradeCost(
            broker=broker,
            instrument=instrument,
            trade_id=trade_data['trade_id'],
            timestamp=trade_data.get('timestamp', datetime.utcnow()),
            spread_cost=spread_cost,
            commission=commission,
            swap_cost=swap_cost,
            slippage_cost=slippage_cost,
            financing_cost=financing_cost,
            total_cost=total_cost,
            trade_size=trade_size,
            cost_per_unit=total_cost / trade_size if trade_size > 0 else Decimal('0'),
            cost_basis_points=(total_cost / notional_value * 10000) if notional_value > 0 else Decimal('0'),
            cost_category=cost_category,
            execution_phase=ExecutionPhase(trade_data.get('execution_phase', 'order_fill')),
            market_conditions=trade_data.get('market_conditions', {})
        )
        
        # Cache for analysis
        self.cost_cache[trade_data['trade_id']] = trade_cost
        
        logger.info("Trade cost calculated",
                   broker=broker,
                   trade_id=trade_data['trade_id'],
                   total_cost=float(total_cost),
                   cost_bps=float(trade_cost.cost_basis_points))
        
        return trade_cost
    
    async def _calculate_spread_cost(self, trade_data: Dict[str, Any]) -> Decimal:
        """Calculate cost from bid-ask spread"""
        bid = Decimal(str(trade_data.get('bid', 0)))
        ask = Decimal(str(trade_data.get('ask', 0)))
        units = abs(Decimal(str(trade_data['units'])))
        
        if bid == 0 or ask == 0:
            return Decimal('0')
        
        spread = ask - bid
        # Cost is half spread * units (assuming mid-price execution impact)
        return (spread / 2) * units
    
    async def _calculate_slippage_cost(self, trade_data: Dict[str, Any]) -> Decimal:
        """Calculate cost from slippage"""
        expected_price = Decimal(str(trade_data.get('expected_price', 0)))
        actual_price = Decimal(str(trade_data.get('fill_price', trade_data.get('price', 0))))
        units = abs(Decimal(str(trade_data['units'])))
        
        if expected_price == 0 or actual_price == 0:
            return Decimal('0')
        
        slippage = abs(actual_price - expected_price)
        return slippage * units
    
    async def _calculate_swap_cost(self, broker: str, trade_data: Dict[str, Any]) -> Decimal:
        """Calculate swap cost for trade"""
        if 'days_held' not in trade_data or trade_data['days_held'] <= 0:
            return Decimal('0')
        
        return await self.swap_tracker.calculate_swap_cost(
            broker=broker,
            instrument=trade_data['instrument'],
            position_side=trade_data.get('side', 'buy'),
            position_size=abs(Decimal(str(trade_data['units']))),
            days_held=trade_data['days_held']
        )
    
    async def generate_broker_cost_comparison(self, period_days: int = 30) -> Dict[str, Dict[str, Any]]:
        """Generate comprehensive cost comparison across brokers"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Get all trade costs in period
        recent_costs = [
            cost for cost in self.cost_cache.values()
            if start_date <= cost.timestamp <= end_date
        ]
        
        broker_stats = defaultdict(lambda: {
            'total_cost': Decimal('0'),
            'total_volume': Decimal('0'),
            'avg_spread': Decimal('0'),
            'avg_commission': Decimal('0'),
            'avg_slippage': Decimal('0'),
            'avg_swap': Decimal('0'),
            'trade_count': 0,
            'cost_by_category': defaultdict(Decimal),
            'cost_by_instrument': defaultdict(Decimal),
            'avg_cost_bps': Decimal('0')
        })
        
        for cost in recent_costs:
            stats = broker_stats[cost.broker]
            stats['total_cost'] += cost.total_cost
            stats['total_volume'] += cost.trade_size
            stats['trade_count'] += 1
            
            # Category breakdown
            for category, amount in cost.cost_category.items():
                stats['cost_by_category'][category.value] += amount
            
            # Instrument breakdown
            stats['cost_by_instrument'][cost.instrument] += cost.total_cost
        
        # Calculate averages and derived metrics
        for broker, stats in broker_stats.items():
            if stats['trade_count'] > 0:
                stats['avg_cost_per_trade'] = stats['total_cost'] / stats['trade_count']
                stats['cost_per_million'] = (stats['total_cost'] / stats['total_volume']) * 1000000 if stats['total_volume'] > 0 else Decimal('0')
                stats['avg_cost_bps'] = sum(
                    cost.cost_basis_points for cost in recent_costs if cost.broker == broker
                ) / stats['trade_count']
                
                # Convert defaultdicts to regular dicts for JSON serialization
                stats['cost_by_category'] = dict(stats['cost_by_category'])
                stats['cost_by_instrument'] = dict(stats['cost_by_instrument'])
        
        return dict(broker_stats)
    
    async def get_cost_trends(self, broker: str, instrument: str = None, 
                            period_days: int = 90) -> Dict[str, List[Tuple[date, float]]]:
        """Get cost trends over time"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Filter costs
        filtered_costs = [
            cost for cost in self.cost_cache.values()
            if cost.broker == broker and start_date <= cost.timestamp <= end_date
            and (instrument is None or cost.instrument == instrument)
        ]
        
        # Group by date
        daily_costs = defaultdict(list)
        for cost in filtered_costs:
            daily_costs[cost.timestamp.date()].append(cost)
        
        # Calculate daily averages
        trends = {
            'total_cost': [],
            'spread_cost': [],
            'commission': [],
            'slippage_cost': [],
            'swap_cost': [],
            'cost_bps': []
        }
        
        for trade_date in sorted(daily_costs.keys()):
            day_costs = daily_costs[trade_date]
            
            trends['total_cost'].append((
                trade_date,
                float(sum(c.total_cost for c in day_costs) / len(day_costs))
            ))
            trends['spread_cost'].append((
                trade_date,
                float(sum(c.spread_cost for c in day_costs) / len(day_costs))
            ))
            trends['commission'].append((
                trade_date,
                float(sum(c.commission for c in day_costs) / len(day_costs))
            ))
            trends['slippage_cost'].append((
                trade_date,
                float(sum(c.slippage_cost for c in day_costs) / len(day_costs))
            ))
            trends['swap_cost'].append((
                trade_date,
                float(sum(c.swap_cost for c in day_costs) / len(day_costs))
            ))
            trends['cost_bps'].append((
                trade_date,
                float(sum(c.cost_basis_points for c in day_costs) / len(day_costs))
            ))
        
        return trends