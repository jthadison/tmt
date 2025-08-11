#[cfg(test)]
mod integration_tests {
    use super::*;
    use tokio::time::{sleep, Duration};
    use std::sync::Arc;
    use std::collections::HashMap;
    use crate::platforms::{PlatformType, ITradingPlatform, PlatformError, UnifiedOrderResponse, UnifiedPosition, UnifiedPositionSide};

    // Mock implementations for testing
    struct MockTradeLockerClient {
        pub should_fail_connection: bool,
        pub should_fail_orders: bool,
        pub order_latency_ms: u64,
        pub orders: Arc<tokio::sync::Mutex<Vec<UnifiedOrderResponse>>>,
        pub positions: Arc<tokio::sync::Mutex<Vec<UnifiedPosition>>>,
        pub connection_count: Arc<tokio::sync::Mutex<u32>>,
    }

    impl MockTradeLockerClient {
        fn new() -> Self {
            Self {
                should_fail_connection: false,
                should_fail_orders: false,
                order_latency_ms: 50,
                orders: Arc::new(tokio::sync::Mutex::new(Vec::new())),
                positions: Arc::new(tokio::sync::Mutex::new(Vec::new())),
                connection_count: Arc::new(tokio::sync::Mutex::new(0)),
            }
        }

        async fn simulate_connection_failure(&mut self) {
            self.should_fail_connection = true;
        }

        async fn simulate_order_failures(&mut self) {
            self.should_fail_orders = true;
        }

        async fn add_test_position(&self, symbol: &str, quantity: rust_decimal::Decimal) {
            let position = UnifiedPosition {
                position_id: format!("pos_{}", symbol),
                symbol: symbol.to_string(),
                side: if quantity > rust_decimal::Decimal::ZERO { 
                    UnifiedPositionSide::Long 
                } else { 
                    UnifiedPositionSide::Short 
                },
                quantity: quantity.abs(),
                entry_price: rust_decimal::Decimal::new(11000, 4), // 1.1000
                current_price: rust_decimal::Decimal::new(11050, 4), // 1.1050
                unrealized_pnl: rust_decimal::Decimal::new(50, 0),
                realized_pnl: rust_decimal::Decimal::ZERO,
                margin_used: rust_decimal::Decimal::new(1000, 0),
                commission: rust_decimal::Decimal::new(5, 0),
                stop_loss: None,
                take_profit: None,
                opened_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
                account_id: "test_account".to_string(),
                platform_specific: HashMap::new(),
            };
            self.positions.lock().await.push(position);
        }
    }

    struct MockPlatformAdapter {
        client: MockTradeLockerClient,
        platform_type: PlatformType,
        is_connected: bool,
    }

    impl MockPlatformAdapter {
        fn new(platform_type: PlatformType) -> Self {
            Self {
                client: MockTradeLockerClient::new(),
                platform_type,
                is_connected: false,
            }
        }
    }

    #[async_trait::async_trait]
    impl ITradingPlatform for MockPlatformAdapter {
        fn platform_type(&self) -> PlatformType { self.platform_type.clone() }
        fn platform_name(&self) -> &str { "MockPlatform" }
        fn platform_version(&self) -> &str { "1.0.0" }

        async fn connect(&mut self) -> std::result::Result<(), PlatformError> {
            if self.client.should_fail_connection {
                return Err(PlatformError::ConnectionFailed { 
                    reason: "Mock connection failure".to_string() 
                });
            }
            
            let mut count = self.client.connection_count.lock().await;
            *count += 1;
            self.is_connected = true;
            
            // Simulate connection latency
            sleep(Duration::from_millis(100)).await;
            Ok(())
        }

        async fn disconnect(&mut self) -> std::result::Result<(), PlatformError> {
            self.is_connected = false;
            Ok(())
        }

        async fn is_connected(&self) -> bool { self.is_connected }

        async fn ping(&self) -> std::result::Result<u64, PlatformError> {
            if !self.is_connected {
                return Err(PlatformError::Disconnected { 
                    reason: "Not connected".to_string() 
                });
            }
            Ok(25) // Mock 25ms latency
        }

