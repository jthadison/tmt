'use client'

import React, { useState, useMemo } from 'react'
import { 
  AggregatedMetrics, 
  ExecutionMetrics as MetricsType,
  TimeframePeriod,
  MetricsDataPoint,
  MetricsChartConfig
} from '@/types/tradeExecution'
import Card from '@/components/ui/Card'

/**
 * Props for ExecutionMetrics component
 */
interface ExecutionMetricsProps {
  /** Aggregated metrics data */
  metrics: AggregatedMetrics | null
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback when timeframe changes */
  onTimeframeChange?: (timeframe: TimeframePeriod) => void
  /** Show detailed breakdown */
  detailed?: boolean
  /** Callback to refresh metrics */
  onRefresh?: () => void
}

/**
 * Simple SVG chart component for metrics visualization
 */
function SimpleMetricsChart({
  data,
  width = 400,
  height = 200,
  color = '#3b82f6',
  label,
  unit = '',
  showGrid = true
}: {
  data: MetricsDataPoint[]
  width?: number
  height?: number
  color?: string
  label: string
  unit?: string
  showGrid?: boolean
}) {
  const margin = { top: 20, right: 30, bottom: 40, left: 60 }
  const chartWidth = width - margin.left - margin.right
  const chartHeight = height - margin.top - margin.bottom

  const { xMin, xMax, yMin, yMax, scaledData } = useMemo(() => {
    if (data.length === 0) return { xMin: 0, xMax: 1, yMin: 0, yMax: 1, scaledData: [] }

    const xMin = Math.min(...data.map(d => d.timestamp.getTime()))
    const xMax = Math.max(...data.map(d => d.timestamp.getTime()))
    const yMin = Math.min(...data.map(d => d.value))
    const yMax = Math.max(...data.map(d => d.value))

    // Add padding to y-axis
    const yPadding = (yMax - yMin) * 0.1 || 1
    const adjustedYMin = Math.max(0, yMin - yPadding)
    const adjustedYMax = yMax + yPadding

    const scaledData = data.map(d => ({
      x: ((d.timestamp.getTime() - xMin) / (xMax - xMin)) * chartWidth,
      y: chartHeight - ((d.value - adjustedYMin) / (adjustedYMax - adjustedYMin)) * chartHeight,
      original: d
    }))

    return { xMin, xMax, yMin: adjustedYMin, yMax: adjustedYMax, scaledData }
  }, [data, chartWidth, chartHeight])

  const formatValue = (value: number): string => {
    if (unit === '%') return `${value.toFixed(1)}%`
    if (unit === 'ms') return `${value.toFixed(0)}ms`
    if (unit === '$') return `$${value.toLocaleString()}`
    return value.toLocaleString()
  }

  // Generate grid lines
  const yGridLines = []
  const ySteps = 4
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
          {formatValue(value)}
        </text>
      </g>
    )
  }

  // Generate path for line chart
  const pathData = scaledData.length > 0 ? 
    `M ${scaledData[0].x} ${scaledData[0].y} ` +
    scaledData.slice(1).map(d => `L ${d.x} ${d.y}`).join(' ') : ''

  return (
    <div className="bg-gray-800 p-4 rounded-lg">
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
              r={3}
              fill={color}
              className="cursor-pointer"
            />
          ))}
          
          {/* X-axis labels */}
          {data.length > 0 && [0, Math.floor(scaledData.length / 2), scaledData.length - 1].map(i => {
            if (!scaledData[i]) return null
            return (
              <text
                key={`x-label-${i}`}
                x={scaledData[i].x}
                y={chartHeight + 20}
                textAnchor="middle"
                className="fill-gray-400 text-xs"
              >
                {scaledData[i].original.timestamp.toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </text>
            )
          })}
        </g>
      </svg>
    </div>
  )
}

/**
 * Metric card component
 */
