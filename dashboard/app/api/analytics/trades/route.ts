/**
 * Trade Breakdown API Endpoint
 * Provides detailed trade-by-trade analysis
 */

import { NextRequest, NextResponse } from 'next/server'

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { accountId, agentId, dateRange } = body

    if (!accountId) {
      return NextResponse.json(
        { error: 'Account ID is required' },
        { status: 400 }
      )
    }

    // Try to fetch from orchestrator first
    try {
      const orchestratorResponse = await fetch(`${ORCHESTRATOR_URL}/analytics/trades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accountId, agentId, dateRange })
      })

      if (orchestratorResponse.ok) {
        const data = await orchestratorResponse.json()
        return NextResponse.json(data)
      }
    } catch (orchestratorError) {
      console.warn('Orchestrator not available, using mock data')
    }

    // Mock trade data for development
    const mockTrades = [
      {
        id: 'trade_001',
        accountId,
        agentId: agentId || 'market-analysis',
        agentName: 'Market Analysis Agent',
        symbol: 'EUR_USD',
        direction: 'buy',
        openTime: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        closeTime: new Date(Date.now() - 1 * 60 * 60 * 1000), // 1 hour ago
        openPrice: 1.0850,
        closePrice: 1.0875,
        size: 10000,
        commission: 2.5,
        swap: 0.5,
        profit: 25.0,
        status: 'closed',
        stopLoss: 1.0800,
        takeProfit: 1.0900,
        strategy: 'wyckoff_accumulation'
      },
      {
        id: 'trade_002',
        accountId,
        agentId: agentId || 'strategy-analysis',
        agentName: 'Strategy Analysis Agent',
        symbol: 'GBP_USD',
        direction: 'sell',
        openTime: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
        closeTime: new Date(Date.now() - 3 * 60 * 60 * 1000), // 3 hours ago
        openPrice: 1.2650,
        closePrice: 1.2625,
        size: 8000,
        commission: 2.0,
        swap: -0.3,
        profit: 20.0,
        status: 'closed',
        stopLoss: 1.2700,
        takeProfit: 1.2600,
        strategy: 'smart_money_concepts'
      },
      {
        id: 'trade_003',
        accountId,
        agentId: agentId || 'pattern-detection',
        agentName: 'Pattern Detection Agent',
        symbol: 'USD_JPY',
        direction: 'buy',
        openTime: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
        closeTime: null,
        openPrice: 150.25,
        closePrice: null,
        size: 5000,
        commission: 1.5,
        swap: 0,
        profit: null,
        status: 'open',
        stopLoss: 149.80,
        takeProfit: 151.00,
        strategy: 'volume_price_analysis'
      }
    ]

    return NextResponse.json(mockTrades)

  } catch (error) {
    console.error('Error fetching trades:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}