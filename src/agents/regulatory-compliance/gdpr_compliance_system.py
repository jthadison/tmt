"""
GDPR Compliance System - Story 8.15

Manages GDPR compliance for EU users including:
- Data subject rights (access, rectification, erasure, portability)
- Consent management
- Data processing records
- Privacy impact assessments
- Breach notification requirements
- Cross-border data transfer compliance
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json
import hashlib
from collections import defaultdict

logger = structlog.get_logger(__name__)


class DataSubjectRight(Enum):
    """GDPR data subject rights"""
    ACCESS = "access"  # Right to access personal data
    RECTIFICATION = "rectification"  # Right to rectify inaccurate data
    ERASURE = "erasure"  # Right to be forgotten
    PORTABILITY = "portability"  # Right to data portability
    RESTRICTION = "restriction"  # Right to restrict processing
    OBJECTION = "objection"  # Right to object to processing
    WITHDRAW_CONSENT = "withdraw_consent"  # Right to withdraw consent


class LawfulBasis(Enum):
    """GDPR lawful basis for processing"""
    CONSENT = "consent"  # Article 6(1)(a)
    CONTRACT = "contract"  # Article 6(1)(b)
    LEGAL_OBLIGATION = "legal_obligation"  # Article 6(1)(c)
    VITAL_INTERESTS = "vital_interests"  # Article 6(1)(d)
    PUBLIC_TASK = "public_task"  # Article 6(1)(e)
    LEGITIMATE_INTERESTS = "legitimate_interests"  # Article 6(1)(f)


class ProcessingPurpose(Enum):
    """Purposes for data processing"""
    ACCOUNT_MANAGEMENT = "account_management"
    TRADING_SERVICES = "trading_services"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    FRAUD_PREVENTION = "fraud_prevention"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    CUSTOMER_SUPPORT = "customer_support"


class ConsentStatus(Enum):
    """Consent status"""
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class RequestStatus(Enum):
    """Data subject request status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    PARTIALLY_COMPLETED = "partially_completed"


