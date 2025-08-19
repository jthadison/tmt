/**
 * Custom hook for trade execution data management
 * Story 9.4: Trade Execution Monitoring Interface
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  TradeExecution,
  AggregatedMetrics,
  ExecutionAlert,
  ExecutionAlertRule,
  ExecutionUpdate,
  ExecutionFilter,
  ExecutionSort,
  WebSocketStatus,
  UseTradeExecutionState,
  ExecutionFeedConfig,
  OrderLifecycle,
  TimeframePeriod
} from '@/types/tradeExecution'
import { TradeExecutionService } from '@/services/tradeExecutionService'

/**
 * Hook return interface
 */
interface UseTradeExecutionReturn extends UseTradeExecutionState {
  // Data fetching
  refreshExecutions: () => Promise<void>
  loadMoreExecutions: () => Promise<void>
  getExecutionById: (id: string) => Promise<TradeExecution | null>
  
  // Metrics
  refreshMetrics: () => Promise<void>
  getMetricsByTimeframe: (timeframe: TimeframePeriod) => Promise<void>
  
  // Alerts
  refreshAlerts: () => Promise<void>
  acknowledgeAlert: (alertId: string) => Promise<void>
  dismissAlert: (alertId: string) => void
  
  // Order lifecycle
  getOrderLifecycle: (orderId: string) => Promise<OrderLifecycle | null>
  
  // Filtering and sorting
  updateFilter: (filter: Partial<ExecutionFilter>) => void
  updateSort: (sort: ExecutionSort) => void
  clearFilters: () => void
  
  // Feed configuration
  updateFeedConfig: (config: Partial<ExecutionFeedConfig>) => void
  pauseRealTimeUpdates: () => void
  resumeRealTimeUpdates: () => void
  
  // WebSocket management
  reconnectWebSocket: () => void
  
  // Export functionality
  exportExecutions: (format: 'csv' | 'json' | 'xlsx') => Promise<string | null>
  
  // Utility functions
  getFilteredExecutions: () => TradeExecution[]
  getExecutionsByAccount: (accountId: string) => TradeExecution[]
  getExecutionsByInstrument: (instrument: string) => TradeExecution[]
  getTotalVolume: () => number
  getAverageSlippage: () => number
}

/**
 * Service instance (singleton)
 */
let serviceInstance: TradeExecutionService | null = null

const getService = (): TradeExecutionService => {
  if (!serviceInstance) {
    serviceInstance = new TradeExecutionService()
    
    // Start mock data simulation in development
    if (process.env.NODE_ENV === 'development') {
      serviceInstance.startMockDataSimulation()
    }
  }
  return serviceInstance
}

/**
 * Default filter configuration
 */
const defaultFilter: ExecutionFilter = {}

/**
 * Default sort configuration
 */
const defaultSort: ExecutionSort = {
  field: 'timestamp',
  direction: 'desc'
}

/**
 * Default feed configuration
 */
const defaultFeedConfig: ExecutionFeedConfig = {
  maxItems: 100,
  autoScroll: true,
  showNotifications: true,
  soundEnabled: false,
  filter: defaultFilter,
  sort: defaultSort,
  refreshInterval: 5,
  pauseUpdates: false
}

/**
 * Main hook for trade execution data management
 */
