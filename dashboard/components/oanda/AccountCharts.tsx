'use client'

import React, { useState, useMemo } from 'react'
import { AccountHistoryPoint, AccountPerformanceSummary, TimeFrame, CurrencyCode } from '@/types/oanda'
import Card from '@/components/ui/Card'

/**
 * Props for AccountCharts component
 */
interface AccountChartsProps {
  /** Account ID */
  accountId: string
  /** Account currency for formatting */
  currency: CurrencyCode
  /** Historical data points */
  historyData: AccountHistoryPoint[]
  /** Performance summary */
  performanceSummary?: AccountPerformanceSummary
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Time frame selection */
  timeFrame?: TimeFrame
  /** Callback when time frame changes */
  onTimeFrameChange?: (timeFrame: TimeFrame) => void
  /** Chart height */
  height?: number
}

/**
 * Simple chart component using SVG for account performance visualization
 */
function SimpleLineChart({
  data,
  width = 800,
  height = 300,
  color = '#3b82f6',
  currency,
  showGrid = true,
  label
}: {
  data: { x: number; y: number; tooltip?: string }[]
  width?: number
  height?: number
  color?: string
  currency: CurrencyCode
  showGrid?: boolean
  label: string
}) {
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)

  const margin = { top: 20, right: 30, bottom: 40, left: 80 }
  const chartWidth = width - margin.left - margin.right
  const chartHeight = height - margin.top - margin.bottom

  const { xMin, xMax, yMin, yMax, scaledData } = useMemo(() => {
    if (data.length === 0) return { xMin: 0, xMax: 1, yMin: 0, yMax: 1, scaledData: [] }

    const xMin = Math.min(...data.map(d => d.x))
    const xMax = Math.max(...data.map(d => d.x))
    const yMin = Math.min(...data.map(d => d.y))
    const yMax = Math.max(...data.map(d => d.y))

    // Add padding to y-axis
    const yPadding = (yMax - yMin) * 0.1
    const adjustedYMin = yMin - yPadding
    const adjustedYMax = yMax + yPadding

    const scaledData = data.map(d => ({
      x: ((d.x - xMin) / (xMax - xMin)) * chartWidth,
      y: chartHeight - ((d.y - adjustedYMin) / (adjustedYMax - adjustedYMin)) * chartHeight,
      original: d
    }))

    return { xMin, xMax, yMin: adjustedYMin, yMax: adjustedYMax, scaledData }
  }, [data, chartWidth, chartHeight])

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleDateString()
  }

  // Generate grid lines
  const yGridLines = []
  const ySteps = 5
  for (let i = 0; i <= ySteps; i++) {
    const y = (chartHeight / ySteps) * i
    const value = yMax - ((yMax - yMin) / ySteps) * i
    yGridLines.push(
      <g key={`y-grid-${i}`}>
        <line
          x1={0}
          y1={y}
          x2={chartWidth}
          y2={y}
          stroke="#374151"
          strokeWidth={0.5}
          opacity={0.5}
        />
        <text
          x={-10}
          y={y + 4}
          textAnchor="end"
          className="fill-gray-400 text-xs"
        >
          {formatCurrency(value)}
        </text>
      </g>
    )
  }

  // Generate path for line chart
  const pathData = scaledData.length > 0 ? 
    `M ${scaledData[0].x} ${scaledData[0].y} ` +
    scaledData.slice(1).map(d => `L ${d.x} ${d.y}`).join(' ') : ''

  return (
    <div className="relative">
      <div className="text-sm font-medium text-white mb-2">{label}</div>
      <svg width={width} height={height} className="overflow-visible">
        <g transform={`translate(${margin.left}, ${margin.top})`}>
          {/* Grid */}
          {showGrid && yGridLines}
          
          {/* Chart area background */}
          <rect
            width={chartWidth}
            height={chartHeight}
            fill="transparent"
            stroke="#374151"
            strokeWidth={1}
          />
          
          {/* Line */}
          {pathData && (
            <path
              d={pathData}
              fill="none"
              stroke={color}
              strokeWidth={2}
              className="drop-shadow-sm"
            />
          )}
          
          {/* Data points */}
          {scaledData.map((d, i) => (
            <circle
              key={i}
              cx={d.x}
              cy={d.y}
              r={hoveredPoint === i ? 5 : 3}
              fill={color}
              className="cursor-pointer transition-all duration-200"
              onMouseEnter={() => setHoveredPoint(i)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          ))}
          
          {/* Tooltip */}
          {hoveredPoint !== null && scaledData[hoveredPoint] && (
            <g>
              <rect
                x={scaledData[hoveredPoint].x - 60}
                y={scaledData[hoveredPoint].y - 40}
                width={120}
                height={30}
                fill="#1f2937"
                stroke="#374151"
                rx={4}
              />
              <text
                x={scaledData[hoveredPoint].x}
                y={scaledData[hoveredPoint].y - 25}
                textAnchor="middle"
                className="fill-white text-xs font-medium"
              >
                {formatCurrency(scaledData[hoveredPoint].original.y)}
              </text>
              <text
                x={scaledData[hoveredPoint].x}
                y={scaledData[hoveredPoint].y - 12}
                textAnchor="middle"
                className="fill-gray-300 text-xs"
              >
                {formatDate(scaledData[hoveredPoint].original.x)}
              </text>
            </g>
          )}
          
          {/* X-axis labels */}
          {[0, Math.floor(scaledData.length / 2), scaledData.length - 1].map(i => {
            if (!scaledData[i]) return null
            return (
              <text
                key={`x-label-${i}`}
                x={scaledData[i].x}
                y={chartHeight + 20}
                textAnchor="middle"
                className="fill-gray-400 text-xs"
              >
                {formatDate(scaledData[i].original.x)}
              </text>
            )
          })}
        </g>
      </svg>
    </div>
  )
}

