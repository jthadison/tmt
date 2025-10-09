/**
 * useValidationMetrics Hook - Story 11.8, Task 9
 *
 * Custom hook for fetching current validation metrics with auto-refresh
 */

import { useState, useEffect, useCallback } from 'react';
import type { ValidationMetrics } from '@/types/validation';

interface UseValidationMetricsOptions {
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
}

interface UseValidationMetricsReturn {
  metrics: ValidationMetrics | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  lastUpdated: Date | null;
}

export function useValidationMetrics(
  options: UseValidationMetricsOptions = {}
): UseValidationMetricsReturn {
  const { autoRefresh = true, refreshInterval = 60000 } = options; // Default 60s

  const [metrics, setMetrics] = useState<ValidationMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/validation/current-metrics', {
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

      setMetrics(data.data);
      setLastUpdated(new Date());
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch validation metrics';
      setError(errorMessage);
      console.error('[useValidationMetrics] Error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchMetrics();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchMetrics]);

  return {
    metrics,
    loading,
    error,
    refetch: fetchMetrics,
    lastUpdated,
  };
}
