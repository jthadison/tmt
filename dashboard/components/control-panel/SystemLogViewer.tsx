'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
import { SystemLogEntry, LogFilter, LogLevel } from '@/types/systemControl'

/**
 * Props for SystemLogViewer component
 */
interface SystemLogViewerProps {
  /** Array of system log entries */
  logEntries: SystemLogEntry[]
  /** Callback when log export is requested */
  onExportLogs?: (filter: LogFilter) => void
  /** Enable real-time updates */
  realTimeUpdates?: boolean
  /** Loading state indicator */
  loading?: boolean
}

/**
 * System log viewer with real-time updates, filtering, and export capabilities
 * Provides comprehensive log monitoring with search and filtering functionality
 */
export function SystemLogViewer({
  logEntries,
  onExportLogs,
  realTimeUpdates = true,
  loading = false
}: SystemLogViewerProps) {
  const [filter, setFilter] = useState<LogFilter>({
    level: undefined,
    component: undefined,
    accountId: undefined,
    timeRange: undefined,
    searchQuery: ''
  })
  const [autoScroll, setAutoScroll] = useState(true)
  const [selectedEntry, setSelectedEntry] = useState<SystemLogEntry | null>(null)
  const [showExportDialog, setShowExportDialog] = useState(false)
  const logContainerRef = useRef<HTMLDivElement>(null)

  // Severity options with colors and descriptions
  const severityOptions: { value: LogLevel; label: string; color: string; description: string }[] = [
    { value: 'debug', label: 'Debug', color: 'text-gray-400', description: 'Detailed diagnostic information' },
    { value: 'info', label: 'Info', color: 'text-blue-400', description: 'General information messages' },
    { value: 'warn', label: 'Warning', color: 'text-yellow-400', description: 'Warning conditions' },
    { value: 'error', label: 'Error', color: 'text-red-400', description: 'Error conditions' },
    { value: 'critical', label: 'Critical', color: 'text-red-500', description: 'Critical failures' }
  ]

  // Get unique components from log entries
  const availableComponents = useMemo(() => {
    const components = new Set(logEntries.map(entry => entry.component))
    return Array.from(components).sort()
  }, [logEntries])

  // Get unique account IDs from log entries
  const availableAccounts = useMemo(() => {
    const accounts = new Set(
      logEntries
        .map(entry => entry.accountId)
        .filter((id): id is string => id !== undefined)
    )
    return Array.from(accounts).sort()
  }, [logEntries])

  // Filter log entries based on current filters
  const filteredLogs = useMemo(() => {
    let filtered = [...logEntries]

    // Filter by log level
    if (filter.level && filter.level.length > 0) {
      filtered = filtered.filter(entry => filter.level!.includes(entry.level))
    }

    // Filter by component
    if (filter.component && filter.component.length > 0) {
      filtered = filtered.filter(entry => filter.component!.includes(entry.component))
    }

    // Filter by account
    if (filter.accountId) {
      filtered = filtered.filter(entry => entry.accountId === filter.accountId)
    }

    // Filter by time range
    if (filter.timeRange?.start) {
      filtered = filtered.filter(entry => entry.timestamp >= filter.timeRange!.start!)
    }
    if (filter.timeRange?.end) {
      filtered = filtered.filter(entry => entry.timestamp <= filter.timeRange!.end!)
    }

    // Filter by search query
    if (filter.searchQuery?.trim()) {
      const query = filter.searchQuery.toLowerCase()
      filtered = filtered.filter(entry =>
        entry.message.toLowerCase().includes(query) ||
        entry.component.toLowerCase().includes(query) ||
        entry.accountId?.toLowerCase().includes(query)
      )
    }

    // Sort by timestamp (newest first)
    return filtered.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  }, [logEntries, filter])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [filteredLogs, autoScroll])

  const getSeverityColor = (level: LogLevel): string => {
    return severityOptions.find(opt => opt.value === level)?.color || 'text-gray-400'
  }

  const getSeverityIcon = (level: LogLevel): string => {
    switch (level) {
      case 'debug': return '🔍'
      case 'info': return 'ℹ️'
      case 'warn': return '⚠️'
      case 'error': return '❌'
      case 'critical': return '🚨'
      default: return '📝'
    }
  }

  const formatTimestamp = (timestamp: Date): string => {
    return timestamp.toLocaleString([], {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    })
  }

  const formatRelativeTime = (timestamp: Date): string => {
    const diff = Date.now() - timestamp.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    if (seconds > 0) return `${seconds}s ago`
    return 'Now'
  }

  const clearFilters = () => {
    setFilter({
      level: undefined,
      component: undefined,
      accountId: undefined,
      timeRange: undefined,
      searchQuery: ''
    })
  }

  const handleExport = () => {
    if (onExportLogs) {
      onExportLogs(filter)
    }
    setShowExportDialog(false)
  }

  const getLogCounts = () => {
    const counts = {
      debug: 0,
      info: 0,
      warn: 0,
      error: 0,
      critical: 0
    }

    filteredLogs.forEach(entry => {
      counts[entry.level]++
    })

    return counts
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-32"></div>
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-gray-800 rounded-lg p-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6">
          <h3 className="text-lg font-semibold text-white">System Logs</h3>
          <div className="flex items-center gap-3">
            <div className="text-sm text-gray-400">
              {filteredLogs.length} of {logEntries.length} entries
            </div>
            {realTimeUpdates && (
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-green-400 text-sm">Live</span>
              </div>
            )}
            <button
              onClick={() => setShowExportDialog(true)}
              disabled={!onExportLogs || filteredLogs.length === 0}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-3 py-2 rounded text-sm transition-colors"
            >
              📥 Export
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="block text-gray-300 text-sm mb-2">Level</label>
            <select
              value={filter.level?.[0] || ''}
              onChange={(e) => setFilter(prev => ({ ...prev, level: e.target.value ? [e.target.value as LogLevel] : undefined }))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="">All Levels</option>
              {severityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-gray-300 text-sm mb-2">Component</label>
            <select
              value={filter.component?.[0] || ''}
              onChange={(e) => setFilter(prev => ({ ...prev, component: e.target.value ? [e.target.value] : undefined }))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="">All Components</option>
              {availableComponents.map((component) => (
                <option key={component} value={component}>
                  {component}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-gray-300 text-sm mb-2">Account</label>
            <select
              value={filter.accountId || ''}
              onChange={(e) => setFilter(prev => ({ ...prev, accountId: e.target.value || undefined }))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="">All Accounts</option>
              {availableAccounts.map((account) => (
                <option key={account} value={account}>
                  {account}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-gray-300 text-sm mb-2">Search</label>
            <input
              type="text"
              value={filter.searchQuery || ''}
              onChange={(e) => setFilter(prev => ({ ...prev, searchQuery: e.target.value }))}
              placeholder="Search logs..."
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        {/* Time Range Filter */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-gray-300 text-sm mb-2">Start Time</label>
            <input
              type="datetime-local"
              value={filter.timeRange?.start?.toISOString().slice(0, 16) || ''}
              onChange={(e) => setFilter(prev => ({
                ...prev,
                timeRange: e.target.value ? {
                  start: new Date(e.target.value),
                  end: prev.timeRange?.end || new Date()
                } : undefined
              }))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>

          <div>
            <label className="block text-gray-300 text-sm mb-2">End Time</label>
            <input
              type="datetime-local"
              value={filter.timeRange?.end?.toISOString().slice(0, 16) || ''}
              onChange={(e) => setFilter(prev => ({
                ...prev,
                timeRange: e.target.value ? {
                  start: prev.timeRange?.start || new Date(),
                  end: new Date(e.target.value)
                } : undefined
              }))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>

          <div className="flex items-end gap-2">
            <button
              onClick={clearFilters}
              className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors"
            >
              Clear Filters
            </button>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="auto-scroll"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-gray-600 bg-gray-700 text-blue-600"
              />
              <label htmlFor="auto-scroll" className="text-gray-300 text-sm">
                Auto-scroll
              </label>
            </div>
          </div>
        </div>

        {/* Log Count Summary */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          {severityOptions.map((severity) => {
            const count = getLogCounts()[severity.value]
            return (
              <div key={severity.value} className="text-center">
                <div className={`text-lg font-bold ${severity.color}`}>
                  {count}
                </div>
                <div className="text-xs text-gray-400">{severity.label}</div>
              </div>
            )
          })}
        </div>

        {/* Log Entries */}
        <div 
          ref={logContainerRef}
          className="bg-gray-900 rounded border border-gray-700 h-96 overflow-y-auto font-mono text-sm"
        >
          {filteredLogs.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 text-lg">No Log Entries Found</div>
              <p className="text-gray-500 mt-2">
                {logEntries.length === 0 
                  ? 'No logs are available' 
                  : 'Try adjusting your filter criteria'
                }
              </p>
            </div>
          ) : (
            <div className="space-y-1 p-4">
              {filteredLogs.map((entry, index) => (
                <div
                  key={`${entry.timestamp.getTime()}-${index}`}
                  onClick={() => setSelectedEntry(entry)}
                  className={`
                    flex items-start gap-3 p-2 rounded cursor-pointer transition-colors
                    hover:bg-gray-800
                    ${selectedEntry === entry ? 'bg-gray-750 border border-blue-500' : ''}
                  `}
                >
                  <div className="flex-shrink-0 text-xs text-gray-500 w-20">
                    {formatRelativeTime(entry.timestamp)}
                  </div>
                  
                  <div className="flex-shrink-0">
                    <span className="text-sm">
                      {getSeverityIcon(entry.level)}
                    </span>
                  </div>
                  
                  <div className={`flex-shrink-0 text-xs font-medium w-16 ${getSeverityColor(entry.level)}`}>
                    {entry.level.toUpperCase()}
                  </div>
                  
                  <div className="flex-shrink-0 text-xs text-blue-400 w-24 truncate">
                    {entry.component}
                  </div>
                  
                  {entry.accountId && (
                    <div className="flex-shrink-0 text-xs text-yellow-400 w-20 truncate">
                      {entry.accountId}
                    </div>
                  )}
                  
                  <div className="flex-1 text-white">
                    {entry.message}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Log Entry Details */}
        {selectedEntry && (
          <div className="mt-4 p-4 bg-gray-750 rounded border border-gray-600">
            <h4 className="text-white font-medium mb-3">Log Entry Details</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Timestamp:</span>
                <span className="text-white ml-2">{formatTimestamp(selectedEntry.timestamp)}</span>
              </div>
              <div>
                <span className="text-gray-400">Severity:</span>
                <span className={`ml-2 ${getSeverityColor(selectedEntry.level)}`}>
                  {selectedEntry.level.toUpperCase()}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Component:</span>
                <span className="text-blue-400 ml-2">{selectedEntry.component}</span>
              </div>
              {selectedEntry.accountId && (
                <div>
                  <span className="text-gray-400">Account:</span>
                  <span className="text-yellow-400 ml-2">{selectedEntry.accountId}</span>
                </div>
              )}
            </div>
            
            <div className="mt-3">
              <div className="text-gray-400 text-sm mb-1">Message:</div>
              <div className="text-white bg-gray-800 rounded p-3 font-mono text-sm">
                {selectedEntry.message}
              </div>
            </div>
            
            {selectedEntry.context && (
              <div className="mt-3">
                <div className="text-gray-400 text-sm mb-1">Additional Details:</div>
                <pre className="text-white bg-gray-800 rounded p-3 font-mono text-xs overflow-x-auto">
                  {JSON.stringify(selectedEntry.context, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Export Dialog */}
      {showExportDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg max-w-md w-full border border-gray-700">
            <div className="p-6 border-b border-gray-700">
              <h3 className="text-xl font-bold text-white">Export Logs</h3>
              <p className="text-gray-400 text-sm mt-1">
                Export {filteredLogs.length} log entries
              </p>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-gray-750 rounded p-3">
                <div className="text-white font-medium mb-2">Export Summary</div>
                <div className="text-sm text-gray-300 space-y-1">
                  <div>Total entries: {filteredLogs.length}</div>
                  <div>Time range: {
                    filter.timeRange?.start 
                      ? `${formatTimestamp(filter.timeRange.start)} - ${filter.timeRange?.end ? formatTimestamp(filter.timeRange.end) : 'Now'}`
                      : 'All time'
                  }</div>
                  <div>Filters applied: {
                    [filter.level, filter.component, filter.accountId, filter.searchQuery]
                      .filter(Boolean).length || 'None'
                  }</div>
                </div>
              </div>

              <div className="text-sm text-gray-400">
                Logs will be exported in JSON format including all metadata and filtering information.
              </div>
            </div>

            <div className="p-6 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setShowExportDialog(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExport}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
              >
                📥 Export Logs
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}