/**
 * Global Status Bar Component
 * Persistent header showing aggregated system health at a glance
 */

'use client'

import React, { useState, useMemo } from 'react'
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Signal,
  SignalZero,
  ChevronDown
} from 'lucide-react'
import { useSystemHealth } from '@/hooks/useSystemHealth'
import { HealthStatus } from '@/types/health'
import { ConnectionStatus } from '@/types/websocket'

interface StatusBarProps {
  onExpandClick?: () => void
  className?: string
}

/**
 * Health indicator with icon and color
 */
function HealthIndicator({
  status,
  size = 'md'
}: {
  status: HealthStatus
  size?: 'sm' | 'md' | 'lg'
}) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  }

  const config = useMemo(() => {
    switch (status) {
      case 'healthy':
        return {
          Icon: CheckCircle,
          color: 'text-green-400',
          label: 'Healthy'
        }
      case 'degraded':
        return {
          Icon: AlertTriangle,
          color: 'text-yellow-400',
          label: 'Degraded'
        }
      case 'critical':
        return {
          Icon: XCircle,
          color: 'text-red-400',
          label: 'Critical'
        }
    }
  }, [status])

  const { Icon, color, label } = config

  return (
    <div
      className="flex items-center gap-1.5"
      role="img"
      aria-label={`System status: ${label}`}
    >
      <Icon className={`${color} ${sizeClasses[size]}`} aria-hidden="true" />
      <span className={`${color} text-sm font-medium`}>{label}</span>
    </div>
  )
}

/**
 * Metric display with color coding
 */
function Metric({
  label,
  value,
  color,
  tooltip
}: {
  label: string
  value: string | number
  color: string
  tooltip?: string
}) {
  return (
    <div
      className="flex items-center gap-2 px-3 py-1 rounded hover:bg-gray-800/50 transition-colors cursor-help"
      title={tooltip}
      role="status"
      aria-label={`${label}: ${value}`}
    >
      <span className="text-xs text-gray-400">{label}:</span>
      <span className={`text-sm font-semibold ${color}`}>{value}</span>
    </div>
  )
}

/**
 * OANDA Connection Indicator
 */
function OandaConnectionIndicator({ connected }: { connected: boolean }) {
  const Icon = connected ? Signal : SignalZero
  const color = connected ? 'text-green-400' : 'text-red-400'
  const label = connected ? 'Connected' : 'Disconnected'

  return (
    <div
      className="flex items-center gap-1.5 px-3 py-1 rounded hover:bg-gray-800/50 transition-colors cursor-help"
      title={`OANDA API: ${label}`}
      role="status"
      aria-label={`OANDA ${label}`}
    >
      <Icon className={`${color} w-4 h-4`} aria-hidden="true" />
      <span className="text-xs text-gray-400">OANDA</span>
      <span className={`text-sm font-medium ${color}`}>{label}</span>
    </div>
  )
}

/**
 * Global Status Bar Component
 */
