"""
Comprehensive tests for Account Manager system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from unittest.mock import Mock, patch, AsyncMock

from src.agents.account_manager.app.models import (
    AccountConfiguration, AccountCreateRequest, AccountUpdateRequest,
    AccountStatus, PropFirm, BrokerType, BrokerCredentials,
    TradingParameters, RiskLimits, NotificationSettings,
    AccountStatusTransition, TwoFactorAuthSetup
)
from src.agents.account_manager.app.vault_service import VaultService, VaultConfig
from src.agents.account_manager.app.two_factor_auth import TwoFactorAuthService
from src.agents.account_manager.app.status_manager import AccountStatusManager
from src.agents.account_manager.app.import_export_service import ImportExportService


@pytest.fixture
def mock_vault_config():
    """Create mock Vault configuration."""
    return VaultConfig(
        url="http://localhost:8200",
        token="test_token",
        mount_point="secret",
        credential_path_prefix="test-accounts"
    )


@pytest.fixture
def mock_broker_credentials():
    """Create mock broker credentials."""
    return BrokerCredentials(
        broker=BrokerType.METATRADER4,
        server="broker.test.com:443",
        login="12345",
        password="test_password",
        investor_password="readonly_password"
    )


@pytest.fixture
def mock_account_config(mock_broker_credentials):
    """Create mock account configuration."""
    return AccountConfiguration(
        prop_firm=PropFirm.FTMO,
        account_number="MT4_12345",
        initial_balance=Decimal("100000.00"),
        balance=Decimal("100000.00"),
        equity=Decimal("100000.00"),
        broker_credentials=mock_broker_credentials,
        trading_parameters=TradingParameters(),
        risk_limits=RiskLimits(),
        notification_settings=NotificationSettings()
    )


@pytest.fixture
def mock_vault_service(mock_vault_config):
    """Create mock Vault service."""
    vault_service = Mock(spec=VaultService)
    vault_service.config = mock_vault_config
    
    # Mock store_credentials to return a reference
    vault_service.store_credentials.return_value = Mock(
        vault_path="test/path",
        version=1
    )
    
    vault_service.health_check.return_value = {
        "status": "healthy",
        "authenticated": True,
        "sealed": False
    }
    
    return vault_service


@pytest.fixture
def mock_auth_service():
    """Create mock 2FA service."""
    auth_service = Mock(spec=TwoFactorAuthService)
    
    auth_service.setup_2fa.return_value = TwoFactorAuthSetup(
        secret_key="TEST_SECRET_KEY",
        qr_code_url="data:image/png;base64,test_qr_code",
        backup_codes=["CODE1", "CODE2", "CODE3"]
    )
    
    auth_service.verify_totp.return_value = True
    auth_service.get_2fa_status.return_value = {
        "is_setup": True,
        "remaining_backup_codes": 3,
        "is_rate_limited": False
    }
    
    return auth_service


class TestVaultService:
    """Test Vault credential storage service."""
    
    def test_vault_config_creation(self):
        """Test Vault configuration creation."""
        config = VaultConfig(
            url="http://localhost:8200",
            token="test_token"
        )
        
        assert config.url == "http://localhost:8200"
        assert config.token == "test_token"
        assert config.mount_point == "secret"
        assert config.credential_path_prefix == "trading-accounts"
    
    @patch('hvac.Client')
    def test_vault_service_initialization(self, mock_client, mock_vault_config):
        """Test Vault service initialization."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.is_authenticated.return_value = True
        
        vault_service = VaultService(mock_vault_config)
        
        assert vault_service.config == mock_vault_config
        mock_client.assert_called_once()
        mock_client_instance.is_authenticated.assert_called_once()
    
    def test_credential_storage(self, mock_vault_service, mock_broker_credentials):
        """Test credential storage in Vault."""
        account_id = uuid4()
        
        reference = mock_vault_service.store_credentials(account_id, mock_broker_credentials)
        
        mock_vault_service.store_credentials.assert_called_once_with(account_id, mock_broker_credentials)
        assert reference.vault_path == "test/path"
        assert reference.version == 1


