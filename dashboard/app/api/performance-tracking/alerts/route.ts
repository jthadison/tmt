/**
 * API endpoint for performance tracking alerts
 * Connects to orchestrator performance tracking service
 */

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    // First try to get real alerts from orchestrator
    console.log('Fetching real performance alerts from orchestrator...')

    const response = await fetch('http://localhost:8090/api/performance-tracking/alerts', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 5000 // 5 second timeout
    })

    if (response.ok) {
      const data = await response.json()
      console.log('Successfully received real alerts data:', data)

      // Transform real alerts data for frontend
      const alerts = data.alerts?.map((alert: any, index: number) => ({
        id: alert.id || `alert-${index}`,
        severity: alert.severity || 'INFO',
        type: alert.type || 'Performance Alert',
        message: alert.message || 'Performance tracking alert',
        timestamp: new Date(alert.timestamp || Date.now()),
        acknowledged: alert.acknowledged || false
      })) || []

      return NextResponse.json({
        success: true,
        data: alerts,
        timestamp: new Date().toISOString(),
        source: 'real_data'
      })
    } else {
      throw new Error(`Orchestrator responded with status: ${response.status}`)
    }

  } catch (error) {
    console.warn('Failed to fetch real alerts data, using fallback:', error.message)

    // Only use mock data as fallback when real system is unavailable
    const mockAlerts = [
      {
        id: 'alert-1',
        severity: 'WARNING',
        type: 'Confidence Interval Breach',
        message: 'Performance has exceeded 95% confidence interval for 2 consecutive days',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        acknowledged: false
      },
      {
        id: 'alert-2',
        severity: 'INFO',
        type: 'Sharpe Ratio Update',
        message: '30-day rolling Sharpe ratio improved to 1.42',
        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
        acknowledged: false
      },
      {
        id: 'alert-3',
        severity: 'CRITICAL',
        type: 'Performance Deviation',
        message: 'Actual P&L deviating significantly from Monte Carlo projections (-15.2%)',
        timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000), // 6 hours ago
        acknowledged: false
      }
    ]

    return NextResponse.json({
      success: true,
      data: mockAlerts,
      timestamp: new Date().toISOString(),
      source: 'fallback_mock',
      warning: 'Using mock data - orchestrator service unavailable'
    })
  }
}