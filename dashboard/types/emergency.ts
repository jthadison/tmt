/**
 * Emergency Stop Types
 * Type definitions for emergency stop functionality
 */

export interface EmergencyStopRequest {
  closePositions: boolean;
  reason?: string;
}

export interface EmergencyStopResponse {
  success: boolean;
  message: string;
  positions_closed: number;
  timestamp: string;
}

export interface SystemStatus {
  trading_enabled: boolean;
  active_positions: number;
  daily_pnl: number;
  open_trades: OpenTrade[];
  timestamp: string;
}

export interface OpenTrade {
  instrument: string;
  direction: 'long' | 'short';
  pnl: number;
}

export interface AuditLogEntry {
  timestamp: string;
  action: 'emergency_stop' | 'resume_trading';
  user: string | 'anonymous';
  closePositions?: boolean;
  positionsClosed?: number;
  activePositionsCount?: number;
  dailyPnl?: number;
  success: boolean;
  error?: string;
  userAgent?: string;
  ipAddress?: string;
}
