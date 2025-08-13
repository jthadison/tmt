import { render, screen, fireEvent } from '@testing-library/react'
import { AccountOverviewGrid } from '@/components/dashboard/AccountOverviewGrid'
import { AccountOverview } from '@/types/account'

// Mock the child components
jest.mock('@/components/dashboard/AccountCard', () => ({
  AccountCard: jest.fn(({ account, onClick }) => (
    <div data-testid={`account-card-${account.id}`} onClick={onClick}>
      {account.accountName}
    </div>
  ))
}))

jest.mock('@/components/ui/LoadingSkeleton', () => ({
  LoadingSkeleton: jest.fn(({ className }) => (
    <div data-testid="loading-skeleton" className={className}></div>
  ))
}))

const mockAccounts: AccountOverview[] = [
  {
    id: 'account-1',
    accountName: 'Account A1',
    propFirm: 'FTMO',
    balance: 100000,
    equity: 102000,
    pnl: {
      daily: 500,
      weekly: 2000,
      total: 2000,
      percentage: 2.0
    },
    drawdown: {
      current: 1000,
      maximum: 5000,
      percentage: 20
    },
    positions: {
      active: 5,
      long: 3,
      short: 2
    },
    exposure: {
      total: 25000,
      limit: 50000,
      utilization: 50
    },
    status: 'healthy',
    lastUpdate: new Date('2023-01-01T12:00:00Z')
  },
  {
    id: 'account-2',
    accountName: 'Account B2',
    propFirm: 'MyForexFunds',
    balance: 50000,
    equity: 48000,
    pnl: {
      daily: -800,
      weekly: -2000,
      total: -2000,
      percentage: -4.0
    },
    drawdown: {
      current: 4000,
      maximum: 5000,
      percentage: 80
    },
    positions: {
      active: 2,
      long: 1,
      short: 1
    },
    exposure: {
      total: 40000,
      limit: 45000,
      utilization: 88.9
    },
    status: 'danger',
    lastUpdate: new Date('2023-01-01T11:30:00Z')
  }
]

describe('AccountOverviewGrid (Core Functionality)', () => {
  const defaultProps = {
    accounts: mockAccounts,
    loading: false,
    onAccountClick: jest.fn(),
    onRefresh: jest.fn(),
    refreshInterval: 30
  }

  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
  })

  it('renders account overview grid with title', () => {
    render(<AccountOverviewGrid {...defaultProps} />)
    
    expect(screen.getByText('Account Overview')).toBeInTheDocument()
    expect(screen.getByText('2 of 2 accounts')).toBeInTheDocument()
  })

  it('renders all account cards', () => {
    render(<AccountOverviewGrid {...defaultProps} />)
    
    expect(screen.getByTestId('account-card-account-1')).toBeInTheDocument()
    expect(screen.getByTestId('account-card-account-2')).toBeInTheDocument()
  })

  it('shows loading state with skeletons', () => {
    render(<AccountOverviewGrid {...defaultProps} loading={true} accounts={[]} />)
    
    const skeletons = screen.getAllByTestId('loading-skeleton')
    expect(skeletons).toHaveLength(8)
  })

  it('shows error state with retry button', () => {
    render(<AccountOverviewGrid {...defaultProps} error="Failed to load accounts" />)
    
    expect(screen.getByText('⚠️ Error Loading Accounts')).toBeInTheDocument()
    expect(screen.getByText('Failed to load accounts')).toBeInTheDocument()
    expect(screen.getByText('Try Again')).toBeInTheDocument()
  })

  it('calls onRefresh when retry button is clicked', () => {
    render(<AccountOverviewGrid {...defaultProps} error="Failed to load accounts" />)
    
    fireEvent.click(screen.getByText('Try Again'))
    expect(defaultProps.onRefresh).toHaveBeenCalledTimes(1)
  })

  it('shows no accounts found message when empty', () => {
    render(<AccountOverviewGrid {...defaultProps} accounts={[]} />)
    
    expect(screen.getByText('No accounts found')).toBeInTheDocument()
    expect(screen.getByText('Try adjusting your filters or search term')).toBeInTheDocument()
  })

  it('calls onAccountClick when account card is clicked', () => {
    render(<AccountOverviewGrid {...defaultProps} />)
    
    fireEvent.click(screen.getByTestId('account-card-account-1'))
    expect(defaultProps.onAccountClick).toHaveBeenCalledWith('account-1')
  })

  it('calls onRefresh when refresh button is clicked', () => {
    render(<AccountOverviewGrid {...defaultProps} />)
    
    fireEvent.click(screen.getByText('⟳ Refresh'))
    expect(defaultProps.onRefresh).toHaveBeenCalledTimes(1)
  })

  it('disables refresh button when loading', () => {
    render(<AccountOverviewGrid {...defaultProps} loading={true} />)
    
    const refreshButton = screen.getByText('↻ Refresh')
    expect(refreshButton).toBeDisabled()
  })

  it('sets up auto-refresh interval', () => {
    const spy = jest.spyOn(global, 'setInterval')
    
    render(<AccountOverviewGrid {...defaultProps} refreshInterval={10} />)
    
    expect(spy).toHaveBeenCalledWith(expect.any(Function), 10000)
  })

  it('has proper accessibility attributes', () => {
    render(<AccountOverviewGrid {...defaultProps} />)
    
    const grid = screen.getByRole('grid', { name: 'Account overview grid' })
    expect(grid).toBeInTheDocument()
  })

  it('filters accounts by search term correctly', () => {
    render(<AccountOverviewGrid {...defaultProps} />)
    
    const searchInput = screen.getByPlaceholderText('Search accounts or prop firms...')
    
    // Simulate typing FTMO
    fireEvent.change(searchInput, { target: { value: 'FTMO' } })
    
    // Should show 1 of 2 accounts
    expect(screen.getByText('1 of 2 accounts')).toBeInTheDocument()
  })

  it('updates account count when search filters results', () => {
    render(<AccountOverviewGrid {...defaultProps} />)
    
    const searchInput = screen.getByPlaceholderText('Search accounts or prop firms...')
    
    // Search for something that doesn't exist
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } })
    
    // Should show 0 of 2 accounts
    expect(screen.getByText('0 of 2 accounts')).toBeInTheDocument()
  })
})