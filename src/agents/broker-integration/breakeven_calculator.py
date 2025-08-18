"""
Break-even Calculator & Profitability Optimizer - Story 8.14 Task 5

This module provides comprehensive break-even analysis, profitability calculations,
risk-reward optimization, and scenario planning for trading cost optimization.

Features:
- Profitability calculator with cost considerations
- Break-even analysis for trades and strategies
- Minimum trade size calculations
- Risk-reward ratio optimization
- Trading optimization suggestions
- Scenario planning and what-if analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
import math
from collections import defaultdict

import structlog

logger = structlog.get_logger(__name__)


class TradeType(str, Enum):
    """Trade type classifications"""
    SCALPING = "scalping"
    DAY_TRADING = "day_trading"
    SWING_TRADING = "swing_trading"
    POSITION_TRADING = "position_trading"


class OptimizationType(str, Enum):
    """Optimization objective types"""
    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_PROFIT = "maximize_profit"
    OPTIMIZE_RISK_REWARD = "optimize_risk_reward"
    MAXIMIZE_SHARPE = "maximize_sharpe"


@dataclass
class TradeParameters:
    """Trade setup parameters"""
    instrument: str
    entry_price: Decimal
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    trade_size: Decimal
    direction: str  # 'buy' or 'sell'
    broker: str
    holding_period_days: int = 0
    expected_volatility: Optional[Decimal] = None


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a trade"""
    spread_cost: Decimal
    commission: Decimal
    swap_cost: Decimal
    slippage_cost: Decimal
    financing_cost: Decimal
    total_cost: Decimal
    cost_per_unit: Decimal
    cost_basis_points: Decimal


@dataclass
class ProfitabilityAnalysis:
    """Comprehensive profitability analysis"""
    trade_parameters: TradeParameters
    cost_breakdown: CostBreakdown
    gross_profit: Decimal
    net_profit: Decimal
    profit_margin: Decimal
    return_on_investment: Decimal
    break_even_price: Decimal
    break_even_movement_pips: Decimal
    risk_reward_ratio: Decimal
    profit_probability: Optional[float]
    expected_value: Decimal
    max_adverse_excursion: Decimal
    profit_factor: Decimal


@dataclass
class BreakEvenAnalysis:
    """Break-even analysis results"""
    instrument: str
    broker: str
    current_costs: CostBreakdown
    break_even_price: Decimal
    break_even_movement_pips: Decimal
    break_even_movement_bps: Decimal
    minimum_profit_target: Decimal
    recommended_stop_loss: Decimal
    recommended_take_profit: Decimal
    minimum_hold_time: int  # minutes
    cost_recovery_scenarios: List[Dict[str, Any]]
    sensitivity_analysis: Dict[str, Decimal]


@dataclass
class MinimumTradeSize:
    """Minimum trade size calculations"""
    instrument: str
    broker: str
    minimum_size_by_cost: Decimal  # Based on cost efficiency
    minimum_size_by_risk: Decimal  # Based on risk management
    minimum_size_by_profit: Decimal  # Based on profit targets
    recommended_minimum: Decimal
    cost_efficiency_curve: List[Tuple[Decimal, Decimal]]  # size -> cost per unit
    optimal_size_range: Tuple[Decimal, Decimal]
    scalability_analysis: Dict[str, Any]


@dataclass
class RiskRewardOptimization:
    """Risk-reward optimization results"""
    trade_parameters: TradeParameters
    current_risk_reward: Decimal
    optimal_risk_reward: Decimal
    recommended_stop_loss: Decimal
    recommended_take_profit: Decimal
    position_size_adjustment: Decimal
    expected_return: Decimal
    value_at_risk: Decimal
    maximum_drawdown: Decimal
    win_rate_required: Decimal
    optimization_suggestions: List[str]


@dataclass
class ScenarioAnalysis:
    """Scenario planning analysis"""
    base_scenario: ProfitabilityAnalysis
    scenarios: Dict[str, ProfitabilityAnalysis]  # scenario_name -> analysis
    best_case: ProfitabilityAnalysis
    worst_case: ProfitabilityAnalysis
    most_likely: ProfitabilityAnalysis
    scenario_probabilities: Dict[str, float]
    expected_outcome: ProfitabilityAnalysis
    risk_metrics: Dict[str, Decimal]
    sensitivity_factors: Dict[str, Decimal]


