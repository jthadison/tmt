"""
Continuous Improvement Pipeline Service

FastAPI service for the continuous improvement system that orchestrates
systematic testing, validation, and deployment of trading improvements.

This service provides REST APIs for:
- Pipeline management and monitoring
- Test lifecycle management  
- Manual approvals and oversight
- Performance analytics and reporting
- Emergency controls and safety mechanisms
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from .pipeline_orchestrator import ContinuousImprovementOrchestrator
from .models import (
    TestPhase, TestDecision, SuggestionStatus, Priority, RiskLevel,
    ImprovementType, ImplementationComplexity
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Optional[ContinuousImprovementOrchestrator] = None
background_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global orchestrator, background_task
    
    try:
        # Initialize orchestrator
        orchestrator = ContinuousImprovementOrchestrator()
        
        # Start pipeline
        success = await orchestrator.start_pipeline()
        if not success:
            raise Exception("Failed to start improvement pipeline")
        
        # Start background execution loop
        background_task = asyncio.create_task(pipeline_execution_loop())
        
        logger.info("Continuous Improvement Service started successfully")
        yield
        
    finally:
        # Cleanup
        if background_task:
            background_task.cancel()
            try:
                await background_task
            except asyncio.CancelledError:
                pass
        
        if orchestrator:
            await orchestrator.stop_pipeline()
        
        logger.info("Continuous Improvement Service stopped")


# FastAPI app with lifecycle management
app = FastAPI(
    title="Continuous Improvement Pipeline",
    description="Systematic testing and deployment of trading improvements",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models for API requests/responses

class PipelineStatusResponse(BaseModel):
    """Pipeline status response"""
    pipeline_id: str
    running: bool
    cycle_count: int
    last_cycle: Optional[datetime]
    improvements_in_testing: int
    improvements_in_rollout: int
    successful_deployments: int
    rollbacks: int
    pending_approvals: int
    pipeline_health: float
    success_rate: float


class ActiveTestResponse(BaseModel):
    """Active test response"""
    test_id: str
    name: str
    phase: str
    start_date: datetime
    expected_completion: Optional[datetime]
    improvement_type: str
    risk_level: Optional[str] = None
    progress_percentage: Optional[float] = None


class ImprovementSuggestionResponse(BaseModel):
    """Improvement suggestion response"""
    suggestion_id: str
    title: str
    description: str
    suggestion_type: str
    priority: str
    priority_score: float
    risk_level: str
    expected_impact: str
    status: str
    timestamp: datetime


class CreateSuggestionRequest(BaseModel):
    """Request to create improvement suggestion"""
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Detailed description")
    rationale: str = Field(..., description="Why this improvement is needed")
    suggestion_type: str = Field(..., description="Type of improvement")
    category: str = Field(..., description="Category or component affected")
    expected_impact: str = Field(default="moderate", description="Expected impact level")
    risk_level: str = Field(default="medium", description="Risk assessment")
    implementation_effort: str = Field(default="medium", description="Implementation complexity")
    priority: str = Field(default="medium", description="Priority level")


class ApproveTestRequest(BaseModel):
    """Request to approve test advancement"""
    approver: str = Field(..., description="Name/ID of approver")
    notes: str = Field(default="", description="Approval notes")


class EmergencyStopRequest(BaseModel):
    """Request for emergency test stop"""
    reason: str = Field(..., description="Reason for emergency stop")
    authorized_by: str = Field(..., description="Authorization source")


class CycleExecutionRequest(BaseModel):
    """Request to execute improvement cycle"""
    force_execution: bool = Field(default=False, description="Force execution even if recent cycle")


# Dependency to get orchestrator
def get_orchestrator() -> ContinuousImprovementOrchestrator:
    """Get orchestrator instance"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Improvement pipeline not initialized")
    return orchestrator


# Background execution loop
async def pipeline_execution_loop():
    """Background loop for continuous improvement execution"""
    global orchestrator
    
    cycle_interval = timedelta(minutes=30)  # Execute every 30 minutes
    
    while True:
        try:
            if orchestrator:
                logger.info("Executing scheduled improvement cycle")
                results = await orchestrator.execute_improvement_cycle()
                
                if not results.success:
                    logger.error(f"Improvement cycle failed: {results.summary}")
                else:
                    logger.info(f"Improvement cycle completed: {results.summary}")
            
            # Wait for next cycle
            await asyncio.sleep(cycle_interval.total_seconds())
            
        except asyncio.CancelledError:
            logger.info("Pipeline execution loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in pipeline execution loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error


# API Endpoints

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Continuous Improvement Pipeline",
        "version": "1.0.0",
        "status": "operational",
        "description": "Systematic testing and deployment of trading improvements",
        "endpoints": {
            "status": "/status",
            "tests": "/tests",
            "suggestions": "/suggestions",
            "execute": "/execute-cycle",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if not orchestrator:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "reason": "Orchestrator not initialized"}
            )
        
        status = await orchestrator.get_pipeline_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "pipeline_running": status.get('running', False),
            "cycle_count": status.get('cycle_count', 0),
            "last_cycle": status.get('last_cycle')
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": str(e)}
        )