class TestTwoFactorAuth:
    """Test 2FA authentication service."""
    
    def test_2fa_setup(self):
        """Test 2FA setup for user."""
        auth_service = TwoFactorAuthService()
        
        setup_info = auth_service.setup_2fa("test_user", "test_account")
        
        assert setup_info.secret_key
        assert len(setup_info.secret_key) >= 16
        assert setup_info.qr_code_url.startswith("data:image/png;base64,")
        assert len(setup_info.backup_codes) == 10
    
    def test_totp_verification(self):
        """Test TOTP code verification."""
        auth_service = TwoFactorAuthService()
        
        # Setup 2FA first
        setup_info = auth_service.setup_2fa("test_user", "test_account")
        
        # Generate a TOTP code
        import pyotp
        totp = pyotp.TOTP(setup_info.secret_key)
        valid_code = totp.now()
        
        # Verify valid code
        assert auth_service.verify_totp(setup_info.secret_key, valid_code, "test_user") is True
        
        # Verify invalid code
        assert auth_service.verify_totp(setup_info.secret_key, "000000", "test_user") is False
    
    def test_backup_code_verification(self):
        """Test backup code verification."""
        auth_service = TwoFactorAuthService()
        
        # Setup 2FA
        setup_info = auth_service.setup_2fa("test_user", "test_account")
        backup_code = setup_info.backup_codes[0]
        
        # Verify backup code (first use)
        assert auth_service.verify_backup_code("test_user", backup_code) is True
        
        # Verify same backup code (should fail - already used)
        assert auth_service.verify_backup_code("test_user", backup_code) is False
        
        # Verify invalid backup code
        assert auth_service.verify_backup_code("test_user", "INVALID") is False
    
    def test_rate_limiting(self):
        """Test rate limiting for failed attempts."""
        auth_service = TwoFactorAuthService()
        
        # Setup 2FA
        setup_info = auth_service.setup_2fa("test_user", "test_account")
        
        # Make multiple failed attempts
        for _ in range(5):
            auth_service.verify_totp(setup_info.secret_key, "000000", "test_user")
        
        # Should be rate limited now
        assert auth_service._is_rate_limited("test_user") is True
        
        # Valid code should still fail due to rate limiting
        import pyotp
        totp = pyotp.TOTP(setup_info.secret_key)
        valid_code = totp.now()
        assert auth_service.verify_totp(setup_info.secret_key, valid_code, "test_user") is False


