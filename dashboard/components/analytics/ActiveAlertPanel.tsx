'use client'

import { useState, useEffect } from 'react'
import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react'
import { PerformanceAlert, AlertSeverity } from '@/types/analytics'

interface AlertCardProps {
  alert: PerformanceAlert
  onAcknowledge: (id: string) => void
}

function AlertCard({ alert, onAcknowledge }: AlertCardProps) {
  const severityConfig = {
    critical: {
      icon: AlertTriangle,
      color: 'text-red-600',
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-500'
    },
    high: {
      icon: AlertTriangle,
      color: 'text-orange-600',
      bg: 'bg-orange-50 dark:bg-orange-900/20',
      border: 'border-orange-500'
    },
    medium: {
      icon: AlertCircle,
      color: 'text-blue-600',
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-500'
    },
    low: {
      icon: Info,
      color: 'text-gray-600',
      bg: 'bg-gray-50 dark:bg-gray-800',
      border: 'border-gray-400'
    }
  }

  const config = severityConfig[alert.severity]
  const Icon = config.icon

  return (
    <div
      className={`alert-card p-4 rounded-lg border-l-4 ${config.bg} ${config.border}`}
      data-testid="alert-card"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`${config.color} mt-0.5`}>
          <Icon className="w-5 h-5" />
        </div>

        {/* Content */}
        <div className="flex-1">
          <div className="flex items-start justify-between mb-2">
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-white">
                {alert.message}
              </h4>
              <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                {new Date(alert.timestamp).toLocaleString()}
              </div>
            </div>
            <span
              className={`px-2 py-1 text-xs font-semibold rounded uppercase ${config.color} ${config.bg}`}
            >
              {alert.severity}
            </span>
          </div>

          {/* Metrics */}
          <div className="flex items-center gap-4 mb-2 text-sm">
            <div>
              <span className="text-gray-600 dark:text-gray-400">Current: </span>
              <span className="font-mono font-semibold text-gray-900 dark:text-white">
                {alert.currentValue.toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Threshold: </span>
              <span className="font-mono font-semibold text-gray-900 dark:text-white">
                {alert.thresholdValue.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Recommendation */}
          <p className="text-sm bg-white dark:bg-gray-800 p-2 rounded mb-3 text-gray-700 dark:text-gray-300">
            💡 {alert.recommendation}
          </p>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onAcknowledge(alert.id)}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              Acknowledge
            </button>
            <button className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300">
              View Details
            </button>
            {alert.autoRollback && (
              <span className="ml-auto text-xs text-red-600 dark:text-red-400 font-semibold">
                ⚡ Auto-rollback trigger
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function ActiveAlertPanel() {
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch alerts on mount
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch('/api/analytics/degradation-alerts?refresh=true')
        if (!response.ok) throw new Error('Failed to fetch alerts')

        const data = await response.json()
        setAlerts(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchAlerts()
  }, [])

  const handleAcknowledge = async (alertId: string) => {
    try {
      const response = await fetch(
        `/api/analytics/degradation-alerts/acknowledge/${alertId}`,
        { method: 'POST' }
      )

      if (!response.ok) throw new Error('Failed to acknowledge alert')

      // Remove from list
      setAlerts(prev => prev.filter(a => a.id !== alertId))
    } catch (err) {
      console.error('Error acknowledging alert:', err)
    }
  }

  if (loading) {
    return (
      <div className="active-alert-panel p-6 bg-white dark:bg-gray-800 rounded-lg">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="active-alert-panel p-6 bg-white dark:bg-gray-800 rounded-lg">
        <div className="text-red-600 dark:text-red-400">
          Error loading alerts: {error}
        </div>
      </div>
    )
  }

  if (alerts.length === 0) {
    return (
      <div className="active-alert-panel p-6 bg-white dark:bg-gray-800 rounded-lg">
        <div className="text-center text-gray-600 dark:text-gray-400 py-8">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-600" />
          <p>No active alerts. System performance is nominal.</p>
        </div>
      </div>
    )
  }

  // Sort by severity then timestamp
  const sortedAlerts = [...alerts].sort((a, b) => {
    const severityOrder: Record<AlertSeverity, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3
    }
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity]
    if (severityDiff !== 0) return severityDiff
    return b.timestamp - a.timestamp
  })

  return (
    <div className="active-alert-panel p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Active Performance Alerts
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {alerts.length} active
          </span>
          {alerts.some(a => a.autoRollback) && (
            <span className="px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs rounded">
              Auto-rollback enabled
            </span>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {sortedAlerts.map(alert => (
          <AlertCard key={alert.id} alert={alert} onAcknowledge={handleAcknowledge} />
        ))}
      </div>
    </div>
  )
}
