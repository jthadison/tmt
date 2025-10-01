/**
 * Circuit Breaker Types
 * Type definitions for circuit breaker functionality
 */

export interface ThresholdStatus {
  current: number;
  threshold: number;
  limit: number;
}

export interface CircuitBreakerStatus {
  daily_loss: ThresholdStatus;
  account_drawdown: ThresholdStatus;
  consecutive_losses: ThresholdStatus;
  last_triggered: {
    type: string;
    timestamp: string;
  } | null;
  state: 'closed' | 'open' | 'half_open';
}

export interface ResetBreakersResponse {
  success: boolean;
  message: string;
  timestamp: string;
}
