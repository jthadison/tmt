/**
 * Close Positions Hook
 * Manages position closing logic and state
 */

import { useState, useCallback } from 'react';
import { closeAllPositions, getOpenPositions } from '@/api/execution';
import { logEmergencyAction } from '@/api/emergency';
import type { Position, ClosePositionsResponse } from '@/types/execution';

export function useClosePositions() {
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loadingPositions, setLoadingPositions] = useState(false);

  // Fetch current open positions
  const fetchPositions = useCallback(async () => {
    try {
      setLoadingPositions(true);
      const data = await getOpenPositions();
      setPositions(data);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Failed to fetch positions:', err);
    } finally {
      setLoadingPositions(false);
    }
  }, []);

  // Execute close all positions
  const executeCloseAll = useCallback(async (reason?: string): Promise<ClosePositionsResponse> => {
    setIsExecuting(true);
    setError(null);

    try {
      const result = await closeAllPositions({ reason });

      // Log audit trail
      await logEmergencyAction({
        action: 'close_positions',
        user: 'anonymous',
        positionsClosed: result.positions_closed,
        success: result.success,
        details: {
          errors: result.errors,
          reason,
        },
      });

      // Refresh positions after closing
      await fetchPositions();

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);

      // Log failed attempt
      await logEmergencyAction({
        action: 'close_positions',
        user: 'anonymous',
        success: false,
        error: errorMessage,
      });

      throw err;
    } finally {
      setIsExecuting(false);
    }
  }, [fetchPositions]);

  return {
    executeCloseAll,
    fetchPositions,
    positions,
    isExecuting,
    loadingPositions,
    error,
  };
}
