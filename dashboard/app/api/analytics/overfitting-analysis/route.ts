import { NextRequest, NextResponse } from 'next/server'
import { BacktestResults } from '../backtest-results/route'
import { ForwardTestResults } from '../forward-test-performance/route'

export interface OverfittingAnalysis {
  overfittingScore: number // 0-1
  degradationPercentage: number // Average across metrics
  riskLevel: 'low' | 'moderate' | 'high'
  metricDegradation: {
    [key: string]: {
      backtest: number
      forward: number
      degradation: number // %
    }
  }
  interpretation: string
  recommendations: string[]
  stabilityScore: number
}

function calculateOverfittingAnalysis(
  backtest: BacktestResults,
  forward: ForwardTestResults
): OverfittingAnalysis {
  const metrics = [
    'winRate',
    'profitFactor',
    'sharpeRatio',
    'avgWin',
    'avgLoss'
  ]

  const degradations: number[] = []
  const metricDegradation: any = {}

  metrics.forEach(metric => {
    let backtestValue: number
    let forwardValue: number

    if (metric === 'avgLoss') {
      backtestValue = backtest.metrics.avgLoss
      forwardValue = forward.metrics.avgLoss
    } else {
      backtestValue = backtest.metrics[metric as keyof typeof backtest.metrics] as number
      forwardValue = forward.metrics[metric as keyof typeof forward.metrics] as number
    }

    // Calculate degradation (negative change is degradation)
    let degradation = backtestValue !== 0
      ? ((forwardValue - backtestValue) / Math.abs(backtestValue)) * 100
      : 0

    // For avgLoss, lower is better, so inverse the sign
    if (metric === 'avgLoss') {
      degradation = -degradation
    }

    // Only count degradation (negative changes)
    if (degradation < 0) {
      degradations.push(Math.abs(degradation))
    }

    metricDegradation[metric] = {
      backtest: backtestValue,
      forward: forwardValue,
      degradation
    }
  })

  // Calculate average degradation
  const avgDegradation = degradations.length > 0
    ? degradations.reduce((sum, d) => sum + d, 0) / degradations.length
    : 0

  // Normalize to 0-1 scale (30% degradation = 1.0)
  const overfittingScore = Math.min(avgDegradation / 30, 1)

  // Determine risk level
  let riskLevel: 'low' | 'moderate' | 'high'
  if (avgDegradation < 15) riskLevel = 'low'
  else if (avgDegradation < 30) riskLevel = 'moderate'
  else riskLevel = 'high'

  // Calculate stability score
  const stabilityScore = calculateStabilityScore(forward)

  // Generate interpretation and recommendations
  const interpretation = generateInterpretation(overfittingScore, avgDegradation, stabilityScore)
  const recommendations = generateRecommendations(riskLevel, metricDegradation, stabilityScore)

  return {
    overfittingScore,
    degradationPercentage: avgDegradation,
    riskLevel,
    metricDegradation,
    interpretation,
    recommendations,
    stabilityScore
  }
}

function calculateStabilityScore(forwardTest: ForwardTestResults): number {
  if (forwardTest.dailyReturns.length < 7) return 100 // Not enough data

  // Split into weekly windows
  const windowSize = 7
  const windows: number[][] = []

  for (let i = 0; i < forwardTest.dailyReturns.length; i += windowSize) {
    const window = forwardTest.dailyReturns.slice(i, i + windowSize).map(d => d.return)
    if (window.length === windowSize) {
      windows.push(window)
    }
  }

  if (windows.length < 2) return 100 // Not enough windows

  // Calculate Sharpe ratio for each window
  const windowSharpes = windows.map(window => {
    const avg = window.reduce((sum, r) => sum + r, 0) / window.length
    const variance = window.reduce((sum, r) => sum + Math.pow(r - avg, 2), 0) / window.length
    const stdDev = Math.sqrt(variance)
    return stdDev === 0 ? 0 : (avg / stdDev) * Math.sqrt(252)
  })

  // Calculate coefficient of variation (std dev / mean)
  const mean = windowSharpes.reduce((sum, s) => sum + s, 0) / windowSharpes.length
  const variance = windowSharpes.reduce((sum, s) => sum + Math.pow(s - mean, 2), 0) / windowSharpes.length
  const stdDev = Math.sqrt(variance)
  const coefficientOfVariation = Math.abs(mean) > 0.01 ? stdDev / Math.abs(mean) : 0

  // Convert to 0-100 scale (lower CV = higher stability)
  const stabilityScore = Math.max(0, Math.min(100, 100 - (coefficientOfVariation * 100)))

  return stabilityScore
}

