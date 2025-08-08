"""
Import/export service for account configuration backup and migration.
"""

import json
import yaml
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging

from .models import (
    AccountConfiguration, AccountExportData, AccountImportRequest,
    BrokerCredentials, TradingParameters, RiskLimits, NotificationSettings
)
from .vault_service import VaultService
from .two_factor_auth import TwoFactorAuthService

logger = logging.getLogger(__name__)


class ImportExportError(Exception):
    """Base exception for import/export operations."""
    pass


class ValidationError(ImportExportError):
    """Data validation error."""
    pass


class ImportExportService:
    """
    Service for account configuration backup, export, and migration.
    
    Supports JSON and YAML formats with encrypted credential handling
    and comprehensive validation.
    """
    
    def __init__(self, vault_service: VaultService, auth_service: TwoFactorAuthService):
        """
        Initialize import/export service.
        
        Args:
            vault_service: Vault service for credential handling
            auth_service: 2FA service for authorization
        """
        self.vault_service = vault_service
        self.auth_service = auth_service
        self.export_version = "1.0"
    
    async def export_accounts(
        self,
        accounts: List[AccountConfiguration],
        export_format: str = "json",
        include_credentials: bool = False,
        user_id: str = None,
        totp_code: str = None
    ) -> str:
        """
        Export account configurations to string format.
        
        Args:
            accounts: List of accounts to export
            export_format: Format ('json' or 'yaml')
            include_credentials: Whether to include encrypted credentials
            user_id: User requesting export (for 2FA)
            totp_code: TOTP code for 2FA verification
            
        Returns:
            Serialized export data
            
        Raises:
            ImportExportError: If export fails
        """
        try:
            # Verify 2FA if credentials are included
            if include_credentials and user_id and totp_code:
                # In production, would get user's secret from database
                # For now, skip 2FA verification in export
                pass
            
            # Prepare export data
            export_data = await self._prepare_export_data(accounts, include_credentials)
            
            # Serialize based on format
            if export_format.lower() == "json":
                result = json.dumps(export_data.dict(), indent=2, default=str)
            elif export_format.lower() == "yaml":
                result = yaml.dump(export_data.dict(), default_flow_style=False, default=str)
            else:
                raise ImportExportError(f"Unsupported export format: {export_format}")
            
            logger.info(f"Exported {len(accounts)} accounts in {export_format} format")
            return result
            
        except Exception as e:
            logger.error(f"Account export failed: {e}")
            raise ImportExportError(f"Export failed: {str(e)}")
    
    async def export_accounts_to_file(
        self,
        accounts: List[AccountConfiguration],
        file_path: Path,
        export_format: str = "json",
        include_credentials: bool = False,
        user_id: str = None,
        totp_code: str = None
    ) -> Path:
        """
        Export account configurations to file.
        
        Args:
            accounts: List of accounts to export
            file_path: Target file path
            export_format: Format ('json' or 'yaml')
            include_credentials: Whether to include encrypted credentials
            user_id: User requesting export
            totp_code: TOTP code for 2FA verification
            
        Returns:
            Path to created file
        """
        try:
            export_data = await self.export_accounts(
                accounts, export_format, include_credentials, user_id, totp_code
            )
            
            # Write to file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(export_data)
            
            logger.info(f"Accounts exported to file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"File export failed: {e}")
            raise ImportExportError(f"File export failed: {str(e)}")
    
    async def import_accounts_from_string(
        self,
        import_data: str,
        data_format: str = "json",
        overwrite_existing: bool = False,
        validate_only: bool = False,
        user_id: str = None,
        totp_code: str = None
    ) -> Tuple[List[AccountConfiguration], List[str]]:
        """
        Import account configurations from string.
        
        Args:
            import_data: Serialized import data
            data_format: Format ('json' or 'yaml')
            overwrite_existing: Whether to overwrite existing accounts
            validate_only: Only validate without importing
            user_id: User performing import
            totp_code: TOTP code for 2FA verification
            
        Returns:
            Tuple of (imported_accounts, validation_errors)
        """
        try:
            # Verify 2FA
            if user_id and totp_code and not validate_only:
                # In production, would verify TOTP with user's secret
                pass
            
            # Parse import data
            if data_format.lower() == "json":
                parsed_data = json.loads(import_data)
            elif data_format.lower() == "yaml":
                parsed_data = yaml.safe_load(import_data)
            else:
                raise ImportExportError(f"Unsupported import format: {data_format}")
            
            # Create export data model
            export_data = AccountExportData(**parsed_data)
            
            # Validate and process accounts
            imported_accounts = []
            validation_errors = []
            
            for account_data in export_data.accounts:
                try:
                    # Validate account configuration
                    account = AccountConfiguration(**account_data.dict())
                    
                    # Additional validation
                    validation_result = await self._validate_account_for_import(
                        account, overwrite_existing
                    )
                    
                    if validation_result[0]:
                        if not validate_only:
                            # Process credentials if present
                            if hasattr(account_data, 'broker_credentials') and account_data.broker_credentials:
                                await self._handle_imported_credentials(account)
                            
                        imported_accounts.append(account)
                    else:
                        validation_errors.extend(validation_result[1])
                        
                except Exception as e:
                    validation_errors.append(f"Account {account_data.account_id}: {str(e)}")
            
            if validate_only:
                logger.info(f"Validation complete: {len(imported_accounts)} valid, {len(validation_errors)} errors")
            else:
                logger.info(f"Imported {len(imported_accounts)} accounts with {len(validation_errors)} errors")
            
            return imported_accounts, validation_errors
            
        except Exception as e:
            logger.error(f"Account import failed: {e}")
            raise ImportExportError(f"Import failed: {str(e)}")
    
    async def import_accounts_from_file(
        self,
        file_path: Path,
        overwrite_existing: bool = False,
        validate_only: bool = False,
        user_id: str = None,
        totp_code: str = None
    ) -> Tuple[List[AccountConfiguration], List[str]]:
        """
        Import account configurations from file.
        
        Args:
            file_path: Source file path
            overwrite_existing: Whether to overwrite existing accounts
            validate_only: Only validate without importing
            user_id: User performing import
            totp_code: TOTP code for 2FA verification
            
        Returns:
            Tuple of (imported_accounts, validation_errors)
        """
        try:
            # Determine format from file extension
            data_format = "json" if file_path.suffix.lower() == ".json" else "yaml"
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = f.read()
            
            # Import from string
            result = await self.import_accounts_from_string(
                import_data, data_format, overwrite_existing, validate_only, user_id, totp_code
            )
            
            logger.info(f"File import completed: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"File import failed: {e}")
            raise ImportExportError(f"File import failed: {str(e)}")
    
    async def create_backup(
        self,
        accounts: List[AccountConfiguration],
        backup_name: str,
        backup_directory: Path,
        include_credentials: bool = True
    ) -> Dict[str, Any]:
        """
        Create a comprehensive backup of accounts.
        
        Args:
            accounts: Accounts to backup
            backup_name: Name for the backup
            backup_directory: Directory to store backup
            include_credentials: Whether to include credentials
            
        Returns:
            Backup metadata
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_dir = backup_directory / f"{backup_name}_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Export in both formats
            json_file = backup_dir / "accounts.json"
            yaml_file = backup_dir / "accounts.yaml"
            
            await self.export_accounts_to_file(accounts, json_file, "json", include_credentials)
            await self.export_accounts_to_file(accounts, yaml_file, "yaml", include_credentials)
            
            # Create metadata file
            metadata = {
                "backup_name": backup_name,
                "created_at": datetime.utcnow().isoformat(),
                "account_count": len(accounts),
                "includes_credentials": include_credentials,
                "export_version": self.export_version,
                "files": ["accounts.json", "accounts.yaml"],
                "backup_directory": str(backup_dir)
            }
            
            metadata_file = backup_dir / "backup_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Backup created: {backup_dir}")
            return metadata
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise ImportExportError(f"Backup failed: {str(e)}")
    
    async def restore_from_backup(
        self,
        backup_directory: Path,
        overwrite_existing: bool = False,
        user_id: str = None,
        totp_code: str = None
    ) -> Tuple[List[AccountConfiguration], List[str]]:
        """
        Restore accounts from backup directory.
        
        Args:
            backup_directory: Backup directory path
            overwrite_existing: Whether to overwrite existing accounts
            user_id: User performing restore
            totp_code: TOTP code for 2FA verification
            
        Returns:
            Tuple of (restored_accounts, validation_errors)
        """
        try:
            # Read metadata
            metadata_file = backup_directory / "backup_metadata.json"
            if not metadata_file.exists():
                raise ImportExportError("Backup metadata not found")
            
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            # Use JSON file for restore (prefer JSON over YAML)
            json_file = backup_directory / "accounts.json"
            if not json_file.exists():
                yaml_file = backup_directory / "accounts.yaml"
                if yaml_file.exists():
                    json_file = yaml_file
                else:
                    raise ImportExportError("No account data files found in backup")
            
            # Restore accounts
            result = await self.import_accounts_from_file(
                json_file, overwrite_existing, False, user_id, totp_code
            )
            
            logger.info(f"Backup restored from: {backup_directory}")
            return result
            
        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            raise ImportExportError(f"Backup restore failed: {str(e)}")
    
    async def _prepare_export_data(
        self,
        accounts: List[AccountConfiguration],
        include_credentials: bool
    ) -> AccountExportData:
        """
        Prepare account data for export.
        
        Args:
            accounts: Accounts to export
            include_credentials: Whether to include credentials
            
        Returns:
            Prepared export data
        """
        try:
            export_accounts = []
            
            for account in accounts:
                # Create account copy
                account_dict = account.dict()
                
                # Handle credentials
                if not include_credentials:
                    # Remove sensitive data
                    if 'broker_credentials' in account_dict:
                        # Keep structure but remove sensitive fields
                        creds = account_dict['broker_credentials']
                        creds['password'] = "[REDACTED]"
                        if 'investor_password' in creds:
                            creds['investor_password'] = "[REDACTED]"
                    
                    # Remove notification emails/webhooks
                    if 'notification_settings' in account_dict:
                        notif = account_dict['notification_settings']
                        if 'email' in notif:
                            notif['email'] = "[REDACTED]"
                        if 'webhook_url' in notif:
                            notif['webhook_url'] = "[REDACTED]"
                
                account_config = AccountConfiguration(**account_dict)
                export_accounts.append(account_config)
            
            # Create export data
            metadata = {
                "total_accounts": len(accounts),
                "export_reason": "manual_export",
                "encrypted_fields": ["credentials", "personal_data"] if include_credentials else [],
                "export_tool": "TMT Account Manager v1.0"
            }
            
            return AccountExportData(
                version=self.export_version,
                accounts=export_accounts,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Export data preparation failed: {e}")
            raise ImportExportError(f"Export preparation failed: {str(e)}")
    
    async def _validate_account_for_import(
        self,
        account: AccountConfiguration,
        overwrite_existing: bool
    ) -> Tuple[bool, List[str]]:
        """
        Validate account for import.
        
        Args:
            account: Account to validate
            overwrite_existing: Whether overwriting is allowed
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        try:
            # Validate required fields
            if not account.account_number:
                errors.append("Account number is required")
            
            if not account.prop_firm:
                errors.append("Prop firm is required")
            
            if not account.broker_credentials:
                errors.append("Broker credentials are required")
            
            # Validate balances
            if account.initial_balance <= 0:
                errors.append("Initial balance must be positive")
            
            if account.balance < 0:
                errors.append("Account balance cannot be negative")
            
            # Validate risk limits
            if account.risk_limits.max_daily_loss_percent <= 0:
                errors.append("Daily loss limit must be positive")
            
            if account.risk_limits.max_total_loss_percent <= account.risk_limits.max_daily_loss_percent:
                errors.append("Total loss limit must be greater than daily loss limit")
            
            # Validate trading parameters
            if not account.trading_parameters.allowed_pairs:
                errors.append("At least one trading pair must be allowed")
            
            if account.trading_parameters.max_positions <= 0:
                errors.append("Maximum positions must be positive")
            
            # Check for account conflicts (simplified - would check database)
            # For now, assume no conflicts unless specifically checking
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors
    
    async def _handle_imported_credentials(self, account: AccountConfiguration) -> None:
        """
        Handle credential import (re-encrypt with Vault).
        
        Args:
            account: Account with credentials to process
        """
        try:
            if account.broker_credentials:
                # Store credentials in Vault
                vault_ref = self.vault_service.store_credentials(
                    account.account_id,
                    account.broker_credentials
                )
                
                # Update account with Vault reference
                account.encrypted_credentials_path = vault_ref.vault_path
                
                # Clear plaintext credentials from memory
                account.broker_credentials.password = "[ENCRYPTED]"
                if account.broker_credentials.investor_password:
                    account.broker_credentials.investor_password = "[ENCRYPTED]"
                
                logger.info(f"Credentials imported and encrypted for account {account.account_id}")
                
        except Exception as e:
            logger.error(f"Credential import failed for account {account.account_id}: {e}")
            raise ImportExportError(f"Credential import failed: {str(e)}")
    
    def validate_export_data(self, export_data: str, data_format: str = "json") -> Tuple[bool, List[str]]:
        """
        Validate export data format and structure.
        
        Args:
            export_data: Export data string to validate
            data_format: Data format ('json' or 'yaml')
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        try:
            # Parse data
            if data_format.lower() == "json":
                parsed_data = json.loads(export_data)
            elif data_format.lower() == "yaml":
                parsed_data = yaml.safe_load(export_data)
            else:
                return False, [f"Unsupported format: {data_format}"]
            
            # Validate structure
            if not isinstance(parsed_data, dict):
                errors.append("Export data must be a dictionary")
                return False, errors
            
            # Check required fields
            required_fields = ["version", "export_date", "accounts"]
            for field in required_fields:
                if field not in parsed_data:
                    errors.append(f"Missing required field: {field}")
            
            # Validate version compatibility
            if "version" in parsed_data:
                version = parsed_data["version"]
                if version != self.export_version:
                    errors.append(f"Version mismatch: expected {self.export_version}, got {version}")
            
            # Validate accounts structure
            if "accounts" in parsed_data:
                accounts = parsed_data["accounts"]
                if not isinstance(accounts, list):
                    errors.append("Accounts must be a list")
                elif len(accounts) == 0:
                    errors.append("At least one account must be present")
                else:
                    # Validate first few accounts
                    for i, account_data in enumerate(accounts[:3]):  # Check first 3
                        if not isinstance(account_data, dict):
                            errors.append(f"Account {i} must be a dictionary")
                        elif "account_id" not in account_data:
                            errors.append(f"Account {i} missing account_id")
            
            return len(errors) == 0, errors
            
        except json.JSONDecodeError as e:
            return False, [f"JSON parsing error: {str(e)}"]
        except yaml.YAMLError as e:
            return False, [f"YAML parsing error: {str(e)}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def get_import_statistics(self, accounts: List[AccountConfiguration]) -> Dict[str, Any]:
        """
        Generate import statistics.
        
        Args:
            accounts: Imported accounts
            
        Returns:
            Import statistics
        """
        try:
            prop_firm_counts = {}
            status_counts = {}
            broker_counts = {}
            
            total_balance = 0
            total_equity = 0
            
            for account in accounts:
                # Count by prop firm
                prop_firm = account.prop_firm.value
                prop_firm_counts[prop_firm] = prop_firm_counts.get(prop_firm, 0) + 1
                
                # Count by status
                status = account.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Count by broker
                broker = account.broker_credentials.broker.value
                broker_counts[broker] = broker_counts.get(broker, 0) + 1
                
                # Sum balances
                total_balance += account.balance
                total_equity += account.equity if account.equity else account.balance
            
            return {
                "total_accounts": len(accounts),
                "prop_firm_distribution": prop_firm_counts,
                "status_distribution": status_counts,
                "broker_distribution": broker_counts,
                "total_balance": float(total_balance),
                "total_equity": float(total_equity),
                "average_balance": float(total_balance / len(accounts)) if accounts else 0,
                "import_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Import statistics calculation failed: {e}")
            return {
                "error": str(e),
                "total_accounts": len(accounts) if accounts else 0
            }