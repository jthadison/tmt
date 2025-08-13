'use client'

import { useState } from 'react'
import { AgentStatusInfo, AgentControlRequest, AgentAction } from '@/types/systemControl'

/**
 * Props for AgentMonitor component
 */
interface AgentMonitorProps {
  /** Array of agent status information */
  agents: AgentStatusInfo[]
  /** Callback when agent action is requested */
  onAgentAction: (request: AgentControlRequest) => void
  /** Show compact view */
  compact?: boolean
  /** Loading state indicator */
  loading?: boolean
}

/**
 * Agent monitoring dashboard with health indicators and control actions
 * Displays real-time status and performance metrics for all AI agents
 */
export function AgentMonitor({
  agents,
  onAgentAction,
  compact = false,
  loading = false
}: AgentMonitorProps) {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [showActionDialog, setShowActionDialog] = useState(false)
  const [selectedAction, setSelectedAction] = useState<AgentAction>('restart')
  const [actionReason, setActionReason] = useState('')

  const getStatusColor = (status: AgentStatusInfo['status']): string => {
    switch (status) {
      case 'active':
        return 'text-green-400'
      case 'idle':
        return 'text-yellow-400'
      case 'error':
        return 'text-red-400'
      case 'stopped':
        return 'text-gray-400'
      case 'restarting':
        return 'text-blue-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (status: AgentStatusInfo['status']): string => {
    switch (status) {
      case 'active':
        return '✓'
      case 'idle':
        return '○'
      case 'error':
        return '✗'
      case 'stopped':
        return '■'
      case 'restarting':
        return '↻'
      default:
        return '?'
    }
  }

  const getStatusBadge = (status: AgentStatusInfo['status']): string => {
    switch (status) {
      case 'active':
        return 'bg-green-900/30 text-green-400 border-green-500/30'
      case 'idle':
        return 'bg-yellow-900/30 text-yellow-400 border-yellow-500/30'
      case 'error':
        return 'bg-red-900/30 text-red-400 border-red-500/30'
      case 'stopped':
        return 'bg-gray-900/30 text-gray-400 border-gray-500/30'
      case 'restarting':
        return 'bg-blue-900/30 text-blue-400 border-blue-500/30'
      default:
        return 'bg-gray-900/30 text-gray-400 border-gray-500/30'
    }
  }

  const formatUptime = (uptime: number): string => {
    const days = Math.floor(uptime / (24 * 60 * 60 * 1000))
    const hours = Math.floor((uptime % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000))
    const minutes = Math.floor((uptime % (60 * 60 * 1000)) / (60 * 1000))
    
    if (days > 0) return `${days}d ${hours}h`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  const formatMemory = (memory: number): string => {
    if (memory >= 1024) return `${(memory / 1024).toFixed(1)}GB`
    return `${memory}MB`
  }

  const getPerformanceColor = (percentage: number): string => {
    if (percentage >= 95) return 'text-green-400'
    if (percentage >= 85) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getCpuColor = (cpu: number): string => {
    if (cpu >= 80) return 'text-red-400'
    if (cpu >= 60) return 'text-yellow-400'
    return 'text-green-400'
  }

  const getMemoryColor = (memoryPercentage: number): string => {
    if (memoryPercentage >= 85) return 'text-red-400'
    if (memoryPercentage >= 70) return 'text-yellow-400'
    return 'text-green-400'
  }

  const handleAgentAction = (agentId: string) => {
    setSelectedAgent(agentId)
    setShowActionDialog(true)
  }

  const handleConfirmAction = () => {
    if (!selectedAgent || !actionReason.trim()) return

    const request: AgentControlRequest = {
      agentId: selectedAgent,
      action: selectedAction,
      reason: actionReason.trim()
    }

    onAgentAction(request)
    setShowActionDialog(false)
    setSelectedAgent(null)
    setActionReason('')
  }

  const getActionDescription = (action: AgentAction): string => {
    switch (action) {
      case 'restart':
        return 'Restart the agent (preserves state)'
      case 'stop':
        return 'Stop the agent (requires manual start)'
      case 'start':
        return 'Start the stopped agent'
      case 'reset_errors':
        return 'Reset error counters and clear error state'
      default:
        return ''
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-32"></div>
          <div className="grid grid-cols-1 gap-4">
            {Array.from({ length: compact ? 3 : 6 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-700 rounded"></div>
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
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-white">
            Agent Monitor {compact && '(Overview)'}
          </h3>
          <div className="text-sm text-gray-400">
            {agents.filter(a => a.status === 'active').length} / {agents.length} active
          </div>
        </div>

        {/* Agent Grid */}
        <div className={`grid gap-4 ${compact ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="bg-gray-750 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`text-lg ${getStatusColor(agent.status)}`}>
                      {getStatusIcon(agent.status)}
                    </span>
                    <h4 className="font-medium text-white">{agent.name}</h4>
                    <span className={`px-2 py-1 rounded text-xs border ${getStatusBadge(agent.status)}`}>
                      {agent.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-sm text-gray-400">
                    Type: {agent.type.replace('_', ' ')} • v{agent.version}
                  </div>
                </div>
                
                <button
                  onClick={() => handleAgentAction(agent.id)}
                  className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors"
                >
                  Control
                </button>
              </div>

              {/* Performance Metrics */}
              {!compact && (
                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div>
                    <div className="text-xs text-gray-400">Tasks Completed</div>
                    <div className="font-medium text-white">{agent.performanceMetrics.tasksCompleted.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Success Rate</div>
                    <div className={`font-medium ${getPerformanceColor(agent.performanceMetrics.successRate)}`}>
                      {agent.performanceMetrics.successRate.toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Avg Response</div>
                    <div className="font-medium text-white">{agent.performanceMetrics.avgResponseTime}ms</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Errors</div>
                    <div className={`font-medium ${agent.performanceMetrics.errors > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {agent.performanceMetrics.errors}
                    </div>
                  </div>
                </div>
              )}

              {/* Resource Usage */}
              <div className="grid grid-cols-3 gap-4 mb-3">
                <div>
                  <div className="text-xs text-gray-400">CPU</div>
                  <div className={`font-medium ${getCpuColor(agent.resourceUsage.cpu)}`}>
                    {agent.resourceUsage.cpu.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Memory</div>
                  <div className={`font-medium ${getMemoryColor(agent.resourceUsage.memoryPercentage)}`}>
                    {formatMemory(agent.resourceUsage.memory)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Uptime</div>
                  <div className="font-medium text-white">{formatUptime(agent.uptime)}</div>
                </div>
              </div>

              {/* Status Details */}
              <div className="flex justify-between items-center text-xs text-gray-500">
                <span>
                  Last heartbeat: {new Date(agent.lastHeartbeat).toLocaleTimeString()}
                </span>
                {agent.lastError && (
                  <span className="text-red-400 truncate max-w-32" title={agent.lastError}>
                    Error: {agent.lastError}
                  </span>
                )}
              </div>

              {/* Configuration Info (detailed view only) */}
              {!compact && (
                <div className="mt-3 pt-3 border-t border-gray-600">
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                    <div>Max Tasks: {agent.config.maxConcurrentTasks}</div>
                    <div>Timeout: {agent.config.taskTimeout / 1000}s</div>
                    <div>Restart: {agent.config.restartPolicy}</div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Summary Statistics */}
        {!compact && (
          <div className="mt-6 pt-6 border-t border-gray-700">
            <h4 className="text-white font-medium mb-3">System Summary</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-gray-400">Total Tasks</div>
                <div className="text-white font-medium">
                  {agents.reduce((sum, agent) => sum + agent.performanceMetrics.tasksCompleted, 0).toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Average Success Rate</div>
                <div className="text-green-400 font-medium">
                  {(agents.reduce((sum, agent) => sum + agent.performanceMetrics.successRate, 0) / agents.length).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-gray-400">Total Errors</div>
                <div className={`font-medium ${agents.some(a => a.performanceMetrics.errors > 0) ? 'text-red-400' : 'text-green-400'}`}>
                  {agents.reduce((sum, agent) => sum + agent.performanceMetrics.errors, 0)}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Avg Response Time</div>
                <div className="text-white font-medium">
                  {Math.round(agents.reduce((sum, agent) => sum + agent.performanceMetrics.avgResponseTime, 0) / agents.length)}ms
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Agent Action Dialog */}
      {showActionDialog && selectedAgent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg max-w-md w-full border border-gray-700">
            <div className="p-6 border-b border-gray-700">
              <h3 className="text-xl font-bold text-white">Agent Control</h3>
              <p className="text-gray-400 text-sm mt-1">
                {agents.find(a => a.id === selectedAgent)?.name}
              </p>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-gray-300 text-sm mb-2">Action</label>
                <select
                  value={selectedAction}
                  onChange={(e) => setSelectedAction(e.target.value as AgentAction)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                >
                  <option value="restart">Restart Agent</option>
                  <option value="stop">Stop Agent</option>
                  <option value="start">Start Agent</option>
                  <option value="reset_errors">Reset Errors</option>
                </select>
                <p className="text-gray-500 text-xs mt-1">
                  {getActionDescription(selectedAction)}
                </p>
              </div>

              <div>
                <label className="block text-gray-300 text-sm mb-2">Reason *</label>
                <textarea
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  placeholder="Explain why this action is necessary..."
                  rows={3}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  required
                />
              </div>

              {selectedAction === 'restart' && (
                <div className="bg-yellow-900/20 border border-yellow-500/30 rounded p-3">
                  <div className="text-yellow-400 text-sm font-medium">⚠️ Warning</div>
                  <div className="text-yellow-200 text-sm mt-1">
                    Agent will be temporarily unavailable during restart. Active tasks may be interrupted.
                  </div>
                </div>
              )}

              {selectedAction === 'stop' && (
                <div className="bg-red-900/20 border border-red-500/30 rounded p-3">
                  <div className="text-red-400 text-sm font-medium">🛑 Caution</div>
                  <div className="text-red-200 text-sm mt-1">
                    Agent will stop completely and require manual restart. All active tasks will be terminated.
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowActionDialog(false)
                  setSelectedAgent(null)
                  setActionReason('')
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                disabled={!actionReason.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Execute Action
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}