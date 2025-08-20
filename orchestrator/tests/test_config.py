"""
Tests for Configuration Management
"""

import pytest
import os
import tempfile
from unittest.mock import patch
from pydantic import ValidationError

from app.config import (
    Settings, TestSettings, ProductionSettings,
    get_settings, reload_settings, get_settings_for_environment
)


class TestSettings:
    """Test Settings class and validation"""
    
    def test_default_settings(self):
        """Test default settings values"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account_123'
        }):
            settings = Settings()
            
            assert settings.app_name == "TMT Trading System Orchestrator"
            assert settings.app_version == "1.0.0"
            assert settings.environment == "development"
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.oanda_environment == "practice"
    
    def test_environment_variables(self):
        """Test that environment variables override defaults"""
        env_vars = {
            'OANDA_API_KEY': 'custom_api_key',
            'OANDA_ACCOUNT_IDS': 'account_1,account_2,account_3',
            'OANDA_ENVIRONMENT': 'live',
            'DEBUG': 'true',
            'LOG_LEVEL': 'DEBUG',
            'PORT': '9000',
            'RISK_PER_TRADE': '0.015'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.oanda_api_key == 'custom_api_key'
            assert len(settings.account_ids_list) == 3
            assert settings.oanda_environment == 'live'
            assert settings.debug is True
            assert settings.log_level == 'DEBUG'
            assert settings.port == 9000
            assert settings.risk_per_trade == 0.015
    
    def test_account_ids_parsing(self):
        """Test parsing of comma-separated account IDs"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'account_1, account_2 ,account_3,  account_4  '
        }):
            settings = Settings()
            
            # Should parse and clean whitespace
            assert settings.account_ids_list == ['account_1', 'account_2', 'account_3', 'account_4']
    
    def test_environment_validation(self):
        """Test OANDA environment validation"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account',
            'OANDA_ENVIRONMENT': 'invalid_env'
        }):
            with pytest.raises(ValidationError) as excinfo:
                Settings()
            
            assert "OANDA environment must be 'practice' or 'live'" in str(excinfo.value)
    
    def test_risk_validation(self):
        """Test risk parameter validation"""
        # Test risk_per_trade validation
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account',
            'RISK_PER_TRADE': '0.15'  # 15% - too high
        }):
            with pytest.raises(ValidationError) as excinfo:
                Settings()
            
            assert "Risk per trade must be between 0.1% and 10%" in str(excinfo.value)
        
        # Test max_daily_loss validation
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account',
            'MAX_DAILY_LOSS': '0.6'  # 60% - too high
        }):
            with pytest.raises(ValidationError) as excinfo:
                Settings()
            
            assert "Max daily loss must be between 1% and 50%" in str(excinfo.value)
    
    def test_required_fields(self):
        """Test that required fields raise validation errors"""
        with pytest.raises(ValidationError) as excinfo:
            Settings()  # Missing OANDA_API_KEY and OANDA_ACCOUNT_IDS
        
        error_str = str(excinfo.value)
        assert "oanda_api_key" in error_str
        assert "oanda_account_ids" in error_str
    
    def test_api_url_properties(self):
        """Test OANDA API URL properties"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account',
            'OANDA_ENVIRONMENT': 'practice'
        }):
            settings = Settings()
            
            assert settings.oanda_api_url == "https://api-fxpractice.oanda.com"
            assert settings.oanda_streaming_url == "https://stream-fxpractice.oanda.com"
            assert settings.is_live_trading is False
        
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account',
            'OANDA_ENVIRONMENT': 'live'
        }):
            settings = Settings()
            
            assert settings.oanda_api_url == "https://api-fxtrade.oanda.com"
            assert settings.oanda_streaming_url == "https://stream-fxtrade.oanda.com"
            assert settings.is_live_trading is True
    
    def test_agent_endpoints(self):
        """Test agent endpoints configuration"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account'
        }):
            settings = Settings()
            
            expected_agents = [
                "market-analysis",
                "strategy-analysis", 
                "parameter-optimization",
                "learning-safety",
                "disagreement-engine",
                "data-collection",
                "continuous-improvement",
                "pattern-detection"
            ]
            
            for agent_type in expected_agents:
                assert agent_type in settings.agent_endpoints
                endpoint = settings.get_agent_endpoint(agent_type)
                assert endpoint is not None
                assert endpoint.startswith("http://localhost:")
    
    def test_trading_hours(self):
        """Test trading hours configuration"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account'
        }):
            settings = Settings()
            
            # Test default trading hours
            assert settings.trading_hours["enabled"] is True
            assert settings.trading_hours["start_hour"] == 0
            assert settings.trading_hours["end_hour"] == 22
            assert 21 in settings.trading_hours["break_hours"]
            
            # Test is_trading_hours method (simplified test)
            # Note: This is a basic test since the actual implementation 
            # would need proper datetime mocking
            is_trading = settings.is_trading_hours()
            assert isinstance(is_trading, bool)
    
    def test_circuit_breaker_configuration(self):
        """Test circuit breaker configuration"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account'
        }):
            settings = Settings()
            
            # Test default circuit breaker config
            cb_config = settings.circuit_breaker_config
            assert cb_config["account_loss_threshold"] == 0.05  # 5%
            assert cb_config["daily_loss_threshold"] == 0.03    # 3%
            assert cb_config["consecutive_losses"] == 5
            assert cb_config["correlation_threshold"] == 0.8
            assert cb_config["volatility_threshold"] == 2.0
            assert cb_config["recovery_time_minutes"] == 30
            
            # Test getter methods
            assert settings.get_circuit_breaker_threshold("account_loss") == 0.05
            assert settings.get_circuit_breaker_threshold("nonexistent") == 0.05  # default
    
    def test_performance_thresholds(self):
        """Test performance threshold configuration"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account'
        }):
            settings = Settings()
            
            # Test default performance thresholds
            perf_thresholds = settings.performance_thresholds
            assert perf_thresholds["max_latency_ms"] == 100.0
            assert perf_thresholds["min_win_rate"] == 0.5
            assert perf_thresholds["max_drawdown"] == 0.1
            assert perf_thresholds["min_profit_factor"] == 1.2
            assert perf_thresholds["max_correlation"] == 0.7
            
            # Test getter method
            assert settings.get_performance_threshold("max_latency_ms") == 100.0
            assert settings.get_performance_threshold("nonexistent") == 0.0  # default


