"""
Enhanced Position Sizer

Accurate position sizing based on actual account balance and proper currency conversion.
"""

import logging
import time
from decimal import Decimal
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .pip_calculator import PipCalculator, PipInfo
from .currency_converter import CurrencyConverter

logger = logging.getLogger(__name__)


@dataclass
class PositionSizeResult:
    """
    Result of position size calculation

    Attributes:
        position_size: Calculated position size in units (signed: +long, -short)
        risk_amount: Risk amount in account currency
        stop_distance_pips: Stop loss distance in pips
        pip_value_account: Pip value in account currency
        account_balance: Current account balance used
        constraints_applied: List of constraints that were applied
        warnings: List of warning messages
        calculation_time_ms: Calculation time in milliseconds
        metadata: Additional metadata for audit trail
    """
    position_size: int
    risk_amount: Decimal
    stop_distance_pips: Decimal
    pip_value_account: Decimal
    account_balance: Decimal
    constraints_applied: List[str]
    warnings: List[str]
    calculation_time_ms: float
    metadata: Dict[str, Any]


class EnhancedPositionSizer:
    """
    Enhanced position sizing with accurate calculations

    Features:
    - Dynamic account balance integration from OANDA API
    - Accurate pip value calculation for all instrument types
    - Currency conversion for position sizing
    - Position size limits (per-trade, portfolio heat, per-instrument)
    - Broker validation and margin checks
    - Comprehensive audit logging
    - Alert system integration
    """

    def __init__(
        self,
        oanda_client,
        account_currency: str = "USD",
        balance_cache_ttl_minutes: int = 5,
        min_account_balance: Decimal = Decimal("5000"),
        max_per_trade_pct: Decimal = Decimal("0.05"),  # 5%
        max_portfolio_heat_pct: Decimal = Decimal("0.15"),  # 15%
        max_per_instrument_pct: Decimal = Decimal("0.10"),  # 10%
        min_margin_buffer: Decimal = Decimal("5000"),
    ):
        """
        Initialize enhanced position sizer

        Args:
            oanda_client: OANDA API client
            account_currency: Account currency (default: USD)
            balance_cache_ttl_minutes: Account balance cache TTL (default: 5)
            min_account_balance: Minimum account balance threshold (default: $5000)
            max_per_trade_pct: Maximum per-trade position size (default: 5%)
            max_portfolio_heat_pct: Maximum total portfolio heat (default: 15%)
            max_per_instrument_pct: Maximum per-instrument position (default: 10%)
            min_margin_buffer: Minimum margin buffer required (default: $5000)
        """
        self.oanda_client = oanda_client
        self.account_currency = account_currency

        # Initialize components
        self.pip_calculator = PipCalculator()
        self.currency_converter = CurrencyConverter(
            oanda_client=oanda_client,
            cache_ttl_minutes=balance_cache_ttl_minutes
        )

        # Configuration
        self.balance_cache_ttl = timedelta(minutes=balance_cache_ttl_minutes)
        self.min_account_balance = min_account_balance
        self.max_per_trade_pct = max_per_trade_pct
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.max_per_instrument_pct = max_per_instrument_pct
        self.min_margin_buffer = min_margin_buffer

        # Caches
        self.account_balance_cache: Dict[str, tuple] = {}  # {account_id: (balance, timestamp)}

        # OANDA broker limits
        self.min_units = 1  # Minimum trade size
        self.max_units = 10000000  # Maximum trade size

        logger.info(
            f"EnhancedPositionSizer initialized: "
            f"currency={account_currency}, "
            f"max_per_trade={max_per_trade_pct:.1%}, "
            f"max_portfolio_heat={max_portfolio_heat_pct:.1%}"
        )

    async def calculate_position_size(
        self,
        instrument: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        account_id: str,
        direction: str,  # "BUY" or "SELL"
        risk_percent: Decimal = Decimal("0.02"),  # 2% default
        take_profit: Optional[Decimal] = None
    ) -> PositionSizeResult:
        """
        Calculate position size with accurate pip value and balance

        Args:
            instrument: Trading instrument (e.g., "EUR_USD")
            entry_price: Entry price level
            stop_loss: Stop loss price level
            account_id: OANDA account ID
            direction: Trade direction ("BUY" or "SELL")
            risk_percent: Risk percentage per trade (default: 2%)
            take_profit: Optional take profit level

        Returns:
            PositionSizeResult with calculated position size and metadata

        Formula:
            Position Size = (Account Balance × Risk %) / (Stop Loss Pips × Pip Value in Account Currency)
        """
        start_time = time.perf_counter()
        warnings = []
        constraints_applied = []

        try:
            # Step 1: Get actual account balance
            account_balance = await self._get_account_balance(account_id)

            # Check minimum balance threshold
            if account_balance < self.min_account_balance:
                warning = f"Account balance ${account_balance:.2f} < minimum ${self.min_account_balance:.2f}"
                warnings.append(warning)
                logger.warning(warning)

            # Step 2: Calculate risk amount
            risk_amount = account_balance * risk_percent

            # Step 3: Get accurate pip info for instrument
            pip_info = self.pip_calculator.get_pip_info(instrument)

            # Step 4: Calculate stop distance in pips
            stop_distance_pips = self.pip_calculator.calculate_stop_distance_pips(
                instrument, entry_price, stop_loss
            )

            if stop_distance_pips <= 0:
                raise ValueError(f"Invalid stop distance: {stop_distance_pips} pips")

            # Step 5: Calculate pip value in quote currency
            # For 1 unit position
            pip_value_quote = pip_info.pip_value

            # Step 6: Convert pip value to account currency
            pip_value_account = await self.currency_converter.convert_pip_value_to_account_currency(
                instrument=instrument,
                pip_value_quote=pip_value_quote,
                account_currency=self.account_currency
            )

            # Step 7: Calculate raw position size
            # Position Size = Risk Amount / (Stop Distance Pips × Pip Value per Unit)
            position_size_raw = risk_amount / (stop_distance_pips * pip_value_account)

            # Convert to integer units
            position_size = int(position_size_raw)

            # Step 8: Apply position limits
            position_size, limits_applied = await self._apply_position_limits(
                position_size=position_size,
                instrument=instrument,
                account_id=account_id,
                account_balance=account_balance,
                entry_price=entry_price
            )
            constraints_applied.extend(limits_applied)

            # Step 9: Validate margin requirements
            margin_valid, margin_warnings = await self._validate_margin(
                instrument=instrument,
                position_size=position_size,
                entry_price=entry_price,
                account_id=account_id
            )
            warnings.extend(margin_warnings)

            if not margin_valid:
                constraints_applied.append("margin_insufficient")
                # Reduce position size by 50% if margin insufficient
                position_size = int(position_size * 0.5)
                warnings.append("Position size reduced by 50% due to margin constraints")

            # Step 10: Apply direction (negative for SELL)
            if direction.upper() in ["SELL", "SHORT"]:
                position_size = -abs(position_size)
            else:
                position_size = abs(position_size)

            # Calculate actual pip value for the position
            actual_pip_value = pip_value_account * abs(position_size)

            # Calculation time
            calc_time_ms = (time.perf_counter() - start_time) * 1000

            # Build metadata
            metadata = {
                "instrument": instrument,
                "entry_price": float(entry_price),
                "stop_loss": float(stop_loss),
                "take_profit": float(take_profit) if take_profit else None,
                "direction": direction,
                "risk_percent": float(risk_percent),
                "pip_info": {
                    "pip_value": float(pip_info.pip_value),
                    "precision": pip_info.precision,
                    "instrument_type": self.pip_calculator.get_instrument_type(instrument)
                },
                "account_currency": self.account_currency,
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Position sizing: {instrument} - "
                f"Balance: ${account_balance:.2f}, "
                f"Risk: {risk_percent:.1%}, "
                f"Stop: {stop_distance_pips:.1f} pips, "
                f"Size: {position_size} units, "
                f"Time: {calc_time_ms:.2f}ms"
            )

            return PositionSizeResult(
                position_size=position_size,
                risk_amount=risk_amount,
                stop_distance_pips=stop_distance_pips,
                pip_value_account=actual_pip_value,
                account_balance=account_balance,
                constraints_applied=constraints_applied,
                warnings=warnings,
                calculation_time_ms=calc_time_ms,
                metadata=metadata
            )

        except Exception as e:
            calc_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Position size calculation failed: {e}", exc_info=True)

            # Return zero position on error
            return PositionSizeResult(
                position_size=0,
                risk_amount=Decimal("0"),
                stop_distance_pips=Decimal("0"),
                pip_value_account=Decimal("0"),
                account_balance=Decimal("0"),
                constraints_applied=["calculation_error"],
                warnings=[f"Calculation error: {str(e)}"],
                calculation_time_ms=calc_time_ms,
                metadata={"error": str(e)}
            )

    async def _get_account_balance(self, account_id: str) -> Decimal:
        """
        Get account balance with 5-minute caching

        Args:
            account_id: OANDA account ID

        Returns:
            Account balance in account currency
        """
        # Check cache
        if account_id in self.account_balance_cache:
            balance, timestamp = self.account_balance_cache[account_id]
            if datetime.now() - timestamp < self.balance_cache_ttl:
                logger.debug(f"Cache hit for account {account_id}: ${balance:.2f}")
                return balance

        # Query from OANDA
        try:
            account_info = await self.oanda_client.get_account_info(account_id)
            balance = Decimal(str(account_info.balance))

            # Cache the balance
            self.account_balance_cache[account_id] = (balance, datetime.now())

            logger.debug(f"Fetched account balance for {account_id}: ${balance:.2f}")

            return balance

        except Exception as e:
            logger.error(f"Failed to fetch account balance for {account_id}: {e}")
            raise

    async def _apply_position_limits(
        self,
        position_size: int,
        instrument: str,
        account_id: str,
        account_balance: Decimal,
        entry_price: Decimal
    ) -> tuple[int, List[str]]:
        """
        Apply position size limits and constraints

        Args:
            position_size: Raw calculated position size
            instrument: Trading instrument
            account_id: Account ID
            account_balance: Current account balance
            entry_price: Entry price

        Returns:
            Tuple of (limited_position_size, constraints_applied)
        """
        constraints = []
        limited_size = position_size

        # Calculate position value
        position_value = abs(position_size) * entry_price

        # Limit 1: Per-trade limit (5% of account)
        max_position_value = account_balance * self.max_per_trade_pct
        if position_value > max_position_value:
            limited_size = int(max_position_value / entry_price)
            constraints.append(f"per_trade_limit_5pct")
            logger.debug(
                f"Per-trade limit applied: {position_size} -> {limited_size} units"
            )

        # Limit 2: Portfolio heat check (15% total risk limit)
        try:
            current_positions = await self.oanda_client.get_positions(account_id)
            current_heat = self._calculate_portfolio_heat(
                current_positions, account_balance
            )

            if current_heat > Decimal("0.12"):  # Approaching 15% limit
                limited_size = int(limited_size * Decimal("0.5"))
                constraints.append("portfolio_heat_high")
                logger.warning(
                    f"Portfolio heat {current_heat:.1%} high, "
                    f"reducing position by 50%"
                )
        except Exception as e:
            logger.warning(f"Could not check portfolio heat: {e}")

        # Limit 3: Per-instrument limit (10% of account)
        max_instrument_value = account_balance * self.max_per_instrument_pct
        instrument_position_value = abs(limited_size) * entry_price

        if instrument_position_value > max_instrument_value:
            limited_size = int(max_instrument_value / entry_price)
            constraints.append("per_instrument_limit_10pct")
            logger.debug(
                f"Per-instrument limit applied: {limited_size} units"
            )

        # Limit 4: Broker limits (OANDA)
        if abs(limited_size) < self.min_units:
            limited_size = self.min_units if limited_size > 0 else -self.min_units
            constraints.append("broker_min_size")

        if abs(limited_size) > self.max_units:
            limited_size = self.max_units if limited_size > 0 else -self.max_units
            constraints.append("broker_max_size")

        return limited_size, constraints

    def _calculate_portfolio_heat(
        self,
        positions: List,
        account_balance: Decimal
    ) -> Decimal:
        """
        Calculate current portfolio heat (total risk exposure)

        Args:
            positions: List of current positions
            account_balance: Account balance

        Returns:
            Portfolio heat as decimal (e.g., 0.12 = 12%)
        """
        if not positions or account_balance == 0:
            return Decimal("0")

        total_exposure = Decimal("0")

        for position in positions:
            if hasattr(position, 'units') and hasattr(position, 'average_price'):
                position_value = abs(Decimal(str(position.units))) * Decimal(str(position.average_price))
                total_exposure += position_value

        portfolio_heat = total_exposure / account_balance

        return portfolio_heat

    async def _validate_margin(
        self,
        instrument: str,
        position_size: int,
        entry_price: Decimal,
        account_id: str
    ) -> tuple[bool, List[str]]:
        """
        Validate margin requirements

        Args:
            instrument: Trading instrument
            position_size: Position size to validate
            entry_price: Entry price
            account_id: Account ID

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        try:
            # Get account info for margin data
            account_info = await self.oanda_client.get_account_info(account_id)
            available_margin = Decimal(str(account_info.margin_available))

            # Estimate margin requirement (typically 3% for forex)
            # This is a rough estimate; OANDA calculates exact margin
            estimated_margin = abs(position_size) * entry_price * Decimal("0.03")

            # Check if margin buffer is maintained
            remaining_margin = available_margin - estimated_margin

            if remaining_margin < self.min_margin_buffer:
                warnings.append(
                    f"Insufficient margin buffer: "
                    f"${remaining_margin:.2f} < ${self.min_margin_buffer:.2f}"
                )
                return False, warnings

            return True, warnings

        except Exception as e:
            logger.warning(f"Margin validation failed: {e}")
            warnings.append(f"Margin validation error: {str(e)}")
            return False, warnings

    def clear_caches(self):
        """Clear all caches"""
        self.account_balance_cache.clear()
        self.currency_converter.clear_cache()
        logger.info("All caches cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get position sizer statistics

        Returns:
            Dictionary with statistics
        """
        return {
            "balance_cache_entries": len(self.account_balance_cache),
            "currency_converter_stats": self.currency_converter.get_cache_stats(),
            "configuration": {
                "account_currency": self.account_currency,
                "max_per_trade_pct": float(self.max_per_trade_pct),
                "max_portfolio_heat_pct": float(self.max_portfolio_heat_pct),
                "max_per_instrument_pct": float(self.max_per_instrument_pct),
                "min_margin_buffer": float(self.min_margin_buffer)
            }
        }