export default function StatusBar({ onExpandClick, className = '' }: StatusBarProps) {
  const { healthStatus, isLoading, error, connectionStatus } = useSystemHealth({
    enableWebSocket: true,
    pollingInterval: 5000,
    fallbackDelay: 10000
  })

  const [isHovered, setIsHovered] = useState(false)

  // Calculate agent count color
  const agentCountColor = useMemo(() => {
    if (!healthStatus) return 'text-gray-400'
    const { healthyAgents, totalAgents } = healthStatus

    if (healthyAgents === totalAgents) return 'text-green-400'
    if (healthyAgents >= totalAgents - 2) return 'text-yellow-400'
    return 'text-red-400'
  }, [healthStatus])

  // Calculate latency color
  const latencyColor = useMemo(() => {
    if (!healthStatus) return 'text-gray-400'
    const { averageLatency } = healthStatus

    if (averageLatency < 100) return 'text-green-400'
    if (averageLatency <= 300) return 'text-yellow-400'
    return 'text-red-400'
  }, [healthStatus])

  // Determine connection quality
  const connectionQuality = useMemo(() => {
    if (connectionStatus === ConnectionStatus.CONNECTED) {
      return { text: 'WebSocket', color: 'text-green-400' }
    } else if (connectionStatus === ConnectionStatus.RECONNECTING) {
      return { text: 'Reconnecting', color: 'text-yellow-400' }
    } else if (connectionStatus === ConnectionStatus.ERROR || connectionStatus === ConnectionStatus.DISCONNECTED) {
      return { text: 'Polling', color: 'text-yellow-400' }
    }
    return { text: 'Connecting', color: 'text-gray-400' }
  }, [connectionStatus])

  // Show loading state
  if (isLoading && !healthStatus) {
    return (
      <div className={`bg-gray-800 border-b border-gray-700 px-4 py-2 ${className}`}>
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <div className="animate-pulse flex items-center gap-2">
              <div className="h-5 w-5 bg-gray-700 rounded-full"></div>
              <div className="h-4 w-32 bg-gray-700 rounded"></div>
            </div>
          </div>
          <div className="text-xs text-gray-500">Loading system health...</div>
        </div>
      </div>
    )
  }

  // Show error state
  if (error && !healthStatus) {
    return (
      <div className={`bg-gray-800 border-b border-gray-700 px-4 py-2 ${className}`}>
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-400" />
            <span className="text-sm text-red-400">Failed to load system health</span>
          </div>
          <div className="text-xs text-gray-500">{error}</div>
        </div>
      </div>
    )
  }

  // Fallback if no data
  if (!healthStatus) {
    return null
  }

  const { overall, healthyAgents, totalAgents, averageLatency, oandaConnected, lastUpdate } = healthStatus

  // Check if data is stale (>2 seconds old)
  const isStale = Date.now() - new Date(lastUpdate).getTime() > 2000

  return (
    <div
      className={`bg-gray-800 border-b border-gray-700 px-4 py-2 ${className}`}
      role="region"
      aria-label="System health status bar"
    >
      <div
        className={`flex items-center justify-between max-w-7xl mx-auto ${
          onExpandClick ? 'cursor-pointer' : ''
        }`}
        onClick={onExpandClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Left side: Health indicators */}
        <div className="flex items-center gap-6">
          {/* Overall health indicator */}
          <HealthIndicator status={overall} size="md" />

          {/* Agent count */}
          <Metric
            label="Agents"
            value={`${healthyAgents}/${totalAgents}`}
            color={agentCountColor}
            tooltip={`${healthyAgents} of ${totalAgents} AI agents operational`}
          />

          {/* Average latency */}
          <Metric
            label="Latency"
            value={`${averageLatency}ms`}
            color={latencyColor}
            tooltip={`Average response time: ${averageLatency}ms`}
          />

          {/* OANDA connection status */}
          <OandaConnectionIndicator connected={oandaConnected} />
        </div>

        {/* Right side: Connection status and expand button */}
        <div className="flex items-center gap-4">
          {/* Connection quality indicator */}
          <div className="text-xs text-gray-500">
            <span className={connectionQuality.color}>{connectionQuality.text}</span>
            {isStale && <span className="ml-2 text-yellow-400">(Stale)</span>}
          </div>

          {/* Expand/collapse indicator */}
          {onExpandClick && (
            <button
              className="text-gray-400 hover:text-gray-200 transition-colors p-1 rounded hover:bg-gray-700"
              onClick={(e) => {
                e.stopPropagation()
                onExpandClick()
              }}
              aria-label="Expand detailed health panel"
              aria-expanded="false"
            >
              {isHovered ? (
                <ChevronDown className="w-5 h-5" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-5 h-5" aria-hidden="true" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// Export sub-components for testing
export { HealthIndicator, Metric, OandaConnectionIndicator }
