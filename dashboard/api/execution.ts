/**
 * Execution Engine API Client
 * Handles communication with execution engine endpoints
 */

import type {
  Position,
  ClosePositionsRequest,
  ClosePositionsResponse,
  RollbackRequest,
  RollbackResponse,
} from '@/types/execution';

const EXECUTION_ENGINE_URL = process.env.NEXT_PUBLIC_EXECUTION_ENGINE_URL || 'http://localhost:8082';
const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8089';

/**
 * Get all open positions
 */
export async function getOpenPositions(): Promise<Position[]> {
  const response = await fetch(`${EXECUTION_ENGINE_URL}/api/positions`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to fetch positions: ${error.detail || response.statusText}`);
  }

  const data = await response.json();
  return data.positions || [];
}

/**
 * Close all open positions immediately
 */
export async function closeAllPositions(request?: ClosePositionsRequest): Promise<ClosePositionsResponse> {
  const response = await fetch(`${EXECUTION_ENGINE_URL}/api/positions/close-all`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reason: request?.reason || 'Emergency close via dashboard',
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to close positions: ${error.detail || response.statusText}`);
  }

  return response.json();
}

/**
 * Execute emergency rollback (session → universal or vice versa)
 */
export async function executeRollback(request: RollbackRequest): Promise<RollbackResponse> {
  const response = await fetch(`${ORCHESTRATOR_URL}/api/rollback/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_mode: request.target_mode,
      reason: request.reason || 'Emergency rollback via dashboard',
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to execute rollback: ${error.detail || response.statusText}`);
  }

  return response.json();
}