class ProfitabilityCalculator:
    """Advanced profitability calculator with cost integration"""
    
    def __init__(self):
        self.pip_values = {
            'EUR_USD': Decimal('10'),   # $10 per pip for standard lot
            'GBP_USD': Decimal('10'),
            'USD_JPY': Decimal('9.09'),  # Approximate, varies with price
            'USD_CHF': Decimal('10'),
            'AUD_USD': Decimal('10'),
            'USD_CAD': Decimal('7.69'),  # Approximate
            'NZD_USD': Decimal('10')
        }
        
    async def calculate_profitability(self, trade_params: TradeParameters,
                                    cost_analyzer = None) -> ProfitabilityAnalysis:
        """Calculate comprehensive trade profitability including all costs"""
        
        # Estimate trading costs
        cost_breakdown = await self._estimate_trade_costs(trade_params, cost_analyzer)
        
        # Calculate gross profit/loss
        gross_profit = await self._calculate_gross_profit(trade_params)
        
        # Calculate net profit after costs
        net_profit = gross_profit - cost_breakdown.total_cost
        
        # Calculate profitability metrics
        profit_margin = (net_profit / gross_profit * 100) if gross_profit != 0 else Decimal('0')
        
        trade_value = trade_params.trade_size * trade_params.entry_price
        roi = (net_profit / trade_value * 100) if trade_value != 0 else Decimal('0')
        
        # Calculate break-even requirements
        break_even_price = await self._calculate_break_even_price(trade_params, cost_breakdown)
        break_even_pips = await self._calculate_break_even_pips(trade_params, cost_breakdown)
        
        # Calculate risk-reward ratio
        risk_reward_ratio = await self._calculate_risk_reward_ratio(trade_params, cost_breakdown)
        
        # Estimate profit probability (simplified model)
        profit_probability = await self._estimate_profit_probability(trade_params)
        
        # Calculate expected value
        expected_value = net_profit * Decimal(str(profit_probability)) if profit_probability else net_profit
        
        # Calculate maximum adverse excursion
        max_adverse_excursion = await self._calculate_max_adverse_excursion(trade_params, cost_breakdown)
        
        # Calculate profit factor
        profit_factor = await self._calculate_profit_factor(trade_params, cost_breakdown)
        
        analysis = ProfitabilityAnalysis(
            trade_parameters=trade_params,
            cost_breakdown=cost_breakdown,
            gross_profit=gross_profit,
            net_profit=net_profit,
            profit_margin=profit_margin,
            return_on_investment=roi,
            break_even_price=break_even_price,
            break_even_movement_pips=break_even_pips,
            risk_reward_ratio=risk_reward_ratio,
            profit_probability=profit_probability,
            expected_value=expected_value,
            max_adverse_excursion=max_adverse_excursion,
            profit_factor=profit_factor
        )
        
        logger.info("Profitability analysis completed",
                   instrument=trade_params.instrument,
                   broker=trade_params.broker,
                   net_profit=float(net_profit),
                   roi=float(roi))
        
        return analysis
    
    async def _estimate_trade_costs(self, trade_params: TradeParameters,
                                  cost_analyzer = None) -> CostBreakdown:
        """Estimate comprehensive trading costs"""
        
        # Mock trade data for cost calculation
        trade_data = {
            'instrument': trade_params.instrument,
            'units': str(trade_params.trade_size),
            'price': str(trade_params.entry_price),
            'expected_price': str(trade_params.entry_price),
            'fill_price': str(trade_params.entry_price),
            'bid': str(trade_params.entry_price - Decimal('0.0001')),  # Mock spread
            'ask': str(trade_params.entry_price + Decimal('0.0001')),
            'trade_id': f"mock_{datetime.utcnow().timestamp()}",
            'timestamp': datetime.utcnow(),
            'days_held': trade_params.holding_period_days,
            'side': trade_params.direction
        }
        
        if cost_analyzer:
            try:
                trade_cost = await cost_analyzer.calculate_trade_cost(trade_params.broker, trade_data)
                return CostBreakdown(
                    spread_cost=trade_cost.spread_cost,
                    commission=trade_cost.commission,
                    swap_cost=trade_cost.swap_cost,
                    slippage_cost=trade_cost.slippage_cost,
                    financing_cost=trade_cost.financing_cost,
                    total_cost=trade_cost.total_cost,
                    cost_per_unit=trade_cost.cost_per_unit,
                    cost_basis_points=trade_cost.cost_basis_points
                )
            except Exception as e:
                logger.warning("Error calculating costs, using estimates", error=str(e))
        
        # Fallback to estimated costs
        spread_cost = trade_params.trade_size * Decimal('0.0001')  # 1 pip spread
        commission = trade_params.trade_size * Decimal('0.00005')  # 0.5 pip commission
        swap_cost = Decimal('0') if trade_params.holding_period_days == 0 else trade_params.trade_size * Decimal('0.0001') * trade_params.holding_period_days
        slippage_cost = trade_params.trade_size * Decimal('0.00003')  # 0.3 pip slippage
        financing_cost = Decimal('0')
        
        total_cost = spread_cost + commission + swap_cost + slippage_cost + financing_cost
        cost_per_unit = total_cost / trade_params.trade_size if trade_params.trade_size > 0 else Decimal('0')
        
        trade_value = trade_params.trade_size * trade_params.entry_price
        cost_bps = (total_cost / trade_value * 10000) if trade_value > 0 else Decimal('0')
        
        return CostBreakdown(
            spread_cost=spread_cost,
            commission=commission,
            swap_cost=swap_cost,
            slippage_cost=slippage_cost,
            financing_cost=financing_cost,
            total_cost=total_cost,
            cost_per_unit=cost_per_unit,
            cost_basis_points=cost_bps
        )
    
    async def _calculate_gross_profit(self, trade_params: TradeParameters) -> Decimal:
        """Calculate gross profit before costs"""
        if not trade_params.take_profit:
            return Decimal('0')  # Can't calculate without target
        
        price_difference = trade_params.take_profit - trade_params.entry_price
        
        if trade_params.direction.lower() == 'sell':
            price_difference = -price_difference
        
        return price_difference * trade_params.trade_size
    
    async def _calculate_break_even_price(self, trade_params: TradeParameters,
                                        cost_breakdown: CostBreakdown) -> Decimal:
        """Calculate break-even price including all costs"""
        cost_per_unit = cost_breakdown.cost_per_unit
        
        if trade_params.direction.lower() == 'buy':
            return trade_params.entry_price + cost_per_unit
        else:
            return trade_params.entry_price - cost_per_unit
    
    async def _calculate_break_even_pips(self, trade_params: TradeParameters,
                                       cost_breakdown: CostBreakdown) -> Decimal:
        """Calculate break-even movement in pips"""
        pip_size = await self._get_pip_size(trade_params.instrument)
        cost_per_unit = cost_breakdown.cost_per_unit
        
        return cost_per_unit / pip_size
    
    async def _calculate_risk_reward_ratio(self, trade_params: TradeParameters,
                                         cost_breakdown: CostBreakdown) -> Decimal:
        """Calculate risk-reward ratio including costs"""
        if not trade_params.take_profit or not trade_params.stop_loss:
            return Decimal('0')
        
        # Calculate potential reward (profit target minus costs)
        gross_reward = abs(trade_params.take_profit - trade_params.entry_price) * trade_params.trade_size
        net_reward = gross_reward - cost_breakdown.total_cost
        
        # Calculate potential risk (stop loss plus costs)
        gross_risk = abs(trade_params.entry_price - trade_params.stop_loss) * trade_params.trade_size
        total_risk = gross_risk + cost_breakdown.total_cost
        
        if total_risk == 0:
            return Decimal('0')
        
        return net_reward / total_risk
    
    async def _estimate_profit_probability(self, trade_params: TradeParameters) -> Optional[float]:
        """Estimate probability of profitable trade (simplified model)"""
        if not trade_params.take_profit or not trade_params.stop_loss:
            return None
        
        # Simple model based on risk-reward ratio and volatility
        risk_distance = abs(trade_params.entry_price - trade_params.stop_loss)
        reward_distance = abs(trade_params.take_profit - trade_params.entry_price)
        
        # Assume 50% base probability, adjust for risk-reward ratio
        base_probability = 0.5
        rr_ratio = float(reward_distance / risk_distance) if risk_distance > 0 else 1.0
        
        # Adjust probability based on risk-reward ratio (simplified)
        if rr_ratio > 2:
            adjusted_probability = base_probability * 0.8  # Lower probability for high RR
        elif rr_ratio > 1:
            adjusted_probability = base_probability * 0.9
        else:
            adjusted_probability = base_probability * 1.1  # Higher probability for conservative targets
        
        return min(0.95, max(0.05, adjusted_probability))
    
    async def _calculate_max_adverse_excursion(self, trade_params: TradeParameters,
                                             cost_breakdown: CostBreakdown) -> Decimal:
        """Calculate maximum adverse excursion including costs"""
        if not trade_params.stop_loss:
            return cost_breakdown.total_cost
        
        stop_loss_cost = abs(trade_params.entry_price - trade_params.stop_loss) * trade_params.trade_size
        return stop_loss_cost + cost_breakdown.total_cost
    
    async def _calculate_profit_factor(self, trade_params: TradeParameters,
                                     cost_breakdown: CostBreakdown) -> Decimal:
        """Calculate profit factor (gross profit / gross loss)"""
        if not trade_params.take_profit or not trade_params.stop_loss:
            return Decimal('1')
        
        gross_profit = abs(trade_params.take_profit - trade_params.entry_price) * trade_params.trade_size
        gross_loss = abs(trade_params.entry_price - trade_params.stop_loss) * trade_params.trade_size
        
        if gross_loss == 0:
            return Decimal('999')  # Very high profit factor
        
        return gross_profit / gross_loss
    
    async def _get_pip_size(self, instrument: str) -> Decimal:
        """Get pip size for instrument"""
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


