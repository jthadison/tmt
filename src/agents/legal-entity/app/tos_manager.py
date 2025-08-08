"""Terms of Service acceptance and tracking management."""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from .models import (
    ToSAcceptance, LegalEntity,
    ToSAcceptanceRequest, ActionType
)
from .audit_service import AuditService


class ToSManager:
    """Manages Terms of Service acceptance and compliance."""
    
    def __init__(self, db_session: Session, audit_service: AuditService):
        self.db = db_session
        self.audit = audit_service
        self.current_version = "2.0.0"
        self.versions = {
            "1.0.0": {
                "released": datetime(2024, 1, 1),
                "deprecated": datetime(2024, 6, 1),
                "hash": "abc123..."
            },
            "1.5.0": {
                "released": datetime(2024, 6, 1),
                "deprecated": datetime(2024, 12, 1),
                "hash": "def456..."
            },
            "2.0.0": {
                "released": datetime(2024, 12, 1),
                "deprecated": None,
                "hash": "ghi789..."
            }
        }
    
    async def record_acceptance(
        self,
        acceptance_request: ToSAcceptanceRequest
    ) -> Dict[str, Any]:
        """Record ToS acceptance with full audit trail."""
        # Verify entity exists
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == acceptance_request.entity_id
        ).first()
        
        if not entity:
            raise ValueError(f"Entity {acceptance_request.entity_id} not found")
        
        # Create acceptance record
        acceptance = ToSAcceptance(
            entity_id=acceptance_request.entity_id,
            version=acceptance_request.version,
            accepted_date=datetime.utcnow(),
            ip_address=acceptance_request.ip_address,
            user_agent=acceptance_request.user_agent,
            device_fingerprint=acceptance_request.device_fingerprint,
            acceptance_method=acceptance_request.acceptance_method,
            document_hash=self.versions.get(acceptance_request.version, {}).get("hash")
        )
        
        self.db.add(acceptance)
        
        # Update entity record
        entity.tos_accepted_version = acceptance_request.version
        entity.tos_accepted_date = acceptance.accepted_date
        entity.tos_accepted_ip = acceptance_request.ip_address
        
        self.db.commit()
        self.db.refresh(acceptance)
        
        # Create audit log
        await self.audit.create_audit_entry(
            entity_id=acceptance_request.entity_id,
            action_type=ActionType.TOS_ACCEPTANCE,
            action_details={
                "version": acceptance_request.version,
                "ip_address": acceptance_request.ip_address,
                "method": acceptance_request.acceptance_method,
                "timestamp": acceptance.accepted_date.isoformat()
            },
            decision_rationale=f"Terms of Service v{acceptance_request.version} accepted"
        )
        
        # Generate acceptance proof
        proof = await self.generate_acceptance_proof(acceptance)
        
        return {
            "acceptance_id": str(acceptance.acceptance_id),
            "entity_id": str(acceptance.entity_id),
            "version": acceptance.version,
            "accepted_date": acceptance.accepted_date.isoformat(),
            "proof": proof,
            "valid_until": (acceptance.accepted_date + timedelta(days=365)).isoformat()
        }
    
    async def check_compliance(self, entity_id: UUID) -> Dict[str, Any]:
        """Check ToS compliance for an entity."""
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == entity_id
        ).first()
        
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        
        # Get latest acceptance
        latest_acceptance = self.db.query(ToSAcceptance).filter(
            ToSAcceptance.entity_id == entity_id
        ).order_by(desc(ToSAcceptance.accepted_date)).first()
        
        if not latest_acceptance:
            return {
                "compliant": False,
                "current_version": self.current_version,
                "accepted_version": None,
                "requires_acceptance": True,
                "reason": "No Terms of Service acceptance on record"
            }
        
        # Check version currency
        is_current = latest_acceptance.version == self.current_version
        
        # Check acceptance expiry (1 year)
        acceptance_expired = (
            datetime.utcnow() - latest_acceptance.accepted_date
        ).days > 365
        
        compliant = is_current and not acceptance_expired
        
        reasons = []
        if not is_current:
            reasons.append(f"Outdated version (accepted: {latest_acceptance.version}, current: {self.current_version})")
        if acceptance_expired:
            reasons.append("Acceptance expired (>365 days)")
        
        return {
            "compliant": compliant,
            "current_version": self.current_version,
            "accepted_version": latest_acceptance.version,
            "accepted_date": latest_acceptance.accepted_date.isoformat(),
            "expires_date": (latest_acceptance.accepted_date + timedelta(days=365)).isoformat(),
            "requires_acceptance": not compliant,
            "reason": " | ".join(reasons) if reasons else "Compliant"
        }
    
    async def get_acceptance_history(
        self,
        entity_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get ToS acceptance history for an entity."""
        acceptances = self.db.query(ToSAcceptance).filter(
            ToSAcceptance.entity_id == entity_id
        ).order_by(desc(ToSAcceptance.accepted_date)).limit(limit).all()
        
        history = []
        for acceptance in acceptances:
            history.append({
                "acceptance_id": str(acceptance.acceptance_id),
                "version": acceptance.version,
                "accepted_date": acceptance.accepted_date.isoformat(),
                "ip_address": str(acceptance.ip_address),
                "acceptance_method": acceptance.acceptance_method,
                "document_hash": acceptance.document_hash
            })
        
        return history
    
    async def generate_acceptance_proof(
        self,
        acceptance: ToSAcceptance
    ) -> Dict[str, Any]:
        """Generate cryptographic proof of ToS acceptance."""
        proof_data = {
            "acceptance_id": str(acceptance.acceptance_id),
            "entity_id": str(acceptance.entity_id),
            "version": acceptance.version,
            "accepted_date": acceptance.accepted_date.isoformat(),
            "ip_address": str(acceptance.ip_address),
            "user_agent": acceptance.user_agent,
            "device_fingerprint": acceptance.device_fingerprint,
            "acceptance_method": acceptance.acceptance_method,
            "document_hash": acceptance.document_hash
        }
        
        # Generate proof hash
        proof_json = json.dumps(proof_data, sort_keys=True, default=str)
        proof_hash = hashlib.sha256(proof_json.encode()).hexdigest()
        
        return {
            "proof_hash": proof_hash,
            "proof_data": proof_data,
            "generated_at": datetime.utcnow().isoformat(),
            "verification_method": "SHA256"
        }
    
    async def notify_required_updates(self) -> List[Dict[str, Any]]:
        """Identify entities requiring ToS updates."""
        entities_requiring_update = []
        
        # Get all active entities
        entities = self.db.query(LegalEntity).filter(
            LegalEntity.status == "active"
        ).all()
        
        for entity in entities:
            compliance = await self.check_compliance(entity.entity_id)
            
            if not compliance["compliant"]:
                entities_requiring_update.append({
                    "entity_id": str(entity.entity_id),
                    "entity_name": entity.entity_name,
                    "current_version": compliance["accepted_version"],
                    "required_version": self.current_version,
                    "reason": compliance["reason"]
                })
        
        return entities_requiring_update
    
    async def bulk_check_compliance(
        self,
        entity_ids: List[UUID]
    ) -> Dict[str, Dict[str, Any]]:
        """Check ToS compliance for multiple entities."""
        results = {}
        
        for entity_id in entity_ids:
            try:
                results[str(entity_id)] = await self.check_compliance(entity_id)
            except Exception as e:
                results[str(entity_id)] = {
                    "compliant": False,
                    "error": str(e)
                }
        
        return results
    
    async def get_version_info(self, version: Optional[str] = None) -> Dict[str, Any]:
        """Get information about ToS versions."""
        if version:
            version_data = self.versions.get(version)
            if not version_data:
                raise ValueError(f"Version {version} not found")
            
            return {
                "version": version,
                "released": version_data["released"].isoformat(),
                "deprecated": version_data["deprecated"].isoformat() if version_data["deprecated"] else None,
                "hash": version_data["hash"],
                "is_current": version == self.current_version
            }
        
        # Return all versions
        all_versions = []
        for ver, data in self.versions.items():
            all_versions.append({
                "version": ver,
                "released": data["released"].isoformat(),
                "deprecated": data["deprecated"].isoformat() if data["deprecated"] else None,
                "is_current": ver == self.current_version
            })
        
        return {
            "current_version": self.current_version,
            "versions": all_versions,
            "total_versions": len(self.versions)
        }
    
    async def validate_acceptance_proof(
        self,
        proof_hash: str,
        proof_data: Dict[str, Any]
    ) -> bool:
        """Validate a ToS acceptance proof."""
        # Recreate hash from proof data
        proof_json = json.dumps(proof_data, sort_keys=True, default=str)
        computed_hash = hashlib.sha256(proof_json.encode()).hexdigest()
        
        return computed_hash == proof_hash


import json  # Add this import at the top of the file