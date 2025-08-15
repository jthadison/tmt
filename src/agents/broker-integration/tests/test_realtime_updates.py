"""
Tests for Real-time Updates System - Story 8.2
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime
import json

from ..realtime_updates import (
    AccountUpdateService,
    AccountUpdate,
    UpdateType,
    ChangeDetector,
    UpdateBatcher
)
from ..account_manager import AccountSummary, AccountCurrency
from ..instrument_service import InstrumentSpread

class TestChangeDetector:
    """Test ChangeDetector functionality"""
    
    def test_initialization(self):
        """Test change detector initialization"""
        detector = ChangeDetector()
        assert len(detector.previous_hashes) == 0
        assert len(detector.previous_data) == 0
    
    def test_first_change_detection(self):
        """Test change detection on first data"""
        detector = ChangeDetector()
        
        data = {"balance": "10000", "currency": "USD"}
        changed = detector.has_changed("account", data)
        
        assert changed is True
        assert "account" in detector.previous_hashes
        assert detector.previous_data["account"] == data
    
    def test_no_change_detection(self):
        """Test no change when data is same"""
        detector = ChangeDetector()
        
        data = {"balance": "10000", "currency": "USD"}
        
        # First call
        changed1 = detector.has_changed("account", data)
        assert changed1 is True
        
        # Second call with same data
        changed2 = detector.has_changed("account", data)
        assert changed2 is False
    
    def test_change_detection(self):
        """Test change detection when data changes"""
        detector = ChangeDetector()
        
        data1 = {"balance": "10000", "currency": "USD"}
        data2 = {"balance": "10100", "currency": "USD"}
        
        # First call
        changed1 = detector.has_changed("account", data1)
        assert changed1 is True
        
        # Second call with different data
        changed2 = detector.has_changed("account", data2)
        assert changed2 is True
        assert detector.previous_data["account"] == data2
    
    def test_get_changed_fields_new_data(self):
        """Test getting changed fields for new data"""
        detector = ChangeDetector()
        
        data = {"balance": "10000", "currency": "USD", "equity": "10050"}
        changed_fields = detector.get_changed_fields("account", data)
        
        assert set(changed_fields) == {"balance", "currency", "equity"}
    
    def test_get_changed_fields_existing_data(self):
        """Test getting changed fields for modified data"""
        detector = ChangeDetector()
        
        # First set of data
        data1 = {"balance": "10000", "currency": "USD", "equity": "10000"}
        detector.has_changed("account", data1)
        
        # Modified data
        data2 = {"balance": "10100", "currency": "USD", "equity": "10150"}
        changed_fields = detector.get_changed_fields("account", data2)
        
        assert set(changed_fields) == {"balance", "equity"}
        assert "currency" not in changed_fields

class TestUpdateBatcher:
    """Test UpdateBatcher functionality"""
    
    def test_initialization(self):
        """Test update batcher initialization"""
        batcher = UpdateBatcher(batch_size=5, batch_timeout=1.0)
        
        assert batcher.batch_size == 5
        assert batcher.batch_timeout == 1.0
        assert len(batcher.pending_updates) == 0
    
    @pytest.mark.asyncio
    async def test_batch_by_size(self):
        """Test batching by size"""
        batcher = UpdateBatcher(batch_size=2, batch_timeout=10.0)
        
        # Create test updates
        update1 = AccountUpdate(
            update_type=UpdateType.BALANCE,
            timestamp=datetime.utcnow(),
            data={"balance": 10000},
            changed_fields=["balance"],
            account_id="test"
        )
        
        update2 = AccountUpdate(
            update_type=UpdateType.MARGIN,
            timestamp=datetime.utcnow(),
            data={"margin_used": 500},
            changed_fields=["margin_used"],
            account_id="test"
        )
        
        # Add first update - should not trigger batch
        batch1 = await batcher.add_update(update1)
        assert batch1 is None
        assert len(batcher.pending_updates) == 1
        
        # Add second update - should trigger batch
        batch2 = await batcher.add_update(update2)
        assert batch2 is not None
        assert len(batch2) == 2
        assert len(batcher.pending_updates) == 0
    
    @pytest.mark.asyncio
    async def test_batch_by_timeout(self):
        """Test batching by timeout"""
        batcher = UpdateBatcher(batch_size=10, batch_timeout=0.1)
        
        update = AccountUpdate(
            update_type=UpdateType.BALANCE,
            timestamp=datetime.utcnow(),
            data={"balance": 10000},
            changed_fields=["balance"],
            account_id="test"
        )
        
        # Add update
        batch1 = await batcher.add_update(update)
        assert batch1 is None
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Add another update - should trigger batch due to timeout
        update2 = AccountUpdate(
            update_type=UpdateType.MARGIN,
            timestamp=datetime.utcnow(),
            data={"margin": 500},
            changed_fields=["margin"],
            account_id="test"
        )
        
        batch2 = await batcher.add_update(update2)
        assert batch2 is not None
        assert len(batch2) == 2
    
    @pytest.mark.asyncio
    async def test_flush(self):
        """Test manual flush"""
        batcher = UpdateBatcher(batch_size=10, batch_timeout=10.0)
        
        # Add some updates
        for i in range(3):
            update = AccountUpdate(
                update_type=UpdateType.BALANCE,
                timestamp=datetime.utcnow(),
                data={"balance": 10000 + i},
                changed_fields=["balance"],
                account_id="test"
            )
            await batcher.add_update(update)
        
        assert len(batcher.pending_updates) == 3
        
        # Flush
        batch = await batcher.flush()
        assert len(batch) == 3
        assert len(batcher.pending_updates) == 0

class TestAccountUpdate:
    """Test AccountUpdate functionality"""
    
    def test_to_json(self):
        """Test JSON serialization"""
        update = AccountUpdate(
            update_type=UpdateType.BALANCE,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            data={"balance": 10000.50, "currency": "USD"},
            changed_fields=["balance"],
            account_id="test-account"
        )
        
        json_str = update.to_json()
        data = json.loads(json_str)
        
        assert data['type'] == 'balance'
        assert data['account_id'] == 'test-account'
        assert data['data']['balance'] == 10000.50
        assert data['changed_fields'] == ['balance']
        assert 'timestamp' in data

class TestAccountUpdateService:
    """Test AccountUpdateService functionality"""
    
    @pytest.fixture
    def mock_account_manager(self):
        """Create mock account manager"""
        manager = AsyncMock()
        manager.account_id = "test-account"
        return manager
    
    @pytest.fixture
    def mock_instrument_service(self):
        """Create mock instrument service"""
        service = AsyncMock()
        return service
    
    @pytest.fixture
    def update_service(self, mock_account_manager, mock_instrument_service):
        """Create update service"""
        return AccountUpdateService(
            account_manager=mock_account_manager,
            instrument_service=mock_instrument_service,
            update_interval=1  # Short interval for testing
        )
    
    def create_mock_account_summary(self):
        """Create mock account summary"""
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
    
    def test_initialization(self, update_service):
        """Test update service initialization"""
        assert update_service.update_interval == 1
        assert len(update_service.websocket_clients) == 0
        assert not update_service.is_running
        assert len(update_service.watched_instruments) == 0
        
        # Check update callbacks are initialized
        for update_type in UpdateType:
            assert update_type in update_service.update_callbacks
            assert len(update_service.update_callbacks[update_type]) == 0
    
    def test_websocket_client_management(self, update_service):
        """Test WebSocket client management"""
        # Create mock clients
        client1 = MagicMock()
        client2 = MagicMock()
        
        # Add clients
        update_service.add_websocket_client(client1)
        assert len(update_service.websocket_clients) == 1
        assert update_service.metrics['connected_clients'] == 1
        
        update_service.add_websocket_client(client2)
        assert len(update_service.websocket_clients) == 2
        assert update_service.metrics['connected_clients'] == 2
        
        # Remove client
        update_service.remove_websocket_client(client1)
        assert len(update_service.websocket_clients) == 1
        assert update_service.metrics['connected_clients'] == 1
        assert client2 in update_service.websocket_clients
    
    def test_instrument_watching(self, update_service):
        """Test instrument watching"""
        # Add instruments to watch
        update_service.watch_instrument("EUR_USD")
        update_service.watch_instrument("GBP_USD")
        
        assert len(update_service.watched_instruments) == 2
        assert "EUR_USD" in update_service.watched_instruments
        assert "GBP_USD" in update_service.watched_instruments
        
        # Remove instrument
        update_service.unwatch_instrument("EUR_USD")
        assert len(update_service.watched_instruments) == 1
        assert "EUR_USD" not in update_service.watched_instruments
        assert "GBP_USD" in update_service.watched_instruments
    
    def test_update_callback_subscription(self, update_service):
        """Test update callback subscription"""
        # Create mock callback
        callback = MagicMock()
        
        # Subscribe to updates
        update_service.subscribe_to_updates(UpdateType.BALANCE, callback)
        
        assert callback in update_service.update_callbacks[UpdateType.BALANCE]
        assert len(update_service.update_callbacks[UpdateType.BALANCE]) == 1
    
    @pytest.mark.asyncio
    async def test_start_stop(self, update_service):
        """Test starting and stopping update service"""
        assert not update_service.is_running
        
        # Start service
        await update_service.start()
        assert update_service.is_running
        assert update_service.update_task is not None
        assert update_service.spread_task is not None
        
        # Stop service
        await update_service.stop()
        assert not update_service.is_running
    
    @pytest.mark.asyncio
    async def test_account_update_detection(self, update_service, mock_account_manager):
        """Test account update detection"""
        # Setup mock account summary
        summary = self.create_mock_account_summary()
        mock_account_manager.get_account_summary.return_value = summary
        mock_account_manager.get_open_positions.return_value = []
        mock_account_manager.get_pending_orders.return_value = []
        mock_account_manager.get_margin_status.return_value = {"margin_used": 500}
        mock_account_manager.get_account_changes.return_value = {}
        
        # Create callback to capture updates
        captured_updates = []
        
        async def capture_update(update):
            captured_updates.append(update)
        
        update_service.subscribe_to_updates(UpdateType.ACCOUNT_SUMMARY, capture_update)
        
        # Simulate one update cycle
        await update_service._account_update_loop()
        
        # Should have detected change (first time)
        assert len(captured_updates) > 0
        update = captured_updates[0]
        assert update.update_type == UpdateType.ACCOUNT_SUMMARY
        assert update.account_id == "test-account"
    
    @pytest.mark.asyncio
    async def test_spread_update_detection(self, update_service, mock_instrument_service):
        """Test spread update detection"""
        # Add instruments to watch
        update_service.watch_instrument("EUR_USD")
        
        # Setup mock spreads
        eur_spread = InstrumentSpread(
            instrument="EUR_USD",
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            spread=Decimal("0.0002"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.utcnow(),
            liquidity=10,
            tradeable=True
        )
        
        mock_instrument_service.get_current_prices.return_value = {"EUR_USD": eur_spread}
        
        # Create callback to capture updates
        captured_updates = []
        
        async def capture_update(update):
            captured_updates.append(update)
        
        update_service.subscribe_to_updates(UpdateType.SPREADS, capture_update)
        
        # Simulate one spread update cycle
        await update_service._spread_update_loop()
        
        # Should have detected spread change
        assert len(captured_updates) > 0
        update = captured_updates[0]
        assert update.update_type == UpdateType.SPREADS
        assert "spreads" in update.data
    
    @pytest.mark.asyncio
    async def test_force_update(self, update_service):
        """Test force update functionality"""
        # Add some data to change detector
        update_service.change_detector.has_changed("test", {"data": "value"})
        assert len(update_service.change_detector.previous_hashes) == 1
        
        # Force update should clear change detection
        await update_service.force_update()
        assert len(update_service.change_detector.previous_hashes) == 0
        assert len(update_service.change_detector.previous_data) == 0
    
    @pytest.mark.asyncio
    async def test_websocket_message_sending(self, update_service):
        """Test WebSocket message sending"""
        # Create mock WebSocket clients
        client1 = AsyncMock()
        client2 = AsyncMock()
        
        update_service.add_websocket_client(client1)
        update_service.add_websocket_client(client2)
        
        # Create test update
        update = AccountUpdate(
            update_type=UpdateType.BALANCE,
            timestamp=datetime.utcnow(),
            data={"balance": 10000},
            changed_fields=["balance"],
            account_id="test"
        )
        
        # Process update
        await update_service._process_update(update)
        
        # Both clients should receive the message
        client1.send.assert_called()
        client2.send.assert_called()
        
        # Check metrics
        assert update_service.metrics['messages_sent'] > 0
        assert update_service.metrics['batches_sent'] > 0
    
    @pytest.mark.asyncio
    async def test_websocket_client_disconnection_handling(self, update_service):
        """Test handling of disconnected WebSocket clients"""
        # Create mock clients - one working, one that will fail
        working_client = AsyncMock()
        failing_client = AsyncMock()
        failing_client.send.side_effect = Exception("Connection closed")
        
        update_service.add_websocket_client(working_client)
        update_service.add_websocket_client(failing_client)
        
        assert len(update_service.websocket_clients) == 2
        
        # Create test update
        update = AccountUpdate(
            update_type=UpdateType.BALANCE,
            timestamp=datetime.utcnow(),
            data={"balance": 10000},
            changed_fields=["balance"],
            account_id="test"
        )
        
        # Process update
        await update_service._process_update(update)
        
        # Working client should receive message
        working_client.send.assert_called()
        
        # Failing client should be removed
        assert len(update_service.websocket_clients) == 1
        assert working_client in update_service.websocket_clients
        assert failing_client not in update_service.websocket_clients
    
    def test_get_metrics(self, update_service):
        """Test metrics retrieval"""
        metrics = update_service.get_metrics()
        
        assert 'updates_sent' in metrics
        assert 'batches_sent' in metrics
        assert 'errors' in metrics
        assert 'connected_clients' in metrics
        assert 'last_update' in metrics
        
        # Metrics should be a copy, not reference
        metrics['test'] = 'value'
        original_metrics = update_service.get_metrics()
        assert 'test' not in original_metrics

if __name__ == "__main__":
    pytest.main([__file__, "-v"])