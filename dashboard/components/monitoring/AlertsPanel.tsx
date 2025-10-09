/**
 * Alerts Panel Component - Story 11.4, Task 6
 *
 * Recent alerts and recommendations panel
 */

'use client'

import React, { useState } from 'react'
import { AlertTriangle, XCircle, CheckCircle, X } from 'lucide-react'

interface Alert {
  id: string
  timestamp: string
  severity: 'normal' | 'warning' | 'critical'
  metric: string
  value: number
  threshold: number
  message: string
  recommendation?: string
  acknowledged: boolean
}

interface AlertsPanelProps {
  alerts: Alert[]
  onAcknowledge?: (alertId: string) => void
  className?: string
}

/**
 * Panel displaying recent overfitting alerts
 *
 * @param alerts - List of alerts
 * @param onAcknowledge - Callback when alert is acknowledged
 * @param className - Additional CSS classes
 * @returns Alerts panel component
 */
export function AlertsPanel({
  alerts,
  onAcknowledge,
  className = ''
}: AlertsPanelProps) {
  const [expandedAlert, setExpandedAlert] = useState<string | null>(null)

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="w-5 h-5 text-red-400" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-400" />
      default:
        return <CheckCircle className="w-5 h-5 text-green-400" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-red-500 bg-red-900/20'
      case 'warning':
        return 'border-yellow-500 bg-yellow-900/20'
      default:
        return 'border-green-500 bg-green-900/20'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

    if (hours < 1) {
      return `${minutes}m ago`
    } else if (hours < 24) {
      return `${hours}h ago`
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
  }

  // Filter unacknowledged alerts
  const activeAlerts = alerts.filter(a => !a.acknowledged)
  const criticalCount = activeAlerts.filter(a => a.severity === 'critical').length
  const warningCount = activeAlerts.filter(a => a.severity === 'warning').length

  return (
    <div className={`bg-gray-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Active Alerts</h3>
        <div className="flex gap-3 text-sm">
          {criticalCount > 0 && (
            <div className="flex items-center gap-1">
              <XCircle className="w-4 h-4 text-red-400" />
              <span className="text-red-400 font-medium">{criticalCount}</span>
            </div>
          )}
          {warningCount > 0 && (
            <div className="flex items-center gap-1">
              <AlertTriangle className="w-4 h-4 text-yellow-400" />
              <span className="text-yellow-400 font-medium">{warningCount}</span>
            </div>
          )}
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {activeAlerts.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-400" />
            <p>No active alerts</p>
            <p className="text-sm mt-1">All systems operating normally</p>
          </div>
        ) : (
          activeAlerts.map(alert => (
            <div
              key={alert.id}
              className={`border-l-4 p-4 rounded-r ${getSeverityColor(alert.severity)} transition-all`}
            >
              {/* Alert Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  {getSeverityIcon(alert.severity)}
                  <div>
                    <div className="text-sm font-medium text-white">
                      {alert.severity.toUpperCase()}
                    </div>
                    <div className="text-xs text-gray-400">
                      {formatTimestamp(alert.timestamp)}
                    </div>
                  </div>
                </div>
                {onAcknowledge && (
                  <button
                    onClick={() => onAcknowledge(alert.id)}
                    className="text-gray-400 hover:text-white transition-colors"
                    title="Acknowledge alert"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Alert Message */}
              <div className="text-sm text-gray-200 mb-2">
                {alert.message}
              </div>

              {/* Alert Details */}
              <div className="flex gap-4 text-xs text-gray-400 mb-2">
                <div>
                  <span className="font-medium">Metric:</span> {alert.metric}
                </div>
                <div>
                  <span className="font-medium">Value:</span> {alert.value.toFixed(3)}
                </div>
                <div>
                  <span className="font-medium">Threshold:</span> {alert.threshold.toFixed(3)}
                </div>
              </div>

              {/* Recommendation (expandable) */}
              {alert.recommendation && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <button
                    onClick={() =>
                      setExpandedAlert(
                        expandedAlert === alert.id ? null : alert.id
                      )
                    }
                    className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    {expandedAlert === alert.id
                      ? '▼ Hide Recommendation'
                      : '▶ Show Recommendation'}
                  </button>
                  {expandedAlert === alert.id && (
                    <div className="mt-2 p-3 bg-gray-900/50 rounded text-xs text-gray-300">
                      {alert.recommendation}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Summary Footer */}
      {activeAlerts.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <div className="text-gray-400">
              {activeAlerts.length} active alert{activeAlerts.length !== 1 ? 's' : ''}
            </div>
            {onAcknowledge && (
              <button
                onClick={() => activeAlerts.forEach(a => onAcknowledge(a.id))}
                className="text-blue-400 hover:text-blue-300 transition-colors"
              >
                Acknowledge All
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
