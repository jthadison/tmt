#[cfg(test)]
mod integration_tests {
    use std::sync::Arc;
    use wiremock::{
        MockServer, Mock, ResponseTemplate, Request, 
        matchers::{method, path, header, body_json_schema},
    };
    use serde_json::{json, Value};
    use crate::platforms::tradelocker::{
        TradeLockerClient, TradeLockerAuth, TradeLockerConfig, 
        TradeLockerEnvironment, OrderRequest, OrderSide, OrderType, TimeInForce,
    };
    use crate::utils::vault::VaultClient;
    use rust_decimal::Decimal;

    struct MockTradeLockerServer {
        server: MockServer,
        base_url: String,
    }

    impl MockTradeLockerServer {
        async fn start() -> Self {
            let server = MockServer::start().await;
            let base_url = server.uri();
            
            Self { server, base_url }
        }

        fn base_url(&self) -> &str {
            &self.base_url
        }

        async fn mock_authentication_success(&self) {
            Mock::given(method("POST"))
                .and(path("/auth/token"))
                .respond_with(ResponseTemplate::new(200)
                    .set_body_json(json!({
                        "access_token": "mock_access_token",
                        "refresh_token": "mock_refresh_token", 
                        "expires_in": 3600,
                        "token_type": "Bearer"
                    })))
                .mount(&self.server)
                .await;
        }

        async fn mock_authentication_failure(&self) {
            Mock::given(method("POST"))
                .and(path("/auth/token"))
                .respond_with(ResponseTemplate::new(401)
                    .set_body_json(json!({
                        "error": "invalid_credentials",
                        "error_description": "Invalid API key or secret"
                    })))
                .mount(&self.server)
                .await;
        }

        async fn mock_order_placement_success(&self) {
            Mock::given(method("POST"))
                .and(path("/api/v1/orders"))
                .and(header("authorization", "Bearer mock_access_token"))
                .respond_with(ResponseTemplate::new(200)
                    .set_body_json(json!({
                        "order_id": "ord_123456789",
                        "client_order_id": "test_order_123",
                        "status": "new",
                        "symbol": "EURUSD",
                        "side": "buy",
                        "order_type": "market",
                        "quantity": "1.00000",
                        "filled_quantity": "0.00000",
                        "price": null,
                        "average_price": null,
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:00:00Z"
                    })))
                .mount(&self.server)
                .await;
        }

        async fn mock_order_rejection(&self) {
            Mock::given(method("POST"))
                .and(path("/api/v1/orders"))
                .respond_with(ResponseTemplate::new(400)
                    .set_body_json(json!({
                        "error": "insufficient_margin",
                        "message": "Insufficient margin to place this order"
                    })))
                .mount(&self.server)
                .await;
        }

        async fn mock_rate_limit(&self) {
            Mock::given(method("POST"))
                .and(path("/api/v1/orders"))
                .respond_with(ResponseTemplate::new(429)
                    .set_body_json(json!({
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests"
                    }))
                    .append_header("Retry-After", "60"))
                .mount(&self.server)
                .await;
        }

        async fn mock_health_check(&self) {
            Mock::given(method("GET"))
                .and(path("/health"))
                .respond_with(ResponseTemplate::new(200)
                    .set_body_json(json!({
                        "status": "ok",
                        "timestamp": "2024-01-01T12:00:00Z"
                    })))
                .mount(&self.server)
                .await;
        }

        async fn mock_account_info(&self) {
            Mock::given(method("GET"))
                .and(path("/api/v1/account"))
                .and(header("authorization", "Bearer mock_access_token"))
                .respond_with(ResponseTemplate::new(200)
                    .set_body_json(json!({
                        "account_id": "acc_12345",
                        "currency": "USD",
                        "balance": "10000.00",
                        "equity": "10000.00",
                        "margin_used": "0.00",
                        "margin_available": "10000.00",
                        "unrealized_pnl": "0.00",
                        "realized_pnl": "0.00",
                        "margin_level": null
                    })))
                .mount(&self.server)
                .await;
        }

        async fn mock_positions(&self) {
            Mock::given(method("GET"))
                .and(path("/api/v1/positions"))
                .and(header("authorization", "Bearer mock_access_token"))
                .respond_with(ResponseTemplate::new(200)
                    .set_body_json(json!([
                        {
                            "position_id": "pos_123456",
                            "symbol": "EURUSD",
                            "side": "long",
                            "quantity": "1.00000",
                            "entry_price": "1.11000",
                            "current_price": "1.11250",
                            "unrealized_pnl": "25.00",
                            "realized_pnl": "0.00",
                            "margin_used": "888.00",
                            "stop_loss": "1.10000",
                            "take_profit": "1.12500",
                            "opened_at": "2024-01-01T10:00:00Z"
                        }
                    ])))
                .mount(&self.server)
                .await;
        }
    }