class TestTestSettings:
    """Test TestSettings configuration"""
    
    def test_test_settings_overrides(self):
        """Test that TestSettings has appropriate test overrides"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account'
        }):
            settings = TestSettings()
            
            # Should override for testing
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.database_url == "sqlite:///:memory:"
            assert settings.message_broker_url == "redis://localhost:6379/1"
            
            # Should have more conservative test limits
            assert settings.risk_per_trade == 0.001
            assert settings.max_daily_loss == 0.01
            assert settings.max_concurrent_trades == 1
            
            # Test agent endpoints use different ports
            for agent_type, endpoint in settings.agent_endpoints.items():
                assert endpoint.startswith("http://localhost:1800")


class TestProductionSettings:
    """Test ProductionSettings configuration"""
    
    def test_production_settings_overrides(self):
        """Test that ProductionSettings has appropriate production overrides"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account',
            'JWT_SECRET_KEY': 'production_secret_key'
        }):
            settings = ProductionSettings()
            
            # Should override for production
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.workers == 4
            assert settings.jwt_secret_key == "production_secret_key"
            
            # Should have more conservative production limits
            assert settings.emergency_close_positions is True
            assert settings.max_trades_per_hour == 5  # More conservative
            
            # Should have longer health check intervals
            assert settings.agent_health_check_interval == 60
            assert settings.health_check_interval == 60


class TestSettingsFunctions:
    """Test settings utility functions"""
    
    def test_get_settings_singleton(self):
        """Test that get_settings returns a singleton"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account'
        }):
            settings1 = get_settings()
            settings2 = get_settings()
            
            # Should be the same instance
            assert settings1 is settings2
    
    def test_reload_settings(self):
        """Test settings reload functionality"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account',
            'DEBUG': 'false'
        }):
            settings1 = get_settings()
            assert settings1.debug is False
        
        # Change environment and reload
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account',
            'DEBUG': 'true'
        }):
            settings2 = reload_settings()
            assert settings2.debug is True
            
            # Should be a new instance
            assert settings1 is not settings2
    
    def test_get_settings_for_environment(self):
        """Test environment-specific settings"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'test_account'
        }):
            # Test settings
            test_settings = get_settings_for_environment("test")
            assert isinstance(test_settings, TestSettings)
            assert test_settings.debug is True
            
            # Production settings (needs JWT_SECRET_KEY)
            with patch.dict(os.environ, {'JWT_SECRET_KEY': 'prod_secret'}):
                prod_settings = get_settings_for_environment("production")
                assert isinstance(prod_settings, ProductionSettings)
                assert prod_settings.debug is False
            
            # Default settings
            default_settings = get_settings_for_environment("development")
            assert isinstance(default_settings, Settings)
            assert default_settings.environment == "development"


class TestConfigurationEdgeCases:
    """Test configuration edge cases and error conditions"""
    
    def test_empty_account_ids(self):
        """Test handling of empty account IDs"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': ''
        }):
            settings = Settings()
            assert settings.account_ids_list == []
    
    def test_whitespace_only_account_ids(self):
        """Test handling of whitespace-only account IDs"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': '  ,  ,  '
        }):
            settings = Settings()
            assert settings.account_ids_list == []
    
    def test_mixed_valid_invalid_account_ids(self):
        """Test handling of mixed valid/invalid account IDs"""
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'test_key',
            'OANDA_ACCOUNT_IDS': 'valid_1, , valid_2,   , valid_3'
        }):
            settings = Settings()
            assert settings.account_ids_list == ['valid_1', 'valid_2', 'valid_3']
    
    def test_config_with_env_file(self, temp_env_file):
        """Test configuration loading from .env file"""
        # This would need to be integrated with the actual settings loading
        # For now, just test that the fixture works
        assert os.path.exists(temp_env_file)
        
        with open(temp_env_file, 'r') as f:
            content = f.read()
            assert 'OANDA_API_KEY=test_key' in content
            assert 'OANDA_ENVIRONMENT=practice' in content