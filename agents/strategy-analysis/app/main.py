"""
FastAPI application for Strategy Performance Analysis Agent.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import asyncio

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models import (
    TradingStrategy, StrategyPerformance, UnderperformanceDetection,
    StrategyCorrelationAnalysis, StrategyEffectivenessReport
)
from .strategy_performance_analyzer import StrategyPerformanceAnalyzer
from .correlation_analyzer import CorrelationAnalyzer
from .underperformance_detector import UnderperformanceDetector
from .report_generator import ReportGenerator
from .strategy_controller import StrategyController
from .strategy_lifecycle import StrategyLifecycleManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Strategy Performance Analysis Agent",
    description="Comprehensive strategy performance analysis and management system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
performance_analyzer = StrategyPerformanceAnalyzer()
correlation_analyzer = CorrelationAnalyzer()
underperformance_detector = UnderperformanceDetector()
report_generator = ReportGenerator()
strategy_controller = StrategyController()
lifecycle_manager = StrategyLifecycleManager()


# Request/Response Models
class AnalyzePerformanceRequest(BaseModel):
    strategy_id: str = Field(description="Strategy ID to analyze")
    evaluation_period_days: int = Field(default=90, description="Evaluation period in days")


class CorrelationAnalysisRequest(BaseModel):
    strategy_ids: List[str] = Field(description="List of strategy IDs to analyze")
    analysis_period_days: int = Field(default=90, description="Analysis period in days")


class UnderperformanceCheckRequest(BaseModel):
    strategy_id: str = Field(description="Strategy ID to check")


class GenerateReportRequest(BaseModel):
    strategy_ids: List[str] = Field(description="List of strategy IDs for report")
    report_date: Optional[datetime] = Field(default=None, description="Report date (defaults to current)")


class StrategyControlRequest(BaseModel):
    strategy_id: str = Field(description="Strategy ID")
    user_id: str = Field(description="User performing the action")
    reason: str = Field(description="Reason for the action")
    override_checks: bool = Field(default=False, description="Override safety checks")


class AllocationUpdateRequest(BaseModel):
    strategy_id: str = Field(description="Strategy ID")
    new_allocation: Decimal = Field(description="New allocation percentage (0-1)")
    user_id: str = Field(description="User performing the action")
    reason: str = Field(description="Reason for the change")


class ConfigurationUpdateRequest(BaseModel):
    strategy_id: str = Field(description="Strategy ID")
    configuration_updates: Dict = Field(description="Configuration changes")
    user_id: str = Field(description="User performing the action")
    reason: str = Field(description="Reason for the changes")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "strategy-performance-analysis",
        "version": "1.0.0"
    }


# Strategy Performance Analysis Endpoints
@app.post("/analyze/performance", response_model=StrategyPerformance)
async def analyze_strategy_performance(request: AnalyzePerformanceRequest):
    """Analyze comprehensive strategy performance."""
    try:
        evaluation_period = timedelta(days=request.evaluation_period_days)
        performance = await performance_analyzer.analyze_strategy_performance(
            request.strategy_id, evaluation_period
        )
        return performance
    except Exception as e:
        logger.error(f"Error analyzing strategy performance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze/correlation", response_model=StrategyCorrelationAnalysis)
async def analyze_strategy_correlations(request: CorrelationAnalysisRequest):
    """Analyze correlations between strategies."""
    try:
        # In production, would retrieve actual strategy objects
        # For now, create mock strategies for the analysis
        strategies = await _get_strategies_by_ids(request.strategy_ids)
        
        analysis_period = timedelta(days=request.analysis_period_days)
        correlation_analysis = await correlation_analyzer.analyze_strategy_correlations(
            strategies, analysis_period
        )
        return correlation_analysis
    except Exception as e:
        logger.error(f"Error analyzing correlations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Correlation analysis failed: {str(e)}")


@app.post("/analyze/underperformance")
async def check_underperformance(request: UnderperformanceCheckRequest):
    """Check strategy for underperformance."""
    try:
        # In production, would retrieve actual strategy object
        strategy = await _get_strategy_by_id(request.strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        detection = await underperformance_detector.detect_underperformance(strategy)
        
        if detection:
            return {
                "underperformance_detected": True,
                "detection": detection
            }
        else:
            return {
                "underperformance_detected": False,
                "message": "No performance issues detected"
            }
    except Exception as e:
        logger.error(f"Error checking underperformance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Underperformance check failed: {str(e)}")


@app.post("/reports/weekly", response_model=StrategyEffectivenessReport)
async def generate_weekly_report(request: GenerateReportRequest):
    """Generate weekly strategy effectiveness report."""
    try:
        # In production, would retrieve actual strategy objects
        strategies = await _get_strategies_by_ids(request.strategy_ids)
        
        report = await report_generator.generate_weekly_report(
            strategies, request.report_date
        )
        return report
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# Strategy Control Endpoints
@app.post("/control/enable")
async def enable_strategy(request: StrategyControlRequest):
    """Enable a strategy."""
    try:
        strategy = await _get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        result = await strategy_controller.enable_strategy(
            strategy, request.user_id, request.reason, request.override_checks
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Enable failed'))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Enable operation failed: {str(e)}")


@app.post("/control/disable")
async def disable_strategy(request: StrategyControlRequest):
    """Disable a strategy."""
    try:
        strategy = await _get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        result = await strategy_controller.disable_strategy(
            strategy, request.user_id, request.reason
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Disable failed'))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Disable operation failed: {str(e)}")


@app.post("/control/allocation")
async def update_allocation(request: AllocationUpdateRequest):
    """Update strategy allocation."""
    try:
        strategy = await _get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        result = await strategy_controller.update_allocation(
            strategy, request.new_allocation, request.user_id, request.reason
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Allocation update failed'))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating allocation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Allocation update failed: {str(e)}")


@app.post("/control/configuration")
async def update_configuration(request: ConfigurationUpdateRequest):
    """Update strategy configuration."""
    try:
        strategy = await _get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        result = await strategy_controller.update_configuration(
            strategy, request.configuration_updates, request.user_id, request.reason
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Configuration update failed'))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")


@app.post("/control/emergency-stop")
async def emergency_stop_strategy(request: StrategyControlRequest):
    """Emergency stop for a strategy."""
    try:
        strategy = await _get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        result = await strategy_controller.emergency_stop_strategy(
            strategy, request.user_id, request.reason
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Emergency stop failed'))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in emergency stop: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")


@app.get("/control/audit-log")
async def get_audit_log(
    strategy_id: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get control action audit log."""
    try:
        audit_log = await strategy_controller.get_control_audit_log(
            strategy_id, user_id, start_date, end_date
        )
        return {"audit_log": audit_log}
    except Exception as e:
        logger.error(f"Error retrieving audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit log retrieval failed: {str(e)}")


