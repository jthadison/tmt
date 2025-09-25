"""
Authentication and Authorization for Performance Alerts API

Provides configurable security for alert management endpoints
with role-based access control and API key validation.
"""

import os
import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import jwt
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AlertPermission(Enum):
    """Alert system permissions"""
    VIEW_STATUS = "alert:view_status"
    VIEW_HISTORY = "alert:view_history"
    TRIGGER_MANUAL = "alert:trigger_manual"
    ENABLE_DISABLE = "alert:enable_disable"
    CONFIGURE = "alert:configure"
    ADMIN = "alert:admin"


class AlertRole(Enum):
    """Pre-defined alert system roles"""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


@dataclass
class AlertUser:
    """Alert system user"""
    user_id: str
    username: str
    roles: Set[AlertRole] = field(default_factory=set)
    permissions: Set[AlertPermission] = field(default_factory=set)
    api_key: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    enabled: bool = True


class AlertAuthConfig:
    """Configuration for alert authentication"""

    def __init__(self):
        # Load configuration from environment
        self.enabled = os.getenv("ALERT_AUTH_ENABLED", "true").lower() == "true"
        self.jwt_secret = os.getenv("ALERT_JWT_SECRET") or secrets.token_urlsafe(32)
        self.jwt_algorithm = os.getenv("ALERT_JWT_ALGORITHM", "HS256")
        self.jwt_expire_hours = int(os.getenv("ALERT_JWT_EXPIRE_HOURS", "24"))

        # API key configuration
        self.api_key_header = os.getenv("ALERT_API_KEY_HEADER", "X-Alert-API-Key")
        self.master_api_key = os.getenv("ALERT_MASTER_API_KEY")

        # Role-based permissions
        self.role_permissions = {
            AlertRole.VIEWER: {
                AlertPermission.VIEW_STATUS,
                AlertPermission.VIEW_HISTORY
            },
            AlertRole.OPERATOR: {
                AlertPermission.VIEW_STATUS,
                AlertPermission.VIEW_HISTORY,
                AlertPermission.TRIGGER_MANUAL,
                AlertPermission.ENABLE_DISABLE
            },
            AlertRole.ADMIN: {
                AlertPermission.VIEW_STATUS,
                AlertPermission.VIEW_HISTORY,
                AlertPermission.TRIGGER_MANUAL,
                AlertPermission.ENABLE_DISABLE,
                AlertPermission.CONFIGURE,
                AlertPermission.ADMIN
            }
        }

        # Initialize default users if enabled
        self.users: Dict[str, AlertUser] = {}
        if self.enabled:
            self._initialize_default_users()

        logger.info(f"Alert authentication {'enabled' if self.enabled else 'disabled'}")

    def _initialize_default_users(self):
        """Initialize default users from environment"""
        # Create default admin user
        admin_key = os.getenv("ALERT_ADMIN_API_KEY")
        if admin_key:
            admin_user = AlertUser(
                user_id="admin",
                username="admin",
                roles={AlertRole.ADMIN},
                api_key=self._hash_api_key(admin_key),
                permissions=self.role_permissions[AlertRole.ADMIN]
            )
            self.users["admin"] = admin_user
            logger.info("Created default admin user")

        # Create default operator user
        operator_key = os.getenv("ALERT_OPERATOR_API_KEY")
        if operator_key:
            operator_user = AlertUser(
                user_id="operator",
                username="operator",
                roles={AlertRole.OPERATOR},
                api_key=self._hash_api_key(operator_key),
                permissions=self.role_permissions[AlertRole.OPERATOR]
            )
            self.users["operator"] = operator_user
            logger.info("Created default operator user")

        # Create default viewer user
        viewer_key = os.getenv("ALERT_VIEWER_API_KEY")
        if viewer_key:
            viewer_user = AlertUser(
                user_id="viewer",
                username="viewer",
                roles={AlertRole.VIEWER},
                api_key=self._hash_api_key(viewer_key),
                permissions=self.role_permissions[AlertRole.VIEWER]
            )
            self.users["viewer"] = viewer_user
            logger.info("Created default viewer user")

        if not self.users and not self.master_api_key:
            logger.warning("Alert authentication enabled but no users or master API key configured")

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, api_key: str) -> Optional[AlertUser]:
        """Verify API key and return user"""
        if not self.enabled:
            return None

        # Check master API key
        if self.master_api_key and api_key == self.master_api_key:
            # Master key has all permissions
            return AlertUser(
                user_id="master",
                username="master",
                roles={AlertRole.ADMIN},
                permissions=set(AlertPermission),  # All permissions
                last_used=datetime.utcnow()
            )

        # Check user API keys
        hashed_key = self._hash_api_key(api_key)
        for user in self.users.values():
            if user.enabled and user.api_key == hashed_key:
                user.last_used = datetime.utcnow()
                return user

        return None

    def create_jwt_token(self, user: AlertUser) -> str:
        """Create JWT token for user"""
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "roles": [role.value for role in user.roles],
            "permissions": [perm.value for perm in user.permissions],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expire_hours)
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_jwt_token(self, token: str) -> Optional[AlertUser]:
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            user = AlertUser(
                user_id=payload["user_id"],
                username=payload["username"],
                roles={AlertRole(role) for role in payload["roles"]},
                permissions={AlertPermission(perm) for perm in payload["permissions"]},
                last_used=datetime.utcnow()
            )

            return user

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    def has_permission(self, user: AlertUser, permission: AlertPermission) -> bool:
        """Check if user has specific permission"""
        return permission in user.permissions


