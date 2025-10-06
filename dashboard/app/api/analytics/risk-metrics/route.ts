import { NextRequest, NextResponse } from 'next/server'
import { RiskMetrics, DrawdownBucket } from '@/types/analytics'

/**
 * Calculate Sortino Ratio
 * Uses only downside deviation (negative returns)
 */
function calculateSortinoRatio(returns: number[], riskFreeRate: number = 0.02): number {
  if (returns.length === 0) return 0

  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length

  // Downside deviation (only negative returns)
  const downsideReturns = returns.filter(r => r < 0)
  if (downsideReturns.length === 0) return avgReturn > 0 ? 999 : 0

  const downsideVariance =
    downsideReturns.reduce((sum, r) => sum + r * r, 0) / downsideReturns.length
  const downsideDeviation = Math.sqrt(downsideVariance)

  if (downsideDeviation === 0) return avgReturn > 0 ? 999 : 0

  return (avgReturn - riskFreeRate / 252) / downsideDeviation
}

/**
 * Calculate Calmar Ratio
 * Annual return divided by maximum drawdown
 */
function calculateCalmarRatio(annualReturn: number, maxDrawdownPercent: number): number {
  if (maxDrawdownPercent === 0) return annualReturn > 0 ? 999 : 0
  return annualReturn / Math.abs(maxDrawdownPercent)
}

/**
 * Calculate drawdown distribution buckets
 */
function calculateDrawdownDistribution(drawdowns: number[]): DrawdownBucket[] {
  const buckets: DrawdownBucket[] = [
    { bucket: '0-5%', count: 0, percentage: 0 },
    { bucket: '5-10%', count: 0, percentage: 0 },
    { bucket: '10-15%', count: 0, percentage: 0 },
    { bucket: '15-20%', count: 0, percentage: 0 },
    { bucket: '>20%', count: 0, percentage: 0 }
  ]

  drawdowns.forEach(dd => {
    const percent = Math.abs(dd)
    if (percent < 5) buckets[0].count++
    else if (percent < 10) buckets[1].count++
    else if (percent < 15) buckets[2].count++
    else if (percent < 20) buckets[3].count++
    else buckets[4].count++
  })

  const total = drawdowns.length || 1
  buckets.forEach(bucket => {
    bucket.percentage = (bucket.count / total) * 100
  })

  return buckets
}

/**
 * Determine volatility trend
 */
function getVolatilityTrend(recent: number, historical: number): 'increasing' | 'stable' | 'decreasing' {
  const change = ((recent - historical) / historical) * 100

  if (change > 10) return 'increasing'
  if (change < -10) return 'decreasing'
  return 'stable'
}

/**
 * Generate mock risk metrics
 * In production, calculate from actual trade data
 */
function generateRiskMetrics(): RiskMetrics {
  // Mock returns data
  const returns: number[] = []
  for (let i = 0; i < 100; i++) {
    returns.push((Math.random() - 0.45) * 0.05) // Slightly positive bias
  }

  // Mock drawdowns
  const drawdowns: number[] = []
  for (let i = 0; i < 50; i++) {
    drawdowns.push(-(Math.random() * 25)) // 0% to -25%
  }

  const sharpeRatio = 1.42
  const annualReturn = 0.35 // 35%
  const maxDrawdownPercent = -18.5

  const sortinoRatio = calculateSortinoRatio(returns)
  const calmarRatio = calculateCalmarRatio(annualReturn * 100, maxDrawdownPercent)
  const distribution = calculateDrawdownDistribution(drawdowns)

  // Volatility calculations
  const dailyVolatility = 0.018 // 1.8%
  const monthlyVolatility = dailyVolatility * Math.sqrt(21) // Annualized monthly
  const recentVolatility = 0.021
  const historicalVolatility = 0.017

  return {
    sharpeRatio,
    sortinoRatio,
    calmarRatio,
    drawdown: {
      max: -18500,
      maxPercent: -18.5,
      avg: -4200,
      avgPercent: -4.2,
      current: -2300,
      currentPercent: -2.3,
      avgRecoveryDays: 12,
      maxRecoveryDays: 45,
      distribution
    },
    volatility: {
      daily: dailyVolatility,
      monthly: monthlyVolatility,
      trend: getVolatilityTrend(recentVolatility, historicalVolatility)
    },
    riskReward: {
      avgRRRatio: 2.8,
      winRate: 62.5,
      expectancy: 185.50,
      profitFactor: 2.35
    }
  }
}

/**
 * GET /api/analytics/risk-metrics
 * Returns comprehensive risk-adjusted metrics
 */
export async function GET(request: NextRequest) {
  try {
    const metrics = generateRiskMetrics()
    return NextResponse.json(metrics)
  } catch (error) {
    console.error('Error fetching risk metrics:', error)
    return NextResponse.json(
      { error: 'Failed to fetch risk metrics' },
      { status: 500 }
    )
  }
}