class BreakEvenAnalyzer:
    """Advanced break-even analysis system"""
    
    def __init__(self):
        self.profitability_calculator = ProfitabilityCalculator()
    
    async def analyze_break_even(self, instrument: str, broker: str, entry_price: Decimal,
                               trade_size: Decimal, direction: str,
                               cost_analyzer = None) -> BreakEvenAnalysis:
        """Comprehensive break-even analysis"""
        
        # Create base trade parameters
        trade_params = TradeParameters(
            instrument=instrument,
            entry_price=entry_price,
            stop_loss=None,
            take_profit=None,
            trade_size=trade_size,
            direction=direction,
            broker=broker
        )
        
        # Calculate current costs
        cost_breakdown = await self.profitability_calculator._estimate_trade_costs(
            trade_params, cost_analyzer
        )
        
        # Calculate break-even metrics
        break_even_price = await self.profitability_calculator._calculate_break_even_price(
            trade_params, cost_breakdown
        )
        
        break_even_pips = await self.profitability_calculator._calculate_break_even_pips(
            trade_params, cost_breakdown
        )
        
        break_even_bps = (abs(break_even_price - entry_price) / entry_price * 10000) if entry_price > 0 else Decimal('0')
        
        # Calculate recommendations
        minimum_profit_target = await self._calculate_minimum_profit_target(cost_breakdown, trade_size)
        recommended_stop_loss = await self._calculate_recommended_stop_loss(entry_price, cost_breakdown, direction)
        recommended_take_profit = await self._calculate_recommended_take_profit(entry_price, cost_breakdown, direction)
        
        # Estimate minimum hold time
        minimum_hold_time = await self._estimate_minimum_hold_time(cost_breakdown, trade_size)
        
        # Generate cost recovery scenarios
        cost_recovery_scenarios = await self._generate_cost_recovery_scenarios(
            entry_price, cost_breakdown, direction
        )
        
        # Perform sensitivity analysis
        sensitivity_analysis = await self._perform_sensitivity_analysis(
            trade_params, cost_breakdown, cost_analyzer
        )
        
        analysis = BreakEvenAnalysis(
            instrument=instrument,
            broker=broker,
            current_costs=cost_breakdown,
            break_even_price=break_even_price,
            break_even_movement_pips=break_even_pips,
            break_even_movement_bps=break_even_bps,
            minimum_profit_target=minimum_profit_target,
            recommended_stop_loss=recommended_stop_loss,
            recommended_take_profit=recommended_take_profit,
            minimum_hold_time=minimum_hold_time,
            cost_recovery_scenarios=cost_recovery_scenarios,
            sensitivity_analysis=sensitivity_analysis
        )
        
        logger.info("Break-even analysis completed",
                   instrument=instrument,
                   broker=broker,
                   break_even_pips=float(break_even_pips))
        
        return analysis
    
    async def _calculate_minimum_profit_target(self, cost_breakdown: CostBreakdown,
                                             trade_size: Decimal) -> Decimal:
        """Calculate minimum profit target to justify trade"""
        # Minimum should be 2x the total costs for reasonable risk-reward
        return cost_breakdown.total_cost * 2
    
    async def _calculate_recommended_stop_loss(self, entry_price: Decimal,
                                             cost_breakdown: CostBreakdown,
                                             direction: str) -> Decimal:
        """Calculate recommended stop loss considering costs"""
        # Risk should be 2-3x the costs maximum
        max_acceptable_risk = cost_breakdown.total_cost * 3
        risk_per_unit = max_acceptable_risk / cost_breakdown.total_cost if cost_breakdown.total_cost > 0 else Decimal('0.001')
        
        if direction.lower() == 'buy':
            return entry_price - risk_per_unit
        else:
            return entry_price + risk_per_unit
    
    async def _calculate_recommended_take_profit(self, entry_price: Decimal,
                                               cost_breakdown: CostBreakdown,
                                               direction: str) -> Decimal:
        """Calculate recommended take profit for good risk-reward"""
        # Target should provide 2:1 risk-reward after costs
        profit_target = cost_breakdown.total_cost * 4  # 2x costs for profit + 2x costs to cover risk
        profit_per_unit = profit_target / cost_breakdown.total_cost if cost_breakdown.total_cost > 0 else Decimal('0.002')
        
        if direction.lower() == 'buy':
            return entry_price + profit_per_unit
        else:
            return entry_price - profit_per_unit
    
    async def _estimate_minimum_hold_time(self, cost_breakdown: CostBreakdown,
                                        trade_size: Decimal) -> int:
        """Estimate minimum hold time in minutes to justify costs"""
        # Based on cost per unit, estimate time needed for normal market movement
        cost_per_unit = cost_breakdown.cost_per_unit
        
        # Rough estimate: 1 pip movement per 15 minutes in normal markets
        # Convert cost to pips and multiply by 15
        pip_value = Decimal('0.0001')  # Simplified
        cost_in_pips = cost_per_unit / pip_value
        
        minimum_minutes = int(float(cost_in_pips) * 15)
        
        # Reasonable bounds
        return max(5, min(240, minimum_minutes))  # 5 minutes to 4 hours
    
    async def _generate_cost_recovery_scenarios(self, entry_price: Decimal,
                                              cost_breakdown: CostBreakdown,
                                              direction: str) -> List[Dict[str, Any]]:
        """Generate scenarios for cost recovery"""
        scenarios = []
        
        cost_per_unit = cost_breakdown.cost_per_unit
        pip_size = Decimal('0.0001')  # Simplified
        
        # Quick recovery (break-even + small profit)
        quick_target = cost_per_unit * Decimal('1.2')
        quick_price = entry_price + quick_target if direction.lower() == 'buy' else entry_price - quick_target
        scenarios.append({
            'name': 'Quick Recovery',
            'target_price': quick_price,
            'movement_pips': float(quick_target / pip_size),
            'profit_after_costs': float(quick_target - cost_per_unit),
            'time_estimate_minutes': 30
        })
        
        # Conservative recovery (2:1 reward)
        conservative_target = cost_per_unit * 2
        conservative_price = entry_price + conservative_target if direction.lower() == 'buy' else entry_price - conservative_target
        scenarios.append({
            'name': 'Conservative Target',
            'target_price': conservative_price,
            'movement_pips': float(conservative_target / pip_size),
            'profit_after_costs': float(conservative_target - cost_per_unit),
            'time_estimate_minutes': 120
        })
        
        # Aggressive recovery (3:1 reward)
        aggressive_target = cost_per_unit * 3
        aggressive_price = entry_price + aggressive_target if direction.lower() == 'buy' else entry_price - aggressive_target
        scenarios.append({
            'name': 'Aggressive Target',
            'target_price': aggressive_price,
            'movement_pips': float(aggressive_target / pip_size),
            'profit_after_costs': float(aggressive_target - cost_per_unit),
            'time_estimate_minutes': 240
        })
        
        return scenarios
    
    async def _perform_sensitivity_analysis(self, trade_params: TradeParameters,
                                          cost_breakdown: CostBreakdown,
                                          cost_analyzer = None) -> Dict[str, Decimal]:
        """Analyze sensitivity to various factors"""
        sensitivity = {}
        
        # Sensitivity to trade size
        larger_size = trade_params.trade_size * Decimal('2')
        larger_params = TradeParameters(
            instrument=trade_params.instrument,
            entry_price=trade_params.entry_price,
            stop_loss=trade_params.stop_loss,
            take_profit=trade_params.take_profit,
            trade_size=larger_size,
            direction=trade_params.direction,
            broker=trade_params.broker
        )
        
        larger_costs = await self.profitability_calculator._estimate_trade_costs(
            larger_params, cost_analyzer
        )
        
        size_sensitivity = (larger_costs.cost_per_unit - cost_breakdown.cost_per_unit) / cost_breakdown.cost_per_unit * 100
        sensitivity['trade_size_2x'] = size_sensitivity
        
        # Sensitivity to holding period
        if trade_params.holding_period_days == 0:
            overnight_params = TradeParameters(
                instrument=trade_params.instrument,
                entry_price=trade_params.entry_price,
                stop_loss=trade_params.stop_loss,
                take_profit=trade_params.take_profit,
                trade_size=trade_params.trade_size,
                direction=trade_params.direction,
                broker=trade_params.broker,
                holding_period_days=1
            )
            
            overnight_costs = await self.profitability_calculator._estimate_trade_costs(
                overnight_params, cost_analyzer
            )
            
            holding_sensitivity = (overnight_costs.total_cost - cost_breakdown.total_cost) / cost_breakdown.total_cost * 100
            sensitivity['overnight_holding'] = holding_sensitivity
        
        return sensitivity


