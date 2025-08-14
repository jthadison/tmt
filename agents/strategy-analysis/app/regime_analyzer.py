"""
Market regime analyzer for strategy performance evaluation.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import asyncio
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .models import (
    MarketRegime, RegimePerformance, RegimeCharacteristics, 
    RegimeEffectiveness, RegimeStatistics, PerformanceMetrics,
    VolatilityLevel, VolumeProfile, TrendDirection
)

logger = logging.getLogger(__name__)


class MarketData:
    """Market data point for regime classification."""
    def __init__(self, timestamp: datetime, price: Decimal, volume: Decimal,
                 volatility: Decimal, trend_strength: Decimal):
        self.timestamp = timestamp
        self.price = price
        self.volume = volume
        self.volatility = volatility
        self.trend_strength = trend_strength


class MarketRegimeAnalyzer:
    """
    Market regime analyzer for classifying market conditions and 
    evaluating strategy performance in different regimes.
    """
    
    def __init__(self):
        self.regime_classifier = None
        self.scaler = StandardScaler()
        
        # Regime classification thresholds
        self.volatility_thresholds = {
            'low': Decimal('0.01'),     # 1% daily volatility
            'high': Decimal('0.03')     # 3% daily volatility
        }
        
        self.trend_thresholds = {
            'strong': Decimal('0.02'),   # 2% daily trend
            'weak': Decimal('0.005')     # 0.5% daily trend
        }
        
        self.volume_thresholds = {
            'low': Decimal('0.8'),      # 80% of average volume
            'high': Decimal('1.5')      # 150% of average volume
        }
    
    async def analyze_regime_performance(self, trades: List) -> Dict[MarketRegime, RegimePerformance]:
        """
        Analyze strategy performance across different market regimes.
        
        Args:
            trades: List of Trade objects with timestamps
            
        Returns:
            Dictionary mapping regimes to performance metrics
        """
        logger.info("Analyzing regime-based performance")
        
        if not trades:
            return {}
        
        # Classify market regime for each trade
        regime_trades = await self._classify_trades_by_regime(trades)
        
        # Calculate performance for each regime
        regime_performance = {}
        
        for regime, regime_trade_list in regime_trades.items():
            if len(regime_trade_list) >= 5:  # Minimum trades for regime analysis
                performance = self._calculate_regime_performance(regime, regime_trade_list, trades)
                regime_performance[regime] = performance
        
        return regime_performance
    
    async def _classify_trades_by_regime(self, trades: List) -> Dict[MarketRegime, List]:
        """Classify trades by market regime at time of execution."""
        regime_trades = {regime: [] for regime in MarketRegime}
        
        for trade in trades:
            # Get market data around trade time
            market_data = await self._get_market_data_at_time(trade.timestamp)
            
            # Classify regime
            regime = await self._classify_regime(market_data, trade.timestamp)
            
            regime_trades[regime].append(trade)
        
        return regime_trades
    
    async def _get_market_data_at_time(self, timestamp: datetime) -> MarketData:
        """
        Get market data at specific timestamp for regime classification.
        In production, this would query actual market data.
        """
        # Mock implementation - would query actual market data service
        return MarketData(
            timestamp=timestamp,
            price=Decimal('1.1000'),  # Mock price
            volume=Decimal('1000000'),  # Mock volume
            volatility=Decimal('0.015'),  # Mock volatility
            trend_strength=Decimal('0.01')  # Mock trend strength
        )
    
    async def _classify_regime(self, market_data: MarketData, timestamp: datetime) -> MarketRegime:
        """
        Classify market regime based on market conditions.
        
        Uses volatility, trend strength, and volume to determine regime.
        """
        # Calculate volatility level
        volatility = market_data.volatility
        
        # Calculate trend direction and strength
        trend_strength = market_data.trend_strength
        
        # Determine regime based on conditions
        if trend_strength >= self.trend_thresholds['strong']:
            if trend_strength > 0:
                return MarketRegime.STRONG_UPTREND
            else:
                return MarketRegime.STRONG_DOWNTREND
        elif abs(trend_strength) >= self.trend_thresholds['weak']:
            if trend_strength > 0:
                return MarketRegime.WEAK_UPTREND
            else:
                return MarketRegime.WEAK_DOWNTREND
        else:
            return MarketRegime.SIDEWAYS
    
    def _calculate_regime_performance(self, regime: MarketRegime, 
                                    regime_trades: List, 
                                    all_trades: List) -> RegimePerformance:
        """Calculate comprehensive performance metrics for a specific regime."""
        
        # Calculate basic performance metrics
        performance = self._calculate_performance_metrics_for_trades(regime_trades)
        
        # Calculate regime characteristics
        characteristics = self._calculate_regime_characteristics(regime, regime_trades)
        
        # Calculate effectiveness metrics
        overall_performance = self._calculate_performance_metrics_for_trades(all_trades)
        effectiveness = self._calculate_regime_effectiveness(performance, overall_performance, regime)
        
        # Calculate regime statistics
        statistics = self._calculate_regime_statistics(regime_trades, regime)
        
        return RegimePerformance(
            regime=regime,
            performance=performance,
            characteristics=characteristics,
            effectiveness=effectiveness,
            statistics=statistics
        )
    
    def _calculate_performance_metrics_for_trades(self, trades: List) -> PerformanceMetrics:
        """Calculate performance metrics from trade list."""
        if not trades:
            return self._empty_performance_metrics()
        
        total_trades = len(trades)
        wins = [t for t in trades if t.win]
        losses = [t for t in trades if not t.win]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = Decimal(win_count) / Decimal(total_trades) if total_trades > 0 else Decimal('0')
        
        # PnL calculations
        total_pnl = sum(t.pnl for t in trades)
        winning_pnl = sum(t.pnl for t in wins) if wins else Decimal('0')
        losing_pnl = abs(sum(t.pnl for t in losses)) if losses else Decimal('0')
        
        average_win = winning_pnl / Decimal(win_count) if win_count > 0 else Decimal('0')
        average_loss = losing_pnl / Decimal(loss_count) if loss_count > 0 else Decimal('0')
        
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else Decimal('1000')
        expectancy = (win_rate * average_win) - ((Decimal('1') - win_rate) * average_loss)
        
        # Time-based calculations
        if trades:
            total_hold_seconds = sum(t.hold_time.total_seconds() for t in trades)
            average_hold_time = timedelta(seconds=total_hold_seconds / total_trades)
        else:
            average_hold_time = timedelta(0)
        
        # Risk metrics (simplified)
        max_drawdown = self._calculate_max_drawdown(trades)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        calmar_ratio = self._calculate_calmar_ratio(total_pnl, max_drawdown, len(trades))
        
        # Returns
        total_return = total_pnl
        if len(trades) > 1:
            days_traded = (trades[-1].timestamp - trades[0].timestamp).days
            days_traded = max(days_traded, 1)  # Prevent division by zero
            annualized_return = total_return * Decimal('365') / Decimal(days_traded)
        else:
            annualized_return = Decimal('0')
        
        return PerformanceMetrics(
            total_trades=total_trades,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            average_win=average_win,
            average_loss=average_loss,
            average_hold_time=average_hold_time,
            total_return=total_return,
            annualized_return=annualized_return
        )
    
    def _calculate_regime_characteristics(self, regime: MarketRegime, trades: List) -> RegimeCharacteristics:
        """Calculate characteristics of the market regime."""
        
        # Determine volatility level based on regime
        if regime in [MarketRegime.STRONG_UPTREND, MarketRegime.STRONG_DOWNTREND]:
            volatility = VolatilityLevel.HIGH
        elif regime == MarketRegime.SIDEWAYS:
            volatility = VolatilityLevel.LOW
        else:
            volatility = VolatilityLevel.MEDIUM
        
        # Determine volume profile (simplified)
        volume_profile = VolumeProfile.NORMAL  # Would be calculated from actual volume data
        
        # Determine trading sessions (simplified)
        time_of_day = ["london", "new_york"]  # Would be calculated from trade timestamps
        
        return RegimeCharacteristics(
            volatility=volatility,
            trend=regime,
            volume_profile=volume_profile,
            time_of_day=time_of_day
        )
    
    def _calculate_regime_effectiveness(self, regime_performance: PerformanceMetrics,
                                      overall_performance: PerformanceMetrics,
                                      regime: MarketRegime) -> RegimeEffectiveness:
        """Calculate how effective the strategy is in this regime."""
        
        # Calculate relative performance
        if overall_performance.expectancy != 0:
            relative_performance = regime_performance.expectancy / overall_performance.expectancy
        else:
            relative_performance = Decimal('1')
        
        # Determine if this is a preferred regime
        preferred_regime = relative_performance > Decimal('1.1')  # 10% better than average
        
        # Calculate consistency (simplified)
        consistency = min(regime_performance.win_rate * Decimal('2'), Decimal('1'))
        
        # Calculate adaptability (simplified)
        adaptability = Decimal('0.8')  # Would be calculated based on performance stability
        
        return RegimeEffectiveness(
            preferred_regime=preferred_regime,
            relative_performance=relative_performance,
            consistency=consistency,
            adaptability=adaptability
        )
    
    def _calculate_regime_statistics(self, trades: List, regime: MarketRegime) -> RegimeStatistics:
        """Calculate statistical information about regime occurrence."""
        
        total_trades = len(trades)
        
        # Estimate occurrences and duration (would be calculated from historical data)
        occurrences = max(1, total_trades // 10)  # Simplified estimation
        average_trades_per_occurrence = Decimal(total_trades) / Decimal(occurrences)
        regime_duration = timedelta(hours=24)  # Simplified - would be calculated from actual data
        
        return RegimeStatistics(
            occurrences=occurrences,
            total_trades=total_trades,
            average_trades_per_occurrence=average_trades_per_occurrence,
            regime_duration=regime_duration
        )
    
    def _calculate_max_drawdown(self, trades: List) -> Decimal:
        """Calculate maximum drawdown from trade sequence."""
        if not trades:
            return Decimal('0')
        
        running_pnl = Decimal('0')
        peak = Decimal('0')
        max_drawdown = Decimal('0')
        
        for trade in trades:
            running_pnl += trade.pnl
            peak = max(peak, running_pnl)
            drawdown = peak - running_pnl
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self, trades: List) -> Decimal:
        """Calculate Sharpe ratio (simplified version)."""
        if not trades or len(trades) < 2:
            return Decimal('0')
        
        returns = [trade.pnl for trade in trades]
        mean_return = sum(returns) / len(returns)
        
        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** Decimal('0.5')
        
        if std_dev == 0:
            return Decimal('0')
        
        sharpe = mean_return / std_dev
        return sharpe
    
    def _calculate_calmar_ratio(self, total_return: Decimal, max_drawdown: Decimal, num_trades: int) -> Decimal:
        """Calculate Calmar ratio."""
        if max_drawdown == 0 or num_trades == 0:
            return Decimal('0')
        
        # Simplified Calmar ratio
        annualized_return = total_return * Decimal('252') / Decimal(num_trades)
        calmar = annualized_return / max_drawdown if max_drawdown > 0 else Decimal('0')
        return calmar
    
    def _empty_performance_metrics(self) -> PerformanceMetrics:
        """Create empty performance metrics."""
        return PerformanceMetrics(
            total_trades=0,
            win_count=0,
            loss_count=0,
            win_rate=Decimal('0'),
            profit_factor=Decimal('0'),
            expectancy=Decimal('0'),
            sharpe_ratio=Decimal('0'),
            calmar_ratio=Decimal('0'),
            max_drawdown=Decimal('0'),
            average_win=Decimal('0'),
            average_loss=Decimal('0'),
            average_hold_time=timedelta(0),
            total_return=Decimal('0'),
            annualized_return=Decimal('0')
        )
    
    async def train_regime_classifier(self, historical_data: List[MarketData]) -> None:
        """
        Train ML model for automated regime classification.
        
        Args:
            historical_data: Historical market data for training
        """
        if len(historical_data) < 100:  # Need sufficient data
            logger.warning("Insufficient data for regime classifier training")
            return
        
        # Prepare features for training
        features = []
        for data in historical_data:
            feature_vector = [
                float(data.volatility),
                float(data.trend_strength),
                float(data.volume)
            ]
            features.append(feature_vector)
        
        # Normalize features
        features_normalized = self.scaler.fit_transform(features)
        
        # Train KMeans clustering for regime identification
        self.regime_classifier = KMeans(n_clusters=5, random_state=42)
        self.regime_classifier.fit(features_normalized)
        
        logger.info("Regime classifier trained successfully")
    
    async def predict_regime(self, market_data: MarketData) -> MarketRegime:
        """
        Predict market regime using trained classifier.
        
        Args:
            market_data: Current market data
            
        Returns:
            Predicted market regime
        """
        if self.regime_classifier is None:
            # Fallback to rule-based classification
            return await self._classify_regime(market_data, market_data.timestamp)
        
        # Prepare features
        features = [[
            float(market_data.volatility),
            float(market_data.trend_strength),
            float(market_data.volume)
        ]]
        
        # Normalize and predict
        features_normalized = self.scaler.transform(features)
        cluster = self.regime_classifier.predict(features_normalized)[0]
        
        # Map cluster to regime (simplified mapping)
        regime_mapping = {
            0: MarketRegime.STRONG_UPTREND,
            1: MarketRegime.WEAK_UPTREND,
            2: MarketRegime.SIDEWAYS,
            3: MarketRegime.WEAK_DOWNTREND,
            4: MarketRegime.STRONG_DOWNTREND
        }
        
        return regime_mapping.get(cluster, MarketRegime.SIDEWAYS)