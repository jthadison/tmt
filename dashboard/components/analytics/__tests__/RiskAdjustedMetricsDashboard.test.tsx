import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { RiskAdjustedMetricsDashboard } from '../RiskAdjustedMetricsDashboard'
import { RiskMetrics } from '@/types/analytics'

// Mock fetch
global.fetch = jest.fn()

const mockRiskMetrics: RiskMetrics = {
  sharpeRatio: 1.42,
  sortinoRatio: 1.85,
  calmarRatio: 4.2,
  drawdown: {
    max: -18500,
    maxPercent: -18.5,
    avg: -4200,
    avgPercent: -4.2,
    current: -2300,
    currentPercent: -2.3,
    avgRecoveryDays: 12,
    maxRecoveryDays: 45,
    distribution: [
      { bucket: '0-5%', count: 45, percentage: 60 },
      { bucket: '5-10%', count: 20, percentage: 27 },
      { bucket: '10-15%', count: 8, percentage: 11 },
      { bucket: '15-20%', count: 2, percentage: 2 },
      { bucket: '>20%', count: 0, percentage: 0 }
    ]
  },
  volatility: {
    daily: 0.018,
    monthly: 0.083,
    trend: 'stable'
  },
  riskReward: {
    avgRRRatio: 2.8,
    winRate: 62.5,
    expectancy: 185.5,
    profitFactor: 2.35
  }
}

describe('RiskAdjustedMetricsDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('displays all risk metric sections', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockRiskMetrics
    })

    render(<RiskAdjustedMetricsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Risk-Adjusted Returns')).toBeInTheDocument()
      expect(screen.getByText('Drawdown Analysis')).toBeInTheDocument()
      expect(screen.getByText('Volatility Analysis')).toBeInTheDocument()
      expect(screen.getByText('Risk/Reward Profile')).toBeInTheDocument()
    })
  })

  test('displays Sharpe, Sortino, and Calmar ratios', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockRiskMetrics
    })

    render(<RiskAdjustedMetricsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument()
      expect(screen.getByText('Sortino Ratio')).toBeInTheDocument()
      expect(screen.getByText('Calmar Ratio')).toBeInTheDocument()
      expect(screen.getByText('1.42')).toBeInTheDocument()
      expect(screen.getByText('1.85')).toBeInTheDocument()
      expect(screen.getByText('4.20')).toBeInTheDocument()
    })
  })

  test('displays drawdown metrics', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockRiskMetrics
    })

    render(<RiskAdjustedMetricsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Max Drawdown')).toBeInTheDocument()
      expect(screen.getByText('Avg Drawdown')).toBeInTheDocument()
      expect(screen.getByText('Recovery Time')).toBeInTheDocument()
      expect(screen.getByText('Current Drawdown')).toBeInTheDocument()
    })
  })

  test('displays volatility metrics', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockRiskMetrics
    })

    render(<RiskAdjustedMetricsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Daily Volatility')).toBeInTheDocument()
      expect(screen.getByText('Monthly Volatility')).toBeInTheDocument()
      expect(screen.getByText('Volatility Trend')).toBeInTheDocument()
      expect(screen.getByText('1.80%')).toBeInTheDocument()
    })
  })

  test('displays risk/reward profile', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockRiskMetrics
    })

    render(<RiskAdjustedMetricsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Avg R:R Ratio')).toBeInTheDocument()
      expect(screen.getByText('Win Ratio')).toBeInTheDocument()
      expect(screen.getByText('Expectancy')).toBeInTheDocument()
      expect(screen.getByText('Profit Factor')).toBeInTheDocument()
    })
  })

  test('shows loading state initially', () => {
    ;(global.fetch as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(<RiskAdjustedMetricsDashboard />)

    const container = document.querySelector('.risk-metrics-dashboard')
    expect(container?.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  test('displays error state on fetch failure', async () => {
    ;(global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'))

    render(<RiskAdjustedMetricsDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/Error loading risk metrics/)).toBeInTheDocument()
    })
  })
})
