'use client'

import { DrawdownMetrics } from '@/types/account'

/**
 * Props for DrawdownBar component
 */
interface DrawdownBarProps {
  /** Drawdown metrics to visualize */
  drawdown: DrawdownMetrics
  /** Show detailed tooltip on hover */
  showTooltip?: boolean
  /** Additional CSS classes */
  className?: string
}

/**
 * Progress bar component for drawdown visualization
 * Color-coded based on risk levels with hover tooltips
 */
export function DrawdownBar({ 
  drawdown, 
  showTooltip = true, 
  className = '' 
}: DrawdownBarProps) {
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const getProgressBarColor = (percentage: number): string => {
    if (percentage <= 30) return 'bg-green-500'
    if (percentage <= 50) return 'bg-yellow-500'
    if (percentage <= 80) return 'bg-orange-500'
    return 'bg-red-500'
  }


  const getRiskLevel = (percentage: number): string => {
    if (percentage <= 30) return 'Low Risk'
    if (percentage <= 50) return 'Moderate Risk'
    if (percentage <= 80) return 'High Risk'
    return 'Critical Risk'
  }

  const getRiskIcon = (percentage: number): string => {
    if (percentage <= 30) return '🟢'
    if (percentage <= 50) return '🟡'
    if (percentage <= 80) return '🟠'
    return '🔴'
  }

  // Ensure percentage is between 0 and 100
  const safePercentage = Math.max(0, Math.min(100, drawdown.percentage))

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-400">Drawdown</span>
        <span className="text-sm font-medium text-white">
          {safePercentage.toFixed(1)}%
        </span>
      </div>

      {/* Progress Bar Container */}
      <div className="relative group">
        {/* Background Track */}
        <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
          {/* Progress Fill */}
          <div
            className={`
              h-full transition-all duration-300 ease-out
              ${getProgressBarColor(safePercentage)}
            `}
            style={{ width: `${safePercentage}%` }}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={safePercentage}
            aria-label={`Drawdown: ${safePercentage.toFixed(1)}% of maximum`}
          />
        </div>

        {/* Risk Markers */}
        <div className="absolute top-0 w-full h-2 flex">
          {/* 50% marker */}
          <div 
            className="absolute top-0 h-2 w-0.5 bg-white/30"
            style={{ left: '50%' }}
            aria-hidden="true"
          />
          {/* 80% marker */}
          <div 
            className="absolute top-0 h-2 w-0.5 bg-white/50"
            style={{ left: '80%' }}
            aria-hidden="true"
          />
        </div>

        {/* Tooltip on Hover */}
        {showTooltip && (
          <div className="
            absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2
            bg-gray-900 border border-gray-600 rounded-lg px-3 py-2
            opacity-0 group-hover:opacity-100 transition-opacity duration-200
            pointer-events-none z-10 shadow-xl
            min-w-max
          ">
            <div className="text-sm text-white space-y-1">
              <div className="flex items-center gap-2 font-medium">
                <span>{getRiskIcon(safePercentage)}</span>
                <span>{getRiskLevel(safePercentage)}</span>
              </div>
              <div className="text-xs text-gray-300 space-y-0.5">
                <div>Current: {formatCurrency(drawdown.current)}</div>
                <div>Maximum: {formatCurrency(drawdown.maximum)}</div>
                <div>Percentage: {safePercentage.toFixed(2)}%</div>
                <div>Remaining: {formatCurrency(drawdown.maximum - drawdown.current)}</div>
              </div>
            </div>
            {/* Tooltip Arrow */}
            <div className="
              absolute top-full left-1/2 transform -translate-x-1/2
              w-0 h-0 border-l-4 border-r-4 border-t-4
              border-l-transparent border-r-transparent border-t-gray-600
            "></div>
          </div>
        )}
      </div>

      {/* Current vs Maximum Display */}
      <div className="flex justify-between items-center text-xs">
        <span className="text-gray-500">
          {formatCurrency(drawdown.current)}
        </span>
        <span className="text-gray-500">
          / {formatCurrency(drawdown.maximum)}
        </span>
      </div>
    </div>
  )
}

/**
 * Compact drawdown bar for dense layouts
 */
export function CompactDrawdownBar({ 
  drawdown, 
  className = '' 
}: {
  drawdown: DrawdownMetrics
  className?: string
}) {
  const getProgressBarColor = (percentage: number): string => {
    if (percentage <= 50) return 'bg-green-500'
    if (percentage <= 80) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const safePercentage = Math.max(0, Math.min(100, drawdown.percentage))

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-xs text-gray-400 min-w-0 flex-shrink-0">DD</span>
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${getProgressBarColor(safePercentage)}`}
          style={{ width: `${safePercentage}%` }}
        />
      </div>
      <span className="text-xs text-white min-w-0 flex-shrink-0">
        {safePercentage.toFixed(0)}%
      </span>
    </div>
  )
}