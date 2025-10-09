/**
 * Validation Dashboard Types - Story 11.8
 *
 * TypeScript type definitions for validation metrics, alerts, and reports
 */

export enum ValidationStatus {
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  WARNING = 'WARNING',
  IN_PROGRESS = 'IN_PROGRESS',
  FAILED = 'FAILED',
}

export enum AlertLevel {
  INFO = 'INFO',
  WARNING = 'WARNING',
  CRITICAL = 'CRITICAL',
}

export interface ValidationMetrics {
  overfitting_score: number;
  live_sharpe: number;
  backtest_sharpe: number;
  sharpe_ratio: number; // live/backtest ratio
  parameter_drift_7d: number;
  parameter_drift_30d: number;
  last_updated: string;
}

export interface CurrentMetricsResponse {
  data: ValidationMetrics;
  error: string | null;
  correlation_id: string;
}

export interface ParameterVersion {
  version: string;
  date: string;
  author: string;
  reason: string;
  metrics: {
    backtest_sharpe: number;
    out_of_sample_sharpe: number;
    overfitting_score: number;
    max_drawdown?: number;
    win_rate?: number;
    profit_factor?: number;
  };
}

export interface ParameterHistoryResponse {
  data: ParameterVersion[];
  error: string | null;
  correlation_id: string;
}

export interface OverfittingScorePoint {
  timestamp: string;
  score: number;
  threshold_warning: number;
  threshold_critical: number;
}

export interface OverfittingHistoryResponse {
  data: OverfittingScorePoint[];
  error: string | null;
  correlation_id: string;
}

export interface PerformanceComparison {
  metric: string;
  live_value: number;
  backtest_value: number;
  deviation_pct: number;
}

export interface PerformanceComparisonResponse {
  data: PerformanceComparison[];
  error: string | null;
  correlation_id: string;
}

export interface SharpeDataPoint {
  date: string;
  sharpe: number;
  target?: number;
}

export interface SharpeRatioTrendResponse {
  data: SharpeDataPoint[];
  error: string | null;
  correlation_id: string;
}

export interface ValidationAlert {
  id: string;
  alert_type: 'OVERFITTING' | 'PERFORMANCE_DEGRADATION' | 'PARAMETER_DRIFT' | 'VALIDATION_FAILURE';
  severity: AlertLevel;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  resolved: boolean;
  resolution_note?: string;
  metadata?: Record<string, any>;
}

export interface AlertsResponse {
  data: ValidationAlert[];
  error: string | null;
  correlation_id: string;
}

export interface WalkForwardWindow {
  window_id: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  in_sample_sharpe: number;
  out_of_sample_sharpe: number;
  max_drawdown: number;
  win_rate: number;
  num_trades: number;
}

export interface SessionPerformance {
  session: string;
  sharpe: number;
  win_rate: number;
  profit_factor: number;
  num_trades: number;
  avg_win: number;
  avg_loss: number;
}

export interface ParameterStability {
  parameter: string;
  mean: number;
  std_dev: number;
  coefficient_of_variation: number;
  is_stable: boolean;
}

export interface WalkForwardReport {
  job_id: string;
  config_file: string;
  timestamp: string;
  status: ValidationStatus;

  // Windows data
  windows: WalkForwardWindow[];

  // Session performance
  session_performance: SessionPerformance[];

  // Parameter stability
  parameter_stability: ParameterStability[];

  // Summary metrics
  avg_in_sample_sharpe: number;
  avg_out_of_sample_sharpe: number;
  overfitting_score: number;
  degradation_factor: number;

  // Equity curve data
  equity_curve_in_sample: { date: string; equity: number }[];
  equity_curve_out_of_sample: { date: string; equity: number }[];

  // Trade distribution
  trade_distribution: { hour: number; count: number }[];
}

export interface WalkForwardReportResponse {
  data: WalkForwardReport;
  error: string | null;
  correlation_id: string;
}

export interface ValidationJob {
  job_id: string;
  status: ValidationStatus;
  progress_pct: number;
  current_step: string;
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface ValidationJobsResponse {
  data: ValidationJob[];
  error: string | null;
  correlation_id: string;
}

// PDF Export types
export interface PDFExportOptions {
  report_id: string;
  include_charts: boolean;
  include_detailed_windows: boolean;
  format: 'portrait' | 'landscape';
}

export interface PDFExportResponse {
  pdf_url: string;
  file_name: string;
  size_bytes: number;
}
