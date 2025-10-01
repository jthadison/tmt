/**
 * AgentHealthCard Component
 * Displays individual AI agent health status with latency sparkline
 */

'use client'

import React from 'react'
import { CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-react'
import { DetailedAgentHealth } from '@/types/health'
import SparkLine from './SparkLine'

interface AgentHealthCardProps {
  agent: DetailedAgentHealth
  latencyHistory?: number[]
}

/**
 * Status badge component
 */
function StatusBadge({ status }: { status: string }) {
  const config = {
    healthy: {
      Icon: CheckCircle,
      bgColor: 'bg-green-500/10',
      textColor: 'text-green-400',
      label: 'Healthy'
    },
    degraded: {
      Icon: AlertTriangle,
      bgColor: 'bg-yellow-500/10',
      textColor: 'text-yellow-400',
      label: 'Degraded'
    },
    critical: {
      Icon: XCircle,
      bgColor: 'bg-red-500/10',
      textColor: 'text-red-400',
      label: 'Critical'
    },
    unknown: {
      Icon: HelpCircle,
      bgColor: 'bg-gray-500/10',
      textColor: 'text-gray-400',
      label: 'Unknown'
    }
  }

  const { Icon, bgColor, textColor, label } = config[status as keyof typeof config] || config.unknown

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1 rounded ${bgColor}`}
      role="status"
      aria-label={`Status: ${label}`}
    >
      <Icon className={`w-3.5 h-3.5 ${textColor}`} aria-hidden="true" />
      <span className={`text-xs font-medium ${textColor}`}>{label}</span>
    </div>
  )
}

/**
 * Agent health card component
 */
export default function AgentHealthCard({
  agent,
  latencyHistory = []
}: AgentHealthCardProps) {
  // Determine latency color
  const latencyColor = agent.latency_ms
    ? agent.latency_ms < 100
      ? 'text-green-400'
      : agent.latency_ms <= 300
      ? 'text-yellow-400'
      : 'text-red-400'
    : 'text-gray-400'

  // Format timestamp
  const lastCheckTime = new Date(agent.last_check).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })

  return (
    <div
      className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
      role="article"
      aria-label={`${agent.name} health status`}
    >
      {/* Header: Name and Port */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-white">{agent.name}</h3>
          <p className="text-xs text-gray-400">Port {agent.port}</p>
        </div>
        <StatusBadge status={agent.status} />
      </div>

      {/* Latency and Sparkline */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="text-xs text-gray-400">Latency: </span>
          <span className={`text-sm font-semibold ${latencyColor}`}>
            {agent.latency_ms !== null ? `${agent.latency_ms}ms` : 'N/A'}
          </span>
        </div>
        {latencyHistory.length > 0 && (
          <SparkLine data={latencyHistory} width={60} height={20} />
        )}
      </div>

      {/* Last Updated */}
      <div className="text-xs text-gray-500">
        Last check: {lastCheckTime}
      </div>
    </div>
  )
}
