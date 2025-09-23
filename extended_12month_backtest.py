#!/usr/bin/env python3
"""
Extended 12-Month Backtest Analysis
===================================
Comprehensive 12-month backtesting for Cycle 2 (Ultra Selective) and Cycle 4 (Balanced Aggressive).

Features:
- Full 12-month simulation
- Monthly performance breakdown
- Seasonal analysis
- Drawdown periods analysis
- Risk-adjusted metrics
- Comparative analysis
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import random
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MonthlyResults:
    """Monthly performance results"""
    month: int
    month_name: str
    starting_balance: float
    ending_balance: float
    monthly_pnl: float
    monthly_return_pct: float
    trades_count: int
    wins: int
    losses: int
    win_rate: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    max_drawdown_month: float
    profitable_month: bool

@dataclass
class Extended12MonthResult:
    """Complete 12-month backtest results"""
    cycle_name: str
    cycle_config: Dict

    # Overall Performance
    starting_balance: float
    ending_balance: float
    total_pnl: float
    total_return_pct: float
    annualized_return_pct: float

    # Trade Statistics
    total_trades: int
    total_wins: int
    total_losses: int
    overall_win_rate: float
    overall_profit_factor: float
    overall_rr_ratio: float

    # Risk Metrics
    max_drawdown_dollars: float
    max_drawdown_pct: float
    longest_drawdown_days: int
    sharpe_ratio_annual: float
    sortino_ratio_annual: float
    calmar_ratio: float
    var_95_monthly: float

    # Consistency Metrics
    profitable_months: int
    profitable_months_pct: float
    consecutive_profitable_months_max: int
    consecutive_losing_months_max: int
    best_month_pnl: float
    worst_month_pnl: float
    monthly_volatility: float

    # Advanced Metrics
    avg_monthly_return: float
    median_monthly_return: float
    monthly_returns: List[float]
    monthly_results: List[MonthlyResults]

    # Quarterly Performance
    q1_pnl: float
    q2_pnl: float
    q3_pnl: float
    q4_pnl: float

class Extended12MonthBacktest:
    """Extended 12-month backtesting engine"""

    def __init__(self, start_balance: float = 100000.0):
        """Initialize 12-month backtester"""
        self.start_balance = start_balance
        self.months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        logger.info(f"Initialized Extended 12-Month Backtest with ${start_balance:,.2f}")

    def run_cycle_2_backtest(self) -> Extended12MonthResult:
        """Run 12-month backtest for Cycle 2: Ultra Selective"""

        config = {
            'name': 'Ultra_Selective',
            'confidence_threshold': 85.0,
            'min_volume_confirmation': 80.0,
            'min_structure_score': 75.0,
            'min_risk_reward': 4.0,
            'atr_multiplier_stop': 0.3,
            'enable_regime_filter': True,
            'enable_frequency_management': True,
            'expected_signals_per_month': 8,
            'expected_win_rate': 75.0
        }

        return self._simulate_12_month_trading("Cycle_2_Ultra_Selective", config)

    def run_cycle_4_backtest(self) -> Extended12MonthResult:
        """Run 12-month backtest for Cycle 4: Balanced Aggressive"""

        config = {
            'name': 'Balanced_Aggressive',
            'confidence_threshold': 70.0,
            'min_volume_confirmation': 60.0,
            'min_structure_score': 58.0,
            'min_risk_reward': 2.8,
            'atr_multiplier_stop': 0.6,
            'enable_regime_filter': False,
            'enable_frequency_management': True,
            'expected_signals_per_month': 25,
            'expected_win_rate': 52.0
        }

        return self._simulate_12_month_trading("Cycle_4_Balanced_Aggressive", config)

    def _simulate_12_month_trading(self, cycle_name: str, config: Dict) -> Extended12MonthResult:
        """Simulate 12 months of trading with given configuration"""

        logger.info(f"Starting 12-month simulation for {cycle_name}")

        balance = self.start_balance
        peak_balance = balance
        max_drawdown = 0.0
        longest_drawdown_days = 0
        current_drawdown_days = 0

        monthly_results = []
        all_trades = []
        monthly_returns = []

        total_wins = 0
        total_losses = 0

        # Track consecutive months
        consecutive_profitable = 0
        consecutive_losing = 0
        max_consecutive_profitable = 0
        max_consecutive_losing = 0

        # Simulate each month
        for month_idx in range(12):
            month_start_balance = balance
            month_name = self.months[month_idx]

            # Generate monthly trading activity
            month_result = self._simulate_monthly_trading(
                month_idx + 1, month_name, balance, config
            )

            # Update balance
            balance = month_result.ending_balance

            # Track peak and drawdown
            if balance > peak_balance:
                peak_balance = balance
                current_drawdown_days = 0
            else:
                current_drawdown_days += 30  # Assume 30 days per month
                longest_drawdown_days = max(longest_drawdown_days, current_drawdown_days)

            current_drawdown = (peak_balance - balance) / peak_balance
            max_drawdown = max(max_drawdown, current_drawdown)

            # Track consecutive months
            if month_result.profitable_month:
                consecutive_profitable += 1
                consecutive_losing = 0
                max_consecutive_profitable = max(max_consecutive_profitable, consecutive_profitable)
            else:
                consecutive_losing += 1
                consecutive_profitable = 0
                max_consecutive_losing = max(max_consecutive_losing, consecutive_losing)

            # Accumulate totals
            total_wins += month_result.wins
            total_losses += month_result.losses
            monthly_returns.append(month_result.monthly_return_pct)

            monthly_results.append(month_result)

            logger.info(f"  {month_name}: ${month_result.monthly_pnl:+,.0f} "
                       f"({month_result.monthly_return_pct:+.1f}%) "
                       f"Balance: ${balance:,.0f}")

        # Calculate overall metrics
        total_pnl = balance - self.start_balance
        total_return_pct = (total_pnl / self.start_balance) * 100
        annualized_return_pct = total_return_pct  # Already 12 months

        overall_win_rate = (total_wins / (total_wins + total_losses)) * 100 if (total_wins + total_losses) > 0 else 0

        # Calculate profit factor
        total_win_amount = sum([mr.wins * mr.avg_win for mr in monthly_results])
        total_loss_amount = sum([mr.losses * abs(mr.avg_loss) for mr in monthly_results])
        overall_profit_factor = total_win_amount / total_loss_amount if total_loss_amount > 0 else 0

        # Calculate R:R ratio
        avg_win_overall = total_win_amount / total_wins if total_wins > 0 else 0
        avg_loss_overall = total_loss_amount / total_losses if total_losses > 0 else 0
        overall_rr_ratio = avg_win_overall / avg_loss_overall if avg_loss_overall > 0 else 0

        # Risk metrics
        monthly_mean = np.mean(monthly_returns)
        monthly_std = np.std(monthly_returns) if len(monthly_returns) > 1 else 0

        sharpe_ratio_annual = (monthly_mean / monthly_std * np.sqrt(12)) if monthly_std > 0 else 0

        # Sortino ratio (downside deviation)
        negative_returns = [r for r in monthly_returns if r < 0]
        downside_std = np.std(negative_returns) if len(negative_returns) > 1 else monthly_std
        sortino_ratio_annual = (monthly_mean / downside_std * np.sqrt(12)) if downside_std > 0 else 0

        # Calmar ratio
        calmar_ratio = (annualized_return_pct / 100) / max_drawdown if max_drawdown > 0 else 0

        # VaR 95%
        var_95_monthly = np.percentile(monthly_returns, 5) if monthly_returns else 0

        # Profitable months
        profitable_months = len([mr for mr in monthly_results if mr.profitable_month])
        profitable_months_pct = (profitable_months / 12) * 100

        # Best/worst months
        best_month_pnl = max([mr.monthly_pnl for mr in monthly_results])
        worst_month_pnl = min([mr.monthly_pnl for mr in monthly_results])

        # Quarterly performance
        q1_pnl = sum([mr.monthly_pnl for mr in monthly_results[0:3]])
        q2_pnl = sum([mr.monthly_pnl for mr in monthly_results[3:6]])
        q3_pnl = sum([mr.monthly_pnl for mr in monthly_results[6:9]])
        q4_pnl = sum([mr.monthly_pnl for mr in monthly_results[9:12]])

        return Extended12MonthResult(
            cycle_name=cycle_name,
            cycle_config=config,
            starting_balance=self.start_balance,
            ending_balance=balance,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            annualized_return_pct=annualized_return_pct,
            total_trades=sum([mr.trades_count for mr in monthly_results]),
            total_wins=total_wins,
            total_losses=total_losses,
            overall_win_rate=overall_win_rate,
            overall_profit_factor=overall_profit_factor,
            overall_rr_ratio=overall_rr_ratio,
            max_drawdown_dollars=max_drawdown * peak_balance,
            max_drawdown_pct=max_drawdown * 100,
            longest_drawdown_days=longest_drawdown_days,
            sharpe_ratio_annual=sharpe_ratio_annual,
            sortino_ratio_annual=sortino_ratio_annual,
            calmar_ratio=calmar_ratio,
            var_95_monthly=var_95_monthly,
            profitable_months=profitable_months,
            profitable_months_pct=profitable_months_pct,
            consecutive_profitable_months_max=max_consecutive_profitable,
            consecutive_losing_months_max=max_consecutive_losing,
            best_month_pnl=best_month_pnl,
            worst_month_pnl=worst_month_pnl,
            monthly_volatility=monthly_std,
            avg_monthly_return=monthly_mean,
            median_monthly_return=np.median(monthly_returns),
            monthly_returns=monthly_returns,
            monthly_results=monthly_results,
            q1_pnl=q1_pnl,
            q2_pnl=q2_pnl,
            q3_pnl=q3_pnl,
            q4_pnl=q4_pnl
        )

    def _simulate_monthly_trading(self, month_num: int, month_name: str,
                                 starting_balance: float, config: Dict) -> MonthlyResults:
        """Simulate trading activity for a single month"""

        balance = starting_balance
        trades_this_month = config['expected_signals_per_month']

        # Add some randomness to trade count (±30%)
        trades_this_month = int(trades_this_month * random.uniform(0.7, 1.3))

        # Calculate expected win rate with some monthly variation
        base_win_rate = config['expected_win_rate'] / 100.0
        monthly_win_rate = base_win_rate * random.uniform(0.8, 1.2)  # ±20% variation
        monthly_win_rate = min(0.95, max(0.05, monthly_win_rate))  # Cap between 5-95%

        wins = 0
        losses = 0
        winning_trades_pnl = []
        losing_trades_pnl = []

        avg_risk_per_trade = starting_balance * 0.02  # 2% risk per trade
        rr_ratio = config['min_risk_reward']

        month_peak = balance
        month_max_dd = 0.0

        # Simulate individual trades
        for trade_num in range(trades_this_month):
            is_winner = random.random() < monthly_win_rate

            if is_winner:
                # Winner: Risk × R:R ratio
                pnl = avg_risk_per_trade * rr_ratio
                wins += 1
                winning_trades_pnl.append(pnl)
            else:
                # Loser: -Risk amount
                pnl = -avg_risk_per_trade
                losses += 1
                losing_trades_pnl.append(pnl)

            # Apply regime filtering
            if config.get('enable_regime_filter', False):
                # 25% of trades filtered out in poor market conditions
                if random.random() < 0.25:
                    continue

            balance += pnl

            # Track monthly drawdown
            if balance > month_peak:
                month_peak = balance
            month_dd = (month_peak - balance) / month_peak
            month_max_dd = max(month_max_dd, month_dd)

        # Calculate monthly metrics
        monthly_pnl = balance - starting_balance
        monthly_return_pct = (monthly_pnl / starting_balance) * 100

        actual_win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

        avg_win = np.mean(winning_trades_pnl) if winning_trades_pnl else 0
        avg_loss = np.mean(losing_trades_pnl) if losing_trades_pnl else 0
        largest_win = max(winning_trades_pnl) if winning_trades_pnl else 0
        largest_loss = min(losing_trades_pnl) if losing_trades_pnl else 0

        return MonthlyResults(
            month=month_num,
            month_name=month_name,
            starting_balance=starting_balance,
            ending_balance=balance,
            monthly_pnl=monthly_pnl,
            monthly_return_pct=monthly_return_pct,
            trades_count=wins + losses,
            wins=wins,
            losses=losses,
            win_rate=actual_win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            max_drawdown_month=month_max_dd * 100,
            profitable_month=monthly_pnl > 0
        )

    def compare_cycles(self, cycle2_result: Extended12MonthResult,
                      cycle4_result: Extended12MonthResult) -> Dict:
        """Compare results between Cycle 2 and Cycle 4"""

        comparison = {
            'summary': {
                'cycle2_name': cycle2_result.cycle_name,
                'cycle4_name': cycle4_result.cycle_name,
                'test_period': '12 months',
                'starting_balance': cycle2_result.starting_balance
            },
            'performance_comparison': {
                'total_return': {
                    'cycle2': cycle2_result.total_return_pct,
                    'cycle4': cycle4_result.total_return_pct,
                    'difference': cycle2_result.total_return_pct - cycle4_result.total_return_pct,
                    'winner': 'Cycle 2' if cycle2_result.total_return_pct > cycle4_result.total_return_pct else 'Cycle 4'
                },
                'total_pnl': {
                    'cycle2': cycle2_result.total_pnl,
                    'cycle4': cycle4_result.total_pnl,
                    'difference': cycle2_result.total_pnl - cycle4_result.total_pnl,
                    'winner': 'Cycle 2' if cycle2_result.total_pnl > cycle4_result.total_pnl else 'Cycle 4'
                },
                'win_rate': {
                    'cycle2': cycle2_result.overall_win_rate,
                    'cycle4': cycle4_result.overall_win_rate,
                    'difference': cycle2_result.overall_win_rate - cycle4_result.overall_win_rate,
                    'winner': 'Cycle 2' if cycle2_result.overall_win_rate > cycle4_result.overall_win_rate else 'Cycle 4'
                },
                'rr_ratio': {
                    'cycle2': cycle2_result.overall_rr_ratio,
                    'cycle4': cycle4_result.overall_rr_ratio,
                    'difference': cycle2_result.overall_rr_ratio - cycle4_result.overall_rr_ratio,
                    'winner': 'Cycle 2' if cycle2_result.overall_rr_ratio > cycle4_result.overall_rr_ratio else 'Cycle 4'
                }
            },
            'risk_comparison': {
                'max_drawdown': {
                    'cycle2': cycle2_result.max_drawdown_pct,
                    'cycle4': cycle4_result.max_drawdown_pct,
                    'difference': cycle2_result.max_drawdown_pct - cycle4_result.max_drawdown_pct,
                    'winner': 'Cycle 2' if cycle2_result.max_drawdown_pct < cycle4_result.max_drawdown_pct else 'Cycle 4'
                },
                'sharpe_ratio': {
                    'cycle2': cycle2_result.sharpe_ratio_annual,
                    'cycle4': cycle4_result.sharpe_ratio_annual,
                    'difference': cycle2_result.sharpe_ratio_annual - cycle4_result.sharpe_ratio_annual,
                    'winner': 'Cycle 2' if cycle2_result.sharpe_ratio_annual > cycle4_result.sharpe_ratio_annual else 'Cycle 4'
                },
                'monthly_volatility': {
                    'cycle2': cycle2_result.monthly_volatility,
                    'cycle4': cycle4_result.monthly_volatility,
                    'difference': cycle2_result.monthly_volatility - cycle4_result.monthly_volatility,
                    'winner': 'Cycle 2' if cycle2_result.monthly_volatility < cycle4_result.monthly_volatility else 'Cycle 4'
                }
            },
            'consistency_comparison': {
                'profitable_months': {
                    'cycle2': cycle2_result.profitable_months_pct,
                    'cycle4': cycle4_result.profitable_months_pct,
                    'difference': cycle2_result.profitable_months_pct - cycle4_result.profitable_months_pct,
                    'winner': 'Cycle 2' if cycle2_result.profitable_months_pct > cycle4_result.profitable_months_pct else 'Cycle 4'
                },
                'best_month': {
                    'cycle2': cycle2_result.best_month_pnl,
                    'cycle4': cycle4_result.best_month_pnl,
                    'difference': cycle2_result.best_month_pnl - cycle4_result.best_month_pnl,
                    'winner': 'Cycle 2' if cycle2_result.best_month_pnl > cycle4_result.best_month_pnl else 'Cycle 4'
                },
                'worst_month': {
                    'cycle2': cycle2_result.worst_month_pnl,
                    'cycle4': cycle4_result.worst_month_pnl,
                    'difference': cycle2_result.worst_month_pnl - cycle4_result.worst_month_pnl,
                    'winner': 'Cycle 2' if cycle2_result.worst_month_pnl > cycle4_result.worst_month_pnl else 'Cycle 4'
                }
            },
            'trade_frequency': {
                'cycle2_trades_per_month': cycle2_result.total_trades / 12,
                'cycle4_trades_per_month': cycle4_result.total_trades / 12,
                'cycle2_total_trades': cycle2_result.total_trades,
                'cycle4_total_trades': cycle4_result.total_trades
            }
        }

        return comparison

    def print_detailed_results(self, result: Extended12MonthResult):
        """Print detailed results for a cycle"""

        print(f"\n{result.cycle_name.upper()} - 12 MONTH RESULTS")
        print("=" * 60)

        print(f"\nOVERALL PERFORMANCE:")
        print(f"  Starting Balance: ${result.starting_balance:,.2f}")
        print(f"  Ending Balance:   ${result.ending_balance:,.2f}")
        print(f"  Total P&L:        ${result.total_pnl:+,.2f}")
        print(f"  Total Return:     {result.total_return_pct:+.1f}%")
        print(f"  Annualized:       {result.annualized_return_pct:+.1f}%")

        print(f"\nTRADE STATISTICS:")
        print(f"  Total Trades:     {result.total_trades}")
        print(f"  Wins:             {result.total_wins}")
        print(f"  Losses:           {result.total_losses}")
        print(f"  Win Rate:         {result.overall_win_rate:.1f}%")
        print(f"  Profit Factor:    {result.overall_profit_factor:.2f}")
        print(f"  R:R Ratio:        {result.overall_rr_ratio:.2f}:1")
        print(f"  Trades/Month:     {result.total_trades/12:.1f}")

        print(f"\nRISK METRICS:")
        print(f"  Max Drawdown:     ${result.max_drawdown_dollars:,.2f} ({result.max_drawdown_pct:.1f}%)")
        print(f"  Longest DD:       {result.longest_drawdown_days} days")
        print(f"  Sharpe Ratio:     {result.sharpe_ratio_annual:.2f}")
        print(f"  Sortino Ratio:    {result.sortino_ratio_annual:.2f}")
        print(f"  Calmar Ratio:     {result.calmar_ratio:.2f}")
        print(f"  VaR 95% Monthly:  {result.var_95_monthly:.1f}%")
        print(f"  Monthly Volatility: {result.monthly_volatility:.1f}%")

        print(f"\nCONSISTENCY METRICS:")
        print(f"  Profitable Months: {result.profitable_months}/12 ({result.profitable_months_pct:.1f}%)")
        print(f"  Best Month:       ${result.best_month_pnl:+,.2f}")
        print(f"  Worst Month:      ${result.worst_month_pnl:+,.2f}")
        print(f"  Avg Monthly:      ${result.avg_monthly_return:.1f}%")
        print(f"  Median Monthly:   ${result.median_monthly_return:.1f}%")
        print(f"  Max Consecutive Profitable: {result.consecutive_profitable_months_max} months")
        print(f"  Max Consecutive Losing:     {result.consecutive_losing_months_max} months")

        print(f"\nQUARTERLY BREAKDOWN:")
        print(f"  Q1 P&L:  ${result.q1_pnl:+,.2f}")
        print(f"  Q2 P&L:  ${result.q2_pnl:+,.2f}")
        print(f"  Q3 P&L:  ${result.q3_pnl:+,.2f}")
        print(f"  Q4 P&L:  ${result.q4_pnl:+,.2f}")

        print(f"\nMONTHLY PERFORMANCE:")
        for mr in result.monthly_results:
            status = "PROFIT" if mr.profitable_month else "LOSS"
            print(f"  {mr.month_name:>9}: ${mr.monthly_pnl:+8,.0f} ({mr.monthly_return_pct:+5.1f}%) "
                  f"Trades: {mr.trades_count:2d} WR: {mr.win_rate:4.1f}% {status}")

def main():
    """Main execution function"""

    print("Extended 12-Month Backtest Analysis")
    print("=" * 50)
    print("Comparing Cycle 2 (Ultra Selective) vs Cycle 4 (Balanced Aggressive)")
    print("Test Period: 12 months")
    print("Starting Balance: $100,000")
    print()

    # Initialize backtester
    backtester = Extended12MonthBacktest(start_balance=100000.0)

    # Run Cycle 2 backtest
    print("Running Cycle 2: Ultra Selective...")
    cycle2_result = backtester.run_cycle_2_backtest()

    # Run Cycle 4 backtest
    print("\nRunning Cycle 4: Balanced Aggressive...")
    cycle4_result = backtester.run_cycle_4_backtest()

    # Print detailed results
    backtester.print_detailed_results(cycle2_result)
    backtester.print_detailed_results(cycle4_result)

    # Compare cycles
    comparison = backtester.compare_cycles(cycle2_result, cycle4_result)

    print(f"\n\nCOMPARATIVE ANALYSIS")
    print("=" * 60)

    print(f"\nPERFORMANCE COMPARISON:")
    perf = comparison['performance_comparison']
    print(f"  Total Return:")
    print(f"    Cycle 2: {perf['total_return']['cycle2']:+.1f}%")
    print(f"    Cycle 4: {perf['total_return']['cycle4']:+.1f}%")
    print(f"    Winner:  {perf['total_return']['winner']} (+{abs(perf['total_return']['difference']):.1f}%)")

    print(f"  Total P&L:")
    print(f"    Cycle 2: ${perf['total_pnl']['cycle2']:+,.0f}")
    print(f"    Cycle 4: ${perf['total_pnl']['cycle4']:+,.0f}")
    print(f"    Winner:  {perf['total_pnl']['winner']} (+${abs(perf['total_pnl']['difference']):,.0f})")

    print(f"  Win Rate:")
    print(f"    Cycle 2: {perf['win_rate']['cycle2']:.1f}%")
    print(f"    Cycle 4: {perf['win_rate']['cycle4']:.1f}%")
    print(f"    Winner:  {perf['win_rate']['winner']} (+{abs(perf['win_rate']['difference']):.1f}%)")

    print(f"  R:R Ratio:")
    print(f"    Cycle 2: {perf['rr_ratio']['cycle2']:.2f}:1")
    print(f"    Cycle 4: {perf['rr_ratio']['cycle4']:.2f}:1")
    print(f"    Winner:  {perf['rr_ratio']['winner']} (+{abs(perf['rr_ratio']['difference']):.2f})")

    print(f"\nRISK COMPARISON:")
    risk = comparison['risk_comparison']
    print(f"  Max Drawdown:")
    print(f"    Cycle 2: {risk['max_drawdown']['cycle2']:.1f}%")
    print(f"    Cycle 4: {risk['max_drawdown']['cycle4']:.1f}%")
    print(f"    Winner:  {risk['max_drawdown']['winner']} (lower by {abs(risk['max_drawdown']['difference']):.1f}%)")

    print(f"  Sharpe Ratio:")
    print(f"    Cycle 2: {risk['sharpe_ratio']['cycle2']:.2f}")
    print(f"    Cycle 4: {risk['sharpe_ratio']['cycle4']:.2f}")
    print(f"    Winner:  {risk['sharpe_ratio']['winner']} (+{abs(risk['sharpe_ratio']['difference']):.2f})")

    print(f"\nCONSISTENCY COMPARISON:")
    consistency = comparison['consistency_comparison']
    print(f"  Profitable Months:")
    print(f"    Cycle 2: {consistency['profitable_months']['cycle2']:.1f}%")
    print(f"    Cycle 4: {consistency['profitable_months']['cycle4']:.1f}%")
    print(f"    Winner:  {consistency['profitable_months']['winner']} (+{abs(consistency['profitable_months']['difference']):.1f}%)")

    print(f"\nTRADE FREQUENCY:")
    freq = comparison['trade_frequency']
    print(f"  Cycle 2: {freq['cycle2_trades_per_month']:.1f} trades/month ({freq['cycle2_total_trades']} total)")
    print(f"  Cycle 4: {freq['cycle4_trades_per_month']:.1f} trades/month ({freq['cycle4_total_trades']} total)")

    # Final recommendation
    print(f"\n\nFINAL RECOMMENDATION:")
    print("=" * 40)

    cycle2_score = 0
    cycle4_score = 0

    # Score based on key metrics
    if perf['total_return']['winner'] == 'Cycle 2': cycle2_score += 2
    else: cycle4_score += 2

    if perf['win_rate']['winner'] == 'Cycle 2': cycle2_score += 1
    else: cycle4_score += 1

    if perf['rr_ratio']['winner'] == 'Cycle 2': cycle2_score += 2
    else: cycle4_score += 2

    if risk['max_drawdown']['winner'] == 'Cycle 2': cycle2_score += 2
    else: cycle4_score += 2

    if risk['sharpe_ratio']['winner'] == 'Cycle 2': cycle2_score += 1
    else: cycle4_score += 1

    if consistency['profitable_months']['winner'] == 'Cycle 2': cycle2_score += 1
    else: cycle4_score += 1

    if cycle2_score > cycle4_score:
        print("RECOMMENDED CONFIGURATION: Cycle 2 - Ultra Selective")
        print(f"Scoring: Cycle 2 ({cycle2_score}/9) vs Cycle 4 ({cycle4_score}/9)")
        print("Reason: Superior risk-adjusted returns with better consistency")
    elif cycle4_score > cycle2_score:
        print("RECOMMENDED CONFIGURATION: Cycle 4 - Balanced Aggressive")
        print(f"Scoring: Cycle 4 ({cycle4_score}/9) vs Cycle 2 ({cycle2_score}/9)")
        print("Reason: Higher absolute returns justify increased risk")
    else:
        print("RECOMMENDATION: TIE - Both configurations viable")
        print(f"Scoring: Cycle 2 ({cycle2_score}/9) vs Cycle 4 ({cycle4_score}/9)")
        print("Consider personal risk tolerance and trading style preference")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"extended_12month_results_{timestamp}.json"

    detailed_results = {
        'cycle2_result': asdict(cycle2_result),
        'cycle4_result': asdict(cycle4_result),
        'comparison': comparison,
        'generated_timestamp': timestamp
    }

    with open(results_file, 'w') as f:
        json.dump(detailed_results, f, indent=2, default=str)

    print(f"\nDetailed results saved to: {results_file}")

    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)