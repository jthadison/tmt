/**
 * Analytics Configuration Constants
 *
 * Centralized configuration for analytics calculations including
 * overfitting thresholds, risk levels, and default parameters.
 */

export const ANALYTICS_CONSTANTS = {
  // Overfitting Analysis
  OVERFITTING: {
    // Risk level thresholds (percentage degradation)
    LOW_RISK_THRESHOLD: 15,
    MODERATE_RISK_THRESHOLD: 30,

    // Overfitting score normalization factor
    DEGRADATION_NORMALIZATION: 30,

    // Divergence detection threshold for charts
    DIVERGENCE_THRESHOLD: 0.2, // 20%
  },

  // Stability Analysis
  STABILITY: {
    // Stability score thresholds
    STABLE_THRESHOLD: 70,
    MODERATE_THRESHOLD: 30,

    // Rolling window size (days)
    WINDOW_SIZE_DAYS: 7,

    // Minimum data points required
    MIN_DATA_POINTS: 7,
  },

  // Performance Calculations
  PERFORMANCE: {
    // Default starting capital for percentage calculations
    STARTING_CAPITAL: 10000,

    // Annualization factor for Sharpe ratio
    TRADING_DAYS_PER_YEAR: 252,
  },

  // Comparison Variance Thresholds
  VARIANCE: {
    GOOD: 15,      // <15% variance is good
    WARNING: 30,   // 15-30% variance is warning
    // >30% is poor (implicit)
  },

  // API Configuration
  API: {
    // Cache duration in seconds
    BACKTEST_CACHE_DURATION: 300,      // 5 minutes
    FORWARD_TEST_CACHE_DURATION: 60,   // 1 minute
    OVERFITTING_CACHE_DURATION: 300,   // 5 minutes
  },
} as const

// Export individual constants for convenience
export const {
  OVERFITTING,
  STABILITY,
  PERFORMANCE,
  VARIANCE,
  API,
} = ANALYTICS_CONSTANTS
