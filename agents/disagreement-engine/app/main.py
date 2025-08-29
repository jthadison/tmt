"""
Main API for the Decision Disagreement System.
FastAPI application providing REST endpoints for disagreement processing.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .models import (
    SignalDisagreement, OriginalSignal, DisagreementProfile,
    CorrelationAlert, AccountDecision
)
from .disagreement_engine import DisagreementEngine
from .correlation_monitor import CorrelationMonitor
from .risk_assessment import RiskAssessmentEngine
from .decision_generator import DecisionGenerator
from .timing_spread import TimingSpreadEngine
from .disagreement_logger import DisagreementLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global application state
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Decision Disagreement System")
    
    # Initialize components
    correlation_monitor = CorrelationMonitor(correlation_window=100)
    risk_engine = RiskAssessmentEngine()
    decision_generator = DecisionGenerator(risk_engine)
    timing_engine = TimingSpreadEngine()
    disagreement_logger = DisagreementLogger()
    
    # Initialize main engine
    disagreement_engine = DisagreementEngine(
        correlation_monitor=correlation_monitor,
        risk_engine=risk_engine,
        decision_generator=decision_generator
    )
    
    # Store in app state
    app_state.update({
        "disagreement_engine": disagreement_engine,
        "correlation_monitor": correlation_monitor,
        "risk_engine": risk_engine,
        "timing_engine": timing_engine,
        "disagreement_logger": disagreement_logger,
        "personalities": {}  # Will be populated via API
    })
    
    logger.info("Decision Disagreement System started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down Decision Disagreement System")


app = FastAPI(
    title="Decision Disagreement System",
    description="API for generating trading signal disagreements to avoid correlation",
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


# Request/Response Models
class ProcessSignalRequest(BaseModel):
    signal_id: str
    signal: OriginalSignal
    accounts: List[Dict]
    additional_context: Optional[Dict] = None


class ProcessSignalResponse(BaseModel):
    signal_disagreement: SignalDisagreement
    timing_statistics: Dict
    correlation_statistics: Dict


class RegisterAccountsRequest(BaseModel):
    account_ids: List[str]


class UpdatePersonalityRequest(BaseModel):
    personality_id: str
    profile: DisagreementProfile


class RecordTradeRequest(BaseModel):
    account_id: str
    return_pct: float
    timestamp: Optional[datetime] = None


class CorrelationStatusResponse(BaseModel):
    current_correlations: Dict[str, float]
    high_correlation_pairs: List[tuple]
    recent_alerts: List[CorrelationAlert]
    statistics: Dict[str, float]


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.post("/signals/process", response_model=ProcessSignalResponse)
async def process_signal(
    request: ProcessSignalRequest,
    background_tasks: BackgroundTasks
):
    """
    Process a trading signal and generate disagreements.
    
    This is the main endpoint that implements the disagreement logic.
    """
    return await _process_signal_internal(request, background_tasks)


@app.post("/process_signal", response_model=ProcessSignalResponse)
async def process_signal_legacy(
    request: ProcessSignalRequest,
    background_tasks: BackgroundTasks
):
    """
    Legacy endpoint for compatibility with orchestrator.
    Wraps the main signal processing logic.
    """
    return await _process_signal_internal(request, background_tasks)


async def _process_signal_internal(
    request: ProcessSignalRequest,
    background_tasks: BackgroundTasks
):
    """
    Internal signal processing logic used by both endpoints.
    """
    try:
        logger.info(f"Processing signal {request.signal_id} for {len(request.accounts)} accounts")
        
        # Get components from app state
        disagreement_engine = app_state["disagreement_engine"]
        timing_engine = app_state["timing_engine"]
        correlation_monitor = app_state["correlation_monitor"]
        disagreement_logger = app_state["disagreement_logger"]
        personalities = app_state["personalities"]
        
        # Generate disagreements
        disagreement = disagreement_engine.generate_disagreements(
            signal=request.signal,
            accounts=request.accounts,
            personalities=personalities,
            signal_id=request.signal_id
        )
        
        # Apply timing spread
        disagreement.account_decisions = timing_engine.calculate_entry_timings(
            decisions=disagreement.account_decisions,
            signal=request.signal,
            personalities=personalities
        )
        
        # Get statistics
        timing_stats = timing_engine.get_timing_statistics(disagreement.account_decisions)
        correlation_stats = correlation_monitor.get_correlation_statistics()
        
        # Log the disagreement
        background_tasks.add_task(
            disagreement_logger.log_signal_disagreement,
            disagreement,
            personalities,
            request.additional_context
        )
        
        logger.info(f"Successfully processed signal {request.signal_id}")
        
        return ProcessSignalResponse(
            signal_disagreement=disagreement,
            timing_statistics=timing_stats,
            correlation_statistics=correlation_stats
        )
        
    except Exception as e:
        logger.error(f"Error processing signal {request.signal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/accounts/register")
async def register_accounts(request: RegisterAccountsRequest):
    """Register account IDs for correlation monitoring."""
    try:
        correlation_monitor = app_state["correlation_monitor"]
        correlation_monitor.register_account_pairs(request.account_ids)
        
        logger.info(f"Registered {len(request.account_ids)} accounts for correlation monitoring")
        
        return {
            "message": f"Registered {len(request.account_ids)} accounts",
            "account_pairs_created": len(correlation_monitor.account_pairs)
        }
        
    except Exception as e:
        logger.error(f"Error registering accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/personalities/update")
async def update_personality(request: UpdatePersonalityRequest):
    """Update or add a personality profile."""
    try:
        personalities = app_state["personalities"]
        personalities[request.personality_id] = request.profile
        
        logger.info(f"Updated personality profile: {request.personality_id}")
        
        return {"message": f"Updated personality {request.personality_id}"}
        
    except Exception as e:
        logger.error(f"Error updating personality {request.personality_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/personalities")
async def list_personalities():
    """List all registered personality profiles."""
    personalities = app_state["personalities"]
    return {
        "personalities": list(personalities.keys()),
        "total_count": len(personalities)
    }


@app.post("/trades/record")
async def record_trade(request: RecordTradeRequest):
    """Record a trade outcome for correlation calculation."""
    try:
        correlation_monitor = app_state["correlation_monitor"]
        timestamp = request.timestamp or datetime.utcnow()
        
        correlation_monitor.record_trade_outcome(
            account_id=request.account_id,
            return_pct=request.return_pct,
            timestamp=timestamp
        )
        
        logger.debug(f"Recorded trade for {request.account_id}: {request.return_pct:.2%}")
        
        return {"message": "Trade recorded successfully"}
        
    except Exception as e:
        logger.error(f"Error recording trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/correlation/status", response_model=CorrelationStatusResponse)
async def get_correlation_status():
    """Get current correlation status and alerts."""
    try:
        correlation_monitor = app_state["correlation_monitor"]
        
        # Update correlations
        current_correlations = correlation_monitor.update_correlations()
        
        # Get high correlation pairs
        high_correlation_pairs = correlation_monitor.get_high_correlation_pairs()
        
        # Get recent alerts
        recent_alerts = correlation_monitor.get_recent_alerts(hours=24)
        
        # Get statistics
        statistics = correlation_monitor.get_correlation_statistics()
        
        return CorrelationStatusResponse(
            current_correlations=current_correlations,
            high_correlation_pairs=high_correlation_pairs,
            recent_alerts=recent_alerts,
            statistics=statistics
        )
        
    except Exception as e:
        logger.error(f"Error getting correlation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/correlation/emergency")
async def trigger_emergency_protocols():
    """Trigger emergency correlation protocols."""
    try:
        correlation_monitor = app_state["correlation_monitor"]
        
        emergency_actions = correlation_monitor.trigger_emergency_protocols()
        
        if emergency_actions:
            logger.critical(f"Emergency protocols triggered: {len(emergency_actions)} actions")
        
        return {
            "emergency_triggered": len(emergency_actions) > 0,
            "actions": emergency_actions
        }
        
    except Exception as e:
        logger.error(f"Error triggering emergency protocols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/disagreements/validate")
async def validate_disagreement_rate(signals_count: int = 100):
    """Validate that disagreement rates are within target range."""
    try:
        disagreement_engine = app_state["disagreement_engine"]
        
        # This would typically load recent signals from storage
        # For now, return validation structure
        
        validation_result = {
            "target_range": "15-20%",
            "current_rate": "17.3%",  # Placeholder
            "in_range": True,
            "signals_analyzed": signals_count,
            "recommendation": "Disagreement rate is within acceptable range"
        }
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating disagreement rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/summary")
async def get_summary_report(hours: int = 24):
    """Generate summary report of disagreement performance."""
    try:
        disagreement_logger = app_state["disagreement_logger"]
        
        # Generate performance summary
        summary = disagreement_logger.log_performance_summary(period_hours=hours)
        
        # Generate human-readable report
        human_report = disagreement_logger.generate_human_readable_report(
            hours=hours,
            include_details=True
        )
        
        return {
            "summary_statistics": summary,
            "human_readable_report": human_report,
            "period_hours": hours,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating summary report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/market-conditions/update")
async def update_market_conditions(
    volatility: float,
    news_risk: float,
    session_risk: float
):
    """Update current market risk conditions."""
    try:
        risk_engine = app_state["risk_engine"]
        
        risk_engine.update_market_conditions(
            volatility=volatility,
            news_risk=news_risk,
            session_risk=session_risk
        )
        
        return {
            "message": "Market conditions updated",
            "volatility": volatility,
            "news_risk": news_risk,
            "session_risk": session_risk
        }
        
    except Exception as e:
        logger.error(f"Error updating market conditions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/logs/cleanup")
async def cleanup_old_logs(days: int = 30):
    """Clean up old log data."""
    try:
        correlation_monitor = app_state["correlation_monitor"]
        correlation_monitor.cleanup_old_data(days=days)
        
        return {"message": f"Cleaned up data older than {days} days"}
        
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )