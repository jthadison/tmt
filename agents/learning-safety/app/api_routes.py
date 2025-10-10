"""
API routes for shadow testing and parameter suggestions.

Provides REST API endpoints for managing shadow tests, retrieving suggestions,
and monitoring test progress.
"""

import logging
from typing import List, Dict, Optional
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1", tags=["shadow-testing"])


# Request/Response models
class ShadowTestResponse(BaseModel):
    """Shadow test response model."""
    test_id: str
    suggestion_id: str
    parameter_name: str
    session: Optional[str]
    current_value: Optional[float]
    test_value: Optional[float]
    start_date: str
    status: str
    control_trades: int
    test_trades: int
    control_win_rate: Optional[float]
    test_win_rate: Optional[float]


class TerminateTestRequest(BaseModel):
    """Request model for terminating shadow test."""
    reason: str


class SuggestionResponse(BaseModel):
    """Parameter suggestion response model."""
    suggestion_id: str
    session: str
    parameter: str
    current_value: float
    suggested_value: float
    reason: str
    expected_improvement: float
    confidence_level: float
    status: str


# Global shadow test repository (injected at startup)
shadow_test_repository = None


def set_shadow_test_repository(repository):
    """
    Set shadow test repository for API routes.

    Args:
        repository: ShadowTestRepository instance
    """
    global shadow_test_repository
    shadow_test_repository = repository


@router.get("/shadow-tests/active", response_model=List[ShadowTestResponse])
async def get_active_shadow_tests():
    """
    Get all active shadow tests.

    Returns:
        List[ShadowTestResponse]: List of active shadow tests with metadata
    """
    if not shadow_test_repository:
        raise HTTPException(status_code=500, detail="Shadow test repository not initialized")

    try:
        tests = await shadow_test_repository.get_active_tests()

        response = [
            ShadowTestResponse(
                test_id=test.test_id,
                suggestion_id=test.suggestion_id,
                parameter_name=test.parameter_name,
                session=test.session,
                current_value=float(test.current_value) if test.current_value else None,
                test_value=float(test.test_value) if test.test_value else None,
                start_date=test.start_date.isoformat(),
                status=test.status,
                control_trades=test.control_trades,
                test_trades=test.test_trades,
                control_win_rate=float(test.control_win_rate) if test.control_win_rate else None,
                test_win_rate=float(test.test_win_rate) if test.test_win_rate else None
            )
            for test in tests
        ]

        logger.info(f"✅ Retrieved {len(response)} active shadow tests")
        return response

    except Exception as e:
        logger.error(f"❌ Failed to get active shadow tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shadow-tests/{test_id}", response_model=ShadowTestResponse)
async def get_shadow_test_by_id(test_id: str):
    """
    Get shadow test by ID.

    Args:
        test_id: Unique test identifier

    Returns:
        ShadowTestResponse: Shadow test details including current metrics

    Raises:
        HTTPException: If test not found (404) or server error (500)
    """
    if not shadow_test_repository:
        raise HTTPException(status_code=500, detail="Shadow test repository not initialized")

    try:
        test = await shadow_test_repository.get_test_by_id(test_id)

        if not test:
            raise HTTPException(status_code=404, detail=f"Shadow test not found: {test_id}")

        response = ShadowTestResponse(
            test_id=test.test_id,
            suggestion_id=test.suggestion_id,
            parameter_name=test.parameter_name,
            session=test.session,
            current_value=float(test.current_value) if test.current_value else None,
            test_value=float(test.test_value) if test.test_value else None,
            start_date=test.start_date.isoformat(),
            status=test.status,
            control_trades=test.control_trades,
            test_trades=test.test_trades,
            control_win_rate=float(test.control_win_rate) if test.control_win_rate else None,
            test_win_rate=float(test.test_win_rate) if test.test_win_rate else None
        )

        logger.info(f"✅ Retrieved shadow test: {test_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get shadow test {test_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shadow-tests/{test_id}/terminate", response_model=ShadowTestResponse)
async def terminate_shadow_test(test_id: str, request: TerminateTestRequest):
    """
    Terminate shadow test early.

    Args:
        test_id: Unique test identifier
        request: Termination request with reason

    Returns:
        ShadowTestResponse: Terminated test details

    Raises:
        HTTPException: If test not found (404) or server error (500)
    """
    if not shadow_test_repository:
        raise HTTPException(status_code=500, detail="Shadow test repository not initialized")

    try:
        test = await shadow_test_repository.terminate_test(test_id, request.reason)

        response = ShadowTestResponse(
            test_id=test.test_id,
            suggestion_id=test.suggestion_id,
            parameter_name=test.parameter_name,
            session=test.session,
            current_value=float(test.current_value) if test.current_value else None,
            test_value=float(test.test_value) if test.test_value else None,
            start_date=test.start_date.isoformat(),
            status=test.status,
            control_trades=test.control_trades,
            test_trades=test.test_trades,
            control_win_rate=float(test.control_win_rate) if test.control_win_rate else None,
            test_win_rate=float(test.test_win_rate) if test.test_win_rate else None
        )

        logger.info(f"✅ Terminated shadow test: {test_id}")
        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Failed to terminate shadow test {test_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/pending", response_model=List[Dict])
async def get_pending_suggestions():
    """
    Get all pending parameter suggestions.

    Returns:
        List[Dict]: List of pending suggestions with expected improvement

    Note: This is a placeholder implementation. In production, suggestions
    would be stored in database and queried here.
    """
    logger.info("📋 Retrieved pending suggestions")

    # Placeholder - in production, query from database
    return []
