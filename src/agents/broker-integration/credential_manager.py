"""
OANDA Credential Manager with HashiCorp Vault Integration
Story 8.1 - Task 1: Set up secure credential storage
"""
import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import hvac
from cryptography.fernet import Fernet
import aiohttp
import json

logger = logging.getLogger(__name__)

class CredentialValidationError(Exception):
    """Raised when credential validation fails"""
    pass

class VaultConnectionError(Exception):
    """Raised when Vault connection fails"""
    pass

class OandaCredentialManager:
    """Manages OANDA API credentials with secure storage in HashiCorp Vault"""
    
    def __init__(self, vault_url: str, vault_token: str, encryption_key: Optional[bytes] = None):
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.vault_client = hvac.Client(url=vault_url, token=vault_token)
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self._audit_events = []
        
        # OANDA API endpoints for validation
        self.oanda_endpoints = {
            'practice': 'https://api-fxpractice.oanda.com',
            'live': 'https://api-fxtrade.oanda.com'
        }
    
    async def store_credentials(self, user_id: str, credentials: Dict[str, Any]) -> bool:
        """
        Store OANDA API credentials securely in Vault
        
        Args:
            user_id: Unique user identifier
            credentials: Dict containing api_key, account_id, environment
            
        Returns:
            bool: True if successful
            
        Raises:
            CredentialValidationError: If credentials are invalid
            VaultConnectionError: If Vault storage fails
        """
        logger.info(f"Storing credentials for user: {user_id}")
        
        # Validate credentials first
        if not await self.validate_credentials(credentials):
            raise CredentialValidationError("Invalid OANDA credentials provided")
        
        # Encrypt sensitive data
        encrypted_credentials = self._encrypt_credentials(credentials)
        
        # Prepare metadata
        metadata = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'environment': credentials.get('environment', 'practice'),
            'validated': True
        }
        
        try:
            # Store in Vault
            vault_path = f"secret/oanda/{user_id}"
            self.vault_client.secrets.kv.v2.create_or_update_secret(
                path=vault_path,
                secret={
                    'credentials': encrypted_credentials,
                    'metadata': metadata
                }
            )
            
            # Audit log
            await self._audit_credential_access(user_id, "store", success=True)
            logger.info(f"Credentials stored successfully for user: {user_id}")
            return True
            
        except Exception as e:
            await self._audit_credential_access(user_id, "store", success=False, error=str(e))
            logger.error(f"Failed to store credentials for user {user_id}: {e}")
            raise VaultConnectionError(f"Vault storage failed: {e}")
    
    async def retrieve_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt OANDA credentials from Vault
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with decrypted credentials or None if not found
        """
        logger.info(f"Retrieving credentials for user: {user_id}")
        
        try:
            vault_path = f"secret/oanda/{user_id}"
            response = self.vault_client.secrets.kv.v2.read_secret_version(path=vault_path)
            
            if not response or 'data' not in response:
                logger.warning(f"No credentials found for user: {user_id}")
                return None
            
            secret_data = response['data']['data']
            encrypted_credentials = secret_data['credentials']
            
            # Decrypt credentials
            credentials = self._decrypt_credentials(encrypted_credentials)
            
            # Audit log
            await self._audit_credential_access(user_id, "retrieve", success=True)
            logger.info(f"Credentials retrieved successfully for user: {user_id}")
            
            return credentials
            
        except Exception as e:
            await self._audit_credential_access(user_id, "retrieve", success=False, error=str(e))
            logger.error(f"Failed to retrieve credentials for user {user_id}: {e}")
            return None
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate OANDA credentials by making API call
        
        Args:
            credentials: Dict containing api_key, account_id, environment
            
        Returns:
            bool: True if credentials are valid
        """
        required_fields = ['api_key', 'account_id', 'environment']
        if not all(field in credentials for field in required_fields):
            logger.error("Missing required credential fields")
            return False
        
        api_key = credentials['api_key']
        account_id = credentials['account_id']
        environment = credentials['environment']
        
        if environment not in ['practice', 'live']:
            logger.error(f"Invalid environment: {environment}")
            return False
        
        try:
            # Test API connection
            base_url = self.oanda_endpoints[environment]
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Test with account details endpoint
                url = f"{base_url}/v3/accounts/{account_id}"
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"Credentials validated successfully for account: {account_id}")
                        return True
                    else:
                        logger.error(f"API validation failed with status: {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            logger.error("Credential validation timed out")
            return False
        except Exception as e:
            logger.error(f"Credential validation error: {e}")
            return False
    
    async def rotate_credentials(self, user_id: str, new_credentials: Dict[str, Any]) -> bool:
        """
        Rotate user credentials with validation
        
        Args:
            user_id: User identifier
            new_credentials: New credential set
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Rotating credentials for user: {user_id}")
        
        # Validate new credentials first
        if not await self.validate_credentials(new_credentials):
            raise CredentialValidationError("New credentials are invalid")
        
        # Store old credentials as backup
        old_credentials = await self.retrieve_credentials(user_id)
        if old_credentials:
            backup_path = f"secret/oanda/{user_id}/backup/{datetime.utcnow().isoformat()}"
            try:
                self.vault_client.secrets.kv.v2.create_or_update_secret(
                    path=backup_path,
                    secret={'credentials': self._encrypt_credentials(old_credentials)}
                )
            except Exception as e:
                logger.warning(f"Failed to backup old credentials: {e}")
        
        # Store new credentials
        success = await self.store_credentials(user_id, new_credentials)
        
        if success:
            await self._audit_credential_access(user_id, "rotate", success=True)
            logger.info(f"Credentials rotated successfully for user: {user_id}")
        
        return success
    
    def _encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt credentials using Fernet"""
        credentials_json = json.dumps(credentials)
        encrypted = self.cipher_suite.encrypt(credentials_json.encode())
        return encrypted.decode()
    
    def _decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """Decrypt credentials using Fernet"""
        decrypted = self.cipher_suite.decrypt(encrypted_credentials.encode())
        return json.loads(decrypted.decode())
    
    async def _audit_credential_access(self, user_id: str, action: str, success: bool, error: str = None):
        """Log credential access for audit trail"""
        audit_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'success': success,
            'error': error
        }
        
        self._audit_events.append(audit_event)
        logger.info(f"Audit: {action} credentials for {user_id} - Success: {success}")
        
        # In production, this would write to a dedicated audit log system
        if len(self._audit_events) > 1000:  # Rotate audit events
            self._audit_events = self._audit_events[-500:]
    
    def get_audit_trail(self, user_id: Optional[str] = None) -> list:
        """Get audit trail for credential access"""
        if user_id:
            return [event for event in self._audit_events if event['user_id'] == user_id]
        return self._audit_events.copy()
    
    async def delete_credentials(self, user_id: str) -> bool:
        """
        Securely delete user credentials
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if successful
        """
        try:
            vault_path = f"secret/oanda/{user_id}"
            self.vault_client.secrets.kv.v2.delete_metadata_and_all_versions(path=vault_path)
            
            await self._audit_credential_access(user_id, "delete", success=True)
            logger.info(f"Credentials deleted successfully for user: {user_id}")
            return True
            
        except Exception as e:
            await self._audit_credential_access(user_id, "delete", success=False, error=str(e))
            logger.error(f"Failed to delete credentials for user {user_id}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check Vault connection health"""
        try:
            # Test Vault connection
            if self.vault_client.is_authenticated():
                vault_status = "healthy"
            else:
                vault_status = "authentication_failed"
                
            return {
                'vault_connection': vault_status,
                'vault_url': self.vault_url,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'vault_connection': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }