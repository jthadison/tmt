"""
Compliance Agent FastAPI Application

Main application entry point for the prop firm rules engine.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Dict, List
import uvicorn

from .models import (
    ValidationRequest, ValidationResult, TradingAccount, 
    AccountStatus, ComplianceViolation, ComplianceMetrics
)
from .rules_engine import RulesEngine, ComplianceMonitor
from .prop_firm_configs import PropFirm, get_all_prop_firms
from ...shared.health import HealthChecker
from .config import get_settings


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Compliance Agent...")
    
    # Initialize components
    app.state.rules_engine = RulesEngine()
    app.state.compliance_monitor = ComplianceMonitor(app.state.rules_engine)
    app.state.health_checker = HealthChecker(
        service_name="compliance-agent",
        version="1.0.0"
    )
    
    logger.info("Compliance Agent started successfully")
    yield
    
    logger.info("Shutting down Compliance Agent...")


# Create FastAPI application
app = FastAPI(
    title="Compliance Agent - Prop Firm Rules Engine",
    description="Validates trades against prop firm rules to maintain account compliance",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_rules_engine() -> RulesEngine:
    """Get rules engine dependency"""
    return app.state.rules_engine


def get_compliance_monitor() -> ComplianceMonitor:
    """Get compliance monitor dependency"""
    return app.state.compliance_monitor


def get_health_checker() -> HealthChecker:
    """Get health checker dependency"""
    return app.state.health_checker


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "compliance-agent",
        "version": "1.0.0",
        "status": "running",
        "description": "Prop Firm Rules Engine for trade compliance validation"
    }


@app.get("/health")
async def health_check(health_checker: HealthChecker = Depends(get_health_checker)):
    """Standard health check endpoint"""
    return await health_checker.check_health()


@app.post("/api/v1/compliance/validate-trade", response_model=ValidationResult)
async def validate_trade(
    request: ValidationRequest,
    rules_engine: RulesEngine = Depends(get_rules_engine)
):
    """
    Validate a trade order against prop firm rules
    
    This is the main endpoint for pre-trade validation. It checks the trade
    against all applicable rules for the account's prop firm and returns
    detailed validation results.
    """
    try:
        # In a real implementation, we would fetch the account from database
        # For now, create a mock account based on request
        account = TradingAccount(
            account_id=request.account_id,
            prop_firm=PropFirm.DNA_FUNDED,  # Would be fetched from database
            account_phase="funded",
            initial_balance=50000,  # Would be fetched from database
            current_balance=51000,  # Would be fetched from database
            platform="tradelocker",
            status="compliant"
        )
        
        result = await rules_engine.validate_trade(
            account=account,
            trade_order=request.trade_order,
            current_positions=request.current_positions,
            upcoming_news=request.upcoming_news
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating trade: {e}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@app.get("/api/v1/compliance/account-status/{account_id}", response_model=AccountStatus)
async def get_account_status(
    account_id: str,
    rules_engine: RulesEngine = Depends(get_rules_engine)
):
    """
    Get current compliance status for an account
    
    Returns comprehensive compliance status including P&L, drawdown,
    position counts, and recent violations.
    """
    try:
        # Mock implementation - would fetch from database
        status = AccountStatus(
            account_id=account_id,
            compliance_status="compliant",
            daily_pnl=150.00,
            daily_loss_limit=2500.00,
            daily_loss_remaining=2350.00,
            total_drawdown=0.00,
            max_drawdown_limit=5000.00,
            drawdown_remaining=5000.00,
            open_positions=2,
            max_positions_allowed=5,
            trading_days_completed=8,
            min_trading_days_required=5,
            recent_violations=[],
            warnings=[]
        )
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting account status: {e}")
        raise HTTPException(status_code=500, detail=f"Status error: {str(e)}")


@app.get("/api/v1/compliance/violations/{account_id}", response_model=List[ComplianceViolation])
async def get_violations(
    account_id: str,
    limit: int = 50
):
    """
    Get violation history for an account
    
    Returns recent violations with details about rules violated,
    timestamps, and resolution status.
    """
    try:
        # Mock implementation - would fetch from database
        violations = []  # Would query violation history
        
        return violations
        
    except Exception as e:
        logger.error(f"Error getting violations: {e}")
        raise HTTPException(status_code=500, detail=f"Violations error: {str(e)}")


@app.get("/api/v1/compliance/prop-firms", response_model=List[str])
async def get_supported_prop_firms():
    """Get list of supported prop firms"""
    return [firm.value for firm in get_all_prop_firms()]


@app.get("/api/v1/compliance/metrics/{account_id}", response_model=ComplianceMetrics)
async def get_compliance_metrics(
    account_id: str
):
    """
    Get compliance metrics for monitoring and analysis
    
    Returns statistics about validation performance, violation rates,
    and overall compliance health.
    """
    try:
        # Mock implementation - would calculate from database
        metrics = ComplianceMetrics(
            account_id=account_id,
            total_trades=245,
            successful_validations=242,
            violations_count=3,
            warnings_count=12,
            compliance_rate=98.8,
            avg_validation_time_ms=24.5,
            last_violation=None,
            uptime_minutes=1440
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting compliance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics error: {str(e)}")


@app.post("/api/v1/compliance/update-pnl")
async def update_account_pnl(
    account_id: str,
    realized_pnl: float,
    unrealized_pnl: float,
    compliance_monitor: ComplianceMonitor = Depends(get_compliance_monitor)
):
    """
    Update account P&L and check for violations
    
    This endpoint is called when positions are closed or mark-to-market
    updates are received to maintain real-time compliance monitoring.
    """
    try:
        # Mock account fetch - would get from database
        account = TradingAccount(
            account_id=account_id,
            prop_firm=PropFirm.DNA_FUNDED,
            account_phase="funded",
            initial_balance=50000,
            current_balance=51000,
            platform="tradelocker",
            status="compliant"
        )
        
        is_compliant = await compliance_monitor.update_account_pnl(
            account=account,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl
        )
        
        return {
            "account_id": account_id,
            "updated": True,
            "is_compliant": is_compliant,
            "new_balance": float(account.current_balance),
            "daily_pnl": float(account.daily_pnl),
            "status": account.status.value
        }
        
    except Exception as e:
        logger.error(f"Error updating P&L: {e}")
        raise HTTPException(status_code=500, detail=f"P&L update error: {str(e)}")


@app.post("/api/v1/compliance/reset-daily")
async def reset_daily_pnl(
    account_id: str,
    compliance_monitor: ComplianceMonitor = Depends(get_compliance_monitor)
):
    """
    Reset daily P&L for an account (called at market close)
    
    This endpoint resets the daily P&L tracking and increments
    the trading days counter for the account.
    """
    try:
        # Mock account fetch - would get from database
        account = TradingAccount(
            account_id=account_id,
            prop_firm=PropFirm.DNA_FUNDED,
            account_phase="funded",
            initial_balance=50000,
            current_balance=51000,
            platform="tradelocker",
            status="compliant"
        )
        
        await compliance_monitor.reset_daily_pnl(account)
        
        return {
            "account_id": account_id,
            "reset": True,
            "trading_days_completed": account.trading_days_completed,
            "reset_time": account.last_reset_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting daily P&L: {e}")
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,  # Different port for compliance agent
        reload=True,
        log_level="info"
    )