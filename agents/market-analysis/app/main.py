#!/usr/bin/env python3
"""
Market Analysis Agent - FastAPI Service
Provides real-time market analysis and signal generation
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .market_state_agent import MarketStateAgent
from .signals.signal_quality_analyzer import SignalQualityAnalyzer, SignalQualityMonitor
from .signals.confidence_threshold_optimizer import ConfidenceThresholdOptimizer
from .wyckoff.enhanced_pattern_detector import EnhancedWyckoffDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market_analysis_service")

# Global market analysis agent and optimization components
market_agent = None
signal_quality_analyzer = None
threshold_optimizer = None
enhanced_detector = None
quality_monitor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize market analysis agent on startup"""
    global market_agent, signal_quality_analyzer, threshold_optimizer, enhanced_detector, quality_monitor
    
    logger.info("🚀 Starting Market Analysis Service")
    
    # Initialize market state agent
    market_agent = MarketStateAgent()
    
    # Initialize optimization components
    signal_quality_analyzer = SignalQualityAnalyzer()
    threshold_optimizer = ConfidenceThresholdOptimizer()
    enhanced_detector = EnhancedWyckoffDetector()
    quality_monitor = SignalQualityMonitor()
    
    # Start market monitoring in background
    asyncio.create_task(market_agent.start_monitoring())
    
    logger.info("✅ Market Analysis Service with optimization capabilities ready")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down Market Analysis Service")

# Initialize FastAPI app
app = FastAPI(
    title="TMT Market Analysis Service",
    description="Real-time market analysis and signal generation for trading system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if market_agent is None:
            return {
                "status": "starting",
                "timestamp": datetime.now().isoformat(),
                "market_data_connected": False,
                "subscribed_instruments": [],
                "last_price_update": None,
                "total_signals": 0
            }
        
        # Get real status from market agent
        connected = getattr(market_agent, 'connected', False)
        signal_count = getattr(market_agent, 'signal_count', 0)
        
        market_data = getattr(market_agent, 'market_data', {})
        instruments = list(market_data.get('prices', {}).keys()) if market_data else []
        last_update = market_data.get('timestamp') if market_data else None
        
        status = "healthy" if connected else "degraded"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int((datetime.now() - datetime.now()).total_seconds()) if connected else 0,
            "market_data_connected": connected,
            "subscribed_instruments": instruments,
            "last_price_update": last_update.isoformat() if last_update else None,
            "total_signals": signal_count,
            "oanda_configured": bool(os.getenv("OANDA_API_KEY")),
            "market_state": getattr(market_agent, 'current_state', 'unknown')
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "market_data_connected": False,
            "subscribed_instruments": [],
            "last_price_update": None,
            "total_signals": 0
        }

@app.get("/market-data")
async def get_market_data():
    """Get current market data"""
    try:
        if market_agent is None or not hasattr(market_agent, 'market_data'):
            raise HTTPException(status_code=503, detail="Market data not available")
        
        return market_agent.market_data
        
    except Exception as e:
        logger.error(f"Market data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market-state")