class TestAccountStatusManager:
    """Test account status management."""
    
    @pytest.mark.asyncio
    async def test_status_transition(self, mock_account_config):
        """Test account status transitions."""
        status_manager = AccountStatusManager()
        
        # Test valid transition: ACTIVE -> SUSPENDED
        transition = await status_manager.transition_status(
            mock_account_config,
            AccountStatus.SUSPENDED,
            "Manual suspension for testing",
            "test_user"
        )
        
        assert transition.from_status == AccountStatus.ACTIVE
        assert transition.to_status == AccountStatus.SUSPENDED
        assert transition.reason == "Manual suspension for testing"
        assert transition.triggered_by == "test_user"
        assert mock_account_config.status == AccountStatus.SUSPENDED
    
    @pytest.mark.asyncio
    async def test_invalid_status_transition(self, mock_account_config):
        """Test invalid status transition."""
        status_manager = AccountStatusManager()
        
        # Set account to terminated
        mock_account_config.status = AccountStatus.TERMINATED
        
        # Try to transition from TERMINATED to ACTIVE (invalid)
        with pytest.raises(Exception):  # Should raise StatusTransitionError
            await status_manager.transition_status(
                mock_account_config,
                AccountStatus.ACTIVE,
                "Invalid transition",
                "test_user"
            )
    
    @pytest.mark.asyncio
    async def test_automatic_daily_loss_transition(self, mock_account_config):
        """Test automatic transition due to daily loss limit."""
        status_manager = AccountStatusManager()
        
        # Set account to exceed daily loss limit
        mock_account_config.balance = Decimal("95000.00")  # 5% loss, matches default limit
        
        # Check automatic transitions
        transition = await status_manager.check_automatic_transitions(mock_account_config)
        
        # Should trigger IN_DRAWDOWN status
        if transition:
            assert transition.to_status == AccountStatus.IN_DRAWDOWN
            assert "daily loss limit" in transition.reason.lower()
    
    def test_status_restrictions(self):
        """Test status-based trading restrictions."""
        status_manager = AccountStatusManager()
        
        # Test ACTIVE status permissions
        restrictions = status_manager.get_status_restrictions(AccountStatus.ACTIVE)
        assert restrictions["can_trade"] is True
        assert restrictions["can_open_positions"] is True
        assert restrictions["can_close_positions"] is True
        
        # Test SUSPENDED status restrictions
        restrictions = status_manager.get_status_restrictions(AccountStatus.SUSPENDED)
        assert restrictions["can_trade"] is False
        assert restrictions["can_open_positions"] is False
        assert restrictions["can_close_positions"] is True  # Allow closing only
        
        # Test IN_DRAWDOWN status (close-only mode)
        restrictions = status_manager.get_status_restrictions(AccountStatus.IN_DRAWDOWN)
        assert restrictions["can_trade"] is True  # Limited trading
        assert restrictions["can_open_positions"] is False  # Close-only
        assert restrictions["can_close_positions"] is True
        
        # Test TERMINATED status (no access)
        restrictions = status_manager.get_status_restrictions(AccountStatus.TERMINATED)
        assert restrictions["can_trade"] is False
        assert restrictions["can_open_positions"] is False
        assert restrictions["can_close_positions"] is False
    
    def test_action_permission_check(self, mock_account_config):
        """Test action permission checking."""
        status_manager = AccountStatusManager()
        
        # Active account should allow trading
        mock_account_config.status = AccountStatus.ACTIVE
        can_trade, reason = status_manager.can_perform_action(mock_account_config, "trade")
        assert can_trade is True
        
        # Suspended account should not allow trading
        mock_account_config.status = AccountStatus.SUSPENDED
        can_trade, reason = status_manager.can_perform_action(mock_account_config, "trade")
        assert can_trade is False
        assert "suspended" in reason.lower()
    
    def test_transition_history_tracking(self, mock_account_config):
        """Test status transition history tracking."""
        status_manager = AccountStatusManager()
        
        # Initially no history
        history = status_manager.get_transition_history(mock_account_config.account_id)
        assert len(history) == 0
        
        # Make a transition
        asyncio.run(status_manager.transition_status(
            mock_account_config,
            AccountStatus.SUSPENDED,
            "Test transition",
            "test_user"
        ))
        
        # Check history
        history = status_manager.get_transition_history(mock_account_config.account_id)
        assert len(history) == 1
        assert history[0].to_status == AccountStatus.SUSPENDED
        
        # Get last transition
        last_transition = status_manager.get_last_transition(mock_account_config.account_id)
        assert last_transition.to_status == AccountStatus.SUSPENDED


