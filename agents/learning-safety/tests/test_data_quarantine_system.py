"""
Tests for Data Quarantine System

Tests quarantine data storage, decision engine, manual review workflow,
release mechanisms, and analytics reporting.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from data_quarantine_system import (
    DataQuarantineSystem,
    QuarantineStorage,
    QuarantineDecisionEngine,
    ManualReviewWorkflow,
    QuarantineRecord,
    QuarantineStatus,
    DataType,
    ReviewDecision,
    ReviewResult,
    QuarantineMetadata
)
from market_condition_detector import (
    MarketConditionAnomaly,
    MarketConditionType,
    Severity
)
from performance_anomaly_detector import TradeResult


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_anomaly():
    """Create sample anomaly for testing"""
    return MarketConditionAnomaly(
        detection_id="test_anomaly_001",
        timestamp=datetime.utcnow(),
        condition_type=MarketConditionType.FLASH_CRASH,
        severity=Severity.HIGH,
        confidence=0.85,
        observed_value=0.08,
        expected_value=0.02,
        threshold=0.05,
        deviation_magnitude=0.03,
        symbol="EURUSD",
        description="Suspicious market crash detected",
        potential_causes=["Market manipulation", "System error"],
        learning_safe=False,
        quarantine_recommended=True,
        lockout_duration_minutes=120
    )


@pytest.fixture
def sample_trade_data():
    """Create sample trade data for quarantine testing"""
    trades = []
    base_time = datetime.utcnow()
    
    for i in range(10):
        trade = TradeResult(
            trade_id=f"trade_{i}",
            timestamp=base_time + timedelta(minutes=i*30),
            symbol="EURUSD",
            side="buy",
            entry_price=Decimal("1.0500"),
            exit_price=Decimal("1.0550"),
            quantity=Decimal("10000"),
            profit_loss=Decimal("50"),
            duration_minutes=30
        )
        trades.append(trade)
    
    return trades


@pytest.fixture
def sample_review_result():
    """Create sample review result"""
    return ReviewResult(
        reviewer_id="test_reviewer",
        review_timestamp=datetime.utcnow(),
        decision=ReviewDecision.APPROVE_ALL,
        confidence_score=0.9,
        review_notes="Data appears clean after manual inspection",
        data_quality_assessment={"completeness": 1.0, "accuracy": 0.95},
        recommended_action="Release for learning"
    )


class TestQuarantineStorage:
    """Test quarantine storage functionality"""
    
    def test_store_and_retrieve_data(self, temp_storage_dir, sample_trade_data):
        """Test storing and retrieving quarantined data"""
        storage = QuarantineStorage(temp_storage_dir)
        
        # Store data
        quarantine_id = "test_q_001"
        storage_info = storage.store_data(quarantine_id, DataType.TRADE_RESULT, sample_trade_data)
        
        assert storage_info["data_count"] == 10
        assert storage_info["data_size_bytes"] > 0
        assert storage_info["data_hash"] is not None
        
        # Retrieve data
        retrieved_data = storage.retrieve_data(quarantine_id, DataType.TRADE_RESULT)
        
        assert len(retrieved_data) == 10
        # Note: After serialization/deserialization, objects become dicts
        assert retrieved_data[0]["trade_id"] == "trade_0"
        assert retrieved_data[0]["symbol"] == "EURUSD"
    
    def test_data_integrity_verification(self, temp_storage_dir, sample_trade_data):
        """Test data integrity checking"""
        storage = QuarantineStorage(temp_storage_dir)
        
        # Store data
        quarantine_id = "test_q_002"
        storage.store_data(quarantine_id, DataType.TRADE_RESULT, sample_trade_data)
        
        # Retrieve with integrity check
        retrieved_data = storage.retrieve_data(quarantine_id, DataType.TRADE_RESULT, verify_integrity=True)
        assert len(retrieved_data) == 10
        
        # Retrieve without integrity check should also work
        retrieved_data_no_check = storage.retrieve_data(quarantine_id, DataType.TRADE_RESULT, verify_integrity=False)
        assert len(retrieved_data_no_check) == 10
    
    def test_delete_data(self, temp_storage_dir, sample_trade_data):
        """Test secure data deletion"""
        storage = QuarantineStorage(temp_storage_dir)
        
        # Store data
        quarantine_id = "test_q_003"
        storage.store_data(quarantine_id, DataType.TRADE_RESULT, sample_trade_data)
        
        # Verify data exists
        storage_path = Path(temp_storage_dir) / DataType.TRADE_RESULT.value / f"{quarantine_id}.json"
        assert storage_path.exists()
        
        # Delete data
        result = storage.delete_data(quarantine_id, DataType.TRADE_RESULT)
        assert result is True
        assert not storage_path.exists()
    
    def test_file_not_found_handling(self, temp_storage_dir):
        """Test handling of missing files"""
        storage = QuarantineStorage(temp_storage_dir)
        
        with pytest.raises(FileNotFoundError):
            storage.retrieve_data("nonexistent_id", DataType.TRADE_RESULT)


class TestQuarantineDecisionEngine:
    """Test quarantine decision logic"""
    
    def test_should_quarantine_critical_severity(self, sample_anomaly):
        """Test that critical severity anomalies are always quarantined"""
        engine = QuarantineDecisionEngine()
        
        # Create critical anomaly
        critical_anomaly = sample_anomaly
        critical_anomaly.severity = Severity.CRITICAL
        
        should_quarantine = engine.should_quarantine(critical_anomaly)
        assert should_quarantine is True
    
    def test_should_quarantine_high_risk_score(self):
        """Test quarantine decision based on high risk score"""
        engine = QuarantineDecisionEngine()
        
        # Create medium severity anomaly with high confidence
        anomaly = MarketConditionAnomaly(
            detection_id="risk_test",
            timestamp=datetime.utcnow(),
            condition_type=MarketConditionType.FLASH_CRASH,
            severity=Severity.MEDIUM,
            confidence=0.95,  # High confidence
            observed_value=0.08,
            expected_value=0.02,
            threshold=0.05,
            deviation_magnitude=0.03,
            symbol="EURUSD",
            description="Suspicious performance improvement detected",
            potential_causes=["Data manipulation"],
            learning_safe=False,
            quarantine_recommended=True,
            lockout_duration_minutes=60
        )
        
        # High-risk context
        context = {
            "concurrent_anomalies": 3,
            "repeated_anomaly": True,
            "multiple_accounts_affected": True
        }
        
        should_quarantine = engine.should_quarantine(anomaly, context)
        assert should_quarantine is True
    
    def test_should_not_quarantine_low_risk(self):
        """Test that low-risk anomalies are not quarantined"""
        engine = QuarantineDecisionEngine()
        
        # Create low-risk anomaly
        anomaly = MarketConditionAnomaly(
            detection_id="low_risk_test",
            timestamp=datetime.utcnow(),
            condition_type=MarketConditionType.MARKET_HOURS,
            severity=Severity.LOW,
            confidence=0.3,
            observed_value=0.02,
            expected_value=0.01,
            threshold=0.05,
            deviation_magnitude=0.01,
            symbol="EURUSD",
            description="Market opening period detected",
            potential_causes=["Normal market hours"],
            learning_safe=False,
            quarantine_recommended=False,
            lockout_duration_minutes=30
        )
        
        should_quarantine = engine.should_quarantine(anomaly)
        assert should_quarantine is False
    
    def test_quarantine_duration_calculation(self, sample_anomaly):
        """Test quarantine duration calculation"""
        engine = QuarantineDecisionEngine()
        
        # Test different severities
        duration_critical = engine.calculate_quarantine_duration(sample_anomaly)
        
        sample_anomaly.severity = Severity.LOW
        duration_low = engine.calculate_quarantine_duration(sample_anomaly)
        
        assert duration_critical > duration_low
        
        # Test bounds
        assert duration_critical >= timedelta(hours=4)
        assert duration_critical <= timedelta(days=7)


class TestManualReviewWorkflow:
    """Test manual review workflow"""
    
    def test_assign_for_review(self):
        """Test review assignment"""
        workflow = ManualReviewWorkflow()
        
        quarantine_id = "test_q_review_001"
        result = workflow.assign_for_review(quarantine_id, priority="high")
        
        assert result is True
        assert quarantine_id in workflow.review_queue
        assert quarantine_id in workflow.review_assignments
    
    def test_submit_review(self, sample_review_result):
        """Test review submission"""
        workflow = ManualReviewWorkflow()
        
        quarantine_id = "test_q_review_002"
        
        # Assign for review first
        workflow.assign_for_review(quarantine_id)
        assert quarantine_id in workflow.review_queue
        
        # Submit review
        result = workflow.submit_review(quarantine_id, sample_review_result)
        
        assert result is True
        assert quarantine_id not in workflow.review_queue
    
    def test_escalation_handling(self):
        """Test review escalation"""
        workflow = ManualReviewWorkflow()
        
        quarantine_id = "test_q_escalate_001"
        workflow.assign_for_review(quarantine_id)
        
        # Create escalation review
        escalation_review = ReviewResult(
            reviewer_id="reviewer_1",
            review_timestamp=datetime.utcnow(),
            decision=ReviewDecision.ESCALATE,
            confidence_score=0.5,
            review_notes="Requires senior review",
            data_quality_assessment={"complexity": "high"},
            recommended_action="Escalate to senior analyst"
        )
        
        workflow.submit_review(quarantine_id, escalation_review)
        
        assert quarantine_id in workflow.escalation_queue
    
    def test_get_review_queue_by_reviewer(self):
        """Test getting review queue for specific reviewer"""
        workflow = ManualReviewWorkflow()
        
        # Assign multiple quarantines
        workflow.assign_for_review("q1", preferred_reviewer="reviewer_1")
        workflow.assign_for_review("q2", preferred_reviewer="reviewer_2")
        workflow.assign_for_review("q3", preferred_reviewer="reviewer_1")
        
        reviewer_1_queue = workflow.get_review_queue("reviewer_1")
        assert len(reviewer_1_queue) == 2
        assert "q1" in reviewer_1_queue
        assert "q3" in reviewer_1_queue
        
        reviewer_2_queue = workflow.get_review_queue("reviewer_2")
        assert len(reviewer_2_queue) == 1
        assert "q2" in reviewer_2_queue


class TestDataQuarantineSystem:
    """Test integrated data quarantine system"""
    
    def test_quarantine_data_flow(self, temp_storage_dir, sample_anomaly, sample_trade_data):
        """Test complete quarantine flow"""
        system = DataQuarantineSystem(temp_storage_dir)
        
        # Quarantine data
        quarantine_id = system.quarantine_data(
            sample_trade_data, 
            DataType.TRADE_RESULT, 
            sample_anomaly,
            context={"risk_score": 0.9}
        )
        
        assert quarantine_id is not None
        assert quarantine_id in system.quarantine_registry
        
        record = system.quarantine_registry[quarantine_id]
        assert record.status == QuarantineStatus.PENDING
        assert record.data_type == DataType.TRADE_RESULT
        assert record.data_count == 10
    
    def test_review_and_release_flow(self, temp_storage_dir, sample_anomaly, 
                                   sample_trade_data, sample_review_result):
        """Test review and data release flow"""
        system = DataQuarantineSystem(temp_storage_dir)
        
        # Quarantine data
        quarantine_id = system.quarantine_data(
            sample_trade_data, 
            DataType.TRADE_RESULT, 
            sample_anomaly
        )
        
        assert quarantine_id is not None
        
        # Submit review
        result = system.submit_review(quarantine_id, sample_review_result)
        assert result is True
        
        record = system.quarantine_registry[quarantine_id]
        assert record.status == QuarantineStatus.APPROVED
        assert len(record.review_history) == 1
        
        # Release data
        released_data = system.release_data(quarantine_id)
        assert released_data is not None
        assert len(released_data) == 10
    
    def test_partial_approval_flow(self, temp_storage_dir, sample_anomaly, sample_trade_data):
        """Test partial approval and data filtering"""
        system = DataQuarantineSystem(temp_storage_dir)
        
        # Quarantine data
        quarantine_id = system.quarantine_data(
            sample_trade_data, 
            DataType.TRADE_RESULT, 
            sample_anomaly
        )
        
        # Create partial approval review
        partial_review = ReviewResult(
            reviewer_id="test_reviewer",
            review_timestamp=datetime.utcnow(),
            decision=ReviewDecision.APPROVE_PARTIAL,
            confidence_score=0.8,
            review_notes="Approve only first 5 trades",
            data_quality_assessment={"partial_quality": "good"},
            recommended_action="Use partial data",
            approved_subset=["0", "1", "2", "3", "4"]  # First 5 trades
        )
        
        # Submit partial review
        system.submit_review(quarantine_id, partial_review)
        
        record = system.quarantine_registry[quarantine_id]
        assert record.status == QuarantineStatus.PARTIAL_APPROVAL
        
        # Release partial data
        released_data = system.release_data(quarantine_id)
        assert released_data is not None
        assert len(released_data) == 5  # Only approved subset
    
    def test_rejection_flow(self, temp_storage_dir, sample_anomaly, sample_trade_data):
        """Test data rejection flow"""
        system = DataQuarantineSystem(temp_storage_dir)
        
        # Quarantine data
        quarantine_id = system.quarantine_data(
            sample_trade_data, 
            DataType.TRADE_RESULT, 
            sample_anomaly
        )
        
        # Create rejection review
        rejection_review = ReviewResult(
            reviewer_id="test_reviewer",
            review_timestamp=datetime.utcnow(),
            decision=ReviewDecision.REJECT_ALL,
            confidence_score=0.95,
            review_notes="Data is corrupted and unsafe",
            data_quality_assessment={"corruption_detected": True},
            recommended_action="Discard all data",
            rejection_reasons=["Data corruption", "Suspicious patterns"]
        )
        
        # Submit rejection
        system.submit_review(quarantine_id, rejection_review)
        
        record = system.quarantine_registry[quarantine_id]
        assert record.status == QuarantineStatus.REJECTED
        
        # Attempt to release rejected data should fail
        released_data = system.release_data(quarantine_id)
        assert released_data is None
    
    def test_cleanup_expired_quarantines(self, temp_storage_dir, sample_anomaly, sample_trade_data):
        """Test cleanup of expired quarantine records"""
        system = DataQuarantineSystem(temp_storage_dir)
        
        # Quarantine data
        quarantine_id = system.quarantine_data(
            sample_trade_data, 
            DataType.TRADE_RESULT, 
            sample_anomaly
        )
        
        # Manually expire the quarantine
        record = system.quarantine_registry[quarantine_id]
        record.expiry_date = datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        
        # Run cleanup
        cleaned_count = system.cleanup_expired_quarantines()
        
        assert cleaned_count == 1
        assert record.status == QuarantineStatus.EXPIRED
    
    def test_quarantine_analytics(self, temp_storage_dir, sample_anomaly, 
                                sample_trade_data, sample_review_result):
        """Test quarantine analytics and reporting"""
        system = DataQuarantineSystem(temp_storage_dir)
        
        # Create multiple quarantine records
        q1 = system.quarantine_data(sample_trade_data, DataType.TRADE_RESULT, sample_anomaly)
        q2 = system.quarantine_data(sample_trade_data, DataType.TRADE_RESULT, sample_anomaly)
        
        # Approve one
        system.submit_review(q1, sample_review_result)
        
        # Get analytics
        analytics = system.get_quarantine_analytics()
        
        assert analytics["summary_stats"]["total_quarantined"] == 2
        assert analytics["summary_stats"]["approved"] == 1
        assert analytics["current_metrics"]["total_active_quarantines"] == 2
        assert analytics["performance_metrics"]["approval_rate"] == 1.0  # 1 approved, 0 rejected
        
        # Check data type breakdown
        assert analytics["data_breakdown"]["trade_result"] == 2
        
        # Check anomaly type breakdown
        assert analytics["anomaly_breakdown"]["flash_crash"] == 2
    
    def test_no_quarantine_for_safe_data(self, temp_storage_dir, sample_trade_data):
        """Test that safe data is not quarantined"""
        system = DataQuarantineSystem(temp_storage_dir)
        
        # Create low-risk anomaly
        safe_anomaly = MarketConditionAnomaly(
            detection_id="safe_test",
            timestamp=datetime.utcnow(),
            condition_type=MarketConditionType.MARKET_HOURS,
            severity=Severity.LOW,
            confidence=0.3,
            observed_value=0.02,
            expected_value=0.01,
            threshold=0.05,
            deviation_magnitude=0.01,
            symbol="EURUSD",
            description="Normal market hours",
            potential_causes=["Market schedule"],
            learning_safe=True,
            quarantine_recommended=False,
            lockout_duration_minutes=15
        )
        
        # Attempt to quarantine
        quarantine_id = system.quarantine_data(
            sample_trade_data, 
            DataType.TRADE_RESULT, 
            safe_anomaly
        )
        
        # Should not be quarantined
        assert quarantine_id is None
        assert len(system.quarantine_registry) == 0
    
    def test_statistics_tracking(self, temp_storage_dir, sample_anomaly, sample_trade_data):
        """Test statistics tracking accuracy"""
        system = DataQuarantineSystem(temp_storage_dir)
        
        # Initial stats should be zero
        assert system.stats["total_quarantined"] == 0
        assert system.stats["pending_review"] == 0
        
        # Quarantine data
        quarantine_id = system.quarantine_data(
            sample_trade_data, 
            DataType.TRADE_RESULT, 
            sample_anomaly
        )
        
        # Stats should be updated
        assert system.stats["total_quarantined"] == 1
        assert system.stats["pending_review"] == 1
        
        # Approve the quarantine
        approval_review = ReviewResult(
            reviewer_id="test_reviewer",
            review_timestamp=datetime.utcnow(),
            decision=ReviewDecision.APPROVE_ALL,
            confidence_score=0.9,
            review_notes="Approved",
            data_quality_assessment={},
            recommended_action="Release"
        )
        
        system.submit_review(quarantine_id, approval_review)
        
        # Stats should reflect approval
        assert system.stats["approved"] == 1
        assert system.stats["pending_review"] == 0