"""
Tests for Dashboard Components - Story 8.2
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timedelta
import json
import websockets

from ..dashboard.account_dashboard import (
    AccountDashboard,
    DashboardWidget,
    AccountSummaryWidget,
    MarginStatusWidget,
    PositionCounterWidget,
    InstrumentSpreadWidget,
    BalanceHistoryWidget,
    EquityCurveWidget,
    WidgetStatus
)
from ..dashboard.websocket_handler import (
    DashboardWebSocketHandler,
    WebSocketMessage
)
from ..account_manager import AccountSummary, AccountCurrency
from ..instrument_service import InstrumentSpread
from ..historical_data import BalanceHistoryData, PerformanceMetrics, TrendDirection, TimeInterval

class TestDashboardWidget:
    """Test base DashboardWidget functionality"""
    
    def test_widget_initialization(self):
        """Test widget initialization"""
        widget = DashboardWidget(
            widget_id="test_widget",
            title="Test Widget",
            status=WidgetStatus.READY,
            last_update=datetime.utcnow(),
            data={"key": "value"}
        )
        
        assert widget.widget_id == "test_widget"
        assert widget.title == "Test Widget"
        assert widget.status == WidgetStatus.READY
        assert widget.data["key"] == "value"
        assert widget.error_message is None
    
    def test_widget_to_dict(self):
        """Test widget dictionary conversion"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        widget = DashboardWidget(
            widget_id="test_widget",
            title="Test Widget",
            status=WidgetStatus.ERROR,
            last_update=timestamp,
            data={"balance": 10000},
            error_message="Test error"
        )
        
        data = widget.to_dict()
        
        assert data["widget_id"] == "test_widget"
        assert data["title"] == "Test Widget"
        assert data["status"] == "error"
        assert data["last_update"] == timestamp.isoformat()
        assert data["data"]["balance"] == 10000
        assert data["error_message"] == "Test error"

class TestAccountSummaryWidget:
    """Test AccountSummaryWidget functionality"""
    
    def create_test_account_summary(self):
        """Create test account summary"""
        return AccountSummary(
            account_id="test-account",
            currency=AccountCurrency.USD,
            balance=Decimal("10000.00"),
            unrealized_pl=Decimal("150.50"),
            realized_pl=Decimal("-25.75"),
            margin_used=Decimal("500.00"),
            margin_available=Decimal("9500.00"),
            margin_closeout_percent=Decimal("50.0"),
            margin_call_percent=Decimal("100.0"),
            open_position_count=3,
            pending_order_count=2,
            leverage=50,
            financing=Decimal("5.25"),
            commission=Decimal("2.50"),
            dividend_adjustment=Decimal("0.00"),
            account_equity=Decimal("10150.50"),
            nav=Decimal("10150.50"),
            margin_rate=Decimal("0.02"),
            position_value=Decimal("25000.00"),
            last_transaction_id="12345",
            created_time=datetime.utcnow()
        )
    
    def test_from_account_summary(self):
        """Test creating widget from account summary"""
        summary = self.create_test_account_summary()
        widget = AccountSummaryWidget.from_account_summary(summary)
        
        assert widget.widget_id == "account_summary"
        assert widget.title == "Account Summary"
        assert widget.status == WidgetStatus.READY
        
        data = widget.data
        assert data["account_id"] == "test-account"
        assert data["currency"] == "USD"
        assert data["balance"] == 10000.00
        assert data["unrealized_pl"] == 150.50
        assert data["equity"] == 10150.50
        assert data["leverage"] == 50
        assert data["pl_color"] == "green"  # Positive unrealized P&L
    
    def test_negative_pl_color(self):
        """Test P&L color for negative unrealized P&L"""
        summary = self.create_test_account_summary()
        summary.unrealized_pl = Decimal("-100.00")
        summary.account_equity = Decimal("9900.00")
        
        widget = AccountSummaryWidget.from_account_summary(summary)
        assert widget.data["pl_color"] == "red"

