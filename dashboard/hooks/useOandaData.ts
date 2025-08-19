/**
 * Custom hook for managing OANDA account data and real-time updates
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { 
  OandaAccount, 
  AccountMetrics, 
  AccountHistoryPoint, 
  AccountPerformanceSummary,
  TradingLimits,
  AggregatedAccountMetrics,
  AccountUpdateMessage,
  AccountAlert,
  AccountConnectionStatus,
  TimeFrame,
  AccountFilter
} from '@/types/oanda'
import { OandaService } from '@/services/oandaService'

/**
 * Hook state interface
 */
interface UseOandaDataState {
  accounts: OandaAccount[]
  accountMetrics: Map<string, AccountMetrics>
  accountHistory: Map<string, AccountHistoryPoint[]>
  performanceSummaries: Map<string, AccountPerformanceSummary>
  tradingLimits: Map<string, TradingLimits>
  aggregatedMetrics: AggregatedAccountMetrics | null
  connectionStatus: AccountConnectionStatus[]
  alerts: AccountAlert[]
  isLoading: boolean
  error: string | null
  lastUpdate: Date | null
}

/**
 * Hook return interface
 */
interface UseOandaDataReturn extends UseOandaDataState {
  // Data fetching
  refreshData: () => Promise<void>
  refreshAccount: (accountId: string) => Promise<void>
  
  // History and performance
  loadAccountHistory: (accountId: string, timeFrame: TimeFrame, startDate: Date, endDate: Date) => Promise<void>
  getPerformanceSummary: (accountId: string, startDate: Date, endDate: Date) => Promise<void>
  
  // Real-time updates
  subscribeToUpdates: () => void
  unsubscribeFromUpdates: () => void
  
  // Connection management
  reconnectAccount: (accountId: string) => Promise<void>
  
  // Alerts
  dismissAlert: (alertId: string) => void
  getAlertsForAccount: (accountId: string) => AccountAlert[]
  
  // Filtering and sorting
  getFilteredAccounts: (filter: AccountFilter) => OandaAccount[]
  
  // Utility functions
  getAccountById: (accountId: string) => OandaAccount | undefined
  getMetricsById: (accountId: string) => AccountMetrics | undefined
  isAccountConnected: (accountId: string) => boolean
}

/**
 * OANDA service instance (singleton)
 */
let oandaServiceInstance: OandaService | null = null

const getOandaService = (): OandaService => {
  if (!oandaServiceInstance) {
    const config = {
      apiUrl: process.env.NEXT_PUBLIC_OANDA_API_URL || 'https://api-fxpractice.oanda.com',
      streamUrl: process.env.NEXT_PUBLIC_OANDA_STREAM_URL || 'https://stream-fxpractice.oanda.com',
      apiKey: process.env.NEXT_PUBLIC_OANDA_API_KEY || 'demo-key',
      accountIds: (process.env.NEXT_PUBLIC_OANDA_ACCOUNT_IDS || 'demo-account-1,demo-account-2').split(','),
      rateLimitRequests: parseInt(process.env.NEXT_PUBLIC_OANDA_RATE_LIMIT || '100'),
      rateLimitWindow: parseInt(process.env.NEXT_PUBLIC_OANDA_RATE_WINDOW || '60000'),
      retryAttempts: parseInt(process.env.NEXT_PUBLIC_OANDA_RETRY_ATTEMPTS || '3'),
      retryDelay: parseInt(process.env.NEXT_PUBLIC_OANDA_RETRY_DELAY || '1000')
    }
    
    oandaServiceInstance = new OandaService(config)
  }
  
  return oandaServiceInstance
}

/**
 * Hook for managing OANDA account data
 */