/**
 * Account charts component with multiple chart types
 */
export function AccountCharts({
  accountId,
  currency,
  historyData,
  performanceSummary,
  loading = false,
  error,
  timeFrame = '1D',
  onTimeFrameChange,
  height = 300
}: AccountChartsProps) {
  const [activeChart, setActiveChart] = useState<'balance' | 'equity' | 'drawdown' | 'pnl'>('balance')

  const timeFrameOptions: { value: TimeFrame; label: string }[] = [
    { value: '1H', label: '1H' },
    { value: '4H', label: '4H' },
    { value: '1D', label: '1D' },
    { value: '1W', label: '1W' },
    { value: '1M', label: '1M' }
  ]

  const chartTabs = [
    { key: 'balance' as const, label: 'Balance', color: '#3b82f6' },
    { key: 'equity' as const, label: 'Equity', color: '#10b981' },
    { key: 'drawdown' as const, label: 'Drawdown', color: '#f59e0b' },
    { key: 'pnl' as const, label: 'P&L', color: '#8b5cf6' }
  ]

  // Prepare chart data based on active chart
  const chartData = useMemo(() => {
    return historyData.map(point => {
      let value: number
      switch (activeChart) {
        case 'balance':
          value = point.balance
          break
        case 'equity':
          value = point.equity
          break
        case 'drawdown':
          value = -point.drawdown // Negative for visual representation
          break
        case 'pnl':
          value = point.unrealizedPL
          break
        default:
          value = point.balance
      }

      return {
        x: point.timestamp.getTime(),
        y: value,
        tooltip: `${new Date(point.timestamp).toLocaleDateString()}: ${
          new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
          }).format(value)
        }`
      }
    })
  }, [historyData, activeChart, currency])

  const activeChartConfig = chartTabs.find(tab => tab.key === activeChart)

  if (loading) {
    return (
      <Card>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-48"></div>
          <div className="flex space-x-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 bg-gray-700 rounded w-16"></div>
            ))}
          </div>
          <div className={`h-${height} bg-gray-700 rounded`}></div>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Charts</div>
          <p className="text-gray-400">{error}</p>
        </div>
      </Card>
    )
  }

  if (historyData.length === 0) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-gray-400 text-lg mb-2">No Historical Data</div>
          <p className="text-gray-500">No chart data available for this account</p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6">
        <h3 className="text-lg font-semibold text-white">Account Performance Charts</h3>
        
        {/* Time Frame Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Time Frame:</span>
          <div className="flex bg-gray-700 rounded-lg p-1">
            {timeFrameOptions.map(option => (
              <button
                key={option.value}
                onClick={() => onTimeFrameChange?.(option.value)}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  timeFrame === option.value
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart Type Tabs */}
      <div className="flex space-x-1 mb-6 bg-gray-800 rounded-lg p-1">
        {chartTabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveChart(tab.key)}
            className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeChart === tab.key
                ? 'bg-gray-700 text-white shadow-sm'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="mb-6">
        <SimpleLineChart
          data={chartData}
          width={800}
          height={height}
          color={activeChartConfig?.color || '#3b82f6'}
          currency={currency}
          label={activeChartConfig?.label || 'Balance'}
        />
      </div>

      {/* Performance Summary */}
      {performanceSummary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-6 border-t border-gray-700">
          <div className="text-center">
            <div className="text-gray-400 text-sm">Total Return</div>
            <div className={`text-lg font-bold ${
              performanceSummary.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {performanceSummary.totalReturn >= 0 ? '+' : ''}
              {new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency
              }).format(performanceSummary.totalReturn)}
            </div>
            <div className="text-sm text-gray-500">
              ({performanceSummary.totalReturnPercent >= 0 ? '+' : ''}
              {performanceSummary.totalReturnPercent.toFixed(2)}%)
            </div>
          </div>

          <div className="text-center">
            <div className="text-gray-400 text-sm">Max Drawdown</div>
            <div className="text-lg font-bold text-red-400">
              -{new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency
              }).format(performanceSummary.maxDrawdown)}
            </div>
            <div className="text-sm text-gray-500">
              (-{performanceSummary.maxDrawdownPercent.toFixed(2)}%)
            </div>
          </div>

          <div className="text-center">
            <div className="text-gray-400 text-sm">Win Rate</div>
            <div className="text-lg font-bold text-white">
              {performanceSummary.winRate.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500">
              {performanceSummary.winningTrades}/{performanceSummary.totalTrades} trades
            </div>
          </div>

          <div className="text-center">
            <div className="text-gray-400 text-sm">Profit Factor</div>
            <div className={`text-lg font-bold ${
              performanceSummary.profitFactor >= 1 ? 'text-green-400' : 'text-red-400'
            }`}>
              {performanceSummary.profitFactor.toFixed(2)}
            </div>
            <div className="text-sm text-gray-500">
              Avg Win: {new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency
              }).format(performanceSummary.averageWin)}
            </div>
          </div>
        </div>
      )}

      {/* Additional Metrics */}
      {performanceSummary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-700">
          <div className="text-center">
            <div className="text-gray-400 text-sm">Sharpe Ratio</div>
            <div className={`text-lg font-bold ${
              performanceSummary.sharpeRatio >= 1 ? 'text-green-400' : 
              performanceSummary.sharpeRatio >= 0 ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {performanceSummary.sharpeRatio.toFixed(2)}
            </div>
          </div>

          <div className="text-center">
            <div className="text-gray-400 text-sm">Sortino Ratio</div>
            <div className={`text-lg font-bold ${
              performanceSummary.sortinoRatio >= 1 ? 'text-green-400' : 
              performanceSummary.sortinoRatio >= 0 ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {performanceSummary.sortinoRatio.toFixed(2)}
            </div>
          </div>

          <div className="text-center">
            <div className="text-gray-400 text-sm">Current Drawdown</div>
            <div className={`text-lg font-bold ${
              performanceSummary.currentDrawdown > 0 ? 'text-red-400' : 'text-green-400'
            }`}>
              -{new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency
              }).format(performanceSummary.currentDrawdown)}
            </div>
            <div className="text-sm text-gray-500">
              (-{performanceSummary.currentDrawdownPercent.toFixed(2)}%)
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}

export default AccountCharts