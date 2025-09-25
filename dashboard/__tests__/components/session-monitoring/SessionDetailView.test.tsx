import { render, screen, fireEvent } from '@testing-library/react'
import SessionDetailView from '@/components/session-monitoring/SessionDetailView'
import { renderWithProviders } from '@/__tests__/testUtils'

const mockSessionData = {
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
      id: '1',
      type: 'BUY',
      pair: 'EUR/USD',
      size: 10000,
      time: '14:30',
      pnl: 125.50,
      entry: 1.0850,
      exit: 1.0875,
      duration: '2h 15m'
    },
    {
      id: '2',
      type: 'SELL',
      pair: 'GBP/USD',
      size: 8500,
      time: '13:45',
      pnl: -45.25,
      entry: 1.2650,
      exit: 1.2665,
      duration: '45m'
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

const mockForwardTestMetrics = {
  walkForwardStability: 34.4,
  outOfSampleValidation: 17.4,
  overfittingScore: 0.634,
  kurtosisExposure: 20.316,
  monthsOfData: 6
}

describe('SessionDetailView', () => {
  const mockOnClose = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders session detail view with correct session info', () => {
    renderWithProviders(
      <SessionDetailView
        session={mockSessionData}
        onClose={mockOnClose}
      />
    )

    expect(screen.getByText('London Session')).toBeInTheDocument()
    expect(screen.getByText('GMT (UTC+0)')).toBeInTheDocument()
    expect(screen.getByText('07:00-16:00 GMT')).toBeInTheDocument()
    expect(screen.getByText('active')).toBeInTheDocument()
  })

  it('displays navigation tabs correctly', () => {
    renderWithProviders(
      <SessionDetailView
        session={mockSessionData}
        onClose={mockOnClose}
      />
    )

    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Recent Trades')).toBeInTheDocument()
    expect(screen.getByText('Risk Controls')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('switches tabs when clicked', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    // Click on Recent Trades tab
    const tradesTab = screen.getByText('Recent Trades')
    fireEvent.click(tradesTab)

    // Tab should become active
    expect(tradesTab).toHaveClass('border-blue-500', 'text-blue-400')

    // Should show trades content
    expect(screen.getByText('Trade History')).toBeInTheDocument()
    expect(screen.getByText('EUR/USD')).toBeInTheDocument()
    expect(screen.getByText('GBP/USD')).toBeInTheDocument()
  })

  it('displays overview tab content by default', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    // Overview content should be visible
    expect(screen.getByText('Session Performance Summary')).toBeInTheDocument()
    expect(screen.getByText('Win Rate')).toBeInTheDocument()
    expect(screen.getByText('72.1%')).toBeInTheDocument()
    expect(screen.getByText('Profit Factor')).toBeInTheDocument()
    expect(screen.getByText('1.85')).toBeInTheDocument()
  })

  it('shows recent trades in trades tab', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const tradesTab = screen.getByText('Recent Trades')
    fireEvent.click(tradesTab)

    expect(screen.getByText('Trade History')).toBeInTheDocument()
    expect(screen.getByText('BUY')).toBeInTheDocument()
    expect(screen.getByText('SELL')).toBeInTheDocument()
    expect(screen.getByText('+$125.50')).toBeInTheDocument()
    expect(screen.getByText('-$45.25')).toBeInTheDocument()
    expect(screen.getByText('1.0850')).toBeInTheDocument() // Entry price
    expect(screen.getByText('1.0875')).toBeInTheDocument() // Exit price
  })

  it('displays risk controls in risk tab', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const riskTab = screen.getByText('Risk Controls')
    fireEvent.click(riskTab)

    expect(screen.getByText('Position Sizing Controls')).toBeInTheDocument()
    expect(screen.getByText('Forward Test Adjustments')).toBeInTheDocument()
    expect(screen.getByText('Emergency Controls')).toBeInTheDocument()
  })

  it('shows settings in settings tab', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const settingsTab = screen.getByText('Settings')
    fireEvent.click(settingsTab)

    expect(screen.getByText('Session Configuration')).toBeInTheDocument()
    expect(screen.getByText('Trading Parameters')).toBeInTheDocument()
    expect(screen.getByText('Confidence Threshold')).toBeInTheDocument()
    expect(screen.getByText('Risk Per Trade')).toBeInTheDocument()
  })

  it('displays session status with correct styling', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const activeStatus = screen.getByText('🟢 Active')
    expect(activeStatus).toHaveClass('bg-green-500/20', 'text-green-400')
  })

  it('shows performance metrics in overview', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    // Performance metrics grid
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument()
    expect(screen.getByText('-2.8%')).toBeInTheDocument()
    expect(screen.getByText('Total Trades')).toBeInTheDocument()
    expect(screen.getByText('62')).toBeInTheDocument()
    expect(screen.getByText('Avg Risk:Reward')).toBeInTheDocument()
    expect(screen.getByText('3.2:1')).toBeInTheDocument()
  })

  it('displays current phase information', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    expect(screen.getByText('Current Phase')).toBeInTheDocument()
    expect(screen.getByText('Phase 3')).toBeInTheDocument()
    expect(screen.getByText('50% Capital Allocation')).toBeInTheDocument()
  })

  it('shows trade details correctly', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const tradesTab = screen.getByText('Recent Trades')
    fireEvent.click(tradesTab)

    // Trade details
    expect(screen.getByText('10,000')).toBeInTheDocument() // EUR/USD size
    expect(screen.getByText('8,500')).toBeInTheDocument()  // GBP/USD size
    expect(screen.getByText('14:30')).toBeInTheDocument()  // Trade time
    expect(screen.getByText('13:45')).toBeInTheDocument()  // Trade time
    expect(screen.getByText('2h 15m')).toBeInTheDocument() // Duration
    expect(screen.getByText('45m')).toBeInTheDocument()    // Duration
  })

  it('applies correct color coding for trade PnL', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const tradesTab = screen.getByText('Recent Trades')
    fireEvent.click(tradesTab)

    const profitTrade = screen.getByText('+$125.50')
    const lossTrade = screen.getByText('-$45.25')

    expect(profitTrade).toHaveClass('text-green-400')
    expect(lossTrade).toHaveClass('text-red-400')
  })

  it('shows trade type badges with correct styling', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const tradesTab = screen.getByText('Recent Trades')
    fireEvent.click(tradesTab)

    const buyBadge = screen.getByText('BUY')
    const sellBadge = screen.getByText('SELL')

    expect(buyBadge).toHaveClass('bg-green-500/20', 'text-green-400')
    expect(sellBadge).toHaveClass('bg-red-500/20', 'text-red-400')
  })

  it('displays risk controls information', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const riskTab = screen.getByText('Risk Controls')
    fireEvent.click(riskTab)

    expect(screen.getByText('Max Position Size')).toBeInTheDocument()
    expect(screen.getByText('4.0%')).toBeInTheDocument()
    expect(screen.getByText('Current Risk')).toBeInTheDocument()
    expect(screen.getByText('1.2%')).toBeInTheDocument()
    expect(screen.getByText('Position Reduction')).toBeInTheDocument()
    expect(screen.getByText('28%')).toBeInTheDocument()
  })

  it('shows forward test integration', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const riskTab = screen.getByText('Risk Controls')
    fireEvent.click(riskTab)

    expect(screen.getByText('Walk-Forward Stability')).toBeInTheDocument()
    expect(screen.getByText('34.4')).toBeInTheDocument()
    expect(screen.getByText('Out-of-Sample Validation')).toBeInTheDocument()
    expect(screen.getByText('17.4')).toBeInTheDocument()
  })

  it('displays session settings configuration', () => {
    renderWithProviders(
      <SessionDetailView
        sessionData={mockSessionData}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const settingsTab = screen.getByText('Settings')
    fireEvent.click(settingsTab)

    expect(screen.getByText('Session Hours')).toBeInTheDocument()
    expect(screen.getByText('07:00-16:00 GMT')).toBeInTheDocument()
    expect(screen.getByText('Timezone')).toBeInTheDocument()
    expect(screen.getByText('GMT (UTC+0)')).toBeInTheDocument()
  })

  it('handles session without trades gracefully', () => {
    const sessionWithoutTrades = {
      ...mockSessionData,
      recentTrades: []
    }

    renderWithProviders(
      <SessionDetailView
        sessionData={sessionWithoutTrades}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const tradesTab = screen.getByText('Recent Trades')
    fireEvent.click(tradesTab)

    expect(screen.getByText('No recent trades available')).toBeInTheDocument()
  })

  it('shows inactive session status correctly', () => {
    const inactiveSession = {
      ...mockSessionData,
      status: 'inactive' as const
    }

    renderWithProviders(
      <SessionDetailView
        sessionData={inactiveSession}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const inactiveStatus = screen.getByText('⚫ Inactive')
    expect(inactiveStatus).toHaveClass('bg-gray-500/20', 'text-gray-400')
  })

  it('displays upcoming session status correctly', () => {
    const upcomingSession = {
      ...mockSessionData,
      status: 'upcoming' as const
    }

    renderWithProviders(
      <SessionDetailView
        sessionData={upcomingSession}
        forwardTestMetrics={mockForwardTestMetrics}
      />
    )

    const upcomingStatus = screen.getByText('🟡 Upcoming')
    expect(upcomingStatus).toHaveClass('bg-yellow-500/20', 'text-yellow-400')
  })
})