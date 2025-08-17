# Multi-Broker Support Foundation

This module implements Story 8.10: Multi-Account Broker Support Foundation, providing an extensible architecture for integrating multiple brokers with unified interfaces, configuration management, capability discovery, A/B testing, and performance comparison.

## Overview

The Multi-Broker Support Foundation enables the trading system to work with multiple brokers simultaneously, providing:

- **Unified broker interface** - Abstract base class for consistent broker interactions
- **Factory pattern** - Dynamic broker instantiation and lifecycle management  
- **Configuration management** - Hot-reloadable, environment-specific broker configurations
- **Unified error handling** - Standardized error codes and mapping across brokers
- **Capability discovery** - Automatic detection of broker features and limitations
- **A/B testing framework** - Intelligent order routing and performance comparison
- **Performance metrics** - Real-time monitoring and comparative analysis

## Architecture

```
broker-integration/
├── broker_adapter.py          # Abstract broker interface
├── broker_factory.py          # Factory for broker instantiation
├── broker_config.py           # Multi-broker configuration system
├── unified_errors.py          # Standardized error handling
├── capability_discovery.py    # Broker capability testing
├── ab_testing_framework.py    # A/B testing and routing
├── performance_metrics.py     # Performance monitoring and comparison
└── tests/
    └── test_multi_broker_foundation.py
```

## Quick Start

### 1. Basic Broker Integration

```python
from broker_integration import BrokerFactory, get_global_config_manager

# Register a broker adapter
factory = BrokerFactory()
factory.register_adapter('my_broker', MyBrokerAdapter)

# Configure the broker
config_manager = get_global_config_manager()
config = BrokerConfiguration(
    broker_name='my_broker',
    display_name='My Broker',
    credentials=BrokerCredentials(api_key='key', secret_key='secret'),
    endpoints=BrokerEndpoints(base_url='https://api.mybroker.com')
)
config_manager.set_configuration('my_broker', config)

# Create broker instance
adapter = await factory.create_adapter('my_broker', config.to_dict())
```

### 2. Capability Discovery

```python
from broker_integration import CapabilityDiscoveryEngine, CapabilityTestType

# Discover broker capabilities
discovery = CapabilityDiscoveryEngine()
profile = await discovery.discover_capabilities(
    adapter, 
    test_type=CapabilityTestType.DYNAMIC
)

print(f"Broker supports: {profile.capabilities}")
print(f"Instruments: {len(profile.supported_instruments)}")
```

### 3. A/B Testing

```python
from broker_integration import BrokerABTestingFramework, TrafficSplit

# Set up A/B testing
ab_framework = BrokerABTestingFramework()
ab_framework.register_broker_adapter('broker1', adapter1)
ab_framework.register_broker_adapter('broker2', adapter2)

# Create test
test_id = ab_framework.create_ab_test(
    test_name='Speed Comparison',
    description='Compare execution speed',
    traffic_splits=[
        TrafficSplit(broker_name='broker1', percentage=50.0),
        TrafficSplit(broker_name='broker2', percentage=50.0)
    ]
)

# Execute order through test
result = await ab_framework.execute_order_with_test(order, test_id)
```

### 4. Performance Monitoring

```python
from broker_integration import PerformanceMetricsCollector, ComparisonPeriod

# Set up performance monitoring
metrics = PerformanceMetricsCollector()
metrics.register_broker('broker1', adapter1)
metrics.register_broker('broker2', adapter2)
metrics.start_collection()

# Generate comparison report
comparison = await metrics.compare_brokers(
    ['broker1', 'broker2'],
    period=ComparisonPeriod.LAST_DAY
)

print(f"Winner: {comparison.winner}")
for recommendation in comparison.recommendations:
    print(f"- {recommendation}")
```

## Core Components

### BrokerAdapter

Abstract base class defining the unified broker interface:

- **Authentication**: `authenticate()`, `disconnect()`, `health_check()`
- **Orders**: `place_order()`, `modify_order()`, `cancel_order()`, `get_orders()`
- **Positions**: `get_positions()`, `close_position()`
- **Market Data**: `get_current_price()`, `stream_prices()`, `get_historical_data()`
- **Account Info**: `get_account_summary()`, `get_accounts()`

### BrokerFactory

Factory pattern for broker lifecycle management:

