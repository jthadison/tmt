/**
 * Type definitions for system health status
 */

import { ServiceHealth, SystemHealth } from '@/services/healthCheck'

export type HealthStatus = 'healthy' | 'degraded' | 'critical'

export interface AgentHealth {
  name: string
  status: HealthStatus
  latency?: number
  lastChecked: Date
  message?: string
}

export interface SystemHealthStatus {
  overall: HealthStatus
  agents: AgentHealth[]
  totalAgents: number
  healthyAgents: number
  averageLatency: number
  oandaConnected: boolean
  lastUpdate: Date
  uptime: number
}

export interface HealthIndicatorProps {
  status: HealthStatus
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
  showText?: boolean
  className?: string
}

// Re-export service types for convenience
export type { ServiceHealth, SystemHealth }
