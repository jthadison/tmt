/**
 * Overfitting Trend Chart Component - Story 11.4, Task 6
 *
 * Historical overfitting score trend chart (30 days)
 */

'use client'

import React from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface OverfittingDataPoint {
  time: string
  score: number
  alert_level: 'normal' | 'warning' | 'critical'
}

interface OverfittingTrendChartProps {
  data: OverfittingDataPoint[]
  days?: number
  className?: string
}

/**
 * Line chart showing overfitting score trends over time
 *
 * @param data - Historical overfitting scores
 * @param days - Number of days displayed
 * @param className - Additional CSS classes
 * @returns Chart component
 */
export function OverfittingTrendChart({
  data,
  days = 30,
  className = ''
}: OverfittingTrendChartProps) {
  // Prepare chart data
  const labels = data.map(d => {
    const date = new Date(d.time)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  })

  const scores = data.map(d => d.score)

  // Color points based on alert level
  const pointColors = data.map(d => {
    switch (d.alert_level) {
      case 'critical':
        return 'rgb(239, 68, 68)'
      case 'warning':
        return 'rgb(234, 179, 8)'
      default:
        return 'rgb(34, 197, 94)'
    }
  })

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Overfitting Score',
        data: scores,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        pointBackgroundColor: pointColors,
        pointBorderColor: pointColors,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.3,
        fill: true
      }
    ]
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          color: 'rgb(156, 163, 175)'
        }
      },
      title: {
        display: false
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        backgroundColor: 'rgb(31, 41, 55)',
        titleColor: 'rgb(243, 244, 246)',
        bodyColor: 'rgb(209, 213, 219)',
        borderColor: 'rgb(75, 85, 99)',
        borderWidth: 1,
        callbacks: {
          label: (context: any) => {
            const score = context.parsed.y.toFixed(3)
            const alertLevel = data[context.dataIndex].alert_level
            return `Score: ${score} (${alertLevel})`
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(75, 85, 99, 0.3)'
        },
        ticks: {
          color: 'rgb(156, 163, 175)',
          maxRotation: 45,
          minRotation: 45
        }
      },
      y: {
        min: 0,
        max: 1.0,
        grid: {
          color: 'rgba(75, 85, 99, 0.3)'
        },
        ticks: {
          color: 'rgb(156, 163, 175)',
          callback: (value: any) => value.toFixed(1)
        }
      }
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false
    }
  }

  // Calculate statistics
  const avgScore = scores.length > 0
    ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(3)
    : '0.000'

  const maxScore = scores.length > 0
    ? Math.max(...scores).toFixed(3)
    : '0.000'

  const criticalCount = data.filter(d => d.alert_level === 'critical').length
  const warningCount = data.filter(d => d.alert_level === 'warning').length

  return (
    <div className={`bg-gray-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">
          Overfitting Trend ({days} Days)
        </h3>
        <div className="flex gap-4 text-sm">
          <div className="text-gray-400">
            Avg: <span className="text-white font-medium">{avgScore}</span>
          </div>
          <div className="text-gray-400">
            Max: <span className="text-white font-medium">{maxScore}</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64 mb-4">
        <Line data={chartData} options={options} />
      </div>

      {/* Threshold Lines Legend */}
      <div className="flex items-center justify-between text-xs text-gray-400 mb-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-12 h-0.5 bg-green-500" />
            <span>Acceptable (&lt; 0.3)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-12 h-0.5 bg-yellow-500" />
            <span>Warning (0.3-0.5)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-12 h-0.5 bg-red-500" />
            <span>Critical (&gt; 0.5)</span>
          </div>
        </div>
      </div>

      {/* Alert Summary */}
      <div className="flex gap-4 p-4 bg-gray-700/50 rounded">
        <div className="flex-1">
          <div className="text-xs text-gray-400 mb-1">Critical Alerts</div>
          <div className="text-2xl font-bold text-red-400">{criticalCount}</div>
        </div>
        <div className="flex-1">
          <div className="text-xs text-gray-400 mb-1">Warning Alerts</div>
          <div className="text-2xl font-bold text-yellow-400">{warningCount}</div>
        </div>
        <div className="flex-1">
          <div className="text-xs text-gray-400 mb-1">Normal Days</div>
          <div className="text-2xl font-bold text-green-400">
            {data.length - criticalCount - warningCount}
          </div>
        </div>
      </div>
    </div>
  )
}
