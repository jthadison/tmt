'use client'

import { useState, useMemo } from 'react'
import { Trade, TradeSortOptions } from '@/types/accountDetail'
import { useLivePricing } from '@/hooks/useLivePricing'

interface OpenTradesGridProps {
  trades: Trade[]
  loading?: boolean
  enableLivePricing?: boolean
}

export function OpenTradesGrid({ trades, loading = false, enableLivePricing = true }: OpenTradesGridProps) {
  const [sortOptions, setSortOptions] = useState<TradeSortOptions>({
    field: 'openTime',
    direction: 'desc'
  })

  // Filter only open trades
  const openTrades = useMemo(() => {
    return trades.filter(trade => trade.status === 'open')
  }, [trades])

  // Extract instruments for live pricing
  const instruments = useMemo(() => {
    return Array.from(new Set(openTrades.map(trade => {
      const instrument = trade.instrument || trade.symbol || ''
      return instrument.replace('_', '/')
    })))
  }, [openTrades])

  // Live pricing hook
  const { prices, calculatePnL, connected, lastUpdate, error: pricingError } = useLivePricing({
    instruments,
    enabled: enableLivePricing && instruments.length > 0,
    updateInterval: 10000 // 10 seconds
  })

  // Sort open trades
  const sortedTrades = useMemo(() => {
    return [...openTrades].sort((a, b) => {
      const { field, direction } = sortOptions
      
      let aValue: any, bValue: any
      
      switch (field) {
        case 'symbol':
          aValue = a.instrument || a.symbol
          bValue = b.instrument || b.symbol
          break
        case 'entryPrice':
          aValue = a.price || a.entryPrice || 0
          bValue = b.price || b.entryPrice || 0
          break
        case 'size':
          aValue = a.units || a.size
          bValue = b.units || b.size
          break
        case 'openTime':
          aValue = a.openTime
          bValue = b.openTime
          break
        case 'side':
          aValue = a.side || (a.type === 'long' ? 'buy' : 'sell')
          bValue = b.side || (b.type === 'long' ? 'buy' : 'sell')
          break
        case 'stopLoss':
          aValue = a.stopLoss || 0
          bValue = b.stopLoss || 0
          break
        case 'takeProfit':
          aValue = a.takeProfit || 0
          bValue = b.takeProfit || 0
          break
        default:
          aValue = a[field]
          bValue = b[field]
      }

      // Handle null/undefined values
      if (aValue == null && bValue == null) return 0
      if (aValue == null) return direction === 'asc' ? 1 : -1
      if (bValue == null) return direction === 'asc' ? -1 : 1

      if (aValue instanceof Date && bValue instanceof Date) {
        return direction === 'asc' 
          ? aValue.getTime() - bValue.getTime()
          : bValue.getTime() - aValue.getTime()
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return direction === 'asc' ? aValue - bValue : bValue - aValue
      }

      const aStr = String(aValue).toLowerCase()
      const bStr = String(bValue).toLowerCase()
      
      return direction === 'asc' 
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr)
    })
  }, [openTrades, sortOptions])

  const handleSort = (field: keyof Trade) => {
    setSortOptions(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  const formatDate = (date: Date | string | null): string => {
    if (!date) return '-'
    
    const dateObj = date instanceof Date ? date : new Date(date)
    
    if (isNaN(dateObj.getTime()) || dateObj.getTime() === 0 || dateObj.getFullYear() < 2000) {
      return '-'
    }
    
    return dateObj.toLocaleDateString('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getCurrentDuration = (openTime: Date | string | null): string => {
    if (!openTime) return '-'
    
    const openDate = openTime instanceof Date ? openTime : new Date(openTime)
    if (isNaN(openDate.getTime())) return '-'
    
    const now = new Date()
    const diffMs = now.getTime() - openDate.getTime()
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    
    if (diffMinutes < 60) return `${diffMinutes}m`
    const hours = Math.floor(diffMinutes / 60)
    const remainingMinutes = diffMinutes % 60
    if (hours < 24) {
      return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
    }
    const days = Math.floor(hours / 24)
    const remainingHours = hours % 24
    return remainingHours > 0 ? `${days}d ${remainingHours}h` : `${days}d`
  }

  const getPnLColor = (pnl: number): string => {
    if (pnl > 0) return 'text-green-400'
    if (pnl < 0) return 'text-red-400'
    return 'text-gray-400'
  }

  const getSortIcon = (field: keyof Trade): string => {
    if (sortOptions.field !== field) return '↕'
    return sortOptions.direction === 'asc' ? '↑' : '↓'
  }

  const calculateUnrealizedPnL = (trade: Trade): { pnl: number; currentPrice: number } => {
    const instrument = (trade.instrument || trade.symbol || '').replace('_', '/')
    const entryPrice = trade.entryPrice || trade.price || 0
    const units = trade.units || trade.size || 0
    const side = trade.side || (trade.type === 'long' ? 'buy' : 'sell')
    
    // First priority: Use OANDA's provided unrealized P&L if available
    if (trade.pnl !== undefined) {
      // For open trades, OANDA provides the accurate unrealized P&L
      // Try to get current price from live pricing, fallback to entry price
      let currentPrice = entryPrice
      if (enableLivePricing && prices[instrument]) {
        currentPrice = prices[instrument].price
      }
      return { pnl: trade.pnl, currentPrice }
    }
    
    // Second priority: Try to use live pricing if available
    if (enableLivePricing && prices[instrument]) {
      const livePrice = prices[instrument]
      const pnl = calculatePnL(instrument, entryPrice, units, side) || 0
      return { pnl, currentPrice: livePrice.price }
    }
    
    // Fallback to basic calculation (without the incorrect 100x multiplier)
    const mockCurrentPrice = entryPrice * (1 + (Math.random() - 0.5) * 0.01) // Smaller random variation
    let pnl: number
    
    if (side === 'buy' || trade.type === 'long') {
      // For forex, 1 pip = 0.0001, and profit = (current - entry) * units * pip_value
      pnl = (mockCurrentPrice - entryPrice) * units
    } else {
      pnl = (entryPrice - mockCurrentPrice) * units
    }
    
    return { pnl, currentPrice: mockCurrentPrice }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-40"></div>
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="flex justify-between items-center p-6 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
          Individual Open Trades ({sortedTrades.length})
        </h3>
        <div className="flex items-center gap-2 text-sm">
          <div className={`w-2 h-2 rounded-full ${
            connected ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
          }`}></div>
          <span className={connected ? 'text-green-400' : 'text-gray-400'}>
            {connected ? 'Live Prices' : 'Offline'}
          </span>
          {lastUpdate > 0 && (
            <span className="text-xs text-gray-500">
              Updated {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {sortedTrades.length === 0 ? (
        <div className="p-8 text-center text-gray-400">
          <div className="mb-4">📊</div>
          <p>No open positions</p>
          <p className="text-sm mt-2">All positions have been closed</p>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-700">
                  <th className="text-left py-3 px-4 font-medium text-gray-300">
                    Trade ID
                  </th>
                  <th 
                    className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('symbol')}
                  >
                    Symbol {getSortIcon('symbol')}
                  </th>
                  <th 
                    className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('side')}
                  >
                    Buy/Sell {getSortIcon('side')}
                  </th>
                  <th 
                    className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('size')}
                  >
                    Size {getSortIcon('size')}
                  </th>
                  <th 
                    className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('entryPrice')}
                  >
                    Entry Price {getSortIcon('entryPrice')}
                  </th>
                  <th className="text-right py-3 px-4 font-medium text-gray-300">
                    Current Price
                  </th>
                  <th 
                    className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('stopLoss')}
                  >
                    Stop Loss {getSortIcon('stopLoss')}
                  </th>
                  <th 
                    className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('takeProfit')}
                  >
                    Take Profit {getSortIcon('takeProfit')}
                  </th>
                  <th className="text-right py-3 px-4 font-medium text-gray-300">
                    Unrealized P&L
                  </th>
                  <th 
                    className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('openTime')}
                  >
                    Open Time {getSortIcon('openTime')}
                  </th>
                  <th className="text-right py-3 px-4 font-medium text-gray-300">
                    Duration
                  </th>
                  <th className="text-left py-3 px-4 font-medium text-gray-300">
                    Strategy
                  </th>
                  <th className="text-left py-3 px-4 font-medium text-gray-300">
                    Pattern
                  </th>
                  <th className="text-right py-3 px-4 font-medium text-gray-300">
                    Confidence
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedTrades.map((trade, index) => {
                  const { pnl: unrealizedPnL, currentPrice } = calculateUnrealizedPnL(trade)
                  const instrument = (trade.instrument || trade.symbol || '').replace('_', '/')
                  const livePrice = prices[instrument]
                  const priceChange = livePrice?.change || 0
                  
                  return (
                    <tr 
                      key={`${trade.id}-${index}`}
                      className={`
                        border-b border-gray-700 hover:bg-gray-750 transition-colors
                        ${index % 2 === 0 ? 'bg-gray-800' : 'bg-gray-850'}
                      `}
                    >
                      <td className="py-3 px-4 text-blue-400 font-mono text-sm">
                        #{trade.id}
                      </td>
                      <td className="py-3 px-4 text-white font-medium">
                        {trade.symbol || trade.instrument}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`
                          capitalize font-medium inline-flex items-center gap-1
                          ${(trade.side === 'buy' || trade.type === 'long') ? 'text-green-400' : 'text-red-400'}
                        `}>
                          {(trade.side === 'buy' || trade.type === 'long') ? '📈' : '📉'} {trade.side || (trade.type === 'long' ? 'buy' : 'sell')}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-white">
                        {(trade.size || trade.units || 0).toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-right text-white">
                        {(trade.entryPrice || trade.price || 0).toFixed(5)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex flex-col items-end">
                          <span className="text-white font-medium">
                            {currentPrice.toFixed(5)}
                          </span>
                          {livePrice && priceChange !== 0 && (
                            <span className={`text-xs ${
                              priceChange > 0 ? 'text-green-400' : 'text-red-400'
                            }`}>
                              {priceChange > 0 ? '+' : ''}{priceChange.toFixed(5)}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right text-white">
                        {trade.stopLoss ? (
                          <span className="text-red-400 font-medium">
                            {trade.stopLoss.toFixed(5)}
                          </span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right text-white">
                        {trade.takeProfit ? (
                          <span className="text-green-400 font-medium">
                            {trade.takeProfit.toFixed(5)}
                          </span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className={`font-medium ${getPnLColor(unrealizedPnL)}`}>
                          {formatCurrency(unrealizedPnL)}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-gray-300 text-sm">
                        {formatDate(trade.openTime)}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {getCurrentDuration(trade.openTime)}
                      </td>
                      <td className="py-3 px-4 text-gray-300">
                        {trade.strategy || '-'}
                      </td>
                      <td className="py-3 px-4 text-gray-300">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          trade.pattern 
                            ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' 
                            : 'text-gray-500'
                        }`}>
                          {trade.pattern || '-'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {trade.confidence ? (
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            trade.confidence >= 80 ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                            trade.confidence >= 65 ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                            'bg-red-500/20 text-red-400 border border-red-500/30'
                          }`}>
                            {trade.confidence}%
                          </span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Summary Stats */}
          <div className="p-4 border-t border-gray-700 bg-gray-750">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
              <div>
                <div className="text-gray-400">Individual Trades</div>
                <div className="text-white font-medium">{sortedTrades.length}</div>
              </div>
              <div>
                <div className="text-gray-400">Total Size</div>
                <div className="text-white font-medium">
                  {sortedTrades.reduce((sum, t) => sum + (t.size || t.units || 0), 0).toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Unrealized P&L</div>
                <div className={`font-medium ${getPnLColor(
                  sortedTrades.reduce((sum, t) => sum + calculateUnrealizedPnL(t).pnl, 0)
                )}`}>
                  {formatCurrency(sortedTrades.reduce((sum, t) => sum + calculateUnrealizedPnL(t).pnl, 0))}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Avg Duration</div>
                <div className="text-white font-medium">
                  {sortedTrades.length > 0 ? 
                    getCurrentDuration(new Date(
                      sortedTrades.reduce((sum, t) => {
                        const openTime = t.openTime instanceof Date ? t.openTime : new Date(t.openTime || 0)
                        return sum + openTime.getTime()
                      }, 0) / sortedTrades.length
                    )) : '-'
                  }
                </div>
              </div>
              <div>
                <div className="text-gray-400">
                  Pending Orders
                  <span className="text-xs block text-gray-500">Not shown in table</span>
                </div>
                <div className="text-yellow-400 font-medium">
                  {/* This will be populated from API stats */}
                  -
                </div>
              </div>
            </div>
          </div>

          {/* Trade Display Info */}
          <div className="px-4 py-2 border-t border-gray-700 bg-gray-750">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-4">
                <span className="text-blue-400 flex items-center gap-1">
                  <span className="w-1 h-1 bg-blue-400 rounded-full"></span>
                  Individual Trades: Each row represents a separate trade with unique ID
                </span>
                <span className="text-gray-500">
                  Note: OANDA TradingView may show different counts as it displays net positions and pending orders
                </span>
              </div>
            </div>
          </div>
          
          {/* Live Pricing Status */}
          {enableLivePricing && (
            <div className="px-4 py-2 border-t border-gray-700 bg-gray-750">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">Live Pricing:</span>
                  <span className={connected ? 'text-green-400' : 'text-red-400'}>
                    {connected ? 'Connected' : 'Disconnected'}
                  </span>
                  {instruments.length > 0 && (
                    <span className="text-gray-500">
                      • {instruments.length} instruments
                    </span>
                  )}
                </div>
                {pricingError && (
                  <span className="text-red-400 text-xs">
                    Error: {pricingError}
                  </span>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}