@app.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)):
    """Get comprehensive pipeline status"""
    try:
        status_data = await orch.get_pipeline_status()
        
        return PipelineStatusResponse(
            pipeline_id=status_data['pipeline_id'],
            running=status_data['running'],
            cycle_count=status_data['cycle_count'],
            last_cycle=status_data.get('last_cycle'),
            improvements_in_testing=status_data['status']['improvements_in_testing'],
            improvements_in_rollout=status_data['status']['improvements_in_rollout'],
            successful_deployments=status_data['status']['successful_deployments'],
            rollbacks=status_data['status']['rollbacks'],
            pending_approvals=status_data['status']['pending_approvals'],
            pipeline_health=status_data['status'].get('pipeline_health', 100.0),
            success_rate=status_data['metrics']['improvement_success_rate']
        )
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tests", response_model=List[ActiveTestResponse])
async def get_active_tests(orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)):
    """Get list of active improvement tests"""
    try:
        tests = await orch.get_active_tests()
        
        return [
            ActiveTestResponse(
                test_id=test['test_id'],
                name=test['name'],
                phase=test['phase'],
                start_date=test['start_date'],
                expected_completion=test.get('expected_completion'),
                improvement_type=test['improvement_type'],
                progress_percentage=_calculate_progress_percentage(test)
            )
            for test in tests
        ]
    except Exception as e:
        logger.error(f"Failed to get active tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tests/{test_id}")
async def get_test_details(test_id: str, orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)):
    """Get detailed information about a specific test"""
    try:
        # Find test in orchestrator
        test = None
        for active_test in orch.pipeline.active_improvements:
            if active_test.test_id == test_id:
                test = active_test
                break
        
        if not test:
            raise HTTPException(status_code=404, detail="Test not found")
        
        # Build detailed response
        response = {
            "test_id": test.test_id,
            "name": test.name,
            "description": test.description,
            "hypothesis": test.hypothesis,
            "current_phase": test.current_phase.value,
            "improvement_type": test.improvement_type.value,
            "start_date": test.start_date,
            "current_stage_start": test.current_stage_start,
            "expected_completion": test.expected_completion,
            "actual_completion": test.actual_completion,
            "risk_assessment": test.risk_assessment,
            "implementation_complexity": test.implementation_complexity.value,
            "human_review_required": test.human_review_required,
            "rollback_reason": test.rollback_reason
        }
        
        # Add group information if available
        if test.control_group:
            response["control_group"] = {
                "accounts": test.control_group.accounts,
                "allocation_percentage": float(test.control_group.allocation_percentage),
                "trades_completed": test.control_group.trades_completed
            }
        
        if test.treatment_group:
            response["treatment_group"] = {
                "accounts": test.treatment_group.accounts,
                "allocation_percentage": float(test.treatment_group.allocation_percentage),
                "trades_completed": test.treatment_group.trades_completed,
                "changes_count": len(test.treatment_group.changes)
            }
        
        # Add results if available
        if test.shadow_results:
            response["shadow_results"] = {
                "validation_passed": test.shadow_results.validation_passed,
                "total_signals": test.shadow_results.total_signals,
                "trades_executed": test.shadow_results.trades_executed,
                "performance_gain": float(test.shadow_results.performance_gain),
                "risk_score": test.shadow_results.risk_score,
                "recommendation": test.shadow_results.recommendation
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get test details for {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/suggestions", response_model=List[ImprovementSuggestionResponse])
async def get_improvement_suggestions(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)
):
    """Get improvement suggestions with optional filtering"""
    try:
        suggestions = orch.pipeline.pending_suggestions
        
        # Apply filters
        if status:
            suggestions = [s for s in suggestions if s.status.value == status]
        
        if priority:
            suggestions = [s for s in suggestions if s.priority.value == priority]
        
        # Sort by priority score and limit
        suggestions = sorted(suggestions, key=lambda s: s.priority_score, reverse=True)[:limit]
        
        return [
            ImprovementSuggestionResponse(
                suggestion_id=suggestion.suggestion_id,
                title=suggestion.title,
                description=suggestion.description,
                suggestion_type=suggestion.suggestion_type.value,
                priority=suggestion.priority.value,
                priority_score=suggestion.priority_score,
                risk_level=suggestion.risk_level.value,
                expected_impact=suggestion.expected_impact,
                status=suggestion.status.value,
                timestamp=suggestion.timestamp
            )
            for suggestion in suggestions
        ]
    except Exception as e:
        logger.error(f"Failed to get improvement suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/suggestions")
async def create_improvement_suggestion(
    request: CreateSuggestionRequest,
    orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)
):
    """Create a new improvement suggestion"""
    try:
        from .models import ImprovementSuggestion
        
        # Create suggestion
        suggestion = ImprovementSuggestion(
            title=request.title,
            description=request.description,
            rationale=request.rationale,
            suggestion_type=ImprovementType(request.suggestion_type),
            category=request.category,
            expected_impact=request.expected_impact,
            risk_level=RiskLevel(request.risk_level),
            implementation_effort=ImplementationComplexity(request.implementation_effort),
            priority=Priority(request.priority),
            source_type="manual_submission"
        )
        
        # Calculate priority score (simplified)
        suggestion.priority_score = _calculate_priority_score(suggestion)
        
        # Add to pipeline
        orch.pipeline.pending_suggestions.append(suggestion)
        
        logger.info(f"Created improvement suggestion: {suggestion.suggestion_id}")
        
        return {
            "suggestion_id": suggestion.suggestion_id,
            "status": "created",
            "priority_score": suggestion.priority_score,
            "message": "Improvement suggestion created successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")
    except Exception as e:
        logger.error(f"Failed to create improvement suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tests/{test_id}/approve")
