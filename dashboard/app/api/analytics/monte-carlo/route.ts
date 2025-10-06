/**
 * Monte Carlo Simulation API - Story 8.1
 * Provides probabilistic P&L projections with confidence intervals
 */

import { NextRequest, NextResponse } from 'next/server'
import { MonteCarloData, StabilityMetrics } from '@/types/analytics'

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

// In-memory cache for development (production should use Redis)
let monteCarloCache: { data: MonteCarloData | null; timestamp: number } = {
  data: null,
  timestamp: 0,
}

const CACHE_TTL = 24 * 60 * 60 * 1000 // 24 hours in milliseconds
const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8089'

/**
 * Monte Carlo Simulator Class
 */
class MonteCarloSimulator {
  private winRate: number = 0.6
  private avgProfit: number = 150
  private avgLoss: number = -80
  private stdDev: number = 100
  private tradesPerDay: number = 2

  constructor(historicalTrades: Trade[]) {
    this.calculateParameters(historicalTrades)
  }

  /**
   * Calculate simulation parameters from historical trades
   */
  private calculateParameters(trades: Trade[]): void {
    if (trades.length === 0) {
      // Default parameters
      this.winRate = 0.6
      this.avgProfit = 150
      this.avgLoss = -80
      this.stdDev = 100
      this.tradesPerDay = 2
      return
    }

    // Calculate win rate
    const winningTrades = trades.filter((t) => (t.profit || t.pnl || 0) > 0)
    this.winRate = winningTrades.length / trades.length

    // Calculate average profit and loss
    const profits = winningTrades.map((t) => t.profit || t.pnl || 0)
    const losses = trades
      .filter((t) => (t.profit || t.pnl || 0) <= 0)
      .map((t) => t.profit || t.pnl || 0)

    this.avgProfit = profits.length > 0 ? profits.reduce((a, b) => a + b, 0) / profits.length : 100
    this.avgLoss = losses.length > 0 ? losses.reduce((a, b) => a + b, 0) / losses.length : -50

    // Calculate standard deviation
    const allPnL = trades.map((t) => t.profit || t.pnl || 0)
    const mean = allPnL.reduce((a, b) => a + b, 0) / allPnL.length
    const variance = allPnL.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / allPnL.length
    this.stdDev = Math.sqrt(variance)

    // Calculate trades per day
    const sortedTrades = trades
      .map((t) => new Date(t.openTime || t.timestamp).getTime())
      .sort((a, b) => a - b)
    const firstTrade = sortedTrades[0]
    const lastTrade = sortedTrades[sortedTrades.length - 1]
    const daysSpan = (lastTrade - firstTrade) / (24 * 60 * 60 * 1000)
    this.tradesPerDay = daysSpan > 0 ? trades.length / daysSpan : 2
  }

  /**
   * Run Monte Carlo simulation
   */
  runSimulation(days: number = 180, simulations: number = 1000): MonteCarloData {
    const results: number[][] = []

    // Run simulations
    for (let sim = 0; sim < simulations; sim++) {
      const dailyPnL: number[] = []
      let cumulativePnL = 0

      for (let day = 0; day < days; day++) {
        // Generate number of trades for this day (Poisson distribution approximation)
        const numTrades = this.poissonRandom(this.tradesPerDay)

        let dayPnL = 0
        for (let trade = 0; trade < numTrades; trade++) {
          // Determine if win or loss
          if (Math.random() < this.winRate) {
            // Winning trade
            dayPnL += this.normalRandom(this.avgProfit, this.stdDev)
          } else {
            // Losing trade
            dayPnL += this.normalRandom(this.avgLoss, this.stdDev)
          }
        }

        cumulativePnL += dayPnL
        dailyPnL.push(cumulativePnL)
      }

      results.push(dailyPnL)
    }

    // Calculate statistics
    return this.calculateStatistics(results)
  }

  /**
   * Calculate statistics from simulation results
   */
  private calculateStatistics(results: number[][]): MonteCarloData {
    const days = results[0].length

    // Convert results to matrix (days x simulations)
    const matrix: number[][] = []
    for (let day = 0; day < days; day++) {
      const dayResults: number[] = []
      for (let sim = 0; sim < results.length; sim++) {
        dayResults.push(results[sim][day])
      }
      matrix.push(dayResults.sort((a, b) => a - b))
    }

    // Calculate percentiles for confidence intervals
    const ci95Lower: number[] = []
    const ci95Upper: number[] = []
    const ci99Lower: number[] = []
    const ci99Upper: number[] = []
    const expected: number[] = []

    for (let day = 0; day < days; day++) {
      const dayResults = matrix[day]
      const n = dayResults.length

      ci95Lower.push(this.percentile(dayResults, 2.5))
      ci95Upper.push(this.percentile(dayResults, 97.5))
      ci99Lower.push(this.percentile(dayResults, 0.5))
      ci99Upper.push(this.percentile(dayResults, 99.5))

      // Expected value (mean)
      const mean = dayResults.reduce((a, b) => a + b, 0) / n
      expected.push(mean)
    }

    return {
      expectedTrajectory: expected.map((v) => Number(v.toFixed(2))),
      confidenceIntervals: {
        '95': {
          lower: ci95Lower.map((v) => Number(v.toFixed(2))),
          upper: ci95Upper.map((v) => Number(v.toFixed(2))),
        },
        '99': {
          lower: ci99Lower.map((v) => Number(v.toFixed(2))),
          upper: ci99Upper.map((v) => Number(v.toFixed(2))),
        },
      },
      simulationsRun: results.length,
      parameters: {
        winRate: Number(this.winRate.toFixed(3)),
        avgProfit: Number(this.avgProfit.toFixed(2)),
        avgLoss: Number(this.avgLoss.toFixed(2)),
        stdDev: Number(this.stdDev.toFixed(2)),
        tradesPerDay: Number(this.tradesPerDay.toFixed(2)),
      },
      calculatedAt: Date.now(),
      cachedUntil: Date.now() + CACHE_TTL,
    }
  }

