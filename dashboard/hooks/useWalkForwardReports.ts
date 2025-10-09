/**
 * useWalkForwardReports Hook - Story 11.8, Task 9
 *
 * Custom hook for fetching walk-forward validation reports
 */

import { useState, useEffect, useCallback } from 'react';
import type { ValidationJob, WalkForwardReport } from '@/types/validation';

interface UseWalkForwardReportsOptions {
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseWalkForwardReportsReturn {
  reports: ValidationJob[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  fetchReportDetail: (reportId: string) => Promise<WalkForwardReport | null>;
}

export function useWalkForwardReports(
  options: UseWalkForwardReportsOptions = {}
): UseWalkForwardReportsReturn {
  const { limit = 20, autoRefresh = true, refreshInterval = 30000 } = options; // Default 30s

  const [reports, setReports] = useState<ValidationJob[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/validation/walk-forward-reports?limit=${limit}`, {
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

      setReports(data.data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch walk-forward reports';
      setError(errorMessage);
      console.error('[useWalkForwardReports] Error:', err);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  const fetchReportDetail = useCallback(async (reportId: string): Promise<WalkForwardReport | null> => {
    try {
      const response = await fetch(`/api/validation/report/${reportId}`, {
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

      return data.data;
    } catch (err) {
      console.error(`[useWalkForwardReports] Error fetching report ${reportId}:`, err);
      return null;
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchReports();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchReports]);

  return {
    reports,
    loading,
    error,
    refetch: fetchReports,
    fetchReportDetail,
  };
}
