#!/usr/bin/env python3
"""
Circuit Breaker Agent API Service
Provides REST API for circuit breaker monitoring and control
"""

import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime

from circuit_breaker import CircuitBreakerAgent, BreakerConfig, BreakerState, AlertLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("circuit_breaker_api")

# Create FastAPI app
app = FastAPI(title="Circuit Breaker Agent", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global circuit breaker instance
breaker: Optional[CircuitBreakerAgent] = None


class BreakerConfigUpdate(BaseModel):
    """Model for updating breaker configuration"""
    max_daily_loss_percent: Optional[float] = None
    max_consecutive_losses: Optional[int] = None
    max_position_size_percent: Optional[float] = None
    max_trades_per_hour: Optional[int] = None
    max_trades_per_day: Optional[int] = None
    min_margin_level: Optional[float] = None
    max_drawdown_percent: Optional[float] = None
    cooldown_minutes: Optional[int] = None
    max_correlated_positions: Optional[int] = None
    max_total_exposure_percent: Optional[float] = None


class ManualOverride(BaseModel):
    """Model for manual circuit breaker override"""
    action: str  # "open", "close", "reset"
    reason: str
    force: bool = False


class TradeEvaluation(BaseModel):
    """Model for evaluating if a trade should be allowed"""
    instrument: str
    direction: str  # "long" or "short"
    units: float
    account_id: str


@app.on_event("startup")
async def startup_event():
    """Initialize circuit breaker on startup"""
    global breaker
    
    # Load configuration from environment or use defaults
    config = BreakerConfig(
        max_daily_loss_percent=float(os.getenv("CB_MAX_DAILY_LOSS", "5.0")),
        max_consecutive_losses=int(os.getenv("CB_MAX_CONSECUTIVE_LOSSES", "3")),
        max_position_size_percent=float(os.getenv("CB_MAX_POSITION_SIZE", "10.0")),
        max_trades_per_hour=int(os.getenv("CB_MAX_TRADES_HOUR", "10")),
        max_trades_per_day=int(os.getenv("CB_MAX_TRADES_DAY", "20")),
        min_margin_level=float(os.getenv("CB_MIN_MARGIN", "150.0")),
        max_drawdown_percent=float(os.getenv("CB_MAX_DRAWDOWN", "10.0")),
        cooldown_minutes=int(os.getenv("CB_COOLDOWN", "30"))
    )
    
    breaker = CircuitBreakerAgent(config)
    
    # Start monitoring in background
    asyncio.create_task(breaker.start())
    
    logger.info("Circuit Breaker Agent API started")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Circuit Breaker Agent",
        "status": "running",
        "breaker_state": breaker.state.value if breaker else "not_initialized"
    }


@app.get("/api/status")
async def get_status():
    """Get current circuit breaker status"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    return breaker.get_status()


@app.get("/api/metrics")
async def get_metrics():
    """Get current trading metrics"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    return {
        "daily_pnl": breaker.metrics.daily_pnl,
        "daily_trades": breaker.metrics.daily_trades,
        "hourly_trades": breaker.metrics.hourly_trades,
        "consecutive_losses": breaker.metrics.consecutive_losses,
        "consecutive_wins": breaker.metrics.consecutive_wins,
        "largest_position_percent": breaker.metrics.largest_position_percent,
        "total_exposure_percent": breaker.metrics.total_exposure_percent,
        "margin_level": breaker.metrics.margin_level,
        "drawdown_percent": breaker.metrics.drawdown_percent,
        "current_balance": breaker.metrics.current_balance,
        "peak_balance": breaker.metrics.peak_balance,
        "open_positions": breaker.metrics.open_positions,
        "correlated_positions": breaker.metrics.correlated_positions,
        "last_trade_time": breaker.metrics.last_trade_time.isoformat() if breaker.metrics.last_trade_time else None
    }


@app.get("/api/config")
async def get_config():
    """Get current circuit breaker configuration"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    config = breaker.config
    return {
        "max_daily_loss_percent": config.max_daily_loss_percent,
        "max_consecutive_losses": config.max_consecutive_losses,
        "max_position_size_percent": config.max_position_size_percent,
        "max_trades_per_hour": config.max_trades_per_hour,
        "max_trades_per_day": config.max_trades_per_day,
        "min_margin_level": config.min_margin_level,
        "max_drawdown_percent": config.max_drawdown_percent,
        "cooldown_minutes": config.cooldown_minutes,
        "half_open_test_trades": config.half_open_test_trades,
        "max_correlated_positions": config.max_correlated_positions,
        "max_total_exposure_percent": config.max_total_exposure_percent
    }


@app.put("/api/config")
async def update_config(update: BreakerConfigUpdate):
    """Update circuit breaker configuration"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    config = breaker.config
    
    # Update only provided fields
    if update.max_daily_loss_percent is not None:
        config.max_daily_loss_percent = update.max_daily_loss_percent
    if update.max_consecutive_losses is not None:
        config.max_consecutive_losses = update.max_consecutive_losses
    if update.max_position_size_percent is not None:
        config.max_position_size_percent = update.max_position_size_percent
    if update.max_trades_per_hour is not None:
        config.max_trades_per_hour = update.max_trades_per_hour
    if update.max_trades_per_day is not None:
        config.max_trades_per_day = update.max_trades_per_day
    if update.min_margin_level is not None:
        config.min_margin_level = update.min_margin_level
    if update.max_drawdown_percent is not None:
        config.max_drawdown_percent = update.max_drawdown_percent
    if update.cooldown_minutes is not None:
        config.cooldown_minutes = update.cooldown_minutes
    if update.max_correlated_positions is not None:
        config.max_correlated_positions = update.max_correlated_positions
    if update.max_total_exposure_percent is not None:
        config.max_total_exposure_percent = update.max_total_exposure_percent
    
    logger.info(f"Circuit breaker configuration updated: {config}")
    
    return {"message": "Configuration updated", "config": await get_config()}


