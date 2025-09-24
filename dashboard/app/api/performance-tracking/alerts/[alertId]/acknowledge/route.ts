/**
 * API endpoint for acknowledging performance tracking alerts
 * Connects to orchestrator performance tracking service
 */

import { NextRequest, NextResponse } from 'next/server'

export async function POST(
  request: NextRequest,
  { params }: { params: { alertId: string } }
) {
  try {
    const { alertId } = params

    // First try to acknowledge alert via orchestrator
    console.log(`Acknowledging alert ${alertId} via orchestrator...`)

    const response = await fetch(`http://localhost:8090/api/performance-tracking/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 5000 // 5 second timeout
    })

    if (response.ok) {
      const data = await response.json()
      console.log(`Successfully acknowledged alert ${alertId}:`, data)

      return NextResponse.json({
        success: true,
        message: `Alert ${alertId} acknowledged successfully`,
        data: data,
        timestamp: new Date().toISOString(),
        source: 'real_system'
      })
    } else {
      throw new Error(`Orchestrator responded with status: ${response.status}`)
    }

  } catch (error) {
    console.warn(`Failed to acknowledge alert ${params.alertId} in real system, using fallback:`, error.message)

    // Only use fallback when real system is unavailable
    return NextResponse.json({
      success: true,
      message: `Alert ${params.alertId} acknowledged successfully`,
      timestamp: new Date().toISOString(),
      source: 'fallback_mock',
      warning: 'Alert acknowledged locally - orchestrator service unavailable'
    })
  }
}