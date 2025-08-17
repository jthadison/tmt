"""
Tests for Audit Trail System
Story 8.8 - Task 5 tests
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_trail import (
    AuditTrailManager, AuditRecord, AuditEventType, SignalExecutionTrail, AuditReport
)


class TestAuditTrailManager:
    """Test suite for AuditTrailManager"""
    
    @pytest.fixture
    def audit_manager(self):
        """Audit trail manager instance"""
        return AuditTrailManager()
        
    @pytest.mark.asyncio
    async def test_record_signal_generated(self, audit_manager):
        """Test recording signal generation"""
        signal_id = "signal_123"
        account_id = "account_456"
        signal_data = {
            "instrument": "EUR_USD",
            "direction": "long",
            "confidence": 0.85
        }
        correlation_id = "corr_789"
        
        audit_id = await audit_manager.record_signal_generated(
            signal_id, account_id, signal_data, correlation_id
        )
        
        # Check audit record was created
        assert audit_id in audit_manager.audit_records
        record = audit_manager.audit_records[audit_id]
        
        assert record.event_type == AuditEventType.SIGNAL_GENERATED
        assert record.signal_id == signal_id
        assert record.account_id == account_id
        assert record.event_data == signal_data
        assert record.correlation_id == correlation_id
        assert record.source_component == "signal_generator"
        
        # Check execution trail was created
        assert signal_id in audit_manager.execution_trails
        trail = audit_manager.execution_trails[signal_id]
        
        assert trail.signal_id == signal_id
        assert trail.execution_success is False
        assert len(trail.transaction_ids) == 0
        
    @pytest.mark.asyncio
    async def test_record_risk_check(self, audit_manager):
        """Test recording risk check"""
        signal_id = "signal_123"
        account_id = "account_456"
        risk_data = {"risk_score": 75.5, "max_position_size": 1000}
        risk_score = 75.5
        passed = True
        
        # First create the signal
        await audit_manager.record_signal_generated(
            signal_id, account_id, {"test": "data"}
        )
        
        audit_id = await audit_manager.record_risk_check(
            signal_id, account_id, risk_data, risk_score, passed
        )
        
        # Check audit record
        record = audit_manager.audit_records[audit_id]
        assert record.event_type == AuditEventType.RISK_CHECK
        assert record.signal_id == signal_id
        assert record.risk_score == risk_score
        assert "PASSED" in record.notes
        
        # Check it was added to execution trail
        trail = audit_manager.execution_trails[signal_id]
        assert len(trail.risk_checks) == 1
        assert trail.risk_checks[0].audit_id == audit_id
        
    @pytest.mark.asyncio
    async def test_record_compliance_check(self, audit_manager):
        """Test recording compliance check"""
        signal_id = "signal_123"
        account_id = "account_456"
        compliance_data = {"rule": "max_daily_trades", "limit": 10, "current": 5}
        status = "PASSED"
        
        # First create the signal
        await audit_manager.record_signal_generated(
            signal_id, account_id, {"test": "data"}
        )
        
        audit_id = await audit_manager.record_compliance_check(
            signal_id, account_id, compliance_data, status
        )
        
        # Check audit record
        record = audit_manager.audit_records[audit_id]
        assert record.event_type == AuditEventType.COMPLIANCE_CHECK
        assert record.compliance_status == status
        assert record.source_component == "compliance_engine"
        
        # Check it was added to execution trail
        trail = audit_manager.execution_trails[signal_id]
        assert len(trail.compliance_checks) == 1
        assert trail.compliance_checks[0].compliance_status == status
        
    @pytest.mark.asyncio
    async def test_link_signal_to_transaction(self, audit_manager):
        """Test linking signal to transaction"""
        signal_id = "signal_123"
        transaction_id = "txn_456"
        account_id = "account_789"
        execution_latency_ms = 150.5
        
        # First create the signal
        await audit_manager.record_signal_generated(
            signal_id, account_id, {"test": "data"}
        )
        
        audit_id = await audit_manager.link_signal_to_transaction(
            signal_id, transaction_id, account_id, execution_latency_ms
        )
        
        # Check audit record
        record = audit_manager.audit_records[audit_id]
        assert record.event_type == AuditEventType.SIGNAL_EXECUTED
        assert record.signal_id == signal_id
        assert record.transaction_id == transaction_id
        assert record.source_component == "execution_engine"
        
        # Check signal mapping
        assert audit_manager.signal_mappings[transaction_id] == signal_id
        
        # Check execution trail was updated
        trail = audit_manager.execution_trails[signal_id]
        assert trail.execution_success is True
        assert trail.execution_latency_ms == execution_latency_ms
        assert transaction_id in trail.transaction_ids
        assert trail.execution_timestamp is not None
        
    @pytest.mark.asyncio
    async def test_record_trade_event(self, audit_manager):
        """Test recording trade events"""
        transaction_id = "txn_123"
        account_id = "account_456"
        trade_data = {
            "trade_id": "trade_789",
            "order_id": "order_101",
            "instrument": "EUR_USD",
            "units": 1000
        }
        
        audit_id = await audit_manager.record_trade_event(
            transaction_id, account_id, AuditEventType.TRADE_OPENED, trade_data
        )
        
        record = audit_manager.audit_records[audit_id]
        assert record.event_type == AuditEventType.TRADE_OPENED
        assert record.transaction_id == transaction_id
        assert record.trade_id == trade_data["trade_id"]
        assert record.order_id == trade_data["order_id"]
        assert record.source_component == "trade_manager"
        
    @pytest.mark.asyncio
    async def test_get_signal_execution_trail(self, audit_manager):
        """Test retrieving signal execution trail"""
        signal_id = "signal_123"
        account_id = "account_456"
        
        # Create signal and add some checks
        await audit_manager.record_signal_generated(signal_id, account_id, {"test": "data"})
        await audit_manager.record_risk_check(signal_id, account_id, {"score": 50}, 50, True)
        await audit_manager.record_compliance_check(signal_id, account_id, {}, "PASSED")
        await audit_manager.link_signal_to_transaction(signal_id, "txn_123", account_id, 100)
        
        trail = await audit_manager.get_signal_execution_trail(signal_id)
        
        assert trail is not None
        assert trail.signal_id == signal_id
        assert len(trail.risk_checks) == 1
        assert len(trail.compliance_checks) == 1
        assert len(trail.transaction_ids) == 1
        assert trail.execution_success is True
        
    @pytest.mark.asyncio
    async def test_get_transaction_audit_trail(self, audit_manager):
        """Test retrieving transaction audit trail"""
        transaction_id = "txn_123"
        account_id = "account_456"
        
        # Create some audit records for the transaction
        await audit_manager.record_trade_event(
            transaction_id, account_id, AuditEventType.TRADE_OPENED, {"test": "data"}
        )
        await audit_manager.record_trade_event(
            transaction_id, account_id, AuditEventType.TRADE_CLOSED, {"test": "data"}
        )
        
        trail = await audit_manager.get_transaction_audit_trail(transaction_id)
        
        assert len(trail) == 2
        assert all(record.transaction_id == transaction_id for record in trail)
        
    @pytest.mark.asyncio
    async def test_generate_audit_report(self, audit_manager):
        """Test generating comprehensive audit report"""
        # Create test data
        signal_id1 = "signal_1"
        signal_id2 = "signal_2"
        account_id = "account_123"
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Create some audit records
        await audit_manager.record_signal_generated(signal_id1, account_id, {"test": "data1"})
        await audit_manager.record_signal_generated(signal_id2, account_id, {"test": "data2"})
        
        # Add risk and compliance checks
        await audit_manager.record_risk_check(signal_id1, account_id, {"score": 90}, 90, False)
        await audit_manager.record_compliance_check(signal_id2, account_id, {}, "FAILED")
        
        # Link one signal to transaction
        await audit_manager.link_signal_to_transaction(signal_id1, "txn_1", account_id, 200)
        
        # Generate report
        report = await audit_manager.generate_audit_report(start_date, end_date, [account_id])
        
        assert isinstance(report, AuditReport)
        assert report.total_signals == 2
        assert report.executed_signals == 1
        assert report.failed_signals == 1
        assert len(report.compliance_violations) == 1
        assert len(report.risk_events) == 1  # High risk score
        assert len(report.signal_execution_trails) == 2
        
    @pytest.mark.asyncio
    async def test_cleanup_old_records(self, audit_manager):
        """Test cleanup of old audit records"""
        # Create old records
        old_signal_id = "old_signal"
        recent_signal_id = "recent_signal"
        account_id = "account_123"
        
        # Mock old timestamps
        old_time = datetime.now(timezone.utc) - timedelta(days=3000)  # Very old
        recent_time = datetime.now(timezone.utc)
        
        # Create records
        await audit_manager.record_signal_generated(old_signal_id, account_id, {"test": "old"})
        await audit_manager.record_signal_generated(recent_signal_id, account_id, {"test": "recent"})
        
        # Manually set old timestamp
        for record in audit_manager.audit_records.values():
            if record.signal_id == old_signal_id:
                record.timestamp = old_time
                
        if old_signal_id in audit_manager.execution_trails:
            audit_manager.execution_trails[old_signal_id].signal_timestamp = old_time
        
        # Count before cleanup
        records_before = len(audit_manager.audit_records)
        trails_before = len(audit_manager.execution_trails)
        
        # Run cleanup
        await audit_manager.cleanup_old_records()
        
        # Should have fewer records now
        records_after = len(audit_manager.audit_records)
        trails_after = len(audit_manager.execution_trails)
        
        assert records_after <= records_before
        assert trails_after <= trails_before
        
        # Recent signal should still exist
        recent_exists = any(
            record.signal_id == recent_signal_id 
            for record in audit_manager.audit_records.values()
        )
        assert recent_exists
        
    def test_get_audit_statistics(self, audit_manager):
        """Test audit statistics collection"""
        stats = audit_manager.get_audit_statistics()
        
        assert 'total_audit_records' in stats
        assert 'total_execution_trails' in stats
        assert 'event_type_counts' in stats
        assert 'signal_mappings' in stats
        
        assert isinstance(stats['total_audit_records'], int)
        assert isinstance(stats['total_execution_trails'], int)
        assert isinstance(stats['event_type_counts'], dict)
        assert isinstance(stats['signal_mappings'], int)
        
    def test_audit_record_serialization(self):
        """Test audit record serialization"""
        record = AuditRecord(
            audit_id="test_123",
            event_type=AuditEventType.SIGNAL_GENERATED,
            timestamp=datetime(2024, 1, 15, 10, 0),
            account_id="account_456",
            signal_id="signal_789",
            event_data={"test": "data"},
            risk_score=75.5
        )
        
        data = record.to_dict()
        
        assert data['audit_id'] == "test_123"
        assert data['event_type'] == "SIGNAL_GENERATED"
        assert '2024-01-15T10:00:00' in data['timestamp']
        assert data['risk_score'] == 75.5
        
    def test_signal_execution_trail_serialization(self):
        """Test signal execution trail serialization"""
        trail = SignalExecutionTrail(
            signal_id="signal_123",
            signal_timestamp=datetime(2024, 1, 15, 10, 0),
            execution_timestamp=datetime(2024, 1, 15, 10, 1),
            transaction_ids=["txn_1", "txn_2"],
            risk_checks=[],
            compliance_checks=[],
            execution_latency_ms=1000.0,
            execution_success=True
        )
        
        data = trail.to_dict()
        
        assert data['signal_id'] == "signal_123"
        assert '2024-01-15T10:00:00' in data['signal_timestamp']
        assert '2024-01-15T10:01:00' in data['execution_timestamp']
        assert data['transaction_ids'] == ["txn_1", "txn_2"]
        assert data['execution_latency_ms'] == 1000.0
        assert data['execution_success'] is True
        
    def test_identify_system_anomalies(self, audit_manager):
        """Test system anomaly identification"""
        # Create trails with anomalies
        trails = [
            SignalExecutionTrail(
                signal_id="high_latency_signal",
                signal_timestamp=datetime.now(timezone.utc),
                execution_timestamp=datetime.now(timezone.utc),
                transaction_ids=["txn_1"],
                risk_checks=[],
                compliance_checks=[],
                execution_latency_ms=10000.0,  # High latency
                execution_success=True
            ),
            SignalExecutionTrail(
                signal_id="failed_signal",
                signal_timestamp=datetime.now(timezone.utc),
                execution_timestamp=None,
                transaction_ids=[],
                risk_checks=[],
                compliance_checks=[],
                execution_latency_ms=None,
                execution_success=False,
                failure_reason="Network timeout"
            )
        ]
        
        anomalies = audit_manager._identify_system_anomalies([], trails)
        
        assert len(anomalies) == 2
        
        # Check high latency anomaly
        high_latency_anomaly = next(
            a for a in anomalies 
            if a.event_data.get('anomaly_type') == 'HIGH_LATENCY'
        )
        assert high_latency_anomaly.signal_id == "high_latency_signal"
        assert high_latency_anomaly.event_data['latency_ms'] == 10000.0
        
        # Check execution failure anomaly
        failure_anomaly = next(
            a for a in anomalies 
            if a.event_data.get('anomaly_type') == 'EXECUTION_FAILURE'
        )
        assert failure_anomaly.signal_id == "failed_signal"
        assert failure_anomaly.event_data['reason'] == "Network timeout"