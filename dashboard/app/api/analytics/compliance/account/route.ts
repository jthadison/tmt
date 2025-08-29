/**
 * Account Compliance API Endpoint
 * Provides compliance data for individual accounts
 */

import { NextRequest, NextResponse } from 'next/server'

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8083'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { accountId, dateRange } = body

    if (!accountId) {
      return NextResponse.json(
        { error: 'Account ID is required' },
        { status: 400 }
      )
    }

    // Try to fetch from orchestrator first
    try {
      const orchestratorResponse = await fetch(`${ORCHESTRATOR_URL}/analytics/compliance/account`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accountId, dateRange })
      })

      if (orchestratorResponse.ok) {
        const data = await orchestratorResponse.json()
        return NextResponse.json(data)
      }
    } catch (orchestratorError) {
      console.warn('Orchestrator not available, using mock data')
    }

    // Mock account compliance data
    const startBalance = 100000
    const currentBalance = startBalance + (Math.random() * 10000 - 5000) // ±5k variation
    const totalReturn = ((currentBalance - startBalance) / startBalance) * 100

    const accountCompliance = {
      accountId,
      propFirm: 'FTMO',
      accountType: 'Challenge',
      startBalance,
      endBalance: currentBalance,
      totalReturn,
      maxDrawdown: Math.abs(Math.min(0, currentBalance - startBalance) * 1.2), // Mock max drawdown
      dailyLossLimit: 5000, // 5% daily loss limit
      maxDailyLossReached: Math.max(0, Math.random() * 2000), // Random daily loss up to 2k
      totalLossLimit: 10000, // 10% total loss limit  
      maxTotalLossReached: Math.max(0, startBalance - currentBalance),
      profitTarget: 10000, // 10% profit target
      profitAchieved: Math.max(0, currentBalance - startBalance),
      rulesViolated: Math.random() > 0.8 ? ['daily_loss_limit'] : [], // 20% chance of violation
      tradingDays: Math.floor(Math.random() * 30) + 15, // 15-45 trading days
      averageDailyVolume: Math.random() * 500000 + 100000 // 100k-600k daily volume
    }

    return NextResponse.json(accountCompliance)

  } catch (error) {
    console.error('Error fetching account compliance:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}