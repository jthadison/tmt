import { NextRequest, NextResponse } from 'next/server'
import { PerformanceAlert, AlertSeverity, AlertType } from '@/types/analytics'

/**
 * Generate mock historical alerts for testing
 */
function generateMockHistory(): PerformanceAlert[] {
  const now = Date.now()
  const history: PerformanceAlert[] = []

  const alertTypes: { type: AlertType; severity: AlertSeverity; message: string }[] = [
    {
      type: 'profit_decline',
      severity: 'high',
      message: 'Profit factor declined 12.3%'
    },
    {
      type: 'win_rate_decline',
      severity: 'high',
      message: 'Win rate declined 18.5% from average'
    },
    {
      type: 'sharpe_drop',
      severity: 'medium',
      message: 'Sharpe ratio declined 22.1% in recent window'
    },
    {
      type: 'stability_loss',
      severity: 'medium',
      message: 'Performance stability degraded'
    },
    {
      type: 'overfitting',
      severity: 'critical',
      message: 'High overfitting detected'
    },
    {
      type: 'confidence_breach',
      severity: 'high',
      message: 'Sharpe ratio below threshold for 2+ days'
    }
  ]

  // Generate alerts for last 30 days
  for (let i = 0; i < 20; i++) {
    const daysAgo = Math.floor(Math.random() * 30)
    const alertTemplate = alertTypes[Math.floor(Math.random() * alertTypes.length)]

    history.push({
      id: `alert_history_${i}`,
      type: alertTemplate.type,
      severity: alertTemplate.severity,
      timestamp: now - daysAgo * 24 * 60 * 60 * 1000,
      metric: alertTemplate.type.replace(/_/g, ' '),
      currentValue: Math.random() * 100,
      thresholdValue: Math.random() * 100,
      message: alertTemplate.message,
      recommendation: 'Historical alert - resolved',
      autoRollback: alertTemplate.severity === 'critical',
      acknowledged: true,
      acknowledgedAt: now - (daysAgo - 1) * 24 * 60 * 60 * 1000,
      resolvedAt: now - (daysAgo - 1) * 24 * 60 * 60 * 1000
    })
  }

  return history.sort((a, b) => b.timestamp - a.timestamp)
}

/**
 * GET /api/analytics/degradation-alerts/history
 * Get historical alerts with filtering
 */
export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url)
    const dateRange = url.searchParams.get('dateRange') || '30d'
    const severity = url.searchParams.get('severity') || 'all'
    const type = url.searchParams.get('type') || 'all'

    let history = generateMockHistory()

    // Filter by date range
    const now = Date.now()
    let cutoffTime = 0

    switch (dateRange) {
      case '7d':
        cutoffTime = now - 7 * 24 * 60 * 60 * 1000
        break
      case '30d':
        cutoffTime = now - 30 * 24 * 60 * 60 * 1000
        break
      case '90d':
        cutoffTime = now - 90 * 24 * 60 * 60 * 1000
        break
      case 'all':
      default:
        cutoffTime = 0
        break
    }

    if (cutoffTime > 0) {
      history = history.filter(alert => alert.timestamp >= cutoffTime)
    }

    // Filter by severity
    if (severity !== 'all') {
      history = history.filter(alert => alert.severity === severity)
    }

    // Filter by type
    if (type !== 'all') {
      history = history.filter(alert => alert.type === type)
    }

    return NextResponse.json(history)
  } catch (error) {
    console.error('Error fetching alert history:', error)
    return NextResponse.json(
      { error: 'Failed to fetch alert history' },
      { status: 500 }
    )
  }
}
