/**
 * Rollback API Client
 * Provides functions to interact with the emergency rollback system
 */

export interface RollbackEvent {
  event_id: string;
  timestamp: string;
  trigger_type: string;
  trigger_reason: string;
  previous_mode: string;
  new_mode: string;
  status: string;
  success: boolean;
  user?: string;
}

export interface RollbackCondition {
  trigger_type: string;
  enabled: boolean;
  threshold_value: number;
  threshold_unit: string;
  consecutive_periods: number;
  description: string;
  priority: number;
  current_value: number;
}

const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8089';

export async function executeRollback(reason: string): Promise<{
  success: boolean;
  event_id: string;
  previous_mode: string;
  new_mode: string;
  status: string;
  timestamp: string;
}> {
  const response = await fetch(`${ORCHESTRATOR_URL}/api/rollback/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason, notify_contacts: true })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Rollback execution failed' }));
    throw new Error(error.detail || 'Rollback execution failed');
  }

  return response.json();
}

export async function getRollbackHistory(limit = 20): Promise<RollbackEvent[]> {
  const response = await fetch(`${ORCHESTRATOR_URL}/api/rollback/history?limit=${limit}`);

  if (!response.ok) {
    throw new Error('Failed to fetch rollback history');
  }

  const data = await response.json();
  return data.events || [];
}

export async function getRollbackConditions(): Promise<RollbackCondition[]> {
  const response = await fetch(`${ORCHESTRATOR_URL}/api/rollback/conditions`);

  if (!response.ok) {
    throw new Error('Failed to fetch rollback conditions');
  }

  const data = await response.json();
  return data.conditions || [];
}

export async function updateRollbackCondition(
  triggerType: string,
  enabled: boolean
): Promise<void> {
  const response = await fetch(
    `${ORCHESTRATOR_URL}/api/rollback/conditions/${triggerType}?enabled=${enabled}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' }
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update rollback condition' }));
    throw new Error(error.detail || 'Failed to update rollback condition');
  }
}

export async function getCurrentTradingMode(): Promise<string> {
  try {
    const response = await fetch(`${ORCHESTRATOR_URL}/emergency-rollback/status`);
    if (!response.ok) return 'unknown';

    const data = await response.json();
    return data.current_mode || 'Universal Cycle 4';
  } catch (error) {
    console.error('Error fetching trading mode:', error);
    return 'unknown';
  }
}