@app.post("/api/evaluate-trade")
async def evaluate_trade(trade: TradeEvaluation):
    """Evaluate if a trade should be allowed"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    # Check if circuit breaker is open
    if breaker.state == BreakerState.OPEN:
        return {
            "allowed": False,
            "reason": "Circuit breaker is OPEN - trading halted",
            "state": breaker.state.value
        }
    
    # Check if in half-open state
    if breaker.state == BreakerState.HALF_OPEN:
        if breaker.test_trades_count >= breaker.config.half_open_test_trades:
            return {
                "allowed": False,
                "reason": "Half-open test limit reached",
                "state": breaker.state.value
            }
        # Allow test trade
        breaker.test_trades_count += 1
        return {
            "allowed": True,
            "reason": "Test trade allowed in half-open state",
            "state": breaker.state.value,
            "test_trade": True
        }
    
    # Check safety conditions
    breaches = breaker.check_safety_conditions()
    
    if breaches:
        critical_breaches = [b for b in breaches if b["level"].value >= AlertLevel.CRITICAL.value]
        if critical_breaches:
            return {
                "allowed": False,
                "reason": f"Safety breach: {critical_breaches[0]['type']}",
                "breaches": breaches,
                "state": breaker.state.value
            }
    
    return {
        "allowed": True,
        "reason": "Trade approved by circuit breaker",
        "state": breaker.state.value
    }


@app.post("/api/override")
async def manual_override(override: ManualOverride):
    """Manually override circuit breaker state"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    if override.action == "open":
        await breaker.open_circuit_breaker()
        logger.warning(f"Manual override: Circuit breaker OPENED - {override.reason}")
    elif override.action == "close":
        if override.force or breaker.state == BreakerState.HALF_OPEN:
            breaker.state = BreakerState.CLOSED
            breaker.last_state_change = datetime.now()
            logger.warning(f"Manual override: Circuit breaker CLOSED - {override.reason}")
        else:
            raise HTTPException(status_code=400, detail="Cannot close circuit breaker without force flag")
    elif override.action == "reset":
        # Reset metrics
        breaker.metrics.consecutive_losses = 0
        breaker.metrics.daily_pnl = 0
        breaker.metrics.daily_trades = 0
        breaker.metrics.hourly_trades = 0
        logger.info(f"Manual override: Metrics RESET - {override.reason}")
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {override.action}")
    
    return {"message": f"Override applied: {override.action}", "state": breaker.state.value}


@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    """Get recent alerts"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    return {
        "alerts": breaker.alerts[-limit:] if len(breaker.alerts) > limit else breaker.alerts,
        "total": len(breaker.alerts)
    }


@app.get("/api/state-history")
async def get_state_history(limit: int = 50):
    """Get circuit breaker state history"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    return {
        "history": breaker.state_history[-limit:] if len(breaker.state_history) > limit else breaker.state_history,
        "current_state": breaker.state.value,
        "last_change": breaker.last_state_change.isoformat()
    }


@app.post("/api/report-trade")
async def report_trade(trade_result: Dict):
    """Report trade result to update metrics"""
    if not breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not initialized")
    
    # Update metrics based on trade result
    success = trade_result.get("success", False)
    pnl = trade_result.get("pnl", 0)
    
    if success:
        if pnl > 0:
            breaker.metrics.consecutive_wins += 1
            breaker.metrics.consecutive_losses = 0
        else:
            breaker.metrics.consecutive_losses += 1
            breaker.metrics.consecutive_wins = 0
    
    breaker.metrics.daily_pnl += pnl
    breaker.metrics.daily_trades += 1
    breaker.metrics.hourly_trades += 1  # Would need time-based reset
    breaker.metrics.last_trade_time = datetime.now()
    
    # Check if we need to trigger circuit breaker
    breaches = breaker.check_safety_conditions()
    if breaches:
        await breaker.handle_breaches(breaches)
    
    return {
        "message": "Trade reported",
        "metrics_updated": True,
        "breaker_state": breaker.state.value
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "breaker_initialized": breaker is not None,
        "breaker_state": breaker.state.value if breaker else None
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8085"))
    uvicorn.run(app, host="0.0.0.0", port=port)