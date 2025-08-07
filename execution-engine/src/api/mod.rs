/*!
 * API Module for Execution Engine
 *
 * Contains all HTTP API endpoints including health checks,
 * order management, and system monitoring.
 */

pub mod health;

pub use health::{HealthChecker, HealthResponse, HealthStatus};