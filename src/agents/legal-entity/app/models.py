"""Data models for legal entity management."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, IPvAnyAddress
from sqlalchemy import Column, String, DateTime, Date, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EntityType(str, Enum):
    LLC = "LLC"
    CORPORATION = "Corporation"
    TRUST = "Trust"
    PARTNERSHIP = "Partnership"
    SOLE_PROPRIETORSHIP = "Sole_Proprietorship"


class EntityStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class ActionType(str, Enum):
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    CONFIGURATION = "configuration"
    ANALYSIS = "analysis"
    COMPLIANCE = "compliance"
    TOS_ACCEPTANCE = "tos_acceptance"


class JurisdictionRestriction(str, Enum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"


class LegalEntity(Base):
    """SQLAlchemy model for legal entities."""
    __tablename__ = 'legal_entities'
    
    entity_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_name = Column(String(200), nullable=False)
    entity_type = Column(String(50), nullable=False)
    jurisdiction = Column(String(100), nullable=False)
    registration_number = Column(String(100), unique=True)
    tax_id = Column(String(50))
    registered_address = Column(Text, nullable=False)
    mailing_address = Column(Text)
    incorporation_date = Column(Date, nullable=False)
    status = Column(String(20), default=EntityStatus.ACTIVE.value)
    tos_accepted_version = Column(String(20))
    tos_accepted_date = Column(DateTime(timezone=True))
    tos_accepted_ip = Column(String(45))  # Support both IPv4 and IPv6
    entity_metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class EntityAuditLog(Base):
    """SQLAlchemy model for entity audit logs."""
    __tablename__ = 'entity_audit_logs'
    
    log_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_id = Column(PGUUID(as_uuid=True), ForeignKey('legal_entities.entity_id'), nullable=False)
    account_id = Column(PGUUID(as_uuid=True))
    action_type = Column(String(50), nullable=False)
    action_details = Column(JSON, nullable=False)
    decision_rationale = Column(Text)
    correlation_id = Column(PGUUID(as_uuid=True), nullable=False, default=uuid4)
    signature = Column(String(256))
    previous_hash = Column(String(256))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_entity_audit_entity', 'entity_id'),
        Index('idx_entity_audit_timestamp', 'created_at'),
        Index('idx_entity_audit_correlation', 'correlation_id'),
    )


class DecisionLog(Base):
    """SQLAlchemy model for independent decision logging."""
    __tablename__ = 'decision_logs'
    
    decision_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_id = Column(PGUUID(as_uuid=True), ForeignKey('legal_entities.entity_id'), nullable=False)
    account_id = Column(PGUUID(as_uuid=True))
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    decision_type = Column(String(50), nullable=False)
    analysis = Column(JSON, nullable=False)
    action = Column(JSON, nullable=False)
    independent_factors = Column(JSON, nullable=False)
    personality_profile = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_decision_entity', 'entity_id'),
        Index('idx_decision_timestamp', 'timestamp'),
    )


class GeographicRestriction(Base):
    """SQLAlchemy model for geographic restrictions."""
    __tablename__ = 'geographic_restrictions'
    
    restriction_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    jurisdiction = Column(String(100), nullable=False, unique=True)
    restriction_level = Column(String(20), nullable=False)
    trading_hours = Column(JSON)
    holidays = Column(JSON)
    regulatory_requirements = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ToSAcceptance(Base):
    """SQLAlchemy model for Terms of Service acceptance tracking."""
    __tablename__ = 'tos_acceptances'
    
    acceptance_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_id = Column(PGUUID(as_uuid=True), ForeignKey('legal_entities.entity_id'), nullable=False)
    version = Column(String(20), nullable=False)
    accepted_date = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String(45), nullable=False)  # Support both IPv4 and IPv6
    user_agent = Column(Text)
    device_fingerprint = Column(String(256))
    acceptance_method = Column(String(50))
    document_hash = Column(String(256))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_tos_entity', 'entity_id'),
        Index('idx_tos_version', 'version'),
    )


# Pydantic models for API requests/responses

class LegalEntityCreate(BaseModel):
    """Model for creating a new legal entity."""
    entity_name: str = Field(..., min_length=1, max_length=200)
    entity_type: EntityType
    jurisdiction: str = Field(..., min_length=1, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    registered_address: str = Field(..., min_length=1)
    mailing_address: Optional[str] = None
    incorporation_date: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LegalEntityResponse(BaseModel):
    """Model for legal entity responses."""
    entity_id: UUID
    entity_name: str
    entity_type: EntityType
    jurisdiction: str
    registration_number: Optional[str]
    tax_id: Optional[str]
    registered_address: str
    mailing_address: Optional[str]
    incorporation_date: datetime
    status: EntityStatus
    tos_accepted_version: Optional[str]
    tos_accepted_date: Optional[datetime]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ToSAcceptanceRequest(BaseModel):
    """Model for recording ToS acceptance."""
    entity_id: UUID
    version: str = Field(..., min_length=1, max_length=20)
    ip_address: str
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    acceptance_method: str = Field(default="click", max_length=50)


class DecisionLogEntry(BaseModel):
    """Model for decision log entries."""
    entity_id: UUID
    account_id: Optional[UUID]
    decision_type: str
    analysis: Dict[str, Any]
    action: Dict[str, Any]
    independent_factors: Dict[str, Any]
    personality_profile: Optional[str]


class AuditLogEntry(BaseModel):
    """Model for audit log entries."""
    entity_id: UUID
    account_id: Optional[UUID]
    action_type: ActionType
    action_details: Dict[str, Any]
    decision_rationale: Optional[str]
    correlation_id: Optional[UUID] = Field(default_factory=uuid4)


class ComplianceReport(BaseModel):
    """Model for compliance report generation."""
    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    period_start: datetime
    period_end: datetime
    total_entities: int
    active_entities: int
    compliance_score: float
    independence_metrics: Dict[str, Any]
    trading_patterns: Dict[str, Any]
    audit_summary: Dict[str, Any]
    regulatory_compliance: Dict[str, Any]
    recommendations: List[str]


class EntityComplianceStatus(BaseModel):
    """Model for entity compliance status."""
    entity_id: UUID
    entity_name: str
    is_compliant: bool
    tos_current: bool
    geographic_compliance: bool
    audit_trail_complete: bool
    independence_score: float
    issues: List[str]
    last_activity: Optional[datetime]


class GeographicRestrictionConfig(BaseModel):
    """Model for geographic restriction configuration."""
    jurisdiction: str
    restriction_level: JurisdictionRestriction
    trading_hours: Optional[Dict[str, str]]
    holidays: Optional[List[datetime]]
    regulatory_requirements: Optional[Dict[str, Any]]