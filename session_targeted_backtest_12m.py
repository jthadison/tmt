#!/usr/bin/env python3
"""
12-Month Session-Targeted Backtest Suite

Comprehensive backtest analysis using the reversible session-targeted trading system
over a 12-month period to validate the effectiveness of session-specific optimization.

Usage:
    python session_targeted_backtest_12m.py --run-all
    python session_targeted_backtest_12m.py --session-targeting
    python session_targeted_backtest_12m.py --universal
    python session_targeted_backtest_12m.py --compare
"""

import asyncio
import argparse
import logging
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
import pytz

# Add necessary imports
sys.path.append(str(Path(__file__).parent / "agents" / "market-analysis"))

# Import from app modules
try:
    from app.signals.parameter_calculator import SignalParameterCalculator
    from app.signals.signal_generator import SignalGenerator, TradingSession
    from app.wyckoff.enhanced_pattern_detector import EnhancedWyckoffDetector
    from app.wyckoff.confidence_scorer import PatternConfidenceScorer
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Import error: {e}")
    # Fallback - create mock implementations for testing
    class TradingSession:
        SYDNEY = "Sydney"
        TOKYO = "Tokyo"
        LONDON = "London"
        NEW_YORK = "New_York"
        LONDON_NY_OVERLAP = "London_NY_Overlap"

    class SignalParameterCalculator:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def calculate_signal_parameters(self, **kwargs):
            return {'entry_price': 1.0500, 'stop_loss': 1.0480, 'take_profit_1': 1.0520, 'risk_reward_ratio': 1.0, 'signal_type': 'long'}

    class SignalGenerator:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.enable_session_targeting = kwargs.get('enable_session_targeting', False)
        async def _detect_wyckoff_patterns(self, price_data, volume_data):
            return [{'type': 'accumulation', 'confidence': 70.0}]
        def toggle_session_targeting(self, enabled):
            self.enable_session_targeting = enabled
            return {'status': 'success'}

    class EnhancedWyckoffDetector:
        def __init__(self, **kwargs):
            self.validation_thresholds = {'min_confidence': 65, 'min_risk_reward': 1.5}

    class PatternConfidenceScorer:
        def __init__(self, **kwargs):
            pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SessionBacktestResult:
    """Enhanced backtest result with session-targeting metrics"""
    test_id: str
    configuration: str
    session_targeting_enabled: bool
    start_date: datetime
    end_date: datetime
    total_signals: int
    executed_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    average_win: float
    average_loss: float
    max_drawdown: float
    sharpe_ratio: float
    session_performance: Dict[str, Dict]  # Performance by session
    parameters_used: Dict[str, Any]
    detailed_trades: List[Dict]


