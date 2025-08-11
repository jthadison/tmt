use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use super::capabilities::PlatformOperation;
use super::errors::PlatformError;

/// Performance monitoring and metrics collection
pub struct PerformanceMonitor {
    metrics: Arc<Mutex<PerformanceMetrics>>,
    operation_timers: Arc<Mutex<HashMap<String, Vec<Duration>>>>,
    error_tracker: Arc<Mutex<ErrorTracker>>,
    throughput_tracker: Arc<Mutex<ThroughputTracker>>,
    sla_monitor: SLAMonitor,
}

impl PerformanceMonitor {
    pub fn new() -> Self {
        Self {
            metrics: Arc::new(Mutex::new(PerformanceMetrics::default())),
            operation_timers: Arc::new(Mutex::new(HashMap::new())),
            error_tracker: Arc::new(Mutex::new(ErrorTracker::new())),
            throughput_tracker: Arc::new(Mutex::new(ThroughputTracker::new())),
            sla_monitor: SLAMonitor::new(),
        }
    }

    /// Start timing an operation
    pub fn start_operation(&self, operation: &str) -> OperationTimer {
        OperationTimer::new(operation.to_string(), self.clone())
    }

    /// Record operation completion with duration
    pub fn record_operation(&self, operation: &str, duration: Duration, success: bool) {
        // Record timing
        {
            let mut timers = self.operation_timers.lock().unwrap();
            timers.entry(operation.to_string())
                .or_insert_with(Vec::new)
                .push(duration);
        }

        // Update metrics
        {
            let mut metrics = self.metrics.lock().unwrap();
            metrics.total_operations += 1;
            
            let operation_metrics = metrics.operations.entry(operation.to_string())
                .or_insert_with(OperationMetrics::default);
            
            operation_metrics.count += 1;
            operation_metrics.total_duration += duration;
            operation_metrics.min_duration = operation_metrics.min_duration
                .map(|min| min.min(duration))
                .or(Some(duration));
            operation_metrics.max_duration = operation_metrics.max_duration
                .map(|max| max.max(duration))
                .or(Some(duration));
            
            if !success {
                operation_metrics.error_count += 1;
                metrics.total_errors += 1;
            }
        }

        // Track throughput
        {
            let mut throughput = self.throughput_tracker.lock().unwrap();
            throughput.record_operation();
        }

        // Track errors
        if !success {
            let mut error_tracker = self.error_tracker.lock().unwrap();
            error_tracker.record_error(operation);
        }

        // Check SLA violations
        if let Some(sla_duration) = self.sla_monitor.get_sla(operation) {
            if duration > sla_duration {
                self.record_sla_violation(operation, duration, sla_duration);
            }
        }
    }

    /// Record an error
    pub fn record_error(&self, operation: &str, error: &PlatformError) {
        let mut error_tracker = self.error_tracker.lock().unwrap();
        error_tracker.record_platform_error(operation, error);

        let mut metrics = self.metrics.lock().unwrap();
        metrics.total_errors += 1;
        
        if let Some(operation_metrics) = metrics.operations.get_mut(operation) {
            operation_metrics.error_count += 1;
        }
    }

    /// Get current performance metrics
    pub fn get_metrics(&self) -> PerformanceMetrics {
        let metrics = self.metrics.lock().unwrap();
        metrics.clone()
    }

    /// Get operation statistics
    pub fn get_operation_stats(&self, operation: &str) -> Option<OperationStats> {
        let timers = self.operation_timers.lock().unwrap();
        let durations = timers.get(operation)?;
        
        if durations.is_empty() {
            return None;
        }

        let mut sorted_durations = durations.clone();
        sorted_durations.sort();

        let count = sorted_durations.len();
        let sum: Duration = sorted_durations.iter().sum();
        let avg = sum / count as u32;
        
        let p50 = sorted_durations[count * 50 / 100];
        let p95 = sorted_durations[count * 95 / 100];
        let p99 = sorted_durations[count * 99 / 100];

        Some(OperationStats {
            operation: operation.to_string(),
            count: count as u64,
            min: sorted_durations.first().copied().unwrap(),
            max: sorted_durations.last().copied().unwrap(),
            avg,
            p50,
            p95,
            p99,
            total: sum,
        })
    }

    /// Get current throughput
    pub fn get_throughput(&self) -> ThroughputMetrics {
        let throughput = self.throughput_tracker.lock().unwrap();
        throughput.get_metrics()
    }

    /// Get error metrics
    pub fn get_error_metrics(&self) -> ErrorMetrics {
        let error_tracker = self.error_tracker.lock().unwrap();
        error_tracker.get_metrics()
    }

    /// Reset all metrics
    pub fn reset_metrics(&self) {
        let mut metrics = self.metrics.lock().unwrap();
        *metrics = PerformanceMetrics::default();
        
        let mut timers = self.operation_timers.lock().unwrap();
        timers.clear();
        
        let mut error_tracker = self.error_tracker.lock().unwrap();
        error_tracker.reset();
        
        let mut throughput = self.throughput_tracker.lock().unwrap();
        throughput.reset();
    }

