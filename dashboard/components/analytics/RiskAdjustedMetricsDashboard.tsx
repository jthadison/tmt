'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Minus, ArrowUp, ArrowDown } from 'lucide-react'
import { RiskMetrics } from '@/types/analytics'
import { DrawdownDistributionChart } from './DrawdownDistributionChart'

interface MetricCardProps {
  label: string
  value: string
  subValue?: string
  color?: 'success' | 'danger' | 'warning' | 'info'
  icon?: React.ReactNode
}

function MetricCard({ label, value, subValue, color, icon }: MetricCardProps) {
  const colorClasses = {
    success: 'text-green-600 dark:text-green-400',
    danger: 'text-red-600 dark:text-red-400',
    warning: 'text-orange-600 dark:text-orange-400',
    info: 'text-blue-600 dark:text-blue-400'
  }

  const colorClass = color ? colorClasses[color] : 'text-gray-900 dark:text-white'

  return (
    <div className="metric-card p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">
          {label}
        </div>
        {icon && <div className={colorClass}>{icon}</div>}
      </div>
      <div className={`text-2xl font-bold ${colorClass}`}>{value}</div>
      {subValue && (
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subValue}</div>
      )}
    </div>
  )
}

interface RatioCardProps {
  label: string
  value: number
  interpretation: string
  tooltip: string
}

function RatioCard({ label, value, interpretation, tooltip }: RatioCardProps) {
  const getColor = (val: number): 'success' | 'warning' | 'danger' => {
    if (label.includes('Sharpe')) {
      if (val > 1) return 'success'
      if (val > 0.5) return 'warning'
      return 'danger'
    }
    if (label.includes('Sortino')) {
      if (val > 1.5) return 'success'
      if (val > 0.75) return 'warning'
      return 'danger'
    }
    if (label.includes('Calmar')) {
      if (val > 3) return 'success'
      if (val > 1.5) return 'warning'
      return 'danger'
    }
    return 'success'
  }

  const color = getColor(value)

  return (
    <div className="ratio-card p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="text-sm text-gray-600 dark:text-gray-400 mb-2" title={tooltip}>
        {label}
      </div>
      <div
        className={`text-3xl font-bold mb-2 ${
          color === 'success'
            ? 'text-green-600'
            : color === 'warning'
              ? 'text-orange-600'
              : 'text-red-600'
        }`}
      >
        {value.toFixed(2)}
      </div>
      <div className="text-xs text-gray-500 dark:text-gray-400">{interpretation}</div>
    </div>
  )
}

function interpretSharpe(value: number): string {
  if (value > 2) return 'Outstanding'
  if (value > 1) return 'Excellent'
  if (value > 0.5) return 'Good'
  if (value > 0) return 'Acceptable'
  return 'Poor'
}

function interpretSortino(value: number): string {
  if (value > 2) return 'Excellent'
  if (value > 1) return 'Good'
  if (value > 0.5) return 'Fair'
  return 'Poor'
}

function interpretCalmar(value: number): string {
  if (value > 5) return 'Exceptional'
  if (value > 3) return 'Excellent'
  if (value > 1.5) return 'Good'
  return 'Fair'
}

function interpretRRRatio(value: number): string {
  if (value > 3) return 'Excellent'
  if (value > 2) return 'Good'
  if (value > 1) return 'Fair'
  return 'Poor'
}

function interpretProfitFactor(value: number): string {
  if (value > 2) return 'Excellent'
  if (value > 1.5) return 'Good'
  if (value > 1) return 'Profitable'
  return 'Unprofitable'
}

function getTrendIcon(trend: 'increasing' | 'stable' | 'decreasing') {
  if (trend === 'increasing') return <TrendingUp className="w-5 h-5" />
  if (trend === 'decreasing') return <TrendingDown className="w-5 h-5" />
  return <Minus className="w-5 h-5" />
}

function getTrendColor(trend: 'increasing' | 'stable' | 'decreasing'): MetricCardProps['color'] {
  if (trend === 'increasing') return 'danger' // Higher volatility is bad
  if (trend === 'decreasing') return 'success' // Lower volatility is good
  return 'info'
}

