/**
 * useAgentDisagreement Hook
 *
 * Custom hook for fetching and managing agent disagreement data
 *
 * Story 7.1: Data Management Hook
 */

import { useState, useEffect, useCallback } from 'react';
import { DisagreementData } from '@/types/intelligence';
import { fetchDisagreementData } from '@/services/api/intelligence';

export interface UseAgentDisagreementOptions {
  symbol: string;
  enabled?: boolean;
  refreshInterval?: number; // milliseconds
}

export interface UseAgentDisagreementResult {
  data: DisagreementData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch and manage agent disagreement data
 *
 * @param options - Configuration options
 * @param options.symbol - Trading symbol to fetch disagreement for
 * @param options.enabled - Whether to fetch data (default: true)
 * @param options.refreshInterval - Auto-refresh interval in ms (optional)
 *
 * @returns Object with data, loading state, error, and refetch function
 *
 * @example
 * const { data, loading, error, refetch } = useAgentDisagreement({
 *   symbol: 'EUR_USD',
 *   enabled: true,
 *   refreshInterval: 5000
 * });
 */
export function useAgentDisagreement({
  symbol,
  enabled = true,
  refreshInterval
}: UseAgentDisagreementOptions): UseAgentDisagreementResult {
  const [data, setData] = useState<DisagreementData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled) return;

    setLoading(true);
    setError(null);

    try {
      const disagreementData = await fetchDisagreementData(symbol);
      setData(disagreementData);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch disagreement data');
      setError(error);
      console.error('Error in useAgentDisagreement:', error);
    } finally {
      setLoading(false);
    }
  }, [symbol, enabled]);

  // Initial fetch and refresh interval
  useEffect(() => {
    fetchData();

    if (refreshInterval && enabled) {
      const intervalId = setInterval(fetchData, refreshInterval);
      return () => clearInterval(intervalId);
    }
  }, [fetchData, refreshInterval, enabled]);

  return {
    data,
    loading,
    error,
    refetch: fetchData
  };
}
