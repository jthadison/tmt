'use client'

import { useState, useEffect } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { TradeHistory } from '@/components/account-detail/TradeHistory'
import { tradeHistoryService } from '@/services/tradeHistoryService'
import { Trade } from '@/types/accountDetail'

export default function HistoryPage() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTradeHistory = async () => {
      try {
        setLoading(true)
        console.log('HistoryPage: Fetching trade history...')
        
        const response = await tradeHistoryService.getTradeHistory({
          accountId: 'all-accounts',
          limit: 100 // Get more trades for the history view
        })
        
        console.log('HistoryPage: Received trade history response:', response)
        setTrades(response.trades)
        setError(null)
      } catch (err) {
        console.error('HistoryPage: Error fetching trade history:', err)
        setError('Failed to load trade history')
      } finally {
        setLoading(false)
      }
    }

    fetchTradeHistory()
  }, [])

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-white">Trading History</h1>
            <p className="text-gray-400 mt-2">
              Complete trade history across all accounts with real-time data from the trading system
            </p>
            {!loading && trades.length > 0 && (
              <p className="text-sm text-blue-400 mt-1">
                📡 Connected to live trading system - showing {trades.length} trades
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
            accountId="all-accounts"
            loading={loading}
            showAccountColumn={true}
          />
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}