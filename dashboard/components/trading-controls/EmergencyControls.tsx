/**
 * Emergency Controls Component - AC2  
 * Story 9.5: System-wide emergency controls with stop-all trading and risk parameter overrides
 * 
 * SECURITY: Administrator access only - critical system controls with audit logging
 */

'use client'

import React, { useState, useMemo } from 'react'
import { 
  EmergencyStop,
  EmergencyStopType,
  SystemStatus,
  ComponentStatus
} from '@/types/tradingControls'
import Card from '@/components/ui/Card'
import Modal from '@/components/ui/Modal'

/**
 * Props for EmergencyControls component
 */
interface EmergencyControlsProps {
  /** System status information */
  systemStatus: SystemStatus | null
  /** Active emergency stops */
  emergencyStops: EmergencyStop[]
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback for emergency stop all */
  onEmergencyStopAll?: (justification: string) => Promise<boolean>
  /** Callback to clear emergency stop */
  onClearEmergencyStop?: (stopId: string, justification: string) => Promise<boolean>
  /** Callback to refresh system status */
  onRefresh?: () => void
}

/**
 * System status overview component
 */
function SystemStatusOverview({ 
  systemStatus 
}: { 
  systemStatus: SystemStatus | null 
}) {
  if (!systemStatus) {
    return (
      <div className="animate-pulse p-4 bg-gray-800 rounded-lg">
        <div className="h-6 bg-gray-700 rounded w-32 mb-4"></div>
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  const getHealthStatusColor = (isHealthy: boolean): string => {
    return isHealthy ? 'text-green-400 bg-green-900/20' : 'text-red-400 bg-red-900/20'
  }

  const getRiskLevelColor = (level: string): string => {
    switch (level) {
      case 'low': return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'medium': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'high': return 'text-orange-400 bg-orange-900/20 border-orange-500/30'
      case 'critical': return 'text-red-400 bg-red-900/20 border-red-500/30'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    if (days > 0) return `${days}d ${hours}h`
    return `${hours}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  return (
    <div className="space-y-4">
      {/* System Health Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className={`border-2 ${systemStatus.isHealthy ? 'border-green-500/50' : 'border-red-500/50'}`}>
          <div className="text-center">
            <div className={`text-2xl font-bold ${getHealthStatusColor(systemStatus.isHealthy)}`}>
              {systemStatus.isHealthy ? '✓' : '✗'}
            </div>
            <div className="text-sm text-gray-400 mt-1">
              {systemStatus.isHealthy ? 'Healthy' : 'Degraded'}
            </div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-lg font-bold text-white">{formatUptime(systemStatus.uptime)}</div>
            <div className="text-sm text-gray-400">Uptime</div>
          </div>
        </Card>

        <Card className={`border ${systemStatus.emergencyStopActive ? 'border-red-500/50' : 'border-gray-700'}`}>
          <div className="text-center">
            <div className={`text-lg font-bold ${systemStatus.emergencyStopActive ? 'text-red-400' : 'text-green-400'}`}>
              {systemStatus.emergencyStopActive ? '🚨 ACTIVE' : '✓ Normal'}
            </div>
            <div className="text-sm text-gray-400">Emergency Stop</div>
          </div>
        </Card>

        <Card className={`border ${getRiskLevelColor(systemStatus.riskLevel).split(' ')[2]}`}>
          <div className="text-center">
            <div className={`text-lg font-bold ${getRiskLevelColor(systemStatus.riskLevel).split(' ')[0]}`}>
              {systemStatus.riskLevel.toUpperCase()}
            </div>
            <div className="text-sm text-gray-400">Risk Level</div>
          </div>
        </Card>
      </div>

      {/* Agent Status Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{systemStatus.activeAgents}</div>
            <div className="text-sm text-gray-400">Active Agents</div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{systemStatus.pausedAgents}</div>
            <div className="text-sm text-gray-400">Paused Agents</div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">{systemStatus.errorAgents}</div>
            <div className="text-sm text-gray-400">Error Agents</div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">{systemStatus.pendingApprovals}</div>
            <div className="text-sm text-gray-400">Pending Approvals</div>
          </div>
        </Card>
      </div>
    </div>
  )
}

/**
 * Component status grid
 */
function ComponentStatusGrid({ 
  components 
}: { 
  components: ComponentStatus[] 
}) {
  const getStatusColor = (status: ComponentStatus['status']): string => {
    switch (status) {
      case 'healthy': return 'text-green-400 bg-green-900/20'
      case 'warning': return 'text-yellow-400 bg-yellow-900/20'
      case 'error': return 'text-red-400 bg-red-900/20'
      case 'offline': return 'text-gray-400 bg-gray-900/20'
      default: return 'text-gray-400 bg-gray-900/20'
    }
  }

  const getStatusIcon = (status: ComponentStatus['status']): string => {
    switch (status) {
      case 'healthy': return '✓'
      case 'warning': return '⚠'
      case 'error': return '✗'
      case 'offline': return '○'
      default: return '?'
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {components.map(component => (
        <Card key={component.name}>
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-white">{component.name}</h4>
              <p className="text-sm text-gray-400">
                Last check: {component.lastCheck.toLocaleTimeString()}
              </p>
              {component.responseTime && (
                <p className="text-xs text-gray-500">
                  Response: {component.responseTime}ms
                </p>
              )}
            </div>
            
            <div className={`px-2 py-1 rounded text-sm font-medium ${getStatusColor(component.status)}`}>
              <span className="mr-1">{getStatusIcon(component.status)}</span>
              {component.status.toUpperCase()}
            </div>
          </div>
          
          {component.errorMessage && (
            <div className="mt-2 p-2 bg-red-900/20 border border-red-500/30 rounded">
              <p className="text-red-300 text-xs">{component.errorMessage}</p>
            </div>
          )}
        </Card>
      ))}
    </div>
  )
}

/**
 * Emergency stop card component
 */
function EmergencyStopCard({
  emergencyStop,
  onClear
}: {
  emergencyStop: EmergencyStop
  onClear?: (stopId: string, justification: string) => Promise<boolean>
}) {
  const [showClearModal, setShowClearModal] = useState(false)
  const [justification, setJustification] = useState('')
  const [clearing, setClearing] = useState(false)

  const getStopTypeColor = (type: EmergencyStopType): string => {
    switch (type) {
      case 'immediate_halt': return 'text-red-400 bg-red-900/20 border-red-500/30'
      case 'manual_intervention': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'risk_breach': return 'text-orange-400 bg-orange-900/20 border-orange-500/30'
      case 'system_error': return 'text-red-400 bg-red-900/20 border-red-500/30'
      case 'compliance_violation': return 'text-purple-400 bg-purple-900/20 border-purple-500/30'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const handleClear = async () => {
    if (!onClear || !justification.trim()) return

    setClearing(true)
    try {
      const success = await onClear(emergencyStop.id, justification.trim())
      if (success) {
        setShowClearModal(false)
        setJustification('')
      }
    } finally {
      setClearing(false)
    }
  }

  const formatDuration = (): string => {
    const now = new Date()
    const diff = now.getTime() - emergencyStop.triggeredAt.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) return `${hours}h ${minutes % 60}m`
    return `${minutes}m`
  }

  return (
    <>
      <Card className={`border-2 ${emergencyStop.isActive ? 'border-red-500/50' : 'border-gray-700'}`}>
        <div className="space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center space-x-2 mb-2">
                <span className="text-red-400 text-lg">🚨</span>
                <h3 className="font-medium text-white">Emergency Stop Active</h3>
              </div>
              <div className={`inline-flex px-2 py-1 rounded text-xs font-medium border ${getStopTypeColor(emergencyStop.type)}`}>
                {emergencyStop.type.replace('_', ' ').toUpperCase()}
              </div>
            </div>
            
            <div className="text-right text-sm">
              <div className="text-gray-400">Duration</div>
              <div className="text-white font-medium">{formatDuration()}</div>
            </div>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Triggered By:</span>
              <span className="text-white">{emergencyStop.triggeredBy}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Triggered At:</span>
              <span className="text-white">{emergencyStop.triggeredAt.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Affected Agents:</span>
              <span className="text-white">{emergencyStop.affectedAgents.length}</span>
            </div>
          </div>

          <div className="p-3 bg-gray-800 rounded">
            <div className="text-gray-400 text-sm mb-1">Reason:</div>
            <div className="text-white text-sm">{emergencyStop.reason}</div>
          </div>

          {emergencyStop.isActive && onClear && (
            <button
              onClick={() => setShowClearModal(true)}
              className="w-full bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-4 rounded font-medium transition-colors"
            >
              Clear Emergency Stop
            </button>
          )}
        </div>
      </Card>

      {/* Clear Emergency Stop Modal */}
      <Modal isOpen={showClearModal} onClose={() => setShowClearModal(false)} size="md">
        <div className="bg-gray-900 p-6">
          <h2 className="text-xl font-bold text-white mb-4">Clear Emergency Stop</h2>
          
          <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded">
            <p className="text-yellow-300 text-sm">
              <span className="font-medium">⚠ Critical System Action</span>
            </p>
            <p className="text-yellow-200 text-sm mt-1">
              Clearing this emergency stop will allow system operations to resume. This action will be logged.
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Clearance Justification (Required)
            </label>
            <textarea
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white resize-none"
              rows={3}
              placeholder="Explain why it's safe to clear this emergency stop..."
              required
            />
          </div>

          <div className="flex justify-end space-x-3">
            <button
              onClick={() => setShowClearModal(false)}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
              disabled={clearing}
            >
              Cancel
            </button>
            <button
              onClick={handleClear}
              disabled={!justification.trim() || clearing}
              className="bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 text-white px-4 py-2 rounded font-medium"
            >
              {clearing ? 'Clearing...' : 'Clear Emergency Stop'}
            </button>
          </div>
        </div>
      </Modal>
    </>
  )
}

/**
 * Emergency action button component
 */
function EmergencyActionButton({
  onEmergencyStopAll,
  disabled = false
}: {
  onEmergencyStopAll?: (justification: string) => Promise<boolean>
  disabled?: boolean
}) {
  const [showModal, setShowModal] = useState(false)
  const [justification, setJustification] = useState('')
  const [confirming, setConfirming] = useState(false)

  const handleEmergencyStop = async () => {
    if (!onEmergencyStopAll || !justification.trim()) return

    setConfirming(true)
    try {
      const success = await onEmergencyStopAll(justification.trim())
      if (success) {
        setShowModal(false)
        setJustification('')
      }
    } finally {
      setConfirming(false)
    }
  }

  return (
    <>
      <Card className="border-red-500/50">
        <div className="text-center space-y-4">
          <div className="text-red-400 text-4xl">🚨</div>
          <div>
            <h3 className="text-lg font-bold text-red-400 mb-2">Emergency Stop All</h3>
            <p className="text-sm text-gray-300 mb-4">
              Immediately halt all AI agents and trading operations
            </p>
          </div>
          
          <button
            onClick={() => setShowModal(true)}
            disabled={disabled}
            className="w-full bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:opacity-50 text-white py-3 px-6 rounded font-bold text-lg transition-colors"
          >
            EMERGENCY STOP ALL
          </button>
          
          <p className="text-xs text-gray-500">
            This action cannot be undone without administrator clearance
          </p>
        </div>
      </Card>

      {/* Emergency Stop Confirmation Modal */}
      <Modal isOpen={showModal} onClose={() => setShowModal(false)} size="md">
        <div className="bg-gray-900 p-6">
          <div className="text-center mb-6">
            <div className="text-red-400 text-6xl mb-4">🚨</div>
            <h2 className="text-2xl font-bold text-red-400 mb-2">EMERGENCY STOP ALL</h2>
            <p className="text-white">You are about to halt ALL system operations</p>
          </div>
          
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/50 rounded">
            <h3 className="text-red-300 font-medium mb-2">⚠ CRITICAL WARNING</h3>
            <ul className="text-red-200 text-sm space-y-1">
              <li>• All AI agents will be immediately stopped</li>
              <li>• All trading operations will cease</li>
              <li>• Open positions may be at risk</li>
              <li>• Manual intervention will be required to resume</li>
              <li>• This action will be logged and audited</li>
            </ul>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Emergency Justification (Required)
            </label>
            <textarea
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white resize-none"
              rows={3}
              placeholder="Describe the emergency situation requiring immediate system halt..."
              required
            />
          </div>

          <div className="flex justify-end space-x-3">
            <button
              onClick={() => setShowModal(false)}
              className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded"
              disabled={confirming}
            >
              Cancel
            </button>
            <button
              onClick={handleEmergencyStop}
              disabled={!justification.trim() || confirming}
              className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white px-6 py-2 rounded font-bold"
            >
              {confirming ? 'STOPPING...' : 'CONFIRM EMERGENCY STOP'}
            </button>
          </div>
        </div>
      </Modal>
    </>
  )
}

/**
 * Main EmergencyControls component
 */
export function EmergencyControls({
  systemStatus,
  emergencyStops,
  loading = false,
  error,
  onEmergencyStopAll,
  onClearEmergencyStop,
  onRefresh
}: EmergencyControlsProps) {
  const activeEmergencyStops = useMemo(() => 
    emergencyStops.filter(stop => stop.isActive), [emergencyStops])

  if (loading && !systemStatus) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-48"></div>
          <div className="grid grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Emergency Controls</div>
          <p className="text-gray-400 mb-4">{error}</p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Retry
            </button>
          )}
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Emergency Controls</h2>
          <p className="text-sm text-gray-400">System-wide emergency controls - Administrator access only</p>
        </div>
        
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded text-sm font-medium"
          >
            {loading ? 'Refreshing...' : 'Refresh Status'}
          </button>
        )}
      </div>

      {/* System Status Overview */}
      <SystemStatusOverview systemStatus={systemStatus} />

      {/* Emergency Controls Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Emergency Stop All Button */}
        <EmergencyActionButton
          onEmergencyStopAll={onEmergencyStopAll}
          disabled={loading || (activeEmergencyStops.length > 0)}
        />

        {/* Active Emergency Stops */}
        {activeEmergencyStops.map(emergencyStop => (
          <EmergencyStopCard
            key={emergencyStop.id}
            emergencyStop={emergencyStop}
            onClear={onClearEmergencyStop}
          />
        ))}

        {/* Placeholder for additional emergency controls */}
        {activeEmergencyStops.length === 0 && (
          <Card className="lg:col-span-2">
            <div className="text-center py-8">
              <div className="text-green-400 text-4xl mb-4">✓</div>
              <div className="text-green-400 font-medium text-lg mb-2">System Operating Normally</div>
              <p className="text-gray-400">No emergency stops are currently active</p>
            </div>
          </Card>
        )}
      </div>

      {/* Component Status */}
      {systemStatus?.components && systemStatus.components.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white">Component Status</h3>
          <ComponentStatusGrid components={systemStatus.components} />
        </div>
      )}
    </div>
  )
}

export default EmergencyControls