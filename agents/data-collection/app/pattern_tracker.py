"""
Pattern success tracking system.

This module implements pattern identification, performance tracking, and
success rate calculations across different timeframes and market regimes.
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
    PatternPerformance,
    SuccessMetrics,
    PatternEvolution,
    PatternStatistics,
    MarketRegime,
    MarketSession,
)


logger = logging.getLogger(__name__)


@dataclass
class PatternIdentifier:
    """Identifies and tags trading patterns."""
    
    def identify_pattern(self, record: ComprehensiveTradeRecord) -> Tuple[str, Dict[str, Any]]:
        """
        Identify pattern from trade record and return pattern ID with metadata.
        
        Returns:
            Tuple of (pattern_id, pattern_metadata)
        """
        pattern_type = record.signal_context.pattern_type
        pattern_subtype = record.signal_context.pattern_subtype
        
        # Create comprehensive pattern identifier
        pattern_id = self._create_pattern_id(
            pattern_type=pattern_type,
            pattern_subtype=pattern_subtype,
            market_regime=record.market_conditions.market_regime,
            session=record.market_conditions.session,
            symbol=record.trade_details.symbol
        )
        
        # Extract pattern metadata
        metadata = {
            "pattern_type": pattern_type,
            "pattern_subtype": pattern_subtype,
            "market_regime": record.market_conditions.market_regime.value,
            "session": record.market_conditions.session.value,
            "symbol": record.trade_details.symbol,
            "timeframe": self._determine_timeframe(record),
            "volatility_level": self._classify_volatility(record.market_conditions.volatility),
            "confidence": record.signal_context.confidence,
            "strength": record.signal_context.strength,
            "volume_confirmation": record.signal_context.volume_confirmation,
            "cross_confirmation": record.signal_context.cross_confirmation,
        }
        
        return pattern_id, metadata
    
    def _create_pattern_id(
        self,
        pattern_type: str,
        pattern_subtype: str,
        market_regime: MarketRegime,
        session: MarketSession,
        symbol: str
    ) -> str:
        """Create unique pattern identifier."""
        return f"{pattern_type}_{pattern_subtype}_{market_regime.value}_{session.value}_{symbol}"
    
    def _determine_timeframe(self, record: ComprehensiveTradeRecord) -> str:
        """Determine effective timeframe based on trade duration and market conditions."""
        # This would typically be provided by the signal generation system
        # For now, classify based on expected trade duration or market conditions
        
        atr = record.market_conditions.atr14
        volatility = record.market_conditions.volatility
        
        # Simple timeframe classification based on volatility and expected duration
        if volatility > Decimal("0.8") or atr > Decimal("100"):
            return "H1"  # High volatility suggests shorter timeframes
        elif volatility > Decimal("0.4") or atr > Decimal("50"):
            return "H4"
        else:
            return "D1"  # Lower volatility suggests daily patterns
    
    def _classify_volatility(self, volatility: Decimal) -> str:
        """Classify volatility level."""
        if volatility > Decimal("0.8"):
            return "high"
        elif volatility > Decimal("0.4"):
            return "medium"
        else:
            return "low"


class PatternSuccessCalculator:
    """Calculates success rates and performance metrics for patterns."""
    
    def __init__(self):
        self.min_sample_size = 30  # Minimum trades for statistical significance
        self.confidence_level = Decimal("0.95")  # 95% confidence interval
    
    def calculate_success_metrics(self, trades: List[ComprehensiveTradeRecord]) -> SuccessMetrics:
        """Calculate comprehensive success metrics from trade history."""
        if not trades:
            return self._create_empty_metrics()
        
        total_trades = len(trades)
        wins = [t for t in trades if t.performance.actual_outcome == "win"]
        losses = [t for t in trades if t.performance.actual_outcome == "loss"]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = Decimal(str(win_count / total_trades)) if total_trades > 0 else Decimal("0")
        
        # Calculate average win/loss
        average_win = Decimal("0")
        if wins:
            win_amounts = [t.performance.actual_pnl for t in wins]
            average_win = sum(win_amounts) / Decimal(str(len(win_amounts)))
        
        average_loss = Decimal("0")
        if losses:
            loss_amounts = [abs(t.performance.actual_pnl) for t in losses]
            average_loss = sum(loss_amounts) / Decimal(str(len(loss_amounts)))
        
        # Calculate profit factor
        gross_profit = sum(t.performance.actual_pnl for t in wins)
        gross_loss = sum(abs(t.performance.actual_pnl) for t in losses)
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else Decimal("0")
        
        # Calculate expectancy
        expectancy = (win_rate * average_win) - ((Decimal("1") - win_rate) * average_loss)
        
        # Calculate maximum drawdown
        max_drawdown = self._calculate_max_drawdown(trades)
        
        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        
        return SuccessMetrics(
            total_trades=total_trades,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            last_updated=datetime.now()
        )
    
    def _calculate_max_drawdown(self, trades: List[ComprehensiveTradeRecord]) -> Decimal:
        """Calculate maximum drawdown from trade sequence."""
        if not trades:
            return Decimal("0")
        
        # Sort trades by timestamp
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)
        
        # Calculate cumulative PnL
        cumulative_pnl = Decimal("0")
        peak_pnl = Decimal("0")
        max_drawdown = Decimal("0")
        
        for trade in sorted_trades:
            cumulative_pnl += trade.performance.actual_pnl
            
            if cumulative_pnl > peak_pnl:
                peak_pnl = cumulative_pnl
            
            drawdown = peak_pnl - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self, trades: List[ComprehensiveTradeRecord]) -> Decimal:
        """Calculate Sharpe ratio from trade returns."""
        if len(trades) < 2:
            return Decimal("0")
        
        returns = [t.performance.holding_period_return for t in trades if t.performance.holding_period_return != 0]
        
        if len(returns) < 2:
            return Decimal("0")
        
        # Convert to float for statistics calculation
        float_returns = [float(r) for r in returns]
        
        try:
            mean_return = Decimal(str(statistics.mean(float_returns)))
            std_return = Decimal(str(statistics.stdev(float_returns)))
            
            if std_return == 0:
                return Decimal("0")
            
            # Assume risk-free rate of 2% annually (convert to trade-level)
            risk_free_rate = Decimal("0.02") / Decimal("252")  # Daily risk-free rate
            
            sharpe = (mean_return - risk_free_rate) / std_return
            return sharpe
            
        except (statistics.StatisticsError, ValueError):
            return Decimal("0")
    
    def _create_empty_metrics(self) -> SuccessMetrics:
        """Create empty success metrics."""
        return SuccessMetrics(
            total_trades=0,
            win_count=0,
            loss_count=0,
            win_rate=Decimal("0"),
            average_win=Decimal("0"),
            average_loss=Decimal("0"),
            profit_factor=Decimal("0"),
            expectancy=Decimal("0"),
            max_drawdown=Decimal("0"),
            sharpe_ratio=Decimal("0"),
            last_updated=datetime.now()
        )


class MarketRegimeClassifier:
    """Classifies market regimes for pattern context."""
    
    def classify_regime(self, record: ComprehensiveTradeRecord) -> MarketRegime:
        """
        Classify market regime based on multiple indicators.
        This enhances the basic classification from feature extractors.
        """
        # Get basic classification from record
        base_regime = record.market_conditions.market_regime
        
        # Enhance classification with additional analysis
        enhanced_regime = self._enhance_classification(record, base_regime)
        
        return enhanced_regime
    
    def _enhance_classification(
        self,
        record: ComprehensiveTradeRecord,
        base_regime: MarketRegime
    ) -> MarketRegime:
        """Enhance market regime classification with additional indicators."""
        
        # Collect relevant indicators
        volatility = record.market_conditions.volatility
        atr = record.market_conditions.atr14
        volume = record.market_conditions.volume
        ma_alignment = record.market_conditions.moving_average_alignment
        rsi = record.market_conditions.rsi_level
        
        # Calculate trend strength
        trend_strength = abs(ma_alignment) if ma_alignment else Decimal("0")
        
        # Volatility thresholds (these would be calibrated based on historical data)
        high_vol_threshold = Decimal("0.8")
        low_vol_threshold = Decimal("0.3")
        
        # Enhanced classification logic
        if volatility > high_vol_threshold or atr > Decimal("150"):
            return MarketRegime.VOLATILE
        elif trend_strength > Decimal("0.7") and volatility > Decimal("0.4"):
            return MarketRegime.TRENDING
        elif volatility < low_vol_threshold and trend_strength < Decimal("0.3"):
            return MarketRegime.QUIET
        else:
            # Use RSI to help distinguish between ranging and trending
            if Decimal("40") <= rsi <= Decimal("60") and trend_strength < Decimal("0.5"):
                return MarketRegime.RANGING
            else:
                return base_regime


class PatternPerformanceAnalyzer:
    """Analyzes pattern performance across different contexts."""
    
    def __init__(self):
        self.pattern_identifier = PatternIdentifier()
        self.success_calculator = PatternSuccessCalculator()
        self.regime_classifier = MarketRegimeClassifier()
    
    def analyze_pattern_performance(
        self,
        pattern_id: str,
        trades: List[ComprehensiveTradeRecord]
    ) -> PatternPerformance:
        """Analyze comprehensive pattern performance."""
        
        if not trades:
            return self._create_empty_pattern_performance(pattern_id)
        
        # Calculate overall success rates
        overall_metrics = self.success_calculator.calculate_success_metrics(trades)
        
        # Calculate success rates by different contexts
        success_rates = {
            "overall": overall_metrics,
            "byTimeframe": self._calculate_by_timeframe(trades),
            "byMarketRegime": self._calculate_by_market_regime(trades),
            "bySession": self._calculate_by_session(trades),
            "byVolatility": self._calculate_by_volatility(trades),
            "bySymbol": self._calculate_by_symbol(trades),
        }
        
        # Calculate pattern evolution metrics
        evolution = self._calculate_pattern_evolution(trades)
        
        # Calculate statistical significance
        statistics = self._calculate_pattern_statistics(trades)
        
        # Extract pattern name from first trade
        pattern_name = f"{trades[0].signal_context.pattern_type}_{trades[0].signal_context.pattern_subtype}"
        
        return PatternPerformance(
            pattern_id=pattern_id,
            pattern_name=pattern_name,
            success_rates=success_rates,
            evolution=evolution,
            statistics=statistics
        )
    
    def _calculate_by_timeframe(self, trades: List[ComprehensiveTradeRecord]) -> Dict[str, SuccessMetrics]:
        """Calculate success rates by timeframe."""
        timeframe_groups = defaultdict(list)
        
        for trade in trades:
            timeframe = self.pattern_identifier._determine_timeframe(trade)
            timeframe_groups[timeframe].append(trade)
        
        return {
            tf: self.success_calculator.calculate_success_metrics(tf_trades)
            for tf, tf_trades in timeframe_groups.items()
        }
    
    def _calculate_by_market_regime(self, trades: List[ComprehensiveTradeRecord]) -> Dict[str, SuccessMetrics]:
        """Calculate success rates by market regime."""
        regime_groups = defaultdict(list)
        
        for trade in trades:
            regime = trade.market_conditions.market_regime.value
            regime_groups[regime].append(trade)
        
        return {
            regime: self.success_calculator.calculate_success_metrics(regime_trades)
            for regime, regime_trades in regime_groups.items()
        }
    
    def _calculate_by_session(self, trades: List[ComprehensiveTradeRecord]) -> Dict[str, SuccessMetrics]:
        """Calculate success rates by trading session."""
        session_groups = defaultdict(list)
        
        for trade in trades:
            session = trade.market_conditions.session.value
            session_groups[session].append(trade)
        
        return {
            session: self.success_calculator.calculate_success_metrics(session_trades)
            for session, session_trades in session_groups.items()
        }
    
    def _calculate_by_volatility(self, trades: List[ComprehensiveTradeRecord]) -> Dict[str, SuccessMetrics]:
        """Calculate success rates by volatility level."""
        volatility_groups = defaultdict(list)
        
        for trade in trades:
            vol_level = self.pattern_identifier._classify_volatility(trade.market_conditions.volatility)
            volatility_groups[vol_level].append(trade)
        
        return {
            vol_level: self.success_calculator.calculate_success_metrics(vol_trades)
            for vol_level, vol_trades in volatility_groups.items()
        }
    
    def _calculate_by_symbol(self, trades: List[ComprehensiveTradeRecord]) -> Dict[str, SuccessMetrics]:
        """Calculate success rates by symbol."""
        symbol_groups = defaultdict(list)
        
        for trade in trades:
            symbol = trade.trade_details.symbol
            symbol_groups[symbol].append(trade)
        
        return {
            symbol: self.success_calculator.calculate_success_metrics(symbol_trades)
            for symbol, symbol_trades in symbol_groups.items()
        }
    
    def _calculate_pattern_evolution(self, trades: List[ComprehensiveTradeRecord]) -> PatternEvolution:
        """Calculate pattern evolution metrics."""
        if not trades:
            return PatternEvolution(
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                total_occurrences=0,
                recent_trend="stable",
                adaptation_required=False
            )
        
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)
        first_seen = sorted_trades[0].timestamp
        last_seen = sorted_trades[-1].timestamp
        total_occurrences = len(trades)
        
        # Analyze recent trend (last 30 days vs previous 30 days)
        recent_trend = self._analyze_recent_trend(sorted_trades)
        
        # Determine if adaptation is required
        recent_performance = self._get_recent_performance(sorted_trades)
        adaptation_required = recent_performance.win_rate < Decimal("0.4")  # Below 40% win rate
        
        return PatternEvolution(
            first_seen=first_seen,
            last_seen=last_seen,
            total_occurrences=total_occurrences,
            recent_trend=recent_trend,
            adaptation_required=adaptation_required
        )
    
    def _analyze_recent_trend(self, sorted_trades: List[ComprehensiveTradeRecord]) -> str:
        """Analyze recent performance trend."""
        if len(sorted_trades) < 10:
            return "stable"  # Not enough data
        
        # Split into recent vs historical periods
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_trades = [t for t in sorted_trades if t.timestamp > cutoff_date]
        historical_trades = [t for t in sorted_trades if t.timestamp <= cutoff_date]
        
        if not recent_trades or not historical_trades:
            return "stable"
        
        recent_metrics = self.success_calculator.calculate_success_metrics(recent_trades)
        historical_metrics = self.success_calculator.calculate_success_metrics(historical_trades)
        
        # Compare win rates
        win_rate_diff = recent_metrics.win_rate - historical_metrics.win_rate
        
        if win_rate_diff > Decimal("0.1"):  # 10% improvement
            return "improving"
        elif win_rate_diff < Decimal("-0.1"):  # 10% decline
            return "declining"
        else:
            return "stable"
    
    def _get_recent_performance(self, sorted_trades: List[ComprehensiveTradeRecord]) -> SuccessMetrics:
        """Get performance metrics for recent trades."""
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_trades = [t for t in sorted_trades if t.timestamp > cutoff_date]
        
        return self.success_calculator.calculate_success_metrics(recent_trades)
    
    def _calculate_pattern_statistics(self, trades: List[ComprehensiveTradeRecord]) -> PatternStatistics:
        """Calculate statistical significance metrics."""
        sample_size = len(trades)
        minimum_sample_size = 30
        
        # Calculate confidence interval for win rate
        if sample_size > 0:
            win_count = len([t for t in trades if t.performance.actual_outcome == "win"])
            win_rate = win_count / sample_size
            
            # Calculate 95% confidence interval for proportion
            if sample_size >= 5:  # Minimum for normal approximation
                z_score = 1.96  # 95% confidence
                margin_error = z_score * ((win_rate * (1 - win_rate)) / sample_size) ** 0.5
                confidence_interval = Decimal(str(margin_error))
            else:
                confidence_interval = Decimal("0.5")  # Very wide interval for small samples
        else:
            confidence_interval = Decimal("1.0")
        
        # Simple p-value calculation (comparing to random 50% win rate)
        if sample_size >= 5:
            # Simplified binomial test approximation
            expected_wins = sample_size * 0.5
            actual_wins = len([t for t in trades if t.performance.actual_outcome == "win"])
            
            # Very simplified p-value estimation
            z_stat = abs(actual_wins - expected_wins) / (sample_size * 0.25) ** 0.5
            p_value = max(Decimal("0.01"), Decimal("1.0") - Decimal(str(min(z_stat / 2, 0.49))))
        else:
            p_value = Decimal("1.0")  # Not significant with small sample
        
        statistically_significant = (sample_size >= minimum_sample_size and 
                                   p_value < Decimal("0.05"))
        
        return PatternStatistics(
            sample_size=sample_size,
            confidence_interval=confidence_interval,
            p_value=p_value,
            statistically_significant=statistically_significant,
            minimum_sample_size=minimum_sample_size
        )
    
    def _create_empty_pattern_performance(self, pattern_id: str) -> PatternPerformance:
        """Create empty pattern performance structure."""
        empty_metrics = self.success_calculator._create_empty_metrics()
        
        return PatternPerformance(
            pattern_id=pattern_id,
            pattern_name="Unknown_Pattern",
            success_rates={"overall": empty_metrics},
            evolution=PatternEvolution(
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                total_occurrences=0,
                recent_trend="stable",
                adaptation_required=False
            ),
            statistics=PatternStatistics(
                sample_size=0,
                confidence_interval=Decimal("1.0"),
                p_value=Decimal("1.0"),
                statistically_significant=False,
                minimum_sample_size=30
            )
        )