class MinimumTradeSizeCalculator:
    """Calculate optimal minimum trade sizes"""
    
    def __init__(self):
        self.profitability_calculator = ProfitabilityCalculator()
    
    async def calculate_minimum_trade_size(self, instrument: str, broker: str,
                                         entry_price: Decimal, direction: str,
                                         cost_analyzer = None) -> MinimumTradeSize:
        """Calculate minimum trade size based on various criteria"""
        
        # Test different trade sizes to find optimal points
        test_sizes = [
            Decimal('1000'), Decimal('5000'), Decimal('10000'), Decimal('25000'),
            Decimal('50000'), Decimal('100000'), Decimal('250000'), Decimal('500000')
        ]
        
        cost_efficiency_curve = []
        
        for size in test_sizes:
            trade_params = TradeParameters(
                instrument=instrument,
                entry_price=entry_price,
                stop_loss=None,
                take_profit=None,
                trade_size=size,
                direction=direction,
                broker=broker
            )
            
            cost_breakdown = await self.profitability_calculator._estimate_trade_costs(
                trade_params, cost_analyzer
            )
            
            cost_efficiency_curve.append((size, cost_breakdown.cost_per_unit))
        
        # Calculate different minimum sizes
        min_size_cost = await self._calculate_min_size_by_cost_efficiency(cost_efficiency_curve)
        min_size_risk = await self._calculate_min_size_by_risk_management(entry_price)
        min_size_profit = await self._calculate_min_size_by_profit_targets(cost_efficiency_curve)
        
        # Recommended minimum is the maximum of all criteria
        recommended_minimum = max(min_size_cost, min_size_risk, min_size_profit)
        
        # Find optimal size range
        optimal_range = await self._find_optimal_size_range(cost_efficiency_curve)
        
        # Scalability analysis
        scalability_analysis = await self._analyze_scalability(cost_efficiency_curve)
        
        result = MinimumTradeSize(
            instrument=instrument,
            broker=broker,
            minimum_size_by_cost=min_size_cost,
            minimum_size_by_risk=min_size_risk,
            minimum_size_by_profit=min_size_profit,
            recommended_minimum=recommended_minimum,
            cost_efficiency_curve=cost_efficiency_curve,
            optimal_size_range=optimal_range,
            scalability_analysis=scalability_analysis
        )
        
        logger.info("Minimum trade size calculated",
                   instrument=instrument,
                   broker=broker,
                   recommended_minimum=float(recommended_minimum))
        
        return result
    
    async def _calculate_min_size_by_cost_efficiency(self, cost_curve: List[Tuple[Decimal, Decimal]]) -> Decimal:
        """Find minimum size where cost efficiency levels off"""
        if len(cost_curve) < 2:
            return Decimal('10000')  # Default
        
        # Find where marginal cost improvement becomes minimal
        for i in range(1, len(cost_curve)):
            current_size, current_cost = cost_curve[i]
            prev_size, prev_cost = cost_curve[i-1]
            
            if prev_cost > 0:
                cost_improvement = (prev_cost - current_cost) / prev_cost
                if cost_improvement < 0.05:  # Less than 5% improvement
                    return prev_size
        
        return cost_curve[0][0]  # Return smallest size if no leveling found
    
    async def _calculate_min_size_by_risk_management(self, entry_price: Decimal) -> Decimal:
        """Calculate minimum size based on risk management principles"""
        # Assume maximum risk per trade is 2% of a $10,000 account
        max_risk_dollars = Decimal('200')
        
        # Assume typical stop loss is 20 pips
        typical_stop_pips = 20
        pip_size = Decimal('0.0001')
        stop_loss_distance = typical_stop_pips * pip_size
        
        # Calculate position size that risks $200 with 20 pip stop
        min_size = max_risk_dollars / stop_loss_distance
        
        return min_size.quantize(Decimal('1000'), rounding=ROUND_HALF_UP)
    
    async def _calculate_min_size_by_profit_targets(self, cost_curve: List[Tuple[Decimal, Decimal]]) -> Decimal:
        """Calculate minimum size to achieve meaningful profit targets"""
        # Target minimum $50 profit after 10 pip move
        target_profit = Decimal('50')
        target_movement_pips = 10
        pip_size = Decimal('0.0001')
        
        min_size_for_profit = target_profit / (target_movement_pips * pip_size)
        
        return min_size_for_profit.quantize(Decimal('1000'), rounding=ROUND_HALF_UP)
    
    async def _find_optimal_size_range(self, cost_curve: List[Tuple[Decimal, Decimal]]) -> Tuple[Decimal, Decimal]:
        """Find optimal trade size range for best cost efficiency"""
        if len(cost_curve) < 3:
            return cost_curve[0][0], cost_curve[-1][0]
        
        # Find the range where cost per unit is within 10% of the best
        best_cost = min(cost for _, cost in cost_curve)
        threshold = best_cost * Decimal('1.1')
        
        optimal_sizes = [size for size, cost in cost_curve if cost <= threshold]
        
        if optimal_sizes:
            return min(optimal_sizes), max(optimal_sizes)
        else:
            return cost_curve[0][0], cost_curve[-1][0]
    
    async def _analyze_scalability(self, cost_curve: List[Tuple[Decimal, Decimal]]) -> Dict[str, Any]:
        """Analyze how costs scale with trade size"""
        if len(cost_curve) < 2:
            return {'scalability': 'insufficient_data'}
        
        # Calculate scaling factors
        scaling_factors = []
        for i in range(1, len(cost_curve)):
            size_ratio = float(cost_curve[i][0] / cost_curve[i-1][0])
            cost_ratio = float(cost_curve[i][1] / cost_curve[i-1][1])
            scaling_factors.append(cost_ratio / size_ratio)
        
        avg_scaling = sum(scaling_factors) / len(scaling_factors)
        
        # Determine scalability characteristics
        if avg_scaling < 0.8:
            scalability = 'economies_of_scale'
            description = 'Larger trades are more cost efficient'
        elif avg_scaling > 1.2:
            scalability = 'diseconomies_of_scale'
            description = 'Larger trades are less cost efficient'
        else:
            scalability = 'linear_scaling'
            description = 'Costs scale proportionally with size'
        
        return {
            'scalability': scalability,
            'description': description,
            'average_scaling_factor': avg_scaling,
            'scaling_factors': scaling_factors
        }