function generateInterpretation(score: number, degradation: number, stability: number): string {
  const stabilityText = stability > 70 ? 'stable' : stability > 30 ? 'moderately stable' : 'unstable'

  if (score < 0.3) {
    return `Low overfitting risk (${degradation.toFixed(1)}% degradation). Strategy generalizes well to unseen data and shows ${stabilityText} performance.`
  } else if (score < 0.8) {
    return `Moderate overfitting detected (${degradation.toFixed(1)}% degradation). Strategy shows ${stabilityText} performance but requires close monitoring.`
  } else {
    return `High overfitting risk (${degradation.toFixed(1)}% degradation). Strategy may be overfit to historical data with ${stabilityText} live performance.`
  }
}

function generateRecommendations(
  riskLevel: string,
  metricDegradation: any,
  stability: number
): string[] {
  const recommendations: string[] = []

  if (riskLevel === 'high') {
    recommendations.push('Consider rolling back to previous strategy version')
    recommendations.push('Re-optimize parameters with walk-forward analysis')
    recommendations.push('Increase out-of-sample validation period')
  } else if (riskLevel === 'moderate') {
    recommendations.push('Monitor performance daily for further degradation')
    recommendations.push('Review trading session optimization parameters')
  }

  // Metric-specific recommendations
  if (metricDegradation.winRate?.degradation < -15) {
    recommendations.push('Win rate declined significantly - review entry criteria')
  }

  if (metricDegradation.profitFactor?.degradation < -20) {
    recommendations.push('Profit factor dropped - adjust risk/reward ratios')
  }

  if (metricDegradation.sharpeRatio?.degradation < -20) {
    recommendations.push('Sharpe ratio degraded - consider reducing position sizes')
  }

  if (stability < 30) {
    recommendations.push('Performance is unstable - consider reducing trade frequency')
  } else if (stability < 70) {
    recommendations.push('Moderate performance volatility detected - monitor consistency')
  }

  if (recommendations.length === 0) {
    recommendations.push('Strategy performing well - continue monitoring')
    recommendations.push('Consider gradual position size increases if stability maintains')
  }

  return recommendations
}

async function fetchBacktestResults(): Promise<BacktestResults | null> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3003'
    const response = await fetch(`${baseUrl}/api/analytics/backtest-results`, {
      next: { revalidate: 300 } // Cache for 5 minutes
    })

    if (response.ok) {
      return await response.json()
    }
  } catch (error) {
    console.error('Error fetching backtest results:', error)
  }
  return null
}

async function fetchForwardTestResults(): Promise<ForwardTestResults | null> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3003'
    const response = await fetch(`${baseUrl}/api/analytics/forward-test-performance`, {
      next: { revalidate: 60 } // Cache for 1 minute
    })

    if (response.ok) {
      return await response.json()
    }
  } catch (error) {
    console.error('Error fetching forward test results:', error)
  }
  return null
}

export async function GET(request: NextRequest) {
  try {
    const backtest = await fetchBacktestResults()
    const forward = await fetchForwardTestResults()

    if (!backtest || !forward) {
      return NextResponse.json(
        { error: 'Unable to fetch backtest or forward test results' },
        { status: 404 }
      )
    }

    const analysis = calculateOverfittingAnalysis(backtest, forward)

    return NextResponse.json(analysis)
  } catch (error) {
    console.error('Error calculating overfitting analysis:', error)
    return NextResponse.json(
      { error: 'Failed to calculate overfitting analysis' },
      { status: 500 }
    )
  }
}
