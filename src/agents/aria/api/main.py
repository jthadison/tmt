"""
ARIA REST API
=============

FastAPI application providing REST endpoints for position sizing calculations,
risk management, and portfolio analysis functionality.
"""

import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from ..position_sizing.calculator import PositionSizeCalculator
from ..position_sizing.models import (
    PositionSizeRequest, PositionSizeResponse, PositionSize,
    RiskModel, PropFirm
)
from ..position_sizing.validators import PositionSizeValidator
from ..position_sizing.adjusters import (
    VolatilityAdjuster, DrawdownAdjuster, CorrelationAdjuster,
    PropFirmLimitChecker, SizeVarianceEngine
)
from ..position_sizing.adjusters.drawdown import DrawdownTracker
from ..position_sizing.adjusters.correlation import PositionTracker, CorrelationCalculator
from ..position_sizing.adjusters.prop_firm_limits import AccountFirmMapping
from ..position_sizing.adjusters.variance import VarianceHistoryTracker

logger = logging.getLogger(__name__)


# Pydantic models for API requests/responses
class PositionSizeRequestAPI(BaseModel):
    """API request model for position size calculation."""
    signal_id: str
    account_id: str
    symbol: str
    account_balance: float
    stop_distance_pips: float
    risk_model: str = "fixed"
    base_risk_percentage: Optional[float] = 1.0
    entry_price: Optional[float] = None
    direction: str = "long"

    class Config:
        schema_extra = {
            "example": {
                "signal_id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "987fcdeb-51a2-43d7-8f9e-123456789012",
                "symbol": "EURUSD",
                "account_balance": 10000.0,
                "stop_distance_pips": 20.0,
                "risk_model": "fixed",
                "base_risk_percentage": 1.0,
                "direction": "long"
            }
        }


class PositionSizeResponseAPI(BaseModel):
    """API response model for position size calculation."""
    signal_id: str
    account_id: str
    symbol: str
    base_size: float
    adjusted_size: float
    risk_amount: float
    adjustments: Dict[str, float]
    reasoning: str
    validation_errors: List[str]
    warnings: List[str]
    calculation_time_ms: int

    class Config:
        schema_extra = {
            "example": {
                "signal_id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "987fcdeb-51a2-43d7-8f9e-123456789012",
                "symbol": "EURUSD",
                "base_size": 0.50,
                "adjusted_size": 0.35,
                "risk_amount": 100.0,
                "adjustments": {
                    "volatility_factor": 0.9,
                    "drawdown_factor": 0.8,
                    "correlation_factor": 1.0,
                    "limit_factor": 1.0,
                    "variance_factor": 0.95
                },
                "reasoning": "Base calculation: 0.50 lots; Volatility adjustment: reduced by 10.0%; Drawdown adjustment: reduced by 20.0%",
                "validation_errors": [],
                "warnings": [],
                "calculation_time_ms": 45
            }
        }


class AccountLimitsResponse(BaseModel):
    """API response for account limits information."""
    account_id: str
    prop_firm: str
    limits: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = "healthy"
    timestamp: str
    version: str = "1.0.0"


# Dependency injection for components
_position_calculator: Optional[PositionSizeCalculator] = None


def get_position_calculator() -> PositionSizeCalculator:
    """Get or create position size calculator instance."""
    global _position_calculator
    
    if _position_calculator is None:
        # Initialize all components
        drawdown_tracker = DrawdownTracker()
        position_tracker = PositionTracker()
        correlation_calculator = CorrelationCalculator()
        account_firm_mapping = AccountFirmMapping()
        variance_history = VarianceHistoryTracker()
        
        # Create adjusters
        volatility_adjuster = VolatilityAdjuster()
        drawdown_adjuster = DrawdownAdjuster(drawdown_tracker)
        correlation_adjuster = CorrelationAdjuster(position_tracker, correlation_calculator)
        prop_firm_checker = PropFirmLimitChecker(account_firm_mapping)
        variance_engine = SizeVarianceEngine(variance_history)
        
        # Create validator
        validator = PositionSizeValidator()
        
        # Create calculator
        _position_calculator = PositionSizeCalculator(
            volatility_adjuster=volatility_adjuster,
            drawdown_adjuster=drawdown_adjuster,
            correlation_adjuster=correlation_adjuster,
            prop_firm_checker=prop_firm_checker,
            variance_engine=variance_engine,
            validator=validator
        )
    
    return _position_calculator


