/**
 * Equity Curve Chart Component
 * Line chart showing 30-day equity progression with peak/trough markers
 */

'use client'

import React, { useMemo } from 'react'
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
import { EquityCurveData } from '@/types/metrics'
import { format } from 'date-fns'
import { formatCurrency } from '@/utils/formatCurrency'

// Register Chart.js components
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

interface EquityCurveChartProps {
  /** Equity curve data */
  data: EquityCurveData
}

/**
 * Equity curve chart component
 */
export function EquityCurveChart({ data }: EquityCurveChartProps) {
  // Prepare chart data
  const chartData = useMemo(() => {
    const labels = data.points.map(p => format(new Date(p.date), 'MMM dd'))
    const equityValues = data.points.map(p => p.equity)

    // Find indices for peak and trough
    const peakIndex = data.peak ? data.points.findIndex(p => p.date === data.peak!.date) : -1
    const troughIndex = data.trough ? data.points.findIndex(p => p.date === data.trough!.date) : -1

    // Create point colors array (highlight peak and trough)
    const pointColors = data.points.map((_, index) => {
      if (index === peakIndex) return '#4ade80' // green for peak
      if (index === troughIndex) return '#f87171' // red for trough
      return 'transparent'
    })

    // Create point radius array (larger for peak and trough)
    const pointRadius = data.points.map((_, index) => {
      if (index === peakIndex || index === troughIndex) return 6
      return 0
    })

    return {
      labels,
      datasets: [
        {
          label: 'Equity',
          data: equityValues,
          borderColor: '#4ade80', // green-400
          backgroundColor: 'rgba(74, 222, 128, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: pointColors,
          pointBorderColor: pointColors,
          pointRadius: pointRadius,
          pointHoverRadius: pointRadius.map(r => r > 0 ? 8 : 3)
        }
      ]
    }
  }, [data])

  // Chart options
  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        backgroundColor: '#1f2937',
        titleColor: '#fff',
        bodyColor: '#9ca3af',
        borderColor: '#374151',
        borderWidth: 1,
        padding: 12,
        displayColors: false,
        callbacks: {
          label: (context: any) => {
            const point = data.points[context.dataIndex]
            const equity = formatCurrency(point.equity)
            const dailyPnL = formatCurrency(point.dailyPnL)
            const dailyLabel = point.dailyPnL >= 0 ? '+' + dailyPnL : dailyPnL

            return [
              `Equity: ${equity}`,
              `Daily P&L: ${dailyLabel}`
            ]
          },
          title: (context: any) => {
            return format(new Date(data.points[context[0].dataIndex].date), 'MMM dd, yyyy')
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          color: '#374151',
          display: true
        },
        ticks: {
          color: '#9ca3af',
          maxRotation: 45,
          minRotation: 45
        }
      },
      y: {
        grid: {
          color: '#374151',
          display: true
        },
        ticks: {
          color: '#9ca3af',
          callback: (value: any) => {
            // Format as $Xk for thousands
            if (value >= 1000) {
              return `$${(value / 1000).toFixed(1)}k`
            }
            return `$${value}`
          }
        }
      }
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false
    }
  }), [data.points])

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">30-Day Equity Curve</h3>

        {/* Drawdown Badge */}
        {data.currentDrawdown < 0 && (
          <div className="text-sm">
            <span className="text-gray-400">Current DD: </span>
            <span className="text-red-400 font-semibold">
              {data.currentDrawdown.toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      {/* Chart */}
      <div className="h-64">
        <Line data={chartData} options={chartOptions} />
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-center space-x-6 text-xs text-gray-400">
        {data.peak && (
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-green-400" />
            <span>Peak: {formatCurrency(data.peak.equity)}</span>
          </div>
        )}
        {data.trough && (
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-400" />
            <span>Trough: {formatCurrency(data.trough.equity)}</span>
          </div>
        )}
        {data.maxDrawdown < 0 && (
          <div className="flex items-center space-x-2">
            <span>Max DD: {data.maxDrawdown.toFixed(2)}%</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default EquityCurveChart
