"""
Trading System Orchestrator - Main Application

Central coordination service for the TMT Trading System that manages
8 specialized AI agents and coordinates automated trading on OANDA accounts.
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uvicorn

from .orchestrator import TradingOrchestrator
from .models import (
    SystemStatus, AgentStatus, AccountStatus, 
    TradeSignal, SystemMetrics, EmergencyStopRequest
)
from .config import get_settings
from .exceptions import OrchestratorException
# Analytics request models
class RealtimePnLRequest(BaseModel):
    accountId: str
    agentId: Optional[str] = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: TradingOrchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global orchestrator
    
    logger.info("Starting Trading System Orchestrator...")
    
    try:
        # Initialize orchestrator
        orchestrator = TradingOrchestrator()
        
        # Start orchestrator
        await orchestrator.start()
        logger.info("Trading System Orchestrator started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start orchestrator: {e}")
        raise
    finally:
        # Cleanup
        if orchestrator:
            logger.info("Shutting down Trading System Orchestrator...")
            await orchestrator.stop()
            logger.info("Trading System Orchestrator stopped")


# Create FastAPI app
app = FastAPI(
    title="TMT Trading System Orchestrator",
    description="Central coordination service for automated trading agents",
    version="1.0.0",
    lifespan=lifespan
)

# Analytics endpoints integrated directly

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(OrchestratorException)
async def orchestrator_exception_handler(request, exc: OrchestratorException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc)}
    )


# Health check endpoint
@app.get("/health", response_model=SystemStatus)
async def health_check():
    """Get system health status"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return await orchestrator.get_system_status()


# System control endpoints
@app.post("/start")
async def start_trading():
    """Start the trading system"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        await orchestrator.start_trading()
        return {"status": "Trading started successfully"}
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@app.post("/stop")
async def stop_trading():
    """Stop the trading system gracefully"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        await orchestrator.stop_trading()
        return {"status": "Trading stopped successfully"}
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@app.post("/emergency-stop")
async def emergency_stop(request: EmergencyStopRequest):
    """Emergency stop - immediately halt all trading"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        await orchestrator.emergency_stop(request.reason)
        return {"status": "Emergency stop executed", "reason": request.reason}
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# Agent management endpoints
@app.get("/agents")
async def list_agents():
    """List all registered agents"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return await orchestrator.list_agents()


@app.get("/agents/{agent_id}/health", response_model=AgentStatus)
async def get_agent_health(agent_id: str):
    """Get health status of specific agent"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        return await orchestrator.get_agent_status(agent_id)
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@app.post("/agents/{agent_id}/restart")
async def restart_agent(agent_id: str, background_tasks: BackgroundTasks):
    """Restart specific agent"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        background_tasks.add_task(orchestrator.restart_agent, agent_id)
        return {"status": f"Agent {agent_id} restart initiated"}
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# Trading control endpoints
@app.get("/accounts")
async def list_accounts():
    """List all OANDA accounts"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return await orchestrator.list_accounts()


@app.get("/accounts/{account_id}/status", response_model=AccountStatus)
async def get_account_status(account_id: str):
    """Get status of specific OANDA account"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        return await orchestrator.get_account_status(account_id)
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@app.post("/accounts/{account_id}/enable")
async def enable_account_trading(account_id: str):
    """Enable trading on specific account"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        await orchestrator.enable_account(account_id)
        return {"status": f"Trading enabled for account {account_id}"}
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@app.post("/accounts/{account_id}/disable")
async def disable_account_trading(account_id: str):
    """Disable trading on specific account"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        await orchestrator.disable_account(account_id)
        return {"status": f"Trading disabled for account {account_id}"}
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# Monitoring endpoints
@app.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics():
    """Get system performance metrics"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return await orchestrator.get_system_metrics()


@app.get("/events")
async def get_recent_events(limit: int = 100):
    """Get recent system events"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return await orchestrator.get_recent_events(limit)


@app.get("/trades")
async def get_recent_trades(limit: int = 50):
    """Get recent trades"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return await orchestrator.get_recent_trades(limit)


@app.get("/positions")
async def get_current_positions():
    """Get current open positions"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return await orchestrator.get_current_positions()


# Signal processing endpoint (for manual testing)
@app.post("/signals/process")
async def process_signal(signal: TradeSignal):
    """Process a trading signal (for testing purposes)"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        result = await orchestrator.process_signal(signal)
        return {"status": "Signal processed", "result": result}
    except OrchestratorException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# Analytics endpoints
@app.post("/analytics/realtime-pnl")
async def get_realtime_pnl(request: RealtimePnLRequest):
    """Get real-time P&L data for an account"""
    try:
        # Return mock data for now - will integrate with OANDA when credentials are ready
        mock_data = {
            "currentPnL": 450.75,
            "realizedPnL": 320.50,
            "unrealizedPnL": 130.25,
            "dailyPnL": 85.30,
            "weeklyPnL": 425.60,
            "monthlyPnL": 1250.80,
            "lastUpdate": datetime.now().isoformat()
        }
        return mock_data
    except Exception as e:
        logger.error(f"Error getting real-time P&L: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time system updates"""
    if not orchestrator:
        await websocket.close(code=1000, reason="Orchestrator not initialized")
        return
    
    await orchestrator.handle_websocket(websocket)


# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info"
    )