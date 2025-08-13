'use client'

import { useMemo } from 'react'
import { PerformanceReport, BenchmarkComparison } from '@/types/analytics'

/**
 * Props for AggregateMetrics component
 */
interface AggregateMetricsProps {
  /** Performance report data */
  performanceReport?: PerformanceReport
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
}

/**
 * Aggregate performance metrics display component
 * Shows portfolio-wide performance indicators and key metrics
 */
export function AggregateMetrics({
  performanceReport,
  loading = false,
  error
}: AggregateMetricsProps) {
  
  // Calculate additional derived metrics
  const derivedMetrics = useMemo(() => {
    if (!performanceReport) return null

    const { aggregateMetrics, accountComparisons } = performanceReport
    
    // Portfolio composition analysis
    const totalCapital = accountComparisons.reduce((sum, acc) => sum + acc.currentBalance, 0)
    const totalInitialCapital = accountComparisons.reduce((sum, acc) => sum + acc.initialBalance, 0)
    
    // Risk metrics
    const accountReturns = accountComparisons.map(acc => acc.metrics.totalReturn)
    const avgReturn = accountReturns.reduce((sum, ret) => sum + ret, 0) / accountReturns.length
    const returnVariance = accountReturns.reduce((sum, ret) => sum + Math.pow(ret - avgReturn, 2), 0) / accountReturns.length
    const portfolioVolatility = Math.sqrt(returnVariance)
    
    // Performance ratios
    const informationRatio = portfolioVolatility > 0 ? (aggregateMetrics.totalReturn - 2) / portfolioVolatility : 0 // Assuming 2% risk-free rate
    const gainToPainRatio = aggregateMetrics.maxDrawdown !== 0 ? aggregateMetrics.totalReturn / Math.abs(aggregateMetrics.maxDrawdown) : 0
    
    // Trading efficiency metrics
    const totalTrades = aggregateMetrics.totalTrades
    const avgTradeSize = totalCapital / totalTrades
    const profitPerTrade = aggregateMetrics.totalPnL / totalTrades
    const tradesPerDay = totalTrades / 30 // Assuming 30-day period
    
    return {
      totalCapital,
      totalInitialCapital,
      portfolioVolatility,
      informationRatio,
      gainToPainRatio,
      avgTradeSize,
      profitPerTrade,
      tradesPerDay,
      capitalUtilization: (totalCapital - totalInitialCapital) / totalInitialCapital * 100,
      riskAdjustedReturn: aggregateMetrics.totalReturn / Math.max(portfolioVolatility, 1)
    }
  }, [performanceReport])

  // Mock benchmark data (would come from API in real implementation)
  const benchmarkComparisons: BenchmarkComparison[] = useMemo(() => [
    {
      name: 'S&P 500',
      symbol: 'SPY',
      portfolioReturn: performanceReport?.aggregateMetrics.totalReturn || 0,
      benchmarkReturn: 8.5, // Mock data
      excessReturn: (performanceReport?.aggregateMetrics.totalReturn || 0) - 8.5,
      beta: 0.65,
      alpha: 2.3,
      correlation: 0.23,
      trackingError: 5.2,
      informationRatio: 0.44
    },
    {
      name: 'NASDAQ 100',
      symbol: 'QQQ',
      portfolioReturn: performanceReport?.aggregateMetrics.totalReturn || 0,
      benchmarkReturn: 12.3,
      excessReturn: (performanceReport?.aggregateMetrics.totalReturn || 0) - 12.3,
      beta: 0.45,
      alpha: 1.8,
      correlation: 0.18,
      trackingError: 6.8,
      informationRatio: 0.26
    },
    {
      name: 'Forex Index',
      symbol: 'DXY',
      portfolioReturn: performanceReport?.aggregateMetrics.totalReturn || 0,
      benchmarkReturn: 3.2,
      excessReturn: (performanceReport?.aggregateMetrics.totalReturn || 0) - 3.2,
      beta: 0.12,
      alpha: 8.9,
      correlation: 0.08,
      trackingError: 2.1,
      informationRatio: 4.24
    }
  ], [performanceReport])

  // Format currency values
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  // Format percentage values
  const formatPercentage = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: value !== 0 ? 'always' : 'never'
    }).format(value / 100)
  }

  // Format number with appropriate precision
  const formatNumber = (value: number, decimals: number = 2): string => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
      signDisplay: value !== 0 ? 'always' : 'never'
    }).format(value)
  }

  // Get color for metric based on value and thresholds
  const getMetricColor = (value: number, goodThreshold: number, excellentThreshold: number, inverse: boolean = false): string => {
    if (inverse) {
      if (value <= excellentThreshold) return 'text-green-400'
      if (value <= goodThreshold) return 'text-yellow-400'
      return 'text-red-400'
    } else {
      if (value >= excellentThreshold) return 'text-green-400'
      if (value >= goodThreshold) return 'text-yellow-400'
      return 'text-red-400'
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="bg-gray-750 rounded-lg p-4">
                <div className="h-4 bg-gray-700 rounded mb-2"></div>
                <div className="h-6 bg-gray-700 rounded"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
        <div className="text-red-400 font-medium">Error Loading Metrics</div>
        <div className="text-red-200 text-sm mt-1">{error}</div>
      </div>
    )
  }

  // No data state
  if (!performanceReport || !derivedMetrics) {
    return (
      <div className="bg-gray-750 rounded-lg p-8 text-center">
        <div className="text-gray-400 text-lg">No Performance Data Available</div>
        <div className="text-gray-500 text-sm mt-2">
          Select accounts and a date range to view analytics
        </div>
      </div>
    )
  }

  const { aggregateMetrics } = performanceReport

  return (
    <div className="space-y-6">
      {/* Primary Performance Metrics */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Portfolio Performance Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Total P&L */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-1">Total P&L</div>
            <div className={`text-2xl font-bold ${aggregateMetrics.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(aggregateMetrics.totalPnL)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              {formatCurrency(derivedMetrics.profitPerTrade)} per trade
            </div>
          </div>

          {/* Total Return */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-1">Total Return</div>
            <div className={`text-2xl font-bold ${aggregateMetrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatPercentage(aggregateMetrics.totalReturn)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              {formatPercentage(aggregateMetrics.annualizedReturn)} annualized
            </div>
          </div>

          {/* Win Rate */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-1">Win Rate</div>
            <div className={`text-2xl font-bold ${getMetricColor(aggregateMetrics.winRate, 50, 65)}`}>
              {formatPercentage(aggregateMetrics.winRate)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              {aggregateMetrics.totalTrades} total trades
            </div>
          </div>

          {/* Sharpe Ratio */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-1">Sharpe Ratio</div>
            <div className={`text-2xl font-bold ${getMetricColor(aggregateMetrics.sharpeRatio, 1.0, 2.0)}`}>
              {formatNumber(aggregateMetrics.sharpeRatio)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              Risk-adjusted return
            </div>
          </div>
        </div>
      </div>

      {/* Risk Metrics */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Risk Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Max Drawdown */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-1">Max Drawdown</div>
            <div className={`text-2xl font-bold ${getMetricColor(aggregateMetrics.maxDrawdownPercent, -10, -5, true)}`}>
              {formatPercentage(aggregateMetrics.maxDrawdownPercent)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              {formatCurrency(aggregateMetrics.maxDrawdown)} absolute
            </div>
          </div>

          {/* Profit Factor */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-1">Profit Factor</div>
            <div className={`text-2xl font-bold ${getMetricColor(aggregateMetrics.profitFactor, 1.5, 2.0)}`}>
              {formatNumber(aggregateMetrics.profitFactor)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              Gross profit / Gross loss
            </div>
          </div>

          {/* Volatility */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-1">Portfolio Volatility</div>
            <div className={`text-2xl font-bold ${getMetricColor(derivedMetrics.portfolioVolatility, 15, 10, true)}`}>
              {formatPercentage(derivedMetrics.portfolioVolatility)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              Standard deviation
            </div>
          </div>

          {/* Calmar Ratio */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-1">Calmar Ratio</div>
            <div className={`text-2xl font-bold ${getMetricColor(aggregateMetrics.calmarRatio, 1.0, 2.0)}`}>
              {formatNumber(aggregateMetrics.calmarRatio)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              Annual return / Max DD
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Metrics */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Advanced Analytics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Trading Efficiency */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-3">Trading Efficiency</div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Avg Trade Size</span>
                <span className="text-white font-medium">{formatCurrency(derivedMetrics.avgTradeSize)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Trades per Day</span>
                <span className="text-white font-medium">{derivedMetrics.tradesPerDay.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Profit per Trade</span>
                <span className={`font-medium ${derivedMetrics.profitPerTrade >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrency(derivedMetrics.profitPerTrade)}
                </span>
              </div>
            </div>
          </div>

          {/* Win/Loss Analysis */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-3">Win/Loss Analysis</div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Average Win</span>
                <span className="text-green-400 font-medium">{formatCurrency(aggregateMetrics.averageWin)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Average Loss</span>
                <span className="text-red-400 font-medium">{formatCurrency(aggregateMetrics.averageLoss)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Best Trade</span>
                <span className="text-green-400 font-medium">{formatCurrency(aggregateMetrics.bestTrade)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Worst Trade</span>
                <span className="text-red-400 font-medium">{formatCurrency(aggregateMetrics.worstTrade)}</span>
              </div>
            </div>
          </div>

          {/* Streak Analysis */}
          <div className="bg-gray-750 rounded-lg p-4">
            <div className="text-gray-400 text-sm mb-3">Streak Analysis</div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Longest Win Streak</span>
                <span className="text-green-400 font-medium">{aggregateMetrics.longestWinStreak}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Longest Loss Streak</span>
                <span className="text-red-400 font-medium">{aggregateMetrics.longestLossStreak}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300 text-sm">Capital Utilization</span>
                <span className={`font-medium ${derivedMetrics.capitalUtilization >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercentage(derivedMetrics.capitalUtilization)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Benchmark Comparisons */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Benchmark Performance Comparison</h3>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {benchmarkComparisons.map((benchmark) => (
            <div key={benchmark.symbol} className="bg-gray-750 rounded-lg p-4">
              <div className="flex justify-between items-center mb-3">
                <div>
                  <div className="text-white font-medium">{benchmark.name}</div>
                  <div className="text-gray-400 text-sm">{benchmark.symbol}</div>
                </div>
                <div className={`text-lg font-bold ${benchmark.excessReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercentage(benchmark.excessReturn)}
                </div>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-300">Portfolio Return</span>
                  <span className="text-white">{formatPercentage(benchmark.portfolioReturn)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Benchmark Return</span>
                  <span className="text-white">{formatPercentage(benchmark.benchmarkReturn)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Alpha</span>
                  <span className={`${benchmark.alpha >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatNumber(benchmark.alpha)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Beta</span>
                  <span className="text-white">{formatNumber(benchmark.beta)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Information Ratio</span>
                  <span className={`${benchmark.informationRatio >= 0.5 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {formatNumber(benchmark.informationRatio)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Summary */}
      <div className="bg-gray-750 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Portfolio Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="text-gray-400 text-sm mb-2">Total Capital Deployed</div>
            <div className="text-2xl font-bold text-white mb-1">
              {formatCurrency(derivedMetrics.totalCapital)}
            </div>
            <div className="text-gray-500 text-sm">
              Initial: {formatCurrency(derivedMetrics.totalInitialCapital)}
            </div>
          </div>
          
          <div>
            <div className="text-gray-400 text-sm mb-2">Risk-Adjusted Performance</div>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-300">Sortino Ratio</span>
                <span className={`font-medium ${getMetricColor(aggregateMetrics.sortinoRatio, 1.5, 2.5)}`}>
                  {formatNumber(aggregateMetrics.sortinoRatio)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Information Ratio</span>
                <span className={`font-medium ${getMetricColor(derivedMetrics.informationRatio, 0.5, 1.0)}`}>
                  {formatNumber(derivedMetrics.informationRatio)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Gain-to-Pain Ratio</span>
                <span className={`font-medium ${getMetricColor(derivedMetrics.gainToPainRatio, 1.0, 2.0)}`}>
                  {formatNumber(derivedMetrics.gainToPainRatio)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}