    /// Check if platform is meeting SLA requirements
    pub fn check_sla_compliance(&self) -> SLAComplianceReport {
        let metrics = self.get_metrics();
        let mut violations = Vec::new();
        
        for (operation, operation_metrics) in &metrics.operations {
            if let Some(sla_duration) = self.sla_monitor.get_sla(operation) {
                let avg_duration = operation_metrics.total_duration / operation_metrics.count as u32;
                if avg_duration > sla_duration {
                    violations.push(SLAViolation {
                        operation: operation.clone(),
                        expected: sla_duration,
                        actual: avg_duration,
                        violation_percentage: (avg_duration.as_millis() as f64 / sla_duration.as_millis() as f64 - 1.0) * 100.0,
                    });
                }
            }
        }

        SLAComplianceReport {
            is_compliant: violations.is_empty(),
            violations,
            overall_error_rate: metrics.error_rate(),
            timestamp: chrono::Utc::now(),
        }
    }

    fn record_sla_violation(&self, operation: &str, actual: Duration, expected: Duration) {
        // Could emit events or log SLA violations here
        eprintln!("SLA violation for {}: expected {:?}, got {:?}", operation, expected, actual);
    }
}

impl Default for PerformanceMonitor {
    fn default() -> Self {
        Self::new()
    }
}

impl Clone for PerformanceMonitor {
    fn clone(&self) -> Self {
        Self {
            metrics: Arc::clone(&self.metrics),
            operation_timers: Arc::clone(&self.operation_timers),
            error_tracker: Arc::clone(&self.error_tracker),
            throughput_tracker: Arc::clone(&self.throughput_tracker),
            sla_monitor: self.sla_monitor.clone(),
        }
    }
}

/// Timer for measuring operation duration
pub struct OperationTimer {
    operation: String,
    start_time: Instant,
    monitor: PerformanceMonitor,
}

impl OperationTimer {
    fn new(operation: String, monitor: PerformanceMonitor) -> Self {
        Self {
            operation,
            start_time: Instant::now(),
            monitor,
        }
    }

    /// Complete the operation successfully
    pub fn success(self) {
        let duration = self.start_time.elapsed();
        self.monitor.record_operation(&self.operation, duration, true);
    }

    /// Complete the operation with an error
    pub fn error(self, error: &PlatformError) {
        let duration = self.start_time.elapsed();
        self.monitor.record_operation(&self.operation, duration, false);
        self.monitor.record_error(&self.operation, error);
    }

    /// Get elapsed time without completing the timer
    pub fn elapsed(&self) -> Duration {
        self.start_time.elapsed()
    }
}

/// Overall performance metrics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    pub total_operations: u64,
    pub total_errors: u64,
    pub operations: HashMap<String, OperationMetrics>,
    pub start_time: Option<chrono::DateTime<chrono::Utc>>,
}

impl PerformanceMetrics {
    pub fn error_rate(&self) -> f64 {
        if self.total_operations == 0 {
            0.0
        } else {
            self.total_errors as f64 / self.total_operations as f64
        }
    }
}

/// Metrics for a specific operation type
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct OperationMetrics {
    pub count: u64,
    pub error_count: u64,
    pub total_duration: Duration,
    pub min_duration: Option<Duration>,
    pub max_duration: Option<Duration>,
}

impl OperationMetrics {
    pub fn avg_duration(&self) -> Duration {
        if self.count == 0 {
            Duration::default()
        } else {
            self.total_duration / self.count as u32
        }
    }

    pub fn error_rate(&self) -> f64 {
        if self.count == 0 {
            0.0
        } else {
            self.error_count as f64 / self.count as f64
        }
    }
}

/// Detailed operation statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationStats {
    pub operation: String,
    pub count: u64,
    pub min: Duration,
    pub max: Duration,
    pub avg: Duration,
    pub p50: Duration,
    pub p95: Duration,
    pub p99: Duration,
    pub total: Duration,
}

/// Error tracking
struct ErrorTracker {
    error_counts: HashMap<String, u64>,
    error_types: HashMap<String, u64>,
    recent_errors: Vec<(String, PlatformError, chrono::DateTime<chrono::Utc>)>,
    max_recent_errors: usize,
}

impl ErrorTracker {
    fn new() -> Self {
        Self {
            error_counts: HashMap::new(),
            error_types: HashMap::new(),
            recent_errors: Vec::new(),
            max_recent_errors: 100,
        }
    }

    fn record_error(&mut self, operation: &str) {
        *self.error_counts.entry(operation.to_string()).or_insert(0) += 1;
    }

    fn record_platform_error(&mut self, operation: &str, error: &PlatformError) {
        self.record_error(operation);
        
        let error_type = format!("{:?}", std::mem::discriminant(error));
        *self.error_types.entry(error_type).or_insert(0) += 1;
        
        self.recent_errors.push((operation.to_string(), error.clone(), chrono::Utc::now()));
        
        if self.recent_errors.len() > self.max_recent_errors {
            self.recent_errors.remove(0);
        }
    }

