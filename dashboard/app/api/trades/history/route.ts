/**
 * Trade History API Endpoint
 * Direct OANDA integration for comprehensive trade history
 */

import { NextRequest, NextResponse } from 'next/server'
import { getOandaClient } from '@/lib/oanda-client'

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8089'
const EXECUTION_ENGINE_URL = process.env.EXECUTION_ENGINE_URL || 'http://localhost:8082'

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
    const filter: Record<string, any> = {}
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

    // Try orchestrator first, but always fetch open trades from OANDA
    const skipOrchestrator = false;
    const preferOandaForOpenTrades = true;
    
    // Try to fetch real trade data from orchestrator first
    if (!skipOrchestrator) {
      try {
      console.log(`Fetching real trade history from orchestrator: ${ORCHESTRATOR_URL}/trades`)
      
      const orchestratorResponse = await fetch(`${ORCHESTRATOR_URL}/trades`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      
      if (!orchestratorResponse.ok) {
        throw new Error(`Orchestrator responded with ${orchestratorResponse.status}: ${orchestratorResponse.statusText}`)
      }
      
      const orchestratorTrades = await orchestratorResponse.json()
      console.log(`Successfully fetched ${orchestratorTrades.length || 0} real trades from orchestrator`)
      
      // Transform orchestrator trades to dashboard format
      const transformedTrades = orchestratorTrades.map((trade: any) => {
        const orderData = trade.result?.details?.order_data
        const metadata = orderData?.metadata || {}
        const oandaResponse = trade.result?.details?.oanda_response
        
        // Extract real pattern and confidence data
        const pattern = metadata.pattern_type || 'unknown'
        const confidence = metadata.confidence || 0
        
        // Extract execution details
        const fillTransaction = oandaResponse?.orderFillTransaction
        const side = orderData?.side || 'unknown'
        const instrument = (orderData?.instrument || trade.symbol || '').replace('_', '/')
        const units = Math.abs(parseFloat(orderData?.units || '0'))
        const fillPrice = parseFloat(fillTransaction?.price || orderData?.fill_price || '0')
        const pnl = parseFloat(fillTransaction?.pl || trade.result?.details?.pl || '0')
        const status = trade.result?.details?.status === 'filled' ? 'closed' : 'open'
        
        // Parse timestamp
        const timestamp = trade.timestamp ? new Date(trade.timestamp) : new Date()
        
        return {
          id: trade.signal_id || `trade_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          accountId: orderData?.account_id || accountId,
          accountName: 'OANDA Practice Account',
          instrument,
          symbol: instrument,
          type: 'market',
          side,
          units,
          size: units,
          price: fillPrice,
          entryPrice: fillPrice,
          exitPrice: status === 'closed' ? fillPrice : null,
          stopLoss: parseFloat(orderData?.stop_loss_price || '0') || null,
          takeProfit: parseFloat(orderData?.take_profit_price || '0') || null,
          openTime: timestamp,
          closeTime: status === 'closed' ? timestamp : null,
          status,
          pnl,
          commission: parseFloat(fillTransaction?.commission || '0'),
          swap: parseFloat(fillTransaction?.financing || '0'),
          tags: ['orchestrator-real', `agent-${metadata.agent_id || 'unknown'}`],
          strategy: 'ai-trading',
          pattern, // Real pattern from metadata
          confidence, // Real confidence from metadata
          agentName: metadata.agent_id || 'Market Analysis Agent'
        }
      })
      
      // Apply filters
      let filteredTrades = transformedTrades
      
      // If we want open trades, fetch them directly from OANDA instead
      if (status === 'open' && preferOandaForOpenTrades) {
        console.log('Status is open, skipping orchestrator trades and fetching from OANDA')
        throw new Error('Fetch open trades from OANDA')  // Force fallback to OANDA
      }
      
      if (status) filteredTrades = filteredTrades.filter((t: any) => t.status === status)
      if (instrument) filteredTrades = filteredTrades.filter((t: any) => t.instrument === instrument)
      
      // Sort trades
      filteredTrades.sort((a: any, b: any) => {
        const aValue = a[sortBy as keyof typeof a] || 0
        const bValue = b[sortBy as keyof typeof b] || 0
        
        if (sortOrder === 'asc') {
          return aValue > bValue ? 1 : -1
        } else {
          return aValue < bValue ? 1 : -1
        }
      })

      // Calculate pagination
      const total = filteredTrades.length
      const totalPages = Math.ceil(total / limit)
      const startIndex = (page - 1) * limit
      const paginatedTrades = filteredTrades.slice(startIndex, startIndex + limit)

      // Calculate statistics
      const closedTradesOnly = filteredTrades.filter((t: any) => t.status === 'closed')
      const openTradesOnly = filteredTrades.filter((t: any) => t.status === 'open')
      const winningTrades = closedTradesOnly.filter((t: any) => t.pnl > 0)
      const losingTrades = closedTradesOnly.filter((t: any) => t.pnl < 0)
      
      const totalPnL = closedTradesOnly.reduce((sum: number, t: any) => sum + t.pnl, 0)
      const totalSwap = filteredTrades.reduce((sum: number, t: any) => sum + t.swap, 0)
      
      const stats = {
        totalTrades: total,
        closedTrades: closedTradesOnly.length,
        openTrades: openTradesOnly.length,
        winningTrades: winningTrades.length,
        losingTrades: losingTrades.length,
        totalPnL: Math.round(totalPnL * 100) / 100,
        winRate: closedTradesOnly.length > 0 ? Math.round((winningTrades.length / closedTradesOnly.length) * 100 * 100) / 100 : 0,
        averageWin: winningTrades.length > 0 ? Math.round((winningTrades.reduce((sum: number, t: any) => sum + t.pnl, 0) / winningTrades.length) * 100) / 100 : 0,
        averageLoss: losingTrades.length > 0 ? Math.round((losingTrades.reduce((sum: number, t: any) => sum + t.pnl, 0) / losingTrades.length) * 100) / 100 : 0,
        profitFactor: losingTrades.length > 0 ? Math.abs(winningTrades.reduce((sum: number, t: any) => sum + t.pnl, 0) / losingTrades.reduce((sum: number, t: any) => sum + t.pnl, 0)) : 0,
        maxDrawdown: Math.abs(Math.min(...closedTradesOnly.map((t: any) => t.pnl), 0)),
        totalCommission: filteredTrades.reduce((sum: number, t: any) => sum + t.commission, 0),
        totalSwap: Math.round(totalSwap * 100) / 100
      }

      return NextResponse.json({
        trades: paginatedTrades,
        stats,
        pagination: {
          total,
          page,
          limit,
          totalPages
        },
        source: 'orchestrator-real',
        message: `Showing ${paginatedTrades.length} real trades from orchestrator (${closedTradesOnly.length} closed, ${openTradesOnly.length} open)`
      })

      } catch (orchestratorError) {
        console.warn('Orchestrator not available, trying OANDA direct API:', orchestratorError)
      }
    } // end of if (!skipOrchestrator)

    // Try to fetch real closed and open trades from OANDA as fallback
    try {
      console.log('Fetching closed and open trades directly from OANDA API as fallback')
      const oandaClient = getOandaClient()
      
      // Get both closed and open trades from OANDA, plus transaction-based history and pending orders
      const [closedTrades, openTrades, transactionTrades, pendingOrders] = await Promise.all([
        oandaClient.getClosedTrades(500), // Get up to 500 closed trades
        oandaClient.getOpenTrades(), // Get current open positions
        oandaClient.getTradeHistoryFromTransactions(500), // Get transaction-based history with timestamps
        oandaClient.getPendingOrders() // Get pending orders
      ])
      
      console.log(`OANDA API returned ${closedTrades.length} closed trades, ${openTrades.length} open trades, ${transactionTrades.length} transaction-based trades, and ${pendingOrders.length} pending orders`)
      
      // Create a map of transaction-based trades for timestamp lookup
      const transactionTradeMap = new Map<string, any>()
      transactionTrades.forEach(trade => {
        transactionTradeMap.set(trade.id, trade)
      })
      
      // Transform closed trades (mark them as closed)
      const transformedClosedTrades = closedTrades.map((trade: any) => {
        // Helper function to safely parse dates
        const safeParseDate = (dateStr: any): Date | null => {
          if (!dateStr) return null
          
          // Handle Unix timestamp (seconds since epoch) - OANDA format
          if (typeof dateStr === 'string' && /^\d+\.\d+$/.test(dateStr)) {
            const timestamp = parseFloat(dateStr) * 1000 // Convert to milliseconds
            const date = new Date(timestamp)
            return isNaN(date.getTime()) ? null : date
          }
          
          // Handle regular date strings
          const date = new Date(dateStr)
          return isNaN(date.getTime()) ? null : date
        }
        
        // Try to get timestamps from transaction data if regular trade data is missing
        const transactionTrade = transactionTradeMap.get(trade.id)
        const openTime = safeParseDate(trade.openTime) || safeParseDate(transactionTrade?.openTime)
        const closeTime = safeParseDate(trade.closeTime) || safeParseDate(transactionTrade?.closeTime)
        
        // Determine side from units - for closed trades, use initial units since current may be 0
        const rawUnits = parseFloat(trade.initialUnits || trade.currentUnits || '0')
        const side = rawUnits > 0 ? 'buy' : 'sell'
        const absoluteUnits = Math.abs(rawUnits)
        
        // Debug logging for first few trades (keeping minimal for production)
        if (closedTrades.indexOf(trade) < 1) {
          console.log(`OANDA Closed Trade ${trade.id}: units=${rawUnits}, side=${side}, pnl=${trade.realizedPL}`)
        }

        return {
          id: trade.id,
          accountId: accountId === 'all-accounts' ? 'oanda-practice' : accountId,
          accountName: 'OANDA Practice Account',
          instrument: trade.instrument.replace('_', '/'), // Convert EUR_USD to EUR/USD
          symbol: trade.instrument.replace('_', '/'),
          type: 'market',
          side,
          units: absoluteUnits,
          size: absoluteUnits,
          price: parseFloat(trade.price || trade.averageClosePrice || '0'),
          entryPrice: parseFloat(trade.price || trade.averageClosePrice || '0'),
          exitPrice: parseFloat(trade.averageClosePrice || trade.price || '0'),
          stopLoss: trade.stopLossOrder?.price ? parseFloat(trade.stopLossOrder.price) : null,
          takeProfit: trade.takeProfitOrder?.price ? parseFloat(trade.takeProfitOrder.price) : null,
          openTime,
          closeTime,
          status: 'closed', // These came from getClosedTrades()
          pnl: parseFloat(trade.realizedPL || '0'), // OANDA provides realizedPL for closed trades
          commission: 0, // OANDA includes this in spread
          swap: parseFloat(trade.financing || '0'),
          tags: ['oanda-live', 'closed-trade'],
          strategy: 'live-trading',
          pattern: null, // No pattern data available from OANDA
          confidence: null, // No confidence data available from OANDA
          agentName: 'OANDA Live System'
        }
      })

      // Transform open trades (mark them as open)
      const transformedOpenTrades = openTrades.map((trade: any) => {
        // Helper function to safely parse dates
        const safeParseDate = (dateStr: any): Date | null => {
          if (!dateStr) return null
          
          // Handle Unix timestamp (seconds since epoch) - OANDA format
          if (typeof dateStr === 'string' && /^\d+\.\d+$/.test(dateStr)) {
            const timestamp = parseFloat(dateStr) * 1000 // Convert to milliseconds
            const date = new Date(timestamp)
            return isNaN(date.getTime()) ? null : date
          }
          
          // Handle regular date strings
          const date = new Date(dateStr)
          return isNaN(date.getTime()) ? null : date
        }
        
        const openTime = safeParseDate(trade.openTime)
        
        // Determine side from units - for open trades, use current units
        const rawUnits = parseFloat(trade.currentUnits || trade.initialUnits || '0')
        const side = rawUnits > 0 ? 'buy' : 'sell'
        const absoluteUnits = Math.abs(rawUnits)
        
        // Debug logging to see actual OANDA response structure
        if (openTrades.indexOf(trade) < 2) {
          console.log(`OANDA Open Trade ${trade.id} full data:`, JSON.stringify(trade, null, 2))
        }

        return {
          id: trade.id,
          accountId: accountId === 'all-accounts' ? 'oanda-practice' : accountId,
          accountName: 'OANDA Practice Account',
          instrument: trade.instrument.replace('_', '/'), // Convert EUR_USD to EUR/USD
          symbol: trade.instrument.replace('_', '/'),
          type: 'market',
          side,
          units: absoluteUnits,
          size: absoluteUnits,
          price: parseFloat(trade.price || trade.averageClosePrice || '0'),
          entryPrice: parseFloat(trade.price || trade.averageClosePrice || '0'),
          stopLoss: trade.stopLossOrder?.price ? parseFloat(trade.stopLossOrder.price) : null,
          takeProfit: trade.takeProfitOrder?.price ? parseFloat(trade.takeProfitOrder.price) : null,
          openTime,
          closeTime: null, // Open trades don't have close time
          status: 'open', // These came from getOpenTrades()
          pnl: parseFloat(trade.unrealizedPL || '0'), // OANDA provides unrealizedPL for open trades
          commission: 0, // OANDA includes this in spread
          swap: parseFloat(trade.financing || '0'),
          tags: ['oanda-live', 'open-position'],
          strategy: 'live-trading',
          pattern: null, // No pattern data available from OANDA
          confidence: null, // No confidence data available from OANDA
          agentName: 'OANDA Live System'
        }
      })

      // Combine all trades
      const allOandaTrades = [...transformedClosedTrades, ...transformedOpenTrades]

      // Apply filters
      let filteredTrades = allOandaTrades
      if (status) filteredTrades = filteredTrades.filter(t => t.status === status)
      if (instrument) filteredTrades = filteredTrades.filter(t => t.instrument === instrument)
      
      // Sort trades
      filteredTrades.sort((a: any, b: any) => {
        const aValue = a[sortBy as keyof typeof a] || 0
        const bValue = b[sortBy as keyof typeof b] || 0
        
        if (sortOrder === 'asc') {
          return aValue > bValue ? 1 : -1
        } else {
          return aValue < bValue ? 1 : -1
        }
      })

      // Calculate pagination
      const total = filteredTrades.length
      const totalPages = Math.ceil(total / limit)
      const startIndex = (page - 1) * limit
      const paginatedTrades = filteredTrades.slice(startIndex, startIndex + limit)

      // Calculate statistics
      const closedTradesOnly = filteredTrades.filter((t: any) => t.status === 'closed')
      const openTradesOnly = filteredTrades.filter((t: any) => t.status === 'open')
      const winningTrades = closedTradesOnly.filter((t: any) => t.pnl > 0)
      const losingTrades = closedTradesOnly.filter((t: any) => t.pnl < 0)
      
      const totalPnL = closedTradesOnly.reduce((sum: number, t: any) => sum + t.pnl, 0)
      const totalSwap = filteredTrades.reduce((sum: number, t: any) => sum + t.swap, 0)
      
      const stats = {
        totalTrades: total,
        closedTrades: closedTradesOnly.length,
        openTrades: openTradesOnly.length,
        pendingOrders: pendingOrders.length,
        winningTrades: winningTrades.length,
        losingTrades: losingTrades.length,
        totalPnL: Math.round(totalPnL * 100) / 100,
        winRate: closedTradesOnly.length > 0 ? Math.round((winningTrades.length / closedTradesOnly.length) * 100 * 100) / 100 : 0,
        averageWin: winningTrades.length > 0 ? Math.round((winningTrades.reduce((sum, t) => sum + t.pnl, 0) / winningTrades.length) * 100) / 100 : 0,
        averageLoss: losingTrades.length > 0 ? Math.round((losingTrades.reduce((sum, t) => sum + t.pnl, 0) / losingTrades.length) * 100) / 100 : 0,
        profitFactor: losingTrades.length > 0 ? Math.abs(winningTrades.reduce((sum, t) => sum + t.pnl, 0) / losingTrades.reduce((sum, t) => sum + t.pnl, 0)) : 0,
        maxDrawdown: Math.abs(Math.min(...closedTradesOnly.map(t => t.pnl), 0)),
        totalCommission: 0, // Included in spread for OANDA
        totalSwap: Math.round(totalSwap * 100) / 100
      }

      return NextResponse.json({
        trades: paginatedTrades,
        stats,
        pagination: {
          total,
          page,
          limit,
          totalPages
        },
        source: 'oanda-live',
        message: `Showing ${paginatedTrades.length} trades from OANDA (${closedTradesOnly.length} closed, ${openTradesOnly.length} open, ${pendingOrders.length} pending orders)`
      })

    } catch (oandaError) {
      console.warn('OANDA API not available, trying execution engine:', oandaError)
      
      // Final fallback to execution engine data
      try {
        console.log(`Fetching fallback data from execution engine: ${EXECUTION_ENGINE_URL}/journal/summary`)
        
        const summaryResponse = await fetch(`${EXECUTION_ENGINE_URL}/journal/summary`)
        
        if (summaryResponse.ok) {
          const summaryData = await summaryResponse.json()
          console.log(`Execution engine has ${summaryData.summary.total_trades} total trades as fallback`)
          
          // Return minimal error response if all sources fail
          return NextResponse.json({
            trades: [],
            stats: {
              totalTrades: summaryData.summary.total_trades,
              closedTrades: summaryData.summary.closed_trades,
              openTrades: summaryData.summary.open_trades,
              winningTrades: summaryData.summary.successful_trades,
              losingTrades: summaryData.summary.total_trades - summaryData.summary.successful_trades,
              totalPnL: summaryData.summary.total_pl,
              winRate: summaryData.summary.success_rate_percent,
              averageWin: 0,
              averageLoss: 0,
              profitFactor: 1.0,
              maxDrawdown: Math.abs(summaryData.summary.total_pl) * 0.1,
              totalCommission: 0,
              totalSwap: 0
            },
            pagination: {
              total: summaryData.summary.total_trades,
              page,
              limit,
              totalPages: Math.ceil(summaryData.summary.total_trades / limit)
            },
            source: 'execution-engine-fallback',
            message: `No trade data available - using execution engine summary only`
          })
        }
      } catch (executionEngineError) {
        console.error('All data sources failed:', executionEngineError)
        
        // Return minimal error response if all sources fail
        return NextResponse.json({
          trades: [],
          stats: {
            totalTrades: 0,
            closedTrades: 0,
            openTrades: 0,
            winningTrades: 0,
            losingTrades: 0,
            totalPnL: 0,
            winRate: 0,
            averageWin: 0,
            averageLoss: 0,
            profitFactor: 0,
            maxDrawdown: 0,
            totalCommission: 0,
            totalSwap: 0
          },
          pagination: {
            total: 0,
            page,
            limit,
            totalPages: 0
          },
          source: 'error',
          message: 'No trade data available - all sources failed'
        }, { status: 503 })
      }
    }
    
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