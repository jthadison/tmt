/**
 * useSkeletonTimeout Hook
 * Story 9.1: Hook to handle skeleton screen timeout after 30 seconds
 */

'use client';

import { useEffect, useState } from 'react';

interface UseSkeletonTimeoutOptions {
  timeout?: number; // milliseconds, default 30000 (30s)
  onTimeout?: () => void;
}

export function useSkeletonTimeout({
  timeout = 30000,
  onTimeout,
}: UseSkeletonTimeoutOptions = {}) {
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setTimedOut(true);
      onTimeout?.();
    }, timeout);

    return () => clearTimeout(timer);
  }, [timeout, onTimeout]);

  const reset = () => setTimedOut(false);

  return { timedOut, reset };
}