# Lifecycle Management Endpoints
@app.post("/lifecycle/activate")
async def activate_strategy(request: StrategyControlRequest):
    """Activate a new strategy."""
    try:
        strategy = await _get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        success = await lifecycle_manager.activate_strategy(strategy)
        
        if not success:
            raise HTTPException(status_code=400, detail="Strategy activation failed validation")
        
        return {"success": True, "message": "Strategy activated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Activation failed: {str(e)}")


@app.post("/lifecycle/suspend")
async def suspend_strategy(request: StrategyControlRequest):
    """Suspend a strategy."""
    try:
        strategy = await _get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        success = await lifecycle_manager.suspend_strategy(strategy, request.reason)
        
        if not success:
            raise HTTPException(status_code=400, detail="Strategy suspension failed")
        
        return {"success": True, "message": "Strategy suspended successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suspending strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Suspension failed: {str(e)}")


@app.get("/lifecycle/summary/{strategy_id}")
async def get_lifecycle_summary(strategy_id: str):
    """Get strategy lifecycle summary."""
    try:
        strategy = await _get_strategy_by_id(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        summary = await lifecycle_manager.get_strategy_lifecycle_summary(strategy)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lifecycle summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary retrieval failed: {str(e)}")


# Background Tasks
@app.post("/tasks/auto-analysis")
async def trigger_auto_analysis(background_tasks: BackgroundTasks):
    """Trigger automated analysis of all strategies."""
    background_tasks.add_task(run_automated_analysis)
    return {"message": "Automated analysis triggered"}


async def run_automated_analysis():
    """Run automated analysis for all strategies."""
    try:
        logger.info("Starting automated strategy analysis")
        
        # In production, would get all active strategies
        all_strategies = await _get_all_strategies()
        
        for strategy in all_strategies:
            # Check for underperformance
            detection = await underperformance_detector.detect_underperformance(strategy)
            
            if detection:
                logger.warning(f"Underperformance detected for strategy {strategy.strategy_id}")
                
                # Auto-suspend if critical
                if detection.automatic_actions.suspension_triggered:
                    await lifecycle_manager.suspend_strategy(
                        strategy, 
                        f"Auto-suspended: {detection.severity.level.value} underperformance"
                    )
            
            # Check auto-suspension triggers
            suspension_reason = await lifecycle_manager.check_auto_suspension_triggers(strategy)
            if suspension_reason:
                await lifecycle_manager.suspend_strategy(strategy, suspension_reason)
        
        logger.info("Completed automated strategy analysis")
    
    except Exception as e:
        logger.error(f"Error in automated analysis: {str(e)}")


# Helper functions (would be replaced with actual data access in production)
async def _get_strategy_by_id(strategy_id: str) -> Optional[TradingStrategy]:
    """Get strategy by ID - mock implementation."""
    # In production, would query database/service
    return None


async def _get_strategies_by_ids(strategy_ids: List[str]) -> List[TradingStrategy]:
    """Get strategies by IDs - mock implementation."""
    # In production, would query database/service
    return []


async def _get_all_strategies() -> List[TradingStrategy]:
    """Get all strategies - mock implementation."""
    # In production, would query database/service
    return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)