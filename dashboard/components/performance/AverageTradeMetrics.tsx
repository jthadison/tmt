/**
 * Average Trade Metrics Component
 * Displays average trade statistics with period-over-period comparison
 */

'use client'

import React, { useMemo } from 'react'
import { PerformanceMetrics } from '@/types/metrics'
import { formatCurrency } from '@/utils/formatCurrency'
import { cn } from '@/lib/utils'

interface AverageTradeMetricsProps {
  /** Current period metrics */
  current: PerformanceMetrics
  /** Previous period metrics for comparison (optional) */
  previous?: PerformanceMetrics | null
}

/**
 * Calculate percentage change between periods
 */
function calculateChange(current: number, previous: number | undefined): {
  percentage: number
  isPositive: boolean
  arrow: string
} {
  if (!previous || previous === 0) {
    return { percentage: 0, isPositive: false, arrow: '' }
  }

  const change = ((current - previous) / Math.abs(previous)) * 100
  const isPositive = change > 0

  return {
    percentage: Math.abs(change),
    isPositive,
    arrow: isPositive ? '↑' : '↓'
  }
}

/**
 * Format duration from hours to human-readable
 */
function formatDuration(hours: number): string {
  if (hours < 1) {
    const minutes = Math.round(hours * 60)
    return `${minutes}m`
  }

  const wholeHours = Math.floor(hours)
  const minutes = Math.round((hours - wholeHours) * 60)

  if (minutes === 0) {
    return `${wholeHours}h`
  }

  return `${wholeHours}h ${minutes}m`
}

/**
 * Metric card component
 */
function MetricCard({
  title,
  value,
  previous,
  colorClass,
  isBetter
}: {
  title: string
  value: string
  previous?: number
  colorClass: string
  isBetter?: (change: number) => boolean
}) {
  const change = useMemo(() => {
    if (previous === undefined) return null

    const currentNum = parseFloat(value.replace(/[$,]/g, ''))
    return calculateChange(currentNum, previous)
  }, [value, previous])

  const showComparison = change && change.percentage !== 0

  // Determine if change is good (green) or bad (red)
  const isGoodChange = useMemo(() => {
    if (!change || !isBetter) return false
    return isBetter(change.isPositive ? change.percentage : -change.percentage)
  }, [change, isBetter])

  return (
    <div className="flex flex-col">
      <div className="text-sm text-gray-400 mb-1">{title}</div>
      <div className={cn('text-2xl font-bold', colorClass)}>{value}</div>
      {showComparison && (
        <div className={cn(
          'text-xs mt-1 flex items-center space-x-1',
          isGoodChange ? 'text-green-400' : 'text-red-400'
        )}>
          <span>{change!.arrow}</span>
          <span>{change!.percentage.toFixed(1)}%</span>
        </div>
      )}
    </div>
  )
}

/**
 * Average trade metrics component
 */
export function AverageTradeMetrics({ current, previous }: AverageTradeMetricsProps) {
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-6">Average Trade Metrics</h3>

      <div className="grid grid-cols-2 gap-6">
        {/* Average Win */}
        <MetricCard
          title="Average Win"
          value={formatCurrency(current.avgWin)}
          previous={previous?.avgWin}
          colorClass="text-green-400"
          isBetter={(change) => change > 0}
        />

        {/* Average Loss */}
        <MetricCard
          title="Average Loss"
          value={formatCurrency(current.avgLoss)}
          previous={previous?.avgLoss}
          colorClass="text-red-400"
          isBetter={(change) => change < 0} // Lower loss is better
        />

        {/* Average R:R */}
        <MetricCard
          title="Average R:R"
          value={`${current.avgRiskReward.toFixed(2)}:1`}
          previous={previous?.avgRiskReward}
          colorClass="text-blue-400"
          isBetter={(change) => change > 0}
        />

        {/* Average Duration */}
        <MetricCard
          title="Avg Duration"
          value={formatDuration(current.avgDurationHours)}
          previous={previous?.avgDurationHours}
          colorClass="text-gray-300"
          isBetter={(change) => change < 0} // Shorter duration can be better
        />
      </div>

      {/* Period Comparison Note */}
      {previous && (
        <div className="mt-4 pt-4 border-t border-gray-700 text-xs text-gray-400 text-center">
          Compared to previous period
        </div>
      )}
    </div>
  )
}

export default AverageTradeMetrics
