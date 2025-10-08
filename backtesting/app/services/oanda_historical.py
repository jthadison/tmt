"""
OANDA Historical Data Client

Fetches historical market data from OANDA API with rate limiting and error handling.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import httpx
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..config import get_settings
from ..models.market_data import MarketCandleSchema

logger = structlog.get_logger()


class OandaHistoricalClient:
    """Client for fetching historical market data from OANDA"""

    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.settings.oanda_api_key}",
                "Content-Type": "application/json",
                "Accept-Datetime-Format": "RFC3339",
            },
        )
        self.base_url = self.settings.oanda_api_url
        self.max_candles_per_request = self.settings.max_candles_per_request

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def fetch_candles(
        self,
        instrument: str,
        start_time: datetime,
        end_time: datetime,
        timeframe: str = "H1",
    ) -> List[MarketCandleSchema]:
        """
        Fetch historical candles from OANDA API

        Args:
            instrument: Trading instrument (e.g., "EUR_USD")
            start_time: Start of data range
            end_time: End of data range
            timeframe: Candle timeframe (e.g., "H1", "M15", "D")

        Returns:
            List of market candles
        """
        logger.info(
            "Fetching candles from OANDA",
            instrument=instrument,
            start=start_time.isoformat(),
            end=end_time.isoformat(),
            timeframe=timeframe,
        )

        # OANDA uses different granularity format
        granularity = self._convert_timeframe(timeframe)

        # OANDA has a limit on candles per request, so we may need to paginate
        all_candles = []
        current_start = start_time

        while current_start < end_time:
            # Calculate chunk end time
            chunk_end = min(
                current_start + timedelta(hours=self.max_candles_per_request),
                end_time,
            )

            # Build API request
            params = {
                "from": current_start.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                "to": chunk_end.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                "granularity": granularity,
                "price": "M",  # Mid prices
            }

            try:
                response = await self.client.get(
                    f"{self.base_url}/v3/instruments/{instrument}/candles",
                    params=params,
                )
                response.raise_for_status()

                data = response.json()
                candles_data = data.get("candles", [])

                logger.info(
                    f"Fetched {len(candles_data)} candles",
                    instrument=instrument,
                    chunk_start=current_start.isoformat(),
                    chunk_end=chunk_end.isoformat(),
                )

                # Convert to our schema
                for candle_data in candles_data:
                    if candle_data.get("complete", False):
                        candle = self._parse_candle(
                            candle_data, instrument, timeframe
                        )
                        all_candles.append(candle)

                # Rate limiting - avoid hitting OANDA rate limits
                await asyncio.sleep(0.1)

                # Move to next chunk
                current_start = chunk_end

            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP error fetching candles",
                    status_code=e.response.status_code,
                    error=str(e),
                )
                raise
            except Exception as e:
                logger.error("Error fetching candles", error=str(e))
                raise

        logger.info(
            f"Total candles fetched: {len(all_candles)}",
            instrument=instrument,
            timeframe=timeframe,
        )

        return all_candles

    def _parse_candle(
        self, candle_data: dict, instrument: str, timeframe: str
    ) -> MarketCandleSchema:
        """Parse OANDA candle data to our schema"""
        mid = candle_data["mid"]

        return MarketCandleSchema(
            timestamp=datetime.fromisoformat(
                candle_data["time"].replace("Z", "+00:00")
            ),
            instrument=instrument,
            timeframe=timeframe,
            open=float(mid["o"]),
            high=float(mid["h"]),
            low=float(mid["l"]),
            close=float(mid["c"]),
            volume=int(candle_data.get("volume", 0)),
            complete=candle_data.get("complete", True),
        )

    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert our timeframe format to OANDA granularity"""
        mapping = {
            "M1": "M1",
            "M5": "M5",
            "M15": "M15",
            "M30": "M30",
            "H1": "H1",
            "H4": "H4",
            "D": "D",
            "W": "W",
            "M": "M",
        }

        return mapping.get(timeframe, "H1")

    async def fetch_instruments(self) -> List[str]:
        """Fetch available instruments from OANDA"""
        try:
            # Use first account ID to get instruments
            account_id = self.settings.oanda_account_ids.split(",")[0]

            response = await self.client.get(
                f"{self.base_url}/v3/accounts/{account_id}/instruments"
            )
            response.raise_for_status()

            data = response.json()
            instruments = [inst["name"] for inst in data.get("instruments", [])]

            logger.info(f"Found {len(instruments)} available instruments")
            return instruments

        except Exception as e:
            logger.error("Error fetching instruments", error=str(e))
            raise