class RiskRewardOptimizer:
    """Optimize risk-reward ratios considering costs"""
    
    def __init__(self):
        self.profitability_calculator = ProfitabilityCalculator()
    
    async def optimize_risk_reward(self, trade_params: TradeParameters,
                                 target_risk_reward: Decimal = Decimal('2'),
                                 cost_analyzer = None) -> RiskRewardOptimization:
        """Optimize trade parameters for better risk-reward ratio"""
        
        # Calculate current metrics
        current_analysis = await self.profitability_calculator.calculate_profitability(
            trade_params, cost_analyzer
        )
        
        # Optimize stop loss and take profit
        optimized_sl, optimized_tp = await self._optimize_stop_take_levels(
            trade_params, target_risk_reward, cost_analyzer
        )
        
        # Calculate position size adjustment
        position_adjustment = await self._calculate_position_size_adjustment(
            trade_params, optimized_sl, optimized_tp, cost_analyzer
        )
        
        # Create optimized trade parameters
        optimized_params = TradeParameters(
            instrument=trade_params.instrument,
            entry_price=trade_params.entry_price,
            stop_loss=optimized_sl,
            take_profit=optimized_tp,
            trade_size=trade_params.trade_size * position_adjustment,
            direction=trade_params.direction,
            broker=trade_params.broker,
            holding_period_days=trade_params.holding_period_days
        )
        
        # Calculate optimized metrics
        optimized_analysis = await self.profitability_calculator.calculate_profitability(
            optimized_params, cost_analyzer
        )
        
        # Calculate risk metrics
        expected_return = optimized_analysis.expected_value
        value_at_risk = optimized_analysis.max_adverse_excursion
        max_drawdown = value_at_risk  # Simplified
        
        # Calculate required win rate for breakeven
        win_rate_required = await self._calculate_required_win_rate(optimized_analysis)
        
        # Generate optimization suggestions
        suggestions = await self._generate_optimization_suggestions(
            current_analysis, optimized_analysis
        )
        
        optimization = RiskRewardOptimization(
            trade_parameters=optimized_params,
            current_risk_reward=current_analysis.risk_reward_ratio,
            optimal_risk_reward=optimized_analysis.risk_reward_ratio,
            recommended_stop_loss=optimized_sl,
            recommended_take_profit=optimized_tp,
            position_size_adjustment=position_adjustment,
            expected_return=expected_return,
            value_at_risk=value_at_risk,
            maximum_drawdown=max_drawdown,
            win_rate_required=win_rate_required,
            optimization_suggestions=suggestions
        )
        
        logger.info("Risk-reward optimization completed",
                   current_rr=float(current_analysis.risk_reward_ratio),
                   optimal_rr=float(optimized_analysis.risk_reward_ratio))
        
        return optimization
    
    async def _optimize_stop_take_levels(self, trade_params: TradeParameters,
                                       target_rr: Decimal, cost_analyzer = None) -> Tuple[Decimal, Decimal]:
        """Optimize stop loss and take profit levels"""
        
        # Get cost estimates
        temp_params = TradeParameters(
            instrument=trade_params.instrument,
            entry_price=trade_params.entry_price,
            stop_loss=None,
            take_profit=None,
            trade_size=trade_params.trade_size,
            direction=trade_params.direction,
            broker=trade_params.broker
        )
        
        cost_breakdown = await self.profitability_calculator._estimate_trade_costs(
            temp_params, cost_analyzer
        )
        
        # Calculate minimum movements needed for target risk-reward
        # Accounting for costs in both risk and reward calculations
        
        entry_price = trade_params.entry_price
        cost_per_unit = cost_breakdown.cost_per_unit
        
        # For target risk-reward ratio, if risk = R, then reward should be target_rr * R
        # But we need to account for costs reducing reward and increasing risk
        
        # Start with reasonable risk (e.g., 1% of entry price)
        base_risk_distance = entry_price * Decimal('0.01')
        
        # Calculate actual risk including costs
        total_risk = base_risk_distance + cost_per_unit
        
        # Calculate required reward distance to achieve target RR
        required_net_reward = target_rr * total_risk
        required_gross_reward = required_net_reward + cost_per_unit
        
        # Calculate stop loss and take profit
        if trade_params.direction.lower() == 'buy':
            stop_loss = entry_price - base_risk_distance
            take_profit = entry_price + required_gross_reward
        else:
            stop_loss = entry_price + base_risk_distance
            take_profit = entry_price - required_gross_reward
        
        return stop_loss, take_profit
    
    async def _calculate_position_size_adjustment(self, trade_params: TradeParameters,
                                                optimized_sl: Decimal, optimized_tp: Decimal,
                                                cost_analyzer = None) -> Decimal:
        """Calculate position size adjustment for optimal risk management"""
        
        # Calculate risk with new stop loss
        risk_distance = abs(trade_params.entry_price - optimized_sl)
        
        # Target maximum risk per trade (e.g., $100 for a $10,000 account)
        max_risk_dollars = Decimal('100')
        
        # Calculate optimal position size
        optimal_size = max_risk_dollars / risk_distance
        
        # Calculate adjustment ratio
        adjustment = optimal_size / trade_params.trade_size
        
        # Limit adjustment to reasonable bounds
        return max(Decimal('0.1'), min(Decimal('5.0'), adjustment))
    
    async def _calculate_required_win_rate(self, analysis: ProfitabilityAnalysis) -> Decimal:
        """Calculate minimum win rate required for breakeven"""
        
        if not analysis.trade_parameters.stop_loss or not analysis.trade_parameters.take_profit:
            return Decimal('50')  # Default 50%
        
        # Calculate average win and loss amounts
        gross_win = abs(analysis.trade_parameters.take_profit - analysis.trade_parameters.entry_price) * analysis.trade_parameters.trade_size
        net_win = gross_win - analysis.cost_breakdown.total_cost
        
        gross_loss = abs(analysis.trade_parameters.entry_price - analysis.trade_parameters.stop_loss) * analysis.trade_parameters.trade_size
        total_loss = gross_loss + analysis.cost_breakdown.total_cost
        
        # For breakeven: (win_rate * net_win) = ((1 - win_rate) * total_loss)
        # Solving for win_rate: win_rate = total_loss / (net_win + total_loss)
        
        if net_win + total_loss == 0:
            return Decimal('50')
        
        required_win_rate = total_loss / (net_win + total_loss) * 100
        
        return min(Decimal('95'), max(Decimal('5'), required_win_rate))
    
    async def _generate_optimization_suggestions(self, current: ProfitabilityAnalysis,
                                               optimized: ProfitabilityAnalysis) -> List[str]:
        """Generate actionable optimization suggestions"""
        suggestions = []
        
        # Risk-reward improvement
        rr_improvement = optimized.risk_reward_ratio - current.risk_reward_ratio
        if rr_improvement > Decimal('0.5'):
            suggestions.append(f"Improve risk-reward ratio by {rr_improvement:.2f} with optimized levels")
        
        # Cost efficiency
        if optimized.cost_breakdown.cost_basis_points < current.cost_breakdown.cost_basis_points:
            cost_savings = current.cost_breakdown.cost_basis_points - optimized.cost_breakdown.cost_basis_points
            suggestions.append(f"Reduce costs by {cost_savings:.1f} basis points")
        
        # Profit margin improvement
        margin_improvement = optimized.profit_margin - current.profit_margin
        if margin_improvement > 5:  # 5% improvement
            suggestions.append(f"Increase profit margin by {margin_improvement:.1f}%")
        
        # Position size optimization
        if optimized.trade_parameters.trade_size != current.trade_parameters.trade_size:
            size_change = (optimized.trade_parameters.trade_size / current.trade_parameters.trade_size - 1) * 100
            if abs(size_change) > 10:  # 10% change
                direction = "increase" if size_change > 0 else "decrease"
                suggestions.append(f"Consider {direction} position size by {abs(size_change):.0f}%")
        
        if not suggestions:
            suggestions.append("Current trade parameters are well optimized")
        
        return suggestions