export function useTradeExecution(): UseTradeExecutionReturn {
  const [state, setState] = useState<UseTradeExecutionState>({
    executions: [],
    metrics: null,
    alerts: [],
    alertRules: [],
    isLoading: true,
    error: null,
    lastUpdate: null,
    wsStatus: {
      connected: false,
      url: '',
      reconnectAttempts: 0
    },
    filter: defaultFilter,
    sort: defaultSort,
    feedConfig: defaultFeedConfig
  })

  const service = useRef<TradeExecutionService>(getService())
  const executionCache = useRef<Map<string, TradeExecution>>(new Map())
  const currentPage = useRef(1)
  const hasMoreData = useRef(true)
  const loadingMore = useRef(false)

  /**
   * Handle real-time execution updates
   */
  const handleExecutionUpdate = useCallback((execution: TradeExecution) => {
    executionCache.current.set(execution.id, execution)
    
    setState(prevState => {
      // Update existing execution or add new one
      const existingIndex = prevState.executions.findIndex(e => e.id === execution.id)
      let newExecutions: TradeExecution[]

      if (existingIndex >= 0) {
        newExecutions = [...prevState.executions]
        newExecutions[existingIndex] = execution
      } else {
        // Add new execution at the beginning (newest first)
        newExecutions = [execution, ...prevState.executions]
        
        // Limit the number of executions in memory
        if (newExecutions.length > prevState.feedConfig.maxItems) {
          newExecutions = newExecutions.slice(0, prevState.feedConfig.maxItems)
        }
      }

      // Sort executions according to current sort config
      newExecutions.sort((a, b) => {
        const aValue = getExecutionFieldValue(a, prevState.sort.field)
        const bValue = getExecutionFieldValue(b, prevState.sort.field)
        
        if (prevState.sort.direction === 'asc') {
          return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
        } else {
          return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
        }
      })

      return {
        ...prevState,
        executions: newExecutions,
        lastUpdate: new Date()
      }
    })
  }, [])

  /**
   * Handle new alerts
   */
  const handleNewAlert = useCallback((alert: ExecutionAlert) => {
    setState(prevState => ({
      ...prevState,
      alerts: [alert, ...prevState.alerts.filter(a => a.id !== alert.id)]
    }))

    // Show notification if enabled
    if (state.feedConfig.showNotifications) {
      // You could integrate with a notification service here
      console.log('New execution alert:', alert.title)
    }
  }, [state.feedConfig.showNotifications])

  /**
   * Handle WebSocket status changes
   */
  const handleWebSocketStatus = useCallback((status: WebSocketStatus) => {
    setState(prevState => ({
      ...prevState,
      wsStatus: status
    }))
  }, [])

  /**
   * Get field value from execution for sorting
   */
  const getExecutionFieldValue = (execution: TradeExecution, field: string): any => {
    switch (field) {
      case 'timestamp':
        return execution.timestamps.lastUpdate.getTime()
      case 'instrument':
        return execution.instrument
      case 'size':
        return execution.executedSize
      case 'slippage':
        return execution.slippage
      case 'status':
        return execution.status
      case 'account':
        return execution.accountAlias
      default:
        return execution.timestamps.lastUpdate.getTime()
    }
  }

  /**
   * Apply filters to executions
   */
  const applyFilters = useCallback((executions: TradeExecution[], filter: ExecutionFilter): TradeExecution[] => {
    return executions.filter(execution => {
      // Account filter
      if (filter.accounts && filter.accounts.length > 0) {
        if (!filter.accounts.includes(execution.accountId)) return false
      }

      // Instrument filter
      if (filter.instruments && filter.instruments.length > 0) {
        if (!filter.instruments.includes(execution.instrument)) return false
      }

      // Status filter
      if (filter.statuses && filter.statuses.length > 0) {
        if (!filter.statuses.includes(execution.status)) return false
      }

      // Broker filter
      if (filter.brokers && filter.brokers.length > 0) {
        if (!filter.brokers.includes(execution.broker)) return false
      }

      // Direction filter
      if (filter.directions && filter.directions.length > 0) {
        if (!filter.directions.includes(execution.direction)) return false
      }

      // Time range filter
      if (filter.timeRange) {
        const executionTime = execution.timestamps.lastUpdate.getTime()
        if (executionTime < filter.timeRange.start.getTime() || 
            executionTime > filter.timeRange.end.getTime()) {
          return false
        }
      }

      // Size filters
      if (filter.minSize && execution.executedSize < filter.minSize) return false
      if (filter.maxSize && execution.executedSize > filter.maxSize) return false

      // Slippage filters
      if (filter.minSlippage && execution.slippage < filter.minSlippage) return false
      if (filter.maxSlippage && execution.slippage > filter.maxSlippage) return false

      // Priority filter
      if (filter.priorities && filter.priorities.length > 0) {
        if (!filter.priorities.includes(execution.priority)) return false
      }

      // Search query
      if (filter.searchQuery && filter.searchQuery.trim()) {
        const query = filter.searchQuery.toLowerCase()
        const searchableText = `${execution.instrument} ${execution.accountAlias} ${execution.broker} ${execution.orderId}`.toLowerCase()
        if (!searchableText.includes(query)) return false
      }

      return true
    })
  }, [])

  /**
   * Load executions from API
   */
  const refreshExecutions = useCallback(async () => {
    setState(prevState => ({ ...prevState, isLoading: true, error: null }))

    try {
      const response = await service.current.getExecutions(state.filter, state.sort, 1, state.feedConfig.maxItems)
      
      if (response.success && response.data) {
        // Cache all executions
        response.data.forEach(execution => {
          executionCache.current.set(execution.id, execution)
        })

        setState(prevState => ({
          ...prevState,
          executions: response.data || [],
          isLoading: false,
          lastUpdate: new Date()
        }))

        currentPage.current = 1
        hasMoreData.current = response.pagination?.hasNext || false
      } else {
        setState(prevState => ({
          ...prevState,
          isLoading: false,
          error: response.error || 'Failed to load executions'
        }))
      }
    } catch (error) {
      setState(prevState => ({
        ...prevState,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }))
    }
  }, [state.filter, state.sort, state.feedConfig.maxItems])

  /**
   * Load more executions for pagination
   */
  const loadMoreExecutions = useCallback(async () => {
    if (loadingMore.current || !hasMoreData.current) return

    loadingMore.current = true

    try {
      const nextPage = currentPage.current + 1
      const response = await service.current.getExecutions(state.filter, state.sort, nextPage, 50)
      
      if (response.success && response.data) {
        // Cache new executions
        response.data.forEach(execution => {
          executionCache.current.set(execution.id, execution)
        })

        setState(prevState => ({
          ...prevState,
          executions: [...prevState.executions, ...response.data!],
          lastUpdate: new Date()
        }))

        currentPage.current = nextPage
        hasMoreData.current = response.pagination?.hasNext || false
      }
    } catch (error) {
      console.error('Error loading more executions:', error)
    } finally {
      loadingMore.current = false
    }
  }, [state.filter, state.sort])

  /**
   * Get single execution by ID
   */
  const getExecutionById = useCallback(async (id: string): Promise<TradeExecution | null> => {
    // Check cache first
    const cachedExecution = executionCache.current.get(id)
    if (cachedExecution) {
      return cachedExecution
    }

    try {
      const response = await service.current.getExecution(id)
      if (response.success && response.data) {
        executionCache.current.set(id, response.data)
        return response.data
      }
    } catch (error) {
      console.error('Error fetching execution:', error)
    }

    return null
  }, [])

  /**
   * Refresh metrics
   */
  const refreshMetrics = useCallback(async () => {
    try {
      const response = await service.current.getMetrics('1h')
      if (response.success && response.data) {
        setState(prevState => ({
          ...prevState,
          metrics: response.data!
        }))
      }
    } catch (error) {
      console.error('Error fetching metrics:', error)
    }
  }, [])

  /**
   * Get metrics by timeframe
   */
  const getMetricsByTimeframe = useCallback(async (timeframe: TimeframePeriod) => {
    try {
      const response = await service.current.getMetrics(timeframe)
      if (response.success && response.data) {
        setState(prevState => ({
          ...prevState,
          metrics: response.data!
        }))
      }
    } catch (error) {
      console.error('Error fetching metrics by timeframe:', error)
    }
  }, [])

  /**
   * Refresh alerts
   */
  const refreshAlerts = useCallback(async () => {
    try {
      const response = await service.current.getAlerts()
      if (response.success && response.data) {
        setState(prevState => ({
          ...prevState,
          alerts: response.data!
        }))
      }
    } catch (error) {
      console.error('Error fetching alerts:', error)
    }
  }, [])

  /**
   * Acknowledge alert
   */
  const acknowledgeAlert = useCallback(async (alertId: string) => {
    try {
      const response = await service.current.acknowledgeAlert(alertId)
      if (response.success) {
        setState(prevState => ({
          ...prevState,
          alerts: prevState.alerts.map(alert => 
            alert.id === alertId 
              ? { ...alert, acknowledged: true, acknowledgedAt: new Date() }
              : alert
          )
        }))
      }
    } catch (error) {
      console.error('Error acknowledging alert:', error)
    }
  }, [])

  /**
   * Dismiss alert locally
   */
  const dismissAlert = useCallback((alertId: string) => {
    setState(prevState => ({
      ...prevState,
      alerts: prevState.alerts.filter(alert => alert.id !== alertId)
    }))
  }, [])

  /**
   * Get order lifecycle
   */
  const getOrderLifecycle = useCallback(async (orderId: string): Promise<OrderLifecycle | null> => {
    try {
      const response = await service.current.getOrderLifecycle(orderId)
      if (response.success && response.data) {
        return response.data
      }
    } catch (error) {
      console.error('Error fetching order lifecycle:', error)
    }
    return null
  }, [])

  /**
   * Update filter
   */
  const updateFilter = useCallback((newFilter: Partial<ExecutionFilter>) => {
    setState(prevState => ({
      ...prevState,
      filter: { ...prevState.filter, ...newFilter }
    }))
  }, [])

  /**
   * Update sort
   */
  const updateSort = useCallback((sort: ExecutionSort) => {
    setState(prevState => ({
      ...prevState,
      sort
    }))
  }, [])

  /**
   * Clear filters
   */
  const clearFilters = useCallback(() => {
    setState(prevState => ({
      ...prevState,
      filter: defaultFilter
    }))
  }, [])

  /**
   * Update feed configuration
   */
  const updateFeedConfig = useCallback((config: Partial<ExecutionFeedConfig>) => {
    setState(prevState => ({
      ...prevState,
      feedConfig: { ...prevState.feedConfig, ...config }
    }))
  }, [])

  /**
   * Pause real-time updates
   */
  const pauseRealTimeUpdates = useCallback(() => {
    setState(prevState => ({
      ...prevState,
      feedConfig: { ...prevState.feedConfig, pauseUpdates: true }
    }))
  }, [])

  /**
   * Resume real-time updates
   */
  const resumeRealTimeUpdates = useCallback(() => {
    setState(prevState => ({
      ...prevState,
      feedConfig: { ...prevState.feedConfig, pauseUpdates: false }
    }))
  }, [])

  /**
   * Reconnect WebSocket
   */
  const reconnectWebSocket = useCallback(() => {
    service.current.reconnect()
  }, [])

  /**
   * Export executions
   */
  const exportExecutions = useCallback(async (format: 'csv' | 'json' | 'xlsx'): Promise<string | null> => {
    try {
      const exportConfig = {
        format,
        filter: state.filter,
        fields: ['id', 'instrument', 'direction', 'executedSize', 'executedPrice', 'slippage', 'status', 'timestamp'],
        timeRange: {
          start: new Date(Date.now() - 24 * 60 * 60 * 1000), // Last 24 hours
          end: new Date()
        },
        includeFees: true,
        includeMetadata: false
      }

      const response = await service.current.exportExecutions(exportConfig)
      if (response.success && response.data) {
        return response.data
      }
    } catch (error) {
      console.error('Error exporting executions:', error)
    }
    return null
  }, [state.filter])

  /**
   * Utility functions
   */
  const getFilteredExecutions = useCallback((): TradeExecution[] => {
    return applyFilters(state.executions, state.filter)
  }, [state.executions, state.filter, applyFilters])

  const getExecutionsByAccount = useCallback((accountId: string): TradeExecution[] => {
    return state.executions.filter(execution => execution.accountId === accountId)
  }, [state.executions])

  const getExecutionsByInstrument = useCallback((instrument: string): TradeExecution[] => {
    return state.executions.filter(execution => execution.instrument === instrument)
  }, [state.executions])

  const getTotalVolume = useCallback((): number => {
    return state.executions.reduce((total, execution) => total + execution.executedSize, 0)
  }, [state.executions])

  const getAverageSlippage = useCallback((): number => {
    const filledExecutions = state.executions.filter(e => e.status === 'filled')
    if (filledExecutions.length === 0) return 0
    
    const totalSlippage = filledExecutions.reduce((total, execution) => total + execution.slippage, 0)
    return totalSlippage / filledExecutions.length
  }, [state.executions])

  // Set up event listeners on mount
  useEffect(() => {
    const handleUpdate = (update: ExecutionUpdate) => {
      if (state.feedConfig.pauseUpdates) return
      
      if (update.execution) {
        handleExecutionUpdate(update.execution)
      }
      if (update.alert) {
        handleNewAlert(update.alert)
      }
    }

    service.current.on('update', handleUpdate)
    service.current.on('execution:update', handleExecutionUpdate)
    service.current.on('alert:new', handleNewAlert)
    service.current.on('ws:connected', handleWebSocketStatus)
    service.current.on('ws:disconnected', handleWebSocketStatus)
    service.current.on('ws:error', ({ status }: { status: WebSocketStatus }) => handleWebSocketStatus(status))

    return () => {
      service.current.off('update', handleUpdate)
      service.current.off('execution:update', handleExecutionUpdate)
      service.current.off('alert:new', handleNewAlert)
      service.current.off('ws:connected', handleWebSocketStatus)
      service.current.off('ws:disconnected', handleWebSocketStatus)
      service.current.off('ws:error', ({ status }: { status: WebSocketStatus }) => handleWebSocketStatus(status))
    }
  }, [handleExecutionUpdate, handleNewAlert, handleWebSocketStatus, state.feedConfig.pauseUpdates])

  // Initial data load
  useEffect(() => {
    refreshExecutions()
    refreshMetrics()
    refreshAlerts()
  }, [refreshExecutions, refreshMetrics, refreshAlerts])

  // Refresh executions when filter or sort changes
  useEffect(() => {
    refreshExecutions()
  }, [state.filter, state.sort])

  // Periodic metrics refresh
  useEffect(() => {
    const interval = setInterval(() => {
      refreshMetrics()
    }, state.feedConfig.refreshInterval * 1000)

    return () => clearInterval(interval)
  }, [refreshMetrics, state.feedConfig.refreshInterval])

  return {
    ...state,
    refreshExecutions,
    loadMoreExecutions,
    getExecutionById,
    refreshMetrics,
    getMetricsByTimeframe,
    refreshAlerts,
    acknowledgeAlert,
    dismissAlert,
    getOrderLifecycle,
    updateFilter,
    updateSort,
    clearFilters,
    updateFeedConfig,
    pauseRealTimeUpdates,
    resumeRealTimeUpdates,
    reconnectWebSocket,
    exportExecutions,
    getFilteredExecutions,
    getExecutionsByAccount,
    getExecutionsByInstrument,
    getTotalVolume,
    getAverageSlippage
  }
}