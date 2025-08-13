"""
Learning Rollback System

Provides model versioning, snapshotting, and rollback capabilities to restore
previous stable states when performance degradation or anomalies are detected.
"""

import json
import pickle
import hashlib
import shutil
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import copy

from market_condition_detector import MarketConditionAnomaly
from performance_anomaly_detector import PerformanceWindow

logger = logging.getLogger(__name__)


class SnapshotTrigger(Enum):
    """Triggers for creating model snapshots"""
    SCHEDULED = "scheduled"
    BEFORE_LEARNING = "before_learning"
    MANUAL = "manual"
    CIRCUIT_BREAKER = "circuit_breaker"
    PERFORMANCE_MILESTONE = "performance_milestone"
    DEPLOYMENT = "deployment"


class ModelState(Enum):
    """Model state status"""
    STABLE = "stable"
    TESTING = "testing"
    UNSTABLE = "unstable"
    DEPRECATED = "deprecated"
    CORRUPTED = "corrupted"


class RollbackTrigger(Enum):
    """Triggers for model rollback"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ANOMALY_DETECTION = "anomaly_detection"
    MANUAL_INTERVENTION = "manual_intervention"
    VALIDATION_FAILURE = "validation_failure"
    SYSTEM_ERROR = "system_error"


@dataclass
class ModelMetrics:
    """Performance metrics for model evaluation"""
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    stability_score: float  # 0-1, higher is more stable
    
    # Validation metrics
    validation_accuracy: float
    validation_loss: float
    overfitting_score: float  # 0-1, higher indicates overfitting
    
    # Risk metrics
    risk_score: float
    volatility: float
    correlation_with_baseline: float
    
    def is_better_than(self, other: 'ModelMetrics', threshold: float = 0.05) -> bool:
        """Compare if this model is significantly better than another"""
        # Weighted comparison of key metrics
        weights = {
            'sharpe_ratio': 0.3,
            'win_rate': 0.2,
            'stability_score': 0.25,
            'profit_factor': 0.15,
            'max_drawdown': -0.1  # Lower is better
        }
        
        score_self = (
            weights['sharpe_ratio'] * self.sharpe_ratio +
            weights['win_rate'] * self.win_rate +
            weights['stability_score'] * self.stability_score +
            weights['profit_factor'] * min(self.profit_factor, 3.0) / 3.0 +  # Cap at 3.0
            weights['max_drawdown'] * (1.0 - self.max_drawdown)  # Invert drawdown
        )
        
        score_other = (
            weights['sharpe_ratio'] * other.sharpe_ratio +
            weights['win_rate'] * other.win_rate +
            weights['stability_score'] * other.stability_score +
            weights['profit_factor'] * min(other.profit_factor, 3.0) / 3.0 +
            weights['max_drawdown'] * (1.0 - other.max_drawdown)
        )
        
        return score_self > score_other + threshold


@dataclass
class LearningSnapshot:
    """Complete learning system snapshot"""
    snapshot_id: str
    timestamp: datetime
    version: str
    
    # Model state
    model_states: Dict[str, Any]  # Serialized model parameters
    model_configs: Dict[str, Any]  # Model configurations
    hyperparameters: Dict[str, Any]  # Learning hyperparameters
    
    # Performance data
    performance_metrics: ModelMetrics
    performance_history: List[PerformanceWindow]
    
    # System state
    learning_state: Dict[str, Any]  # Current learning algorithm state
    feature_importance: Dict[str, float]  # Feature importance scores
    data_statistics: Dict[str, Any]  # Training data statistics
    
    # Metadata
    description: str
    trigger: SnapshotTrigger
    creator: str
    tags: List[str]
    
    # Validation
    data_hash: str  # Hash of the training data used
    model_hash: str  # Hash of the model state
    validation_results: Dict[str, Any]
    
    # Status tracking
    state: ModelState
    is_stable: bool
    rollback_target: bool  # Whether this snapshot can be used for rollback
    
    # Dependencies
    parent_snapshot_id: Optional[str] = None
    dependent_snapshots: List[str] = None
    
    def __post_init__(self):
        if self.dependent_snapshots is None:
            self.dependent_snapshots = []


@dataclass
class RollbackEvent:
    """Record of a rollback operation"""
    rollback_id: str
    timestamp: datetime
    trigger: RollbackTrigger
    trigger_details: Dict[str, Any]
    
    # Rollback operation
    from_snapshot_id: str
    to_snapshot_id: str
    rollback_reason: str
    rollback_scope: List[str]  # Which components were rolled back
    
    # Authorization
    authorized_by: str
    authorization_level: str  # 'automatic', 'operator', 'admin'
    
    # Results
    rollback_successful: bool
    rollback_duration_seconds: float
    validation_passed: bool
    rollback_notes: str
    
    # Impact assessment
    affected_models: List[str]
    data_loss: Dict[str, Any]  # What data/learning was lost
    performance_impact: Dict[str, float]


class ModelVersionManager:
    """Manages model versions and snapshots"""
    
    def __init__(self, storage_path: str = "./model_snapshots"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.storage_path / "snapshots").mkdir(exist_ok=True)
        (self.storage_path / "models").mkdir(exist_ok=True)
        (self.storage_path / "metadata").mkdir(exist_ok=True)
        (self.storage_path / "validation").mkdir(exist_ok=True)
        
        # In-memory registry
        self.snapshots_registry: Dict[str, LearningSnapshot] = {}
        self.version_tree: Dict[str, List[str]] = {}  # parent -> children mapping
        
        # Load existing snapshots
        self._load_existing_snapshots()
    
    def create_snapshot(self, model_data: Dict[str, Any], 
                       performance_metrics: ModelMetrics,
                       trigger: SnapshotTrigger,
                       description: str = "",
                       creator: str = "system",
                       tags: Optional[List[str]] = None) -> str:
        """Create a new model snapshot"""
        try:
            # Generate snapshot ID with microseconds for uniqueness
            timestamp = datetime.utcnow()
            snapshot_id = f"snap_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{trigger.value[:4]}"
            
            # Calculate hashes for validation
            model_hash = self._calculate_model_hash(model_data)
            data_hash = self._calculate_data_hash(model_data.get('training_data', {}))
            
            # Create snapshot
            snapshot = LearningSnapshot(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                version=self._generate_version_number(),
                model_states=model_data.get('model_states', {}),
                model_configs=model_data.get('model_configs', {}),
                hyperparameters=model_data.get('hyperparameters', {}),
                performance_metrics=performance_metrics,
                performance_history=model_data.get('performance_history', []),
                learning_state=model_data.get('learning_state', {}),
                feature_importance=model_data.get('feature_importance', {}),
                data_statistics=model_data.get('data_statistics', {}),
                description=description,
                trigger=trigger,
                creator=creator,
                tags=tags or [],
                data_hash=data_hash,
                model_hash=model_hash,
                validation_results={},
                state=ModelState.TESTING,  # New snapshots start as testing
                is_stable=False,
                rollback_target=False
            )
            
            # Store snapshot
            self._store_snapshot(snapshot)
            
            # Register in memory
            self.snapshots_registry[snapshot_id] = snapshot
            
            # Validate snapshot
            validation_results = self._validate_snapshot(snapshot)
            snapshot.validation_results = validation_results
            
            # Update stability assessment
            self._assess_stability(snapshot)
            
            logger.info(f"Created model snapshot: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            raise
    
    def mark_snapshot_stable(self, snapshot_id: str, 
                           validation_data: Optional[Dict[str, Any]] = None) -> bool:
        """Mark a snapshot as stable and suitable for rollback"""
        try:
            if snapshot_id not in self.snapshots_registry:
                raise ValueError(f"Snapshot not found: {snapshot_id}")
            
            snapshot = self.snapshots_registry[snapshot_id]
            
            # Additional validation if provided
            if validation_data:
                validation_passed = self._run_stability_validation(snapshot, validation_data)
                if not validation_passed:
                    logger.warning(f"Stability validation failed for snapshot {snapshot_id}")
                    return False
            
            # Mark as stable
            snapshot.state = ModelState.STABLE
            snapshot.is_stable = True
            snapshot.rollback_target = True
            
            # Update storage
            self._store_snapshot(snapshot)
            
            logger.info(f"Marked snapshot as stable: {snapshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark snapshot stable {snapshot_id}: {e}")
            return False
    
    def get_rollback_candidates(self, criteria: Optional[Dict[str, Any]] = None) -> List[LearningSnapshot]:
        """Get snapshots suitable for rollback based on criteria"""
        candidates = []
        
        for snapshot in self.snapshots_registry.values():
            # Only include stable snapshots that are marked as rollback targets
            if not (snapshot.rollback_target and snapshot.is_stable):
                continue
            
            # Apply criteria filters
            if criteria:
                if 'min_performance' in criteria:
                    min_perf = criteria['min_performance']
                    if snapshot.performance_metrics.sharpe_ratio < min_perf.get('sharpe_ratio', 0):
                        continue
                    if snapshot.performance_metrics.win_rate < min_perf.get('win_rate', 0):
                        continue
                
                if 'max_age_hours' in criteria:
                    max_age = timedelta(hours=criteria['max_age_hours'])
                    if datetime.utcnow() - snapshot.timestamp > max_age:
                        continue
                
                if 'required_tags' in criteria:
                    required_tags = set(criteria['required_tags'])
                    if not required_tags.issubset(set(snapshot.tags)):
                        continue
            
            candidates.append(snapshot)
        
        # Sort by performance and recency
        candidates.sort(key=lambda s: (
            s.performance_metrics.stability_score,
            s.performance_metrics.sharpe_ratio,
            s.timestamp
        ), reverse=True)
        
        return candidates
    
    def delete_snapshot(self, snapshot_id: str, force: bool = False) -> bool:
        """Delete a snapshot (with safety checks)"""
        try:
            if snapshot_id not in self.snapshots_registry:
                raise ValueError(f"Snapshot not found: {snapshot_id}")
            
            snapshot = self.snapshots_registry[snapshot_id]
            
            # Safety checks
            if not force:
                if snapshot.rollback_target:
                    raise ValueError("Cannot delete rollback target without force=True")
                if snapshot.dependent_snapshots:
                    raise ValueError("Cannot delete snapshot with dependencies without force=True")
            
            # Delete from storage
            snapshot_file = self.storage_path / "snapshots" / f"{snapshot_id}.pkl"
            metadata_file = self.storage_path / "metadata" / f"{snapshot_id}.json"
            
            if snapshot_file.exists():
                snapshot_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Remove from registry
            del self.snapshots_registry[snapshot_id]
            
            logger.info(f"Deleted snapshot: {snapshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete snapshot {snapshot_id}: {e}")
            return False
    
    def _store_snapshot(self, snapshot: LearningSnapshot) -> None:
        """Store snapshot to disk"""
        # Store model data (binary)
        snapshot_file = self.storage_path / "snapshots" / f"{snapshot.snapshot_id}.pkl"
        with open(snapshot_file, 'wb') as f:
            pickle.dump(snapshot, f)
        
        # Store metadata (JSON for easy inspection)
        metadata = {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp.isoformat(),
            "version": snapshot.version,
            "description": snapshot.description,
            "trigger": snapshot.trigger.value,
            "creator": snapshot.creator,
            "tags": snapshot.tags,
            "state": snapshot.state.value,
            "is_stable": snapshot.is_stable,
            "rollback_target": snapshot.rollback_target,
            "model_hash": snapshot.model_hash,
            "data_hash": snapshot.data_hash,
            "performance_metrics": asdict(snapshot.performance_metrics)
        }
        
        metadata_file = self.storage_path / "metadata" / f"{snapshot.snapshot_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def _load_existing_snapshots(self) -> None:
        """Load existing snapshots from storage"""
        snapshots_dir = self.storage_path / "snapshots"
        
        for snapshot_file in snapshots_dir.glob("*.pkl"):
            try:
                with open(snapshot_file, 'rb') as f:
                    snapshot = pickle.load(f)
                    self.snapshots_registry[snapshot.snapshot_id] = snapshot
            except Exception as e:
                logger.error(f"Failed to load snapshot {snapshot_file}: {e}")
    
    def _calculate_model_hash(self, model_data: Dict[str, Any]) -> str:
        """Calculate hash of model state for integrity checking"""
        # Create a deterministic representation of the model
        model_str = json.dumps(model_data, sort_keys=True, default=str)
        return hashlib.sha256(model_str.encode()).hexdigest()
    
    def _calculate_data_hash(self, training_data: Dict[str, Any]) -> str:
        """Calculate hash of training data"""
        data_str = json.dumps(training_data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _generate_version_number(self) -> str:
        """Generate version number for new snapshot"""
        # Simple versioning: v1.0, v1.1, etc.
        existing_versions = [s.version for s in self.snapshots_registry.values()]
        if not existing_versions:
            return "v1.0"
        
        # Find the highest version
        version_numbers = []
        for version in existing_versions:
            try:
                major, minor = version[1:].split('.')
                version_numbers.append((int(major), int(minor)))
            except:
                continue
        
        if not version_numbers:
            return "v1.0"
        
        max_major, max_minor = max(version_numbers)
        return f"v{max_major}.{max_minor + 1}"
    
    def _validate_snapshot(self, snapshot: LearningSnapshot) -> Dict[str, Any]:
        """Validate snapshot integrity and completeness"""
        validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "integrity_check": False,
            "completeness_check": False,
            "performance_check": False,
            "issues": []
        }
        
        try:
            # Integrity check
            if snapshot.model_hash and snapshot.data_hash:
                validation_results["integrity_check"] = True
            else:
                validation_results["issues"].append("Missing integrity hashes")
            
            # Completeness check
            required_fields = ['model_states', 'model_configs', 'performance_metrics']
            missing_fields = [field for field in required_fields 
                            if not getattr(snapshot, field, None)]
            
            if not missing_fields:
                validation_results["completeness_check"] = True
            else:
                validation_results["issues"].append(f"Missing fields: {missing_fields}")
            
            # Performance check
            metrics = snapshot.performance_metrics
            if (metrics.sharpe_ratio > -1.0 and metrics.win_rate >= 0.0 and 
                metrics.stability_score >= 0.0):
                validation_results["performance_check"] = True
            else:
                validation_results["issues"].append("Invalid performance metrics")
            
        except Exception as e:
            validation_results["issues"].append(f"Validation error: {e}")
        
        return validation_results
    
    def _assess_stability(self, snapshot: LearningSnapshot) -> None:
        """Assess snapshot stability based on various factors"""
        stability_factors = []
        
        # Performance consistency
        if snapshot.performance_metrics.stability_score > 0.7:
            stability_factors.append(0.3)
        elif snapshot.performance_metrics.stability_score > 0.5:
            stability_factors.append(0.15)
        
        # Validation results
        if snapshot.validation_results.get("performance_check", False):
            stability_factors.append(0.2)
        
        # Model complexity (avoid overfitting)
        if snapshot.performance_metrics.overfitting_score < 0.3:
            stability_factors.append(0.2)
        
        # Risk assessment
        if snapshot.performance_metrics.risk_score < 0.6:
            stability_factors.append(0.3)
        
        # Overall stability score
        stability_score = sum(stability_factors)
        
        # New snapshots are not automatically stable or rollback targets
        # They start as testing and must be explicitly marked stable
        snapshot.is_stable = False
        snapshot.rollback_target = False
    
    def _run_stability_validation(self, snapshot: LearningSnapshot, 
                                 validation_data: Dict[str, Any]) -> bool:
        """Run additional stability validation"""
        # This is a placeholder for more sophisticated validation
        # In production, this would run the model on validation data
        
        try:
            # Basic validation checks
            if 'validation_performance' in validation_data:
                val_perf = validation_data['validation_performance']
                training_perf = snapshot.performance_metrics
                
                # Check for overfitting (validation much worse than training)
                performance_gap = training_perf.sharpe_ratio - val_perf.get('sharpe_ratio', 0)
                if performance_gap > 0.5:  # Significant gap indicates overfitting
                    return False
            
            # Check for data consistency
            if 'data_consistency' in validation_data:
                consistency_score = validation_data['data_consistency']
                if consistency_score < 0.8:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Stability validation error: {e}")
            return False


class RollbackManager:
    """Manages model rollback operations"""
    
    def __init__(self, version_manager: ModelVersionManager):
        self.version_manager = version_manager
        self.rollback_history: List[RollbackEvent] = []
        
        # Rollback policies
        self.auto_rollback_enabled = True
        self.max_rollback_attempts = 3
        self.rollback_cooldown_hours = 2
        
    def detect_rollback_need(self, current_performance: ModelMetrics,
                           recent_anomalies: List[MarketConditionAnomaly]) -> Optional[RollbackTrigger]:
        """Detect if rollback is needed based on current conditions"""
        # Performance degradation check
        stable_snapshots = self.version_manager.get_rollback_candidates()
        if stable_snapshots:
            baseline = stable_snapshots[0].performance_metrics
            
            # Check for significant performance drop
            if current_performance.sharpe_ratio < baseline.sharpe_ratio * 0.7:
                return RollbackTrigger.PERFORMANCE_DEGRADATION
            
            if current_performance.stability_score < baseline.stability_score * 0.6:
                return RollbackTrigger.PERFORMANCE_DEGRADATION
        
        # Anomaly-based rollback
        critical_anomalies = [a for a in recent_anomalies 
                            if a.severity.value in ['critical', 'high']]
        
        if len(critical_anomalies) >= 3:  # Multiple critical anomalies
            return RollbackTrigger.ANOMALY_DETECTION
        
        # Check for validation failures
        if current_performance.validation_accuracy < 0.5:
            return RollbackTrigger.VALIDATION_FAILURE
        
        return None
    
    def execute_rollback(self, target_snapshot_id: str,
                        trigger: RollbackTrigger,
                        trigger_details: Dict[str, Any],
                        authorized_by: str = "system",
                        rollback_scope: Optional[List[str]] = None) -> Optional[str]:
        """Execute rollback to target snapshot"""
        try:
            # Generate rollback ID with microseconds for uniqueness
            rollback_id = f"rollback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Get target snapshot
            if target_snapshot_id not in self.version_manager.snapshots_registry:
                raise ValueError(f"Target snapshot not found: {target_snapshot_id}")
            
            target_snapshot = self.version_manager.snapshots_registry[target_snapshot_id]
            
            # Validate rollback is safe
            if not self._validate_rollback_safety(target_snapshot):
                raise ValueError(f"Rollback to {target_snapshot_id} is not safe")
            
            # Check cooldown period
            if not self._check_rollback_cooldown():
                raise ValueError("Rollback cooldown period still active")
            
            start_time = datetime.utcnow()
            
            # Determine current snapshot (for rollback record)
            current_snapshot_id = self._get_current_snapshot_id()
            
            # Perform the rollback
            rollback_successful = self._perform_rollback(target_snapshot, rollback_scope)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Run post-rollback validation
            validation_passed = self._validate_post_rollback(target_snapshot)
            
            # Create rollback event record
            rollback_event = RollbackEvent(
                rollback_id=rollback_id,
                timestamp=start_time,
                trigger=trigger,
                trigger_details=trigger_details,
                from_snapshot_id=current_snapshot_id,
                to_snapshot_id=target_snapshot_id,
                rollback_reason=self._generate_rollback_reason(trigger, trigger_details),
                rollback_scope=rollback_scope or ["all"],
                authorized_by=authorized_by,
                authorization_level="automatic" if authorized_by == "system" else "manual",
                rollback_successful=rollback_successful,
                rollback_duration_seconds=duration,
                validation_passed=validation_passed,
                rollback_notes="",
                affected_models=rollback_scope or ["all"],
                data_loss=self._assess_data_loss(current_snapshot_id, target_snapshot_id),
                performance_impact=self._assess_performance_impact(target_snapshot)
            )
            
            # Record rollback
            self.rollback_history.append(rollback_event)
            
            if rollback_successful and validation_passed:
                logger.info(f"Rollback successful: {rollback_id} to {target_snapshot_id}")
                return rollback_id
            else:
                logger.error(f"Rollback failed: {rollback_id}")
                return None
                
        except Exception as e:
            logger.error(f"Rollback execution failed: {e}")
            return None
    
    def get_recommended_rollback_target(self, trigger: RollbackTrigger,
                                      context: Dict[str, Any]) -> Optional[str]:
        """Get recommended rollback target based on trigger and context"""
        candidates = self.version_manager.get_rollback_candidates()
        
        if not candidates:
            return None
        
        # Filter candidates based on trigger
        if trigger == RollbackTrigger.PERFORMANCE_DEGRADATION:
            # Look for snapshots with better performance
            current_performance = context.get('current_performance')
            if current_performance:
                candidates = [c for c in candidates 
                            if c.performance_metrics.is_better_than(current_performance)]
        
        elif trigger == RollbackTrigger.ANOMALY_DETECTION:
            # Look for recent stable snapshots (within last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            candidates = [c for c in candidates if c.timestamp > recent_cutoff]
        
        # Return the best candidate
        if candidates:
            return candidates[0].snapshot_id
        
        return None
    
    def get_rollback_history(self, limit: int = 50) -> List[RollbackEvent]:
        """Get recent rollback history"""
        return sorted(self.rollback_history, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def _validate_rollback_safety(self, target_snapshot: LearningSnapshot) -> bool:
        """Validate that rollback to target is safe"""
        # Check snapshot is stable and suitable for rollback
        if not target_snapshot.rollback_target or not target_snapshot.is_stable:
            return False
        
        # Check snapshot age (don't rollback to very old snapshots)
        age = datetime.utcnow() - target_snapshot.timestamp
        if age > timedelta(days=30):
            return False
        
        # Check performance metrics are reasonable
        metrics = target_snapshot.performance_metrics
        if metrics.sharpe_ratio < -0.5 or metrics.stability_score < 0.3:
            return False
        
        return True
    
    def _check_rollback_cooldown(self) -> bool:
        """Check if rollback cooldown period has passed"""
        if not self.rollback_history:
            return True
        
        last_rollback = max(self.rollback_history, key=lambda r: r.timestamp)
        cooldown_end = last_rollback.timestamp + timedelta(hours=self.rollback_cooldown_hours)
        
        return datetime.utcnow() >= cooldown_end
    
    def _get_current_snapshot_id(self) -> str:
        """Get current active snapshot ID (mock implementation)"""
        # In a real system, this would query the currently active model
        return "current_active_model"
    
    def _perform_rollback(self, target_snapshot: LearningSnapshot, 
                         rollback_scope: Optional[List[str]]) -> bool:
        """Perform the actual rollback operation (mock implementation)"""
        try:
            # In a real system, this would:
            # 1. Stop current learning processes
            # 2. Load target snapshot model states
            # 3. Restore model configurations
            # 4. Update hyperparameters
            # 5. Reset learning state
            # 6. Restart learning processes
            
            logger.info(f"Performing rollback to {target_snapshot.snapshot_id}")
            
            # Simulate rollback operations
            components = rollback_scope or ["models", "configs", "hyperparameters", "learning_state"]
            
            for component in components:
                if component == "models":
                    # Restore model states
                    pass
                elif component == "configs":
                    # Restore configurations
                    pass
                elif component == "hyperparameters":
                    # Restore hyperparameters
                    pass
                elif component == "learning_state":
                    # Reset learning state
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Rollback operation failed: {e}")
            return False
    
    def _validate_post_rollback(self, target_snapshot: LearningSnapshot) -> bool:
        """Validate system state after rollback"""
        try:
            # In a real system, this would:
            # 1. Verify model loaded correctly
            # 2. Run basic prediction tests
            # 3. Check system health
            # 4. Validate performance metrics
            
            # Mock validation
            return True
            
        except Exception as e:
            logger.error(f"Post-rollback validation failed: {e}")
            return False
    
    def _generate_rollback_reason(self, trigger: RollbackTrigger, 
                                 trigger_details: Dict[str, Any]) -> str:
        """Generate human-readable rollback reason"""
        if trigger == RollbackTrigger.PERFORMANCE_DEGRADATION:
            return f"Performance degradation detected: {trigger_details.get('details', 'N/A')}"
        elif trigger == RollbackTrigger.ANOMALY_DETECTION:
            return f"Anomalies detected: {trigger_details.get('anomaly_count', 0)} anomalies"
        elif trigger == RollbackTrigger.VALIDATION_FAILURE:
            return f"Validation failure: {trigger_details.get('failure_reason', 'N/A')}"
        else:
            return f"Manual rollback: {trigger_details.get('reason', 'No reason provided')}"
    
    def _assess_data_loss(self, from_snapshot_id: str, to_snapshot_id: str) -> Dict[str, Any]:
        """Assess what data/learning will be lost in rollback"""
        # In a real system, this would calculate:
        # - Learning progress lost
        # - Training data that won't be used
        # - Model improvements that will be reverted
        
        return {
            "learning_progress_lost": "Estimated hours of learning lost",
            "training_data_unused": "Amount of training data that won't be used",
            "model_improvements_reverted": "Performance improvements that will be lost"
        }
    
    def _assess_performance_impact(self, target_snapshot: LearningSnapshot) -> Dict[str, float]:
        """Assess expected performance impact of rollback"""
        metrics = target_snapshot.performance_metrics
        
        return {
            "expected_sharpe_ratio": metrics.sharpe_ratio,
            "expected_win_rate": metrics.win_rate,
            "expected_stability_score": metrics.stability_score,
            "risk_score": metrics.risk_score
        }


class LearningRollbackSystem:
    """Main learning rollback system coordinating all components"""
    
    def __init__(self, storage_path: str = "./learning_rollbacks"):
        self.version_manager = ModelVersionManager(storage_path)
        self.rollback_manager = RollbackManager(self.version_manager)
        
        # System configuration
        self.auto_snapshot_enabled = True
        self.auto_rollback_enabled = True
        self.snapshot_frequency_hours = 6
        
        # Monitoring
        self.last_snapshot_time: Optional[datetime] = None
        self.system_health_score = 1.0  # 0-1, lower indicates issues
    
    def create_learning_snapshot(self, model_data: Dict[str, Any],
                               performance_metrics: ModelMetrics,
                               trigger: SnapshotTrigger = SnapshotTrigger.MANUAL,
                               description: str = "",
                               creator: str = "system") -> str:
        """Create a new learning snapshot"""
        snapshot_id = self.version_manager.create_snapshot(
            model_data, performance_metrics, trigger, description, creator
        )
        
        self.last_snapshot_time = datetime.utcnow()
        return snapshot_id
    
    def check_rollback_conditions(self, current_performance: ModelMetrics,
                                 recent_anomalies: List[MarketConditionAnomaly]) -> Optional[str]:
        """Check if rollback conditions are met and execute if needed"""
        if not self.auto_rollback_enabled:
            return None
        
        # Detect rollback need
        trigger = self.rollback_manager.detect_rollback_need(current_performance, recent_anomalies)
        
        if trigger:
            # Get recommended target
            context = {
                'current_performance': current_performance,
                'recent_anomalies': recent_anomalies
            }
            
            target_snapshot_id = self.rollback_manager.get_recommended_rollback_target(trigger, context)
            
            if target_snapshot_id:
                # Execute automatic rollback
                rollback_id = self.rollback_manager.execute_rollback(
                    target_snapshot_id,
                    trigger,
                    trigger_details={
                        'anomaly_count': len(recent_anomalies),
                        'performance_drop': True,
                        'details': 'Automatic rollback triggered'
                    },
                    authorized_by="system"
                )
                
                return rollback_id
        
        return None
    
    def manual_rollback(self, target_snapshot_id: str, reason: str,
                       authorized_by: str) -> Optional[str]:
        """Execute manual rollback"""
        return self.rollback_manager.execute_rollback(
            target_snapshot_id,
            RollbackTrigger.MANUAL_INTERVENTION,
            trigger_details={'reason': reason},
            authorized_by=authorized_by
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get rollback system status and health"""
        snapshots = list(self.version_manager.snapshots_registry.values())
        stable_snapshots = [s for s in snapshots if s.is_stable]
        rollback_targets = [s for s in snapshots if s.rollback_target]
        
        recent_rollbacks = [r for r in self.rollback_manager.rollback_history
                          if r.timestamp > datetime.utcnow() - timedelta(days=7)]
        
        return {
            "snapshot_summary": {
                "total_snapshots": len(snapshots),
                "stable_snapshots": len(stable_snapshots),
                "rollback_targets": len(rollback_targets),
                "last_snapshot": self.last_snapshot_time.isoformat() if self.last_snapshot_time else None
            },
            "rollback_summary": {
                "total_rollbacks": len(self.rollback_manager.rollback_history),
                "recent_rollbacks": len(recent_rollbacks),
                "successful_rollbacks": len([r for r in recent_rollbacks if r.rollback_successful]),
                "auto_rollback_enabled": self.auto_rollback_enabled
            },
            "system_health": {
                "health_score": self.system_health_score,
                "auto_snapshot_enabled": self.auto_snapshot_enabled,
                "snapshot_frequency_hours": self.snapshot_frequency_hours
            }
        }