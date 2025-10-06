/**
 * Rolling Window Card Component - Story 8.1
 * Displays Sharpe ratio for a specific time window with trend indicator
 */

'use client'

import React from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface RollingWindowCardProps {
  period: string
  value: number
  trend: 'up' | 'down' | 'stable'
  changePercent: number
}

export const RollingWindowCard: React.FC<RollingWindowCardProps> = ({
  period,
  value,
  trend,
  changePercent,
}) => {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-500" />
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-500" />
      default:
        return <Minus className="w-4 h-4 text-gray-500" />
    }
  }

  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'text-green-600 dark:text-green-400'
      case 'down':
        return 'text-red-600 dark:text-red-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  const getValueColor = (val: number) => {
    if (val >= 2.0) return 'text-emerald-700 dark:text-emerald-400'
    if (val >= 1.5) return 'text-green-600 dark:text-green-400'
    if (val >= 1.0) return 'text-yellow-600 dark:text-yellow-400'
    if (val >= 0.5) return 'text-orange-600 dark:text-orange-400'
    return 'text-red-600 dark:text-red-400'
  }

  return (
    <div className="rolling-window-card p-4 rounded-lg border border-border bg-card hover:shadow-md transition-shadow">
      {/* Period label */}
      <div className="text-xs font-medium text-muted-foreground mb-2 uppercase">{period}</div>

      {/* Value */}
      <div className={`text-2xl font-bold ${getValueColor(value)} mb-1`}>{value.toFixed(2)}</div>

      {/* Trend indicator */}
      <div className={`flex items-center gap-1 text-xs ${getTrendColor()}`}>
        {getTrendIcon()}
        <span className="font-medium">
          {changePercent > 0 ? '+' : ''}
          {changePercent.toFixed(1)}%
        </span>
      </div>

      {/* Trend label */}
      <div className="text-xs text-muted-foreground mt-1">
        {trend === 'up' && 'Improving'}
        {trend === 'down' && 'Declining'}
        {trend === 'stable' && 'Stable'}
      </div>
    </div>
  )
}