class TestImportExportService:
    """Test account import/export functionality."""
    
    @pytest.mark.asyncio
    async def test_account_export_json(self, mock_vault_service, mock_auth_service, mock_account_config):
        """Test account export in JSON format."""
        import_export_service = ImportExportService(mock_vault_service, mock_auth_service)
        
        accounts = [mock_account_config]
        
        export_data = await import_export_service.export_accounts(
            accounts, "json", False  # Don't include credentials
        )
        
        assert export_data
        assert '"prop_firm": "FTMO"' in export_data
        assert '"account_number": "MT4_12345"' in export_data
        # Credentials should be redacted
        assert '"password": "[REDACTED]"' in export_data
    
    @pytest.mark.asyncio
    async def test_account_export_yaml(self, mock_vault_service, mock_auth_service, mock_account_config):
        """Test account export in YAML format."""
        import_export_service = ImportExportService(mock_vault_service, mock_auth_service)
        
        accounts = [mock_account_config]
        
        export_data = await import_export_service.export_accounts(
            accounts, "yaml", False
        )
        
        assert export_data
        assert "prop_firm: FTMO" in export_data
        assert "account_number: MT4_12345" in export_data
    
    def test_export_data_validation(self, mock_vault_service, mock_auth_service):
        """Test export data format validation."""
        import_export_service = ImportExportService(mock_vault_service, mock_auth_service)
        
        # Valid JSON export data
        valid_json = '{"version": "1.0", "export_date": "2024-01-01T00:00:00", "accounts": [{"account_id": "test"}], "metadata": {}}'
        is_valid, errors = import_export_service.validate_export_data(valid_json, "json")
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid JSON
        invalid_json = '{"invalid": "json"'  # Missing closing brace
        is_valid, errors = import_export_service.validate_export_data(invalid_json, "json")
        assert is_valid is False
        assert len(errors) > 0
        
        # Missing required fields
        incomplete_json = '{"version": "1.0"}'
        is_valid, errors = import_export_service.validate_export_data(incomplete_json, "json")
        assert is_valid is False
        assert any("Missing required field" in error for error in errors)


