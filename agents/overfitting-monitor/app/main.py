"""
Overfitting Monitor FastAPI Application - Story 11.4, Task 5

REST API endpoints for overfitting monitoring.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from .config import get_settings, Settings
from .monitor import OverfittingMonitor
from .alert_service import AlertService
from .performance_tracker import PerformanceTracker
from .scheduler import MonitoringScheduler
from .database import init_database, get_database
from .models import (
    OverfittingScore,
    OverfittingAlert,
    OverfittingHistory,
    MonitoringStatus,
    ParameterComparison,
    AlertLevel
)

# Configure logging
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
logger = structlog.get_logger()

# Global instances
monitor: Optional[OverfittingMonitor] = None
alert_service: Optional[AlertService] = None
performance_tracker: Optional[PerformanceTracker] = None
scheduler: Optional[MonitoringScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    settings = get_settings()
    logger.info("Starting Overfitting Monitor Agent", port=settings.port)

    # Initialize database
    await init_database(settings.database_url)
    logger.info("Database initialized")

    # Initialize components
    global monitor, alert_service, performance_tracker, scheduler

    monitor = OverfittingMonitor(
        baseline_parameters=settings.get_baseline_parameters(),
        warning_threshold=settings.overfitting_warning_threshold,
        critical_threshold=settings.overfitting_critical_threshold,
        max_drift_pct=settings.max_parameter_drift_pct
    )

    alert_service = AlertService(
        slack_webhook_url=settings.slack_webhook_url,
        email_enabled=settings.email_enabled,
        sendgrid_api_key=settings.sendgrid_api_key,
        alert_recipients=settings.get_alert_recipients_list()
    )
    await alert_service.initialize()

    performance_tracker = PerformanceTracker(
        rolling_window_days=settings.rolling_performance_window_days,
        degradation_threshold=settings.performance_degradation_threshold
    )

    # Initialize scheduler with dummy parameter provider
    async def get_current_params():
        # In production, this would fetch from configuration service
        # For now, return baseline parameters with slight variations
        return {
            "London": {
                "confidence_threshold": 72.0,
                "min_risk_reward": 3.2,
                "vpa_threshold": 0.65
            },
            "NY": {
                "confidence_threshold": 70.0,
                "min_risk_reward": 2.8,
                "vpa_threshold": 0.62
            },
            "Tokyo": {
                "confidence_threshold": 85.0,
                "min_risk_reward": 4.0,
                "vpa_threshold": 0.7
            }
        }

    scheduler = MonitoringScheduler(
        monitor=monitor,
        alert_service=alert_service,
        performance_tracker=performance_tracker,
        baseline_parameters=settings.get_baseline_parameters(),
        current_parameters_provider=get_current_params
    )

    # Set expected backtest metrics
    scheduler.set_expected_backtest_metrics(
        sharpe=settings.expected_backtest_sharpe,
        win_rate=settings.expected_backtest_win_rate,
        profit_factor=settings.expected_backtest_profit_factor
    )

    # Start scheduler
    if settings.enable_scheduler:
        await scheduler.start()
        logger.info("Monitoring scheduler started")

    logger.info("Overfitting Monitor Agent started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Overfitting Monitor Agent")

    if scheduler:
        await scheduler.stop()

    if alert_service:
        await alert_service.close()

    db = await get_database()
    await db.disconnect()

    logger.info("Overfitting Monitor Agent shut down")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency for correlation ID
def get_correlation_id() -> str:
    """Generate correlation ID for request tracing"""
    return str(uuid.uuid4())


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint

    @returns: Health status
    """
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.api_version,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with component status

    @returns: Detailed health status
    """
    db = await get_database()

    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.api_version,
        "components": {
            "database": "connected",
            "monitor": "active" if monitor else "inactive",
            "alert_service": "active" if alert_service else "inactive",
            "scheduler": "running" if scheduler and scheduler.running else "stopped"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# Overfitting Score Endpoints
# ============================================================================

@app.get("/api/monitoring/overfitting/current", response_model=Dict[str, Any])
async def get_current_overfitting_score(
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get current overfitting score

    @returns: Latest overfitting score data
    """
    logger.info("Fetching current overfitting score", correlation_id=correlation_id)

    db = await get_database()
    score_data = await db.get_latest_overfitting_score()

    if not score_data:
        raise HTTPException(status_code=404, detail="No overfitting scores found")

    return {
        "data": score_data,
        "correlation_id": correlation_id
    }


