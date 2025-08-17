"""
Broker Factory Pattern Implementation
Story 8.10 - Task 2: Implement broker factory pattern (AC2)
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Type, Set, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import importlib
import inspect
from pathlib import Path

try:
    from .broker_adapter import BrokerAdapter, BrokerCapability, BrokerInfo
    from .unified_errors import StandardBrokerError, StandardErrorCode, ErrorSeverity, ErrorContext
except ImportError:
    from broker_adapter import BrokerAdapter, BrokerCapability, BrokerInfo
    from unified_errors import StandardBrokerError, StandardErrorCode, ErrorSeverity, ErrorContext

logger = logging.getLogger(__name__)


class BrokerStatus(Enum):
    """Broker instance status"""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class BrokerRegistration:
    """Broker adapter registration information"""
    name: str
    display_name: str
    adapter_class: Type[BrokerAdapter]
    version: str
    description: str
    supported_capabilities: Set[BrokerCapability]
    configuration_schema: Dict[str, Any]
    registration_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerInstance:
    """Broker adapter instance information"""
    instance_id: str
    broker_name: str
    adapter: BrokerAdapter
    config: Dict[str, Any]
    status: BrokerStatus
    created_at: datetime
    last_health_check: Optional[datetime] = None
    health_status: Optional[Dict[str, Any]] = None
    error_count: int = 0
    last_error: Optional[StandardBrokerError] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnsupportedBrokerError(StandardBrokerError):
    """Raised when attempting to use unsupported broker"""
    def __init__(self, broker_name: str):
        super().__init__(
            error_code=StandardErrorCode.NOT_IMPLEMENTED,
            message=f"Broker '{broker_name}' is not registered",
            severity=ErrorSeverity.HIGH
        )


class BrokerAuthenticationError(StandardBrokerError):
    """Raised when broker authentication fails"""
    def __init__(self, broker_name: str, details: str = ""):
        super().__init__(
            error_code=StandardErrorCode.AUTHENTICATION_FAILED,
            message=f"Failed to authenticate with {broker_name}: {details}",
            severity=ErrorSeverity.HIGH
        )


class BrokerConfigurationError(StandardBrokerError):
    """Raised when broker configuration is invalid"""
    def __init__(self, broker_name: str, details: str):
        super().__init__(
            error_code=StandardErrorCode.VALIDATION_ERROR,
            message=f"Invalid configuration for {broker_name}: {details}",
            severity=ErrorSeverity.MEDIUM
        )


class BrokerFactory:
    """Factory for creating and managing broker adapter instances"""
    
    def __init__(self):
        self._registrations: Dict[str, BrokerRegistration] = {}
        self._instances: Dict[str, BrokerInstance] = {}
        self._health_check_interval = 300  # 5 minutes
        self._max_error_count = 5
        self._instance_counter = 0
        
        # Auto-discovery settings
        self._auto_discovery_enabled = True
        self._discovery_paths = ['src.agents.broker_integration.adapters']
        
        # Start background tasks
        self._health_check_task = None
        self._start_background_tasks()
        
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
    async def _health_check_loop(self):
        """Background task for health checking instances"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_checks()
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
                
    async def _perform_health_checks(self):
        """Perform health checks on all active instances"""
        for instance_id, instance in list(self._instances.items()):
            try:
                health_status = await instance.adapter.health_check()
                instance.last_health_check = datetime.now(timezone.utc)
                instance.health_status = health_status
                
                # Update status based on health check
                if health_status.get('status') == 'healthy':
                    instance.status = BrokerStatus.CONNECTED
                    instance.error_count = max(0, instance.error_count - 1)  # Decay errors
                else:
                    instance.status = BrokerStatus.ERROR
                    instance.error_count += 1
                    
                # Remove unhealthy instances
                if instance.error_count >= self._max_error_count:
                    logger.warning(f"Removing unhealthy broker instance: {instance_id}")
                    await self._cleanup_instance(instance_id)
                    
            except Exception as e:
                instance.error_count += 1
                instance.last_error = StandardBrokerError(
                    error_code=StandardErrorCode.CONNECTION_ERROR,
                    message=f"Health check failed: {e}",
                    context=ErrorContext(broker_name=instance.broker_name)
                )
                logger.error(f"Health check failed for {instance_id}: {e}")
                
    async def _cleanup_instance(self, instance_id: str):
        """Clean up broker instance"""
        if instance_id in self._instances:
            instance = self._instances[instance_id]
            try:
                await instance.adapter.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting instance {instance_id}: {e}")
            finally:
                del self._instances[instance_id]
                
    def register_adapter(self, 
                        name: str,
                        adapter_class: Type[BrokerAdapter],
                        display_name: Optional[str] = None,
                        version: str = "1.0.0",
                        description: str = "",
                        configuration_schema: Optional[Dict[str, Any]] = None,
                        **metadata):
        """
        Register a broker adapter class
        
        Args:
            name: Unique broker name
            adapter_class: BrokerAdapter subclass
            display_name: Human-readable name
            version: Adapter version
            description: Adapter description
            configuration_schema: JSON schema for configuration validation
            **metadata: Additional metadata
        """
        if not issubclass(adapter_class, BrokerAdapter):
            raise ValueError(f"Adapter class must inherit from BrokerAdapter")
            
        if name in self._registrations:
            logger.warning(f"Overriding existing broker registration: {name}")
            
        # Get capabilities from adapter class
        try:
            temp_instance = adapter_class({})
            capabilities = temp_instance.capabilities
        except Exception as e:
            logger.warning(f"Could not determine capabilities for {name}: {e}")
            capabilities = set()
            
        registration = BrokerRegistration(
            name=name,
            display_name=display_name or name.title(),
            adapter_class=adapter_class,
            version=version,
            description=description,
            supported_capabilities=capabilities,
            configuration_schema=configuration_schema or {},
            metadata=metadata
        )
        
        self._registrations[name] = registration
        logger.info(f"Registered broker adapter: {name} (v{version})")
        
    def unregister_adapter(self, name: str):
        """
        Unregister a broker adapter
        
        Args:
            name: Broker name to unregister
        """
        if name not in self._registrations:
            raise UnsupportedBrokerError(name)
            
        # Close all instances of this broker
        instances_to_close = [
            instance_id for instance_id, instance in self._instances.items()
            if instance.broker_name == name
        ]
        
        for instance_id in instances_to_close:
            asyncio.create_task(self._cleanup_instance(instance_id))
            
        del self._registrations[name]
        logger.info(f"Unregistered broker adapter: {name}")
        
    async def create_adapter(self, 
                           broker_name: str, 
                           config: Dict[str, Any],
                           instance_id: Optional[str] = None) -> BrokerAdapter:
        """
        Create and configure broker adapter instance
        
        Args:
            broker_name: Name of registered broker
            config: Configuration dictionary
            instance_id: Optional custom instance ID
            
        Returns:
            Configured BrokerAdapter instance
        """
        if broker_name not in self._registrations:
            raise UnsupportedBrokerError(broker_name)
            
        registration = self._registrations[broker_name]
        
        if not registration.is_enabled:
            raise StandardBrokerError(
                error_code=StandardErrorCode.SERVICE_UNAVAILABLE,
                message=f"Broker '{broker_name}' is currently disabled",
                severity=ErrorSeverity.MEDIUM
            )
            
        # Validate configuration
        validation_errors = self._validate_configuration(broker_name, config)
        if validation_errors:
            raise BrokerConfigurationError(
                broker_name, 
                f"Configuration validation failed: {'; '.join(validation_errors)}"
            )
            
        # Generate instance ID
        if instance_id is None:
            self._instance_counter += 1
            instance_id = f"{broker_name}_{self._instance_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        try:
            # Create adapter instance
            adapter_class = registration.adapter_class
            adapter = adapter_class(config)
            
            # Create instance record
            instance = BrokerInstance(
                instance_id=instance_id,
                broker_name=broker_name,
                adapter=adapter,
                config=config.copy(),  # Store copy of config
                status=BrokerStatus.INITIALIZING,
                created_at=datetime.now(timezone.utc)
            )
            
            # Authenticate if credentials provided
            credentials = config.get('credentials', {})
            if credentials:
                try:
                    auth_success = await adapter.authenticate(credentials)
                    if not auth_success:
                        raise BrokerAuthenticationError(
                            broker_name, 
                            "Authentication returned False"
                        )
                    instance.status = BrokerStatus.CONNECTED
                except Exception as e:
                    instance.status = BrokerStatus.ERROR
                    instance.last_error = StandardBrokerError(
                        error_code=StandardErrorCode.AUTHENTICATION_FAILED,
                        message=str(e),
                        context=ErrorContext(broker_name=broker_name)
                    )
                    raise BrokerAuthenticationError(broker_name, str(e))
            else:
                instance.status = BrokerStatus.DISCONNECTED
                
            # Store instance
            self._instances[instance_id] = instance
            
            logger.info(f"Created broker adapter instance: {instance_id} ({broker_name})")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to create adapter for {broker_name}: {e}")
            raise
            
    async def get_adapter(self, instance_id: str) -> Optional[BrokerAdapter]:
        """
        Get existing adapter instance
        
        Args:
            instance_id: Instance ID
            
        Returns:
            BrokerAdapter instance or None if not found
        """
        instance = self._instances.get(instance_id)
        return instance.adapter if instance else None
        
    async def destroy_adapter(self, instance_id: str) -> bool:
        """
        Destroy adapter instance
        
        Args:
            instance_id: Instance ID to destroy
            
        Returns:
            True if successfully destroyed
        """
        if instance_id not in self._instances:
            return False
            
        await self._cleanup_instance(instance_id)
        logger.info(f"Destroyed broker adapter instance: {instance_id}")
        return True
        
    def _validate_configuration(self, broker_name: str, config: Dict[str, Any]) -> List[str]:
        """
        Validate broker configuration
        
        Args:
            broker_name: Name of broker
            config: Configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        registration = self._registrations[broker_name]
        schema = registration.configuration_schema
        
        if not schema:
            return errors
            
        # Basic schema validation
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
                
        # Type validation
        properties = schema.get('properties', {})
        for field, value in config.items():
            if field in properties:
                expected_type = properties[field].get('type')
                if expected_type:
                    if expected_type == 'string' and not isinstance(value, str):
                        errors.append(f"Field '{field}' must be string")
                    elif expected_type == 'number' and not isinstance(value, (int, float)):
                        errors.append(f"Field '{field}' must be number")
                    elif expected_type == 'boolean' and not isinstance(value, bool):
                        errors.append(f"Field '{field}' must be boolean")
                        
        return errors
        
    def get_registered_brokers(self) -> List[str]:
        """Get list of registered broker names"""
        return list(self._registrations.keys())
        
    def get_enabled_brokers(self) -> List[str]:
        """Get list of enabled broker names"""
        return [name for name, reg in self._registrations.items() if reg.is_enabled]
        
    def get_broker_registration(self, broker_name: str) -> Optional[BrokerRegistration]:
        """Get broker registration information"""
        return self._registrations.get(broker_name)
        
    def get_broker_capabilities(self, broker_name: str) -> Set[BrokerCapability]:
        """
        Get capabilities for a specific broker
        
        Args:
            broker_name: Name of broker
            
        Returns:
            Set of supported capabilities
        """
        registration = self._registrations.get(broker_name)
        return registration.supported_capabilities if registration else set()
        
    def get_brokers_with_capability(self, capability: BrokerCapability) -> List[str]:
        """
        Get brokers that support specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of broker names with capability
        """
        return [
            name for name, registration in self._registrations.items()
            if capability in registration.supported_capabilities and registration.is_enabled
        ]
        
    def get_instance_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific instance"""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
            
        return {
            'instance_id': instance.instance_id,
            'broker_name': instance.broker_name,
            'status': instance.status.value,
            'created_at': instance.created_at.isoformat(),
            'last_health_check': instance.last_health_check.isoformat() if instance.last_health_check else None,
            'health_status': instance.health_status,
            'error_count': instance.error_count,
            'last_error': instance.last_error.to_dict() if instance.last_error else None
        }
        
    def get_all_instances(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all instances"""
        return {
            instance_id: self.get_instance_status(instance_id)
            for instance_id in self._instances.keys()
        }
        
    def get_factory_statistics(self) -> Dict[str, Any]:
        """Get factory statistics and health information"""
        total_instances = len(self._instances)
        connected_instances = sum(
            1 for instance in self._instances.values()
            if instance.status == BrokerStatus.CONNECTED
        )
        error_instances = sum(
            1 for instance in self._instances.values()
            if instance.status == BrokerStatus.ERROR
        )
        
        return {
            'registered_brokers': len(self._registrations),
            'enabled_brokers': len(self.get_enabled_brokers()),
            'total_instances': total_instances,
            'connected_instances': connected_instances,
            'error_instances': error_instances,
            'health_check_interval': self._health_check_interval,
            'registrations': {
                name: {
                    'display_name': reg.display_name,
                    'version': reg.version,
                    'enabled': reg.is_enabled,
                    'capabilities_count': len(reg.supported_capabilities)
                }
                for name, reg in self._registrations.items()
            }
        }
        
    def enable_broker(self, broker_name: str):
        """Enable a broker"""
        if broker_name in self._registrations:
            self._registrations[broker_name].is_enabled = True
            logger.info(f"Enabled broker: {broker_name}")
            
    def disable_broker(self, broker_name: str):
        """Disable a broker (prevents new instances)"""
        if broker_name in self._registrations:
            self._registrations[broker_name].is_enabled = False
            logger.info(f"Disabled broker: {broker_name}")
            
    async def auto_discover_adapters(self, discovery_paths: Optional[List[str]] = None):
        """
        Automatically discover and register broker adapters
        
        Args:
            discovery_paths: Optional list of module paths to search
        """
        if not self._auto_discovery_enabled:
            return
            
        paths = discovery_paths or self._discovery_paths
        discovered_count = 0
        
        for module_path in paths:
            try:
                # Import module
                module = importlib.import_module(module_path)
                
                # Look for BrokerAdapter subclasses
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BrokerAdapter) and 
                        obj != BrokerAdapter):
                        
                        # Extract broker name from class
                        broker_name = getattr(obj, '_broker_name', name.lower().replace('adapter', ''))
                        
                        if broker_name not in self._registrations:
                            self.register_adapter(
                                name=broker_name,
                                adapter_class=obj,
                                description=f"Auto-discovered adapter from {module_path}"
                            )
                            discovered_count += 1
                            
            except ImportError as e:
                logger.warning(f"Could not import discovery path {module_path}: {e}")
            except Exception as e:
                logger.error(f"Error during auto-discovery in {module_path}: {e}")
                
        if discovered_count > 0:
            logger.info(f"Auto-discovered {discovered_count} broker adapters")
            
    async def shutdown(self):
        """Shutdown factory and cleanup all resources"""
        logger.info("Shutting down broker factory...")
        
        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
                
        # Cleanup all instances
        instance_ids = list(self._instances.keys())
        for instance_id in instance_ids:
            await self._cleanup_instance(instance_id)
            
        logger.info("Broker factory shutdown complete")


# Global factory instance
_global_broker_factory: Optional[BrokerFactory] = None


def get_global_broker_factory() -> BrokerFactory:
    """Get global broker factory instance"""
    global _global_broker_factory
    if _global_broker_factory is None:
        _global_broker_factory = BrokerFactory()
    return _global_broker_factory


async def register_standard_brokers():
    """Register standard broker adapters"""
    factory = get_global_broker_factory()
    
    # Auto-discover adapters
    await factory.auto_discover_adapters()
    
    # Register known adapters if available
    try:
        from .adapters.oanda_adapter import OandaBrokerAdapter
        factory.register_adapter(
            name="oanda",
            adapter_class=OandaBrokerAdapter,
            display_name="OANDA",
            version="1.0.0",
            description="OANDA v20 API integration"
        )
    except ImportError:
        logger.info("OANDA adapter not available")
        
    # Add other brokers as they become available
    # try:
    #     from .adapters.interactive_brokers_adapter import IBBrokerAdapter
    #     factory.register_adapter("interactive_brokers", IBBrokerAdapter)
    # except ImportError:
    #     pass