/**
 * Session Detail Modal Component
 * Displays detailed trade information for a specific trading session
 */

'use client'

import React, { useState, useEffect, useMemo } from 'react'
import Modal from '@/components/ui/Modal'
import { TradingSession, SessionTrade, SESSION_CONFIG } from '@/types/session'
import { formatCurrency } from '@/utils/formatCurrency'
import { cn } from '@/lib/utils'

interface SessionDetailModalProps {
  /** Is modal open */
  isOpen: boolean
  /** Close handler */
  onClose: () => void
  /** Selected session */
  session: TradingSession | null
  /** Date range for filtering trades */
  startDate: Date
  /** Date range for filtering trades */
  endDate: Date
}

type SortColumn = 'timestamp' | 'pnl' | 'duration' | 'instrument'
type SortDirection = 'asc' | 'desc'

/**
 * Session detail modal displaying trades for selected session
 */
export function SessionDetailModal({
  isOpen,
  onClose,
  session,
  startDate,
  endDate
}: SessionDetailModalProps) {
  const [trades, setTrades] = useState<SessionTrade[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sortColumn, setSortColumn] = useState<SortColumn>('timestamp')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const config = session ? SESSION_CONFIG[session] : null

  /**
   * Fetch trades for selected session
   */
  useEffect(() => {
    if (!isOpen || !session) return

    const fetchTrades = async () => {
      try {
        setIsLoading(true)

        const params = new URLSearchParams({
          session,
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString()
        })

        const response = await fetch(`http://localhost:8089/api/performance/session-trades?${params}`)

        if (!response.ok) {
          throw new Error('Failed to fetch session trades')
        }

        const data = await response.json()

        const mappedTrades: SessionTrade[] = data.trades.map((t: any) => ({
          id: t.id,
          timestamp: new Date(t.timestamp),
          instrument: t.instrument,
          direction: t.direction,
          pnL: t.pnl || t.pnL,
          duration: t.duration
        }))

        setTrades(mappedTrades)
      } catch (error) {
        console.error('Error fetching session trades:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchTrades()
  }, [isOpen, session, startDate, endDate])

  /**
   * Calculate summary statistics
   */
  const stats = useMemo(() => {
    if (trades.length === 0) {
      return {
        totalPnL: 0,
        winRate: 0,
        avgTrade: 0,
        totalTrades: 0
      }
    }

    const totalPnL = trades.reduce((sum, t) => sum + t.pnL, 0)
    const winningTrades = trades.filter(t => t.pnL > 0).length
    const winRate = (winningTrades / trades.length) * 100
    const avgTrade = totalPnL / trades.length

    return {
      totalPnL,
      winRate,
      avgTrade,
      totalTrades: trades.length
    }
  }, [trades])

  /**
   * Sort trades
   */
  const sortedTrades = useMemo(() => {
    const sorted = [...trades]

    sorted.sort((a, b) => {
      let comparison = 0

      switch (sortColumn) {
        case 'timestamp':
          comparison = a.timestamp.getTime() - b.timestamp.getTime()
          break
        case 'pnl':
          comparison = a.pnL - b.pnL
          break
        case 'duration':
          comparison = a.duration - b.duration
          break
        case 'instrument':
          comparison = a.instrument.localeCompare(b.instrument)
          break
      }

      return sortDirection === 'asc' ? comparison : -comparison
    })

    return sorted
  }, [trades, sortColumn, sortDirection])

  /**
   * Handle column sort
   */
  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  /**
   * Format duration (seconds to human-readable)
   */
  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  /**
   * Sort indicator component
   */
  const SortIndicator = ({ column }: { column: SortColumn }) => {
    if (sortColumn !== column) return null

    return (
      <span className="ml-1">
        {sortDirection === 'asc' ? '↑' : '↓'}
      </span>
    )
  }

  if (!session || !config) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${config.name} Session Trades`}
      size="xl"
    >
      <div className="space-y-4">
        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4 p-4 bg-gray-800 rounded-lg">
          <div>
            <div className="text-sm text-gray-400">Total P&L</div>
            <div className={cn(
              'text-xl font-bold',
              stats.totalPnL > 0 ? 'text-green-400' : 'text-red-400'
            )}>
              {formatCurrency(stats.totalPnL)}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Win Rate</div>
            <div className="text-xl font-bold text-white">
              {stats.winRate.toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Avg Trade</div>
            <div className={cn(
              'text-xl font-bold',
              stats.avgTrade > 0 ? 'text-green-400' : 'text-red-400'
            )}>
              {formatCurrency(stats.avgTrade)}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Total Trades</div>
            <div className="text-xl font-bold text-white">
              {stats.totalTrades}
            </div>
          </div>
        </div>

        {/* Trades Table */}
        {isLoading ? (
          <div className="text-center text-gray-400 py-8">Loading trades...</div>
        ) : trades.length === 0 ? (
          <div className="text-center text-gray-400 py-8">No trades found for this session</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800">
                <tr>
                  <th
                    className="px-4 py-3 text-left text-sm font-semibold text-gray-300 cursor-pointer hover:text-white"
                    onClick={() => handleSort('timestamp')}
                  >
                    Timestamp <SortIndicator column="timestamp" />
                  </th>
                  <th
                    className="px-4 py-3 text-left text-sm font-semibold text-gray-300 cursor-pointer hover:text-white"
                    onClick={() => handleSort('instrument')}
                  >
                    Instrument <SortIndicator column="instrument" />
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">
                    Direction
                  </th>
                  <th
                    className="px-4 py-3 text-right text-sm font-semibold text-gray-300 cursor-pointer hover:text-white"
                    onClick={() => handleSort('pnl')}
                  >
                    P&L <SortIndicator column="pnl" />
                  </th>
                  <th
                    className="px-4 py-3 text-right text-sm font-semibold text-gray-300 cursor-pointer hover:text-white"
                    onClick={() => handleSort('duration')}
                  >
                    Duration <SortIndicator column="duration" />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {sortedTrades.map((trade) => (
                  <tr key={trade.id} className="hover:bg-gray-800/50">
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {trade.timestamp.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-white">
                      {trade.instrument}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={cn(
                        'px-2 py-1 rounded text-xs font-semibold',
                        trade.direction === 'long'
                          ? 'bg-blue-500/10 text-blue-400'
                          : 'bg-orange-500/10 text-orange-400'
                      )}>
                        {trade.direction.toUpperCase()}
                      </span>
                    </td>
                    <td className={cn(
                      'px-4 py-3 text-sm font-bold text-right',
                      trade.pnL > 0 ? 'text-green-400' : 'text-red-400'
                    )}>
                      {formatCurrency(trade.pnL)}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400 text-right">
                      {formatDuration(trade.duration)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Modal>
  )
}

export default SessionDetailModal
