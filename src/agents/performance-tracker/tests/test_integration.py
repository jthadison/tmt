"""Integration tests for Performance Tracker Agent."""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from ..app.models import Base, TradePerformance, TradeStatus, PeriodType
from ..app.main import app, get_db
from ..app.pnl_tracker import PnLTracker
from ..app.market_data import MarketDataFeed


@pytest.fixture(scope="module")
def test_db():
    """Create test database for integration tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal


@pytest.fixture(scope="module")
def client(test_db):
    """Create test client with database override."""
    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
async def setup_test_data(test_db):
    """Setup test data for integration tests."""
    db = test_db()
    
    account_ids = [uuid4() for _ in range(3)]
    
    # Create performance data for multiple accounts
    base_time = datetime.utcnow() - timedelta(days=30)
    
    for i, account_id in enumerate(account_ids):
        # Create trades with different performance patterns
        for day in range(20):
            # Account 1: Consistent winner
            # Account 2: Volatile performer 
            # Account 3: Consistent loser
            
            if i == 0:  # Best performer
                pnl = Decimal("25.0") + (Decimal("5.0") * day / 20)
            elif i == 1:  # Volatile performer
                pnl = Decimal("50.0") if day % 3 == 0 else Decimal("-20.0")
            else:  # Worst performer
                pnl = Decimal("-10.0") - (Decimal("2.0") * day / 20)
            
            trade = TradePerformance(
                trade_id=uuid4(),
                account_id=account_id,
                symbol="EURUSD" if day % 2 == 0 else "GBPUSD",
                entry_time=base_time + timedelta(days=day),
                exit_time=base_time + timedelta(days=day) + timedelta(hours=2),
                entry_price=Decimal("1.1000"),
                exit_price=Decimal("1.1000") + (pnl / 10000),
                position_size=Decimal("1.0"),
                pnl=pnl,
                commission=Decimal("2.0"),
                status=TradeStatus.CLOSED.value
            )
            db.add(trade)
    
    db.commit()
    db.close()
    
    return account_ids


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_performance_metrics_endpoint(client, setup_test_data):
    """Test performance metrics API endpoint."""
    account_ids = await setup_test_data
    account_id = str(account_ids[0])  # Best performer
    
    start_date = datetime.utcnow() - timedelta(days=25)
    end_date = datetime.utcnow() - timedelta(days=5)
    
    response = client.get(
        f"/api/v1/performance/metrics/{account_id}",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "period_type": "daily"
        }
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "total_trades" in data
    assert "win_rate" in data
    assert "total_pnl" in data
    assert "profit_factor" in data
    
    # Best performer should have positive P&L
    assert float(data["total_pnl"]) > 0


@pytest.mark.asyncio
async def test_account_comparison_endpoint(client, setup_test_data):
    """Test account comparison API endpoint."""
    account_ids = await setup_test_data
    
    request_data = {
        "account_ids": [str(aid) for aid in account_ids],
        "start_date": (datetime.utcnow() - timedelta(days=25)).isoformat(),
        "end_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "period_type": "monthly"
    }
    
    response = client.post("/api/v1/performance/compare", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "rankings" in data
    assert "comparison_period" in data
    
    rankings = data["rankings"]
    assert len(rankings) == 3
    
    # Verify rankings are ordered (best to worst)
    assert rankings[0]["performance_rank"] == 1
    assert rankings[1]["performance_rank"] == 2
    assert rankings[2]["performance_rank"] == 3
    
    # Best performer should have highest P&L
    assert float(rankings[0]["total_pnl"]) > float(rankings[2]["total_pnl"])


@pytest.mark.asyncio
async def test_best_worst_performers_endpoint(client, setup_test_data):
    """Test best/worst performers identification endpoint."""
    account_ids = await setup_test_data
    
    params = {
        "account_ids": [str(aid) for aid in account_ids],
        "start_date": (datetime.utcnow() - timedelta(days=25)).isoformat(),
        "end_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "period_type": "monthly"
    }
    
    response = client.get("/api/v1/performance/compare/best-worst", params=params)
    assert response.status_code == 200
    
    data = response.json()
    assert "best_performer" in data
    assert "worst_performer" in data
    assert "median_performer" in data
    
    # Best performer should outperform worst performer
    best_pnl = float(data["best_performer"]["total_pnl"])
    worst_pnl = float(data["worst_performer"]["total_pnl"])
    assert best_pnl > worst_pnl


@pytest.mark.asyncio
async def test_heatmap_endpoint(client, setup_test_data):
    """Test performance heatmap generation endpoint."""
    account_ids = await setup_test_data
    
    params = {
        "account_ids": [str(aid) for aid in account_ids],
        "start_date": (datetime.utcnow() - timedelta(days=25)).isoformat(),
        "end_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "metric_type": "total_pnl"
    }
    
    response = client.get("/api/v1/performance/heatmap", params=params)
    assert response.status_code == 200
    
    data = response.json()
    assert "accounts" in data
    assert "data" in data
    assert "statistics" in data
    
    assert len(data["accounts"]) == 3
    assert len(data["data"]) == 3
    
    # Statistics should be calculated
    stats = data["statistics"]
    assert "min" in stats
    assert "max" in stats
    assert "mean" in stats


@pytest.mark.asyncio
async def test_report_generation_endpoint(client, setup_test_data):
    """Test report generation endpoints."""
    account_ids = await setup_test_data
    account_id = str(account_ids[0])
    
    # Test daily report
    daily_request = {
        "account_id": account_id,
        "report_type": "daily",
        "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat()
    }
    
    response = client.post("/api/v1/performance/report", json=daily_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "account_id" in data
    assert "summary" in data
    assert "trade_breakdown" in data
    
    # Test custom period report
    custom_request = {
        "account_id": account_id,
        "report_type": "custom",
        "start_date": (datetime.utcnow() - timedelta(days=15)).isoformat(),
        "end_date": (datetime.utcnow() - timedelta(days=5)).isoformat()
    }
    
    response = client.post("/api/v1/performance/report", json=custom_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "period_days" in data
    assert data["period_days"] == 10


@pytest.mark.asyncio
async def test_export_endpoint(client, setup_test_data):
    """Test data export endpoints."""
    account_ids = await setup_test_data
    
    export_request = {
        "account_ids": [str(account_ids[0])],
        "start_date": (datetime.utcnow() - timedelta(days=15)).isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "export_format": "csv",
        "report_type": "trades",
        "include_details": True
    }
    
    response = client.post("/api/v1/performance/export", json=export_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "export_id" in data
    assert "filename" in data
    assert "content_type" in data
    assert data["content_type"] == "text/csv"


def test_data_retention_endpoints(client):
    """Test data retention management endpoints."""
    # Test integrity check
    response = client.get("/api/v1/performance/retention/integrity")
    # Note: This might return 503 if retention manager not available in test mode
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "verified_at" in data
        assert "issues_found" in data
    
    # Test backup creation
    response = client.post(
        "/api/v1/performance/retention/backup",
        params={"backup_type": "incremental"}
    )
    assert response.status_code in [200, 503]


@pytest.mark.asyncio
async def test_error_handling(client):
    """Test API error handling."""
    # Test invalid account ID
    invalid_uuid = "invalid-uuid"
    response = client.get(f"/api/v1/performance/metrics/{invalid_uuid}")
    assert response.status_code == 422  # Validation error
    
    # Test missing required parameters for custom report
    invalid_request = {
        "account_id": str(uuid4()),
        "report_type": "custom"
        # Missing start_date and end_date
    }
    
    response = client.post("/api/v1/performance/report", json=invalid_request)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_websocket_connection(client):
    """Test WebSocket connection for real-time updates."""
    # Note: This is a basic connection test
    # Full WebSocket testing would require more complex setup
    
    with client.websocket_connect("/ws") as websocket:
        # Connection should be established
        assert websocket is not None
        
        # Send a test message to keep connection alive
        websocket.send_text("ping")


def test_cross_account_data_isolation(client, test_db):
    """Test that account data is properly isolated."""
    db = test_db()
    
    account1 = uuid4()
    account2 = uuid4()
    
    # Create trades for both accounts
    trade1 = TradePerformance(
        trade_id=uuid4(),
        account_id=account1,
        symbol="EURUSD",
        entry_time=datetime.utcnow() - timedelta(days=5),
        pnl=Decimal("100.0"),
        status=TradeStatus.CLOSED.value
    )
    
    trade2 = TradePerformance(
        trade_id=uuid4(),
        account_id=account2,
        symbol="EURUSD",
        entry_time=datetime.utcnow() - timedelta(days=5),
        pnl=Decimal("200.0"),
        status=TradeStatus.CLOSED.value
    )
    
    db.add(trade1)
    db.add(trade2)
    db.commit()
    db.close()
    
    # Request metrics for account1 only
    response = client.get(
        f"/api/v1/performance/metrics/{account1}",
        params={
            "start_date": (datetime.utcnow() - timedelta(days=10)).isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only include account1's data (P&L = 100)
    assert float(data["total_pnl"]) == 100.0
    assert data["total_trades"] == 1