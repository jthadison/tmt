/**
 * Circuit Breaker Hook
 * Manages circuit breaker status, real-time updates, and reset functionality
 */

import { useState, useEffect, useCallback } from 'react';
import { getCircuitBreakerStatus, resetCircuitBreakers } from '@/api/circuitBreaker';
import { logEmergencyAction } from '@/api/emergency';
import type { CircuitBreakerStatus } from '@/types/circuitBreaker';

const POLLING_INTERVAL = 5000; // 5 seconds fallback polling

export function useCircuitBreaker() {
  const [status, setStatus] = useState<CircuitBreakerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch circuit breaker status
  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCircuitBreakerStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Failed to fetch circuit breaker status:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Reset circuit breakers
  const reset = useCallback(async () => {
    try {
      const result = await resetCircuitBreakers();

      // Log audit trail
      await logEmergencyAction({
        action: 'reset_breakers',
        user: 'anonymous',
        success: true,
        details: { message: result.message },
      });

      // Refresh status after reset
      await fetchStatus();

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';

      // Log failed attempt
      await logEmergencyAction({
        action: 'reset_breakers',
        user: 'anonymous',
        success: false,
        error: errorMessage,
      });

      throw err;
    }
  }, [fetchStatus]);

  // Initial fetch and polling
  useEffect(() => {
    fetchStatus();

    // Set up polling as fallback (WebSocket integration would replace this)
    const interval = setInterval(fetchStatus, POLLING_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchStatus]);

  return {
    status,
    loading,
    error,
    refresh: fetchStatus,
    reset,
  };
}
