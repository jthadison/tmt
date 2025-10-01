/**
 * Emergency Stop Hook
 * Manages emergency stop logic, rate limiting, and state
 */

import { useState, useMemo, useCallback } from 'react';
import { emergencyStopTrading, resumeTrading, logEmergencyAction } from '@/api/emergency';
import type { EmergencyStopResponse } from '@/types/emergency';

const COOLDOWN_MS = 60000; // 60 seconds

export function useEmergencyStop() {
  const [isExecuting, setIsExecuting] = useState(false);
  const [lastStopTime, setLastStopTime] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canExecute = useMemo(() => {
    if (!lastStopTime) return true;
    const elapsed = Date.now() - lastStopTime.getTime();
    return elapsed > COOLDOWN_MS;
  }, [lastStopTime]);

  const cooldownRemaining = useMemo(() => {
    if (!lastStopTime) return 0;
    return Math.max(0, Math.ceil((COOLDOWN_MS - (Date.now() - lastStopTime.getTime())) / 1000));
  }, [lastStopTime]);

  const executeEmergencyStop = useCallback(
    async (closePositions: boolean): Promise<EmergencyStopResponse> => {
      if (!canExecute) {
        throw new Error('Emergency stop cooldown active');
      }

      setIsExecuting(true);
      setError(null);

      try {
        const result = await emergencyStopTrading({ closePositions });
        setLastStopTime(new Date());

        // Log audit trail
        await logEmergencyAction({
          action: 'emergency_stop',
          user: 'anonymous',
          closePositions,
          positionsClosed: result.positions_closed,
          success: true,
        });

        return result;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);

        // Log failed attempt
        await logEmergencyAction({
          action: 'emergency_stop',
          user: 'anonymous',
          closePositions,
          success: false,
          error: errorMessage,
        });

        throw err;
      } finally {
        setIsExecuting(false);
      }
    },
    [canExecute]
  );

  const executeResumeTrading = useCallback(async (): Promise<EmergencyStopResponse> => {
    setIsExecuting(true);
    setError(null);

    try {
      const result = await resumeTrading();

      await logEmergencyAction({
        action: 'resume_trading',
        user: 'anonymous',
        success: true,
      });

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setIsExecuting(false);
    }
  }, []);

  return {
    executeEmergencyStop,
    executeResumeTrading,
    isExecuting,
    canExecute,
    error,
    cooldownRemaining,
  };
}