class TestMarginStatusWidget:
    """Test MarginStatusWidget functionality"""
    
    def create_healthy_account_summary(self):
        """Create healthy account summary"""
        return AccountSummary(
            account_id="test-account",
            currency=AccountCurrency.USD,
            balance=Decimal("10000.00"),
            unrealized_pl=Decimal("150.50"),
            realized_pl=Decimal("-25.75"),
            margin_used=Decimal("500.00"),
            margin_available=Decimal("9500.00"),
            margin_closeout_percent=Decimal("50.0"),
            margin_call_percent=Decimal("100.0"),
            open_position_count=3,
            pending_order_count=2,
            leverage=50,
            financing=Decimal("5.25"),
            commission=Decimal("2.50"),
            dividend_adjustment=Decimal("0.00"),
            account_equity=Decimal("10150.50"),
            nav=Decimal("10150.50"),
            margin_rate=Decimal("0.02"),
            position_value=Decimal("25000.00"),
            last_transaction_id="12345",
            created_time=datetime.utcnow()
        )
    
    def test_healthy_margin_status(self):
        """Test margin status for healthy account"""
        summary = self.create_healthy_account_summary()
        widget = MarginStatusWidget.from_account_summary(summary)
        
        assert widget.widget_id == "margin_status"
        assert widget.title == "Margin Status"
        
        data = widget.data
        assert data["status_color"] == "green"
        assert data["status_text"] == "SAFE"
        assert not data["is_margin_call"]
        assert not data["is_margin_closeout"]
        assert data["margin_level"] > 2000  # Healthy margin level
    
    def test_margin_call_status(self):
        """Test margin status for margin call situation"""
        summary = self.create_healthy_account_summary()
        summary.account_equity = Decimal("400.00")  # Below margin call level
        
        widget = MarginStatusWidget.from_account_summary(summary)
        
        data = widget.data
        assert data["status_color"] == "orange"
        assert data["status_text"] == "WARNING"
        assert data["is_margin_call"]
        assert not data["is_margin_closeout"]
    
    def test_margin_closeout_status(self):
        """Test margin status for margin closeout situation"""
        summary = self.create_healthy_account_summary()
        summary.account_equity = Decimal("200.00")  # Below closeout level
        
        widget = MarginStatusWidget.from_account_summary(summary)
        
        data = widget.data
        assert data["status_color"] == "red"
        assert data["status_text"] == "DANGER"
        assert data["is_margin_call"]
        assert data["is_margin_closeout"]

class TestPositionCounterWidget:
    """Test PositionCounterWidget functionality"""
    
    def test_from_account_summary(self):
        """Test creating position counter widget"""
        summary = AccountSummary(
            account_id="test-account",
            currency=AccountCurrency.USD,
            balance=Decimal("10000.00"),
            unrealized_pl=Decimal("150.50"),
            realized_pl=Decimal("-25.75"),
            margin_used=Decimal("500.00"),
            margin_available=Decimal("9500.00"),
            margin_closeout_percent=Decimal("50.0"),
            margin_call_percent=Decimal("100.0"),
            open_position_count=5,
            pending_order_count=3,
            leverage=50,
            financing=Decimal("5.25"),
            commission=Decimal("2.50"),
            dividend_adjustment=Decimal("0.00"),
            account_equity=Decimal("10150.50"),
            nav=Decimal("10150.50"),
            margin_rate=Decimal("0.02"),
            position_value=Decimal("25000.00"),
            last_transaction_id="12345",
            created_time=datetime.utcnow()
        )
        
        widget = PositionCounterWidget.from_account_summary(summary)
        
        assert widget.widget_id == "position_counter"
        
        data = widget.data
        assert data["open_positions"] == 5
        assert data["pending_orders"] == 3
        assert data["total_trades"] == 8
        assert data["positions_color"] == "blue"  # Has positions
        assert data["orders_color"] == "orange"   # Has orders
    
    def test_no_positions_or_orders(self):
        """Test widget with no positions or orders"""
        summary = AccountSummary(
            account_id="test-account",
            currency=AccountCurrency.USD,
            balance=Decimal("10000.00"),
            unrealized_pl=Decimal("0"),
            realized_pl=Decimal("0"),
            margin_used=Decimal("0"),
            margin_available=Decimal("10000.00"),
            margin_closeout_percent=Decimal("50.0"),
            margin_call_percent=Decimal("100.0"),
            open_position_count=0,
            pending_order_count=0,
            leverage=50,
            financing=Decimal("0"),
            commission=Decimal("0"),
            dividend_adjustment=Decimal("0"),
            account_equity=Decimal("10000.00"),
            nav=Decimal("10000.00"),
            margin_rate=Decimal("0.02"),
            position_value=Decimal("0"),
            last_transaction_id="12345",
            created_time=datetime.utcnow()
        )
        
        widget = PositionCounterWidget.from_account_summary(summary)
        
        data = widget.data
        assert data["open_positions"] == 0
        assert data["pending_orders"] == 0
        assert data["total_trades"] == 0
        assert data["positions_color"] == "gray"
        assert data["orders_color"] == "gray"

