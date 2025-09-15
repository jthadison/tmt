'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { OpenTradesGrid } from '@/components/account-detail/OpenTradesGrid'
import { ClosedTradesGrid } from '@/components/account-detail/ClosedTradesGrid'
import { tradeHistoryService } from '@/services/tradeHistoryService'
import { Trade } from '@/types/accountDetail'
import { useRealtimeUpdates } from '@/hooks/useRealtimeUpdates'

export default function HistoryPage() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [openTrades, setOpenTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastRefresh, setLastRefresh] = useState<number>(0)
  const [realtimeEnabled, setRealtimeEnabled] = useState(true)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // Real-time updates
  const { connected: realtimeConnected, lastUpdate, error: realtimeError } = useRealtimeUpdates({
    enabled: realtimeEnabled,
    onUpdate: (update) => {
      if (update.type === 'update' && update.data?.recentTrades) {
        // Separate open and closed trades for real-time updates
        const newTrades = update.data!.recentTrades!
        const newOpenTrades = newTrades.filter(t => t.status === 'open')
        const newClosedTrades = newTrades.filter(t => t.status === 'closed' || !t.status || t.closeTime)
        
        // Update open trades
        if (newOpenTrades.length > 0) {
          setOpenTrades(prevTrades => {
            const newTradeIds = new Set(newOpenTrades.map(t => t.id))
            const filteredPrevTrades = prevTrades.filter(t => !newTradeIds.has(t.id))
            return [...newOpenTrades, ...filteredPrevTrades]
          })
        }
        
        // Update closed trades
        if (newClosedTrades.length > 0) {
          setTrades(prevTrades => {
            const newTradeIds = new Set(newClosedTrades.map(t => t.id))
            const filteredPrevTrades = prevTrades.filter(t => !newTradeIds.has(t.id))
            return [...newClosedTrades, ...filteredPrevTrades]
          })
        }
        
        setLastRefresh(Date.now())
      }
    }
  })

  const fetchTradeHistory = useCallback(async (showLoading: boolean = true) => {
    try {
      if (showLoading) setLoading(true)
      console.log('HistoryPage: Fetching trade history...')
      
      // Fetch all trades (mostly closed) from orchestrator
      const allTradesResponse = await tradeHistoryService.getTradeHistory({
        accountId: 'all-accounts',
        limit: 100
      })
      
      // Fetch open trades separately from OANDA to get accurate financial data
      const openTradesResponse = await tradeHistoryService.getTradeHistory({
        accountId: 'all-accounts',
        filter: { status: 'open' },
        limit: 20
      })
      
      console.log('HistoryPage: Received all trades:', allTradesResponse.trades?.length)
      console.log('HistoryPage: Received open trades:', openTradesResponse.trades?.length)
      
      // Sort orchestrator trades by openTime (most recent first) for better matching
      const sortedOrchestratorTrades = [...allTradesResponse.trades].sort((a, b) => {
        const aTime = new Date(a.openTime || 0).getTime()
        const bTime = new Date(b.openTime || 0).getTime() 
        return bTime - aTime  // Most recent first
      })
      
      // Merge OANDA financial data with orchestrator AI metadata
      const mergedOpenTrades = openTradesResponse.trades.map((oandaTrade, index) => {
        console.log(`\n--- Matching OANDA Trade ${index + 1} ---`)
        console.log(`OANDA: ID=${oandaTrade.id}, ${oandaTrade.instrument}, ${oandaTrade.side}, ${oandaTrade.units} units, Entry: ${oandaTrade.entryPrice}`)
        
        // Try to find matching trade in orchestrator data by instrument, side, and approximate entry price
        const matchingOrchestratorTrade = sortedOrchestratorTrades.find((orchTrade, orchIndex) => {
          // Don't filter by status - orchestrator marks trades as closed immediately after placing
          // but OANDA still has them as open positions
          
          // Match by instrument
          const oandaInstrument = oandaTrade.instrument || oandaTrade.symbol
          const orchInstrument = orchTrade.instrument || orchTrade.symbol
          if (oandaInstrument !== orchInstrument) return false
          
          // Match by side
          if (oandaTrade.side !== orchTrade.side) return false
          
          // Match by approximate entry price (within 1% tolerance for price matching)
          const oandaPrice = oandaTrade.entryPrice || oandaTrade.price || 0
          const orchPrice = orchTrade.entryPrice || orchTrade.price || 0
          
          if (oandaPrice > 0 && orchPrice > 0) {
            const priceDiff = Math.abs(oandaPrice - orchPrice) / oandaPrice
            if (priceDiff > 0.01) { // 1% tolerance
              console.log(`  Orch ${orchIndex}: ${orchTrade.id} - Price mismatch: OANDA=${oandaPrice}, Orch=${orchPrice}, diff=${(priceDiff*100).toFixed(2)}%`)
              return false
            }
          }
          
          // Match by approximate size (within 10% tolerance)
          const oandaSize = oandaTrade.units || oandaTrade.size || 0
          const orchSize = orchTrade.units || orchTrade.size || 0
          const sizeDiff = Math.abs(oandaSize - orchSize) / Math.max(oandaSize, orchSize)
          if (sizeDiff > 0.1) {
            console.log(`  Orch ${orchIndex}: ${orchTrade.id} - Size mismatch: OANDA=${oandaSize}, Orch=${orchSize}, diff=${(sizeDiff*100).toFixed(2)}%`)
            return false
          }
          
          console.log(`  ✅ MATCH FOUND: Orch ${orchIndex}: ${orchTrade.id} - Pattern: ${orchTrade.pattern}, Confidence: ${orchTrade.confidence}`)
          return true
        })
        
        // Return OANDA trade with AI metadata if found
        if (matchingOrchestratorTrade) {
          const merged = {
            ...oandaTrade,
            pattern: matchingOrchestratorTrade.pattern,
            confidence: matchingOrchestratorTrade.confidence,
            strategy: matchingOrchestratorTrade.strategy || oandaTrade.strategy,
            agentName: matchingOrchestratorTrade.agentName || oandaTrade.agentName
          }
          console.log(`  ✅ MERGED: Added pattern='${merged.pattern}', confidence=${merged.confidence}`)
          return merged
        }
        
        console.log(`  ⚠️  NO MATCH: Will show without pattern/confidence`)
        return oandaTrade
      })
      
      const mergedCount = mergedOpenTrades.filter(t => t.pattern).length
      console.log(`\n✨ MERGE SUMMARY: ${mergedCount}/${mergedOpenTrades.length} OANDA trades merged with AI metadata`)
      
      setTrades(allTradesResponse.trades)
      setOpenTrades(mergedOpenTrades)
      setError(null)
      setLastRefresh(Date.now())
    } catch (err) {
      console.error('HistoryPage: Error fetching trade history:', err)
      setError('Failed to load trade history')
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [])

  const startAutoRefresh = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    
    intervalRef.current = setInterval(() => {
      fetchTradeHistory(false) // Don't show loading spinner for auto-refresh
    }, 30000) // Refresh every 30 seconds
  }, [fetchTradeHistory])

  const stopAutoRefresh = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const handleManualRefresh = useCallback(async () => {
    await fetchTradeHistory(true)
  }, [fetchTradeHistory])

  useEffect(() => {
    fetchTradeHistory()
  }, [fetchTradeHistory])

  useEffect(() => {
    if (autoRefresh) {
      startAutoRefresh()
    } else {
      stopAutoRefresh()
    }
    
    return () => {
      stopAutoRefresh()
    }
  }, [autoRefresh, startAutoRefresh, stopAutoRefresh])

  // Calculate trade counts for display
  const openTradesCount = openTrades.length
  const closedTradesCount = trades.filter(trade => trade.status === 'closed' || !trade.status || trade.closeTime).length
  const totalTradesCount = closedTradesCount + openTradesCount

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-8">
          {/* Header */}
          <div>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-white">Trading Overview</h1>
                <p className="text-gray-400 mt-2">
                  Live trading positions and complete trade history across all accounts
                </p>
              </div>
              
              <div className="flex items-center gap-4">
                {/* Real-time toggle */}
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-300" htmlFor="realtime">
                    Real-time
                  </label>
                  <button
                    id="realtime"
                    onClick={() => setRealtimeEnabled(!realtimeEnabled)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      realtimeEnabled ? 'bg-green-600' : 'bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        realtimeEnabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                
                {/* Auto-refresh toggle */}
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-300" htmlFor="auto-refresh">
                    Auto-refresh
                  </label>
                  <button
                    id="auto-refresh"
                    onClick={() => setAutoRefresh(!autoRefresh)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      autoRefresh ? 'bg-blue-600' : 'bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        autoRefresh ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                
                {/* Manual refresh button */}
                <button
                  onClick={handleManualRefresh}
                  disabled={loading}
                  className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm rounded-md transition-colors"
                >
                  <svg
                    className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Refresh
                </button>
              </div>
            </div>
            
            {!loading && (trades.length > 0 || openTrades.length > 0) && (
              <div className="flex items-center gap-6 mt-4 text-sm flex-wrap">
                <p className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    realtimeConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
                  }`}></span>
                  <span className={realtimeConnected ? 'text-green-400' : 'text-gray-400'}>
                    {realtimeConnected ? '📡 Live system' : '📡 System offline'}
                  </span>
                  <span className="text-white">
                    - {openTradesCount} open, {closedTradesCount} completed
                  </span>
                </p>
                <p className="text-gray-400">
                  Total: {totalTradesCount} trades
                </p>
                {lastRefresh > 0 && (
                  <p className="text-gray-500 flex items-center gap-1">
                    <span>Last updated:</span>
                    <span className="font-mono">
                      {new Date(lastRefresh).toLocaleTimeString()}
                    </span>
                  </p>
                )}
                <div className="flex items-center gap-4">
                  {realtimeEnabled && (
                    <p className="text-green-400 text-xs flex items-center gap-1">
                      <span className="w-1 h-1 bg-green-400 rounded-full animate-ping"></span>
                      Real-time updates active
                    </p>
                  )}
                  {autoRefresh && (
                    <p className="text-blue-400 text-xs">
                      Auto-refreshing every 30s
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {(error || realtimeError) && (
            <div className="space-y-2">
              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-md">
                  <p className="text-red-400">Trade Data Error: {error}</p>
                </div>
              )}
              {realtimeError && (
                <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-md">
                  <p className="text-yellow-400">Real-time Connection: {realtimeError}</p>
                </div>
              )}
            </div>
          )}

          {/* Open Trades Grid */}
          <div>
            <OpenTradesGrid 
              trades={openTrades}
              loading={loading}
            />
          </div>

          {/* Closed Trades Grid */}
          <div>
            <ClosedTradesGrid 
              trades={trades}
              loading={loading}
              itemsPerPage={25}
            />
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}