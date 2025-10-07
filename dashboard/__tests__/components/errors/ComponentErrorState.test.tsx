import { render, screen, fireEvent } from '@testing-library/react'
import { ComponentErrorState } from '@/components/errors/ComponentErrorState'

describe('ComponentErrorState', () => {
  const mockError = new Error('Test error message')
  const mockOnRetry = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('displays 4-part error message design', () => {
    render(<ComponentErrorState error={mockError} onRetry={mockOnRetry} />)

    // 1. What Happened
    expect(screen.getByText(/unable to load component/i)).toBeInTheDocument()

    // 2. Why It Matters (Impact)
    expect(screen.getByText(/impact:/i)).toBeInTheDocument()

    // 3. Next Steps implied by recovery options

    // 4. Recovery Options
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('displays inline within component boundary (not full page)', () => {
    const { container } = render(
      <ComponentErrorState error={mockError} onRetry={mockOnRetry} />
    )

    const errorContainer = container.firstChild as HTMLElement
    expect(errorContainer).not.toHaveClass('fixed')
    expect(errorContainer).not.toHaveClass('min-h-screen')
  })

  it('triggers retry callback when retry button is clicked', () => {
    render(<ComponentErrorState error={mockError} onRetry={mockOnRetry} />)

    const retryButton = screen.getByRole('button', { name: /retry/i })
    fireEvent.click(retryButton)

    expect(mockOnRetry).toHaveBeenCalledTimes(1)
  })

  it('displays custom title, description, and impact when provided', () => {
    const customTitle = 'Custom Error Title'
    const customDescription = 'Custom error description'
    const customImpact = 'Custom impact message'

    render(
      <ComponentErrorState
        error={mockError}
        onRetry={mockOnRetry}
        title={customTitle}
        description={customDescription}
        impact={customImpact}
      />
    )

    expect(screen.getByText(customTitle)).toBeInTheDocument()
    expect(screen.getByText(customDescription)).toBeInTheDocument()
    expect(screen.getByText(/custom impact message/i)).toBeInTheDocument()
  })

  it('displays technical details in development mode', () => {
    const originalEnv = process.env.NODE_ENV
    process.env.NODE_ENV = 'development'

    render(<ComponentErrorState error={mockError} onRetry={mockOnRetry} />)

    expect(screen.getByText(/technical details/i)).toBeInTheDocument()
    expect(screen.getByText(/test error message/i)).toBeInTheDocument()

    process.env.NODE_ENV = originalEnv
  })

  it('does not display technical details in production mode', () => {
    const originalEnv = process.env.NODE_ENV
    process.env.NODE_ENV = 'production'

    render(<ComponentErrorState error={mockError} onRetry={mockOnRetry} />)

    expect(screen.queryByText(/technical details/i)).not.toBeInTheDocument()

    process.env.NODE_ENV = originalEnv
  })

  it('has AlertTriangle icon visible', () => {
    const { container } = render(
      <ComponentErrorState error={mockError} onRetry={mockOnRetry} />
    )

    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })

  it('has reload page button', () => {
    render(<ComponentErrorState error={mockError} onRetry={mockOnRetry} />)

    const reloadButton = screen.getByRole('button', { name: /reload page/i })
    expect(reloadButton).toBeInTheDocument()
  })
})