class TestInstrumentSpreadWidget:
    """Test InstrumentSpreadWidget functionality"""
    
    def create_test_spreads(self):
        """Create test instrument spreads"""
        return {
            "EUR_USD": InstrumentSpread(
                instrument="EUR_USD",
                bid=Decimal("1.1000"),
                ask=Decimal("1.1002"),
                spread=Decimal("0.0002"),
                spread_pips=Decimal("2.0"),
                timestamp=datetime.utcnow(),
                liquidity=10,
                tradeable=True
            ),
            "GBP_USD": InstrumentSpread(
                instrument="GBP_USD",
                bid=Decimal("1.2500"),
                ask=Decimal("1.2506"),
                spread=Decimal("0.0006"),
                spread_pips=Decimal("6.0"),
                timestamp=datetime.utcnow(),
                liquidity=8,
                tradeable=False
            ),
            "USD_JPY": InstrumentSpread(
                instrument="USD_JPY",
                bid=Decimal("110.000"),
                ask=Decimal("110.015"),
                spread=Decimal("0.015"),
                spread_pips=Decimal("1.5"),
                timestamp=datetime.utcnow(),
                liquidity=9,
                tradeable=True
            )
        }
    
    def test_from_spreads(self):
        """Test creating widget from spreads"""
        spreads = self.create_test_spreads()
        widget = InstrumentSpreadWidget.from_spreads(spreads)
        
        assert widget.widget_id == "instrument_spreads"
        assert widget.title == "Instrument Spreads"
        
        data = widget.data
        assert data["total_instruments"] == 3
        assert data["tradeable_count"] == 2  # EUR_USD and USD_JPY
        assert len(data["spreads"]) == 3
        
        # Check sorting by spread (USD_JPY should be first with 1.5 pips)
        first_spread = data["spreads"][0]
        assert first_spread["instrument"] == "USD_JPY"
        assert first_spread["spread_pips"] == 1.5
        
        # Check spread colors
        eur_spread = next(s for s in data["spreads"] if s["instrument"] == "EUR_USD")
        assert eur_spread["spread_color"] == "green"  # 2.0 pips = good
        
        gbp_spread = next(s for s in data["spreads"] if s["instrument"] == "GBP_USD")
        assert gbp_spread["spread_color"] == "red"    # 6.0 pips = poor
        assert gbp_spread["status_color"] == "red"    # Not tradeable
    
    def test_spread_color_classification(self):
        """Test spread color classification"""
        spreads = {
            "GOOD": InstrumentSpread(
                instrument="GOOD", bid=Decimal("1.0000"), ask=Decimal("1.0001"),
                spread=Decimal("0.0001"), spread_pips=Decimal("1.0"),
                timestamp=datetime.utcnow(), liquidity=10, tradeable=True
            ),
            "AVERAGE": InstrumentSpread(
                instrument="AVERAGE", bid=Decimal("1.0000"), ask=Decimal("1.0003"),
                spread=Decimal("0.0003"), spread_pips=Decimal("3.0"),
                timestamp=datetime.utcnow(), liquidity=10, tradeable=True
            ),
            "POOR": InstrumentSpread(
                instrument="POOR", bid=Decimal("1.0000"), ask=Decimal("1.0008"),
                spread=Decimal("0.0008"), spread_pips=Decimal("8.0"),
                timestamp=datetime.utcnow(), liquidity=10, tradeable=True
            )
        }
        
        widget = InstrumentSpreadWidget.from_spreads(spreads)
        spreads_data = widget.data["spreads"]
        
        good_spread = next(s for s in spreads_data if s["instrument"] == "GOOD")
        assert good_spread["spread_color"] == "green"  # <= 2 pips
        
        avg_spread = next(s for s in spreads_data if s["instrument"] == "AVERAGE")
        assert avg_spread["spread_color"] == "orange"  # 2-5 pips
        
        poor_spread = next(s for s in spreads_data if s["instrument"] == "POOR")
        assert poor_spread["spread_color"] == "red"    # > 5 pips

