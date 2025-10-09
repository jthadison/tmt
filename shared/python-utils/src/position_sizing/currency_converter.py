"""
Currency Converter

Handles currency conversion for position sizing calculations with caching.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """
    Convert pip values to account currency for accurate position sizing

    Features:
    - Exchange rate caching (5-minute TTL)
    - Direct conversion when quote currency = account currency
    - Cross-currency conversion support
    - OANDA API integration for real-time rates
    """

    def __init__(self, oanda_client, cache_ttl_minutes: int = 5):
        """
        Initialize currency converter

        Args:
            oanda_client: OANDA client for fetching exchange rates
            cache_ttl_minutes: Cache TTL in minutes (default: 5)
        """
        self.oanda_client = oanda_client
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.exchange_rate_cache: Dict[str, Tuple[Decimal, datetime]] = {}

        logger.info(f"CurrencyConverter initialized with {cache_ttl_minutes}min cache TTL")

    async def convert_pip_value_to_account_currency(
        self,
        instrument: str,
        pip_value_quote: Decimal,
        account_currency: str
    ) -> Decimal:
        """
        Convert pip value from quote currency to account currency

        Args:
            instrument: Trading instrument (e.g., "EUR_USD")
            pip_value_quote: Pip value in quote currency
            account_currency: Account currency (e.g., "USD")

        Returns:
            Pip value in account currency

        Examples:
            For EUR_USD with USD account:
            - Quote currency = USD
            - Account currency = USD
            - No conversion needed, return pip_value_quote

            For EUR_USD with EUR account:
            - Quote currency = USD
            - Account currency = EUR
            - Need USD/EUR conversion rate
        """
        quote_currency = self._extract_quote_currency(instrument)

        # No conversion needed if quote currency = account currency
        if quote_currency == account_currency:
            logger.debug(
                f"No conversion needed for {instrument} "
                f"(quote={quote_currency}, account={account_currency})"
            )
            return pip_value_quote

        # Get exchange rate for conversion
        exchange_rate = await self._get_exchange_rate(
            from_currency=quote_currency,
            to_currency=account_currency
        )

        converted_value = pip_value_quote * exchange_rate

        logger.debug(
            f"Converted pip value: {pip_value_quote} {quote_currency} "
            f"-> {converted_value} {account_currency} "
            f"(rate: {exchange_rate})"
        )

        return converted_value

    async def get_current_exchange_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """
        Get current exchange rate (public method)

        Args:
            from_currency: Source currency
            to_currency: Target currency

        Returns:
            Exchange rate
        """
        return await self._get_exchange_rate(from_currency, to_currency)

    async def _get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """
        Get exchange rate with caching

        Args:
            from_currency: Source currency (e.g., "USD")
            to_currency: Target currency (e.g., "EUR")

        Returns:
            Exchange rate

        Notes:
            - Uses 5-minute cache
            - Queries OANDA API for real-time rates
            - Handles inverse rates (e.g., EUR_USD vs USD_EUR)
        """
        cache_key = f"{from_currency}_{to_currency}"

        # Check cache
        if cache_key in self.exchange_rate_cache:
            rate, timestamp = self.exchange_rate_cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit for {cache_key}: {rate}")
                return rate

        # Fetch from OANDA
        rate = await self._fetch_exchange_rate_from_oanda(
            from_currency, to_currency
        )

        # Cache the rate
        self.exchange_rate_cache[cache_key] = (rate, datetime.now())

        logger.debug(f"Fetched and cached exchange rate {cache_key}: {rate}")

        return rate

    async def _fetch_exchange_rate_from_oanda(
        self,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """
        Fetch exchange rate from OANDA API

        Args:
            from_currency: Source currency
            to_currency: Target currency

        Returns:
            Exchange rate

        Raises:
            Exception: If rate cannot be fetched
        """
        # Try direct pair first (e.g., USD_EUR)
        instrument = f"{from_currency}_{to_currency}"

        try:
            price_data = await self.oanda_client.get_current_price(instrument)
            # Use mid price for conversion
            rate = Decimal(str(price_data["mid"]))
            logger.debug(f"Direct rate for {instrument}: {rate}")
            return rate

        except Exception as e:
            logger.debug(f"Direct pair {instrument} not available: {e}")

            # Try inverse pair (e.g., EUR_USD for USD_EUR conversion)
            inverse_instrument = f"{to_currency}_{from_currency}"

            try:
                price_data = await self.oanda_client.get_current_price(inverse_instrument)
                inverse_rate = Decimal(str(price_data["mid"]))

                # Convert inverse to direct rate
                if inverse_rate == 0:
                    raise ValueError(f"Invalid inverse rate: {inverse_rate}")

                rate = Decimal("1") / inverse_rate
                logger.debug(
                    f"Inverse rate for {inverse_instrument}: {inverse_rate} "
                    f"-> {rate}"
                )
                return rate

            except Exception as e2:
                logger.error(
                    f"Failed to fetch exchange rate for {from_currency}/{to_currency}: {e2}"
                )
                raise ValueError(
                    f"Cannot fetch exchange rate for {from_currency}/{to_currency}"
                )

    def _extract_quote_currency(self, instrument: str) -> str:
        """
        Extract quote currency from instrument symbol

        Args:
            instrument: Instrument symbol (e.g., "EUR_USD", "USD_JPY")

        Returns:
            Quote currency (second currency in pair)

        Examples:
            >>> converter._extract_quote_currency("EUR_USD")
            "USD"
            >>> converter._extract_quote_currency("USD_JPY")
            "JPY"
            >>> converter._extract_quote_currency("XAU_USD")
            "USD"
        """
        parts = instrument.split("_")
        if len(parts) >= 2:
            return parts[1].upper()
        else:
            # Fallback: assume USD if cannot parse
            logger.warning(f"Cannot parse instrument {instrument}, assuming USD")
            return "USD"

    def _extract_base_currency(self, instrument: str) -> str:
        """
        Extract base currency from instrument symbol

        Args:
            instrument: Instrument symbol (e.g., "EUR_USD")

        Returns:
            Base currency (first currency in pair)
        """
        parts = instrument.split("_")
        if len(parts) >= 2:
            return parts[0].upper()
        else:
            logger.warning(f"Cannot parse instrument {instrument}")
            return "EUR"

    def clear_cache(self):
        """Clear the exchange rate cache"""
        self.exchange_rate_cache.clear()
        logger.info("Exchange rate cache cleared")

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        now = datetime.now()
        valid_entries = sum(
            1 for _, timestamp in self.exchange_rate_cache.values()
            if now - timestamp < self.cache_ttl
        )

        return {
            "total_entries": len(self.exchange_rate_cache),
            "valid_entries": valid_entries,
            "stale_entries": len(self.exchange_rate_cache) - valid_entries,
            "cache_ttl_minutes": self.cache_ttl.total_seconds() / 60
        }
