'use client'

import React, { useState, useMemo } from 'react'
import { 
  ExecutionAlert, 
  ExecutionAlertRule, 
  ExecutionAlertType, 
  AlertSeverity
} from '@/types/tradeExecution'
import Card from '@/components/ui/Card'
import Modal from '@/components/ui/Modal'

/**
 * Props for ExecutionAlerts component
 */
interface ExecutionAlertsProps {
  /** Array of active alerts */
  alerts: ExecutionAlert[]
  /** Array of alert rules */
  alertRules?: ExecutionAlertRule[]
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback to acknowledge alert */
  onAcknowledgeAlert?: (alertId: string) => void
  /** Callback to dismiss alert */
  onDismissAlert?: (alertId: string) => void
  /** Callback to create/update alert rule */
  onUpdateAlertRule?: (rule: ExecutionAlertRule) => void
  /** Callback to delete alert rule */
  onDeleteAlertRule?: (ruleId: string) => void
  /** Show alert rule management */
  showRuleManagement?: boolean
  /** Compact view mode */
  compact?: boolean
}

/**
 * Individual alert item component
 */
function AlertItem({
  alert,
  onAcknowledge,
  onDismiss,
  compact = false
}: {
  alert: ExecutionAlert
  onAcknowledge?: (alertId: string) => void
  onDismiss?: (alertId: string) => void
  compact?: boolean
}) {
  const getSeverityColor = (severity: AlertSeverity): string => {
    switch (severity) {
      case 'info': return 'text-blue-400 bg-blue-900/20 border-blue-500/30'
      case 'warning': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'error': return 'text-orange-400 bg-orange-900/20 border-orange-500/30'
      case 'critical': return 'text-red-400 bg-red-900/20 border-red-500/30'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const getSeverityIcon = (severity: AlertSeverity): string => {
    switch (severity) {
      case 'info': return 'ℹ'
      case 'warning': return '⚠'
      case 'error': return '⚡'
      case 'critical': return '🚨'
      default: return '?'
    }
  }

  const getTypeLabel = (type: ExecutionAlertType): string => {
    switch (type) {
      case 'execution_failed': return 'Execution Failed'
      case 'high_slippage': return 'High Slippage'
      case 'partial_fill': return 'Partial Fill'
      case 'execution_delay': return 'Execution Delay'
      case 'rejection': return 'Order Rejected'
      case 'timeout': return 'Execution Timeout'
      default: return 'Unknown'
    }
  }

  const formatTime = (date: Date): string => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return date.toLocaleDateString()
  }

  if (compact) {
    return (
      <div className={`p-3 border-l-4 ${getSeverityColor(alert.severity).split(' ')[2]} bg-gray-800 hover:bg-gray-750 transition-colors`}>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <span className="text-lg">{getSeverityIcon(alert.severity)}</span>
              <span className="font-medium text-white text-sm">{alert.title}</span>
              <span className="text-xs text-gray-400">{formatTime(alert.timestamp)}</span>
            </div>
            <p className="text-sm text-gray-300 mt-1">{alert.message}</p>
            {alert.accountId && (
              <div className="text-xs text-gray-400 mt-1">
                Account: {alert.accountId} • {alert.instrument || 'N/A'}
              </div>
            )}
          </div>
          <div className="flex items-center space-x-2 ml-4">
            {!alert.acknowledged && onAcknowledge && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                className="text-blue-400 hover:text-blue-300 text-xs"
              >
                Ack
              </button>
            )}
            {onDismiss && (
              <button
                onClick={() => onDismiss(alert.id)}
                className="text-gray-400 hover:text-red-400 text-xs"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <Card className={`border-l-4 ${getSeverityColor(alert.severity).split(' ')[2]} ${alert.acknowledged ? 'opacity-75' : ''}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-3 mb-2">
            <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
              <span className="mr-1">{getSeverityIcon(alert.severity)}</span>
              {alert.severity.toUpperCase()}
            </span>
            <span className="text-sm text-gray-400">{getTypeLabel(alert.type)}</span>
            <span className="text-xs text-gray-500">{formatTime(alert.timestamp)}</span>
          </div>
          
          <h3 className="font-semibold text-white mb-2">{alert.title}</h3>
          <p className="text-gray-300 mb-3">{alert.message}</p>
          
          {/* Alert Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            {alert.executionId && (
              <div>
                <span className="text-gray-400">Execution ID:</span>
                <span className="ml-2 font-mono text-white">{alert.executionId}</span>
              </div>
            )}
            {alert.accountId && (
              <div>
                <span className="text-gray-400">Account:</span>
                <span className="ml-2 text-white">{alert.accountId}</span>
              </div>
            )}
            {alert.instrument && (
              <div>
                <span className="text-gray-400">Instrument:</span>
                <span className="ml-2 text-white">{alert.instrument}</span>
              </div>
            )}
            {alert.broker && (
              <div>
                <span className="text-gray-400">Broker:</span>
                <span className="ml-2 text-white">{alert.broker}</span>
              </div>
            )}
          </div>
          
          {/* Acknowledgment Info */}
          {alert.acknowledged && (
            <div className="mt-3 p-2 bg-green-900/20 border border-green-500/30 rounded text-sm">
              <span className="text-green-400">✓ Acknowledged</span>
              {alert.acknowledgedBy && (
                <span className="text-gray-400 ml-2">by {alert.acknowledgedBy}</span>
              )}
              {alert.acknowledgedAt && (
                <span className="text-gray-400 ml-2">
                  {alert.acknowledgedAt.toLocaleString()}
                </span>
              )}
            </div>
          )}
        </div>
        
        {/* Actions */}
        <div className="flex items-start space-x-2 ml-4">
          {!alert.acknowledged && onAcknowledge && (
            <button
              onClick={() => onAcknowledge(alert.id)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
            >
              Acknowledge
            </button>
          )}
          {onDismiss && (
            <button
              onClick={() => onDismiss(alert.id)}
              className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    </Card>
  )
}

/**
 * Alert statistics component
 */
function AlertStats({ 
  alerts 
}: { 
  alerts: ExecutionAlert[]
}) {
  const stats = useMemo(() => {
    const total = alerts.length
    const acknowledged = alerts.filter(a => a.acknowledged).length
    const unacknowledged = total - acknowledged
    const resolved = alerts.filter(a => a.resolved).length
    
    const bySeverity = alerts.reduce((acc, alert) => {
      acc[alert.severity] = (acc[alert.severity] || 0) + 1
      return acc
    }, {} as Record<AlertSeverity, number>)
    
    const byType = alerts.reduce((acc, alert) => {
      acc[alert.type] = (acc[alert.type] || 0) + 1
      return acc
    }, {} as Record<ExecutionAlertType, number>)
    
    return { total, acknowledged, unacknowledged, resolved, bySeverity, byType }
  }, [alerts])

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Card>
        <div className="text-center">
          <div className="text-2xl font-bold text-white">{stats.total}</div>
          <div className="text-sm text-gray-400">Total Alerts</div>
        </div>
      </Card>
      
      <Card>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-400">{stats.unacknowledged}</div>
          <div className="text-sm text-gray-400">Unacknowledged</div>
        </div>
      </Card>
      
      <Card>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-400">{stats.acknowledged}</div>
          <div className="text-sm text-gray-400">Acknowledged</div>
        </div>
      </Card>
      
      <Card>
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{stats.resolved}</div>
          <div className="text-sm text-gray-400">Resolved</div>
        </div>
      </Card>
    </div>
  )
}

/**
 * Alert rule configuration component
 */
function AlertRuleModal({
  isOpen,
  onClose,
  rule,
  onSave,
  onDelete
}: {
  isOpen: boolean
  onClose: () => void
  rule?: ExecutionAlertRule
  onSave: (rule: ExecutionAlertRule) => void
  onDelete?: (ruleId: string) => void
}) {
  const [formData, setFormData] = useState<Partial<ExecutionAlertRule>>(
    rule || {
      name: '',
      type: 'high_slippage',
      severity: 'warning',
      enabled: true,
      conditions: {},
      notifications: { dashboard: true },
      cooldownPeriod: 5
    }
  )

  const alertTypes: { value: ExecutionAlertType; label: string }[] = [
    { value: 'execution_failed', label: 'Execution Failed' },
    { value: 'high_slippage', label: 'High Slippage' },
    { value: 'partial_fill', label: 'Partial Fill' },
    { value: 'execution_delay', label: 'Execution Delay' },
    { value: 'rejection', label: 'Order Rejection' },
    { value: 'timeout', label: 'Execution Timeout' }
  ]

  const severityOptions: { value: AlertSeverity; label: string }[] = [
    { value: 'info', label: 'Info' },
    { value: 'warning', label: 'Warning' },
    { value: 'error', label: 'Error' },
    { value: 'critical', label: 'Critical' }
  ]

  const handleSave = () => {
    const ruleData: ExecutionAlertRule = {
      id: rule?.id || `rule_${Date.now()}`,
      name: formData.name || '',
      type: formData.type || 'high_slippage',
      severity: formData.severity || 'warning',
      enabled: formData.enabled !== false,
      conditions: formData.conditions || {},
      notifications: formData.notifications || { dashboard: true },
      cooldownPeriod: formData.cooldownPeriod || 5,
      createdAt: rule?.createdAt || new Date(),
      updatedAt: new Date()
    }
    
    onSave(ruleData)
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <div className="bg-gray-900 p-6">
        <h2 className="text-xl font-bold text-white mb-6">
          {rule ? 'Edit Alert Rule' : 'Create Alert Rule'}
        </h2>
        
        <div className="space-y-4">
          {/* Basic Info */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Rule Name</label>
            <input
              type="text"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              placeholder="Enter rule name"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Alert Type</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value as ExecutionAlertType })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                {alertTypes.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Severity</label>
              <select
                value={formData.severity}
                onChange={(e) => setFormData({ ...formData, severity: e.target.value as AlertSeverity })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                {severityOptions.map(severity => (
                  <option key={severity.value} value={severity.value}>
                    {severity.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Conditions */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Conditions</label>
            <div className="grid grid-cols-2 gap-4">
              {formData.type === 'high_slippage' && (
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Slippage Threshold (pips)</label>
                  <input
                    type="number"
                    value={formData.conditions?.slippageThreshold || ''}
                    onChange={(e) => setFormData({
                      ...formData,
                      conditions: {
                        ...formData.conditions,
                        slippageThreshold: e.target.value ? parseFloat(e.target.value) : undefined
                      }
                    })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                    placeholder="2.0"
                  />
                </div>
              )}
              
              {formData.type === 'execution_delay' && (
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Delay Threshold (ms)</label>
                  <input
                    type="number"
                    value={formData.conditions?.delayThreshold || ''}
                    onChange={(e) => setFormData({
                      ...formData,
                      conditions: {
                        ...formData.conditions,
                        delayThreshold: e.target.value ? parseInt(e.target.value) : undefined
                      }
                    })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                    placeholder="1000"
                  />
                </div>
              )}
            </div>
          </div>
          
          {/* Settings */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Cooldown Period (minutes)</label>
              <input
                type="number"
                value={formData.cooldownPeriod || ''}
                onChange={(e) => setFormData({ ...formData, cooldownPeriod: e.target.value ? parseInt(e.target.value) : 5 })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                placeholder="5"
              />
            </div>
            
            <div className="flex items-center">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.enabled !== false}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                  className="rounded"
                />
                <span className="text-gray-300">Enabled</span>
              </label>
            </div>
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex justify-between mt-6">
          <div>
            {rule && onDelete && (
              <button
                onClick={() => {
                  onDelete(rule.id)
                  onClose()
                }}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
              >
                Delete Rule
              </button>
            )}
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Save Rule
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

/**
 * Main ExecutionAlerts component
 */
export function ExecutionAlerts({
  alerts,
  alertRules = [],
  loading = false,
  error,
  onAcknowledgeAlert,
  onDismissAlert,
  onUpdateAlertRule,
  onDeleteAlertRule,
  showRuleManagement = false,
  compact = false
}: ExecutionAlertsProps) {
  const [filter, setFilter] = useState<'all' | 'unacknowledged' | 'critical'>('unacknowledged')
  const [showRuleModal, setShowRuleModal] = useState(false)
  const [editingRule, setEditingRule] = useState<ExecutionAlertRule | undefined>()

  // Filter alerts based on selected filter
  const filteredAlerts = useMemo(() => {
    switch (filter) {
      case 'unacknowledged':
        return alerts.filter(alert => !alert.acknowledged)
      case 'critical':
        return alerts.filter(alert => alert.severity === 'critical' || alert.severity === 'error')
      default:
        return alerts
    }
  }, [alerts, filter])

  // Sort alerts by timestamp (newest first)
  const sortedAlerts = useMemo(() => {
    return [...filteredAlerts].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  }, [filteredAlerts])

  const handleEditRule = (rule: ExecutionAlertRule) => {
    setEditingRule(rule)
    setShowRuleModal(true)
  }

  const handleCreateRule = () => {
    setEditingRule(undefined)
    setShowRuleModal(true)
  }

  if (loading && alerts.length === 0) {
    return (
      <Card>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-32"></div>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-700 rounded"></div>
          ))}
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Alerts</div>
          <p className="text-gray-400">{error}</p>
        </div>
      </Card>
    )
  }

  if (compact) {
    const recentAlerts = sortedAlerts.slice(0, 5)
    return (
      <Card>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">Recent Alerts</h3>
          <span className="text-sm text-gray-400">{alerts.length} total</span>
        </div>
        
        {recentAlerts.length === 0 ? (
          <div className="text-center py-4">
            <div className="text-gray-400">No alerts</div>
          </div>
        ) : (
          <div className="space-y-2">
            {recentAlerts.map(alert => (
              <AlertItem
                key={alert.id}
                alert={alert}
                onAcknowledge={onAcknowledgeAlert}
                onDismiss={onDismissAlert}
                compact={true}
              />
            ))}
          </div>
        )}
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">Execution Alerts</h2>
            <p className="text-sm text-gray-400">Monitor and manage trade execution alerts</p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Filter Buttons */}
            <div className="flex bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  filter === 'all'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                All ({alerts.length})
              </button>
              <button
                onClick={() => setFilter('unacknowledged')}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  filter === 'unacknowledged'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Unacknowledged ({alerts.filter(a => !a.acknowledged).length})
              </button>
              <button
                onClick={() => setFilter('critical')}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  filter === 'critical'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Critical ({alerts.filter(a => a.severity === 'critical' || a.severity === 'error').length})
              </button>
            </div>
            
            {showRuleManagement && onUpdateAlertRule && (
              <button
                onClick={handleCreateRule}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-medium"
              >
                Create Rule
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Alert Statistics */}
      <AlertStats alerts={alerts} />

      {/* Alert Rules Management */}
      {showRuleManagement && alertRules.length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-white mb-4">Alert Rules</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {alertRules.map(rule => (
              <div key={rule.id} className="p-4 bg-gray-800 rounded-lg">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h4 className="font-medium text-white">{rule.name}</h4>
                    <p className="text-sm text-gray-400">{rule.type.replace('_', ' ')}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded text-xs ${rule.enabled ? 'bg-green-900/30 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                      {rule.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                    <button
                      onClick={() => handleEditRule(rule)}
                      className="text-blue-400 hover:text-blue-300 text-sm"
                    >
                      Edit
                    </button>
                  </div>
                </div>
                <div className="text-xs text-gray-400">
                  Severity: {rule.severity} • Cooldown: {rule.cooldownPeriod}m
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Alerts List */}
      <div className="space-y-4">
        {sortedAlerts.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <div className="text-gray-400 text-lg mb-2">No Alerts</div>
              <p className="text-gray-500">
                {filter === 'all' 
                  ? 'No execution alerts have been generated'
                  : `No ${filter} alerts found`
                }
              </p>
            </div>
          </Card>
        ) : (
          sortedAlerts.map(alert => (
            <AlertItem
              key={alert.id}
              alert={alert}
              onAcknowledge={onAcknowledgeAlert}
              onDismiss={onDismissAlert}
            />
          ))
        )}
      </div>

      {/* Alert Rule Modal */}
      {showRuleManagement && (
        <AlertRuleModal
          isOpen={showRuleModal}
          onClose={() => {
            setShowRuleModal(false)
            setEditingRule(undefined)
          }}
          rule={editingRule}
          onSave={(rule) => onUpdateAlertRule?.(rule)}
          onDelete={(ruleId) => onDeleteAlertRule?.(ruleId)}
        />
      )}
    </div>
  )
}

export default ExecutionAlerts