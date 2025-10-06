/**
 * Hook for fetching and managing pattern detection data
 */

import { useState, useEffect, useCallback } from 'react';
import { PatternData } from '@/types/intelligence';
import { fetchPatterns, generateMockPatterns } from '@/services/api/patterns';

interface UsePatternDataOptions {
  symbol: string;
  timeframe?: string;
  limit?: number;
  enabled?: boolean;
  useMockData?: boolean;
}

interface UsePatternDataReturn {
  patterns: PatternData[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Fetch pattern detection data for a symbol
 */
export function usePatternData({
  symbol,
  timeframe = '1h',
  limit = 10,
  enabled = true,
  useMockData = false
}: UsePatternDataOptions): UsePatternDataReturn {
  const [patterns, setPatterns] = useState<PatternData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled || !symbol) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let data: PatternData[];

      if (useMockData) {
        // Use mock data for development
        data = generateMockPatterns(symbol);
      } else {
        // Fetch from Pattern Detection agent
        data = await fetchPatterns(symbol, timeframe, limit);
      }

      setPatterns(data);
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error('Failed to fetch patterns');
      setError(errorObj);
      console.error('Error in usePatternData:', errorObj);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe, limit, enabled, useMockData]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    patterns,
    loading,
    error,
    refetch: fetchData
  };
}
