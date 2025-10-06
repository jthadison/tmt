import { NextRequest, NextResponse } from 'next/server'
import {
  PerformanceAlert,
  AlertType,
  AlertSeverity,
  DegradationThresholds,
  DEFAULT_THRESHOLDS
} from '@/types/analytics'

// TODO: Replace in-memory storage with database (PostgreSQL/TimescaleDB)
const alertsStore: PerformanceAlert[] = []
const thresholdsStore: DegradationThresholds = { ...DEFAULT_THRESHOLDS }

// Mock data for recent metrics (in production, fetch from database)
interface MetricsSnapshot {
  profitFactor: number
  sharpeRatio: number
  winRate: number
  timestamp: number
}

// Simulated historical data
const metricsHistory: MetricsSnapshot[] = []

/**
 * Initialize with some historical data for testing
 */
function initializeHistoricalData() {
  if (metricsHistory.length === 0) {
    const now = Date.now()
    for (let i = 90; i >= 0; i--) {
      metricsHistory.push({
        profitFactor: 2.3 + Math.random() * 0.4 - 0.2,
        sharpeRatio: 1.5 + Math.random() * 0.3 - 0.15,
        winRate: 65 + Math.random() * 8 - 4,
        timestamp: now - i * 24 * 60 * 60 * 1000
      })
    }
  }
}

/**
 * Generate unique ID
 */
