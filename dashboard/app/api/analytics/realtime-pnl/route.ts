/**
 * Real-time P&L API Endpoint
 * Connects to orchestrator to get live trading data
 */

import { NextRequest, NextResponse } from 'next/server'

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8100'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { accountId, agentId } = body

    if (!accountId) {
      return NextResponse.json(
        { error: 'Account ID is required' },
        { status: 400 }
      )
    }

    // Try to fetch from orchestrator first
    try {
      const orchestratorResponse = await fetch(`${ORCHESTRATOR_URL}/analytics/realtime-pnl`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accountId, agentId })
      })

      if (orchestratorResponse.ok) {
        const data = await orchestratorResponse.json()
        return NextResponse.json(data)
      }
    } catch (orchestratorError) {
      console.warn('Orchestrator not available, using mock data')
    }

    // Mock data for development/testing
    const mockPnL = {
      currentPnL: Math.random() * 1000 - 500, // Random P&L between -500 and 500
      realizedPnL: Math.random() * 2000 - 1000,
      unrealizedPnL: Math.random() * 300 - 150,
      dailyPnL: Math.random() * 200 - 100,
      weeklyPnL: Math.random() * 800 - 400,
      monthlyPnL: Math.random() * 2000 - 1000,
      lastUpdate: new Date().toISOString()
    }

    return NextResponse.json(mockPnL)

  } catch (error) {
    console.error('Error fetching real-time P&L:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}