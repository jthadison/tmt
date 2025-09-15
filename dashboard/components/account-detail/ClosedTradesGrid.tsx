'use client'

import { useState, useMemo } from 'react'
import { Trade, TradeSortOptions, TradeHistoryFilters } from '@/types/accountDetail'

interface ClosedTradesGridProps {
  trades: Trade[]
  loading?: boolean
  itemsPerPage?: number
}

export function ClosedTradesGrid({ trades, loading = false, itemsPerPage = 25 }: ClosedTradesGridProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [filters, setFilters] = useState<TradeHistoryFilters>({})
  const [sortOptions, setSortOptions] = useState<TradeSortOptions>({
    field: 'closeTime',
    direction: 'desc'
  })
  const [showFilters, setShowFilters] = useState(false)

  // Filter only closed trades
  const closedTrades = useMemo(() => {
    return trades.filter(trade => trade.status === 'closed' || !trade.status || trade.closeTime)
  }, [trades])

  // Apply additional filters
  const filteredTrades = useMemo(() => {
    return closedTrades.filter(trade => {
      const tradeSymbol = trade.symbol || trade.instrument || ''
      if (filters.symbol && !tradeSymbol.toLowerCase().includes(filters.symbol.toLowerCase())) {
        return false
      }
      if (filters.type && (trade.side || (trade.type === 'long' ? 'buy' : 'sell')) !== filters.type) {
        return false
      }
      if (filters.strategy && trade.strategy !== filters.strategy) {
        return false
      }
      if (filters.pattern && trade.pattern !== filters.pattern) {
        return false
      }
      if (filters.dateRange) {
        const tradeDate = trade.closeTime instanceof Date ? trade.closeTime : (trade.closeTime ? new Date(trade.closeTime) : null)
        if (!tradeDate || tradeDate < filters.dateRange.start || tradeDate > filters.dateRange.end) {
          return false
        }
      }
      if (filters.pnlRange) {
        if (trade.pnl < filters.pnlRange.min || trade.pnl > filters.pnlRange.max) {
          return false
        }
      }
      return true
    })
  }, [closedTrades, filters])

  // Sort filtered trades
  const sortedTrades = useMemo(() => {
    return [...filteredTrades].sort((a, b) => {
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
        case 'exitPrice':
          aValue = a.exitPrice || 0
          bValue = b.exitPrice || 0
          break
        case 'size':
          aValue = a.units || a.size
          bValue = b.units || b.size
          break
        case 'openTime':
          aValue = a.openTime
          bValue = b.openTime
          break
        case 'closeTime':
          aValue = a.closeTime
          bValue = b.closeTime
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
  }, [filteredTrades, sortOptions])

  // Paginate sorted trades
  const paginatedTrades = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    return sortedTrades.slice(startIndex, startIndex + itemsPerPage)
  }, [sortedTrades, currentPage, itemsPerPage])

  const totalPages = Math.ceil(sortedTrades.length / itemsPerPage)

  const handleSort = (field: keyof Trade) => {
    setSortOptions(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
    setCurrentPage(1)
  }

  const handleFilterChange = (newFilters: Partial<TradeHistoryFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }))
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setFilters({})
    setCurrentPage(1)
  }

  const exportTrades = () => {
    const csvData = sortedTrades.map(trade => ({
      Symbol: trade.symbol || trade.instrument || '',
      BuySell: trade.side || (trade.type === 'long' ? 'buy' : 'sell'),
      Size: trade.size || trade.units || 0,
      EntryPrice: trade.entryPrice || trade.price || 0,
      ExitPrice: trade.exitPrice || 0,
      PnL: trade.pnl,
      Commission: trade.commission,
      OpenTime: trade.openTime ? (trade.openTime instanceof Date ? trade.openTime.toISOString() : new Date(trade.openTime).toISOString()) : '',
      CloseTime: trade.closeTime ? (trade.closeTime instanceof Date ? trade.closeTime.toISOString() : new Date(trade.closeTime).toISOString()) : '',
      Duration: trade.duration || 0,
      Strategy: trade.strategy || '',
      Pattern: trade.pattern || '',
      Confidence: trade.confidence ? `${trade.confidence}%` : ''
    }))
    
    console.log('Exporting closed trades:', csvData)
    // In real implementation, this would trigger a CSV download
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

  const formatDuration = (minutes: number | undefined): string => {
    if (!minutes) return '-'
    if (minutes < 60) return `${minutes}m`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
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

  const getUniqueValues = (field: keyof Trade): string[] => {
    return Array.from(new Set(closedTrades.map(trade => String(trade[field])).filter(Boolean)))
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-40"></div>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 p-6 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
          Trade History ({sortedTrades.length} closed trades)
        </h3>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors"
          >
            🔍 Filters {Object.keys(filters).length > 0 && `(${Object.keys(filters).length})`}
          </button>
          <button
            onClick={exportTrades}
            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm transition-colors"
          >
            📊 Export
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="p-6 border-b border-gray-700 bg-gray-750">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
              <select
                value={filters.symbol || ''}
                onChange={(e) => handleFilterChange({ symbol: e.target.value || undefined })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                <option value="">All Symbols</option>
                {getUniqueValues('symbol').map(symbol => (
                  <option key={symbol} value={symbol}>{symbol}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Buy/Sell</label>
              <select
                value={filters.type || ''}
                onChange={(e) => handleFilterChange({ type: (e.target.value as 'buy' | 'sell' | '') || undefined })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                <option value="">All Types</option>
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Strategy</label>
              <select
                value={filters.strategy || ''}
                onChange={(e) => handleFilterChange({ strategy: e.target.value || undefined })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                <option value="">All Strategies</option>
                {getUniqueValues('strategy').map(strategy => (
                  <option key={strategy} value={strategy}>{strategy}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Pattern</label>
              <select
                value={filters.pattern || ''}
                onChange={(e) => handleFilterChange({ pattern: e.target.value || undefined })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                <option value="">All Patterns</option>
                {getUniqueValues('pattern').map(pattern => (
                  <option key={pattern} value={pattern}>{pattern}</option>
                ))}
              </select>
            </div>
            
            <div className="flex items-end">
              <button
                onClick={clearFilters}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>
      )}

      {closedTrades.length === 0 ? (
        <div className="p-8 text-center text-gray-400">
          <div className="mb-4">📈</div>
          <p>No trade history</p>
          <p className="text-sm mt-2">Closed trades will appear here</p>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-700">
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
                    className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('openTime')}
                  >
                    Entry Date {getSortIcon('openTime')}
                  </th>
                  <th 
                    className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('closeTime')}
                  >
                    Exit Date {getSortIcon('closeTime')}
                  </th>
                  <th 
                    className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('entryPrice')}
                  >
                    Entry Price {getSortIcon('entryPrice')}
                  </th>
                  <th 
                    className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('exitPrice')}
                  >
                    Exit Price {getSortIcon('exitPrice')}
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
                  <th 
                    className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('pnl')}
                  >
                    P&L {getSortIcon('pnl')}
                  </th>
                  <th 
                    className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('duration')}
                  >
                    Duration {getSortIcon('duration')}
                  </th>
                  <th 
                    className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('strategy')}
                  >
                    Strategy {getSortIcon('strategy')}
                  </th>
                  <th 
                    className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                    onClick={() => handleSort('pattern')}
                  >
                    Pattern {getSortIcon('pattern')}
                  </th>
                  <th className="text-right py-3 px-4 font-medium text-gray-300">
                    Confidence
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedTrades.map((trade, index) => (
                  <tr 
                    key={`${trade.id}-${index}-${trade.instrument || trade.symbol}-${trade.openTime}`}
                    className={`
                      border-b border-gray-700 hover:bg-gray-750 transition-colors
                      ${index % 2 === 0 ? 'bg-gray-800' : 'bg-gray-850'}
                    `}
                  >
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
                    <td className="py-3 px-4 text-gray-300 text-sm">
                      {trade.openTime ? formatDate(trade.openTime) : '-'}
                    </td>
                    <td className="py-3 px-4 text-gray-300 text-sm">
                      {trade.closeTime ? formatDate(trade.closeTime) : '-'}
                    </td>
                    <td className="py-3 px-4 text-right text-white">
                      {(trade.entryPrice || trade.price || 0).toFixed(5)}
                    </td>
                    <td className="py-3 px-4 text-right text-white">
                      {trade.exitPrice ? trade.exitPrice.toFixed(5) : '-'}
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
                      <div className={`font-medium ${getPnLColor(trade.pnl)}`}>
                        {formatCurrency(trade.pnl)}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right text-gray-300">
                      {trade.duration ? formatDuration(trade.duration) : '-'}
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
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center p-4 border-t border-gray-700">
              <div className="text-sm text-gray-400">
                Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, sortedTrades.length)} of {sortedTrades.length} trades
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 bg-gray-700 text-white rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-400">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 bg-gray-700 text-white rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {/* Trade Statistics */}
          <div className="p-4 border-t border-gray-700 bg-gray-750">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-gray-400">Closed Trades</div>
                <div className="text-white font-medium">{sortedTrades.length}</div>
              </div>
              <div>
                <div className="text-gray-400">Win Rate</div>
                <div className="text-white font-medium">
                  {sortedTrades.length > 0 
                    ? `${((sortedTrades.filter(t => t.pnl > 0).length / sortedTrades.length) * 100).toFixed(1)}%`
                    : '0%'}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Total P&L</div>
                <div className={`font-medium ${getPnLColor(sortedTrades.reduce((sum, t) => sum + t.pnl, 0))}`}>
                  {formatCurrency(sortedTrades.reduce((sum, t) => sum + t.pnl, 0))}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Avg P&L per Trade</div>
                <div className={`font-medium ${getPnLColor(sortedTrades.reduce((sum, t) => sum + t.pnl, 0) / Math.max(sortedTrades.length, 1))}`}>
                  {formatCurrency(sortedTrades.reduce((sum, t) => sum + t.pnl, 0) / Math.max(sortedTrades.length, 1))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}