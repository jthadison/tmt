use lazy_static::lazy_static;
use prometheus::{
    register_histogram, register_int_counter_vec,
    Histogram, IntCounterVec,
};

lazy_static! {
    pub static ref TRADELOCKER_REQUEST_DURATION: Histogram = register_histogram!(
        "tradelocker_request_duration_ms",
        "Duration of TradeLocker API requests in milliseconds"
    ).unwrap();

    pub static ref TRADELOCKER_REQUEST_COUNT: IntCounterVec = register_int_counter_vec!(
        "tradelocker_request_total",
        "Total number of TradeLocker API requests",
        &["status"]
    ).unwrap();
}