class TestBalanceHistoryWidget:
    """Test BalanceHistoryWidget functionality"""
    
    def create_test_history_data(self):
        """Create test balance history data"""
        # Create sample data points
        base_time = datetime.utcnow()
        data_points = []
        
        for i in range(10):
            timestamp = base_time - timedelta(days=9-i)
            balance = Decimal(f"{10000 + i * 100}")
            
            from ..historical_data import BalanceDataPoint
            point = BalanceDataPoint(
                timestamp=timestamp,
                balance=balance,
                unrealized_pl=Decimal("50"),
                realized_pl=Decimal(f"{i * 10}"),
                equity=balance + Decimal("50"),
                margin_used=Decimal("500"),
                margin_available=balance - Decimal("500"),
                open_positions=i % 3,
                pending_orders=i % 2,
                drawdown=Decimal("1.5")
            )
            data_points.append(point)
        
        # Create performance metrics
        metrics = PerformanceMetrics(
            start_balance=Decimal("10000"),
            end_balance=Decimal("10900"),
            total_return=Decimal("900"),
            total_return_percent=Decimal("9.0"),
            max_drawdown=Decimal("150"),
            max_drawdown_percent=Decimal("1.5"),
            sharpe_ratio=None,
            profit_factor=Decimal("2.5"),
            win_rate=Decimal("75.0"),
            average_win=Decimal("120"),
            average_loss=Decimal("48"),
            total_trades=20,
            winning_trades=15,
            losing_trades=5,
            best_trade=Decimal("200"),
            worst_trade=Decimal("-80"),
            consecutive_wins=3,
            consecutive_losses=2,
            trading_days=10
        )
        
        return BalanceHistoryData(
            data_points=data_points,
            start_date=base_time - timedelta(days=9),
            end_date=base_time,
            interval=TimeInterval.DAILY,
            metrics=metrics,
            trend=TrendDirection.UP,
            volatility=Decimal("12.5")
        )
    
    def test_from_history_data(self):
        """Test creating widget from history data"""
        history_data = self.create_test_history_data()
        widget = BalanceHistoryWidget.from_history_data(history_data)
        
        assert widget.widget_id == "balance_history"
        assert widget.title == "Balance History (30 Days)"
        
        data = widget.data
        assert data["period_days"] == 10
        assert data["start_balance"] == 10000.0
        assert data["end_balance"] == 10900.0
        assert data["total_return"] == 900.0
        assert data["total_return_percent"] == 9.0
        assert data["max_drawdown"] == 1.5
        assert data["volatility"] == 12.5
        assert data["trend"] == "up"
        assert data["data_points_count"] == 10
        assert data["return_color"] == "green"  # Positive return
        
        # Check chart data structure
        chart_data = data["chart_data"]
        assert "labels" in chart_data
        assert "datasets" in chart_data
        assert len(chart_data["datasets"]) == 2  # Balance and Equity
    
    def test_negative_return_color(self):
        """Test return color for negative returns"""
        history_data = self.create_test_history_data()
        # Simulate loss
        history_data.data_points[0].balance = Decimal("11000")  # Start higher
        history_data.data_points[-1].balance = Decimal("9500")  # End lower
        
        widget = BalanceHistoryWidget.from_history_data(history_data)
        assert widget.data["return_color"] == "red"

