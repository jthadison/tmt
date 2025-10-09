"""
Backtest Engine - Story 11.2

Core backtesting engine that orchestrates:
- Market data replay
- Signal generation
- Order execution simulation
- Position tracking
- Performance metrics calculation
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import time
import uuid

from .models import (
    BacktestConfig, BacktestResult, Trade, EquityPoint,
    TradingSession, OrderType
)
from .market_replay import MarketReplayIterator
from .signal_replay import SignalReplayEngine
from .order_simulator import OrderSimulator, SlippageModel, OrderStatus
from .metrics_calculator import MetricsCalculator
from .session_detector import TradingSessionDetector
from .validators import LookAheadValidator

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Main backtesting engine

    Orchestrates all components to run a complete backtest:
    1. Load historical data
    2. Replay market bar-by-bar (no look-ahead)
    3. Generate signals from historical data
    4. Simulate order execution
    5. Track positions and P&L
    6. Calculate comprehensive metrics
    """

    def __init__(
        self,
        config: BacktestConfig,
        enable_validation: bool = True
    ):
        """
        Initialize backtest engine

        Args:
            config: Backtest configuration
            enable_validation: Enable look-ahead bias validation
        """

        self.config = config
        self.enable_validation = enable_validation

        # Initialize components
        self.session_detector = TradingSessionDetector()

        slippage_model = SlippageModel(
            model_type=config.slippage_model,
            base_slippage_pips=0.5
        )
        self.order_simulator = OrderSimulator(slippage_model=slippage_model)

        self.signal_replay = SignalReplayEngine(
            min_confidence=config.parameters.get('confidence_threshold', 55.0),
            min_risk_reward=config.parameters.get('min_risk_reward', 1.8),
            max_risk_reward=config.parameters.get('max_risk_reward', 5.0),
            use_session_params=config.session_parameters is not None
        )

        self.metrics_calculator = MetricsCalculator()

        self.validator = LookAheadValidator() if enable_validation else None

        # State tracking
        self.account_balance = config.initial_capital
        self.equity = config.initial_capital
        self.open_positions: List[Dict] = []
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[EquityPoint] = []

        logger.info(
            f"BacktestEngine initialized: "
            f"{len(config.instruments)} instruments, "
            f"{config.start_date} to {config.end_date}"
        )

    async def run(
        self,
        market_data: Dict[str, pd.DataFrame]
    ) -> BacktestResult:
        """
        Run complete backtest

        Args:
            market_data: Dict mapping instrument to DataFrame of OHLCV data

        Returns:
            BacktestResult with all metrics

        Example:
            >>> config = BacktestConfig(...)
            >>> engine = BacktestEngine(config)
            >>> market_data = {
            ...     'EUR_USD': eur_usd_df,
            ...     'GBP_USD': gbp_usd_df
            ... }
            >>> result = await engine.run(market_data)
        """

        start_time = time.time()

        logger.info("=" * 80)
        logger.info("BACKTEST STARTED")
        logger.info("=" * 80)
        logger.info(f"Date range: {self.config.start_date} to {self.config.end_date}")
        logger.info(f"Instruments: {', '.join(self.config.instruments)}")
        logger.info(f"Initial capital: ${self.config.initial_capital:,.2f}")
        logger.info(f"Risk per trade: {self.config.risk_percentage:.1%}")
        logger.info("=" * 80)

        # Validate market data
        self._validate_market_data(market_data)

        # Reset state
        self._reset_state()

        # Run backtest for each instrument
        total_bars = 0

        for instrument in self.config.instruments:
            logger.info(f"\nProcessing {instrument}...")

            inst_data = market_data[instrument]
            bars_processed = await self._run_instrument_backtest(instrument, inst_data)

            total_bars += bars_processed
            logger.info(f"{instrument}: {bars_processed} bars processed")

        # Calculate final metrics
        execution_time = time.time() - start_time

        result = self.metrics_calculator.calculate_all_metrics(
            trades=self.closed_trades,
            equity_curve=self.equity_curve,
            config=self.config,
            execution_time=execution_time,
            bars_processed=total_bars
        )

        logger.info("=" * 80)
        logger.info("BACKTEST COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Execution time: {execution_time:.1f}s")
        logger.info(f"Total bars processed: {total_bars:,}")
        logger.info(f"Total trades: {result.total_trades}")
        logger.info(f"Win rate: {result.win_rate:.1%}")
        logger.info(f"Total return: {result.total_return_pct:.2f}%")
        logger.info(f"CAGR: {result.cagr:.2f}%")
        logger.info(f"Max drawdown: {result.max_drawdown_pct:.2f}%")
        logger.info(f"Sharpe ratio: {result.sharpe_ratio:.2f}")
        logger.info(f"Profit factor: {result.profit_factor:.2f}")
        logger.info("=" * 80)

        return result

    async def _run_instrument_backtest(
        self,
        instrument: str,
        market_data: pd.DataFrame
    ) -> int:
        """
        Run backtest for a single instrument

        Args:
            instrument: Trading instrument
            market_data: OHLCV data for instrument

        Returns:
            Number of bars processed
        """

        # Create market replay iterator
        iterator = MarketReplayIterator(
            data=market_data,
            timeframe=self.config.timeframe,
            min_history_bars=50
        )

        bars_processed = 0

        # Replay market bar-by-bar
        for current_candle, historical_data in iterator:
            bars_processed += 1

            current_timestamp = current_candle.name

            # Log progress every 100 bars
            if bars_processed % 100 == 0:
                progress = iterator.get_progress_pct()
                logger.debug(
                    f"{instrument}: {bars_processed} bars ({progress:.1f}% complete)"
                )

            # Update open positions (check for stop-loss/take-profit hits)
            await self._update_open_positions(current_candle, current_timestamp, instrument)

            # Record equity point
            self._record_equity_point(current_timestamp)

            # Generate signal if no position in this instrument
            if not self._has_open_position(instrument):
                signal = await self._generate_signal(
                    instrument, historical_data, current_timestamp
                )

                if signal:
                    # Execute signal on next bar
                    next_bar = iterator.peek_next_bar()

                    if next_bar is not None:
                        await self._execute_signal(signal, next_bar)

        return bars_processed

    async def _generate_signal(
        self,
        instrument: str,
        historical_data: pd.DataFrame,
        current_timestamp: datetime
    ) -> Optional[Dict]:
        """
        Generate trading signal

        Args:
            instrument: Trading instrument
            historical_data: Historical CLOSED candles
            current_timestamp: Current timestamp

        Returns:
            Signal dict or None
        """

        # Validate no look-ahead bias
        if self.enable_validation:
            try:
                self.validator.validate_historical_data_range(
                    current_timestamp, historical_data
                )
            except ValueError as e:
                logger.error(f"Validation failed: {e}")
                raise

        # Generate signal using signal replay engine
        signal = self.signal_replay.generate_signal(
            symbol=instrument,
            historical_data=historical_data,
            current_timestamp=current_timestamp,
            universal_params=self.config.parameters,
            session_params=self.config.session_parameters
        )

        return signal

    async def _execute_signal(
        self,
        signal: Dict,
        next_bar: pd.Series
    ) -> None:
        """
        Execute trading signal

        Args:
            signal: Signal dict from signal generator
            next_bar: Next bar data (for order fill)
        """

        instrument = signal['symbol']
        direction = signal['direction']
        session = signal['trading_session']

        # Calculate position size based on risk
        pip_value = self.order_simulator.get_pip_value(instrument)
        risk_pips = abs(signal['entry_price'] - signal['stop_loss']) / pip_value

        if risk_pips <= 0:
            logger.warning(f"Invalid risk calculation for {instrument}, skipping signal")
            return

        # Position size = risk amount / (risk in pips * pip value * units per lot)
        risk_amount = self.account_balance * self.config.risk_percentage
        units_per_pip = 1.0  # Simplified - 1 unit per pip
        units = risk_amount / (risk_pips * pip_value)

        # Execute market order at next bar open
        status, execution = self.order_simulator.execute_market_order(
            symbol=instrument,
            direction=direction,
            units=units,
            next_bar=next_bar,
            session=session,
            account_balance=self.account_balance,
            pip_value=pip_value
        )

        if status == OrderStatus.FILLED:
            # Create position
            position = {
                'trade_id': str(uuid.uuid4()),
                'symbol': instrument,
                'direction': direction,
                'entry_time': execution['fill_time'],
                'entry_price': execution['fill_price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'units': units,
                'risk_amount': risk_amount,
                'entry_slippage_pips': execution['slippage_pips'],
                'signal_confidence': signal['confidence'],
                'pattern_type': signal.get('pattern_type'),
                'wyckoff_phase': signal.get('wyckoff_phase'),
                'trading_session': session,
                'pip_value': pip_value
            }

            self.open_positions.append(position)

            logger.info(
                f"TRADE OPENED: {direction.upper()} {units:.0f} {instrument} "
                f"@ {execution['fill_price']:.5f} "
                f"(SL: {signal['stop_loss']:.5f}, TP: {signal['take_profit']:.5f})"
            )

    async def _update_open_positions(
        self,
        current_bar: pd.Series,
        current_timestamp: datetime,
        instrument: str
    ) -> None:
        """
        Update open positions - check for stop-loss/take-profit hits

        Args:
            current_bar: Current bar data
            current_timestamp: Current timestamp
            instrument: Current instrument being processed
        """

        positions_to_close = []

        for position in self.open_positions:
            # Only process positions for current instrument
            if position['symbol'] != instrument:
                continue

            direction = position['direction']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            pip_value = position['pip_value']

            # Check stop-loss hit
            sl_hit, sl_fill_price = self.order_simulator.check_stop_loss_hit(
                trade_direction=direction,
                stop_loss_price=stop_loss,
                current_bar=current_bar,
                pip_value=pip_value
            )

            if sl_hit:
                await self._close_position(
                    position, current_timestamp, sl_fill_price, 'stop_loss'
                )
                positions_to_close.append(position)
                continue

            # Check take-profit hit
            tp_hit, tp_fill_price = self.order_simulator.check_take_profit_hit(
                trade_direction=direction,
                take_profit_price=take_profit,
                current_bar=current_bar,
                pip_value=pip_value
            )

            if tp_hit:
                await self._close_position(
                    position, current_timestamp, tp_fill_price, 'take_profit'
                )
                positions_to_close.append(position)

        # Remove closed positions
        for position in positions_to_close:
            self.open_positions.remove(position)

    async def _close_position(
        self,
        position: Dict,
        exit_time: datetime,
        exit_price: float,
        exit_reason: str
    ) -> None:
        """
        Close a position and record trade

        Args:
            position: Position dict
            exit_time: Exit timestamp
            exit_price: Exit price
            exit_reason: Reason for exit ('stop_loss', 'take_profit')
        """

        direction = position['direction']
        pip_value = position['pip_value']

        # Calculate P&L
        pnl, pnl_pips = self.order_simulator.calculate_position_pnl(
            trade_direction=direction,
            entry_price=position['entry_price'],
            exit_price=exit_price,
            units=position['units'],
            pip_value=pip_value
        )

        # Calculate risk-reward achieved
        rr_achieved = self.order_simulator.calculate_risk_reward_achieved(
            trade_direction=direction,
            entry_price=position['entry_price'],
            exit_price=exit_price,
            stop_loss_price=position['stop_loss'],
            pip_value=pip_value
        )

        # Update account balance
        self.account_balance += pnl

        # Create trade record
        trade = Trade(
            trade_id=position['trade_id'],
            entry_time=position['entry_time'],
            exit_time=exit_time,
            symbol=position['symbol'],
            trade_type=direction,
            entry_price=position['entry_price'],
            exit_price=exit_price,
            stop_loss=position['stop_loss'],
            take_profit=position['take_profit'],
            units=position['units'],
            risk_amount=position['risk_amount'],
            realized_pnl=pnl,
            realized_pnl_pips=pnl_pips,
            risk_reward_achieved=rr_achieved,
            entry_slippage_pips=position['entry_slippage_pips'],
            exit_slippage_pips=0.5,  # Simplified
            signal_confidence=position['signal_confidence'],
            pattern_type=position.get('pattern_type'),
            wyckoff_phase=position.get('wyckoff_phase'),
            trading_session=position['trading_session'],
            exit_reason=exit_reason
        )

        self.closed_trades.append(trade)

        logger.info(
            f"TRADE CLOSED: {direction.upper()} {position['symbol']} "
            f"P&L: ${pnl:+.2f} ({pnl_pips:+.1f} pips) "
            f"R:R: {rr_achieved:.2f} - {exit_reason}"
        )

    def _record_equity_point(self, timestamp: datetime) -> None:
        """
        Record equity curve point

        Args:
            timestamp: Current timestamp
        """

        # Calculate unrealized P&L from open positions
        unrealized_pnl = 0.0
        # TODO: Calculate unrealized P&L from current prices

        equity = self.account_balance + unrealized_pnl

        # Calculate drawdown
        if self.equity_curve:
            peak = max(ep.balance for ep in self.equity_curve)
            drawdown = min(0, equity - peak)
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0.0
        else:
            peak = self.config.initial_capital
            drawdown = 0.0
            drawdown_pct = 0.0

        equity_point = EquityPoint(
            timestamp=timestamp,
            balance=self.account_balance,
            equity=equity,
            unrealized_pnl=unrealized_pnl,
            drawdown=drawdown,
            drawdown_pct=drawdown_pct
        )

        # Record point (sample every N bars to avoid bloat)
        if len(self.equity_curve) == 0 or len(self.equity_curve) % 10 == 0:
            self.equity_curve.append(equity_point)

    def _has_open_position(self, instrument: str) -> bool:
        """Check if there's an open position for instrument"""
        return any(p['symbol'] == instrument for p in self.open_positions)

    def _validate_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Validate market data before running backtest"""

        for instrument in self.config.instruments:
            if instrument not in market_data:
                raise ValueError(f"Missing market data for {instrument}")

            data = market_data[instrument]

            if data.empty:
                raise ValueError(f"Empty market data for {instrument}")

            if not isinstance(data.index, pd.DatetimeIndex):
                raise ValueError(f"Market data for {instrument} must have DatetimeIndex")

            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                raise ValueError(
                    f"Market data for {instrument} missing columns: {missing_cols}"
                )

        logger.info("Market data validation passed")

    def _reset_state(self) -> None:
        """Reset engine state for new backtest run"""

        self.account_balance = self.config.initial_capital
        self.equity = self.config.initial_capital
        self.open_positions = []
        self.closed_trades = []
        self.equity_curve = []

        logger.info("Engine state reset")
