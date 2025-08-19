/**
 * Agent Control Panel Component - AC1
 * Story 9.5: Individual agent control with pause/resume, parameter adjustment, and emergency stop
 * 
 * SECURITY: Administrator access only - all controls require admin authentication
 */

'use client'

import React, { useState, useMemo } from 'react'
import { 
  AIAgent, 
  AgentStatus, 
  AgentType, 
  AgentParameters,
  AgentControlAction 
} from '@/types/tradingControls'
import Card from '@/components/ui/Card'
import Modal from '@/components/ui/Modal'

/**
 * Props for AgentControlPanel component
 */
interface AgentControlPanelProps {
  /** Array of agents to control */
  agents: AIAgent[]
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback to control agent */
  onAgentControl?: (agentId: string, action: AgentControlAction, justification: string, parameters?: Record<string, any>) => Promise<boolean>
  /** Callback to refresh agents */
  onRefresh?: () => void
  /** Compact view mode */
  compact?: boolean
}

/**
 * Individual agent card component
 */
function AgentCard({
  agent,
  onControl,
  compact = false
}: {
  agent: AIAgent
  onControl?: (action: AgentControlAction, justification: string, parameters?: Record<string, any>) => Promise<boolean>
  compact?: boolean
}) {
  const [showParameterModal, setShowParameterModal] = useState(false)
  const [justificationModal, setJustificationModal] = useState<{
    action: AgentControlAction
    show: boolean
  }>({ action: 'pause', show: false })
  const [justification, setJustification] = useState('')
  const [actionLoading, setActionLoading] = useState<AgentControlAction | null>(null)

  const getStatusColor = (status: AgentStatus): string => {
    switch (status) {
      case 'active': return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'paused': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'stopped': return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
      case 'error': return 'text-red-400 bg-red-900/20 border-red-500/30'
      case 'maintenance': return 'text-blue-400 bg-blue-900/20 border-blue-500/30'
      case 'emergency_stop': return 'text-red-400 bg-red-900/30 border-red-500/50'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const getStatusIcon = (status: AgentStatus): string => {
    switch (status) {
      case 'active': return '▶'
      case 'paused': return '⏸'
      case 'stopped': return '⏹'
      case 'error': return '⚠'
      case 'maintenance': return '🔧'
      case 'emergency_stop': return '🚨'
      default: return '?'
    }
  }

  const getTypeDisplayName = (type: AgentType): string => {
    switch (type) {
      case 'circuit_breaker': return 'Circuit Breaker'
      case 'risk_management': return 'Risk Management'
      case 'execution_engine': return 'Execution Engine'
      case 'market_analysis': return 'Market Analysis'
      case 'portfolio_optimization': return 'Portfolio Optimization'
      case 'compliance': return 'Compliance'
      case 'human_behavior': return 'Human Behavior'
      case 'anti_correlation': return 'Anti-Correlation'
      default: return type
    }
  }

  const handleControlAction = async (action: AgentControlAction) => {
    if (action === 'update_parameters') {
      setShowParameterModal(true)
      return
    }

    setJustificationModal({ action, show: true })
    setJustification('')
  }

  const executeControlAction = async () => {
    if (!onControl || !justification.trim()) return

    setActionLoading(justificationModal.action)
    try {
      const success = await onControl(justificationModal.action, justification.trim())
      if (success) {
        setJustificationModal({ action: 'pause', show: false })
        setJustification('')
      }
    } finally {
      setActionLoading(null)
    }
  }

  const getAvailableActions = (): AgentControlAction[] => {
    const actions: AgentControlAction[] = []
    
    switch (agent.status) {
      case 'active':
        actions.push('pause', 'stop', 'emergency_stop', 'update_parameters')
        break
      case 'paused':
        actions.push('resume', 'stop', 'emergency_stop', 'update_parameters')
        break
      case 'stopped':
        actions.push('restart', 'emergency_stop')
        break
      case 'error':
        actions.push('reset_errors', 'restart', 'emergency_stop')
        break
      case 'maintenance':
        actions.push('restart', 'emergency_stop')
        break
      case 'emergency_stop':
        actions.push('restart')
        break
    }
    
    return actions
  }

  const getActionLabel = (action: AgentControlAction): string => {
    switch (action) {
      case 'pause': return 'Pause'
      case 'resume': return 'Resume'
      case 'stop': return 'Stop'
      case 'restart': return 'Restart'
      case 'emergency_stop': return 'Emergency Stop'
      case 'update_parameters': return 'Update Parameters'
      case 'reset_errors': return 'Reset Errors'
      default: return action
    }
  }

  const getActionButtonClass = (action: AgentControlAction): string => {
    const baseClass = "px-3 py-1 rounded text-sm font-medium transition-colors disabled:opacity-50"
    
    switch (action) {
      case 'emergency_stop':
        return `${baseClass} bg-red-600 hover:bg-red-700 text-white`
      case 'pause':
      case 'stop':
        return `${baseClass} bg-yellow-600 hover:bg-yellow-700 text-white`
      case 'resume':
      case 'restart':
        return `${baseClass} bg-green-600 hover:bg-green-700 text-white`
      case 'update_parameters':
        return `${baseClass} bg-blue-600 hover:bg-blue-700 text-white`
      case 'reset_errors':
        return `${baseClass} bg-purple-600 hover:bg-purple-700 text-white`
      default:
        return `${baseClass} bg-gray-600 hover:bg-gray-700 text-white`
    }
  }

  const formatUptime = (uptime: number): string => {
    return `${uptime.toFixed(1)}%`
  }

  const formatResponseTime = (time: number): string => {
    return `${time}ms`
  }

  const timeSinceHeartbeat = useMemo(() => {
    const diff = new Date().getTime() - agent.lastHeartbeat.getTime()
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    return `${Math.floor(diff / 3600000)}h ago`
  }, [agent.lastHeartbeat])

  if (compact) {
    return (
      <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${agent.isActive ? 'bg-green-400' : 'bg-gray-500'} animate-pulse`} />
            <div>
              <h3 className="font-medium text-white text-sm">{agent.name}</h3>
              <p className="text-xs text-gray-400">{getTypeDisplayName(agent.type)}</p>
            </div>
          </div>
          <div className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(agent.status)}`}>
            <span className="mr-1">{getStatusIcon(agent.status)}</span>
            {agent.status.toUpperCase()}
          </div>
        </div>
        
        <div className="flex space-x-2">
          {getAvailableActions().slice(0, 2).map(action => (
            <button
              key={action}
              onClick={() => handleControlAction(action)}
              disabled={actionLoading === action}
              className={getActionButtonClass(action)}
            >
              {actionLoading === action ? 'Processing...' : getActionLabel(action)}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <>
      <Card>
        <div className="space-y-4">
          {/* Agent Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-4 h-4 rounded-full ${agent.isActive ? 'bg-green-400' : 'bg-gray-500'} animate-pulse`} />
              <div>
                <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
                <p className="text-sm text-gray-400">{getTypeDisplayName(agent.type)}</p>
                <p className="text-xs text-gray-500">ID: {agent.id}</p>
              </div>
            </div>
            
            <div className={`px-3 py-1 rounded-lg text-sm font-medium border ${getStatusColor(agent.status)}`}>
              <span className="mr-2">{getStatusIcon(agent.status)}</span>
              {agent.status.toUpperCase()}
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-3 bg-gray-900 rounded-lg">
            <div className="text-center">
              <div className="text-lg font-bold text-green-400">{formatUptime(agent.performance.uptime)}</div>
              <div className="text-xs text-gray-400">Uptime</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-blue-400">{formatResponseTime(agent.performance.responseTime)}</div>
              <div className="text-xs text-gray-400">Response Time</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-white">{agent.performance.totalActions.toLocaleString()}</div>
              <div className="text-xs text-gray-400">Total Actions</div>
            </div>
            <div className="text-center">
              <div className={`text-lg font-bold ${agent.errorCount > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {agent.errorCount}
              </div>
              <div className="text-xs text-gray-400">Errors</div>
            </div>
          </div>

          {/* Status Information */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Last Heartbeat:</span>
              <span className="text-white">{timeSinceHeartbeat}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Success Rate:</span>
              <span className="text-white">{agent.performance.successRate.toFixed(1)}%</span>
            </div>
            {agent.lastError && (
              <div className="flex justify-between">
                <span className="text-gray-400">Last Error:</span>
                <span className="text-red-400 text-xs font-mono">{agent.lastError}</span>
              </div>
            )}
          </div>

          {/* Control Actions */}
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-sm font-medium text-gray-300 mb-3">Control Actions</h4>
            <div className="flex flex-wrap gap-2">
              {getAvailableActions().map(action => (
                <button
                  key={action}
                  onClick={() => handleControlAction(action)}
                  disabled={actionLoading === action}
                  className={getActionButtonClass(action)}
                >
                  {actionLoading === action ? 'Processing...' : getActionLabel(action)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* Justification Modal */}
      <Modal isOpen={justificationModal.show} onClose={() => setJustificationModal({ action: 'pause', show: false })} size="md">
        <div className="bg-gray-900 p-6">
          <h2 className="text-xl font-bold text-white mb-4">
            Confirm {getActionLabel(justificationModal.action)} - {agent.name}
          </h2>
          
          <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded">
            <p className="text-yellow-300 text-sm">
              <span className="font-medium">⚠ Administrator Action Required</span>
            </p>
            <p className="text-yellow-200 text-sm mt-1">
              This action will be logged in the audit trail and requires justification.
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Justification (Required)
            </label>
            <textarea
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white resize-none"
              rows={3}
              placeholder={`Explain why you are performing this ${getActionLabel(justificationModal.action).toLowerCase()} action...`}
              required
            />
          </div>

          <div className="flex justify-end space-x-3">
            <button
              onClick={() => setJustificationModal({ action: 'pause', show: false })}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
              disabled={actionLoading !== null}
            >
              Cancel
            </button>
            <button
              onClick={executeControlAction}
              disabled={!justification.trim() || actionLoading !== null}
              className={`px-4 py-2 rounded font-medium disabled:opacity-50 ${
                justificationModal.action === 'emergency_stop' 
                  ? 'bg-red-600 hover:bg-red-700 text-white' 
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {actionLoading !== null ? 'Processing...' : `Confirm ${getActionLabel(justificationModal.action)}`}
            </button>
          </div>
        </div>
      </Modal>

      {/* Parameter Update Modal - Placeholder */}
      <Modal isOpen={showParameterModal} onClose={() => setShowParameterModal(false)} size="lg">
        <div className="bg-gray-900 p-6">
          <h2 className="text-xl font-bold text-white mb-4">
            Update Parameters - {agent.name}
          </h2>
          <div className="text-center py-8">
            <p className="text-gray-400">Parameter update interface will be implemented in AC4</p>
            <button
              onClick={() => setShowParameterModal(false)}
              className="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </>
  )
}

/**
 * Agent filter component
 */
function AgentFilter({
  agents,
  onFilterChange,
  currentFilter
}: {
  agents: AIAgent[]
  onFilterChange: (filter: string) => void
  currentFilter: string
}) {
  const statusCounts = useMemo(() => {
    const counts = { all: agents.length }
    agents.forEach(agent => {
      counts[agent.status] = (counts[agent.status] || 0) + 1
    })
    return counts
  }, [agents])

  const filterOptions = [
    { value: 'all', label: 'All', count: statusCounts.all },
    { value: 'active', label: 'Active', count: statusCounts.active || 0 },
    { value: 'paused', label: 'Paused', count: statusCounts.paused || 0 },
    { value: 'error', label: 'Errors', count: statusCounts.error || 0 },
    { value: 'stopped', label: 'Stopped', count: statusCounts.stopped || 0 }
  ]

  return (
    <div className="flex bg-gray-700 rounded-lg p-1">
      {filterOptions.map(option => (
        <button
          key={option.value}
          onClick={() => onFilterChange(option.value)}
          className={`px-3 py-1 rounded text-sm transition-colors ${
            currentFilter === option.value
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          {option.label} ({option.count})
        </button>
      ))}
    </div>
  )
}

/**
 * Main AgentControlPanel component
 */
export function AgentControlPanel({
  agents,
  loading = false,
  error,
  onAgentControl,
  onRefresh,
  compact = false
}: AgentControlPanelProps) {
  const [statusFilter, setStatusFilter] = useState('all')

  const filteredAgents = useMemo(() => {
    if (statusFilter === 'all') return agents
    return agents.filter(agent => agent.status === statusFilter)
  }, [agents, statusFilter])

  const handleAgentControl = async (agentId: string, action: AgentControlAction, justification: string, parameters?: Record<string, any>) => {
    if (!onAgentControl) return false
    return onAgentControl(agentId, action, justification, parameters)
  }

  if (loading && agents.length === 0) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-48"></div>
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <div className="space-y-3">
                <div className="h-5 bg-gray-700 rounded w-3/4"></div>
                <div className="h-4 bg-gray-700 rounded w-1/2"></div>
                <div className="grid grid-cols-4 gap-2">
                  {Array.from({ length: 4 }).map((_, j) => (
                    <div key={j} className="h-12 bg-gray-700 rounded"></div>
                  ))}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Agents</div>
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
          <h2 className="text-xl font-bold text-white mb-1">Agent Control Panel</h2>
          <p className="text-sm text-gray-400">Administrator controls for AI agents - All actions are logged</p>
        </div>
        
        <div className="flex items-center gap-4">
          <AgentFilter 
            agents={agents} 
            onFilterChange={setStatusFilter} 
            currentFilter={statusFilter} 
          />
          
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded text-sm font-medium"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          )}
        </div>
      </div>

      {/* Agents Grid */}
      {filteredAgents.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">No Agents Found</div>
            <p className="text-gray-500">
              {statusFilter === 'all' 
                ? 'No agents are currently available'
                : `No agents with status '${statusFilter}' found`
              }
            </p>
          </div>
        </Card>
      ) : (
        <div className={compact ? "space-y-4" : "grid grid-cols-1 lg:grid-cols-2 gap-6"}>
          {filteredAgents.map(agent => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onControl={(action, justification, parameters) => 
                handleAgentControl(agent.id, action, justification, parameters)
              }
              compact={compact}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default AgentControlPanel