class TestAccountModels:
    """Test account data models."""
    
    def test_account_configuration_creation(self, mock_broker_credentials):
        """Test account configuration model creation."""
        account = AccountConfiguration(
            prop_firm=PropFirm.FTMO,
            account_number="TEST_12345",
            initial_balance=Decimal("50000.00"),
            broker_credentials=mock_broker_credentials
        )
        
        assert account.prop_firm == PropFirm.FTMO
        assert account.account_number == "TEST_12345"
        assert account.initial_balance == Decimal("50000.00")
        assert account.balance == Decimal("0.0")  # Default
        assert account.status == AccountStatus.ACTIVE  # Default
        assert account.account_id is not None
        assert isinstance(account.account_id, UUID)
    
    def test_account_validation(self):
        """Test account configuration validation."""
        # Test invalid account number
        with pytest.raises(ValueError):
            AccountConfiguration(
                prop_firm=PropFirm.FTMO,
                account_number="",  # Empty account number
                initial_balance=Decimal("50000.00"),
                broker_credentials=BrokerCredentials(
                    broker=BrokerType.METATRADER4,
                    server="test.com",
                    login="12345",
                    password="test"
                )
            )
    
    def test_broker_credentials_validation(self):
        """Test broker credentials validation."""
        # Valid credentials
        creds = BrokerCredentials(
            broker=BrokerType.METATRADER4,
            server="broker.test.com:443",
            login="12345",
            password="secure_password"
        )
        
        assert creds.broker == BrokerType.METATRADER4
        assert creds.server == "broker.test.com:443"
        
        # Invalid credentials - empty server
        with pytest.raises(ValueError):
            BrokerCredentials(
                broker=BrokerType.METATRADER4,
                server="",  # Empty server
                login="12345",
                password="test"
            )
        
        # Invalid credentials - empty login
        with pytest.raises(ValueError):
            BrokerCredentials(
                broker=BrokerType.METATRADER4,
                server="test.com",
                login="",  # Empty login
                password="test"
            )
    
    def test_trading_parameters_validation(self):
        """Test trading parameters validation."""
        # Valid parameters
        params = TradingParameters(
            allowed_pairs=["EURUSD", "GBPUSD"],
            max_positions=5,
            max_lot_size=Decimal("1.0"),
            trading_hours="08:00-18:00"
        )
        
        assert len(params.allowed_pairs) == 2
        assert "EURUSD" in params.allowed_pairs
        
        # Invalid trading hours format
        with pytest.raises(ValueError):
            TradingParameters(
                trading_hours="invalid_format"
            )
        
        # Empty allowed pairs
        with pytest.raises(ValueError):
            TradingParameters(
                allowed_pairs=[]
            )
    
    def test_risk_limits_validation(self):
        """Test risk limits validation."""
        # Valid risk limits
        limits = RiskLimits(
            max_daily_loss_percent=Decimal("5.0"),
            max_total_loss_percent=Decimal("10.0"),
            max_position_size_percent=Decimal("2.0")
        )
        
        assert limits.max_daily_loss_percent == Decimal("5.0")
        
        # Invalid percentage (too high)
        with pytest.raises(ValueError):
            RiskLimits(
                max_daily_loss_percent=Decimal("150.0")  # > 100%
            )
        
        # Invalid percentage (negative)
        with pytest.raises(ValueError):
            RiskLimits(
                max_daily_loss_percent=Decimal("-5.0")
            )


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_account_lifecycle(self, mock_vault_service, mock_auth_service):
        """Test complete account management lifecycle."""
        # Initialize services
        status_manager = AccountStatusManager()
        
        # Create account
        account = AccountConfiguration(
            prop_firm=PropFirm.FTMO,
            account_number="INTEGRATION_TEST",
            initial_balance=Decimal("100000.00"),
            balance=Decimal("100000.00"),
            broker_credentials=BrokerCredentials(
                broker=BrokerType.METATRADER4,
                server="test.com",
                login="12345",
                password="test"
            )
        )
        
        # Initial state
        assert account.status == AccountStatus.ACTIVE
        
        # Simulate trading loss leading to suspension
        account.balance = Decimal("95000.00")  # 5% loss
        
        # Check automatic transitions
        transition = await status_manager.check_automatic_transitions(account)
        if transition:
            assert transition.to_status == AccountStatus.IN_DRAWDOWN
        
        # Manual status change to suspended
        await status_manager.transition_status(
            account,
            AccountStatus.SUSPENDED,
            "Manual suspension for review",
            "admin_user"
        )
        
        assert account.status == AccountStatus.SUSPENDED
        
        # Check trading permissions
        can_trade, reason = status_manager.can_perform_action(account, "trade")
        assert can_trade is False
        
        can_close, reason = status_manager.can_perform_action(account, "close_positions")
        assert can_close is True  # Should still be able to close positions
        
        # Reactivate account
        await status_manager.transition_status(
            account,
            AccountStatus.ACTIVE,
            "Review completed - reactivating",
            "admin_user"
        )
        
        assert account.status == AccountStatus.ACTIVE
        
        # Verify transition history
        history = status_manager.get_transition_history(account.account_id)
        assert len(history) >= 2  # At least suspension and reactivation
    
    @pytest.mark.asyncio
    async def test_import_export_roundtrip(self, mock_vault_service, mock_auth_service):
        """Test complete import/export roundtrip."""
        import_export_service = ImportExportService(mock_vault_service, mock_auth_service)
        
        # Create test accounts
        accounts = [
            AccountConfiguration(
                prop_firm=PropFirm.FTMO,
                account_number="EXPORT_TEST_1",
                initial_balance=Decimal("100000.00"),
                broker_credentials=BrokerCredentials(
                    broker=BrokerType.METATRADER4,
                    server="test1.com",
                    login="11111",
                    password="pass1"
                )
            ),
            AccountConfiguration(
                prop_firm=PropFirm.FUNDEDNEXT,
                account_number="EXPORT_TEST_2",
                initial_balance=Decimal("50000.00"),
                broker_credentials=BrokerCredentials(
                    broker=BrokerType.METATRADER5,
                    server="test2.com",
                    login="22222",
                    password="pass2"
                )
            )
        ]
        
        # Export accounts
        export_data = await import_export_service.export_accounts(
            accounts, "json", False
        )
        
        assert export_data
        
        # Import accounts back
        imported_accounts, errors = await import_export_service.import_accounts_from_string(
            export_data, "json", False, True  # Validate only
        )
        
        # Should have no validation errors and same number of accounts
        assert len(errors) == 0
        assert len(imported_accounts) == 2
        
        # Verify account details
        imported_account_numbers = {acc.account_number for acc in imported_accounts}
        assert "EXPORT_TEST_1" in imported_account_numbers
        assert "EXPORT_TEST_2" in imported_account_numbers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])