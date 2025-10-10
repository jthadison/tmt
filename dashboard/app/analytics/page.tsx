/**
 * Analytics Page (Story 12.2 - Task 3)
 *
 * Comprehensive performance analytics dashboard with 6 visualization components
 */

'use client'

import React, { useState, useEffect } from 'react'
import { AnalyticsDateRange } from '@/types/analytics122'
import {
  useSessionPerformance,
  usePatternPerformance,
  usePnLByPair,
  useConfidenceCorrelation,
  useDrawdownData,
  useParameterEvolution,
  useExportCSV,
  useAnalyticsPageState
} from '@/hooks/useAnalytics'
import SessionPerformanceCard from '@/components/analytics/SessionPerformanceCard'
import PatternPerformanceCard from '@/components/analytics/PatternPerformanceCard'
import PnLByPairChart from '@/components/analytics/PnLByPairChart'
import ConfidenceCorrelationChart from '@/components/analytics/ConfidenceCorrelationChart'
import DrawdownChart from '@/components/analytics/DrawdownChart'
import ParameterEvolutionTimeline from '@/components/analytics/ParameterEvolutionTimeline'
import { useAnalyticsAutoRefresh } from '@/hooks/useAnalyticsWebSocket'

/**
 * Analytics Page Component
 */
export default function AnalyticsPage() {
  const {
    dateRangePreset,
    setDateRangePreset,
    customDateRange,
    setCustomDateRange,
    autoRefresh,
    setAutoRefresh,
    refreshInterval,
    getDateRange
  } = useAnalyticsPageState()

  const [dateRange, setDateRange] = useState<AnalyticsDateRange | undefined>(getDateRange())

  // Update date range when preset changes
  useEffect(() => {
    setDateRange(getDateRange())
  }, [getDateRange])

  // Auto-refresh logic
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      setDateRange(getDateRange())
    }, refreshInterval * 1000)

    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, getDateRange])

  // Fetch all analytics data
  const sessionPerformance = useSessionPerformance(dateRange)
  const patternPerformance = usePatternPerformance(dateRange)
  const pnlByPair = usePnLByPair(dateRange)
  const confidenceCorrelation = useConfidenceCorrelation(dateRange)
  const drawdownData = useDrawdownData(dateRange)
  const parameterEvolution = useParameterEvolution(dateRange)

  const { exportCSV, loading: exportLoading, error: exportError } = useExportCSV()

  const handleExport = async () => {
    if (!dateRange) {
      alert('Please select a date range first')
      return
    }

    const result = await exportCSV(dateRange)
    if (result.success) {
      alert('CSV exported successfully!')
    } else {
      alert(`Export failed: ${result.error?.message}`)
    }
  }

  const handleRefreshAll = () => {
    sessionPerformance.refetch()
    patternPerformance.refetch()
    pnlByPair.refetch()
    confidenceCorrelation.refetch()
    drawdownData.refetch()
    parameterEvolution.refetch()
  }

  // WebSocket real-time updates
  const { isConnected: wsConnected } = useAnalyticsAutoRefresh(
    [
      sessionPerformance.refetch,
      patternPerformance.refetch,
      pnlByPair.refetch,
      confidenceCorrelation.refetch,
      drawdownData.refetch,
      parameterEvolution.refetch,
    ],
    true // Enable WebSocket updates
  )

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Performance Analytics
            </h1>
            <p className="text-gray-600">
              Comprehensive analysis of trading performance across sessions, patterns, and currency pairs
            </p>
          </div>

          {/* WebSocket Status */}
          <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg shadow-sm border border-gray-200">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
            <span className="text-xs text-gray-600">
              {wsConnected ? 'Live Updates Active' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Controls */}
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            {/* Date Range Picker */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Date Range:</label>
              <select
                value={dateRangePreset}
                onChange={(e) => setDateRangePreset(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="90d">Last 90 Days</option>
                <option value="custom">Custom Range</option>
              </select>
            </div>

            {/* Custom Date Range Inputs */}
            {dateRangePreset === 'custom' && (
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={customDateRange?.start_date.split('T')[0] || ''}
                  onChange={(e) => {
                    const start = new Date(e.target.value)
                    start.setHours(0, 0, 0, 0)
                    setCustomDateRange({
                      start_date: start.toISOString(),
                      end_date: customDateRange?.end_date || new Date().toISOString()
                    })
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-gray-500">to</span>
                <input
                  type="date"
                  value={customDateRange?.end_date.split('T')[0] || ''}
                  onChange={(e) => {
                    const end = new Date(e.target.value)
                    end.setHours(23, 59, 59, 999)
                    setCustomDateRange({
                      start_date: customDateRange?.start_date || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
                      end_date: end.toISOString()
                    })
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            {/* Auto-refresh Toggle */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Auto-refresh:</label>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  autoRefresh
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {autoRefresh ? 'ON (30s)' : 'OFF'}
              </button>
            </div>

            {/* Manual Refresh Button */}
            <button
              onClick={handleRefreshAll}
              className="px-4 py-2 bg-blue-500 text-white rounded-md text-sm font-medium hover:bg-blue-600 transition-colors"
            >
              ↻ Refresh All
            </button>

            {/* Export CSV Button */}
            <button
              onClick={handleExport}
              disabled={exportLoading || !dateRange}
              className="px-4 py-2 bg-green-500 text-white rounded-md text-sm font-medium hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {exportLoading ? 'Exporting...' : '↓ Export CSV'}
            </button>
          </div>

          {exportError && (
            <div className="mt-2 text-sm text-red-600">
              Export error: {exportError.message}
            </div>
          )}
        </div>

        {/* Analytics Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Row 1 */}
          <SessionPerformanceCard
            data={sessionPerformance.data}
            loading={sessionPerformance.loading}
            error={sessionPerformance.error}
          />

          <PatternPerformanceCard
            data={patternPerformance.data}
            loading={patternPerformance.loading}
            error={patternPerformance.error}
          />

          {/* Row 2 */}
          <PnLByPairChart
            data={pnlByPair.data}
            loading={pnlByPair.loading}
            error={pnlByPair.error}
          />

          <ConfidenceCorrelationChart
            data={confidenceCorrelation.data}
            loading={confidenceCorrelation.loading}
            error={confidenceCorrelation.error}
          />

          {/* Row 3 */}
          <div className="lg:col-span-2">
            <DrawdownChart
              data={drawdownData.data}
              loading={drawdownData.loading}
              error={drawdownData.error}
            />
          </div>

          {/* Row 4 */}
          <div className="lg:col-span-2">
            <ParameterEvolutionTimeline
              data={parameterEvolution.data}
              loading={parameterEvolution.loading}
              error={parameterEvolution.error}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}
