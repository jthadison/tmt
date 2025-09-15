import { NextResponse } from 'next/server'
import { getOandaClient } from '@/lib/oanda-client'

export async function GET() {
  try {
    const client = getOandaClient()
    
    console.log('=== FETCHING OANDA DATA ===')
    const [account, positions, trades, orders] = await Promise.all([
      client.getAccountSummary(),
      client.getOpenPositions(), 
      client.getOpenTrades(),
      client.getPendingOrders()
    ])
    
    const debugInfo = {
      account: {
        id: account.id,
        openTradeCount: account.openTradeCount,
        openPositionCount: account.openPositionCount,
        pendingOrderCount: account.pendingOrderCount,
        balance: account.balance,
        unrealizedPL: account.unrealizedPL,
        marginUsed: account.marginUsed
      },
      actualTrades: trades.map((trade, i) => ({
        index: i + 1,
        id: trade.id,
        instrument: trade.instrument,
        side: trade.currentUnits > 0 ? 'Long' : 'Short',
        units: Math.abs(trade.currentUnits),
        unrealizedPL: trade.unrealizedPL,
        openTime: trade.openTime,
        state: trade.state
      })),
      netPositions: positions.map((pos, i) => ({
        index: i + 1,
        instrument: pos.instrument,
        longUnits: pos.long?.units || 0,
        shortUnits: pos.short?.units || 0,
        netUnrealizedPL: pos.unrealizedPL,
        longPL: pos.long?.unrealizedPL || 0,
        shortPL: pos.short?.unrealizedPL || 0,
        longTradeIDs: pos.long?.tradeIDs || [],
        shortTradeIDs: pos.short?.tradeIDs || []
      })),
      pendingOrders: orders.map((order, i) => ({
        index: i + 1,
        id: order.id,
        type: order.type,
        instrument: order.instrument,
        units: order.units,
        price: order.price,
        state: order.state
      })),
      summary: {
        dashboardShows: trades.length + ' individual trades',
        oandaAccountSays: `${account.openTradeCount} open trades, ${account.openPositionCount} open positions, ${account.pendingOrderCount} pending orders`,
        possibleTradingViewCount: `${trades.length} trades + ${orders.length} orders = ${trades.length + orders.length} total items`,
        totalUniquePositions: positions.length,
        tradesWithPositionMapping: positions.reduce((total, pos) => {
          return total + (pos.long?.tradeIDs?.length || 0) + (pos.short?.tradeIDs?.length || 0)
        }, 0)
      }
    }
    
    return NextResponse.json(debugInfo)
    
  } catch (error) {
    console.error('OANDA Debug Error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch OANDA debug info', details: error.message },
      { status: 500 }
    )
  }
}