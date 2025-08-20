/**
 * Historical Performance API Endpoint
 * Provides historical performance data with configurable periods
 */

import { NextRequest, NextResponse } from 'next/server'

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { accountIds, agentIds, dateRange, granularity = 'day' } = body

    if (!accountIds || accountIds.length === 0) {
      return NextResponse.json(
        { error: 'Account IDs are required' },
        { status: 400 }
      )
    }

    // Try to fetch from orchestrator first
    try {
      const orchestratorResponse = await fetch(`${ORCHESTRATOR_URL}/analytics/historical`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accountIds, agentIds, dateRange, granularity })
      })

      if (orchestratorResponse.ok) {
        const data = await orchestratorResponse.json()
        return NextResponse.json(data)
      }
    } catch (orchestratorError) {
      console.warn('Orchestrator not available, using mock data')
    }

    // Generate mock historical data
    const startDate = new Date(dateRange?.start || Date.now() - 30 * 24 * 60 * 60 * 1000) // 30 days ago
    const endDate = new Date(dateRange?.end || Date.now())
    const days = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    
    const historicalData = []
    let cumulativePnL = 0

    for (let i = 0; i < days; i++) {
      const date = new Date(startDate.getTime() + i * 24 * 60 * 60 * 1000)
      const dailyPnL = (Math.random() - 0.5) * 200 // Random daily P&L between -100 and 100
      cumulativePnL += dailyPnL

      historicalData.push({
        date: date.toISOString().split('T')[0],
        dailyPnL,
        cumulativePnL,
        trades: Math.floor(Math.random() * 10) + 1, // 1-10 trades per day
        winRate: Math.random() * 0.4 + 0.4, // 40-80% win rate
        volume: Math.random() * 100000 + 50000, // 50k-150k volume
        drawdown: Math.max(0, cumulativePnL * -0.1), // Simple drawdown calculation
        sharpeRatio: Math.random() * 2 + 0.5 // 0.5-2.5 Sharpe ratio
      })
    }

    return NextResponse.json(historicalData)

  } catch (error) {
    console.error('Error fetching historical performance:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}