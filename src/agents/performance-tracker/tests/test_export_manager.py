"""Tests for export manager functionality."""

import pytest
import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from io import StringIO

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..app.models import (
    Base, TradePerformance, ExportRequest, TradeStatus, 
    PeriodType
)
from ..app.export_manager import PerformanceExportManager


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_trades(db_session):
    """Create sample trades for export testing."""
    account_id = uuid4()
    trades = []
    
    # Create a mix of winning and losing trades
    trade_data = [
        {"pnl": Decimal("50.0"), "symbol": "EURUSD", "entry_price": "1.1000", "exit_price": "1.1050"},
        {"pnl": Decimal("-30.0"), "symbol": "GBPUSD", "entry_price": "1.3000", "exit_price": "1.2970"},
        {"pnl": Decimal("75.0"), "symbol": "USDJPY", "entry_price": "110.00", "exit_price": "110.75"},
        {"pnl": Decimal("-45.0"), "symbol": "EURUSD", "entry_price": "1.1100", "exit_price": "1.1055"},
    ]
    
    base_time = datetime.utcnow() - timedelta(days=10)
    
    for i, data in enumerate(trade_data):
        trade = TradePerformance(
            trade_id=uuid4(),
            account_id=account_id,
            symbol=data["symbol"],
            entry_time=base_time + timedelta(days=i),
            exit_time=base_time + timedelta(days=i) + timedelta(hours=2),
            entry_price=Decimal(data["entry_price"]),
            exit_price=Decimal(data["exit_price"]),
            position_size=Decimal("1.0"),
            pnl=data["pnl"],
            commission=Decimal("2.0"),
            swap=Decimal("0.5"),
            status=TradeStatus.CLOSED.value
        )
        trades.append(trade)
        db_session.add(trade)
    
    db_session.commit()
    return account_id, trades


@pytest.mark.asyncio
async def test_csv_export_trades(db_session, sample_trades):
    """Test CSV export of trades data."""
    account_id, trades = sample_trades
    export_manager = PerformanceExportManager(db_session)
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="csv",
        report_type="trades"
    )
    
    result = await export_manager.export_performance_data(request)
    
    assert "content" in result
    assert "filename" in result
    assert result["content_type"] == "text/csv"
    assert "trades_export_" in result["filename"]
    
    # Parse CSV content to verify structure
    csv_reader = csv.reader(StringIO(result["content"]))
    headers = next(csv_reader)
    
    expected_headers = [
        'Trade ID', 'Account ID', 'Symbol', 'Entry Time', 'Exit Time',
        'Entry Price', 'Exit Price', 'Position Size', 'P&L', 'P&L %',
        'Commission', 'Swap', 'Duration (seconds)', 'Status'
    ]
    
    assert headers == expected_headers
    
    # Verify data rows
    rows = list(csv_reader)
    assert len(rows) == 4  # Should have 4 trades


@pytest.mark.asyncio
async def test_tax_reporting_export(db_session, sample_trades):
    """Test tax reporting format export (Form 8949)."""
    account_id, trades = sample_trades
    export_manager = PerformanceExportManager(db_session)
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="csv",
        report_type="tax"
    )
    
    result = await export_manager.export_performance_data(request)
    
    assert result["content_type"] == "text/csv"
    assert "tax_report_8949_" in result["filename"]
    
    # Parse CSV to verify Form 8949 structure
    csv_reader = csv.reader(StringIO(result["content"]))
    headers = next(csv_reader)
    
    expected_headers = [
        'Description', 'Date Acquired', 'Date Sold', 
        'Proceeds', 'Cost Basis', 'Gain/Loss', 'Code'
    ]
    
    assert headers == expected_headers
    
    # Verify tax data formatting
    rows = list(csv_reader)
    for row in rows:
        assert len(row) == 7
        assert row[6] == 'D'  # Should have derivative code
        
        # Verify dates are properly formatted (MM/DD/YYYY)
        date_acquired = row[1]
        date_sold = row[2]
        assert len(date_acquired.split('/')) == 3
        assert len(date_sold.split('/')) == 3


@pytest.mark.asyncio
async def test_json_export(db_session, sample_trades):
    """Test JSON format export."""
    account_id, trades = sample_trades
    export_manager = PerformanceExportManager(db_session)
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="json",
        report_type="performance",
        include_details=True
    )
    
    result = await export_manager.export_performance_data(request)
    
    assert result["content_type"] == "application/json"
    assert "performance_export_" in result["filename"]
    
    # Parse JSON content
    json_data = json.loads(result["content"])
    
    assert "export_metadata" in json_data
    assert "accounts" in json_data
    
    # Verify metadata
    metadata = json_data["export_metadata"]
    assert "generated_at" in metadata
    assert "account_ids" in metadata
    assert len(metadata["account_ids"]) == 1
    
    # Verify account data
    assert len(json_data["accounts"]) == 1
    account_data = json_data["accounts"][0]
    
    assert "account_id" in account_data
    assert "summary" in account_data
    assert "trades" in account_data  # Should include details
    
    # Verify trade details are included
    assert len(account_data["trades"]) == 4


@pytest.mark.asyncio
async def test_json_export_without_details(db_session, sample_trades):
    """Test JSON export without detailed trade data."""
    account_id, trades = sample_trades
    export_manager = PerformanceExportManager(db_session)
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="json",
        report_type="performance",
        include_details=False
    )
    
    result = await export_manager.export_performance_data(request)
    
    json_data = json.loads(result["content"])
    account_data = json_data["accounts"][0]
    
    # Should not include trade details
    assert "trades" not in account_data or len(account_data.get("trades", [])) == 0