async def approve_test_advancement(
    test_id: str,
    request: ApproveTestRequest,
    orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)
):
    """Approve test for advancement to next stage"""
    try:
        success = await orch.approve_test_advancement(
            test_id=test_id,
            approver=request.approver,
            notes=request.notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Test not found")
        
        return {
            "test_id": test_id,
            "status": "approved",
            "approver": request.approver,
            "timestamp": datetime.utcnow(),
            "message": "Test approved for advancement"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tests/{test_id}/emergency-stop")
async def emergency_stop_test(
    test_id: str,
    request: EmergencyStopRequest,
    orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)
):
    """Emergency stop for a test"""
    try:
        success = await orch.emergency_stop_test(
            test_id=test_id,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Test not found")
        
        logger.warning(f"Emergency stop executed for test {test_id} by {request.authorized_by}")
        
        return {
            "test_id": test_id,
            "status": "emergency_stopped",
            "reason": request.reason,
            "authorized_by": request.authorized_by,
            "timestamp": datetime.utcnow(),
            "message": "Emergency stop executed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to emergency stop test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute-cycle")
async def execute_improvement_cycle(
    request: CycleExecutionRequest,
    background_tasks: BackgroundTasks,
    orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)
):
    """Manually trigger improvement cycle execution"""
    try:
        # Check if recent cycle was executed
        if not request.force_execution and orch._last_cycle_time:
            time_since_last = datetime.utcnow() - orch._last_cycle_time
            if time_since_last < timedelta(minutes=10):
                raise HTTPException(
                    status_code=429,
                    detail=f"Recent cycle executed {time_since_last.seconds}s ago. Use force_execution=true to override."
                )
        
        # Execute cycle in background
        background_tasks.add_task(_execute_cycle_background, orch)
        
        return {
            "status": "executing",
            "message": "Improvement cycle execution started",
            "timestamp": datetime.utcnow(),
            "force_execution": request.force_execution
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute improvement cycle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_pipeline_metrics(orch: ContinuousImprovementOrchestrator = Depends(get_orchestrator)):
    """Get detailed pipeline performance metrics"""
    try:
        status = await orch.get_pipeline_status()
        
        return {
            "pipeline_metrics": status['metrics'],
            "success_rate": status['metrics']['improvement_success_rate'],
            "rollback_rate": status['metrics']['rollback_rate'],
            "average_test_duration": str(status['metrics']['average_test_duration']),
            "active_tests": status['active_tests'],
            "pending_suggestions": status['pending_suggestions'],
            "last_updated": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to get pipeline metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

def _calculate_progress_percentage(test: Dict[str, Any]) -> float:
    """Calculate test progress percentage"""
    phase = test['phase']
    
    # Simple progress calculation based on phase
    phase_progress = {
        'shadow': 20.0,
        'rollout_10': 40.0,
        'rollout_25': 60.0,
        'rollout_50': 80.0,
        'rollout_100': 95.0,
        'completed': 100.0,
        'rolled_back': 0.0
    }
    
    return phase_progress.get(phase, 0.0)


def _calculate_priority_score(suggestion) -> float:
    """Calculate priority score for suggestion"""
    # Simplified scoring algorithm
    impact_scores = {'minor': 25, 'moderate': 50, 'significant': 75, 'major': 100}
    risk_scores = {'high': 25, 'medium': 50, 'low': 100}
    effort_scores = {'high': 25, 'medium': 50, 'low': 100}
    
    impact_score = impact_scores.get(suggestion.expected_impact, 50)
    risk_score = risk_scores.get(suggestion.risk_level.value, 50)
    effort_score = effort_scores.get(suggestion.implementation_effort.value, 50)
    
    # Weighted calculation
    total_score = (impact_score * 0.4 + risk_score * 0.3 + effort_score * 0.3)
    return min(100.0, max(0.0, total_score))


async def _execute_cycle_background(orch: ContinuousImprovementOrchestrator):
    """Execute improvement cycle in background"""
    try:
        results = await orch.execute_improvement_cycle()
        logger.info(f"Manual cycle execution completed: {results.summary}")
    except Exception as e:
        logger.error(f"Background cycle execution failed: {e}")


# Entry point
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
        log_level="info"
    )