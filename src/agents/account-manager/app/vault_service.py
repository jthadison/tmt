"""
HashiCorp Vault integration for secure credential storage.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from uuid import UUID

import hvac
from pydantic import BaseModel

from .models import BrokerCredentials, VaultCredentialReference

logger = logging.getLogger(__name__)


class VaultConfig(BaseModel):
    """Vault configuration settings."""
    url: str = "http://localhost:8200"
    token: Optional[str] = None
    mount_point: str = "secret"
    credential_path_prefix: str = "trading-accounts"
    timeout: int = 30
    verify_ssl: bool = True
    namespace: Optional[str] = None


class VaultError(Exception):
    """Base exception for Vault operations."""
    pass


class VaultAuthenticationError(VaultError):
    """Vault authentication failed."""
    pass


class VaultAccessError(VaultError):
    """Access denied to Vault resource."""
    pass


class VaultService:
    """
    Service for secure credential storage using HashiCorp Vault.
    
    Provides encryption, decryption, and management of sensitive broker
    credentials with audit logging and automatic key rotation support.
    """
    
    def __init__(self, config: VaultConfig):
        """
        Initialize Vault service.
        
        Args:
            config: Vault configuration
        """
        self.config = config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Vault client connection."""
        try:
            self.client = hvac.Client(
                url=self.config.url,
                token=self.config.token,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
                namespace=self.config.namespace
            )
            
            # Verify authentication
            if not self.client.is_authenticated():
                raise VaultAuthenticationError("Failed to authenticate with Vault")
            
            logger.info("Vault client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {e}")
            raise VaultError(f"Vault initialization failed: {str(e)}")
    
    def store_credentials(self, account_id: UUID, credentials: BrokerCredentials) -> VaultCredentialReference:
        """
        Store broker credentials securely in Vault.
        
        Args:
            account_id: Account identifier
            credentials: Broker credentials to encrypt and store
            
        Returns:
            Reference to stored credentials
        """
        try:
            # Create vault path
            vault_path = f"{self.config.credential_path_prefix}/{account_id}/credentials"
            
            # Prepare credential data
            credential_data = {
                "broker": credentials.broker.value,
                "server": credentials.server,
                "login": credentials.login,
                "password": credentials.password,
                "investor_password": credentials.investor_password,
                "stored_at": datetime.utcnow().isoformat(),
                "account_id": str(account_id)
            }
            
            # Store in Vault
            response = self.client.secrets.kv.v2.create_or_update_secret(
                mount_point=self.config.mount_point,
                path=vault_path,
                secret=credential_data
            )
            
            # Log successful storage (without sensitive data)
            logger.info(f"Credentials stored for account {account_id} at version {response['data']['version']}")
            
            # Create reference
            reference = VaultCredentialReference(
                vault_path=vault_path,
                version=response['data']['version'],
                created_at=datetime.utcnow()
            )
            
            # Log audit event
            self._log_audit_event("credentials_stored", account_id, {
                "vault_path": vault_path,
                "version": response['data']['version']
            })
            
            return reference
            
        except Exception as e:
            logger.error(f"Failed to store credentials for account {account_id}: {e}")
            raise VaultError(f"Credential storage failed: {str(e)}")
    
    def retrieve_credentials(self, reference: VaultCredentialReference) -> BrokerCredentials:
        """
        Retrieve broker credentials from Vault.
        
        Args:
            reference: Vault credential reference
            
        Returns:
            Decrypted broker credentials
        """
        try:
            # Retrieve from Vault
            response = self.client.secrets.kv.v2.read_secret_version(
                mount_point=self.config.mount_point,
                path=reference.vault_path,
                version=reference.version
            )
            
            credential_data = response['data']['data']
            
            # Create credentials object
            credentials = BrokerCredentials(
                broker=credential_data['broker'],
                server=credential_data['server'],
                login=credential_data['login'],
                password=credential_data['password'],
                investor_password=credential_data.get('investor_password')
            )
            
            # Update last accessed time
            reference.last_accessed = datetime.utcnow()
            
            # Log successful retrieval
            account_id = credential_data.get('account_id', 'unknown')
            logger.info(f"Credentials retrieved for account {account_id}")
            
            # Log audit event
            self._log_audit_event("credentials_retrieved", account_id, {
                "vault_path": reference.vault_path,
                "version": reference.version
            })
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to retrieve credentials from {reference.vault_path}: {e}")
            raise VaultError(f"Credential retrieval failed: {str(e)}")
    
    def rotate_credentials(self, account_id: UUID, old_reference: VaultCredentialReference, 
                          new_credentials: BrokerCredentials) -> VaultCredentialReference:
        """
        Rotate credentials by storing new version.
        
        Args:
            account_id: Account identifier
            old_reference: Previous credential reference
            new_credentials: New credentials to store
            
        Returns:
            New credential reference
        """
        try:
            # Store new credentials
            new_reference = self.store_credentials(account_id, new_credentials)
            
            # Mark old version with rotation timestamp
            self._mark_credentials_rotated(old_reference, account_id)
            
            logger.info(f"Credentials rotated for account {account_id}: v{old_reference.version} -> v{new_reference.version}")
            
            # Log audit event
            self._log_audit_event("credentials_rotated", account_id, {
                "old_version": old_reference.version,
                "new_version": new_reference.version,
                "vault_path": new_reference.vault_path
            })
            
            return new_reference
            
        except Exception as e:
            logger.error(f"Failed to rotate credentials for account {account_id}: {e}")
            raise VaultError(f"Credential rotation failed: {str(e)}")
    
    def delete_credentials(self, reference: VaultCredentialReference, account_id: UUID) -> None:
        """
        Permanently delete credentials from Vault.
        
        Args:
            reference: Credential reference to delete
            account_id: Account identifier for logging
        """
        try:
            # Delete all versions of the secret
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                mount_point=self.config.mount_point,
                path=reference.vault_path
            )
            
            logger.warning(f"Credentials permanently deleted for account {account_id}")
            
            # Log audit event
            self._log_audit_event("credentials_deleted", account_id, {
                "vault_path": reference.vault_path,
                "deleted_versions": "all"
            })
            
        except Exception as e:
            logger.error(f"Failed to delete credentials for account {account_id}: {e}")
            raise VaultError(f"Credential deletion failed: {str(e)}")
    
    def list_account_credentials(self, account_id: UUID) -> Dict[str, Any]:
        """
        List credential metadata for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Credential metadata
        """
        try:
            vault_path = f"{self.config.credential_path_prefix}/{account_id}/credentials"
            
            # Get metadata
            response = self.client.secrets.kv.v2.read_secret_metadata(
                mount_point=self.config.mount_point,
                path=vault_path
            )
            
            metadata = response['data']
            
            return {
                "vault_path": vault_path,
                "current_version": metadata['current_version'],
                "versions": metadata['versions'],
                "created_time": metadata['created_time'],
                "updated_time": metadata['updated_time']
            }
            
        except hvac.exceptions.InvalidPath:
            return None
        except Exception as e:
            logger.error(f"Failed to list credentials for account {account_id}: {e}")
            raise VaultError(f"Credential listing failed: {str(e)}")
    
    def purge_account_credentials(self, account_id: UUID) -> None:
        """
        Emergency purge all credentials for an account.
        
        Args:
            account_id: Account identifier
        """
        try:
            # List all paths under the account
            account_path = f"{self.config.credential_path_prefix}/{account_id}"
            
            # Delete credentials
            credentials_path = f"{account_path}/credentials"
            try:
                self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                    mount_point=self.config.mount_point,
                    path=credentials_path
                )
            except hvac.exceptions.InvalidPath:
                pass  # Already deleted
            
            logger.critical(f"EMERGENCY PURGE: All credentials deleted for account {account_id}")
            
            # Log audit event
            self._log_audit_event("credentials_purged", account_id, {
                "purge_type": "emergency",
                "paths_deleted": [credentials_path]
            })
            
        except Exception as e:
            logger.error(f"Failed to purge credentials for account {account_id}: {e}")
            raise VaultError(f"Credential purge failed: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Vault service health.
        
        Returns:
            Health status information
        """
        try:
            # Check authentication
            is_authenticated = self.client.is_authenticated()
            
            # Check seal status
            seal_status = self.client.sys.read_seal_status()
            
            # Test write/read capability
            test_path = f"{self.config.credential_path_prefix}/health-check"
            test_data = {"timestamp": datetime.utcnow().isoformat()}
            
            try:
                self.client.secrets.kv.v2.create_or_update_secret(
                    mount_point=self.config.mount_point,
                    path=test_path,
                    secret=test_data
                )
                
                # Clean up test data
                self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                    mount_point=self.config.mount_point,
                    path=test_path
                )
                
                write_test_passed = True
            except Exception:
                write_test_passed = False
            
            return {
                "vault_url": self.config.url,
                "authenticated": is_authenticated,
                "sealed": seal_status.get('sealed', True),
                "write_test_passed": write_test_passed,
                "mount_point": self.config.mount_point,
                "status": "healthy" if (is_authenticated and not seal_status.get('sealed', True) and write_test_passed) else "unhealthy"
            }
            
        except Exception as e:
            logger.error(f"Vault health check failed: {e}")
            return {
                "vault_url": self.config.url,
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _mark_credentials_rotated(self, reference: VaultCredentialReference, account_id: UUID) -> None:
        """Mark old credentials as rotated."""
        try:
            # This would typically update metadata to mark as rotated
            # For now, we'll log the rotation
            logger.info(f"Marked credentials as rotated for account {account_id}, version {reference.version}")
            
        except Exception as e:
            logger.warning(f"Failed to mark credentials as rotated: {e}")
    
    def _log_audit_event(self, event_type: str, account_id: str, metadata: Dict[str, Any]) -> None:
        """
        Log audit event for credential operations.
        
        Args:
            event_type: Type of operation
            account_id: Account identifier
            metadata: Additional event data
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "account_id": str(account_id),
            "service": "vault_service",
            "metadata": metadata
        }
        
        # In production, this would go to a dedicated audit log
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    def get_credential_versions(self, account_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all versions of credentials for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List of credential versions
        """
        try:
            metadata = self.list_account_credentials(account_id)
            
            if not metadata:
                return []
            
            versions = []
            for version_num, version_data in metadata['versions'].items():
                if not version_data.get('deleted_time'):  # Only active versions
                    versions.append({
                        "version": int(version_num),
                        "created_time": version_data['created_time'],
                        "is_current": int(version_num) == metadata['current_version']
                    })
            
            return sorted(versions, key=lambda x: x['version'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get credential versions for account {account_id}: {e}")
            return []


class VaultServiceFactory:
    """Factory for creating Vault service instances."""
    
    _instance = None
    _config = None
    
    @classmethod
    def create(cls, config: VaultConfig = None) -> VaultService:
        """
        Create or return existing Vault service instance.
        
        Args:
            config: Vault configuration (optional for singleton)
            
        Returns:
            VaultService instance
        """
        if cls._instance is None or config is not None:
            if config is None:
                # Use default configuration
                config = VaultConfig()
            
            cls._config = config
            cls._instance = VaultService(config)
        
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance."""
        cls._instance = None
        cls._config = None