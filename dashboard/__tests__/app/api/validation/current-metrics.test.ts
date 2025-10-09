/**
 * GET /api/validation/current-metrics Integration Tests - Story 11.8
 */

import { GET } from '@/app/api/validation/current-metrics/route';
import { NextRequest } from 'next/server';

// Mock fetch
global.fetch = jest.fn();

describe('GET /api/validation/current-metrics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns current validation metrics successfully', async () => {
    const mockBackendResponse = {
      data: {
        current_score: 0.274,
        live_performance: { sharpe_ratio: 1.38 },
        backtest_performance: { sharpe_ratio: 1.52 },
        performance_ratio: 0.908,
        drift_7d: 0.08,
        drift_30d: 0.15,
        timestamp: '2025-10-09T12:00:00Z',
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockBackendResponse,
    });

    const request = new NextRequest('http://localhost:3000/api/validation/current-metrics');
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.data).toHaveProperty('overfitting_score');
    expect(data.data.overfitting_score).toBe(0.274);
    expect(data.data.live_sharpe).toBe(1.38);
    expect(data.data.backtest_sharpe).toBe(1.52);
    expect(data.error).toBeNull();
    expect(data.correlation_id).toBeDefined();
  });

  it('handles backend service errors', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    });

    const request = new NextRequest('http://localhost:3000/api/validation/current-metrics');
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toContain('Overfitting monitor returned 500');
    expect(data.correlation_id).toBeDefined();
  });

  it('handles network errors', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    const request = new NextRequest('http://localhost:3000/api/validation/current-metrics');
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Network error');
  });

  it('includes correlation ID in response headers', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: {} }),
    });

    const request = new NextRequest('http://localhost:3000/api/validation/current-metrics');
    const response = await GET(request);

    expect(response.headers.get('X-Correlation-ID')).toBeDefined();
  });

  it('returns default values when backend data is missing', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: {} }),
    });

    const request = new NextRequest('http://localhost:3000/api/validation/current-metrics');
    const response = await GET(request);
    const data = await response.json();

    expect(data.data.overfitting_score).toBe(0);
    expect(data.data.live_sharpe).toBe(0);
    expect(data.data.backtest_sharpe).toBe(0);
  });
});