# Global configuration instance
_auth_config: Optional[AlertAuthConfig] = None


def get_auth_config() -> AlertAuthConfig:
    """Get global auth configuration instance"""
    global _auth_config
    if _auth_config is None:
        _auth_config = AlertAuthConfig()
    return _auth_config


# FastAPI dependencies
security_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-Alert-API-Key", auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=401, detail=detail)


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[AlertUser]:
    """Get current authenticated user"""
    auth_config = get_auth_config()

    # If authentication is disabled, return admin-like user
    if not auth_config.enabled:
        return AlertUser(
            user_id="system",
            username="system",
            roles={AlertRole.ADMIN},
            permissions=set(AlertPermission)
        )

    user = None

    # Try API key authentication first
    if api_key:
        user = auth_config.verify_api_key(api_key)
        if user:
            logger.debug(f"Authenticated user {user.username} via API key")
            return user

    # Try JWT token authentication
    if credentials:
        user = auth_config.verify_jwt_token(credentials.credentials)
        if user:
            logger.debug(f"Authenticated user {user.username} via JWT")
            return user

    # No valid authentication found
    if auth_config.enabled:
        raise AuthenticationError("Invalid authentication credentials")

    return None


def require_permission(permission: AlertPermission):
    """Decorator to require specific permission"""
    def dependency(user: AlertUser = Depends(get_current_user)) -> AlertUser:
        if not user:
            raise AuthenticationError()

        auth_config = get_auth_config()
        if auth_config.enabled and not auth_config.has_permission(user, permission):
            raise AuthorizationError(f"Permission required: {permission.value}")

        return user

    return dependency


# Convenience dependencies for different permission levels
async def require_view_status(user: AlertUser = Depends(require_permission(AlertPermission.VIEW_STATUS))) -> AlertUser:
    """Require view status permission"""
    return user


async def require_view_history(user: AlertUser = Depends(require_permission(AlertPermission.VIEW_HISTORY))) -> AlertUser:
    """Require view history permission"""
    return user


async def require_trigger_manual(user: AlertUser = Depends(require_permission(AlertPermission.TRIGGER_MANUAL))) -> AlertUser:
    """Require manual trigger permission"""
    return user


async def require_enable_disable(user: AlertUser = Depends(require_permission(AlertPermission.ENABLE_DISABLE))) -> AlertUser:
    """Require enable/disable permission"""
    return user


async def require_configure(user: AlertUser = Depends(require_permission(AlertPermission.CONFIGURE))) -> AlertUser:
    """Require configure permission"""
    return user


async def require_admin(user: AlertUser = Depends(require_permission(AlertPermission.ADMIN))) -> AlertUser:
    """Require admin permission"""
    return user


# Pydantic models for API requests/responses
class LoginRequest(BaseModel):
    api_key: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class UserInfoResponse(BaseModel):
    user_id: str
    username: str
    roles: List[str]
    permissions: List[str]
    last_used: Optional[str]
    enabled: bool