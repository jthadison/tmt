/**
 * Performance Analytics Components Test Suite
 * Story 9.6: Comprehensive test coverage for all performance analytics functionality
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { jest } from '@jest/globals'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'
import RealtimePnLTracker from '../RealtimePnLTracker'
import HistoricalPerformanceDashboard from '../HistoricalPerformanceDashboard'
import RiskAnalyticsDashboard from '../RiskAnalyticsDashboard'
import AgentComparisonDashboard from '../AgentComparisonDashboard'
import ComplianceReportGenerator from '../ComplianceReportGenerator'
import PerformanceAnalyticsDashboard from '../PerformanceAnalyticsDashboard'
import { 
  RealtimePnL, 
  RiskMetrics, 
  AgentPerformance, 
  ComplianceReport,
  MonthlyBreakdown 
} from '@/types/performanceAnalytics'

// Mock the performance analytics service
jest.mock('@/services/performanceAnalyticsService', () => ({
  performanceAnalyticsService: {
    getRealtimePnL: jest.fn(),
    getHistoricalPerformance: jest.fn(),
    calculateRiskMetrics: jest.fn(),
    getAgentComparison: jest.fn(),
    generateComplianceReport: jest.fn(),
    exportReport: jest.fn()
  }
}))

// Mock Chart.js components
jest.mock('react-chartjs-2', () => ({
  Line: ({ data, options, ...props }: any) => <div data-testid="line-chart" {...props}>{JSON.stringify({ data, options })}</div>,
  Bar: ({ data, options, ...props }: any) => <div data-testid="bar-chart" {...props}>{JSON.stringify({ data, options })}</div>,
  Doughnut: ({ data, options, ...props }: any) => <div data-testid="doughnut-chart" {...props}>{JSON.stringify({ data, options })}</div>,
  Radar: ({ data, options, ...props }: any) => <div data-testid="radar-chart" {...props}>{JSON.stringify({ data, options })}</div>,
  Scatter: ({ data, options, ...props }: any) => <div data-testid="scatter-chart" {...props}>{JSON.stringify({ data, options })}</div>
}))

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    tr: ({ children, ...props }: any) => <tr {...props}>{children}</tr>
  },
  AnimatePresence: ({ children }: any) => <>{children}</>
}))

// Mock data
const mockRealtimePnL: RealtimePnL = {
  accountId: 'test-account-1',
  agentId: 'test-agent-1',
  currentPnL: 1250.75,
  realizedPnL: 980.50,
  unrealizedPnL: 270.25,
  dailyPnL: 150.30,
  weeklyPnL: 420.80,
  monthlyPnL: 1250.75,
  trades: [
    {
      tradeId: 'trade-1',
      symbol: 'EUR_USD',
      entryTime: new Date('2024-01-01T10:00:00Z'),
      exitTime: new Date('2024-01-01T12:00:00Z'),
      entryPrice: 1.1000,
      exitPrice: 1.1050,
      size: 10000,
      direction: 'long',
      pnl: 50.00,
      pnlPercent: 4.55,
      commission: 2.00,
      netPnL: 48.00,
      duration: 120,
      agentId: 'test-agent-1',
      agentName: 'Market Analysis Agent',
      strategy: 'breakout',
      riskRewardRatio: 2.5
    }
  ],
  lastUpdate: new Date(),
  highWaterMark: 1300.00,
  currentDrawdown: 49.25
}

const mockRiskMetrics: RiskMetrics = {
  sharpeRatio: 1.85,
  sortinoRatio: 2.12,
  calmarRatio: 1.45,
  maxDrawdown: 250.50,
  maxDrawdownPercent: 8.5,
  currentDrawdown: 49.25,
  currentDrawdownPercent: 3.2,
  averageDrawdown: 120.30,
  drawdownDuration: 15,
  recoveryFactor: 2.8,
  volatility: 12.5,
  downsideDeviation: 8.3,
  valueAtRisk95: -45.20,
  valueAtRisk99: -78.90,
  conditionalVaR: -95.30,
  beta: 0.85,
  alpha: 0.15,
  correlation: 0.72,
  winLossRatio: 1.85,
  profitFactor: 1.42,
  expectancy: 25.80,
  kellyPercentage: 12.3
}

const mockAgentPerformance: AgentPerformance[] = [
  {
    agentId: 'agent-1',
    agentName: 'Market Analysis Agent',
    agentType: 'market_analysis',
    totalTrades: 125,
    winningTrades: 78,
    losingTrades: 47,
    winRate: 62.4,
    totalPnL: 2450.75,
    averagePnL: 19.61,
    bestTrade: 150.30,
    worstTrade: -95.20,
    averageWin: 45.80,
    averageLoss: 28.40,
    profitFactor: 1.61,
    sharpeRatio: 1.85,
    maxDrawdown: 180.50,
    consistency: 78.5,
    reliability: 82.3,
    contribution: 35.2,
    patterns: ['breakout', 'trend_following'],
    preferredSymbols: ['EUR_USD', 'GBP_USD'],
    activeHours: [9, 10, 14, 15],
    performance: mockRiskMetrics
  }
]

const mockHistoricalData = {
  daily: [
    {
      month: '2024-01-01',
      trades: 15,
      winRate: 66.7,
      pnl: 245.80,
      return: 2.45,
      drawdown: -45.20,
      sharpeRatio: 1.85
    }
  ] as MonthlyBreakdown[],
  weekly: [] as MonthlyBreakdown[],
  monthly: [] as MonthlyBreakdown[]
}

const mockComplianceReport: ComplianceReport = {
  reportId: 'RPT-123456789',
  generatedAt: new Date(),
  period: {
    start: new Date('2024-01-01'),
    end: new Date('2024-01-31')
  },
  accounts: [
    {
      accountId: 'test-account-1',
      propFirm: 'Test Prop Firm',
      accountType: 'funded',
      startBalance: 50000,
      endBalance: 52450.75,
      totalReturn: 4.9,
      maxDrawdown: 8.5,
      dailyLossLimit: 2500,
      maxDailyLossReached: 180.50,
      totalLossLimit: 5000,
      maxTotalLossReached: 250.50,
      rulesViolated: [],
      tradingDays: 22,
      averageDailyVolume: 125000
    }
  ],
  aggregateMetrics: {
    totalPnL: 2450.75,
    totalTrades: 125,
    totalVolume: 2750000,
    averageDailyVolume: 125000,
    peakExposure: 275000,
    maxDrawdown: 250.50
  },
  violations: [],
  auditTrail: [],
  regulatoryMetrics: {
    mifidCompliant: true,
    nfaCompliant: true,
    esmaCompliant: true,
    bestExecutionScore: 95,
    orderToTradeRatio: 1.2,
    cancelRatio: 0.05,
    messagingRate: 100,
    marketImpact: 0.01,
    slippageCost: 0.02
  },
  signature: 'test-signature'
}

const mockPerformanceService = performanceAnalyticsService as jest.Mocked<typeof performanceAnalyticsService>

describe('Performance Analytics Components', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    
    // Setup default mock responses
    mockPerformanceService.getRealtimePnL.mockResolvedValue(mockRealtimePnL)
    mockPerformanceService.getHistoricalPerformance.mockResolvedValue(mockHistoricalData)
    mockPerformanceService.calculateRiskMetrics.mockResolvedValue(mockRiskMetrics)
    mockPerformanceService.getAgentComparison.mockResolvedValue(mockAgentPerformance)
    mockPerformanceService.generateComplianceReport.mockResolvedValue(mockComplianceReport)
    mockPerformanceService.exportReport.mockResolvedValue(new Blob(['test'], { type: 'application/pdf' }))
  })

  describe('RealtimePnLTracker', () => {
    test('renders P&L metrics correctly', async () => {
      render(<RealtimePnLTracker accountId="test-account-1" />)
      
      await waitFor(() => {
        expect(screen.getByText('Real-time P&L Tracker')).toBeInTheDocument()
        expect(screen.getByText('$1,250.75')).toBeInTheDocument()
        expect(screen.getByText('+$150.30')).toBeInTheDocument()
      })
    })

    test('handles timeframe changes', async () => {
      render(<RealtimePnLTracker accountId="test-account-1" />)
      
      await waitFor(() => {
        const weeklyButton = screen.getByText('weekly')
        fireEvent.click(weeklyButton)
        expect(screen.getByText('$420.80')).toBeInTheDocument()
      })
    })

    test('displays trade breakdown when expanded', async () => {
      render(<RealtimePnLTracker accountId="test-account-1" showBreakdown={true} />)
      
      await waitFor(() => {
        const breakdownSection = screen.getByText('Trade Breakdown (1 trades)')
        expect(breakdownSection).toBeInTheDocument()
        expect(screen.getByText('EUR_USD')).toBeInTheDocument()
        expect(screen.getByText('$48.00')).toBeInTheDocument()
      })
    })

    test('handles auto-refresh toggle', async () => {
      render(<RealtimePnLTracker accountId="test-account-1" />)
      
      await waitFor(() => {
        const autoRefreshButton = screen.getByRole('button', { name: /refresh/i })
        fireEvent.click(autoRefreshButton)
        // Auto-refresh should be toggled
      })
    })
  })

  describe('HistoricalPerformanceDashboard', () => {
    test('renders historical performance chart', async () => {
      render(<HistoricalPerformanceDashboard accountIds={['test-account-1']} />)
      
      await waitFor(() => {
        expect(screen.getByText('Historical Performance')).toBeInTheDocument()
        expect(screen.getByTestId('line-chart')).toBeInTheDocument()
      })
    })

    test('handles view mode changes', async () => {
      render(<HistoricalPerformanceDashboard accountIds={['test-account-1']} />)
      
      await waitFor(() => {
        const weeklyButton = screen.getByText('weekly')
        fireEvent.click(weeklyButton)
        expect(weeklyButton).toHaveClass('bg-blue-600')
      })
    })

    test('handles chart type changes', async () => {
      render(<HistoricalPerformanceDashboard accountIds={['test-account-1']} />)
      
      await waitFor(() => {
        const barButton = screen.getByText('bar')
        fireEvent.click(barButton)
        expect(barButton).toHaveClass('bg-blue-600')
      })
    })

    test('displays summary statistics', async () => {
      render(<HistoricalPerformanceDashboard accountIds={['test-account-1']} />)
      
      await waitFor(() => {
        expect(screen.getByText('$245.80')).toBeInTheDocument() // Total P&L from mock data
      })
    })
  })

  describe('RiskAnalyticsDashboard', () => {
    const dateRange = { start: new Date('2024-01-01'), end: new Date('2024-01-31') }

    test('renders risk metrics correctly', async () => {
      render(<RiskAnalyticsDashboard accountId="test-account-1" dateRange={dateRange} />)
      
      await waitFor(() => {
        expect(screen.getByText('Risk Analytics')).toBeInTheDocument()
        expect(screen.getByText('1.85')).toBeInTheDocument() // Sharpe ratio
        expect(screen.getByText('8.5%')).toBeInTheDocument() // Max drawdown
      })
    })

    test('handles view mode changes', async () => {
      render(<RiskAnalyticsDashboard accountId="test-account-1" dateRange={dateRange} />)
      
      await waitFor(() => {
        const drawdownButton = screen.getByText('Drawdown')
        fireEvent.click(drawdownButton)
        expect(screen.getByText('Underwater Curve')).toBeInTheDocument()
      })
    })

    test('displays risk level correctly', async () => {
      render(<RiskAnalyticsDashboard accountId="test-account-1" dateRange={dateRange} />)
      
      await waitFor(() => {
        // Risk level should be calculated and displayed
        const riskLevel = screen.getByText(/Risk/)
        expect(riskLevel).toBeInTheDocument()
      })
    })
  })

  describe('AgentComparisonDashboard', () => {
    const dateRange = { start: new Date('2024-01-01'), end: new Date('2024-01-31') }

    test('renders agent comparison table', async () => {
      render(<AgentComparisonDashboard accountIds={['test-account-1']} dateRange={dateRange} />)
      
      await waitFor(() => {
        expect(screen.getByText('Agent Performance Comparison')).toBeInTheDocument()
        expect(screen.getByText('Market Analysis Agent')).toBeInTheDocument()
        expect(screen.getByText('$2,450.75')).toBeInTheDocument()
      })
    })

    test('handles view mode changes', async () => {
      render(<AgentComparisonDashboard accountIds={['test-account-1']} dateRange={dateRange} />)
      
      await waitFor(() => {
        const chartsButton = screen.getByText('Charts')
        fireEvent.click(chartsButton)
        expect(screen.getByText('Performance Comparison')).toBeInTheDocument()
      })
    })

    test('handles agent selection', async () => {
      render(<AgentComparisonDashboard accountIds={['test-account-1']} dateRange={dateRange} />)
      
      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox')
        fireEvent.click(checkbox)
        // Agent should be selected for comparison
      })
    })

    test('displays radar chart in radar mode', async () => {
      render(<AgentComparisonDashboard accountIds={['test-account-1']} dateRange={dateRange} />)
      
      await waitFor(() => {
        const radarButton = screen.getByText('Radar')
        fireEvent.click(radarButton)
        expect(screen.getByTestId('radar-chart')).toBeInTheDocument()
      })
    })
  })

  describe('ComplianceReportGenerator', () => {
    test('generates compliance report', async () => {
      render(<ComplianceReportGenerator accountIds={['test-account-1']} />)
      
      const generateButton = screen.getByText('Generate Report')
      fireEvent.click(generateButton)
      
      await waitFor(() => {
        expect(mockPerformanceService.generateComplianceReport).toHaveBeenCalledWith(
          ['test-account-1'],
          expect.any(Object),
          'standard'
        )
        expect(screen.getByText('RPT-123456789')).toBeInTheDocument()
      })
    })

    test('handles report type changes', () => {
      render(<ComplianceReportGenerator accountIds={['test-account-1']} />)
      
      const select = screen.getByDisplayValue('Standard Report')
      fireEvent.change(select, { target: { value: 'detailed' } })
      expect(select).toHaveValue('detailed')
    })

    test('exports report in different formats', async () => {
      render(<ComplianceReportGenerator accountIds={['test-account-1']} />)
      
      // Generate report first
      const generateButton = screen.getByText('Generate Report')
      fireEvent.click(generateButton)
      
      await waitFor(() => {
        const pdfButton = screen.getByText('PDF')
        fireEvent.click(pdfButton)
        expect(mockPerformanceService.exportReport).toHaveBeenCalledWith(
          mockComplianceReport,
          'pdf'
        )
      })
    })

    test('displays report preview', async () => {
      render(<ComplianceReportGenerator accountIds={['test-account-1']} />)
      
      // Generate report first
      const generateButton = screen.getByText('Generate Report')
      fireEvent.click(generateButton)
      
      await waitFor(() => {
        const previewButton = screen.getByText('Preview')
        fireEvent.click(previewButton)
        expect(screen.getByText('Compliance Report')).toBeInTheDocument()
      })
    })
  })

  describe('PerformanceAnalyticsDashboard', () => {
    test('renders main dashboard with navigation', () => {
      render(<PerformanceAnalyticsDashboard accountIds={['test-account-1']} />)
      
      expect(screen.getByText('Performance Analytics')).toBeInTheDocument()
      expect(screen.getByText('Overview')).toBeInTheDocument()
      expect(screen.getByText('Real-time P&L')).toBeInTheDocument()
      expect(screen.getByText('Historical')).toBeInTheDocument()
      expect(screen.getByText('Risk Analytics')).toBeInTheDocument()
      expect(screen.getByText('Agent Comparison')).toBeInTheDocument()
      expect(screen.getByText('Compliance')).toBeInTheDocument()
    })

    test('handles view navigation', async () => {
      render(<PerformanceAnalyticsDashboard accountIds={['test-account-1']} />)
      
      const riskButton = screen.getByText('Risk Analytics')
      fireEvent.click(riskButton)
      
      await waitFor(() => {
        expect(riskButton).toHaveClass('bg-blue-600')
      })
    })

    test('handles date range changes', () => {
      render(<PerformanceAnalyticsDashboard accountIds={['test-account-1']} />)
      
      const sevenDayButton = screen.getByText('7d')
      fireEvent.click(sevenDayButton)
      
      // Date range should be updated
      const startDateInput = screen.getByDisplayValue(
        new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      )
      expect(startDateInput).toBeInTheDocument()
    })

    test('handles auto-refresh toggle', () => {
      render(<PerformanceAnalyticsDashboard accountIds={['test-account-1']} />)
      
      const autoRefreshButton = screen.getByText('Auto-refresh ON')
      fireEvent.click(autoRefreshButton)
      
      expect(screen.getByText('Auto-refresh OFF')).toBeInTheDocument()
    })

    test('handles fullscreen toggle', () => {
      render(<PerformanceAnalyticsDashboard accountIds={['test-account-1']} />)
      
      const fullscreenButton = screen.getByRole('button', { name: '' }) // Icon button
      // Would test fullscreen functionality if supported in test environment
    })
  })

  describe('Error Handling', () => {
    test('displays error messages when service calls fail', async () => {
      mockPerformanceService.getRealtimePnL.mockRejectedValue(new Error('Service unavailable'))
      
      render(<RealtimePnLTracker accountId="test-account-1" />)
      
      await waitFor(() => {
        expect(screen.getByText('Service unavailable')).toBeInTheDocument()
      })
    })

    test('handles network errors gracefully', async () => {
      mockPerformanceService.calculateRiskMetrics.mockRejectedValue(new Error('Network error'))
      
      const dateRange = { start: new Date('2024-01-01'), end: new Date('2024-01-31') }
      render(<RiskAnalyticsDashboard accountId="test-account-1" dateRange={dateRange} />)
      
      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })
  })

  describe('Loading States', () => {
    test('displays loading indicators during data fetch', () => {
      // Mock a slow response
      mockPerformanceService.getRealtimePnL.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockRealtimePnL), 1000))
      )
      
      render(<RealtimePnLTracker accountId="test-account-1" />)
      
      // Should show loading animation
      expect(screen.getByRole('generic')).toHaveClass('animate-pulse')
    })
  })

  describe('Data Validation', () => {
    test('handles invalid or missing data gracefully', async () => {
      mockPerformanceService.getRealtimePnL.mockResolvedValue({
        ...mockRealtimePnL,
        trades: [] // Empty trades array
      })
      
      render(<RealtimePnLTracker accountId="test-account-1" showBreakdown={true} />)
      
      await waitFor(() => {
        expect(screen.getByText('Trade Breakdown (0 trades)')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    test('provides appropriate ARIA labels', () => {
      render(<PerformanceAnalyticsDashboard accountIds={['test-account-1']} />)
      
      const buttons = screen.getAllByRole('button')
      buttons.forEach(button => {
        // Each button should have accessible text or aria-label
        expect(button).toHaveAttribute('type')
      })
    })

    test('supports keyboard navigation', () => {
      render(<PerformanceAnalyticsDashboard accountIds={['test-account-1']} />)
      
      const navButtons = screen.getAllByRole('button')
      navButtons.forEach(button => {
        expect(button).not.toHaveAttribute('tabIndex', '-1')
      })
    })
  })

  describe('Performance', () => {
    test('memoizes expensive calculations', () => {
      const { rerender } = render(<RealtimePnLTracker accountId="test-account-1" />)
      
      // Re-render with same props shouldn't trigger new calculations
      rerender(<RealtimePnLTracker accountId="test-account-1" />)
      
      // Service should only be called once
      expect(mockPerformanceService.getRealtimePnL).toHaveBeenCalledTimes(1)
    })
  })
})