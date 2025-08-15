"""
Tests for Historical Data Service - Story 8.2
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timedelta
import json
import csv
import io

from ..historical_data import (
    HistoricalDataService,
    HistoricalDataStore,
    BalanceDataPoint,
    BalanceHistoryData,
    PerformanceMetrics,
    TimeInterval,
    TrendDirection
)

class TestBalanceDataPoint:
    """Test BalanceDataPoint functionality"""
    
    def create_test_data_point(self, timestamp=None):
        """Create test balance data point"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        return BalanceDataPoint(
            timestamp=timestamp,
            balance=Decimal("10000.00"),
            unrealized_pl=Decimal("150.50"),
            realized_pl=Decimal("-25.75"),
            equity=Decimal("10150.50"),
            margin_used=Decimal("500.00"),
            margin_available=Decimal("9500.00"),
            open_positions=3,
            pending_orders=2,
            drawdown=Decimal("2.5")
        )
    
    def test_to_chart_data(self):
        """Test conversion to chart data format"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        point = self.create_test_data_point(timestamp)
        
        chart_data = point.to_chart_data()
        
        assert chart_data['timestamp'] == int(timestamp.timestamp() * 1000)
        assert chart_data['balance'] == 10000.00
        assert chart_data['equity'] == 10150.50
        assert chart_data['unrealized_pl'] == 150.50
        assert chart_data['margin_used'] == 500.00
        assert chart_data['drawdown'] == 2.5
    
    def test_to_chart_data_no_drawdown(self):
        """Test chart data conversion with no drawdown"""
        point = self.create_test_data_point()
        point.drawdown = None
        
        chart_data = point.to_chart_data()
        assert chart_data['drawdown'] is None

class TestHistoricalDataStore:
    """Test HistoricalDataStore functionality"""
    
    def test_initialization(self):
        """Test data store initialization"""
        store = HistoricalDataStore()
        
        assert len(store.balance_history) == 0
        assert store.max_points == 10000
    
    def test_add_balance_point(self):
        """Test adding balance points"""
        store = HistoricalDataStore()
        account_id = "test-account"
        
        # Create test points
        timestamp1 = datetime.utcnow() - timedelta(hours=2)
        point1 = BalanceDataPoint(
            timestamp=timestamp1,
            balance=Decimal("10000"),
            unrealized_pl=Decimal("100"),
            realized_pl=Decimal("0"),
            equity=Decimal("10100"),
            margin_used=Decimal("200"),
            margin_available=Decimal("9800"),
            open_positions=1,
            pending_orders=0
        )
        
        timestamp2 = datetime.utcnow() - timedelta(hours=1)
        point2 = BalanceDataPoint(
            timestamp=timestamp2,
            balance=Decimal("10050"),
            unrealized_pl=Decimal("150"),
            realized_pl=Decimal("50"),
            equity=Decimal("10200"),
            margin_used=Decimal("300"),
            margin_available=Decimal("9700"),
            open_positions=2,
            pending_orders=1
        )
        
        # Add points
        store.add_balance_point(account_id, point1)
        store.add_balance_point(account_id, point2)
        
        # Check storage
        history = store.get_balance_history(account_id)
        assert len(history) == 2
        
        # Should be sorted by timestamp
        assert history[0].timestamp == timestamp1
        assert history[1].timestamp == timestamp2
    
    def test_add_duplicate_timestamp(self):
        """Test adding point with duplicate timestamp"""
        store = HistoricalDataStore()
        account_id = "test-account"
        timestamp = datetime.utcnow()
        
        # Create two points with same timestamp
        point1 = BalanceDataPoint(
            timestamp=timestamp,
            balance=Decimal("10000"),
            unrealized_pl=Decimal("100"),
            realized_pl=Decimal("0"),
            equity=Decimal("10100"),
            margin_used=Decimal("200"),
            margin_available=Decimal("9800"),
            open_positions=1,
            pending_orders=0
        )
        
        point2 = BalanceDataPoint(
            timestamp=timestamp,
            balance=Decimal("10050"),
            unrealized_pl=Decimal("150"),
            realized_pl=Decimal("50"),
            equity=Decimal("10200"),
            margin_used=Decimal("300"),
            margin_available=Decimal("9700"),
            open_positions=2,
            pending_orders=1
        )
        
        # Add both points
        store.add_balance_point(account_id, point1)
        store.add_balance_point(account_id, point2)
        
        # Should only have one point (second one replaces first)
        history = store.get_balance_history(account_id)
        assert len(history) == 1
        assert history[0].balance == Decimal("10050")
    
    def test_memory_limit(self):
        """Test memory limit enforcement"""
        store = HistoricalDataStore()
        store.max_points = 5  # Small limit for testing
        account_id = "test-account"
        
        # Add more points than limit
        for i in range(10):
            timestamp = datetime.utcnow() - timedelta(minutes=i)
            point = BalanceDataPoint(
                timestamp=timestamp,
                balance=Decimal(f"{10000 + i}"),
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                equity=Decimal(f"{10000 + i}"),
                margin_used=Decimal("0"),
                margin_available=Decimal(f"{10000 + i}"),
                open_positions=0,
                pending_orders=0
            )
            store.add_balance_point(account_id, point)
        
        # Should be limited to max_points
        history = store.get_balance_history(account_id)
        assert len(history) <= store.max_points
    
    def test_get_balance_history_with_date_range(self):
        """Test getting balance history with date filtering"""
        store = HistoricalDataStore()
        account_id = "test-account"
        
        # Add points across different times
        base_time = datetime.utcnow()
        for i in range(5):
            timestamp = base_time - timedelta(days=i)
            point = BalanceDataPoint(
                timestamp=timestamp,
                balance=Decimal(f"{10000 + i}"),
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                equity=Decimal(f"{10000 + i}"),
                margin_used=Decimal("0"),
                margin_available=Decimal(f"{10000 + i}"),
                open_positions=0,
                pending_orders=0
            )
            store.add_balance_point(account_id, point)
        
        # Get history for last 2 days
        start_date = base_time - timedelta(days=2)
        history = store.get_balance_history(account_id, start_date=start_date)
        
        # Should get 3 points (days 0, 1, 2)
        assert len(history) == 3
        for point in history:
            assert point.timestamp >= start_date
    
    def test_clear_account_history(self):
        """Test clearing account history"""
        store = HistoricalDataStore()
        account_id = "test-account"
        
        # Add some points
        point = BalanceDataPoint(
            timestamp=datetime.utcnow(),
            balance=Decimal("10000"),
            unrealized_pl=Decimal("0"),
            realized_pl=Decimal("0"),
            equity=Decimal("10000"),
            margin_used=Decimal("0"),
            margin_available=Decimal("10000"),
            open_positions=0,
            pending_orders=0
        )
        store.add_balance_point(account_id, point)
        
        assert len(store.get_balance_history(account_id)) == 1
        
        # Clear history
        store.clear_account_history(account_id)
        assert len(store.get_balance_history(account_id)) == 0

class TestHistoricalDataService:
    """Test HistoricalDataService functionality"""
    
    @pytest.fixture
    def historical_service(self):
        """Create test historical data service"""
        return HistoricalDataService(account_id="test-account")
    
    def test_initialization(self, historical_service):
        """Test service initialization"""
        assert historical_service.account_id == "test-account"
        assert historical_service.data_store is not None
        assert historical_service.collection_interval == timedelta(minutes=5)
        assert not historical_service.is_collecting
        assert historical_service.collection_task is None
    
    def test_record_balance_snapshot(self, historical_service):
        """Test recording balance snapshots"""
        timestamp = datetime.utcnow()
        
        historical_service.record_balance_snapshot(
            balance=Decimal("10000"),
            unrealized_pl=Decimal("150"),
            realized_pl=Decimal("-25"),
            equity=Decimal("10150"),
            margin_used=Decimal("500"),
            margin_available=Decimal("9500"),
            open_positions=3,
            pending_orders=2,
            timestamp=timestamp
        )
        
        # Check that point was recorded
        history = historical_service.data_store.get_balance_history("test-account")
        assert len(history) == 1
        
        point = history[0]
        assert point.timestamp == timestamp
        assert point.balance == Decimal("10000")
        assert point.equity == Decimal("10150")
        assert point.open_positions == 3
    
    def test_record_balance_snapshot_with_drawdown(self, historical_service):
        """Test recording snapshots with drawdown calculation"""
        base_time = datetime.utcnow()
        
        # First snapshot - peak equity
        historical_service.record_balance_snapshot(
            balance=Decimal("10000"),
            unrealized_pl=Decimal("500"),
            realized_pl=Decimal("0"),
            equity=Decimal("10500"),  # Peak
            margin_used=Decimal("300"),
            margin_available=Decimal("9700"),
            open_positions=2,
            pending_orders=1,
            timestamp=base_time - timedelta(hours=1)
        )
        
        # Second snapshot - lower equity (drawdown)
        historical_service.record_balance_snapshot(
            balance=Decimal("10000"),
            unrealized_pl=Decimal("200"),
            realized_pl=Decimal("0"),
            equity=Decimal("10200"),  # Below peak
            margin_used=Decimal("400"),
            margin_available=Decimal("9600"),
            open_positions=3,
            pending_orders=0,
            timestamp=base_time
        )
        
        # Check drawdown calculation
        history = historical_service.data_store.get_balance_history("test-account")
        assert len(history) == 2
        
        # Second point should have drawdown calculated
        second_point = history[1]
        assert second_point.drawdown is not None
        
        # Drawdown = (10500 - 10200) / 10500 = ~2.86%
        expected_drawdown = (10500 - 10200) / 10500
        assert abs(float(second_point.drawdown) - expected_drawdown) < 0.01
    
    @pytest.mark.asyncio
    async def test_get_balance_history_empty(self, historical_service):
        """Test getting balance history when empty"""
        history_data = await historical_service.get_balance_history(days=30)
        
        assert isinstance(history_data, BalanceHistoryData)
        assert len(history_data.data_points) == 0
        assert history_data.trend == TrendDirection.SIDEWAYS
        assert history_data.volatility == Decimal('0')
        assert history_data.metrics.total_trades == 0
    
    @pytest.mark.asyncio
    async def test_get_balance_history_with_data(self, historical_service):
        """Test getting balance history with data"""
        # Add sample data
        base_time = datetime.utcnow()
        for i in range(10):
            timestamp = base_time - timedelta(days=9-i)
            balance = Decimal(f"{10000 + i * 100}")
            equity = balance + Decimal("50")
            
            historical_service.record_balance_snapshot(
                balance=balance,
                unrealized_pl=Decimal("50"),
                realized_pl=Decimal(f"{i * 10}"),
                equity=equity,
                margin_used=Decimal("500"),
                margin_available=balance - Decimal("500"),
                open_positions=i % 3,
                pending_orders=i % 2,
                timestamp=timestamp
            )
        
        # Get history
        history_data = await historical_service.get_balance_history(days=30)
        
        assert len(history_data.data_points) == 10
        assert history_data.trend == TrendDirection.UP  # Increasing balance
        assert history_data.metrics.total_return > 0
        assert history_data.metrics.start_balance == Decimal("10000")
        assert history_data.metrics.end_balance == Decimal("10900")
    
    @pytest.mark.asyncio
    async def test_trend_calculation(self, historical_service):
        """Test trend direction calculation"""
        base_time = datetime.utcnow()
        
        # Test upward trend
        for i in range(5):
            timestamp = base_time - timedelta(days=4-i)
            balance = Decimal(f"{10000 + i * 200}")  # +4% total
            
            historical_service.record_balance_snapshot(
                balance=balance,
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                equity=balance,
                margin_used=Decimal("0"),
                margin_available=balance,
                open_positions=0,
                pending_orders=0,
                timestamp=timestamp
            )
        
        history_data = await historical_service.get_balance_history(days=10)
        assert history_data.trend == TrendDirection.UP
        
        # Clear and test downward trend
        historical_service.data_store.clear_account_history("test-account")
        
        for i in range(5):
            timestamp = base_time - timedelta(days=4-i)
            balance = Decimal(f"{10000 - i * 100}")  # -4% total
            
            historical_service.record_balance_snapshot(
                balance=balance,
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                equity=balance,
                margin_used=Decimal("0"),
                margin_available=balance,
                open_positions=0,
                pending_orders=0,
                timestamp=timestamp
            )
        
        history_data = await historical_service.get_balance_history(days=10)
        assert history_data.trend == TrendDirection.DOWN
    
    @pytest.mark.asyncio
    async def test_volatility_calculation(self, historical_service):
        """Test volatility calculation"""
        base_time = datetime.utcnow()
        
        # Add data with varying equity
        balances = [10000, 10100, 9950, 10200, 9900, 10300, 9800]
        for i, balance in enumerate(balances):
            timestamp = base_time - timedelta(days=len(balances)-1-i)
            
            historical_service.record_balance_snapshot(
                balance=Decimal(str(balance)),
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                equity=Decimal(str(balance)),
                margin_used=Decimal("0"),
                margin_available=Decimal(str(balance)),
                open_positions=0,
                pending_orders=0,
                timestamp=timestamp
            )
        
        history_data = await historical_service.get_balance_history(days=10)
        
        # Should have some volatility due to varying balances
        assert history_data.volatility > Decimal('0')
        assert history_data.volatility < Decimal('100')  # Reasonable range
    
    @pytest.mark.asyncio
    async def test_performance_metrics_calculation(self, historical_service):
        """Test performance metrics calculation"""
        base_time = datetime.utcnow()
        
        # Add sample trading data with wins and losses
        equity_changes = [10000, 10100, 10050, 10200, 10150, 10300, 10250]
        for i, equity in enumerate(equity_changes):
            timestamp = base_time - timedelta(days=len(equity_changes)-1-i)
            
            historical_service.record_balance_snapshot(
                balance=Decimal(str(equity)),
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                equity=Decimal(str(equity)),
                margin_used=Decimal("0"),
                margin_available=Decimal(str(equity)),
                open_positions=0,
                pending_orders=0,
                timestamp=timestamp
            )
        
        history_data = await historical_service.get_balance_history(days=10)
        metrics = history_data.metrics
        
        # Check basic metrics
        assert metrics.start_balance == Decimal("10000")
        assert metrics.end_balance == Decimal("10250")
        assert metrics.total_return == Decimal("250")
        assert metrics.total_return_percent == Decimal("2.5")
        
        # Check trade analysis
        assert metrics.total_trades > 0
        assert metrics.winning_trades >= 0
        assert metrics.losing_trades >= 0
        assert metrics.winning_trades + metrics.losing_trades == metrics.total_trades
    
    @pytest.mark.asyncio
    async def test_export_history_csv(self, historical_service):
        """Test CSV export functionality"""
        # Add sample data
        timestamp = datetime.utcnow()
        historical_service.record_balance_snapshot(
            balance=Decimal("10000"),
            unrealized_pl=Decimal("150"),
            realized_pl=Decimal("-25"),
            equity=Decimal("10150"),
            margin_used=Decimal("500"),
            margin_available=Decimal("9500"),
            open_positions=3,
            pending_orders=2,
            timestamp=timestamp
        )
        
        # Export as CSV
        csv_data = await historical_service.export_history(days=30, format='csv')
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        
        assert len(rows) == 1
        row = rows[0]
        assert float(row['Balance']) == 10000.0
        assert float(row['Unrealized P&L']) == 150.0
        assert float(row['Equity']) == 10150.0
        assert int(row['Open Positions']) == 3
    
    @pytest.mark.asyncio
    async def test_export_history_json(self, historical_service):
        """Test JSON export functionality"""
        # Add sample data
        timestamp = datetime.utcnow()
        historical_service.record_balance_snapshot(
            balance=Decimal("10000"),
            unrealized_pl=Decimal("150"),
            realized_pl=Decimal("-25"),
            equity=Decimal("10150"),
            margin_used=Decimal("500"),
            margin_available=Decimal("9500"),
            open_positions=3,
            pending_orders=2,
            timestamp=timestamp
        )
        
        # Export as JSON
        json_data = await historical_service.export_history(days=30, format='json')
        
        # Parse JSON
        data = json.loads(json_data)
        
        assert 'export_date' in data
        assert data['account_id'] == 'test-account'
        assert data['period_days'] == 30
        assert len(data['data_points']) == 1
        assert 'metrics' in data
    
    @pytest.mark.asyncio
    async def test_export_invalid_format(self, historical_service):
        """Test export with invalid format"""
        with pytest.raises(ValueError) as exc_info:
            await historical_service.export_history(format='xml')
        
        assert "Unsupported export format" in str(exc_info.value)
    
    def test_get_latest_snapshot(self, historical_service):
        """Test getting latest snapshot"""
        # Initially empty
        latest = historical_service.get_latest_snapshot()
        assert latest is None
        
        # Add snapshots
        timestamp1 = datetime.utcnow() - timedelta(hours=1)
        historical_service.record_balance_snapshot(
            balance=Decimal("10000"),
            unrealized_pl=Decimal("100"),
            realized_pl=Decimal("0"),
            equity=Decimal("10100"),
            margin_used=Decimal("200"),
            margin_available=Decimal("9800"),
            open_positions=1,
            pending_orders=0,
            timestamp=timestamp1
        )
        
        timestamp2 = datetime.utcnow()
        historical_service.record_balance_snapshot(
            balance=Decimal("10050"),
            unrealized_pl=Decimal("150"),
            realized_pl=Decimal("50"),
            equity=Decimal("10200"),
            margin_used=Decimal("300"),
            margin_available=Decimal("9700"),
            open_positions=2,
            pending_orders=1,
            timestamp=timestamp2
        )
        
        # Should get most recent
        latest = historical_service.get_latest_snapshot()
        assert latest is not None
        assert latest.timestamp == timestamp2
        assert latest.balance == Decimal("10050")
    
    @pytest.mark.asyncio
    async def test_data_aggregation_by_interval(self, historical_service):
        """Test data aggregation by time intervals"""
        base_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Add hourly data points
        for i in range(24):
            timestamp = base_time + timedelta(hours=i)
            balance = Decimal(f"{10000 + i}")
            
            historical_service.record_balance_snapshot(
                balance=balance,
                unrealized_pl=Decimal("0"),
                realized_pl=Decimal("0"),
                equity=balance,
                margin_used=Decimal("0"),
                margin_available=balance,
                open_positions=0,
                pending_orders=0,
                timestamp=timestamp
            )
        
        # Get daily aggregation
        history_data = await historical_service.get_balance_history(
            days=2, 
            interval=TimeInterval.DAILY
        )
        
        # Should have fewer points due to aggregation
        assert len(history_data.data_points) < 24
        assert history_data.interval == TimeInterval.DAILY
    
    def test_start_stop_data_collection(self, historical_service):
        """Test starting and stopping data collection"""
        assert not historical_service.is_collecting
        assert historical_service.collection_task is None
        
        # Start collection
        historical_service.start_data_collection()
        assert historical_service.is_collecting
        assert historical_service.collection_task is not None
        
        # Stop collection
        historical_service.stop_data_collection()
        assert not historical_service.is_collecting

if __name__ == "__main__":
    pytest.main([__file__, "-v"])