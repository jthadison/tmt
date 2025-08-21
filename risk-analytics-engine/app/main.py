"""
Risk Management & Portfolio Analytics Engine - Main API Application

Comprehensive risk monitoring, portfolio analytics, and compliance reporting
with real-time risk assessment and automated alerting capabilities.
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.models import (
    RiskMetrics,
    PortfolioAnalytics,
    RiskLimits,
    AnalyticsConfig,
    RiskAlert,
    ComplianceRecord,
    ReportType,
    ReportFormat,
    StressTestScenario,
    StressTestResult
)
from .portfolio.portfolio_analyzer import PortfolioAnalyticsEngine
from .risk.risk_calculator import RiskCalculationEngine
from .analytics.pl_monitor import RealTimePLMonitor
from .alerts.alert_manager import RiskAlertManager
from .compliance.compliance_engine import ComplianceEngine, RegulationType
from .integrations.execution_client import ExecutionEngineClient
from .integrations.market_data_client import MarketDataClient

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class RiskAnalyticsState:
    """Global application state."""
    
    def __init__(self):
        # Core engines
        self.portfolio_analyzer: Optional[PortfolioAnalyticsEngine] = None
        self.risk_calculator: Optional[RiskCalculationEngine] = None
        self.pl_monitor: Optional[RealTimePLMonitor] = None
        self.alert_manager: Optional[RiskAlertManager] = None
        self.compliance_engine: Optional[ComplianceEngine] = None
        
        # Integration clients
        self.execution_client: Optional[ExecutionEngineClient] = None
        self.market_data_client: Optional[MarketDataClient] = None
        
        # Configuration
        self.risk_limits: Optional[RiskLimits] = None
        self.analytics_config: Optional[AnalyticsConfig] = None
        
        # State tracking
        self.initialized = False
        self.monitored_accounts: List[str] = []


# Global state
app_state = RiskAnalyticsState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Risk Management & Portfolio Analytics Engine")
    
    try:
        # Initialize configuration
        app_state.risk_limits = RiskLimits(
            max_position_size=Decimal(os.getenv("MAX_POSITION_SIZE", "100000")),
            max_positions_per_instrument=int(os.getenv("MAX_POSITIONS_PER_INSTRUMENT", "3")),
            max_leverage=Decimal(os.getenv("MAX_LEVERAGE", "30")),
            max_daily_loss=Decimal(os.getenv("MAX_DAILY_LOSS", "1000")),
            max_drawdown=Decimal(os.getenv("MAX_DRAWDOWN", "5000")),
            required_margin_ratio=Decimal(os.getenv("REQUIRED_MARGIN_RATIO", "0.02")),
        )
        
        app_state.analytics_config = AnalyticsConfig(
            risk_calculation_interval_ms=int(os.getenv("RISK_CALC_INTERVAL_MS", "100")),
            portfolio_update_interval_ms=int(os.getenv("PORTFOLIO_UPDATE_INTERVAL_MS", "1000")),
            var_confidence_level=float(os.getenv("VAR_CONFIDENCE_LEVEL", "0.95")),
            var_lookback_days=int(os.getenv("VAR_LOOKBACK_DAYS", "252"))
        )
        
        # Initialize core engines
        app_state.portfolio_analyzer = PortfolioAnalyticsEngine(
            risk_free_rate=float(os.getenv("RISK_FREE_RATE", "0.02"))
        )
        
        app_state.risk_calculator = RiskCalculationEngine(app_state.risk_limits)
        
        app_state.pl_monitor = RealTimePLMonitor(
            update_interval_ms=app_state.analytics_config.portfolio_update_interval_ms
        )
        
        app_state.alert_manager = RiskAlertManager()
        
        app_state.compliance_engine = ComplianceEngine(
            retention_years=app_state.analytics_config.audit_trail_retention_years
        )
        
        # Initialize integration clients
        execution_url = os.getenv("EXECUTION_ENGINE_URL", "http://localhost:8004")
        market_data_url = os.getenv("MARKET_DATA_URL", "http://localhost:8002")
        
        app_state.execution_client = ExecutionEngineClient(execution_url)
        app_state.market_data_client = MarketDataClient(market_data_url)
        
        # Connect to external services
        execution_connected = await app_state.execution_client.connect()
        market_data_connected = await app_state.market_data_client.connect()
        
        if not execution_connected:
            logger.warning("Could not connect to execution engine - running in limited mode")
        
        if not market_data_connected:
            logger.warning("Could not connect to market data service - using mock data")
        
        # Setup integration callbacks
        if execution_connected:
            app_state.execution_client.register_position_callback(
                app_state.pl_monitor.update_positions
            )
        
        if market_data_connected:
            app_state.market_data_client.register_price_callback(
                _handle_price_update
            )
        
        # Start monitoring for configured accounts
        monitored_accounts = os.getenv("MONITORED_ACCOUNTS", "").split(",")
        monitored_accounts = [acc.strip() for acc in monitored_accounts if acc.strip()]
        
        if monitored_accounts:
            app_state.monitored_accounts = monitored_accounts
            await app_state.pl_monitor.start_monitoring(monitored_accounts)
            
            if execution_connected:
                await app_state.execution_client.start_position_monitoring(monitored_accounts)
            
            logger.info(f"Started monitoring {len(monitored_accounts)} accounts")
        
        app_state.initialized = True
        logger.info("Risk Analytics Engine initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize Risk Analytics Engine", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down Risk Analytics Engine")
    
    try:
        if app_state.pl_monitor:
            await app_state.pl_monitor.stop_monitoring()
        
        if app_state.execution_client:
            await app_state.execution_client.disconnect()
        
        if app_state.market_data_client:
            await app_state.market_data_client.disconnect()
        
        logger.info("Risk Analytics Engine shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


async def _handle_price_update(instrument: str, price: Decimal):
    """Handle price updates from market data service."""
    if app_state.pl_monitor:
        app_state.pl_monitor.update_prices({instrument: price})


# Create FastAPI application
app = FastAPI(
    title="TMT Risk Management & Portfolio Analytics Engine",
    description="Comprehensive risk monitoring, portfolio analytics, and compliance reporting",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
def get_portfolio_analyzer() -> PortfolioAnalyticsEngine:
    """Get portfolio analyzer dependency."""
    if not app_state.initialized or not app_state.portfolio_analyzer:
        raise HTTPException(status_code=503, detail="Portfolio analyzer not initialized")
    return app_state.portfolio_analyzer


def get_risk_calculator() -> RiskCalculationEngine:
    """Get risk calculator dependency."""
    if not app_state.initialized or not app_state.risk_calculator:
        raise HTTPException(status_code=503, detail="Risk calculator not initialized")
    return app_state.risk_calculator


def get_pl_monitor() -> RealTimePLMonitor:
    """Get P&L monitor dependency."""
    if not app_state.initialized or not app_state.pl_monitor:
        raise HTTPException(status_code=503, detail="P&L monitor not initialized")
    return app_state.pl_monitor


def get_alert_manager() -> RiskAlertManager:
    """Get alert manager dependency."""
    if not app_state.initialized or not app_state.alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    return app_state.alert_manager


def get_compliance_engine() -> ComplianceEngine:
    """Get compliance engine dependency."""
    if not app_state.initialized or not app_state.compliance_engine:
        raise HTTPException(status_code=503, detail="Compliance engine not initialized")
    return app_state.compliance_engine


# Health Check Endpoints

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if app_state.initialized else "initializing",
        "timestamp": time.time(),
        "version": "1.0.0",
        "components": {
            "portfolio_analyzer": app_state.portfolio_analyzer is not None,
            "risk_calculator": app_state.risk_calculator is not None,
            "pl_monitor": app_state.pl_monitor is not None,
            "alert_manager": app_state.alert_manager is not None,
            "compliance_engine": app_state.compliance_engine is not None,
            "execution_client": app_state.execution_client.is_connected if app_state.execution_client else False,
            "market_data_client": app_state.market_data_client.is_connected if app_state.market_data_client else False
        }
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with performance metrics."""
    performance_metrics = {}
    
    if app_state.risk_calculator:
        performance_metrics["risk_calculator"] = app_state.risk_calculator.get_performance_metrics()
    
    if app_state.pl_monitor:
        performance_metrics["pl_monitor"] = app_state.pl_monitor.get_monitoring_performance()
    
    if app_state.alert_manager:
        performance_metrics["alert_manager"] = app_state.alert_manager.get_performance_metrics()
    
    if app_state.execution_client:
        performance_metrics["execution_client"] = app_state.execution_client.get_client_performance()
    
    if app_state.market_data_client:
        performance_metrics["market_data_client"] = app_state.market_data_client.get_client_performance()
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "monitored_accounts": len(app_state.monitored_accounts),
        "performance_metrics": performance_metrics
    }


