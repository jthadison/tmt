'use client'

import { useEffect, useState } from 'react'
import Card from '@/components/ui/Card'
import { getHealthCheckService, SystemHealth } from '@/services/healthCheck'
import { formatDistanceToNow } from '@/utils/dateFormat'

interface HealthCheckPanelProps {
  className?: string
  compact?: boolean
}

/**
 * Real-time health check panel showing system component status
 */
export default function HealthCheckPanel({ className = '', compact = false }: HealthCheckPanelProps) {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [isExpanded, setIsExpanded] = useState(!compact)

  useEffect(() => {
    const healthService = getHealthCheckService()
    
    // Start health checks
    healthService.start()
    
    // Subscribe to updates
    const unsubscribe = healthService.subscribe(setHealth)
    
    return () => {
      unsubscribe()
    }
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-400'
      case 'degraded':
        return 'text-yellow-400'
      case 'unhealthy':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return '●'
      case 'degraded':
        return '◐'
      case 'unhealthy':
        return '●'
      default:
        return '○'
    }
  }

  const getOverallStatusMessage = () => {
    if (!health) return 'Checking system health...'
    
    switch (health.overall) {
      case 'healthy':
        return 'All systems operational'
      case 'degraded':
        return 'Some services degraded'
      case 'unhealthy':
        return 'Critical services offline'
      default:
        return 'Unknown status'
    }
  }

  const formatUptime = (milliseconds: number) => {
    const hours = Math.floor(milliseconds / (1000 * 60 * 60))
    const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))
    
    if (hours > 24) {
      const days = Math.floor(hours / 24)
      return `${days}d ${hours % 24}h`
    }
    return `${hours}h ${minutes}m`
  }

  if (!health) {
    return (
      <Card title="System Health" className={className}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </Card>
    )
  }

  if (compact && !isExpanded) {
    return (
      <Card 
        title="System Health" 
        className={className}
        onClick={() => setIsExpanded(true)}
      >
        <div className="flex items-center justify-between cursor-pointer">
          <div className="flex items-center space-x-2">
            <span className={`text-lg ${getStatusColor(health.overall)}`}>
              {getStatusIcon(health.overall)}
            </span>
            <span className="text-sm text-gray-400">
              {getOverallStatusMessage()}
            </span>
          </div>
          <button 
            className="text-gray-400 hover:text-gray-200"
            onClick={(e) => {
              e.stopPropagation()
              setIsExpanded(true)
            }}
          >
            ↓
          </button>
        </div>
      </Card>
    )
  }

  return (
    <Card 
      title={
        <div className="flex items-center justify-between">
          <span>System Health</span>
          {compact && (
            <button 
              className="text-gray-400 hover:text-gray-200 text-sm"
              onClick={() => setIsExpanded(false)}
            >
              ↑
            </button>
          )}
        </div>
      }
      className={className}
    >
      <div className="space-y-4">
        {/* Overall Status */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-700">
          <div className="flex items-center space-x-3">
            <span className={`text-2xl ${getStatusColor(health.overall)}`}>
              {getStatusIcon(health.overall)}
            </span>
            <div>
              <div className="font-medium">{getOverallStatusMessage()}</div>
              <div className="text-xs text-gray-500">
                Uptime: {formatUptime(health.uptime)}
              </div>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            Last check: {health.timestamp ? formatDistanceToNow(health.timestamp) : 'Never'}
          </div>
        </div>

        {/* Service List */}
        <div className="space-y-0.5">
          {health.services.map((service) => (
            <div
              key={service.name}
              className="grid grid-cols-[auto_1fr_auto] gap-2 items-center py-1 px-2 rounded hover:bg-gray-800/50 transition-colors"
            >
              <span className={`${getStatusColor(service.status)} flex-shrink-0 text-xs leading-none`}>
                {getStatusIcon(service.status)}
              </span>
              <span className="text-xs truncate min-w-0">{service.name}</span>
              {service.latency !== undefined && (
                <span className="text-xs text-gray-400 tabular-nums text-right whitespace-nowrap">
                  {service.latency}ms
                </span>
              )}
              {service.message && !service.latency && (
                <span className="text-xs text-red-400 truncate">
                  {service.message}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Summary Stats */}
        <div className="pt-3 border-t border-gray-700">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-green-400 text-lg font-bold">
                {health.services.filter(s => s.status === 'healthy').length}
              </div>
              <div className="text-xs text-gray-500">Healthy</div>
            </div>
            <div>
              <div className="text-yellow-400 text-lg font-bold">
                {health.services.filter(s => s.status === 'degraded').length}
              </div>
              <div className="text-xs text-gray-500">Degraded</div>
            </div>
            <div>
              <div className="text-red-400 text-lg font-bold">
                {health.services.filter(s => s.status === 'unhealthy').length}
              </div>
              <div className="text-xs text-gray-500">Unhealthy</div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}