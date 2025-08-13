"""
Data Quarantine System

Safely isolates suspicious data for manual review, maintaining audit trails
and providing mechanisms for data release or discard based on review outcomes.
"""

import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

from market_condition_detector import MarketConditionAnomaly
from performance_anomaly_detector import TradeResult, PerformanceWindow

logger = logging.getLogger(__name__)


class QuarantineStatus(Enum):
    """Quarantine record status"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIAL_APPROVAL = "partial_approval"
    EXPIRED = "expired"


class DataType(Enum):
    """Types of data that can be quarantined"""
    TRADE_RESULT = "trade_result"
    MARKET_DATA = "market_data"
    PERFORMANCE_WINDOW = "performance_window"
    SIGNAL_DATA = "signal_data"
    MODEL_OUTPUT = "model_output"


class ReviewDecision(Enum):
    """Review decisions for quarantined data"""
    APPROVE_ALL = "approve_all"
    APPROVE_PARTIAL = "approve_partial"
    REJECT_ALL = "reject_all"
    EXTEND_REVIEW = "extend_review"
    ESCALATE = "escalate"


@dataclass
class QuarantineMetadata:
    """Metadata about why data was quarantined"""
    trigger_anomaly: MarketConditionAnomaly
    quarantine_reason: str
    risk_score: float
    confidence: float
    detected_patterns: List[str]
    affected_accounts: List[str]
    data_characteristics: Dict[str, Any]


@dataclass
class ReviewResult:
    """Result of manual data review"""
    reviewer_id: str
    review_timestamp: datetime
    decision: ReviewDecision
    confidence_score: float  # 0-1 reviewer confidence
    review_notes: str
    data_quality_assessment: Dict[str, Any]
    recommended_action: str
    
    # Partial approval details
    approved_subset: Optional[List[str]] = None
    rejection_reasons: Optional[List[str]] = None


@dataclass
class QuarantineRecord:
    """Complete quarantine record"""
    quarantine_id: str
    timestamp: datetime
    status: QuarantineStatus
    data_type: DataType
    
    # Data storage
    data_hash: str
    data_size_bytes: int
    data_count: int  # Number of records
    storage_path: str
    
    # Quarantine context
    metadata: QuarantineMetadata
    expiry_date: datetime
    
    # Review tracking
    review_history: List[ReviewResult]
    current_reviewer: Optional[str] = None
    review_deadline: Optional[datetime] = None
    
    # Resolution
    final_decision: Optional[ReviewDecision] = None
    release_timestamp: Optional[datetime] = None
    data_usage_decision: str = "pending"  # use_all, use_partial, discard_all
    
    def is_expired(self) -> bool:
        """Check if quarantine period has expired"""
        return datetime.utcnow() > self.expiry_date
    
    def is_ready_for_review(self) -> bool:
        """Check if record is ready for human review"""
        return self.status == QuarantineStatus.PENDING and not self.is_expired()
    
    def needs_escalation(self) -> bool:
        """Check if case needs escalation"""
        if self.review_deadline and datetime.utcnow() > self.review_deadline:
            return True
        if len(self.review_history) > 2:  # Multiple review rounds
            return True
        return False


class QuarantineStorage:
    """Handles secure storage and retrieval of quarantined data"""
    
    def __init__(self, storage_base_path: str = "./quarantine_storage"):
        self.storage_base_path = Path(storage_base_path)
        self.storage_base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories by data type
        for data_type in DataType:
            (self.storage_base_path / data_type.value).mkdir(exist_ok=True)
    
    def store_data(self, quarantine_id: str, data_type: DataType, 
                   data: Union[List[Any], Any]) -> Dict[str, Any]:
        """Store data securely with integrity checking"""
        try:
            # Serialize data
            if isinstance(data, list):
                serialized_data = [self._serialize_item(item) for item in data]
            else:
                serialized_data = self._serialize_item(data)
            
            data_json = json.dumps(serialized_data, indent=2, default=str)
            data_bytes = data_json.encode('utf-8')
            
            # Calculate hash for integrity
            data_hash = hashlib.sha256(data_bytes).hexdigest()
            
            # Store data
            storage_path = self.storage_base_path / data_type.value / f"{quarantine_id}.json"
            with open(storage_path, 'w', encoding='utf-8') as f:
                f.write(data_json)
            
            # Store metadata
            metadata = {
                "quarantine_id": quarantine_id,
                "data_type": data_type.value,
                "storage_timestamp": datetime.utcnow().isoformat(),
                "data_hash": data_hash,
                "data_size_bytes": len(data_bytes),
                "data_count": len(data) if isinstance(data, list) else 1,
                "file_path": str(storage_path)
            }
            
            metadata_path = storage_path.with_suffix('.metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Stored quarantined data: {quarantine_id}, {len(data_bytes)} bytes")
            
            return {
                "storage_path": str(storage_path),
                "data_hash": data_hash,
                "data_size_bytes": len(data_bytes),
                "data_count": metadata["data_count"]
            }
            
        except Exception as e:
            logger.error(f"Failed to store quarantined data {quarantine_id}: {e}")
            raise
    
    def retrieve_data(self, quarantine_id: str, data_type: DataType, 
                      verify_integrity: bool = True) -> Any:
        """Retrieve quarantined data with integrity verification"""
        try:
            storage_path = self.storage_base_path / data_type.value / f"{quarantine_id}.json"
            
            if not storage_path.exists():
                raise FileNotFoundError(f"Quarantined data not found: {quarantine_id}")
            
            # Load data
            with open(storage_path, 'r', encoding='utf-8') as f:
                data_json = f.read()
            
            if verify_integrity:
                # Verify integrity
                metadata_path = storage_path.with_suffix('.metadata.json')
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                current_hash = hashlib.sha256(data_json.encode('utf-8')).hexdigest()
                if current_hash != metadata["data_hash"]:
                    raise ValueError(f"Data integrity check failed for {quarantine_id}")
            
            # Deserialize data
            data = json.loads(data_json)
            return self._deserialize_data(data, data_type)
            
        except Exception as e:
            logger.error(f"Failed to retrieve quarantined data {quarantine_id}: {e}")
            raise
    
    def delete_data(self, quarantine_id: str, data_type: DataType) -> bool:
        """Securely delete quarantined data"""
        try:
            storage_path = self.storage_base_path / data_type.value / f"{quarantine_id}.json"
            metadata_path = storage_path.with_suffix('.metadata.json')
            
            deleted_files = []
            if storage_path.exists():
                storage_path.unlink()
                deleted_files.append(str(storage_path))
            
            if metadata_path.exists():
                metadata_path.unlink()
                deleted_files.append(str(metadata_path))
            
            logger.info(f"Deleted quarantined data: {quarantine_id}, files: {deleted_files}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete quarantined data {quarantine_id}: {e}")
            return False
    
    def _serialize_item(self, item: Any) -> Dict[str, Any]:
        """Serialize individual data items"""
        if hasattr(item, '__dict__'):
            # Handle dataclass or custom objects
            if hasattr(item, '__dataclass_fields__'):
                return asdict(item)
            else:
                return item.__dict__
        elif isinstance(item, (dict, list, str, int, float, bool)):
            return item
        elif isinstance(item, Decimal):
            return {"__decimal__": str(item)}
        elif isinstance(item, datetime):
            return {"__datetime__": item.isoformat()}
        else:
            return {"__str__": str(item), "__type__": type(item).__name__}
    
    def _deserialize_data(self, data: Any, data_type: DataType) -> Any:
        """Deserialize data based on type"""
        if isinstance(data, dict):
            if "__decimal__" in data:
                return Decimal(data["__decimal__"])
            elif "__datetime__" in data:
                return datetime.fromisoformat(data["__datetime__"])
            elif "__str__" in data:
                return data["__str__"]  # Return as string for safety
        
        return data  # Return as-is for basic types


class QuarantineDecisionEngine:
    """Determines what data should be quarantined based on anomaly analysis"""
    
    def __init__(self):
        # Risk thresholds for quarantine decisions
        self.risk_thresholds = {
            "auto_quarantine": 0.8,      # Auto-quarantine if risk > 80%
            "manual_review": 0.6,        # Manual review if risk > 60%
            "enhanced_monitoring": 0.4   # Enhanced monitoring if risk > 40%
        }
        
        # Severity-based quarantine rules
        self.severity_rules = {
            "critical": True,    # Always quarantine critical anomalies
            "high": True,       # Always quarantine high severity
            "medium": False,    # Decision based on confidence/context
            "low": False        # Usually no quarantine
        }
    
    def should_quarantine(self, anomaly: MarketConditionAnomaly, 
                         context: Dict[str, Any] = None) -> bool:
        """Determine if data should be quarantined"""
        context = context or {}
        
        # Check severity-based rules
        if anomaly.severity.value in self.severity_rules:
            if self.severity_rules[anomaly.severity.value]:
                return True
        
        # Calculate risk score
        risk_score = self._calculate_quarantine_risk(anomaly, context)
        
        # Apply risk thresholds
        if risk_score >= self.risk_thresholds["auto_quarantine"]:
            return True
        
        # Check anomaly-specific patterns
        if self._has_quarantine_patterns(anomaly):
            return True
        
        # Check if multiple concurrent anomalies
        concurrent_anomalies = context.get("concurrent_anomalies", 0)
        if concurrent_anomalies >= 3:
            return True
        
        return False
    
    def calculate_quarantine_duration(self, anomaly: MarketConditionAnomaly) -> timedelta:
        """Calculate appropriate quarantine duration"""
        base_duration = timedelta(hours=24)  # Default 24 hours
        
        # Adjust based on severity
        severity_multipliers = {
            "critical": 3.0,
            "high": 2.0,
            "medium": 1.0,
            "low": 0.5
        }
        
        multiplier = severity_multipliers.get(anomaly.severity.value, 1.0)
        
        # Adjust based on confidence
        confidence_factor = max(0.5, anomaly.confidence)
        
        # Adjust based on anomaly type
        type_adjustments = {
            "flash_crash": 2.0,
            "news_event": 0.5,
            "market_hours": 0.3
        }
        
        type_factor = type_adjustments.get(anomaly.condition_type.value, 1.0)
        
        final_duration = base_duration * multiplier * confidence_factor * type_factor
        
        # Enforce reasonable bounds (4 hours to 7 days)
        min_duration = timedelta(hours=4)
        max_duration = timedelta(days=7)
        
        return max(min_duration, min(max_duration, final_duration))
    
    def _calculate_quarantine_risk(self, anomaly: MarketConditionAnomaly, 
                                  context: Dict[str, Any]) -> float:
        """Calculate risk score for quarantine decision"""
        base_risk = 0.0
        
        # Severity contribution
        severity_scores = {"low": 0.2, "medium": 0.4, "high": 0.7, "critical": 1.0}
        base_risk += severity_scores.get(anomaly.severity.value, 0.5) * 0.4
        
        # Confidence contribution
        base_risk += anomaly.confidence * 0.3
        
        # Quarantine recommendation weight
        if anomaly.quarantine_recommended:
            base_risk += 0.2
        
        # Context factors
        if context.get("repeated_anomaly", False):
            base_risk += 0.1
        
        if context.get("multiple_accounts_affected", False):
            base_risk += 0.1
        
        return min(1.0, base_risk)
    
    def _has_quarantine_patterns(self, anomaly: MarketConditionAnomaly) -> bool:
        """Check for specific patterns that warrant quarantine"""
        quarantine_patterns = [
            "suspicious",
            "manipulation",
            "poisoning",
            "artificial",
            "corruption"
        ]
        
        description_lower = anomaly.description.lower()
        return any(pattern in description_lower for pattern in quarantine_patterns)


class ManualReviewWorkflow:
    """Manages the manual review process for quarantined data"""
    
    def __init__(self):
        self.review_assignments: Dict[str, str] = {}  # quarantine_id -> reviewer_id
        self.review_queue: List[str] = []
        self.escalation_queue: List[str] = []
        
    def assign_for_review(self, quarantine_id: str, priority: str = "normal",
                         preferred_reviewer: Optional[str] = None) -> bool:
        """Assign quarantine record for manual review"""
        try:
            if preferred_reviewer:
                self.review_assignments[quarantine_id] = preferred_reviewer
            else:
                # Simple round-robin assignment (in production, this would be more sophisticated)
                available_reviewers = self._get_available_reviewers()
                if not available_reviewers:
                    logger.warning("No available reviewers for quarantine assignment")
                    return False
                
                reviewer = available_reviewers[len(self.review_assignments) % len(available_reviewers)]
                self.review_assignments[quarantine_id] = reviewer
            
            # Add to appropriate queue based on priority
            if priority == "high":
                self.review_queue.insert(0, quarantine_id)  # High priority at front
            else:
                self.review_queue.append(quarantine_id)
            
            logger.info(f"Assigned quarantine {quarantine_id} to reviewer {self.review_assignments[quarantine_id]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign quarantine for review {quarantine_id}: {e}")
            return False
    
    def submit_review(self, quarantine_id: str, review_result: ReviewResult) -> bool:
        """Submit review result for quarantined data"""
        try:
            # Validate review result
            if not self._validate_review_result(review_result):
                raise ValueError("Invalid review result")
            
            # Remove from review queue
            if quarantine_id in self.review_queue:
                self.review_queue.remove(quarantine_id)
            
            # Handle escalation if needed
            if review_result.decision == ReviewDecision.ESCALATE:
                self.escalation_queue.append(quarantine_id)
                logger.info(f"Escalated quarantine review: {quarantine_id}")
            
            logger.info(f"Review submitted for quarantine {quarantine_id}: {review_result.decision.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit review for {quarantine_id}: {e}")
            return False
    
    def get_review_queue(self, reviewer_id: Optional[str] = None) -> List[str]:
        """Get review queue for specific reviewer or all reviewers"""
        if reviewer_id:
            return [qid for qid in self.review_queue 
                   if self.review_assignments.get(qid) == reviewer_id]
        return self.review_queue.copy()
    
    def get_escalation_queue(self) -> List[str]:
        """Get queue of escalated reviews"""
        return self.escalation_queue.copy()
    
    def _get_available_reviewers(self) -> List[str]:
        """Get list of available reviewers (mock implementation)"""
        # In production, this would query a user management system
        return ["reviewer_1", "reviewer_2", "reviewer_3", "senior_analyst"]
    
    def _validate_review_result(self, review_result: ReviewResult) -> bool:
        """Validate review result completeness"""
        if not review_result.reviewer_id:
            return False
        if not review_result.review_notes:
            return False
        if not (0 <= review_result.confidence_score <= 1):
            return False
        if review_result.decision == ReviewDecision.APPROVE_PARTIAL and not review_result.approved_subset:
            return False
        return True


class DataQuarantineSystem:
    """Main data quarantine system coordinating all components"""
    
    def __init__(self, storage_path: str = "./quarantine_storage"):
        self.storage = QuarantineStorage(storage_path)
        self.decision_engine = QuarantineDecisionEngine()
        self.review_workflow = ManualReviewWorkflow()
        
        # In-memory registry of quarantine records
        self.quarantine_registry: Dict[str, QuarantineRecord] = {}
        
        # Statistics tracking
        self.stats = {
            "total_quarantined": 0,
            "pending_review": 0,
            "approved": 0,
            "rejected": 0,
            "expired": 0
        }
    
    def quarantine_data(self, data: Any, data_type: DataType, 
                       anomaly: MarketConditionAnomaly,
                       context: Dict[str, Any] = None) -> Optional[str]:
        """Quarantine data if warranted by anomaly analysis"""
        try:
            # Check if quarantine is warranted
            if not self.decision_engine.should_quarantine(anomaly, context):
                logger.debug(f"Data not quarantined: {anomaly.detection_id}")
                return None
            
            # Generate quarantine ID with microseconds to ensure uniqueness
            import uuid
            timestamp = datetime.utcnow()
            quarantine_id = f"Q_{timestamp.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Store data
            storage_info = self.storage.store_data(quarantine_id, data_type, data)
            
            # Calculate quarantine duration
            duration = self.decision_engine.calculate_quarantine_duration(anomaly)
            expiry_date = datetime.utcnow() + duration
            
            # Create quarantine metadata
            metadata = QuarantineMetadata(
                trigger_anomaly=anomaly,
                quarantine_reason=f"Anomaly detected: {anomaly.description}",
                risk_score=context.get("risk_score", 0.5) if context else 0.5,
                confidence=anomaly.confidence,
                detected_patterns=context.get("patterns", []) if context else [],
                affected_accounts=context.get("affected_accounts", []) if context else [],
                data_characteristics=self._extract_data_characteristics(data, data_type)
            )
            
            # Create quarantine record
            record = QuarantineRecord(
                quarantine_id=quarantine_id,
                timestamp=datetime.utcnow(),
                status=QuarantineStatus.PENDING,
                data_type=data_type,
                data_hash=storage_info["data_hash"],
                data_size_bytes=storage_info["data_size_bytes"],
                data_count=storage_info["data_count"],
                storage_path=storage_info["storage_path"],
                metadata=metadata,
                expiry_date=expiry_date,
                review_history=[],
                review_deadline=datetime.utcnow() + timedelta(hours=48)  # 48 hour review deadline
            )
            
            # Register quarantine record
            self.quarantine_registry[quarantine_id] = record
            
            # Assign for review if high priority
            priority = "high" if anomaly.severity.value in ["critical", "high"] else "normal"
            self.review_workflow.assign_for_review(quarantine_id, priority)
            
            # Update statistics
            self.stats["total_quarantined"] += 1
            self.stats["pending_review"] += 1
            
            logger.warning(f"Data quarantined: {quarantine_id}, reason: {metadata.quarantine_reason}")
            
            return quarantine_id
            
        except Exception as e:
            logger.error(f"Failed to quarantine data: {e}")
            return None
    
    def submit_review(self, quarantine_id: str, review_result: ReviewResult) -> bool:
        """Submit manual review result for quarantined data"""
        try:
            if quarantine_id not in self.quarantine_registry:
                raise ValueError(f"Quarantine record not found: {quarantine_id}")
            
            record = self.quarantine_registry[quarantine_id]
            
            # Add review to history
            record.review_history.append(review_result)
            record.status = QuarantineStatus.IN_REVIEW
            
            # Submit to workflow
            self.review_workflow.submit_review(quarantine_id, review_result)
            
            # Update record based on decision
            if review_result.decision == ReviewDecision.APPROVE_ALL:
                record.status = QuarantineStatus.APPROVED
                record.final_decision = ReviewDecision.APPROVE_ALL
                record.data_usage_decision = "use_all"
                record.release_timestamp = datetime.utcnow()
                self.stats["approved"] += 1
                self.stats["pending_review"] -= 1
                
            elif review_result.decision == ReviewDecision.REJECT_ALL:
                record.status = QuarantineStatus.REJECTED
                record.final_decision = ReviewDecision.REJECT_ALL
                record.data_usage_decision = "discard_all"
                record.release_timestamp = datetime.utcnow()
                self.stats["rejected"] += 1
                self.stats["pending_review"] -= 1
                
            elif review_result.decision == ReviewDecision.APPROVE_PARTIAL:
                record.status = QuarantineStatus.PARTIAL_APPROVAL
                record.final_decision = ReviewDecision.APPROVE_PARTIAL
                record.data_usage_decision = "use_partial"
                record.release_timestamp = datetime.utcnow()
                self.stats["approved"] += 1
                self.stats["pending_review"] -= 1
            
            logger.info(f"Review processed for quarantine {quarantine_id}: {review_result.decision.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process review for {quarantine_id}: {e}")
            return False
    
    def release_data(self, quarantine_id: str) -> Optional[Any]:
        """Release approved quarantined data for use"""
        try:
            if quarantine_id not in self.quarantine_registry:
                raise ValueError(f"Quarantine record not found: {quarantine_id}")
            
            record = self.quarantine_registry[quarantine_id]
            
            # Check if data can be released
            if record.status not in [QuarantineStatus.APPROVED, QuarantineStatus.PARTIAL_APPROVAL]:
                raise ValueError(f"Data not approved for release: {record.status.value}")
            
            # Retrieve data
            data = self.storage.retrieve_data(quarantine_id, record.data_type)
            
            # For partial approval, filter data based on approved subset
            if record.status == QuarantineStatus.PARTIAL_APPROVAL:
                latest_review = record.review_history[-1]
                if latest_review.approved_subset:
                    data = self._filter_data_subset(data, latest_review.approved_subset)
            
            logger.info(f"Released quarantined data: {quarantine_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to release quarantined data {quarantine_id}: {e}")
            return None
    
    def cleanup_expired_quarantines(self) -> int:
        """Clean up expired quarantine records"""
        cleaned_count = 0
        expired_ids = []
        
        for quarantine_id, record in self.quarantine_registry.items():
            if record.is_expired() and record.status == QuarantineStatus.PENDING:
                record.status = QuarantineStatus.EXPIRED
                expired_ids.append(quarantine_id)
                
                # Delete expired data
                self.storage.delete_data(quarantine_id, record.data_type)
                cleaned_count += 1
        
        # Update statistics
        self.stats["expired"] += cleaned_count
        self.stats["pending_review"] -= len([r for r in expired_ids 
                                           if self.quarantine_registry[r].status == QuarantineStatus.PENDING])
        
        logger.info(f"Cleaned up {cleaned_count} expired quarantine records")
        return cleaned_count
    
    def get_quarantine_analytics(self) -> Dict[str, Any]:
        """Get quarantine system analytics and reporting"""
        current_time = datetime.utcnow()
        
        # Calculate review metrics
        pending_records = [r for r in self.quarantine_registry.values() 
                          if r.status == QuarantineStatus.PENDING]
        
        overdue_reviews = [r for r in pending_records 
                          if r.review_deadline and current_time > r.review_deadline]
        
        # Calculate resolution times
        resolved_records = [r for r in self.quarantine_registry.values() 
                           if r.release_timestamp]
        
        avg_resolution_time = None
        if resolved_records:
            resolution_times = [(r.release_timestamp - r.timestamp).total_seconds() / 3600 
                               for r in resolved_records]
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
        
        analytics = {
            "summary_stats": self.stats.copy(),
            "current_metrics": {
                "total_active_quarantines": len([r for r in self.quarantine_registry.values() 
                                                if r.status not in [QuarantineStatus.EXPIRED]]),
                "pending_review_count": len(pending_records),
                "overdue_review_count": len(overdue_reviews),
                "escalation_queue_size": len(self.review_workflow.escalation_queue)
            },
            "performance_metrics": {
                "average_resolution_time_hours": avg_resolution_time,
                "approval_rate": self.stats["approved"] / max(1, self.stats["approved"] + self.stats["rejected"]),
                "quarantine_effectiveness": len(self.quarantine_registry) / max(1, self.stats["total_quarantined"])
            },
            "data_breakdown": self._get_data_type_breakdown(),
            "anomaly_breakdown": self._get_anomaly_type_breakdown()
        }
        
        return analytics
    
    def _extract_data_characteristics(self, data: Any, data_type: DataType) -> Dict[str, Any]:
        """Extract characteristics from data for metadata"""
        characteristics = {"data_type": data_type.value}
        
        if isinstance(data, list):
            characteristics["record_count"] = len(data)
            if data:
                characteristics["sample_record"] = str(data[0])[:100]
        else:
            characteristics["record_count"] = 1
            characteristics["sample_record"] = str(data)[:100]
        
        return characteristics
    
    def _filter_data_subset(self, data: Any, approved_subset: List[str]) -> Any:
        """Filter data to approved subset for partial releases"""
        # This is a simplified implementation
        # In production, this would need sophisticated filtering logic
        if isinstance(data, list) and approved_subset:
            try:
                approved_indices = [int(idx) for idx in approved_subset if idx.isdigit()]
                return [data[i] for i in approved_indices if i < len(data)]
            except (ValueError, IndexError):
                logger.warning("Failed to filter data subset, returning original data")
                return data
        return data
    
    def _get_data_type_breakdown(self) -> Dict[str, int]:
        """Get breakdown of quarantined data by type"""
        breakdown = {}
        for record in self.quarantine_registry.values():
            data_type = record.data_type.value
            breakdown[data_type] = breakdown.get(data_type, 0) + 1
        return breakdown
    
    def _get_anomaly_type_breakdown(self) -> Dict[str, int]:
        """Get breakdown of quarantined data by anomaly type"""
        breakdown = {}
        for record in self.quarantine_registry.values():
            anomaly_type = record.metadata.trigger_anomaly.condition_type.value
            breakdown[anomaly_type] = breakdown.get(anomaly_type, 0) + 1
        return breakdown