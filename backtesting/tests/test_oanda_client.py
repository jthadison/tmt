"""
Tests for OANDA Historical Client
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.oanda_historical import OandaHistoricalClient
from app.models.market_data import MarketCandleSchema


class TestOandaHistoricalClient:
    """Test OANDA historical data client"""

    @pytest.fixture
    def mock_oanda_response(self):
        """Mock OANDA API response"""
        return {
            "instrument": "EUR_USD",
            "granularity": "H1",
            "candles": [
                {
                    "time": "2024-01-01T00:00:00.000000000Z",
                    "volume": 1000,
                    "complete": True,
                    "mid": {
                        "o": "1.1000",
                        "h": "1.1010",
                        "l": "1.0990",
                        "c": "1.1005",
                    },
                },
                {
                    "time": "2024-01-01T01:00:00.000000000Z",
                    "volume": 1100,
                    "complete": True,
                    "mid": {
                        "o": "1.1005",
                        "h": "1.1015",
                        "l": "1.0995",
                        "c": "1.1010",
                    },
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_fetch_candles_success(self, mock_oanda_response):
        """Test successful candle fetch"""
        client = OandaHistoricalClient()

        # Mock HTTP client
        with patch.object(
            client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_oanda_response
            mock_get.return_value = mock_response

            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 1, 2, 0, 0)

            candles = await client.fetch_candles("EUR_USD", start, end, "H1")

            assert len(candles) == 2
            assert isinstance(candles[0], MarketCandleSchema)
            assert candles[0].instrument == "EUR_USD"
            assert candles[0].open == 1.1000
            assert candles[0].close == 1.1005

        await client.close()

    @pytest.mark.asyncio
    async def test_fetch_candles_empty_response(self):
        """Test handling empty response"""
        client = OandaHistoricalClient()

        with patch.object(
            client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"candles": []}
            mock_get.return_value = mock_response

            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 1, 2, 0, 0)

            candles = await client.fetch_candles("EUR_USD", start, end, "H1")

            assert len(candles) == 0

        await client.close()

    @pytest.mark.asyncio
    async def test_fetch_candles_http_error(self):
        """Test handling HTTP errors with retry"""
        from tenacity import RetryError

        client = OandaHistoricalClient()

        with patch.object(
            client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_get.return_value = mock_response

            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 1, 2, 0, 0)

            # The retry decorator will wrap the HTTPStatusError in RetryError after 3 attempts
            with pytest.raises((httpx.HTTPStatusError, RetryError)):
                await client.fetch_candles("EUR_USD", start, end, "H1")

        await client.close()

    def test_parse_candle(self):
        """Test candle parsing"""
        client = OandaHistoricalClient()

        candle_data = {
            "time": "2024-01-01T00:00:00.000000000Z",
            "volume": 1000,
            "complete": True,
            "mid": {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"},
        }

        candle = client._parse_candle(candle_data, "EUR_USD", "H1")

        assert candle.instrument == "EUR_USD"
        assert candle.timeframe == "H1"
        assert candle.open == 1.1000
        assert candle.high == 1.1010
        assert candle.low == 1.0990
        assert candle.close == 1.1005
        assert candle.volume == 1000
        assert candle.complete == True

    def test_convert_timeframe(self):
        """Test timeframe conversion"""
        client = OandaHistoricalClient()

        assert client._convert_timeframe("M1") == "M1"
        assert client._convert_timeframe("M15") == "M15"
        assert client._convert_timeframe("H1") == "H1"
        assert client._convert_timeframe("H4") == "H4"
        assert client._convert_timeframe("D") == "D"
        assert client._convert_timeframe("INVALID") == "H1"  # Default

    @pytest.mark.asyncio
    async def test_fetch_instruments(self):
        """Test fetching available instruments"""
        client = OandaHistoricalClient()

        mock_response_data = {
            "instruments": [
                {"name": "EUR_USD", "type": "CURRENCY"},
                {"name": "GBP_USD", "type": "CURRENCY"},
                {"name": "USD_JPY", "type": "CURRENCY"},
            ]
        }

        with patch.object(
            client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            instruments = await client.fetch_instruments()

            assert len(instruments) == 3
            assert "EUR_USD" in instruments
            assert "GBP_USD" in instruments
            assert "USD_JPY" in instruments

        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_oanda_response):
        """Test that rate limiting delays are applied"""
        client = OandaHistoricalClient()

        with patch.object(
            client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_oanda_response
            mock_get.return_value = mock_response

            # Fetch multiple chunks
            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 10)  # Multiple days

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                candles = await client.fetch_candles("EUR_USD", start, end, "H1")

                # Should have called sleep for rate limiting
                assert mock_sleep.call_count > 0

        await client.close()
