/**
 * Performance Analytics Service Tests
 * ===================================
 * 
 * Test suite for the performance analytics service including API calls,
 * caching, error handling, and data processing.
 */

import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'

// Mock fetch globally
global.fetch = jest.fn()

const mockFetch = fetch as jest.MockedFunction<typeof fetch>

describe('PerformanceAnalyticsService', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Clear service cache
    performanceAnalyticsService.clearCache()
  })

  describe('getRealtimePnL', () => {
    const mockPnLResponse = {
      accountId: 'test_account_001',
      agentId: 'market_analysis',
      currentPnL: 1250.00,
      realizedPnL: 800.00,
      unrealizedPnL: 450.00,
      dailyPnL: 125.50,
      weeklyPnL: 340.75,
      monthlyPnL: 1250.00,
      trades: [],
      lastUpdate: new Date().toISOString(),
      highWaterMark: 2000.00,
      currentDrawdown: 750.00
    }

    it('should fetch real-time P&L data successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPnLResponse,
      } as Response)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      } as Response)

      const result = await performanceAnalyticsService.getRealtimePnL('test_account_001', 'market_analysis')

      expect(result).toMatchObject({
        accountId: 'test_account_001',
        agentId: 'market_analysis',
        currentPnL: 1250.00,
        realizedPnL: 800.00,
        unrealizedPnL: 450.00
      })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/analytics/realtime-pnl'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            accountId: 'test_account_001', 
            agentId: 'market_analysis' 
          })
        })
      )
    })

    it('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Network error'))

      await expect(
        performanceAnalyticsService.getRealtimePnL('test_account_001')
      ).rejects.toThrow('Network error fetching P&L data')
    })

    it('should handle API errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
      } as Response)

      await expect(
        performanceAnalyticsService.getRealtimePnL('test_account_001')
      ).rejects.toThrow('Failed to fetch real-time P&L: Internal Server Error')
    })

    it('should handle malformed JSON responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => { throw new SyntaxError('Invalid JSON') },
      } as Response)

      await expect(
        performanceAnalyticsService.getRealtimePnL('test_account_001')
      ).rejects.toThrow('Invalid response format')
    })

    it('should use caching for repeated requests', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockPnLResponse,
      } as Response)

      // First call
      await performanceAnalyticsService.getRealtimePnL('test_account_001', 'market_analysis')
      
      // Second call - should use cache
      await performanceAnalyticsService.getRealtimePnL('test_account_001', 'market_analysis')

      // Should only make API call once due to caching
      expect(mockFetch).toHaveBeenCalledTimes(2) // One for P&L, one for trades
    })
  })

  describe('getTradeBreakdown', () => {
    const mockTradesResponse = [
      {
        id: 'trade_001',
        symbol: 'EURUSD',
        openTime: '2024-01-15T10:30:00Z',
        closeTime: '2024-01-15T14:45:00Z',
        openPrice: 1.0850,
        closePrice: 1.0875,
        size: 1.0,
        direction: 'buy',
        profit: 250.00,
        commission: 7.00,
        swap: 0.50,
        agentId: 'market_analysis',
        agentName: 'Market Analysis',
        strategy: 'wyckoff_accumulation'
      }
    ]

    it('should fetch trade breakdown successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTradesResponse,
      } as Response)

      const result = await performanceAnalyticsService.getTradeBreakdown('test_account_001')

      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        tradeId: 'trade_001',
        symbol: 'EURUSD',
        direction: 'long',
        pnl: 250.00,
        commission: 7.00
      })
    })

    it('should handle empty trade list', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      } as Response)

      const result = await performanceAnalyticsService.getTradeBreakdown('test_account_001')

      expect(result).toEqual([])
    })

    it('should filter by agent ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTradesResponse,
      } as Response)

      await performanceAnalyticsService.getTradeBreakdown(
        'test_account_001',
        'market_analysis'
      )

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/analytics/trades'),
        expect.objectContaining({
          body: JSON.stringify({ 
            accountId: 'test_account_001', 
            agentId: 'market_analysis' 
          })
        })
      )
    })

    it('should apply date range filter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTradesResponse,
      } as Response)

      const dateRange = {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-31')
      }

      await performanceAnalyticsService.getTradeBreakdown(
        'test_account_001',
        undefined,
        dateRange
      )

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/analytics/trades'),
        expect.objectContaining({
          body: JSON.stringify({ 
            accountId: 'test_account_001', 
            agentId: undefined,
            dateRange 
          })
        })
      )
    })
  })

  describe('calculateRiskMetrics', () => {
    const mockRiskMetrics = {
      sharpeRatio: 1.35,
      sortinoRatio: 1.72,
      calmarRatio: 0.89,
      maxDrawdown: 850.00,
      maxDrawdownPercent: 8.5,
      currentDrawdown: 200.00,
      currentDrawdownPercent: 2.0,
      averageDrawdown: 425.00,
      drawdownDuration: 5,
      recoveryFactor: 2.3,
      volatility: 0.15,
      downsideDeviation: 0.08,
      valueAtRisk95: -125.00,
      valueAtRisk99: -185.00,
      conditionalVaR: -220.00,
      beta: 1.05,
      alpha: 0.02,
      correlation: 0.65,
      winLossRatio: 0.72,
      profitFactor: 1.85,
      expectancy: 45.20,
      kellyPercentage: 0.18
    }

    it('should calculate risk metrics successfully', async () => {
      // Mock the trades response first
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      } as Response)

      // Mock the actual risk metrics response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRiskMetrics,
      } as Response)

      const dateRange = {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-31')
      }

      const result = await performanceAnalyticsService.calculateRiskMetrics(
        'test_account_001',
        dateRange
      )

      expect(result).toMatchObject({
        sharpeRatio: 1.35,
        sortinoRatio: 1.72,
        maxDrawdown: 850.00,
        winLossRatio: 0.72,
        profitFactor: 1.85
      })
    })

    it('should handle calculation errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Calculation failed'))

      const dateRange = {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-31')
      }

      await expect(
        performanceAnalyticsService.calculateRiskMetrics('test_account_001', dateRange)
      ).rejects.toThrow('Calculation failed')
    })
  })

  describe('generateComplianceReport', () => {
    const mockComplianceReport = {
      reportId: 'RPT-12345',
      generatedAt: new Date().toISOString(),
      period: {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-31')
      },
      accounts: [],
      aggregateMetrics: {
        totalPnL: 2500.00,
        totalTrades: 45,
        totalVolume: 125.5,
        averageDailyVolume: 4.05,
        peakExposure: 15000.00,
        maxDrawdown: 750.00
      },
      violations: [],
      auditTrail: [],
      regulatoryMetrics: {
        mifidCompliant: true,
        nfaCompliant: true,
        esmaCompliant: true,
        bestExecutionScore: 95,
        orderToTradeRatio: 1.2,
        cancelRatio: 0.05
      },
      signature: 'COMP-RPT-12345'
    }

    it('should generate compliance report successfully', async () => {
      // Mock all the required API calls
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockComplianceReport,
      } as Response)

      const result = await performanceAnalyticsService.generateComplianceReport(
        ['test_account_001'],
        {
          start: new Date('2024-01-01'),
          end: new Date('2024-01-31')
        },
        'standard'
      )

      expect(result).toMatchObject({
        reportId: 'RPT-12345',
        aggregateMetrics: expect.objectContaining({
          totalPnL: 2500.00,
          totalTrades: 45
        }),
        regulatoryMetrics: expect.objectContaining({
          mifidCompliant: true,
          nfaCompliant: true
        })
      })
    })

    it('should handle different report types', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockComplianceReport,
      } as Response)

      const reportTypes = ['standard', 'detailed', 'executive', 'regulatory'] as const

      for (const reportType of reportTypes) {
        await performanceAnalyticsService.generateComplianceReport(
          ['test_account_001'],
          {
            start: new Date('2024-01-01'),
            end: new Date('2024-01-31')
          },
          reportType
        )
      }

      expect(mockFetch).toHaveBeenCalledTimes(reportTypes.length * 4) // Multiple API calls per report
    })
  })

  describe('exportReport', () => {
    it('should export report as JSON', async () => {
      const mockBlob = new Blob(['{"test": "data"}'], { type: 'application/json' })
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      } as Response)

      const report = { test: 'data' }
      const result = await performanceAnalyticsService.exportReport(report, 'json')

      expect(result).toBeInstanceOf(Blob)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/analytics/export'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ report, format: 'json' })
        })
      )
    })

    it('should handle export errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Export failed',
      } as Response)

      const report = { test: 'data' }

      await expect(
        performanceAnalyticsService.exportReport(report, 'pdf')
      ).rejects.toThrow('Failed to export report: Export failed')
    })
  })

  describe('caching', () => {
    it('should cache responses for specified TTL', async () => {
      const mockResponse = { test: 'data' }
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      // Make two identical requests
      await performanceAnalyticsService.getRealtimePnL('test_account_001')
      await performanceAnalyticsService.getRealtimePnL('test_account_001')

      // Should use cache for second request
      expect(mockFetch).toHaveBeenCalledTimes(2) // P&L + trades for first call only
    })

    it('should clear cache when requested', async () => {
      const mockResponse = { test: 'data' }
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      // Make request
      await performanceAnalyticsService.getRealtimePnL('test_account_001')
      
      // Clear cache
      performanceAnalyticsService.clearCache()
      
      // Make same request again
      await performanceAnalyticsService.getRealtimePnL('test_account_001')

      // Should make API call again after cache clear
      expect(mockFetch).toHaveBeenCalledTimes(4) // 2 calls * 2 (P&L + trades each)
    })

    it('should track query performance metrics', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({}),
      } as Response)

      await performanceAnalyticsService.getRealtimePnL('test_account_001')

      const metrics = performanceAnalyticsService.getQueryPerformance()
      expect(metrics.length).toBeGreaterThan(0)
      expect(metrics[0]).toHaveProperty('queryId')
      expect(metrics[0]).toHaveProperty('executionTime')
      expect(metrics[0]).toHaveProperty('timestamp')
    })
  })

  describe('error handling', () => {
    it('should handle unexpected errors gracefully', async () => {
      mockFetch.mockImplementationOnce(() => {
        throw new Error('Unexpected error')
      })

      await expect(
        performanceAnalyticsService.getRealtimePnL('test_account_001')
      ).rejects.toThrow('Unexpected error')
    })

    it('should handle timeout errors', async () => {
      mockFetch.mockImplementationOnce(() => 
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Request timeout')), 100)
        )
      )

      await expect(
        performanceAnalyticsService.getRealtimePnL('test_account_001')
      ).rejects.toThrow('Request timeout')
    })
  })

  describe('data validation', () => {
    it('should handle invalid date formats', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          accountId: 'test_account_001',
          lastUpdate: 'invalid-date',
          trades: []
        }),
      } as Response)

      // Should not throw but might need to handle invalid dates
      const result = await performanceAnalyticsService.getRealtimePnL('test_account_001')
      expect(result).toBeDefined()
    })

    it('should handle missing required fields', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          // Missing required fields
          incomplete: 'data'
        }),
      } as Response)

      // Service should handle missing fields gracefully
      await expect(
        performanceAnalyticsService.getRealtimePnL('test_account_001')
      ).rejects.toThrow() // Or handle gracefully depending on implementation
    })
  })
})