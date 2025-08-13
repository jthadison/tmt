'use client'

import { useState, useMemo } from 'react'
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
  TimeScale
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import 'chartjs-adapter-date-fns'
import { EquityPoint, ChartTimeframe } from '@/types/accountDetail'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale
)

/**
 * Props for EquityCurveChart component
 */
interface EquityCurveChartProps {
  /** Historical equity data points */
  equityHistory: EquityPoint[]
  /** Account name for chart title */
  accountName: string
  /** Show detailed chart features */
  showDetailed?: boolean
  /** Default timeframe to display */
  defaultTimeframe?: ChartTimeframe
  /** Chart height in pixels */
  height?: number
}

/**
 * Equity curve chart component with multiple timeframes and technical analysis
 * Displays account performance over time with drawdown overlay
 */
export function EquityCurveChart({
  equityHistory,
  accountName,
  showDetailed = false,
  defaultTimeframe = '1M',
  height = 400
}: EquityCurveChartProps) {
  const [selectedTimeframe, setSelectedTimeframe] = useState<ChartTimeframe>(defaultTimeframe)
  const [showDrawdown, setShowDrawdown] = useState(true)
  const [showBalance, setShowBalance] = useState(false)

  // Filter data based on selected timeframe
  const filteredData = useMemo(() => {
    const now = new Date()
    const cutoffDates: Record<ChartTimeframe, Date> = {
      '1D': new Date(now.getTime() - 24 * 60 * 60 * 1000),
      '1W': new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000),
      '1M': new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000),
      '3M': new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000),
      '6M': new Date(now.getTime() - 180 * 24 * 60 * 60 * 1000),
      '1Y': new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000),
      'ALL': new Date(0)
    }

    return equityHistory.filter(point => point.timestamp >= cutoffDates[selectedTimeframe])
  }, [equityHistory, selectedTimeframe])

  // Calculate performance metrics
  const performanceMetrics = useMemo(() => {
    if (filteredData.length === 0) return null

    const firstPoint = filteredData[0]
    const lastPoint = filteredData[filteredData.length - 1]
    const totalReturn = lastPoint.equity - firstPoint.equity
    const returnPercentage = (totalReturn / firstPoint.equity) * 100
    const maxEquity = Math.max(...filteredData.map(p => p.equity))
    const currentDrawdown = ((maxEquity - lastPoint.equity) / maxEquity) * 100
    const maxDrawdown = Math.max(...filteredData.map(p => p.drawdown))

    return {
      totalReturn,
      returnPercentage,
      maxEquity,
      currentDrawdown,
      maxDrawdown,
      daysTracked: filteredData.length
    }
  }, [filteredData])

  // Prepare chart data
  const chartData = useMemo(() => {
    const datasets = [
      {
        label: 'Equity',
        data: filteredData.map(point => ({
          x: point.timestamp,
          y: point.equity
        })),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4
      }
    ]

    if (showBalance) {
      datasets.push({
        label: 'Balance',
        data: filteredData.map(point => ({
          x: point.timestamp,
          y: point.balance
        })),
        borderColor: 'rgb(156, 163, 175)',
        backgroundColor: 'transparent',
        borderWidth: 1,
        fill: false,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4
      })
    }

    if (showDrawdown) {
      datasets.push({
        label: 'Drawdown',
        data: filteredData.map(point => ({
          x: point.timestamp,
          y: -point.drawdown
        })),
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderWidth: 1,
        fill: false,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4,
        yAxisID: 'drawdown'
      } as typeof datasets[0] & { yAxisID: string })
    }

    return { datasets }
  }, [filteredData, showBalance, showDrawdown])

  // Chart options
  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      title: {
        display: true,
        text: `${accountName} - Equity Curve`,
        color: 'rgb(255, 255, 255)',
        font: {
          size: 16,
          weight: 'bold' as const
        }
      },
      legend: {
        display: true,
        labels: {
          color: 'rgb(156, 163, 175)',
          usePointStyle: true
        }
      },
      tooltip: {
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        titleColor: 'rgb(255, 255, 255)',
        bodyColor: 'rgb(156, 163, 175)',
        borderColor: 'rgb(75, 85, 99)',
        borderWidth: 1,
        callbacks: {
          label: function(context: { dataset: { label?: string }, parsed: { y: number } }) {
            const label = context.dataset.label || ''
            const value = context.parsed.y
            if (label === 'Drawdown') {
              return `${label}: -$${Math.abs(value).toLocaleString()}`
            }
            return `${label}: $${value.toLocaleString()}`
          }
        }
      }
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: selectedTimeframe === '1D' ? 'hour' : 
                selectedTimeframe === '1W' ? 'day' :
                selectedTimeframe === '1M' ? 'day' : 'week'
        },
        grid: {
          color: 'rgba(75, 85, 99, 0.3)'
        },
        ticks: {
          color: 'rgb(156, 163, 175)'
        }
      },
      y: {
        position: 'left' as const,
        grid: {
          color: 'rgba(75, 85, 99, 0.3)'
        },
        ticks: {
          color: 'rgb(156, 163, 175)',
          callback: function(value: number) {
            return '$' + value.toLocaleString()
          }
        }
      },
      ...(showDrawdown && {
        drawdown: {
          type: 'linear' as const,
          position: 'right' as const,
          grid: {
            drawOnChartArea: false,
          },
          ticks: {
            color: 'rgb(239, 68, 68)',
            callback: function(value: number) {
              return '-$' + Math.abs(value).toLocaleString()
            }
          }
        }
      })
    }
  }), [accountName, selectedTimeframe, showDrawdown])

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  const timeframes: { value: ChartTimeframe; label: string }[] = [
    { value: '1D', label: '1D' },
    { value: '1W', label: '1W' },
    { value: '1M', label: '1M' },
    { value: '3M', label: '3M' },
    { value: '6M', label: '6M' },
    { value: '1Y', label: '1Y' },
    { value: 'ALL', label: 'All' }
  ]

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      {/* Chart Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <h3 className="text-lg font-semibold text-white">
          {showDetailed ? 'Performance Chart' : 'Equity Curve'}
        </h3>
        
        <div className="flex flex-wrap items-center gap-3">
          {/* Timeframe Selector */}
          <div className="flex bg-gray-700 rounded-lg p-1">
            {timeframes.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setSelectedTimeframe(value)}
                className={`
                  px-3 py-1 text-sm font-medium rounded transition-colors
                  ${selectedTimeframe === value
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-600'
                  }
                `}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Chart Options */}
          {showDetailed && (
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={showBalance}
                  onChange={(e) => setShowBalance(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-700 text-blue-600"
                />
                Balance
              </label>
              <label className="flex items-center gap-1 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={showDrawdown}
                  onChange={(e) => setShowDrawdown(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-700 text-blue-600"
                />
                Drawdown
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Performance Metrics */}
      {performanceMetrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 p-4 bg-gray-750 rounded-lg">
          <div>
            <div className="text-gray-400 text-sm">Total Return</div>
            <div className={`font-bold ${performanceMetrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(performanceMetrics.totalReturn)}
            </div>
            <div className={`text-xs ${performanceMetrics.returnPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {performanceMetrics.returnPercentage >= 0 ? '+' : ''}{performanceMetrics.returnPercentage.toFixed(2)}%
            </div>
          </div>
          <div>
            <div className="text-gray-400 text-sm">Peak Equity</div>
            <div className="text-white font-bold">
              {formatCurrency(performanceMetrics.maxEquity)}
            </div>
          </div>
          <div>
            <div className="text-gray-400 text-sm">Current DD</div>
            <div className="text-red-400 font-bold">
              -{performanceMetrics.currentDrawdown.toFixed(2)}%
            </div>
          </div>
          <div>
            <div className="text-gray-400 text-sm">Max DD</div>
            <div className="text-red-400 font-bold">
              {formatCurrency(performanceMetrics.maxDrawdown)}
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div style={{ height: `${height}px` }}>
        {filteredData.length > 0 ? (
          <Line 
            data={chartData} 
            // Chart.js options have complex typing, using unknown for compatibility
            options={chartOptions as unknown as Parameters<typeof Line>[0]['options']} 
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-gray-400 text-lg">No Data Available</div>
              <p className="text-gray-500 mt-2">No equity data for selected timeframe</p>
            </div>
          </div>
        )}
      </div>

      {/* Chart Footer */}
      {showDetailed && performanceMetrics && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="text-sm text-gray-400">
            Showing {performanceMetrics.daysTracked} data points over {selectedTimeframe} timeframe
          </div>
        </div>
      )}
    </div>
  )
}