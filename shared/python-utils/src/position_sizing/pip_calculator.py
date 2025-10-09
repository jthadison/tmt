"""
Pip Value Calculator

Provides accurate pip value calculation for all instrument types
including forex, JPY pairs, metals, and cryptocurrencies.
"""

import logging
from decimal import Decimal
from typing import Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PipInfo:
    """
    Information about pip value and precision for an instrument

    Attributes:
        pip_value: The pip value in base currency (e.g., 0.0001 for EUR_USD)
        precision: Number of decimal places for the instrument
        point_value: The minimum price movement (for pipettes)
        pip_position: Which decimal position represents a pip (4 or 2)
    """
    pip_value: Decimal
    precision: int
    point_value: Decimal
    pip_position: int


class PipCalculator:
    """
    Calculate accurate pip values for all instrument types

    Handles:
    - Standard forex pairs (EUR_USD, GBP_USD, etc.): 0.0001
    - JPY pairs (USD_JPY, EUR_JPY, etc.): 0.01
    - Gold/metals (XAU_USD, XAG_USD): instrument-specific
    - Cryptocurrencies (BTC_USD, ETH_USD): instrument-specific
    - Fractional pips (pipettes)
    """

    # Instrument type patterns and their pip configurations
    JPY_PAIRS = ["JPY"]
    GOLD_SYMBOLS = ["XAU", "GOLD"]
    SILVER_SYMBOLS = ["XAG", "SILVER"]
    PLATINUM_SYMBOLS = ["XPT", "PLATINUM"]
    PALLADIUM_SYMBOLS = ["XPD", "PALLADIUM"]
    CRYPTO_SYMBOLS = ["BTC", "ETH", "LTC", "BCH", "XRP"]

    def __init__(self):
        """Initialize pip calculator"""
        logger.info("PipCalculator initialized")

    def get_pip_info(self, instrument: str) -> PipInfo:
        """
        Get pip information for an instrument

        Args:
            instrument: Instrument symbol (e.g., "EUR_USD", "USD_JPY", "XAU_USD")

        Returns:
            PipInfo: Pip value and precision information

        Examples:
            >>> calc = PipCalculator()
            >>> info = calc.get_pip_info("EUR_USD")
            >>> info.pip_value
            Decimal('0.0001')
            >>> info.precision
            5
        """
        instrument_upper = instrument.upper()

        # Check for JPY pairs (pip = 0.01)
        if self._is_jpy_pair(instrument_upper):
            return PipInfo(
                pip_value=Decimal("0.01"),
                precision=3,
                point_value=Decimal("0.001"),  # Pipette
                pip_position=2
            )

        # Check for gold (XAU_USD)
        if self._is_gold(instrument_upper):
            return PipInfo(
                pip_value=Decimal("0.01"),
                precision=2,
                point_value=Decimal("0.01"),
                pip_position=2
            )

        # Check for silver (XAG_USD)
        if self._is_silver(instrument_upper):
            return PipInfo(
                pip_value=Decimal("0.001"),
                precision=3,
                point_value=Decimal("0.001"),
                pip_position=3
            )

        # Check for other precious metals
        if self._is_platinum(instrument_upper):
            return PipInfo(
                pip_value=Decimal("0.01"),
                precision=2,
                point_value=Decimal("0.01"),
                pip_position=2
            )

        if self._is_palladium(instrument_upper):
            return PipInfo(
                pip_value=Decimal("0.01"),
                precision=2,
                point_value=Decimal("0.01"),
                pip_position=2
            )

        # Check for cryptocurrencies
        if self._is_crypto(instrument_upper):
            return self._get_crypto_pip_info(instrument_upper)

        # Standard forex pairs (EUR_USD, GBP_USD, etc.)
        return PipInfo(
            pip_value=Decimal("0.0001"),
            precision=5,
            point_value=Decimal("0.00001"),  # Pipette
            pip_position=4
        )

    def calculate_stop_distance_pips(
        self,
        instrument: str,
        entry_price: Decimal,
        stop_loss: Decimal
    ) -> Decimal:
        """
        Calculate stop loss distance in pips

        Args:
            instrument: Instrument symbol
            entry_price: Entry price level
            stop_loss: Stop loss price level

        Returns:
            Stop distance in pips (always positive)

        Examples:
            >>> calc = PipCalculator()
            >>> calc.calculate_stop_distance_pips("EUR_USD", Decimal("1.0850"), Decimal("1.0800"))
            Decimal('50')
        """
        pip_info = self.get_pip_info(instrument)
        price_distance = abs(entry_price - stop_loss)
        pips = price_distance / pip_info.pip_value

        logger.debug(
            f"Stop distance for {instrument}: {pips:.1f} pips "
            f"({entry_price} -> {stop_loss})"
        )

        return pips

    def calculate_pip_value_in_quote_currency(
        self,
        instrument: str,
        units: int
    ) -> Decimal:
        """
        Calculate pip value in quote currency for given position size

        For EUR_USD with 10,000 units:
        - 1 pip (0.0001) movement = 10,000 * 0.0001 = $1 USD

        Args:
            instrument: Instrument symbol
            units: Position size in units

        Returns:
            Pip value in quote currency per pip movement

        Examples:
            >>> calc = PipCalculator()
            >>> calc.calculate_pip_value_in_quote_currency("EUR_USD", 10000)
            Decimal('1.0')
        """
        pip_info = self.get_pip_info(instrument)
        pip_value_quote = abs(units) * pip_info.pip_value

        return pip_value_quote

    def _is_jpy_pair(self, instrument: str) -> bool:
        """Check if instrument is a JPY pair"""
        return any(symbol in instrument for symbol in self.JPY_PAIRS)

    def _is_gold(self, instrument: str) -> bool:
        """Check if instrument is gold"""
        return any(symbol in instrument for symbol in self.GOLD_SYMBOLS)

    def _is_silver(self, instrument: str) -> bool:
        """Check if instrument is silver"""
        return any(symbol in instrument for symbol in self.SILVER_SYMBOLS)

    def _is_platinum(self, instrument: str) -> bool:
        """Check if instrument is platinum"""
        return any(symbol in instrument for symbol in self.PLATINUM_SYMBOLS)

    def _is_palladium(self, instrument: str) -> bool:
        """Check if instrument is palladium"""
        return any(symbol in instrument for symbol in self.PALLADIUM_SYMBOLS)

    def _is_crypto(self, instrument: str) -> bool:
        """Check if instrument is cryptocurrency"""
        return any(symbol in instrument for symbol in self.CRYPTO_SYMBOLS)

    def _get_crypto_pip_info(self, instrument: str) -> PipInfo:
        """Get pip info for cryptocurrency instruments"""
        if "BTC" in instrument:
            # Bitcoin: pip = 1.0
            return PipInfo(
                pip_value=Decimal("1.0"),
                precision=1,
                point_value=Decimal("1.0"),
                pip_position=1
            )
        elif "ETH" in instrument:
            # Ethereum: pip = 0.01
            return PipInfo(
                pip_value=Decimal("0.01"),
                precision=2,
                point_value=Decimal("0.01"),
                pip_position=2
            )
        elif "LTC" in instrument or "BCH" in instrument:
            # Litecoin/Bitcoin Cash: pip = 0.01
            return PipInfo(
                pip_value=Decimal("0.01"),
                precision=2,
                point_value=Decimal("0.01"),
                pip_position=2
            )
        elif "XRP" in instrument:
            # Ripple: pip = 0.0001
            return PipInfo(
                pip_value=Decimal("0.0001"),
                precision=4,
                point_value=Decimal("0.0001"),
                pip_position=4
            )
        else:
            # Default crypto: pip = 0.01
            return PipInfo(
                pip_value=Decimal("0.01"),
                precision=2,
                point_value=Decimal("0.01"),
                pip_position=2
            )

    def get_instrument_type(self, instrument: str) -> str:
        """
        Get human-readable instrument type

        Args:
            instrument: Instrument symbol

        Returns:
            Instrument type ("forex", "jpy_pair", "gold", "silver", "crypto", etc.)
        """
        instrument_upper = instrument.upper()

        if self._is_jpy_pair(instrument_upper):
            return "jpy_pair"
        elif self._is_gold(instrument_upper):
            return "gold"
        elif self._is_silver(instrument_upper):
            return "silver"
        elif self._is_platinum(instrument_upper):
            return "platinum"
        elif self._is_palladium(instrument_upper):
            return "palladium"
        elif self._is_crypto(instrument_upper):
            return "crypto"
        else:
            return "forex"