  /**
   * Calculate percentile from sorted array
   */
  private percentile(sortedArray: number[], percentile: number): number {
    const index = (percentile / 100) * (sortedArray.length - 1)
    const lower = Math.floor(index)
    const upper = Math.ceil(index)
    const weight = index % 1

    if (lower === upper) {
      return sortedArray[lower]
    }

    return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight
  }

  /**
   * Generate random number from normal distribution (Box-Muller transform)
   */
  private normalRandom(mean: number, stdDev: number): number {
    const u1 = Math.random()
    const u2 = Math.random()
    const z0 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
    return mean + z0 * stdDev
  }

  /**
   * Generate random number from Poisson distribution (approximation)
   */
  private poissonRandom(lambda: number): number {
    const L = Math.exp(-lambda)
    let k = 0
    let p = 1

    do {
      k++
      p *= Math.random()
    } while (p > L)

    return k - 1
  }

  /**
   * Get parameters for API response
   */
  getParameters() {
    return {
      winRate: this.winRate,
      avgProfit: this.avgProfit,
      avgLoss: this.avgLoss,
      stdDev: this.stdDev,
      tradesPerDay: this.tradesPerDay,
    }
  }
}

/**
 * Calculate walk-forward and overfitting metrics
 */
function calculateStabilityMetrics(trades: Trade[]): StabilityMetrics {
  // Split data into in-sample and out-of-sample
  const splitPoint = Math.floor(trades.length * 0.7)
  const inSample = trades.slice(0, splitPoint)
  const outSample = trades.slice(splitPoint)

  // Calculate performance metrics for both samples
  const inSampleWinRate = calculateWinRate(inSample)
  const outSampleWinRate = calculateWinRate(outSample)

  const inSampleAvgReturn = calculateAvgReturn(inSample)
  const outSampleAvgReturn = calculateAvgReturn(outSample)

  // Walk-forward stability score (0-100)
  // Based on consistency of performance across time periods
  const performanceDegradation = Math.abs(inSampleWinRate - outSampleWinRate)
  const walkForwardScore = Math.max(0, 100 - performanceDegradation * 200)

  // Overfitting score (0-1, lower is better)
  // Based on difference between in-sample and out-of-sample performance
  const returnDegradation =
    inSampleAvgReturn !== 0
      ? Math.abs((inSampleAvgReturn - outSampleAvgReturn) / inSampleAvgReturn)
      : 0
  const overfittingScore = Math.min(1, returnDegradation)

  // Out-of-sample validation percentage
  const outOfSampleValidation =
    inSampleAvgReturn !== 0 ? (outSampleAvgReturn / inSampleAvgReturn) * 100 : 50

  return {
    walkForwardScore: Number(walkForwardScore.toFixed(1)),
    overfittingScore: Number(overfittingScore.toFixed(3)),
    outOfSampleValidation: Number(Math.max(0, Math.min(100, outOfSampleValidation)).toFixed(1)),
  }
}

/**
 * Calculate win rate from trades
 */
function calculateWinRate(trades: Trade[]): number {
  if (trades.length === 0) return 0
  const winners = trades.filter((t) => (t.profit || t.pnl || 0) > 0).length
  return winners / trades.length
}

/**
 * Calculate average return from trades
 */
function calculateAvgReturn(trades: Trade[]): number {
  if (trades.length === 0) return 0
  const totalPnL = trades.reduce((sum, t) => sum + (t.profit || t.pnl || 0), 0)
  return totalPnL / trades.length
}

/**
 * GET /api/analytics/monte-carlo
 * Run Monte Carlo simulation and return projections
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const days = parseInt(searchParams.get('days') || '180')
    const simulations = parseInt(searchParams.get('simulations') || '1000')
    const forceRefresh = searchParams.get('refresh') === 'true'
    const includeStability = searchParams.get('stability') === 'true'

    // Validate parameters
    if (days < 1 || days > 365) {
      return NextResponse.json({ error: 'Days must be between 1 and 365' }, { status: 400 })
    }
    if (simulations < 100 || simulations > 10000) {
      return NextResponse.json(
        { error: 'Simulations must be between 100 and 10000' },
        { status: 400 }
      )
    }

    // Check cache
    const now = Date.now()
    if (!forceRefresh && monteCarloCache.data && now - monteCarloCache.timestamp < CACHE_TTL) {
      return NextResponse.json({
        monteCarlo: monteCarloCache.data,
        stability: includeStability ? calculateStabilityMetrics([]) : undefined,
      })
    }

    // Fetch trade history
    let trades: Trade[] = []

    try {
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
      trades = generateMockTrades(90)
    }

    // Run Monte Carlo simulation
    const simulator = new MonteCarloSimulator(trades)
    const monteCarloData = simulator.runSimulation(days, simulations)

    // Update cache
    monteCarloCache = {
      data: monteCarloData,
      timestamp: now,
    }

    // Calculate stability metrics if requested
    const stabilityMetrics = includeStability ? calculateStabilityMetrics(trades) : undefined

    return NextResponse.json({
      monteCarlo: monteCarloData,
      stability: stabilityMetrics,
    })
  } catch (error) {
    console.error('Error running Monte Carlo simulation:', error)
    return NextResponse.json(
      { error: 'Failed to run Monte Carlo simulation', details: (error as Error).message },
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