class TestEquityCurveWidget:
    """Test EquityCurveWidget functionality"""
    
    def test_from_history_data(self):
        """Test creating equity curve widget"""
        # Use the same test data as balance history
        from .test_dashboard import TestBalanceHistoryWidget
        test_helper = TestBalanceHistoryWidget()
        history_data = test_helper.create_test_history_data()
        
        widget = EquityCurveWidget.from_history_data(history_data)
        
        assert widget.widget_id == "equity_curve"
        assert widget.title == "Equity Curve & Performance"
        
        data = widget.data
        assert "equity_curve" in data
        assert "drawdown_curve" in data
        assert "performance_metrics" in data
        assert data["trend_direction"] == "up"
        assert data["volatility_percent"] == 12.5
        
        # Check equity curve data
        equity_curve = data["equity_curve"]
        assert len(equity_curve) == 10
        assert all("timestamp" in point for point in equity_curve)
        assert all("equity" in point for point in equity_curve)
        
        # Check chart configuration
        chart_config = data["chart_config"]
        assert chart_config["type"] == "line"
        assert chart_config["responsive"] is True

class TestAccountDashboard:
    """Test AccountDashboard functionality"""
    
    @pytest.fixture
    def mock_account_manager(self):
        """Create mock account manager"""
        manager = AsyncMock()
        manager.get_account_summary.return_value = AccountSummary(
            account_id="test-account",
            currency=AccountCurrency.USD,
            balance=Decimal("10000.00"),
            unrealized_pl=Decimal("150.50"),
            realized_pl=Decimal("-25.75"),
            margin_used=Decimal("500.00"),
            margin_available=Decimal("9500.00"),
            margin_closeout_percent=Decimal("50.0"),
            margin_call_percent=Decimal("100.0"),
            open_position_count=3,
            pending_order_count=2,
            leverage=50,
            financing=Decimal("5.25"),
            commission=Decimal("2.50"),
            dividend_adjustment=Decimal("0.00"),
            account_equity=Decimal("10150.50"),
            nav=Decimal("10150.50"),
            margin_rate=Decimal("0.02"),
            position_value=Decimal("25000.00"),
            last_transaction_id="12345",
            created_time=datetime.utcnow()
        )
        return manager
    
    @pytest.fixture
    def mock_instrument_service(self):
        """Create mock instrument service"""
        service = AsyncMock()
        service.get_current_prices.return_value = {
            "EUR_USD": InstrumentSpread(
                instrument="EUR_USD",
                bid=Decimal("1.1000"),
                ask=Decimal("1.1002"),
                spread=Decimal("0.0002"),
                spread_pips=Decimal("2.0"),
                timestamp=datetime.utcnow(),
                liquidity=10,
                tradeable=True
            )
        }
        return service
    
    @pytest.fixture
    def mock_update_service(self):
        """Create mock update service"""
        service = AsyncMock()
        service.subscribe_to_updates = MagicMock()
        service.watch_instrument = MagicMock()
        return service
    
    @pytest.fixture
    def mock_historical_service(self):
        """Create mock historical service"""
        service = AsyncMock()
        
        # Create minimal test data
        from ..historical_data import BalanceDataPoint, BalanceHistoryData, PerformanceMetrics
        
        data_point = BalanceDataPoint(
            timestamp=datetime.utcnow(),
            balance=Decimal("10000"),
            unrealized_pl=Decimal("100"),
            realized_pl=Decimal("0"),
            equity=Decimal("10100"),
            margin_used=Decimal("200"),
            margin_available=Decimal("9800"),
            open_positions=1,
            pending_orders=0
        )
        
        metrics = PerformanceMetrics(
            start_balance=Decimal("10000"),
            end_balance=Decimal("10100"),
            total_return=Decimal("100"),
            total_return_percent=Decimal("1.0"),
            max_drawdown=Decimal("0"),
            max_drawdown_percent=Decimal("0"),
            sharpe_ratio=None,
            profit_factor=None,
            win_rate=None,
            average_win=None,
            average_loss=None,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            best_trade=None,
            worst_trade=None,
            consecutive_wins=0,
            consecutive_losses=0,
            trading_days=1
        )
        
        history_data = BalanceHistoryData(
            data_points=[data_point],
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            interval=TimeInterval.DAILY,
            metrics=metrics,
            trend=TrendDirection.UP,
            volatility=Decimal("0")
        )
        
        service.get_balance_history.return_value = history_data
        service.record_balance_snapshot = MagicMock()
        return service
    
    @pytest.fixture
    def dashboard(self, mock_account_manager, mock_instrument_service, 
                  mock_update_service, mock_historical_service):
        """Create test dashboard"""
        return AccountDashboard(
            account_manager=mock_account_manager,
            instrument_service=mock_instrument_service,
            update_service=mock_update_service,
            historical_service=mock_historical_service
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, dashboard):
        """Test dashboard initialization"""
        await dashboard.initialize()
        
        # Check that update subscriptions were set up
        assert dashboard.update_service.subscribe_to_updates.call_count == 5
        
        # Check that major pairs are being watched
        expected_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CHF', 'AUD_USD', 'USD_CAD', 'NZD_USD']
        for pair in expected_pairs:
            dashboard.update_service.watch_instrument.assert_any_call(pair)
    
    @pytest.mark.asyncio
    async def test_refresh_all_widgets(self, dashboard):
        """Test refreshing all widgets"""
        widgets = await dashboard.refresh_all_widgets()
        
        # Should have all 6 widget types
        expected_widgets = [
            'account_summary', 'margin_status', 'position_counter',
            'instrument_spreads', 'balance_history', 'equity_curve'
        ]
        
        assert len(widgets) == 6
        for widget_id in expected_widgets:
            assert widget_id in widgets
            assert isinstance(widgets[widget_id], DashboardWidget)
            assert widgets[widget_id].status == WidgetStatus.READY
    
    @pytest.mark.asyncio
    async def test_get_widget(self, dashboard):
        """Test getting specific widget"""
        # Initialize dashboard first
        await dashboard.refresh_all_widgets()
        
        # Get specific widget
        widget = await dashboard.get_widget('account_summary')
        assert widget is not None
        assert widget.widget_id == 'account_summary'
        
        # Get non-existent widget
        widget = await dashboard.get_widget('non_existent')
        assert widget is None
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary(self, dashboard):
        """Test getting dashboard summary"""
        summary = await dashboard.get_dashboard_summary()
        
        assert 'account_id' in summary
        assert 'currency' in summary
        assert 'equity' in summary
        assert 'balance' in summary
        assert 'unrealized_pl' in summary
        assert 'margin_level' in summary
        assert 'open_positions' in summary
        assert 'pending_orders' in summary
        assert 'status' in summary
        
        assert summary['account_id'] == 'test-account'
        assert summary['currency'] == 'USD'
        assert summary['equity'] == 10150.50
    
    def test_update_callback_management(self, dashboard):
        """Test update callback management"""
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        # Add callbacks
        dashboard.add_update_callback(callback1)
        dashboard.add_update_callback(callback2)
        
        assert len(dashboard.update_callbacks) == 2
        assert callback1 in dashboard.update_callbacks
        assert callback2 in dashboard.update_callbacks
        
        # Remove callback
        dashboard.remove_update_callback(callback1)
        assert len(dashboard.update_callbacks) == 1
        assert callback1 not in dashboard.update_callbacks
        assert callback2 in dashboard.update_callbacks
    
    def test_get_metrics(self, dashboard):
        """Test getting dashboard metrics"""
        metrics = dashboard.get_metrics()
        
        assert 'widget_updates' in metrics
        assert 'update_errors' in metrics
        assert 'last_full_refresh' in metrics
        assert 'refresh_duration' in metrics

