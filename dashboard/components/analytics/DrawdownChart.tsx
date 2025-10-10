/**
 * Drawdown Chart Component (Story 12.2 - Task 8)
 *
 * Displays equity curve with drawdown periods and maximum drawdown annotation
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
  Filler,
  ChartOptions
} from 'chart.js'
import { DrawdownData } from '@/types/analytics122'
import { format } from 'date-fns'

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

interface DrawdownChartProps {
  data: DrawdownData | null
  loading: boolean
  error: Error | null
}

/**
 * Drawdown Chart Component
 */
export default function DrawdownChart({
  data,
  loading,
  error
}: DrawdownChartProps) {
  // Prepare chart data
  const chartData = React.useMemo(() => {
    if (!data || !data.equity_curve.length) return null

    const labels = data.equity_curve.map(point =>
      format(new Date(point.time), 'MMM dd, HH:mm')
    )
    const equityValues = data.equity_curve.map(point => point.equity)
    const startingEquity = equityValues[0] || 100000

    // Color based on above/below starting equity
    const backgroundColors = equityValues.map(equity =>
      equity >= startingEquity
        ? 'rgba(34, 197, 94, 0.1)'
        : 'rgba(239, 68, 68, 0.1)'
    )

    return {
      labels,
      datasets: [
        {
          label: 'Account Equity',
          data: equityValues,
          borderColor: 'rgba(59, 130, 246, 1)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 5,
        },
        {
          label: 'Starting Balance',
          data: new Array(equityValues.length).fill(startingEquity),
          borderColor: 'rgba(156, 163, 175, 0.5)',
          borderDash: [5, 5],
          borderWidth: 2,
          fill: false,
          pointRadius: 0,
          pointHoverRadius: 0,
        }
      ],
    }
  }, [data])

  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const value = context.parsed.y
            return `${context.dataset.label}: $${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
          font: {
            size: 10,
          }
        }
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          callback: (value) => `$${value.toLocaleString()}`,
        },
        title: {
          display: true,
          text: 'Account Equity ($)',
          font: {
            size: 12,
            weight: 'bold',
          }
        }
      },
    },
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Equity Curve & Drawdown Analysis
      </h2>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-red-800">
            <span className="font-semibold">Error:</span> {error.message}
          </p>
        </div>
      )}

      {loading && (
        <div className="h-96 flex items-center justify-center">
          <div className="animate-pulse text-gray-400">Loading chart...</div>
        </div>
      )}

      {!loading && !error && chartData && (
        <>
          <div className="h-96 mb-4">
            <Line data={chartData} options={chartOptions} />
          </div>

          {data && data.max_drawdown && data.max_drawdown.amount < 0 && (
            <div className="grid grid-cols-2 gap-4 p-4 bg-red-50 rounded-lg border border-red-200">
              <div>
                <h3 className="text-sm font-semibold text-red-900 mb-2">
                  Maximum Drawdown
                </h3>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-sm text-red-700">Amount:</span>
                    <span className="text-sm font-bold text-red-900">
                      ${data.max_drawdown.amount.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-red-700">Percentage:</span>
                    <span className="text-sm font-bold text-red-900">
                      {data.max_drawdown.percentage.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-red-900 mb-2">
                  Drawdown Period
                </h3>
                <div className="space-y-1">
                  {data.max_drawdown.start && (
                    <div className="text-xs text-red-700">
                      <span className="font-medium">Start:</span>{' '}
                      {format(new Date(data.max_drawdown.start), 'MMM dd, yyyy HH:mm')}
                    </div>
                  )}
                  {data.max_drawdown.end && (
                    <div className="text-xs text-red-700">
                      <span className="font-medium">End:</span>{' '}
                      {format(new Date(data.max_drawdown.end), 'MMM dd, yyyy HH:mm')}
                    </div>
                  )}
                  {data.max_drawdown.recovery_duration_days > 0 && (
                    <div className="text-xs text-red-700">
                      <span className="font-medium">Recovery:</span>{' '}
                      {data.max_drawdown.recovery_duration_days} days
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {data && data.drawdown_periods.length > 0 && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">
                Drawdown Summary
              </h3>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-xs text-gray-600">Total Drawdowns</div>
                  <div className="text-lg font-bold text-gray-900">
                    {data.drawdown_periods.length}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-600">Average Drawdown</div>
                  <div className="text-lg font-bold text-gray-900">
                    ${(data.drawdown_periods.reduce((sum, dd) => sum + Math.abs(dd.amount), 0) / data.drawdown_periods.length).toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-600">Current Equity</div>
                  <div className="text-lg font-bold text-gray-900">
                    ${data.equity_curve[data.equity_curve.length - 1]?.equity.toFixed(2) || '0.00'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {!loading && !error && (!data || data.equity_curve.length === 0) && (
        <div className="h-96 flex flex-col items-center justify-center text-gray-500">
          <p>No equity data available</p>
          <p className="text-sm mt-2">Try adjusting the date range filter</p>
        </div>
      )}
    </div>
  )
}
