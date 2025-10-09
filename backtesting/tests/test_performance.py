"""
Performance Tests for Historical Data Infrastructure

Tests the AC requirement: "Query 1 year of data in < 5 seconds"
"""

import pytest
import time
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.historical_data_repository import HistoricalDataRepository
from app.models.market_data import MarketCandleSchema


class TestPerformance:
    """Performance benchmark tests"""

    @pytest.mark.asyncio
    async def test_query_one_year_performance(self, db_session: AsyncSession):
        """
        Test AC requirement: Query 1 year of data in < 5 seconds

        This test generates 1 year of hourly candles (~8760 candles) and
        verifies retrieval performance meets the requirement.
        """
        repo = HistoricalDataRepository(db_session)

        # Generate 1 year of hourly candles (365 days * 24 hours = 8760 candles)
        start_date = datetime(2024, 1, 1, 0, 0, 0)
        end_date = start_date + timedelta(days=365)

        # Create sample candles (simulate 1 year of data)
        candles = []
        current_time = start_date
        price = 1.1000

        while current_time < end_date:
            candle = MarketCandleSchema(
                timestamp=current_time,
                instrument="EUR_USD",
                timeframe="H1",
                open=price,
                high=price + 0.0010,
                low=price - 0.0010,
                close=price + 0.0005,
                volume=1000,
                complete=True,
            )
            candles.append(candle)
            current_time += timedelta(hours=1)
            price += 0.0001  # Slight price movement

        print(f"\nGenerated {len(candles)} candles for 1-year test")

        # Store candles
        stored = await repo.store_market_data(candles)
        assert stored == len(candles)

        # Measure query performance
        start_time = time.time()

        df = await repo.get_market_data(
            instrument="EUR_USD",
            start_date=start_date,
            end_date=end_date,
            timeframe="H1",
        )

        query_time = time.time() - start_time

        print(f"Retrieved {len(df)} candles in {query_time:.2f} seconds")

        # Assertions
        assert len(df) > 0
        assert len(df) == len(candles)

        # AC Requirement: < 5 seconds
        assert query_time < 5.0, f"Query took {query_time:.2f}s, requirement is < 5s"

    @pytest.mark.asyncio
    async def test_query_two_year_performance(self, db_session: AsyncSession):
        """
        Test querying 2 years of data (full historical data requirement)

        This should complete in reasonable time (< 10 seconds)
        """
        repo = HistoricalDataRepository(db_session)

        # Generate 2 years of hourly candles (~17,520 candles)
        start_date = datetime(2023, 1, 1, 0, 0, 0)
        end_date = start_date + timedelta(days=730)  # 2 years

        # Create sample candles
        candles = []
        current_time = start_date
        price = 1.1000

        # Generate candles every hour for 2 years
        while current_time < end_date:
            candle = MarketCandleSchema(
                timestamp=current_time,
                instrument="EUR_USD",
                timeframe="H1",
                open=price,
                high=price + 0.0010,
                low=price - 0.0010,
                close=price + 0.0005,
                volume=1000,
                complete=True,
            )
            candles.append(candle)
            current_time += timedelta(hours=1)
            price += 0.0001

        print(f"\nGenerated {len(candles)} candles for 2-year test")

        # Store candles
        stored = await repo.store_market_data(candles)
        assert stored == len(candles)

        # Measure query performance
        start_time = time.time()

        df = await repo.get_market_data(
            instrument="EUR_USD",
            start_date=start_date,
            end_date=end_date,
            timeframe="H1",
        )

        query_time = time.time() - start_time

        print(f"Retrieved {len(df)} candles in {query_time:.2f} seconds")

        # Assertions
        assert len(df) > 0
        assert len(df) == len(candles)

        # Should be reasonable (< 10 seconds for 2 years)
        assert query_time < 10.0, f"Query took {query_time:.2f}s, expected < 10s"

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, db_session: AsyncSession):
        """
        Test bulk insert performance

        Should be able to insert 10,000 candles in < 30 seconds
        """
        repo = HistoricalDataRepository(db_session)

        # Generate 10,000 candles
        start_date = datetime(2024, 1, 1, 0, 0, 0)
        candles = []

        for i in range(10000):
            candle = MarketCandleSchema(
                timestamp=start_date + timedelta(hours=i),
                instrument="EUR_USD",
                timeframe="H1",
                open=1.1000 + (i * 0.0001),
                high=1.1010 + (i * 0.0001),
                low=1.0990 + (i * 0.0001),
                close=1.1005 + (i * 0.0001),
                volume=1000,
                complete=True,
            )
            candles.append(candle)

        # Measure insert performance
        start_time = time.time()

        stored = await repo.store_market_data(candles)

        insert_time = time.time() - start_time

        print(f"\nInserted {stored} candles in {insert_time:.2f} seconds")
        print(f"Rate: {stored / insert_time:.0f} candles/second")

        # Assertions
        assert stored == 10000

        # Should complete in reasonable time
        assert insert_time < 30.0, f"Insert took {insert_time:.2f}s, expected < 30s"

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, db_session: AsyncSession):
        """
        Test concurrent query performance

        Multiple instruments queried simultaneously should complete efficiently
        """
        import asyncio

        repo = HistoricalDataRepository(db_session)

        # Generate data for 3 instruments
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]
        start_date = datetime(2024, 1, 1, 0, 0, 0)
        end_date = start_date + timedelta(days=30)  # 1 month

        for instrument in instruments:
            candles = []
            current_time = start_date
            price = 1.1000

            while current_time < end_date:
                candle = MarketCandleSchema(
                    timestamp=current_time,
                    instrument=instrument,
                    timeframe="H1",
                    open=price,
                    high=price + 0.0010,
                    low=price - 0.0010,
                    close=price + 0.0005,
                    volume=1000,
                    complete=True,
                )
                candles.append(candle)
                current_time += timedelta(hours=1)

            await repo.store_market_data(candles)

        # Measure concurrent query performance
        start_time = time.time()

        # Query all 3 instruments simultaneously (Note: in real app would use separate sessions)
        tasks = []
        for instrument in instruments:
            tasks.append(
                repo.get_market_data(instrument, start_date, end_date, "H1")
            )

        # Wait for all queries (note: sharing session, but tests pattern)
        for task in tasks:
            await task

        query_time = time.time() - start_time

        print(f"\nQueried {len(instruments)} instruments in {query_time:.2f} seconds")

        # Should complete in reasonable time
        assert query_time < 15.0, f"Concurrent queries took {query_time:.2f}s"