export function RiskAdjustedMetricsDashboard() {
  const [metrics, setMetrics] = useState<RiskMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch('/api/analytics/risk-metrics')
        if (!response.ok) throw new Error('Failed to fetch risk metrics')

        const data = await response.json()
        setMetrics(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
  }, [])

  if (loading) {
    return (
      <div className="risk-metrics-dashboard space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !metrics) {
    return (
      <div className="risk-metrics-dashboard p-6 bg-white dark:bg-gray-800 rounded-lg">
        <div className="text-red-600 dark:text-red-400">
          Error loading risk metrics: {error || 'Unknown error'}
        </div>
      </div>
    )
  }

  return (
    <div className="risk-metrics-dashboard space-y-6">
      {/* Risk-Adjusted Ratios */}
      <div className="ratios-section p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          Risk-Adjusted Returns
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <RatioCard
            label="Sharpe Ratio"
            value={metrics.sharpeRatio}
            interpretation={interpretSharpe(metrics.sharpeRatio)}
            tooltip="Risk-adjusted return using total volatility"
          />
          <RatioCard
            label="Sortino Ratio"
            value={metrics.sortinoRatio}
            interpretation={interpretSortino(metrics.sortinoRatio)}
            tooltip="Risk-adjusted return using downside volatility only"
          />
          <RatioCard
            label="Calmar Ratio"
            value={metrics.calmarRatio}
            interpretation={interpretCalmar(metrics.calmarRatio)}
            tooltip="Annual return divided by maximum drawdown"
          />
        </div>
      </div>

      {/* Drawdown Analysis */}
      <div className="drawdown-section p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          Drawdown Analysis
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard
            label="Max Drawdown"
            value={`$${Math.abs(metrics.drawdown.max).toFixed(2)}`}
            subValue={`${metrics.drawdown.maxPercent.toFixed(1)}%`}
            color="danger"
          />
          <MetricCard
            label="Avg Drawdown"
            value={`$${Math.abs(metrics.drawdown.avg).toFixed(2)}`}
            subValue={`${metrics.drawdown.avgPercent.toFixed(1)}%`}
            color="warning"
          />
          <MetricCard
            label="Recovery Time"
            value={`${metrics.drawdown.avgRecoveryDays} days`}
            subValue={`Max: ${metrics.drawdown.maxRecoveryDays} days`}
            color="info"
          />
          <MetricCard
            label="Current Drawdown"
            value={`$${Math.abs(metrics.drawdown.current).toFixed(2)}`}
            subValue={`${metrics.drawdown.currentPercent.toFixed(1)}%`}
            color={metrics.drawdown.current < 0 ? 'danger' : 'success'}
          />
        </div>

        {/* Drawdown distribution histogram */}
        <DrawdownDistributionChart distribution={metrics.drawdown.distribution} />
      </div>

      {/* Volatility Metrics */}
      <div className="volatility-section p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          Volatility Analysis
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            label="Daily Volatility"
            value={`${(metrics.volatility.daily * 100).toFixed(2)}%`}
            color="info"
          />
          <MetricCard
            label="Monthly Volatility"
            value={`${(metrics.volatility.monthly * 100).toFixed(2)}%`}
            subValue="Annualized"
            color="info"
          />
          <MetricCard
            label="Volatility Trend"
            value={metrics.volatility.trend.charAt(0).toUpperCase() + metrics.volatility.trend.slice(1)}
            color={getTrendColor(metrics.volatility.trend)}
            icon={getTrendIcon(metrics.volatility.trend)}
          />
        </div>
      </div>

      {/* Risk/Reward Profile */}
      <div className="risk-reward-section p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          Risk/Reward Profile
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="Avg R:R Ratio"
            value={metrics.riskReward.avgRRRatio.toFixed(2)}
            subValue={interpretRRRatio(metrics.riskReward.avgRRRatio)}
          />
          <MetricCard
            label="Win Ratio"
            value={`${metrics.riskReward.winRate.toFixed(1)}%`}
            color={metrics.riskReward.winRate > 60 ? 'success' : metrics.riskReward.winRate > 50 ? 'warning' : 'danger'}
          />
          <MetricCard
            label="Expectancy"
            value={`$${metrics.riskReward.expectancy.toFixed(2)}`}
            subValue="Per trade"
            color={metrics.riskReward.expectancy > 0 ? 'success' : 'danger'}
          />
          <MetricCard
            label="Profit Factor"
            value={metrics.riskReward.profitFactor.toFixed(2)}
            subValue={interpretProfitFactor(metrics.riskReward.profitFactor)}
            color={metrics.riskReward.profitFactor > 1.5 ? 'success' : metrics.riskReward.profitFactor > 1 ? 'warning' : 'danger'}
          />
        </div>
      </div>
    </div>
  )
}
