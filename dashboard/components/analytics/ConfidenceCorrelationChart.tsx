/**
 * Confidence Correlation Chart Component (Story 12.2 - Task 7)
 *
 * Displays scatter plot showing correlation between confidence scores and outcomes
 */

'use client'

import React from 'react'
import { Scatter } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js'
import { ConfidenceCorrelationData, getCorrelationStrength } from '@/types/analytics122'

ChartJS.register(
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface ConfidenceCorrelationChartProps {
  data: ConfidenceCorrelationData | null
  loading: boolean
  error: Error | null
}

const SYMBOL_COLORS: Record<string, string> = {
  'EUR_USD': 'rgba(59, 130, 246, 0.6)',
  'GBP_USD': 'rgba(239, 68, 68, 0.6)',
  'USD_JPY': 'rgba(34, 197, 94, 0.6)',
  'AUD_USD': 'rgba(251, 146, 60, 0.6)',
  'USD_CHF': 'rgba(168, 85, 247, 0.6)',
}

/**
 * Confidence Correlation Chart Component
 */
export default function ConfidenceCorrelationChart({
  data,
  loading,
  error
}: ConfidenceCorrelationChartProps) {
  // Prepare chart data grouped by symbol
  const chartData = React.useMemo(() => {
    if (!data || !data.scatter_data.length) return null

    // Group data by symbol
    const symbolGroups = data.scatter_data.reduce((acc, point) => {
      if (!acc[point.symbol]) {
        acc[point.symbol] = []
      }
      acc[point.symbol].push({ x: point.confidence, y: point.outcome })
      return acc
    }, {} as Record<string, Array<{ x: number; y: number }>>)

    // Create dataset for each symbol
    const datasets = Object.entries(symbolGroups).map(([symbol, points]) => ({
      label: symbol.replace('_', '/'),
      data: points,
      backgroundColor: SYMBOL_COLORS[symbol] || 'rgba(156, 163, 175, 0.6)',
      pointRadius: 4,
      pointHoverRadius: 6,
    }))

    return { datasets }
  }, [data])

  const chartOptions: ChartOptions<'scatter'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          usePointStyle: true,
          padding: 15,
        }
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const x = context.parsed.x
            const y = context.parsed.y
            return [
              `Symbol: ${context.dataset.label}`,
              `Confidence: ${x.toFixed(1)}%`,
              `Outcome: ${y === 1 ? 'Win' : 'Loss'}`
            ]
          }
        }
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Confidence Score (%)',
          font: {
            size: 12,
            weight: 'bold',
          }
        },
        min: 0,
        max: 100,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        }
      },
      y: {
        title: {
          display: true,
          text: 'Outcome',
          font: {
            size: 12,
            weight: 'bold',
          }
        },
        min: -0.1,
        max: 1.1,
        ticks: {
          callback: (value) => value === 0 ? 'Loss' : value === 1 ? 'Win' : '',
          stepSize: 1,
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        }
      },
    },
  }

  const correlationStrength = data ? getCorrelationStrength(data.correlation_coefficient) : 'N/A'

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">
          Confidence Score vs Outcome Correlation
        </h2>
        {data && (
          <div className="text-right">
            <div className="text-sm text-gray-600">Correlation</div>
            <div className="text-lg font-bold text-gray-900">
              r = {data.correlation_coefficient.toFixed(3)}
            </div>
            <div className="text-xs text-gray-500">{correlationStrength}</div>
          </div>
        )}
      </div>

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
        <div className="h-96">
          <Scatter data={chartData} options={chartOptions} />
        </div>
      )}

      {!loading && !error && (!data || data.scatter_data.length === 0) && (
        <div className="h-96 flex flex-col items-center justify-center text-gray-500">
          <p>No correlation data available</p>
          <p className="text-sm mt-2">Try adjusting the date range filter</p>
        </div>
      )}

      {!loading && !error && data && data.scatter_data.length > 0 && (
        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">Interpretation</h3>
          <p className="text-sm text-blue-800">
            {data.correlation_coefficient > 0.7 && (
              <>Strong positive correlation: Higher confidence scores strongly predict winning trades.</>
            )}
            {data.correlation_coefficient >= 0.3 && data.correlation_coefficient <= 0.7 && (
              <>Moderate positive correlation: Higher confidence scores tend to predict winning trades.</>
            )}
            {data.correlation_coefficient > -0.3 && data.correlation_coefficient < 0.3 && (
              <>Weak correlation: Confidence scores show limited predictive power for trade outcomes.</>
            )}
            {data.correlation_coefficient < 0 && (
              <>Negative correlation: Higher confidence scores may predict losing trades - review signal generation.</>
            )}
          </p>
        </div>
      )}
    </div>
  )
}
