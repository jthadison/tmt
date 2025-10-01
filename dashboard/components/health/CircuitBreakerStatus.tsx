/**
 * CircuitBreakerStatus Component
 * Displays circuit breaker thresholds with progress bars
 */

'use client'

import React from 'react'
import { CircuitBreakerStatus as CircuitBreakerStatusType } from '@/types/health'

interface CircuitBreakerStatusProps {
  circuitBreaker: CircuitBreakerStatusType
}

interface ProgressBarProps {
  label: string
  current: number
  threshold: number
  limit: number
  unit: string
  tooltip: string
}

/**
 * Progress bar with threshold and limit markers
 */
function ThresholdProgressBar({
  label,
  current,
  threshold,
  limit,
  unit,
  tooltip
}: ProgressBarProps) {
  // Calculate percentages based on limit
  const currentPercent = Math.min((current / limit) * 100, 100)
  const thresholdPercent = (threshold / limit) * 100

  // Determine color based on value
  const barColor =
    current < threshold
      ? 'bg-green-500'
      : current < limit
      ? 'bg-yellow-500'
      : 'bg-red-500'

  // Format display values
  const formatValue = (val: number) => {
    if (unit === '$') {
      return `$${val.toFixed(2)}`
    } else if (unit === '%') {
      return `${val.toFixed(1)}%`
    }
    return val.toString()
  }

  return (
    <div className="space-y-2" title={tooltip}>
      {/* Label and values */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-300">{label}</span>
        <span className="text-xs text-gray-400">
          {formatValue(current)} / {formatValue(threshold)} / {formatValue(limit)}
        </span>
      </div>

      {/* Progress bar container */}
      <div className="relative h-3 bg-gray-700 rounded-full overflow-hidden">
        {/* Threshold marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-gray-500 z-10"
          style={{ left: `${thresholdPercent}%` }}
          aria-label="Threshold marker"
        />

        {/* Current value bar */}
        <div
          className={`h-full transition-all duration-500 ${barColor} rounded-full`}
          style={{ width: `${currentPercent}%` }}
          role="progressbar"
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={limit}
          aria-label={`${label}: ${formatValue(current)}`}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-green-500 rounded-full" />
          <span>Normal</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-yellow-500 rounded-full" />
          <span>Warning</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-red-500 rounded-full" />
          <span>Critical</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Circuit breaker status display
 */
export default function CircuitBreakerStatus({
  circuitBreaker
}: CircuitBreakerStatusProps) {
  return (
    <div
      className="bg-gray-800 rounded-lg p-4 border border-gray-700 space-y-4"
      role="region"
      aria-label="Circuit breaker status"
    >
      <h3 className="text-sm font-semibold text-white mb-4">
        Circuit Breaker Thresholds
      </h3>

      {/* Max Drawdown */}
      <ThresholdProgressBar
        label="Max Drawdown"
        current={circuitBreaker.max_drawdown.current}
        threshold={circuitBreaker.max_drawdown.threshold}
        limit={circuitBreaker.max_drawdown.limit}
        unit="%"
        tooltip="Maximum portfolio drawdown percentage before circuit breaker triggers"
      />

      {/* Daily Loss */}
      <ThresholdProgressBar
        label="Daily Loss"
        current={circuitBreaker.daily_loss.current}
        threshold={circuitBreaker.daily_loss.threshold}
        limit={circuitBreaker.daily_loss.limit}
        unit="$"
        tooltip="Total daily loss amount before circuit breaker triggers"
      />

      {/* Consecutive Losses */}
      <ThresholdProgressBar
        label="Consecutive Losses"
        current={circuitBreaker.consecutive_losses.current}
        threshold={circuitBreaker.consecutive_losses.threshold}
        limit={circuitBreaker.consecutive_losses.limit}
        unit=""
        tooltip="Number of consecutive losing trades before circuit breaker triggers"
      />
    </div>
  )
}
