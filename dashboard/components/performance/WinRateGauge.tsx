/**
 * Win Rate Gauge Component
 * Circular gauge displaying win rate percentage with color zones
 */

'use client'

import React, { useMemo } from 'react'
import { Doughnut } from 'react-chartjs-2'
import { Chart as ChartJS, ArcElement, Tooltip } from 'chart.js'
import { cn } from '@/lib/utils'

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip)

interface WinRateGaugeProps {
  /** Win rate percentage (0-100) */
  winRate: number
  /** Optional size in pixels */
  size?: number
}

/**
 * Determine color zone based on win rate
 */
function getWinRateZone(winRate: number): {
  color: string
  label: string
  textColor: string
} {
  if (winRate >= 60) {
    return {
      color: '#4ade80', // green-400
      label: 'Excellent',
      textColor: 'text-green-400'
    }
  } else if (winRate >= 40) {
    return {
      color: '#fbbf24', // yellow-400
      label: 'Average',
      textColor: 'text-yellow-400'
    }
  } else {
    return {
      color: '#f87171', // red-400
      label: 'Needs Improvement',
      textColor: 'text-red-400'
    }
  }
}

/**
 * Win rate gauge component
 */
export function WinRateGauge({ winRate, size = 180 }: WinRateGaugeProps) {
  const zone = useMemo(() => getWinRateZone(winRate), [winRate])

  // Chart data for doughnut
  const chartData = useMemo(() => ({
    datasets: [
      {
        data: [winRate, 100 - winRate],
        backgroundColor: [zone.color, '#374151'], // gray-700
        borderWidth: 0,
        circumference: 180,
        rotation: 270
      }
    ]
  }), [winRate, zone.color])

  // Chart options
  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: true,
    cutout: '70%',
    plugins: {
      tooltip: {
        enabled: false
      }
    }
  }), [])

  return (
    <div className="bg-gray-800 rounded-lg p-6 flex flex-col items-center">
      <h3 className="text-lg font-semibold text-white mb-4">Win Rate</h3>

      {/* Gauge Chart */}
      <div className="relative" style={{ width: size, height: size }}>
        <Doughnut data={chartData} options={chartOptions} />

        {/* Center Text */}
        <div className="absolute inset-0 flex items-center justify-center" style={{ top: '25%' }}>
          <div className="text-center">
            <div className="text-4xl font-bold text-white">
              {winRate.toFixed(1)}%
            </div>
          </div>
        </div>
      </div>

      {/* Interpretation Label */}
      <div className={cn('mt-4 text-sm font-medium', zone.textColor)}>
        {zone.label}
      </div>

      {/* Color Legend */}
      <div className="mt-4 flex items-center space-x-4 text-xs text-gray-400">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 rounded-full bg-red-400" />
          <span>&lt;40%</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 rounded-full bg-yellow-400" />
          <span>40-60%</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 rounded-full bg-green-400" />
          <span>&gt;60%</span>
        </div>
      </div>
    </div>
  )
}

export default WinRateGauge
