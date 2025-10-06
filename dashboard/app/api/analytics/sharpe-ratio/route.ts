/**
 * Sharpe Ratio Analytics API - Story 8.1
 * Provides risk-adjusted return metrics with rolling windows
 */

import { NextRequest, NextResponse } from 'next/server'
import { SharpeRatioData } from '@/types/analytics'

// In-memory cache for development (production should use Redis)
let sharpeCache: { data: SharpeRatioData | null; timestamp: number } = {
  data: null,
  timestamp: 0,
}

const CACHE_TTL = 24 * 60 * 60 * 1000 // 24 hours in milliseconds
const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8089'

/**
 * Calculate Sharpe ratio from trade data
 */
interface Trade {
  id?: string
  openTime?: string
  timestamp?: string
  profit?: number
  pnl?: number
  units?: number
  size?: number
  instrument?: string
}

function calculateSharpeRatio(
  trades: Trade[],
  period: string = '30d',
  riskFreeRate: number = 0.02
): SharpeRatioData {
  const periodDays = parseInt(period.replace('d', ''))
  const now = new Date()
  const periodStart = new Date(now.getTime() - periodDays * 24 * 60 * 60 * 1000)

  // Filter trades within period
  const periodTrades = trades.filter((t) => {
    const tradeDate = new Date(t.openTime || t.timestamp || '')
    return tradeDate >= periodStart && tradeDate <= now
  })

  if (periodTrades.length === 0) {
    return createEmptySharpeData(riskFreeRate)
  }

  // Calculate Sharpe ratio for different windows
  const rollingWindows = {
    '7d': calculateWindow(trades, 7, riskFreeRate),
    '14d': calculateWindow(trades, 14, riskFreeRate),
    '30d': calculateWindow(trades, 30, riskFreeRate),
    '90d': calculateWindow(trades, 90, riskFreeRate),
  }

  // Calculate historical data (last 90 days)
  const historicalData = calculateHistoricalSharpe(trades, 90, riskFreeRate)

  // Current Sharpe (30-day default)
  const currentSharpe = rollingWindows['30d'].value

  // Determine threshold and interpretation
  const { thresholdLevel, interpretation } = getThresholdInfo(currentSharpe)

  return {
    currentSharpe,
    rollingWindows,
    historicalData,
    interpretation,
    thresholdLevel,
    calculatedAt: Date.now(),
    riskFreeRate,
    totalTrades: periodTrades.length,
  }
}

/**
 * Calculate Sharpe ratio for a specific window
 */
function calculateWindow(
  trades: Trade[],
  days: number,
  riskFreeRate: number
): { value: number; trend: 'up' | 'down' | 'stable'; changePercent: number } {
  const now = new Date()
  const windowStart = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
  const previousWindowStart = new Date(now.getTime() - days * 2 * 24 * 60 * 60 * 1000)

  // Current window
  const currentTrades = trades.filter((t) => {
    const tradeDate = new Date(t.openTime || t.timestamp || '')
    return tradeDate >= windowStart && tradeDate <= now
  })

  // Previous window (for comparison)
  const previousTrades = trades.filter((t) => {
    const tradeDate = new Date(t.openTime || t.timestamp || '')
    return tradeDate >= previousWindowStart && tradeDate < windowStart
  })

  const currentSharpe = calculateSharpeValue(currentTrades, riskFreeRate)
  const previousSharpe = calculateSharpeValue(previousTrades, riskFreeRate)

  // Calculate trend
  let trend: 'up' | 'down' | 'stable' = 'stable'
  let changePercent = 0

  if (previousSharpe !== 0) {
    changePercent = ((currentSharpe - previousSharpe) / Math.abs(previousSharpe)) * 100

    if (Math.abs(changePercent) < 5) {
      trend = 'stable'
    } else if (changePercent > 0) {
      trend = 'up'
    } else {
      trend = 'down'
    }
  }

  return {
    value: currentSharpe,
    trend,
    changePercent,
  }
}

/**
 * Calculate Sharpe ratio value from trades
 */
function calculateSharpeValue(trades: Trade[], riskFreeRate: number): number {
  if (trades.length === 0) return 0

  const dailyReturns = calculateDailyReturns(trades)
  if (dailyReturns.length === 0) return 0

  // Average daily return
  const avgReturn = dailyReturns.reduce((sum, r) => sum + r, 0) / dailyReturns.length

  // Standard deviation of returns
  const variance =
    dailyReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) /
    (dailyReturns.length - 1)
  const stdDev = Math.sqrt(variance)

  if (stdDev === 0) return 0

  // Convert annual risk-free rate to daily
  const dailyRiskFreeRate = riskFreeRate / 252

  // Calculate Sharpe ratio
  const sharpe = (avgReturn - dailyRiskFreeRate) / stdDev

  // Annualize Sharpe ratio (multiply by sqrt of trading days)
  return sharpe * Math.sqrt(252)
}

/**
 * Calculate daily returns from trades
 */
function calculateDailyReturns(trades: Trade[]): number[] {
  if (trades.length === 0) return []

  // Group trades by date
  const tradesByDate = new Map<string, number>()

  trades.forEach((trade) => {
    const date = new Date(trade.openTime || trade.timestamp || '').toISOString().split('T')[0]
    const pnl = trade.profit || trade.pnl || 0
    tradesByDate.set(date, (tradesByDate.get(date) || 0) + pnl)
  })

  // Convert to returns array
  const returns: number[] = []
  const dates = Array.from(tradesByDate.keys()).sort()

  // Estimate initial capital from first trades
  const initialCapital = estimateInitialCapital(trades)

  dates.forEach((date) => {
    const dailyPnL = tradesByDate.get(date) || 0
    const dailyReturn = dailyPnL / initialCapital
    returns.push(dailyReturn)
  })

  return returns
}

