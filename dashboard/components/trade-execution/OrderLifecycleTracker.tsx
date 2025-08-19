'use client'

import React, { useState, useEffect } from 'react'
import { OrderLifecycle, OrderLifecycleStage, TradeExecution } from '@/types/tradeExecution'
import Card from '@/components/ui/Card'

/**
 * Props for OrderLifecycleTracker component
 */
interface OrderLifecycleTrackerProps {
  /** Order ID to track */
  orderId?: string
  /** Pre-loaded lifecycle data */
  lifecycle?: OrderLifecycle
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback to fetch lifecycle data */
  onFetchLifecycle?: (orderId: string) => Promise<OrderLifecycle | null>
  /** Show detailed latency information */
  showLatency?: boolean
  /** Compact view mode */
  compact?: boolean
}

/**
 * Individual stage component
 */
function StageItem({ 
  stage, 
  isActive, 
  isCompleted, 
  showLatency 
}: { 
  stage: OrderLifecycleStage
  isActive: boolean
  isCompleted: boolean
  showLatency?: boolean
}) {
  const getStageIcon = (status: OrderLifecycleStage['status']): string => {
    switch (status) {
      case 'completed': return '✓'
      case 'current': return '●'
      case 'pending': return '○'
      case 'failed': return '✗'
      default: return '?'
    }
  }

  const getStageColor = (status: OrderLifecycleStage['status']): string => {
    switch (status) {
      case 'completed': return 'text-green-400 border-green-500'
      case 'current': return 'text-blue-400 border-blue-500'
      case 'pending': return 'text-gray-400 border-gray-500'
      case 'failed': return 'text-red-400 border-red-500'
      default: return 'text-gray-400 border-gray-500'
    }
  }

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    })
  }

  const getLatencyColor = (latencyMs?: number): string => {
    if (!latencyMs) return 'text-gray-400'
    if (latencyMs < 100) return 'text-green-400'
    if (latencyMs < 500) return 'text-yellow-400'
    if (latencyMs < 1000) return 'text-orange-400'
    return 'text-red-400'
  }

  return (
    <div className={`flex items-center space-x-4 p-3 rounded-lg border ${
      isActive ? 'bg-blue-900/20 border-blue-500/50' : 
      isCompleted ? 'bg-green-900/20 border-green-500/30' : 'bg-gray-800/50 border-gray-700'
    }`}>
      {/* Stage Icon */}
      <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${getStageColor(stage.status)}`}>
        <span className="text-sm font-bold">
          {getStageIcon(stage.status)}
        </span>
      </div>

      {/* Stage Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <h4 className={`font-medium ${
            stage.status === 'failed' ? 'text-red-400' : 
            stage.status === 'completed' ? 'text-green-400' : 
            stage.status === 'current' ? 'text-blue-400' : 'text-white'
          }`}>
            {stage.name}
          </h4>
          <div className="text-xs text-gray-400">
            {formatTime(stage.timestamp)}
          </div>
        </div>

        {/* Additional Details */}
        <div className="mt-1 space-y-1">
          {showLatency && stage.latencyMs !== undefined && (
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-gray-400">Latency:</span>
              <span className={getLatencyColor(stage.latencyMs)}>
                {formatDuration(stage.latencyMs)}
              </span>
            </div>
          )}
          
          {stage.duration && (
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-gray-400">Duration:</span>
              <span className="text-white">
                {formatDuration(stage.duration)}
              </span>
            </div>
          )}

          {stage.details && (
            <div className="text-xs text-gray-400">
              {stage.details}
            </div>
          )}

          {!stage.expected && (
            <div className="text-xs text-yellow-400">
              ⚠ Unexpected stage
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Progress bar component
 */
function ProgressBar({ 
  stages, 
  currentStage 
}: { 
  stages: OrderLifecycleStage[]
  currentStage: string
}) {
  const completedStages = stages.filter(s => s.status === 'completed').length
  const totalStages = stages.length
  const progressPercent = totalStages > 0 ? (completedStages / totalStages) * 100 : 0

  return (
    <div className="mb-6">
      <div className="flex justify-between text-sm text-gray-400 mb-2">
        <span>Progress</span>
        <span>{completedStages} / {totalStages} stages completed</span>
      </div>
      
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div 
          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  )
}

/**
 * Lifecycle timeline component
 */
function LifecycleTimeline({ 
  stages, 
  currentStage, 
  showLatency 
}: { 
  stages: OrderLifecycleStage[]
  currentStage: string
  showLatency?: boolean
}) {
  const sortedStages = [...stages].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())

  return (
    <div className="space-y-3">
      {sortedStages.map((stage, index) => {
        const isActive = stage.id === currentStage
        const isCompleted = stage.status === 'completed'
        
        return (
          <div key={stage.id} className="relative">
            {/* Timeline connector */}
            {index < sortedStages.length - 1 && (
              <div className="absolute left-4 top-12 w-0.5 h-8 bg-gray-600" />
            )}
            
            <StageItem
              stage={stage}
              isActive={isActive}
              isCompleted={isCompleted}
              showLatency={showLatency}
            />
          </div>
        )
      })}
    </div>
  )
}

/**
 * Lifecycle summary component
 */
function LifecycleSummary({ 
  lifecycle 
}: { 
  lifecycle: OrderLifecycle
}) {
  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const completedStages = lifecycle.stages.filter(s => s.status === 'completed')
  const failedStages = lifecycle.stages.filter(s => s.status === 'failed')
  const averageLatency = completedStages.reduce((sum, stage) => sum + (stage.latencyMs || 0), 0) / completedStages.length

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-800 rounded-lg">
      <div className="text-center">
        <div className="text-2xl font-bold text-white">
          {formatDuration(lifecycle.totalDuration)}
        </div>
        <div className="text-sm text-gray-400">Total Duration</div>
      </div>
      
      <div className="text-center">
        <div className={`text-2xl font-bold ${lifecycle.isComplete ? 'text-green-400' : 'text-yellow-400'}`}>
          {lifecycle.isComplete ? 'Complete' : 'In Progress'}
        </div>
        <div className="text-sm text-gray-400">Status</div>
      </div>
      
      <div className="text-center">
        <div className={`text-2xl font-bold ${failedStages.length > 0 ? 'text-red-400' : 'text-green-400'}`}>
          {failedStages.length}
        </div>
        <div className="text-sm text-gray-400">Failed Stages</div>
      </div>
      
      <div className="text-center">
        <div className={`text-2xl font-bold ${
          averageLatency < 100 ? 'text-green-400' :
          averageLatency < 500 ? 'text-yellow-400' : 'text-red-400'
        }`}>
          {isNaN(averageLatency) ? '-' : formatDuration(averageLatency)}
        </div>
        <div className="text-sm text-gray-400">Avg Latency</div>
      </div>
    </div>
  )
}

/**
 * Order info header component
 */
function OrderInfoHeader({ 
  lifecycle 
}: { 
  lifecycle: OrderLifecycle
}) {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg mb-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Order Lifecycle</h3>
        <p className="text-sm text-gray-400">
          Order ID: <span className="font-mono text-white">{lifecycle.orderId}</span>
        </p>
        <p className="text-sm text-gray-400">
          Execution ID: <span className="font-mono text-white">{lifecycle.executionId}</span>
        </p>
      </div>
      
      <div className="text-right">
        <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
          lifecycle.hasErrors ? 'text-red-400 bg-red-900/20' :
          lifecycle.isComplete ? 'text-green-400 bg-green-900/20' :
          'text-yellow-400 bg-yellow-900/20'
        }`}>
          {lifecycle.hasErrors ? '⚠ Has Errors' :
           lifecycle.isComplete ? '✓ Complete' :
           '● In Progress'}
        </div>
        
        {lifecycle.warnings.length > 0 && (
          <div className="text-xs text-yellow-400 mt-1">
            {lifecycle.warnings.length} warning(s)
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Main OrderLifecycleTracker component
 */
export function OrderLifecycleTracker({
  orderId,
  lifecycle,
  loading = false,
  error,
  onFetchLifecycle,
  showLatency = true,
  compact = false
}: OrderLifecycleTrackerProps) {
  const [localLifecycle, setLocalLifecycle] = useState<OrderLifecycle | null>(lifecycle || null)
  const [localLoading, setLocalLoading] = useState(loading)
  const [localError, setLocalError] = useState<string | null>(error || null)

  // Fetch lifecycle data when orderId changes
  useEffect(() => {
    if (orderId && onFetchLifecycle && !lifecycle) {
      setLocalLoading(true)
      setLocalError(null)
      
      onFetchLifecycle(orderId)
        .then(data => {
          setLocalLifecycle(data)
          setLocalLoading(false)
        })
        .catch(err => {
          setLocalError(err instanceof Error ? err.message : 'Failed to load lifecycle')
          setLocalLoading(false)
        })
    }
  }, [orderId, onFetchLifecycle, lifecycle])

  // Update local state when props change
  useEffect(() => {
    if (lifecycle) {
      setLocalLifecycle(lifecycle)
    }
  }, [lifecycle])

  useEffect(() => {
    setLocalLoading(loading)
  }, [loading])

  useEffect(() => {
    setLocalError(error || null)
  }, [error])

  if (localLoading) {
    return (
      <Card>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-48"></div>
          <div className="h-4 bg-gray-700 rounded w-full"></div>
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <div className="w-8 h-8 bg-gray-700 rounded-full"></div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
                  <div className="h-3 bg-gray-700 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    )
  }

  if (localError) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Order Lifecycle</div>
          <p className="text-gray-400">{localError}</p>
          {orderId && onFetchLifecycle && (
            <button
              onClick={() => {
                setLocalError(null)
                setLocalLoading(true)
                onFetchLifecycle(orderId).then(setLocalLifecycle).finally(() => setLocalLoading(false))
              }}
              className="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Retry
            </button>
          )}
        </div>
      </Card>
    )
  }

  if (!localLifecycle) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-gray-400 text-lg mb-2">No Order Selected</div>
          <p className="text-gray-500">Select an order to view its lifecycle tracking</p>
        </div>
      </Card>
    )
  }

  if (compact) {
    return (
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">Order {localLifecycle.orderId}</h3>
              <p className="text-sm text-gray-400">
                {localLifecycle.stages.filter(s => s.status === 'completed').length} / {localLifecycle.stages.length} stages completed
              </p>
            </div>
            <div className={`text-sm font-medium ${
              localLifecycle.hasErrors ? 'text-red-400' :
              localLifecycle.isComplete ? 'text-green-400' :
              'text-yellow-400'
            }`}>
              {localLifecycle.hasErrors ? 'Has Errors' :
               localLifecycle.isComplete ? 'Complete' :
               'In Progress'}
            </div>
          </div>
          
          <ProgressBar 
            stages={localLifecycle.stages} 
            currentStage={localLifecycle.currentStage}
          />
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <OrderInfoHeader lifecycle={localLifecycle} />
      
      <LifecycleSummary lifecycle={localLifecycle} />
      
      <div className="mt-6">
        <ProgressBar 
          stages={localLifecycle.stages} 
          currentStage={localLifecycle.currentStage}
        />
        
        <h4 className="text-lg font-semibold text-white mb-4">Timeline</h4>
        
        <LifecycleTimeline
          stages={localLifecycle.stages}
          currentStage={localLifecycle.currentStage}
          showLatency={showLatency}
        />
        
        {localLifecycle.warnings.length > 0 && (
          <div className="mt-6 p-4 bg-yellow-900/20 border border-yellow-500/30 rounded-lg">
            <h5 className="text-yellow-400 font-medium mb-2">Warnings</h5>
            <ul className="space-y-1">
              {localLifecycle.warnings.map((warning, index) => (
                <li key={index} className="text-sm text-yellow-300">
                  • {warning}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  )
}

export default OrderLifecycleTracker