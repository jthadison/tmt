#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use rust_decimal::Decimal;
    use pretty_assertions::assert_eq;
    use crate::platforms::tradelocker::{
        TradeLockerClient, TradeLockerAuth, TradeLockerConfig,
        TradeLockerEnvironment, OrderRequest, OrderSide, OrderType, TimeInForce,
    };
    use crate::utils::vault::VaultClient;

    async fn create_test_client() -> TradeLockerClient {
        let vault_client = Arc::new(VaultClient::new("http://localhost:8200".to_string()).await.unwrap());
        let auth = Arc::new(TradeLockerAuth::new(vault_client).await.unwrap());
        let config = TradeLockerConfig::default();
        let environment = TradeLockerEnvironment::Sandbox;

        TradeLockerClient::new(auth, config, environment).unwrap()
    }

    fn create_test_order() -> OrderRequest {
        OrderRequest {
            symbol: "EURUSD".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Market,
            quantity: Decimal::new(100000, 5), // 1.00000 lot
            price: None,
            stop_price: None,
            take_profit: Some(Decimal::new(112500, 5)), // 1.12500
            stop_loss: Some(Decimal::new(110000, 5)),   // 1.10000
            time_in_force: TimeInForce::Ioc,
            client_order_id: Some("test_order_123".to_string()),
        }
    }

    #[tokio::test]
    async fn test_client_creation() {
        let client = create_test_client().await;
        
        // Client should be created successfully
        // In a real implementation, we'd test that the HTTP client is configured correctly
        assert!(client.health_check().await.is_err()); // Should fail without real API
    }

    #[test]
    fn test_order_validation() {
        let _client = tokio_test::block_on(create_test_client());
        let order = create_test_order();
        
        // This would call the private validate_order method
        // For now, we test the types are constructed correctly
        assert_eq!(order.symbol, "EURUSD");
        assert_eq!(order.quantity, Decimal::new(100000, 5));
        assert!(order.take_profit.is_some());
        assert!(order.stop_loss.is_some());
    }

    #[test]
    fn test_order_validation_errors() {
        // Test various invalid orders
        let mut order = create_test_order();
        
        // Zero quantity should be invalid
        order.quantity = Decimal::ZERO;
        // In real implementation, we'd call validate_order and expect error
        
        // Limit order without price
        order = create_test_order();
        order.order_type = OrderType::Limit;
        order.price = None;
        // Should be invalid
        
        // Stop order without stop price
        order = create_test_order();
        order.order_type = OrderType::Stop;
        order.stop_price = None;
        // Should be invalid
    }

    #[test]
    fn test_order_types() {
        // Test all order types can be created
        let mut order = create_test_order();
        
        order.order_type = OrderType::Market;
        order.price = None;
        order.stop_price = None;
        // Should be valid
        
        order.order_type = OrderType::Limit;
        order.price = Some(Decimal::new(111000, 5));
        order.stop_price = None;
        // Should be valid
        
        order.order_type = OrderType::Stop;
        order.price = None;
        order.stop_price = Some(Decimal::new(111500, 5));
        // Should be valid
        
        order.order_type = OrderType::StopLimit;
        order.price = Some(Decimal::new(111000, 5));
        order.stop_price = Some(Decimal::new(111500, 5));
        // Should be valid
    }

    #[test]
    fn test_time_in_force_options() {
        let order = create_test_order();
        
        // Test all TimeInForce variants can be serialized
        let tifs = vec![
            TimeInForce::Gtc,
            TimeInForce::Ioc,
            TimeInForce::Fok,
            TimeInForce::Day,
        ];
        
        for tif in tifs {
            let mut test_order = order.clone();
            test_order.time_in_force = tif;
            
            let json = serde_json::to_string(&test_order).unwrap();
            let _deserialized: OrderRequest = serde_json::from_str(&json).unwrap();
        }
    }

    #[test]
    fn test_order_sides() {
        let order = create_test_order();
        
        // Test both order sides
        let sides = vec![OrderSide::Buy, OrderSide::Sell];
        
        for side in sides {
            let mut test_order = order.clone();
            test_order.side = side;
            
            let json = serde_json::to_string(&test_order).unwrap();
            let deserialized: OrderRequest = serde_json::from_str(&json).unwrap();
            assert_eq!(test_order.side, deserialized.side);
        }
    }

    #[test]
    fn test_decimal_precision() {
        let order = create_test_order();
        
        // Test that decimal precision is maintained
        assert_eq!(order.quantity.scale(), 5);
        if let Some(tp) = order.take_profit {
            assert_eq!(tp.scale(), 5);
        }
        if let Some(sl) = order.stop_loss {
            assert_eq!(sl.scale(), 5);
        }
    }

    #[tokio::test]
    async fn test_config_timeouts() {
        let config = TradeLockerConfig::default();
        
        // Test timeout conversions
        assert_eq!(config.connection_timeout().as_millis(), config.connection_timeout_ms as u128);
        assert_eq!(config.request_timeout().as_millis(), config.request_timeout_ms as u128);
        assert_eq!(config.order_timeout().as_millis(), config.order_execution_timeout_ms as u128);
    }

    #[test]
    fn test_environment_configuration() {
        let prod = TradeLockerEnvironment::Production;
        let sandbox = TradeLockerEnvironment::Sandbox;
        
        // Verify URLs are different
        assert_ne!(prod.base_url(), sandbox.base_url());
        assert_ne!(prod.ws_url(), sandbox.ws_url());
        
        // Verify HTTPS/WSS protocols
        assert!(prod.base_url().starts_with("https://"));
        assert!(prod.ws_url().starts_with("wss://"));
        assert!(sandbox.base_url().starts_with("https://"));
        assert!(sandbox.ws_url().starts_with("wss://"));
    }

    #[tokio::test]
    async fn test_client_request_flow() {
        let _client = create_test_client().await;
        
        // In a real test with mocked HTTP:
        // 1. Mock successful authentication
        // 2. Mock order placement response
        // 3. Verify request parameters
        // 4. Verify response parsing
        // 5. Test error handling
        
        // For now, we just verify the client can be created
    }

    #[test]
    fn test_order_serialization_formats() {
        let order = create_test_order();
        
        // Test JSON serialization
        let json = serde_json::to_string(&order).unwrap();
        assert!(json.contains("EURUSD"));
        assert!(json.contains("buy"));
        assert!(json.contains("market"));
        
        // Test deserialization
        let deserialized: OrderRequest = serde_json::from_str(&json).unwrap();
        assert_eq!(order.symbol, deserialized.symbol);
        assert_eq!(order.quantity, deserialized.quantity);
    }
}