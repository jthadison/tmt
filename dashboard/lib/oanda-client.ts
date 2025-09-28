/**
 * OANDA API Client for Dashboard
 * Direct integration with OANDA REST API for real-time performance analytics
 */

export interface OandaConfig {
  apiKey: string
  accountId: string
  environment?: 'practice' | 'live'
}

export interface AccountSummary {
  id: string
  alias: string
  currency: string
  balance: number
  unrealizedPL: number
  realizedPL: number
  marginUsed: number
  marginAvailable: number
  openTradeCount: number
  openPositionCount: number
  pendingOrderCount: number
  hedgingEnabled: boolean
  lastTransactionID: string
  NAV: number
}

export interface Position {
  instrument: string
  long?: {
    units: string
    averagePrice: string
    pl: string
    resettablePL: string
    financing: string
    tradeIDs: string[]
    unrealizedPL: string
  }
  short?: {
    units: string
    averagePrice: string
    pl: string
    resettablePL: string
    financing: string
    tradeIDs: string[]
    unrealizedPL: string
  }
  pl: string
  resettablePL: string
  financing: string
  commission: string
  unrealizedPL: string
  marginUsed: string
}

export interface Trade {
  id: string
  instrument: string
  price: string
  openTime: string
  initialUnits: string
  currentUnits: string
  realizedPL: string
  unrealizedPL: string
  averageClosePrice?: string
  closingTransactionIDs?: string[]
  financing: string
  closeTime?: string
  clientExtensions?: any
  takeProfitOrder?: any
  stopLossOrder?: any
  trailingStopLossOrder?: any
}

export interface Transaction {
  id: string
  time: string
  userID: number
  accountID: string
  batchID: string
  requestID?: string
  type: string
  instrument?: string
  units?: string
  price?: string
  pl?: string
  financing?: string
  commission?: string
  accountBalance?: string
  reason?: string
}

export interface Candle {
  time: string
  volume: number
  mid?: {
    o: string
    h: string
    l: string
    c: string
  }
  bid?: {
    o: string
    h: string
    l: string
    c: string
  }
  ask?: {
    o: string
    h: string
    l: string
    c: string
  }
  complete: boolean
}

export class OandaClient {
  private baseUrl: string
  private headers: HeadersInit

  constructor(private config: OandaConfig) {
    this.baseUrl = config.environment === 'live' 
      ? 'https://api-fxtrade.oanda.com'
      : 'https://api-fxpractice.oanda.com'
    
    this.headers = {
      'Authorization': `Bearer ${config.apiKey}`,
      'Content-Type': 'application/json',
      'Accept-Datetime-Format': 'UNIX'
    }
  }

