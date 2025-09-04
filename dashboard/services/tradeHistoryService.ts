/**
 * Trade History Service
 * Provides aggregated trade history data from multiple sources
 */

import { Trade, TradeFilter, TradeStats } from '@/types/accountDetail'

export interface TradeHistoryResponse {
  trades: Trade[]
  stats: TradeStats
  pagination: {
    total: number
    page: number
    limit: number
    totalPages: number
  }
}

export interface TradeHistoryParams {
  page?: number
  limit?: number
  filter?: TradeFilter
  accountId?: string
  dateFrom?: string
  dateTo?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

class TradeHistoryService {
  private baseUrl: string

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3003'
  }

  /**
   * Get aggregated trade history from all accounts
   */
  async getTradeHistory(params: TradeHistoryParams = {}): Promise<TradeHistoryResponse> {
    try {
      const queryParams = new URLSearchParams()
      
      if (params.page) queryParams.set('page', params.page.toString())
      if (params.limit) queryParams.set('limit', params.limit.toString())
      if (params.accountId && params.accountId !== 'all-accounts') {
        queryParams.set('accountId', params.accountId)
      }
      if (params.dateFrom) queryParams.set('dateFrom', params.dateFrom)
      if (params.dateTo) queryParams.set('dateTo', params.dateTo)
      if (params.sortBy) queryParams.set('sortBy', params.sortBy)
      if (params.sortOrder) queryParams.set('sortOrder', params.sortOrder)
      
      // Add filter parameters
      if (params.filter) {
        if (params.filter.instrument) {
          queryParams.set('instrument', params.filter.instrument)
        }
        if (params.filter.status) {
          queryParams.set('status', params.filter.status)
        }
        if (params.filter.type) {
          queryParams.set('type', params.filter.type)
        }
        if (params.filter.minProfit !== undefined) {
          queryParams.set('minProfit', params.filter.minProfit.toString())
        }
        if (params.filter.maxProfit !== undefined) {
          queryParams.set('maxProfit', params.filter.maxProfit.toString())
        }
      }

      console.log('Fetching trade history from real API endpoint:', `/api/trades/history?${queryParams}`)
      
      const response = await fetch(`/api/trades/history?${queryParams}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch trade history: ${response.statusText}`)
      }

      const data = await response.json()
      console.log('Successfully fetched real trade history data:', data.trades?.length, 'trades')
      return data
      
    } catch (error) {
      console.error('Error fetching trade history, falling back to mock data:', error)
      
      // Fallback to mock data for development
      return this.getMockTradeHistory(params)
    }
  }

  /**
   * Get trade history for a specific account
   */
  async getAccountTradeHistory(accountId: string, params: TradeHistoryParams = {}): Promise<TradeHistoryResponse> {
    return this.getTradeHistory({ ...params, accountId })
  }

  /**
   * Export trade history to CSV
   */
  async exportTradeHistory(params: TradeHistoryParams = {}): Promise<Blob> {
    try {
      const queryParams = new URLSearchParams()
      
      // Add all relevant parameters for export
      if (params.accountId && params.accountId !== 'all-accounts') {
        queryParams.set('accountId', params.accountId)
      }
      if (params.dateFrom) queryParams.set('dateFrom', params.dateFrom)
      if (params.dateTo) queryParams.set('dateTo', params.dateTo)
      
      if (params.filter) {
        if (params.filter.instrument) {
          queryParams.set('instrument', params.filter.instrument)
        }
        if (params.filter.status) {
          queryParams.set('status', params.filter.status)
        }
        if (params.filter.type) {
          queryParams.set('type', params.filter.type)
        }
      }

      const response = await fetch(`${this.baseUrl}/api/trades/export?${queryParams}`, {
        headers: {
          'Accept': 'text/csv'
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to export trade history: ${response.statusText}`)
      }

      return await response.blob()
    } catch (error) {
      console.error('Error exporting trade history:', error)
      
      // Fallback to generating CSV from current data
      const data = await this.getTradeHistory(params)
      return this.generateCSVBlob(data.trades)
    }
  }

  /**
   * Get available instruments from trade history
   */
  async getInstruments(): Promise<string[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/trades/instruments`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch instruments: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching instruments:', error)
      
      // Fallback to common instruments
      return ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD']
    }
  }

  /**
   * Get available accounts for filtering
   */
  async getAccounts(): Promise<Array<{ id: string; name: string; type: string }>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/accounts`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch accounts: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching accounts:', error)
      
      // Fallback to mock accounts
      return [
        { id: 'demo-001', name: 'Demo Account 1', type: 'demo' },
        { id: 'demo-002', name: 'Demo Account 2', type: 'demo' },
        { id: 'live-001', name: 'OANDA Live', type: 'live' }
      ]
    }
  }

  /**
   * Mock trade history for development/fallback
   */
  private getMockTradeHistory(params: TradeHistoryParams): TradeHistoryResponse {
    const mockTrades: Trade[] = [
      {
        id: 'T001',
        accountId: 'demo-001',
        accountName: 'Demo Account 1',
        instrument: 'EUR/USD',
        type: 'market',
        side: 'buy',
        units: 10000,
        price: 1.0856,
        stopLoss: 1.0800,
        takeProfit: 1.0920,
        openTime: new Date('2024-01-15T10:30:00Z'),
        closeTime: new Date('2024-01-15T14:22:00Z'),
        status: 'closed',
        pnl: 45.20,
        commission: 0.50,
        swap: 0.0,
        tags: ['scalping', 'trend']
      },
      {
        id: 'T002',
        accountId: 'demo-001',
        accountName: 'Demo Account 1',
        instrument: 'GBP/USD',
        type: 'limit',
        side: 'sell',
        units: 15000,
        price: 1.2745,
        stopLoss: 1.2800,
        takeProfit: 1.2680,
        openTime: new Date('2024-01-15T08:15:00Z'),
        closeTime: new Date('2024-01-15T16:45:00Z'),
        status: 'closed',
        pnl: -32.10,
        commission: 0.75,
        swap: -0.25,
        tags: ['reversal']
      },
      {
        id: 'T003',
        accountId: 'demo-002',
        accountName: 'Demo Account 2',
        instrument: 'USD/JPY',
        type: 'market',
        side: 'buy',
        units: 20000,
        price: 148.25,
        stopLoss: 147.80,
        takeProfit: 149.00,
        openTime: new Date('2024-01-15T12:00:00Z'),
        status: 'open',
        pnl: 67.50,
        commission: 1.00,
        swap: 0.15,
        tags: ['breakout']
      }
    ]

    // Apply basic filtering
    let filteredTrades = mockTrades
    
    if (params.accountId && params.accountId !== 'all-accounts') {
      filteredTrades = filteredTrades.filter(trade => trade.accountId === params.accountId)
    }

    if (params.filter) {
      const filter = params.filter
      
      if (filter.instrument) {
        filteredTrades = filteredTrades.filter(trade => trade.instrument === filter.instrument)
      }
      
      if (filter.status) {
        filteredTrades = filteredTrades.filter(trade => trade.status === filter.status)
      }
      
      if (filter.type) {
        filteredTrades = filteredTrades.filter(trade => trade.type === filter.type)
      }
    }

    // Calculate stats
    const closedTrades = filteredTrades.filter(trade => trade.status === 'closed')
    const totalPnL = closedTrades.reduce((sum, trade) => sum + trade.pnl, 0)
    const winningTrades = closedTrades.filter(trade => trade.pnl > 0).length
    const losingTrades = closedTrades.filter(trade => trade.pnl < 0).length
    
    const stats: TradeStats = {
      totalTrades: filteredTrades.length,
      closedTrades: closedTrades.length,
      openTrades: filteredTrades.filter(trade => trade.status === 'open').length,
      winningTrades,
      losingTrades,
      totalPnL,
      winRate: closedTrades.length > 0 ? (winningTrades / closedTrades.length) * 100 : 0,
      averageWin: winningTrades > 0 ? closedTrades.filter(trade => trade.pnl > 0).reduce((sum, trade) => sum + trade.pnl, 0) / winningTrades : 0,
      averageLoss: losingTrades > 0 ? Math.abs(closedTrades.filter(trade => trade.pnl < 0).reduce((sum, trade) => sum + trade.pnl, 0) / losingTrades) : 0,
      profitFactor: 0,
      maxDrawdown: 0,
      totalCommission: filteredTrades.reduce((sum, trade) => sum + trade.commission, 0),
      totalSwap: filteredTrades.reduce((sum, trade) => sum + trade.swap, 0)
    }

    // Calculate profit factor
    const grossProfit = closedTrades.filter(trade => trade.pnl > 0).reduce((sum, trade) => sum + trade.pnl, 0)
    const grossLoss = Math.abs(closedTrades.filter(trade => trade.pnl < 0).reduce((sum, trade) => sum + trade.pnl, 0))
    stats.profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 999 : 0

    // Simple pagination
    const page = params.page || 1
    const limit = params.limit || 50
    const startIndex = (page - 1) * limit
    const paginatedTrades = filteredTrades.slice(startIndex, startIndex + limit)

    return {
      trades: paginatedTrades,
      stats,
      pagination: {
        total: filteredTrades.length,
        page,
        limit,
        totalPages: Math.ceil(filteredTrades.length / limit)
      }
    }
  }

  /**
   * Generate CSV blob from trades data
   */
  private generateCSVBlob(trades: Trade[]): Blob {
    const headers = [
      'ID', 'Account', 'Instrument', 'Type', 'Side', 'Units', 'Price',
      'Stop Loss', 'Take Profit', 'Open Time', 'Close Time', 'Status',
      'P&L', 'Commission', 'Swap', 'Tags'
    ]

    const csvContent = [
      headers.join(','),
      ...trades.map(trade => [
        trade.id,
        trade.accountName,
        trade.instrument,
        trade.type,
        trade.side,
        trade.units,
        trade.price,
        trade.stopLoss || '',
        trade.takeProfit || '',
        trade.openTime.toISOString(),
        trade.closeTime?.toISOString() || '',
        trade.status,
        trade.pnl.toFixed(2),
        trade.commission.toFixed(2),
        trade.swap.toFixed(2),
        (trade.tags || []).join(';')
      ].join(','))
    ].join('\n')

    return new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  }
}

// Singleton instance
export const tradeHistoryService = new TradeHistoryService()
export default tradeHistoryService