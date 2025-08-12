import { renderHook, act, waitFor } from '@testing-library/react'
import { useAccountData, useAccountWebSocket } from '@/hooks/useAccountData'

// Mock timers for testing intervals
jest.useFakeTimers()

describe('useAccountData', () => {
  beforeEach(() => {
    jest.clearAllTimers()
    jest.clearAllMocks()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
    jest.useFakeTimers()
  })

  it('initializes with loading state', () => {
    const { result } = renderHook(() => useAccountData())
    
    expect(result.current.loading).toBe(true)
    expect(result.current.accounts).toEqual([])
    expect(result.current.error).toBe(null)
  })

  it('loads mock account data after initialization', async () => {
    const { result } = renderHook(() => useAccountData())
    
    // Fast-forward past the initialization delay
    act(() => {
      jest.advanceTimersByTime(1000)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.accounts).toHaveLength(12)
    expect(result.current.error).toBe(null)
    
    // Check that accounts have required properties
    const firstAccount = result.current.accounts[0]
    expect(firstAccount).toHaveProperty('id')
    expect(firstAccount).toHaveProperty('accountName')
    expect(firstAccount).toHaveProperty('propFirm')
    expect(firstAccount).toHaveProperty('balance')
    expect(firstAccount).toHaveProperty('pnl')
    expect(firstAccount).toHaveProperty('drawdown')
    expect(firstAccount).toHaveProperty('positions')
    expect(firstAccount).toHaveProperty('exposure')
    expect(firstAccount).toHaveProperty('status')
  })

  it('refreshes data when refreshData is called', async () => {
    const { result } = renderHook(() => useAccountData())
    
    // Wait for initial load
    act(() => {
      jest.advanceTimersByTime(1000)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialAccounts = result.current.accounts
    
    // Call refresh
    act(() => {
      result.current.refreshData()
    })

    expect(result.current.loading).toBe(true)

    // Fast-forward refresh delay
    act(() => {
      jest.advanceTimersByTime(500)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Accounts should be updated (different P&L values)
    expect(result.current.accounts).toHaveLength(12)
    expect(result.current.accounts[0].accountName).toBe(initialAccounts[0].accountName) // Name preserved
    expect(result.current.accounts[0].propFirm).toBe(initialAccounts[0].propFirm) // Prop firm preserved
  })

  it('simulates real-time updates for specific account', async () => {
    const { result } = renderHook(() => useAccountData())
    
    // Wait for initial load
    act(() => {
      jest.advanceTimersByTime(1000)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialAccount = result.current.accounts[0]
    const initialPnL = initialAccount.pnl.daily
    
    // Simulate real-time update
    act(() => {
      result.current.simulateRealTimeUpdate(initialAccount.id)
    })

    // P&L should have changed
    const updatedAccount = result.current.accounts[0]
    expect(updatedAccount.pnl.daily).not.toBe(initialPnL)
    expect(updatedAccount.lastUpdate.getTime()).toBeGreaterThan(initialAccount.lastUpdate.getTime())
  })

  it('sets up periodic real-time updates', async () => {
    const { result } = renderHook(() => useAccountData())
    
    // Wait for initial load
    act(() => {
      jest.advanceTimersByTime(1000)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialAccounts = [...result.current.accounts]
    
    // Fast-forward to trigger periodic update (5 seconds)
    act(() => {
      jest.advanceTimersByTime(5000)
    })

    // One account should have updated P&L
    const updatedAccounts = result.current.accounts
    const hasUpdates = updatedAccounts.some((account, index) => 
      account.pnl.daily !== initialAccounts[index].pnl.daily ||
      account.lastUpdate.getTime() > initialAccounts[index].lastUpdate.getTime()
    )
    
    expect(hasUpdates).toBe(true)
  })

  it('generates accounts with varied statuses', async () => {
    const { result } = renderHook(() => useAccountData())
    
    act(() => {
      jest.advanceTimersByTime(1000)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const statuses = result.current.accounts.map(account => account.status)
    const uniqueStatuses = new Set(statuses)
    
    // Should have multiple different statuses
    expect(uniqueStatuses.size).toBeGreaterThan(1)
    expect([...uniqueStatuses].every(status => 
      ['healthy', 'warning', 'danger'].includes(status)
    )).toBe(true)
  })

  it('generates accounts with different prop firms', async () => {
    const { result } = renderHook(() => useAccountData())
    
    act(() => {
      jest.advanceTimersByTime(1000)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const propFirms = result.current.accounts.map(account => account.propFirm)
    const uniquePropFirms = new Set(propFirms)
    
    // Should have multiple different prop firms
    expect(uniquePropFirms.size).toBeGreaterThan(1)
    expect([...uniquePropFirms]).toContain('FTMO')
    expect([...uniquePropFirms]).toContain('MyForexFunds')
  })

  it('ensures account data follows business rules', async () => {
    const { result } = renderHook(() => useAccountData())
    
    act(() => {
      jest.advanceTimersByTime(1000)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    result.current.accounts.forEach(account => {
      // Equity should equal balance + total P&L
      expect(account.equity).toBeCloseTo(account.balance + account.pnl.total, 2)
      
      // Drawdown percentage should match calculation
      const expectedPercentage = (account.drawdown.current / account.drawdown.maximum) * 100
      expect(account.drawdown.percentage).toBeCloseTo(expectedPercentage, 1)
      
      // Exposure utilization should match calculation
      const expectedUtilization = (account.exposure.total / account.exposure.limit) * 100
      expect(account.exposure.utilization).toBeCloseTo(expectedUtilization, 1)
      
      // Active positions should equal long + short
      expect(account.positions.active).toBe(account.positions.long + account.positions.short)
      
      // P&L percentage should match calculation
      const expectedPnLPercentage = (account.pnl.total / account.balance) * 100
      expect(account.pnl.percentage).toBeCloseTo(expectedPnLPercentage, 1)
    })
  })
})

describe('useAccountWebSocket', () => {
  it('initializes with disconnected status', () => {
    const { result } = renderHook(() => useAccountWebSocket([]))
    
    expect(result.current.connectionStatus).toBe('disconnected')
  })

  it('connects and sets status to connected', async () => {
    const { result } = renderHook(() => useAccountWebSocket([]))
    
    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('connected')
    })
  })

  it('simulates WebSocket connection management', async () => {
    const mockAccounts = [
      { id: 'account-1' } as any,
      { id: 'account-2' } as any
    ]
    
    const { result, unmount } = renderHook(() => useAccountWebSocket(mockAccounts))
    
    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('connected')
    })
    
    // Simulate unmounting (disconnection)
    unmount()
    
    // In a real implementation, this would test actual WebSocket cleanup
    // For now, we just verify the hook doesn't crash on unmount
  })
})