export function useOandaData(): UseOandaDataReturn {
  const [state, setState] = useState<UseOandaDataState>({
    accounts: [],
    accountMetrics: new Map(),
    accountHistory: new Map(),
    performanceSummaries: new Map(),
    tradingLimits: new Map(),
    aggregatedMetrics: null,
    connectionStatus: [],
    alerts: [],
    isLoading: true,
    error: null,
    lastUpdate: null
  })

  const oandaService = useRef<OandaService>(getOandaService())
  const updateSubscribed = useRef(false)
  const alertSubscribed = useRef(false)

  /**
   * Handle real-time account updates
   */
  const handleAccountUpdate = useCallback((update: AccountUpdateMessage) => {
    setState(prevState => {
      const newMetrics = new Map(prevState.accountMetrics)
      newMetrics.set(update.accountId, { ...update.metrics } as AccountMetrics)
      
      return {
        ...prevState,
        accountMetrics: newMetrics,
        lastUpdate: update.timestamp
      }
    })
  }, [])

  /**
   * Handle alert notifications
   */
  const handleAlert = useCallback((alert: AccountAlert) => {
    setState(prevState => ({
      ...prevState,
      alerts: [...prevState.alerts.filter(a => a.id !== alert.id), alert]
    }))
  }, [])

  /**
   * Load all account data
   */
  const refreshData = useCallback(async () => {
    setState(prevState => ({ ...prevState, isLoading: true, error: null }))
    
    try {
      // Load accounts
      const accountsResponse = await oandaService.current.getAllAccounts()
      if (accountsResponse.status !== 'success') {
        throw new Error(accountsResponse.error || 'Failed to load accounts')
      }

      // Load metrics for each account
      const metricsMap = new Map<string, AccountMetrics>()
      const limitsMap = new Map<string, TradingLimits>()
      
      for (const account of accountsResponse.data) {
        // Load metrics
        const metricsResponse = await oandaService.current.getAccountMetrics(account.id)
        if (metricsResponse.status === 'success' && metricsResponse.data) {
          metricsMap.set(account.id, metricsResponse.data)
        }
        
        // Load trading limits
        const limitsResponse = await oandaService.current.getTradingLimits(account.id)
        if (limitsResponse.status === 'success' && limitsResponse.data) {
          limitsMap.set(account.id, limitsResponse.data)
        }
      }

      // Load aggregated metrics
      const aggregatedResponse = await oandaService.current.getAggregatedMetrics()
      const aggregatedMetrics = aggregatedResponse.status === 'success' ? 
        aggregatedResponse.data : null

      // Get connection status
      const connectionStatus = oandaService.current.getConnectionStatus()

      setState(prevState => ({
        ...prevState,
        accounts: accountsResponse.data,
        accountMetrics: metricsMap,
        tradingLimits: limitsMap,
        aggregatedMetrics,
        connectionStatus,
        isLoading: false,
        lastUpdate: new Date()
      }))

    } catch (error) {
      setState(prevState => ({
        ...prevState,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      }))
    }
  }, [])

  /**
   * Refresh single account data
   */
  const refreshAccount = useCallback(async (accountId: string) => {
    try {
      const accountResponse = await oandaService.current.getAccount(accountId)
      const metricsResponse = await oandaService.current.getAccountMetrics(accountId)
      const limitsResponse = await oandaService.current.getTradingLimits(accountId)

      setState(prevState => {
        const newAccounts = prevState.accounts.map(account => 
          account.id === accountId && accountResponse.status === 'success' ? 
            accountResponse.data : account
        )
        
        const newMetrics = new Map(prevState.accountMetrics)
        if (metricsResponse.status === 'success' && metricsResponse.data) {
          newMetrics.set(accountId, metricsResponse.data)
        }
        
        const newLimits = new Map(prevState.tradingLimits)
        if (limitsResponse.status === 'success' && limitsResponse.data) {
          newLimits.set(accountId, limitsResponse.data)
        }

        return {
          ...prevState,
          accounts: newAccounts,
          accountMetrics: newMetrics,
          tradingLimits: newLimits,
          lastUpdate: new Date()
        }
      })
    } catch (error) {
      console.error(`Error refreshing account ${accountId}:`, error)
    }
  }, [])

  /**
   * Load account history
   */
  const loadAccountHistory = useCallback(async (
    accountId: string, 
    timeFrame: TimeFrame, 
    startDate: Date, 
    endDate: Date
  ) => {
    try {
      const historyResponse = await oandaService.current.getAccountHistory(
        accountId, 
        timeFrame, 
        startDate, 
        endDate
      )
      
      if (historyResponse.status === 'success' && historyResponse.data) {
        setState(prevState => {
          const newHistory = new Map(prevState.accountHistory)
          newHistory.set(accountId, historyResponse.data)
          
          return {
            ...prevState,
            accountHistory: newHistory
          }
        })
      }
    } catch (error) {
      console.error(`Error loading history for account ${accountId}:`, error)
    }
  }, [])

  /**
   * Get performance summary
   */
  const getPerformanceSummary = useCallback(async (
    accountId: string, 
    startDate: Date, 
    endDate: Date
  ) => {
    try {
      const summaryResponse = await oandaService.current.getPerformanceSummary(
        accountId, 
        startDate, 
        endDate
      )
      
      if (summaryResponse.status === 'success' && summaryResponse.data) {
        setState(prevState => {
          const newSummaries = new Map(prevState.performanceSummaries)
          newSummaries.set(accountId, summaryResponse.data)
          
          return {
            ...prevState,
            performanceSummaries: newSummaries
          }
        })
      }
    } catch (error) {
      console.error(`Error loading performance summary for account ${accountId}:`, error)
    }
  }, [])

  /**
   * Subscribe to real-time updates
   */
  const subscribeToUpdates = useCallback(() => {
    if (!updateSubscribed.current) {
      oandaService.current.subscribeToUpdates(handleAccountUpdate)
      updateSubscribed.current = true
    }
  }, [handleAccountUpdate])

  /**
   * Unsubscribe from real-time updates
   */
  const unsubscribeFromUpdates = useCallback(() => {
    if (updateSubscribed.current) {
      // Note: In a real implementation, OandaService would need an unsubscribe method
      updateSubscribed.current = false
    }
  }, [])

  /**
   * Reconnect account
   */
  const reconnectAccount = useCallback(async (accountId: string) => {
    try {
      await oandaService.current.reconnectAccount(accountId)
      
      // Update connection status
      const connectionStatus = oandaService.current.getConnectionStatus()
      setState(prevState => ({
        ...prevState,
        connectionStatus
      }))
    } catch (error) {
      console.error(`Error reconnecting account ${accountId}:`, error)
    }
  }, [])

  /**
   * Dismiss alert
   */
  const dismissAlert = useCallback((alertId: string) => {
    setState(prevState => ({
      ...prevState,
      alerts: prevState.alerts.filter(alert => alert.id !== alertId)
    }))
  }, [])

  /**
   * Get alerts for specific account
   */
  const getAlertsForAccount = useCallback((accountId: string): AccountAlert[] => {
    return state.alerts.filter(alert => alert.accountId === accountId)
  }, [state.alerts])

  /**
   * Get filtered accounts
   */
  const getFilteredAccounts = useCallback((filter: AccountFilter): OandaAccount[] => {
    let filtered = [...state.accounts]

    if (filter.accountTypes && filter.accountTypes.length > 0) {
      filtered = filtered.filter(account => filter.accountTypes!.includes(account.type))
    }

    if (filter.currencies && filter.currencies.length > 0) {
      filtered = filtered.filter(account => filter.currencies!.includes(account.currency))
    }

    if (filter.healthStatus && filter.healthStatus.length > 0) {
      filtered = filtered.filter(account => filter.healthStatus!.includes(account.healthStatus))
    }

    if (filter.minBalance !== undefined) {
      filtered = filtered.filter(account => account.balance >= filter.minBalance!)
    }

    if (filter.maxBalance !== undefined) {
      filtered = filtered.filter(account => account.balance <= filter.maxBalance!)
    }

    if (filter.searchQuery && filter.searchQuery.trim()) {
      const query = filter.searchQuery.toLowerCase()
      filtered = filtered.filter(account => 
        account.alias.toLowerCase().includes(query) ||
        account.id.toLowerCase().includes(query)
      )
    }

    // Apply sorting
    if (filter.sortBy) {
      filtered.sort((a, b) => {
        let aValue: number | string
        let bValue: number | string

        switch (filter.sortBy) {
          case 'balance':
            aValue = a.balance
            bValue = b.balance
            break
          case 'equity':
            aValue = a.NAV
            bValue = b.NAV
            break
          case 'unrealizedPL':
            aValue = a.unrealizedPL
            bValue = b.unrealizedPL
            break
          case 'marginUtilization':
            const aTotal = a.marginUsed + a.marginAvailable
            const bTotal = b.marginUsed + b.marginAvailable
            aValue = aTotal > 0 ? (a.marginUsed / aTotal) * 100 : 0
            bValue = bTotal > 0 ? (b.marginUsed / bTotal) * 100 : 0
            break
          case 'alias':
            aValue = a.alias.toLowerCase()
            bValue = b.alias.toLowerCase()
            break
          default:
            aValue = a.balance
            bValue = b.balance
        }

        const direction = filter.sortDirection || 'desc'
        
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          return direction === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
        }

        return direction === 'asc' ? 
          (aValue as number) - (bValue as number) : 
          (bValue as number) - (aValue as number)
      })
    }

    return filtered
  }, [state.accounts])

  /**
   * Get account by ID
   */
  const getAccountById = useCallback((accountId: string): OandaAccount | undefined => {
    return state.accounts.find(account => account.id === accountId)
  }, [state.accounts])

  /**
   * Get metrics by ID
   */
  const getMetricsById = useCallback((accountId: string): AccountMetrics | undefined => {
    return state.accountMetrics.get(accountId)
  }, [state.accountMetrics])

  /**
   * Check if account is connected
   */
  const isAccountConnected = useCallback((accountId: string): boolean => {
    const status = state.connectionStatus.find(s => s.accountId === accountId)
    return status?.status === 'connected'
  }, [state.connectionStatus])

  // Initialize data on mount
  useEffect(() => {
    refreshData()
    
    // Subscribe to alerts
    if (!alertSubscribed.current) {
      oandaService.current.subscribeToAlerts(handleAlert)
      alertSubscribed.current = true
    }

    // Cleanup on unmount
    return () => {
      if (oandaServiceInstance) {
        oandaServiceInstance.cleanup()
        oandaServiceInstance = null
      }
    }
  }, [refreshData, handleAlert])

  return {
    ...state,
    refreshData,
    refreshAccount,
    loadAccountHistory,
    getPerformanceSummary,
    subscribeToUpdates,
    unsubscribeFromUpdates,
    reconnectAccount,
    dismissAlert,
    getAlertsForAccount,
    getFilteredAccounts,
    getAccountById,
    getMetricsById,
    isAccountConnected
  }
}