/**
 * Sharpe Ratio Dashboard Component - Story 8.1
 * Main dashboard for risk-adjusted performance metrics
 */

'use client'

import React, { useEffect, useState } from 'react'
import { SharpeRatioData } from '@/types/analytics'
import { SharpeRatioGauge } from './SharpeRatioGauge'
import { RollingWindowCard } from './RollingWindowCard'
import { SharpeRatioHistoricalChart } from './SharpeRatioHistoricalChart'
import { RefreshCw, AlertCircle } from 'lucide-react'

interface LoadingSkeletonProps {}

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = () => {
  return (
    <div className="animate-pulse">
      <div className="h-8 bg-muted rounded w-1/3 mb-6" />
      <div className="h-64 bg-muted rounded mb-8" />
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-muted rounded" />
        ))}
      </div>
      <div className="h-96 bg-muted rounded" />
    </div>
  )
}

interface ErrorStateProps {
  error?: string
  onRetry?: () => void
}

const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
      <h3 className="text-lg font-semibold mb-2">Failed to Load Sharpe Ratio Data</h3>
      <p className="text-muted-foreground mb-4">
        {error || 'An error occurred while fetching analytics data'}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  )
}

export const SharpeRatioDashboard: React.FC = () => {
  const [sharpeData, setSharpeData] = useState<SharpeRatioData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchSharpeData = async (forceRefresh: boolean = false) => {
    try {
      setLoading(!sharpeData) // Only show loading skeleton on initial load
      setError(null)
      if (forceRefresh) setIsRefreshing(true)

      const url = forceRefresh
        ? '/api/analytics/sharpe-ratio?period=30d&refresh=true'
        : '/api/analytics/sharpe-ratio?period=30d'

      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`Failed to fetch Sharpe ratio data: ${response.statusText}`)
      }

      const data = await response.json()
      setSharpeData(data)
    } catch (err) {
      console.error('Error fetching Sharpe ratio data:', err)
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchSharpeData()

    // Refresh daily at midnight
    const now = new Date()
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
    const msUntilMidnight = tomorrow.getTime() - now.getTime()

    const midnightTimeout = setTimeout(() => {
      fetchSharpeData(true)

      // Set up daily interval after first midnight refresh
      const dailyInterval = setInterval(() => fetchSharpeData(true), 24 * 60 * 60 * 1000)

      return () => clearInterval(dailyInterval)
    }, msUntilMidnight)

    return () => clearTimeout(midnightTimeout)
  }, [])

  if (loading && !sharpeData) return <LoadingSkeleton />
  if (error && !sharpeData) return <ErrorState error={error} onRetry={() => fetchSharpeData()} />
  if (!sharpeData) return <ErrorState onRetry={() => fetchSharpeData()} />

  return (
    <div className="sharpe-ratio-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Sharpe Ratio Analysis</h2>
          <p className="text-sm text-muted-foreground mt-1">Risk-adjusted performance metrics</p>
        </div>
        <button
          onClick={() => fetchSharpeData(true)}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Refresh data"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* Current Sharpe Gauge */}
      <div className="gauge-section mb-8 p-6 bg-card rounded-lg border border-border">
        <SharpeRatioGauge
          value={sharpeData.currentSharpe}
          thresholdLevel={sharpeData.thresholdLevel}
          interpretation={sharpeData.interpretation}
        />
      </div>

      {/* Rolling Windows */}
      <div className="rolling-windows-section mb-8">
        <h3 className="text-lg font-semibold mb-4">Rolling Window Analysis</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(sharpeData.rollingWindows).map(([period, data]) => (
            <RollingWindowCard
              key={period}
              period={period}
              value={data.value}
              trend={data.trend}
              changePercent={data.changePercent}
            />
          ))}
        </div>
      </div>

      {/* Historical Chart */}
      <div className="historical-chart-section p-6 bg-card rounded-lg border border-border">
        <h3 className="text-lg font-semibold mb-4">90-Day Historical Trend</h3>
        <SharpeRatioHistoricalChart data={sharpeData.historicalData} />
      </div>

      {/* Metadata */}
      <div className="metadata mt-4 text-xs text-muted-foreground flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-4">
          <span>Risk-free rate: {(sharpeData.riskFreeRate * 100).toFixed(2)}%</span>
          <span>•</span>
          <span>Total trades: {sharpeData.totalTrades}</span>
        </div>
        <div>Last updated: {new Date(sharpeData.calculatedAt).toLocaleString()}</div>
      </div>

      {/* Error indicator (for background refresh errors) */}
      {error && sharpeData && (
        <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
            <span className="text-sm text-yellow-800 dark:text-yellow-200">
              Failed to refresh data. Showing cached results.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
