"""
Performance analysis data models.

Defines dataclasses for storing performance metrics across different
dimensions: trading sessions, pattern types, and confidence buckets.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional


@dataclass
class SessionMetrics:
    """
    Performance metrics for a specific trading session.

    Tracks wins, losses, win rate, risk-reward ratio, profit factor,
    and total P&L for a trading session (Tokyo, London, NY, Sydney, Overlap).
    """

    session: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    avg_rr: Decimal
    profit_factor: Decimal
    total_pnl: Decimal

    def __post_init__(self):
        """Validate Decimal types for monetary/percentage fields."""
        if not isinstance(self.win_rate, Decimal):
            self.win_rate = Decimal(str(self.win_rate))
        if not isinstance(self.avg_rr, Decimal):
            self.avg_rr = Decimal(str(self.avg_rr))
        if not isinstance(self.profit_factor, Decimal):
            self.profit_factor = Decimal(str(self.profit_factor))
        if not isinstance(self.total_pnl, Decimal):
            self.total_pnl = Decimal(str(self.total_pnl))


@dataclass
class PatternMetrics:
    """
    Performance metrics for a specific pattern type.

    Tracks wins, losses, win rate, and risk-reward ratio for
    pattern types (Spring, Upthrust, Accumulation, Distribution).
    """

    pattern_type: str
    sample_size: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    avg_rr: Decimal

    def __post_init__(self):
        """Validate Decimal types for monetary/percentage fields."""
        if not isinstance(self.win_rate, Decimal):
            self.win_rate = Decimal(str(self.win_rate))
        if not isinstance(self.avg_rr, Decimal):
            self.avg_rr = Decimal(str(self.avg_rr))


@dataclass
class ConfidenceMetrics:
    """
    Performance metrics for a specific confidence bucket.

    Tracks sample size, win rate, and risk-reward ratio for
    confidence buckets (50-60%, 60-70%, 70-80%, 80-90%, 90-100%).
    """

    bucket: str
    sample_size: int
    win_rate: Decimal
    avg_rr: Decimal

    def __post_init__(self):
        """Validate Decimal types for monetary/percentage fields."""
        if not isinstance(self.win_rate, Decimal):
            self.win_rate = Decimal(str(self.win_rate))
        if not isinstance(self.avg_rr, Decimal):
            self.avg_rr = Decimal(str(self.avg_rr))


@dataclass
class PerformanceAnalysis:
    """
    Comprehensive performance analysis result.

    Aggregates performance metrics across all dimensions: sessions,
    patterns, and confidence buckets. Includes analysis metadata and
    identification of best/worst performing dimensions.
    """

    session_metrics: Dict[str, SessionMetrics]
    pattern_metrics: Dict[str, PatternMetrics]
    confidence_metrics: Dict[str, ConfidenceMetrics]
    analysis_timestamp: datetime
    trade_count: int
    best_session: Optional[str] = None
    worst_session: Optional[str] = None

    def summary(self) -> str:
        """
        Generate human-readable summary of analysis results.

        Returns:
            str: Formatted summary string with key findings
        """
        lines = [
            f"Performance Analysis Summary (as of {self.analysis_timestamp.isoformat()})",
            f"Total Trades Analyzed: {self.trade_count}",
            "",
            "Session Performance:"
        ]

        for session, metrics in self.session_metrics.items():
            lines.append(
                f"  {session}: {metrics.total_trades} trades, "
                f"{metrics.win_rate:.1f}% win rate, "
                f"{metrics.avg_rr:.2f} avg R:R, "
                f"${metrics.total_pnl:.2f} P&L"
            )

        if self.best_session:
            lines.append(f"\nBest Performing Session: {self.best_session}")
        if self.worst_session:
            lines.append(f"Worst Performing Session: {self.worst_session}")

        lines.append("\nPattern Performance:")
        for pattern, metrics in self.pattern_metrics.items():
            lines.append(
                f"  {pattern}: {metrics.sample_size} trades, "
                f"{metrics.win_rate:.1f}% win rate, "
                f"{metrics.avg_rr:.2f} avg R:R"
            )

        lines.append("\nConfidence Bucket Performance:")
        for bucket, metrics in self.confidence_metrics.items():
            lines.append(
                f"  {bucket}: {metrics.sample_size} trades, "
                f"{metrics.win_rate:.1f}% win rate, "
                f"{metrics.avg_rr:.2f} avg R:R"
            )

        return "\n".join(lines)
