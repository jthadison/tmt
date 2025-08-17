"""
Multi-Broker Support Foundation
Story 8.10 - Main Package
"""

# We'll export these when the modules are properly imported
# For now, just make this an empty package to allow testing

__all__ = [
    # Broker Adapter
    'BrokerAdapter',
    'BrokerCapability',
    'OrderType',
    'OrderSide',
    'TimeInForce',
    'UnifiedOrder',
    'UnifiedPosition',
    'UnifiedAccountSummary',
    'OrderResult',
    'PriceTick',
    'BrokerInfo',
    
    # Unified Errors
    'StandardBrokerError',
    'StandardErrorCode',
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorContext',
    'ErrorCodeMapper',
    'error_mapper',
    'map_broker_error',
    
    # Broker Factory
    'BrokerFactory',
    'BrokerRegistration',
    'BrokerInstance',
    'BrokerStatus',
    'UnsupportedBrokerError',
    'BrokerAuthenticationError',
    'BrokerConfigurationError',
    
    # Configuration
    'ConfigurationManager',
    'BrokerConfiguration',
    'BrokerCredentials',
    'BrokerEndpoints',
    'BrokerLimits',
    'BrokerSettings',
    'ConfigEnvironment',
    'get_global_config_manager',
    
    # Capability Discovery
    'CapabilityDiscoveryEngine',
    'CapabilityTestResult',
    'CapabilityTestType',
    'BrokerCapabilityProfile',
    'InstrumentInfo',
    
    # A/B Testing
    'BrokerABTestingFramework',
    'ABTestConfig',
    'TrafficSplit',
    'RoutingStrategy',
    'ABTestStatus',
    'OrderExecution',
    'MetricType',
    
    # Performance Metrics
    'PerformanceMetricsCollector',
    'BrokerBenchmark',
    'BrokerComparison',
    'ComparisonPeriod',
    'BenchmarkType',
    'MetricSnapshot',
]

__version__ = '1.0.0'