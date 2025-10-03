/**
 * Tests for usePnLData hook
 */

import { renderHook, act } from '@testing-library/react'
import { usePnLData } from '@/hooks/usePnLData'
import { useOandaData } from '@/hooks/useOandaData'

// Mock the useOandaData hook
jest.mock('@/hooks/useOandaData')

const mockUseOandaData = useOandaData as jest.MockedFunction<typeof useOandaData>

describe('usePnLData', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('calculates total daily P&L correctly', () => {
    mockUseOandaData.mockReturnValue({
      accounts: [
        {
          id: 'acc1',
          alias: 'Account 1',
          type: 'demo',
          currency: 'USD',
          balance: 100000,
          NAV: 100500,
          unrealizedPL: 300,
          realizedPL: 200,
          marginUsed: 1000,
          marginAvailable: 99000,
          marginRate: 0.02,
          openTradeCount: 2,
          openPositionCount: 2,
          pendingOrderCount: 0,
          createdTime: '2024-01-01',
          lastTransactionID: '123',
          commission: {
            homeConversionFactor: 1,
            unitsAvailable: { default: { long: '1000000', short: '1000000' } },
          },
          financing: { dividendAdjustment: 0 },
          healthStatus: 'healthy',
          lastUpdate: new Date(),
        },
        {
          id: 'acc2',
          alias: 'Account 2',
          type: 'demo',
          currency: 'USD',
          balance: 50000,
          NAV: 50150,
          unrealizedPL: 100,
          realizedPL: 50,
          marginUsed: 500,
          marginAvailable: 49500,
          marginRate: 0.02,
          openTradeCount: 1,
          openPositionCount: 1,
          pendingOrderCount: 0,
          createdTime: '2024-01-01',
          lastTransactionID: '456',
          commission: {
            homeConversionFactor: 1,
            unitsAvailable: { default: { long: '500000', short: '500000' } },
          },
          financing: { dividendAdjustment: 0 },
          healthStatus: 'healthy',
          lastUpdate: new Date(),
        },
      ],
      accountMetrics: new Map(),
      accountHistory: new Map(),
      performanceSummaries: new Map(),
      tradingLimits: new Map(),
      aggregatedMetrics: null,
      connectionStatus: [],
      alerts: [],
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      refreshData: jest.fn(),
      refreshAccount: jest.fn(),
      loadAccountHistory: jest.fn(),
      getPerformanceSummary: jest.fn(),
      subscribeToUpdates: jest.fn(),
      unsubscribeFromUpdates: jest.fn(),
      reconnectAccount: jest.fn(),
      dismissAlert: jest.fn(),
      getAlertsForAccount: jest.fn(),
      getFilteredAccounts: jest.fn(),
      getAccountById: jest.fn(),
      getMetricsById: jest.fn(),
      isAccountConnected: jest.fn(),
    })

    const { result } = renderHook(() => usePnLData())

    // Total P&L = (300 + 200) + (100 + 50) = 650
    expect(result.current.dailyPnL).toBe(650)
    expect(result.current.realizedPnL).toBe(250)
    expect(result.current.unrealizedPnL).toBe(400)
  })

  it('calculates P&L percentage correctly', () => {
    mockUseOandaData.mockReturnValue({
      accounts: [
        {
          id: 'acc1',
          alias: 'Account 1',
          type: 'demo',
          currency: 'USD',
          balance: 100000,
          NAV: 101000,
          unrealizedPL: 500,
          realizedPL: 500,
          marginUsed: 1000,
          marginAvailable: 99000,
          marginRate: 0.02,
          openTradeCount: 1,
          openPositionCount: 1,
          pendingOrderCount: 0,
          createdTime: '2024-01-01',
          lastTransactionID: '123',
          commission: {
            homeConversionFactor: 1,
            unitsAvailable: { default: { long: '1000000', short: '1000000' } },
          },
          financing: { dividendAdjustment: 0 },
          healthStatus: 'healthy',
          lastUpdate: new Date(),
        },
      ],
      accountMetrics: new Map(),
      accountHistory: new Map(),
      performanceSummaries: new Map(),
      tradingLimits: new Map(),
      aggregatedMetrics: null,
      connectionStatus: [],
      alerts: [],
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      refreshData: jest.fn(),
      refreshAccount: jest.fn(),
      loadAccountHistory: jest.fn(),
      getPerformanceSummary: jest.fn(),
      subscribeToUpdates: jest.fn(),
      unsubscribeFromUpdates: jest.fn(),
      reconnectAccount: jest.fn(),
      dismissAlert: jest.fn(),
      getAlertsForAccount: jest.fn(),
      getFilteredAccounts: jest.fn(),
      getAccountById: jest.fn(),
      getMetricsById: jest.fn(),
      isAccountConnected: jest.fn(),
    })

    const { result } = renderHook(() => usePnLData())

    // Total P&L = 1000, Balance = 100000, Percentage = 1%
    expect(result.current.pnLPercentage).toBe(1)
  })

  it('updates P&L history when P&L changes significantly', () => {
    const mockAccounts = [
      {
        id: 'acc1',
        alias: 'Account 1',
        type: 'demo' as const,
        currency: 'USD' as const,
        balance: 100000,
        NAV: 100000,
        unrealizedPL: 0,
        realizedPL: 0,
        marginUsed: 0,
        marginAvailable: 100000,
        marginRate: 0.02,
        openTradeCount: 0,
        openPositionCount: 0,
        pendingOrderCount: 0,
        createdTime: '2024-01-01',
        lastTransactionID: '123',
        commission: {
          homeConversionFactor: 1,
          unitsAvailable: { default: { long: '1000000', short: '1000000' } },
        },
        financing: { dividendAdjustment: 0 },
        healthStatus: 'healthy' as const,
        lastUpdate: new Date(),
      },
    ]

    mockUseOandaData.mockReturnValue({
      accounts: mockAccounts,
      accountMetrics: new Map(),
      accountHistory: new Map(),
      performanceSummaries: new Map(),
      tradingLimits: new Map(),
      aggregatedMetrics: null,
      connectionStatus: [],
      alerts: [],
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      refreshData: jest.fn(),
      refreshAccount: jest.fn(),
      loadAccountHistory: jest.fn(),
      getPerformanceSummary: jest.fn(),
      subscribeToUpdates: jest.fn(),
      unsubscribeFromUpdates: jest.fn(),
      reconnectAccount: jest.fn(),
      dismissAlert: jest.fn(),
      getAlertsForAccount: jest.fn(),
      getFilteredAccounts: jest.fn(),
      getAccountById: jest.fn(),
      getMetricsById: jest.fn(),
      isAccountConnected: jest.fn(),
    })

    const { result, rerender } = renderHook(() => usePnLData())

    const initialHistoryLength = result.current.pnLHistory.length

    // Update accounts with significant P&L change (>$0.01)
    mockUseOandaData.mockReturnValue({
      accounts: [
        {
          ...mockAccounts[0],
          unrealizedPL: 100,
          realizedPL: 50,
        },
      ],
      accountMetrics: new Map(),
      accountHistory: new Map(),
      performanceSummaries: new Map(),
      tradingLimits: new Map(),
      aggregatedMetrics: null,
      connectionStatus: [],
      alerts: [],
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      refreshData: jest.fn(),
      refreshAccount: jest.fn(),
      loadAccountHistory: jest.fn(),
      getPerformanceSummary: jest.fn(),
      subscribeToUpdates: jest.fn(),
      unsubscribeFromUpdates: jest.fn(),
      reconnectAccount: jest.fn(),
      dismissAlert: jest.fn(),
      getAlertsForAccount: jest.fn(),
      getFilteredAccounts: jest.fn(),
      getAccountById: jest.fn(),
      getMetricsById: jest.fn(),
      isAccountConnected: jest.fn(),
    })

    rerender()

    // History should have been updated
    expect(result.current.pnLHistory.length).toBeGreaterThan(initialHistoryLength)
  })

  it('maintains max 20 history points', () => {
    const mockAccounts = [
      {
        id: 'acc1',
        alias: 'Account 1',
        type: 'demo' as const,
        currency: 'USD' as const,
        balance: 100000,
        NAV: 100000,
        unrealizedPL: 0,
        realizedPL: 0,
        marginUsed: 0,
        marginAvailable: 100000,
        marginRate: 0.02,
        openTradeCount: 0,
        openPositionCount: 0,
        pendingOrderCount: 0,
        createdTime: '2024-01-01',
        lastTransactionID: '123',
        commission: {
          homeConversionFactor: 1,
          unitsAvailable: { default: { long: '1000000', short: '1000000' } },
        },
        financing: { dividendAdjustment: 0 },
        healthStatus: 'healthy' as const,
        lastUpdate: new Date(),
      },
    ]

    mockUseOandaData.mockReturnValue({
      accounts: mockAccounts,
      accountMetrics: new Map(),
      accountHistory: new Map(),
      performanceSummaries: new Map(),
      tradingLimits: new Map(),
      aggregatedMetrics: null,
      connectionStatus: [],
      alerts: [],
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      refreshData: jest.fn(),
      refreshAccount: jest.fn(),
      loadAccountHistory: jest.fn(),
      getPerformanceSummary: jest.fn(),
      subscribeToUpdates: jest.fn(),
      unsubscribeFromUpdates: jest.fn(),
      reconnectAccount: jest.fn(),
      dismissAlert: jest.fn(),
      getAlertsForAccount: jest.fn(),
      getFilteredAccounts: jest.fn(),
      getAccountById: jest.fn(),
      getMetricsById: jest.fn(),
      isAccountConnected: jest.fn(),
    })

    const { result, rerender } = renderHook(() => usePnLData())

    // Simulate 25 updates with significant changes
    for (let i = 1; i <= 25; i++) {
      mockUseOandaData.mockReturnValue({
        accounts: [
          {
            ...mockAccounts[0],
            unrealizedPL: i * 10,
          },
        ],
        accountMetrics: new Map(),
        accountHistory: new Map(),
        performanceSummaries: new Map(),
        tradingLimits: new Map(),
        aggregatedMetrics: null,
        connectionStatus: [],
        alerts: [],
        isLoading: false,
        error: null,
        lastUpdate: new Date(),
        refreshData: jest.fn(),
        refreshAccount: jest.fn(),
        loadAccountHistory: jest.fn(),
        getPerformanceSummary: jest.fn(),
        subscribeToUpdates: jest.fn(),
        unsubscribeFromUpdates: jest.fn(),
        reconnectAccount: jest.fn(),
        dismissAlert: jest.fn(),
        getAlertsForAccount: jest.fn(),
        getFilteredAccounts: jest.fn(),
        getAccountById: jest.fn(),
        getMetricsById: jest.fn(),
        isAccountConnected: jest.fn(),
      })
      rerender()
    }

    // Should never exceed 20 points
    expect(result.current.pnLHistory.length).toBeLessThanOrEqual(20)
  })
})