async def get_market_state():
    """Get current market state analysis"""
    try:
        if market_agent is None:
            raise HTTPException(status_code=503, detail="Market agent not available")
        
        return {
            "current_state": getattr(market_agent, 'current_state', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.8,  # Basic confidence for real-time analysis
            "analysis": getattr(market_agent, 'market_data', {}).get('volatility_analysis', {})
        }
        
    except Exception as e:
        logger.error(f"Market state error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/{instrument}")
async def analyze_instrument(instrument: str):
    """Analyze specific instrument"""
    try:
        if market_agent is None:
            raise HTTPException(status_code=503, detail="Market agent not available")
        
        # Get instrument data
        market_data = getattr(market_agent, 'market_data', {})
        prices = market_data.get('prices', {})
        
        if instrument not in prices:
            raise HTTPException(status_code=404, detail=f"Instrument {instrument} not found")
        
        price_data = prices[instrument]
        spread = market_data.get('spreads', {}).get(instrument, 0)
        
        return {
            "instrument": instrument,
            "analysis": {
                "current_price": price_data['mid'],
                "bid": price_data['bid'],
                "ask": price_data['ask'],
                "spread": spread,
                "spread_pips": (spread / price_data['mid']) * 10000,
                "market_state": market_data.get('market_state', 'unknown'),
                "execution_quality": "good" if spread < price_data['mid'] * 0.0002 else "fair",
                "timestamp": price_data['time']
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error for {instrument}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instruments")
async def get_supported_instruments():
    """Get list of supported instruments"""
    return {
        "instruments": ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", "NZD_USD", "USD_CAD"],
        "total": 7,
        "actively_monitored": len(getattr(market_agent, 'market_data', {}).get('prices', {}))
    }

@app.post("/emergency-stop")
async def emergency_stop():
    """Emergency stop market analysis"""
    try:
        logger.critical("🚨 Emergency stop requested for market analysis")
        
        if market_agent:
            market_agent.connected = False
            
        return {
            "status": "stopped",
            "timestamp": datetime.now().isoformat(),
            "message": "Market analysis emergency stopped"
        }
        
    except Exception as e:
        logger.error(f"Emergency stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimization/analyze")
async def analyze_signal_performance():
    """Analyze current signal performance and identify optimization opportunities"""
    try:
        if signal_quality_analyzer is None:
            raise HTTPException(status_code=503, detail="Signal quality analyzer not initialized")
        
        # Mock data for demonstration - in production this would load real data
        historical_signals = []
        execution_data = []
        
        # Generate mock data if no real data available
        if not historical_signals:
            logger.info("Using mock data for analysis demonstration")
            historical_signals = _generate_demo_signals()
            execution_data = _generate_demo_executions(historical_signals)
        
        # Run analysis
        analysis_result = await signal_quality_analyzer.analyze_signal_performance(
            historical_signals, execution_data
        )
        
        return {
            "analysis_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "analysis_result": analysis_result
        }
        
    except Exception as e:
        logger.error(f"Signal performance analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimization/optimize-threshold")
async def optimize_confidence_threshold():
    """Optimize confidence threshold based on historical performance"""
    try:
        if threshold_optimizer is None:
            raise HTTPException(status_code=503, detail="Threshold optimizer not initialized")
        
        # Load historical data
        historical_signals = _generate_demo_signals()
        execution_data = _generate_demo_executions(historical_signals)
        
        # Run optimization
        optimization_result = await threshold_optimizer.optimize_threshold(
            historical_signals, execution_data
        )
        
        return {
            "optimization_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "recommendation": {
                "current_threshold": optimization_result.current_threshold,
                "recommended_threshold": optimization_result.recommended_threshold,
                "expected_improvement": optimization_result.expected_improvement,
                "confidence_level": optimization_result.confidence_level,
                "implementation_priority": optimization_result.implementation_priority,
                "reasoning": optimization_result.reasoning
            }
        }
        
    except Exception as e:
        logger.error(f"Threshold optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimization/implement")
async def implement_optimization(threshold: float, dry_run: bool = False):
    """Implement optimized confidence threshold"""
    try:
        if not 40.0 <= threshold <= 95.0:
            raise HTTPException(status_code=400, detail="Threshold must be between 40.0 and 95.0")
        
        if threshold_optimizer is None:
            raise HTTPException(status_code=503, detail="Threshold optimizer not initialized")
        
        # Implement threshold change
        implementation_result = await threshold_optimizer.implement_threshold_change(
            new_threshold=threshold,
            change_reason=f"API implementation {'(dry_run)' if dry_run else ''}"
        )
        
        return {
            "implementation_status": "success" if not dry_run else "dry_run_completed",
            "timestamp": datetime.now().isoformat(),
            "changes": implementation_result,
            "monitoring_recommendation": "Monitor performance for 24-48 hours"
        }
        
    except Exception as e:
        logger.error(f"Optimization implementation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/optimization/monitor")
async def monitor_optimization_performance(hours: int = 24):
    """Monitor optimization performance"""
    try:
        if threshold_optimizer is None:
            raise HTTPException(status_code=503, detail="Threshold optimizer not initialized")
        
        # Load recent data for monitoring
        recent_signals = _generate_demo_signals()[-20:]  # Last 20 signals
        recent_executions = _generate_demo_executions(recent_signals)[-5:]  # Last 5 executions
        
        # Monitor performance
        monitoring_result = await threshold_optimizer.monitor_threshold_performance(
            recent_signals, recent_executions, hours
        )
        
        return {
            "monitoring_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "monitoring_result": monitoring_result
        }
        
    except Exception as e:
        logger.error(f"Optimization monitoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/optimization/status")
async def get_optimization_status():
    """Get current optimization status and configuration"""
    try:
        status = {
            "optimization_capabilities": {
                "signal_quality_analyzer": signal_quality_analyzer is not None,
                "threshold_optimizer": threshold_optimizer is not None,
                "enhanced_detector": enhanced_detector is not None,
                "quality_monitor": quality_monitor is not None
            },
            "current_configuration": {},
            "optimization_history": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Get current threshold if optimizer is available
        if threshold_optimizer:
            status["current_configuration"]["confidence_threshold"] = threshold_optimizer.current_optimal_threshold
            status["optimization_history"] = threshold_optimizer.optimization_history[-5:]  # Last 5 optimizations
        
        # Get analyzer summary if available
        if signal_quality_analyzer and signal_quality_analyzer.cached_results:
            analysis_summary = signal_quality_analyzer.cached_results.get('data_summary', {})
            status["current_performance"] = {
                "conversion_rate": analysis_summary.get('conversion_rate', 0),
                "signals_analyzed": analysis_summary.get('signals_analyzed', 0),
                "analysis_period_days": analysis_summary.get('analysis_period_days', 0)
            }
        
        return status
        
    except Exception as e:
        logger.error(f"Optimization status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/optimization/report")
async def get_optimization_report():
    """Get comprehensive optimization report"""
    try:
        if signal_quality_analyzer is None:
            raise HTTPException(status_code=503, detail="Signal quality analyzer not initialized")
        
        # Generate comprehensive report
        optimization_report = await signal_quality_analyzer.get_optimization_report()
        
        return {
            "report_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "optimization_report": optimization_report
        }
        
    except Exception as e:
        logger.error(f"Optimization report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions for demo data generation
def _generate_demo_signals() -> List[Dict]:
    """Generate demo signal data for testing"""
    import numpy as np
    from datetime import datetime, timedelta
    
    signals = []
    base_date = datetime.now() - timedelta(days=7)
    
    # Generate 50 demo signals
    for i in range(50):
        signal_date = base_date + timedelta(hours=i*3)  # Every 3 hours
        
        # Simulate confidence distribution
        if i % 8 == 0:
            confidence = np.random.normal(82, 3)  # High confidence
        elif i % 4 == 0:
            confidence = np.random.normal(68, 4)  # Medium confidence
        else:
            confidence = np.random.normal(58, 6)  # Lower confidence
        
        confidence = max(45, min(95, confidence))
        
        signals.append({
            'signal_id': f'demo_signal_{i:03d}',
            'generated_at': signal_date,
            'symbol': 'EUR_USD',
            'confidence': confidence,
            'pattern_type': np.random.choice(['accumulation', 'spring', 'markup', 'distribution']),
            'risk_reward_ratio': np.random.normal(2.2, 0.4),
            'valid_until': signal_date + timedelta(hours=24)
        })
    
    return signals

def _generate_demo_executions(signals: List[Dict]) -> List[Dict]:
    """Generate demo execution data correlated with signal quality"""
    import numpy as np
    
    executions = []
    
    for signal in signals:
        confidence = signal['confidence']
        
        # Higher confidence = higher execution probability
        if confidence >= 75:
            execution_prob = 0.30  # 30% for high confidence
        elif confidence >= 65:
            execution_prob = 0.15  # 15% for medium confidence
        else:
            execution_prob = 0.05  # 5% for low confidence
        
        if np.random.random() < execution_prob:
            # Generate realistic P&L based on confidence
            base_profit = (confidence - 60) * 0.8
            profit = np.random.normal(base_profit, 12)
            
            executions.append({
                'signal_id': signal['signal_id'],
                'executed_at': signal['generated_at'] + timedelta(minutes=np.random.randint(10, 180)),
                'pnl': profit,
                'symbol': signal['symbol'],
                'execution_price': 1.0500 + np.random.normal(0, 0.0015),
                'position_size': 1000
            })
    
    return executions

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )