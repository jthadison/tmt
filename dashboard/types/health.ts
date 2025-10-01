/**
 * Type definitions for system health status
 */

import { ServiceHealth, SystemHealth } from '@/services/healthCheck'

export type HealthStatus = 'healthy' | 'degraded' | 'critical' | 'unknown'

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

// Detailed Health Panel Types

export interface DetailedAgentHealth {
  name: string
  port: number
  status: HealthStatus
  latency_ms: number | null
  last_check: string
}

export interface DetailedServiceHealth {
  name: string
  port?: number
  status: HealthStatus
  latency_ms: number | null
  last_check: string
}

export interface CircuitBreakerMetric {
  current: number
  threshold: number
  limit: number
}

export interface CircuitBreakerStatus {
  max_drawdown: CircuitBreakerMetric
  daily_loss: CircuitBreakerMetric
  consecutive_losses: CircuitBreakerMetric
}

export interface SystemMetrics {
  avg_latency_ms: number
  active_positions: number
  daily_pnl: number
}

export interface DetailedHealthData {
  agents: DetailedAgentHealth[]
  services: DetailedServiceHealth[]
  external_services: DetailedServiceHealth[]
  circuit_breaker: CircuitBreakerStatus
  system_metrics: SystemMetrics
  timestamp: string
}

// Connection Quality Types

export type ConnectionQuality = 'excellent' | 'good' | 'fair' | 'poor' | 'disconnected'

export interface ConnectionMetrics {
  wsStatus: 'connected' | 'connecting' | 'disconnected' | 'error'
  avgLatency: number // milliseconds
  dataAge: number // seconds since last update
}

export interface ConnectionQualityData {
  quality: ConnectionQuality
  metrics: ConnectionMetrics
  lastUpdate: Date | null
}

export interface MiniAgentCardData {
  name: string
  status: HealthStatus
  latencyHistory: number[] // Last 5 measurements
  port: number
}
