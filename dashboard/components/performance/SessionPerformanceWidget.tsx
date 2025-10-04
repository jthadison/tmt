/**
 * Session Performance Widget Component
 * Main widget displaying session-based P&L breakdown with date filtering
 */

'use client'

import React, { useState, useMemo } from 'react'
import { DateRange, DateRangePreset, TradingSession } from '@/types/session'
import { useSessionPerformance } from '@/hooks/useSessionPerformance'
import SessionRow from './SessionRow'
import SessionDetailModal from './SessionDetailModal'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { startOfDay, endOfDay, startOfWeek, startOfMonth, format } from 'date-fns'

/**
 * Date range filter component
 */
function DateRangeFilter({
  value,
  onChange
}: {
  value: DateRange
  onChange: (range: DateRange) => void
}) {
  const [activePreset, setActivePreset] = useState<DateRangePreset>('today')
  const [showCustomPicker, setShowCustomPicker] = useState(false)

  const handlePresetChange = (preset: DateRangePreset) => {
    setActivePreset(preset)
    setShowCustomPicker(false)

    const now = new Date()

    switch (preset) {
      case 'today':
        onChange({
          start: startOfDay(now),
          end: endOfDay(now)
        })
        break
      case 'week':
        onChange({
          start: startOfWeek(now),
          end: endOfDay(now)
        })
        break
      case 'month':
        onChange({
          start: startOfMonth(now),
          end: endOfDay(now)
        })
        break
      case 'custom':
        setShowCustomPicker(true)
        break
    }
  }

  return (
    <div className="flex items-center space-x-2">
      <button
        onClick={() => handlePresetChange('today')}
        className={`px-3 py-1 rounded text-sm transition-colors ${
          activePreset === 'today'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        Today
      </button>
      <button
        onClick={() => handlePresetChange('week')}
        className={`px-3 py-1 rounded text-sm transition-colors ${
          activePreset === 'week'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        This Week
      </button>
      <button
        onClick={() => handlePresetChange('month')}
        className={`px-3 py-1 rounded text-sm transition-colors ${
          activePreset === 'month'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        This Month
      </button>
      <button
        onClick={() => handlePresetChange('custom')}
        className={`px-3 py-1 rounded text-sm transition-colors ${
          activePreset === 'custom'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        Custom
      </button>

      {showCustomPicker && (
        <div className="flex items-center space-x-2 ml-4">
          <input
            type="date"
            value={format(value.start, 'yyyy-MM-dd')}
            onChange={(e) => onChange({ ...value, start: new Date(e.target.value) })}
            className="px-2 py-1 bg-gray-700 text-white text-sm rounded border border-gray-600"
          />
          <span className="text-gray-400">to</span>
          <input
            type="date"
            value={format(value.end, 'yyyy-MM-dd')}
            onChange={(e) => onChange({ ...value, end: new Date(e.target.value) })}
            className="px-2 py-1 bg-gray-700 text-white text-sm rounded border border-gray-600"
          />
        </div>
      )}
    </div>
  )
}

/**
 * Export sessions to CSV
 */
function exportSessionsToCSV(sessions: any[], dateRange: DateRange) {
  const headers = ['Session', 'Total P&L', 'Trade Count', 'Win Rate (%)', 'Confidence Threshold (%)']
  const rows = sessions.map(s => [
    s.session,
    s.totalPnL.toFixed(2),
    s.tradeCount,
    s.winRate.toFixed(2),
    s.confidenceThreshold
  ])

  const csv = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')

  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `session_performance_${format(dateRange.start, 'yyyy-MM-dd')}_to_${format(dateRange.end, 'yyyy-MM-dd')}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Session performance widget
 */
export function SessionPerformanceWidget() {
  const [dateRange, setDateRange] = useState<DateRange>({
    start: startOfDay(new Date()),
    end: endOfDay(new Date())
  })

  const [selectedSession, setSelectedSession] = useState<TradingSession | null>(null)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)

  const { sessions, isLoading, error } = useSessionPerformance({ dateRange })

  // Calculate max P&L for bar scaling
  const maxPnL = useMemo(() => {
    if (sessions.length === 0) return 1
    return Math.max(...sessions.map(s => Math.abs(s.totalPnL)), 1)
  }, [sessions])

  const handleSessionClick = (session: TradingSession) => {
    setSelectedSession(session)
    setIsDetailModalOpen(true)
  }

  const handleExportCSV = () => {
    exportSessionsToCSV(sessions, dateRange)
  }

  return (
    <section className="bg-gray-800 rounded-lg p-6 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Session Performance</h2>
        <div className="flex items-center space-x-4">
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
          <button
            onClick={handleExportCSV}
            disabled={sessions.length === 0}
            className="px-3 py-1 text-sm text-blue-400 hover:text-blue-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Export session data as CSV"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <LoadingSkeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      ) : (
        <>
          {/* Session Rows */}
          {sessions.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              No session data available for selected date range
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.map(session => (
                <SessionRow
                  key={session.session}
                  session={session}
                  maxPnL={maxPnL}
                  isActive={session.isActive}
                  onClick={() => handleSessionClick(session.session)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Detail Modal */}
      <SessionDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        session={selectedSession}
        startDate={dateRange.start}
        endDate={dateRange.end}
      />
    </section>
  )
}

export default SessionPerformanceWidget
