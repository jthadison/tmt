"""
Account Manager FastAPI application.
Multi-account configuration management with secure credential storage and 2FA.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
import uvicorn

from .models import (
    AccountConfiguration, AccountCreateRequest, AccountUpdateRequest,
    AccountStatusChangeRequest, AccountListResponse, AccountSummaryStats,
    AccountHealthStatus, TwoFactorAuthSetup, TwoFactorAuthVerification,
    CredentialRotationRequest, AccountExportData, AccountImportRequest,
    AccountStatus, PropFirm, TradingParameters, RiskLimits, NotificationSettings
)
from .vault_service import VaultService, VaultConfig, VaultServiceFactory
from .two_factor_auth import TwoFactorAuthService, TwoFactorAuthManager
from .status_manager import AccountStatusManager
from .import_export_service import ImportExportService
from ...shared.health import HealthChecker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TMT Account Manager",
    description="Multi-Account Configuration Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Global services (in production, these would be dependency-injected)
vault_service = None
auth_service = None
status_manager = None
import_export_service = None
health_checker = HealthChecker("account-manager", "1.0.0")

# In-memory storage (in production, would use database)
accounts_db: Dict[UUID, AccountConfiguration] = {}
user_secrets: Dict[str, str] = {}  # user_id -> totp_secret


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global vault_service, auth_service, status_manager, import_export_service
    
    try:
        # Initialize Vault service
        vault_config = VaultConfig()  # Uses defaults, in production would load from config
        vault_service = VaultServiceFactory.create(vault_config)
        
        # Initialize 2FA service
        auth_service = TwoFactorAuthManager.get_instance()
        
        # Initialize status manager
        status_manager = AccountStatusManager()
        
        # Initialize import/export service
        import_export_service = ImportExportService(vault_service, auth_service)
        
        logger.info("Account Manager services initialized")
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        # In production, would exit or retry


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Get current user from JWT token (mock implementation).
    
    In production, this would validate JWT tokens and return user information.
    """
    # Mock user - in production would decode JWT token
    return "user_123"


async def verify_2fa(user_id: str, totp_code: str) -> bool:
    """
    Verify 2FA code for user.
    
    Args:
        user_id: User identifier
        totp_code: TOTP code to verify
        
    Returns:
        True if code is valid
    """
    try:
        # Get user's secret (in production, from database)
        secret = user_secrets.get(user_id)
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA not set up for user"
            )
        
        return auth_service.verify_totp(secret, totp_code, user_id)
        
    except Exception as e:
        logger.error(f"2FA verification failed for user {user_id}: {e}")
        return False


# Account Management Endpoints

@app.post("/api/v1/accounts", response_model=AccountConfiguration)
async def create_account(
    request: AccountCreateRequest,
    current_user: str = Depends(get_current_user)
):
    """Create a new trading account."""
    try:
        # Verify 2FA
        if not await verify_2fa(current_user, request.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
        
        # Create account configuration
        account = AccountConfiguration(
            prop_firm=request.prop_firm,
            account_number=request.account_number,
            initial_balance=request.initial_balance,
            balance=request.initial_balance,
            equity=request.initial_balance,
            broker_credentials=request.broker_credentials,
            trading_parameters=request.trading_parameters or TradingParameters(),
            risk_limits=request.risk_limits or RiskLimits(),
            notification_settings=request.notification_settings or NotificationSettings(),
            legal_entity_id=request.legal_entity_id,
            personality_profile_id=request.personality_profile_id,
            created_by=current_user
        )
        
        # Store credentials in Vault
        vault_ref = vault_service.store_credentials(account.account_id, request.broker_credentials)
        account.encrypted_credentials_path = vault_ref.vault_path
        
        # Store account
        accounts_db[account.account_id] = account
        
        logger.info(f"Account created: {account.account_id} by {current_user}")
        return account
        
    except Exception as e:
        logger.error(f"Account creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account creation failed: {str(e)}"
        )


@app.get("/api/v1/accounts", response_model=AccountListResponse)
async def list_accounts(
    page: int = 1,
    page_size: int = 50,
    prop_firm: Optional[PropFirm] = None,
    status_filter: Optional[AccountStatus] = None,
    current_user: str = Depends(get_current_user)
):
    """List all accounts with optional filtering."""
    try:
        # Get all accounts
        all_accounts = list(accounts_db.values())
        
        # Apply filters
        filtered_accounts = all_accounts
        
        if prop_firm:
            filtered_accounts = [acc for acc in filtered_accounts if acc.prop_firm == prop_firm]
        
        if status_filter:
            filtered_accounts = [acc for acc in filtered_accounts if acc.status == status_filter]
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_accounts = filtered_accounts[start_idx:end_idx]
        
        return AccountListResponse(
            accounts=paginated_accounts,
            total_count=len(filtered_accounts),
            page=page,
            page_size=page_size,
            has_more=end_idx < len(filtered_accounts)
        )
        
    except Exception as e:
        logger.error(f"Account listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account listing failed: {str(e)}"
        )


@app.get("/api/v1/accounts/{account_id}", response_model=AccountConfiguration)
async def get_account(
    account_id: UUID,
    current_user: str = Depends(get_current_user)
):
    """Get specific account by ID."""
    try:
        account = accounts_db.get(account_id)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account retrieval failed: {str(e)}"
        )


