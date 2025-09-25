import { render, screen, fireEvent } from '@testing-library/react'
import SessionPerformanceMetrics from '@/components/session-monitoring/SessionPerformanceMetrics'
import { renderWithProviders } from '@/__tests__/testUtils'

const mockSessionData = [
  {
    session: 'london' as const,
    name: 'London Session',
    timezone: 'GMT (UTC+0)',
    hours: '07:00-16:00 GMT',
    status: 'active' as const,
    metrics: {
      winRate: 72.1,
      avgRiskReward: 3.2,
      totalTrades: 62,
      profitFactor: 1.85,
      maxDrawdown: -2.8,
      confidenceThreshold: 72,
      positionSizeReduction: 28,
      currentPhase: 3,
      capitalAllocation: 50
    },
    recentTrades: [
      {
        type: 'BUY',
        pair: 'EUR/USD',
        size: 10000,
        time: '14:30',
        pnl: 125.50
      },
      {
        type: 'SELL',
        pair: 'GBP/USD',
        size: 8500,
        time: '13:45',
        pnl: -45.25
      }
    ],
    positionSizing: {
      stabilityFactor: 0.55,
      validationFactor: 0.35,
      volatilityFactor: 0.95,
      totalReduction: 0.28,
      maxPosition: 4.0,
      currentRisk: 1.2
    }
  }
]

describe('SessionPerformanceMetrics', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders session performance data correctly', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    expect(screen.getByText('London Session Performance Metrics')).toBeInTheDocument()
    expect(screen.getByText('72.1%')).toBeInTheDocument() // Win rate
    expect(screen.getByText('1.85')).toBeInTheDocument() // Profit factor
    expect(screen.getByText('-2.8%')).toBeInTheDocument() // Max drawdown
    expect(screen.getByText('-28%')).toBeInTheDocument() // Position reduction
  })

  it('renders timeframe selector buttons', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    expect(screen.getByText('1D')).toBeInTheDocument()
    expect(screen.getByText('1W')).toBeInTheDocument()
    expect(screen.getByText('1M')).toBeInTheDocument()
    expect(screen.getByText('3M')).toBeInTheDocument()
  })

  it('changes timeframe when button is clicked', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    const monthButton = screen.getByText('1M')
    fireEvent.click(monthButton)

    // Check if the button becomes active (has blue background)
    expect(monthButton).toHaveClass('bg-blue-600', 'text-white')
  })

  it('displays key performance metrics with correct colors', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    const winRate = screen.getByText('72.1%')
    const profitFactor = screen.getByText('1.85')

    // Win rate > 70% should be green
    expect(winRate).toHaveClass('text-green-400')
    // Profit factor > 1.5 should be green
    expect(profitFactor).toHaveClass('text-green-400')
  })

  it('shows session requirements and status correctly', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    expect(screen.getByText('Session Requirements & Status')).toBeInTheDocument()
    expect(screen.getByText('Confidence Threshold')).toBeInTheDocument()
    expect(screen.getByText('72%')).toBeInTheDocument() // Confidence threshold
    expect(screen.getByText('MET')).toBeInTheDocument() // Should meet threshold

    expect(screen.getByText('Risk-Reward Target')).toBeInTheDocument()
    expect(screen.getByText('3.2:1')).toBeInTheDocument() // R:R ratio
  })

  it('displays position sizing information', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    expect(screen.getByText('Max Position Size')).toBeInTheDocument()
    expect(screen.getByText('4%')).toBeInTheDocument() // Max position
    expect(screen.getByText('Capital Allocation')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument() // Capital allocation
    expect(screen.getByText('Current Risk')).toBeInTheDocument()
    expect(screen.getByText('1.2%')).toBeInTheDocument() // Current risk
  })

  it('renders profit factor trend chart', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    expect(screen.getByText('Profit Factor Trend')).toBeInTheDocument()
    expect(screen.getByText('1w timeframe • 8 data points')).toBeInTheDocument()

    // Chart scale indicators
    expect(screen.getByText('PF: 0.5')).toBeInTheDocument()
    expect(screen.getByText('1.0')).toBeInTheDocument()
    expect(screen.getByText('1.5')).toBeInTheDocument()
    expect(screen.getByText('2.0+')).toBeInTheDocument()
  })

  it('displays recent trades when available', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    expect(screen.getByText('Recent Trades')).toBeInTheDocument()
    expect(screen.getByText('BUY')).toBeInTheDocument()
    expect(screen.getByText('SELL')).toBeInTheDocument()
    expect(screen.getByText('EUR/USD')).toBeInTheDocument()
    expect(screen.getByText('GBP/USD')).toBeInTheDocument()
    expect(screen.getByText('+$125.50')).toBeInTheDocument()
    expect(screen.getByText('-$45.25')).toBeInTheDocument()
  })

  it('applies correct color coding for trade PnL', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    const profitTrade = screen.getByText('+$125.50')
    const lossTrade = screen.getByText('-$45.25')

    expect(profitTrade).toHaveClass('text-green-400')
    expect(lossTrade).toHaveClass('text-red-400')
  })

  it('shows confidence threshold status correctly', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    // Win rate (72.1%) meets confidence threshold (72%)
    const metStatus = screen.getByText('MET')
    expect(metStatus).toHaveClass('bg-green-500/20', 'text-green-400')
  })

  it('displays risk-reward assessment', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    // R:R of 3.2 should be "GOOD" (>= 2.5)
    const rrStatus = screen.getByText('GOOD')
    expect(rrStatus).toHaveClass('bg-green-500/20', 'text-green-400')
  })

  it('handles missing session gracefully', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="tokyo" // Session not in data
      />
    )

    // Component should not render when session is not found
    expect(screen.queryByText('Tokyo Session Performance Metrics')).not.toBeInTheDocument()
  })

  it('handles session without recent trades', () => {
    const sessionWithoutTrades = [{
      ...mockSessionData[0],
      recentTrades: []
    }]

    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={sessionWithoutTrades}
        selectedSession="london"
      />
    )

    // Recent trades section should not appear
    expect(screen.queryByText('Recent Trades')).not.toBeInTheDocument()
  })

  it('shows correct phase information', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    expect(screen.getByText('Phase 3')).toBeInTheDocument()
    expect(screen.getByText('62 trades total')).toBeInTheDocument()
  })

  it('generates chart data based on timeframe selection', () => {
    renderWithProviders(
      <SessionPerformanceMetrics
        sessionData={mockSessionData}
        selectedSession="london"
      />
    )

    // Default 1W should show 8 data points (7 days + current)
    expect(screen.getByText('1w timeframe • 8 data points')).toBeInTheDocument()

    // Switch to 1M
    const monthButton = screen.getByText('1M')
    fireEvent.click(monthButton)

    // Should now show 31 data points (30 days + current)
    expect(screen.getByText('1m timeframe • 31 data points')).toBeInTheDocument()
  })
})