# Risk Management Endpoints

@app.get("/api/v1/risk/{account_id}/metrics", response_model=RiskMetrics, tags=["Risk Management"])
async def get_risk_metrics(
    account_id: str,
    risk_calculator: RiskCalculationEngine = Depends(get_risk_calculator)
):
    """Get current risk metrics for an account."""
    try:
        # Get positions from execution engine
        positions = []
        account_balance = Decimal("10000")  # Default
        margin_available = Decimal("9000")  # Default
        current_prices = {}
        
        if app_state.execution_client and app_state.execution_client.is_connected:
            positions = await app_state.execution_client.get_positions(account_id)
            
            account_summary = await app_state.execution_client.get_account_summary(account_id)
            if account_summary:
                account_balance = Decimal(str(account_summary.get('balance', 10000)))
                margin_available = Decimal(str(account_summary.get('margin_available', 9000)))
        
        if app_state.market_data_client and app_state.market_data_client.is_connected:
            instruments = list(set(pos.instrument for pos in positions))
            if instruments:
                current_prices = await app_state.market_data_client.get_current_prices(instruments)
        
        # Calculate risk metrics
        risk_metrics = await risk_calculator.calculate_real_time_risk(
            account_id=account_id,
            positions=positions,
            account_balance=account_balance,
            margin_available=margin_available,
            current_prices=current_prices
        )
        
        return risk_metrics
        
    except Exception as e:
        logger.error("Failed to get risk metrics", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get risk metrics: {str(e)}")


@app.get("/api/v1/risk/{account_id}/trends", tags=["Risk Management"])
async def get_risk_trends(
    account_id: str,
    risk_calculator: RiskCalculationEngine = Depends(get_risk_calculator)
):
    """Get risk trends and patterns for an account."""
    try:
        trends = risk_calculator.get_risk_trends(account_id)
        return {
            "account_id": account_id,
            "trends": trends,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Failed to get risk trends", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get risk trends: {str(e)}")


# Portfolio Analytics Endpoints

@app.get("/api/v1/portfolio/{account_id}/analytics", response_model=PortfolioAnalytics, tags=["Portfolio Analytics"])
async def get_portfolio_analytics(
    account_id: str,
    portfolio_analyzer: PortfolioAnalyticsEngine = Depends(get_portfolio_analyzer)
):
    """Get comprehensive portfolio analytics for an account."""
    try:
        # Get positions and account data
        positions = []
        current_portfolio_value = Decimal("10000")
        cash_balance = Decimal("10000")
        
        if app_state.execution_client and app_state.execution_client.is_connected:
            positions = await app_state.execution_client.get_positions(account_id)
            
            account_summary = await app_state.execution_client.get_account_summary(account_id)
            if account_summary:
                current_portfolio_value = Decimal(str(account_summary.get('balance', 10000)))
                cash_balance = Decimal(str(account_summary.get('balance', 10000)))
        
        # Calculate portfolio analytics
        analytics = await portfolio_analyzer.calculate_portfolio_analytics(
            account_id=account_id,
            positions=positions,
            current_portfolio_value=current_portfolio_value,
            cash_balance=cash_balance
        )
        
        return analytics
        
    except Exception as e:
        logger.error("Failed to get portfolio analytics", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio analytics: {str(e)}")


@app.get("/api/v1/portfolio/{account_id}/performance", tags=["Portfolio Analytics"])
async def get_performance_summary(
    account_id: str,
    portfolio_analyzer: PortfolioAnalyticsEngine = Depends(get_portfolio_analyzer)
):
    """Get performance summary metrics for an account."""
    try:
        summary = portfolio_analyzer.get_performance_summary(account_id)
        return {
            "account_id": account_id,
            "performance_summary": summary,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Failed to get performance summary", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get performance summary: {str(e)}")


# P&L Monitoring Endpoints

@app.get("/api/v1/pl/{account_id}/current", tags=["P&L Monitoring"])
async def get_current_pl(
    account_id: str,
    pl_monitor: RealTimePLMonitor = Depends(get_pl_monitor)
):
    """Get current P&L snapshot for an account."""
    try:
        pl_snapshot = await pl_monitor.get_real_time_pl(account_id)
        
        if pl_snapshot:
            return {
                "account_id": account_id,
                "timestamp": pl_snapshot.timestamp.isoformat(),
                "total_pl": float(pl_snapshot.total_pl),
                "unrealized_pl": float(pl_snapshot.unrealized_pl),
                "realized_pl": float(pl_snapshot.realized_pl),
                "daily_pl": float(pl_snapshot.daily_pl),
                "position_count": pl_snapshot.position_count,
                "market_value": float(pl_snapshot.market_value)
            }
        else:
            raise HTTPException(status_code=404, detail="No P&L data available")
            
    except Exception as e:
        logger.error("Failed to get current P&L", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get current P&L: {str(e)}")


@app.get("/api/v1/pl/{account_id}/history", tags=["P&L Monitoring"])
async def get_pl_history(
    account_id: str,
    hours: int = Query(24, ge=1, le=168),
    pl_monitor: RealTimePLMonitor = Depends(get_pl_monitor)
):
    """Get P&L history for an account."""
    try:
        pl_history = await pl_monitor.get_pl_history(account_id, hours)
        
        return {
            "account_id": account_id,
            "period_hours": hours,
            "data_points": len(pl_history),
            "pl_history": [
                {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "total_pl": float(snapshot.total_pl),
                    "unrealized_pl": float(snapshot.unrealized_pl),
                    "daily_pl": float(snapshot.daily_pl),
                    "position_count": snapshot.position_count
                }
                for snapshot in pl_history
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get P&L history", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get P&L history: {str(e)}")


# Alert Management Endpoints

@app.get("/api/v1/alerts/active", tags=["Alert Management"])
async def get_active_alerts(
    account_id: Optional[str] = None,
    alert_manager: RiskAlertManager = Depends(get_alert_manager)
):
    """Get active alerts, optionally filtered by account."""
    try:
        alerts = alert_manager.get_active_alerts(account_id)
        
        return {
            "total_active_alerts": len(alerts),
            "alerts": [
                {
                    "alert_id": str(alert.alert_id),
                    "account_id": alert.account_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "risk_score": alert.risk_score,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "is_acknowledged": alert.acknowledged_at is not None
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get active alerts", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get active alerts: {str(e)}")


@app.post("/api/v1/alerts/{alert_id}/acknowledge", tags=["Alert Management"])
async def acknowledge_alert(
    alert_id: UUID,
    acknowledged_by: str,
    alert_manager: RiskAlertManager = Depends(get_alert_manager)
):
    """Acknowledge an alert."""
    try:
        success = alert_manager.acknowledge_alert(alert_id, acknowledged_by)
        
        if success:
            return {"status": "acknowledged", "alert_id": str(alert_id)}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
            
    except Exception as e:
        logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


# Compliance Endpoints

@app.get("/api/v1/compliance/{account_id}/summary", tags=["Compliance"])
async def get_compliance_summary(
    account_id: str,
    compliance_engine: ComplianceEngine = Depends(get_compliance_engine)
):
    """Get compliance summary for an account."""
    try:
        summary = compliance_engine.get_compliance_summary(account_id)
        return summary
        
    except Exception as e:
        logger.error("Failed to get compliance summary", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get compliance summary: {str(e)}")


@app.post("/api/v1/compliance/{account_id}/check", tags=["Compliance"])
async def perform_compliance_check(
    account_id: str,
    regulations: Optional[List[RegulationType]] = None,
    compliance_engine: ComplianceEngine = Depends(get_compliance_engine),
    risk_calculator: RiskCalculationEngine = Depends(get_risk_calculator)
):
    """Perform compliance check for an account."""
    try:
        # Get current risk metrics and positions
        positions = []
        risk_metrics = None
        
        if app_state.execution_client and app_state.execution_client.is_connected:
            positions = await app_state.execution_client.get_positions(account_id)
            
            # Get basic risk metrics
            account_balance = Decimal("10000")
            margin_available = Decimal("9000")
            current_prices = {}
            
            risk_metrics = await risk_calculator.calculate_real_time_risk(
                account_id=account_id,
                positions=positions,
                account_balance=account_balance,
                margin_available=margin_available,
                current_prices=current_prices
            )
        
        # Perform compliance check
        compliance_records = await compliance_engine.perform_compliance_check(
            account_id=account_id,
            risk_metrics=risk_metrics,
            positions=positions,
            regulations=regulations
        )
        
        return {
            "account_id": account_id,
            "check_timestamp": time.time(),
            "records_generated": len(compliance_records),
            "violations": sum(1 for r in compliance_records if r.status == "violation"),
            "compliance_records": [
                {
                    "record_type": record.record_type,
                    "regulation": record.regulation,
                    "status": record.status,
                    "severity": record.severity.value,
                    "description": record.description
                }
                for record in compliance_records
            ]
        }
        
    except Exception as e:
        logger.error("Failed to perform compliance check", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to perform compliance check: {str(e)}")


# System Management Endpoints

@app.get("/api/v1/system/performance", tags=["System Management"])
async def get_system_performance():
    """Get overall system performance metrics."""
    try:
        performance_data = {
            "timestamp": time.time(),
            "monitored_accounts": len(app_state.monitored_accounts),
            "system_status": "healthy" if app_state.initialized else "initializing"
        }
        
        if app_state.risk_calculator:
            performance_data["risk_calculator"] = app_state.risk_calculator.get_performance_metrics()
        
        if app_state.pl_monitor:
            performance_data["pl_monitor"] = app_state.pl_monitor.get_monitoring_performance()
        
        if app_state.alert_manager:
            performance_data["alert_manager"] = app_state.alert_manager.get_performance_metrics()
        
        if app_state.compliance_engine:
            performance_data["compliance_engine"] = app_state.compliance_engine.get_compliance_summary()
        
        return performance_data
        
    except Exception as e:
        logger.error("Failed to get system performance", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get system performance: {str(e)}")


@app.post("/api/v1/system/emergency/kill-switch/{account_id}", tags=["System Management"])
async def activate_emergency_kill_switch(
    account_id: str,
    reason: str,
    background_tasks: BackgroundTasks
):
    """Activate emergency kill switch for an account."""
    try:
        logger.critical("Emergency kill switch activated", account_id=account_id, reason=reason)
        
        # Trigger kill switch in execution engine
        if app_state.execution_client and app_state.execution_client.is_connected:
            success = await app_state.execution_client.trigger_kill_switch(account_id, reason)
            
            if success:
                # Generate critical alert
                if app_state.alert_manager:
                    background_tasks.add_task(
                        app_state.alert_manager.process_risk_metrics,
                        account_id,
                        # Mock high-risk metrics to trigger alert
                        type('RiskMetrics', (), {
                            'risk_score': 100.0,
                            'risk_level': 'critical',
                            'risk_limit_breaches': [f'emergency_kill_switch: {reason}']
                        })(),
                        []
                    )
                
                return {
                    "status": "activated",
                    "account_id": account_id,
                    "reason": reason,
                    "timestamp": time.time()
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to activate kill switch in execution engine")
        else:
            raise HTTPException(status_code=503, detail="Execution engine not available")
            
    except Exception as e:
        logger.error("Failed to activate kill switch", account_id=account_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to activate kill switch: {str(e)}")


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception", 
                path=str(request.url),
                method=request.method,
                error=str(exc))
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8006"))
    log_level = os.getenv("LOG_LEVEL", "info")
    
    logger.info("Starting Risk Management & Portfolio Analytics Engine",
               host=host,
               port=port,
               log_level=log_level)
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
        access_log=False,
    )