/**
 * useValidationAlerts Hook - Story 11.8, Task 9
 *
 * Custom hook for fetching validation alerts with filtering
 */

import { useState, useEffect, useCallback } from 'react';
import type { ValidationAlert, AlertLevel } from '@/types/validation';

interface UseValidationAlertsOptions {
  severity?: AlertLevel;
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseValidationAlertsReturn {
  alerts: ValidationAlert[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<boolean>;
  dismissAlert: (alertId: string) => Promise<boolean>;
}

export function useValidationAlerts(
  options: UseValidationAlertsOptions = {}
): UseValidationAlertsReturn {
  const { severity, limit = 50, autoRefresh = true, refreshInterval = 15000 } = options; // Default 15s

  const [alerts, setAlerts] = useState<ValidationAlert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (severity) params.append('severity', severity);
      params.append('limit', limit.toString());

      const response = await fetch(`/api/validation/alerts?${params.toString()}`, {
        cache: 'no-store',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setAlerts(data.data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch validation alerts';
      setError(errorMessage);
      console.error('[useValidationAlerts] Error:', err);
    } finally {
      setLoading(false);
    }
  }, [severity, limit]);

  const acknowledgeAlert = useCallback(async (alertId: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/validation/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to acknowledge alert: ${response.statusText}`);
      }

      // Refresh alerts after acknowledgment
      await fetchAlerts();
      return true;
    } catch (err) {
      console.error(`[useValidationAlerts] Error acknowledging alert ${alertId}:`, err);
      return false;
    }
  }, [fetchAlerts]);

  const dismissAlert = useCallback(async (alertId: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/validation/alerts/${alertId}/dismiss`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to dismiss alert: ${response.statusText}`);
      }

      // Refresh alerts after dismissal
      await fetchAlerts();
      return true;
    } catch (err) {
      console.error(`[useValidationAlerts] Error dismissing alert ${alertId}:`, err);
      return false;
    }
  }, [fetchAlerts]);

  // Initial fetch
  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchAlerts();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchAlerts]);

  return {
    alerts,
    loading,
    error,
    refetch: fetchAlerts,
    acknowledgeAlert,
    dismissAlert,
  };
}
