"""Comprehensive audit trail service with cryptographic integrity."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from .models import EntityAuditLog, ActionType


class AuditService:
    """Service for managing audit trails with integrity verification."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.retention_policy = {
            "trade": timedelta(days=365 * 7),  # 7 years for trade logs
            "operational": timedelta(days=365 * 2),  # 2 years for operational logs
            "compliance": timedelta(days=365 * 7)  # 7 years for compliance logs
        }
    
    async def create_audit_entry(
        self,
        entity_id: UUID,
        action_type: ActionType,
        action_details: Dict[str, Any],
        decision_rationale: Optional[str] = None,
        account_id: Optional[UUID] = None,
        correlation_id: Optional[UUID] = None
    ) -> EntityAuditLog:
        """Create a new audit log entry with cryptographic signing."""
        # Get previous log for hash chaining
        previous_log = self.db.query(EntityAuditLog).filter(
            EntityAuditLog.entity_id == entity_id
        ).order_by(EntityAuditLog.created_at.desc()).first()
        
        previous_hash = previous_log.signature if previous_log else "genesis_block"
        
        # Create new log entry
        log_entry = EntityAuditLog(
            entity_id=entity_id,
            account_id=account_id,
            action_type=action_type.value,
            action_details=action_details,
            decision_rationale=decision_rationale,
            correlation_id=correlation_id,
            previous_hash=previous_hash
        )
        
        # Generate signature
        log_entry.signature = self._generate_signature(log_entry, previous_hash)
        
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        
        return log_entry
    
    async def verify_audit_trail_integrity(
        self,
        entity_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Verify the integrity of the audit trail for an entity."""
        query = self.db.query(EntityAuditLog).filter(
            EntityAuditLog.entity_id == entity_id
        )
        
        if start_date:
            query = query.filter(EntityAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(EntityAuditLog.created_at <= end_date)
        
        logs = query.order_by(EntityAuditLog.created_at.asc()).all()
        
        if not logs:
            return {
                "valid": True,
                "total_logs": 0,
                "errors": [],
                "message": "No logs found for verification"
            }
        
        errors = []
        valid_count = 0
        
        for i, log in enumerate(logs):
            # Verify signature
            expected_previous_hash = "genesis_block" if i == 0 else logs[i-1].signature
            
            if log.previous_hash != expected_previous_hash:
                errors.append({
                    "log_id": str(log.log_id),
                    "error": "Hash chain broken",
                    "expected_previous": expected_previous_hash,
                    "actual_previous": log.previous_hash
                })
                continue
            
            # Verify signature
            computed_signature = self._generate_signature(log, log.previous_hash)
            if computed_signature != log.signature:
                errors.append({
                    "log_id": str(log.log_id),
                    "error": "Invalid signature",
                    "expected": computed_signature,
                    "actual": log.signature
                })
            else:
                valid_count += 1
        
        return {
            "valid": len(errors) == 0,
            "total_logs": len(logs),
            "valid_logs": valid_count,
            "invalid_logs": len(errors),
            "errors": errors[:10],  # Limit error details
            "verification_timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_audit_trail(
        self,
        entity_id: UUID,
        action_types: Optional[List[ActionType]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve audit trail for an entity with filters."""
        query = self.db.query(EntityAuditLog).filter(
            EntityAuditLog.entity_id == entity_id
        )
        
        if action_types:
            query = query.filter(
                EntityAuditLog.action_type.in_([a.value for a in action_types])
            )
        
        if start_date:
            query = query.filter(EntityAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(EntityAuditLog.created_at <= end_date)
        
        logs = query.order_by(EntityAuditLog.created_at.desc()).limit(limit).all()
        
        return [self._serialize_log(log) for log in logs]
    
    async def generate_audit_summary(
        self,
        entity_id: UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Generate audit trail summary for reporting."""
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get total logs by type
        action_counts = self.db.query(
            EntityAuditLog.action_type,
            func.count(EntityAuditLog.log_id).label('count')
        ).filter(
            and_(
                EntityAuditLog.entity_id == entity_id,
                EntityAuditLog.created_at >= start_date
            )
        ).group_by(EntityAuditLog.action_type).all()
        
        action_summary = {ac[0]: ac[1] for ac in action_counts}
        
        # Get total logs
        total_logs = self.db.query(func.count(EntityAuditLog.log_id)).filter(
            and_(
                EntityAuditLog.entity_id == entity_id,
                EntityAuditLog.created_at >= start_date
            )
        ).scalar()
        
        # Verify integrity
        integrity_check = await self.verify_audit_trail_integrity(
            entity_id, start_date
        )
        
        # Get first and last log
        first_log = self.db.query(EntityAuditLog).filter(
            and_(
                EntityAuditLog.entity_id == entity_id,
                EntityAuditLog.created_at >= start_date
            )
        ).order_by(EntityAuditLog.created_at.asc()).first()
        
        last_log = self.db.query(EntityAuditLog).filter(
            and_(
                EntityAuditLog.entity_id == entity_id,
                EntityAuditLog.created_at >= start_date
            )
        ).order_by(EntityAuditLog.created_at.desc()).first()
        
        return {
            "entity_id": str(entity_id),
            "period_start": start_date.isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "total_logs": total_logs,
            "action_summary": action_summary,
            "integrity_valid": integrity_check["valid"],
            "integrity_details": {
                "valid_logs": integrity_check.get("valid_logs", 0),
                "invalid_logs": integrity_check.get("invalid_logs", 0)
            },
            "first_activity": first_log.created_at.isoformat() if first_log else None,
            "last_activity": last_log.created_at.isoformat() if last_log else None,
            "coverage_complete": total_logs > 0
        }
    
    async def archive_old_logs(self) -> Dict[str, int]:
        """Archive old logs based on retention policy."""
        archived_counts = {}
        
        for action_category, retention_period in self.retention_policy.items():
            cutoff_date = datetime.utcnow() - retention_period
            
            # In production, this would move logs to cold storage
            # For now, we'll just count what would be archived
            if action_category == "trade":
                action_types = [ActionType.TRADE_ENTRY.value, ActionType.TRADE_EXIT.value]
            elif action_category == "compliance":
                action_types = [ActionType.COMPLIANCE.value, ActionType.TOS_ACCEPTANCE.value]
            else:
                action_types = [ActionType.CONFIGURATION.value, ActionType.ANALYSIS.value]
            
            count = self.db.query(func.count(EntityAuditLog.log_id)).filter(
                and_(
                    EntityAuditLog.action_type.in_(action_types),
                    EntityAuditLog.created_at < cutoff_date
                )
            ).scalar()
            
            archived_counts[action_category] = count
        
        return archived_counts
    
    async def detect_tampering(
        self,
        entity_id: UUID,
        check_period_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Detect potential tampering in audit logs."""
        start_date = datetime.utcnow() - timedelta(days=check_period_days)
        
        integrity_check = await self.verify_audit_trail_integrity(
            entity_id, start_date
        )
        
        tampering_indicators = []
        
        if not integrity_check["valid"]:
            for error in integrity_check["errors"]:
                tampering_indicators.append({
                    "type": "integrity_violation",
                    "severity": "critical",
                    "details": error,
                    "detected_at": datetime.utcnow().isoformat()
                })
        
        # Check for suspicious patterns
        logs = self.db.query(EntityAuditLog).filter(
            and_(
                EntityAuditLog.entity_id == entity_id,
                EntityAuditLog.created_at >= start_date
            )
        ).order_by(EntityAuditLog.created_at.asc()).all()
        
        # Check for time anomalies
        for i in range(1, len(logs)):
            time_diff = (logs[i].created_at - logs[i-1].created_at).total_seconds()
            if time_diff < 0:  # Logs out of order
                tampering_indicators.append({
                    "type": "temporal_anomaly",
                    "severity": "high",
                    "details": {
                        "log_id": str(logs[i].log_id),
                        "message": "Log timestamp earlier than previous log"
                    },
                    "detected_at": datetime.utcnow().isoformat()
                })
        
        return tampering_indicators
    
    def _generate_signature(self, log_entry: EntityAuditLog, previous_hash: str) -> str:
        """Generate cryptographic signature for log entry."""
        data_to_sign = {
            "entity_id": str(log_entry.entity_id),
            "account_id": str(log_entry.account_id) if log_entry.account_id else None,
            "action_type": log_entry.action_type,
            "action_details": log_entry.action_details,
            "decision_rationale": log_entry.decision_rationale,
            "correlation_id": str(log_entry.correlation_id),
            "previous_hash": previous_hash,
            "timestamp": log_entry.created_at.isoformat() if log_entry.created_at else datetime.utcnow().isoformat()
        }
        
        json_data = json.dumps(data_to_sign, sort_keys=True, default=str)
        return hashlib.sha256(json_data.encode()).hexdigest()
    
    def _serialize_log(self, log: EntityAuditLog) -> Dict[str, Any]:
        """Serialize audit log for API response."""
        return {
            "log_id": str(log.log_id),
            "entity_id": str(log.entity_id),
            "account_id": str(log.account_id) if log.account_id else None,
            "action_type": log.action_type,
            "action_details": log.action_details,
            "decision_rationale": log.decision_rationale,
            "correlation_id": str(log.correlation_id),
            "signature": log.signature,
            "previous_hash": log.previous_hash,
            "created_at": log.created_at.isoformat()
        }