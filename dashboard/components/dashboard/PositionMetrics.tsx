'use client'

import { PositionMetrics as PositionData, ExposureMetrics } from '@/types/account'

/**
 * Props for PositionMetrics component
 */
interface PositionMetricsProps {
  /** Position count data */
  positions: PositionData
  /** Exposure data */
  exposure: ExposureMetrics
  /** Show detailed breakdown */
  detailed?: boolean
  /** Additional CSS classes */
  className?: string
}

/**
 * Component displaying position count and exposure metrics
 * Shows active positions, long/short breakdown, and exposure limits
 */
export function PositionMetrics({ 
  positions, 
  exposure, 
  detailed = false, 
  className = '' 
}: PositionMetricsProps) {
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const getExposureColorClass = (utilization: number): string => {
    if (utilization <= 50) return 'text-green-400'
    if (utilization <= 80) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getExposureBackgroundClass = (utilization: number): string => {
    if (utilization <= 50) return 'bg-green-500'
    if (utilization <= 80) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getDirectionIcon = (long: number, short: number): string => {
    if (long > short) return '↗' // Net long
    if (short > long) return '↘' // Net short
    return '↔' // Balanced
  }

  const getNetDirection = (long: number, short: number): string => {
    if (long > short) return 'Net Long'
    if (short > long) return 'Net Short'
    return 'Balanced'
  }

  if (detailed) {
    return (
      <div className={`space-y-4 ${className}`}>
        {/* Positions Section */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-300">Positions</div>
          
          {/* Total Active Positions */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Active</span>
            <span className="text-sm font-bold text-white">
              {positions.active}
            </span>
          </div>

          {/* Long/Short Breakdown */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-green-500/10 border border-green-500/20 rounded p-2">
              <div className="text-xs text-gray-400">Long</div>
              <div className="text-sm font-medium text-green-400">
                {positions.long}
              </div>
            </div>
            <div className="bg-red-500/10 border border-red-500/20 rounded p-2">
              <div className="text-xs text-gray-400">Short</div>
              <div className="text-sm font-medium text-red-400">
                {positions.short}
              </div>
            </div>
          </div>

          {/* Net Direction */}
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-500">Direction</span>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-300">
                {getNetDirection(positions.long, positions.short)}
              </span>
              <span className="text-sm">
                {getDirectionIcon(positions.long, positions.short)}
              </span>
            </div>
          </div>
        </div>

        {/* Exposure Section */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-300">Exposure</div>
          
          {/* Total Exposure */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Total</span>
            <span className="text-sm font-bold text-white">
              {formatCurrency(exposure.total)}
            </span>
          </div>

          {/* Exposure Progress Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Utilization</span>
              <span className={`font-medium ${getExposureColorClass(exposure.utilization)}`}>
                {exposure.utilization.toFixed(1)}%
              </span>
            </div>
            <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${getExposureBackgroundClass(exposure.utilization)}`}
                style={{ width: `${Math.min(100, exposure.utilization)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>{formatCurrency(exposure.total)}</span>
              <span>{formatCurrency(exposure.limit)}</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Compact display for account cards
  return (
    <div className={`space-y-2 ${className}`}>
      {/* Positions Row */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-400">Positions</span>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">
            {positions.active}
          </span>
          <div className="flex items-center gap-1 text-xs">
            <span className="text-green-400">{positions.long}L</span>
            <span className="text-gray-500">/</span>
            <span className="text-red-400">{positions.short}S</span>
          </div>
        </div>
      </div>

      {/* Exposure Row */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-400">Exposure</span>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">
            {formatCurrency(exposure.total)}
          </span>
          <span className={`text-xs ${getExposureColorClass(exposure.utilization)}`}>
            {exposure.utilization.toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Mini Exposure Bar */}
      <div className="w-full h-1 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${getExposureBackgroundClass(exposure.utilization)}`}
          style={{ width: `${Math.min(100, exposure.utilization)}%` }}
        />
      </div>
    </div>
  )
}

/**
 * Real-time position metrics with update animations
 */
export function AnimatedPositionMetrics({ 
  positions, 
  exposure, 
  previousPositions,
  previousExposure,
  className = '' 
}: {
  positions: PositionData
  exposure: ExposureMetrics
  previousPositions?: PositionData
  previousExposure?: ExposureMetrics
  className?: string
}) {
  const positionsChanged = previousPositions && (
    positions.active !== previousPositions.active ||
    positions.long !== previousPositions.long ||
    positions.short !== previousPositions.short
  )

  const exposureChanged = previousExposure && (
    exposure.total !== previousExposure.total ||
    exposure.utilization !== previousExposure.utilization
  )

  const hasChanges = positionsChanged || exposureChanged

  return (
    <div className={`
      ${className}
      ${hasChanges ? 'animate-pulse' : ''}
      transition-all duration-300
    `}>
      <PositionMetrics positions={positions} exposure={exposure} />
      
      {/* Change indicators */}
      {positionsChanged && (
        <div className="flex justify-center mt-1">
          <div className="w-1 h-1 bg-blue-400 rounded-full animate-ping"></div>
        </div>
      )}
    </div>
  )
}