class BreachSeverity(Enum):
    """Data breach severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DataSubject:
    """Represents a data subject (EU user)"""
    subject_id: str
    email: str
    country: str
    is_eu_resident: bool
    registration_date: datetime
    last_login: Optional[datetime]
    account_status: str
    data_categories: Set[str]  # Categories of personal data we process
    consents: Dict[str, 'ConsentRecord'] = field(default_factory=dict)
    requests: List['DataSubjectRequest'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsentRecord:
    """Records consent given by data subject"""
    consent_id: str
    subject_id: str
    purpose: ProcessingPurpose
    lawful_basis: LawfulBasis
    consent_date: datetime
    expiry_date: Optional[datetime]
    status: ConsentStatus
    consent_text: str
    version: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    withdrawal_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSubjectRequest:
    """Data subject request under GDPR"""
    request_id: str
    subject_id: str
    request_type: DataSubjectRight
    request_date: datetime
    description: str
    status: RequestStatus
    due_date: datetime  # Must respond within 30 days
    assigned_to: Optional[str]
    response_date: Optional[datetime] = None
    response_data: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingRecord:
    """Record of processing activities (Article 30 GDPR)"""
    record_id: str
    controller_name: str
    contact_details: Dict[str, str]
    processing_purposes: List[ProcessingPurpose]
    data_categories: List[str]
    recipients: List[str]
    third_country_transfers: List[Dict[str, str]]
    retention_periods: Dict[str, int]  # Days
    security_measures: List[str]
    created_date: datetime
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataBreach:
    """Data breach incident record"""
    breach_id: str
    discovery_date: datetime
    breach_type: str
    affected_subjects_count: int
    data_categories_affected: List[str]
    severity: BreachSeverity
    description: str
    containment_measures: List[str]
    impact_assessment: str
    notification_required: bool
    authority_notified: bool = False
    authority_notification_date: Optional[datetime] = None
    subjects_notified: bool = False
    subjects_notification_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossBorderTransfer:
    """Record of cross-border data transfers"""
    transfer_id: str
    destination_country: str
    adequacy_decision: bool
    safeguards: List[str]  # Standard contractual clauses, BCRs, etc.
    data_categories: List[str]
    transfer_date: datetime
    recipient: str
    purpose: str
    retention_period: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class GDPRComplianceSystem:
    """Main GDPR compliance management system"""
    
    # GDPR response timeframes
    RESPONSE_PERIOD_DAYS = 30  # Standard response time
    BREACH_NOTIFICATION_HOURS = 72  # Authority notification
    BREACH_SUBJECT_NOTIFICATION_DAYS = 3  # Subject notification
    
    def __init__(self):
        self.data_subjects: Dict[str, DataSubject] = {}
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.data_subject_requests: Dict[str, DataSubjectRequest] = {}
        self.processing_records: List[ProcessingRecord] = []
        self.data_breaches: List[DataBreach] = []
        self.cross_border_transfers: List[CrossBorderTransfer] = []
        self.consent_manager = ConsentManager()
        self.request_processor = RequestProcessor()
        self.breach_manager = BreachManager()
        self.privacy_assessor = PrivacyImpactAssessor()
        
    async def initialize(self):
        """Initialize GDPR compliance system"""
        logger.info("Initializing GDPR compliance system")
        await self.consent_manager.initialize()
        await self.request_processor.initialize()
        await self.breach_manager.initialize()
        await self.privacy_assessor.initialize()
        
        # Create default processing record
        await self._create_default_processing_record()
        
    async def _create_default_processing_record(self):
        """Create default processing record for trading platform"""
        record = ProcessingRecord(
            record_id="trading_platform_main",
            controller_name="Trading Platform Ltd",
            contact_details={
                "address": "123 Trading Street, London, UK",
                "email": "privacy@tradingplatform.com",
                "phone": "+44 20 1234 5678"
            },
            processing_purposes=[
                ProcessingPurpose.ACCOUNT_MANAGEMENT,
                ProcessingPurpose.TRADING_SERVICES,
                ProcessingPurpose.REGULATORY_COMPLIANCE,
                ProcessingPurpose.FRAUD_PREVENTION
            ],
            data_categories=[
                "Identity data", "Contact data", "Financial data",
                "Trading data", "Technical data", "Usage data"
            ],
            recipients=[
                "Regulatory authorities", "Payment processors",
                "Cloud service providers", "Audit firms"
            ],
            third_country_transfers=[
                {
                    "country": "United States",
                    "safeguard": "Standard Contractual Clauses",
                    "purpose": "Cloud hosting services"
                }
            ],
            retention_periods={
                "trading_records": 7 * 365,  # 7 years
                "customer_data": 7 * 365,    # 7 years
                "marketing_data": 3 * 365,   # 3 years
                "analytics_data": 2 * 365    # 2 years
            },
            security_measures=[
                "Encryption at rest and in transit",
                "Multi-factor authentication",
                "Access controls and logging",
                "Regular security assessments",
                "Staff training and awareness"
            ],
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.processing_records.append(record)
        
    async def register_data_subject(self, email: str, country: str, account_data: Dict[str, Any]) -> DataSubject:
        """Register a new data subject"""
        is_eu_resident = self._is_eu_country(country)
        
        subject = DataSubject(
            subject_id=f"subj_{hashlib.md5(email.encode()).hexdigest()[:8]}",
            email=email,
            country=country,
            is_eu_resident=is_eu_resident,
            registration_date=datetime.now(),
            last_login=None,
            account_status="active",
            data_categories={
                "identity", "contact", "financial", "trading"
            }
        )
        
        self.data_subjects[subject.subject_id] = subject
        
        # If EU resident, create consent records for required purposes
        if is_eu_resident:
            await self._create_initial_consents(subject.subject_id)
        
        logger.info(f"Registered data subject: {subject.subject_id} (EU: {is_eu_resident})")
        return subject
        
    def _is_eu_country(self, country: str) -> bool:
        """Check if country is in EU/EEA"""
        eu_countries = {
            'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI',
            'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT',
            'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK', 'IS', 'LI', 'NO'
        }
        return country.upper() in eu_countries
        
    async def _create_initial_consents(self, subject_id: str):
        """Create initial consent records for EU subjects"""
        # Essential consents for service provision
        essential_consents = [
            (ProcessingPurpose.ACCOUNT_MANAGEMENT, LawfulBasis.CONTRACT),
            (ProcessingPurpose.TRADING_SERVICES, LawfulBasis.CONTRACT),
            (ProcessingPurpose.REGULATORY_COMPLIANCE, LawfulBasis.LEGAL_OBLIGATION),
            (ProcessingPurpose.FRAUD_PREVENTION, LawfulBasis.LEGITIMATE_INTERESTS)
        ]
        
        for purpose, basis in essential_consents:
            consent = ConsentRecord(
                consent_id=f"consent_{subject_id}_{purpose.value}",
                subject_id=subject_id,
                purpose=purpose,
                lawful_basis=basis,
                consent_date=datetime.now(),
                expiry_date=None,  # No expiry for essential services
                status=ConsentStatus.GIVEN,
                consent_text=f"Processing for {purpose.value} based on {basis.value}",
                version="1.0",
                ip_address=None,
                user_agent=None
            )
            
            self.consent_records[consent.consent_id] = consent
            self.data_subjects[subject_id].consents[purpose.value] = consent
            
    async def record_consent(self, subject_id: str, purpose: ProcessingPurpose,
                           consent_given: bool, ip_address: str = None,
                           user_agent: str = None) -> ConsentRecord:
        """Record consent for data processing"""
        if subject_id not in self.data_subjects:
            raise ValueError(f"Data subject not found: {subject_id}")
        
        subject = self.data_subjects[subject_id]
        
        if not subject.is_eu_resident:
            # Non-EU subjects don't need explicit consent tracking
            return None
        
        consent = ConsentRecord(
            consent_id=f"consent_{subject_id}_{purpose.value}_{datetime.now().timestamp()}",
            subject_id=subject_id,
            purpose=purpose,
            lawful_basis=LawfulBasis.CONSENT,
            consent_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365 * 2),  # 2 years
            status=ConsentStatus.GIVEN if consent_given else ConsentStatus.WITHDRAWN,
            consent_text=self._get_consent_text(purpose),
            version="1.0",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.consent_records[consent.consent_id] = consent
        subject.consents[purpose.value] = consent
        
        logger.info(f"Recorded consent: {consent.consent_id} - {consent.status.value}")
        return consent
        
    def _get_consent_text(self, purpose: ProcessingPurpose) -> str:
        """Get consent text for processing purpose"""
        consent_texts = {
            ProcessingPurpose.MARKETING: "I consent to receiving marketing communications",
            ProcessingPurpose.ANALYTICS: "I consent to analytics and performance tracking",
            ProcessingPurpose.CUSTOMER_SUPPORT: "I consent to customer support data processing"
        }
        return consent_texts.get(purpose, f"I consent to data processing for {purpose.value}")
        
    async def submit_data_subject_request(self, subject_id: str, request_type: DataSubjectRight,
                                         description: str) -> DataSubjectRequest:
        """Submit a data subject request"""
        if subject_id not in self.data_subjects:
            raise ValueError(f"Data subject not found: {subject_id}")
        
        subject = self.data_subjects[subject_id]
        
        if not subject.is_eu_resident:
            raise ValueError("GDPR rights only apply to EU residents")
        
        request = DataSubjectRequest(
            request_id=f"req_{subject_id}_{datetime.now().timestamp()}",
            subject_id=subject_id,
            request_type=request_type,
            request_date=datetime.now(),
            description=description,
            status=RequestStatus.PENDING,
            due_date=datetime.now() + timedelta(days=self.RESPONSE_PERIOD_DAYS)
        )
        
        self.data_subject_requests[request.request_id] = request
        subject.requests.append(request)
        
        logger.info(f"Submitted data subject request: {request.request_id}")
        
        # Auto-process certain types of requests
        if request_type == DataSubjectRight.ACCESS:
            await self.request_processor.process_access_request(request, subject)
        
        return request
        
    async def process_data_subject_request(self, request_id: str) -> Dict[str, Any]:
        """Process a data subject request"""
        if request_id not in self.data_subject_requests:
            raise ValueError(f"Request not found: {request_id}")
        
        request = self.data_subject_requests[request_id]
        subject = self.data_subjects[request.subject_id]
        
        request.status = RequestStatus.IN_PROGRESS
        
        try:
            if request.request_type == DataSubjectRight.ACCESS:
                response = await self.request_processor.process_access_request(request, subject)
            elif request.request_type == DataSubjectRight.RECTIFICATION:
                response = await self.request_processor.process_rectification_request(request, subject)
            elif request.request_type == DataSubjectRight.ERASURE:
                response = await self.request_processor.process_erasure_request(request, subject)
            elif request.request_type == DataSubjectRight.PORTABILITY:
                response = await self.request_processor.process_portability_request(request, subject)
            else:
                response = {"status": "manual_review_required"}
            
            request.status = RequestStatus.COMPLETED
            request.response_date = datetime.now()
            request.response_data = response
            
        except Exception as e:
            request.status = RequestStatus.REJECTED
            request.rejection_reason = str(e)
            response = {"error": str(e)}
        
        logger.info(f"Processed data subject request: {request_id} - {request.status.value}")
        return response
        
    async def report_data_breach(self, breach_type: str, affected_subjects: List[str],
                                data_categories: List[str], description: str) -> DataBreach:
        """Report a data breach"""
        # Assess severity
        severity = self._assess_breach_severity(len(affected_subjects), data_categories)
        
        breach = DataBreach(
            breach_id=f"breach_{datetime.now().timestamp()}",
            discovery_date=datetime.now(),
            breach_type=breach_type,
            affected_subjects_count=len(affected_subjects),
            data_categories_affected=data_categories,
            severity=severity,
            description=description,
            containment_measures=[],
            impact_assessment="",
            notification_required=severity in [BreachSeverity.HIGH, BreachSeverity.CRITICAL]
        )
        
        self.data_breaches.append(breach)
        
        # Auto-notify if required
        if breach.notification_required:
            await self.breach_manager.notify_authorities(breach)
            
            # Notify subjects if high risk
            if severity == BreachSeverity.CRITICAL:
                await self.breach_manager.notify_subjects(breach, affected_subjects)
        
        logger.warning(f"Data breach reported: {breach.breach_id} - {severity.value}")
        return breach
        
    def _assess_breach_severity(self, affected_count: int, data_categories: List[str]) -> BreachSeverity:
        """Assess breach severity"""
        sensitive_categories = {"financial", "trading", "identity", "authentication"}
        
        has_sensitive_data = any(cat.lower() in sensitive_categories for cat in data_categories)
        
        if affected_count > 1000 and has_sensitive_data:
            return BreachSeverity.CRITICAL
        elif affected_count > 100 and has_sensitive_data:
            return BreachSeverity.HIGH
        elif affected_count > 10 or has_sensitive_data:
            return BreachSeverity.MEDIUM
        else:
            return BreachSeverity.LOW
            
    async def get_gdpr_compliance_summary(self) -> Dict[str, Any]:
        """Get GDPR compliance summary"""
        total_subjects = len(self.data_subjects)
        eu_subjects = len([s for s in self.data_subjects.values() if s.is_eu_resident])
        
        pending_requests = len([r for r in self.data_subject_requests.values() 
                               if r.status == RequestStatus.PENDING])
        overdue_requests = len([r for r in self.data_subject_requests.values()
                               if r.status == RequestStatus.PENDING and r.due_date < datetime.now()])
        
        active_consents = len([c for c in self.consent_records.values()
                              if c.status == ConsentStatus.GIVEN])
        
        breach_count = len(self.data_breaches)
        critical_breaches = len([b for b in self.data_breaches
                                if b.severity == BreachSeverity.CRITICAL])
        
        return {
            'total_data_subjects': total_subjects,
            'eu_data_subjects': eu_subjects,
            'pending_requests': pending_requests,
            'overdue_requests': overdue_requests,
            'active_consents': active_consents,
            'data_breaches': breach_count,
            'critical_breaches': critical_breaches,
            'processing_records': len(self.processing_records),
            'cross_border_transfers': len(self.cross_border_transfers),
            'compliance_status': 'compliant' if overdue_requests == 0 and critical_breaches == 0 else 'issues'
        }


class ConsentManager:
    """Manages consent records and validation"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize consent manager"""
        logger.info("Initialized consent manager")
        
    async def validate_consent(self, subject_id: str, purpose: ProcessingPurpose) -> bool:
        """Validate if consent exists for processing purpose"""
        # This would check consent records and validate they're still valid
        return True  # Simplified for demo
        
    async def expire_consents(self):
        """Expire old consents"""
        # This would run periodically to expire old consents
        pass


