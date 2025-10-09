"""
Order Execution Simulator - Story 11.2

Realistic order execution simulation with:
- Market, limit, and stop order types
- Realistic slippage modeling
- Stop-loss and take-profit execution
- Order rejection logic
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from datetime import datetime
from decimal import Decimal
from enum import Enum
import logging

from .models import OrderType, Trade, TradingSession

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order execution status"""
    FILLED = "filled"
    REJECTED = "rejected"
    PENDING = "pending"
    CANCELLED = "cancelled"


class SlippageModel:
    """
    Slippage modeling for realistic order execution

    Calculates expected slippage based on:
    - Trading session volatility
    - Order size
    - Market conditions
    - Historical execution data (when available)
    """

    def __init__(
        self,
        model_type: str = "session_based",
        base_slippage_pips: float = 0.5,
        use_historical_data: bool = False
    ):
        """
        Initialize slippage model

        Args:
            model_type: 'fixed', 'session_based', 'historical'
            base_slippage_pips: Base slippage in pips
            use_historical_data: Use historical execution data if available
        """

        self.model_type = model_type
        self.base_slippage_pips = base_slippage_pips
        self.use_historical_data = use_historical_data

        # Session-based slippage multipliers
        self.session_multipliers = {
            TradingSession.SYDNEY: 0.8,      # Lower volatility
            TradingSession.TOKYO: 1.0,       # Moderate volatility
            TradingSession.LONDON: 1.2,      # Higher volatility
            TradingSession.NEW_YORK: 1.3,    # High volatility
            TradingSession.OVERLAP: 1.5,     # Highest volatility
        }

        logger.info(
            f"SlippageModel initialized: type={model_type}, "
            f"base={base_slippage_pips} pips"
        )

    def calculate_slippage(
        self,
        symbol: str,
        order_type: OrderType,
        session: TradingSession,
        volatility_atr: Optional[float] = None
    ) -> float:
        """
        Calculate slippage in pips for an order

        Args:
            symbol: Trading instrument
            order_type: Type of order
            session: Current trading session
            volatility_atr: Optional ATR for volatility-adjusted slippage

        Returns:
            Slippage in pips (always positive)
        """

        if self.model_type == "fixed":
            return self.base_slippage_pips

        if self.model_type == "session_based":
            multiplier = self.session_multipliers.get(session, 1.0)
            slippage = self.base_slippage_pips * multiplier

            # Market orders have higher slippage
            if order_type == OrderType.MARKET:
                slippage *= 1.2

            # Add small random component for realism
            random_factor = np.random.uniform(0.8, 1.2)
            slippage *= random_factor

            return round(slippage, 1)

        if self.model_type == "historical":
            # TODO: Implement historical slippage model from trade_executions table
            # For now, fall back to session-based
            logger.warning("Historical slippage model not yet implemented, using session-based")
            # Temporarily switch to session_based to avoid recursion
            old_model = self.model_type
            self.model_type = "session_based"
            result = self.calculate_slippage(symbol, order_type, session, volatility_atr)
            self.model_type = old_model
            return result

        return self.base_slippage_pips

    def apply_slippage_to_price(
        self,
        price: float,
        slippage_pips: float,
        direction: str,
        pip_value: float = 0.0001
    ) -> float:
        """
        Apply slippage to a price

        Args:
            price: Original price
            slippage_pips: Slippage in pips
            direction: 'long' or 'short'
            pip_value: Pip value for instrument (0.0001 for EUR_USD, 0.01 for JPY pairs)

        Returns:
            Price with slippage applied

        Example:
            >>> model = SlippageModel()
            >>> # Long entry: slippage makes entry worse (higher price)
            >>> entry_price = model.apply_slippage_to_price(1.0850, 1.5, 'long')
            >>> # Returns: 1.08515 (1.5 pips worse)
        """

        slippage_decimal = slippage_pips * pip_value

        if direction == 'long':
            # Long entry: slippage increases entry price (worse fill)
            # Long exit: slippage decreases exit price (worse fill)
            return price + slippage_decimal
        else:  # short
            # Short entry: slippage decreases entry price (worse fill)
            # Short exit: slippage increases exit price (worse fill)
            return price - slippage_decimal


