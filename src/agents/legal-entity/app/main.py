"""Legal Entity Separation Agent - Main FastAPI Application."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from .models import (
    Base, LegalEntityCreate, LegalEntityResponse,
    ToSAcceptanceRequest, DecisionLogEntry, AuditLogEntry,
    ComplianceReport, EntityComplianceStatus,
    GeographicRestrictionConfig, EntityStatus
)
from .entity_manager import EntityManager
from .audit_service import AuditService
from .tos_manager import ToSManager
from .geographic_service import GeographicService
from .compliance_reporter import ComplianceReporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql://trading_user:trading_pass@localhost:5432/trading_system"

# Create database engine
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Legal Entity Agent starting up...")
    yield
    logger.info("Legal Entity Agent shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Legal Entity Separation Agent",
    description="Manages legal entity separation and compliance for multi-account trading",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get database session
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependency to get services
def get_entity_manager(db: Session = Depends(get_db)) -> EntityManager:
    """Get entity manager service."""
    return EntityManager(db)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Get audit service."""
    return AuditService(db)


def get_tos_manager(
    db: Session = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service)
) -> ToSManager:
    """Get ToS manager service."""
    return ToSManager(db, audit_service)


def get_geographic_service(db: Session = Depends(get_db)) -> GeographicService:
    """Get geographic service."""
    return GeographicService(db)


def get_compliance_reporter(
    db: Session = Depends(get_db),
    entity_manager: EntityManager = Depends(get_entity_manager),
    audit_service: AuditService = Depends(get_audit_service),
    tos_manager: ToSManager = Depends(get_tos_manager),
    geographic_service: GeographicService = Depends(get_geographic_service)
) -> ComplianceReporter:
    """Get compliance reporter service."""
    return ComplianceReporter(db, entity_manager, audit_service, tos_manager, geographic_service)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "legal-entity-agent",
        "timestamp": datetime.utcnow().isoformat()
    }


# Entity management endpoints
@app.post("/api/v1/entities", response_model=LegalEntityResponse)
async def create_entity(
    entity_data: LegalEntityCreate,
    entity_manager: EntityManager = Depends(get_entity_manager)
):
    """Create a new legal entity."""
    try:
        entity = await entity_manager.create_entity(entity_data)
        logger.info(f"Created entity: {entity.entity_id}")
        return entity
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating entity: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/entities", response_model=List[LegalEntityResponse])
async def list_entities(
    status: Optional[EntityStatus] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    entity_manager: EntityManager = Depends(get_entity_manager)
):
    """List all legal entities with optional filters."""
    try:
        entities = await entity_manager.list_entities(status, jurisdiction)
        return entities
    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/entities/{entity_id}", response_model=LegalEntityResponse)
async def get_entity(
    entity_id: UUID,
    entity_manager: EntityManager = Depends(get_entity_manager)
):
    """Get a specific legal entity."""
    entity = await entity_manager.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@app.put("/api/v1/entities/{entity_id}/status")
async def update_entity_status(
    entity_id: UUID,
    status: EntityStatus,
    reason: str = Query(..., description="Reason for status change"),
    entity_manager: EntityManager = Depends(get_entity_manager)
):
    """Update entity status."""
    success = await entity_manager.update_entity_status(entity_id, status, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"message": "Status updated successfully"}


@app.get("/api/v1/entities/{entity_id}/compliance", response_model=EntityComplianceStatus)
async def check_entity_compliance(
    entity_id: UUID,
    entity_manager: EntityManager = Depends(get_entity_manager)
):
    """Check compliance status for an entity."""
    try:
        compliance = await entity_manager.check_entity_compliance(entity_id)
        return compliance
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Decision independence endpoints
@app.post("/api/v1/entities/{entity_id}/decisions")
async def ensure_decision_independence(
    entity_id: UUID,
    decision_type: str,
    base_decision: Dict[str, Any],
    entity_manager: EntityManager = Depends(get_entity_manager)
):
    """Ensure decision independence for an entity."""
    try:
        independent_decision = await entity_manager.ensure_entity_independence(
            entity_id, decision_type, base_decision
        )
        return independent_decision
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ToS management endpoints
@app.post("/api/v1/entities/{entity_id}/tos-accept")
async def accept_terms_of_service(
    entity_id: UUID,
    request: Request,
    version: str = Query(...),
    user_agent: Optional[str] = Query(None),
    device_fingerprint: Optional[str] = Query(None),
    tos_manager: ToSManager = Depends(get_tos_manager)
):
    """Record Terms of Service acceptance."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    acceptance_request = ToSAcceptanceRequest(
        entity_id=entity_id,
        version=version,
        ip_address=client_ip,
        user_agent=user_agent or request.headers.get("User-Agent"),
        device_fingerprint=device_fingerprint
    )
    
    try:
        result = await tos_manager.record_acceptance(acceptance_request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/entities/{entity_id}/tos-compliance")
async def check_tos_compliance(
    entity_id: UUID,
    tos_manager: ToSManager = Depends(get_tos_manager)
):
    """Check ToS compliance for an entity."""
    try:
        compliance = await tos_manager.check_compliance(entity_id)
        return compliance
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/entities/{entity_id}/tos-history")
async def get_tos_history(
    entity_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    tos_manager: ToSManager = Depends(get_tos_manager)
):
    """Get ToS acceptance history for an entity."""
    history = await tos_manager.get_acceptance_history(entity_id, limit)
    return history


# Geographic restriction endpoints
@app.post("/api/v1/entities/{entity_id}/check-access")
async def check_jurisdiction_access(
    entity_id: UUID,
    request: Request,
    geographic_service: GeographicService = Depends(get_geographic_service)
):
    """Check if access is allowed from current location."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    try:
        access_result = await geographic_service.check_jurisdiction_access(
            entity_id, client_ip
        )
        return access_result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/entities/{entity_id}/trading-hours")