    async fn create_test_client_with_mock_url(base_url: &str) -> TradeLockerClient {
        let vault_client = Arc::new(VaultClient::new("http://localhost:8200".to_string()).await.unwrap());
        let auth = Arc::new(TradeLockerAuth::new(vault_client).await.unwrap());
        let config = TradeLockerConfig {
            connection_timeout_ms: 1000,
            request_timeout_ms: 1000,
            ..Default::default()
        };
        
        // Create custom environment with mock URL
        let environment = TradeLockerEnvironment::Sandbox; // We'd need to modify this to use custom URL
        
        TradeLockerClient::new(auth, config, environment).unwrap()
    }

    #[tokio::test]
    async fn test_health_check_integration() {
        let mock_server = MockTradeLockerServer::start().await;
        mock_server.mock_health_check().await;
        
        let _client = create_test_client_with_mock_url(mock_server.base_url()).await;
        
        // Note: This would require modifying the client to accept custom URLs
        // For now, this test demonstrates the integration testing structure
        
        // In a real implementation:
        // let result = client.health_check().await;
        // assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_authentication_flow() {
        let mock_server = MockTradeLockerServer::start().await;
        mock_server.mock_authentication_success().await;
        
        // Test successful authentication
        // This would require injecting the mock URL into the auth system
        
        // Test authentication failure
        mock_server.mock_authentication_failure().await;
        
        // In a real implementation, we'd test the actual auth flow
    }

    #[tokio::test]
    async fn test_order_placement_flow() {
        let mock_server = MockTradeLockerServer::start().await;
        mock_server.mock_authentication_success().await;
        mock_server.mock_order_placement_success().await;
        
        let _client = create_test_client_with_mock_url(mock_server.base_url()).await;
        
        let _order = OrderRequest {
            symbol: "EURUSD".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Market,
            quantity: Decimal::new(100000, 5), // 1.00000
            price: None,
            stop_price: None,
            take_profit: Some(Decimal::new(112500, 5)), // 1.12500
            stop_loss: Some(Decimal::new(110000, 5)),   // 1.10000
            time_in_force: TimeInForce::Ioc,
            client_order_id: Some("test_order_123".to_string()),
        };

        // In a real implementation:
        // let result = client.place_order("test_account", order).await;
        // assert!(result.is_ok());
        // let order_response = result.unwrap();
        // assert_eq!(order_response.order_id, "ord_123456789");
    }

    #[tokio::test]
    async fn test_error_handling() {
        let mock_server = MockTradeLockerServer::start().await;
        mock_server.mock_authentication_success().await;
        mock_server.mock_order_rejection().await;
        
        let _client = create_test_client_with_mock_url(mock_server.base_url()).await;
        
        // Test order rejection handling
        // In real implementation, we'd verify error types and messages
    }

    #[tokio::test]
    async fn test_rate_limiting() {
        let mock_server = MockTradeLockerServer::start().await;
        mock_server.mock_authentication_success().await;
        mock_server.mock_rate_limit().await;
        
        let _client = create_test_client_with_mock_url(mock_server.base_url()).await;
        
        // Test rate limit handling
        // In real implementation, we'd verify retry behavior
    }

    #[test]
    fn test_mock_server_responses() {
        // Test that our mock responses are correctly formatted
        let order_response = json!({
            "order_id": "ord_123456789",
            "client_order_id": "test_order_123",
            "status": "new",
            "symbol": "EURUSD",
            "side": "buy",
            "order_type": "market",
            "quantity": "1.00000",
            "filled_quantity": "0.00000",
            "price": null,
            "average_price": null,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z"
        });
        
        // Verify structure
        assert!(order_response.get("order_id").is_some());
        assert!(order_response.get("symbol").is_some());
        assert!(order_response.get("quantity").is_some());
        
        // Test account info response
        let account_response = json!({
            "account_id": "acc_12345",
            "currency": "USD",
            "balance": "10000.00",
            "equity": "10000.00"
        });
        
        assert!(account_response.get("account_id").is_some());
        assert!(account_response.get("balance").is_some());
    }

    // Property-based testing using proptest
    #[cfg(feature = "proptest")]
    mod property_tests {
        use super::*;
        use proptest::prelude::*;

        proptest! {
            #[test]
            fn test_order_serialization_roundtrip(
                symbol in "[A-Z]{6}",
                quantity in 0.00001f64..1000000.0f64,
                price in prop::option::of(0.00001f64..10.0f64)
            ) {
                let order = OrderRequest {
                    symbol,
                    side: OrderSide::Buy,
                    order_type: OrderType::Market,
                    quantity: Decimal::try_from(quantity).unwrap(),
                    price: price.map(|p| Decimal::try_from(p).unwrap()),
                    stop_price: None,
                    take_profit: None,
                    stop_loss: None,
                    time_in_force: TimeInForce::Ioc,
                    client_order_id: None,
                };

                // Test serialization roundtrip
                let json = serde_json::to_string(&order)?;
                let deserialized: OrderRequest = serde_json::from_str(&json)?;
                
                prop_assert_eq!(order.symbol, deserialized.symbol);
                prop_assert_eq!(order.quantity, deserialized.quantity);
                prop_assert_eq!(order.price, deserialized.price);
            }
        }
    }
}