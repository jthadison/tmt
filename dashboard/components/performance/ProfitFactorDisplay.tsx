/**
 * Profit Factor Display Component
 * Displays profit factor with interpretation and color coding
 */

'use client'

import React, { useMemo } from 'react'
import { ProfitFactorDisplay as ProfitFactorData, ProfitFactorRating } from '@/types/metrics'
import { cn } from '@/lib/utils'

interface ProfitFactorDisplayProps {
  /** Profit factor value */
  profitFactor: number
}

/**
 * Get profit factor rating and styling
 */
function getProfitFactorRating(profitFactor: number): ProfitFactorData {
  if (profitFactor >= 2) {
    return {
      value: profitFactor,
      rating: 'excellent',
      color: '#4ade80', // green-400
      label: 'Excellent'
    }
  } else if (profitFactor >= 1.5) {
    return {
      value: profitFactor,
      rating: 'good',
      color: '#fbbf24', // yellow-400
      label: 'Good'
    }
  } else if (profitFactor >= 1) {
    return {
      value: profitFactor,
      rating: 'fair',
      color: '#fb923c', // orange-400
      label: 'Fair'
    }
  } else {
    return {
      value: profitFactor,
      rating: 'poor',
      color: '#f87171', // red-400
      label: 'Poor'
    }
  }
}

/**
 * Profit factor display component
 */
export function ProfitFactorDisplay({ profitFactor }: ProfitFactorDisplayProps) {
  const data = useMemo(() => getProfitFactorRating(profitFactor), [profitFactor])

  // Text color class based on rating
  const textColorClass = useMemo(() => {
    switch (data.rating) {
      case 'excellent':
        return 'text-green-400'
      case 'good':
        return 'text-yellow-400'
      case 'fair':
        return 'text-orange-400'
      case 'poor':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }, [data.rating])

  return (
    <div className="bg-gray-800 rounded-lg p-6 flex flex-col items-center justify-center">
      <h3 className="text-lg font-semibold text-white mb-4">Profit Factor</h3>

      {/* Large Number Display */}
      <div className={cn('text-5xl font-bold mb-4', textColorClass)}>
        {data.value.toFixed(2)}
      </div>

      {/* Interpretation Label */}
      <div className={cn('text-base font-medium mb-4', textColorClass)}>
        {data.label}
      </div>

      {/* Tooltip / Explanation */}
      <div className="text-xs text-gray-400 text-center max-w-xs">
        <p className="mb-2">Gross Profit ÷ Gross Loss</p>
        <div className="flex flex-col space-y-1 text-left">
          <div className="flex items-center justify-between">
            <span className="text-green-400">≥2.0</span>
            <span className="ml-2">Excellent</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-yellow-400">1.5-2.0</span>
            <span className="ml-2">Good</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-orange-400">1.0-1.5</span>
            <span className="ml-2">Fair</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-red-400">&lt;1.0</span>
            <span className="ml-2">Poor</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProfitFactorDisplay
