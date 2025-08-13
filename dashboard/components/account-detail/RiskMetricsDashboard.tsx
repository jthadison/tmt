'use client'

import { useMemo } from 'react'
import { RiskMetrics } from '@/types/accountDetail'

/**
 * Props for RiskMetricsDashboard component
 */
interface RiskMetricsDashboardProps {
  /** Risk metrics data */
  riskMetrics: RiskMetrics
  /** Show detailed view with additional metrics */
  detailed?: boolean
  /** Loading state indicator */
  loading?: boolean
}

/**
 * Risk metrics dashboard displaying key performance indicators
 * Provides comprehensive risk analysis with color-coded warnings
 */
export function RiskMetricsDashboard({
  riskMetrics,
  detailed = false,
  loading = false
}: RiskMetricsDashboardProps) {
  
  // Calculate additional derived metrics
  const derivedMetrics = useMemo(() => {
    const avgTradeSize = riskMetrics.totalTrades > 0 
      ? (riskMetrics.averageWin * (riskMetrics.winRate / 100) + 
         Math.abs(riskMetrics.averageLoss) * ((100 - riskMetrics.winRate) / 100))
      : 0

    const riskRewardRatio = riskMetrics.averageLoss !== 0 
      ? riskMetrics.averageWin / Math.abs(riskMetrics.averageLoss)
      : 0

    const expectedValue = (riskMetrics.winRate / 100) * riskMetrics.averageWin + 
                          ((100 - riskMetrics.winRate) / 100) * riskMetrics.averageLoss

    const consistency = riskMetrics.totalTrades > 0
      ? Math.max(0, 100 - ((riskMetrics.consecutiveLosses / riskMetrics.totalTrades) * 100))
      : 0

    return {
      avgTradeSize,
      riskRewardRatio,
      expectedValue,
      consistency
    }
  }, [riskMetrics])

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  const formatPercentage = (value: number, decimals: number = 1): string => {
    return `${value.toFixed(decimals)}%`
  }

  const formatDecimal = (value: number, decimals: number = 2): string => {
    return value.toFixed(decimals)
  }

  const getMetricColor = (metric: string, value: number): string => {
    switch (metric) {
      case 'sharpeRatio':
        if (value >= 2.0) return 'text-green-400'
        if (value >= 1.0) return 'text-yellow-400'
        return 'text-red-400'
      
      case 'winRate':
        if (value >= 60) return 'text-green-400'
        if (value >= 50) return 'text-yellow-400'
        return 'text-red-400'
      
      case 'profitFactor':
        if (value >= 1.5) return 'text-green-400'
        if (value >= 1.0) return 'text-yellow-400'
        return 'text-red-400'
      
      case 'maxDrawdown':
        if (value <= 5) return 'text-green-400'
        if (value <= 10) return 'text-yellow-400'
        return 'text-red-400'
      
      case 'riskReward':
        if (value >= 2.0) return 'text-green-400'
        if (value >= 1.0) return 'text-yellow-400'
        return 'text-red-400'
      
      default:
        return 'text-white'
    }
  }

  const getBackgroundColor = (metric: string, value: number): string => {
    const colorClass = getMetricColor(metric, value)
    switch (colorClass) {
      case 'text-green-400':
        return 'bg-green-900/20'
      case 'text-yellow-400':
        return 'bg-yellow-900/20'
      case 'text-red-400':
        return 'bg-red-900/20'
      default:
        return 'bg-gray-750'
    }
  }

  const getRiskLevel = (sharpeRatio: number, drawdown: number, winRate: number): {
    level: string
    color: string
    description: string
  } => {
    if (sharpeRatio >= 1.5 && drawdown <= 8 && winRate >= 55) {
      return {
        level: 'Low Risk',
        color: 'text-green-400',
        description: 'Excellent risk management with consistent performance'
      }
    } else if (sharpeRatio >= 1.0 && drawdown <= 15 && winRate >= 50) {
      return {
        level: 'Moderate Risk',
        color: 'text-yellow-400',
        description: 'Good performance with acceptable risk levels'
      }
    } else {
      return {
        level: 'High Risk',
        color: 'text-red-400',
        description: 'High volatility or poor risk management detected'
      }
    }
  }

  const riskAssessment = getRiskLevel(
    riskMetrics.sharpeRatio,
    riskMetrics.maxDrawdown,
    riskMetrics.winRate
  )

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-40"></div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-16 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-white">
          {detailed ? 'Detailed Risk Analysis' : 'Risk Metrics'}
        </h3>
        <div className={`px-3 py-1 rounded-full text-xs font-medium ${riskAssessment.color} bg-opacity-20`}>
          {riskAssessment.level}
        </div>
      </div>

      {/* Core Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
        {/* Sharpe Ratio */}
        <div className={`p-4 rounded-lg ${getBackgroundColor('sharpeRatio', riskMetrics.sharpeRatio)}`}>
          <div className="text-gray-400 text-sm">Sharpe Ratio</div>
          <div className={`text-xl font-bold ${getMetricColor('sharpeRatio', riskMetrics.sharpeRatio)}`}>
            {formatDecimal(riskMetrics.sharpeRatio)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Risk-adjusted return</div>
        </div>

        {/* Win Rate */}
        <div className={`p-4 rounded-lg ${getBackgroundColor('winRate', riskMetrics.winRate)}`}>
          <div className="text-gray-400 text-sm">Win Rate</div>
          <div className={`text-xl font-bold ${getMetricColor('winRate', riskMetrics.winRate)}`}>
            {formatPercentage(riskMetrics.winRate)}
          </div>
          <div className="text-xs text-gray-500 mt-1">{riskMetrics.totalTrades} trades</div>
        </div>

        {/* Profit Factor */}
        <div className={`p-4 rounded-lg ${getBackgroundColor('profitFactor', riskMetrics.profitFactor)}`}>
          <div className="text-gray-400 text-sm">Profit Factor</div>
          <div className={`text-xl font-bold ${getMetricColor('profitFactor', riskMetrics.profitFactor)}`}>
            {formatDecimal(riskMetrics.profitFactor)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Gross profit / loss</div>
        </div>

        {/* Max Drawdown */}
        <div className={`p-4 rounded-lg ${getBackgroundColor('maxDrawdown', riskMetrics.maxDrawdown)}`}>
          <div className="text-gray-400 text-sm">Max Drawdown</div>
          <div className={`text-xl font-bold ${getMetricColor('maxDrawdown', riskMetrics.maxDrawdown)}`}>
            {formatPercentage(riskMetrics.maxDrawdown)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Peak to trough</div>
        </div>

        {/* Average Win */}
        <div className="p-4 rounded-lg bg-gray-750">
          <div className="text-gray-400 text-sm">Avg Win</div>
          <div className="text-xl font-bold text-green-400">
            {formatCurrency(riskMetrics.averageWin)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Per winning trade</div>
        </div>

        {/* Average Loss */}
        <div className="p-4 rounded-lg bg-gray-750">
          <div className="text-gray-400 text-sm">Avg Loss</div>
          <div className="text-xl font-bold text-red-400">
            {formatCurrency(riskMetrics.averageLoss)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Per losing trade</div>
        </div>

        {/* Risk/Reward Ratio */}
        <div className={`p-4 rounded-lg ${getBackgroundColor('riskReward', derivedMetrics.riskRewardRatio)}`}>
          <div className="text-gray-400 text-sm">Risk/Reward</div>
          <div className={`text-xl font-bold ${getMetricColor('riskReward', derivedMetrics.riskRewardRatio)}`}>
            {formatDecimal(derivedMetrics.riskRewardRatio)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Avg win / avg loss</div>
        </div>

        {/* Expected Value */}
        <div className="p-4 rounded-lg bg-gray-750">
          <div className="text-gray-400 text-sm">Expected Value</div>
          <div className={`text-xl font-bold ${derivedMetrics.expectedValue >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatCurrency(derivedMetrics.expectedValue)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Per trade</div>
        </div>
      </div>

      {/* Detailed Metrics (shown when detailed=true) */}
      {detailed && (
        <div className="space-y-6">
          {/* Performance Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gray-750 rounded-lg p-4">
              <h4 className="text-white font-medium mb-3">Performance Breakdown</h4>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Largest Win</span>
                  <span className="text-green-400 font-medium">
                    {formatCurrency(riskMetrics.largestWin)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Largest Loss</span>
                  <span className="text-red-400 font-medium">
                    {formatCurrency(riskMetrics.largestLoss)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Consecutive Wins</span>
                  <span className="text-white font-medium">{riskMetrics.consecutiveWins}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Consecutive Losses</span>
                  <span className="text-white font-medium">{riskMetrics.consecutiveLosses}</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-750 rounded-lg p-4">
              <h4 className="text-white font-medium mb-3">Risk Assessment</h4>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Risk Level</span>
                  <span className={`font-medium ${riskAssessment.color}`}>
                    {riskAssessment.level}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Consistency Score</span>
                  <span className="text-white font-medium">
                    {formatPercentage(derivedMetrics.consistency)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Avg Trade Size</span>
                  <span className="text-white font-medium">
                    {formatCurrency(derivedMetrics.avgTradeSize)}
                  </span>
                </div>
              </div>
              <div className="mt-4 p-3 bg-gray-700 rounded text-sm text-gray-300">
                {riskAssessment.description}
              </div>
            </div>
          </div>

          {/* Risk Indicators */}
          <div className="bg-gray-750 rounded-lg p-4">
            <h4 className="text-white font-medium mb-4">Risk Indicators</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className={`text-2xl font-bold mb-1 ${getMetricColor('sharpeRatio', riskMetrics.sharpeRatio)}`}>
                  {riskMetrics.sharpeRatio >= 1.5 ? '✓' : riskMetrics.sharpeRatio >= 1.0 ? '⚠' : '✗'}
                </div>
                <div className="text-sm text-gray-400">Risk-Adjusted Returns</div>
                <div className="text-xs text-gray-500 mt-1">
                  Target: ≥ 1.5
                </div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold mb-1 ${getMetricColor('maxDrawdown', riskMetrics.maxDrawdown)}`}>
                  {riskMetrics.maxDrawdown <= 5 ? '✓' : riskMetrics.maxDrawdown <= 10 ? '⚠' : '✗'}
                </div>
                <div className="text-sm text-gray-400">Drawdown Control</div>
                <div className="text-xs text-gray-500 mt-1">
                  Target: ≤ 5%
                </div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold mb-1 ${getMetricColor('winRate', riskMetrics.winRate)}`}>
                  {riskMetrics.winRate >= 60 ? '✓' : riskMetrics.winRate >= 50 ? '⚠' : '✗'}
                </div>
                <div className="text-sm text-gray-400">Win Consistency</div>
                <div className="text-xs text-gray-500 mt-1">
                  Target: ≥ 60%
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}