    fn get_metrics(&self) -> ErrorMetrics {
        ErrorMetrics {
            total_errors: self.error_counts.values().sum(),
            errors_by_operation: self.error_counts.clone(),
            errors_by_type: self.error_types.clone(),
            recent_error_count: self.recent_errors.len() as u64,
        }
    }

    fn reset(&mut self) {
        self.error_counts.clear();
        self.error_types.clear();
        self.recent_errors.clear();
    }
}

/// Error metrics summary
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorMetrics {
    pub total_errors: u64,
    pub errors_by_operation: HashMap<String, u64>,
    pub errors_by_type: HashMap<String, u64>,
    pub recent_error_count: u64,
}

/// Throughput tracking
struct ThroughputTracker {
    operation_timestamps: Vec<Instant>,
    window_size: Duration,
}

impl ThroughputTracker {
    fn new() -> Self {
        Self {
            operation_timestamps: Vec::new(),
            window_size: Duration::from_secs(60), // 1-minute window
        }
    }

    fn record_operation(&mut self) {
        let now = Instant::now();
        self.operation_timestamps.push(now);
        
        // Clean up old timestamps
        let cutoff = now - self.window_size;
        self.operation_timestamps.retain(|&timestamp| timestamp > cutoff);
    }

    fn get_metrics(&self) -> ThroughputMetrics {
        let operations_per_minute = self.operation_timestamps.len() as f64;
        let operations_per_second = operations_per_minute / 60.0;
        
        ThroughputMetrics {
            operations_per_second,
            operations_per_minute,
            window_size_seconds: self.window_size.as_secs(),
        }
    }

    fn reset(&mut self) {
        self.operation_timestamps.clear();
    }
}

/// Throughput metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThroughputMetrics {
    pub operations_per_second: f64,
    pub operations_per_minute: f64,
    pub window_size_seconds: u64,
}

/// SLA monitoring
#[derive(Debug, Clone)]
pub struct SLAMonitor {
    sla_limits: HashMap<String, Duration>,
}

impl SLAMonitor {
    pub fn new() -> Self {
        let mut sla_limits = HashMap::new();
        
        // Default SLA limits (can be overridden)
        sla_limits.insert("place_order".to_string(), Duration::from_millis(100));
        sla_limits.insert("modify_order".to_string(), Duration::from_millis(50));
        sla_limits.insert("cancel_order".to_string(), Duration::from_millis(30));
        sla_limits.insert("get_market_data".to_string(), Duration::from_millis(20));
        sla_limits.insert("get_account_info".to_string(), Duration::from_millis(200));
        sla_limits.insert("get_positions".to_string(), Duration::from_millis(100));
        
        Self { sla_limits }
    }

    pub fn set_sla(&mut self, operation: &str, limit: Duration) {
        self.sla_limits.insert(operation.to_string(), limit);
    }

    pub fn get_sla(&self, operation: &str) -> Option<Duration> {
        self.sla_limits.get(operation).copied()
    }
}

/// SLA violation record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SLAViolation {
    pub operation: String,
    pub expected: Duration,
    pub actual: Duration,
    pub violation_percentage: f64,
}

/// SLA compliance report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SLAComplianceReport {
    pub is_compliant: bool,
    pub violations: Vec<SLAViolation>,
    pub overall_error_rate: f64,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// Performance benchmark utilities
pub struct PerformanceBenchmark;

impl PerformanceBenchmark {
    /// Run a performance benchmark for an operation
    pub async fn benchmark_operation<T, F, Fut>(
        operation_name: &str,
        operation: F,
        iterations: u32,
        monitor: &PerformanceMonitor,
    ) -> BenchmarkResult
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = Result<T, PlatformError>>,
    {
        let mut successful_runs = 0;
        let mut failed_runs = 0;
        let mut total_duration = Duration::default();
        let start_time = Instant::now();

        for _ in 0..iterations {
            let timer = monitor.start_operation(operation_name);
            let operation_start = Instant::now();
            
            match operation().await {
                Ok(_) => {
                    successful_runs += 1;
                    timer.success();
                }
                Err(e) => {
                    failed_runs += 1;
                    timer.error(&e);
                }
            }
            
            total_duration += operation_start.elapsed();
        }

        let benchmark_duration = start_time.elapsed();
        let avg_operation_time = total_duration / iterations;

        BenchmarkResult {
            operation: operation_name.to_string(),
            iterations,
            successful_runs,
            failed_runs,
            avg_operation_time,
            total_benchmark_time: benchmark_duration,
            operations_per_second: iterations as f64 / benchmark_duration.as_secs_f64(),
            success_rate: successful_runs as f64 / iterations as f64,
        }
    }
}

/// Benchmark results
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkResult {
    pub operation: String,
    pub iterations: u32,
    pub successful_runs: u32,
    pub failed_runs: u32,
    pub avg_operation_time: Duration,
    pub total_benchmark_time: Duration,
    pub operations_per_second: f64,
    pub success_rate: f64,
}