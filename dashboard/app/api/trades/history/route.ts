/**
 * Trade History API Endpoint
 * Provides comprehensive trade history with filtering, sorting, and pagination
 */

import { NextRequest, NextResponse } from 'next/server'

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8086'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    
    // Extract query parameters
    const accountId = searchParams.get('accountId') || 'all-accounts'
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('limit') || '50')
    const sortBy = searchParams.get('sortBy') || 'openTime'
    const sortOrder = searchParams.get('sortOrder') || 'desc'
    
    // Extract filter parameters
    const filter: any = {}
    const instrument = searchParams.get('instrument')
    const status = searchParams.get('status')
    const type = searchParams.get('type')
    const minProfit = searchParams.get('minProfit')
    const maxProfit = searchParams.get('maxProfit')
    const dateFrom = searchParams.get('dateFrom')
    const dateTo = searchParams.get('dateTo')
    
    if (instrument) filter.instrument = instrument
    if (status) filter.status = status
    if (type) filter.type = type
    if (minProfit !== null) filter.minProfit = parseFloat(minProfit || '0')
    if (maxProfit !== null) filter.maxProfit = parseFloat(maxProfit || '0')
    
    // Build request payload for orchestrator
    const requestPayload = {
      accountId,
      page,
      limit,
      sortBy,
      sortOrder,
      filter,
      dateRange: (dateFrom && dateTo) ? { start: dateFrom, end: dateTo } : undefined
    }

    // Try to fetch from orchestrator first
    try {
      const orchestratorResponse = await fetch(`${ORCHESTRATOR_URL}/analytics/trade-history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload)
      })

      if (orchestratorResponse.ok) {
        const data = await orchestratorResponse.json()
        
        // Transform data to match our frontend interface
        const transformedData = {
          trades: data.trades.map((trade: any) => ({
            id: trade.id,
            accountId: trade.accountId,
            accountName: `Account ${trade.accountId}`,
            instrument: trade.symbol,
            type: 'market', // Most trades are market orders
            side: trade.direction,
            units: trade.size,
            price: trade.openPrice,
            stopLoss: trade.stopLoss || null,
            takeProfit: trade.takeProfit || null,
            openTime: new Date(trade.openTime),
            closeTime: trade.closeTime ? new Date(trade.closeTime) : null,
            status: trade.status,
            pnl: trade.profit,
            commission: trade.commission,
            swap: trade.swap,
            tags: [trade.strategy, trade.agentId]
          })),
          stats: data.stats,
          pagination: data.pagination
        }
        
        return NextResponse.json(transformedData)
      }
    } catch (orchestratorError) {
      console.warn('Orchestrator not available for trade history, using mock data:', orchestratorError)
    }

    // Fallback to mock data if orchestrator is unavailable
    console.log('Using mock data for trade history')
    
    // Generate comprehensive mock trade history
    const mockTrades = []
    const symbols = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'GBP/JPY', 'EUR/JPY']
    const strategies = ['wyckoff_accumulation', 'smart_money_concepts', 'volume_price_analysis', 'breakout', 'reversal', 'scalping']
    
    for (let i = 0; i < 100; i++) {
      const daysAgo = Math.floor(i / 3) // ~3 trades per day
      const hoursOffset = i % 24
      const openTime = new Date(Date.now() - (daysAgo * 24 * 60 * 60 * 1000) - (hoursOffset * 60 * 60 * 1000))
      const closeTime = new Date(openTime.getTime() + (1.5 * 60 * 60 * 1000)) // 1.5h average trade duration
      
      const symbol = symbols[i % symbols.length]
      const strategy = strategies[i % strategies.length]
      const side = i % 2 === 0 ? 'buy' : 'sell'
      
      // Realistic win rate ~65%
      const isWin = (i % 20) < 13
      const basePnl = 30 + (i % 150) // $30-180 base
      const pnl = isWin ? basePnl : -basePnl * 0.6 // 1.67 R:R ratio
      
      const trade = {
        id: `mock_${i + 1}`,
        accountId: accountId === 'all-accounts' ? `account-${(i % 3) + 1}` : accountId,
        accountName: `Demo Account ${(i % 3) + 1}`,
        instrument: symbol,
        type: 'market',
        side: side,
        units: 10000 + (i % 5) * 5000, // 10k-35k units
        price: 1.0800 + (i % 500) / 10000, // Realistic price range
        stopLoss: side === 'buy' ? 1.0750 : 1.0850,
        takeProfit: side === 'buy' ? 1.0900 : 1.0700,
        openTime,
        closeTime,
        status: 'closed',
        pnl: Math.round(pnl * 100) / 100,
        commission: 2.5,
        swap: i % 4 === 0 ? 0 : Math.round((-0.5 + Math.random()) * 100) / 100,
        tags: [strategy, `agent-${(i % 3) + 1}`]
      }
      
      mockTrades.push(trade)
    }
    
    // Apply filters
    let filteredTrades = mockTrades
    
    if (filter.instrument) {
      filteredTrades = filteredTrades.filter(t => t.instrument === filter.instrument)
    }
    
    if (filter.status) {
      filteredTrades = filteredTrades.filter(t => t.status === filter.status)
    }
    
    if (filter.type) {
      if (filter.type === 'long') {
        filteredTrades = filteredTrades.filter(t => t.side === 'buy')
      } else if (filter.type === 'short') {
        filteredTrades = filteredTrades.filter(t => t.side === 'sell')
      }
    }
    
    if (filter.minProfit !== undefined) {
      filteredTrades = filteredTrades.filter(t => t.pnl >= filter.minProfit)
    }
    
    if (filter.maxProfit !== undefined) {
      filteredTrades = filteredTrades.filter(t => t.pnl <= filter.maxProfit)
    }
    
    // Apply sorting
    filteredTrades.sort((a: any, b: any) => {
      let aVal = a[sortBy]
      let bVal = b[sortBy]
      
      // Handle date sorting
      if (sortBy === 'openTime' || sortBy === 'closeTime') {
        aVal = new Date(aVal).getTime()
        bVal = new Date(bVal).getTime()
      }
      
      if (sortOrder === 'desc') {
        return bVal - aVal
      } else {
        return aVal - bVal
      }
    })
    
    // Calculate statistics
    const closedTrades = filteredTrades.filter(t => t.status === 'closed')
    const winningTrades = closedTrades.filter(t => t.pnl > 0)
    const losingTrades = closedTrades.filter(t => t.pnl < 0)
    
    const totalPnL = closedTrades.reduce((sum, t) => sum + t.pnl, 0)
    const totalCommission = filteredTrades.reduce((sum, t) => sum + t.commission, 0)
    const totalSwap = filteredTrades.reduce((sum, t) => sum + t.swap, 0)
    
    const grossProfit = winningTrades.reduce((sum, t) => sum + t.pnl, 0)
    const grossLoss = Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0))
    
    const stats = {
      totalTrades: filteredTrades.length,
      closedTrades: closedTrades.length,
      openTrades: filteredTrades.filter(t => t.status === 'open').length,
      winningTrades: winningTrades.length,
      losingTrades: losingTrades.length,
      totalPnL: Math.round(totalPnL * 100) / 100,
      winRate: closedTrades.length > 0 ? (winningTrades.length / closedTrades.length) * 100 : 0,
      averageWin: winningTrades.length > 0 ? grossProfit / winningTrades.length : 0,
      averageLoss: losingTrades.length > 0 ? grossLoss / losingTrades.length : 0,
      profitFactor: grossLoss > 0 ? grossProfit / grossLoss : (grossProfit > 0 ? 999 : 0),
      maxDrawdown: 0, // Would need running calculation
      totalCommission: Math.round(totalCommission * 100) / 100,
      totalSwap: Math.round(totalSwap * 100) / 100
    }
    
    // Apply pagination
    const startIndex = (page - 1) * limit
    const paginatedTrades = filteredTrades.slice(startIndex, startIndex + limit)
    
    const response = {
      trades: paginatedTrades,
      stats,
      pagination: {
        total: filteredTrades.length,
        page,
        limit,
        totalPages: Math.ceil(filteredTrades.length / limit)
      }
    }
    
    return NextResponse.json(response)

  } catch (error) {
    console.error('Error fetching trade history:', error)
    return NextResponse.json(
      { error: 'Internal server error', details: error },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // For POST requests, parameters come in the body
    const {
      accountId = 'all-accounts',
      page = 1,
      limit = 50,
      sortBy = 'openTime',
      sortOrder = 'desc',
      filter = {}
    } = body

    // Build query string and redirect to GET
    const params = new URLSearchParams({
      accountId,
      page: page.toString(),
      limit: limit.toString(),
      sortBy,
      sortOrder,
      ...(filter.instrument && { instrument: filter.instrument }),
      ...(filter.status && { status: filter.status }),
      ...(filter.type && { type: filter.type }),
      ...(filter.minProfit !== undefined && { minProfit: filter.minProfit.toString() }),
      ...(filter.maxProfit !== undefined && { maxProfit: filter.maxProfit.toString() })
    })

    // Create a new request URL with parameters
    const url = new URL(request.url)
    url.search = params.toString()
    
    // Create new request object for GET handler
    const getRequest = new NextRequest(url)
    return GET(getRequest)

  } catch (error) {
    console.error('Error in POST trade history:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}