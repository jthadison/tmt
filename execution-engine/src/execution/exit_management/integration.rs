use std::sync::Arc;
use anyhow::Result;

use crate::platforms::abstraction::ITradingPlatform;
use crate::platforms::abstraction::interfaces::EventFilter;
use crate::platforms::abstraction::events::PlatformEvent;
use super::{
    ExitManagementSystem, ExitAuditLogger, PlatformAdapterFactory,
    TrailingStopManager, BreakEvenManager, PartialProfitManager, 
    TimeBasedExitManager, NewsEventProtection
};

/// Integration factory for creating a fully configured exit management system
pub struct ExitManagementIntegration;

impl ExitManagementIntegration {
    /// Create a complete exit management system with platform integration
    pub fn create_with_platform(
        platform: Arc<dyn ITradingPlatform + Send + Sync>
    ) -> Result<ExitManagementSystem> {
        // Create platform adapter
        let trading_platform = PlatformAdapterFactory::create_exit_management_adapter(platform);
        
        // Create audit logger
        let exit_logger = Arc::new(ExitAuditLogger::new());
        
        // Create the exit management system
        Ok(ExitManagementSystem::new(trading_platform, exit_logger))
    }

    /// Create exit management system with custom audit database
    pub fn create_with_custom_database(
        platform: Arc<dyn ITradingPlatform + Send + Sync>,
        audit_database: Arc<dyn super::exit_logger::AuditDatabase>,
    ) -> Result<ExitManagementSystem> {
        // Create platform adapter
        let trading_platform = PlatformAdapterFactory::create_exit_management_adapter(platform);
        
        // Create audit logger with custom database
        let exit_logger = Arc::new(ExitAuditLogger::with_database(audit_database));
        
        // Create the exit management system
        Ok(ExitManagementSystem::new(trading_platform, exit_logger))
    }

    /// Create individual components for more granular control
    pub fn create_components(
        platform: Arc<dyn ITradingPlatform + Send + Sync>
    ) -> Result<ExitManagementComponents> {
        // Create platform adapter
        let trading_platform = PlatformAdapterFactory::create_exit_management_adapter(platform);
        
        // Create audit logger
        let exit_logger = Arc::new(ExitAuditLogger::new());
        
        // Create individual managers
        let trailing_stop_manager = Arc::new(TrailingStopManager::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));
        
        let break_even_manager = Arc::new(BreakEvenManager::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));
        
        let partial_profit_manager = Arc::new(PartialProfitManager::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));
        
        let time_exit_manager = Arc::new(TimeBasedExitManager::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));
        
        let news_protection = Arc::new(NewsEventProtection::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));

        Ok(ExitManagementComponents {
            trading_platform,
            exit_logger,
            trailing_stop_manager,
            break_even_manager,
            partial_profit_manager,
            time_exit_manager,
            news_protection,
        })
    }
}

/// Individual components for granular control
pub struct ExitManagementComponents {
    pub trading_platform: Arc<dyn super::TradingPlatform>,
    pub exit_logger: Arc<ExitAuditLogger>,
    pub trailing_stop_manager: Arc<TrailingStopManager>,
    pub break_even_manager: Arc<BreakEvenManager>,
    pub partial_profit_manager: Arc<PartialProfitManager>,
    pub time_exit_manager: Arc<TimeBasedExitManager>,
    pub news_protection: Arc<NewsEventProtection>,
}

