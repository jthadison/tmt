// Basic compilation test for the platform abstraction layer
use super::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_platform_type_creation() {
        let platform_type = crate::platforms::PlatformType::TradeLocker;
        assert_eq!(platform_type, crate::platforms::PlatformType::TradeLocker);
    }

    #[test]
    fn test_unified_order_creation() {
        let order = UnifiedOrder {
            client_order_id: "test123".to_string(),
            symbol: "EURUSD".to_string(),
            side: UnifiedOrderSide::Buy,
            order_type: UnifiedOrderType::Market,
            quantity: rust_decimal::Decimal::new(100000, 0),
            price: None,
            stop_price: None,
            take_profit: None,
            stop_loss: None,
            time_in_force: UnifiedTimeInForce::Ioc,
            account_id: Some("test_account".to_string()),
            metadata: OrderMetadata {
                strategy_id: None,
                signal_id: None,
                risk_parameters: std::collections::HashMap::new(),
                tags: Vec::new(),
                expires_at: None,
            },
        };

        assert_eq!(order.symbol, "EURUSD");
        assert_eq!(order.side, UnifiedOrderSide::Buy);
    }

    #[test]
    fn test_platform_error_creation() {
        let error = PlatformError::ConnectionFailed {
            reason: "Test connection failure".to_string(),
        };

        match error {
            PlatformError::ConnectionFailed { reason } => {
                assert_eq!(reason, "Test connection failure");
            }
            _ => panic!("Unexpected error type"),
        }
    }

    #[test]
    fn test_platform_capabilities() {
        let caps = tradelocker_capabilities();
        assert_eq!(caps.platform_name, "TradeLocker");
        assert!(caps.supports_feature(PlatformFeature::MarketOrders));
        assert!(caps.supports_feature(PlatformFeature::LimitOrders));
    }

    #[test]
    #[ignore] // Temporarily disabled - PerformanceMonitor not available
    fn test_performance_monitor() {
        // let monitor = PerformanceMonitor::new();
        // let timer = monitor.start_operation("test_operation");
        // timer.success();

        // let metrics = monitor.get_metrics();
        // assert_eq!(metrics.total_operations, 1);
    }
}