class ScenarioPlanner:
    """Advanced scenario planning and what-if analysis"""
    
    def __init__(self):
        self.profitability_calculator = ProfitabilityCalculator()
    
    async def create_scenario_analysis(self, base_trade_params: TradeParameters,
                                     cost_analyzer = None) -> ScenarioAnalysis:
        """Create comprehensive scenario analysis"""
        
        # Calculate base scenario
        base_scenario = await self.profitability_calculator.calculate_profitability(
            base_trade_params, cost_analyzer
        )
        
        # Create scenario variations
        scenarios = {}
        
        # Market volatility scenarios
        scenarios['high_volatility'] = await self._create_volatility_scenario(
            base_trade_params, 'high', cost_analyzer
        )
        scenarios['low_volatility'] = await self._create_volatility_scenario(
            base_trade_params, 'low', cost_analyzer
        )
        
        # Cost scenarios
        scenarios['high_cost'] = await self._create_cost_scenario(
            base_trade_params, 'high', cost_analyzer
        )
        scenarios['low_cost'] = await self._create_cost_scenario(
            base_trade_params, 'low', cost_analyzer
        )
        
        # Size scenarios
        scenarios['large_position'] = await self._create_size_scenario(
            base_trade_params, 2.0, cost_analyzer
        )
        scenarios['small_position'] = await self._create_size_scenario(
            base_trade_params, 0.5, cost_analyzer
        )
        
        # Time scenarios
        scenarios['quick_exit'] = await self._create_time_scenario(
            base_trade_params, 'quick', cost_analyzer
        )
        scenarios['extended_hold'] = await self._create_time_scenario(
            base_trade_params, 'extended', cost_analyzer
        )
        
        # Identify best/worst cases
        best_case = max(scenarios.values(), key=lambda x: x.net_profit)
        worst_case = min(scenarios.values(), key=lambda x: x.net_profit)
        
        # Most likely scenario (weighted average)
        most_likely = await self._calculate_most_likely_scenario(base_scenario, scenarios)
        
        # Assign scenario probabilities (simplified)
        scenario_probabilities = {
            'base': 0.3,
            'high_volatility': 0.15,
            'low_volatility': 0.15,
            'high_cost': 0.1,
            'low_cost': 0.1,
            'large_position': 0.05,
            'small_position': 0.05,
            'quick_exit': 0.05,
            'extended_hold': 0.05
        }
        
        # Calculate expected outcome
        expected_outcome = await self._calculate_expected_outcome(
            base_scenario, scenarios, scenario_probabilities
        )
        
        # Calculate risk metrics
        risk_metrics = await self._calculate_scenario_risk_metrics(base_scenario, scenarios)
        
        # Sensitivity analysis
        sensitivity_factors = await self._calculate_sensitivity_factors(base_scenario, scenarios)
        
        analysis = ScenarioAnalysis(
            base_scenario=base_scenario,
            scenarios=scenarios,
            best_case=best_case,
            worst_case=worst_case,
            most_likely=most_likely,
            scenario_probabilities=scenario_probabilities,
            expected_outcome=expected_outcome,
            risk_metrics=risk_metrics,
            sensitivity_factors=sensitivity_factors
        )
        
        logger.info("Scenario analysis completed",
                   scenarios_count=len(scenarios),
                   best_case_profit=float(best_case.net_profit),
                   worst_case_profit=float(worst_case.net_profit))
        
        return analysis
    
    async def _create_volatility_scenario(self, base_params: TradeParameters,
                                        volatility_level: str, cost_analyzer = None) -> ProfitabilityAnalysis:
        """Create scenario with different volatility assumptions"""
        
        # Adjust expected volatility
        if volatility_level == 'high':
            volatility_multiplier = Decimal('1.5')
        else:  # low
            volatility_multiplier = Decimal('0.7')
        
        # Adjust stop loss and take profit based on volatility
        if base_params.stop_loss and base_params.take_profit:
            sl_distance = abs(base_params.entry_price - base_params.stop_loss)
            tp_distance = abs(base_params.take_profit - base_params.entry_price)
            
            new_sl_distance = sl_distance * volatility_multiplier
            new_tp_distance = tp_distance * volatility_multiplier
            
            if base_params.direction.lower() == 'buy':
                new_stop_loss = base_params.entry_price - new_sl_distance
                new_take_profit = base_params.entry_price + new_tp_distance
            else:
                new_stop_loss = base_params.entry_price + new_sl_distance
                new_take_profit = base_params.entry_price - new_tp_distance
        else:
            new_stop_loss = base_params.stop_loss
            new_take_profit = base_params.take_profit
        
        scenario_params = TradeParameters(
            instrument=base_params.instrument,
            entry_price=base_params.entry_price,
            stop_loss=new_stop_loss,
            take_profit=new_take_profit,
            trade_size=base_params.trade_size,
            direction=base_params.direction,
            broker=base_params.broker,
            holding_period_days=base_params.holding_period_days,
            expected_volatility=base_params.expected_volatility * volatility_multiplier if base_params.expected_volatility else None
        )
        
        return await self.profitability_calculator.calculate_profitability(scenario_params, cost_analyzer)
    
    async def _create_cost_scenario(self, base_params: TradeParameters,
                                  cost_level: str, cost_analyzer = None) -> ProfitabilityAnalysis:
        """Create scenario with different cost assumptions"""
        
        # For cost scenarios, we would typically modify the cost analyzer
        # For simplicity, we'll adjust the holding period which affects swap costs
        
        if cost_level == 'high':
            # Simulate higher costs by extending holding period
            new_holding_period = max(1, base_params.holding_period_days * 2)
        else:  # low
            # Simulate lower costs by reducing holding period
            new_holding_period = 0
        
        scenario_params = TradeParameters(
            instrument=base_params.instrument,
            entry_price=base_params.entry_price,
            stop_loss=base_params.stop_loss,
            take_profit=base_params.take_profit,
            trade_size=base_params.trade_size,
            direction=base_params.direction,
            broker=base_params.broker,
            holding_period_days=new_holding_period,
            expected_volatility=base_params.expected_volatility
        )
        
        return await self.profitability_calculator.calculate_profitability(scenario_params, cost_analyzer)
    
    async def _create_size_scenario(self, base_params: TradeParameters,
                                  size_multiplier: float, cost_analyzer = None) -> ProfitabilityAnalysis:
        """Create scenario with different position sizes"""
        
        scenario_params = TradeParameters(
            instrument=base_params.instrument,
            entry_price=base_params.entry_price,
            stop_loss=base_params.stop_loss,
            take_profit=base_params.take_profit,
            trade_size=base_params.trade_size * Decimal(str(size_multiplier)),
            direction=base_params.direction,
            broker=base_params.broker,
            holding_period_days=base_params.holding_period_days,
            expected_volatility=base_params.expected_volatility
        )
        
        return await self.profitability_calculator.calculate_profitability(scenario_params, cost_analyzer)
    
    async def _create_time_scenario(self, base_params: TradeParameters,
                                  time_scenario: str, cost_analyzer = None) -> ProfitabilityAnalysis:
        """Create scenario with different time horizons"""
        
        if time_scenario == 'quick':
            new_holding_period = 0  # Intraday
            # Adjust targets for quick exit (smaller moves)
            if base_params.stop_loss and base_params.take_profit:
                sl_distance = abs(base_params.entry_price - base_params.stop_loss) * Decimal('0.5')
                tp_distance = abs(base_params.take_profit - base_params.entry_price) * Decimal('0.5')
                
                if base_params.direction.lower() == 'buy':
                    new_stop_loss = base_params.entry_price - sl_distance
                    new_take_profit = base_params.entry_price + tp_distance
                else:
                    new_stop_loss = base_params.entry_price + sl_distance
                    new_take_profit = base_params.entry_price - tp_distance
            else:
                new_stop_loss = base_params.stop_loss
                new_take_profit = base_params.take_profit
        else:  # extended
            new_holding_period = max(7, base_params.holding_period_days * 3)
            # Keep original targets for extended hold
            new_stop_loss = base_params.stop_loss
            new_take_profit = base_params.take_profit
        
        scenario_params = TradeParameters(
            instrument=base_params.instrument,
            entry_price=base_params.entry_price,
            stop_loss=new_stop_loss,
            take_profit=new_take_profit,
            trade_size=base_params.trade_size,
            direction=base_params.direction,
            broker=base_params.broker,
            holding_period_days=new_holding_period,
            expected_volatility=base_params.expected_volatility
        )
        
        return await self.profitability_calculator.calculate_profitability(scenario_params, cost_analyzer)
    
    async def _calculate_most_likely_scenario(self, base_scenario: ProfitabilityAnalysis,
                                            scenarios: Dict[str, ProfitabilityAnalysis]) -> ProfitabilityAnalysis:
        """Calculate most likely scenario outcome"""
        # For simplicity, return the base scenario as most likely
        # In practice, this would be a weighted combination
        return base_scenario
    
    async def _calculate_expected_outcome(self, base_scenario: ProfitabilityAnalysis,
                                        scenarios: Dict[str, ProfitabilityAnalysis],
                                        probabilities: Dict[str, float]) -> ProfitabilityAnalysis:
        """Calculate probability-weighted expected outcome"""
        # For simplicity, return base scenario
        # In practice, would calculate weighted averages of all metrics
        return base_scenario
    
    async def _calculate_scenario_risk_metrics(self, base_scenario: ProfitabilityAnalysis,
                                             scenarios: Dict[str, ProfitabilityAnalysis]) -> Dict[str, Decimal]:
        """Calculate risk metrics across scenarios"""
        
        all_profits = [base_scenario.net_profit] + [s.net_profit for s in scenarios.values()]
        
        # Calculate various risk metrics
        max_profit = max(all_profits)
        min_profit = min(all_profits)
        profit_range = max_profit - min_profit
        
        # Standard deviation of profits
        mean_profit = sum(all_profits) / len(all_profits)
        variance = sum((p - mean_profit) ** 2 for p in all_profits) / len(all_profits)
        std_dev = variance ** Decimal('0.5')
        
        return {
            'max_profit': max_profit,
            'min_profit': min_profit,
            'profit_range': profit_range,
            'profit_volatility': std_dev,
            'downside_risk': min(Decimal('0'), min_profit)
        }
    
    async def _calculate_sensitivity_factors(self, base_scenario: ProfitabilityAnalysis,
                                           scenarios: Dict[str, ProfitabilityAnalysis]) -> Dict[str, Decimal]:
        """Calculate sensitivity to various factors"""
        
        sensitivity = {}
        base_profit = base_scenario.net_profit
        
        for scenario_name, scenario in scenarios.items():
            if base_profit != 0:
                profit_change = (scenario.net_profit - base_profit) / base_profit * 100
                sensitivity[scenario_name] = profit_change
            else:
                sensitivity[scenario_name] = Decimal('0')
        
        return sensitivity


