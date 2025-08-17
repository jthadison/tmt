"""
Multi-Broker Configuration System
Story 8.10 - Task 3: Build multi-broker configuration system (AC3)
"""
import json
import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
import yaml
import copy
from threading import RLock

logger = logging.getLogger(__name__)


class ConfigFormat(Enum):
    """Configuration file formats"""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"


class ConfigEnvironment(Enum):
    """Configuration environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class BrokerCredentials:
    """Broker authentication credentials"""
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    access_token: Optional[str] = None
    account_id: Optional[str] = None
    environment: str = "practice"  # practice or live
    additional_params: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding secrets"""
        result = asdict(self)
        if not include_secrets:
            # Mask sensitive fields
            for field_name in ['api_key', 'secret_key', 'access_token']:
                if result.get(field_name):
                    result[field_name] = "***masked***"
        return result


@dataclass
class BrokerEndpoints:
    """Broker API endpoints configuration"""
    base_url: str
    stream_url: Optional[str] = None
    auth_url: Optional[str] = None
    websocket_url: Optional[str] = None
    additional_endpoints: Dict[str, str] = field(default_factory=dict)


@dataclass
class BrokerLimits:
    """Broker rate limits and restrictions"""
    requests_per_second: Optional[int] = None
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    max_orders_per_second: Optional[int] = None
    max_concurrent_connections: Optional[int] = None
    burst_allowance: Optional[int] = None
    additional_limits: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerSettings:
    """Broker-specific settings"""
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    enable_streaming: bool = True
    enable_historical_data: bool = True
    default_currency: str = "USD"
    timezone: str = "UTC"
    additional_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerConfiguration:
    """Complete broker configuration"""
    broker_name: str
    display_name: str
    enabled: bool = True
    credentials: Optional[BrokerCredentials] = None
    endpoints: Optional[BrokerEndpoints] = None
    limits: Optional[BrokerLimits] = None
    settings: Optional[BrokerSettings] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = asdict(self)
        result['last_updated'] = self.last_updated.isoformat()
        
        if not include_secrets and self.credentials:
            result['credentials'] = self.credentials.to_dict(include_secrets=False)
            
        return result
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrokerConfiguration':
        """Create from dictionary representation"""
        # Handle nested objects
        if 'credentials' in data and data['credentials']:
            data['credentials'] = BrokerCredentials(**data['credentials'])
            
        if 'endpoints' in data and data['endpoints']:
            data['endpoints'] = BrokerEndpoints(**data['endpoints'])
            
        if 'limits' in data and data['limits']:
            data['limits'] = BrokerLimits(**data['limits'])
            
        if 'settings' in data and data['settings']:
            data['settings'] = BrokerSettings(**data['settings'])
            
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'].replace('Z', '+00:00'))
            
        return cls(**data)


