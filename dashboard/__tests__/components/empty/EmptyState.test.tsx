import { render, screen, fireEvent } from '@testing-library/react'
import { EmptyState } from '@/components/empty/EmptyState'

describe('EmptyState', () => {
  it('displays no-data type with Inbox icon', () => {
    const { container } = render(
      <EmptyState
        type="no-data"
        title="No Open Positions"
        description="You haven't opened any positions yet."
      />
    )

    expect(screen.getByText('No Open Positions')).toBeInTheDocument()
    expect(screen.getByText(/you haven't opened any positions yet/i)).toBeInTheDocument()

    // Check for SVG icon
    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })

  it('displays no-results type with Search icon', () => {
    const { container } = render(
      <EmptyState
        type="no-results"
        title="No Positions Match Your Filters"
        description="Try adjusting your filters"
      />
    )

    expect(screen.getByText('No Positions Match Your Filters')).toBeInTheDocument()
    expect(screen.getByText(/try adjusting your filters/i)).toBeInTheDocument()

    // Check for SVG icon
    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })

  it('displays action button when provided', () => {
    const onClick = jest.fn()

    render(
      <EmptyState
        type="no-data"
        title="No Open Positions"
        description="You haven't opened any positions yet."
        action={{ label: 'View Available Signals', onClick }}
      />
    )

    const actionButton = screen.getByRole('button', { name: /view available signals/i })
    expect(actionButton).toBeInTheDocument()

    fireEvent.click(actionButton)
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('displays secondary action button when provided', () => {
    const primaryOnClick = jest.fn()
    const secondaryOnClick = jest.fn()

    render(
      <EmptyState
        type="no-data"
        title="No Open Positions"
        description="You haven't opened any positions yet."
        action={{ label: 'Primary Action', onClick: primaryOnClick }}
        secondaryAction={{ label: 'Secondary Action', onClick: secondaryOnClick }}
      />
    )

    const primaryButton = screen.getByRole('button', { name: /primary action/i })
    const secondaryButton = screen.getByRole('button', { name: /secondary action/i })

    expect(primaryButton).toBeInTheDocument()
    expect(secondaryButton).toBeInTheDocument()

    fireEvent.click(primaryButton)
    expect(primaryOnClick).toHaveBeenCalledTimes(1)

    fireEvent.click(secondaryButton)
    expect(secondaryOnClick).toHaveBeenCalledTimes(1)
  })

  it('renders without action buttons', () => {
    render(
      <EmptyState
        type="no-data"
        title="No Data"
        description="No data available"
      />
    )

    expect(screen.getByText('No Data')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('applies different icon colors for different types', () => {
    const { container: noDataContainer } = render(
      <EmptyState
        type="no-data"
        title="No Data"
        description="Description"
      />
    )

    const noDataIcon = noDataContainer.querySelector('svg')
    expect(noDataIcon).toHaveClass('text-gray-400')

    const { container: noResultsContainer } = render(
      <EmptyState
        type="no-results"
        title="No Results"
        description="Description"
      />
    )

    const noResultsIcon = noResultsContainer.querySelector('svg')
    expect(noResultsIcon).toHaveClass('text-blue-400')
  })

  it('centers content properly', () => {
    const { container } = render(
      <EmptyState
        type="no-data"
        title="No Data"
        description="Description"
      />
    )

    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center', 'text-center')
  })
})