function MetricCard({
  title,
  value,
  unit = '',
  change,
  changeUnit = '',
  color = 'text-white',
  icon,
  trend,
  loading = false
}: {
  title: string
  value: number | string
  unit?: string
  change?: number
  changeUnit?: string
  color?: string
  icon?: string
  trend?: 'up' | 'down' | 'neutral'
  loading?: boolean
}) {
  const formatValue = (val: number | string): string => {
    if (typeof val === 'string') return val
    if (unit === '%') return `${val.toFixed(1)}%`
    if (unit === 'ms') return `${val.toFixed(0)}ms`
    if (unit === '$') return `$${val.toLocaleString()}`
    return val.toLocaleString()
  }

  const getTrendIcon = (): string => {
    switch (trend) {
      case 'up': return '↗'
      case 'down': return '↘'
      case 'neutral': return '→'
      default: return ''
    }
  }

  const getTrendColor = (): string => {
    switch (trend) {
      case 'up': return change && change > 0 ? 'text-green-400' : 'text-red-400'
      case 'down': return change && change < 0 ? 'text-red-400' : 'text-green-400'
      case 'neutral': return 'text-gray-400'
      default: return 'text-gray-400'
    }
  }

  if (loading) {
    return (
      <Card>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-24 mb-2"></div>
          <div className="h-8 bg-gray-700 rounded w-16 mb-2"></div>
          <div className="h-3 bg-gray-700 rounded w-20"></div>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            {icon && <span className="text-lg">{icon}</span>}
            <h3 className="text-sm font-medium text-gray-400">{title}</h3>
          </div>
          <div className={`text-2xl font-bold ${color} mb-1`}>
            {formatValue(value)}
          </div>
          {change !== undefined && (
            <div className={`text-xs flex items-center space-x-1 ${getTrendColor()}`}>
              <span>{getTrendIcon()}</span>
              <span>
                {change >= 0 ? '+' : ''}{change.toFixed(1)}{changeUnit} vs prev period
              </span>
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}

/**
 * Metrics breakdown component
 */
function MetricsBreakdown({
  title,
  data,
  loading = false
}: {
  title: string
  data: Map<string, number> | Map<string, MetricsType>
  loading?: boolean
}) {
  if (loading) {
    return (
      <Card>
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-gray-700 rounded w-32"></div>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex justify-between">
              <div className="h-4 bg-gray-700 rounded w-24"></div>
              <div className="h-4 bg-gray-700 rounded w-16"></div>
            </div>
          ))}
        </div>
      </Card>
    )
  }

  const entries = Array.from(data.entries()).slice(0, 8) // Show top 8

  return (
    <Card>
      <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      <div className="space-y-3">
        {entries.map(([key, value]) => {
          const displayValue = typeof value === 'number' ? 
            value.toLocaleString() : 
            `${value.fillRate.toFixed(1)}%`
          
          const additionalInfo = typeof value === 'object' ? 
            `${value.totalExecutions} trades` : null

          return (
            <div key={key} className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-white truncate">{key}</div>
                {additionalInfo && (
                  <div className="text-xs text-gray-400">{additionalInfo}</div>
                )}
              </div>
              <div className="text-right">
                <div className="font-medium text-white">{displayValue}</div>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

/**
 * Main ExecutionMetrics component
 */
export function ExecutionMetrics({
  metrics,
  loading = false,
  error,
  onTimeframeChange,
  detailed = false,
  onRefresh
}: ExecutionMetricsProps) {
  const [selectedTimeframe, setSelectedTimeframe] = useState<TimeframePeriod>('1h')

  const timeframeOptions: { value: TimeframePeriod; label: string }[] = [
    { value: '1h', label: '1H' },
    { value: '1d', label: '1D' },
    { value: '1w', label: '1W' },
    { value: '1m', label: '1M' }
  ]

  // Generate mock chart data for visualization
  const generateChartData = (baseValue: number, points: number = 24): MetricsDataPoint[] => {
    const data: MetricsDataPoint[] = []
    const now = new Date()
    
    for (let i = points - 1; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000) // Hourly data
      const variation = (Math.random() - 0.5) * 0.2 // ±10% variation
      const value = baseValue * (1 + variation)
      
      data.push({
        timestamp,
        value: Math.max(0, value) // Ensure non-negative values
      })
    }
    
    return data
  }

  const handleTimeframeChange = (timeframe: TimeframePeriod) => {
    setSelectedTimeframe(timeframe)
    onTimeframeChange?.(timeframe)
  }

  if (loading && !metrics) {
    return (
      <div className="space-y-6">
        <Card>
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-gray-700 rounded w-48"></div>
            <div className="grid grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Metrics</div>
          <p className="text-gray-400 mb-4">{error}</p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Retry
            </button>
          )}
        </div>
      </Card>
    )
  }

  if (!metrics) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-gray-400 text-lg mb-2">No Metrics Available</div>
          <p className="text-gray-500">Execution metrics will appear here once trades are executed</p>
        </div>
      </Card>
    )
  }

  const { overall } = metrics

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">Execution Quality Metrics</h2>
            <p className="text-sm text-gray-400">
              {overall.periodStart.toLocaleDateString()} - {overall.periodEnd.toLocaleDateString()}
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Timeframe Selector */}
            <div className="flex bg-gray-700 rounded-lg p-1">
              {timeframeOptions.map(option => (
                <button
                  key={option.value}
                  onClick={() => handleTimeframeChange(option.value)}
                  className={`px-3 py-1 rounded text-sm transition-colors ${
                    selectedTimeframe === option.value
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
            
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-medium"
                disabled={loading}
              >
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Key Performance Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <MetricCard
          title="Fill Rate"
          value={overall.fillRate}
          unit="%"
          change={2.3}
          changeUnit="%"
          color="text-green-400"
          icon="✓"
          trend="up"
          loading={loading}
        />
        
        <MetricCard
          title="Avg Slippage"
          value={overall.averageSlippage * 10000} // Convert to pips
          unit="p"
          change={-0.2}
          changeUnit="p"
          color="text-yellow-400"
          icon="📊"
          trend="down"
          loading={loading}
        />
        
        <MetricCard
          title="Avg Speed"
          value={overall.averageExecutionSpeed}
          unit="ms"
          change={-15}
          changeUnit="ms"
          color="text-blue-400"
          icon="⚡"
          trend="down"
          loading={loading}
        />
        
        <MetricCard
          title="Rejection Rate"
          value={overall.rejectionRate}
          unit="%"
          change={-0.5}
          changeUnit="%"
          color={overall.rejectionRate > 5 ? "text-red-400" : "text-green-400"}
          icon="⚠"
          trend="down"
          loading={loading}
        />
      </div>

      {/* Volume and Trading Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <MetricCard
          title="Total Executions"
          value={overall.totalExecutions}
          color="text-white"
          icon="📈"
          loading={loading}
        />
        
        <MetricCard
          title="Volume Traded"
          value={overall.totalVolumeTraded}
          unit="$"
          color="text-white"
          icon="💰"
          loading={loading}
        />
        
        <MetricCard
          title="Avg Trade Size"
          value={overall.averageTradeSize}
          unit="$"
          color="text-white"
          icon="📊"
          loading={loading}
        />
        
        <MetricCard
          title="Total Fees"
          value={overall.totalFees}
          unit="$"
          color="text-orange-400"
          icon="💸"
          loading={loading}
        />
      </div>

      {/* Performance Charts */}
      {detailed && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <SimpleMetricsChart
            data={generateChartData(overall.fillRate)}
            label="Fill Rate Over Time"
            unit="%"
            color="#10b981"
          />
          
          <SimpleMetricsChart
            data={generateChartData(overall.averageSlippage * 10000)}
            label="Average Slippage (Pips)"
            unit="p"
            color="#f59e0b"
          />
          
          <SimpleMetricsChart
            data={generateChartData(overall.averageExecutionSpeed)}
            label="Execution Speed"
            unit="ms"
            color="#3b82f6"
          />
          
          <SimpleMetricsChart
            data={generateChartData(overall.executionsPerHour)}
            label="Executions Per Hour"
            color="#8b5cf6"
          />
        </div>
      )}

      {/* Detailed Breakdowns */}
      {detailed && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {metrics.byAccount.size > 0 && (
            <MetricsBreakdown
              title="Performance by Account"
              data={metrics.byAccount}
              loading={loading}
            />
          )}
          
          {metrics.byInstrument.size > 0 && (
            <MetricsBreakdown
              title="Performance by Instrument"
              data={metrics.byInstrument}
              loading={loading}
            />
          )}
          
          {metrics.byBroker.size > 0 && (
            <MetricsBreakdown
              title="Performance by Broker"
              data={metrics.byBroker}
              loading={loading}
            />
          )}
        </div>
      )}

      {/* Status Distribution */}
      {metrics.byStatus.size > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-white mb-4">Execution Status Distribution</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {Array.from(metrics.byStatus.entries()).map(([status, count]) => {
              const percentage = overall.totalExecutions > 0 ? (count / overall.totalExecutions) * 100 : 0
              
              const getStatusColor = (status: string): string => {
                switch (status) {
                  case 'filled': return 'text-green-400 border-green-500'
                  case 'partial': return 'text-yellow-400 border-yellow-500'
                  case 'pending': return 'text-blue-400 border-blue-500'
                  case 'rejected': return 'text-red-400 border-red-500'
                  case 'cancelled': return 'text-gray-400 border-gray-500'
                  default: return 'text-gray-400 border-gray-500'
                }
              }

              return (
                <div key={status} className={`p-3 rounded-lg border ${getStatusColor(status)} bg-opacity-10`}>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{count}</div>
                    <div className="text-sm capitalize">{status}</div>
                    <div className="text-xs opacity-75">{percentage.toFixed(1)}%</div>
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}
    </div>
  )
}

export default ExecutionMetrics