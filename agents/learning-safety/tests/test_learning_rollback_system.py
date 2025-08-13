"""
Tests for Learning Rollback System

Tests model versioning, snapshotting, rollback triggers, automated rollback
mechanisms, rollback validation, and audit trail functionality.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from learning_rollback_system import (
    LearningRollbackSystem,
    ModelVersionManager,
    RollbackManager,
    LearningSnapshot,
    ModelMetrics,
    RollbackEvent,
    SnapshotTrigger,
    ModelState,
    RollbackTrigger
)
from market_condition_detector import (
    MarketConditionAnomaly,
    MarketConditionType,
    Severity
)


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_model_data():
    """Create sample model data for testing"""
    return {
        "model_states": {
            "layer_1_weights": [[0.1, 0.2], [0.3, 0.4]],
            "layer_1_bias": [0.1, 0.2],
            "layer_2_weights": [[0.5, 0.6]],
            "layer_2_bias": [0.3]
        },
        "model_configs": {
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 100,
            "architecture": "neural_network"
        },
        "hyperparameters": {
            "dropout_rate": 0.2,
            "regularization": 0.01,
            "optimizer": "adam"
        },
        "learning_state": {
            "current_epoch": 50,
            "best_loss": 0.15,
            "plateau_count": 0
        },
        "feature_importance": {
            "feature_1": 0.3,
            "feature_2": 0.7
        },
        "data_statistics": {
            "training_samples": 10000,
            "validation_samples": 2000,
            "feature_count": 10
        }
    }


@pytest.fixture
def sample_performance_metrics():
    """Create sample performance metrics"""
    return ModelMetrics(
        win_rate=0.65,
        profit_factor=1.8,
        sharpe_ratio=1.2,
        max_drawdown=0.15,
        total_trades=1000,
        stability_score=0.8,
        validation_accuracy=0.85,
        validation_loss=0.25,
        overfitting_score=0.1,
        risk_score=0.3,
        volatility=0.12,
        correlation_with_baseline=0.85
    )


@pytest.fixture
def degraded_performance_metrics():
    """Create degraded performance metrics for rollback testing"""
    return ModelMetrics(
        win_rate=0.45,  # Much lower
        profit_factor=1.1,  # Much lower
        sharpe_ratio=0.3,   # Much lower
        max_drawdown=0.35,  # Higher (worse)
        total_trades=1200,
        stability_score=0.4,  # Lower
        validation_accuracy=0.65,  # Lower
        validation_loss=0.45,      # Higher (worse)
        overfitting_score=0.6,     # Higher (worse)
        risk_score=0.8,            # Higher (worse)
        volatility=0.25,           # Higher
        correlation_with_baseline=0.5  # Lower
    )


@pytest.fixture
def sample_anomalies():
    """Create sample anomalies for testing"""
    anomalies = []
    base_time = datetime.utcnow()
    
    for i in range(3):
        anomaly = MarketConditionAnomaly(
            detection_id=f"anomaly_{i}",
            timestamp=base_time + timedelta(minutes=i*30),
            condition_type=MarketConditionType.FLASH_CRASH,
            severity=Severity.HIGH,
            confidence=0.9,
            observed_value=0.08,
            expected_value=0.02,
            threshold=0.05,
            deviation_magnitude=0.03,
            symbol="EURUSD",
            description=f"Critical anomaly {i}",
            potential_causes=["Market manipulation"],
            learning_safe=False,
            quarantine_recommended=True,
            lockout_duration_minutes=120
        )
        anomalies.append(anomaly)
    
    return anomalies


class TestModelMetrics:
    """Test ModelMetrics functionality"""
    
    def test_is_better_than_comparison(self, sample_performance_metrics, degraded_performance_metrics):
        """Test performance comparison logic"""
        # Good metrics should be better than degraded metrics
        assert sample_performance_metrics.is_better_than(degraded_performance_metrics)
        
        # Degraded metrics should not be better than good metrics
        assert not degraded_performance_metrics.is_better_than(sample_performance_metrics)
        
        # Should not be significantly better than itself
        assert not sample_performance_metrics.is_better_than(sample_performance_metrics, threshold=0.05)
    
    def test_performance_threshold_sensitivity(self, sample_performance_metrics):
        """Test performance comparison with different thresholds"""
        # Create slightly better metrics
        slightly_better = ModelMetrics(
            win_rate=sample_performance_metrics.win_rate + 0.02,
            profit_factor=sample_performance_metrics.profit_factor + 0.1,
            sharpe_ratio=sample_performance_metrics.sharpe_ratio + 0.05,
            max_drawdown=sample_performance_metrics.max_drawdown,
            total_trades=sample_performance_metrics.total_trades,
            stability_score=sample_performance_metrics.stability_score + 0.02,
            validation_accuracy=sample_performance_metrics.validation_accuracy,
            validation_loss=sample_performance_metrics.validation_loss,
            overfitting_score=sample_performance_metrics.overfitting_score,
            risk_score=sample_performance_metrics.risk_score,
            volatility=sample_performance_metrics.volatility,
            correlation_with_baseline=sample_performance_metrics.correlation_with_baseline
        )
        
        # With low threshold, should be considered better
        assert slightly_better.is_better_than(sample_performance_metrics, threshold=0.01)
        
        # With high threshold, should not be considered significantly better
        assert not slightly_better.is_better_than(sample_performance_metrics, threshold=0.10)


class TestModelVersionManager:
    """Test model version management"""
    
    def test_create_snapshot(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test creating model snapshots"""
        manager = ModelVersionManager(temp_storage_dir)
        
        snapshot_id = manager.create_snapshot(
            sample_model_data,
            sample_performance_metrics,
            SnapshotTrigger.MANUAL,
            "Test snapshot",
            "test_user"
        )
        
        assert snapshot_id is not None
        assert snapshot_id in manager.snapshots_registry
        
        snapshot = manager.snapshots_registry[snapshot_id]
        assert snapshot.description == "Test snapshot"
        assert snapshot.creator == "test_user"
        assert snapshot.trigger == SnapshotTrigger.MANUAL
        assert snapshot.state == ModelState.TESTING  # New snapshots start as testing
    
    def test_mark_snapshot_stable(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test marking snapshots as stable"""
        manager = ModelVersionManager(temp_storage_dir)
        
        snapshot_id = manager.create_snapshot(
            sample_model_data,
            sample_performance_metrics,
            SnapshotTrigger.MANUAL
        )
        
        # Initially should not be stable
        snapshot = manager.snapshots_registry[snapshot_id]
        assert not snapshot.is_stable
        assert not snapshot.rollback_target
        
        # Mark as stable
        result = manager.mark_snapshot_stable(snapshot_id)
        assert result is True
        
        # Should now be stable and rollback target
        assert snapshot.is_stable
        assert snapshot.rollback_target
        assert snapshot.state == ModelState.STABLE
    
    def test_get_rollback_candidates(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test getting rollback candidates"""
        manager = ModelVersionManager(temp_storage_dir)
        
        # Create multiple snapshots
        snapshot_ids = []
        for i in range(3):
            # Vary performance slightly
            metrics = ModelMetrics(
                win_rate=sample_performance_metrics.win_rate + i*0.05,
                profit_factor=sample_performance_metrics.profit_factor + i*0.1,
                sharpe_ratio=sample_performance_metrics.sharpe_ratio + i*0.1,
                max_drawdown=sample_performance_metrics.max_drawdown,
                total_trades=sample_performance_metrics.total_trades,
                stability_score=sample_performance_metrics.stability_score + i*0.05,
                validation_accuracy=sample_performance_metrics.validation_accuracy,
                validation_loss=sample_performance_metrics.validation_loss,
                overfitting_score=sample_performance_metrics.overfitting_score,
                risk_score=sample_performance_metrics.risk_score,
                volatility=sample_performance_metrics.volatility,
                correlation_with_baseline=sample_performance_metrics.correlation_with_baseline
            )
            
            snapshot_id = manager.create_snapshot(
                sample_model_data,
                metrics,
                SnapshotTrigger.MANUAL,
                f"Snapshot {i}",
                tags=[f"tag_{i}"]
            )
            snapshot_ids.append(snapshot_id)
            
            # Mark as stable
            manager.mark_snapshot_stable(snapshot_id)
        
        # Get all candidates
        candidates = manager.get_rollback_candidates()
        assert len(candidates) == 3
        
        # Should be sorted by performance (best first)
        assert candidates[0].performance_metrics.sharpe_ratio >= candidates[1].performance_metrics.sharpe_ratio
        
        # Test filtering by minimum performance
        criteria = {
            'min_performance': {
                'sharpe_ratio': sample_performance_metrics.sharpe_ratio + 0.15,
                'win_rate': 0.65
            }
        }
        
        filtered_candidates = manager.get_rollback_candidates(criteria)
        assert len(filtered_candidates) <= len(candidates)
        
        # Test filtering by tags
        tag_criteria = {'required_tags': ['tag_2']}
        tag_candidates = manager.get_rollback_candidates(tag_criteria)
        assert len(tag_candidates) == 1
        assert 'tag_2' in tag_candidates[0].tags
    
    def test_delete_snapshot(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test snapshot deletion with safety checks"""
        manager = ModelVersionManager(temp_storage_dir)
        
        snapshot_id = manager.create_snapshot(
            sample_model_data,
            sample_performance_metrics,
            SnapshotTrigger.MANUAL
        )
        
        # Should be able to delete non-rollback target
        result = manager.delete_snapshot(snapshot_id)
        assert result is True
        assert snapshot_id not in manager.snapshots_registry
        
        # Create and mark as rollback target
        snapshot_id2 = manager.create_snapshot(
            sample_model_data,
            sample_performance_metrics,
            SnapshotTrigger.MANUAL
        )
        manager.mark_snapshot_stable(snapshot_id2)
        
        # Should not be able to delete rollback target without force
        result = manager.delete_snapshot(snapshot_id2, force=False)
        assert result is False
        assert snapshot_id2 in manager.snapshots_registry
        
        # Should be able to delete with force
        result = manager.delete_snapshot(snapshot_id2, force=True)
        assert result is True
        assert snapshot_id2 not in manager.snapshots_registry
    
    def test_snapshot_persistence(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test that snapshots persist across manager instances"""
        # Create snapshot with first manager instance
        manager1 = ModelVersionManager(temp_storage_dir)
        snapshot_id = manager1.create_snapshot(
            sample_model_data,
            sample_performance_metrics,
            SnapshotTrigger.MANUAL,
            "Persistent test"
        )
        
        # Create new manager instance (should load existing snapshots)
        manager2 = ModelVersionManager(temp_storage_dir)
        
        assert snapshot_id in manager2.snapshots_registry
        snapshot = manager2.snapshots_registry[snapshot_id]
        assert snapshot.description == "Persistent test"
    
    def test_version_number_generation(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test version number generation"""
        manager = ModelVersionManager(temp_storage_dir)
        
        # First snapshot should be v1.0
        snapshot_id1 = manager.create_snapshot(sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL)
        assert manager.snapshots_registry[snapshot_id1].version == "v1.0"
        
        # Second snapshot should be v1.1
        snapshot_id2 = manager.create_snapshot(sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL)
        assert manager.snapshots_registry[snapshot_id2].version == "v1.1"
        
        # Third snapshot should be v1.2
        snapshot_id3 = manager.create_snapshot(sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL)
        assert manager.snapshots_registry[snapshot_id3].version == "v1.2"


class TestRollbackManager:
    """Test rollback management"""
    
    def test_detect_rollback_need_performance_degradation(self, temp_storage_dir, sample_model_data, 
                                                         sample_performance_metrics, degraded_performance_metrics):
        """Test detection of rollback need due to performance degradation"""
        version_manager = ModelVersionManager(temp_storage_dir)
        rollback_manager = RollbackManager(version_manager)
        
        # Create stable baseline snapshot
        baseline_id = version_manager.create_snapshot(
            sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL
        )
        version_manager.mark_snapshot_stable(baseline_id)
        
        # Check with degraded performance
        trigger = rollback_manager.detect_rollback_need(degraded_performance_metrics, [])
        
        assert trigger == RollbackTrigger.PERFORMANCE_DEGRADATION
    
    def test_detect_rollback_need_anomaly_detection(self, temp_storage_dir, sample_model_data,
                                                   sample_performance_metrics, sample_anomalies):
        """Test detection of rollback need due to anomalies"""
        version_manager = ModelVersionManager(temp_storage_dir)
        rollback_manager = RollbackManager(version_manager)
        
        # Check with critical anomalies
        trigger = rollback_manager.detect_rollback_need(sample_performance_metrics, sample_anomalies)
        
        assert trigger == RollbackTrigger.ANOMALY_DETECTION
    
    def test_no_rollback_needed(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test that no rollback is triggered for good conditions"""
        version_manager = ModelVersionManager(temp_storage_dir)
        rollback_manager = RollbackManager(version_manager)
        
        # Check with good performance and no anomalies
        trigger = rollback_manager.detect_rollback_need(sample_performance_metrics, [])
        
        assert trigger is None
    
    def test_execute_rollback(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test rollback execution"""
        version_manager = ModelVersionManager(temp_storage_dir)
        rollback_manager = RollbackManager(version_manager)
        
        # Create target snapshot
        target_id = version_manager.create_snapshot(
            sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL
        )
        version_manager.mark_snapshot_stable(target_id)
        
        # Execute rollback
        rollback_id = rollback_manager.execute_rollback(
            target_id,
            RollbackTrigger.MANUAL_INTERVENTION,
            trigger_details={'reason': 'Test rollback'},
            authorized_by='test_user'
        )
        
        assert rollback_id is not None
        assert len(rollback_manager.rollback_history) == 1
        
        rollback_event = rollback_manager.rollback_history[0]
        assert rollback_event.rollback_id == rollback_id
        assert rollback_event.to_snapshot_id == target_id
        assert rollback_event.authorized_by == 'test_user'
        assert rollback_event.rollback_successful is True
    
    def test_rollback_cooldown(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test rollback cooldown period"""
        version_manager = ModelVersionManager(temp_storage_dir)
        rollback_manager = RollbackManager(version_manager)
        rollback_manager.rollback_cooldown_hours = 0.0001  # Very short cooldown for testing
        
        # Create target snapshot
        target_id = version_manager.create_snapshot(
            sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL
        )
        version_manager.mark_snapshot_stable(target_id)
        
        # First rollback should succeed
        rollback_id1 = rollback_manager.execute_rollback(
            target_id, RollbackTrigger.MANUAL_INTERVENTION,
            trigger_details={'reason': 'First rollback'}, authorized_by='test_user'
        )
        assert rollback_id1 is not None
        
        # Immediate second rollback should fail (cooldown)
        rollback_id2 = rollback_manager.execute_rollback(
            target_id, RollbackTrigger.MANUAL_INTERVENTION,
            trigger_details={'reason': 'Second rollback'}, authorized_by='test_user'
        )
        assert rollback_id2 is None  # Should fail due to cooldown
    
    def test_get_recommended_rollback_target(self, temp_storage_dir, sample_model_data,
                                           sample_performance_metrics, degraded_performance_metrics):
        """Test getting recommended rollback target"""
        version_manager = ModelVersionManager(temp_storage_dir)
        rollback_manager = RollbackManager(version_manager)
        
        # Create multiple stable snapshots with different performance
        good_id = version_manager.create_snapshot(
            sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL
        )
        version_manager.mark_snapshot_stable(good_id)
        
        bad_id = version_manager.create_snapshot(
            sample_model_data, degraded_performance_metrics, SnapshotTrigger.MANUAL
        )
        version_manager.mark_snapshot_stable(bad_id)
        
        # Should recommend the better performing snapshot
        context = {'current_performance': degraded_performance_metrics}
        recommended = rollback_manager.get_recommended_rollback_target(
            RollbackTrigger.PERFORMANCE_DEGRADATION, context
        )
        
        assert recommended == good_id  # Should recommend the better snapshot


class TestLearningRollbackSystem:
    """Test integrated learning rollback system"""
    
    def test_create_learning_snapshot(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test creating learning snapshots"""
        system = LearningRollbackSystem(temp_storage_dir)
        
        snapshot_id = system.create_learning_snapshot(
            sample_model_data,
            sample_performance_metrics,
            SnapshotTrigger.MANUAL,
            "Test system snapshot"
        )
        
        assert snapshot_id is not None
        assert system.last_snapshot_time is not None
        assert snapshot_id in system.version_manager.snapshots_registry
    
    def test_check_rollback_conditions_triggers_rollback(self, temp_storage_dir, sample_model_data,
                                                        sample_performance_metrics, degraded_performance_metrics,
                                                        sample_anomalies):
        """Test automatic rollback triggering"""
        system = LearningRollbackSystem(temp_storage_dir)
        
        # Create stable baseline
        baseline_id = system.create_learning_snapshot(
            sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL
        )
        system.version_manager.mark_snapshot_stable(baseline_id)
        
        # Temporarily reduce cooldown for testing
        system.rollback_manager.rollback_cooldown_hours = 0.001
        
        # Check conditions with degraded performance
        rollback_id = system.check_rollback_conditions(degraded_performance_metrics, sample_anomalies)
        
        assert rollback_id is not None
        assert len(system.rollback_manager.rollback_history) == 1
    
    def test_manual_rollback(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test manual rollback functionality"""
        system = LearningRollbackSystem(temp_storage_dir)
        
        # Create target snapshot
        target_id = system.create_learning_snapshot(
            sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL
        )
        system.version_manager.mark_snapshot_stable(target_id)
        
        # Execute manual rollback
        rollback_id = system.manual_rollback(target_id, "Manual intervention required", "admin_user")
        
        assert rollback_id is not None
        
        rollback_event = system.rollback_manager.rollback_history[0]
        assert rollback_event.trigger == RollbackTrigger.MANUAL_INTERVENTION
        assert rollback_event.authorized_by == "admin_user"
    
    def test_get_system_status(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test system status reporting"""
        system = LearningRollbackSystem(temp_storage_dir)
        
        # Create some snapshots
        for i in range(3):
            snapshot_id = system.create_learning_snapshot(
                sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL, f"Snapshot {i}"
            )
            if i < 2:  # Mark first two as stable
                system.version_manager.mark_snapshot_stable(snapshot_id)
        
        # Get status
        status = system.get_system_status()
        
        # Verify status structure and content
        assert "snapshot_summary" in status
        assert "rollback_summary" in status
        assert "system_health" in status
        
        snapshot_summary = status["snapshot_summary"]
        assert snapshot_summary["total_snapshots"] == 3
        assert snapshot_summary["stable_snapshots"] == 2
        assert snapshot_summary["rollback_targets"] == 2
        assert snapshot_summary["last_snapshot"] is not None
        
        rollback_summary = status["rollback_summary"]
        assert rollback_summary["total_rollbacks"] == 0  # No rollbacks yet
        assert rollback_summary["auto_rollback_enabled"] is True
        
        system_health = status["system_health"]
        assert system_health["health_score"] == 1.0
        assert system_health["auto_snapshot_enabled"] is True
    
    def test_auto_rollback_disabled(self, temp_storage_dir, sample_model_data,
                                   sample_performance_metrics, degraded_performance_metrics):
        """Test that auto rollback can be disabled"""
        system = LearningRollbackSystem(temp_storage_dir)
        system.auto_rollback_enabled = False
        
        # Create baseline
        baseline_id = system.create_learning_snapshot(
            sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL
        )
        system.version_manager.mark_snapshot_stable(baseline_id)
        
        # Check conditions (should not trigger rollback when disabled)
        rollback_id = system.check_rollback_conditions(degraded_performance_metrics, [])
        
        assert rollback_id is None
        assert len(system.rollback_manager.rollback_history) == 0
    
    def test_snapshot_validation_and_integrity(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test snapshot validation and integrity checks"""
        system = LearningRollbackSystem(temp_storage_dir)
        
        snapshot_id = system.create_learning_snapshot(
            sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL
        )
        
        snapshot = system.version_manager.snapshots_registry[snapshot_id]
        
        # Check that validation was performed
        assert snapshot.validation_results is not None
        assert "integrity_check" in snapshot.validation_results
        assert "completeness_check" in snapshot.validation_results
        assert "performance_check" in snapshot.validation_results
        
        # Check hashes were calculated
        assert snapshot.model_hash is not None
        assert snapshot.data_hash is not None
        assert len(snapshot.model_hash) == 64  # SHA256 hash length
        assert len(snapshot.data_hash) == 64
    
    def test_rollback_history_tracking(self, temp_storage_dir, sample_model_data, sample_performance_metrics):
        """Test that rollback history is properly tracked"""
        system = LearningRollbackSystem(temp_storage_dir)
        
        # Create target snapshots
        target_ids = []
        for i in range(2):
            target_id = system.create_learning_snapshot(
                sample_model_data, sample_performance_metrics, SnapshotTrigger.MANUAL, f"Target {i}"
            )
            system.version_manager.mark_snapshot_stable(target_id)
            target_ids.append(target_id)
        
        # Reduce cooldown for testing (convert to seconds: 0.0001 hours = 0.36 seconds)
        system.rollback_manager.rollback_cooldown_hours = 0.0001
        
        # Execute multiple rollbacks
        rollback_ids = []
        for i, target_id in enumerate(target_ids):
            import time
            if i > 0:  # Only sleep for subsequent rollbacks
                time.sleep(0.5)  # 0.5 seconds > 0.36 seconds cooldown
            rollback_id = system.manual_rollback(target_id, f"Manual rollback {i}", f"user_{i}")
            rollback_ids.append(rollback_id)
        
        # Check history
        history = system.rollback_manager.get_rollback_history()
        assert len(history) == 2
        
        # History should be sorted by timestamp (most recent first)
        assert history[0].timestamp >= history[1].timestamp
        
        # Verify rollback details
        for i, event in enumerate(history):
            assert event.rollback_id in rollback_ids
            assert event.authorized_by in ["user_0", "user_1"]
            assert event.rollback_successful is True