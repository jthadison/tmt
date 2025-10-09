"""
Unit tests for CurrencyConverter

Tests currency conversion logic with mocked OANDA client.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from position_sizing.currency_converter import CurrencyConverter


class TestCurrencyConverter:
    """Test suite for CurrencyConverter"""

    @pytest.fixture
    def mock_oanda_client(self):
        """Create mock OANDA client"""
        client = AsyncMock()

        # Mock price responses
        async def mock_get_current_price(instrument):
            price_map = {
                "USD_EUR": {"bid": 0.92, "ask": 0.93, "mid": 0.925},
                "EUR_USD": {"bid": 1.08, "ask": 1.09, "mid": 1.085},
                "USD_JPY": {"bid": 149.45, "ask": 149.55, "mid": 149.50},
                "JPY_USD": {"bid": 0.0066, "ask": 0.0067, "mid": 0.00665},
            }

            if instrument in price_map:
                return price_map[instrument]
            else:
                raise Exception(f"Instrument {instrument} not found")

        client.get_current_price = mock_get_current_price

        return client

    @pytest.fixture
    def converter(self, mock_oanda_client):
        """Create currency converter with mock client"""
        return CurrencyConverter(
            oanda_client=mock_oanda_client,
            cache_ttl_minutes=5
        )

    @pytest.mark.asyncio
    async def test_no_conversion_needed_same_currency(self, converter):
        """Test no conversion when quote currency = account currency"""
        result = await converter.convert_pip_value_to_account_currency(
            instrument="EUR_USD",
            pip_value_quote=Decimal("1.0"),
            account_currency="USD"
        )

        # Should return pip_value unchanged
        assert result == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_conversion_eur_usd_to_eur_account(self, converter):
        """Test converting EUR_USD pip value for EUR account"""
        # EUR_USD quote currency = USD, account = EUR
        # Need to convert USD to EUR
        result = await converter.convert_pip_value_to_account_currency(
            instrument="EUR_USD",
            pip_value_quote=Decimal("1.0"),  # 1 USD
            account_currency="EUR"
        )

        # 1 USD * 0.925 (USD_EUR rate) = 0.925 EUR
        assert result == Decimal("0.925")

    @pytest.mark.asyncio
    async def test_extract_quote_currency(self, converter):
        """Test extracting quote currency from instrument"""
        assert converter._extract_quote_currency("EUR_USD") == "USD"
        assert converter._extract_quote_currency("USD_JPY") == "JPY"
        assert converter._extract_quote_currency("GBP_USD") == "USD"
        assert converter._extract_quote_currency("XAU_USD") == "USD"

    @pytest.mark.asyncio
    async def test_extract_base_currency(self, converter):
        """Test extracting base currency from instrument"""
        assert converter._extract_base_currency("EUR_USD") == "EUR"
        assert converter._extract_base_currency("USD_JPY") == "USD"
        assert converter._extract_base_currency("GBP_USD") == "GBP"

    @pytest.mark.asyncio
    async def test_get_exchange_rate_direct_pair(self, converter):
        """Test getting exchange rate for direct pair"""
        rate = await converter._get_exchange_rate("USD", "EUR")

        assert rate == Decimal("0.925")

    @pytest.mark.asyncio
    async def test_get_exchange_rate_inverse_pair(self, converter):
        """Test getting exchange rate using inverse pair"""
        # USD_JPY exists, so JPY_USD should use inverse
        rate = await converter._get_exchange_rate("JPY", "USD")

        # Should be inverse of USD_JPY (1 / 149.50)
        expected = Decimal("1") / Decimal("149.50")
        assert abs(rate - expected) < Decimal("0.0001")

    @pytest.mark.asyncio
    async def test_cache_functionality(self, converter):
        """Test that exchange rates are cached"""
        # First call
        rate1 = await converter._get_exchange_rate("USD", "EUR")

        # Second call should hit cache
        rate2 = await converter._get_exchange_rate("USD", "EUR")

        assert rate1 == rate2

        # Check cache stats
        stats = converter.get_cache_stats()
        assert stats["total_entries"] >= 1
        assert stats["valid_entries"] >= 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, converter):
        """Test clearing the cache"""
        # Add entry to cache
        await converter._get_exchange_rate("USD", "EUR")

        # Clear cache
        converter.clear_cache()

        # Cache should be empty
        stats = converter.get_cache_stats()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_get_current_exchange_rate_public_method(self, converter):
        """Test public method for getting exchange rate"""
        rate = await converter.get_current_exchange_rate("USD", "EUR")

        assert rate == Decimal("0.925")

    @pytest.mark.asyncio
    async def test_cache_stats(self, converter):
        """Test cache statistics"""
        # Add some entries
        await converter._get_exchange_rate("USD", "EUR")
        await converter._get_exchange_rate("EUR", "USD")

        stats = converter.get_cache_stats()

        assert "total_entries" in stats
        assert "valid_entries" in stats
        assert "stale_entries" in stats
        assert "cache_ttl_minutes" in stats
        assert stats["cache_ttl_minutes"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
