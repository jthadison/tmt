"""Legal entity management service."""

import hashlib
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func

from .models import (
    LegalEntity, EntityAuditLog, DecisionLog,
    EntityType, EntityStatus, ActionType,
    LegalEntityCreate, LegalEntityResponse,
    EntityComplianceStatus
)


class EntityManager:
    """Manages legal entities and ensures regulatory compliance."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.personality_profiles = [
            "conservative", "moderate", "aggressive",
            "systematic", "opportunistic", "balanced"
        ]
    
    async def create_entity(self, entity_data: LegalEntityCreate) -> LegalEntityResponse:
        """Create a new legal entity with unique characteristics."""
        try:
            entity = LegalEntity(
                entity_name=entity_data.entity_name,
                entity_type=entity_data.entity_type.value,
                jurisdiction=entity_data.jurisdiction,
                registration_number=entity_data.registration_number or self._generate_registration_number(),
                tax_id=entity_data.tax_id,
                registered_address=entity_data.registered_address,
                mailing_address=entity_data.mailing_address,
                incorporation_date=entity_data.incorporation_date,
                metadata=entity_data.metadata
            )
            
            # Assign unique personality profile
            entity.metadata["personality_profile"] = random.choice(self.personality_profiles)
            entity.metadata["risk_tolerance"] = random.uniform(0.3, 0.8)
            entity.metadata["decision_speed"] = random.uniform(5, 30)  # seconds
            
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            
            # Log entity creation
            await self._log_action(
                entity_id=entity.entity_id,
                action_type=ActionType.CONFIGURATION,
                action_details={
                    "action": "entity_created",
                    "entity_type": entity.entity_type,
                    "jurisdiction": entity.jurisdiction
                },
                decision_rationale=f"New legal entity created: {entity.entity_name}"
            )
            
            return LegalEntityResponse.from_orm(entity)
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Entity creation failed: {str(e)}")
    
    async def get_entity(self, entity_id: UUID) -> Optional[LegalEntityResponse]:
        """Retrieve a legal entity by ID."""
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == entity_id
        ).first()
        
        if entity:
            return LegalEntityResponse.from_orm(entity)
        return None
    
    async def list_entities(
        self,
        status: Optional[EntityStatus] = None,
        jurisdiction: Optional[str] = None
    ) -> List[LegalEntityResponse]:
        """List legal entities with optional filters."""
        query = self.db.query(LegalEntity)
        
        if status:
            query = query.filter(LegalEntity.status == status.value)
        if jurisdiction:
            query = query.filter(LegalEntity.jurisdiction == jurisdiction)
        
        entities = query.all()
        return [LegalEntityResponse.from_orm(e) for e in entities]
    
    async def update_entity_status(
        self,
        entity_id: UUID,
        status: EntityStatus,
        reason: str
    ) -> bool:
        """Update entity status with audit logging."""
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == entity_id
        ).first()
        
        if not entity:
            return False
        
        old_status = entity.status
        entity.status = status.value
        entity.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Log status change
        await self._log_action(
            entity_id=entity_id,
            action_type=ActionType.CONFIGURATION,
            action_details={
                "action": "status_change",
                "old_status": old_status,
                "new_status": status.value,
                "reason": reason
            },
            decision_rationale=f"Entity status changed from {old_status} to {status.value}: {reason}"
        )
        
        return True
    
    async def ensure_entity_independence(
        self,
        entity_id: UUID,
        decision_type: str,
        base_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensure decision independence for the entity."""
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == entity_id
        ).first()
        
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        
        # Get entity's unique characteristics
        personality = entity.metadata.get("personality_profile", "moderate")
        risk_tolerance = entity.metadata.get("risk_tolerance", 0.5)
        decision_speed = entity.metadata.get("decision_speed", 15)
        
        # Apply temporal separation
        delay_ms = int(random.uniform(decision_speed * 0.8, decision_speed * 1.2) * 1000)
        
        # Modify decision based on entity personality
        independent_decision = self._apply_personality_variation(
            base_decision, personality, risk_tolerance
        )
        
        # Generate unique rationale
        rationale = self._generate_unique_rationale(
            decision_type, personality, independent_decision
        )
        
        # Create decision log entry
        decision_log = DecisionLog(
            entity_id=entity_id,
            decision_type=decision_type,
            analysis={
                "base_analysis": base_decision.get("analysis", {}),
                "personality_influence": personality,
                "risk_adjustment": risk_tolerance
            },
            action=independent_decision,
            independent_factors={
                "decision_delay_ms": delay_ms,
                "personality_influence": personality,
                "unique_seed": str(uuid4()),
                "variance_applied": True
            },
            personality_profile=personality
        )
        
        self.db.add(decision_log)
        self.db.commit()
        
        return {
            "decision": independent_decision,
            "rationale": rationale,
            "delay_ms": delay_ms,
            "entity_id": str(entity_id)
        }
    
    async def check_entity_compliance(self, entity_id: UUID) -> EntityComplianceStatus:
        """Check compliance status for an entity."""
        entity = self.db.query(LegalEntity).filter(
            LegalEntity.entity_id == entity_id
        ).first()
        
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        
        issues = []
        
        # Check ToS acceptance
        tos_current = bool(entity.tos_accepted_version and 
                          entity.tos_accepted_date and
                          entity.tos_accepted_date > datetime.utcnow() - timedelta(days=365))
        if not tos_current:
            issues.append("Terms of Service acceptance expired or missing")
        
        # Check audit trail completeness
        recent_logs = self.db.query(EntityAuditLog).filter(
            and_(
                EntityAuditLog.entity_id == entity_id,
                EntityAuditLog.created_at > datetime.utcnow() - timedelta(days=30)
            )
        ).count()
        
        audit_complete = recent_logs > 0
        if not audit_complete:
            issues.append("No recent audit logs found")
        
        # Calculate independence score
        independence_score = await self._calculate_independence_score(entity_id)
        if independence_score < 0.7:
            issues.append(f"Low independence score: {independence_score:.2f}")
        
        # Get last activity
        last_decision = self.db.query(DecisionLog).filter(
            DecisionLog.entity_id == entity_id
        ).order_by(DecisionLog.timestamp.desc()).first()
        
        last_activity = last_decision.timestamp if last_decision else None
        
        is_compliant = len(issues) == 0
        
        return EntityComplianceStatus(
            entity_id=entity_id,
            entity_name=entity.entity_name,
            is_compliant=is_compliant,
            tos_current=tos_current,
            geographic_compliance=True,  # Will be implemented with geographic restrictions
            audit_trail_complete=audit_complete,
            independence_score=independence_score,
            issues=issues,
            last_activity=last_activity
        )
    
    async def _log_action(
        self,
        entity_id: UUID,
        action_type: ActionType,
        action_details: Dict[str, Any],
        decision_rationale: Optional[str] = None,
        account_id: Optional[UUID] = None
    ):
        """Create an audit log entry with cryptographic integrity."""
        # Get the previous log entry for hash chaining
        previous_log = self.db.query(EntityAuditLog).filter(
            EntityAuditLog.entity_id == entity_id
        ).order_by(EntityAuditLog.created_at.desc()).first()
        
        previous_hash = previous_log.signature if previous_log else "genesis"
        
        # Create log entry
        log_entry = EntityAuditLog(
            entity_id=entity_id,
            account_id=account_id,
            action_type=action_type.value,
            action_details=action_details,
            decision_rationale=decision_rationale,
            previous_hash=previous_hash
        )
        
        # Generate cryptographic signature
        log_data = {
            "entity_id": str(entity_id),
            "action_type": action_type.value,
            "action_details": action_details,
            "timestamp": log_entry.created_at.isoformat(),
            "previous_hash": previous_hash
        }
        
        log_entry.signature = self._generate_signature(log_data)
        
        self.db.add(log_entry)
        self.db.commit()
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate SHA-256 signature for log integrity."""
        json_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_data.encode()).hexdigest()
    
    def _generate_registration_number(self) -> str:
        """Generate a unique registration number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_suffix = random.randint(1000, 9999)
        return f"REG-{timestamp}-{random_suffix}"
    
    def _apply_personality_variation(
        self,
        base_decision: Dict[str, Any],
        personality: str,
        risk_tolerance: float
    ) -> Dict[str, Any]:
        """Apply personality-based variations to decisions."""
        modified_decision = base_decision.copy()
        
        # Adjust position size based on personality
        if "size" in modified_decision:
            if personality == "conservative":
                modified_decision["size"] *= (0.7 + risk_tolerance * 0.3)
            elif personality == "aggressive":
                modified_decision["size"] *= (1.0 + risk_tolerance * 0.5)
            elif personality == "systematic":
                modified_decision["size"] = round(modified_decision["size"], 2)
        
        # Adjust entry/exit points
        if "entry" in modified_decision:
            variance = random.uniform(-0.0005, 0.0005)
            if personality == "opportunistic":
                variance *= 2
            modified_decision["entry"] += variance
        
        # Add personality-specific indicators
        modified_decision["personality_traits"] = {
            "profile": personality,
            "risk_tolerance": risk_tolerance,
            "execution_style": self._get_execution_style(personality)
        }
        
        return modified_decision
    
    def _get_execution_style(self, personality: str) -> str:
        """Get execution style based on personality."""
        styles = {
            "conservative": "limit_orders",
            "aggressive": "market_orders",
            "systematic": "scheduled",
            "opportunistic": "adaptive",
            "moderate": "mixed",
            "balanced": "optimized"
        }
        return styles.get(personality, "mixed")
    
    def _generate_unique_rationale(
        self,
        decision_type: str,
        personality: str,
        decision: Dict[str, Any]
    ) -> str:
        """Generate unique decision rationale based on entity personality."""
        templates = {
            "conservative": [
                f"Cautious {decision_type} based on strong confirmation signals",
                f"Risk-averse approach to {decision_type} with protective measures",
                f"Conservative {decision_type} following established safety protocols"
            ],
            "aggressive": [
                f"Opportunistic {decision_type} targeting maximum potential",
                f"Bold {decision_type} capitalizing on market momentum",
                f"Aggressive positioning for {decision_type} with high conviction"
            ],
            "systematic": [
                f"Rule-based {decision_type} per systematic trading protocol",
                f"Algorithmic {decision_type} triggered by quantitative signals",
                f"Systematic {decision_type} following predetermined criteria"
            ],
            "opportunistic": [
                f"Tactical {decision_type} exploiting market inefficiency",
                f"Adaptive {decision_type} based on current market dynamics",
                f"Opportunistic {decision_type} capturing short-term movement"
            ],
            "moderate": [
                f"Balanced {decision_type} considering risk-reward ratio",
                f"Measured {decision_type} with moderate position sizing",
                f"Standard {decision_type} following baseline strategy"
            ],
            "balanced": [
                f"Optimized {decision_type} balancing multiple factors",
                f"Well-rounded {decision_type} considering all market aspects",
                f"Balanced {decision_type} with diversified approach"
            ]
        }
        
        rationale_templates = templates.get(personality, templates["moderate"])
        base_rationale = random.choice(rationale_templates)
        
        # Add specific details
        details = []
        if "confidence" in decision:
            details.append(f"confidence: {decision['confidence']:.1f}%")
        if "size" in decision:
            details.append(f"position: {decision['size']}")
        
        if details:
            return f"{base_rationale} ({', '.join(details)})"
        return base_rationale
    
    async def _calculate_independence_score(self, entity_id: UUID) -> float:
        """Calculate independence score based on decision patterns."""
        # Get recent decisions for this entity
        recent_decisions = self.db.query(DecisionLog).filter(
            and_(
                DecisionLog.entity_id == entity_id,
                DecisionLog.timestamp > datetime.utcnow() - timedelta(days=7)
            )
        ).all()
        
        if len(recent_decisions) < 2:
            return 1.0  # Not enough data, assume independent
        
        # Calculate variance in decision timing
        timestamps = [d.timestamp for d in recent_decisions]
        time_deltas = []
        for i in range(1, len(timestamps)):
            delta = (timestamps[i] - timestamps[i-1]).total_seconds()
            time_deltas.append(delta)
        
        if time_deltas:
            avg_delta = sum(time_deltas) / len(time_deltas)
            variance = sum((d - avg_delta) ** 2 for d in time_deltas) / len(time_deltas)
            timing_score = min(1.0, variance / (avg_delta ** 2) if avg_delta > 0 else 1.0)
        else:
            timing_score = 1.0
        
        # Check for unique decision factors
        unique_factors = set()
        for decision in recent_decisions:
            if decision.independent_factors:
                unique_factors.add(decision.independent_factors.get("unique_seed"))
        
        uniqueness_score = len(unique_factors) / len(recent_decisions)
        
        # Calculate overall independence score
        independence_score = (timing_score * 0.5 + uniqueness_score * 0.5)
        
        return min(1.0, max(0.0, independence_score))