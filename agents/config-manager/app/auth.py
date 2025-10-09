"""
API Authentication

Provides API key authentication for configuration management endpoints.
"""

import os
import secrets
import logging
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from datetime import datetime

logger = logging.getLogger(__name__)

# API Key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    """
    API Key Authentication

    Features:
    - API key validation from environment
    - Support for multiple API keys (comma-separated)
    - Read-only vs read-write key differentiation
    - Request logging for audit trail
    """

    def __init__(self):
        """Initialize API key authentication"""
        # Read-write API keys (full access)
        self.api_keys_rw = self._load_api_keys("CONFIG_MANAGER_API_KEYS_RW")

        # Read-only API keys (GET requests only)
        self.api_keys_ro = self._load_api_keys("CONFIG_MANAGER_API_KEYS_RO")

        # Master API key (for emergency access)
        self.master_key = os.getenv("CONFIG_MANAGER_MASTER_KEY")

        # Log initialization
        logger.info(
            f"API Auth initialized: "
            f"{len(self.api_keys_rw)} RW keys, "
            f"{len(self.api_keys_ro)} RO keys, "
            f"Master key: {'set' if self.master_key else 'not set'}"
        )

        # Warn if no keys configured
        if not self.api_keys_rw and not self.api_keys_ro and not self.master_key:
            logger.warning(
                "⚠️  NO API KEYS CONFIGURED - API is UNSECURED! "
                "Set CONFIG_MANAGER_API_KEYS_RW or CONFIG_MANAGER_MASTER_KEY"
            )

    def _load_api_keys(self, env_var: str) -> set:
        """Load API keys from environment variable"""
        keys_str = os.getenv(env_var, "")
        if not keys_str:
            return set()

        # Split by comma and strip whitespace
        keys = set(key.strip() for key in keys_str.split(",") if key.strip())

        return keys

    def validate_api_key(
        self,
        api_key: Optional[str],
        require_write: bool = False
    ) -> bool:
        """
        Validate API key

        Args:
            api_key: API key from request header
            require_write: Whether write access is required

        Returns:
            True if valid, raises HTTPException if invalid
        """
        # If no API key provided
        if not api_key:
            # Check if auth is disabled (no keys configured)
            if not self.api_keys_rw and not self.api_keys_ro and not self.master_key:
                logger.warning("API key not provided, but auth is disabled")
                return True

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required. Provide X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"}
            )

        # Check master key (always valid for read/write)
        if self.master_key and secrets.compare_digest(api_key, self.master_key):
            logger.info("Valid master API key")
            return True

        # Check read-write keys
        if api_key in self.api_keys_rw:
            logger.debug("Valid read-write API key")
            return True

        # Check read-only keys
        if api_key in self.api_keys_ro:
            if require_write:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Read-only API key. Write access denied."
                )
            logger.debug("Valid read-only API key")
            return True

        # Invalid key
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    def generate_api_key(self) -> str:
        """
        Generate a new secure API key

        Returns:
            Random API key string
        """
        return secrets.token_urlsafe(32)


# Global auth instance
_auth_instance: Optional[APIKeyAuth] = None


def get_auth() -> APIKeyAuth:
    """Get global auth instance"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = APIKeyAuth()
    return _auth_instance


async def require_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER)
) -> str:
    """
    Dependency for endpoints requiring any valid API key (read or write)

    Usage:
        @app.get("/api/config/current")
        async def get_current(api_key: str = Depends(require_api_key)):
            ...

    Args:
        api_key: API key from request header

    Returns:
        Valid API key

    Raises:
        HTTPException: If API key is invalid
    """
    auth = get_auth()
    auth.validate_api_key(api_key, require_write=False)
    return api_key


async def require_write_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER)
) -> str:
    """
    Dependency for endpoints requiring write access

    Usage:
        @app.post("/api/config/activate")
        async def activate_config(
            request: ActivateRequest,
            api_key: str = Depends(require_write_api_key)
        ):
            ...

    Args:
        api_key: API key from request header

    Returns:
        Valid write API key

    Raises:
        HTTPException: If API key is invalid or read-only
    """
    auth = get_auth()
    auth.validate_api_key(api_key, require_write=True)
    return api_key


def generate_new_api_key() -> dict:
    """
    Generate a new API key

    Returns:
        Dictionary with key and instructions
    """
    auth = get_auth()
    new_key = auth.generate_api_key()

    return {
        "api_key": new_key,
        "instructions": (
            "Add this key to your environment:\n"
            f"export CONFIG_MANAGER_API_KEYS_RW='{new_key}'\n"
            "Or for read-only access:\n"
            f"export CONFIG_MANAGER_API_KEYS_RO='{new_key}'"
        )
    }


if __name__ == "__main__":
    """CLI for generating API keys"""
    import json

    print("Generating new API key...\n")
    result = generate_new_api_key()
    print(json.dumps(result, indent=2))
    print("\n⚠️  Keep this key secure! It grants access to configuration management.")