        async fn place_order(&self, order: UnifiedOrder) -> std::result::Result<UnifiedOrderResponse, PlatformError> {
            if !self.is_connected {
                return Err(PlatformError::Disconnected { 
                    reason: "Cannot place order while disconnected".to_string() 
                });
            }

            if self.client.should_fail_orders {
                return Err(PlatformError::OrderRejected { 
                    reason: "Mock order rejection".to_string(),
                    platform_code: Some("MOCK_REJECT".to_string()),
                });
            }

            // Simulate order processing latency
            sleep(Duration::from_millis(self.client.order_latency_ms)).await;

            let response = UnifiedOrderResponse {
                platform_order_id: format!("mock_order_{}", uuid::Uuid::new_v4()),
                client_order_id: order.client_order_id,
                status: UnifiedOrderStatus::Filled,
                symbol: order.symbol,
                side: order.side,
                order_type: order.order_type,
                quantity: order.quantity,
                filled_quantity: order.quantity,
                remaining_quantity: rust_decimal::Decimal::ZERO,
                price: order.price,
                average_fill_price: order.price,
                commission: Some(rust_decimal::Decimal::new(5, 0)),
                created_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
                filled_at: Some(chrono::Utc::now()),
                platform_specific: HashMap::new(),
            };

            self.client.orders.lock().await.push(response.clone());
            Ok(response)
        }

