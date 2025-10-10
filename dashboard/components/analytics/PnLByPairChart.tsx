/**
 * P&L By Pair Chart Component (Story 12.2 - Task 6)
 *
 * Displays profit/loss breakdown by currency pair using vertical bar chart
 */

'use client'

import React from 'react'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js'
import { PnLByPairData, CurrencyPair } from '@/types/analytics122'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

interface PnLByPairChartProps {
  data: PnLByPairData | null
  loading: boolean
  error: Error | null
}

const PAIRS: CurrencyPair[] = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CHF']

/**
 * P&L By Pair Chart Component
 */
export default function PnLByPairChart({
  data,
  loading,
  error
}: PnLByPairChartProps) {
  // Prepare chart data
  const chartData = React.useMemo(() => {
    if (!data) return null

    const pnlValues = PAIRS.map(pair => data[pair]?.total_pnl || 0)
    const colors = pnlValues.map(pnl => pnl >= 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)')
    const borderColors = pnlValues.map(pnl => pnl >= 0 ? 'rgba(34, 197, 94, 1)' : 'rgba(239, 68, 68, 1)')

    return {
      labels: PAIRS,
      datasets: [
        {
          label: 'P&L ($)',
          data: pnlValues,
          backgroundColor: colors,
          borderColor: borderColors,
          borderWidth: 2,
        },
      ],
    }
  }, [data])

  const chartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const pnl = context.parsed.y
            const pair = context.label
            const pairData = data?.[pair as CurrencyPair]

            if (!pairData) return `P&L: $${pnl.toFixed(2)}`

            return [
              `P&L: $${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}`,
              `Trades: ${pairData.trade_count}`,
              `Avg P&L: $${pairData.avg_pnl >= 0 ? '+' : ''}${pairData.avg_pnl.toFixed(2)}`
            ]
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
          font: {
            size: 11,
          }
        }
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          callback: (value) => `$${value}`,
        },
        title: {
          display: true,
          text: 'P&L ($)',
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
        Profit/Loss by Currency Pair
      </h2>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-red-800">
            <span className="font-semibold">Error:</span> {error.message}
          </p>
        </div>
      )}

      {loading && (
        <div className="h-80 flex items-center justify-center">
          <div className="animate-pulse text-gray-400">Loading chart...</div>
        </div>
      )}

      {!loading && !error && chartData && (
        <div className="h-80">
          <Bar data={chartData} options={chartOptions} />
        </div>
      )}

      {!loading && !error && data && Object.keys(data).length === 0 && (
        <div className="h-80 flex flex-col items-center justify-center text-gray-500">
          <p>No P&L data available</p>
          <p className="text-sm mt-2">Try adjusting the date range filter</p>
        </div>
      )}

      {!loading && !error && data && Object.keys(data).length > 0 && (
        <div className="mt-4 grid grid-cols-5 gap-2">
          {PAIRS.map(pair => {
            const pairData = data[pair]
            if (!pairData) return null

            const isPositive = pairData.total_pnl >= 0

            return (
              <div key={pair} className="text-center p-2 bg-gray-50 rounded">
                <div className="text-xs text-gray-600 font-medium">{pair.replace('_', '/')}</div>
                <div className={`text-sm font-bold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                  {isPositive ? '+' : ''}${pairData.total_pnl.toFixed(2)}
                </div>
                <div className="text-xs text-gray-500">
                  {pairData.trade_count} trades
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
