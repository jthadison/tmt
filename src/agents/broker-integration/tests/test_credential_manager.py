"""
Tests for OandaCredentialManager
Story 8.1 - Task 1: Secure credential storage
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from credential_manager import (
    OandaCredentialManager, 
    CredentialValidationError, 
    VaultConnectionError
)

class TestOandaCredentialManager:
    """Test credential management functionality"""
    
    @pytest.mark.asyncio
    async def test_store_credentials_success(self, credential_manager, sample_credentials):
        """Test successful credential storage"""
        with patch.object(credential_manager, 'validate_credentials', return_value=True):
            result = await credential_manager.store_credentials('test-user', sample_credentials)
            
            assert result is True
            credential_manager.vault_client.secrets.kv.v2.create_or_update_secret.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_credentials_invalid(self, credential_manager, sample_credentials):
        """Test storing invalid credentials"""
        with patch.object(credential_manager, 'validate_credentials', return_value=False):
            with pytest.raises(CredentialValidationError):
                await credential_manager.store_credentials('test-user', sample_credentials)
    
    @pytest.mark.asyncio
    async def test_store_credentials_vault_error(self, credential_manager, sample_credentials):
        """Test Vault storage error"""
        with patch.object(credential_manager, 'validate_credentials', return_value=True):
            credential_manager.vault_client.secrets.kv.v2.create_or_update_secret.side_effect = Exception("Vault error")
            
            with pytest.raises(VaultConnectionError):
                await credential_manager.store_credentials('test-user', sample_credentials)
    
    @pytest.mark.asyncio
    async def test_retrieve_credentials_success(self, credential_manager, sample_credentials):
        """Test successful credential retrieval"""
        # Mock Vault response
        encrypted_creds = credential_manager._encrypt_credentials(sample_credentials)
        vault_response = {
            'data': {
                'data': {
                    'credentials': encrypted_creds,
                    'metadata': {'user_id': 'test-user'}
                }
            }
        }
        
        credential_manager.vault_client.secrets.kv.v2.read_secret_version.return_value = vault_response
        
        result = await credential_manager.retrieve_credentials('test-user')
        
        assert result is not None
        assert result['api_key'] == sample_credentials['api_key']
        assert result['account_id'] == sample_credentials['account_id']
        assert result['environment'] == sample_credentials['environment']
    
    @pytest.mark.asyncio
    async def test_retrieve_credentials_not_found(self, credential_manager):
        """Test retrieving non-existent credentials"""
        credential_manager.vault_client.secrets.kv.v2.read_secret_version.return_value = None
        
        result = await credential_manager.retrieve_credentials('nonexistent-user')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, credential_manager, sample_credentials, mock_aiohttp_session):
        """Test successful credential validation"""
        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
            result = await credential_manager.validate_credentials(sample_credentials)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_credentials_missing_fields(self, credential_manager):
        """Test validation with missing fields"""
        incomplete_creds = {'api_key': 'test-key'}
        
        result = await credential_manager.validate_credentials(incomplete_creds)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_credentials_invalid_environment(self, credential_manager):
        """Test validation with invalid environment"""
        invalid_creds = {
            'api_key': 'test-key',
            'account_id': 'test-account',
            'environment': 'invalid'
        }
        
        result = await credential_manager.validate_credentials(invalid_creds)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_credentials_api_error(self, credential_manager, sample_credentials):
        """Test validation with API error"""
        mock_session = AsyncMock()
        
        # Mock failed response
        response = AsyncMock()
        response.status = 401  # Unauthorized
        
        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.get.return_value = context_manager
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await credential_manager.validate_credentials(sample_credentials)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_rotate_credentials_success(self, credential_manager, sample_credentials):
        """Test successful credential rotation"""
        # Mock existing credentials
        credential_manager.vault_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {'data': {'credentials': credential_manager._encrypt_credentials(sample_credentials)}}
        }
        
        new_credentials = sample_credentials.copy()
        new_credentials['api_key'] = 'new-api-key-67890'
        
        with patch.object(credential_manager, 'validate_credentials', return_value=True):
            result = await credential_manager.rotate_credentials('test-user', new_credentials)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_credentials_success(self, credential_manager):
        """Test successful credential deletion"""
        result = await credential_manager.delete_credentials('test-user')
        
        assert result is True
        credential_manager.vault_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_credentials_error(self, credential_manager):
        """Test credential deletion with error"""
        credential_manager.vault_client.secrets.kv.v2.delete_metadata_and_all_versions.side_effect = Exception("Delete error")
        
        result = await credential_manager.delete_credentials('test-user')
        
        assert result is False
    
    def test_encrypt_decrypt_credentials(self, credential_manager, sample_credentials):
        """Test credential encryption and decryption"""
        encrypted = credential_manager._encrypt_credentials(sample_credentials)
        decrypted = credential_manager._decrypt_credentials(encrypted)
        
        assert decrypted == sample_credentials
    
    def test_health_check_healthy(self, credential_manager):
        """Test health check when Vault is healthy"""
        result = credential_manager.health_check()
        
        assert result['vault_connection'] == 'healthy'
        assert 'timestamp' in result
    
    def test_health_check_unhealthy(self, credential_manager):
        """Test health check when Vault is unhealthy"""
        credential_manager.vault_client.is_authenticated.return_value = False
        
        result = credential_manager.health_check()
        
        assert result['vault_connection'] == 'authentication_failed'
    
    def test_health_check_error(self, credential_manager):
        """Test health check with exception"""
        credential_manager.vault_client.is_authenticated.side_effect = Exception("Connection error")
        
        result = credential_manager.health_check()
        
        assert result['vault_connection'] == 'error'
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_audit_trail(self, credential_manager, sample_credentials):
        """Test audit trail functionality"""
        with patch.object(credential_manager, 'validate_credentials', return_value=True):
            await credential_manager.store_credentials('test-user', sample_credentials)
        
        audit_trail = credential_manager.get_audit_trail('test-user')
        
        assert len(audit_trail) > 0
        assert audit_trail[0]['user_id'] == 'test-user'
        assert audit_trail[0]['action'] == 'store'
        assert audit_trail[0]['success'] is True
    
    @pytest.mark.asyncio
    async def test_audit_trail_all_users(self, credential_manager, sample_credentials):
        """Test getting audit trail for all users"""
        with patch.object(credential_manager, 'validate_credentials', return_value=True):
            await credential_manager.store_credentials('user1', sample_credentials)
            await credential_manager.store_credentials('user2', sample_credentials)
        
        audit_trail = credential_manager.get_audit_trail()
        
        assert len(audit_trail) >= 2
        user_ids = [event['user_id'] for event in audit_trail]
        assert 'user1' in user_ids
        assert 'user2' in user_ids