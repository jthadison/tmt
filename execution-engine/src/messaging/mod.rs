// Messaging integration for event streaming
#[cfg(feature = "kafka")]
pub mod kafka;

// Stub for when Kafka is not available
#[cfg(not(feature = "kafka"))]
pub mod stub {
    use tracing::warn;
    
    pub struct MessageBus;
    
    impl MessageBus {
        pub fn new() -> Self {
            warn!("Using stub message bus - Kafka not available");
            Self
        }
    }
}