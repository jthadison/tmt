"""
Compliance Agent FastAPI Application

Main application entry point for the prop firm rules engine.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Dict, List, Optional
from datetime import datetime
import uvicorn

from .models import (
    ValidationRequest, ValidationResult, TradingAccount, 
    AccountStatus, ComplianceViolation, ComplianceMetrics
)
from .rules_engine import RulesEngine, ComplianceMonitor
from .prop_firm_configs import PropFirm, get_all_prop_firms
from .us_regulatory import (
    USRegulatoryComplianceEngine, OrderRequest, ComplianceResult
)
from ..shared.health import HealthChecker
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
    app.state.us_regulatory_engine = USRegulatoryComplianceEngine()
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
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Restrict origins for security
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


def get_us_regulatory_engine() -> USRegulatoryComplianceEngine:
    """Get US regulatory compliance engine dependency"""
    return app.state.us_regulatory_engine


async def _get_account_from_database(account_id: str) -> Optional[TradingAccount]:
    """
    Mock function to simulate database account lookup
    TODO: Replace with actual database implementation
    """
    # Mock account data - in production this would be a database query
    mock_accounts = {
        "test_account_1": TradingAccount(
            account_id=account_id,
            prop_firm=PropFirm.DNA_FUNDED,
            account_phase="funded",
            initial_balance=50000,
            current_balance=51000,
            platform="tradelocker",
            status="compliant",
            created_at=datetime.utcnow()
        ),
        "funding_pips_account": TradingAccount(
            account_id=account_id,
            prop_firm=PropFirm.FUNDING_PIPS,
            account_phase="funded",
            initial_balance=25000,
            current_balance=25500,
            platform="dxtrade",
            status="compliant",
            created_at=datetime.utcnow()
        )
    }
    
    return mock_accounts.get(account_id)


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
        # TODO: Replace with actual database lookup
        # In a real implementation, we would fetch the account from database
        account = await _get_account_from_database(request.account_id)
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {request.account_id} not found")
        
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


# US Regulatory Compliance Endpoints

@app.post("/api/v1/compliance/us-regulatory/validate-order", response_model=dict)
async def validate_us_order(
    order_request: dict,
    account_balance: float,
    current_margin_used: float = 0.0,
    us_engine: USRegulatoryComplianceEngine = Depends(get_us_regulatory_engine)
):
    """
    Validate order against US regulatory requirements (FIFO, anti-hedging, leverage)
    
    For US-based retail traders who must comply with NFA regulations.
    """
    try:
        from decimal import Decimal
        
        # Convert request to OrderRequest object
        order = OrderRequest(
            instrument=order_request["instrument"],
            units=order_request["units"],
            side=order_request["side"],
            order_type=order_request["order_type"],
            price=Decimal(str(order_request.get("price", "1.0"))),
            account_id=order_request["account_id"],
            account_region=order_request.get("account_region", "US")
        )
        
        result = await us_engine.validate_order_compliance(
            order, Decimal(str(account_balance)), Decimal(str(current_margin_used))
        )
        
        return {
            "valid": result.valid,
            "violation_type": result.violation_type.value if result.violation_type else None,
            "reason": result.reason,
            "suggested_action": result.suggested_action,
            "metadata": result.metadata
        }
        
    except Exception as e:
        logger.error(f"Error validating US order: {e}")
        raise HTTPException(status_code=500, detail=f"US validation error: {str(e)}")


@app.post("/api/v1/compliance/us-regulatory/add-position")
async def add_fifo_position(
    position_data: dict,
    us_engine: USRegulatoryComplianceEngine = Depends(get_us_regulatory_engine)
):
    """
    Add position to FIFO tracking queue
    
    Called when a new position is opened to maintain FIFO compliance.
    """
    try:
        from decimal import Decimal
        from datetime import datetime
        from .us_regulatory import Position
        
        position = Position(
            id=position_data["id"],
            instrument=position_data["instrument"],
            units=position_data["units"],
            side=position_data["side"],
            entry_price=Decimal(str(position_data["entry_price"])),
            timestamp=datetime.fromisoformat(position_data["timestamp"]),
            account_id=position_data["account_id"]
        )
        
        us_engine.fifo_engine.add_position(position)
        
        return {
            "success": True,
            "message": f"Position {position.id} added to FIFO queue"
        }
        
    except Exception as e:
        logger.error(f"Error adding FIFO position: {e}")
        raise HTTPException(status_code=500, detail=f"Position add error: {str(e)}")


@app.post("/api/v1/compliance/us-regulatory/auto-select-positions")
async def auto_select_fifo_positions(
    request_data: dict,
    us_engine: USRegulatoryComplianceEngine = Depends(get_us_regulatory_engine)
):
    """
    Automatically select positions for FIFO-compliant closing
    
    Returns the positions that should be closed to maintain FIFO order.
    """
    try:
        selected_positions = us_engine.fifo_engine.auto_select_fifo_positions(
            account_id=request_data["account_id"],
            instrument=request_data["instrument"],
            units_to_close=request_data["units_to_close"],
            closing_side=request_data["closing_side"]
        )
        
        return {
            "selected_positions": [
                {
                    "id": pos.id,
                    "units": pos.units,
                    "entry_price": str(pos.entry_price),
                    "timestamp": pos.timestamp.isoformat(),
                    "side": pos.side
                }
                for pos in selected_positions
            ],
            "total_units": sum(pos.units for pos in selected_positions)
        }
        
    except Exception as e:
        logger.error(f"Error selecting FIFO positions: {e}")
        raise HTTPException(status_code=500, detail=f"Position selection error: {str(e)}")


@app.get("/api/v1/compliance/us-regulatory/leverage-limits")
async def get_leverage_limits():
    """Get US leverage limits for major and minor currency pairs"""
    return {
        "major_pairs": [
            "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", 
            "USD_CAD", "AUD_USD", "NZD_USD"
        ],
        "leverage_limits": {
            "major": "50:1",
            "minor": "20:1"
        },
        "description": "US NFA regulatory leverage limits for retail traders"
    }


@app.post("/api/v1/compliance/us-regulatory/calculate-max-position")
async def calculate_max_position_size(
    request_data: dict,
    us_engine: USRegulatoryComplianceEngine = Depends(get_us_regulatory_engine)
):
    """
    Calculate maximum position size given leverage limits
    
    Helps traders determine the largest position they can open.
    """
    try:
        from decimal import Decimal
        
        max_units = us_engine.leverage_validator.calculate_max_position_size(
            instrument=request_data["instrument"],
            price=Decimal(str(request_data["price"])),
            available_margin=Decimal(str(request_data["available_margin"]))
        )
        
        return {
            "instrument": request_data["instrument"],
            "max_units": max_units,
            "price": request_data["price"],
            "available_margin": request_data["available_margin"],
            "pair_type": "major" if request_data["instrument"] in us_engine.leverage_validator.major_pairs else "minor"
        }
        
    except Exception as e:
        logger.error(f"Error calculating max position: {e}")
        raise HTTPException(status_code=500, detail=f"Position calculation error: {str(e)}")


@app.get("/api/v1/compliance/us-regulatory/summary/{account_id}")
async def get_us_compliance_summary(
    account_id: str,
    us_engine: USRegulatoryComplianceEngine = Depends(get_us_regulatory_engine)
):
    """
    Get US regulatory compliance summary for account
    
    Returns FIFO positions, compliance checks, and violation history.
    """
    try:
        summary = us_engine.get_compliance_summary(account_id)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting US compliance summary: {e}")
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,  # Different port for compliance agent
        reload=True,
        log_level="info"
    )