class RequestProcessor:
    """Processes data subject requests"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize request processor"""
        logger.info("Initialized request processor")
        
    async def process_access_request(self, request: DataSubjectRequest, 
                                   subject: DataSubject) -> Dict[str, Any]:
        """Process data access request"""
        # Gather all personal data for the subject
        personal_data = {
            'basic_info': {
                'email': subject.email,
                'country': subject.country,
                'registration_date': subject.registration_date.isoformat(),
                'account_status': subject.account_status
            },
            'consents': [
                {
                    'purpose': consent.purpose.value,
                    'status': consent.status.value,
                    'date': consent.consent_date.isoformat()
                }
                for consent in subject.consents.values()
            ],
            'requests': [
                {
                    'type': req.request_type.value,
                    'date': req.request_date.isoformat(),
                    'status': req.status.value
                }
                for req in subject.requests
            ]
        }
        
        return {
            'request_type': 'access',
            'data': personal_data,
            'export_format': 'json'
        }
        
    async def process_rectification_request(self, request: DataSubjectRequest,
                                          subject: DataSubject) -> Dict[str, Any]:
        """Process data rectification request"""
        return {
            'request_type': 'rectification',
            'status': 'manual_review_required',
            'message': 'Rectification request requires manual review'
        }
        
    async def process_erasure_request(self, request: DataSubjectRequest,
                                    subject: DataSubject) -> Dict[str, Any]:
        """Process data erasure request"""
        return {
            'request_type': 'erasure',
            'status': 'manual_review_required',
            'message': 'Erasure request requires legal and regulatory review'
        }
        
    async def process_portability_request(self, request: DataSubjectRequest,
                                        subject: DataSubject) -> Dict[str, Any]:
        """Process data portability request"""
        # Export data in machine-readable format
        portable_data = {
            'account_data': {
                'email': subject.email,
                'registration_date': subject.registration_date.isoformat()
            },
            'trading_data': {
                # Would include trading history in structured format
                'note': 'Trading data export would be included here'
            }
        }
        
        return {
            'request_type': 'portability',
            'data': portable_data,
            'format': 'json'
        }


