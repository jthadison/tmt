/**
 * Risk Analytics Dashboard Component - AC3
 * Story 9.6: Risk analytics including drawdown analysis, Sharpe ratios, and volatility measurements
 * 
 * Comprehensive risk metrics visualization and analysis
 */

'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Line, Scatter, Bar } from 'react-chartjs-2'
import {
  Shield,
  TrendingDown,
  AlertTriangle,
  BarChart3,
  Activity,
  Target,
  Zap,
  Calendar,
  Info
} from 'lucide-react'
import { motion } from 'framer-motion'
import { RiskMetrics } from '@/types/performanceAnalytics'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'
import { formatCurrency, formatPercent, formatNumber } from '@/utils/formatters'

interface RiskAnalyticsDashboardProps {
  accountId: string
  dateRange: { start: Date; end: Date }
  onRiskAlert?: (alert: { metric: string; value: number; threshold: number }) => void
}

interface RiskThresholds {
  maxDrawdown: number
  minSharpe: number
  maxVolatility: number
  maxVaR: number
}

const defaultThresholds: RiskThresholds = {
  maxDrawdown: 10, // 10%
  minSharpe: 1.0,
  maxVolatility: 20, // 20%
  maxVaR: 5 // 5%
}

export default function RiskAnalyticsDashboard({
  accountId,
  dateRange,
  onRiskAlert
}: RiskAnalyticsDashboardProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null)
  const [thresholds, setThresholds] = useState<RiskThresholds>(defaultThresholds)
  const [selectedView, setSelectedView] = useState<'overview' | 'drawdown' | 'volatility' | 'var'>('overview')

  // Fetch risk metrics
  const fetchRiskMetrics = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const metrics = await performanceAnalyticsService.calculateRiskMetrics(accountId, dateRange)
      setRiskMetrics(metrics)

      // Check for risk alerts
      if (onRiskAlert) {
        if (metrics.maxDrawdownPercent > thresholds.maxDrawdown) {
          onRiskAlert({ metric: 'drawdown', value: metrics.maxDrawdownPercent, threshold: thresholds.maxDrawdown })
        }
        if (metrics.sharpeRatio < thresholds.minSharpe) {
          onRiskAlert({ metric: 'sharpe', value: metrics.sharpeRatio, threshold: thresholds.minSharpe })
        }
        if (metrics.volatility > thresholds.maxVolatility) {
          onRiskAlert({ metric: 'volatility', value: metrics.volatility, threshold: thresholds.maxVolatility })
        }
        if (Math.abs(metrics.valueAtRisk95) > thresholds.maxVaR) {
          onRiskAlert({ metric: 'var', value: Math.abs(metrics.valueAtRisk95), threshold: thresholds.maxVaR })
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch risk metrics')
    } finally {
      setLoading(false)
    }
  }, [accountId, dateRange, thresholds, onRiskAlert])

  useEffect(() => {
    fetchRiskMetrics()
  }, [fetchRiskMetrics])

  // Risk score calculation
  const riskScore = useMemo(() => {
    if (!riskMetrics) return 0

    let score = 100

    // Drawdown impact (0-30 points)
    const drawdownImpact = Math.min(30, (riskMetrics.maxDrawdownPercent / 20) * 30)
    score -= drawdownImpact

    // Sharpe ratio impact (0-25 points)
    const sharpeImpact = riskMetrics.sharpeRatio < 1 ? (1 - riskMetrics.sharpeRatio) * 25 : 0
    score -= sharpeImpact

    // Volatility impact (0-25 points)
    const volatilityImpact = Math.min(25, (riskMetrics.volatility / 30) * 25)
    score -= volatilityImpact

    // VaR impact (0-20 points)
    const varImpact = Math.min(20, (Math.abs(riskMetrics.valueAtRisk95) / 10) * 20)
    score -= varImpact

    return Math.max(0, Math.round(score))
  }, [riskMetrics])

  // Risk level based on score
  const riskLevel = useMemo(() => {
    if (riskScore >= 80) return { level: 'Low', color: 'text-green-400', bgColor: 'bg-green-900/50' }
    if (riskScore >= 60) return { level: 'Medium', color: 'text-yellow-400', bgColor: 'bg-yellow-900/50' }
    if (riskScore >= 40) return { level: 'High', color: 'text-orange-400', bgColor: 'bg-orange-900/50' }
    return { level: 'Critical', color: 'text-red-400', bgColor: 'bg-red-900/50' }
  }, [riskScore])

  // Drawdown underwater curve (mock data - would come from service)
  const underwaterCurve = useMemo(() => {
    if (!riskMetrics) return null

    // Generate sample underwater curve
    const days = 90
    const data = []
    let currentDrawdown = 0

    for (let i = 0; i < days; i++) {
      currentDrawdown = Math.max(-riskMetrics.maxDrawdownPercent, currentDrawdown + (Math.random() - 0.4) * 2)
      data.push({
        date: new Date(dateRange.start.getTime() + i * 24 * 60 * 60 * 1000),
        drawdown: currentDrawdown
      })
    }

    return {
      labels: data.map(d => d.date.toLocaleDateString()),
      datasets: [{
        label: 'Drawdown %',
        data: data.map(d => d.drawdown),
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: true,
        tension: 0.2
      }]
    }
  }, [riskMetrics, dateRange])

  // Volatility distribution (mock data)
  const volatilityDistribution = useMemo(() => {
    if (!riskMetrics) return null

    const returns = Array.from({ length: 100 }, () => 
      (Math.random() - 0.5) * riskMetrics.volatility * 2
    ).sort((a, b) => a - b)

    const bins = 20
    const binSize = (Math.max(...returns) - Math.min(...returns)) / bins
    const histogram = Array(bins).fill(0)
    
    returns.forEach(ret => {
      const bin = Math.min(bins - 1, Math.floor((ret - Math.min(...returns)) / binSize))
      histogram[bin]++
    })

    return {
      labels: histogram.map((_, i) => 
        (Math.min(...returns) + i * binSize).toFixed(1)
      ),
      datasets: [{
        label: 'Frequency',
        data: histogram,
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        borderColor: 'rgb(59, 130, 246)',
        borderWidth: 1
      }]
    }
  }, [riskMetrics])

  // VaR confidence intervals
  const varData = useMemo(() => {
    if (!riskMetrics) return null

    return {
      labels: ['VaR 95%', 'VaR 99%', 'CVaR 95%'],
      datasets: [{
        label: 'Value at Risk',
        data: [
          Math.abs(riskMetrics.valueAtRisk95),
          Math.abs(riskMetrics.valueAtRisk99),
          Math.abs(riskMetrics.conditionalVaR)
        ],
        backgroundColor: [
          'rgba(239, 68, 68, 0.8)',
          'rgba(220, 38, 38, 0.8)',
          'rgba(185, 28, 28, 0.8)'
        ],
        borderColor: [
          'rgb(239, 68, 68)',
          'rgb(220, 38, 38)',
          'rgb(185, 28, 28)'
        ],
        borderWidth: 1
      }]
    }
  }, [riskMetrics])

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-800 rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-800 rounded"></div>
            ))}
          </div>
          <div className="h-64 bg-gray-800 rounded"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-600 rounded-lg p-6">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    )
  }

  if (!riskMetrics) {
    return null
  }

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Shield className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Risk Analytics</h2>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${riskLevel.bgColor} ${riskLevel.color}`}>
              {riskLevel.level} Risk
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Calendar className="w-4 h-4" />
            <span>
              {dateRange.start.toLocaleDateString()} - {dateRange.end.toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* View Selector */}
        <div className="flex gap-1 bg-gray-800 rounded p-1">
          {[
            { key: 'overview', label: 'Overview', icon: BarChart3 },
            { key: 'drawdown', label: 'Drawdown', icon: TrendingDown },
            { key: 'volatility', label: 'Volatility', icon: Activity },
            { key: 'var', label: 'Value at Risk', icon: Target }
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setSelectedView(key as any)}
              className={`flex items-center gap-2 px-3 py-2 rounded text-sm ${
                selectedView === key
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              } transition-colors`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {selectedView === 'overview' && (
          <div className="space-y-6">
            {/* Key Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-800 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-400 text-sm">Risk Score</span>
                  <Shield className="w-4 h-4 text-gray-500" />
                </div>
                <div className={`text-2xl font-bold ${riskLevel.color}`}>
                  {riskScore}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {riskLevel.level} Risk Level
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-gray-800 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-400 text-sm">Sharpe Ratio</span>
                  <TrendingDown className="w-4 h-4 text-gray-500" />
                </div>
                <div className={`text-2xl font-bold ${
                  riskMetrics.sharpeRatio >= 1 ? 'text-green-400' :
                  riskMetrics.sharpeRatio >= 0.5 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {formatNumber(riskMetrics.sharpeRatio, 2)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Risk-Adjusted Return
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-gray-800 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-400 text-sm">Max Drawdown</span>
                  <AlertTriangle className="w-4 h-4 text-gray-500" />
                </div>
                <div className={`text-2xl font-bold ${
                  riskMetrics.maxDrawdownPercent > 10 ? 'text-red-400' :
                  riskMetrics.maxDrawdownPercent > 5 ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {formatPercent(riskMetrics.maxDrawdownPercent)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {formatCurrency(riskMetrics.maxDrawdown)}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-gray-800 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-400 text-sm">Volatility</span>
                  <Activity className="w-4 h-4 text-gray-500" />
                </div>
                <div className={`text-2xl font-bold ${
                  riskMetrics.volatility > 25 ? 'text-red-400' :
                  riskMetrics.volatility > 15 ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {formatPercent(riskMetrics.volatility)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Annualized
                </div>
              </motion.div>
            </div>

            {/* Additional Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Risk Ratios</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">Sortino Ratio</span>
                    <span className="text-white font-medium">
                      {formatNumber(riskMetrics.sortinoRatio, 2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">Calmar Ratio</span>
                    <span className="text-white font-medium">
                      {formatNumber(riskMetrics.calmarRatio, 2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">Win/Loss Ratio</span>
                    <span className="text-white font-medium">
                      {formatNumber(riskMetrics.winLossRatio, 2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">Profit Factor</span>
                    <span className="text-white font-medium">
                      {formatNumber(riskMetrics.profitFactor, 2)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Value at Risk</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">VaR 95%</span>
                    <span className="text-red-400 font-medium">
                      {formatPercent(Math.abs(riskMetrics.valueAtRisk95))}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">VaR 99%</span>
                    <span className="text-red-400 font-medium">
                      {formatPercent(Math.abs(riskMetrics.valueAtRisk99))}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">Conditional VaR</span>
                    <span className="text-red-400 font-medium">
                      {formatPercent(Math.abs(riskMetrics.conditionalVaR))}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">Kelly %</span>
                    <span className="text-blue-400 font-medium">
                      {formatPercent(riskMetrics.kellyPercentage)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedView === 'drawdown' && underwaterCurve && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-white mb-4">Underwater Curve</h3>
              <div className="h-64">
                <Line
                  data={underwaterCurve}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { display: false },
                      tooltip: {
                        callbacks: {
                          label: (context) => `${formatPercent(context.parsed.y)}`
                        }
                      }
                    },
                    scales: {
                      x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: 'rgba(255, 255, 255, 0.5)' }
                      },
                      y: {
                        min: -riskMetrics.maxDrawdownPercent * 1.2,
                        max: 0,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: {
                          color: 'rgba(255, 255, 255, 0.5)',
                          callback: (value) => formatPercent(value as number)
                        }
                      }
                    }
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-xs text-gray-400 mb-1">Current Drawdown</div>
                <div className="text-lg font-bold text-yellow-400">
                  {formatPercent(riskMetrics.currentDrawdownPercent)}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-xs text-gray-400 mb-1">Avg Drawdown</div>
                <div className="text-lg font-bold text-white">
                  {formatPercent(riskMetrics.averageDrawdown)}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-xs text-gray-400 mb-1">Recovery Factor</div>
                <div className="text-lg font-bold text-green-400">
                  {formatNumber(riskMetrics.recoveryFactor, 2)}
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedView === 'volatility' && volatilityDistribution && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-white mb-4">Return Distribution</h3>
              <div className="h-64">
                <Bar
                  data={volatilityDistribution}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { display: false }
                    },
                    scales: {
                      x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: 'rgba(255, 255, 255, 0.5)' }
                      },
                      y: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: 'rgba(255, 255, 255, 0.5)' }
                      }
                    }
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-xs text-gray-400 mb-1">Downside Deviation</div>
                <div className="text-lg font-bold text-red-400">
                  {formatPercent(riskMetrics.downsideDeviation)}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-xs text-gray-400 mb-1">Expectancy</div>
                <div className={`text-lg font-bold ${
                  riskMetrics.expectancy > 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {formatNumber(riskMetrics.expectancy, 2)}
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedView === 'var' && varData && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-white mb-4">Value at Risk Analysis</h3>
              <div className="h-64">
                <Bar
                  data={varData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { display: false },
                      tooltip: {
                        callbacks: {
                          label: (context) => `${formatPercent(context.parsed.y)}`
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
                          callback: (value) => formatPercent(value as number)
                        }
                      }
                    }
                  }}
                />
              </div>
            </div>

            <div className="bg-blue-900/20 border border-blue-600 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-blue-300">
                  <p className="font-medium mb-2">Value at Risk Interpretation:</p>
                  <ul className="space-y-1 text-xs">
                    <li>• VaR 95%: Expected loss exceeded only 5% of the time</li>
                    <li>• VaR 99%: Expected loss exceeded only 1% of the time</li>
                    <li>• CVaR 95%: Average loss when VaR 95% is exceeded</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}