class ConfigurationManager:
    """Manages multi-broker configurations with hot-reloading and versioning"""
    
    def __init__(self, 
                 config_directory: str = "config",
                 environment: ConfigEnvironment = ConfigEnvironment.DEVELOPMENT,
                 auto_reload: bool = True):
        self.config_directory = Path(config_directory)
        self.environment = environment
        self.auto_reload = auto_reload
        
        # Thread-safe configuration storage
        self._lock = RLock()
        self._configurations: Dict[str, BrokerConfiguration] = {}
        self._file_timestamps: Dict[str, float] = {}
        self._watchers: List[callable] = []
        
        # Configuration history for versioning
        self._config_history: Dict[str, List[Dict[str, Any]]] = {}
        self._max_history_size = 50
        
        # Ensure config directory exists
        self.config_directory.mkdir(parents=True, exist_ok=True)
        
        # Load existing configurations
        self._load_all_configurations()
        
    def _load_all_configurations(self):
        """Load all broker configurations from files"""
        config_files = list(self.config_directory.glob("*.json")) + \
                      list(self.config_directory.glob("*.yaml")) + \
                      list(self.config_directory.glob("*.yml"))
                      
        for config_file in config_files:
            try:
                self._load_configuration_file(config_file)
            except Exception as e:
                logger.error(f"Failed to load configuration file {config_file}: {e}")
                
    def _load_configuration_file(self, file_path: Path):
        """Load configuration from specific file"""
        if not file_path.exists():
            return
            
        # Check if file has been modified
        current_mtime = file_path.stat().st_mtime
        if str(file_path) in self._file_timestamps:
            if current_mtime <= self._file_timestamps[str(file_path)]:
                return  # File hasn't changed
                
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.json':
                    data = json.load(f)
                elif file_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    logger.warning(f"Unsupported configuration file format: {file_path}")
                    return
                    
            # Environment-specific configuration override
            env_data = data.get(self.environment.value, {})
            if env_data:
                # Merge environment-specific settings
                merged_data = copy.deepcopy(data.get('default', {}))
                self._deep_merge(merged_data, env_data)
                data = merged_data
            
            # Create configuration object
            config = BrokerConfiguration.from_dict(data)
            
            with self._lock:
                # Store configuration history
                if config.broker_name not in self._config_history:
                    self._config_history[config.broker_name] = []
                    
                history = self._config_history[config.broker_name]
                history.append({
                    'configuration': config.to_dict(include_secrets=False),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source_file': str(file_path)
                })
                
                # Keep history bounded
                if len(history) > self._max_history_size:
                    history[:] = history[-self._max_history_size:]
                
                # Update current configuration
                old_config = self._configurations.get(config.broker_name)
                self._configurations[config.broker_name] = config
                self._file_timestamps[str(file_path)] = current_mtime
                
            # Notify watchers of configuration change
            self._notify_watchers(config.broker_name, old_config, config)
            
            logger.info(f"Loaded configuration for broker: {config.broker_name}")
            
        except Exception as e:
            logger.error(f"Failed to parse configuration file {file_path}: {e}")
            
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Deep merge two dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
                
    def _notify_watchers(self, 
                        broker_name: str, 
                        old_config: Optional[BrokerConfiguration],
                        new_config: BrokerConfiguration):
        """Notify configuration change watchers"""
        for watcher in self._watchers:
            try:
                watcher(broker_name, old_config, new_config)
            except Exception as e:
                logger.error(f"Configuration watcher error: {e}")
                
    def get_configuration(self, broker_name: str) -> Optional[BrokerConfiguration]:
        """
        Get configuration for specific broker
        
        Args:
            broker_name: Name of the broker
            
        Returns:
            BrokerConfiguration or None if not found
        """
        with self._lock:
            if self.auto_reload:
                self._check_for_updates()
            return copy.deepcopy(self._configurations.get(broker_name))
            
    def get_all_configurations(self) -> Dict[str, BrokerConfiguration]:
        """Get all broker configurations"""
        with self._lock:
            if self.auto_reload:
                self._check_for_updates()
            return {name: copy.deepcopy(config) for name, config in self._configurations.items()}
            
    def get_enabled_configurations(self) -> Dict[str, BrokerConfiguration]:
        """Get only enabled broker configurations"""
        with self._lock:
            if self.auto_reload:
                self._check_for_updates()
            return {
                name: copy.deepcopy(config) 
                for name, config in self._configurations.items() 
                if config.enabled
            }
            
    def set_configuration(self, 
                         broker_name: str, 
                         configuration: BrokerConfiguration,
                         save_to_file: bool = True) -> bool:
        """
        Set configuration for broker
        
        Args:
            broker_name: Name of the broker
            configuration: BrokerConfiguration to set
            save_to_file: Whether to persist to file
            
        Returns:
            True if successful
        """
        try:
            configuration.broker_name = broker_name
            configuration.last_updated = datetime.now(timezone.utc)
            
            with self._lock:
                old_config = self._configurations.get(broker_name)
                self._configurations[broker_name] = configuration
                
                # Save configuration history
                if broker_name not in self._config_history:
                    self._config_history[broker_name] = []
                    
                self._config_history[broker_name].append({
                    'configuration': configuration.to_dict(include_secrets=False),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'programmatic'
                })
                
            # Save to file if requested
            if save_to_file:
                self._save_configuration_to_file(broker_name, configuration)
                
            # Notify watchers
            self._notify_watchers(broker_name, old_config, configuration)
            
            logger.info(f"Set configuration for broker: {broker_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set configuration for {broker_name}: {e}")
            return False
            
    def _save_configuration_to_file(self, 
                                   broker_name: str, 
                                   configuration: BrokerConfiguration):
        """Save configuration to file"""
        file_path = self.config_directory / f"{broker_name}.json"
        
        try:
            config_data = configuration.to_dict(include_secrets=True)
            
            # Add environment wrapper if needed
            if self.environment != ConfigEnvironment.DEVELOPMENT:
                config_data = {
                    'default': config_data,
                    self.environment.value: {}
                }
                
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, default=str)
                
            # Update file timestamp
            self._file_timestamps[str(file_path)] = file_path.stat().st_mtime
            
        except Exception as e:
            logger.error(f"Failed to save configuration file for {broker_name}: {e}")
            
    def delete_configuration(self, broker_name: str, delete_file: bool = True) -> bool:
        """
        Delete broker configuration
        
        Args:
            broker_name: Name of the broker
            delete_file: Whether to delete the file
            
        Returns:
            True if successful
        """
        try:
            with self._lock:
                old_config = self._configurations.pop(broker_name, None)
                
            if delete_file:
                file_path = self.config_directory / f"{broker_name}.json"
                if file_path.exists():
                    file_path.unlink()
                    self._file_timestamps.pop(str(file_path), None)
                    
            if old_config:
                self._notify_watchers(broker_name, old_config, None)
                logger.info(f"Deleted configuration for broker: {broker_name}")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete configuration for {broker_name}: {e}")
            return False
            
    def _check_for_updates(self):
        """Check for configuration file updates"""
        config_files = list(self.config_directory.glob("*.json")) + \
                      list(self.config_directory.glob("*.yaml")) + \
                      list(self.config_directory.glob("*.yml"))
                      
        for config_file in config_files:
            current_mtime = config_file.stat().st_mtime
            if (str(config_file) not in self._file_timestamps or
                current_mtime > self._file_timestamps[str(config_file)]):
                self._load_configuration_file(config_file)
                
    def add_watcher(self, callback: callable):
        """Add configuration change watcher"""
        self._watchers.append(callback)
        
    def remove_watcher(self, callback: callable):
        """Remove configuration change watcher"""
        if callback in self._watchers:
            self._watchers.remove(callback)
            
    def get_configuration_history(self, broker_name: str) -> List[Dict[str, Any]]:
        """Get configuration change history for broker"""
        with self._lock:
            return self._config_history.get(broker_name, []).copy()
            
    def backup_configurations(self, backup_path: Optional[str] = None) -> str:
        """
        Create backup of all configurations
        
        Args:
            backup_path: Optional backup file path
            
        Returns:
            Path to backup file
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"config_backup_{timestamp}.json"
            
        backup_data = {
            'metadata': {
                'backup_timestamp': datetime.now(timezone.utc).isoformat(),
                'environment': self.environment.value,
                'total_configurations': len(self._configurations)
            },
            'configurations': {
                name: config.to_dict(include_secrets=True)
                for name, config in self._configurations.items()
            },
            'history': self._config_history
        }
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)
            
        logger.info(f"Created configuration backup: {backup_path}")
        return backup_path
        
    def restore_configurations(self, backup_path: str) -> bool:
        """
        Restore configurations from backup
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
                
            configurations = backup_data.get('configurations', {})
            
            with self._lock:
                for name, config_data in configurations.items():
                    config = BrokerConfiguration.from_dict(config_data)
                    self._configurations[name] = config
                    
                # Restore history if available
                if 'history' in backup_data:
                    self._config_history.update(backup_data['history'])
                    
            logger.info(f"Restored {len(configurations)} configurations from backup")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore configurations from backup: {e}")
            return False
            
    def validate_configuration(self, configuration: BrokerConfiguration) -> List[str]:
        """
        Validate broker configuration
        
        Args:
            configuration: Configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Basic validation
        if not configuration.broker_name:
            errors.append("Broker name is required")
            
        if not configuration.display_name:
            errors.append("Display name is required")
            
        # Credentials validation
        if configuration.credentials:
            if configuration.credentials.environment not in ['practice', 'live']:
                errors.append("Credentials environment must be 'practice' or 'live'")
                
        # Endpoints validation
        if configuration.endpoints:
            if not configuration.endpoints.base_url:
                errors.append("Base URL is required in endpoints")
            elif not configuration.endpoints.base_url.startswith(('http://', 'https://')):
                errors.append("Base URL must start with http:// or https://")
                
        # Limits validation
        if configuration.limits:
            numeric_limits = [
                'requests_per_second', 'requests_per_minute', 'requests_per_hour',
                'max_orders_per_second', 'max_concurrent_connections', 'burst_allowance'
            ]
            for limit_name in numeric_limits:
                value = getattr(configuration.limits, limit_name, None)
                if value is not None and (not isinstance(value, int) or value <= 0):
                    errors.append(f"Limit '{limit_name}' must be a positive integer")
                    
        return errors
        
    def get_manager_status(self) -> Dict[str, Any]:
        """Get configuration manager status"""
        with self._lock:
            return {
                'config_directory': str(self.config_directory),
                'environment': self.environment.value,
                'auto_reload': self.auto_reload,
                'total_configurations': len(self._configurations),
                'enabled_configurations': len([c for c in self._configurations.values() if c.enabled]),
                'watchers_count': len(self._watchers),
                'configurations': list(self._configurations.keys()),
                'last_check': datetime.now(timezone.utc).isoformat()
            }


# Global configuration manager
_global_config_manager: Optional[ConfigurationManager] = None


def get_global_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _global_config_manager
    if _global_config_manager is None:
        # Determine environment from environment variable
        env_name = os.getenv('BROKER_CONFIG_ENV', 'development').lower()
        try:
            environment = ConfigEnvironment(env_name)
        except ValueError:
            environment = ConfigEnvironment.DEVELOPMENT
            
        config_dir = os.getenv('BROKER_CONFIG_DIR', 'config/brokers')
        _global_config_manager = ConfigurationManager(
            config_directory=config_dir,
            environment=environment
        )
        
    return _global_config_manager


# Convenience functions
def get_broker_config(broker_name: str) -> Optional[BrokerConfiguration]:
    """Get configuration for specific broker"""
    return get_global_config_manager().get_configuration(broker_name)


def set_broker_config(broker_name: str, configuration: BrokerConfiguration) -> bool:
    """Set configuration for broker"""
    return get_global_config_manager().set_configuration(broker_name, configuration)


def get_all_broker_configs() -> Dict[str, BrokerConfiguration]:
    """Get all broker configurations"""
    return get_global_config_manager().get_all_configurations()


def get_enabled_broker_configs() -> Dict[str, BrokerConfiguration]:
    """Get only enabled broker configurations"""
    return get_global_config_manager().get_enabled_configurations()