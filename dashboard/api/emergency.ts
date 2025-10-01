/**
 * Emergency Stop API Client
 * Handles communication with orchestrator emergency endpoints
 */

import type {
  EmergencyStopRequest,
  EmergencyStopResponse,
  SystemStatus,
  AuditLogEntry,
} from '@/types/emergency';

const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8089';

/**
 * Emergency stop trading
 */
export async function emergencyStopTrading(
  request: EmergencyStopRequest
): Promise<EmergencyStopResponse> {
  const response = await fetch(`${ORCHESTRATOR_URL}/api/trading/disable`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      close_positions: request.closePositions,
      reason: request.reason || 'User emergency stop',
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Emergency stop failed: ${error.detail || response.statusText}`);
  }

  const data = await response.json();
  return {
    success: data.success,
    message: data.message,
    positions_closed: data.positions_closed,
    timestamp: data.timestamp,
  };
}

/**
 * Resume trading after emergency stop
 */
export async function resumeTrading(): Promise<EmergencyStopResponse> {
  const response = await fetch(`${ORCHESTRATOR_URL}/api/trading/enable`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Resume trading failed: ${error.detail || response.statusText}`);
  }

  const data = await response.json();
  return {
    success: data.success,
    message: data.message,
    positions_closed: 0,
    timestamp: data.timestamp,
  };
}

/**
 * Get current system status
 */
export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${ORCHESTRATOR_URL}/api/system/status`);

  if (!response.ok) {
    throw new Error('Failed to fetch system status');
  }

  const data = await response.json();
  return {
    trading_enabled: data.trading_enabled,
    active_positions: data.active_positions,
    daily_pnl: data.daily_pnl,
    open_trades: data.open_trades,
    timestamp: data.timestamp,
  };
}

/**
 * Log emergency action to audit trail
 */
export async function logEmergencyAction(log: Partial<AuditLogEntry>): Promise<void> {
  try {
    const response = await fetch(`${ORCHESTRATOR_URL}/api/audit/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...log,
        timestamp: new Date().toISOString(),
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
      }),
    });

    if (!response.ok) {
      console.error('Failed to log audit action:', await response.text());
    }
  } catch (error) {
    // Fallback: store locally if API unavailable
    console.error('Failed to log audit action:', error);
    const logs = JSON.parse(localStorage.getItem('audit_logs') || '[]');
    logs.push({
      ...log,
      timestamp: new Date().toISOString(),
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
    });
    localStorage.setItem('audit_logs', JSON.stringify(logs));
  }
}
