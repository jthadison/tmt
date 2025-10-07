/**
 * useSkeletonTimeout Hook
 * Story 9.1: Hook to handle skeleton screen timeout after 30 seconds
 */

'use client';

import { useEffect, useState, useRef } from 'react';

interface UseSkeletonTimeoutOptions {
  timeout?: number; // milliseconds, default 30000 (30s)
  onTimeout?: () => void;
}

export function useSkeletonTimeout({
  timeout = 30000,
  onTimeout,
}: UseSkeletonTimeoutOptions = {}) {
  const [timedOut, setTimedOut] = useState(false);
  const onTimeoutRef = useRef(onTimeout);

  // Update ref when callback changes to avoid stale closure
  useEffect(() => {
    onTimeoutRef.current = onTimeout;
  }, [onTimeout]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setTimedOut(true);
      onTimeoutRef.current?.();
    }, timeout);

    return () => clearTimeout(timer);
  }, [timeout]);

  const reset = () => setTimedOut(false);

  return { timedOut, reset };
}
