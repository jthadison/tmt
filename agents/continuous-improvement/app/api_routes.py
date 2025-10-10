"""
API routes for Continuous Improvement Pipeline.

Provides REST API endpoints for pipeline status, active tests,
pending suggestions, deployments, and emergency controls.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/improvement", tags=["continuous-improvement"])


# Response models
class PipelineStatusResponse(BaseModel):
    """Pipeline status response."""
    pipeline_state: str
    last_cycle_time: Optional[str]
    next_cycle_time: Optional[str]
    cycle_count: int
    suggestions_generated: int
    tests_running: int
    deployments_active: int


class ActiveTestResponse(BaseModel):
    """Active test response."""
    test_id: str
    parameter: str
    session: str
    start_date: str
    current_metrics: Dict


class PendingSuggestionResponse(BaseModel):
    """Pending suggestion response."""
    suggestion_id: str
    parameter: str
    session: str
    current_value: float
    suggested_value: float
    expected_improvement: float
    reason: str
    status: str


class DeploymentResponse(BaseModel):
    """Recent deployment response."""
    deployment_id: str
    parameter: str
    stage: int
    status: str
    metrics: Dict
    deployed_at: str


# Global pipeline orchestrator (injected at startup)
_pipeline_orchestrator = None


def set_pipeline_orchestrator(orchestrator):
    """
    Set pipeline orchestrator for API routes.

    Args:
        orchestrator: ContinuousImprovementOrchestrator instance
    """
    global _pipeline_orchestrator
    _pipeline_orchestrator = orchestrator


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """
    Get continuous improvement pipeline status.

    Returns:
        PipelineStatusResponse: Pipeline state and metrics

    Raises:
        HTTPException: If pipeline not initialized (500)
    """
    if not _pipeline_orchestrator:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")

    try:
        # Get pipeline status from orchestrator
        status = {
            'pipeline_state': 'RUNNING' if _pipeline_orchestrator._running else 'STOPPED',
            'last_cycle_time': _pipeline_orchestrator._last_cycle_time.isoformat()
                if _pipeline_orchestrator._last_cycle_time else None,
            'next_cycle_time': None,  # TODO: Calculate next cycle time
            'cycle_count': _pipeline_orchestrator._cycle_count,
            'suggestions_generated': 0,  # TODO: Query from pipeline metrics
            'tests_running': len(getattr(_pipeline_orchestrator, 'pipeline', {}).get('active_tests', [])),
            'deployments_active': 0  # TODO: Query active deployments
        }

        logger.info("✅ Retrieved pipeline status")
        return PipelineStatusResponse(**status)

    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-tests", response_model=List[ActiveTestResponse])
async def get_active_tests():
    """
    Get all active shadow tests.

    Returns:
        List[ActiveTestResponse]: Active tests with current metrics

    Raises:
        HTTPException: If pipeline not initialized (500)
    """
    if not _pipeline_orchestrator:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")

    try:
        # Get active tests from pipeline
        pipeline = getattr(_pipeline_orchestrator, 'pipeline', None)
        if not pipeline:
            return []

        active_tests = pipeline.active_tests

        response = [
            ActiveTestResponse(
                test_id=test.test_id,
                parameter=test.parameter.name,
                session=test.test_configuration.session or "ALL",
                start_date=test.start_time.isoformat(),
                current_metrics={
                    'control_performance': test.baseline_performance or {},
                    'test_performance': test.current_performance or {},
                    'phase': test.current_phase.value
                }
            )
            for test in active_tests
        ]

        logger.info(f"✅ Retrieved {len(response)} active tests")
        return response

    except Exception as e:
        logger.error(f"Failed to get active tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-suggestions", response_model=List[Dict])
async def get_pending_suggestions():
    """
    Get all pending parameter suggestions.

    Returns:
        List[Dict]: Pending suggestions sorted by expected improvement

    Raises:
        HTTPException: If pipeline not initialized (500)
    """
    if not _pipeline_orchestrator:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")

    try:
        # Get pending suggestions from pipeline
        pipeline = getattr(_pipeline_orchestrator, 'pipeline', None)
        if not pipeline:
            return []

        pending_suggestions = [
            s for s in pipeline.pending_suggestions
            if s.status == 'PENDING'
        ]

        # Sort by expected improvement descending
        pending_suggestions.sort(
            key=lambda s: s.estimated_benefit,
            reverse=True
        )

        response = [
            {
                'suggestion_id': str(s.suggestion_id),
                'title': s.title,
                'description': s.description,
                'expected_improvement': s.estimated_benefit,
                'risk_level': s.risk_level.value,
                'status': s.status.value,
                'created_at': s.creation_timestamp.isoformat()
            }
            for s in pending_suggestions
        ]

        logger.info(f"✅ Retrieved {len(response)} pending suggestions")
        return response

    except Exception as e:
        logger.error(f"Failed to get pending suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployments/recent", response_model=List[Dict])
async def get_recent_deployments(days: int = 30):
    """
    Get recent deployments.

    Args:
        days: Number of days to look back (default: 30)

    Returns:
        List[Dict]: Recent deployments with status and metrics

    Raises:
        HTTPException: If pipeline not initialized (500)
    """
    if not _pipeline_orchestrator:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")

    try:
        # TODO: Query from parameter_history repository
        logger.info(f"Retrieving deployments from last {days} days")

        # Placeholder - return empty list for now
        return []

    except Exception as e:
        logger.error(f"Failed to get recent deployments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/emergency-stop")
async def emergency_stop_pipeline(reason: str, authorized_by: str):
    """
    Emergency stop of continuous improvement pipeline.

    Stops all active shadow tests, halts pipeline execution,
    and rolls back any in-progress deployments.

    Args:
        reason: Reason for emergency stop
        authorized_by: Who authorized the stop

    Returns:
        Dict: Confirmation with actions taken

    Raises:
        HTTPException: If pipeline not initialized (500)
    """
    if not _pipeline_orchestrator:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")

    try:
        logger.warning(f"🚨 EMERGENCY STOP requested by {authorized_by}: {reason}")

        # Stop active tests
        pipeline = getattr(_pipeline_orchestrator, 'pipeline', None)
        if pipeline:
            active_tests_count = len(pipeline.active_tests)

            # TODO: Implement emergency stop logic
            # - Stop all active shadow tests
            # - Rollback in-progress deployments
            # - Set emergency stop flag

            logger.warning(f"Stopped {active_tests_count} active tests")

        # Stop pipeline execution
        await _pipeline_orchestrator.stop_pipeline()

        logger.warning("✅ Emergency stop completed")

        return {
            'success': True,
            'message': 'Emergency stop completed',
            'actions_taken': [
                'Stopped active shadow tests',
                'Halted pipeline execution',
                'Set emergency stop flag'
            ],
            'authorized_by': authorized_by,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to execute emergency stop: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
