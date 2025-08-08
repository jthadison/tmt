"""Test configuration and fixtures."""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, LegalEntity, EntityType, EntityStatus
from app.entity_manager import EntityManager
from app.audit_service import AuditService
from app.tos_manager import ToSManager
from app.geographic_service import GeographicService
from app.compliance_reporter import ComplianceReporter


@pytest.fixture
def test_db():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def entity_manager(test_db):
    """Create entity manager with test database."""
    return EntityManager(test_db)


@pytest.fixture
def audit_service(test_db):
    """Create audit service with test database."""
    return AuditService(test_db)


@pytest.fixture
def tos_manager(test_db, audit_service):
    """Create ToS manager with test database."""
    return ToSManager(test_db, audit_service)


@pytest.fixture
def geographic_service(test_db):
    """Create geographic service with test database."""
    return GeographicService(test_db)


@pytest.fixture
def compliance_reporter(test_db, entity_manager, audit_service, tos_manager, geographic_service):
    """Create compliance reporter with test database."""
    return ComplianceReporter(
        test_db, entity_manager, audit_service, 
        tos_manager, geographic_service
    )


@pytest.fixture
def sample_entity(test_db):
    """Create a sample legal entity."""
    entity = LegalEntity(
        entity_id=uuid4(),
        entity_name="Test Trading LLC",
        entity_type=EntityType.LLC.value,
        jurisdiction="US",
        registration_number="REG-20250101-1234",
        tax_id="12-3456789",
        registered_address="123 Trading St, New York, NY 10001",
        incorporation_date=datetime(2024, 1, 1),
        status=EntityStatus.ACTIVE.value,
        metadata={
            "personality_profile": "moderate",
            "risk_tolerance": 0.5,
            "decision_speed": 15
        }
    )
    test_db.add(entity)
    test_db.commit()
    return entity


@pytest.fixture
def multiple_entities(test_db):
    """Create multiple test entities."""
    entities = []
    personalities = ["conservative", "aggressive", "systematic"]
    
    for i, personality in enumerate(personalities):
        entity = LegalEntity(
            entity_id=uuid4(),
            entity_name=f"Test Entity {i+1}",
            entity_type=EntityType.LLC.value,
            jurisdiction="US",
            registration_number=f"REG-20250101-{1000+i}",
            registered_address=f"{100+i} Main St, City, ST",
            incorporation_date=datetime(2024, 1, 1),
            status=EntityStatus.ACTIVE.value,
            metadata={
                "personality_profile": personality,
                "risk_tolerance": 0.3 + (i * 0.2),
                "decision_speed": 10 + (i * 5)
            }
        )
        test_db.add(entity)
        entities.append(entity)
    
    test_db.commit()
    return entities