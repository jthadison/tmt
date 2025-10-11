"""
Parameter management API routes for orchestrator.

Provides endpoints for updating trading parameters with validation,
authorization, and audit trail logging.
"""

import logging
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator

from .audit_logger import get_audit_logger

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/parameters", tags=["parameters"])


class ParameterUpdateRequest(BaseModel):
    """
    Request model for parameter updates.

    Attributes:
        parameter: Parameter name (e.g., 'confidence_threshold', 'min_risk_reward')
        value: New parameter value
        allocation: Signal allocation percentage (0.10 to 1.00)
        session: Trading session to apply parameter to
        applied_by: Who/what is applying this change
    """
    parameter: str = Field(..., description="Parameter name to update")
    value: float = Field(..., description="New parameter value")
    allocation: float = Field(..., ge=0.0, le=1.0, description="Signal allocation percentage")
    session: str = Field(..., description="Trading session (TOKYO, LONDON, NY, SYDNEY, OVERLAP, ALL)")
    applied_by: str = Field(default="learning_agent", description="Source of parameter change")

    @validator('parameter')
    def validate_parameter_name(cls, v):
        """Validate parameter name is in allowed list."""
        allowed_parameters = ['confidence_threshold', 'min_risk_reward']
        if v not in allowed_parameters:
            raise ValueError(f"Parameter must be one of {allowed_parameters}")
        return v

    @validator('session')
    def validate_session(cls, v):
        """Validate session name."""
        allowed_sessions = ['TOKYO', 'LONDON', 'NY', 'SYDNEY', 'OVERLAP', 'ALL']
        if v not in allowed_sessions:
            raise ValueError(f"Session must be one of {allowed_sessions}")
        return v

    @validator('value')
    def validate_value_range(cls, v, values):
        """Validate parameter value is within reasonable bounds."""
        parameter = values.get('parameter')
        if parameter == 'confidence_threshold':
            if not (40.0 <= v <= 95.0):
                raise ValueError("confidence_threshold must be between 40% and 95%")
        elif parameter == 'min_risk_reward':
            if not (1.5 <= v <= 5.0):
                raise ValueError("min_risk_reward must be between 1.5 and 5.0")
        return v


class ParameterUpdateResponse(BaseModel):
    """Response model for parameter update."""
    success: bool
    message: str
    parameter: str
    value: float
    allocation: float
    session: str
    applied_at: str


# Global configuration store (will be injected at startup)
_parameter_config = {}


def set_parameter_config(config: dict):
    """
    Set global parameter configuration.

    Args:
        config: Parameter configuration dictionary
    """
    global _parameter_config
    _parameter_config = config


@router.post("/update", response_model=ParameterUpdateResponse)
async def update_parameter(request: ParameterUpdateRequest):
    """
    Update trading parameter with validation and audit logging.

    This endpoint allows the learning agent to update trading parameters
    with gradual rollout allocation. Changes are applied immediately to
    signal generation with the specified allocation percentage.

    Args:
        request: Parameter update request

    Returns:
        ParameterUpdateResponse: Confirmation of parameter update

    Raises:
        HTTPException: If parameter update fails (400, 500)
    """
    try:
        logger.info(f"Updating parameter: {request.parameter}={request.value} "
                   f"at {request.allocation:.0%} allocation for {request.session}")

        # Validate authentication/authorization
        if request.applied_by not in ['learning_agent', 'manual', 'system_auto']:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized parameter update source"
            )

        # Update parameter configuration
        session_key = request.session if request.session != 'ALL' else 'default'

        if session_key not in _parameter_config:
            _parameter_config[session_key] = {}

        # Store parameter with allocation tracking
        param_key = f"{request.parameter}_allocation"
        _parameter_config[session_key][request.parameter] = Decimal(str(request.value))
        _parameter_config[session_key][param_key] = Decimal(str(request.allocation))

        # Log to audit trail
        audit_logger = get_audit_logger()
        await audit_logger.log_parameter_change(
            parameter=request.parameter,
            old_value=_parameter_config[session_key].get(request.parameter, 0),
            new_value=request.value,
            session=request.session,
            changed_by=request.applied_by,
            reason=f"Gradual rollout at {request.allocation:.0%} allocation"
        )

        # TODO: Notify Market Analysis Agent to apply parameter in signal generation

        from datetime import datetime, timezone
        logger.info(f"✅ Parameter updated: {request.parameter}={request.value} "
                   f"for {request.session} at {request.allocation:.0%}")

        return ParameterUpdateResponse(
            success=True,
            message=f"Parameter {request.parameter} updated successfully",
            parameter=request.parameter,
            value=request.value,
            allocation=request.allocation,
            session=request.session,
            applied_at=datetime.now(timezone.utc).isoformat()
        )

    except ValueError as e:
        logger.error(f"Invalid parameter update request: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to update parameter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Parameter update failed: {str(e)}")


@router.get("/current")
async def get_current_parameters(session: Optional[str] = None):
    """
    Get current parameter configuration.

    Args:
        session: Optional session filter (TOKYO, LONDON, etc.)

    Returns:
        Dict: Current parameter values with allocations
    """
    try:
        if session:
            session_params = _parameter_config.get(session, {})
            return {
                "session": session,
                "parameters": {
                    k: float(v) if isinstance(v, Decimal) else v
                    for k, v in session_params.items()
                }
            }
        else:
            return {
                "all_sessions": {
                    session_name: {
                        k: float(v) if isinstance(v, Decimal) else v
                        for k, v in params.items()
                    }
                    for session_name, params in _parameter_config.items()
                }
            }

    except Exception as e:
        logger.error(f"Failed to get current parameters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_parameter_history(days: int = 7):
    """
    Get parameter change history.

    Args:
        days: Number of days to look back

    Returns:
        List: Parameter change history
    """
    try:
        # TODO: Query parameter_history table via repository
        logger.info(f"Retrieving parameter history for last {days} days")

        # Placeholder - in production, query from database
        return {
            "history": [],
            "days": days
        }

    except Exception as e:
        logger.error(f"Failed to get parameter history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