@pytest.mark.asyncio
async def test_multiple_accounts_export(db_session):
    """Test export with multiple accounts."""
    export_manager = PerformanceExportManager(db_session)
    
    # Create trades for two accounts
    account_ids = [uuid4(), uuid4()]
    
    for i, account_id in enumerate(account_ids):
        trade = TradePerformance(
            trade_id=uuid4(),
            account_id=account_id,
            symbol="EURUSD",
            entry_time=datetime.utcnow() - timedelta(days=5),
            exit_time=datetime.utcnow() - timedelta(days=5) + timedelta(hours=1),
            entry_price=Decimal("1.1000"),
            exit_price=Decimal("1.1050"),
            position_size=Decimal("1.0"),
            pnl=Decimal("50.0") * (i + 1),  # Different P&L per account
            status=TradeStatus.CLOSED.value
        )
        db_session.add(trade)
    
    db_session.commit()
    
    request = ExportRequest(
        account_ids=account_ids,
        start_date=datetime.utcnow() - timedelta(days=10),
        end_date=datetime.utcnow(),
        export_format="json",
        report_type="performance"
    )
    
    result = await export_manager.export_performance_data(request)
    json_data = json.loads(result["content"])
    
    # Should have data for both accounts
    assert len(json_data["accounts"]) == 2
    assert len(json_data["export_metadata"]["account_ids"]) == 2


@pytest.mark.asyncio
async def test_prop_firm_csv_export(db_session, sample_trades):
    """Test prop firm specific CSV export format."""
    account_id, trades = sample_trades
    export_manager = PerformanceExportManager(db_session)
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="csv",
        report_type="prop_firm"
    )
    
    result = await export_manager.export_performance_data(request)
    
    assert result["content_type"] == "text/csv"
    
    # Verify CSV structure for prop firm reporting
    csv_reader = csv.reader(StringIO(result["content"]))
    headers = next(csv_reader)
    
    # Should contain all necessary trade information
    assert "Trade ID" in headers
    assert "Symbol" in headers
    assert "P&L" in headers


@pytest.mark.asyncio
async def test_pdf_export_placeholder(db_session, sample_trades):
    """Test PDF export placeholder functionality."""
    account_id, trades = sample_trades
    export_manager = PerformanceExportManager(db_session)
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="pdf",
        report_type="performance"
    )
    
    result = await export_manager.export_performance_data(request)
    
    assert result["content_type"] == "application/pdf"
    assert "performance_report_" in result["filename"]
    assert result["content"] == "PDF generation not implemented"


@pytest.mark.asyncio
async def test_excel_export_placeholder(db_session, sample_trades):
    """Test Excel export placeholder functionality."""
    account_id, trades = sample_trades
    export_manager = PerformanceExportManager(db_session)
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="xlsx",
        report_type="performance"
    )
    
    result = await export_manager.export_performance_data(request)
    
    assert result["content_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "performance_data_" in result["filename"]
    assert result["content"] == "Excel generation not implemented"


@pytest.mark.asyncio
async def test_invalid_export_format(db_session, sample_trades):
    """Test error handling for invalid export format."""
    account_id, trades = sample_trades
    export_manager = PerformanceExportManager(db_session)
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="invalid_format",
        report_type="performance"
    )
    
    with pytest.raises(ValueError, match="Unsupported export format"):
        await export_manager.export_performance_data(request)


@pytest.mark.asyncio
async def test_empty_data_export(db_session):
    """Test export behavior with no data."""
    export_manager = PerformanceExportManager(db_session)
    account_id = uuid4()  # Account with no trades
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=15),
        end_date=datetime.utcnow(),
        export_format="csv",
        report_type="trades"
    )
    
    result = await export_manager.export_performance_data(request)
    
    # Should still return valid CSV with headers
    csv_reader = csv.reader(StringIO(result["content"]))
    headers = next(csv_reader)
    assert len(headers) > 0
    
    # Should have no data rows
    rows = list(csv_reader)
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_date_range_filtering(db_session):
    """Test that export respects date range filtering."""
    export_manager = PerformanceExportManager(db_session)
    account_id = uuid4()
    
    # Create trades outside and inside the date range
    old_trade = TradePerformance(
        trade_id=uuid4(),
        account_id=account_id,
        symbol="EURUSD",
        entry_time=datetime.utcnow() - timedelta(days=30),  # Outside range
        exit_time=datetime.utcnow() - timedelta(days=30) + timedelta(hours=1),
        pnl=Decimal("100.0"),
        status=TradeStatus.CLOSED.value
    )
    
    new_trade = TradePerformance(
        trade_id=uuid4(),
        account_id=account_id,
        symbol="EURUSD",
        entry_time=datetime.utcnow() - timedelta(days=5),  # Inside range
        exit_time=datetime.utcnow() - timedelta(days=5) + timedelta(hours=1),
        pnl=Decimal("50.0"),
        status=TradeStatus.CLOSED.value
    )
    
    db_session.add(old_trade)
    db_session.add(new_trade)
    db_session.commit()
    
    request = ExportRequest(
        account_ids=[account_id],
        start_date=datetime.utcnow() - timedelta(days=10),  # Should exclude old trade
        end_date=datetime.utcnow(),
        export_format="csv",
        report_type="trades"
    )
    
    result = await export_manager.export_performance_data(request)
    
    csv_reader = csv.reader(StringIO(result["content"]))
    next(csv_reader)  # Skip headers
    rows = list(csv_reader)
    
    # Should only include the new trade
    assert len(rows) == 1