@app.put("/api/v1/accounts/{account_id}", response_model=AccountConfiguration)
async def update_account(
    account_id: UUID,
    request: AccountUpdateRequest,
    current_user: str = Depends(get_current_user)
):
    """Update account configuration."""
    try:
        # Verify 2FA
        if not await verify_2fa(current_user, request.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
        
        account = accounts_db.get(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Update fields
        if request.prop_firm:
            account.prop_firm = request.prop_firm
        if request.trading_parameters:
            account.trading_parameters = request.trading_parameters
        if request.risk_limits:
            account.risk_limits = request.risk_limits
        if request.notification_settings:
            account.notification_settings = request.notification_settings
        if request.legal_entity_id:
            account.legal_entity_id = request.legal_entity_id
        if request.personality_profile_id:
            account.personality_profile_id = request.personality_profile_id
        
        # Update credentials if provided
        if request.broker_credentials:
            vault_ref = vault_service.store_credentials(account_id, request.broker_credentials)
            account.encrypted_credentials_path = vault_ref.vault_path
        
        account.updated_at = datetime.utcnow()
        
        logger.info(f"Account updated: {account_id} by {current_user}")
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account update failed: {str(e)}"
        )


@app.delete("/api/v1/accounts/{account_id}")
async def delete_account(
    account_id: UUID,
    totp_code: str,
    current_user: str = Depends(get_current_user)
):
    """Delete account and purge credentials."""
    try:
        # Verify 2FA
        if not await verify_2fa(current_user, totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
        
        account = accounts_db.get(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Purge credentials from Vault
        vault_service.purge_account_credentials(account_id)
        
        # Remove account
        del accounts_db[account_id]
        
        logger.critical(f"Account deleted: {account_id} by {current_user}")
        return {"message": "Account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account deletion failed: {str(e)}"
        )


# Status Management Endpoints

@app.post("/api/v1/accounts/{account_id}/status")
async def change_account_status(
    account_id: UUID,
    request: AccountStatusChangeRequest,
    current_user: str = Depends(get_current_user)
):
    """Change account status."""
    try:
        # Verify 2FA
        if not await verify_2fa(current_user, request.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
        
        account = accounts_db.get(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Transition status
        transition = await status_manager.transition_status(
            account,
            request.new_status,
            request.reason,
            current_user
        )
        
        return {
            "message": "Status changed successfully",
            "transition": transition.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status change failed: {str(e)}"
        )


@app.get("/api/v1/accounts/{account_id}/status/history")
async def get_status_history(
    account_id: UUID,
    limit: int = 50,
    current_user: str = Depends(get_current_user)
):
    """Get account status change history."""
    try:
        history = status_manager.get_transition_history(account_id, limit)
        return {"history": [t.dict() for t in history]}
        
    except Exception as e:
        logger.error(f"Status history retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status history retrieval failed: {str(e)}"
        )


# 2FA Endpoints

@app.post("/api/v1/auth/2fa/setup", response_model=TwoFactorAuthSetup)
async def setup_2fa(
    current_user: str = Depends(get_current_user)
):
    """Set up 2FA for user."""
    try:
        setup_info = auth_service.setup_2fa(current_user, f"TMT-{current_user}")
        
        # Store secret for user (in production, would be in database)
        user_secrets[current_user] = setup_info.secret_key
        
        return setup_info
        
    except Exception as e:
        logger.error(f"2FA setup failed for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"2FA setup failed: {str(e)}"
        )


@app.post("/api/v1/auth/2fa/verify")
async def verify_2fa_code(
    verification: TwoFactorAuthVerification,
    current_user: str = Depends(get_current_user)
):
    """Verify 2FA code."""
    try:
        secret = user_secrets.get(current_user)
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA not set up"
            )
        
        is_valid = auth_service.verify_2fa(verification, secret, current_user)
        
        return {"valid": is_valid}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"2FA verification failed: {str(e)}"
        )


@app.get("/api/v1/auth/2fa/status")
async def get_2fa_status(
    current_user: str = Depends(get_current_user)
):
    """Get 2FA status for user."""
    try:
        return auth_service.get_2fa_status(current_user)
        
    except Exception as e:
        logger.error(f"2FA status retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"2FA status retrieval failed: {str(e)}"
        )


# Import/Export Endpoints

@app.post("/api/v1/accounts/export")
async def export_accounts(
    account_ids: Optional[List[UUID]] = None,
    export_format: str = "json",
    include_credentials: bool = False,
    current_user: str = Depends(get_current_user)
):
    """Export account configurations."""
    try:
        # Get accounts to export
        if account_ids:
            accounts = [accounts_db[aid] for aid in account_ids if aid in accounts_db]
        else:
            accounts = list(accounts_db.values())
        
        if not accounts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No accounts found to export"
            )
        
        # Export accounts
        export_data = await import_export_service.export_accounts(
            accounts, export_format, include_credentials, current_user
        )
        
        return {"export_data": export_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account export failed: {str(e)}"
        )


@app.post("/api/v1/accounts/import")
async def import_accounts(
    request: AccountImportRequest,
    current_user: str = Depends(get_current_user)
):
    """Import account configurations."""
    try:
        # Verify 2FA
        if not await verify_2fa(current_user, request.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
        
        # Import accounts
        imported_accounts, validation_errors = await import_export_service.import_accounts_from_string(
            request.export_data.json(),
            "json",
            request.overwrite_existing,
            request.validate_only,
            current_user,
            request.totp_code
        )
        
        # Store imported accounts (if not validate-only)
        if not request.validate_only:
            for account in imported_accounts:
                accounts_db[account.account_id] = account
        
        return {
            "imported_count": len(imported_accounts),
            "validation_errors": validation_errors,
            "validate_only": request.validate_only
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account import failed: {str(e)}"
        )


# Dashboard and Statistics Endpoints

@app.get("/api/v1/accounts/summary", response_model=AccountSummaryStats)
async def get_account_summary(
    current_user: str = Depends(get_current_user)
):
    """Get account summary statistics."""
    try:
        accounts = list(accounts_db.values())
        
        # Calculate statistics
        total_accounts = len(accounts)
        active_accounts = sum(1 for acc in accounts if acc.status == AccountStatus.ACTIVE)
        suspended_accounts = sum(1 for acc in accounts if acc.status == AccountStatus.SUSPENDED)
        in_drawdown_accounts = sum(1 for acc in accounts if acc.status == AccountStatus.IN_DRAWDOWN)
        terminated_accounts = sum(1 for acc in accounts if acc.status == AccountStatus.TERMINATED)
        
        total_balance = sum(acc.balance for acc in accounts)
        total_equity = sum(acc.equity if acc.equity else acc.balance for acc in accounts)
        total_pnl = sum((acc.balance - acc.initial_balance) for acc in accounts)
        
        # Get health scores (mock data)
        health_scores = [90, 85, 95, 88, 92]  # Mock health scores
        avg_health_score = sum(health_scores) / len(health_scores) if health_scores else 0
        
        return AccountSummaryStats(
            total_accounts=total_accounts,
            active_accounts=active_accounts,
            suspended_accounts=suspended_accounts,
            in_drawdown_accounts=in_drawdown_accounts,
            terminated_accounts=terminated_accounts,
            total_balance=total_balance,
            total_equity=total_equity,
            total_pnl=total_pnl,
            avg_health_score=avg_health_score,
            accounts_with_violations=0  # Mock data
        )
        
    except Exception as e:
        logger.error(f"Summary statistics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary statistics failed: {str(e)}"
        )


@app.get("/api/v1/accounts/{account_id}/health", response_model=AccountHealthStatus)
async def get_account_health(
    account_id: UUID,
    current_user: str = Depends(get_current_user)
):
    """Get account health status."""
    try:
        account = accounts_db.get(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Get or create health status
        health = status_manager.get_health_status(account_id)
        
        if not health:
            # Create mock health status
            health = AccountHealthStatus(
                account_id=account_id,
                status=account.status,
                is_healthy=(account.status == AccountStatus.ACTIVE),
                last_heartbeat=datetime.utcnow(),
                connection_status="connected",
                balance_last_updated=account.updated_at,
                health_score=90 if account.status == AccountStatus.ACTIVE else 50
            )
            
            status_manager.update_health_status(account_id, health)
        
        return health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health status retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health status retrieval failed: {str(e)}"
        )


# Health Check Endpoints

@app.get("/health")
async def health_check():
    """Basic health check."""
    return health_checker.get_health()


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including dependencies."""
    try:
        # Check Vault health
        vault_health = vault_service.health_check() if vault_service else {"status": "not_initialized"}
        
        # Check 2FA service
        auth_health = {"status": "healthy" if auth_service else "not_initialized"}
        
        # Check status manager
        status_health = {"status": "healthy" if status_manager else "not_initialized"}
        
        overall_healthy = all([
            vault_health.get("status") == "healthy",
            auth_health.get("status") == "healthy",
            status_health.get("status") == "healthy"
        ])
        
        return {
            "service": "account-manager",
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {
                "vault": vault_health,
                "auth": auth_health,
                "status_manager": status_health
            },
            "statistics": {
                "total_accounts": len(accounts_db),
                "active_accounts": sum(1 for acc in accounts_db.values() if acc.status == AccountStatus.ACTIVE)
            }
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "service": "account-manager",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )