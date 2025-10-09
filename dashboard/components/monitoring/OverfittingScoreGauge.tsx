/**
 * Overfitting Score Gauge Component - Story 11.4, Task 6
 *
 * Real-time overfitting score gauge with green/yellow/red zones
 */

'use client'

import React from 'react'
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

interface OverfittingScoreGaugeProps {
  score: number
  alertLevel: 'normal' | 'warning' | 'critical'
  lastUpdated?: string
  className?: string
}

/**
 * Visual gauge for overfitting score
 *
 * @param score - Overfitting score (0-1+)
 * @param alertLevel - Current alert level
 * @param lastUpdated - Last calculation timestamp
 * @param className - Additional CSS classes
 * @returns Gauge component
 */
export function OverfittingScoreGauge({
  score,
  alertLevel,
  lastUpdated,
  className = ''
}: OverfittingScoreGaugeProps) {
  // Calculate gauge position (0-100%)
  const position = Math.min(score * 100, 100)

  // Determine zone colors
  const getZoneColor = () => {
    if (score < 0.3) return 'bg-green-500'
    if (score < 0.5) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getAlertIcon = () => {
    switch (alertLevel) {
      case 'normal':
        return <CheckCircle className="w-8 h-8 text-green-400" />
      case 'warning':
        return <AlertTriangle className="w-8 h-8 text-yellow-400" />
      case 'critical':
        return <XCircle className="w-8 h-8 text-red-400" />
    }
  }

  const getAlertText = () => {
    if (score < 0.3) return 'Acceptable'
    if (score < 0.5) return 'Warning: Potential Overfitting'
    return 'Critical: Severe Overfitting'
  }

  return (
    <div className={`bg-gray-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Overfitting Score</h3>
        {getAlertIcon()}
      </div>

      {/* Score Display */}
      <div className="text-center mb-6">
        <div className="text-5xl font-bold text-white mb-2">
          {score.toFixed(3)}
        </div>
        <div className={`text-sm font-medium ${
          alertLevel === 'critical' ? 'text-red-400' :
          alertLevel === 'warning' ? 'text-yellow-400' :
          'text-green-400'
        }`}>
          {getAlertText()}
        </div>
      </div>

      {/* Gauge Bar */}
      <div className="relative w-full h-8 bg-gray-700 rounded-full overflow-hidden mb-4">
        {/* Zone backgrounds */}
        <div className="absolute inset-0 flex">
          <div className="w-[30%] bg-green-900/30" />
          <div className="w-[20%] bg-yellow-900/30" />
          <div className="w-[50%] bg-red-900/30" />
        </div>

        {/* Threshold markers */}
        <div className="absolute top-0 left-[30%] w-0.5 h-full bg-gray-500" />
        <div className="absolute top-0 left-[50%] w-0.5 h-full bg-gray-500" />

        {/* Score indicator */}
        <div
          className={`absolute top-0 left-0 h-full ${getZoneColor()} transition-all duration-500`}
          style={{ width: `${position}%` }}
        />

        {/* Current position marker */}
        <div
          className="absolute top-0 h-full w-1 bg-white shadow-lg transition-all duration-500"
          style={{ left: `${position}%` }}
        />
      </div>

      {/* Zone Labels */}
      <div className="flex justify-between text-xs text-gray-400 mb-4">
        <span>0.0 (Good)</span>
        <span>0.3</span>
        <span>0.5</span>
        <span>1.0+</span>
      </div>

      {/* Legend */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-gray-300">Acceptable</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className="text-gray-300">Warning</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-gray-300">Critical</span>
        </div>
      </div>

      {/* Last Updated */}
      {lastUpdated && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="text-xs text-gray-400">
            Last updated: {new Date(lastUpdated).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  )
}
