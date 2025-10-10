/**
 * Analytics Data Hooks (Story 12.2)
 *
 * Custom React hooks for fetching and managing analytics data with
 * caching, error handling, and automatic revalidation.
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  SessionPerformanceData,
  PatternPerformanceData,
  PnLByPairData,
  ConfidenceCorrelationData,
  DrawdownData,
  ParameterChange,
  AnalyticsDateRange,
} from '@/types/analytics122'
import * as analyticsClient from '@/lib/analyticsClient'

interface UseAnalyticsState<T> {
  data: T | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

/**
 * Generic analytics hook factory
 * @param fetchFunction Function to fetch data
 * @param dateRange Optional date range filter
 * @returns Analytics state and refetch function
 */
function useAnalyticsData<T>(
  fetchFunction: (dateRange?: AnalyticsDateRange) => Promise<T>,
  dateRange?: AnalyticsDateRange
): UseAnalyticsState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const mountedRef = useRef(true)

  const fetchData = useCallback(async () => {
    if (!mountedRef.current) return

    setLoading(true)
    setError(null)

    try {
      const result = await fetchFunction(dateRange)
      if (mountedRef.current) {
        setData(result)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err as Error)
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [fetchFunction, dateRange])

  useEffect(() => {
    mountedRef.current = true
    fetchData()

    return () => {
      mountedRef.current = false
    }
  }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}

/**
 * Hook for fetching session performance data
 * @param dateRange Optional date range filter
 * @returns Session performance state
 */
export function useSessionPerformance(
  dateRange?: AnalyticsDateRange
): UseAnalyticsState<SessionPerformanceData> {
  return useAnalyticsData(analyticsClient.fetchSessionPerformance, dateRange)
}

/**
 * Hook for fetching pattern performance data
 * @param dateRange Optional date range filter
 * @returns Pattern performance state
 */
export function usePatternPerformance(
  dateRange?: AnalyticsDateRange
): UseAnalyticsState<PatternPerformanceData> {
  return useAnalyticsData(analyticsClient.fetchPatternPerformance, dateRange)
}

/**
 * Hook for fetching P&L by pair data
 * @param dateRange Optional date range filter
 * @returns P&L data state
 */
export function usePnLByPair(
  dateRange?: AnalyticsDateRange
): UseAnalyticsState<PnLByPairData> {
  return useAnalyticsData(analyticsClient.fetchPnLByPair, dateRange)
}

/**
 * Hook for fetching confidence correlation data
 * @param dateRange Optional date range filter
 * @returns Correlation data state
 */
export function useConfidenceCorrelation(
  dateRange?: AnalyticsDateRange
): UseAnalyticsState<ConfidenceCorrelationData> {
  return useAnalyticsData(analyticsClient.fetchConfidenceCorrelation, dateRange)
}

/**
 * Hook for fetching drawdown data
 * @param dateRange Optional date range filter
 * @returns Drawdown data state
 */
export function useDrawdownData(
  dateRange?: AnalyticsDateRange
): UseAnalyticsState<DrawdownData> {
  return useAnalyticsData(analyticsClient.fetchDrawdownData, dateRange)
}

/**
 * Hook for fetching parameter evolution data
 * @param dateRange Optional date range filter
 * @returns Parameter evolution state
 */
export function useParameterEvolution(
  dateRange?: AnalyticsDateRange
): UseAnalyticsState<ParameterChange[]> {
  return useAnalyticsData(analyticsClient.fetchParameterEvolution, dateRange)
}

/**
 * Hook for CSV export functionality
 * @returns Export state and trigger function
 */
export function useExportCSV() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const exportCSV = useCallback(async (dateRange: AnalyticsDateRange) => {
    setLoading(true)
    setError(null)

    try {
      const blob = await analyticsClient.exportToCSV(dateRange)

      // Generate filename
      const startDate = new Date(dateRange.start_date)
      const endDate = new Date(dateRange.end_date)
      const filename = `trading_history_${startDate.toISOString().split('T')[0]}_${endDate.toISOString().split('T')[0]}.csv`

      // Download file
      analyticsClient.downloadBlob(blob, filename)

      return { success: true }
    } catch (err) {
      setError(err as Error)
      return { success: false, error: err as Error }
    } finally {
      setLoading(false)
    }
  }, [])

  return { exportCSV, loading, error }
}

/**
 * Hook for managing analytics page state
 * @returns Analytics page state and control functions
 */
export function useAnalyticsPageState() {
  const [dateRangePreset, setDateRangePreset] = useState<'7d' | '30d' | '90d' | 'custom'>('30d')
  const [customDateRange, setCustomDateRange] = useState<AnalyticsDateRange | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [refreshInterval, setRefreshInterval] = useState(30) // seconds

  // Calculate actual date range based on preset
  const getDateRange = useCallback((): AnalyticsDateRange | undefined => {
    if (dateRangePreset === 'custom' && customDateRange) {
      return customDateRange
    }

    const end = new Date()
    const start = new Date()

    switch (dateRangePreset) {
      case '7d':
        start.setDate(end.getDate() - 7)
        break
      case '30d':
        start.setDate(end.getDate() - 30)
        break
      case '90d':
        start.setDate(end.getDate() - 90)
        break
    }

    return {
      start_date: start.toISOString(),
      end_date: end.toISOString(),
    }
  }, [dateRangePreset, customDateRange])

  return {
    dateRangePreset,
    setDateRangePreset,
    customDateRange,
    setCustomDateRange,
    autoRefresh,
    setAutoRefresh,
    refreshInterval,
    setRefreshInterval,
    getDateRange,
  }
}