        async fn modify_order(&self, _order_id: &str, _modifications: OrderModification) -> std::result::Result<UnifiedOrderResponse, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "Order modification".to_string() })
        }

        async fn cancel_order(&self, _order_id: &str) -> std::result::Result<(), PlatformError> {
            if !self.is_connected {
                return Err(PlatformError::Disconnected { 
                    reason: "Cannot cancel order while disconnected".to_string() 
                });
            }
            Ok(())
        }

        async fn get_order(&self, _order_id: &str) -> std::result::Result<UnifiedOrderResponse, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "Get specific order".to_string() })
        }

        async fn get_orders(&self, _filter: Option<OrderFilter>) -> std::result::Result<Vec<UnifiedOrderResponse>, PlatformError> {
            if !self.is_connected {
                return Err(PlatformError::Disconnected { 
                    reason: "Cannot get orders while disconnected".to_string() 
                });
            }
            Ok(self.client.orders.lock().await.clone())
        }

        async fn get_positions(&self) -> std::result::Result<Vec<UnifiedPosition>, PlatformError> {
            if !self.is_connected {
                return Err(PlatformError::Disconnected { 
                    reason: "Cannot get positions while disconnected".to_string() 
                });
            }
            Ok(self.client.positions.lock().await.clone())
        }

        async fn get_position(&self, symbol: &str) -> std::result::Result<Option<UnifiedPosition>, PlatformError> {
            let positions = self.get_positions().await?;
            Ok(positions.into_iter().find(|p| p.symbol == symbol))
        }

        async fn close_position(&self, symbol: &str, _quantity: Option<rust_decimal::Decimal>) -> std::result::Result<UnifiedOrderResponse, PlatformError> {
            let position = self.get_position(symbol).await?
                .ok_or_else(|| PlatformError::PositionNotFound { symbol: symbol.to_string() })?;

            let close_order = UnifiedOrder {
                client_order_id: format!("close_{}", uuid::Uuid::new_v4()),
                symbol: symbol.to_string(),
                side: match position.side {
                    UnifiedPositionSide::Long => UnifiedOrderSide::Sell,
                    UnifiedPositionSide::Short => UnifiedOrderSide::Buy,
                },
                order_type: UnifiedOrderType::Market,
                quantity: position.quantity,
                price: None,
                stop_price: None,
                take_profit: None,
                stop_loss: None,
                time_in_force: UnifiedTimeInForce::Ioc,
                account_id: Some("test_account".to_string()),
                metadata: OrderMetadata {
                    strategy_id: None,
                    signal_id: None,
                    risk_parameters: HashMap::new(),
                    tags: vec!["position_close".to_string()],
                    expires_at: None,
                },
            };

            self.place_order(close_order).await
        }

        async fn get_account_info(&self) -> std::result::Result<UnifiedAccountInfo, PlatformError> {
            if !self.is_connected {
                return Err(PlatformError::Disconnected { 
                    reason: "Cannot get account info while disconnected".to_string() 
                });
            }

            Ok(UnifiedAccountInfo {
                account_id: "mock_account_123".to_string(),
                account_name: Some("Mock Trading Account".to_string()),
                currency: "USD".to_string(),
                balance: rust_decimal::Decimal::new(100000, 2), // $1000.00
                equity: rust_decimal::Decimal::new(105000, 2), // $1050.00
                margin_used: rust_decimal::Decimal::new(10000, 2), // $100.00
                margin_available: rust_decimal::Decimal::new(90000, 2), // $900.00
                buying_power: rust_decimal::Decimal::new(180000, 2), // $1800.00
                unrealized_pnl: rust_decimal::Decimal::new(5000, 2), // $50.00
                realized_pnl: rust_decimal::Decimal::ZERO,
                margin_level: Some(rust_decimal::Decimal::new(1050, 0)), // 1050%
                account_type: AccountType::Demo,
                last_updated: chrono::Utc::now(),
                platform_specific: HashMap::new(),
            })
        }

        async fn get_balance(&self) -> std::result::Result<rust_decimal::Decimal, PlatformError> {
            let account = self.get_account_info().await?;
            Ok(account.balance)
        }

        async fn get_margin_info(&self) -> std::result::Result<MarginInfo, PlatformError> {
            let account = self.get_account_info().await?;
            Ok(MarginInfo {
                initial_margin: account.margin_used,
                maintenance_margin: account.margin_used,
                margin_call_level: Some(rust_decimal::Decimal::new(100, 0)), // 100%
                stop_out_level: Some(rust_decimal::Decimal::new(50, 0)), // 50%
                margin_requirements: HashMap::new(),
            })
        }

        async fn get_market_data(&self, symbol: &str) -> std::result::Result<UnifiedMarketData, PlatformError> {
            if !self.is_connected {
                return Err(PlatformError::MarketDataUnavailable { 
                    reason: "Not connected".to_string() 
                });
            }

            Ok(UnifiedMarketData {
                symbol: symbol.to_string(),
                bid: rust_decimal::Decimal::new(11000, 4), // 1.1000
                ask: rust_decimal::Decimal::new(11003, 4), // 1.1003
                spread: rust_decimal::Decimal::new(3, 4), // 0.0003
                last_price: Some(rust_decimal::Decimal::new(11001, 4)), // 1.1001
                volume: Some(rust_decimal::Decimal::new(1000000, 0)),
                high: Some(rust_decimal::Decimal::new(11050, 4)),
                low: Some(rust_decimal::Decimal::new(10950, 4)),
                timestamp: chrono::Utc::now(),
                session: Some(TradingSession::Regular),
                platform_specific: HashMap::new(),
            })
        }

        async fn subscribe_market_data(&self, _symbols: Vec<String>) -> std::result::Result<tokio::sync::mpsc::Receiver<UnifiedMarketData>, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "Market data subscription".to_string() })
        }

        async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> std::result::Result<(), PlatformError> {
            Ok(())
        }

        fn capabilities(&self) -> PlatformCapabilities {
            tradelocker_capabilities()
        }

        async fn subscribe_events(&self) -> std::result::Result<tokio::sync::mpsc::Receiver<PlatformEvent>, PlatformError> {
            let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
            // Mock implementation - would normally set up event streaming
            Ok(rx)
        }

        async fn get_event_history(&self, _filter: EventFilter) -> std::result::Result<Vec<PlatformEvent>, PlatformError> {
            Ok(Vec::new())
        }

        async fn health_check(&self) -> std::result::Result<HealthStatus, PlatformError> {
            Ok(HealthStatus {
                is_healthy: self.is_connected,
                last_ping: Some(chrono::Utc::now()),
                latency_ms: Some(25),
                error_rate: 0.01,
                uptime_seconds: 3600,
                issues: if !self.is_connected { 
                    vec!["Not connected".to_string()] 
                } else { 
                    Vec::new() 
                },
            })
        }

        async fn get_diagnostics(&self) -> std::result::Result<DiagnosticsInfo, PlatformError> {
            let mut performance_metrics = HashMap::new();
            performance_metrics.insert("mock_metric".to_string(), serde_json::Value::String("test".to_string()));

            Ok(DiagnosticsInfo {
                connection_status: if self.is_connected { "Connected".to_string() } else { "Disconnected".to_string() },
                api_limits: HashMap::new(),
                performance_metrics,
                last_errors: Vec::new(),
                platform_specific: HashMap::new(),
            })
        }
    }

    // Integration Tests
    
    #[tokio::test]
    async fn test_platform_connection_lifecycle() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        
        // Initially disconnected
        assert!(!platform.is_connected().await);
        
        // Connect should succeed
        let result = platform.connect().await;
        assert!(result.is_ok());
        assert!(platform.is_connected().await);
        
        // Ping should work when connected
        let ping_result = platform.ping().await;
        assert!(ping_result.is_ok());
        assert_eq!(ping_result.unwrap(), 25);
        
        // Disconnect should succeed
        let result = platform.disconnect().await;
        assert!(result.is_ok());
        assert!(!platform.is_connected().await);
    }

    #[tokio::test]
    async fn test_connection_failure_scenarios() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        platform.client.simulate_connection_failure().await;
        
        // Connection should fail
        let result = platform.connect().await;
        assert!(result.is_err());
        assert!(!platform.is_connected().await);
        
        // Operations should fail when disconnected
        let ping_result = platform.ping().await;
        assert!(ping_result.is_err());
        
        let orders_result = platform.get_orders(None).await;
        assert!(orders_result.is_err());
    }

    #[tokio::test]
    async fn test_order_lifecycle_integration() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        platform.connect().await.expect("Should connect");
        
        // Create test order
        let order = UnifiedOrder {
            client_order_id: "test_order_123".to_string(),
            symbol: "EURUSD".to_string(),
            side: UnifiedOrderSide::Buy,
            order_type: UnifiedOrderType::Market,
            quantity: rust_decimal::Decimal::new(100000, 0),
            price: Some(rust_decimal::Decimal::new(11000, 4)),
            stop_price: None,
            take_profit: None,
            stop_loss: None,
            time_in_force: UnifiedTimeInForce::Ioc,
            account_id: Some("test_account".to_string()),
            metadata: OrderMetadata {
                strategy_id: Some("test_strategy".to_string()),
                signal_id: Some("test_signal".to_string()),
                risk_parameters: HashMap::new(),
                tags: vec!["integration_test".to_string()],
                expires_at: None,
            },
        };
        
        // Place order
        let start_time = std::time::Instant::now();
        let order_result = platform.place_order(order.clone()).await;
        let order_latency = start_time.elapsed();
        
        assert!(order_result.is_ok());
        let order_response = order_result.unwrap();
        
        // Verify order details
        assert_eq!(order_response.client_order_id, "test_order_123");
        assert_eq!(order_response.symbol, "EURUSD");
        assert_eq!(order_response.status, UnifiedOrderStatus::Filled);
        assert_eq!(order_response.quantity, order.quantity);
        
        // Verify performance requirements
        assert!(order_latency.as_millis() < 100, "Order placement should be under 100ms");
        
        // Get orders should include our order
        let orders = platform.get_orders(None).await.expect("Should get orders");
        assert_eq!(orders.len(), 1);
        assert_eq!(orders[0].client_order_id, "test_order_123");
    }

    #[tokio::test]
    async fn test_order_rejection_scenarios() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        platform.connect().await.expect("Should connect");
        platform.client.simulate_order_failures().await;
        
        let order = UnifiedOrder {
            client_order_id: "reject_test".to_string(),
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
                risk_parameters: HashMap::new(),
                tags: Vec::new(),
                expires_at: None,
            },
        };
        
        // Order should be rejected
        let result = platform.place_order(order).await;
        assert!(result.is_err());
        
        match result.unwrap_err() {
            PlatformError::OrderRejected { reason, platform_code } => {
                assert_eq!(reason, "Mock order rejection");
                assert_eq!(platform_code, Some("MOCK_REJECT".to_string()));
            }
            _ => panic!("Expected OrderRejected error"),
        }
    }

    #[tokio::test]
    async fn test_position_management_integration() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        platform.connect().await.expect("Should connect");
        
        // Add test positions
        platform.client.add_test_position("EURUSD", rust_decimal::Decimal::new(100000, 0)).await;
        platform.client.add_test_position("GBPUSD", rust_decimal::Decimal::new(-50000, 0)).await;
        
        // Get all positions
        let positions = platform.get_positions().await.expect("Should get positions");
        assert_eq!(positions.len(), 2);
        
        // Get specific position
        let eur_position = platform.get_position("EURUSD").await.expect("Should get EURUSD position");
        assert!(eur_position.is_some());
        let eur_pos = eur_position.unwrap();
        assert_eq!(eur_pos.symbol, "EURUSD");
        assert_eq!(eur_pos.side, UnifiedPositionSide::Long);
        
        // Close position
        let close_result = platform.close_position("EURUSD", None).await;
        assert!(close_result.is_ok());
        let close_order = close_result.unwrap();
        assert_eq!(close_order.symbol, "EURUSD");
        assert_eq!(close_order.side, UnifiedOrderSide::Sell); // Closing long position
    }

    #[tokio::test]
    async fn test_account_info_integration() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        platform.connect().await.expect("Should connect");
        
        // Get account info
        let account = platform.get_account_info().await.expect("Should get account info");
        assert_eq!(account.account_id, "mock_account_123");
        assert_eq!(account.currency, "USD");
        assert!(account.balance > rust_decimal::Decimal::ZERO);
        assert!(account.equity >= account.balance);
        
        // Get balance directly
        let balance = platform.get_balance().await.expect("Should get balance");
        assert_eq!(balance, account.balance);
        
        // Get margin info
        let margin = platform.get_margin_info().await.expect("Should get margin info");
        assert!(margin.margin_call_level.is_some());
        assert!(margin.stop_out_level.is_some());
    }

    #[tokio::test]
    async fn test_market_data_integration() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        platform.connect().await.expect("Should connect");
        
        // Get market data
        let market_data = platform.get_market_data("EURUSD").await.expect("Should get market data");
        assert_eq!(market_data.symbol, "EURUSD");
        assert!(market_data.bid > rust_decimal::Decimal::ZERO);
        assert!(market_data.ask > market_data.bid);
        assert!(market_data.spread > rust_decimal::Decimal::ZERO);
        assert!(market_data.volume.is_some());
        assert!(market_data.high.is_some());
        assert!(market_data.low.is_some());
    }

    #[tokio::test]
    async fn test_performance_requirements() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        platform.connect().await.expect("Should connect");
        
        let performance_monitor = PerformanceMonitor::new();
        
        // Test multiple operations for performance
        for i in 0..10 {
            let timer = performance_monitor.start_operation("get_account_info");
            let _ = platform.get_account_info().await;
            timer.success();
            
            let timer = performance_monitor.start_operation("get_market_data");
            let _ = platform.get_market_data("EURUSD").await;
            timer.success();
        }
        
        // Check performance metrics
        let account_stats = performance_monitor.get_operation_stats("get_account_info").unwrap();
        let market_stats = performance_monitor.get_operation_stats("get_market_data").unwrap();
        
        // Verify abstraction overhead is minimal (should be sub-millisecond for mocks)
        assert!(account_stats.avg.as_millis() < 10, "Account info should be fast");
        assert!(market_stats.avg.as_millis() < 10, "Market data should be fast");
        
        // Check SLA compliance
        let sla_report = performance_monitor.check_sla_compliance();
        assert!(sla_report.overall_error_rate < 0.1, "Error rate should be low");
    }

    #[tokio::test]
    async fn test_error_handling_and_recovery() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        
        // Test operations while disconnected
        let ping_result = platform.ping().await;
        assert!(matches!(ping_result, Err(PlatformError::Disconnected { .. })));
        
        let orders_result = platform.get_orders(None).await;
        assert!(matches!(orders_result, Err(PlatformError::Disconnected { .. })));
        
        // Connect and test error recovery
        platform.connect().await.expect("Should connect");
        
        // Now operations should work
        let ping_result = platform.ping().await;
        assert!(ping_result.is_ok());
        
        let orders_result = platform.get_orders(None).await;
        assert!(orders_result.is_ok());
    }

    #[tokio::test]
    async fn test_capability_detection() {
        let platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        let capabilities = platform.capabilities();
        
        assert_eq!(capabilities.platform_name, "TradeLocker");
        assert!(capabilities.supports_feature(PlatformFeature::MarketOrders));
        assert!(capabilities.supports_feature(PlatformFeature::LimitOrders));
        assert!(capabilities.supports_order_type(&UnifiedOrderType::Market));
        assert!(capabilities.supports_order_type(&UnifiedOrderType::Limit));
        assert!(capabilities.supports_time_in_force(&UnifiedTimeInForce::Ioc));
        
        // Test performance expectations
        let latency = capabilities.estimate_latency(crate::platforms::abstraction::capabilities::PlatformOperation::PlaceOrder);
        assert!(latency.is_some());
        assert!(latency.unwrap() <= 100); // Should be under 100ms
    }

    #[tokio::test]
    async fn test_concurrent_operations() {
        let platform = Arc::new(tokio::sync::Mutex::new(MockPlatformAdapter::new(PlatformType::TradeLocker)));
        
        // Connect first
        {
            let mut p = platform.lock().await;
            p.connect().await.expect("Should connect");
        }
        
        // Test concurrent operations
        let mut handles = Vec::new();
        
        for i in 0..10 {
            let platform_clone = Arc::clone(&platform);
            let handle = tokio::spawn(async move {
                let p = platform_clone.lock().await;
                let result = p.get_account_info().await;
                assert!(result.is_ok());
                i
            });
            handles.push(handle);
        }
        
        // Wait for all operations to complete
        for handle in handles {
            handle.await.expect("Task should complete");
        }
    }

    #[tokio::test]
    async fn test_platform_registry_integration() {
        let mut registry = PlatformRegistry::new();
        
        // This would normally use real platform configs
        // For now, we'll test the structure exists
        let accounts = registry.list_accounts();
        assert!(accounts.is_empty());
        
        // Test health check on empty registry
        let health_results = registry.health_check_all().await;
        assert!(health_results.is_empty());
    }

    #[tokio::test]
    async fn test_event_system_integration() {
        let platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        
        // Test event subscription (mock implementation)
        let event_receiver = platform.subscribe_events().await;
        assert!(event_receiver.is_ok());
        
        // Test event history
        let event_filter = EventFilter::new();
        let events = platform.get_event_history(event_filter).await;
        assert!(events.is_ok());
        assert!(events.unwrap().is_empty()); // Mock returns empty
    }

    #[tokio::test]
    async fn test_stress_scenario_high_frequency() {
        let mut platform = MockPlatformAdapter::new(PlatformType::TradeLocker);
        platform.connect().await.expect("Should connect");
        
        // Reduce latency for stress test
        platform.client.order_latency_ms = 1;
        
        let performance_monitor = PerformanceMonitor::new();
        let start_time = std::time::Instant::now();
        
        // Place 100 orders rapidly
        for i in 0..100 {
            let order = UnifiedOrder {
                client_order_id: format!("stress_order_{}", i),
                symbol: "EURUSD".to_string(),
                side: if i % 2 == 0 { UnifiedOrderSide::Buy } else { UnifiedOrderSide::Sell },
                order_type: UnifiedOrderType::Market,
                quantity: rust_decimal::Decimal::new(10000, 0),
                price: None,
                stop_price: None,
                take_profit: None,
                stop_loss: None,
                time_in_force: UnifiedTimeInForce::Ioc,
                account_id: Some("stress_test".to_string()),
                metadata: OrderMetadata {
                    strategy_id: Some("stress_strategy".to_string()),
                    signal_id: None,
                    risk_parameters: HashMap::new(),
                    tags: vec!["stress_test".to_string()],
                    expires_at: None,
                },
            };
            
            let timer = performance_monitor.start_operation("place_order_stress");
            let result = platform.place_order(order).await;
            if result.is_ok() {
                timer.success();
            } else {
                timer.error(&result.unwrap_err());
            }
        }
        
        let total_time = start_time.elapsed();
        let throughput = 100.0 / total_time.as_secs_f64();
        
        println!("Stress test completed: {} orders/second", throughput);
        
        // Verify all orders were processed
        let orders = platform.get_orders(None).await.expect("Should get orders");
        assert_eq!(orders.len(), 100);
        
        // Check performance under stress
        let metrics = performance_monitor.get_metrics();
        assert_eq!(metrics.total_operations, 100);
        assert!(metrics.error_rate() < 0.05); // Less than 5% error rate
    }
}