@app.get("/api/monitoring/overfitting/history")
async def get_overfitting_history(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to retrieve"),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get historical overfitting scores

    @param days: Number of days of history to retrieve
    @returns: Historical overfitting data
    """
    logger.info(
        "Fetching overfitting history",
        days=days,
        correlation_id=correlation_id
    )

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    db = await get_database()
    history = await db.get_overfitting_history(start_time, end_time)

    # Calculate aggregate metrics
    scores = [h['score'] for h in history]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0
    alerts_count = sum(1 for h in history if h['alert_level'] != 'normal')

    return {
        "data": {
            "start_date": start_time.isoformat(),
            "end_date": end_time.isoformat(),
            "scores": history,
            "avg_score": avg_score,
            "max_score": max_score,
            "alerts_count": alerts_count
        },
        "correlation_id": correlation_id
    }


# ============================================================================
# Performance Comparison Endpoints
# ============================================================================

@app.get("/api/monitoring/performance-comparison")
async def get_performance_comparison(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to retrieve"),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get live vs backtest performance comparison

    @param days: Number of days of history
    @returns: Performance comparison data
    """
    logger.info(
        "Fetching performance comparison",
        days=days,
        correlation_id=correlation_id
    )

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    db = await get_database()
    performance_history = await db.get_performance_history(start_time, end_time)

    # Get current performance summary
    summary = performance_tracker.get_performance_summary() if performance_tracker else {}

    return {
        "data": {
            "history": performance_history,
            "current_summary": summary
        },
        "correlation_id": correlation_id
    }


# ============================================================================
# Alert Endpoints
# ============================================================================

@app.get("/api/monitoring/alerts")
async def get_alerts(
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get active alerts

    @param severity: Optional severity filter (normal, warning, critical)
    @returns: List of active alerts
    """
    logger.info(
        "Fetching alerts",
        severity=severity,
        correlation_id=correlation_id
    )

    if not alert_service:
        raise HTTPException(status_code=503, detail="Alert service not initialized")

    # Parse severity filter
    severity_filter = None
    if severity:
        try:
            severity_filter = AlertLevel(severity.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity: {severity}. Must be normal, warning, or critical"
            )

    alerts = await alert_service.get_active_alerts(severity=severity_filter)

    return {
        "data": [alert.dict() for alert in alerts],
        "count": len(alerts),
        "correlation_id": correlation_id
    }


@app.post("/api/monitoring/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Acknowledge an alert

    @param alert_id: Alert ID to acknowledge
    @returns: Acknowledged alert
    """
    logger.info(
        "Acknowledging alert",
        alert_id=alert_id,
        correlation_id=correlation_id
    )

    if not alert_service:
        raise HTTPException(status_code=503, detail="Alert service not initialized")

    alert = await alert_service.acknowledge_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

    return {
        "data": alert.dict(),
        "correlation_id": correlation_id
    }


# ============================================================================
# Parameter Drift Endpoints
# ============================================================================

@app.get("/api/monitoring/parameter-drift/{parameter_name}")
async def get_parameter_drift(
    parameter_name: str,
    days: int = Query(default=30, ge=1, le=90, description="Number of days to retrieve"),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get parameter drift history for a specific parameter

    @param parameter_name: Parameter name
    @param days: Number of days of history
    @returns: Parameter drift data
    """
    logger.info(
        "Fetching parameter drift",
        parameter_name=parameter_name,
        days=days,
        correlation_id=correlation_id
    )

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    db = await get_database()
    drift_history = await db.get_parameter_drift_history(
        parameter_name, start_time, end_time
    )

    return {
        "data": {
            "parameter_name": parameter_name,
            "history": drift_history
        },
        "correlation_id": correlation_id
    }


# ============================================================================
# Parameter Comparison Endpoints
# ============================================================================

@app.post("/api/monitoring/compare-parameters")
async def compare_parameters(
    current_params: Dict[str, Dict[str, Any]],
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Compare current parameters against baseline

    @param current_params: Current session-specific parameters
    @returns: Parameter comparison analysis
    """
    logger.info(
        "Comparing parameters",
        correlation_id=correlation_id
    )

    if not monitor:
        raise HTTPException(status_code=503, detail="Monitor not initialized")

    comparison = monitor.compare_parameters(current_params)

    return {
        "data": comparison.dict(),
        "correlation_id": correlation_id
    }


# ============================================================================
# Monitoring Status Endpoint
# ============================================================================

@app.get("/api/monitoring/status", response_model=Dict[str, Any])
async def get_monitoring_status(
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get current monitoring system status

    @returns: Monitoring status summary
    """
    logger.info("Fetching monitoring status", correlation_id=correlation_id)

    # Get latest overfitting score
    db = await get_database()
    latest_score = await db.get_latest_overfitting_score()

    # Get active alerts
    active_alerts = await alert_service.get_active_alerts() if alert_service else []

    # Check performance degradation
    is_degraded, _ = performance_tracker.is_performance_degraded(
        settings.expected_backtest_sharpe
    ) if performance_tracker else (False, 0.0)

    status = {
        "current_overfitting_score": latest_score['score'] if latest_score else 0.0,
        "alert_level": latest_score['alert_level'] if latest_score else "normal",
        "active_alerts": len(active_alerts),
        "parameter_drift_count": 0,  # TODO: Calculate from recent drift data
        "performance_degradation_detected": is_degraded,
        "last_calculation": latest_score['time'].isoformat() if latest_score else None,
        "monitoring_healthy": scheduler.running if scheduler else False
    }

    return {
        "data": status,
        "correlation_id": correlation_id
    }


# ============================================================================
# Manual Trigger Endpoints
# ============================================================================

@app.post("/api/monitoring/trigger/calculate")
async def trigger_overfitting_calculation(
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Manually trigger overfitting score calculation

    @returns: Calculation result
    """
    logger.info("Manual overfitting calculation triggered", correlation_id=correlation_id)

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    await scheduler._calculate_overfitting_task()

    return {
        "data": {"status": "completed"},
        "message": "Overfitting calculation completed",
        "correlation_id": correlation_id
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False
    )
