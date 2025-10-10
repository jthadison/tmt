"""
Performance Calculator for Trading Analytics

Provides comprehensive analytics calculations including:
- Session-based performance (win rates by trading session)
- Pattern-based performance (win rates by pattern type)
- P&L by currency pair
- Confidence score correlation analysis
- Drawdown calculations and equity curve
- Parameter evolution tracking
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any
from statistics import correlation, mean, stdev

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Trade, ParameterHistory

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """
    Calculate comprehensive performance analytics from trade history.

    Provides methods for calculating win rates, P&L breakdowns, correlation
    analysis, drawdown metrics, and parameter evolution tracking.
    """

    def __init__(self, session_factory):
        """
        Initialize performance calculator.

        Args:
            session_factory: Async session factory for database operations
        """
        self.session_factory = session_factory

    async def calculate_session_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate win rates and performance metrics by trading session.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict mapping session names to performance metrics:
            {
                "TOKYO": {
                    "win_rate": 72.5,
                    "total_trades": 40,
                    "winning_trades": 29,
                    "losing_trades": 11
                },
                ...
            }
        """
        try:
            async with self.session_factory() as session:
                # Build query with filters
                conditions = [Trade.exit_time.isnot(None)]  # Only closed trades

                if start_date:
                    conditions.append(Trade.entry_time >= start_date)
                if end_date:
                    conditions.append(Trade.entry_time <= end_date)

                # Query for session performance
                stmt = (
                    select(
                        Trade.session,
                        func.count(Trade.id).label('total_trades'),
                        func.sum(func.case((Trade.pnl > 0, 1), else_=0)).label('winning_trades'),
                        func.sum(func.case((Trade.pnl <= 0, 1), else_=0)).label('losing_trades')
                    )
                    .where(and_(*conditions))
                    .group_by(Trade.session)
                )

                result = await session.execute(stmt)
                rows = result.all()

                # Calculate win rates
                performance = {}
                sessions = ['TOKYO', 'LONDON', 'NY', 'SYDNEY', 'OVERLAP']

                # Initialize all sessions with zero values
                for sess in sessions:
                    performance[sess] = {
                        "win_rate": 0.0,
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0
                    }

                # Update with actual data
                for row in rows:
                    if row.session and row.total_trades > 0:
                        win_rate = (row.winning_trades / row.total_trades) * 100
                        performance[row.session] = {
                            "win_rate": round(float(win_rate), 2),
                            "total_trades": int(row.total_trades),
                            "winning_trades": int(row.winning_trades or 0),
                            "losing_trades": int(row.losing_trades or 0)
                        }

                logger.info(f"Calculated session performance for {len(performance)} sessions")
                return performance

        except Exception as e:
            logger.error(f"❌ Failed to calculate session performance: {e}")
            raise

    async def calculate_pattern_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate win rates and sample sizes by pattern type.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict mapping pattern types to performance metrics:
            {
                "Spring": {
                    "win_rate": 75.5,
                    "sample_size": 42,
                    "significant": True
                },
                ...
            }
        """
        try:
            async with self.session_factory() as session:
                # Build query with filters
                conditions = [
                    Trade.exit_time.isnot(None),
                    Trade.pattern_type.isnot(None)
                ]

                if start_date:
                    conditions.append(Trade.entry_time >= start_date)
                if end_date:
                    conditions.append(Trade.entry_time <= end_date)

                # Query for pattern performance
                stmt = (
                    select(
                        Trade.pattern_type,
                        func.count(Trade.id).label('sample_size'),
                        func.sum(func.case((Trade.pnl > 0, 1), else_=0)).label('winning_trades')
                    )
                    .where(and_(*conditions))
                    .group_by(Trade.pattern_type)
                )

                result = await session.execute(stmt)
                rows = result.all()

                # Calculate win rates with significance
                performance = {}
                pattern_types = ['Spring', 'Upthrust', 'Accumulation', 'Distribution']

                # Initialize all patterns
                for pattern in pattern_types:
                    performance[pattern] = {
                        "win_rate": 0.0,
                        "sample_size": 0,
                        "significant": False
                    }

                # Update with actual data
                for row in rows:
                    if row.pattern_type and row.sample_size > 0:
                        win_rate = (row.winning_trades / row.sample_size) * 100
                        significant = row.sample_size >= 20  # Statistical significance threshold

                        performance[row.pattern_type] = {
                            "win_rate": round(float(win_rate), 2),
                            "sample_size": int(row.sample_size),
                            "significant": significant
                        }

                logger.info(f"Calculated pattern performance for {len(performance)} patterns")
                return performance

        except Exception as e:
            logger.error(f"❌ Failed to calculate pattern performance: {e}")
            raise

    async def calculate_pnl_by_pair(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate total P&L by currency pair.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict mapping symbols to P&L metrics:
            {
                "EUR_USD": {
                    "total_pnl": 1234.56,
                    "trade_count": 42,
                    "avg_pnl": 29.39
                },
                ...
            }
        """
        try:
            async with self.session_factory() as session:
                # Build query with filters
                conditions = [Trade.exit_time.isnot(None)]

                if start_date:
                    conditions.append(Trade.entry_time >= start_date)
                if end_date:
                    conditions.append(Trade.entry_time <= end_date)

                # Query for P&L by symbol
                stmt = (
                    select(
                        Trade.symbol,
                        func.sum(Trade.pnl).label('total_pnl'),
                        func.count(Trade.id).label('trade_count')
                    )
                    .where(and_(*conditions))
                    .group_by(Trade.symbol)
                )

                result = await session.execute(stmt)
                rows = result.all()

                # Calculate P&L metrics
                pnl_data = {}
                symbols = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CHF']

                # Initialize all symbols
                for symbol in symbols:
                    pnl_data[symbol] = {
                        "total_pnl": 0.0,
                        "trade_count": 0,
                        "avg_pnl": 0.0
                    }

                # Update with actual data
                for row in rows:
                    if row.symbol:
                        total_pnl = float(row.total_pnl or 0)
                        trade_count = int(row.trade_count)
                        avg_pnl = total_pnl / trade_count if trade_count > 0 else 0.0

                        pnl_data[row.symbol] = {
                            "total_pnl": round(total_pnl, 2),
                            "trade_count": trade_count,
                            "avg_pnl": round(avg_pnl, 2)
                        }

                logger.info(f"Calculated P&L for {len(pnl_data)} currency pairs")
                return pnl_data

        except Exception as e:
            logger.error(f"❌ Failed to calculate P&L by pair: {e}")
            raise

    async def calculate_confidence_correlation(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate correlation between confidence scores and trade outcomes.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with scatter plot data and correlation coefficient:
            {
                "scatter_data": [
                    {"confidence": 75.5, "outcome": 1, "symbol": "EUR_USD"},
                    ...
                ],
                "correlation_coefficient": 0.73
            }
        """
        try:
            async with self.session_factory() as session:
                # Build query with filters
                conditions = [
                    Trade.exit_time.isnot(None),
                    Trade.confidence_score.isnot(None)
                ]

                if start_date:
                    conditions.append(Trade.entry_time >= start_date)
                if end_date:
                    conditions.append(Trade.entry_time <= end_date)

                # Query for confidence and outcomes
                stmt = (
                    select(
                        Trade.confidence_score,
                        Trade.pnl,
                        Trade.symbol
                    )
                    .where(and_(*conditions))
                    .order_by(Trade.entry_time)
                )

                result = await session.execute(stmt)
                rows = result.all()

                # Build scatter data and calculate correlation
                scatter_data = []
                confidence_scores = []
                outcomes = []

                for row in rows:
                    confidence = float(row.confidence_score)
                    outcome = 1 if row.pnl > 0 else 0

                    scatter_data.append({
                        "confidence": round(confidence, 2),
                        "outcome": outcome,
                        "symbol": row.symbol
                    })

                    confidence_scores.append(confidence)
                    outcomes.append(outcome)

                # Calculate Pearson correlation coefficient
                correlation_coefficient = 0.0
                if len(confidence_scores) >= 2:
                    try:
                        # Calculate correlation manually to avoid issues
                        if stdev(confidence_scores) > 0 and stdev(outcomes) > 0:
                            correlation_coefficient = correlation(confidence_scores, outcomes)
                    except Exception as corr_error:
                        logger.warning(f"Could not calculate correlation: {corr_error}")

                logger.info(f"Calculated confidence correlation for {len(scatter_data)} trades")
                return {
                    "scatter_data": scatter_data,
                    "correlation_coefficient": round(correlation_coefficient, 3)
                }

        except Exception as e:
            logger.error(f"❌ Failed to calculate confidence correlation: {e}")
            raise

    async def calculate_drawdown_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate equity curve and drawdown metrics.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with equity curve and drawdown information:
            {
                "equity_curve": [
                    {"time": "2025-01-01T12:00:00Z", "equity": 100500.00},
                    ...
                ],
                "drawdown_periods": [
                    {
                        "start": "2025-01-05T10:00:00Z",
                        "end": "2025-01-08T15:00:00Z",
                        "amount": -2345.67,
                        "percentage": -2.34
                    },
                    ...
                ],
                "max_drawdown": {
                    "amount": -2345.67,
                    "percentage": -2.34,
                    "start": "2025-01-05T10:00:00Z",
                    "end": "2025-01-08T15:00:00Z",
                    "recovery_duration_days": 3
                }
            }
        """
        try:
            async with self.session_factory() as session:
                # Build query with filters
                conditions = [Trade.exit_time.isnot(None)]

                if start_date:
                    conditions.append(Trade.entry_time >= start_date)
                if end_date:
                    conditions.append(Trade.entry_time <= end_date)

                # Query trades ordered by time
                stmt = (
                    select(Trade)
                    .where(and_(*conditions))
                    .order_by(Trade.exit_time)
                )

                result = await session.execute(stmt)
                trades = result.scalars().all()

                # Calculate running equity curve
                starting_equity = 100000.0  # Assuming $100k starting balance
                equity_curve = []
                cumulative_pnl = 0.0

                for trade in trades:
                    cumulative_pnl += float(trade.pnl or 0)
                    current_equity = starting_equity + cumulative_pnl

                    equity_curve.append({
                        "time": trade.exit_time.isoformat(),
                        "equity": round(current_equity, 2)
                    })

                # Calculate drawdown periods
                drawdown_periods = []
                max_drawdown = {
                    "amount": 0.0,
                    "percentage": 0.0,
                    "start": None,
                    "end": None,
                    "recovery_duration_days": 0
                }

                if equity_curve:
                    peak_equity = starting_equity
                    drawdown_start = None

                    for point in equity_curve:
                        current_equity = point["equity"]

                        # Track peak
                        if current_equity > peak_equity:
                            # End of drawdown period
                            if drawdown_start:
                                drawdown_periods.append({
                                    "start": drawdown_start,
                                    "end": point["time"],
                                    "amount": round(current_equity - peak_equity, 2),
                                    "percentage": round(((current_equity - peak_equity) / peak_equity) * 100, 2)
                                })
                                drawdown_start = None

                            peak_equity = current_equity

                        # Track drawdown
                        elif current_equity < peak_equity:
                            if not drawdown_start:
                                drawdown_start = point["time"]

                            drawdown_amount = current_equity - peak_equity
                            drawdown_pct = (drawdown_amount / peak_equity) * 100

                            # Check if this is max drawdown
                            if drawdown_amount < max_drawdown["amount"]:
                                max_drawdown = {
                                    "amount": round(drawdown_amount, 2),
                                    "percentage": round(drawdown_pct, 2),
                                    "start": drawdown_start,
                                    "end": point["time"],
                                    "recovery_duration_days": 0  # Will calculate if recovered
                                }

                logger.info(f"Calculated drawdown data with {len(equity_curve)} equity points")
                return {
                    "equity_curve": equity_curve,
                    "drawdown_periods": drawdown_periods,
                    "max_drawdown": max_drawdown
                }

        except Exception as e:
            logger.error(f"❌ Failed to calculate drawdown data: {e}")
            raise

    async def get_parameter_evolution(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get parameter change history over time.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of parameter changes:
            [
                {
                    "change_time": "2025-01-10T14:30:00Z",
                    "parameter_mode": "Session-Targeted",
                    "session": "LONDON",
                    "confidence_threshold": 72.0,
                    "min_risk_reward": 3.2,
                    "reason": "Optimized for London session volatility",
                    "changed_by": "learning_agent"
                },
                ...
            ]
        """
        try:
            async with self.session_factory() as session:
                # Build query with filters
                conditions = []

                if start_date:
                    conditions.append(ParameterHistory.change_time >= start_date)
                if end_date:
                    conditions.append(ParameterHistory.change_time <= end_date)

                # Query parameter history
                if conditions:
                    stmt = (
                        select(ParameterHistory)
                        .where(and_(*conditions))
                        .order_by(desc(ParameterHistory.change_time))
                    )
                else:
                    stmt = (
                        select(ParameterHistory)
                        .order_by(desc(ParameterHistory.change_time))
                    )

                result = await session.execute(stmt)
                changes = result.scalars().all()

                # Format parameter changes
                evolution = []
                for change in changes:
                    evolution.append({
                        "change_time": change.change_time.isoformat(),
                        "parameter_mode": change.parameter_mode,
                        "session": change.session,
                        "confidence_threshold": float(change.confidence_threshold) if change.confidence_threshold else None,
                        "min_risk_reward": float(change.min_risk_reward) if change.min_risk_reward else None,
                        "reason": change.reason,
                        "changed_by": change.changed_by
                    })

                logger.info(f"Retrieved {len(evolution)} parameter changes")
                return evolution

        except Exception as e:
            logger.error(f"❌ Failed to get parameter evolution: {e}")
            raise