  /**
   * Get account summary
   */
  async getAccountSummary(): Promise<AccountSummary> {
    const response = await fetch(
      `${this.baseUrl}/v3/accounts/${this.config.accountId}`,
      { headers: this.headers }
    )
    
    if (!response.ok) {
      throw new Error(`OANDA API error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.account
  }

  /**
   * Get all open positions
   */
  async getOpenPositions(): Promise<Position[]> {
    const response = await fetch(
      `${this.baseUrl}/v3/accounts/${this.config.accountId}/positions`,
      { headers: this.headers }
    )
    
    if (!response.ok) {
      throw new Error(`OANDA API error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.positions || []
  }

  /**
   * Get all open trades
   */
  async getOpenTrades(): Promise<Trade[]> {
    const response = await fetch(
      `${this.baseUrl}/v3/accounts/${this.config.accountId}/trades`,
      { headers: this.headers }
    )
    
    if (!response.ok) {
      throw new Error(`OANDA API error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.trades || []
  }

  /**
   * Get all pending orders
   */
  async getPendingOrders(): Promise<any[]> {
    const response = await fetch(
      `${this.baseUrl}/v3/accounts/${this.config.accountId}/orders`,
      { headers: this.headers }
    )
    
    if (!response.ok) {
      throw new Error(`OANDA API error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.orders || []
  }

  /**
   * Get transaction history
   */
  async getTransactions(from?: string, to?: string, count: number = 100): Promise<Transaction[]> {
    let url = `${this.baseUrl}/v3/accounts/${this.config.accountId}/transactions`
    const params = new URLSearchParams()
    
    // OANDA expects transaction IDs or specific format, not timestamps for 'from'
    // Use pageSize instead of count for transaction history
    if (from && !isNaN(parseInt(from))) {
      // If from is a transaction ID
      params.append('from', from)
    }
    if (to && !isNaN(parseInt(to))) {
      // If to is a transaction ID  
      params.append('to', to)
    }
    params.append('pageSize', Math.min(count, 1000).toString())
    
    if (params.toString()) {
      url += '?' + params.toString()
    }
    
    const response = await fetch(url, { headers: this.headers })
    
    if (!response.ok) {
      throw new Error(`OANDA API error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.transactions || []
  }

  /**
   * Get closed trades for P&L calculation
   */
  async getClosedTrades(count: number = 500): Promise<Trade[]> {
    const response = await fetch(
      `${this.baseUrl}/v3/accounts/${this.config.accountId}/trades?state=CLOSED&count=${count}`,
      { headers: this.headers }
    )
    
    if (!response.ok) {
      throw new Error(`OANDA API error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.trades || []
  }

  /**
   * Get trade history with complete timestamps using transactions
   * This provides more reliable entry/exit dates than the trades endpoint
   */
  async getTradeHistoryFromTransactions(count: number = 500): Promise<any[]> {
    try {
      // Get recent transactions
      const transactions = await this.getTransactions(undefined, undefined, count * 3) // Get more transactions to find trades
      
      // Group transactions by trade ID to reconstruct complete trade history
      const tradeMap = new Map<string, any>()
      
      transactions.forEach(tx => {
        // Look for trade-related transactions
        if (tx.type === 'MARKET_ORDER_FILL' || tx.type === 'ORDER_FILL' || tx.type === 'TRADE_CLOSE') {
          const tradeId = (tx as any).tradeOpened?.tradeID || (tx as any).tradeClosed?.tradeID
          
          if (tradeId) {
            if (!tradeMap.has(tradeId)) {
              tradeMap.set(tradeId, {
                id: tradeId,
                instrument: tx.instrument,
                openTime: null,
                closeTime: null,
                openPrice: null,
                closePrice: null,
                units: null,
                pnl: null,
                status: 'unknown'
              })
            }
            
            const trade = tradeMap.get(tradeId)!
            
            if ((tx as any).tradeOpened) {
              // This is a trade opening transaction
              trade.openTime = tx.time
              trade.openPrice = tx.price
              trade.units = (tx as any).tradeOpened.units
              trade.status = 'open'
            }
            
            if ((tx as any).tradeClosed) {
              // This is a trade closing transaction  
              trade.closeTime = tx.time
              trade.closePrice = tx.price
              trade.pnl = tx.pl
              trade.status = 'closed'
            }
          }
        }
      })
      
      return Array.from(tradeMap.values())
        .filter(trade => trade.openTime) // Only return trades with valid open times
        .slice(0, count) // Limit results
        
    } catch (error) {
      console.warn('Failed to get trade history from transactions:', error)
      return []
    }
  }

  /**
   * Get instrument price history (candles)
   */
  async getCandles(
    instrument: string, 
    granularity: string = 'H1',
    count: number = 100
  ): Promise<Candle[]> {
    const params = new URLSearchParams({
      granularity,
      count: count.toString()
    })
    
    const response = await fetch(
      `${this.baseUrl}/v3/instruments/${instrument}/candles?${params}`,
      { headers: this.headers }
    )
    
    if (!response.ok) {
      throw new Error(`OANDA API error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.candles || []
  }

  /**
   * Calculate P&L metrics from account data
   */
  async getPnLMetrics() {
    const [account, positions, trades] = await Promise.all([
      this.getAccountSummary(),
      this.getOpenPositions(),
      this.getOpenTrades()
    ])

    // Get recent transactions to calculate daily P&L
    const recentTransactions = await this.getTransactions(undefined, undefined, 500)
    
    // Filter transactions from today
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayTimestamp = today.getTime()
    
    let dailyPL = 0
    recentTransactions.forEach(tx => {
      const txTime = new Date(tx.time).getTime()
      if (txTime >= todayTimestamp && tx.pl) {
        dailyPL += parseFloat(tx.pl)
      }
    })

    return {
      balance: parseFloat(account.balance),
      unrealizedPL: parseFloat(account.unrealizedPL || '0'),
      realizedPL: parseFloat(account.realizedPL || '0'),
      dailyPL,
      marginUsed: parseFloat(account.marginUsed),
      marginAvailable: parseFloat(account.marginAvailable),
      openTradeCount: account.openTradeCount,
      positions: positions.map(p => ({
        instrument: p.instrument,
        units: p.long ? parseFloat(p.long.units) : parseFloat(p.short?.units || '0'),
        unrealizedPL: parseFloat(p.unrealizedPL),
        side: p.long ? 'long' : 'short'
      })),
      trades: trades.map(t => ({
        id: t.id,
        instrument: t.instrument,
        units: parseFloat(t.currentUnits),
        price: parseFloat(t.price),
        unrealizedPL: parseFloat(t.unrealizedPL),
        openTime: t.openTime
      }))
    }
  }
}

// Singleton instance for the dashboard
let clientInstance: OandaClient | null = null

export function getOandaClient(): OandaClient {
  if (!clientInstance) {
    const apiKey = process.env.OANDA_API_KEY || process.env.NEXT_PUBLIC_OANDA_API_KEY
    const accountId = process.env.OANDA_ACCOUNT_ID || process.env.NEXT_PUBLIC_OANDA_ACCOUNT_ID
    const environment = (process.env.OANDA_ENVIRONMENT || process.env.NEXT_PUBLIC_OANDA_ENVIRONMENT || 'practice') as 'practice' | 'live'

    if (!apiKey || !accountId) {
      throw new Error('OANDA API credentials not configured')
    }

    clientInstance = new OandaClient({
      apiKey,
      accountId,
      environment
    })
  }

  return clientInstance
}