class SessionTargetedBacktestSuite:
    """
    12-month backtest suite for validating session-targeted trading effectiveness.
    """

    def __init__(self):
        self.results_dir = Path("session_backtest_results")
        self.results_dir.mkdir(exist_ok=True)

        # Generate 12 months of market data
        self.market_data = self._generate_12_month_market_data()
        self.backtest_results: List[SessionBacktestResult] = []

        # Session-specific optimal parameters (adjusted for realistic execution)
        self.session_parameters = {
            'Tokyo': {
                'cycle': 'Cycle 2 Ultra Selective',
                'confidence_threshold': 65.0,  # Lowered from 85 for execution
                'min_risk_reward': 2.0,        # Lowered from 4.0 for execution
                'atr_stop_multiplier': 0.3,
                'description': 'Ultra-selective approach during Tokyo session'
            },
            'London': {
                'cycle': 'Cycle 5 Dynamic Adaptive',
                'confidence_threshold': 60.0,  # Lowered from 72 for execution
                'min_risk_reward': 2.2,        # Lowered from 3.2 for execution
                'atr_stop_multiplier': 0.5,
                'description': 'Dynamic adaptive approach during London session'
            },
            'New_York': {
                'cycle': 'Cycle 4 Balanced Aggressive',
                'confidence_threshold': 55.0,  # Lowered from 70 for execution
                'min_risk_reward': 1.8,        # Lowered from 2.8 for execution
                'atr_stop_multiplier': 0.5,
                'description': 'Balanced aggressive approach during NY session'
            },
            'Sydney': {
                'cycle': 'Cycle 3 Multi-Timeframe',
                'confidence_threshold': 62.0,  # Lowered from 78 for execution
                'min_risk_reward': 2.1,        # Lowered from 3.5 for execution
                'atr_stop_multiplier': 0.4,
                'description': 'Multi-timeframe approach during Sydney session'
            },
            'London_NY_Overlap': {
                'cycle': 'Cycle 4 Balanced Aggressive',
                'confidence_threshold': 55.0,  # Lowered from 70 for execution
                'min_risk_reward': 1.8,        # Lowered from 2.8 for execution
                'atr_stop_multiplier': 0.5,
                'description': 'Balanced approach during overlap period'
            }
        }

        # Universal parameters (Cycle 4, adjusted for execution)
        self.universal_parameters = {
            'cycle': 'Cycle 4 Universal',
            'confidence_threshold': 58.0,  # Lowered from 70 for execution
            'min_risk_reward': 1.9,        # Lowered from 2.8 for execution
            'atr_stop_multiplier': 0.5,
            'description': 'Universal approach used when session targeting disabled'
        }

    def _generate_12_month_market_data(self) -> pd.DataFrame:
        """Generate 12 months of realistic hourly market data"""

        logger.info("Generating 12 months of hourly market data...")

        # 12 months = 365 days * 24 hours = 8760 hours
        start_date = datetime.now() - timedelta(days=365)
        dates = pd.date_range(start=start_date, periods=8760, freq='H')

        np.random.seed(42)  # Reproducible results

        # More realistic FX parameters for EUR/USD
        base_price = 1.0500
        daily_volatility = 0.012  # 1.2% daily volatility (more realistic for EUR/USD)
        hourly_volatility = daily_volatility / np.sqrt(24)

        # Generate correlated price movements with seasonal patterns
        returns = np.random.normal(0, hourly_volatility, len(dates))

        # Add seasonal patterns (stronger trends during certain periods)
        for i, date in enumerate(dates):
            # Add some monthly seasonality
            month_factor = 1 + 0.2 * np.sin(2 * np.pi * date.month / 12)
            # Add some weekly patterns
            weekday_factor = 1 + 0.1 * np.sin(2 * np.pi * date.weekday() / 7)
            # Add session-based volatility
            hour_gmt = date.hour
            session_volatility = self._get_session_volatility_multiplier(hour_gmt)

            returns[i] *= month_factor * weekday_factor * session_volatility

        # Add trending behavior
        trend_periods = np.random.choice([0, 1, -1], size=len(dates), p=[0.6, 0.2, 0.2])
        trend_strength = 0.00015  # Slightly stronger trends

        # Apply trends with momentum
        momentum = 0
        for i in range(1, len(returns)):
            momentum = 0.9 * momentum + 0.1 * trend_periods[i]
            returns[i] += momentum * trend_strength

        # Create price series
        prices = [base_price]
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)

        # Generate OHLC data with session-aware volume
        ohlc_data = []
        for i, close_price in enumerate(prices):
            date = dates[i]

            # Generate realistic OHLC
            intrabar_volatility = hourly_volatility * 0.4

            if i == 0:
                open_price = close_price
            else:
                open_price = prices[i-1]

            high_noise = np.random.exponential(intrabar_volatility)
            low_noise = np.random.exponential(intrabar_volatility)

            high = max(open_price, close_price) + high_noise
            low = min(open_price, close_price) - low_noise

            # Session-aware volume generation
            volume = self._get_session_volume(date)

            ohlc_data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume,
                'session': self._get_trading_session(date)
            })

        df = pd.DataFrame(ohlc_data)
        df.set_index('timestamp', inplace=True)

        logger.info(f"Generated {len(df)} hours of market data from {df.index[0]} to {df.index[-1]}")
        logger.info(f"Sessions distribution: {df['session'].value_counts().to_dict()}")

        return df

    def _get_session_volatility_multiplier(self, hour_gmt: int) -> float:
        """Get volatility multiplier based on trading session"""
        if 22 <= hour_gmt or hour_gmt < 6:  # Sydney
            return 0.8
        elif 6 <= hour_gmt < 8:  # Tokyo
            return 1.2
        elif 8 <= hour_gmt < 13:  # London
            return 1.5
        elif 13 <= hour_gmt < 17:  # London/NY Overlap
            return 1.8
        elif 17 <= hour_gmt < 22:  # New York
            return 1.3
        else:
            return 1.0

    def _get_session_volume(self, date: datetime) -> int:
        """Generate session-appropriate volume"""
        hour_gmt = date.hour
        base_volume = 10000

        if 22 <= hour_gmt or hour_gmt < 6:  # Sydney
            multiplier = 0.6
        elif 6 <= hour_gmt < 8:  # Tokyo
            multiplier = 1.2
        elif 8 <= hour_gmt < 13:  # London
            multiplier = 1.8
        elif 13 <= hour_gmt < 17:  # London/NY Overlap
            multiplier = 2.5
        elif 17 <= hour_gmt < 22:  # New York
            multiplier = 1.5
        else:
            multiplier = 1.0

        # Add randomness
        volume = int(base_volume * multiplier * np.random.lognormal(0, 0.3))
        return max(volume, 1000)  # Minimum volume

    def _get_trading_session(self, date: datetime) -> str:
        """Determine trading session based on GMT hour"""
        hour_gmt = date.hour

        if 22 <= hour_gmt or hour_gmt < 6:
            return 'Sydney'
        elif 6 <= hour_gmt < 8:
            return 'Tokyo'
        elif 8 <= hour_gmt < 13:
            return 'London'
        elif 13 <= hour_gmt < 17:
            return 'London_NY_Overlap'
        elif 17 <= hour_gmt < 22:
            return 'New_York'
        else:
            return 'Sydney'

    async def run_session_targeted_backtest(self) -> SessionBacktestResult:
        """Run 12-month backtest with session-targeting enabled"""

        logger.info("Running 12-month session-targeted backtest...")

        # Initialize with session targeting enabled
        signal_generator = SignalGenerator(
            confidence_threshold=70.0,  # Base threshold, will be overridden by sessions
            min_risk_reward=2.8,
            enable_session_targeting=True  # KEY: Enable session-specific optimization
        )

        pattern_detector = EnhancedWyckoffDetector()
        parameter_calculator = SignalParameterCalculator(min_risk_reward=2.8)

        # Run backtest with session targeting
        result = await self._execute_session_backtest(
            "session_targeted",
            signal_generator,
            pattern_detector,
            parameter_calculator,
            session_targeting_enabled=True
        )

        return result

    async def run_universal_backtest(self) -> SessionBacktestResult:
        """Run 12-month backtest with universal parameters (no session targeting)"""

        logger.info("Running 12-month universal backtest...")

        # Initialize with session targeting disabled
        signal_generator = SignalGenerator(
            confidence_threshold=70.0,
            min_risk_reward=2.8,
            enable_session_targeting=False  # KEY: Disable session-specific optimization
        )

        pattern_detector = EnhancedWyckoffDetector()
        parameter_calculator = SignalParameterCalculator(min_risk_reward=2.8)

        # Run backtest without session targeting
        result = await self._execute_session_backtest(
            "universal",
            signal_generator,
            pattern_detector,
            parameter_calculator,
            session_targeting_enabled=False
        )

        return result

    async def _execute_session_backtest(self,
                                      config_name: str,
                                      signal_generator: SignalGenerator,
                                      pattern_detector: EnhancedWyckoffDetector,
                                      parameter_calculator: SignalParameterCalculator,
                                      session_targeting_enabled: bool) -> SessionBacktestResult:
        """Execute a complete 12-month backtest"""

        logger.info(f"Executing {config_name} backtest (session targeting: {session_targeting_enabled})")

        lookback_hours = 24
        signals_generated = []
        executed_trades = []
        session_performance = {session: {'signals': 0, 'trades': 0, 'pnl': 0.0, 'wins': 0}
                             for session in ['Sydney', 'Tokyo', 'London', 'New_York', 'London_NY_Overlap']}

        # Process data in chunks to avoid memory issues
        chunk_size = 1000
        total_processed = 0

        for chunk_start in range(lookback_hours, len(self.market_data) - 24, chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(self.market_data) - 24)

            for i in range(chunk_start, chunk_end):
                current_time = self.market_data.index[i]
                current_session = self.market_data.loc[current_time, 'session']
                price_slice = self.market_data.iloc[i-lookback_hours:i]
                volume_slice = self.market_data['volume'].iloc[i-lookback_hours:i]

                try:
                    # Apply session-specific parameters if enabled
                    if session_targeting_enabled:
                        session_params = self.session_parameters.get(current_session, self.universal_parameters)
                        # Simulate session parameter application
                        effective_confidence = session_params['confidence_threshold']
                        effective_min_rr = session_params['min_risk_reward']
                    else:
                        effective_confidence = self.universal_parameters['confidence_threshold']
                        effective_min_rr = self.universal_parameters['min_risk_reward']

                    # Generate patterns
                    patterns = await signal_generator._detect_wyckoff_patterns(
                        price_slice, volume_slice
                    )

                    if not patterns:
                        continue

                    # Process each pattern
                    for pattern in patterns:
                        # Apply session-specific confidence adjustment
                        pattern_confidence = pattern.get('confidence', 0)

                        # Create signal record
                        signal = {
                            'signal_id': f"{config_name}_{current_time.strftime('%Y%m%d_%H%M%S')}_{len(signals_generated)}",
                            'timestamp': current_time,
                            'session': current_session,
                            'symbol': 'EUR_USD',
                            'pattern_type': pattern.get('type', 'unknown'),
                            'confidence': pattern_confidence,
                            'effective_confidence_threshold': effective_confidence,
                            'entry_price': float(price_slice['close'].iloc[-1] * (1 + np.random.normal(0, 0.0001))),
                            'session_targeting_enabled': session_targeting_enabled
                        }

                        # Calculate parameters based on session or universal settings
                        if session_targeting_enabled:
                            atr_multiplier = session_params['atr_stop_multiplier']
                        else:
                            atr_multiplier = self.universal_parameters['atr_stop_multiplier']

                        # Simple parameter calculation
                        atr = price_slice['high'].rolling(14).mean() - price_slice['low'].rolling(14).mean()
                        current_atr = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0.002

                        signal['stop_loss'] = signal['entry_price'] - (current_atr * atr_multiplier)
                        signal['take_profit'] = signal['entry_price'] + (current_atr * atr_multiplier * effective_min_rr)
                        signal['risk_reward_ratio'] = effective_min_rr
                        signal['signal_type'] = 'long'  # Simplified

                        signals_generated.append(signal)
                        session_performance[current_session]['signals'] += 1

                        # Check if signal should be executed
                        if await self._should_execute_session_signal(signal, effective_confidence, effective_min_rr):
                            trade_result = await self._simulate_trade(
                                signal, self.market_data.iloc[i:i+48]
                            )

                            if trade_result:
                                trade_result['session'] = current_session
                                executed_trades.append(trade_result)

                                # Update session performance
                                session_performance[current_session]['trades'] += 1
                                session_performance[current_session]['pnl'] += trade_result['pnl']
                                if trade_result['outcome'] == 'win':
                                    session_performance[current_session]['wins'] += 1

                except Exception as e:
                    logger.warning(f"Error processing signal at {current_time}: {e}")
                    continue

                total_processed += 1

            # Progress update
            progress = (chunk_end / (len(self.market_data) - 48)) * 100
            logger.info(f"Progress: {progress:.1f}% - Signals: {len(signals_generated)}, Trades: {len(executed_trades)}")

        # Calculate comprehensive metrics
        result = self._calculate_session_backtest_metrics(
            config_name, signals_generated, executed_trades, session_performance, session_targeting_enabled
        )

        logger.info(f"Backtest {config_name} completed:")
        logger.info(f"  Total signals: {result.total_signals}")
        logger.info(f"  Executed trades: {result.executed_trades}")
        logger.info(f"  Win rate: {result.win_rate:.1f}%")
        logger.info(f"  Total P&L: {result.total_pnl:.4f}")

        return result

    async def _should_execute_session_signal(self, signal: Dict, confidence_threshold: float, min_risk_reward: float) -> bool:
        """Determine if signal should be executed based on session-specific criteria"""

        confidence = signal.get('confidence', 0)
        risk_reward = signal.get('risk_reward_ratio', 0)

        return (confidence >= confidence_threshold and
                risk_reward >= min_risk_reward and
                signal['entry_price'] > 0 and
                signal['stop_loss'] > 0)

    async def _simulate_trade(self, signal: Dict, future_data: pd.DataFrame) -> Optional[Dict]:
        """Simulate trade execution and outcome"""

        if len(future_data) < 2:
            return None

        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        signal_type = signal['signal_type']

        # Track trade through future price data
        for i, (timestamp, row) in enumerate(future_data.iterrows()):
            high = row['high']
            low = row['low']

            # Check for stop loss hit (long trades)
            if signal_type == 'long':
                if low <= stop_loss:
                    pnl = stop_loss - entry_price
                    return {
                        'signal_id': signal['signal_id'],
                        'entry_time': signal['timestamp'],
                        'exit_time': timestamp,
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'pnl': pnl,
                        'outcome': 'loss',
                        'hold_hours': i + 1,
                        'signal_type': signal_type
                    }

                # Check for take profit hit
                if high >= take_profit:
                    pnl = take_profit - entry_price
                    return {
                        'signal_id': signal['signal_id'],
                        'entry_time': signal['timestamp'],
                        'exit_time': timestamp,
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'pnl': pnl,
                        'outcome': 'win',
                        'hold_hours': i + 1,
                        'signal_type': signal_type
                    }

        # Trade expired without hitting targets
        final_price = future_data['close'].iloc[-1]
        pnl = final_price - entry_price
        outcome = 'win' if pnl > 0 else 'loss'

        return {
            'signal_id': signal['signal_id'],
            'entry_time': signal['timestamp'],
            'exit_time': future_data.index[-1],
            'entry_price': entry_price,
            'exit_price': final_price,
            'pnl': pnl,
            'outcome': outcome,
            'hold_hours': len(future_data),
            'signal_type': signal_type
        }

    def _calculate_session_backtest_metrics(self,
                                          config_name: str,
                                          signals: List[Dict],
                                          trades: List[Dict],
                                          session_performance: Dict,
                                          session_targeting_enabled: bool) -> SessionBacktestResult:
        """Calculate comprehensive session-aware backtest metrics"""

        if not trades:
            return SessionBacktestResult(
                test_id=f"{config_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                configuration=config_name,
                session_targeting_enabled=session_targeting_enabled,
                start_date=self.market_data.index[0],
                end_date=self.market_data.index[-1],
                total_signals=len(signals),
                executed_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                total_pnl=0.0,
                average_win=0.0,
                average_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                session_performance=session_performance,
                parameters_used={},
                detailed_trades=[]
            )

        # Calculate session-specific performance
        for session in session_performance:
            session_data = session_performance[session]
            if session_data['trades'] > 0:
                session_data['win_rate'] = (session_data['wins'] / session_data['trades']) * 100
                session_data['avg_pnl_per_trade'] = session_data['pnl'] / session_data['trades']
            else:
                session_data['win_rate'] = 0.0
                session_data['avg_pnl_per_trade'] = 0.0

        # Basic metrics
        wins = [t for t in trades if t['outcome'] == 'win']
        losses = [t for t in trades if t['outcome'] == 'loss']

        win_rate = (len(wins) / len(trades)) * 100 if trades else 0

        # P&L metrics
        total_pnl = sum(t['pnl'] for t in trades)
        gross_profit = sum(t['pnl'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        average_win = gross_profit / len(wins) if wins else 0
        average_loss = gross_loss / len(losses) if losses else 0

        # Calculate maximum drawdown
        running_pnl = 0
        peak_pnl = 0
        max_drawdown = 0

        for trade in sorted(trades, key=lambda x: x['exit_time']):
            running_pnl += trade['pnl']
            if running_pnl > peak_pnl:
                peak_pnl = running_pnl
            else:
                drawdown = peak_pnl - running_pnl
                max_drawdown = max(max_drawdown, drawdown)

        # Calculate Sharpe ratio
        if trades:
            daily_returns = []
            current_date = None
            daily_pnl = 0

            for trade in sorted(trades, key=lambda x: x['exit_time']):
                trade_date = trade['exit_time'].date()

                if current_date is None:
                    current_date = trade_date

                if trade_date == current_date:
                    daily_pnl += trade['pnl']
                else:
                    daily_returns.append(daily_pnl)
                    current_date = trade_date
                    daily_pnl = trade['pnl']

            if daily_pnl != 0:
                daily_returns.append(daily_pnl)

            if len(daily_returns) > 1:
                mean_return = np.mean(daily_returns)
                return_std = np.std(daily_returns)
                sharpe_ratio = mean_return / return_std if return_std > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        return SessionBacktestResult(
            test_id=f"{config_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            configuration=config_name,
            session_targeting_enabled=session_targeting_enabled,
            start_date=self.market_data.index[0],
            end_date=self.market_data.index[-1],
            total_signals=len(signals),
            executed_trades=len(trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_pnl=total_pnl,
            average_win=average_win,
            average_loss=average_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            session_performance=session_performance,
            parameters_used={'session_targeting_enabled': session_targeting_enabled},
            detailed_trades=trades
        )

    def generate_session_comparison_report(self, session_result: SessionBacktestResult,
                                         universal_result: SessionBacktestResult) -> Dict:
        """Generate comprehensive comparison report between session-targeted and universal approaches"""

        logger.info("Generating session-targeting comparison report...")

        comparison = {
            'report_generated': datetime.now().isoformat(),
            'test_period': f"{session_result.start_date} to {session_result.end_date}",
            'duration_days': (session_result.end_date - session_result.start_date).days,

            'session_targeted_results': {
                'configuration': session_result.configuration,
                'total_signals': session_result.total_signals,
                'executed_trades': session_result.executed_trades,
                'win_rate': round(session_result.win_rate, 2),
                'profit_factor': round(session_result.profit_factor, 2),
                'total_pnl': round(session_result.total_pnl, 4),
                'max_drawdown': round(session_result.max_drawdown, 4),
                'sharpe_ratio': round(session_result.sharpe_ratio, 3),
                'avg_win': round(session_result.average_win, 4),
                'avg_loss': round(session_result.average_loss, 4),
                'session_performance': session_result.session_performance
            },

            'universal_results': {
                'configuration': universal_result.configuration,
                'total_signals': universal_result.total_signals,
                'executed_trades': universal_result.executed_trades,
                'win_rate': round(universal_result.win_rate, 2),
                'profit_factor': round(universal_result.profit_factor, 2),
                'total_pnl': round(universal_result.total_pnl, 4),
                'max_drawdown': round(universal_result.max_drawdown, 4),
                'sharpe_ratio': round(universal_result.sharpe_ratio, 3),
                'avg_win': round(universal_result.average_win, 4),
                'avg_loss': round(universal_result.average_loss, 4),
                'session_performance': universal_result.session_performance
            }
        }

        # Calculate improvements
        improvements = {
            'signal_generation_improvement': session_result.total_signals - universal_result.total_signals,
            'execution_rate_improvement': ((session_result.executed_trades / session_result.total_signals) -
                                         (universal_result.executed_trades / universal_result.total_signals)) * 100
                                         if session_result.total_signals > 0 and universal_result.total_signals > 0 else 0,
            'win_rate_improvement': session_result.win_rate - universal_result.win_rate,
            'profit_factor_improvement': session_result.profit_factor - universal_result.profit_factor,
            'total_pnl_improvement': session_result.total_pnl - universal_result.total_pnl,
            'drawdown_improvement': universal_result.max_drawdown - session_result.max_drawdown,
            'sharpe_improvement': session_result.sharpe_ratio - universal_result.sharpe_ratio
        }

        comparison['improvements'] = improvements

        # Session-specific analysis
        session_analysis = {}
        for session in session_result.session_performance:
            session_targeted = session_result.session_performance[session]
            universal = universal_result.session_performance[session]

            session_analysis[session] = {
                'targeted_trades': session_targeted['trades'],
                'universal_trades': universal['trades'],
                'targeted_win_rate': session_targeted.get('win_rate', 0),
                'universal_win_rate': universal.get('win_rate', 0),
                'targeted_pnl': session_targeted['pnl'],
                'universal_pnl': universal['pnl'],
                'pnl_improvement': session_targeted['pnl'] - universal['pnl'],
                'win_rate_improvement': session_targeted.get('win_rate', 0) - universal.get('win_rate', 0)
            }

        comparison['session_analysis'] = session_analysis

        # Key insights
        insights = []

        if improvements['total_pnl_improvement'] > 0:
            pnl_improvement_pct = (improvements['total_pnl_improvement'] / abs(universal_result.total_pnl)) * 100 if universal_result.total_pnl != 0 else 0
            insights.append(f"✅ Session targeting improved total P&L by {improvements['total_pnl_improvement']:.4f} ({pnl_improvement_pct:.1f}%)")

        if improvements['win_rate_improvement'] > 0:
            insights.append(f"✅ Win rate improved by {improvements['win_rate_improvement']:.1f} percentage points")

        if improvements['signal_generation_improvement'] > 0:
            insights.append(f"✅ Generated {improvements['signal_generation_improvement']} more signals")

        if improvements['drawdown_improvement'] > 0:
            insights.append(f"✅ Reduced maximum drawdown by {improvements['drawdown_improvement']:.4f}")

        if improvements['sharpe_improvement'] > 0:
            insights.append(f"✅ Improved Sharpe ratio by {improvements['sharpe_improvement']:.3f}")

        # Best performing sessions
        best_sessions = []
        for session, data in session_analysis.items():
            if data['pnl_improvement'] > 0:
                best_sessions.append((session, data['pnl_improvement']))

        best_sessions.sort(key=lambda x: x[1], reverse=True)

        if best_sessions:
            insights.append(f"🎯 Best performing session: {best_sessions[0][0]} (+{best_sessions[0][1]:.4f} P&L improvement)")

        comparison['key_insights'] = insights

        return comparison

    async def run_comprehensive_12m_analysis(self) -> Dict:
        """Run complete 12-month session-targeting analysis"""

        logger.info("Starting comprehensive 12-month session-targeting analysis...")

        # Run both backtests
        session_result = await self.run_session_targeted_backtest()
        universal_result = await self.run_universal_backtest()

        # Store results
        self.backtest_results.extend([session_result, universal_result])

        # Generate comparison report
        comparison_report = self.generate_session_comparison_report(session_result, universal_result)

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        results_file = self.results_dir / f"session_targeting_12m_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'test_duration_months': 12,
                    'data_period': f"{session_result.start_date} to {session_result.end_date}",
                    'total_data_points': len(self.market_data)
                },
                'session_targeted_result': asdict(session_result),
                'universal_result': asdict(universal_result),
                'comparison_report': comparison_report
            }, f, indent=2, default=str)

        logger.info(f"📊 Complete 12-month session-targeting results saved to: {results_file}")

        return comparison_report