class BreachManager:
    """Manages data breach notifications"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize breach manager"""
        logger.info("Initialized breach manager")
        
    async def notify_authorities(self, breach: DataBreach):
        """Notify supervisory authorities of breach"""
        # In real implementation, this would send notifications to relevant authorities
        breach.authority_notified = True
        breach.authority_notification_date = datetime.now()
        
        logger.warning(f"Notified authorities of breach: {breach.breach_id}")
        
    async def notify_subjects(self, breach: DataBreach, affected_subjects: List[str]):
        """Notify affected data subjects of breach"""
        # In real implementation, this would send notifications to affected subjects
        breach.subjects_notified = True
        breach.subjects_notification_date = datetime.now()
        
        logger.warning(f"Notified {len(affected_subjects)} subjects of breach: {breach.breach_id}")


class PrivacyImpactAssessor:
    """Conducts privacy impact assessments"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize privacy impact assessor"""
        logger.info("Initialized privacy impact assessor")
        
    async def conduct_pia(self, processing_purpose: str, data_categories: List[str]) -> Dict[str, Any]:
        """Conduct privacy impact assessment"""
        # This would conduct a full PIA for new processing activities
        return {
            'pia_required': True,
            'risk_level': 'medium',
            'recommendations': [
                'Implement additional encryption',
                'Conduct regular access reviews',
                'Provide staff training'
            ]
        }