function generateId(): string {
  return `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Get current metrics (mock implementation)
 */
async function getCurrentMetrics(): Promise<MetricsSnapshot> {
  initializeHistoricalData()

  // For testing, return slightly degraded metrics to trigger some alerts
  return {
    profitFactor: 2.0, // Down from ~2.3
    sharpeRatio: 0.45, // Below threshold of 0.5
    winRate: 55, // Down from ~65
    timestamp: Date.now()
  }
}

/**
 * Get historical metrics average
 */
async function getHistoricalMetrics(days: number): Promise<MetricsSnapshot> {
  initializeHistoricalData()

  const cutoffTime = Date.now() - days * 24 * 60 * 60 * 1000
  const relevantMetrics = metricsHistory.filter(m => m.timestamp >= cutoffTime)

  const avg = relevantMetrics.reduce(
    (acc, m) => ({
      profitFactor: acc.profitFactor + m.profitFactor,
      sharpeRatio: acc.sharpeRatio + m.sharpeRatio,
      winRate: acc.winRate + m.winRate,
      timestamp: 0
    }),
    { profitFactor: 0, sharpeRatio: 0, winRate: 0, timestamp: 0 }
  )

  const count = relevantMetrics.length || 1
  return {
    profitFactor: avg.profitFactor / count,
    sharpeRatio: avg.sharpeRatio / count,
    winRate: avg.winRate / count,
    timestamp: Date.now()
  }
}

/**
 * Get Sharpe ratio for specific window
 */
async function getSharpeRatio(days: number): Promise<number> {
  const metrics = await getHistoricalMetrics(days)
  return metrics.sharpeRatio
}

/**
 * Get win rate for specific window
 */
async function getWinRate(days: number): Promise<number> {
  const metrics = await getHistoricalMetrics(days)
  return metrics.winRate
}

/**
 * Get overfitting score (mock from Story 8.2)
 */
async function getOverfittingScore(): Promise<number> {
  // Mock implementation - in production, fetch from analytics service
  return 0.65 // Below critical threshold for testing
}

/**
 * Get walk-forward score (mock from Story 8.2)
 */
async function getWalkForwardScore(): Promise<number> {
  // Mock implementation - in production, fetch from analytics service
  return 45 // Above threshold for testing
}

/**
 * Check if Sharpe has been below threshold for N consecutive days
 */
async function checkSharpeBreachDuration(): Promise<boolean> {
  initializeHistoricalData()

  const threshold = thresholdsStore.sharpeThreshold
  const daysRequired = thresholdsStore.sharpeDaysBelow

  // Check last N days
  const recentDays = metricsHistory.slice(-daysRequired)

  return recentDays.every(m => m.sharpeRatio < threshold)
}

/**
 * Create alert object
 */
function createAlert(
  type: AlertType,
  severity: AlertSeverity,
  message: string,
  recommendation: string,
  currentValue: number,
  thresholdValue: number,
  autoRollback: boolean = false
): PerformanceAlert {
  return {
    id: generateId(),
    type,
    severity,
    timestamp: Date.now(),
    metric: type.replace(/_/g, ' '),
    currentValue,
    thresholdValue,
    message,
    recommendation,
    autoRollback,
    acknowledged: false
  }
}

/**
 * Check for performance degradation
 */
async function checkDegradation(): Promise<PerformanceAlert[]> {
  const alerts: PerformanceAlert[] = []

  const current = await getCurrentMetrics()
  const historical = await getHistoricalMetrics(30)

  // Check profit factor decline
  const profitDecline = ((historical.profitFactor - current.profitFactor) / historical.profitFactor) * 100

  if (profitDecline > thresholdsStore.profitFactorDecline) {
    alerts.push(
      createAlert(
        'profit_decline',
        'high',
        `Profit factor declined ${profitDecline.toFixed(1)}%`,
        'Review recent trades for pattern changes',
        current.profitFactor,
        historical.profitFactor
      )
    )
  }

  // Check Sharpe ratio breach
  if (await checkSharpeBreachDuration()) {
    alerts.push(
      createAlert(
        'confidence_breach',
        'high',
        `Sharpe ratio below threshold for ${thresholdsStore.sharpeDaysBelow}+ days`,
        'Consider reducing position sizes or pausing trading',
        current.sharpeRatio,
        thresholdsStore.sharpeThreshold,
        true // Enable auto-rollback
      )
    )
  }

  // Check overfitting
  const overfitting = await getOverfittingScore()
  if (overfitting > thresholdsStore.overfittingThreshold) {
    alerts.push(
      createAlert(
        'overfitting',
        'critical',
        'High overfitting detected',
        'Strategy may be overfit to historical data - consider rollback',
        overfitting,
        thresholdsStore.overfittingThreshold,
        true // Enable auto-rollback
      )
    )
  }

  // Check walk-forward stability
  const stability = await getWalkForwardScore()
  if (stability < thresholdsStore.walkForwardThreshold) {
    alerts.push(
      createAlert(
        'stability_loss',
        'medium',
        'Performance stability degraded',
        'Monitor closely for further decline',
        stability,
        thresholdsStore.walkForwardThreshold
      )
    )
  }

  // Check Sharpe ratio drop
  const sharpe7d = await getSharpeRatio(7)
  const sharpe30d = await getSharpeRatio(30)
  const sharpeDropPercent = Math.abs(((sharpe7d - sharpe30d) / sharpe30d) * 100)

  if (sharpe7d < sharpe30d && sharpeDropPercent > thresholdsStore.sharpeDropPercent) {
    alerts.push(
      createAlert(
        'sharpe_drop',
        'medium',
        `Sharpe ratio declined ${sharpeDropPercent.toFixed(1)}% in recent window`,
        'Risk-adjusted returns deteriorating',
        sharpe7d,
        sharpe30d
      )
    )
  }

  // Check win rate decline
  const currentWinRate = await getWinRate(7)
  const historicalWinRate = await getWinRate(90)
  const winRateDecline = Math.abs(((currentWinRate - historicalWinRate) / historicalWinRate) * 100)

  if (currentWinRate < historicalWinRate && winRateDecline > thresholdsStore.winRateDecline) {
    alerts.push(
      createAlert(
        'win_rate_decline',
        'high',
        `Win rate declined ${winRateDecline.toFixed(1)}% from average`,
        'Review entry criteria and signal quality',
        currentWinRate,
        historicalWinRate
      )
    )
  }

  return alerts
}

/**
 * GET /api/analytics/degradation-alerts
 * Returns active (unacknowledged) alerts
 */
export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url)
    const refresh = url.searchParams.get('refresh') === 'true'

    // If refresh requested, check for new alerts
    if (refresh) {
      const newAlerts = await checkDegradation()

      // Add new alerts to store (avoid duplicates by type)
      newAlerts.forEach(newAlert => {
        const exists = alertsStore.find(
          a => a.type === newAlert.type && !a.acknowledged
        )
        if (!exists) {
          alertsStore.push(newAlert)
        }
      })
    }

    // Return only unacknowledged alerts
    const activeAlerts = alertsStore.filter(a => !a.acknowledged)

    return NextResponse.json(activeAlerts)
  } catch (error) {
    console.error('Error fetching degradation alerts:', error)
    return NextResponse.json(
      { error: 'Failed to fetch alerts' },
      { status: 500 }
    )
  }
}

/**
 * POST /api/analytics/degradation-alerts
 * Manually trigger degradation check
 */
export async function POST(_request: NextRequest) {
  try {
    const newAlerts = await checkDegradation()

    // Add to store
    newAlerts.forEach(newAlert => {
      alertsStore.push(newAlert)
    })

    return NextResponse.json({
      alertsGenerated: newAlerts.length,
      alerts: newAlerts
    })
  } catch (error) {
    console.error('Error checking degradation:', error)
    return NextResponse.json(
      { error: 'Failed to check degradation' },
      { status: 500 }
    )
  }
}
