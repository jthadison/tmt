import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { CriticalErrorState } from '@/components/errors/CriticalErrorState'

describe('CriticalErrorState', () => {
  const mockOnRetry = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it('displays full-page error with all 4-part message components', () => {
    render(
      <CriticalErrorState
        title="Connection Lost"
        description="Unable to connect to trading system"
        impact="Live signals unavailable"
        onRetry={mockOnRetry}
        autoRetrySeconds={15}
      />
    )

    // Should be full-page (check the outer container)
    const container = screen.getByText('Connection Lost').closest('.min-h-screen')
    expect(container).toBeInTheDocument()

    // 1. What Happened
    expect(screen.getByText('Connection Lost')).toBeInTheDocument()

    // 2. Description
    expect(screen.getByText(/unable to connect to trading system/i)).toBeInTheDocument()

    // 3. Why It Matters (Impact)
    expect(screen.getByText(/live signals unavailable/i)).toBeInTheDocument()

    // 4. Recovery Options
    expect(screen.getByRole('button', { name: /retry now/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /contact support/i })).toBeInTheDocument()
  })

  it('shows countdown timer', () => {
    render(
      <CriticalErrorState
        title="Connection Lost"
        description="Unable to connect"
        impact="Services unavailable"
        onRetry={mockOnRetry}
        autoRetrySeconds={15}
      />
    )

    expect(screen.getByText(/reconnecting automatically in 15 seconds/i)).toBeInTheDocument()
  })

  it('updates countdown every second', () => {
    render(
      <CriticalErrorState
        title="Connection Lost"
        description="Unable to connect"
        impact="Services unavailable"
        onRetry={mockOnRetry}
        autoRetrySeconds={10}
      />
    )

    expect(screen.getByText(/reconnecting automatically in 10 seconds/i)).toBeInTheDocument()

    act(() => {
      jest.advanceTimersByTime(1000)
    })
    expect(screen.getByText(/reconnecting automatically in 9 seconds/i)).toBeInTheDocument()

    act(() => {
      jest.advanceTimersByTime(1000)
    })
    expect(screen.getByText(/reconnecting automatically in 8 seconds/i)).toBeInTheDocument()
  })

  it('displays progress bar', () => {
    const { container } = render(
      <CriticalErrorState
        title="Connection Lost"
        description="Unable to connect"
        impact="Services unavailable"
        onRetry={mockOnRetry}
        autoRetrySeconds={15}
      />
    )

    const progressBar = container.querySelector('.bg-blue-600')
    expect(progressBar).toBeInTheDocument()
  })

  it('triggers retry immediately when Retry Now button is clicked', () => {
    render(
      <CriticalErrorState
        title="Connection Lost"
        description="Unable to connect"
        impact="Services unavailable"
        onRetry={mockOnRetry}
        autoRetrySeconds={15}
      />
    )

    const retryButton = screen.getByRole('button', { name: /retry now/i })
    fireEvent.click(retryButton)

    expect(mockOnRetry).toHaveBeenCalledTimes(1)
  })

  it('has contact support link with correct href', () => {
    render(
      <CriticalErrorState
        title="Connection Lost"
        description="Unable to connect"
        impact="Services unavailable"
        onRetry={mockOnRetry}
        supportLink="/help"
      />
    )

    const supportLink = screen.getByRole('link', { name: /contact support/i })
    expect(supportLink).toHaveAttribute('href', '/help')
  })

  it('uses default support link when not provided', () => {
    render(
      <CriticalErrorState
        title="Connection Lost"
        description="Unable to connect"
        impact="Services unavailable"
        onRetry={mockOnRetry}
      />
    )

    const supportLink = screen.getByRole('link', { name: /contact support/i })
    expect(supportLink).toHaveAttribute('href', '/support')
  })

  it('has AlertOctagon icon', () => {
    const { container } = render(
      <CriticalErrorState
        title="Connection Lost"
        description="Unable to connect"
        impact="Services unavailable"
        onRetry={mockOnRetry}
      />
    )

    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })
})
