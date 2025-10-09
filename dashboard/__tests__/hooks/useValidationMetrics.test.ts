/**
 * useValidationMetrics Hook Tests - Story 11.8
 */

import { renderHook, waitFor } from '@testing-library/react';
import { useValidationMetrics } from '@/hooks/useValidationMetrics';

// Mock fetch
global.fetch = jest.fn();

const mockMetricsResponse = {
  data: {
    overfitting_score: 0.274,
    live_sharpe: 1.38,
    backtest_sharpe: 1.52,
    sharpe_ratio: 0.908,
    parameter_drift_7d: 0.08,
    parameter_drift_30d: 0.15,
    last_updated: '2025-10-09T12:00:00Z',
  },
  error: null,
  correlation_id: 'test-123',
};

describe('useValidationMetrics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockMetricsResponse,
    });
  });

  it('fetches metrics on mount', async () => {
    const { result } = renderHook(() => useValidationMetrics());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.metrics).toEqual(mockMetricsResponse.data);
    expect(result.current.error).toBeNull();
  });

  it('handles fetch errors', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useValidationMetrics());

    await waitFor(() => {
      expect(result.current.error).toBe('Network error');
    });

    expect(result.current.metrics).toBeNull();
  });

  it('handles HTTP errors', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    });

    const { result } = renderHook(() => useValidationMetrics());

    await waitFor(() => {
      expect(result.current.error).toContain('500');
    });
  });

  it('handles API errors in response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        data: null,
        error: 'Service unavailable',
        correlation_id: 'test-123',
      }),
    });

    const { result } = renderHook(() => useValidationMetrics());

    await waitFor(() => {
      expect(result.current.error).toBe('Service unavailable');
    });
  });

  it('supports manual refetch', async () => {
    const { result } = renderHook(() => useValidationMetrics({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    await result.current.refetch();

    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it('auto-refreshes when enabled', async () => {
    jest.useFakeTimers();

    const { result } = renderHook(() =>
      useValidationMetrics({ autoRefresh: true, refreshInterval: 1000 })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    jest.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    jest.useRealTimers();
  });

  it('does not auto-refresh when disabled', async () => {
    jest.useFakeTimers();

    const { result } = renderHook(() =>
      useValidationMetrics({ autoRefresh: false })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    jest.advanceTimersByTime(60000);

    expect(global.fetch).toHaveBeenCalledTimes(1);

    jest.useRealTimers();
  });

  it('updates lastUpdated timestamp', async () => {
    const { result } = renderHook(() => useValidationMetrics());

    expect(result.current.lastUpdated).toBeNull();

    await waitFor(() => {
      expect(result.current.lastUpdated).toBeInstanceOf(Date);
    });
  });
});
