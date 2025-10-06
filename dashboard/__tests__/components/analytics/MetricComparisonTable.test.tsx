import { render, screen } from '@testing-library/react'
import { MetricComparisonTable } from '@/components/analytics/MetricComparisonTable'
import { BacktestResults } from '@/app/api/analytics/backtest-results/route'
import { ForwardTestResults } from '@/app/api/analytics/forward-test-performance/route'

describe('MetricComparisonTable', () => {
  const mockBacktest: BacktestResults = {
    strategyName: 'Test Strategy',
    testPeriod: {
      startDate: '2025-01-01',
      endDate: '2025-03-31',
      totalDays: 90
    },
    metrics: {
      winRate: 70,
      avgWin: 145.30,
      avgLoss: 82.50,
      profitFactor: 2.4,
      maxDrawdown: 500,
      maxDrawdownPercent: 5,
      sharpeRatio: 1.8,
      totalTrades: 100,
      totalProfit: 6280
    },
    parsedAt: Date.now(),
    sourceFile: 'backtest_2025.json'
  }

  const mockForward: ForwardTestResults = {
    testPeriod: {
      startDate: '2025-04-01',
      endDate: '2025-06-30',
      totalDays: 90
    },
    metrics: {
      winRate: 62,
      avgWin: 138.20,
      avgLoss: 85.30,
      profitFactor: 2.1,
      maxDrawdown: 620,
      maxDrawdownPercent: 6.2,
      sharpeRatio: 1.5,
      totalTrades: 95,
      totalProfit: 5010
    },
    dailyReturns: [],
    calculatedAt: Date.now()
  }

  it('renders the comparison table', () => {
    render(<MetricComparisonTable backtest={mockBacktest} forwardTest={mockForward} />)

    expect(screen.getByText('Performance Metrics Comparison')).toBeInTheDocument()
    expect(screen.getByText('Backtest vs. Forward Test Performance Analysis')).toBeInTheDocument()
  })

  it('displays all metrics correctly', () => {
    render(<MetricComparisonTable backtest={mockBacktest} forwardTest={mockForward} />)

    expect(screen.getByText('Win Rate')).toBeInTheDocument()
    expect(screen.getByText('Avg Win')).toBeInTheDocument()
    expect(screen.getByText('Avg Loss')).toBeInTheDocument()
    expect(screen.getByText('Profit Factor')).toBeInTheDocument()
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument()
    expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument()
  })

  it('calculates variance correctly', () => {
    render(<MetricComparisonTable backtest={mockBacktest} forwardTest={mockForward} />)

    // Win rate degraded from 70 to 62 = -11.4%
    expect(screen.getByText(/-11\.4%/)).toBeInTheDocument()
  })

  it('shows correct status indicators', () => {
    render(<MetricComparisonTable backtest={mockBacktest} forwardTest={mockForward} />)

    // Should have at least one warning status (✓, ⚠, or ✗)
    const statusIcons = screen.getAllByText(/[✓⚠✗]/)
    expect(statusIcons.length).toBeGreaterThan(0)
  })

  it('formats values with correct units', () => {
    render(<MetricComparisonTable backtest={mockBacktest} forwardTest={mockForward} />)

    // Win rate should have %
    expect(screen.getByText('70.0%')).toBeInTheDocument()
    expect(screen.getByText('62.0%')).toBeInTheDocument()

    // Avg win should have $
    expect(screen.getByText('$145.30')).toBeInTheDocument()
    expect(screen.getByText('$138.20')).toBeInTheDocument()
  })

  it('shows legend with variance thresholds', () => {
    render(<MetricComparisonTable backtest={mockBacktest} forwardTest={mockForward} />)

    expect(screen.getByText(/<15% variance \(Good\)/)).toBeInTheDocument()
    expect(screen.getByText(/15-30% variance \(Warning\)/)).toBeInTheDocument()
    expect(screen.getByText(/>30% variance \(Poor\)/)).toBeInTheDocument()
  })

  it('handles zero backtest values gracefully', () => {
    const zeroBacktest = {
      ...mockBacktest,
      metrics: { ...mockBacktest.metrics, profitFactor: 0 }
    }

    render(<MetricComparisonTable backtest={zeroBacktest} forwardTest={mockForward} />)

    // Should render without crashing
    expect(screen.getByText('Profit Factor')).toBeInTheDocument()
  })
})