class BreakEvenCalculator:
    """Main break-even calculator and optimization system"""
    
    def __init__(self):
        self.profitability_calculator = ProfitabilityCalculator()
        self.breakeven_analyzer = BreakEvenAnalyzer()
        self.min_size_calculator = MinimumTradeSizeCalculator()
        self.risk_reward_optimizer = RiskRewardOptimizer()
        self.scenario_planner = ScenarioPlanner()
        
    async def initialize(self) -> None:
        """Initialize break-even calculator system"""
        logger.info("Break-even calculator system initialized")
    
    async def comprehensive_trade_analysis(self, trade_params: TradeParameters,
                                         cost_analyzer = None) -> Dict[str, Any]:
        """Comprehensive trade analysis including all break-even calculations"""
        
        # Profitability analysis
        profitability = await self.profitability_calculator.calculate_profitability(
            trade_params, cost_analyzer
        )
        
        # Break-even analysis
        breakeven = await self.breakeven_analyzer.analyze_break_even(
            trade_params.instrument, trade_params.broker, trade_params.entry_price,
            trade_params.trade_size, trade_params.direction, cost_analyzer
        )
        
        # Minimum trade size analysis
        min_size = await self.min_size_calculator.calculate_minimum_trade_size(
            trade_params.instrument, trade_params.broker, trade_params.entry_price,
            trade_params.direction, cost_analyzer
        )
        
        # Risk-reward optimization
        risk_reward_opt = await self.risk_reward_optimizer.optimize_risk_reward(
            trade_params, Decimal('2'), cost_analyzer
        )
        
        # Scenario analysis
        scenario_analysis = await self.scenario_planner.create_scenario_analysis(
            trade_params, cost_analyzer
        )
        
        return {
            'profitability_analysis': profitability,
            'breakeven_analysis': breakeven,
            'minimum_trade_size': min_size,
            'risk_reward_optimization': risk_reward_opt,
            'scenario_analysis': scenario_analysis,
            'summary': self._generate_analysis_summary(
                profitability, breakeven, risk_reward_opt
            ),
            'recommendations': self._generate_recommendations(
                profitability, breakeven, min_size, risk_reward_opt
            )
        }
    
    def _generate_analysis_summary(self, profitability: ProfitabilityAnalysis,
                                 breakeven: BreakEvenAnalysis,
                                 risk_reward: RiskRewardOptimization) -> Dict[str, str]:
        """Generate executive summary of analysis"""
        
        return {
            'profitability': f"Net profit: {profitability.net_profit:.2f}, ROI: {profitability.return_on_investment:.2f}%",
            'breakeven': f"Break-even at {breakeven.break_even_movement_pips:.1f} pips movement",
            'risk_reward': f"Current RR: {risk_reward.current_risk_reward:.2f}, Optimal RR: {risk_reward.optimal_risk_reward:.2f}",
            'costs': f"Total costs: {profitability.cost_breakdown.total_cost:.2f} ({profitability.cost_breakdown.cost_basis_points:.1f} bps)"
        }
    
    def _generate_recommendations(self, profitability: ProfitabilityAnalysis,
                                breakeven: BreakEvenAnalysis,
                                min_size: MinimumTradeSize,
                                risk_reward: RiskRewardOptimization) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        # Size recommendations
        if profitability.trade_parameters.trade_size < min_size.recommended_minimum:
            recommendations.append(
                f"Consider increasing position size to at least {min_size.recommended_minimum:.0f} for better cost efficiency"
            )
        
        # Risk-reward recommendations
        if risk_reward.optimal_risk_reward > risk_reward.current_risk_reward + Decimal('0.5'):
            recommendations.append(
                f"Optimize stop/target levels to improve risk-reward from {risk_reward.current_risk_reward:.2f} to {risk_reward.optimal_risk_reward:.2f}"
            )
        
        # Cost efficiency recommendations
        if profitability.cost_breakdown.cost_basis_points > 5:
            recommendations.append(
                f"Consider alternative broker or different timing to reduce {profitability.cost_breakdown.cost_basis_points:.1f} bps cost"
            )
        
        # Breakeven recommendations
        if breakeven.break_even_movement_pips > 5:
            recommendations.append(
                f"High break-even requirement ({breakeven.break_even_movement_pips:.1f} pips) - consider larger position or lower-cost broker"
            )
        
        # Add optimization suggestions from risk-reward optimizer
        recommendations.extend(risk_reward.optimization_suggestions)
        
        return recommendations