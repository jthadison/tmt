"""
Parameter Optimization Agent - Main API

FastAPI service for adaptive risk parameter tuning
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .adaptive_risk_parameter_tuner import AdaptiveRiskParameterTuner
from .performance_calculator import TradeRecord
from .stop_loss_optimizer import ATRData
from .models import ImplementationMethod, OptimizationStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Parameter Optimization Agent",
    description="Adaptive Risk Parameter Tuning for Trading Systems",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the parameter tuner
tuner = AdaptiveRiskParameterTuner()


# Pydantic models for API
class TradeRecordRequest(BaseModel):
    """Trade record for API requests"""
    trade_id: str
    account_id: str
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    pnl_pips: float
    commission: float
    slippage: float
    trade_type: str
    exit_reason: str
    signal_confidence: float
    market_regime: str = "unknown"


class ATRDataRequest(BaseModel):
    """ATR data for API requests"""
    timestamp: datetime
    symbol: str
    atr_value: float
    high: float
    low: float
    close: float


class OptimizationRequest(BaseModel):
    """Request for parameter optimization"""
    account_id: str
    trade_history: List[TradeRecordRequest]
    market_data: Optional[List[ATRDataRequest]] = None
    force_optimization: bool = False


class ImplementationRequest(BaseModel):
    """Request for implementing parameter adjustments"""
    account_id: str
    optimization_id: str
    approved_adjustment_ids: List[str]
    implementation_method: str = "immediate"


class MonitoringRequest(BaseModel):
    """Request for monitoring parameter changes"""
    account_id: str
    change_id: str
    current_performance: Dict[str, Any]


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Parameter Optimization Agent", "status": "active"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/process_signal")
async def process_signal(signal: dict):
    """
    Process a signal for parameter optimization (compatibility endpoint).
    Returns current optimization parameters for the signal.
    """
    try:
        # For now, return default parameters as this agent focuses on historical analysis
        # In a full implementation, this would analyze the signal and suggest optimal parameters
        return {
            "status": "processed",
            "suggested_parameters": {
                "position_size": 0.01,  # 1% risk
                "stop_loss_pips": 20,
                "take_profit_pips": 40,
                "max_drawdown": 0.02
            },
            "confidence": 0.75,
            "message": "Signal processed with default parameters"
        }
    except Exception as e:
        logger.error(f"Error processing signal: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/optimize")
async def optimize_parameters(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """
    Optimize parameters for an account
    """
    try:
        # Convert request data to internal models
        trade_history = []
        for trade_req in request.trade_history:
            trade = TradeRecord(
                trade_id=trade_req.trade_id,
                account_id=trade_req.account_id,
                symbol=trade_req.symbol,
                entry_time=trade_req.entry_time,
                exit_time=trade_req.exit_time,
                entry_price=trade_req.entry_price,
                exit_price=trade_req.exit_price,
                position_size=trade_req.position_size,
                pnl=trade_req.pnl,
                pnl_pips=trade_req.pnl_pips,
                commission=trade_req.commission,
                slippage=trade_req.slippage,
                trade_type=trade_req.trade_type,
                exit_reason=trade_req.exit_reason,
                signal_confidence=trade_req.signal_confidence
            )
            trade_history.append(trade)
        
        # Convert market data if provided
        market_data = None
        if request.market_data:
            market_data = []
            for atr_req in request.market_data:
                atr_data = ATRData(
                    timestamp=atr_req.timestamp,
                    symbol=atr_req.symbol,
                    atr_value=atr_req.atr_value,
                    high=atr_req.high,
                    low=atr_req.low,
                    close=atr_req.close
                )
                market_data.append(atr_data)
        
        # Run optimization
        optimization = tuner.optimize_account_parameters(
            request.account_id,
            trade_history,
            market_data,
            request.force_optimization
        )
        
        # Convert to response format
        response = {
            "optimization_id": optimization.analysis_id,
            "account_id": optimization.account_id,
            "timestamp": optimization.timestamp,
            "status": optimization.status.value,
            "adjustments_count": len(optimization.adjustments),
            "adjustments": [
                {
                    "adjustment_id": adj.adjustment_id,
                    "parameter_name": adj.parameter_name,
                    "category": adj.category.value,
                    "current_value": adj.current_value,
                    "proposed_value": adj.proposed_value,
                    "change_percentage": adj.change_percentage,
                    "change_reason": adj.change_reason,
                    "confidence_level": adj.analysis.get("confidence_level", 0.0),
                    "performance_impact": adj.analysis.get("performance_impact", 0.0)
                }
                for adj in optimization.adjustments
            ]
        }
        
        logger.info(f"Parameter optimization completed for {request.account_id}")
        return response
        
    except Exception as e:
        logger.error(f"Parameter optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/implement")
async def implement_adjustments(request: ImplementationRequest):
    """
    Implement approved parameter adjustments
    """
    try:
        # Convert implementation method
        impl_method = ImplementationMethod.IMMEDIATE
        if request.implementation_method.lower() == "gradual":
            impl_method = ImplementationMethod.GRADUAL
        elif request.implementation_method.lower() == "ab_test":
            impl_method = ImplementationMethod.AB_TEST
        
        # Implement adjustments
        change_log = tuner.implement_adjustments(
            request.account_id,
            request.optimization_id,
            request.approved_adjustment_ids,
            impl_method
        )
        
        response = {
            "change_id": change_log.change_id,
            "account_id": change_log.account_id,
            "timestamp": change_log.timestamp,
            "implementation_method": change_log.implementation_method.value,
            "changes_count": len(change_log.parameter_changes),
            "authorized_by": change_log.authorized_by,
            "monitoring_period": change_log.monitoring.get("monitoring_period", 7)
        }
        
        logger.info(f"Implemented {len(request.approved_adjustment_ids)} adjustments for {request.account_id}")
        return response
        
    except Exception as e:
        logger.error(f"Implementation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/monitor")
async def monitor_changes(request: MonitoringRequest):
    """
    Monitor the impact of parameter changes
    """
    try:
        monitoring_results = tuner.monitor_parameter_changes(
            request.account_id,
            request.change_id,
            request.current_performance
        )
        
        logger.info(f"Monitoring completed for {request.account_id}, change {request.change_id}")
        return monitoring_results
        
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report/{account_id}")
async def get_optimization_report(account_id: str, days: int = 30):
    """
    Get optimization report for an account
    """
    try:
        report = tuner.get_optimization_report(account_id, days)
        
        logger.info(f"Generated optimization report for {account_id}")
        return report
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/constraints/{account_id}")
async def get_constraints_summary(account_id: str):
    """
    Get constraints summary for an account
    """
    try:
        summary = tuner.constraints.get_constraint_summary(account_id)
        
        logger.info(f"Generated constraints summary for {account_id}")
        return summary
        
    except Exception as e:
        logger.error(f"Constraints summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/optimizations")
async def list_optimizations(account_id: Optional[str] = None, limit: int = 10):
    """
    List recent optimizations
    """
    try:
        optimizations = list(tuner.optimizations.values())
        
        # Filter by account if specified
        if account_id:
            optimizations = [opt for opt in optimizations if opt.account_id == account_id]
        
        # Sort by timestamp (most recent first)
        optimizations.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Limit results
        optimizations = optimizations[:limit]
        
        response = [
            {
                "optimization_id": opt.analysis_id,
                "account_id": opt.account_id,
                "timestamp": opt.timestamp,
                "status": opt.status.value,
                "adjustments_count": len(opt.adjustments)
            }
            for opt in optimizations
        ]
        
        return response
        
    except Exception as e:
        logger.error(f"List optimizations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/optimizations/{optimization_id}")
async def delete_optimization(optimization_id: str):
    """
    Delete an optimization (for cleanup)
    """
    try:
        if optimization_id in tuner.optimizations:
            del tuner.optimizations[optimization_id]
            logger.info(f"Deleted optimization {optimization_id}")
            return {"message": "Optimization deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Optimization not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)