- **Registration**: Register broker adapter classes
- **Creation**: Instantiate and authenticate broker adapters
- **Discovery**: Auto-discover available broker adapters
- **Health Monitoring**: Monitor broker health and connectivity

### Configuration Management

Hot-reloadable configuration system:

- **Environment Support**: Development, staging, production configurations
- **Format Support**: JSON, YAML configuration files
- **Hot Reloading**: Automatic detection of configuration changes
- **Versioning**: Configuration history and rollback
- **Validation**: Comprehensive configuration validation

### Unified Error Handling

Standardized error handling across brokers:

- **Standard Error Codes**: Common error classification
- **Error Mapping**: Broker-specific to standard error mapping
- **Error Context**: Rich error information with suggestions
- **Error Analysis**: Aggregation and pattern detection

### Capability Discovery

Automated broker capability testing:

- **Static Discovery**: Based on broker documentation/configuration
- **Dynamic Discovery**: Real-time API testing
- **Synthetic Discovery**: Test orders with immediate cancellation
- **Capability Profiles**: Comprehensive capability documentation

### A/B Testing Framework

Intelligent order routing and testing:

- **Routing Strategies**: Hash-based, random, performance-based routing
- **Traffic Splitting**: Configurable percentage-based traffic allocation
- **Statistical Analysis**: Significance testing and confidence intervals
- **Performance Tracking**: Latency, success rate, error rate monitoring

### Performance Metrics

Real-time performance monitoring:

- **Metric Collection**: Latency, throughput, reliability, cost metrics
- **Benchmarking**: Comprehensive broker performance profiling
- **Comparison**: Multi-broker performance analysis
- **Recommendations**: Data-driven broker selection guidance

## Configuration

### Broker Configuration File

```json
{
  "broker_name": "oanda",
  "display_name": "OANDA",
  "enabled": true,
  "credentials": {
    "api_key": "your_api_key",
    "account_id": "your_account_id",
    "environment": "practice"
  },
  "endpoints": {
    "base_url": "https://api-fxpractice.oanda.com",
    "stream_url": "https://stream-fxpractice.oanda.com"
  },
  "limits": {
    "requests_per_second": 100,
    "max_orders_per_second": 10
  },
  "settings": {
    "timeout_seconds": 30,
    "retry_attempts": 3,
    "enable_streaming": true
  }
}
```

### Environment-Specific Configuration

```json
{
  "default": {
    "broker_name": "oanda",
    "display_name": "OANDA",
    "endpoints": {
      "base_url": "https://api-fxpractice.oanda.com"
    }
  },
  "production": {
    "endpoints": {
      "base_url": "https://api-fxtrade.oanda.com"
    },
    "credentials": {
      "environment": "live"
    }
  }
}
```

## Error Handling

### Standard Error Codes

- `AUTHENTICATION_FAILED` - Invalid credentials
- `INSUFFICIENT_FUNDS` - Not enough account balance
- `INVALID_INSTRUMENT` - Unsupported trading instrument
- `MARKET_CLOSED` - Market is closed for trading
- `RATE_LIMITED` - API rate limit exceeded
- `CONNECTION_ERROR` - Network connectivity issues
- `SERVICE_UNAVAILABLE` - Broker service unavailable

### Error Mapping Example

```python
from broker_integration import map_broker_error

# Map broker-specific error to standard error
error = map_broker_error(
    broker_name='oanda',
    broker_error_code='INSUFFICIENT_MARGIN',
    message='Not enough margin available'
)

print(f"Standard code: {error.error_code}")
print(f"Suggestion: {error.suggested_action}")
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest src/agents/broker-integration/tests/ -v

# Run specific test
python -m pytest src/agents/broker-integration/tests/test_multi_broker_foundation.py::TestBrokerAdapter -v

# Run integration test
python -m pytest src/agents/broker-integration/tests/test_multi_broker_foundation.py::test_integration_multi_broker_workflow -v
```

### Mock Broker Adapter

The test suite includes a `MockBrokerAdapter` for testing without real broker connections:

```python
from tests.test_multi_broker_foundation import MockBrokerAdapter

# Create mock adapter for testing
mock_adapter = MockBrokerAdapter({'broker_name': 'test_broker'})
await mock_adapter.authenticate({'api_key': 'test_key'})
```

