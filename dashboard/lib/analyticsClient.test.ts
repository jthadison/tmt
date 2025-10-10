/**
 * Analytics Client Tests (Story 12.2)
 *
 * Tests for analytics API client with mocked fetch responses
 */

import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals'
import * as analyticsClient from './analyticsClient'
import { AnalyticsDateRange } from '@/types/analytics122'

// Mock global fetch
global.fetch = jest.fn() as jest.MockedFunction<typeof fetch>

describe('Analytics Client', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  afterEach(() => {
    jest.resetAllMocks()
  })

  const mockDateRange: AnalyticsDateRange = {
    start_date: '2025-01-01T00:00:00Z',
    end_date: '2025-01-31T23:59:59Z',
  }

  describe('fetchSessionPerformance', () => {
    it('should fetch session performance data successfully', async () => {
      const mockData = {
        TOKYO: { win_rate: 72.5, total_trades: 40, winning_trades: 29, losing_trades: 11 },
        LONDON: { win_rate: 68.3, total_trades: 35, winning_trades: 24, losing_trades: 11 },
      }

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockData, error: null, correlation_id: 'test-123' }),
      } as Response)

      const result = await analyticsClient.fetchSessionPerformance(mockDateRange)

      expect(result).toEqual(mockData)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/analytics/performance/by-session'),
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      )
    })

    it('should handle API errors gracefully', async () => {
      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: null, error: 'Database connection failed', correlation_id: 'test-123' }),
      } as Response)

      await expect(analyticsClient.fetchSessionPerformance(mockDateRange)).rejects.toThrow(
        'Database connection failed'
      )
    })

    it('should retry on server errors', async () => {
      ;(global.fetch as jest.MockedFunction<typeof fetch>)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ data: {}, error: null, correlation_id: 'test-123' }),
        } as Response)

      const result = await analyticsClient.fetchSessionPerformance(mockDateRange)

      expect(result).toEqual({})
      expect(global.fetch).toHaveBeenCalledTimes(3)
    })
  })

  describe('fetchPatternPerformance', () => {
    it('should fetch pattern performance data successfully', async () => {
      const mockData = {
        Spring: { win_rate: 75.5, sample_size: 42, significant: true },
        Upthrust: { win_rate: 62.1, sample_size: 15, significant: false },
      }

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockData, error: null, correlation_id: 'test-123' }),
      } as Response)

      const result = await analyticsClient.fetchPatternPerformance(mockDateRange)

      expect(result).toEqual(mockData)
    })
  })

  describe('fetchPnLByPair', () => {
    it('should fetch P&L data successfully', async () => {
      const mockData = {
        EUR_USD: { total_pnl: 1234.56, trade_count: 42, avg_pnl: 29.39 },
        GBP_USD: { total_pnl: -543.21, trade_count: 28, avg_pnl: -19.40 },
      }

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockData, error: null, correlation_id: 'test-123' }),
      } as Response)

      const result = await analyticsClient.fetchPnLByPair(mockDateRange)

      expect(result).toEqual(mockData)
    })
  })

  describe('fetchConfidenceCorrelation', () => {
    it('should fetch correlation data successfully', async () => {
      const mockData = {
        scatter_data: [
          { confidence: 75.5, outcome: 1, symbol: 'EUR_USD' },
          { confidence: 62.3, outcome: 0, symbol: 'GBP_USD' },
        ],
        correlation_coefficient: 0.73,
      }

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockData, error: null, correlation_id: 'test-123' }),
      } as Response)

      const result = await analyticsClient.fetchConfidenceCorrelation(mockDateRange)

      expect(result).toEqual(mockData)
    })
  })

  describe('exportToCSV', () => {
    it('should export CSV successfully', async () => {
      const mockBlob = new Blob(['csv data'], { type: 'text/csv' })

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      } as Response)

      const result = await analyticsClient.exportToCSV(mockDateRange)

      expect(result).toBeInstanceOf(Blob)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/analytics/export/csv'),
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      )
    })

    it('should throw error if dates are missing', async () => {
      const invalidRange = { start_date: '', end_date: '' }

      await expect(analyticsClient.exportToCSV(invalidRange)).rejects.toThrow(
        'Start and end dates are required for CSV export'
      )
    })
  })
})
