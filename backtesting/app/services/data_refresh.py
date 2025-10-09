"""
Automated Data Refresh Service

Runs daily to fetch latest market data from OANDA and update database.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List
import structlog

from ..config import get_settings
from ..database import db
from ..repositories import HistoricalDataRepository
from ..services import OandaHistoricalClient, DataQualityValidator
from ..models.market_data import MarketCandleSchema

logger = structlog.get_logger()


class DataRefreshService:
    """Automated service for refreshing historical data"""

    def __init__(self):
        self.settings = get_settings()
        self.oanda_client = OandaHistoricalClient()
        self.validator = DataQualityValidator()

    async def refresh_instrument_data(
        self, instrument: str, lookback_days: int = 7
    ) -> None:
        """
        Refresh data for a single instrument

        Args:
            instrument: Trading instrument to refresh
            lookback_days: Number of days to look back and refresh
        """
        logger.info(
            "Refreshing data for instrument",
            instrument=instrument,
            lookback_days=lookback_days,
        )

        # Calculate date range (refresh last N days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)

        try:
            # Fetch candles from OANDA
            candles = await self.oanda_client.fetch_candles(
                instrument=instrument,
                start_time=start_date,
                end_time=end_date,
                timeframe=self.settings.default_timeframe,
            )

            if not candles:
                logger.warning("No candles fetched from OANDA", instrument=instrument)
                return

            # Validate data quality
            quality_report = self.validator.validate_candles(
                candles, instrument, start_date, end_date, self.settings.default_timeframe
            )

            logger.info(
                "Data quality validation",
                instrument=instrument,
                quality_score=f"{quality_report.quality_score * 100:.1f}%",
                completeness=f"{quality_report.completeness_score * 100:.1f}%",
            )

            # Store in database
            async with db.get_session() as session:
                repo = HistoricalDataRepository(session)

                # Delete existing data in range (to avoid duplicates)
                deleted = await repo.delete_candles_in_range(
                    instrument,
                    start_date,
                    end_date,
                    self.settings.default_timeframe,
                )

                logger.info(f"Deleted {deleted} existing candles for refresh")

                # Store new candles
                stored = await repo.store_market_data(candles)

                logger.info(
                    "Data refresh complete",
                    instrument=instrument,
                    stored_candles=stored,
                )

        except Exception as e:
            logger.error(
                "Error refreshing data",
                instrument=instrument,
                error=str(e),
            )
            raise

    async def refresh_all_instruments(self) -> None:
        """Refresh data for all configured instruments"""
        logger.info("Starting daily data refresh for all instruments")

        instruments = self.settings.instruments

        for instrument in instruments:
            try:
                await self.refresh_instrument_data(instrument)
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(
                    "Failed to refresh instrument",
                    instrument=instrument,
                    error=str(e),
                )
                # Continue with other instruments

        logger.info("Daily data refresh complete for all instruments")

    async def backfill_historical_data(
        self, instrument: str, years: int = 2
    ) -> None:
        """
        Backfill historical data for an instrument

        Args:
            instrument: Trading instrument
            years: Number of years of historical data to fetch
        """
        logger.info(
            "Starting historical data backfill",
            instrument=instrument,
            years=years,
        )

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=years * 365)

        # Fetch data in chunks (3 months at a time to avoid timeouts)
        chunk_size_days = 90
        current_start = start_date

        total_stored = 0

        while current_start < end_date:
            chunk_end = min(current_start + timedelta(days=chunk_size_days), end_date)

            logger.info(
                "Fetching chunk",
                instrument=instrument,
                start=current_start.isoformat(),
                end=chunk_end.isoformat(),
            )

            try:
                # Fetch candles
                candles = await self.oanda_client.fetch_candles(
                    instrument=instrument,
                    start_time=current_start,
                    end_time=chunk_end,
                    timeframe=self.settings.default_timeframe,
                )

                if candles:
                    # Store in database
                    async with db.get_session() as session:
                        repo = HistoricalDataRepository(session)
                        stored = await repo.store_market_data(candles)
                        total_stored += stored

                    logger.info(
                        f"Stored {stored} candles for chunk",
                        total_stored=total_stored,
                    )

                # Move to next chunk
                current_start = chunk_end
                await asyncio.sleep(1)  # Rate limiting

            except Exception as e:
                logger.error(
                    "Error backfilling chunk",
                    instrument=instrument,
                    start=current_start.isoformat(),
                    error=str(e),
                )
                # Continue with next chunk
                current_start = chunk_end

        logger.info(
            "Historical data backfill complete",
            instrument=instrument,
            total_candles=total_stored,
        )

    async def run_daily_refresh_loop(self):
        """Run continuous daily refresh loop"""
        logger.info("Starting daily refresh loop")

        while True:
            try:
                # Run refresh
                await self.refresh_all_instruments()

                # Wait until next refresh (24 hours)
                refresh_interval = timedelta(
                    hours=self.settings.data_refresh_interval_hours
                )
                logger.info(
                    f"Sleeping until next refresh in {refresh_interval.total_seconds() / 3600:.1f} hours"
                )
                await asyncio.sleep(refresh_interval.total_seconds())

            except Exception as e:
                logger.error("Error in daily refresh loop", error=str(e))
                # Wait 1 hour and retry
                await asyncio.sleep(3600)

    async def close(self):
        """Cleanup resources"""
        await self.oanda_client.close()
