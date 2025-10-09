"""
Configuration Manager FastAPI Application

REST API for configuration management operations.
"""

import logging
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config_manager import ConfigurationManager
from .rollback import RollbackManager, ConfigFreeze
from .slack_notifier import SlackNotifier
from .models import (
    TradingConfig,
    ConfigHistoryEntry,
    ConfigActivationRequest,
    ConfigRollbackRequest,
    ConfigProposeRequest,
    ConfigValidationResult
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Configuration Manager API",
    description="Trading System Configuration Management with Version Control",
    version="1.0.0"
)

# Initialize managers
repo_root = Path(__file__).parent.parent.parent.parent
config_dir = repo_root / "config" / "parameters"
schema_path = config_dir / "schema.json"
freeze_file = config_dir / ".freeze"

config_manager = ConfigurationManager(
    config_dir=config_dir,
    schema_path=schema_path,
    repo_path=repo_root
)

rollback_manager = RollbackManager(config_manager)
config_freeze = ConfigFreeze(freeze_file)
slack_notifier = SlackNotifier()


# Response models
class StatusResponse(BaseModel):
    status: str
    message: str


class VersionListResponse(BaseModel):
    versions: List[str]
    active_version: Optional[str]
    total_count: int


# Middleware to check freeze status
@app.middleware("http")
async def check_freeze(request, call_next):
    """Check if configuration is frozen"""
    if config_freeze.is_frozen():
        # Allow GET requests and health checks
        if request.method == "GET" or request.url.path == "/health":
            response = await call_next(request)
            return response

        freeze_info = config_freeze.get_freeze_info()
        return JSONResponse(
            status_code=status.HTTP_423_LOCKED,
            content={
                "error": "Configuration is frozen",
                "freeze_info": freeze_info
            }
        )

    response = await call_next(request)
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "config-manager",
        "version": "1.0.0",
        "frozen": config_freeze.is_frozen()
    }


@app.get("/api/config/current", response_model=TradingConfig)
async def get_current_config():
    """
    Get currently active configuration

    Returns:
        Active trading configuration
    """
    try:
        config = config_manager.load_current_config()
        return config
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to load current config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configuration: {str(e)}"
        )


@app.get("/api/config/version/{version}", response_model=TradingConfig)
async def get_config_version(version: str):
    """
    Get specific configuration version

    Args:
        version: Version string (e.g., "1.0.0")

    Returns:
        Configuration for specified version
    """
    try:
        config = config_manager.load_version(version)
        return config
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration version not found: {version}"
        )
    except Exception as e:
        logger.error(f"Failed to load version {version}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load version: {str(e)}"
        )


@app.get("/api/config/versions", response_model=VersionListResponse)
async def list_versions():
    """
    List all available configuration versions

    Returns:
        List of version strings with active version
    """
    try:
        versions = config_manager.list_versions()
        active_version = config_manager.get_active_version()

        return VersionListResponse(
            versions=versions,
            active_version=active_version,
            total_count=len(versions)
        )
    except Exception as e:
        logger.error(f"Failed to list versions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list versions: {str(e)}"
        )


@app.get("/api/config/history", response_model=List[ConfigHistoryEntry])
async def get_config_history(limit: int = 20):
    """
    Get configuration change history

    Args:
        limit: Maximum number of history entries (default: 20)

    Returns:
        List of configuration history entries from Git
    """
    try:
        history = config_manager.get_config_history(limit=limit)
        return history
    except Exception as e:
        logger.error(f"Failed to get history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )


@app.post("/api/config/propose", response_model=StatusResponse)
async def propose_config(request: ConfigProposeRequest):
    """
    Propose new configuration (saves but doesn't activate)

    Args:
        request: Configuration proposal request

    Returns:
        Status response
    """
    try:
        # Save configuration
        config_path = config_manager.propose_new_config(
            config=request.config,
            auto_commit=True
        )

        # Send notification
        slack_notifier.send_config_change_notification(
            config=request.config,
            activated=False
        )

        return StatusResponse(
            status="success",
            message=f"Configuration v{request.config.version} proposed successfully"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to propose config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to propose configuration: {str(e)}"
        )


@app.post("/api/config/activate", response_model=StatusResponse)
async def activate_config(request: ConfigActivationRequest):
    """
    Activate a configuration version

    Args:
        request: Activation request with version

    Returns:
        Status response
    """
    try:
        # Activate version
        config_path = config_manager.activate_version(
            version=request.version,
            reason=request.reason,
            auto_commit=True
        )

        # Load activated config for notification
        config = config_manager.load_current_config()

        # Send notification
        slack_notifier.send_config_change_notification(
            config=config,
            activated=True
        )

        return StatusResponse(
            status="success",
            message=f"Configuration v{request.version} activated successfully"
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to activate config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate configuration: {str(e)}"
        )


@app.post("/api/config/rollback", response_model=StatusResponse)
async def rollback_config(request: ConfigRollbackRequest):
    """
    Rollback configuration to previous or specific version

    Args:
        request: Rollback request

    Returns:
        Status response
    """
    try:
        # Perform rollback
        rolled_back_config = rollback_manager.rollback(
            version=request.version,
            reason=request.reason,
            emergency=request.emergency,
            notify=True
        )

        return StatusResponse(
            status="success",
            message=f"Configuration rolled back to v{rolled_back_config.version}"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to rollback config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback configuration: {str(e)}"
        )


@app.post("/api/config/validate/{version}", response_model=ConfigValidationResult)
async def validate_config(version: str):
    """
    Validate a configuration version

    Args:
        version: Version to validate

    Returns:
        Validation result
    """
    try:
        version_file = config_manager._get_version_filename(version)
        version_path = config_manager.config_dir / version_file

        if not version_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration version not found: {version}"
            )

        # Validate
        result = config_manager.validator.validate_file(version_path)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate configuration: {str(e)}"
        )


@app.post("/api/config/freeze", response_model=StatusResponse)
async def freeze_config(reason: str = "Manual freeze"):
    """
    Freeze configuration changes

    Args:
        reason: Reason for freeze

    Returns:
        Status response
    """
    try:
        config_freeze.freeze(reason=reason)

        return StatusResponse(
            status="success",
            message="Configuration frozen successfully"
        )

    except Exception as e:
        logger.error(f"Failed to freeze config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to freeze configuration: {str(e)}"
        )


@app.post("/api/config/unfreeze", response_model=StatusResponse)
async def unfreeze_config():
    """
    Unfreeze configuration changes

    Returns:
        Status response
    """
    try:
        config_freeze.unfreeze()

        return StatusResponse(
            status="success",
            message="Configuration unfrozen successfully"
        )

    except Exception as e:
        logger.error(f"Failed to unfreeze config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unfreeze configuration: {str(e)}"
        )


@app.get("/api/config/freeze-status")
async def get_freeze_status():
    """
    Get configuration freeze status

    Returns:
        Freeze status and information
    """
    try:
        is_frozen = config_freeze.is_frozen()
        freeze_info = config_freeze.get_freeze_info() if is_frozen else None

        return {
            "frozen": is_frozen,
            "freeze_info": freeze_info
        }

    except Exception as e:
        logger.error(f"Failed to get freeze status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get freeze status: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8090,
        log_level="info"
    )
