/**
 * Analytics API Client for Performance Dashboard (Story 12.2)
 *
 * Provides methods for fetching analytics data from orchestrator service.
 * Includes error handling, retries, and timeout management.
 */

import {
  SessionPerformanceData,
  PatternPerformanceData,
  PnLByPairData,
  ConfidenceCorrelationData,
  DrawdownData,
  ParameterChange,
  AnalyticsAPIResponse,
  AnalyticsDateRange,
} from '@/types/analytics122'

const ORCHESTRATOR_BASE_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8089'
const REQUEST_TIMEOUT = 10000 // 10 seconds
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // 1 second

/**
 * Sleep utility for retry delays
 * @param ms Milliseconds to sleep
 */
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

/**
 * Fetch with timeout
 * @param url URL to fetch
 * @param options Fetch options
 * @param timeout Timeout in milliseconds
 * @returns Promise resolving to Response
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = REQUEST_TIMEOUT
): Promise<Response> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    clearTimeout(id)
    return response
  } catch (error) {
    clearTimeout(id)
    throw error
  }
}

/**
 * Fetch with retries and exponential backoff
 * @param url URL to fetch
 * @param options Fetch options
 * @returns Promise resolving to Response
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  let lastError: Error | null = null

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const response = await fetchWithTimeout(url, options)

      if (response.ok) {
        return response
      }

      // Don't retry on 4xx errors (client errors)
      if (response.status >= 400 && response.status < 500) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      // Retry on 5xx errors (server errors)
      lastError = new Error(`HTTP ${response.status}: ${response.statusText}`)
    } catch (error) {
      lastError = error as Error
    }

    // Exponential backoff: 1s, 2s, 4s
    if (attempt < MAX_RETRIES - 1) {
      await sleep(RETRY_DELAY * Math.pow(2, attempt))
    }
  }

  throw lastError || new Error('Max retries exceeded')
}

/**
 * Build query string from date range
 * @param dateRange Optional date range
 * @returns Query string (e.g., "?start_date=...&end_date=...")
 */
function buildDateRangeQuery(dateRange?: AnalyticsDateRange): string {
  if (!dateRange) return ''

  const params = new URLSearchParams()
  if (dateRange.start_date) params.append('start_date', dateRange.start_date)
  if (dateRange.end_date) params.append('end_date', dateRange.end_date)

  const query = params.toString()
  return query ? `?${query}` : ''
}

/**
 * Fetch session performance data
 * @param dateRange Optional date range filter
 * @returns Promise resolving to session performance data
 */
export async function fetchSessionPerformance(
  dateRange?: AnalyticsDateRange
): Promise<SessionPerformanceData> {
  const query = buildDateRangeQuery(dateRange)
  const url = `${ORCHESTRATOR_BASE_URL}/analytics/performance/by-session${query}`

  const response = await fetchWithRetry(url)
  const data: AnalyticsAPIResponse<SessionPerformanceData> = await response.json()

  if (data.error) {
    throw new Error(data.error)
  }

  return data.data || {}
}

/**
 * Fetch pattern performance data
 * @param dateRange Optional date range filter
 * @returns Promise resolving to pattern performance data
 */
export async function fetchPatternPerformance(
  dateRange?: AnalyticsDateRange
): Promise<PatternPerformanceData> {
  const query = buildDateRangeQuery(dateRange)
  const url = `${ORCHESTRATOR_BASE_URL}/analytics/performance/by-pattern${query}`

  const response = await fetchWithRetry(url)
  const data: AnalyticsAPIResponse<PatternPerformanceData> = await response.json()

  if (data.error) {
    throw new Error(data.error)
  }

  return data.data || {}
}

/**
 * Fetch P&L by currency pair
 * @param dateRange Optional date range filter
 * @returns Promise resolving to P&L data
 */
export async function fetchPnLByPair(
  dateRange?: AnalyticsDateRange
): Promise<PnLByPairData> {
  const query = buildDateRangeQuery(dateRange)
  const url = `${ORCHESTRATOR_BASE_URL}/analytics/pnl/by-pair${query}`

  const response = await fetchWithRetry(url)
  const data: AnalyticsAPIResponse<PnLByPairData> = await response.json()

  if (data.error) {
    throw new Error(data.error)
  }

  return data.data || {}
}

/**
 * Fetch confidence score correlation data
 * @param dateRange Optional date range filter
 * @returns Promise resolving to correlation data
 */
export async function fetchConfidenceCorrelation(
  dateRange?: AnalyticsDateRange
): Promise<ConfidenceCorrelationData> {
  const query = buildDateRangeQuery(dateRange)
  const url = `${ORCHESTRATOR_BASE_URL}/analytics/confidence-correlation${query}`

  const response = await fetchWithRetry(url)
  const data: AnalyticsAPIResponse<ConfidenceCorrelationData> = await response.json()

  if (data.error) {
    throw new Error(data.error)
  }

  return data.data || { scatter_data: [], correlation_coefficient: 0 }
}

/**
 * Fetch drawdown analysis data
 * @param dateRange Optional date range filter
 * @returns Promise resolving to drawdown data
 */
export async function fetchDrawdownData(
  dateRange?: AnalyticsDateRange
): Promise<DrawdownData> {
  const query = buildDateRangeQuery(dateRange)
  const url = `${ORCHESTRATOR_BASE_URL}/analytics/drawdown${query}`

  const response = await fetchWithRetry(url)
  const data: AnalyticsAPIResponse<DrawdownData> = await response.json()

  if (data.error) {
    throw new Error(data.error)
  }

  return data.data || {
    equity_curve: [],
    drawdown_periods: [],
    max_drawdown: {
      amount: 0,
      percentage: 0,
      start: null,
      end: null,
      recovery_duration_days: 0
    }
  }
}

/**
 * Fetch parameter evolution history
 * @param dateRange Optional date range filter
 * @returns Promise resolving to parameter change array
 */
export async function fetchParameterEvolution(
  dateRange?: AnalyticsDateRange
): Promise<ParameterChange[]> {
  const query = buildDateRangeQuery(dateRange)
  const url = `${ORCHESTRATOR_BASE_URL}/analytics/parameter-evolution${query}`

  const response = await fetchWithRetry(url)
  const data: AnalyticsAPIResponse<ParameterChange[]> = await response.json()

  if (data.error) {
    throw new Error(data.error)
  }

  return data.data || []
}

/**
 * Export trade history to CSV
 * @param dateRange Date range for export (required)
 * @returns Promise resolving to Blob containing CSV data
 */
export async function exportToCSV(
  dateRange: AnalyticsDateRange
): Promise<Blob> {
  if (!dateRange.start_date || !dateRange.end_date) {
    throw new Error('Start and end dates are required for CSV export')
  }

  const query = buildDateRangeQuery(dateRange)
  const url = `${ORCHESTRATOR_BASE_URL}/analytics/export/csv${query}`

  const response = await fetchWithTimeout(url, {}, 30000) // 30 second timeout for exports

  if (!response.ok) {
    throw new Error(`Export failed: HTTP ${response.status}`)
  }

  return await response.blob()
}

/**
 * Download CSV file to user's computer
 * @param blob CSV Blob data
 * @param filename Filename for download
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.style.display = 'none'

  document.body.appendChild(a)
  a.click()

  // Cleanup
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