class OrderSimulator:
    """
    Simulates order execution in backtesting

    Handles:
    - Market orders (fill at next bar open + slippage)
    - Limit orders (fill only if price reached)
    - Stop orders (fill if stop triggered)
    - Stop-loss and take-profit execution
    - Order rejection logic
    """

    def __init__(
        self,
        slippage_model: Optional[SlippageModel] = None,
        min_margin_ratio: float = 0.02  # 50:1 leverage = 2% margin
    ):
        """
        Initialize order simulator

        Args:
            slippage_model: Slippage model to use
            min_margin_ratio: Minimum margin required (0.02 = 50:1 leverage)
        """

        self.slippage_model = slippage_model or SlippageModel()
        self.min_margin_ratio = min_margin_ratio

        logger.info("OrderSimulator initialized")

    def execute_market_order(
        self,
        symbol: str,
        direction: str,
        units: float,
        next_bar: pd.Series,
        session: TradingSession,
        account_balance: float,
        pip_value: float = 0.0001
    ) -> Tuple[OrderStatus, Optional[Dict]]:
        """
        Execute market order at next bar's open

        Args:
            symbol: Trading instrument
            direction: 'long' or 'short'
            units: Position size
            next_bar: Next bar data (for fill price)
            session: Trading session
            account_balance: Current account balance
            pip_value: Pip value for instrument

        Returns:
            Tuple of (OrderStatus, execution_dict or None)

        CRITICAL: Market orders fill at NEXT bar's open, not current bar's close!
                  This prevents look-ahead bias.
        """

        # Check margin requirements
        required_margin = next_bar['open'] * units * self.min_margin_ratio

        if required_margin > account_balance:
            logger.warning(
                f"Order rejected: insufficient margin. "
                f"Required: {required_margin}, Available: {account_balance}"
            )
            return OrderStatus.REJECTED, {
                'reason': 'insufficient_margin',
                'required_margin': required_margin,
                'available_balance': account_balance
            }

        # Calculate slippage
        slippage_pips = self.slippage_model.calculate_slippage(
            symbol, OrderType.MARKET, session
        )

        # Get fill price (next bar open + slippage)
        base_price = next_bar['open']
        fill_price = self.slippage_model.apply_slippage_to_price(
            base_price, slippage_pips, direction, pip_value
        )

        execution = {
            'status': OrderStatus.FILLED,
            'fill_price': fill_price,
            'fill_time': next_bar.name,  # Timestamp of next bar
            'slippage_pips': slippage_pips,
            'requested_price': base_price,
            'units': units
        }

        logger.debug(
            f"Market order filled: {direction} {units} {symbol} @ {fill_price} "
            f"(slippage: {slippage_pips} pips)"
        )

        return OrderStatus.FILLED, execution

    def check_stop_loss_hit(
        self,
        trade_direction: str,
        stop_loss_price: float,
        current_bar: pd.Series,
        pip_value: float = 0.0001
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if stop-loss was hit during current bar

        Args:
            trade_direction: 'long' or 'short'
            stop_loss_price: Stop-loss price level
            current_bar: Current bar data
            pip_value: Pip value for instrument

        Returns:
            Tuple of (was_hit, fill_price or None)

        Logic:
            - Long: Stop-loss triggers if low <= stop_loss_price
            - Short: Stop-loss triggers if high >= stop_loss_price
            - Fill price includes slippage (stop orders usually have worse fills)
        """

        if trade_direction == 'long':
            # Long stop-loss: triggers if price drops to/below stop level
            if current_bar['low'] <= stop_loss_price:
                # Stop-loss fills at stop price (or slightly worse)
                # Assume 0.5 pip slippage on stop-loss
                slippage_pips = 0.5
                fill_price = stop_loss_price - (slippage_pips * pip_value)
                return True, fill_price

        else:  # short
            # Short stop-loss: triggers if price rises to/above stop level
            if current_bar['high'] >= stop_loss_price:
                # Stop-loss fills at stop price (or slightly worse)
                slippage_pips = 0.5
                fill_price = stop_loss_price + (slippage_pips * pip_value)
                return True, fill_price

        return False, None

    def check_take_profit_hit(
        self,
        trade_direction: str,
        take_profit_price: float,
        current_bar: pd.Series,
        pip_value: float = 0.0001
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if take-profit was hit during current bar

        Args:
            trade_direction: 'long' or 'short'
            take_profit_price: Take-profit price level
            current_bar: Current bar data
            pip_value: Pip value for instrument

        Returns:
            Tuple of (was_hit, fill_price or None)

        Logic:
            - Long: Take-profit triggers if high >= take_profit_price
            - Short: Take-profit triggers if low <= take_profit_price
            - Fill price includes minimal slippage (limit orders usually get good fills)
        """

        if trade_direction == 'long':
            # Long take-profit: triggers if price rises to/above TP level
            if current_bar['high'] >= take_profit_price:
                # Take-profit fills at TP price (or slightly better)
                # Minimal slippage on take-profit
                slippage_pips = 0.2
                fill_price = take_profit_price - (slippage_pips * pip_value)
                return True, fill_price

        else:  # short
            # Short take-profit: triggers if price drops to/below TP level
            if current_bar['low'] <= take_profit_price:
                # Take-profit fills at TP price (or slightly better)
                slippage_pips = 0.2
                fill_price = take_profit_price + (slippage_pips * pip_value)
                return True, fill_price

        return False, None

    def calculate_position_pnl(
        self,
        trade_direction: str,
        entry_price: float,
        exit_price: float,
        units: float,
        pip_value: float = 0.0001
    ) -> Tuple[float, float]:
        """
        Calculate P&L for a position

        Args:
            trade_direction: 'long' or 'short'
            entry_price: Entry price
            exit_price: Exit price
            units: Position size
            pip_value: Pip value for instrument

        Returns:
            Tuple of (pnl_dollars, pnl_pips)
        """

        if trade_direction == 'long':
            # Long: profit if exit > entry
            price_diff = exit_price - entry_price
        else:  # short
            # Short: profit if entry > exit
            price_diff = entry_price - exit_price

        pnl_dollars = price_diff * units
        pnl_pips = price_diff / pip_value

        return pnl_dollars, pnl_pips

    def calculate_risk_reward_achieved(
        self,
        trade_direction: str,
        entry_price: float,
        exit_price: float,
        stop_loss_price: float,
        pip_value: float = 0.0001
    ) -> float:
        """
        Calculate actual risk-reward ratio achieved

        Args:
            trade_direction: 'long' or 'short'
            entry_price: Entry price
            exit_price: Exit price
            stop_loss_price: Stop-loss price
            pip_value: Pip value for instrument

        Returns:
            Risk-reward ratio (reward / risk)
        """

        if trade_direction == 'long':
            reward_pips = (exit_price - entry_price) / pip_value
            risk_pips = (entry_price - stop_loss_price) / pip_value
        else:  # short
            reward_pips = (entry_price - exit_price) / pip_value
            risk_pips = (stop_loss_price - entry_price) / pip_value

        if risk_pips <= 0:
            return 0.0

        return reward_pips / risk_pips

    def get_pip_value(self, symbol: str) -> float:
        """
        Get pip value for an instrument

        Args:
            symbol: Trading instrument

        Returns:
            Pip value (0.0001 for most pairs, 0.01 for JPY pairs)
        """

        # JPY pairs use 0.01 as pip value
        if 'JPY' in symbol:
            return 0.01

        # Most other pairs use 0.0001
        return 0.0001