/**
 * Estimate initial capital from trades
 */
function estimateInitialCapital(trades: Trade[]): number {
  // Use average position size or default
  if (trades.length === 0) return 10000

  const avgPositionSize =
    trades.reduce((sum, t) => sum + Math.abs(t.units || t.size || 10000), 0) / trades.length

  return avgPositionSize * 10 // Assume 10:1 leverage
}

/**
 * Calculate historical Sharpe ratio data points
 */
function calculateHistoricalSharpe(
  trades: Trade[],
  days: number,
  riskFreeRate: number
): Array<{ date: string; sharpeRatio: number }> {
  const historicalData: Array<{ date: string; sharpeRatio: number }> = []
  const now = new Date()

  // Calculate Sharpe for each day in the period
  for (let i = days; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
    const dateStr = date.toISOString().split('T')[0]

    // Calculate 30-day trailing Sharpe for this date
    const windowEnd = date
    const windowStart = new Date(date.getTime() - 30 * 24 * 60 * 60 * 1000)

    const windowTrades = trades.filter((t) => {
      const tradeDate = new Date(t.openTime || t.timestamp || '')
      return tradeDate >= windowStart && tradeDate <= windowEnd
    })

    const sharpeRatio = calculateSharpeValue(windowTrades, riskFreeRate)

    historicalData.push({
      date: dateStr,
      sharpeRatio: Number(sharpeRatio.toFixed(3)),
    })
  }

  return historicalData
}

/**
 * Determine threshold level and interpretation
 */
function getThresholdInfo(sharpe: number): {
  thresholdLevel: 'outstanding' | 'excellent' | 'good' | 'acceptable' | 'poor'
  interpretation: string
} {
  if (sharpe >= 2.0) {
    return {
      thresholdLevel: 'outstanding',
      interpretation: 'Outstanding risk-adjusted returns - exceptional performance',
    }
  } else if (sharpe >= 1.5) {
    return {
      thresholdLevel: 'excellent',
      interpretation: 'Excellent risk-adjusted returns - strong performance',
    }
  } else if (sharpe >= 1.0) {
    return {
      thresholdLevel: 'good',
      interpretation: 'Good risk-adjusted returns - solid performance',
    }
  } else if (sharpe >= 0.5) {
    return {
      thresholdLevel: 'acceptable',
      interpretation: 'Acceptable risk-adjusted returns - room for improvement',
    }
  } else {
    return {
      thresholdLevel: 'poor',
      interpretation: 'Poor risk-adjusted returns - significant improvement needed',
    }
  }
}

/**
 * Create empty Sharpe data when no trades available
 */
function createEmptySharpeData(riskFreeRate: number): SharpeRatioData {
  return {
    currentSharpe: 0,
    rollingWindows: {
      '7d': { value: 0, trend: 'stable', changePercent: 0 },
      '14d': { value: 0, trend: 'stable', changePercent: 0 },
      '30d': { value: 0, trend: 'stable', changePercent: 0 },
      '90d': { value: 0, trend: 'stable', changePercent: 0 },
    },
    historicalData: [],
    interpretation: 'No trade data available',
    thresholdLevel: 'poor',
    calculatedAt: Date.now(),
    riskFreeRate,
    totalTrades: 0,
  }
}

/**
 * GET /api/analytics/sharpe-ratio
 * Calculate and return Sharpe ratio metrics
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const period = searchParams.get('period') || '30d'
    const riskFreeRateParam = searchParams.get('riskFreeRate')
    const riskFreeRate = riskFreeRateParam ? parseFloat(riskFreeRateParam) : 0.02
    const forceRefresh = searchParams.get('refresh') === 'true'

    // Check cache
    const now = Date.now()
    if (!forceRefresh && sharpeCache.data && now - sharpeCache.timestamp < CACHE_TTL) {
      return NextResponse.json(sharpeCache.data)
    }

    // Fetch trade history from orchestrator or execution engine
    let trades: Trade[] = []

    try {
      // Try to fetch from orchestrator
      const tradesResponse = await fetch(`${ORCHESTRATOR_URL}/api/trades/history`, {
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (tradesResponse.ok) {
        const tradesData = await tradesResponse.json()
        trades = tradesData.trades || tradesData || []
      }
    } catch (fetchError) {
      console.warn('Could not fetch trades from orchestrator, using mock data:', fetchError)
      // Generate mock data for development
      trades = generateMockTrades(90)
    }

    // Calculate Sharpe ratio
    const sharpeData = calculateSharpeRatio(trades, period, riskFreeRate)

    // Update cache
    sharpeCache = {
      data: sharpeData,
      timestamp: now,
    }

    return NextResponse.json(sharpeData)
  } catch (error) {
    console.error('Error calculating Sharpe ratio:', error)
    return NextResponse.json(
      { error: 'Failed to calculate Sharpe ratio', details: (error as Error).message },
      { status: 500 }
    )
  }
}

/**
 * Generate mock trades for development
 */
function generateMockTrades(days: number): Trade[] {
  const trades: Trade[] = []
  const now = new Date()
  const winRate = 0.65
  const avgProfit = 150
  const avgLoss = -80

  for (let i = 0; i < days * 3; i++) {
    const daysAgo = Math.random() * days
    const timestamp = new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000)

    const isWin = Math.random() < winRate
    const profit = isWin
      ? avgProfit * (0.8 + Math.random() * 0.4)
      : avgLoss * (0.8 + Math.random() * 0.4)

    trades.push({
      id: `mock-${i}`,
      openTime: timestamp.toISOString(),
      timestamp: timestamp.toISOString(),
      profit: profit,
      pnl: profit,
      units: 10000,
      instrument: 'EUR_USD',
    })
  }

  return trades
}