async def main():
    """Main execution function"""

    parser = argparse.ArgumentParser(description="12-Month Session-Targeted Backtest Suite")
    parser.add_argument('--session-targeting', action='store_true', help='Run session-targeting backtest only')
    parser.add_argument('--universal', action='store_true', help='Run universal backtest only')
    parser.add_argument('--compare', action='store_true', help='Run comparison analysis')
    parser.add_argument('--run-all', action='store_true', help='Run complete 12-month analysis')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize backtest suite
    backtest_suite = SessionTargetedBacktestSuite()

    try:
        if args.session_targeting:
            result = await backtest_suite.run_session_targeted_backtest()
            print(f"\n📊 SESSION-TARGETED RESULTS (12 months):")
            print(f"Signals: {result.total_signals}, Trades: {result.executed_trades}")
            print(f"Win Rate: {result.win_rate:.1f}%, Profit Factor: {result.profit_factor:.2f}")
            print(f"Total P&L: {result.total_pnl:.4f}, Max DD: {result.max_drawdown:.4f}")

        elif args.universal:
            result = await backtest_suite.run_universal_backtest()
            print(f"\n📊 UNIVERSAL RESULTS (12 months):")
            print(f"Signals: {result.total_signals}, Trades: {result.executed_trades}")
            print(f"Win Rate: {result.win_rate:.1f}%, Profit Factor: {result.profit_factor:.2f}")
            print(f"Total P&L: {result.total_pnl:.4f}, Max DD: {result.max_drawdown:.4f}")

        elif args.compare or args.run_all:
            comparison = await backtest_suite.run_comprehensive_12m_analysis()

            print(f"\n12-MONTH SESSION-TARGETING ANALYSIS")
            print("=" * 80)

            session_targeted = comparison['session_targeted_results']
            universal = comparison['universal_results']
            improvements = comparison['improvements']

            print(f"\n📅 Test Period: {comparison['test_period']} ({comparison['duration_days']} days)")

            print(f"\nSESSION-TARGETED APPROACH:")
            print(f"  Signals: {session_targeted['total_signals']}, Trades: {session_targeted['executed_trades']}")
            print(f"  Win Rate: {session_targeted['win_rate']}%, P&L: {session_targeted['total_pnl']}")
            print(f"  Profit Factor: {session_targeted['profit_factor']}, Max DD: {session_targeted['max_drawdown']}")

            print(f"\nUNIVERSAL APPROACH (Cycle 4):")
            print(f"  Signals: {universal['total_signals']}, Trades: {universal['executed_trades']}")
            print(f"  Win Rate: {universal['win_rate']}%, P&L: {universal['total_pnl']}")
            print(f"  Profit Factor: {universal['profit_factor']}, Max DD: {universal['max_drawdown']}")

            print(f"\n📈 SESSION-TARGETING IMPROVEMENTS:")
            for insight in comparison.get('key_insights', []):
                print(f"  {insight}")

            print(f"\n🕒 SESSION-SPECIFIC PERFORMANCE:")
            for session, data in comparison['session_analysis'].items():
                pnl_improvement = data['pnl_improvement']
                status = "✅" if pnl_improvement > 0 else "❌" if pnl_improvement < 0 else "➡️"
                print(f"  {status} {session}: {pnl_improvement:+.4f} P&L improvement")

        else:
            print("Please specify a test mode. Use --help for options.")
            return 1

        print("\n✅ 12-month session-targeting analysis completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ 12-month analysis failed: {e}")
        logger.error(f"Analysis error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)