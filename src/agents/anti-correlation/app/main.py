"""Anti-Correlation Engine - Main FastAPI Application."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from .models import (
    Base, CorrelationRequest, CorrelationMatrixResponse,
    AdjustmentRequest, AlertResponse, DailyCorrelationReport,
    DelayCalculationRequest, DelayResponse,
    SizeVarianceRequest, SizeVarianceResponse
)
from .correlation_monitor import CorrelationMonitor
from .alert_manager import AlertManager
from .position_adjuster import PositionAdjuster
from .execution_delay import ExecutionDelayManager
from .size_variance import SizeVarianceManager
from .correlation_reporter import CorrelationReporter

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

# Global services
services = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Anti-Correlation Engine starting up...")
    
    # Initialize services
    db_session = SessionLocal()
    
    services["correlation_monitor"] = CorrelationMonitor(db_session)
    services["alert_manager"] = AlertManager(db_session)
    services["position_adjuster"] = PositionAdjuster(db_session)
    services["execution_delay"] = ExecutionDelayManager(db_session)
    services["size_variance"] = SizeVarianceManager(db_session)
    services["correlation_reporter"] = CorrelationReporter(
        db_session,
        services["correlation_monitor"],
        services["alert_manager"]
    )
    
    # Start background tasks
    asyncio.create_task(services["alert_manager"].auto_escalation_monitor())
    
    yield
    
    logger.info("Anti-Correlation Engine shutting down...")
    db_session.close()


# Create FastAPI app
app = FastAPI(
    title="Anti-Correlation Engine",
    description="Prevents suspicious correlation between trading accounts through real-time monitoring and automatic adjustments",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
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


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "anti-correlation-engine",
        "timestamp": datetime.utcnow().isoformat()
    }


# Correlation Monitoring Endpoints

@app.post("/api/v1/correlation/calculate")
async def calculate_correlation(
    request: CorrelationRequest
) -> Dict[str, Any]:
    """Calculate correlation between specific accounts."""
    if len(request.account_ids) != 2:
        raise HTTPException(status_code=400, detail="Exactly 2 account IDs required")
    
    correlation_monitor = services["correlation_monitor"]
    
    correlation, p_value, components = await correlation_monitor.calculate_correlation(
        request.account_ids[0],
        request.account_ids[1],
        request.time_window,
        request.include_components
    )
    
    return {
        "account_1_id": str(request.account_ids[0]),
        "account_2_id": str(request.account_ids[1]),
        "correlation_coefficient": correlation,
        "p_value": p_value,
        "time_window": request.time_window,
        "components": components,
        "calculation_time": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/correlation/matrix")
async def get_correlation_matrix(
    account_ids: List[UUID],
    time_window: int = Query(3600, ge=300, le=86400)
) -> CorrelationMatrixResponse:
    """Get correlation matrix for multiple accounts."""
    if len(account_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 account IDs required")
    
    correlation_monitor = services["correlation_monitor"]
    
    matrix_result = await correlation_monitor.update_correlation_matrix(
        account_ids, time_window
    )
    
    return matrix_result


@app.get("/api/v1/correlation/history/{account1_id}/{account2_id}")
async def get_correlation_history(
    account1_id: UUID,
    account2_id: UUID,
    hours: int = Query(24, ge=1, le=168)
) -> List[Dict[str, Any]]:
    """Get correlation history between two accounts."""
    correlation_monitor = services["correlation_monitor"]
    
    history = await correlation_monitor.get_correlation_history(
        account1_id, account2_id, hours
    )
    
    return history


@app.get("/api/v1/correlation/high-pairs")
async def get_high_correlation_pairs(
    threshold: float = Query(0.7, ge=0.0, le=1.0),
    time_window: int = Query(3600, ge=300, le=86400)
) -> List[Dict[str, Any]]:
    """Get account pairs with high correlation."""
    correlation_monitor = services["correlation_monitor"]
    
    high_pairs = await correlation_monitor.get_high_correlation_pairs(
        threshold, time_window
    )
    
    return high_pairs


# Alert Management Endpoints

@app.get("/api/v1/alerts/active")
async def get_active_alerts(
    severity: Optional[str] = Query(None),
    account_id: Optional[UUID] = Query(None)
) -> List[AlertResponse]:
    """Get currently active correlation alerts."""
    alert_manager = services["alert_manager"]
    
    severity_filter = None
    if severity:
        try:
            from .models import CorrelationSeverity
            severity_filter = CorrelationSeverity(severity)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid severity level")
    
    alerts = await alert_manager.get_active_alerts(severity_filter, account_id)
    return alerts


@app.post("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: UUID,
    resolution_action: str,
    correlation_after: Optional[float] = None
) -> Dict[str, str]:
    """Resolve a correlation alert."""
    alert_manager = services["alert_manager"]
    
    success = await alert_manager.resolve_alert(
        alert_id, resolution_action, correlation_after
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found or already resolved")
    
    return {"message": "Alert resolved successfully"}


@app.get("/api/v1/alerts/history")
async def get_alert_history(
    hours: int = Query(24, ge=1, le=168),
    include_resolved: bool = Query(True)
) -> List[AlertResponse]:
    """Get alert history."""
    alert_manager = services["alert_manager"]
    
    history = await alert_manager.get_alert_history(hours, include_resolved)
    return history


@app.get("/api/v1/alerts/heatmap")
async def get_correlation_heatmap(
    account_ids: List[UUID],
    time_window: int = Query(3600, ge=300, le=86400)
) -> Dict[str, Any]:
    """Get correlation heatmap data."""
    alert_manager = services["alert_manager"]
    
    heatmap_data = await alert_manager.generate_correlation_heatmap_data(
        account_ids, time_window
    )
    
    return heatmap_data


@app.get("/api/v1/alerts/statistics")
async def get_alert_statistics(
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get alert statistics."""
    alert_manager = services["alert_manager"]
    
    stats = await alert_manager.get_alert_statistics(days)
    return stats


