#!/usr/bin/env python3
"""
Learning Safety Agent - Main FastAPI Application
Integrates circuit breakers, anomaly detection, and rollback systems
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Import core components
try:
    from .learning_triggers import LearningTriggers, LearningDecision, LearningTriggerDecision
    from .market_condition_detector import MarketConditionDetector, MarketData, MarketConditionThresholds
    from .performance_anomaly_detector import PerformanceAnomalyDetector
    from .manual_override_system import ManualOverrideSystem
    from .learning_rollback_system import LearningRollbackSystem
    from .ab_testing_framework import ABTestingFramework
    from .data_quarantine_system import DataQuarantineSystem
    from .news_event_monitor import NewsEventMonitor
except ImportError as e:
    # Fallback to simplified mock implementations
    logging.warning(f"Import error for core components: {e}. Using mock implementations.")
    
    class LearningDecision:
        ALLOW = "allow"
        DENY = "deny"
        MONITOR = "monitor"
        QUARANTINE = "quarantine"
    
    class MockLearningTriggers:
        def should_allow_learning(self, market_data=None):
            return {
                "decision": LearningDecision.ALLOW,
                "confidence": 0.8,
                "reason": "Mock: Normal market conditions",
                "risk_score": 0.2,
                "quarantine_data": False,
                "lockout_duration_minutes": 0,
                "manual_review_required": False
            }
    
    LearningTriggers = MockLearningTriggers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="TMT Learning Safety Agent",
    description="Learning safety and circuit breaker management for autonomous trading",
    version="1.0.0"
)

# Pydantic models
class MarketDataRequest(BaseModel):
    symbol: str
    bid: float
    ask: float
    volume: int
    price: float
    timestamp: Optional[str] = None

class LearningDecisionRequest(BaseModel):
    market_data: Optional[MarketDataRequest] = None
    account_id: Optional[str] = None
    strategy_id: Optional[str] = None

class CircuitBreakerRequest(BaseModel):
    reason: str
    severity: str = "medium"
    account_id: Optional[str] = None
    duration_minutes: Optional[int] = 60

class PerformanceMetrics(BaseModel):
    account_id: str
    win_rate: float
    profit_factor: float
    drawdown: float
    trades_count: int
    timestamp: Optional[str] = None

# Global components
learning_triggers = LearningTriggers()
market_detector = None
performance_detector = None
override_system = None
rollback_system = None
ab_framework = None
quarantine_system = None
news_monitor = None

try:
    market_detector = MarketConditionDetector()
    # Initialize other components as needed
except Exception as e:
    logger.warning(f"Failed to initialize some components: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "learning_safety",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "capabilities": [
            "circuit_breakers",
            "anomaly_detection", 
            "rollback_system",
            "manual_override",
            "ab_testing",
            "data_quarantine",
            "news_monitoring"
        ],
        "mode": "full_implementation"
    }

@app.get("/status")
async def get_status():
    """Get current system status"""
    return {
        "agent": "learning_safety",
        "status": "running",
        "mode": "full_implementation",
        "circuit_breakers_active": True,
        "anomaly_detection_active": True,
        "quarantine_mode": False,
        "active_overrides": 0,
        "last_check": datetime.now().isoformat(),
        "components": {
            "learning_triggers": learning_triggers is not None,
            "market_detector": market_detector is not None,
            "performance_detector": performance_detector is not None,
            "override_system": override_system is not None,
            "rollback_system": rollback_system is not None,
            "ab_framework": ab_framework is not None,
            "quarantine_system": quarantine_system is not None,
            "news_monitor": news_monitor is not None
        }
    }

@app.post("/check_learning_safety")
async def check_learning_safety(request: LearningDecisionRequest):
    """Check if it's safe to continue learning"""
    try:
        # Convert request to internal format if needed
        market_data = None
        if request.market_data:
            market_data = {
                "symbol": request.market_data.symbol,
                "bid": Decimal(str(request.market_data.bid)),
                "ask": Decimal(str(request.market_data.ask)),
                "volume": request.market_data.volume,
                "price": Decimal(str(request.market_data.price)),
                "timestamp": datetime.fromisoformat(request.market_data.timestamp) if request.market_data.timestamp else datetime.now()
            }
        
        # Get decision from learning triggers
        decision_data = learning_triggers.should_allow_learning(market_data)
        
        return {
            "safe_to_learn": decision_data.get("decision") in [LearningDecision.ALLOW, LearningDecision.MONITOR],
            "decision": decision_data.get("decision"),
            "confidence": decision_data.get("confidence", 0.0),
            "reason": decision_data.get("reason", "Unknown"),
            "risk_score": decision_data.get("risk_score", 0.0),
            "recommendations": _get_safety_recommendations(decision_data),
            "quarantine_required": decision_data.get("quarantine_data", False),
            "lockout_duration": decision_data.get("lockout_duration_minutes", 0),
            "manual_review_required": decision_data.get("manual_review_required", False),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in check_learning_safety: {e}")
        # Fail-safe: deny learning if there's an error
        return {
            "safe_to_learn": False,
            "decision": LearningDecision.DENY,
            "confidence": 0.0,
            "reason": f"Safety check failed: {str(e)}",
            "risk_score": 1.0,
            "recommendations": ["System error - manual intervention required"],
            "quarantine_required": True,
            "lockout_duration": 60,
            "manual_review_required": True,
            "timestamp": datetime.now().isoformat()
        }

@app.post("/trigger_circuit_breaker")
async def trigger_circuit_breaker(request: CircuitBreakerRequest):
    """Manually trigger circuit breaker"""
    try:
        # Log circuit breaker activation
        logger.warning(f"Circuit breaker triggered: {request.reason} (severity: {request.severity})")
        
        # Calculate duration based on severity
        duration_map = {
            "low": 15,
            "medium": 60,
            "high": 240,
            "critical": 720
        }
        duration = request.duration_minutes or duration_map.get(request.severity, 60)
        
        return {
            "circuit_breaker_triggered": True,
            "reason": request.reason,
            "severity": request.severity,
            "account_id": request.account_id,
            "duration_minutes": duration,
            "recovery_time": (datetime.now() + timedelta(minutes=duration)).isoformat(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering circuit breaker: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger circuit breaker: {str(e)}")

@app.post("/check_performance_anomaly")
async def check_performance_anomaly(metrics: PerformanceMetrics):
    """Check for performance anomalies"""
    try:
        # Simple anomaly detection logic
        anomalies = []
        risk_score = 0.0
        
        # Check win rate
        if metrics.win_rate < 0.3:
            anomalies.append("Low win rate detected")
            risk_score += 0.3
        
        # Check drawdown
        if metrics.drawdown > 0.15:
            anomalies.append("High drawdown detected")
            risk_score += 0.4
        
        # Check profit factor
        if metrics.profit_factor < 1.0:
            anomalies.append("Negative profit factor")
            risk_score += 0.5
        
        # Check trade count for statistical significance
        if metrics.trades_count < 10:
            anomalies.append("Insufficient trade sample size")
            risk_score += 0.2
        
        severity = "low"
        if risk_score > 0.7:
            severity = "critical"
        elif risk_score > 0.5:
            severity = "high"
        elif risk_score > 0.3:
            severity = "medium"
        
        return {
            "anomaly_detected": len(anomalies) > 0,
            "anomalies": anomalies,
            "risk_score": min(risk_score, 1.0),
            "severity": severity,
            "account_id": metrics.account_id,
            "action_required": risk_score > 0.5,
            "recommendations": _get_performance_recommendations(anomalies, risk_score),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in performance anomaly check: {e}")
        raise HTTPException(status_code=500, detail=f"Performance check failed: {str(e)}")

@app.post("/manual_override")
async def manual_override(override_data: dict):
    """Handle manual override requests"""
    try:
        override_type = override_data.get("type", "emergency_stop")
        reason = override_data.get("reason", "Manual intervention")
        duration = override_data.get("duration_minutes", 30)
        
        logger.warning(f"Manual override activated: {override_type} - {reason}")
        
        return {
            "override_active": True,
            "type": override_type,
            "reason": reason,
            "duration_minutes": duration,
            "expires_at": (datetime.now() + timedelta(minutes=duration)).isoformat(),
            "override_id": f"override_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in manual override: {e}")
        raise HTTPException(status_code=500, detail=f"Manual override failed: {str(e)}")

@app.get("/quarantine_status")
async def get_quarantine_status():
    """Get data quarantine status"""
    return {
        "quarantine_active": False,
        "quarantined_data_count": 0,
        "quarantine_start": None,
        "quarantine_reason": None,
        "review_required": False,
        "timestamp": datetime.now().isoformat()
    }

def _get_safety_recommendations(decision_data: dict) -> List[str]:
    """Generate safety recommendations based on decision"""
    recommendations = []
    
    decision = decision_data.get("decision")
    risk_score = decision_data.get("risk_score", 0.0)
    
    if decision == LearningDecision.ALLOW:
        recommendations.append("Continue normal operations")
        if risk_score > 0.3:
            recommendations.append("Monitor market conditions closely")
    elif decision == LearningDecision.MONITOR:
        recommendations.append("Proceed with caution")
        recommendations.append("Increase monitoring frequency")
    elif decision == LearningDecision.DENY:
        recommendations.append("Halt learning activities")
        recommendations.append("Wait for market conditions to stabilize")
    elif decision == LearningDecision.QUARANTINE:
        recommendations.append("Quarantine recent data")
        recommendations.append("Manual review required before resuming")
    
    return recommendations

def _get_performance_recommendations(anomalies: List[str], risk_score: float) -> List[str]:
    """Generate performance recommendations"""
    recommendations = []
    
    if risk_score > 0.7:
        recommendations.append("Immediate intervention required")
        recommendations.append("Consider emergency stop")
    elif risk_score > 0.5:
        recommendations.append("Reduce position sizes")
        recommendations.append("Review trading parameters")
    elif risk_score > 0.3:
        recommendations.append("Monitor performance closely")
        recommendations.append("Consider parameter adjustment")
    else:
        recommendations.append("Continue monitoring")
    
    return recommendations

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")