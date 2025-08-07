/*!
 * Execution Engine Library
 *
 * High-performance trading execution engine for the Adaptive Trading System.
 * Provides sub-100ms signal-to-execution latency for automated trading.
 */

pub mod api;

pub use api::{HealthChecker, HealthResponse, HealthStatus};

/// Library version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Service name
pub const SERVICE_NAME: &str = "execution-engine";

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version_defined() {
        assert!(!VERSION.is_empty());
    }

    #[test]
    fn test_service_name_defined() {
        assert_eq!(SERVICE_NAME, "execution-engine");
    }
}