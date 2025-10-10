"""
Performance analyzer for autonomous learning loop.

Analyzes trade performance across multiple dimensions: trading sessions,
pattern types, and confidence buckets. Includes statistical significance
checks and identification of best/worst performers.
"""

import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from .models.performance_models import (
    SessionMetrics,
    PatternMetrics,
    ConfidenceMetrics,
    PerformanceAnalysis
)


class PerformanceAnalyzer:
    """
    Analyzes trade performance across multiple dimensions.

    Provides comprehensive performance analysis calculating win rates,
    risk-reward ratios, profit factors, and other metrics grouped by
    trading session, pattern type, and confidence score bucket.
    """

    def __init__(self, min_trades_for_significance: Optional[int] = None):
        """
        Initialize performance analyzer.

        Args:
            min_trades_for_significance: Minimum sample size for statistical
                significance (default: 20, or LEARNING_MIN_TRADES env var)
        """
        if min_trades_for_significance is None:
            min_trades_for_significance = int(
                os.getenv("LEARNING_MIN_TRADES", "20")
            )
        self.min_trades_for_significance = min_trades_for_significance

    def analyze_performance(self, trades: List) -> PerformanceAnalysis:
        """
        Perform comprehensive performance analysis across all dimensions.

        Args:
            trades: List of Trade ORM objects from database

        Returns:
            PerformanceAnalysis: Aggregated analysis results
        """
        # Analyze each dimension
        session_metrics = self.analyze_by_session(trades)
        pattern_metrics = self.analyze_by_pattern(trades)
        confidence_metrics = self.analyze_by_confidence(trades)

        # Identify best and worst performing sessions
        best_session = self.identify_best_performer(session_metrics)
        worst_session = self.identify_worst_performer(session_metrics)

        return PerformanceAnalysis(
            session_metrics=session_metrics,
            pattern_metrics=pattern_metrics,
            confidence_metrics=confidence_metrics,
            analysis_timestamp=datetime.now(),
            trade_count=len(trades),
            best_session=best_session,
            worst_session=worst_session
        )

    def analyze_by_session(self, trades: List) -> Dict[str, SessionMetrics]:
        """
        Analyze performance grouped by trading session.

        Args:
            trades: List of Trade ORM objects

        Returns:
            Dict[str, SessionMetrics]: Metrics per session (TOKYO, LONDON, NY, SYDNEY, OVERLAP)
        """
        # Group trades by session
        session_groups = {}
        for trade in trades:
            if trade.session:
                session = trade.session.upper()
                if session not in session_groups:
                    session_groups[session] = []
                session_groups[session].append(trade)

        # Calculate metrics for each session
        session_metrics = {}
        for session, session_trades in session_groups.items():
            metrics = self._calculate_session_metrics(session, session_trades)
            session_metrics[session] = metrics

        return session_metrics

    def analyze_by_pattern(self, trades: List) -> Dict[str, PatternMetrics]:
        """
        Analyze performance grouped by pattern type.

        Args:
            trades: List of Trade ORM objects

        Returns:
            Dict[str, PatternMetrics]: Metrics per pattern (Spring, Upthrust, Accumulation, Distribution)
        """
        # Group trades by pattern
        pattern_groups = {}
        for trade in trades:
            if trade.pattern_type:
                pattern = trade.pattern_type
                if pattern not in pattern_groups:
                    pattern_groups[pattern] = []
                pattern_groups[pattern].append(trade)

        # Calculate metrics for each pattern
        pattern_metrics = {}
        for pattern, pattern_trades in pattern_groups.items():
            metrics = self._calculate_pattern_metrics(pattern, pattern_trades)
            pattern_metrics[pattern] = metrics

        return pattern_metrics

    def analyze_by_confidence(self, trades: List) -> Dict[str, ConfidenceMetrics]:
        """
        Analyze performance grouped by confidence score buckets.

        Args:
            trades: List of Trade ORM objects

        Returns:
            Dict[str, ConfidenceMetrics]: Metrics per confidence bucket
                (50-60%, 60-70%, 70-80%, 80-90%, 90-100%)
        """
        # Define confidence buckets
        buckets = {
            "50-60%": (50, 60),
            "60-70%": (60, 70),
            "70-80%": (70, 80),
            "80-90%": (80, 90),
            "90-100%": (90, 100)
        }

        # Group trades by confidence bucket
        bucket_groups = {bucket: [] for bucket in buckets.keys()}
        for trade in trades:
            if trade.confidence_score:
                confidence = float(trade.confidence_score)
                for bucket_name, (min_conf, max_conf) in buckets.items():
                    if min_conf <= confidence < max_conf or (
                        bucket_name == "90-100%" and confidence == 100
                    ):
                        bucket_groups[bucket_name].append(trade)
                        break

        # Calculate metrics for each bucket
        confidence_metrics = {}
        for bucket, bucket_trades in bucket_groups.items():
            if bucket_trades:  # Only include buckets with trades
                metrics = self._calculate_confidence_metrics(bucket, bucket_trades)
                confidence_metrics[bucket] = metrics

        return confidence_metrics

    def check_statistical_significance(self, sample_size: int) -> bool:
        """
        Check if sample size meets statistical significance threshold.

        Args:
            sample_size: Number of trades in sample

        Returns:
            bool: True if sample_size >= min_trades_for_significance
        """
        return sample_size >= self.min_trades_for_significance

    def identify_best_performer(self, session_metrics: Dict[str, SessionMetrics]) -> Optional[str]:
        """
        Identify best performing session based on win rate.

        Args:
            session_metrics: Session metrics dictionary

        Returns:
            Optional[str]: Session name with highest win rate (if statistically significant)
        """
        best_session = None
        best_win_rate = Decimal("-1")

        for session, metrics in session_metrics.items():
            if (
                self.check_statistical_significance(metrics.total_trades)
                and metrics.win_rate > best_win_rate
            ):
                best_win_rate = metrics.win_rate
                best_session = session

        return best_session

    def identify_worst_performer(self, session_metrics: Dict[str, SessionMetrics]) -> Optional[str]:
        """
        Identify worst performing session based on win rate.

        Args:
            session_metrics: Session metrics dictionary

        Returns:
            Optional[str]: Session name with lowest win rate (if statistically significant)
        """
        worst_session = None
        worst_win_rate = Decimal("999999")

        for session, metrics in session_metrics.items():
            if (
                self.check_statistical_significance(metrics.total_trades)
                and metrics.win_rate < worst_win_rate
            ):
                worst_win_rate = metrics.win_rate
                worst_session = session

        return worst_session

    def _calculate_session_metrics(self, session: str, trades: List) -> SessionMetrics:
        """
        Calculate comprehensive metrics for a session.

        Args:
            session: Session name
            trades: List of trades for this session

        Returns:
            SessionMetrics: Calculated metrics
        """
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl and t.pnl <= 0)

        # Calculate win rate
        win_rate = (
            Decimal(winning_trades) / Decimal(total_trades) * Decimal(100)
            if total_trades > 0
            else Decimal(0)
        )

        # Calculate average risk-reward ratio
        rr_values = [float(t.risk_reward_ratio) for t in trades if t.risk_reward_ratio]
        avg_rr = (
            Decimal(sum(rr_values) / len(rr_values))
            if rr_values
            else Decimal(0)
        )

        # Calculate profit factor
        winning_pnl = sum(float(t.pnl) for t in trades if t.pnl and t.pnl > 0)
        losing_pnl = sum(float(t.pnl) for t in trades if t.pnl and t.pnl <= 0)
        profit_factor = (
            Decimal(winning_pnl) / abs(Decimal(losing_pnl))
            if losing_pnl != 0
            else Decimal(0)
        )

        # Calculate total P&L
        total_pnl = sum(float(t.pnl) for t in trades if t.pnl)

        return SessionMetrics(
            session=session,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_rr=avg_rr,
            profit_factor=profit_factor,
            total_pnl=Decimal(total_pnl)
        )

    def _calculate_pattern_metrics(self, pattern: str, trades: List) -> PatternMetrics:
        """
        Calculate metrics for a pattern type.

        Args:
            pattern: Pattern type name
            trades: List of trades for this pattern

        Returns:
            PatternMetrics: Calculated metrics
        """
        sample_size = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl and t.pnl <= 0)

        # Calculate win rate
        win_rate = (
            Decimal(winning_trades) / Decimal(sample_size) * Decimal(100)
            if sample_size > 0
            else Decimal(0)
        )

        # Calculate average risk-reward ratio
        rr_values = [float(t.risk_reward_ratio) for t in trades if t.risk_reward_ratio]
        avg_rr = (
            Decimal(sum(rr_values) / len(rr_values))
            if rr_values
            else Decimal(0)
        )

        return PatternMetrics(
            pattern_type=pattern,
            sample_size=sample_size,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_rr=avg_rr
        )

    def _calculate_confidence_metrics(self, bucket: str, trades: List) -> ConfidenceMetrics:
        """
        Calculate metrics for a confidence bucket.

        Args:
            bucket: Confidence bucket name (e.g., "70-80%")
            trades: List of trades in this bucket

        Returns:
            ConfidenceMetrics: Calculated metrics
        """
        sample_size = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)

        # Calculate win rate
        win_rate = (
            Decimal(winning_trades) / Decimal(sample_size) * Decimal(100)
            if sample_size > 0
            else Decimal(0)
        )

        # Calculate average risk-reward ratio
        rr_values = [float(t.risk_reward_ratio) for t in trades if t.risk_reward_ratio]
        avg_rr = (
            Decimal(sum(rr_values) / len(rr_values))
            if rr_values
            else Decimal(0)
        )

        return ConfidenceMetrics(
            bucket=bucket,
            sample_size=sample_size,
            win_rate=win_rate,
            avg_rr=avg_rr
        )
