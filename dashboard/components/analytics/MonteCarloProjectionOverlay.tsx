/**
 * Monte Carlo Projection Overlay Component - Story 8.1
 * Displays actual vs expected P&L with confidence intervals
 */

'use client'

import React, { useEffect, useState } from 'react'
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
  ChartOptions,
} from 'chart.js'
import { MonteCarloData } from '@/types/analytics'
import { AlertCircle, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface MonteCarloProjectionOverlayProps {
  actualPnL?: number[] // Optional actual P&L data
  currentDay?: number // Current day in simulation (0-179)
}

interface MetricCardProps {
  label: string
  value: string
  color: 'info' | 'secondary' | 'success' | 'danger'
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, color }) => {
  const colorClasses = {
    info: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
    secondary: 'bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/20',
    success: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    danger: 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20',
  }

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
      <div className="text-xs font-medium opacity-75 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}

interface ProgressIndicatorProps {
  current: number
  total: number
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ current, total }) => {
  const percentage = (current / total) * 100

  return (
    <div className="flex items-center gap-3">
      <div className="text-sm font-medium">
        Day {current} of {total}
      </div>
      <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

interface VarianceBadgeProps {
  variance: number
}

const VarianceBadge: React.FC<VarianceBadgeProps> = ({ variance }) => {
  const isPositive = variance >= 0
  const Icon = isPositive ? TrendingUp : TrendingDown
  const colorClass = isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'

  return (
    <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${isPositive ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
      <Icon className={`w-4 h-4 ${colorClass}`} />
      <span className={`text-sm font-medium ${colorClass}`}>
        {isPositive ? '+' : ''}
        {variance.toFixed(1)}%
      </span>
    </div>
  )
}

interface PerformanceAlertProps {
  message: string
  severity: 'low' | 'medium' | 'high'
}

const PerformanceAlert: React.FC<PerformanceAlertProps> = ({ message, severity }) => {
  const severityColors = {
    low: 'bg-blue-500/10 border-blue-500/20 text-blue-700 dark:text-blue-400',
    medium: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-700 dark:text-yellow-400',
    high: 'bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-400',
  }

  return (
    <div className={`mt-4 p-4 rounded-lg border ${severityColors[severity]}`}>
      <div className="flex items-center gap-2">
        <AlertCircle className="w-5 h-5" />
        <span className="text-sm font-medium">{message}</span>
      </div>
    </div>
  )
}

export const MonteCarloProjectionOverlay: React.FC<MonteCarloProjectionOverlayProps> = ({
  actualPnL = [],
  currentDay = 0,
}) => {
  const [monteCarlo, setMonteCarlo] = useState<MonteCarloData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMonteCarloData = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('/api/analytics/monte-carlo?days=180&simulations=1000')

      if (!response.ok) {
        throw new Error(`Failed to fetch Monte Carlo data: ${response.statusText}`)
      }

      const data = await response.json()
      setMonteCarlo(data.monteCarlo)
    } catch (err) {
      console.error('Error fetching Monte Carlo data:', err)
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMonteCarloData()
  }, [])

  if (loading) {
    return (
      <div className="animate-pulse p-6 bg-card rounded-lg border border-border">
        <div className="h-8 bg-muted rounded w-1/3 mb-4" />
        <div className="h-96 bg-muted rounded" />
      </div>
    )
  }

  if (error || !monteCarlo) {
    return (
      <div className="p-6 bg-card rounded-lg border border-border">
        <div className="flex flex-col items-center justify-center p-12 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to Load Monte Carlo Data</h3>
          <p className="text-muted-foreground mb-4">{error || 'An error occurred'}</p>
          <button
            onClick={fetchMonteCarloData}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  // Calculate variance
  const actualValue = actualPnL[currentDay] || 0
  const expectedValue = monteCarlo.expectedTrajectory[currentDay] || 0
  const variance = calculateVariance(actualValue, expectedValue)

  // Check if below expected
  const isBelowExpected = checkBelowExpected(actualPnL, monteCarlo.expectedTrajectory, currentDay)

  // Prepare chart data
  const labels = Array.from({ length: 180 }, (_, i) => `Day ${i + 1}`)

  const chartData = {
    labels,
    datasets: [
      // 99% CI Upper
      {
        label: '99% CI Upper',
        data: monteCarlo.confidenceIntervals['99'].upper,
        borderColor: 'rgba(59, 130, 246, 0.1)',
        backgroundColor: 'rgba(59, 130, 246, 0.05)',
        fill: '+1',
        pointRadius: 0,
        tension: 0.2,
        borderWidth: 1,
      },
      // 99% CI Lower
      {
        label: '99% CI Lower',
        data: monteCarlo.confidenceIntervals['99'].lower,
        borderColor: 'rgba(59, 130, 246, 0.1)',
        backgroundColor: 'transparent',
        pointRadius: 0,
        tension: 0.2,
        borderWidth: 1,
      },
      // 95% CI Upper
      {
        label: '95% CI Upper',
        data: monteCarlo.confidenceIntervals['95'].upper,
        borderColor: 'rgba(59, 130, 246, 0.2)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: '+1',
        pointRadius: 0,
        tension: 0.2,
        borderWidth: 1,
      },
      // 95% CI Lower
      {
        label: '95% CI Lower',
        data: monteCarlo.confidenceIntervals['95'].lower,
        borderColor: 'rgba(59, 130, 246, 0.2)',
        backgroundColor: 'transparent',
        pointRadius: 0,
        tension: 0.2,
        borderWidth: 1,
      },
      // Expected P&L
      {
        label: 'Expected P&L',
        data: monteCarlo.expectedTrajectory,
        borderColor: '#9ca3af',
        backgroundColor: 'transparent',
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 0,
        tension: 0.2,
      },
      // Actual P&L
      {
        label: 'Actual P&L',
        data: actualPnL,
        borderColor: '#3b82f6',
        backgroundColor: 'transparent',
        borderWidth: 3,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.2,
      },
    ],
  }

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          filter: (item) => {
            // Only show key labels
            return ['Actual P&L', 'Expected P&L', '95% CI Upper', '95% CI Lower'].includes(
              item.text
            )
          },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        callbacks: {
          label: (context) => {
            return `${context.dataset.label}: $${context.parsed.y.toFixed(2)}`
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Trading Days',
        },
        grid: {
          display: false,
        },
        ticks: {
          maxTicksLimit: 10,
          autoSkip: true,
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Cumulative P&L ($)',
        },
        grid: {
          color: 'rgba(156, 163, 175, 0.1)',
        },
      },
    },
  }

  return (
    <div className="monte-carlo-projection p-6 bg-card rounded-lg border border-border">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Monte Carlo Projection</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Probabilistic P&L forecast based on {monteCarlo.simulationsRun.toLocaleString()}{' '}
            simulations
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ProgressIndicator current={currentDay} total={180} />
          <VarianceBadge variance={variance} />
        </div>
      </div>

      {/* Chart */}
      <div className="chart-container h-[400px] mb-6">
        <Line data={chartData} options={options} />
      </div>

      {/* Performance indicators */}
      <div className="performance-indicators grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <MetricCard
          label="Current Actual"
          value={`$${actualValue.toFixed(2)}`}
          color="info"
        />
        <MetricCard
          label="Expected (Monte Carlo)"
          value={`$${expectedValue.toFixed(2)}`}
          color="secondary"
        />
        <MetricCard
          label="Variance"
          value={`${variance > 0 ? '+' : ''}${variance.toFixed(1)}%`}
          color={variance >= 0 ? 'success' : 'danger'}
        />
      </div>

      {/* Simulation parameters */}
      <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-border">
        <h4 className="text-sm font-semibold mb-3">Simulation Parameters</h4>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-xs">
          <div>
            <div className="text-muted-foreground mb-1">Win Rate</div>
            <div className="font-medium">
              {(monteCarlo.parameters.winRate * 100).toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-muted-foreground mb-1">Avg Profit</div>
            <div className="font-medium">${monteCarlo.parameters.avgProfit.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-muted-foreground mb-1">Avg Loss</div>
            <div className="font-medium">${monteCarlo.parameters.avgLoss.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-muted-foreground mb-1">Std Dev</div>
            <div className="font-medium">${monteCarlo.parameters.stdDev.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-muted-foreground mb-1">Trades/Day</div>
            <div className="font-medium">{monteCarlo.parameters.tradesPerDay.toFixed(1)}</div>
          </div>
        </div>
      </div>

      {/* Alert if below expected */}
      {isBelowExpected && (
        <PerformanceAlert
          message="Performance below expected for 2+ consecutive days"
          severity="medium"
        />
      )}
    </div>
  )
}

/**
 * Calculate variance percentage
 */
function calculateVariance(actual: number, expected: number): number {
  if (expected === 0) return 0
  return ((actual - expected) / Math.abs(expected)) * 100
}

/**
 * Check if performance is below expected for 2+ consecutive days
 */
function checkBelowExpected(
  actual: number[],
  expected: number[],
  currentDay: number
): boolean {
  if (currentDay < 2) return false

  const today = (actual[currentDay] || 0) < expected[currentDay]
  const yesterday = (actual[currentDay - 1] || 0) < expected[currentDay - 1]

  return today && yesterday
}
