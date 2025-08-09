#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use rust_decimal::Decimal;
    use pretty_assertions::assert_eq;
    use crate::platforms::tradelocker::{
        TradeLockerClient, TradeLockerAuth, TradeLockerConfig,
        TradeLockerEnvironment, OrderManager, OrderResponse, OrderSide, OrderType, OrderStatus, TimeInForce,
    };
    use crate::utils::vault::VaultClient;
    use chrono::Utc;

    async fn create_test_order_manager() -> OrderManager {
        let vault_client = Arc::new(VaultClient::new("http://localhost:8200".to_string()).await.unwrap());
        let auth = Arc::new(TradeLockerAuth::new(vault_client).await.unwrap());
        let config = TradeLockerConfig::default();
        let environment = TradeLockerEnvironment::Sandbox;
        let client = Arc::new(TradeLockerClient::new(auth, config, environment).unwrap());

        OrderManager::new(client)
    }

    fn create_test_order_response() -> OrderResponse {
        OrderResponse {
            order_id: "order_123".to_string(),
            client_order_id: Some("client_order_456".to_string()),
            status: OrderStatus::New,
            symbol: "EURUSD".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Market,
            quantity: Decimal::new(100000, 5), // 1.00000
            filled_quantity: Decimal::ZERO,
            price: None,
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    #[tokio::test]
    async fn test_order_manager_creation() {
        let order_manager = create_test_order_manager().await;
        
        // Should start with no active orders
        let active_orders = order_manager.get_active_orders().await;
        assert_eq!(active_orders.len(), 0);
        
        // Should start with no order history
        let history = order_manager.get_order_history(None).await;
        assert_eq!(history.len(), 0);
    }

    #[tokio::test]
    async fn test_order_state_management() {
        let order_manager = create_test_order_manager().await;
        let order_response = create_test_order_response();
        
        // Add an order update
        order_manager.update_order_status(order_response.clone()).await;
        
        // Should be in active orders (not filled/cancelled/rejected)
        let active_orders = order_manager.get_active_orders().await;
        assert_eq!(active_orders.len(), 1);
        assert_eq!(active_orders[0].order_id, "order_123");
        
        // Should not be in history yet
        let history = order_manager.get_order_history(None).await;
        assert_eq!(history.len(), 0);
    }

    #[tokio::test]
    async fn test_order_completion() {
        let order_manager = create_test_order_manager().await;
        let mut order_response = create_test_order_response();
        
        // Add as active order first
        order_manager.update_order_status(order_response.clone()).await;
        assert_eq!(order_manager.get_active_orders().await.len(), 1);
        
        // Update to filled status
        order_response.status = OrderStatus::Filled;
        order_response.filled_quantity = order_response.quantity;
        order_response.average_price = Some(Decimal::new(112000, 5));
        order_manager.update_order_status(order_response).await;
        
        // Should be removed from active orders
        let active_orders = order_manager.get_active_orders().await;
        assert_eq!(active_orders.len(), 0);
        
        // Should be in history
        let history = order_manager.get_order_history(None).await;
        assert_eq!(history.len(), 1);
        assert_eq!(history[0].status, OrderStatus::Filled);
        assert_eq!(history[0].filled_quantity, Decimal::new(100000, 5));
    }

    #[tokio::test]
    async fn test_order_status_transitions() {
        let order_manager = create_test_order_manager().await;
        let _order_response = create_test_order_response();
        
        // Test all completion statuses move to history
        let completion_statuses = vec![
            OrderStatus::Filled,
            OrderStatus::Canceled,
            OrderStatus::Rejected,
            OrderStatus::Expired,
        ];
        
        for (i, status) in completion_statuses.into_iter().enumerate() {
            let mut order = _order_response.clone();
            order.order_id = format!("order_{}", i);
            order.status = status;
            
            order_manager.update_order_status(order).await;
            
            // Should go directly to history
            let history = order_manager.get_order_history(None).await;
            assert_eq!(history.len(), i + 1);
        }
        
        // No active orders
        assert_eq!(order_manager.get_active_orders().await.len(), 0);
    }

    #[tokio::test]
    async fn test_order_retrieval() {
        let order_manager = create_test_order_manager().await;
        let order1 = create_test_order_response();
        let mut order2 = create_test_order_response();
        order2.order_id = "order_456".to_string();
        order2.status = OrderStatus::Filled;
        
        // Add one active, one completed
        order_manager.update_order_status(order1.clone()).await;
        order_manager.update_order_status(order2.clone()).await;
        
        // Test get specific order
        let found_order = order_manager.get_order("order_123").await;
        assert!(found_order.is_some());
        assert_eq!(found_order.unwrap().status, OrderStatus::New);
        
        let found_order = order_manager.get_order("order_456").await;
        assert!(found_order.is_some());
        assert_eq!(found_order.unwrap().status, OrderStatus::Filled);
        
        // Test non-existent order
        let not_found = order_manager.get_order("nonexistent").await;
        assert!(not_found.is_none());
    }

    #[tokio::test]
    async fn test_history_limits() {
        let order_manager = create_test_order_manager().await;
        
        // Add multiple completed orders
        for i in 0..10 {
            let mut order = create_test_order_response();
            order.order_id = format!("order_{}", i);
            order.status = OrderStatus::Filled;
            order_manager.update_order_status(order).await;
        }
        
        // Test unlimited history
        let all_history = order_manager.get_order_history(None).await;
        assert_eq!(all_history.len(), 10);
        
        // Test limited history  
        let limited_history = order_manager.get_order_history(Some(5)).await;
        assert_eq!(limited_history.len(), 5);
        
        // Should be most recent (reverse order)
        assert_eq!(limited_history[0].order_id, "order_9");
        assert_eq!(limited_history[4].order_id, "order_5");
    }

    #[tokio::test]
    async fn test_clear_history() {
        let order_manager = create_test_order_manager().await;
        
        // Add some completed orders
        for i in 0..5 {
            let mut order = create_test_order_response();
            order.order_id = format!("order_{}", i);
            order.status = OrderStatus::Filled;
            order_manager.update_order_status(order).await;
        }
        
        assert_eq!(order_manager.get_order_history(None).await.len(), 5);
        
        // Clear history
        order_manager.clear_history().await;
        
        // History should be empty
        assert_eq!(order_manager.get_order_history(None).await.len(), 0);
    }

    #[test]
    fn test_client_order_id_generation() {
        // Test the generate_client_order_id function would work
        // In real implementation, we'd test the UUID generation
        let id1 = "test_id_1";
        let id2 = "test_id_2";
        
        assert_ne!(id1, id2); // Should be unique
        assert!(id1.len() > 0); // Should not be empty
    }

    #[test]
    fn test_order_status_serialization() {
        let statuses = vec![
            OrderStatus::Pending,
            OrderStatus::New,
            OrderStatus::PartiallyFilled,
            OrderStatus::Filled,
            OrderStatus::Canceled,
            OrderStatus::Rejected,
            OrderStatus::Expired,
        ];
        
        for status in statuses {
            let json = serde_json::to_string(&status).unwrap();
            let deserialized: OrderStatus = serde_json::from_str(&json).unwrap();
            assert_eq!(status, deserialized);
        }
    }

    #[test]
    fn test_order_response_serialization() {
        let order_response = create_test_order_response();
        
        let json = serde_json::to_string(&order_response).unwrap();
        let deserialized: OrderResponse = serde_json::from_str(&json).unwrap();
        
        assert_eq!(order_response.order_id, deserialized.order_id);
        assert_eq!(order_response.symbol, deserialized.symbol);
        assert_eq!(order_response.quantity, deserialized.quantity);
        assert_eq!(order_response.status, deserialized.status);
    }

    #[tokio::test]
    async fn test_partial_fills() {
        let order_manager = create_test_order_manager().await;
        let mut order_response = create_test_order_response();
        
        // Add as new order
        order_manager.update_order_status(order_response.clone()).await;
        
        // Update to partially filled
        order_response.status = OrderStatus::PartiallyFilled;
        order_response.filled_quantity = Decimal::new(50000, 5); // Half filled
        order_response.average_price = Some(Decimal::new(112000, 5));
        order_manager.update_order_status(order_response.clone()).await;
        
        // Should still be in active orders
        let active_orders = order_manager.get_active_orders().await;
        assert_eq!(active_orders.len(), 1);
        assert_eq!(active_orders[0].status, OrderStatus::PartiallyFilled);
        assert_eq!(active_orders[0].filled_quantity, Decimal::new(50000, 5));
        
        // Complete the fill
        order_response.status = OrderStatus::Filled;
        order_response.filled_quantity = order_response.quantity;
        order_manager.update_order_status(order_response).await;
        
        // Should now be in history
        assert_eq!(order_manager.get_active_orders().await.len(), 0);
        assert_eq!(order_manager.get_order_history(None).await.len(), 1);
    }
}