# Position Adjustment Endpoints

@app.post("/api/v1/adjustments/auto-adjust")
async def auto_adjust_positions(
    account1_id: UUID,
    account2_id: UUID,
    current_correlation: float,
    target_correlation: float = 0.5,
    strategy: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Automatically adjust positions to reduce correlation."""
    position_adjuster = services["position_adjuster"]
    
    from .position_adjuster import AdjustmentStrategy
    strategy_enum = None
    if strategy:
        try:
            strategy_enum = AdjustmentStrategy(strategy)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid adjustment strategy")
    
    adjustments = await position_adjuster.adjust_positions_for_correlation(
        account1_id, account2_id, current_correlation, target_correlation, strategy_enum
    )
    
    return adjustments


@app.post("/api/v1/adjustments/manual")
async def manual_adjustment(
    request: AdjustmentRequest
) -> Dict[str, Any]:
    """Execute manual position adjustment."""
    position_adjuster = services["position_adjuster"]
    
    result = await position_adjuster.manual_adjustment(request)
    return result


@app.get("/api/v1/adjustments/suggestions")
async def get_adjustment_suggestions(
    account1_id: UUID,
    account2_id: UUID,
    current_correlation: float,
    target_correlation: float = 0.5
) -> List[Dict[str, Any]]:
    """Get suggested adjustments without executing them."""
    position_adjuster = services["position_adjuster"]
    
    suggestions = await position_adjuster.get_adjustment_suggestions(
        account1_id, account2_id, current_correlation, target_correlation
    )
    
    return suggestions


# Execution Timing Endpoints

@app.post("/api/v1/execution/calculate-delay")
async def calculate_execution_delay(
    request: DelayCalculationRequest
) -> DelayResponse:
    """Calculate execution delay for a trade signal."""
    execution_delay = services["execution_delay"]
    
    response = await execution_delay.calculate_execution_delay(request)
    return response


@app.post("/api/v1/execution/bulk-delays")
async def calculate_bulk_delays(
    requests: List[DelayCalculationRequest]
) -> List[DelayResponse]:
    """Calculate delays for multiple accounts with anti-correlation logic."""
    execution_delay = services["execution_delay"]
    
    responses = await execution_delay.bulk_calculate_delays(requests)
    return responses


@app.get("/api/v1/execution/delay-statistics")
async def get_delay_statistics(
    account_id: Optional[UUID] = Query(None),
    hours: int = Query(24, ge=1, le=168)
) -> Dict[str, Any]:
    """Get execution delay statistics."""
    execution_delay = services["execution_delay"]
    
    stats = await execution_delay.get_delay_statistics(account_id, hours)
    return stats


@app.get("/api/v1/execution/pattern-detection")
async def detect_delay_patterns(
    account_ids: List[UUID],
    hours: int = Query(24, ge=1, le=168)
) -> Dict[str, Any]:
    """Detect potentially suspicious delay patterns."""
    execution_delay = services["execution_delay"]
    
    patterns = await execution_delay.detect_delay_patterns(account_ids, hours)
    return patterns


# Size Variance Endpoints

@app.post("/api/v1/size/calculate-variance")
async def calculate_size_variance(
    request: SizeVarianceRequest
) -> SizeVarianceResponse:
    """Calculate position size variance."""
    size_variance = services["size_variance"]
    
    response = await size_variance.calculate_size_variance(request)
    return response


@app.post("/api/v1/size/bulk-variances")
async def calculate_bulk_variances(
    requests: List[SizeVarianceRequest],
    ensure_diversity: bool = Query(True)
) -> List[SizeVarianceResponse]:
    """Calculate size variances for multiple accounts."""
    size_variance = services["size_variance"]
    
    responses = await size_variance.bulk_calculate_variances(
        requests, ensure_diversity
    )
    return responses


@app.get("/api/v1/size/statistics")
async def get_variance_statistics(
    account_id: Optional[UUID] = Query(None),
    symbol: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get size variance statistics."""
    size_variance = services["size_variance"]
    
    stats = await size_variance.get_variance_statistics(
        account_id, symbol, days
    )
    return stats


@app.post("/api/v1/size/optimize-profiles")
async def optimize_variance_profiles(
    account_ids: List[UUID]
) -> Dict[str, Any]:
    """Optimize variance profiles for accounts."""
    size_variance = services["size_variance"]
    
    results = await size_variance.optimize_variance_profiles(account_ids)
    return results


@app.get("/api/v1/size/pattern-detection")
async def detect_size_patterns(
    account_ids: List[UUID],
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Detect suspicious size patterns across accounts."""
    size_variance = services["size_variance"]
    
    patterns = await size_variance.detect_size_patterns(account_ids, days)
    return patterns


# Reporting Endpoints

@app.post("/api/v1/reports/daily")
async def generate_daily_report(
    report_date: datetime,
    account_ids: List[UUID],
    report_type: str = Query("detailed")
) -> DailyCorrelationReport:
    """Generate daily correlation report."""
    correlation_reporter = services["correlation_reporter"]
    
    report = await correlation_reporter.generate_daily_report(
        report_date, account_ids, report_type
    )
    return report


@app.get("/api/v1/reports/weekly")
async def generate_weekly_summary(
    week_start: datetime,
    account_ids: List[UUID]
) -> Dict[str, Any]:
    """Generate weekly correlation summary."""
    correlation_reporter = services["correlation_reporter"]
    
    summary = await correlation_reporter.generate_weekly_summary(
        week_start, account_ids
    )
    return summary


@app.get("/api/v1/reports/compliance")
async def generate_compliance_report(
    month_start: datetime,
    account_ids: List[UUID]
) -> Dict[str, Any]:
    """Generate monthly compliance report."""
    correlation_reporter = services["correlation_reporter"]
    
    report = await correlation_reporter.generate_compliance_report(
        month_start, account_ids
    )
    return report


@app.post("/api/v1/reports/export/csv")
async def export_report_csv(
    report_date: datetime,
    account_ids: List[UUID]
) -> Dict[str, str]:
    """Export daily report to CSV format."""
    correlation_reporter = services["correlation_reporter"]
    
    # Generate report first
    report = await correlation_reporter.generate_daily_report(
        report_date, account_ids, "detailed"
    )
    
    # Export to CSV
    csv_content = await correlation_reporter.export_report_csv(report)
    
    return {
        "content": csv_content,
        "filename": f"correlation_report_{report_date.date()}.csv",
        "content_type": "text/csv"
    }


@app.post("/api/v1/reports/export/json")
async def export_report_json(
    report_date: datetime,
    account_ids: List[UUID]
) -> Dict[str, str]:
    """Export daily report to JSON format."""
    correlation_reporter = services["correlation_reporter"]
    
    # Generate report first
    report = await correlation_reporter.generate_daily_report(
        report_date, account_ids, "detailed"
    )
    
    # Export to JSON
    json_content = await correlation_reporter.export_report_json(report)
    
    return {
        "content": json_content,
        "filename": f"correlation_report_{report_date.date()}.json",
        "content_type": "application/json"
    }


# Background Task Endpoints

@app.post("/api/v1/monitoring/start")
async def start_monitoring(
    account_ids: List[UUID],
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """Start real-time correlation monitoring."""
    correlation_monitor = services["correlation_monitor"]
    position_adjuster = services["position_adjuster"]
    
    # Start monitoring tasks
    background_tasks.add_task(
        correlation_monitor.monitor_real_time, account_ids
    )
    
    # Start automatic adjustment monitoring
    account_pairs = [(account_ids[i], account_ids[j]) 
                    for i in range(len(account_ids)) 
                    for j in range(i+1, len(account_ids))]
    
    background_tasks.add_task(
        position_adjuster.monitor_and_adjust, account_pairs
    )
    
    return {"message": f"Started monitoring for {len(account_ids)} accounts"}


@app.post("/api/v1/reports/schedule-daily")
async def schedule_daily_reports(
    account_ids: List[UUID],
    background_tasks: BackgroundTasks,
    report_time: str = Query("06:00")
) -> Dict[str, str]:
    """Schedule automatic daily report generation."""
    correlation_reporter = services["correlation_reporter"]
    
    background_tasks.add_task(
        correlation_reporter.schedule_daily_reports, account_ids, report_time
    )
    
    return {"message": f"Scheduled daily reports at {report_time} UTC"}


# WebSocket endpoint for real-time updates
from fastapi import WebSocket

@app.websocket("/ws/correlation-monitor")
async def correlation_websocket(websocket: WebSocket):
    """WebSocket for real-time correlation updates."""
    await websocket.accept()
    
    try:
        while True:
            # Send correlation updates every 30 seconds
            correlation_monitor = services["correlation_monitor"]
            
            # Get current correlation matrix (would be more sophisticated in production)
            update_data = {
                "type": "correlation_update",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "message": "Real-time correlation monitoring active",
                    "last_update": correlation_monitor.last_update.isoformat()
                }
            }
            
            await websocket.send_json(update_data)
            await asyncio.sleep(30)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005, reload=True)