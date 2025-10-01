/**
 * Circuit Breaker API Client
 * Handles communication with circuit breaker agent endpoints
 */

import type {
  CircuitBreakerStatus,
  ResetBreakersResponse,
} from '@/types/circuitBreaker';

const CIRCUIT_BREAKER_URL = process.env.NEXT_PUBLIC_CIRCUIT_BREAKER_URL || 'http://localhost:8084';

/**
 * Get current circuit breaker status
 */
export async function getCircuitBreakerStatus(): Promise<CircuitBreakerStatus> {
  const response = await fetch(`${CIRCUIT_BREAKER_URL}/api/circuit-breakers/status`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to fetch circuit breaker status: ${error.detail || response.statusText}`);
  }

  return response.json();
}

/**
 * Reset all circuit breakers
 */
export async function resetCircuitBreakers(): Promise<ResetBreakersResponse> {
  const response = await fetch(`${CIRCUIT_BREAKER_URL}/api/circuit-breakers/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to reset circuit breakers: ${error.detail || response.statusText}`);
  }

  return response.json();
}
