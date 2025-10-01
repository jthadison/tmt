/**
 * Execution Engine Types
 * Type definitions for execution engine functionality
 */

export interface Position {
  id: string;
  instrument: string;
  direction: 'long' | 'short';
  size: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  timestamp: string;
}

export interface ClosePositionsRequest {
  reason?: string;
}

export interface ClosePositionsResponse {
  success: boolean;
  positions_closed: number;
  errors: string[];
  timestamp: string;
}

export interface RollbackRequest {
  target_mode: 'session' | 'universal';
  reason?: string;
}

export interface RollbackResponse {
  success: boolean;
  message: string;
  previous_mode: string;
  new_mode: string;
  timestamp: string;
}
