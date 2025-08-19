/**
 * Performance Analytics Hook
 * Story 9.6: Centralized hook for managing performance analytics state and operations
 * 
 * Provides unified interface for all performance analytics functionality
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  RealtimePnL,
  RiskMetrics,
  AgentPerformance,
  ComplianceReport,
  AnalyticsQuery,
  PortfolioAnalytics,
  MonthlyBreakdown,
  TradeBreakdown
} from '@/types/performanceAnalytics'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'

interface PerformanceAnalyticsState {
  // Data
  realtimePnL: Map<string, RealtimePnL>
  historicalData: {
    daily: MonthlyBreakdown[]
    weekly: MonthlyBreakdown[]
    monthly: MonthlyBreakdown[]
  } | null
  riskMetrics: Map<string, RiskMetrics>
  agentPerformance: AgentPerformance[]
  portfolioAnalytics: PortfolioAnalytics | null
  complianceReports: ComplianceReport[]
  
  // Loading states
  loading: {
    realtimePnL: boolean
    historical: boolean
    risk: boolean
    agents: boolean
    portfolio: boolean
    compliance: boolean
  }
  
  // Error states
  errors: {
    realtimePnL?: string
    historical?: string
    risk?: string
    agents?: string
    portfolio?: string
    compliance?: string
  }
  
  // Metadata
  lastUpdate: Date
  autoRefresh: boolean
  refreshInterval: number
}

interface PerformanceAnalyticsActions {
  // Real-time P&L
  loadRealtimePnL: (accountId: string, agentId?: string) => Promise<void>
  subscribeToRealtimePnL: (accountId: string, callback: (data: RealtimePnL) => void) => () => void
  
  // Historical data
  loadHistoricalData: (query: AnalyticsQuery) => Promise<void>
  
  // Risk metrics
  loadRiskMetrics: (accountId: string, dateRange: { start: Date; end: Date }) => Promise<void>
  
  // Agent performance
  loadAgentPerformance: (accountIds: string[], dateRange: { start: Date; end: Date }) => Promise<void>
  
  // Portfolio analytics
  loadPortfolioAnalytics: (accountIds: string[]) => Promise<void>
  
  // Compliance reports
  generateComplianceReport: (
    accountIds: string[],
    dateRange: { start: Date; end: Date },
    reportType?: 'standard' | 'detailed' | 'executive' | 'regulatory'
  ) => Promise<ComplianceReport>
  
  // Utility functions
  refreshAll: () => Promise<void>
  clearErrors: () => void
  setAutoRefresh: (enabled: boolean) => void
  setRefreshInterval: (interval: number) => void
  clearCache: () => void
}

export function usePerformanceAnalytics(
  initialAccountIds: string[] = [],
  initialDateRange?: { start: Date; end: Date }
) {
  // State
  const [state, setState] = useState<PerformanceAnalyticsState>({
    realtimePnL: new Map(),
    historicalData: null,
    riskMetrics: new Map(),
    agentPerformance: [],
    portfolioAnalytics: null,
    complianceReports: [],
    loading: {
      realtimePnL: false,
      historical: false,
      risk: false,
      agents: false,
      portfolio: false,
      compliance: false
    },
    errors: {},
    lastUpdate: new Date(),
    autoRefresh: true,
    refreshInterval: 5000
  })

  // Refs for cleanup
  const subscriptionsRef = useRef<Map<string, () => void>>(new Map())
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Update loading state
  const setLoading = useCallback((key: keyof PerformanceAnalyticsState['loading'], loading: boolean) => {
    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, [key]: loading }
    }))
  }, [])

  // Update error state
  const setError = useCallback((key: keyof PerformanceAnalyticsState['errors'], error?: string) => {
    setState(prev => ({
      ...prev,
      errors: { ...prev.errors, [key]: error }
    }))
  }, [])

  // Load real-time P&L data
  const loadRealtimePnL = useCallback(async (accountId: string, agentId?: string) => {
    setLoading('realtimePnL', true)
    setError('realtimePnL', undefined)

    try {
      const data = await performanceAnalyticsService.getRealtimePnL(accountId, agentId)
      
      setState(prev => ({
        ...prev,
        realtimePnL: new Map(prev.realtimePnL).set(
          `${accountId}-${agentId || 'all'}`, 
          data
        ),
        lastUpdate: new Date()
      }))
    } catch (error) {
      setError('realtimePnL', error instanceof Error ? error.message : 'Failed to load real-time P&L')
    } finally {
      setLoading('realtimePnL', false)
    }
  }, [setLoading, setError])

  // Subscribe to real-time P&L updates
  const subscribeToRealtimePnL = useCallback((
    accountId: string, 
    callback: (data: RealtimePnL) => void
  ) => {
    const subscriptionKey = `realtime-${accountId}`
    
    // Create WebSocket subscription (mock implementation)
    const unsubscribe = () => {
      // In real implementation, this would close WebSocket connection
      console.log(`Unsubscribed from real-time P&L for ${accountId}`)
    }
    
    // Store subscription for cleanup
    subscriptionsRef.current.set(subscriptionKey, unsubscribe)
    
    // Simulate real-time updates (in real app, this would be WebSocket)
    const interval = setInterval(async () => {
      try {
        const data = await performanceAnalyticsService.getRealtimePnL(accountId)
        callback(data)
        
        setState(prev => ({
          ...prev,
          realtimePnL: new Map(prev.realtimePnL).set(`${accountId}-all`, data),
          lastUpdate: new Date()
        }))
      } catch (error) {
        setError('realtimePnL', error instanceof Error ? error.message : 'Real-time update failed')
      }
    }, state.refreshInterval)

    return () => {
      clearInterval(interval)
      subscriptionsRef.current.delete(subscriptionKey)
      unsubscribe()
    }
  }, [state.refreshInterval, setError])

  // Load historical performance data
  const loadHistoricalData = useCallback(async (query: AnalyticsQuery) => {
    setLoading('historical', true)
    setError('historical', undefined)

    try {
      const data = await performanceAnalyticsService.getHistoricalPerformance(query)
      
      setState(prev => ({
        ...prev,
        historicalData: data,
        lastUpdate: new Date()
      }))
    } catch (error) {
      setError('historical', error instanceof Error ? error.message : 'Failed to load historical data')
    } finally {
      setLoading('historical', false)
    }
  }, [setLoading, setError])

  // Load risk metrics
  const loadRiskMetrics = useCallback(async (
    accountId: string, 
    dateRange: { start: Date; end: Date }
  ) => {
    setLoading('risk', true)
    setError('risk', undefined)

    try {
      const data = await performanceAnalyticsService.calculateRiskMetrics(accountId, dateRange)
      
      setState(prev => ({
        ...prev,
        riskMetrics: new Map(prev.riskMetrics).set(accountId, data),
        lastUpdate: new Date()
      }))
    } catch (error) {
      setError('risk', error instanceof Error ? error.message : 'Failed to load risk metrics')
    } finally {
      setLoading('risk', false)
    }
  }, [setLoading, setError])

  // Load agent performance
  const loadAgentPerformance = useCallback(async (
    accountIds: string[], 
    dateRange: { start: Date; end: Date }
  ) => {
    setLoading('agents', true)
    setError('agents', undefined)

    try {
      const data = await performanceAnalyticsService.getAgentComparison(accountIds, dateRange)
      
      setState(prev => ({
        ...prev,
        agentPerformance: data,
        lastUpdate: new Date()
      }))
    } catch (error) {
      setError('agents', error instanceof Error ? error.message : 'Failed to load agent performance')
    } finally {
      setLoading('agents', false)
    }
  }, [setLoading, setError])

  // Load portfolio analytics
  const loadPortfolioAnalytics = useCallback(async (accountIds: string[]) => {
    setLoading('portfolio', true)
    setError('portfolio', undefined)

    try {
      const data = await performanceAnalyticsService.getPortfolioAnalytics(accountIds)
      
      setState(prev => ({
        ...prev,
        portfolioAnalytics: data,
        lastUpdate: new Date()
      }))
    } catch (error) {
      setError('portfolio', error instanceof Error ? error.message : 'Failed to load portfolio analytics')
    } finally {
      setLoading('portfolio', false)
    }
  }, [setLoading, setError])

  // Generate compliance report
  const generateComplianceReport = useCallback(async (
    accountIds: string[],
    dateRange: { start: Date; end: Date },
    reportType: 'standard' | 'detailed' | 'executive' | 'regulatory' = 'standard'
  ) => {
    setLoading('compliance', true)
    setError('compliance', undefined)

    try {
      const report = await performanceAnalyticsService.generateComplianceReport(
        accountIds, 
        dateRange, 
        reportType
      )
      
      setState(prev => ({
        ...prev,
        complianceReports: [report, ...prev.complianceReports],
        lastUpdate: new Date()
      }))

      return report
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate compliance report'
      setError('compliance', errorMessage)
      throw error
    } finally {
      setLoading('compliance', false)
    }
  }, [setLoading, setError])

  // Refresh all data
  const refreshAll = useCallback(async () => {
    if (initialAccountIds.length === 0) return

    const dateRange = initialDateRange || {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      end: new Date()
    }

    await Promise.allSettled([
      loadRealtimePnL(initialAccountIds[0]),
      loadHistoricalData({
        accountIds: initialAccountIds,
        dateRange,
        granularity: 'day',
        metrics: ['pnl', 'return', 'trades', 'winRate']
      }),
      loadRiskMetrics(initialAccountIds[0], dateRange),
      loadAgentPerformance(initialAccountIds, dateRange),
      loadPortfolioAnalytics(initialAccountIds)
    ])
  }, [
    initialAccountIds,
    initialDateRange,
    loadRealtimePnL,
    loadHistoricalData,
    loadRiskMetrics,
    loadAgentPerformance,
    loadPortfolioAnalytics
  ])

  // Clear all errors
  const clearErrors = useCallback(() => {
    setState(prev => ({
      ...prev,
      errors: {}
    }))
  }, [])

  // Set auto refresh
  const setAutoRefresh = useCallback((enabled: boolean) => {
    setState(prev => ({
      ...prev,
      autoRefresh: enabled
    }))
  }, [])

  // Set refresh interval
  const setRefreshInterval = useCallback((interval: number) => {
    setState(prev => ({
      ...prev,
      refreshInterval: interval
    }))
  }, [])

  // Clear cache
  const clearCache = useCallback(() => {
    performanceAnalyticsService.clearCache()
    setState(prev => ({
      ...prev,
      realtimePnL: new Map(),
      historicalData: new Map(),
      riskMetrics: new Map(),
      agentPerformance: new Map(),
      portfolioAnalytics: new Map(),
      complianceReports: new Map()
    }))
  }, [])

  // Auto refresh effect
  useEffect(() => {
    if (state.autoRefresh && initialAccountIds.length > 0) {
      refreshTimerRef.current = setInterval(refreshAll, state.refreshInterval)
      
      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current)
          refreshTimerRef.current = null
        }
      }
    }
  }, [state.autoRefresh, state.refreshInterval, refreshAll, initialAccountIds])

  // Cleanup subscriptions on unmount
  useEffect(() => {
    return () => {
      // Clear all subscriptions
      subscriptionsRef.current.forEach(unsubscribe => unsubscribe())
      subscriptionsRef.current.clear()
      
      // Clear refresh timer
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current)
      }
    }
  }, [])

  // Actions object
  const actions: PerformanceAnalyticsActions = {
    loadRealtimePnL,
    subscribeToRealtimePnL,
    loadHistoricalData,
    loadRiskMetrics,
    loadAgentPerformance,
    loadPortfolioAnalytics,
    generateComplianceReport,
    refreshAll,
    clearErrors,
    setAutoRefresh,
    setRefreshInterval,
    clearCache
  }

  return {
    ...state,
    actions
  }
}