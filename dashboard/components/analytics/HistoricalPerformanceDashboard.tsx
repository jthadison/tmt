/**
 * Historical Performance Dashboard Component - AC2
 * Story 9.6: Historical performance dashboard with configurable time periods and metrics
 * 
 * Displays historical trading performance with customizable date ranges and granularity
 */

'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Calendar, TrendingUp, TrendingDown, BarChart2, PieChart, Download, Filter } from 'lucide-react'
import { motion } from 'framer-motion'
import { MonthlyBreakdown, AnalyticsQuery } from '@/types/performanceAnalytics'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'
import { formatCurrency, formatPercent } from '@/utils/formatters'

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface HistoricalPerformanceDashboardProps {
  accountIds: string[]
  initialDateRange?: { start: Date; end: Date }
  onExport?: (data: any) => void
}

type ViewMode = 'cumulative' | 'daily' | 'weekly' | 'monthly'
type ChartType = 'line' | 'bar' | 'area'

export default function HistoricalPerformanceDashboard({
  accountIds,
  initialDateRange,
  onExport
}: HistoricalPerformanceDashboardProps) {
  // State
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState(initialDateRange || {
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end: new Date()
  })
  const [viewMode, setViewMode] = useState<ViewMode>('cumulative')
  const [chartType, setChartType] = useState<ChartType>('line')
  const [performanceData, setPerformanceData] = useState<{
    daily: MonthlyBreakdown[]
    weekly: MonthlyBreakdown[]
    monthly: MonthlyBreakdown[]
  } | null>(null)
  const [setDateRangePreset] = useState<(preset: string) => void>(() => () => {})
  const [PerformanceMetrics] = useState<any>(null)
  const [selectedMetric, setSelectedMetric] = useState<'pnl' | 'return' | 'trades' | 'winRate'>('pnl')

  // Fetch historical performance data
  const fetchPerformanceData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const query: AnalyticsQuery = {
        accountIds,
        dateRange,
        granularity: viewMode === 'cumulative' ? 'day' : viewMode === 'daily' ? 'day' : viewMode === 'weekly' ? 'week' : 'month',
        metrics: ['pnl', 'return', 'trades', 'winRate', 'drawdown', 'sharpeRatio']
      }

      const data = await performanceAnalyticsService.getHistoricalPerformance(query)
      setPerformanceData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch performance data')
    } finally {
      setLoading(false)
    }
  }, [accountIds, dateRange, viewMode])

  useEffect(() => {
    fetchPerformanceData()
  }, [fetchPerformanceData])

  // Process data for charts
  const chartData = useMemo(() => {
    if (!performanceData) return null

    const data = viewMode === 'monthly' ? performanceData.monthly :
                 viewMode === 'weekly' ? performanceData.weekly : performanceData.daily

    const labels = data.map(d => d.month)
    const metricData = data.map(d => {
      switch (selectedMetric) {
        case 'pnl': return d.pnl
        case 'return': return d.return
        case 'trades': return d.trades
        case 'winRate': return d.winRate
        default: return d.pnl
      }
    })

    // Calculate cumulative if needed
    let processedData = [...metricData]
    if (viewMode === 'cumulative' && selectedMetric === 'pnl') {
      let cumulative = 0
      processedData = metricData.map(value => {
        cumulative += value
        return cumulative
      })
    }

    const color = selectedMetric === 'pnl' || selectedMetric === 'return' ?
      processedData[processedData.length - 1] >= 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)' :
      'rgb(59, 130, 246)'

    return {
      labels,
      datasets: [{
        label: {
          pnl: 'Profit & Loss',
          return: 'Return %',
          trades: 'Trade Count',
          winRate: 'Win Rate %'
        }[selectedMetric],
        data: processedData,
        borderColor: color,
        backgroundColor: chartType === 'area' ? `${color}20` : color,
        fill: chartType === 'area',
        tension: chartType === 'line' || chartType === 'area' ? 0.4 : 0,
        borderWidth: 2,
        pointRadius: viewMode === 'cumulative' ? 0 : 3,
        pointHoverRadius: 5
      }]
    }
  }, [performanceData, viewMode, selectedMetric, chartType])

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    if (!performanceData) return null

    const allData = [...performanceData.daily, ...performanceData.weekly, ...performanceData.monthly]
    
    const totalPnL = allData.reduce((sum, d) => sum + d.pnl, 0)
    const totalTrades = allData.reduce((sum, d) => sum + d.trades, 0)
    const avgWinRate = allData.reduce((sum, d) => sum + d.winRate, 0) / allData.length
    const avgReturn = allData.reduce((sum, d) => sum + d.return, 0) / allData.length
    const maxDrawdown = Math.min(...allData.map(d => d.drawdown))
    const bestMonth = Math.max(...performanceData.monthly.map(d => d.pnl))
    const worstMonth = Math.min(...performanceData.monthly.map(d => d.pnl))
    const profitableMonths = performanceData.monthly.filter(d => d.pnl > 0).length
    const totalMonths = performanceData.monthly.length

    return {
      totalPnL,
      totalTrades,
      avgWinRate,
      avgReturn,
      maxDrawdown,
      bestMonth,
      worstMonth,
      profitableMonths,
      totalMonths,
      consistency: (profitableMonths / totalMonths) * 100
    }
  }, [performanceData])

  // Distribution chart data
  const distributionData = useMemo(() => {
    if (!performanceData) return null

    const daily = performanceData.daily
    const profitable = daily.filter(d => d.pnl > 0).length
    const losing = daily.filter(d => d.pnl < 0).length
    const breakeven = daily.filter(d => d.pnl === 0).length

    return {
      labels: ['Profitable', 'Losing', 'Breakeven'],
      datasets: [{
        data: [profitable, losing, breakeven],
        backgroundColor: [
          'rgb(34, 197, 94)',
          'rgb(239, 68, 68)',
          'rgb(107, 114, 128)'
        ],
        borderWidth: 0
      }]
    }
  }, [performanceData])

  // Handle export
  const handleExport = () => {
    if (onExport && performanceData) {
      onExport({
        dateRange,
        data: performanceData,
        statistics: summaryStats
      })
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-800 rounded w-1/3 mb-6"></div>
          <div className="h-64 bg-gray-800 rounded mb-4"></div>
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-20 bg-gray-800 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-600 rounded-lg p-6">
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <BarChart2 className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Historical Performance</h2>
          </div>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 text-gray-300 rounded hover:bg-gray-700 transition-colors"
          >
            <Download className="w-4 h-4" />
            <span className="text-sm">Export</span>
          </button>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-4">
          {/* Date Range */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <input
              type="date"
              value={dateRange.start.toISOString().split('T')[0]}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: new Date(e.target.value) }))}
              className="px-2 py-1 bg-gray-800 text-white rounded text-sm"
            />
            <span className="text-gray-500">to</span>
            <input
              type="date"
              value={dateRange.end.toISOString().split('T')[0]}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: new Date(e.target.value) }))}
              className="px-2 py-1 bg-gray-800 text-white rounded text-sm"
            />
          </div>

          {/* View Mode */}
          <div className="flex gap-1 bg-gray-800 rounded p-1">
            {(['cumulative', 'daily', 'weekly', 'monthly'] as ViewMode[]).map(mode => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`px-3 py-1 rounded text-sm capitalize ${
                  viewMode === mode
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                } transition-colors`}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* Chart Type */}
          <div className="flex gap-1 bg-gray-800 rounded p-1">
            {(['line', 'bar', 'area'] as ChartType[]).map(type => (
              <button
                key={type}
                onClick={() => setChartType(type)}
                className={`px-3 py-1 rounded text-sm capitalize ${
                  chartType === type
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                } transition-colors`}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Metric Selector */}
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value as any)}
            className="px-3 py-1.5 bg-gray-800 text-white rounded text-sm"
          >
            <option value="pnl">P&L</option>
            <option value="return">Return %</option>
            <option value="trades">Trades</option>
            <option value="winRate">Win Rate</option>
          </select>
        </div>
      </div>

      {/* Main Chart */}
      {chartData && (
        <div className="p-6">
          <div className="h-80 relative">
            {chartType === 'bar' ? (
              <Bar
                data={chartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: { display: false },
                    tooltip: {
                      callbacks: {
                        label: (context) => {
                          const value = context.parsed.y
                          if (selectedMetric === 'pnl') return formatCurrency(value)
                          if (selectedMetric === 'return' || selectedMetric === 'winRate') return formatPercent(value)
                          return value.toString()
                        }
                      }
                    }
                  },
                  scales: {
                    x: {
                      grid: { color: 'rgba(255, 255, 255, 0.1)' },
                      ticks: { color: 'rgba(255, 255, 255, 0.5)' }
                    },
                    y: {
                      grid: { color: 'rgba(255, 255, 255, 0.1)' },
                      ticks: {
                        color: 'rgba(255, 255, 255, 0.5)',
                        callback: (value) => {
                          if (selectedMetric === 'pnl') return formatCurrency(value as number)
                          if (selectedMetric === 'return' || selectedMetric === 'winRate') return formatPercent(value as number)
                          return value
                        }
                      }
                    }
                  }
                }}
              />
            ) : (
              <Line
                data={chartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: { display: false },
                    tooltip: {
                      callbacks: {
                        label: (context) => {
                          const value = context.parsed.y
                          if (selectedMetric === 'pnl') return formatCurrency(value)
                          if (selectedMetric === 'return' || selectedMetric === 'winRate') return formatPercent(value)
                          return value.toString()
                        }
                      }
                    }
                  },
                  scales: {
                    x: {
                      grid: { color: 'rgba(255, 255, 255, 0.1)' },
                      ticks: { color: 'rgba(255, 255, 255, 0.5)' }
                    },
                    y: {
                      grid: { color: 'rgba(255, 255, 255, 0.1)' },
                      ticks: {
                        color: 'rgba(255, 255, 255, 0.5)',
                        callback: (value) => {
                          if (selectedMetric === 'pnl') return formatCurrency(value as number)
                          if (selectedMetric === 'return' || selectedMetric === 'winRate') return formatPercent(value as number)
                          return value
                        }
                      }
                    }
                  }
                }}
              />
            )}
          </div>
        </div>
      )}

      {/* Summary Statistics */}
      {summaryStats && (
        <div className="px-6 pb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="text-xs text-gray-400 mb-1">Total P&L</div>
              <div className={`text-xl font-bold ${
                summaryStats.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {formatCurrency(summaryStats.totalPnL)}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="text-xs text-gray-400 mb-1">Win Rate</div>
              <div className="text-xl font-bold text-white">
                {formatPercent(summaryStats.avgWinRate)}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="text-xs text-gray-400 mb-1">Max Drawdown</div>
              <div className="text-xl font-bold text-yellow-400">
                {formatCurrency(Math.abs(summaryStats.maxDrawdown))}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="text-xs text-gray-400 mb-1">Consistency</div>
              <div className="text-xl font-bold text-blue-400">
                {formatPercent(summaryStats.consistency)}
              </div>
            </motion.div>
          </div>

          {/* Distribution Chart */}
          {distributionData && (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Day Distribution</h3>
                <div className="h-48">
                  <Doughnut
                    data={distributionData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'bottom',
                          labels: { color: 'rgba(255, 255, 255, 0.7)' }
                        }
                      }
                    }}
                  />
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Monthly Performance</h3>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Best Month</span>
                    <span className="text-green-400 font-medium">
                      {formatCurrency(summaryStats.bestMonth)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Worst Month</span>
                    <span className="text-red-400 font-medium">
                      {formatCurrency(summaryStats.worstMonth)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Avg Return</span>
                    <span className={`font-medium ${
                      summaryStats.avgReturn >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {formatPercent(summaryStats.avgReturn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Profitable Months</span>
                    <span className="text-white font-medium">
                      {summaryStats.profitableMonths} / {summaryStats.totalMonths}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}