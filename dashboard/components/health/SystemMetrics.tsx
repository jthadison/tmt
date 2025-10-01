/**
 * SystemMetrics Component
 * Displays overall system performance metrics
 */

'use client'

import React from 'react'
import { Activity, TrendingUp, DollarSign } from 'lucide-react'
import { SystemMetrics as SystemMetricsType } from '@/types/health'

interface SystemMetricsProps {
  metrics: SystemMetricsType
}

interface MetricCardProps {
  label: string
  value: string | number
  icon: React.ReactNode
  color: string
  unit?: string
}

/**
 * Individual metric card
 */
function MetricCard({ label, value, icon, color, unit = '' }: MetricCardProps) {
  return (
    <div
      className="bg-gray-800 rounded-lg p-4 border border-gray-700"
      role="article"
      aria-label={`${label}: ${value}${unit}`}
    >
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${color} bg-opacity-10`}>
          {icon}
        </div>
        <div>
          <p className="text-xs text-gray-400">{label}</p>
          <p className={`text-lg font-semibold ${color}`}>
            {value}
            {unit && <span className="text-sm ml-1">{unit}</span>}
          </p>
        </div>
      </div>
    </div>
  )
}

/**
 * System metrics display
 */
export default function SystemMetrics({ metrics }: SystemMetricsProps) {
  // Determine latency color
  const latencyColor =
    metrics.avg_latency_ms < 100
      ? 'text-green-400'
      : metrics.avg_latency_ms <= 300
      ? 'text-yellow-400'
      : 'text-red-400'

  // Determine P&L color
  const pnlColor = metrics.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'

  // Format P&L value
  const formattedPnl = metrics.daily_pnl >= 0
    ? `+$${metrics.daily_pnl.toFixed(2)}`
    : `-$${Math.abs(metrics.daily_pnl).toFixed(2)}`

  return (
    <div
      className="space-y-3"
      role="region"
      aria-label="System performance metrics"
    >
      <h3 className="text-sm font-semibold text-white mb-3">
        System Performance
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Average Latency */}
        <MetricCard
          label="Avg System Latency"
          value={metrics.avg_latency_ms}
          icon={<Activity className={`w-5 h-5 ${latencyColor}`} />}
          color={latencyColor}
          unit="ms"
        />

        {/* Active Positions */}
        <MetricCard
          label="Active Positions"
          value={metrics.active_positions}
          icon={<TrendingUp className="w-5 h-5 text-blue-400" />}
          color="text-blue-400"
        />

        {/* Daily P&L */}
        <MetricCard
          label="Daily P&L"
          value={formattedPnl}
          icon={<DollarSign className={`w-5 h-5 ${pnlColor}`} />}
          color={pnlColor}
        />
      </div>
    </div>
  )
}
