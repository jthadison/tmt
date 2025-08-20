/**
 * Real-time P&L Tracker Component - AC1
 * Story 9.6: Real-time P&L tracking with trade-by-trade breakdown and performance attribution
 * 
 * Displays live profit/loss metrics with detailed trade breakdown and agent attribution
 */

'use client'

import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  BarChart3,
  Clock,
  Users,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  RefreshCw
} from 'lucide-react'
import { RealtimePnL, TradeBreakdown } from '@/types/performanceAnalytics'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'
import { formatCurrency, formatPercent } from '@/utils/formatters'

interface RealtimePnLTrackerProps {
  accountId: string
  agentId?: string
  showBreakdown?: boolean
  refreshInterval?: number
  onTradeClick?: (trade: TradeBreakdown) => void
}

export default function RealtimePnLTracker({
  accountId,
  agentId,
  showBreakdown = true,
  refreshInterval = 5000,
  onTradeClick
}: RealtimePnLTrackerProps) {
  const [pnlData, setPnlData] = useState<RealtimePnL | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(showBreakdown)
  const [selectedTimeframe, setSelectedTimeframe] = useState<'daily' | 'weekly' | 'monthly'>('daily')
  const [autoRefresh, setAutoRefresh] = useState(true)

  // Fetch P&L data
  const fetchPnLData = useCallback(async () => {
    // Don't fetch if accountId is missing
    if (!accountId) {
      setError('Account ID is required')
      setLoading(false)
      return
    }

    try {
      const data = await performanceAnalyticsService.getRealtimePnL(accountId, agentId)
      const tradeBreakdown = await performanceAnalyticsService.getTradeBreakdown(accountId, agentId)
      setPnlData({ ...data, trades: tradeBreakdown })
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch P&L data')
    } finally {
      setLoading(false)
    }
  }, [accountId, agentId])

  // Auto-refresh
  useEffect(() => {
    fetchPnLData()
    
    if (autoRefresh) {
      const interval = setInterval(fetchPnLData, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [fetchPnLData, autoRefresh, refreshInterval])

  // Calculate P&L metrics
  const pnlMetrics = useMemo(() => {
    if (!pnlData) return null

    const timeframePnL = {
      daily: pnlData.dailyPnL,
      weekly: pnlData.weeklyPnL,
      monthly: pnlData.monthlyPnL
    }[selectedTimeframe]

    const pnlPercent = pnlData.currentPnL !== 0 ? 
      (timeframePnL / Math.abs(pnlData.currentPnL)) * 100 : 0

    const drawdownPercent = pnlData.highWaterMark !== 0 ?
      (pnlData.currentDrawdown / pnlData.highWaterMark) * 100 : 0

    return {
      current: pnlData.currentPnL,
      timeframe: timeframePnL,
      timeframePercent: pnlPercent,
      realized: pnlData.realizedPnL,
      unrealized: pnlData.unrealizedPnL,
      drawdown: pnlData.currentDrawdown,
      drawdownPercent,
      tradeCount: pnlData.trades.length,
      winningTrades: pnlData.trades.filter(t => t.pnl > 0).length,
      losingTrades: pnlData.trades.filter(t => t.pnl < 0).length
    }
  }, [pnlData, selectedTimeframe])

  // Group trades by agent
  const tradesByAgent = useMemo(() => {
    if (!pnlData) return new Map()

    const grouped = new Map<string, TradeBreakdown[]>()
    pnlData.trades.forEach(trade => {
      const agent = trade.agentName || 'Unknown'
      if (!grouped.has(agent)) {
        grouped.set(agent, [])
      }
      grouped.get(agent)!.push(trade)
    })

    return grouped
  }, [pnlData])

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg p-6 animate-pulse">
        <div className="h-8 bg-gray-800 rounded w-1/3 mb-4"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 bg-gray-800 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-600 rounded-lg p-6">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    )
  }

  if (!pnlData || !pnlMetrics) {
    return null
  }

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Real-time P&L Tracker</h2>
            {agentId && (
              <span className="px-2 py-1 bg-blue-900/50 text-blue-400 text-sm rounded">
                Agent: {pnlData.agentId}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`p-2 rounded ${
                autoRefresh ? 'bg-green-900/50 text-green-400' : 'bg-gray-800 text-gray-400'
              } hover:bg-opacity-70 transition-colors`}
            >
              <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => fetchPnLData()}
              className="p-2 bg-gray-800 text-gray-400 rounded hover:bg-gray-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Timeframe Selector */}
        <div className="flex gap-2">
          {(['daily', 'weekly', 'monthly'] as const).map(tf => (
            <button
              key={tf}
              onClick={() => setSelectedTimeframe(tf)}
              className={`px-3 py-1 rounded text-sm capitalize ${
                selectedTimeframe === tf
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              } transition-colors`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* P&L Metrics Grid */}
      <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Current P&L */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gray-800 rounded-lg p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Total P&L</span>
            <DollarSign className="w-4 h-4 text-gray-500" />
          </div>
          <div className={`text-2xl font-bold ${
            pnlMetrics.current >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {formatCurrency(pnlMetrics.current)}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <div className={`text-sm ${
              pnlMetrics.timeframe >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {pnlMetrics.timeframe >= 0 ? '+' : ''}{formatCurrency(pnlMetrics.timeframe)}
            </div>
            <div className={`flex items-center gap-1 text-xs px-1 py-0.5 rounded ${
              pnlMetrics.timeframePercent >= 0 
                ? 'bg-green-900/50 text-green-400' 
                : 'bg-red-900/50 text-red-400'
            }`}>
              {pnlMetrics.timeframePercent >= 0 ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              {formatPercent(Math.abs(pnlMetrics.timeframePercent))}
            </div>
          </div>
        </motion.div>

        {/* Realized vs Unrealized */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gray-800 rounded-lg p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Realized / Unrealized</span>
            <BarChart3 className="w-4 h-4 text-gray-500" />
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-400 text-xs">Realized</span>
              <span className={`text-sm font-medium ${
                pnlMetrics.realized >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {formatCurrency(pnlMetrics.realized)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400 text-xs">Unrealized</span>
              <span className={`text-sm font-medium ${
                pnlMetrics.unrealized >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {formatCurrency(pnlMetrics.unrealized)}
              </span>
            </div>
          </div>
          <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-green-500 to-blue-500"
              style={{ 
                width: `${Math.abs(pnlMetrics.realized) / 
                  (Math.abs(pnlMetrics.realized) + Math.abs(pnlMetrics.unrealized)) * 100}%` 
              }}
            />
          </div>
        </motion.div>

        {/* Drawdown */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-800 rounded-lg p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Current Drawdown</span>
            <AlertTriangle className="w-4 h-4 text-gray-500" />
          </div>
          <div className={`text-2xl font-bold ${
            pnlMetrics.drawdown > 0 ? 'text-yellow-400' : 'text-green-400'
          }`}>
            {formatCurrency(pnlMetrics.drawdown)}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <div className={`text-sm ${
              pnlMetrics.drawdownPercent > 5 ? 'text-yellow-400' : 'text-gray-400'
            }`}>
              {formatPercent(pnlMetrics.drawdownPercent)} from peak
            </div>
          </div>
          <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className={`h-full ${
                pnlMetrics.drawdownPercent > 10 ? 'bg-red-500' :
                pnlMetrics.drawdownPercent > 5 ? 'bg-yellow-500' : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(pnlMetrics.drawdownPercent, 100)}%` }}
            />
          </div>
        </motion.div>
      </div>

      {/* Trade Breakdown */}
      {showBreakdown && (
        <div className="border-t border-gray-800">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-300">
                Trade Breakdown ({pnlMetrics.tradeCount} trades)
              </span>
              <div className="flex gap-2 text-xs">
                <span className="text-green-400">
                  {pnlMetrics.winningTrades} wins
                </span>
                <span className="text-gray-500">|</span>
                <span className="text-red-400">
                  {pnlMetrics.losingTrades} losses
                </span>
              </div>
            </div>
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>

          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="px-6 pb-6">
                  {/* Trades by Agent */}
                  {Array.from(tradesByAgent.entries()).map(([agent, trades]) => (
                    <div key={agent} className="mt-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-300">{agent}</span>
                        <span className="text-xs text-gray-500">
                          {trades.length} trades
                        </span>
                      </div>
                      
                      <div className="space-y-1">
                        {trades.slice(0, 5).map((trade) => (
                          <motion.div
                            key={trade.tradeId}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            className="flex items-center justify-between p-2 bg-gray-800/50 rounded hover:bg-gray-800 cursor-pointer transition-colors"
                            onClick={() => onTradeClick?.(trade)}
                          >
                            <div className="flex items-center gap-3">
                              <div className={`w-2 h-2 rounded-full ${
                                trade.direction === 'long' ? 'bg-green-500' : 'bg-red-500'
                              }`} />
                              <div>
                                <div className="text-sm text-white">{trade.symbol}</div>
                                <div className="text-xs text-gray-500">
                                  {trade.strategy} • {trade.size} units
                                </div>
                              </div>
                            </div>
                            
                            <div className="text-right">
                              <div className={`text-sm font-medium ${
                                trade.netPnL >= 0 ? 'text-green-400' : 'text-red-400'
                              }`}>
                                {formatCurrency(trade.netPnL)}
                              </div>
                              <div className="text-xs text-gray-500">
                                {formatPercent(trade.pnlPercent)}
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>

                      {trades.length > 5 && (
                        <button className="mt-2 text-xs text-blue-400 hover:text-blue-300">
                          View {trades.length - 5} more trades →
                        </button>
                      )}
                    </div>
                  ))}

                  {/* Summary Stats */}
                  <div className="mt-4 pt-4 border-t border-gray-800 grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-xs text-gray-500">Win Rate</div>
                      <div className="text-sm font-medium text-white">
                        {formatPercent((pnlMetrics.winningTrades / pnlMetrics.tradeCount) * 100)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500">Avg Win</div>
                      <div className="text-sm font-medium text-green-400">
                        {formatCurrency(
                          pnlData.trades
                            .filter(t => t.pnl > 0)
                            .reduce((sum, t) => sum + t.netPnL, 0) / 
                          Math.max(pnlMetrics.winningTrades, 1)
                        )}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500">Avg Loss</div>
                      <div className="text-sm font-medium text-red-400">
                        {formatCurrency(
                          Math.abs(
                            pnlData.trades
                              .filter(t => t.pnl < 0)
                              .reduce((sum, t) => sum + t.netPnL, 0) / 
                            Math.max(pnlMetrics.losingTrades, 1)
                          )
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Last Update */}
      <div className="px-6 py-2 bg-gray-800/50 text-center">
        <span className="text-xs text-gray-500">
          <Clock className="w-3 h-3 inline mr-1" />
          Last updated: {new Date(pnlData.lastUpdate).toLocaleTimeString()}
        </span>
      </div>
    </div>
  )
}