impl ExitManagementComponents {
    /// Build a complete exit management system from components
    pub fn build(self) -> ExitManagementSystem {
        ExitManagementSystem::from_components(
            self.trailing_stop_manager,
            self.break_even_manager,
            self.partial_profit_manager,
            self.time_exit_manager,
            self.news_protection,
            self.exit_logger,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::platforms::abstraction::{UnifiedPosition, UnifiedMarketData, UnifiedPositionSide, OrderModification, UnifiedOrderResponse, PlatformError};
    use async_trait::async_trait;
    use rust_decimal::Decimal;
    use chrono::Utc;
    use std::collections::HashMap;

    struct MockIntegrationPlatform;

    #[async_trait]
    impl ITradingPlatform for MockIntegrationPlatform {
        fn platform_type(&self) -> crate::platforms::PlatformType {
            crate::platforms::PlatformType::MetaTrader4
        }

        fn platform_name(&self) -> &str { "MockIntegrationPlatform" }
        fn platform_version(&self) -> &str { "1.0.0" }

        async fn connect(&mut self) -> Result<(), PlatformError> { Ok(()) }
        async fn disconnect(&mut self) -> Result<(), PlatformError> { Ok(()) }
        async fn is_connected(&self) -> bool { true }
        async fn ping(&self) -> Result<u64, PlatformError> { Ok(10) }

        async fn place_order(&self, _order: crate::platforms::abstraction::UnifiedOrder) -> Result<UnifiedOrderResponse, PlatformError> {
            unimplemented!()
        }

        async fn modify_order(&self, _order_id: &str, _modifications: OrderModification) -> Result<UnifiedOrderResponse, PlatformError> {
            unimplemented!()
        }

        async fn cancel_order(&self, _order_id: &str) -> Result<(), PlatformError> { Ok(()) }

        async fn get_order(&self, _order_id: &str) -> Result<UnifiedOrderResponse, PlatformError> {
            unimplemented!()
        }

        async fn get_orders(&self, _filter: Option<crate::platforms::abstraction::OrderFilter>) -> Result<Vec<UnifiedOrderResponse>, PlatformError> {
            Ok(Vec::new())
        }

        async fn get_positions(&self) -> Result<Vec<UnifiedPosition>, PlatformError> {
            Ok(vec![UnifiedPosition {
                position_id: "integration-test-1".to_string(),
                symbol: "EURUSD".to_string(),
                side: UnifiedPositionSide::Long,
                quantity: Decimal::from(1),
                entry_price: Decimal::from_f64_retain(1.1000).unwrap(),
                current_price: Decimal::from_f64_retain(1.1050).unwrap(),
                unrealized_pnl: Decimal::from_f64_retain(50.0).unwrap(),
                realized_pnl: Decimal::ZERO,
                margin_used: Decimal::from(100),
                commission: Decimal::from_f64_retain(2.0).unwrap(),
                stop_loss: Some(Decimal::from_f64_retain(1.0950).unwrap()),
                take_profit: Some(Decimal::from_f64_retain(1.1100).unwrap()),
                opened_at: Utc::now(),
                updated_at: Utc::now(),
                account_id: "test-account".to_string(),
                platform_specific: HashMap::new(),
            }])
        }

        async fn get_position(&self, _symbol: &str) -> Result<Option<UnifiedPosition>, PlatformError> {
            Ok(None)
        }

        async fn close_position(&self, _symbol: &str, _quantity: Option<Decimal>) -> Result<UnifiedOrderResponse, PlatformError> {
            unimplemented!()
        }

        async fn get_account_info(&self) -> Result<crate::platforms::abstraction::UnifiedAccountInfo, PlatformError> {
            unimplemented!()
        }

        async fn get_balance(&self) -> Result<Decimal, PlatformError> { Ok(Decimal::from(10000)) }

        async fn get_margin_info(&self) -> Result<crate::platforms::abstraction::MarginInfo, PlatformError> {
            unimplemented!()
        }

        async fn get_market_data(&self, symbol: &str) -> Result<UnifiedMarketData, PlatformError> {
            Ok(UnifiedMarketData {
                symbol: symbol.to_string(),
                bid: Decimal::from_f64_retain(1.1049).unwrap(),
                ask: Decimal::from_f64_retain(1.1051).unwrap(),
                spread: Decimal::from_f64_retain(0.0002).unwrap(),
                last_price: Some(Decimal::from_f64_retain(1.1050).unwrap()),
                volume: Some(Decimal::from(1000)),
                high: Some(Decimal::from_f64_retain(1.1080).unwrap()),
                low: Some(Decimal::from_f64_retain(1.1020).unwrap()),
                timestamp: Utc::now(),
                session: Some(crate::platforms::abstraction::TradingSession::Regular),
                platform_specific: HashMap::new(),
            })
        }

        async fn subscribe_market_data(&self, _symbols: Vec<String>) -> Result<tokio::sync::mpsc::Receiver<UnifiedMarketData>, PlatformError> {
            unimplemented!()
        }

        async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> Result<(), PlatformError> {
            Ok(())
        }

        fn capabilities(&self) -> crate::platforms::abstraction::PlatformCapabilities {
            unimplemented!()
        }

        async fn subscribe_events(&self) -> Result<tokio::sync::mpsc::Receiver<crate::platforms::abstraction::PlatformEvent>, PlatformError> {
            unimplemented!()
        }

        async fn get_event_history(&self, _filter: EventFilter) -> Result<Vec<PlatformEvent>, PlatformError> {
            Ok(Vec::new())
        }

        async fn health_check(&self) -> Result<crate::platforms::abstraction::HealthStatus, PlatformError> {
            unimplemented!()
        }

        async fn get_diagnostics(&self) -> Result<crate::platforms::abstraction::DiagnosticsInfo, PlatformError> {
            unimplemented!()
        }
    }

    #[tokio::test]
    async fn test_integration_create_with_platform() {
        let mock_platform = Arc::new(MockIntegrationPlatform);
        let exit_management = ExitManagementIntegration::create_with_platform(mock_platform).unwrap();
        
        assert!(exit_management.is_enabled());
    }

    #[tokio::test]
    async fn test_integration_create_components() {
        let mock_platform = Arc::new(MockIntegrationPlatform);
        let components = ExitManagementIntegration::create_components(mock_platform).unwrap();
        
        // Test that all components are created
        let exit_management = components.build();
        assert!(exit_management.is_enabled());
    }

    #[tokio::test]
    async fn test_full_integration_workflow() {
        let mock_platform = Arc::new(MockIntegrationPlatform);
        let mut exit_management = ExitManagementIntegration::create_with_platform(mock_platform).unwrap();
        
        // Test monitoring cycle
        exit_management.monitor_once().await.unwrap();
        
        // Test individual manager access
        let trailing_stats = exit_management.get_trailing_stop_stats().await.unwrap();
        assert_eq!(trailing_stats.active_trails, 0);
    }
}