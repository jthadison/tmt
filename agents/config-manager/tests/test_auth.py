"""
Tests for API Authentication
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth import APIKeyAuth, generate_new_api_key
from fastapi import HTTPException


class TestAPIKeyAuth:
    """Test API key authentication"""

    def test_no_keys_configured_allows_access(self):
        """Test that no keys configured allows access (dev mode)"""
        # Clear environment
        os.environ.pop("CONFIG_MANAGER_API_KEYS_RW", None)
        os.environ.pop("CONFIG_MANAGER_API_KEYS_RO", None)
        os.environ.pop("CONFIG_MANAGER_MASTER_KEY", None)

        auth = APIKeyAuth()

        # Should allow access when no key provided (no auth configured)
        result = auth.validate_api_key(None, require_write=False)
        assert result is True

    def test_valid_read_write_key(self):
        """Test valid read-write API key"""
        test_key = "test_rw_key_123"
        os.environ["CONFIG_MANAGER_API_KEYS_RW"] = test_key

        auth = APIKeyAuth()

        # Should allow access with valid key
        result = auth.validate_api_key(test_key, require_write=True)
        assert result is True

        # Cleanup
        os.environ.pop("CONFIG_MANAGER_API_KEYS_RW")

    def test_valid_read_only_key(self):
        """Test valid read-only API key"""
        test_key = "test_ro_key_456"
        os.environ["CONFIG_MANAGER_API_KEYS_RO"] = test_key

        auth = APIKeyAuth()

        # Should allow read access
        result = auth.validate_api_key(test_key, require_write=False)
        assert result is True

        # Cleanup
        os.environ.pop("CONFIG_MANAGER_API_KEYS_RO")

    def test_read_only_key_denied_write_access(self):
        """Test read-only key is denied write access"""
        test_key = "test_ro_key_789"
        os.environ["CONFIG_MANAGER_API_KEYS_RO"] = test_key

        auth = APIKeyAuth()

        # Should deny write access
        with pytest.raises(HTTPException) as exc_info:
            auth.validate_api_key(test_key, require_write=True)

        assert exc_info.value.status_code == 403
        assert "Read-only" in exc_info.value.detail

        # Cleanup
        os.environ.pop("CONFIG_MANAGER_API_KEYS_RO")

    def test_invalid_api_key(self):
        """Test invalid API key is rejected"""
        valid_key = "valid_key_123"
        invalid_key = "invalid_key_456"
        os.environ["CONFIG_MANAGER_API_KEYS_RW"] = valid_key

        auth = APIKeyAuth()

        # Should reject invalid key
        with pytest.raises(HTTPException) as exc_info:
            auth.validate_api_key(invalid_key, require_write=False)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

        # Cleanup
        os.environ.pop("CONFIG_MANAGER_API_KEYS_RW")

    def test_master_key_allows_all_access(self):
        """Test master key allows all access"""
        master_key = "master_secret_key"
        os.environ["CONFIG_MANAGER_MASTER_KEY"] = master_key

        auth = APIKeyAuth()

        # Should allow both read and write with master key
        assert auth.validate_api_key(master_key, require_write=True) is True
        assert auth.validate_api_key(master_key, require_write=False) is True

        # Cleanup
        os.environ.pop("CONFIG_MANAGER_MASTER_KEY")

    def test_multiple_keys_comma_separated(self):
        """Test multiple API keys comma-separated"""
        keys = "key1,key2,key3"
        os.environ["CONFIG_MANAGER_API_KEYS_RW"] = keys

        auth = APIKeyAuth()

        # All keys should be valid
        assert auth.validate_api_key("key1", require_write=True) is True
        assert auth.validate_api_key("key2", require_write=True) is True
        assert auth.validate_api_key("key3", require_write=True) is True

        # Cleanup
        os.environ.pop("CONFIG_MANAGER_API_KEYS_RW")

    def test_generate_api_key(self):
        """Test API key generation"""
        result = generate_new_api_key()

        assert "api_key" in result
        assert "instructions" in result
        assert len(result["api_key"]) > 20  # Should be reasonably long
        assert "CONFIG_MANAGER_API_KEYS" in result["instructions"]

    def test_missing_api_key_when_auth_enabled(self):
        """Test missing API key when auth is enabled"""
        os.environ["CONFIG_MANAGER_API_KEYS_RW"] = "some_key"

        auth = APIKeyAuth()

        # Should reject when no key provided
        with pytest.raises(HTTPException) as exc_info:
            auth.validate_api_key(None, require_write=False)

        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

        # Cleanup
        os.environ.pop("CONFIG_MANAGER_API_KEYS_RW")
