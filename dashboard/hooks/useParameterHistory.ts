/**
 * useParameterHistory Hook - Story 11.8, Task 9
 *
 * Custom hook for fetching parameter version history
 */

import { useState, useEffect, useCallback } from 'react';
import type { ParameterVersion } from '@/types/validation';

interface UseParameterHistoryOptions {
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseParameterHistoryReturn {
  versions: ParameterVersion[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useParameterHistory(
  options: UseParameterHistoryOptions = {}
): UseParameterHistoryReturn {
  const { limit = 10, autoRefresh = false, refreshInterval = 300000 } = options; // Default 5min

  const [versions, setVersions] = useState<ParameterVersion[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/validation/parameter-history?limit=${limit}`, {
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

      setVersions(data.data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch parameter history';
      setError(errorMessage);
      console.error('[useParameterHistory] Error:', err);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  // Initial fetch
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchHistory();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchHistory]);

  return {
    versions,
    loading,
    error,
    refetch: fetchHistory,
  };
}
