import { render, screen, fireEvent } from '@testing-library/react'
import ErrorBoundary from '@/components/ui/ErrorBoundary'

// Component that throws an error
function BrokenComponent() {
  throw new Error('Component crashed')
}

// Working component
function WorkingComponent() {
  return <div>Working component</div>
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress console.error for cleaner test output
    jest.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <WorkingComponent />
      </ErrorBoundary>
    )

    expect(screen.getByText('Working component')).toBeInTheDocument()
  })

  it('catches React errors and displays error state', () => {
    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>
    )

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
  })

  it('displays 4-part error message', () => {
    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>
    )

    // 1. What Happened
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

    // 2. Description
    expect(screen.getByText(/unexpected error occurred/i)).toBeInTheDocument()

    // 3. Impact
    expect(screen.getByText(/impact:/i)).toBeInTheDocument()

    // 4. Recovery Options
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reload page/i })).toBeInTheDocument()
  })

  it('calls onError callback when error is caught', () => {
    const onError = jest.fn()

    render(
      <ErrorBoundary onError={onError}>
        <BrokenComponent />
      </ErrorBoundary>
    )

    expect(onError).toHaveBeenCalled()
    const [error, errorInfo] = onError.mock.calls[0]
    expect(error).toBeInstanceOf(Error)
    expect(error.message).toBe('Component crashed')
    expect(errorInfo).toHaveProperty('componentStack')
  })

  it('resets error state when Try Again is clicked', () => {
    let shouldThrow = true

    function ConditionallyBrokenComponent() {
      if (shouldThrow) {
        throw new Error('Component crashed')
      }
      return <div>Fixed component</div>
    }

    render(
      <ErrorBoundary>
        <ConditionallyBrokenComponent />
      </ErrorBoundary>
    )

    // Error state should be displayed
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

    // Fix the component
    shouldThrow = false

    // Click Try Again
    const tryAgainButton = screen.getByRole('button', { name: /try again/i })
    fireEvent.click(tryAgainButton)

    // Component should render normally
    expect(screen.getByText('Fixed component')).toBeInTheDocument()
  })

  it('renders custom fallback when provided', () => {
    const customFallback = <div>Custom error message</div>

    render(
      <ErrorBoundary fallback={customFallback}>
        <BrokenComponent />
      </ErrorBoundary>
    )

    expect(screen.getByText('Custom error message')).toBeInTheDocument()
    expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
  })

  it('does not crash other components when one fails', () => {
    render(
      <div>
        <h1>Dashboard</h1>
        <ErrorBoundary>
          <BrokenComponent />
        </ErrorBoundary>
        <p>Other content</p>
      </div>
    )

    // Error state should display
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

    // Rest of page should still render
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Other content')).toBeInTheDocument()
  })

  it('displays technical details in development mode', () => {
    const originalEnv = process.env.NODE_ENV
    process.env.NODE_ENV = 'development'

    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>
    )

    expect(screen.getByText(/technical details/i)).toBeInTheDocument()

    process.env.NODE_ENV = originalEnv
  })

  it('hides technical details in production mode', () => {
    const originalEnv = process.env.NODE_ENV
    process.env.NODE_ENV = 'production'

    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>
    )

    expect(screen.queryByText(/technical details/i)).not.toBeInTheDocument()

    process.env.NODE_ENV = originalEnv
  })
})