class TestWebSocketMessage:
    """Test WebSocketMessage functionality"""
    
    def test_success_message(self):
        """Test creating success message"""
        data = {"balance": 10000, "currency": "USD"}
        message_str = WebSocketMessage.success("account_update", data, "req-123")
        
        message = json.loads(message_str)
        assert message["type"] == "account_update"
        assert message["status"] == "success"
        assert message["data"]["balance"] == 10000
        assert message["request_id"] == "req-123"
        assert "timestamp" in message
    
    def test_error_message(self):
        """Test creating error message"""
        message_str = WebSocketMessage.error("invalid_request", "Missing parameter", "req-456")
        
        message = json.loads(message_str)
        assert message["type"] == "invalid_request"
        assert message["status"] == "error"
        assert message["error"] == "Missing parameter"
        assert message["request_id"] == "req-456"
    
    def test_update_message(self):
        """Test creating update message"""
        data = {"spreads": {"EUR_USD": {"bid": 1.1000, "ask": 1.1002}}}
        message_str = WebSocketMessage.update("spreads_update", data)
        
        message = json.loads(message_str)
        assert message["type"] == "update"
        assert message["update_type"] == "spreads_update"
        assert message["data"]["spreads"]["EUR_USD"]["bid"] == 1.1000

class TestDashboardWebSocketHandler:
    """Test DashboardWebSocketHandler functionality"""
    
    @pytest.fixture
    def mock_dashboard(self):
        """Create mock dashboard"""
        dashboard = AsyncMock()
        dashboard.get_dashboard_summary.return_value = {
            "account_id": "test",
            "currency": "USD",
            "status": "operational"
        }
        dashboard.get_all_widgets.return_value = {}
        dashboard.refresh_all_widgets.return_value = {}
        dashboard.get_widget.return_value = None
        return dashboard
    
    @pytest.fixture
    def websocket_handler(self, mock_dashboard):
        """Create test WebSocket handler"""
        return DashboardWebSocketHandler(dashboard=mock_dashboard, port=8766)
    
    def test_initialization(self, websocket_handler):
        """Test WebSocket handler initialization"""
        assert websocket_handler.port == 8766
        assert len(websocket_handler.clients) == 0
        assert not websocket_handler.is_running
        assert websocket_handler.metrics["connected_clients"] == 0
    
    @pytest.mark.asyncio
    async def test_start_stop_server(self, websocket_handler):
        """Test starting and stopping WebSocket server"""
        # Mock websockets.serve
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_serve.return_value = mock_server
            
            # Start server
            await websocket_handler.start_server()
            assert websocket_handler.is_running
            assert websocket_handler.server is not None
            
            # Stop server
            await websocket_handler.stop_server()
            assert not websocket_handler.is_running
            mock_server.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, websocket_handler):
        """Test broadcasting message to clients"""
        # Create mock clients
        client1 = AsyncMock()
        client2 = AsyncMock()
        
        websocket_handler.clients.add(client1)
        websocket_handler.clients.add(client2)
        
        # Broadcast message
        await websocket_handler.broadcast_message("test_message", {"data": "value"})
        
        # Both clients should receive message
        client1.send.assert_called_once()
        client2.send.assert_called_once()
        
        # Check metrics
        assert websocket_handler.metrics["messages_sent"] == 2
    
    @pytest.mark.asyncio
    async def test_client_disconnection_handling(self, websocket_handler):
        """Test handling client disconnections during broadcast"""
        # Create clients - one working, one failing
        working_client = AsyncMock()
        failing_client = AsyncMock()
        failing_client.send.side_effect = websockets.exceptions.ConnectionClosed(None, None)
        
        websocket_handler.clients.add(working_client)
        websocket_handler.clients.add(failing_client)
        
        # Broadcast message
        await websocket_handler.broadcast_message("test", {"data": "value"})
        
        # Failing client should be removed
        assert failing_client not in websocket_handler.clients
        assert working_client in websocket_handler.clients
        assert len(websocket_handler.clients) == 1
    
    def test_get_metrics(self, websocket_handler):
        """Test getting WebSocket handler metrics"""
        metrics = websocket_handler.get_metrics()
        
        assert 'connected_clients' in metrics
        assert 'messages_sent' in metrics
        assert 'messages_received' in metrics
        assert 'errors' in metrics
        assert 'uptime_seconds' in metrics

if __name__ == "__main__":
    pytest.main([__file__, "-v"])