async def check_trading_hours(
    entity_id: UUID,
    check_time: Optional[datetime] = Query(None),
    geographic_service: GeographicService = Depends(get_geographic_service)
):
    """Check if trading is allowed at specified time."""
    try:
        result = await geographic_service.check_trading_hours(
            entity_id, check_time
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/entities/{entity_id}/restrictions")
async def get_entity_restrictions(
    entity_id: UUID,
    geographic_service: GeographicService = Depends(get_geographic_service)
):
    """Get all restrictions for an entity."""
    try:
        restrictions = await geographic_service.get_entity_restrictions(entity_id)
        return restrictions
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Audit trail endpoints
@app.get("/api/v1/entities/{entity_id}/audit-trail")
async def get_audit_trail(
    entity_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Get audit trail for an entity."""
    logs = await audit_service.get_audit_trail(
        entity_id, None, start_date, end_date, limit
    )
    return logs


@app.get("/api/v1/entities/{entity_id}/audit-integrity")
async def verify_audit_integrity(
    entity_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Verify audit trail integrity."""
    result = await audit_service.verify_audit_trail_integrity(
        entity_id, start_date, end_date
    )
    return result


@app.get("/api/v1/entities/{entity_id}/audit-summary")
async def get_audit_summary(
    entity_id: UUID,
    period_days: int = Query(30, ge=1, le=365),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Get audit summary for an entity."""
    summary = await audit_service.generate_audit_summary(entity_id, period_days)
    return summary


# Compliance reporting endpoints
@app.get("/api/v1/reports/entity-separation")
async def generate_entity_separation_report(
    period_days: int = Query(30, ge=1, le=365),
    entity_ids: Optional[List[UUID]] = Query(None),
    compliance_reporter: ComplianceReporter = Depends(get_compliance_reporter)
):
    """Generate entity separation compliance report."""
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=period_days)
    
    report = await compliance_reporter.generate_entity_separation_report(
        period_start, period_end, entity_ids
    )
    
    return report.dict()


@app.post("/api/v1/geographic/restrictions")
async def create_geographic_restriction(
    config: GeographicRestrictionConfig,
    geographic_service: GeographicService = Depends(get_geographic_service)
):
    """Create or update a geographic restriction."""
    restriction = await geographic_service.create_restriction(config)
    return {
        "restriction_id": str(restriction.restriction_id),
        "jurisdiction": restriction.jurisdiction,
        "restriction_level": restriction.restriction_level,
        "message": "Restriction created/updated successfully"
    }


@app.post("/api/v1/compliance/multi-jurisdiction-check")
async def check_multi_jurisdiction_compliance(
    entity_ids: List[UUID],
    geographic_service: GeographicService = Depends(get_geographic_service)
):
    """Check compliance across multiple jurisdictions."""
    result = await geographic_service.validate_multi_jurisdiction_compliance(
        entity_ids
    )
    return result


# WebSocket endpoint for real-time compliance monitoring
from fastapi import WebSocket
import asyncio

@app.websocket("/ws/compliance-monitor")
async def compliance_monitor(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """WebSocket for real-time compliance monitoring."""
    await websocket.accept()
    
    try:
        while True:
            # Send compliance updates every 10 seconds
            entity_manager = EntityManager(db)
            entities = await entity_manager.list_entities()
            
            compliance_statuses = []
            for entity in entities:
                try:
                    status = await entity_manager.check_entity_compliance(
                        entity.entity_id
                    )
                    compliance_statuses.append(status.dict())
                except:
                    pass
            
            await websocket.send_json({
                "type": "compliance_update",
                "timestamp": datetime.utcnow().isoformat(),
                "entities": compliance_statuses
            })
            
            await asyncio.sleep(10)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, reload=True)