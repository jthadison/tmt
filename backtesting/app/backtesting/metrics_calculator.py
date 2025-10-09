"""
Performance Metrics Calculator - Story 11.2

Calculates comprehensive performance metrics including:
- Sharpe ratio, Sortino ratio, Calmar ratio
- Maximum drawdown, CAGR, total return
- Win rate, profit factor, expectancy
- Per-instrument and per-session breakdowns
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .models import (
    Trade, EquityPoint, SessionMetrics, InstrumentMetrics,
    BacktestResult, BacktestConfig, TradingSession
)

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculate comprehensive backtest performance metrics

    Implements industry-standard metrics with proper annualization
    and risk-adjusted returns.
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize metrics calculator

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe/Sortino (default 2%)
        """

        self.risk_free_rate = risk_free_rate
        logger.info(f"MetricsCalculator initialized with risk_free_rate={risk_free_rate}")

    def calculate_all_metrics(
        self,
        trades: List[Trade],
        equity_curve: List[EquityPoint],
        config: BacktestConfig,
        execution_time: float,
        bars_processed: int
    ) -> BacktestResult:
        """
        Calculate all performance metrics

        Args:
            trades: List of all trades
            equity_curve: Equity curve data
            config: Backtest configuration
            execution_time: Backtest execution time in seconds
            bars_processed: Number of bars processed

        Returns:
            Complete BacktestResult with all metrics
        """

        logger.info(f"Calculating metrics for {len(trades)} trades")

        # Calculate overall performance metrics
        sharpe = self.calculate_sharpe_ratio(equity_curve)
        sortino = self.calculate_sortino_ratio(equity_curve)
        max_dd, max_dd_pct = self.calculate_maximum_drawdown(equity_curve, config.initial_capital)
        total_return, total_return_pct = self.calculate_total_return(
            equity_curve, config.initial_capital
        )
        cagr = self.calculate_cagr(
            config.initial_capital,
            equity_curve[-1].balance if equity_curve else config.initial_capital,
            config.start_date,
            config.end_date
        )
        calmar = self.calculate_calmar_ratio(cagr, max_dd)

        # Calculate trade statistics
        win_rate = self.calculate_win_rate(trades)
        profit_factor = self.calculate_profit_factor(trades)
        recovery_factor = self.calculate_recovery_factor(trades, max_dd)
        avg_rr = self.calculate_avg_risk_reward(trades)
        expectancy, expectancy_pct = self.calculate_expectancy(trades)

        # Count trade outcomes
        winning_trades = sum(1 for t in trades if t.realized_pnl and t.realized_pnl > 0)
        losing_trades = sum(1 for t in trades if t.realized_pnl and t.realized_pnl < 0)

        # Calculate breakdowns
        session_performance = self.calculate_session_breakdown(trades)
        instrument_performance = self.calculate_instrument_breakdown(trades)

        result = BacktestResult(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            total_return=total_return,
            total_return_pct=total_return_pct,
            cagr=cagr,
            calmar_ratio=calmar,
            win_rate=win_rate,
            profit_factor=profit_factor,
            recovery_factor=recovery_factor,
            total_trades=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_risk_reward=avg_rr,
            expectancy=expectancy,
            expectancy_pct=expectancy_pct,
            trades=trades,
            equity_curve=equity_curve,
            session_performance=session_performance,
            instrument_performance=instrument_performance,
            config=config,
            execution_time_seconds=execution_time,
            bars_processed=bars_processed
        )

        logger.info(
            f"Metrics calculated: Sharpe={sharpe:.2f}, Win Rate={win_rate:.1%}, "
            f"CAGR={cagr:.1%}, Max DD={max_dd_pct:.1%}"
        )

        return result

    def calculate_sharpe_ratio(self, equity_curve: List[EquityPoint]) -> float:
        """
        Calculate annualized Sharpe ratio

        Formula: (mean_return - risk_free_rate) / std_return * sqrt(periods_per_year)

        Args:
            equity_curve: Equity curve data points

        Returns:
            Annualized Sharpe ratio
        """

        if len(equity_curve) < 2:
            return 0.0

        # Calculate returns
        returns = self._calculate_returns(equity_curve)

        if len(returns) == 0:
            return 0.0

        # Calculate statistics
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        if std_return == 0:
            return 0.0

        # Annualize (assuming daily returns)
        periods_per_year = 252  # Trading days per year
        annualized_return = mean_return * periods_per_year
        annualized_std = std_return * np.sqrt(periods_per_year)

        # Sharpe ratio
        sharpe = (annualized_return - self.risk_free_rate) / annualized_std

        return round(sharpe, 2)

    def calculate_sortino_ratio(self, equity_curve: List[EquityPoint]) -> float:
        """
        Calculate annualized Sortino ratio

        Like Sharpe but only penalizes downside volatility.

        Formula: (mean_return - risk_free_rate) / downside_std * sqrt(periods_per_year)

        Args:
            equity_curve: Equity curve data points

        Returns:
            Annualized Sortino ratio
        """

        if len(equity_curve) < 2:
            return 0.0

        # Calculate returns
        returns = self._calculate_returns(equity_curve)

        if len(returns) == 0:
            return 0.0

        # Calculate downside deviation (only negative returns)
        downside_returns = [r for r in returns if r < 0]

        if len(downside_returns) == 0:
            return 0.0  # No downside = undefined Sortino

        mean_return = np.mean(returns)
        downside_std = np.std(downside_returns, ddof=1)

        if downside_std == 0:
            return 0.0

        # Annualize
        periods_per_year = 252
        annualized_return = mean_return * periods_per_year
        annualized_downside_std = downside_std * np.sqrt(periods_per_year)

        # Sortino ratio
        sortino = (annualized_return - self.risk_free_rate) / annualized_downside_std

        return round(sortino, 2)

    def calculate_maximum_drawdown(
        self,
        equity_curve: List[EquityPoint],
        initial_capital: float
    ) -> Tuple[float, float]:
        """
        Calculate maximum drawdown

        Args:
            equity_curve: Equity curve data points
            initial_capital: Starting capital

        Returns:
            Tuple of (max_drawdown_dollars, max_drawdown_pct)
        """

        if not equity_curve:
            return 0.0, 0.0

        # Get balance values
        balances = [initial_capital] + [ep.balance for ep in equity_curve]

        # Calculate running maximum
        running_max = np.maximum.accumulate(balances)

        # Calculate drawdowns
        drawdowns = balances - running_max

        # Maximum drawdown (most negative value)
        max_dd_dollars = np.min(drawdowns)

        # Find the peak before max drawdown
        max_dd_index = np.argmin(drawdowns)
        peak_before_dd = running_max[max_dd_index]

        if peak_before_dd > 0:
            max_dd_pct = (max_dd_dollars / peak_before_dd) * 100
        else:
            max_dd_pct = 0.0

        return round(max_dd_dollars, 2), round(max_dd_pct, 2)

    def calculate_total_return(
        self,
        equity_curve: List[EquityPoint],
        initial_capital: float
    ) -> Tuple[float, float]:
        """
        Calculate total return

        Args:
            equity_curve: Equity curve data points
            initial_capital: Starting capital

        Returns:
            Tuple of (total_return_decimal, total_return_pct)
        """

        if not equity_curve:
            return 0.0, 0.0

        final_balance = equity_curve[-1].balance
        total_return = final_balance - initial_capital
        total_return_pct = (total_return / initial_capital) * 100

        return round(total_return, 2), round(total_return_pct, 2)

    def calculate_cagr(
        self,
        initial_capital: float,
        final_balance: float,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """
        Calculate Compound Annual Growth Rate

        Formula: (final/initial)^(1/years) - 1

        Args:
            initial_capital: Starting capital
            final_balance: Ending balance
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            CAGR as decimal (0.21 = 21% annual growth)
        """

        # Calculate years
        days = (end_date - start_date).days
        years = days / 365.25

        if years <= 0 or initial_capital <= 0:
            return 0.0

        # CAGR formula
        cagr = (final_balance / initial_capital) ** (1 / years) - 1

        return round(cagr, 4)

    def calculate_calmar_ratio(self, cagr: float, max_drawdown: float) -> float:
        """
        Calculate Calmar ratio

        Formula: CAGR / abs(max_drawdown)

        Higher is better (return per unit of drawdown risk)

        Args:
            cagr: Compound annual growth rate
            max_drawdown: Maximum drawdown (negative)

        Returns:
            Calmar ratio
        """

        if max_drawdown == 0:
            return 0.0

        calmar = cagr / abs(max_drawdown)
        return round(calmar, 2)

    def calculate_win_rate(self, trades: List[Trade]) -> float:
        """
        Calculate win rate

        Args:
            trades: List of trades

        Returns:
            Win rate as decimal (0.58 = 58%)
        """

        if not trades:
            return 0.0

        closed_trades = [t for t in trades if t.realized_pnl is not None]

        if not closed_trades:
            return 0.0

        winners = sum(1 for t in closed_trades if t.realized_pnl > 0)
        win_rate = winners / len(closed_trades)

        return round(win_rate, 3)

    def calculate_profit_factor(self, trades: List[Trade]) -> float:
        """
        Calculate profit factor

        Formula: Gross profit / Gross loss

        Args:
            trades: List of trades

        Returns:
            Profit factor (>1 = profitable)
        """

        if not trades:
            return 0.0

        closed_trades = [t for t in trades if t.realized_pnl is not None]

        if not closed_trades:
            return 0.0

        gross_profit = sum(t.realized_pnl for t in closed_trades if t.realized_pnl > 0)
        gross_loss = abs(sum(t.realized_pnl for t in closed_trades if t.realized_pnl < 0))

        if gross_loss == 0:
            return 0.0 if gross_profit == 0 else 999.0  # All winners

        profit_factor = gross_profit / gross_loss
        return round(profit_factor, 2)

    def calculate_recovery_factor(self, trades: List[Trade], max_drawdown: float) -> float:
        """
        Calculate recovery factor

        Formula: Net profit / abs(max_drawdown)

        Args:
            trades: List of trades
            max_drawdown: Maximum drawdown (negative)

        Returns:
            Recovery factor
        """

        if not trades or max_drawdown == 0:
            return 0.0

        net_profit = sum(t.realized_pnl for t in trades if t.realized_pnl is not None)
        recovery_factor = net_profit / abs(max_drawdown)

        return round(recovery_factor, 2)

    def calculate_avg_risk_reward(self, trades: List[Trade]) -> float:
        """
        Calculate average risk-reward achieved

        Args:
            trades: List of trades

        Returns:
            Average R:R ratio
        """

        if not trades:
            return 0.0

        rr_ratios = [
            t.risk_reward_achieved for t in trades
            if t.risk_reward_achieved is not None
        ]

        if not rr_ratios:
            return 0.0

        avg_rr = np.mean(rr_ratios)
        return round(avg_rr, 2)

    def calculate_expectancy(self, trades: List[Trade]) -> Tuple[float, float]:
        """
        Calculate expectancy (average profit per trade)

        Args:
            trades: List of trades

        Returns:
            Tuple of (expectancy_dollars, expectancy_as_pct_of_risk)
        """

        if not trades:
            return 0.0, 0.0

        closed_trades = [t for t in trades if t.realized_pnl is not None]

        if not closed_trades:
            return 0.0, 0.0

        # Expectancy in dollars
        expectancy_dollars = np.mean([t.realized_pnl for t in closed_trades])

        # Expectancy as % of risk
        avg_risk = np.mean([t.risk_amount for t in closed_trades])
        expectancy_pct = (expectancy_dollars / avg_risk) if avg_risk > 0 else 0.0

        return round(expectancy_dollars, 2), round(expectancy_pct, 3)

    def calculate_session_breakdown(self, trades: List[Trade]) -> Dict[str, SessionMetrics]:
        """
        Calculate performance breakdown by trading session

        Args:
            trades: List of trades

        Returns:
            Dict mapping session name to SessionMetrics
        """

        session_breakdown = {}

        # Group trades by session
        for session in TradingSession:
            session_trades = [t for t in trades if t.trading_session == session]

            if not session_trades:
                continue

            # Calculate metrics for this session
            closed_trades = [t for t in session_trades if t.realized_pnl is not None]

            if not closed_trades:
                continue

            winners = sum(1 for t in closed_trades if t.realized_pnl > 0)
            losers = sum(1 for t in closed_trades if t.realized_pnl < 0)
            win_rate = winners / len(closed_trades) if closed_trades else 0.0

            gross_profit = sum(t.realized_pnl for t in closed_trades if t.realized_pnl > 0)
            gross_loss = abs(sum(t.realized_pnl for t in closed_trades if t.realized_pnl < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

            total_pnl = sum(t.realized_pnl for t in closed_trades)

            avg_rr = np.mean([
                t.risk_reward_achieved for t in closed_trades
                if t.risk_reward_achieved is not None
            ]) if closed_trades else 0.0

            session_breakdown[session.value] = SessionMetrics(
                session=session,
                total_trades=len(closed_trades),
                winning_trades=winners,
                losing_trades=losers,
                win_rate=round(win_rate, 3),
                avg_risk_reward=round(avg_rr, 2),
                total_pnl=round(total_pnl, 2),
                profit_factor=round(profit_factor, 2),
                max_drawdown=0.0,  # TODO: Calculate session-specific drawdown
                sharpe_ratio=0.0   # TODO: Calculate session-specific Sharpe
            )

        return session_breakdown

    def calculate_instrument_breakdown(self, trades: List[Trade]) -> Dict[str, InstrumentMetrics]:
        """
        Calculate performance breakdown by instrument

        Args:
            trades: List of trades

        Returns:
            Dict mapping instrument to InstrumentMetrics
        """

        instrument_breakdown = {}

        # Get unique instruments
        instruments = set(t.symbol for t in trades)

        for instrument in instruments:
            inst_trades = [t for t in trades if t.symbol == instrument]
            closed_trades = [t for t in inst_trades if t.realized_pnl is not None]

            if not closed_trades:
                continue

            winners = sum(1 for t in closed_trades if t.realized_pnl > 0)
            losers = sum(1 for t in closed_trades if t.realized_pnl < 0)
            win_rate = winners / len(closed_trades)

            gross_profit = sum(t.realized_pnl for t in closed_trades if t.realized_pnl > 0)
            gross_loss = abs(sum(t.realized_pnl for t in closed_trades if t.realized_pnl < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

            total_pnl = sum(t.realized_pnl for t in closed_trades)
            total_pnl_pips = sum(
                t.realized_pnl_pips for t in closed_trades
                if t.realized_pnl_pips is not None
            )

            avg_rr = np.mean([
                t.risk_reward_achieved for t in closed_trades
                if t.risk_reward_achieved is not None
            ])

            # Calculate max consecutive losses
            max_consec_losses = self._calculate_max_consecutive_losses(closed_trades)

            # Calculate average trade duration
            avg_duration = self._calculate_avg_trade_duration(closed_trades)

            instrument_breakdown[instrument] = InstrumentMetrics(
                instrument=instrument,
                total_trades=len(closed_trades),
                winning_trades=winners,
                losing_trades=losers,
                win_rate=round(win_rate, 3),
                avg_risk_reward=round(avg_rr, 2),
                total_pnl=round(total_pnl, 2),
                total_pnl_pips=round(total_pnl_pips, 1),
                profit_factor=round(profit_factor, 2),
                max_consecutive_losses=max_consec_losses,
                avg_trade_duration_hours=round(avg_duration, 1)
            )

        return instrument_breakdown

    def _calculate_returns(self, equity_curve: List[EquityPoint]) -> List[float]:
        """Calculate period returns from equity curve"""

        if len(equity_curve) < 2:
            return []

        balances = [ep.balance for ep in equity_curve]
        returns = []

        for i in range(1, len(balances)):
            if balances[i-1] > 0:
                ret = (balances[i] - balances[i-1]) / balances[i-1]
                returns.append(ret)

        return returns

    def _calculate_max_consecutive_losses(self, trades: List[Trade]) -> int:
        """Calculate maximum consecutive losing trades"""

        if not trades:
            return 0

        max_consec = 0
        current_consec = 0

        for trade in trades:
            if trade.realized_pnl is not None and trade.realized_pnl < 0:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0

        return max_consec

    def _calculate_avg_trade_duration(self, trades: List[Trade]) -> float:
        """Calculate average trade duration in hours"""

        if not trades:
            return 0.0

        durations = []

        for trade in trades:
            if trade.exit_time:
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 3600
                durations.append(duration)

        if not durations:
            return 0.0

        return np.mean(durations)