# Create FastAPI app instance first
app = FastAPI(
    title="ARIA - Adaptive Risk Intelligence Agent",
    description="Position sizing and risk management API for intelligent trading systems",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_aria_app() -> FastAPI:
    """Create and configure the ARIA FastAPI application."""
    return app


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    import datetime
    return HealthResponse(
        status="healthy",
        timestamp=datetime.datetime.utcnow().isoformat(),
        version="1.0.0"
    )


@app.post("/api/v1/position-sizing/calculate", response_model=PositionSizeResponseAPI)
async def calculate_position_size(
    request: PositionSizeRequestAPI,
    calculator: PositionSizeCalculator = Depends(get_position_calculator)
):
    """
    Calculate optimal position size with all adjustment factors applied.
    
    This endpoint applies the complete position sizing algorithm including:
    - Base position size calculation
    - Volatility-based adjustments
    - Drawdown-based size reduction
    - Correlation-based portfolio management
    - Prop firm limit enforcement
    - Anti-detection variance application
    """
    start_time = time.time()
    
    try:
        # Convert API request to internal model
        risk_model = RiskModel(request.risk_model.lower())
        
        internal_request = PositionSizeRequest(
            signal_id=UUID(request.signal_id),
            account_id=UUID(request.account_id),
            symbol=request.symbol,
            account_balance=Decimal(str(request.account_balance)),
            stop_distance_pips=Decimal(str(request.stop_distance_pips)),
            risk_model=risk_model,
            base_risk_percentage=Decimal(str(request.base_risk_percentage or 1.0)),
            entry_price=Decimal(str(request.entry_price)) if request.entry_price else None,
            direction=request.direction
        )
        
        # Calculate position size
        position_size = await calculator.calculate_position_size(internal_request)
        
        # Calculate processing time
        calculation_time_ms = int((time.time() - start_time) * 1000)
        
        # Convert to API response format
        response = PositionSizeResponseAPI(
            signal_id=request.signal_id,
            account_id=request.account_id,
            symbol=position_size.symbol,
            base_size=float(position_size.base_size),
            adjusted_size=float(position_size.adjusted_size),
            risk_amount=float(position_size.risk_amount),
            adjustments={
                "volatility_factor": float(position_size.adjustments.volatility_factor),
                "drawdown_factor": float(position_size.adjustments.drawdown_factor),
                "correlation_factor": float(position_size.adjustments.correlation_factor),
                "limit_factor": float(position_size.adjustments.limit_factor),
                "variance_factor": float(position_size.adjustments.variance_factor)
            },
            reasoning=position_size.reasoning,
            validation_errors=[],  # Populated by validator if needed
            warnings=[],           # Populated by validator if needed  
            calculation_time_ms=calculation_time_ms
        )
        
        logger.info(f"Position size calculated successfully for signal {request.signal_id}: "
                   f"{response.adjusted_size} lots")
        
        return response
        
    except ValueError as e:
        logger.error(f"Invalid request for position sizing: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    
    except Exception as e:
        logger.error(f"Position size calculation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")


@app.get("/api/v1/position-sizing/limits/{account_id}", response_model=AccountLimitsResponse)
async def get_position_limits(
    account_id: str,
    calculator: PositionSizeCalculator = Depends(get_position_calculator)
):
    """Get position limits and constraints for a specific account."""
    try:
        account_uuid = UUID(account_id)
        
        # Get limits from prop firm checker
        limits_data = await calculator.prop_firm_checker.get_account_limits_summary(account_uuid)
        
        return AccountLimitsResponse(
            account_id=account_id,
            prop_firm=limits_data.get('prop_firm', 'unknown'),
            limits=limits_data.get('limits', {})
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid account ID: {str(e)}")
    
    except Exception as e:
        logger.error(f"Failed to get limits for account {account_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get limits: {str(e)}")


@app.get("/api/v1/risk-analysis/drawdown/{account_id}")
async def get_drawdown_status(
    account_id: str,
    calculator: PositionSizeCalculator = Depends(get_position_calculator)
):
    """Get detailed drawdown analysis for an account."""
    try:
        account_uuid = UUID(account_id)
        
        # Get drawdown status
        drawdown_status = await calculator.drawdown_adjuster.get_drawdown_recovery_status(account_uuid)
        
        return drawdown_status
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid account ID: {str(e)}")
    
    except Exception as e:
        logger.error(f"Failed to get drawdown status for account {account_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get drawdown status: {str(e)}")


@app.get("/api/v1/risk-analysis/correlation/{account_id}")
async def get_portfolio_correlation_analysis(
    account_id: str,
    calculator: PositionSizeCalculator = Depends(get_position_calculator)
):
    """Get portfolio correlation and risk analysis for an account."""
    try:
        account_uuid = UUID(account_id)
        
        # Get correlation analysis
        correlation_analysis = await calculator.correlation_adjuster.analyze_portfolio_risk(account_uuid)
        
        return correlation_analysis
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid account ID: {str(e)}")
    
    except Exception as e:
        logger.error(f"Failed to get correlation analysis for account {account_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get correlation analysis: {str(e)}")


@app.get("/api/v1/variance-analysis/{account_id}")
async def get_variance_analysis(
    account_id: str,
    calculator: PositionSizeCalculator = Depends(get_position_calculator)
):
    """Get anti-detection variance analysis for an account."""
    try:
        account_uuid = UUID(account_id)
        
        # Get variance analysis
        variance_analysis = await calculator.variance_engine.get_variance_analysis(account_uuid)
        
        return variance_analysis
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid account ID: {str(e)}")
    
    except Exception as e:
        logger.error(f"Failed to get variance analysis for account {account_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get variance analysis: {str(e)}")


# Main entry point for running the server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )