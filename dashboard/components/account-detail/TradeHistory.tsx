'use client'

import { useState, useMemo, useEffect } from 'react'
import { Trade, TradeSortOptions, TradeHistoryFilters } from '@/types/accountDetail'
import { tradeHistoryService } from '@/services/tradeHistoryService'

/**
 * Props for TradeHistory component
 */
interface TradeHistoryProps {
  /** Array of completed trades */
  trades?: Trade[]
  /** Account ID for context */
  accountId: string
  /** Loading state indicator */
  loading?: boolean
  /** Items per page for pagination */
  itemsPerPage?: number
  /** Show account column for multi-account view */
  showAccountColumn?: boolean
}

/**
 * Trade history interface with filtering, sorting, and pagination
 * Displays historical trade data with comprehensive filtering options
 */
export function TradeHistory({
  trades: propTrades,
  accountId,
  loading = false,
  itemsPerPage = 25,
  showAccountColumn = false
}: TradeHistoryProps) {
  // Remove unused parameters warning
  void showAccountColumn
  
  const [currentPage, setCurrentPage] = useState(1)
  const [filters, setFilters] = useState<TradeHistoryFilters>({})
  const [sortOptions, setSortOptions] = useState<TradeSortOptions>({
    field: 'closeTime',
    direction: 'desc'
  })
  const [showFilters, setShowFilters] = useState(false)
  const [realTrades, setRealTrades] = useState<Trade[]>([])
  const [tradeStats, setTradeStats] = useState<Record<string, any> | null>(null)
  const [isLoadingReal, setIsLoadingReal] = useState(false)

  // Load real trade data on component mount and when filters change
  useEffect(() => {
    const loadRealTradeData = async () => {
      setIsLoadingReal(true)
      try {
        const response = await tradeHistoryService.getTradeHistory({
          accountId,
          page: currentPage,
          limit: itemsPerPage,
          filter: {
            instrument: filters.symbol,
            status: filters.type === 'long' ? 'buy' : filters.type === 'short' ? 'sell' : undefined,
            type: filters.strategy
          }
        })
        
        // Transform the API response to match our component's Trade interface
        const transformedTrades = response.trades.map((trade: Record<string, any>) => ({
          id: trade.id,
          symbol: trade.instrument || trade.symbol,
          type: trade.side === 'buy' ? 'long' : 'short',
          size: trade.units || trade.size,
          entryPrice: trade.price || trade.entryPrice || trade.openPrice,
          exitPrice: trade.closePrice || trade.exitPrice,
          pnl: trade.pnl || trade.profit,
          commission: trade.commission,
          openTime: new Date(trade.openTime),
          closeTime: trade.closeTime ? new Date(trade.closeTime) : null,
          duration: trade.duration || (trade.closeTime && trade.openTime ? 
            Math.floor((new Date(trade.closeTime).getTime() - new Date(trade.openTime).getTime()) / (1000 * 60)) : 0),
          strategy: trade.strategy || trade.notes || 'Unknown',
          notes: trade.notes || ''
        }))
        
        setRealTrades(transformedTrades)
        setTradeStats(response.stats)
      } catch (error) {
        console.error('Failed to load real trade data:', error)
        // Keep existing mock trades as fallback
      } finally {
        setIsLoadingReal(false)
      }
    }

    loadRealTradeData()
  }, [accountId, currentPage, itemsPerPage, filters])

  // Generate fallback mock trades for demonstration when real data isn't available
  const mockTrades: Trade[] = useMemo(() => {
    const symbols = ['EUR/USD', 'GBP/JPY', 'XAU/USD', 'USD/JPY', 'AUD/USD', 'GBP/USD', 'USD/CAD']
    const strategies = ['Breakout', 'Reversal', 'Trend Following', 'Scalping', 'News Trading']
    
    return Array.from({ length: 10 }, (_, i) => {
      const isWin = Math.random() > 0.35 // 65% win rate
      const symbol = symbols[i % symbols.length]
      const type = Math.random() > 0.5 ? 'long' : 'short'
      const size = Math.random() * 2 + 0.1
      const entryPrice = 1 + Math.random() * 100
      const priceMove = (Math.random() * 0.01 - 0.005) * entryPrice
      const exitPrice = entryPrice + (isWin ? Math.abs(priceMove) : -Math.abs(priceMove))
      const pnl = (exitPrice - entryPrice) * size * (type === 'long' ? 1 : -1) * 10000
      const duration = Math.floor(Math.random() * 1440) // Up to 24 hours
      const openTime = new Date(Date.now() - (i + 1) * 24 * 60 * 60 * 1000 - Math.random() * 24 * 60 * 60 * 1000)
      
      return {
        id: `fallback-${i + 1}`,
        symbol,
        type,
        size,
        entryPrice,
        exitPrice,
        pnl,
        commission: Math.random() * 20 + 5,
        openTime,
        closeTime: new Date(openTime.getTime() + duration * 60 * 1000),
        duration,
        strategy: strategies[Math.floor(Math.random() * strategies.length)],
        notes: isWin ? 'Good entry timing' : 'Stop loss hit'
      }
    })
  }, [])

  // Use real trades if available, otherwise combine provided trades with fallback mock data
  const allTrades = useMemo(() => {
    if (realTrades.length > 0) {
      return [...(propTrades || []), ...realTrades]
    }
    return [...(propTrades || []), ...mockTrades]
  }, [propTrades, realTrades, mockTrades])

  // Filter trades based on current filters
  const filteredTrades = useMemo(() => {
    return allTrades.filter(trade => {
      if (filters.symbol && !trade.symbol.toLowerCase().includes(filters.symbol.toLowerCase())) {
        return false
      }
      if (filters.type && trade.type !== filters.type) {
        return false
      }
      if (filters.strategy && trade.strategy !== filters.strategy) {
        return false
      }
      if (filters.dateRange) {
        const tradeDate = trade.closeTime
        if (tradeDate < filters.dateRange.start || tradeDate > filters.dateRange.end) {
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
  }, [allTrades, filters])

  // Sort filtered trades
  const sortedTrades = useMemo(() => {
    return [...filteredTrades].sort((a, b) => {
      const { field, direction } = sortOptions
      const aValue = a[field]
      const bValue = b[field]

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
    // Mock export functionality
    const csvData = sortedTrades.map(trade => ({
      Symbol: trade.symbol,
      Type: trade.type,
      Size: trade.size,
      EntryPrice: trade.entryPrice,
      ExitPrice: trade.exitPrice,
      PnL: trade.pnl,
      Commission: trade.commission,
      OpenTime: trade.openTime.toISOString(),
      CloseTime: trade.closeTime.toISOString(),
      Duration: trade.duration,
      Strategy: trade.strategy || ''
    }))
    
    console.log('Exporting trades:', csvData)
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
    if (!date) return 'Open'
    
    const dateObj = date instanceof Date ? date : new Date(date)
    
    if (isNaN(dateObj.getTime())) {
      return 'Invalid Date'
    }
    
    return dateObj.toLocaleDateString('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (minutes: number): string => {
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
    return Array.from(new Set(allTrades.map(trade => String(trade[field])).filter(Boolean)))
  }

  if (loading || isLoadingReal) {
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
        <h3 className="text-lg font-semibold text-white">
          Trade History ({sortedTrades.length} trades)
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
              <label className="block text-sm font-medium text-gray-300 mb-2">Type</label>
              <select
                value={filters.type || ''}
                onChange={(e) => handleFilterChange({ type: (e.target.value as 'long' | 'short') || undefined })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                <option value="">All Types</option>
                <option value="long">Long</option>
                <option value="short">Short</option>
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

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-700">
              <th 
                className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                onClick={() => handleSort('closeTime')}
              >
                Date {getSortIcon('closeTime')}
              </th>
              <th 
                className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                onClick={() => handleSort('symbol')}
              >
                Symbol {getSortIcon('symbol')}
              </th>
              <th 
                className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                onClick={() => handleSort('type')}
              >
                Type {getSortIcon('type')}
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
                Entry {getSortIcon('entryPrice')}
              </th>
              <th 
                className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                onClick={() => handleSort('exitPrice')}
              >
                Exit {getSortIcon('exitPrice')}
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
            </tr>
          </thead>
          <tbody>
            {paginatedTrades.map((trade, index) => (
              <tr 
                key={trade.id}
                className={`
                  border-b border-gray-700 hover:bg-gray-750 transition-colors
                  ${index % 2 === 0 ? 'bg-gray-800' : 'bg-gray-850'}
                `}
              >
                <td className="py-3 px-4 text-gray-300 text-sm">
                  {formatDate(trade.closeTime)}
                </td>
                <td className="py-3 px-4 text-white font-medium">
                  {trade.symbol || trade.instrument}
                </td>
                <td className="py-3 px-4">
                  <span className={`
                    capitalize font-medium
                    ${trade.type === 'long' ? 'text-green-400' : 'text-red-400'}
                  `}>
                    {trade.type}
                  </span>
                </td>
                <td className="py-3 px-4 text-right text-white">
                  {(trade.size || trade.units || 0).toFixed(2)}
                </td>
                <td className="py-3 px-4 text-right text-white">
                  {(trade.entryPrice || trade.price || 0).toFixed(5)}
                </td>
                <td className="py-3 px-4 text-right text-white">
                  {trade.exitPrice ? trade.exitPrice.toFixed(5) : '-'}
                </td>
                <td className="py-3 px-4 text-right">
                  <div className={`font-medium ${getPnLColor(trade.pnl)}`}>
                    {formatCurrency(trade.pnl)}
                  </div>
                </td>
                <td className="py-3 px-4 text-right text-gray-300">
                  {formatDuration(trade.duration)}
                </td>
                <td className="py-3 px-4 text-gray-300">
                  {trade.strategy || '-'}
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
            <div className="text-gray-400">Total Trades</div>
            <div className="text-white font-medium">
              {tradeStats ? tradeStats.totalTrades : sortedTrades.length}
            </div>
          </div>
          <div>
            <div className="text-gray-400">Win Rate</div>
            <div className="text-white font-medium">
              {tradeStats 
                ? `${tradeStats.winRate.toFixed(1)}%`
                : sortedTrades.length > 0 
                  ? `${((sortedTrades.filter(t => t.pnl > 0).length / sortedTrades.length) * 100).toFixed(1)}%`
                  : '0%'}
            </div>
          </div>
          <div>
            <div className="text-gray-400">Total P&L</div>
            <div className={`font-medium ${getPnLColor(tradeStats ? tradeStats.totalPnL : sortedTrades.reduce((sum, t) => sum + t.pnl, 0))}`}>
              {formatCurrency(tradeStats ? tradeStats.totalPnL : sortedTrades.reduce((sum, t) => sum + t.pnl, 0))}
            </div>
          </div>
          <div>
            <div className="text-gray-400">Avg P&L</div>
            <div className={`font-medium ${getPnLColor(tradeStats ? (tradeStats.totalPnL / Math.max(tradeStats.totalTrades, 1)) : (sortedTrades.reduce((sum, t) => sum + t.pnl, 0) / Math.max(sortedTrades.length, 1)))}`}>
              {formatCurrency(tradeStats ? (tradeStats.totalPnL / Math.max(tradeStats.totalTrades, 1)) : (sortedTrades.reduce((sum, t) => sum + t.pnl, 0) / Math.max(sortedTrades.length, 1)))}
            </div>
          </div>
        </div>
        {realTrades.length > 0 && (
          <div className="mt-4 text-xs text-green-400 flex items-center">
            <span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-2"></span>
            Connected to live trading system - Showing real trade data
          </div>
        )}
      </div>
    </div>
  )
}