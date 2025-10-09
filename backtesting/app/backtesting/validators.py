"""
Look-Ahead Bias Validators - Story 11.2

Validates that backtesting logic does not use future information.
Critical for ensuring backtest results are realistic.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LookAheadValidator:
    """
    Validates backtesting logic for look-ahead bias

    Performs runtime checks to ensure:
    1. Signals only use closed candle data
    2. Orders fill at next bar (not current bar)
    3. Historical data doesn't include future timestamps
    4. Pattern detection uses proper data boundaries
    """

    @staticmethod
    def validate_signal_timing(
        signal_timestamp: datetime,
        historical_data: pd.DataFrame
    ) -> bool:
        """
        Validate that signal was generated using only past data

        Args:
            signal_timestamp: When signal was generated
            historical_data: Historical data used for signal

        Returns:
            True if valid, raises ValueError if look-ahead detected

        Raises:
            ValueError: If look-ahead bias detected
        """

        if historical_data.empty:
            return True

        # All historical data must be BEFORE signal timestamp
        last_historical_time = historical_data.index[-1]

        if last_historical_time >= signal_timestamp:
            raise ValueError(
                f"Look-ahead bias detected! Signal timestamp {signal_timestamp} "
                f"<= last historical data {last_historical_time}. "
                "Signals must use only CLOSED candles from before signal time."
            )

        # Check for any future timestamps in historical data
        future_timestamps = historical_data.index[historical_data.index >= signal_timestamp]

        if len(future_timestamps) > 0:
            raise ValueError(
                f"Look-ahead bias! {len(future_timestamps)} future timestamps found "
                f"in historical data used for signal at {signal_timestamp}"
            )

        logger.debug(
            f"Signal timing validated: {signal_timestamp}, "
            f"last historical: {last_historical_time}"
        )

        return True

    @staticmethod
    def validate_order_fill(
        order_time: datetime,
        fill_time: datetime,
        fill_price: float,
        fill_bar: pd.Series
    ) -> bool:
        """
        Validate that order filled at next bar (not current bar)

        Args:
            order_time: When order was placed
            fill_time: When order was filled
            fill_price: Fill price
            fill_bar: Bar data where order filled

        Returns:
            True if valid, raises ValueError if look-ahead detected

        Raises:
            ValueError: If order filled at current bar (look-ahead bias)
        """

        # Fill time must be AFTER order time
        if fill_time <= order_time:
            raise ValueError(
                f"Look-ahead bias! Order filled at {fill_time} "
                f"<= order time {order_time}. "
                "Orders must fill at NEXT bar, not current bar."
            )

        # Fill bar timestamp should match fill time
        if fill_bar.name != fill_time:
            logger.warning(
                f"Fill time mismatch: fill_time={fill_time}, "
                f"fill_bar.timestamp={fill_bar.name}"
            )

        # For market orders, fill price should be near fill bar's open
        # (allowing for slippage)
        open_price = fill_bar['open']
        price_diff_pct = abs(fill_price - open_price) / open_price

        if price_diff_pct > 0.01:  # >1% difference is suspicious
            logger.warning(
                f"Large fill price deviation from open: {price_diff_pct:.2%}. "
                f"Fill: {fill_price}, Open: {open_price}. "
                "Check slippage model."
            )

        logger.debug(
            f"Order fill validated: order={order_time}, fill={fill_time}, "
            f"price={fill_price}"
        )

        return True

    @staticmethod
    def validate_historical_data_range(
        current_timestamp: datetime,
        historical_data: pd.DataFrame
    ) -> bool:
        """
        Validate historical data doesn't include current or future data

        Args:
            current_timestamp: Current replay timestamp
            historical_data: Historical data being used

        Returns:
            True if valid, raises ValueError if look-ahead detected

        Raises:
            ValueError: If historical data includes current/future timestamps
        """

        if historical_data.empty:
            return True

        # Check for timestamps >= current time
        future_data = historical_data.index[historical_data.index >= current_timestamp]

        if len(future_data) > 0:
            raise ValueError(
                f"Look-ahead bias! Historical data contains {len(future_data)} "
                f"timestamps >= current time {current_timestamp}. "
                f"First future timestamp: {future_data[0]}"
            )

        return True

    @staticmethod
    def validate_pattern_detection_data(
        pattern_data: pd.DataFrame,
        decision_timestamp: datetime
    ) -> bool:
        """
        Validate pattern detection used only closed candles

        Args:
            pattern_data: Data used for pattern detection
            decision_timestamp: When pattern was detected

        Returns:
            True if valid, raises ValueError if look-ahead detected

        Raises:
            ValueError: If pattern detection used future data
        """

        if pattern_data.empty:
            return True

        # All pattern data must be BEFORE decision time
        last_data_time = pattern_data.index[-1]

        if last_data_time >= decision_timestamp:
            raise ValueError(
                f"Look-ahead bias in pattern detection! "
                f"Pattern data extends to {last_data_time} "
                f">= decision time {decision_timestamp}. "
                "Pattern detection must use only CLOSED candles."
            )

        # Check for any incomplete/future candles
        future_candles = pattern_data.index[pattern_data.index >= decision_timestamp]

        if len(future_candles) > 0:
            raise ValueError(
                f"Look-ahead bias! Pattern detection used {len(future_candles)} "
                f"future candles (>= {decision_timestamp})"
            )

        return True

    @staticmethod
    def validate_stop_loss_execution(
        trade_entry_time: datetime,
        stop_hit_time: datetime,
        stop_hit_bar: pd.Series,
        trade_direction: str,
        stop_loss_price: float
    ) -> bool:
        """
        Validate stop-loss execution logic

        Args:
            trade_entry_time: When trade was entered
            stop_hit_time: When stop-loss was hit
            stop_hit_bar: Bar where stop was hit
            trade_direction: 'long' or 'short'
            stop_loss_price: Stop-loss price level

        Returns:
            True if valid, raises ValueError if invalid logic

        Raises:
            ValueError: If stop-loss execution has logical errors
        """

        # Stop must hit AFTER entry
        if stop_hit_time <= trade_entry_time:
            raise ValueError(
                f"Invalid stop-loss timing! Stop hit at {stop_hit_time} "
                f"<= entry time {trade_entry_time}"
            )

        # Verify stop-loss price was actually hit
        if trade_direction == 'long':
            # Long stop-loss: must hit if low <= stop price
            if stop_hit_bar['low'] > stop_loss_price:
                raise ValueError(
                    f"Invalid long stop-loss! Stop price {stop_loss_price} "
                    f"not reached (bar low: {stop_hit_bar['low']})"
                )
        else:  # short
            # Short stop-loss: must hit if high >= stop price
            if stop_hit_bar['high'] < stop_loss_price:
                raise ValueError(
                    f"Invalid short stop-loss! Stop price {stop_loss_price} "
                    f"not reached (bar high: {stop_hit_bar['high']})"
                )

        return True

    @staticmethod
    def validate_take_profit_execution(
        trade_entry_time: datetime,
        tp_hit_time: datetime,
        tp_hit_bar: pd.Series,
        trade_direction: str,
        take_profit_price: float
    ) -> bool:
        """
        Validate take-profit execution logic

        Args:
            trade_entry_time: When trade was entered
            tp_hit_time: When take-profit was hit
            tp_hit_bar: Bar where TP was hit
            trade_direction: 'long' or 'short'
            take_profit_price: Take-profit price level

        Returns:
            True if valid, raises ValueError if invalid logic

        Raises:
            ValueError: If take-profit execution has logical errors
        """

        # TP must hit AFTER entry
        if tp_hit_time <= trade_entry_time:
            raise ValueError(
                f"Invalid take-profit timing! TP hit at {tp_hit_time} "
                f"<= entry time {trade_entry_time}"
            )

        # Verify take-profit price was actually hit
        if trade_direction == 'long':
            # Long take-profit: must hit if high >= TP price
            if tp_hit_bar['high'] < take_profit_price:
                raise ValueError(
                    f"Invalid long take-profit! TP price {take_profit_price} "
                    f"not reached (bar high: {tp_hit_bar['high']})"
                )
        else:  # short
            # Short take-profit: must hit if low <= TP price
            if tp_hit_bar['low'] > take_profit_price:
                raise ValueError(
                    f"Invalid short take-profit! TP price {take_profit_price} "
                    f"not reached (bar low: {tp_hit_bar['low']})"
                )

        return True

    @staticmethod
    def create_validation_report(
        validations_run: List[Dict]
    ) -> Dict:
        """
        Create validation report from all checks

        Args:
            validations_run: List of validation results

        Returns:
            Summary report dict
        """

        total_checks = len(validations_run)
        passed_checks = sum(1 for v in validations_run if v.get('passed', False))
        failed_checks = total_checks - passed_checks

        failures = [v for v in validations_run if not v.get('passed', False)]

        report = {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'pass_rate': passed_checks / total_checks if total_checks > 0 else 0.0,
            'failures': failures,
            'all_passed': failed_checks == 0
        }

        if failed_checks > 0:
            logger.error(
                f"Validation failed: {failed_checks}/{total_checks} checks failed"
            )
            for failure in failures:
                logger.error(f"  - {failure.get('check_name')}: {failure.get('error')}")
        else:
            logger.info(f"All {total_checks} validation checks passed")

        return report
