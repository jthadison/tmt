'use client'

import { useState, useEffect } from 'react'
import { Download } from 'lucide-react'
import { PerformanceAlert, AlertFilters, AlertSeverity } from '@/types/analytics'

function convertToCSV(alerts: PerformanceAlert[]): string {
  const headers = [
    'Timestamp',
    'Type',
    'Severity',
    'Message',
    'Current Value',
    'Threshold Value',
    'Recommendation',
    'Auto Rollback',
    'Acknowledged At',
    'Resolved At'
  ]

  const rows = alerts.map(alert => [
    new Date(alert.timestamp).toISOString(),
    alert.type,
    alert.severity,
    `"${alert.message}"`,
    alert.currentValue.toFixed(2),
    alert.thresholdValue.toFixed(2),
    `"${alert.recommendation}"`,
    alert.autoRollback ? 'Yes' : 'No',
    alert.acknowledgedAt ? new Date(alert.acknowledgedAt).toISOString() : '',
    alert.resolvedAt ? new Date(alert.resolvedAt).toISOString() : ''
  ])

  return [headers.join(','), ...rows.map(row => row.join(','))].join('\n')
}

function downloadCSV(csv: string, filename: string) {
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}

function getSeverityClass(severity: AlertSeverity): string {
  const classes = {
    critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    medium: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    low: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
  }
  return classes[severity]
}

export function AlertHistory() {
  const [history, setHistory] = useState<PerformanceAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState<AlertFilters>({
    dateRange: '30d',
    severity: 'all',
    type: 'all'
  })

  const fetchHistory = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        dateRange: filters.dateRange,
        severity: filters.severity,
        type: filters.type
      })

      const response = await fetch(`/api/analytics/degradation-alerts/history?${params}`)
      if (!response.ok) throw new Error('Failed to fetch alert history')

      const data = await response.json()
      setHistory(data)
    } catch (err) {
      console.error('Error fetching alert history:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters])

  const handleExport = () => {
    const csv = convertToCSV(history)
    downloadCSV(csv, `alert-history-${Date.now()}.csv`)
  }

  return (
    <div className="alert-history p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Alert History</h3>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="filters flex flex-wrap items-center gap-3 mb-4">
        <select
          value={filters.dateRange}
          onChange={e =>
            setFilters({ ...filters, dateRange: e.target.value as AlertFilters['dateRange'] })
          }
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="all">All time</option>
        </select>

        <select
          value={filters.severity}
          onChange={e =>
            setFilters({
              ...filters,
              severity: e.target.value as AlertFilters['severity']
            })
          }
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="all">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          value={filters.type}
          onChange={e =>
            setFilters({
              ...filters,
              type: e.target.value as AlertFilters['type']
            })
          }
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="all">All types</option>
          <option value="profit_decline">Profit Decline</option>
          <option value="confidence_breach">Confidence Breach</option>
          <option value="overfitting">Overfitting</option>
          <option value="stability_loss">Stability Loss</option>
          <option value="sharpe_drop">Sharpe Drop</option>
          <option value="win_rate_decline">Win Rate Decline</option>
        </select>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="animate-pulse">
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
        </div>
      )}

      {/* History table */}
      {!loading && history.length === 0 && (
        <div className="text-center text-gray-600 dark:text-gray-400 py-8">
          No alerts found for the selected filters
        </div>
      )}

      {!loading && history.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left p-2 text-gray-700 dark:text-gray-300">Timestamp</th>
                <th className="text-left p-2 text-gray-700 dark:text-gray-300">Type</th>
                <th className="text-left p-2 text-gray-700 dark:text-gray-300">Severity</th>
                <th className="text-left p-2 text-gray-700 dark:text-gray-300">Message</th>
                <th className="text-left p-2 text-gray-700 dark:text-gray-300">Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map(alert => (
                <tr
                  key={alert.id}
                  className="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30"
                >
                  <td className="p-2 text-gray-900 dark:text-gray-100">
                    {new Date(alert.timestamp).toLocaleString()}
                  </td>
                  <td className="p-2 capitalize text-gray-700 dark:text-gray-300">
                    {alert.type.replace(/_/g, ' ')}
                  </td>
                  <td className="p-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityClass(alert.severity)}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                  </td>
                  <td className="p-2 text-gray-900 dark:text-gray-100">{alert.message}</td>
                  <td className="p-2">
                    <span className="text-green-600 dark:text-green-400">✓ Resolved</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
