"""
Portfolio Analytics Engine for comprehensive performance analysis.

Provides real-time portfolio performance metrics, risk-adjusted returns,
attribution analysis, and performance benchmarking capabilities.
"""

import asyncio
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from ..core.models import (
    PortfolioAnalytics,
    Position,
    PerformanceAttribution,
    RiskLevel,
    AssetClass
)


class PortfolioAnalyticsEngine:
    """
    Advanced portfolio analytics engine with real-time performance tracking,
    risk-adjusted return calculations, and comprehensive attribution analysis.
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.business_days_per_year = 252
        
        # Performance caches
        self.price_history: Dict[str, List[Tuple[datetime, Decimal]]] = defaultdict(list)
        self.portfolio_values: Dict[str, List[Tuple[datetime, Decimal]]] = defaultdict(list)
        self.return_series: Dict[str, List[float]] = defaultdict(list)
        
        # Benchmark data
        self.benchmark_returns: List[float] = []
        self.benchmark_prices: List[Tuple[datetime, Decimal]] = []
        
    async def calculate_portfolio_analytics(
        self,
        account_id: str,
        positions: List[Position],
        current_portfolio_value: Decimal,
        cash_balance: Decimal
    ) -> PortfolioAnalytics:
        """Calculate comprehensive portfolio analytics."""
        
        timestamp = datetime.now()
        
        # Basic portfolio metrics
        total_unrealized_pl = sum(pos.unrealized_pl for pos in positions)
        total_realized_pl = sum(pos.realized_pl for pos in positions)
        total_daily_pl = sum(pos.daily_pl for pos in positions)
        
        # Position exposures
        long_exposure = sum(
            pos.market_value for pos in positions 
            if pos.is_long
        )
        short_exposure = sum(
            abs(pos.market_value) for pos in positions 
            if pos.is_short
        )
        net_exposure = long_exposure - short_exposure
        
        # Returns calculation
        returns = await self._calculate_returns(account_id, current_portfolio_value)
        
        # Risk metrics
        volatility = self._calculate_volatility(account_id)
        max_drawdown = await self._calculate_max_drawdown(account_id)
        var_95 = await self._calculate_var(account_id, confidence=0.95)
        expected_shortfall = await self._calculate_expected_shortfall(account_id, confidence=0.95)
        
        # Risk-adjusted returns
        sharpe_ratio = self._calculate_sharpe_ratio(account_id)
        sortino_ratio = self._calculate_sortino_ratio(account_id)
        calmar_ratio = self._calculate_calmar_ratio(account_id, max_drawdown)
        
        # Attribution analysis
        performance_attribution = await self._calculate_performance_attribution(positions)
        sector_allocation = self._calculate_sector_allocation(positions)
        currency_allocation = self._calculate_currency_allocation(positions)
        
        return PortfolioAnalytics(
            account_id=account_id,
            timestamp=timestamp,
            total_value=current_portfolio_value,
            cash_balance=cash_balance,
            unrealized_pl=total_unrealized_pl,
            realized_pl=total_realized_pl,
            total_pl=total_unrealized_pl + total_realized_pl,
            daily_return=returns.get('daily', 0.0),
            weekly_return=returns.get('weekly', 0.0),
            monthly_return=returns.get('monthly', 0.0),
            ytd_return=returns.get('ytd', 0.0),
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            volatility=volatility,
            max_drawdown=max_drawdown,
            var_95=var_95,
            expected_shortfall=expected_shortfall,
            total_positions=len(positions),
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            net_exposure=net_exposure,
            performance_attribution=performance_attribution,
            sector_allocation=sector_allocation,
            currency_allocation=currency_allocation
        )
    
    async def _calculate_returns(
        self, 
        account_id: str, 
        current_value: Decimal
    ) -> Dict[str, float]:
        """Calculate returns over various time periods."""
        
        # Update portfolio value history
        now = datetime.now()
        self.portfolio_values[account_id].append((now, current_value))
        
        # Keep only last 365 days
        cutoff_date = now - timedelta(days=365)
        self.portfolio_values[account_id] = [
            (dt, val) for dt, val in self.portfolio_values[account_id]
            if dt >= cutoff_date
        ]
        
        values = self.portfolio_values[account_id]
        if len(values) < 2:
            return {'daily': 0.0, 'weekly': 0.0, 'monthly': 0.0, 'ytd': 0.0}
        
        returns = {}
        
        # Daily return
        if len(values) >= 2:
            prev_value = float(values[-2][1])
            curr_value = float(current_value)
            returns['daily'] = (curr_value - prev_value) / prev_value if prev_value > 0 else 0.0
        
        # Weekly return
        week_ago = now - timedelta(days=7)
        weekly_values = [(dt, val) for dt, val in values if dt >= week_ago]
        if len(weekly_values) >= 2:
            start_value = float(weekly_values[0][1])
            end_value = float(current_value)
            returns['weekly'] = (end_value - start_value) / start_value if start_value > 0 else 0.0
        else:
            returns['weekly'] = 0.0
        
        # Monthly return
        month_ago = now - timedelta(days=30)
        monthly_values = [(dt, val) for dt, val in values if dt >= month_ago]
        if len(monthly_values) >= 2:
            start_value = float(monthly_values[0][1])
            end_value = float(current_value)
            returns['monthly'] = (end_value - start_value) / start_value if start_value > 0 else 0.0
        else:
            returns['monthly'] = 0.0
        
        # Year-to-date return
        year_start = datetime(now.year, 1, 1)
        ytd_values = [(dt, val) for dt, val in values if dt >= year_start]
        if len(ytd_values) >= 2:
            start_value = float(ytd_values[0][1])
            end_value = float(current_value)
            returns['ytd'] = (end_value - start_value) / start_value if start_value > 0 else 0.0
        else:
            returns['ytd'] = 0.0
        
        # Update return series for risk calculations
        if len(values) >= 2:
            daily_return = returns['daily']
            self.return_series[account_id].append(daily_return)
            
            # Keep only last 252 business days (1 year)
            if len(self.return_series[account_id]) > 252:
                self.return_series[account_id] = self.return_series[account_id][-252:]
        
        return returns
    
    def _calculate_volatility(self, account_id: str) -> float:
        """Calculate annualized volatility."""
        returns = self.return_series.get(account_id, [])
        
        if len(returns) < 30:  # Need at least 30 observations
            return 0.0
        
        # Calculate standard deviation of daily returns
        daily_vol = statistics.stdev(returns) if len(returns) > 1 else 0.0
        
        # Annualize volatility
        annualized_vol = daily_vol * math.sqrt(self.business_days_per_year)
        
        return annualized_vol
    
    async def _calculate_max_drawdown(self, account_id: str) -> float:
        """Calculate maximum drawdown."""
        values = [float(val) for _, val in self.portfolio_values.get(account_id, [])]
        
        if len(values) < 2:
            return 0.0
        
        # Calculate running maximum
        running_max = []
        current_max = values[0]
        
        for value in values:
            current_max = max(current_max, value)
            running_max.append(current_max)
        
        # Calculate drawdowns
        drawdowns = [
            (value - running_max[i]) / running_max[i] 
            for i, value in enumerate(values)
            if running_max[i] > 0
        ]
        
        if not drawdowns:
            return 0.0
        
        return abs(min(drawdowns))  # Return positive value
    
    async def _calculate_var(self, account_id: str, confidence: float = 0.95) -> Decimal:
        """Calculate Value at Risk."""
        returns = self.return_series.get(account_id, [])
        values = [float(val) for _, val in self.portfolio_values.get(account_id, [])]
        
        if len(returns) < 30 or not values:
            return Decimal("0")
        
        # Use historical simulation method
        percentile = (1 - confidence) * 100
        var_return = np.percentile(returns, percentile)
        
        # Convert to dollar VaR
        current_value = values[-1] if values else 0
        var_dollar = abs(var_return * current_value)
        
        return Decimal(str(round(var_dollar, 2)))
    
    async def _calculate_expected_shortfall(self, account_id: str, confidence: float = 0.95) -> Decimal:
        """Calculate Expected Shortfall (Conditional VaR)."""
        returns = self.return_series.get(account_id, [])
        values = [float(val) for _, val in self.portfolio_values.get(account_id, [])]
        
        if len(returns) < 30 or not values:
            return Decimal("0")
        
        # Calculate tail returns beyond VaR threshold
        percentile = (1 - confidence) * 100
        var_threshold = np.percentile(returns, percentile)
        
        tail_returns = [r for r in returns if r <= var_threshold]
        
        if not tail_returns:
            return Decimal("0")
        
        # Average of tail returns
        expected_shortfall_return = np.mean(tail_returns)
        
        # Convert to dollar Expected Shortfall
        current_value = values[-1] if values else 0
        es_dollar = abs(expected_shortfall_return * current_value)
        
        return Decimal(str(round(es_dollar, 2)))
    
    def _calculate_sharpe_ratio(self, account_id: str) -> float:
        """Calculate Sharpe ratio."""
        returns = self.return_series.get(account_id, [])
        
        if len(returns) < 30:
            return 0.0
        
        # Calculate excess returns
        daily_risk_free = self.risk_free_rate / self.business_days_per_year
        excess_returns = [r - daily_risk_free for r in returns]
        
        if not excess_returns:
            return 0.0
        
        mean_excess_return = statistics.mean(excess_returns)
        volatility = statistics.stdev(excess_returns) if len(excess_returns) > 1 else 0.0
        
        if volatility == 0:
            return 0.0
        
        # Annualize
        annualized_return = mean_excess_return * self.business_days_per_year
        annualized_vol = volatility * math.sqrt(self.business_days_per_year)
        
        return annualized_return / annualized_vol if annualized_vol > 0 else 0.0
    
    def _calculate_sortino_ratio(self, account_id: str) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        returns = self.return_series.get(account_id, [])
        
        if len(returns) < 30:
            return 0.0
        
        # Calculate excess returns
        daily_risk_free = self.risk_free_rate / self.business_days_per_year
        excess_returns = [r - daily_risk_free for r in returns]
        
        if not excess_returns:
            return 0.0
        
        mean_excess_return = statistics.mean(excess_returns)
        
        # Calculate downside deviation
        negative_returns = [r for r in excess_returns if r < 0]
        
        if not negative_returns:
            return float('inf') if mean_excess_return > 0 else 0.0
        
        downside_deviation = math.sqrt(sum(r**2 for r in negative_returns) / len(negative_returns))
        
        if downside_deviation == 0:
            return 0.0
        
        # Annualize
        annualized_return = mean_excess_return * self.business_days_per_year
        annualized_downside_vol = downside_deviation * math.sqrt(self.business_days_per_year)
        
        return annualized_return / annualized_downside_vol
    
    def _calculate_calmar_ratio(self, account_id: str, max_drawdown: float) -> float:
        """Calculate Calmar ratio."""
        returns = self.return_series.get(account_id, [])
        
        if len(returns) < 30 or max_drawdown == 0:
            return 0.0
        
        # Annualized return
        mean_return = statistics.mean(returns)
        annualized_return = mean_return * self.business_days_per_year
        
        return annualized_return / max_drawdown
    
    async def _calculate_performance_attribution(self, positions: List[Position]) -> Dict[str, float]:
        """Calculate performance attribution by various factors."""
        if not positions:
            return {}
        
        total_value = sum(float(pos.market_value) for pos in positions)
        
        if total_value == 0:
            return {}
        
        attribution = {}
        
        # Asset class attribution
        asset_class_returns = defaultdict(list)
        asset_class_weights = defaultdict(float)
        
        for position in positions:
            weight = float(position.market_value) / total_value
            daily_return = float(position.daily_pl) / float(position.market_value) if position.market_value != 0 else 0
            
            asset_class_returns[position.asset_class.value].append((weight, daily_return))
            asset_class_weights[position.asset_class.value] += weight
        
        # Calculate weighted attribution by asset class
        for asset_class, weight_returns in asset_class_returns.items():
            weighted_return = sum(weight * ret for weight, ret in weight_returns)
            attribution[f"asset_class_{asset_class}"] = weighted_return
        
        # Currency attribution (simplified)
        currency_attribution = {}
        for position in positions:
            currency = position.instrument.split('_')[0] if '_' in position.instrument else 'USD'
            weight = float(position.market_value) / total_value
            daily_return = float(position.daily_pl) / float(position.market_value) if position.market_value != 0 else 0
            
            if currency not in currency_attribution:
                currency_attribution[currency] = 0
            currency_attribution[currency] += weight * daily_return
        
        attribution.update({f"currency_{k}": v for k, v in currency_attribution.items()})
        
        return attribution
    
    def _calculate_sector_allocation(self, positions: List[Position]) -> Dict[str, float]:
        """Calculate sector allocation."""
        total_value = sum(float(abs(pos.market_value)) for pos in positions)
        
        if total_value == 0:
            return {}
        
        sector_allocation = defaultdict(float)
        
        for position in positions:
            # Simplified sector mapping based on asset class
            sector = position.asset_class.value
            weight = float(abs(position.market_value)) / total_value
            sector_allocation[sector] += weight
        
        return dict(sector_allocation)
    
    def _calculate_currency_allocation(self, positions: List[Position]) -> Dict[str, float]:
        """Calculate currency allocation."""
        total_value = sum(float(abs(pos.market_value)) for pos in positions)
        
        if total_value == 0:
            return {}
        
        currency_allocation = defaultdict(float)
        
        for position in positions:
            # Extract base currency from instrument
            currency = position.instrument.split('_')[0] if '_' in position.instrument else 'USD'
            weight = float(abs(position.market_value)) / total_value
            currency_allocation[currency] += weight
        
        return dict(currency_allocation)
    
    async def generate_performance_attribution_report(
        self,
        account_id: str,
        start_date: datetime,
        end_date: datetime,
        positions: List[Position]
    ) -> PerformanceAttribution:
        """Generate detailed performance attribution report."""
        
        # Calculate total return for period
        period_values = [
            (dt, val) for dt, val in self.portfolio_values.get(account_id, [])
            if start_date <= dt <= end_date
        ]
        
        if len(period_values) < 2:
            total_return = 0.0
        else:
            start_value = float(period_values[0][1])
            end_value = float(period_values[-1][1])
            total_return = (end_value - start_value) / start_value if start_value > 0 else 0.0
        
        # Calculate attribution effects
        performance_attribution = await self._calculate_performance_attribution(positions)
        sector_attribution = self._calculate_sector_allocation(positions)
        currency_attribution = self._calculate_currency_allocation(positions)
        
        # Calculate top contributors and detractors
        position_contributions = []
        for position in positions:
            contribution = float(position.daily_pl) / float(position.market_value) if position.market_value != 0 else 0
            position_contributions.append({
                'instrument': position.instrument,
                'contribution': contribution,
                'pl': float(position.daily_pl)
            })
        
        # Sort by contribution
        position_contributions.sort(key=lambda x: x['contribution'], reverse=True)
        
        top_contributors = position_contributions[:5]
        top_detractors = position_contributions[-5:]
        
        return PerformanceAttribution(
            account_id=account_id,
            period_start=start_date.date(),
            period_end=end_date.date(),
            total_return=total_return,
            asset_allocation_effect=0.0,  # Simplified for MVP
            security_selection_effect=total_return,  # Simplified
            interaction_effect=0.0,
            currency_effect=sum(v for k, v in performance_attribution.items() if k.startswith('currency_')),
            sector_attribution=sector_attribution,
            currency_attribution=currency_attribution,
            strategy_attribution={},  # To be implemented
            top_contributors=top_contributors,
            top_detractors=top_detractors
        )
    
    def get_performance_summary(self, account_id: str) -> Dict[str, float]:
        """Get performance summary metrics."""
        returns = self.return_series.get(account_id, [])
        
        if not returns:
            return {}
        
        return {
            'total_returns': len(returns),
            'mean_daily_return': statistics.mean(returns),
            'volatility': self._calculate_volatility(account_id),
            'sharpe_ratio': self._calculate_sharpe_ratio(account_id),
            'sortino_ratio': self._calculate_sortino_ratio(account_id),
            'best_day': max(returns),
            'worst_day': min(returns),
            'positive_days': sum(1 for r in returns if r > 0),
            'negative_days': sum(1 for r in returns if r < 0),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns) if returns else 0
        }