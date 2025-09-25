import { render, screen, fireEvent } from '@testing-library/react'
import SessionOverviewDashboard from '@/components/session-monitoring/SessionOverviewDashboard'
import { renderWithProviders } from '@/__tests__/testUtils'

// Mock session data for testing
const mockSessionData = [
  {
    session: 'sydney' as const,
    name: 'Sydney Session',
    timezone: 'AEDT (UTC+11)',
    hours: '22:00-07:00 GMT',
    status: 'inactive' as const,
    metrics: {
      winRate: 65.2,
      avgRiskReward: 2.8,
      totalTrades: 45,
      profitFactor: 1.45,
      maxDrawdown: -4.2,
      confidenceThreshold: 78,
      positionSizeReduction: 35,
      currentPhase: 2,
      capitalAllocation: 25
    },
    positionSizing: {
      stabilityFactor: 0.45,
      validationFactor: 0.25,
      volatilityFactor: 0.85,
      totalReduction: 0.35,
      maxPosition: 2.5,
      currentRisk: 0.75
    }
  },
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

describe('SessionOverviewDashboard', () => {
  const mockOnSessionSelect = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders all session cards with correct data', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    expect(screen.getAllByText('Sydney Session')).toHaveLength(2) // One in card, one in summary
    expect(screen.getAllByText('London Session')).toHaveLength(1) // Only in summary since it's current
    expect(screen.getByText('22:00-07:00 GMT')).toBeInTheDocument()
    expect(screen.getByText('07:00-16:00 GMT')).toBeInTheDocument()
  })

  it('displays correct status indicators', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    // Check for status indicators (emojis)
    expect(screen.getByText('🟢')).toBeInTheDocument() // Active session
    expect(screen.getByText('⚫')).toBeInTheDocument() // Inactive session
  })

  it('highlights current session with ring border', () => {
    const { container } = renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    // Find the card containing London session and check for ring classes
    const cards = container.querySelectorAll('.ring-2.ring-blue-500')
    expect(cards.length).toBeGreaterThan(0)
  })

  it('calls onSessionSelect when session card is clicked', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    const sydneyCard = screen.getAllByText('Sydney Session')[0].closest('div')
    fireEvent.click(sydneyCard!)

    expect(mockOnSessionSelect).toHaveBeenCalledWith('sydney')
  })

  it('displays performance metrics correctly', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    // Check win rates
    expect(screen.getByText('65.2%')).toBeInTheDocument()
    expect(screen.getByText('72.1%')).toBeInTheDocument()

    // Check profit factors
    expect(screen.getByText('1.45')).toBeInTheDocument()
    expect(screen.getByText('1.85')).toBeInTheDocument()

    // Check trades count
    expect(screen.getByText('45')).toBeInTheDocument()
    expect(screen.getByText('62')).toBeInTheDocument()
  })

  it('displays position sizing reductions correctly', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    expect(screen.getByText('35%')).toBeInTheDocument() // Sydney reduction
    expect(screen.getByText('28%')).toBeInTheDocument() // London reduction
  })

  it('shows correct color coding for performance metrics', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    // Win rates with color coding
    const sydneyWinRate = screen.getByText('65.2%')
    const londonWinRate = screen.getByText('72.1%')

    expect(sydneyWinRate).toHaveClass('text-yellow-400') // 60-70% range
    expect(londonWinRate).toHaveClass('text-green-400')  // >70% range
  })

  it('displays summary statistics correctly', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    // Best performing session (London with 1.85 profit factor)
    expect(screen.getByText('Best Performing Session')).toBeInTheDocument()
    expect(screen.getByText('Profit Factor: 1.85')).toBeInTheDocument()

    // Most conservative session (Sydney with 35% reduction)
    expect(screen.getByText('Most Conservative Session')).toBeInTheDocument()
    expect(screen.getByText('Size Reduction: 35%')).toBeInTheDocument()

    // Total trades (45 + 62 = 107)
    expect(screen.getByText('107')).toBeInTheDocument()
  })

  it('renders 24-hour timeline correctly', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    expect(screen.getByText('24-Hour Session Timeline')).toBeInTheDocument()
    expect(screen.getByText('Sydney')).toBeInTheDocument()
    expect(screen.getByText('Tokyo')).toBeInTheDocument()
    expect(screen.getByText('London')).toBeInTheDocument()
    expect(screen.getByText('New York')).toBeInTheDocument()

    // Timeline hours
    expect(screen.getByText('22:00-07:00')).toBeInTheDocument()
    expect(screen.getByText('00:00-09:00')).toBeInTheDocument()
    expect(screen.getByText('07:00-16:00')).toBeInTheDocument()
    expect(screen.getByText('13:00-22:00')).toBeInTheDocument()
  })

  it('displays current time indicator', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    expect(screen.getByText('NOW')).toBeInTheDocument()
  })

  it('shows overlap indicators and legend', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    expect(screen.getByText('🟢 Active Session')).toBeInTheDocument()
    expect(screen.getByText('🟡 Upcoming Session')).toBeInTheDocument()
    expect(screen.getByText('⚫ Inactive Session')).toBeInTheDocument()
    expect(screen.getByText('📊 High Volume Overlaps: 13:00-16:00, 00:00-02:00 GMT')).toBeInTheDocument()
  })

  it('handles empty session data gracefully', () => {
    renderWithProviders(
      <SessionOverviewDashboard
        sessionData={[]}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    // Should still render the structure but with no session cards
    expect(screen.getByText('24-Hour Session Timeline')).toBeInTheDocument()
    expect(screen.getByText('Total Trades Today')).toBeInTheDocument()
    // Total trades should be 0 when no session data
    const totalTradesElement = screen.getByText('0')
    expect(totalTradesElement).toBeInTheDocument()
  })

  it('applies correct hover effects and cursor styles', () => {
    const { container } = renderWithProviders(
      <SessionOverviewDashboard
        sessionData={mockSessionData}
        currentSession="london"
        onSessionSelect={mockOnSessionSelect}
      />
    )

    const sessionCards = container.querySelectorAll('[role="button"]')
    sessionCards.forEach(card => {
      expect(card).toHaveClass('cursor-pointer', 'transition-all', 'hover:scale-105')
    })
  })
})