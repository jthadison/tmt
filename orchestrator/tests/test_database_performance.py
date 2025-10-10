"""
Performance tests for database operations.

Tests write latency and query performance under load.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import statistics

from app.database import (
    initialize_database,
    TradeRepository,
)


@pytest.fixture
async def test_db_engine():
    """Create test database with performance configuration"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_performance.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    engine = await initialize_database(database_url=db_url)
    yield engine

    await engine.close()
    if db_path.exists():
        db_path.unlink()
    Path(temp_dir).rmdir()


@pytest.fixture
async def trade_repo(test_db_engine):
    """Create TradeRepository instance"""
    return TradeRepository(test_db_engine.session_factory)


def generate_trade_data(trade_id: str) -> dict:
    """Generate sample trade data for performance testing"""
    return {
        "trade_id": trade_id,
        "account_id": "PERF_ACC_001",
        "symbol": "EUR_USD",
        "direction": "BUY",
        "entry_time": datetime.now(timezone.utc),
        "entry_price": Decimal("1.09500"),
        "position_size": Decimal("10000"),
        "session": "LONDON",
        "pattern_type": "WYCKOFF",
    }


@pytest.mark.asyncio
@pytest.mark.slow
async def test_write_latency_1000_trades(trade_repo):
    """
    Test write latency for 1000 trades.

    AC #7: Write latency <100ms for trade persistence (load test with 1000 trades)

    Measures p50, p95, and p99 latencies to ensure <100ms target is met.
    """
    num_trades = 1000
    latencies = []

    print(f"\n📊 Performance Test: Writing {num_trades} trades...")

    for i in range(num_trades):
        trade_data = generate_trade_data(f"PERF_{i:06d}")

        start_time = time.perf_counter()
        await trade_repo.save_trade(trade_data)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

    # Calculate statistics
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
    avg = statistics.mean(latencies)
    max_latency = max(latencies)

    print(f"\n📈 Latency Statistics ({num_trades} trades):")
    print(f"   Average: {avg:.2f}ms")
    print(f"   P50 (median): {p50:.2f}ms")
    print(f"   P95: {p95:.2f}ms")
    print(f"   P99: {p99:.2f}ms")
    print(f"   Max: {max_latency:.2f}ms")

    # Assertions - AC requires <100ms
    assert p95 < 100, f"P95 latency {p95:.2f}ms exceeds 100ms threshold"
    assert avg < 100, f"Average latency {avg:.2f}ms exceeds 100ms threshold"

    print(f"\n✅ Performance Test PASSED: P95={p95:.2f}ms, Avg={avg:.2f}ms")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_concurrent_write_performance(trade_repo):
    """Test concurrent write performance with multiple tasks"""
    num_concurrent = 10
    trades_per_task = 50

    async def write_trades(task_id: int):
        """Write trades concurrently"""
        latencies = []
        for i in range(trades_per_task):
            trade_data = generate_trade_data(f"CONCURRENT_{task_id:02d}_{i:04d}")

            start_time = time.perf_counter()
            await trade_repo.save_trade(trade_data)
            end_time = time.perf_counter()

            latencies.append((end_time - start_time) * 1000)
        return latencies

    # Execute concurrent writes
    print(f"\n📊 Concurrent Write Test: {num_concurrent} tasks × {trades_per_task} trades...")
    start_time = time.perf_counter()

    tasks = [write_trades(i) for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks)

    end_time = time.perf_counter()

    # Combine all latencies
    all_latencies = [lat for task_lats in results for lat in task_lats]

    total_trades = len(all_latencies)
    total_time = end_time - start_time
    throughput = total_trades / total_time

    p95 = statistics.quantiles(all_latencies, n=20)[18]
    avg = statistics.mean(all_latencies)

    print(f"\n📈 Concurrent Write Statistics:")
    print(f"   Total trades: {total_trades}")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Throughput: {throughput:.2f} trades/sec")
    print(f"   Average latency: {avg:.2f}ms")
    print(f"   P95 latency: {p95:.2f}ms")

    assert p95 < 200, f"Concurrent P95 latency {p95:.2f}ms too high"
    print(f"\n✅ Concurrent Write Test PASSED")


@pytest.mark.asyncio
async def test_read_latency(trade_repo):
    """Test read query performance"""
    # Populate database with test data
    num_trades = 100
    for i in range(num_trades):
        trade_data = generate_trade_data(f"READ_PERF_{i:04d}")
        await trade_repo.save_trade(trade_data)

    # Test get_recent_trades latency
    read_latencies = []
    for _ in range(20):
        start_time = time.perf_counter()
        trades = await trade_repo.get_recent_trades(limit=50)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000
        read_latencies.append(latency_ms)

    avg_read = statistics.mean(read_latencies)
    p95_read = statistics.quantiles(read_latencies, n=20)[18]

    print(f"\n📈 Read Query Statistics:")
    print(f"   Average: {avg_read:.2f}ms")
    print(f"   P95: {p95_read:.2f}ms")

    # Read queries should be very fast
    assert p95_read < 500, f"P95 read latency {p95_read:.2f}ms exceeds 500ms"
    print(f"\n✅ Read Performance Test PASSED")


@pytest.mark.asyncio
async def test_query_with_filters_performance(trade_repo):
    """Test performance of filtered queries"""
    # Populate with varied data
    sessions = ["TOKYO", "LONDON", "NY", "SYDNEY"]
    for i in range(200):
        trade_data = generate_trade_data(f"FILTER_PERF_{i:04d}")
        trade_data["session"] = sessions[i % len(sessions)]
        await trade_repo.save_trade(trade_data)

    # Test filtered query performance
    start_time = time.perf_counter()
    london_trades = await trade_repo.get_trades_by_session("LONDON")
    end_time = time.perf_counter()

    query_time_ms = (end_time - start_time) * 1000

    print(f"\n📈 Filtered Query Statistics:")
    print(f"   Trades found: {len(london_trades)}")
    print(f"   Query time: {query_time_ms:.2f}ms")

    assert query_time_ms < 500, f"Filtered query time {query_time_ms:.2f}ms too high"
    assert len(london_trades) == 50  # Should find 25% of 200
    print(f"\n✅ Filtered Query Test PASSED")
