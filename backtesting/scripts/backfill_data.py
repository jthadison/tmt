"""
Historical Data Backfill Script

Script to backfill historical market data from OANDA.
Usage: python backfill_data.py [--months 3] [--instruments EUR_USD,GBP_USD]
"""

import asyncio
import argparse
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import db
from app.services.data_refresh import DataRefreshService
from app.config import get_settings
import structlog

logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()


async def main():
    """Main backfill function"""
    parser = argparse.ArgumentParser(description="Backfill historical market data")
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Number of months of historical data to fetch (default: 3)",
    )
    parser.add_argument(
        "--instruments",
        type=str,
        default=None,
        help="Comma-separated list of instruments (default: all configured)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force backfill even if data exists",
    )

    args = parser.parse_args()

    settings = get_settings()

    # Determine which instruments to backfill
    if args.instruments:
        instruments = [i.strip() for i in args.instruments.split(",")]
    else:
        instruments = settings.instruments

    logger.info(
        "Starting historical data backfill",
        instruments=instruments,
        months=args.months,
    )

    # Connect to database
    await db.connect()
    await db.create_tables()

    # Enable TimescaleDB if PostgreSQL
    if "postgresql" in settings.database_url:
        try:
            await db.enable_timescaledb()
        except Exception as e:
            logger.warning("Could not enable TimescaleDB", error=str(e))

    # Create refresh service
    refresh_service = DataRefreshService()

    try:
        # Backfill each instrument
        for instrument in instruments:
            logger.info(f"Backfilling {instrument}...")

            # Convert months to years (fractional)
            years = args.months / 12.0

            await refresh_service.backfill_historical_data(
                instrument=instrument,
                years=years,
            )

            logger.info(f"✓ Completed backfill for {instrument}")

        logger.info("✓ All backfills complete!")

    except Exception as e:
        logger.error("Backfill failed", error=str(e))
        raise

    finally:
        await refresh_service.close()
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
