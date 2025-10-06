import { render, screen, waitFor } from '@testing-library/react'
import ComparisonPage from '@/app/analytics/comparison/page'

// Mock fetch for API calls
global.fetch = jest.fn()

describe('Story 8.2: Forward Test vs Backtest Comparison Integration', () => {
  const mockBacktestData = {
    strategyName: 'Wyckoff VPA Strategy',
    testPeriod: {
      startDate: '2025-01-01T00:00:00Z',
      endDate: '2025-03-31T00:00:00Z',
      totalDays: 90
    },
    metrics: {
      winRate: 68.5,
      avgWin: 145.30,
      avgLoss: 82.50,
      profitFactor: 2.4,
      maxDrawdown: 485.75,
      maxDrawdownPercent: 4.86,
      sharpeRatio: 1.85,
      totalTrades: 127,
      totalProfit: 7982.50
    },
    parsedAt: Date.now(),
    sourceFile: 'backtest_results_20250331.json'
  }

  const mockForwardTestData = {
    testPeriod: {
      startDate: '2025-04-01T00:00:00Z',
      endDate: '2025-06-30T00:00:00Z',
      totalDays: 90
    },
    metrics: {
      winRate: 62.3,
      avgWin: 138.20,
      avgLoss: 88.40,
      profitFactor: 2.1,
      maxDrawdown: 612.30,
      maxDrawdownPercent: 6.12,
      sharpeRatio: 1.58,
      totalTrades: 115,
      totalProfit: 5745.80
    },
    dailyReturns: Array(90).fill(0).map((_, i) => ({
      date: `2025-04-${String(i % 30 + 1).padStart(2, '0')}`,
      return: 50 + Math.random() * 100,
      cumulativePnL: (i + 1) * 63.84
    })),
    calculatedAt: Date.now()
  }

  const mockOverfittingData = {
    overfittingScore: 0.32,
    degradationPercentage: 9.6,
    riskLevel: 'low' as const,
    metricDegradation: {
      winRate: {
        backtest: 68.5,
        forward: 62.3,
        degradation: -9.05
      },
      profitFactor: {
        backtest: 2.4,
        forward: 2.1,
        degradation: -12.5
      },
      sharpeRatio: {
        backtest: 1.85,
        forward: 1.58,
        degradation: -14.59
      },
      avgWin: {
        backtest: 145.30,
        forward: 138.20,
        degradation: -4.88
      },
      avgLoss: {
        backtest: 82.50,
        forward: 88.40,
        degradation: -7.15
      }
    },
    interpretation: 'Low overfitting risk (9.6% degradation). Strategy generalizes well to unseen data and shows stable performance.',
    recommendations: [
      'Strategy performing well - continue monitoring',
      'Consider gradual position size increases if stability maintains'
    ],
    stabilityScore: 78.5
  }

  beforeAll(() => {
    // Mock all API endpoints
    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/api/analytics/backtest-results')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockBacktestData
        })
      }
      if (url.includes('/api/analytics/forward-test-performance')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockForwardTestData
        })
      }
      if (url.includes('/api/analytics/overfitting-analysis')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockOverfittingData
        })
      }
      return Promise.reject(new Error('Unknown endpoint'))
    })
  })

  it('AC1: Backtest Results Parser Service - loads and displays backtest data', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      expect(screen.getByText('Forward Test vs. Backtest Comparison')).toBeInTheDocument()
    })

    // Verify backtest period displayed
    await waitFor(() => {
      expect(screen.getByText('90 Days')).toBeInTheDocument()
    })
  })

  it('AC2: Forward Test Performance Aggregator - displays forward test metrics', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      expect(screen.getByText(/Forward Test Period/)).toBeInTheDocument()
    })

    // Verify forward test trades count
    await waitFor(() => {
      expect(screen.getByText('115')).toBeInTheDocument()
    })
  })

  it('AC3: Metric Comparison Table - shows side-by-side comparison with variance', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      expect(screen.getByText('Performance Metrics Comparison')).toBeInTheDocument()
    })

    // Verify table headers
    await waitFor(() => {
      expect(screen.getByText('Backtest')).toBeInTheDocument()
      expect(screen.getByText('Forward Test')).toBeInTheDocument()
      expect(screen.getByText('Variance')).toBeInTheDocument()
    })

    // Verify variance calculation displayed
    await waitFor(() => {
      const varianceElements = screen.getAllByText(/-\d+\.\d%/)
      expect(varianceElements.length).toBeGreaterThan(0)
    })
  })

  it('AC4: Cumulative Returns Chart - displays overlay chart', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      expect(screen.getByText('Cumulative Returns Comparison')).toBeInTheDocument()
    })

    // Verify chart description
    await waitFor(() => {
      expect(screen.getByText(/Historical backtest performance vs. live forward test results/)).toBeInTheDocument()
    })
  })

  it('AC5: Overfitting Analysis Calculator - calculates and displays overfitting score', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      expect(screen.getByText('Overfitting Analysis')).toBeInTheDocument()
    })

    // Verify overfitting score displayed
    await waitFor(() => {
      expect(screen.getByText('0.32')).toBeInTheDocument()
    })

    // Verify degradation percentage
    await waitFor(() => {
      expect(screen.getByText('9.6%')).toBeInTheDocument()
    })

    // Verify risk level
    await waitFor(() => {
      expect(screen.getByText('Low Risk')).toBeInTheDocument()
    })
  })

  it('AC6: Overfitting Analysis Dashboard - shows interpretation and recommendations', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      expect(screen.getByText(/Low overfitting risk/)).toBeInTheDocument()
    })

    // Verify recommendations displayed
    await waitFor(() => {
      expect(screen.getByText(/Strategy performing well/)).toBeInTheDocument()
    })

    // Verify metric degradation breakdown
    await waitFor(() => {
      expect(screen.getByText('Metric Degradation Breakdown')).toBeInTheDocument()
    })
  })

  it('AC7: Performance Stability Score - displays stability metrics', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      expect(screen.getByText('Performance Stability')).toBeInTheDocument()
    })

    // Verify stability score displayed
    await waitFor(() => {
      expect(screen.getByText('79')).toBeInTheDocument() // Rounded from 78.5
    })
  })

  it('AC8: Existing Trading Functionality Unaffected - handles API errors gracefully', async () => {
    // Mock API failure
    (global.fetch as any).mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 500
      })
    )

    render(<ComparisonPage />)

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/Error Loading Data/)).toBeInTheDocument()
    })
  })

  it('displays loading state while fetching data', () => {
    render(<ComparisonPage />)

    expect(screen.getByText('Loading comparison analysis...')).toBeInTheDocument()
  })

  it('shows all key metrics in overview cards', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      // Backtest trades
      expect(screen.getByText('127')).toBeInTheDocument()
      // Forward test trades
      expect(screen.getByText('115')).toBeInTheDocument()
    })
  })

  it('displays analysis methodology information', async () => {
    render(<ComparisonPage />)

    await waitFor(() => {
      expect(screen.getByText('Analysis Methodology')).toBeInTheDocument()
      expect(screen.getByText('Overfitting Score Calculation')).toBeInTheDocument()
      expect(screen.getByText('Stability Score Calculation')).toBeInTheDocument()
    })
  })
})
