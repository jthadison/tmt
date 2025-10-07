/**
 * useSkeletonTimeout Hook Tests
 * Story 9.1: AC8 - Skeleton timeout (30 seconds → error state)
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { useSkeletonTimeout } from '@/hooks/useSkeletonTimeout';

describe('useSkeletonTimeout', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('starts with timedOut as false', () => {
    const { result } = renderHook(() => useSkeletonTimeout());
    expect(result.current.timedOut).toBe(false);
  });

  it('sets timedOut to true after default timeout (30s)', async () => {
    const { result } = renderHook(() => useSkeletonTimeout());

    expect(result.current.timedOut).toBe(false);

    // Fast-forward 30 seconds
    jest.advanceTimersByTime(30000);

    await waitFor(() => {
      expect(result.current.timedOut).toBe(true);
    });
  });

  it('uses custom timeout value', async () => {
    const { result } = renderHook(() => useSkeletonTimeout({ timeout: 5000 }));

    expect(result.current.timedOut).toBe(false);

    // Fast-forward 5 seconds
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(result.current.timedOut).toBe(true);
    });
  });

  it('does not timeout before timeout duration', () => {
    const { result } = renderHook(() => useSkeletonTimeout({ timeout: 10000 }));

    // Fast-forward 9 seconds (less than timeout)
    jest.advanceTimersByTime(9000);

    expect(result.current.timedOut).toBe(false);
  });

  it('calls onTimeout callback when timeout occurs', async () => {
    const onTimeout = jest.fn();
    renderHook(() => useSkeletonTimeout({ timeout: 5000, onTimeout }));

    expect(onTimeout).not.toHaveBeenCalled();

    // Fast-forward to timeout
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(onTimeout).toHaveBeenCalledTimes(1);
    });
  });

  it('cleans up timeout on unmount', () => {
    const { unmount } = renderHook(() => useSkeletonTimeout({ timeout: 5000 }));

    // Unmount before timeout
    unmount();

    // Fast-forward past timeout
    jest.advanceTimersByTime(6000);

    // Timeout should not trigger after unmount
    // (No error should be thrown)
  });

  it('resets timeout when dependencies change', () => {
    let timeout = 5000;
    const { result, rerender } = renderHook(() => useSkeletonTimeout({ timeout }));

    // Fast-forward 3 seconds
    jest.advanceTimersByTime(3000);

    expect(result.current.timedOut).toBe(false);

    // Change timeout value (simulating re-render with new props)
    timeout = 10000;
    rerender();

    // Fast-forward another 4 seconds (total 7 seconds from start)
    jest.advanceTimersByTime(4000);

    // Should not have timed out yet (new timeout is 10s from re-render)
    expect(result.current.timedOut).toBe(false);
  });

  it('provides reset function to manually reset timedOut', async () => {
    const { result } = renderHook(() => useSkeletonTimeout({ timeout: 1000 }));

    // Fast-forward to timeout
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(result.current.timedOut).toBe(true);
    });

    // Reset
    act(() => {
      result.current.reset();
    });

    expect(result.current.timedOut).toBe(false);
  });
});