## Integration Examples

### Adding a New Broker

1. **Create Broker Adapter**:

```python
class NewBrokerAdapter(BrokerAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize broker-specific configuration
        
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        # Implement broker authentication
        pass
        
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        # Implement order placement
        pass
        
    # Implement other required methods...
```

2. **Register with Factory**:

```python
factory = BrokerFactory()
factory.register_adapter('new_broker', NewBrokerAdapter)
```

3. **Add Configuration**:

```json
{
  "broker_name": "new_broker",
  "display_name": "New Broker",
  "credentials": {...},
  "endpoints": {...}
}
```

### Multi-Broker Order Execution

```python
# Set up multiple brokers
brokers = ['broker1', 'broker2', 'broker3']
factory = BrokerFactory()

# Create adapters
adapters = {}
for broker_name in brokers:
    config = config_manager.get_configuration(broker_name)
    adapters[broker_name] = await factory.create_adapter(broker_name, config.to_dict())

# Set up A/B testing
ab_framework = BrokerABTestingFramework()
for name, adapter in adapters.items():
    ab_framework.register_broker_adapter(name, adapter)

# Create performance-based routing test
test_id = ab_framework.create_ab_test(
    test_name='Multi-Broker Execution',
    description='Route orders based on performance',
    traffic_splits=[
        TrafficSplit(broker_name='broker1', percentage=40.0),
        TrafficSplit(broker_name='broker2', percentage=35.0),
        TrafficSplit(broker_name='broker3', percentage=25.0)
    ],
    routing_strategy=RoutingStrategy.PERFORMANCE_BASED
)

# Execute orders
for order in orders:
    result = await ab_framework.execute_order_with_test(order, test_id)
    if result.success:
        print(f"Order {order.order_id} executed successfully")
```

## Best Practices

### 1. Error Handling

- Always map broker-specific errors to standard error codes
- Provide actionable error messages and suggestions
- Log errors with sufficient context for debugging

### 2. Configuration Management

- Use environment-specific configurations
- Never commit sensitive credentials to version control
- Validate configurations before deployment

### 3. Performance Monitoring

- Monitor all brokers continuously
- Set up alerts for performance degradation
- Use A/B testing to validate broker changes

### 4. Capability Discovery

- Run capability discovery periodically
- Cache capability profiles for performance
- Handle capability changes gracefully

### 5. Testing

- Test with mock adapters before production
- Use synthetic testing for critical functionality
- Monitor test results for statistical significance

## Monitoring and Observability

### Performance Metrics

- **Latency**: Order execution latency (avg, p95, p99)
- **Throughput**: Orders per second capability
- **Reliability**: Success rate, error rate, uptime
- **Cost**: Commission, spread, total fees

### Health Checks

- Broker connectivity status
- API rate limit utilization
- Authentication status
- Market data feed health

### Alerting

Set up alerts for:
- Broker connectivity issues
- High error rates
- Performance degradation
- Configuration validation failures

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify credentials are correct
   - Check credential environment (practice vs live)
   - Ensure API key permissions

2. **Connection Timeouts**
   - Check network connectivity
   - Verify endpoint URLs
   - Increase timeout settings

3. **Rate Limiting**
   - Monitor API usage rates
   - Implement exponential backoff
   - Distribute requests across brokers

4. **Configuration Errors**
   - Validate configuration files
   - Check environment-specific overrides
   - Review configuration history

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger('broker_integration').setLevel(logging.DEBUG)
```

## Security Considerations

- Store credentials securely (encrypted at rest)
- Use environment variables for sensitive configuration
- Implement proper authentication token rotation
- Monitor for suspicious trading patterns
- Validate all input data

## Performance Optimization

- Cache broker capabilities and configurations
- Use connection pooling for HTTP requests
- Implement circuit breakers for failing brokers
- Batch operations where possible
- Monitor and optimize memory usage

## Future Enhancements

- **Machine Learning Integration**: Predictive broker routing
- **Advanced Analytics**: Real-time performance dashboards
- **Risk Management**: Position size optimization per broker
- **Regulatory Compliance**: Automated compliance checking
- **Cost Optimization**: Dynamic fee minimization

---

For detailed API documentation, see the individual module docstrings. For examples and tutorials, see the `examples/` directory.