'use client'

import { useState, useEffect } from 'react'
import { TradeHistory } from '@/components/account-detail/TradeHistory'
import { tradeHistoryService } from '@/services/tradeHistoryService'
import { Trade } from '@/types/accountDetail'

export default function HistoryTestPage() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTradeHistory = async () => {
      try {
        setLoading(true)
        console.log('HistoryTestPage: Fetching trade history...')
        
        const response = await tradeHistoryService.getTradeHistory({
          accountId: '101-001-21040028-001',
          limit: 10 // Get trades for testing
        })
        
        console.log('HistoryTestPage: Received trade history response:', response)
        setTrades(response.trades)
        setError(null)
      } catch (err) {
        console.error('HistoryTestPage: Error fetching trade history:', err)
        setError('Failed to load trade history: ' + (err as Error).message)
      } finally {
        setLoading(false)
      }
    }

    fetchTradeHistory()
  }, [])

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white">Trading History Test Page</h1>
          <p className="text-gray-400 mt-2">
            Testing real-time trade data integration with the live trading system
          </p>
          {!loading && trades.length > 0 && (
            <p className="text-sm text-green-400 mt-1">
              ✅ Successfully connected to live trading system - showing {trades.length} real trades
            </p>
          )}
        </div>
        
        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-md">
            <p className="text-red-400">{error}</p>
          </div>
        )}
        
        <TradeHistory 
          trades={trades}
          accountId="101-001-21040028-001"
          loading={loading}
          showAccountColumn={false}
        />
      </div>
    </div>
  )
}