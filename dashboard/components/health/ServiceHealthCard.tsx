/**
 * ServiceHealthCard Component
 * Displays external service health status
 */

'use client'

import React from 'react'
import { CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-react'
import { DetailedServiceHealth } from '@/types/health'

interface ServiceHealthCardProps {
  service: DetailedServiceHealth
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
    connected: {
      Icon: CheckCircle,
      bgColor: 'bg-green-500/10',
      textColor: 'text-green-400',
      label: 'Connected'
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
 * Service health card component
 */
export default function ServiceHealthCard({ service }: ServiceHealthCardProps) {
  // Determine latency color
  const latencyColor = service.latency_ms
    ? service.latency_ms < 100
      ? 'text-green-400'
      : service.latency_ms <= 300
      ? 'text-yellow-400'
      : 'text-red-400'
    : 'text-gray-400'

  // Format timestamp
  const lastCheckTime = new Date(service.last_check).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })

  return (
    <div
      className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
      role="article"
      aria-label={`${service.name} health status`}
    >
      {/* Header: Name and Port */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-white">{service.name}</h3>
          {service.port && (
            <p className="text-xs text-gray-400">Port {service.port}</p>
          )}
        </div>
        <StatusBadge status={service.status} />
      </div>

      {/* Latency */}
      <div className="mb-2">
        <span className="text-xs text-gray-400">Latency: </span>
        <span className={`text-sm font-semibold ${latencyColor}`}>
          {service.latency_ms !== null ? `${service.latency_ms}ms` : 'N/A'}
        </span>
      </div>

      {/* Last Updated */}
      <div className="text-xs text-gray-500">
        Last check: {lastCheckTime}
      </div>
    </div>
  )
}
