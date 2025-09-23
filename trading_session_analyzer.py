#!/usr/bin/env python3
"""
Trading Session Analysis System
===============================
Comprehensive analysis of trading performance by global forex sessions.

Features:
- Session-aware backtesting with realistic timestamps
- Performance analysis by London, New York, Tokyo, Sydney sessions
- Session overlap analysis (London-NY, Tokyo-London)
- Risk analysis by time of day
- Optimal trading hours identification
- Currency pair session preferences
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, time
import pytz
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingSession(Enum):
    """Global forex trading sessions"""
    SYDNEY = "Sydney"
    TOKYO = "Tokyo"
    LONDON = "London"
    NEW_YORK = "New_York"
    LONDON_NY_OVERLAP = "London_NY_Overlap"
    TOKYO_LONDON_OVERLAP = "Tokyo_London_Overlap"
    QUIET_PERIOD = "Quiet_Period"

@dataclass
class SessionTimeframe:
    """Time boundaries for trading sessions (GMT)"""
    name: str
    start_hour: int
    end_hour: int
    peak_hours: Tuple[int, int]
    volatility_multiplier: float
    liquidity_score: float
    typical_spreads: Dict[str, float]

@dataclass
class SessionTrade:
    """Individual trade with session information"""
    trade_id: int
    timestamp: datetime
    session: TradingSession
    session_overlap: Optional[TradingSession]
    currency_pair: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pips: float
    pnl_dollars: float
    win: bool
    trade_duration_hours: float
    confidence_score: float
    risk_reward_ratio: float
    session_volatility: float
    mae_pips: float
    mfe_pips: float

@dataclass
class SessionPerformance:
    """Performance metrics for a trading session"""
    session: TradingSession
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl_dollars: float
    total_pnl_pips: float
    avg_win_dollars: float
    avg_loss_dollars: float
    avg_win_pips: float
    avg_loss_pips: float
    largest_win_dollars: float
    largest_loss_dollars: float
    profit_factor: float
    avg_risk_reward: float
    avg_trade_duration: float

    # Risk metrics
    max_drawdown_dollars: float
    max_drawdown_pips: float
    consecutive_wins_max: int
    consecutive_losses_max: int

    # Advanced metrics
    sharpe_ratio: float
    hit_rate_by_hour: Dict[int, float]
    avg_mae_pips: float
    avg_mfe_pips: float
    volatility_score: float

    # Session characteristics
    peak_performance_hours: List[int]
    avoid_hours: List[int]
    currency_pair_performance: Dict[str, float]

class SessionAnalyzer:
    """Comprehensive trading session analysis engine"""

    def __init__(self):
        """Initialize session analyzer with GMT-based session definitions"""

        # Define trading sessions (all times in GMT)
        self.session_definitions = {
            TradingSession.SYDNEY: SessionTimeframe(
                name="Sydney",
                start_hour=22, end_hour=7,  # 22:00-07:00 GMT
                peak_hours=(23, 2),
                volatility_multiplier=0.7,
                liquidity_score=0.3,
                typical_spreads={"EUR_USD": 1.2, "GBP_USD": 1.8, "USD_JPY": 1.0}
            ),
            TradingSession.TOKYO: SessionTimeframe(
                name="Tokyo",
                start_hour=0, end_hour=9,   # 00:00-09:00 GMT
                peak_hours=(1, 4),
                volatility_multiplier=0.8,
                liquidity_score=0.6,
                typical_spreads={"EUR_USD": 1.0, "GBP_USD": 1.5, "USD_JPY": 0.7}
            ),
            TradingSession.LONDON: SessionTimeframe(
                name="London",
                start_hour=8, end_hour=17,  # 08:00-17:00 GMT
                peak_hours=(9, 12),
                volatility_multiplier=1.2,
                liquidity_score=0.9,
                typical_spreads={"EUR_USD": 0.7, "GBP_USD": 1.0, "USD_JPY": 0.8}
            ),
            TradingSession.NEW_YORK: SessionTimeframe(
                name="New_York",
                start_hour=13, end_hour=22, # 13:00-22:00 GMT
                peak_hours=(14, 18),
                volatility_multiplier=1.4,
                liquidity_score=1.0,
                typical_spreads={"EUR_USD": 0.6, "GBP_USD": 0.9, "USD_JPY": 0.7}
            )
        }

        # Define session overlaps
        self.overlap_definitions = {
            TradingSession.TOKYO_LONDON_OVERLAP: (8, 9),    # 08:00-09:00 GMT
            TradingSession.LONDON_NY_OVERLAP: (13, 17)      # 13:00-17:00 GMT
        }

        logger.info("Session Analyzer initialized with GMT-based definitions")

    def determine_trading_session(self, timestamp: datetime) -> Tuple[TradingSession, Optional[TradingSession]]:
        """
        Determine which trading session(s) a timestamp falls into.

        Returns:
            Tuple of (primary_session, overlap_session)
        """

        # Convert to GMT if needed
        if timestamp.tzinfo is None:
            gmt_time = timestamp
        else:
            gmt_time = timestamp.astimezone(pytz.UTC)

        hour = gmt_time.hour

        # Check for overlaps first (higher priority)
        tokyo_london_start, tokyo_london_end = self.overlap_definitions[TradingSession.TOKYO_LONDON_OVERLAP]
        london_ny_start, london_ny_end = self.overlap_definitions[TradingSession.LONDON_NY_OVERLAP]

        if tokyo_london_start <= hour < tokyo_london_end:
            return TradingSession.LONDON, TradingSession.TOKYO_LONDON_OVERLAP
        elif london_ny_start <= hour < london_ny_end:
            return TradingSession.LONDON, TradingSession.LONDON_NY_OVERLAP

        # Check individual sessions
        for session, definition in self.session_definitions.items():
            start, end = definition.start_hour, definition.end_hour

            # Handle overnight sessions (like Sydney: 22:00-07:00)
            if start > end:
                if hour >= start or hour < end:
                    return session, None
            else:
                if start <= hour < end:
                    return session, None

        # If no session matches, it's a quiet period
        return TradingSession.QUIET_PERIOD, None

    def generate_realistic_timestamp(self, base_date: datetime, session_preference: Optional[TradingSession] = None) -> datetime:
        """
        Generate realistic trading timestamp based on session preferences and volatility patterns.
        """

        # If no preference, weight towards high-activity sessions
        if session_preference is None:
            session_weights = {
                TradingSession.LONDON: 0.35,
                TradingSession.NEW_YORK: 0.30,
                TradingSession.TOKYO: 0.20,
                TradingSession.SYDNEY: 0.10,
                TradingSession.LONDON_NY_OVERLAP: 0.05  # Special high-activity period
            }
            session_preference = np.random.choice(
                list(session_weights.keys()),
                p=list(session_weights.values())
            )

        # Generate hour within preferred session
        if session_preference == TradingSession.LONDON_NY_OVERLAP:
            hour = random.randint(13, 16)  # Peak overlap time
        elif session_preference in self.session_definitions:
            definition = self.session_definitions[session_preference]
            start, end = definition.start_hour, definition.end_hour
            peak_start, peak_end = definition.peak_hours

            # 60% chance during peak hours, 40% during regular session
            if random.random() < 0.6:
                if peak_start > peak_end:  # Overnight session
                    if random.random() < 0.5:
                        hour = random.randint(peak_start, 23)
                    else:
                        hour = random.randint(0, peak_end)
                else:
                    hour = random.randint(peak_start, peak_end)
            else:
                if start > end:  # Overnight session
                    if random.random() < 0.5:
                        hour = random.randint(start, 23)
                    else:
                        hour = random.randint(0, end-1)
                else:
                    hour = random.randint(start, end-1)
        else:
            hour = random.randint(0, 23)  # Random hour for quiet periods

        minute = random.randint(0, 59)

        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def simulate_session_aware_trade(self,
                                   trade_date: datetime,
                                   base_config: Dict,
                                   currency_pair: str = "EUR_USD") -> SessionTrade:
        """
        Simulate a single trade with session-aware characteristics.
        """

        # Generate realistic timestamp
        timestamp = self.generate_realistic_timestamp(trade_date)
        session, overlap = self.determine_trading_session(timestamp)

        # Get session characteristics
        if session in self.session_definitions:
            session_def = self.session_definitions[session]
            volatility_mult = session_def.volatility_multiplier
            liquidity_score = session_def.liquidity_score
        else:
            volatility_mult = 0.5  # Quiet period
            liquidity_score = 0.2

        # Adjust win rate based on session characteristics
        base_win_rate = base_config.get('expected_win_rate', 50.0) / 100.0

        # Session-specific adjustments
        session_adjustments = {
            TradingSession.LONDON: 1.1,        # +10% win rate (high liquidity)
            TradingSession.NEW_YORK: 1.05,     # +5% win rate (high volatility)
            TradingSession.TOKYO: 1.0,         # Neutral
            TradingSession.SYDNEY: 0.9,        # -10% win rate (low liquidity)
            TradingSession.QUIET_PERIOD: 0.8,  # -20% win rate (unpredictable)
            TradingSession.LONDON_NY_OVERLAP: 1.15  # +15% win rate (peak activity)
        }

        # Apply overlap bonus
        if overlap == TradingSession.LONDON_NY_OVERLAP:
            session_win_rate = base_win_rate * session_adjustments[overlap]
        else:
            session_win_rate = base_win_rate * session_adjustments.get(session, 1.0)

        session_win_rate = min(0.95, max(0.05, session_win_rate))  # Cap between 5-95%

        # Determine trade outcome
        is_winner = random.random() < session_win_rate

        # Calculate trade metrics
        base_risk = 1000  # $1000 base risk
        rr_ratio = base_config.get('min_risk_reward', 2.8)

        # Session affects R:R ratio achievement
        rr_multiplier = {
            TradingSession.LONDON: 1.1,        # Better R:R in liquid markets
            TradingSession.NEW_YORK: 1.05,
            TradingSession.TOKYO: 1.0,
            TradingSession.SYDNEY: 0.9,        # Worse R:R in thin markets
            TradingSession.QUIET_PERIOD: 0.8,
            TradingSession.LONDON_NY_OVERLAP: 1.2
        }.get(session, 1.0)

        if overlap == TradingSession.LONDON_NY_OVERLAP:
            rr_multiplier = 1.2

        actual_rr = rr_ratio * rr_multiplier * random.uniform(0.8, 1.2)

        if is_winner:
            pnl_dollars = base_risk * actual_rr
            pnl_pips = pnl_dollars / 10  # Simplified pips calculation
        else:
            pnl_dollars = -base_risk
            pnl_pips = -base_risk / 10

        # Trade duration (session affects typical trade length)
        duration_base = {
            TradingSession.LONDON: 8.0,        # Faster moves in liquid sessions
            TradingSession.NEW_YORK: 6.0,
            TradingSession.TOKYO: 12.0,        # Slower, more methodical
            TradingSession.SYDNEY: 15.0,       # Very slow moves
            TradingSession.QUIET_PERIOD: 20.0,
            TradingSession.LONDON_NY_OVERLAP: 4.0  # Very fast during overlap
        }.get(session, 10.0)

        duration = duration_base * random.uniform(0.5, 2.0)

        # MAE/MFE based on session volatility
        base_mae = abs(pnl_pips) * 0.6 * volatility_mult
        base_mfe = abs(pnl_pips) * 1.3 * volatility_mult

        mae_pips = base_mae * random.uniform(0.8, 1.5)
        mfe_pips = base_mfe * random.uniform(0.8, 1.5) if is_winner else base_mfe * random.uniform(0.2, 0.6)

        return SessionTrade(
            trade_id=random.randint(1000, 9999),
            timestamp=timestamp,
            session=session,
            session_overlap=overlap,
            currency_pair=currency_pair,
            entry_price=1.0850 + random.uniform(-0.01, 0.01),  # Mock EUR/USD price
            exit_price=1.0850 + (pnl_pips/10000),
            pnl=pnl_dollars,
            pnl_pips=pnl_pips,
            pnl_dollars=pnl_dollars,
            win=is_winner,
            trade_duration_hours=duration,
            confidence_score=random.uniform(60, 95),
            risk_reward_ratio=actual_rr if is_winner else abs(pnl_dollars/base_risk),
            session_volatility=volatility_mult,
            mae_pips=mae_pips,
            mfe_pips=mfe_pips
        )

    def run_session_aware_backtest(self,
                                  config: Dict,
                                  start_date: datetime,
                                  end_date: datetime,
                                  currency_pairs: List[str] = ["EUR_USD"]) -> List[SessionTrade]:
        """
        Run comprehensive session-aware backtest.
        """

        logger.info(f"Running session-aware backtest from {start_date} to {end_date}")

        trades = []
        current_date = start_date

        # Calculate expected trades per day based on config
        trades_per_month = config.get('expected_signals_per_month', 25)
        trades_per_day = trades_per_month / 30.0

        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday=0, Sunday=6

                # Determine number of trades for this day (Poisson distribution)
                daily_trades = np.random.poisson(trades_per_day)
                daily_trades = min(daily_trades, 5)  # Cap at 5 trades per day

                for _ in range(daily_trades):
                    # Random currency pair selection
                    currency_pair = random.choice(currency_pairs)

                    # Generate trade
                    trade = self.simulate_session_aware_trade(
                        current_date, config, currency_pair
                    )
                    trades.append(trade)

            current_date += timedelta(days=1)

        logger.info(f"Generated {len(trades)} session-aware trades")
        return trades

    def analyze_session_performance(self, trades: List[SessionTrade]) -> Dict[TradingSession, SessionPerformance]:
        """
        Analyze trading performance by session.
        """

        session_results = {}

        # Group trades by session
        session_trades = {}
        for trade in trades:
            session = trade.session
            if session not in session_trades:
                session_trades[session] = []
            session_trades[session].append(trade)

        # Analyze each session
        for session, session_trade_list in session_trades.items():

            if not session_trade_list:
                continue

            # Basic metrics
            total_trades = len(session_trade_list)
            winning_trades = len([t for t in session_trade_list if t.win])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # P&L metrics
            total_pnl_dollars = sum(t.pnl_dollars for t in session_trade_list)
            total_pnl_pips = sum(t.pnl_pips for t in session_trade_list)

            winning_pnls = [t.pnl_dollars for t in session_trade_list if t.win]
            losing_pnls = [t.pnl_dollars for t in session_trade_list if not t.win]

            avg_win_dollars = np.mean(winning_pnls) if winning_pnls else 0
            avg_loss_dollars = np.mean(losing_pnls) if losing_pnls else 0

            winning_pips = [t.pnl_pips for t in session_trade_list if t.win]
            losing_pips = [t.pnl_pips for t in session_trade_list if not t.win]

            avg_win_pips = np.mean(winning_pips) if winning_pips else 0
            avg_loss_pips = np.mean(losing_pips) if losing_pips else 0

            largest_win = max(winning_pnls) if winning_pnls else 0
            largest_loss = min(losing_pnls) if losing_pnls else 0

            # Profit factor
            total_wins = sum(winning_pnls) if winning_pnls else 0
            total_losses = abs(sum(losing_pnls)) if losing_pnls else 1
            profit_factor = total_wins / total_losses if total_losses > 0 else 0

            # Risk-reward
            avg_rr = np.mean([t.risk_reward_ratio for t in session_trade_list])

            # Duration
            avg_duration = np.mean([t.trade_duration_hours for t in session_trade_list])

            # Drawdown calculation (simplified)
            running_pnl = 0
            peak_pnl = 0
            max_dd = 0

            for trade in sorted(session_trade_list, key=lambda x: x.timestamp):
                running_pnl += trade.pnl_dollars
                if running_pnl > peak_pnl:
                    peak_pnl = running_pnl
                current_dd = peak_pnl - running_pnl
                if current_dd > max_dd:
                    max_dd = current_dd

            # Consecutive wins/losses
            consecutive_wins = consecutive_losses = 0
            max_consecutive_wins = max_consecutive_losses = 0

            for trade in sorted(session_trade_list, key=lambda x: x.timestamp):
                if trade.win:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

            # Hourly performance
            hourly_performance = {}
            for hour in range(24):
                hour_trades = [t for t in session_trade_list if t.timestamp.hour == hour]
                if hour_trades:
                    hour_win_rate = len([t for t in hour_trades if t.win]) / len(hour_trades) * 100
                    hourly_performance[hour] = hour_win_rate

            # MAE/MFE
            avg_mae = np.mean([t.mae_pips for t in session_trade_list])
            avg_mfe = np.mean([t.mfe_pips for t in session_trade_list])

            # Volatility score
            volatility = np.mean([t.session_volatility for t in session_trade_list])

            # Simplified Sharpe ratio
            returns = [t.pnl_dollars for t in session_trade_list]
            returns_mean = np.mean(returns)
            returns_std = np.std(returns) if len(returns) > 1 else 1
            sharpe = (returns_mean / returns_std) if returns_std > 0 else 0

            # Peak performance hours
            best_hours = sorted(hourly_performance.items(), key=lambda x: x[1], reverse=True)
            peak_hours = [hour for hour, win_rate in best_hours[:3] if win_rate > win_rate]
            avoid_hours = [hour for hour, win_rate in best_hours[-3:] if win_rate < win_rate * 0.8]

            # Currency pair performance
            pair_performance = {}
            for pair in set(t.currency_pair for t in session_trade_list):
                pair_trades = [t for t in session_trade_list if t.currency_pair == pair]
                pair_pnl = sum(t.pnl_dollars for t in pair_trades)
                pair_performance[pair] = pair_pnl

            session_results[session] = SessionPerformance(
                session=session,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl_dollars=total_pnl_dollars,
                total_pnl_pips=total_pnl_pips,
                avg_win_dollars=avg_win_dollars,
                avg_loss_dollars=avg_loss_dollars,
                avg_win_pips=avg_win_pips,
                avg_loss_pips=avg_loss_pips,
                largest_win_dollars=largest_win,
                largest_loss_dollars=largest_loss,
                profit_factor=profit_factor,
                avg_risk_reward=avg_rr,
                avg_trade_duration=avg_duration,
                max_drawdown_dollars=max_dd,
                max_drawdown_pips=max_dd / 10,  # Simplified conversion
                consecutive_wins_max=max_consecutive_wins,
                consecutive_losses_max=max_consecutive_losses,
                sharpe_ratio=sharpe,
                hit_rate_by_hour=hourly_performance,
                avg_mae_pips=avg_mae,
                avg_mfe_pips=avg_mfe,
                volatility_score=volatility,
                peak_performance_hours=peak_hours,
                avoid_hours=avoid_hours,
                currency_pair_performance=pair_performance
            )

        return session_results

    def generate_session_report(self, session_results: Dict[TradingSession, SessionPerformance]) -> Dict:
        """
        Generate comprehensive session analysis report.
        """

        # Find best performing sessions
        profitable_sessions = {k: v for k, v in session_results.items() if v.total_pnl_dollars > 0}
        best_session = max(profitable_sessions.items(), key=lambda x: x[1].total_pnl_dollars) if profitable_sessions else None

        # Find highest volume session
        highest_volume = max(session_results.items(), key=lambda x: x[1].total_trades) if session_results else None

        # Find best win rate session
        best_win_rate = max(session_results.items(), key=lambda x: x[1].win_rate) if session_results else None

        # Find highest risk session
        highest_risk = max(session_results.items(), key=lambda x: x[1].max_drawdown_dollars) if session_results else None

        # Calculate total performance
        total_trades = sum(perf.total_trades for perf in session_results.values())
        total_pnl = sum(perf.total_pnl_dollars for perf in session_results.values())

        # Session rankings
        session_rankings = sorted(
            session_results.items(),
            key=lambda x: x[1].total_pnl_dollars,
            reverse=True
        )

        report = {
            'analysis_summary': {
                'total_trades_analyzed': total_trades,
                'total_pnl_dollars': total_pnl,
                'sessions_analyzed': len(session_results),
                'analysis_timestamp': datetime.now().isoformat()
            },
            'best_performing_session': {
                'session': best_session[0].value if best_session else None,
                'total_pnl': best_session[1].total_pnl_dollars if best_session else 0,
                'win_rate': best_session[1].win_rate if best_session else 0,
                'total_trades': best_session[1].total_trades if best_session else 0
            } if best_session else None,
            'highest_volume_session': {
                'session': highest_volume[0].value if highest_volume else None,
                'total_trades': highest_volume[1].total_trades if highest_volume else 0,
                'trades_percentage': (highest_volume[1].total_trades / total_trades * 100) if highest_volume and total_trades > 0 else 0
            } if highest_volume else None,
            'best_win_rate_session': {
                'session': best_win_rate[0].value if best_win_rate else None,
                'win_rate': best_win_rate[1].win_rate if best_win_rate else 0,
                'total_trades': best_win_rate[1].total_trades if best_win_rate else 0
            } if best_win_rate else None,
            'highest_risk_session': {
                'session': highest_risk[0].value if highest_risk else None,
                'max_drawdown': highest_risk[1].max_drawdown_dollars if highest_risk else 0,
                'total_trades': highest_risk[1].total_trades if highest_risk else 0
            } if highest_risk else None,
            'session_rankings': [
                {
                    'rank': idx + 1,
                    'session': session.value,
                    'total_pnl': performance.total_pnl_dollars,
                    'win_rate': performance.win_rate,
                    'total_trades': performance.total_trades,
                    'profit_factor': performance.profit_factor,
                    'avg_risk_reward': performance.avg_risk_reward
                }
                for idx, (session, performance) in enumerate(session_rankings)
            ],
            'detailed_session_results': {
                session.value: asdict(performance)
                for session, performance in session_results.items()
            },
            'trading_recommendations': self._generate_session_recommendations(session_results)
        }

        return report

    def _generate_session_recommendations(self, session_results: Dict[TradingSession, SessionPerformance]) -> List[str]:
        """Generate actionable trading recommendations based on session analysis."""

        recommendations = []

        if not session_results:
            return ["No session data available for analysis"]

        # Find best sessions
        profitable_sessions = [(s, p) for s, p in session_results.items() if p.total_pnl_dollars > 0]
        unprofitable_sessions = [(s, p) for s, p in session_results.items() if p.total_pnl_dollars <= 0]

        if profitable_sessions:
            best_session = max(profitable_sessions, key=lambda x: x[1].total_pnl_dollars)
            recommendations.append(f"FOCUS TRADING: {best_session[0].value} session shows best performance (${best_session[1].total_pnl_dollars:,.0f} profit)")

            if best_session[1].win_rate > 60:
                recommendations.append(f"HIGH WIN RATE: {best_session[0].value} achieves {best_session[1].win_rate:.1f}% win rate - prioritize this session")

        # Identify high-risk sessions
        if unprofitable_sessions:
            worst_session = min(unprofitable_sessions, key=lambda x: x[1].total_pnl_dollars)
            recommendations.append(f"AVOID: {worst_session[0].value} session shows losses (${worst_session[1].total_pnl_dollars:,.0f}) - consider filtering out")

        # Analyze overlaps
        overlap_sessions = [s for s in session_results.keys() if 'OVERLAP' in s.value]
        for overlap in overlap_sessions:
            if overlap in session_results:
                perf = session_results[overlap]
                if perf.total_pnl_dollars > 0:
                    recommendations.append(f"OVERLAP OPPORTUNITY: {overlap.value} shows ${perf.total_pnl_dollars:,.0f} profit - high-activity period")

        # Volume recommendations
        high_volume_sessions = [(s, p) for s, p in session_results.items() if p.total_trades > 20]
        if high_volume_sessions:
            best_volume = max(high_volume_sessions, key=lambda x: x[1].total_trades)
            recommendations.append(f"HIGH VOLUME: {best_volume[0].value} provides most opportunities ({best_volume[1].total_trades} trades)")

        # Risk management
        high_drawdown_sessions = [(s, p) for s, p in session_results.items() if p.max_drawdown_dollars > 1000]
        for session, perf in high_drawdown_sessions:
            recommendations.append(f"RISK WARNING: {session.value} shows high drawdown (${perf.max_drawdown_dollars:,.0f}) - reduce position sizes")

        return recommendations

    def print_session_analysis(self, session_results: Dict[TradingSession, SessionPerformance]):
        """Print comprehensive session analysis to console."""

        print("\n" + "="*80)
        print("TRADING SESSION PERFORMANCE ANALYSIS")
        print("="*80)

        # Summary table
        print(f"\n{'SESSION':<20} {'TRADES':<8} {'WIN RATE':<10} {'TOTAL P&L':<12} {'PROFIT FACTOR':<10} {'AVG R:R':<10}")
        print("-" * 80)

        for session, perf in sorted(session_results.items(), key=lambda x: x[1].total_pnl_dollars, reverse=True):
            print(f"{session.value:<20} {perf.total_trades:<8} {perf.win_rate:>6.1f}% {perf.total_pnl_dollars:>+10,.0f} {perf.profit_factor:>9.2f} {perf.avg_risk_reward:>9.2f}")

        # Detailed analysis
        for session, perf in session_results.items():
            print(f"\n{session.value.upper()} SESSION DETAILED ANALYSIS:")
            print("-" * 50)
            print(f"  Trades: {perf.total_trades} ({perf.winning_trades}W / {perf.losing_trades}L)")
            print(f"  Win Rate: {perf.win_rate:.1f}%")
            print(f"  Total P&L: ${perf.total_pnl_dollars:+,.2f} ({perf.total_pnl_pips:+,.0f} pips)")
            print(f"  Avg Win: ${perf.avg_win_dollars:,.2f} ({perf.avg_win_pips:.0f} pips)")
            print(f"  Avg Loss: ${perf.avg_loss_dollars:,.2f} ({perf.avg_loss_pips:.0f} pips)")
            print(f"  Largest Win: ${perf.largest_win_dollars:,.2f}")
            print(f"  Largest Loss: ${perf.largest_loss_dollars:,.2f}")
            print(f"  Profit Factor: {perf.profit_factor:.2f}")
            print(f"  Avg R:R: {perf.avg_risk_reward:.2f}:1")
            print(f"  Avg Duration: {perf.avg_trade_duration:.1f} hours")
            print(f"  Max Drawdown: ${perf.max_drawdown_dollars:,.2f}")
            print(f"  Sharpe Ratio: {perf.sharpe_ratio:.2f}")
            print(f"  Max Consecutive Wins: {perf.consecutive_wins_max}")
            print(f"  Max Consecutive Losses: {perf.consecutive_losses_max}")

            if perf.peak_performance_hours:
                print(f"  Best Hours: {perf.peak_performance_hours}")
            if perf.avoid_hours:
                print(f"  Avoid Hours: {perf.avoid_hours}")


def main():
    """Main execution function for session analysis demo"""

    print("Trading Session Analysis System")
    print("=" * 50)
    print("Analyzing trading performance by global forex sessions")
    print()

    # Initialize analyzer
    analyzer = SessionAnalyzer()

    # Demo configuration (Cycle 4 parameters)
    config = {
        'name': 'Cycle_4_Demo',
        'expected_signals_per_month': 25,
        'expected_win_rate': 50.0,
        'min_risk_reward': 2.8,
        'confidence_threshold': 70.0
    }

    # Run 3-month session-aware backtest
    start_date = datetime(2024, 10, 1)
    end_date = datetime(2024, 12, 31)

    print(f"Running session-aware backtest: {start_date.date()} to {end_date.date()}")

    # Generate session-aware trades
    trades = analyzer.run_session_aware_backtest(
        config=config,
        start_date=start_date,
        end_date=end_date,
        currency_pairs=["EUR_USD", "GBP_USD", "USD_JPY"]
    )

    print(f"Generated {len(trades)} trades with session awareness")

    # Analyze performance by session
    session_results = analyzer.analyze_session_performance(trades)

    # Print analysis
    analyzer.print_session_analysis(session_results)

    # Generate comprehensive report
    report = analyzer.generate_session_report(session_results)

    print(f"\n\nKEY FINDINGS:")
    print("-" * 30)

    if report['best_performing_session']:
        best = report['best_performing_session']
        print(f"Most Profitable: {best['session']} (${best['total_pnl']:,.0f})")

    if report['highest_volume_session']:
        volume = report['highest_volume_session']
        print(f"Most Active: {volume['session']} ({volume['total_trades']} trades)")

    if report['best_win_rate_session']:
        win_rate = report['best_win_rate_session']
        print(f"Best Win Rate: {win_rate['session']} ({win_rate['win_rate']:.1f}%)")

    print(f"\nRECOMMENDATIONS:")
    for i, rec in enumerate(report['trading_recommendations'], 1):
        print(f"{i}. {rec}")

    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"session_analysis_report_{timestamp}.json"

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nDetailed report saved: {report_file}")

    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)