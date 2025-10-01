/**
 * MiniAgentCard Component
 * Compact agent health card for footer display
 */

'use client'

import React from 'react'
import { MiniAgentCardData } from '@/types/health'
import SparkLine from './SparkLine'

interface MiniAgentCardProps {
  agent: MiniAgentCardData
  onClick?: () => void
}

/**
 * Agent name abbreviations for compact display
 */
const AGENT_ABBREVIATIONS: Record<string, string> = {
  'Market Analysis': 'Market',
  'Strategy Analysis': 'Strategy',
  'Parameter Optimization': 'Params',
  'Learning Safety': 'Safety',
  'Disagreement Engine': 'Disagree',
  'Data Collection': 'Data',
  'Continuous Improvement': 'Improve',
  'Pattern Detection': 'Pattern'
}

/**
 * Get abbreviated agent name
 */
function getAgentAbbreviation(name: string): string {
  return AGENT_ABBREVIATIONS[name] || name
}

/**
 * Get status dot color
 */
function getStatusColor(status: string): string {
  switch (status) {
    case 'healthy':
      return 'bg-green-400'
    case 'degraded':
      return 'bg-yellow-400'
    case 'critical':
      return 'bg-red-400'
    case 'unknown':
    default:
      return 'bg-gray-400'
  }
}

/**
 * Calculate average latency for display
 */
function getAverageLatency(history: number[]): number {
  if (history.length === 0) return 0
  return Math.round(history.reduce((sum, val) => sum + val, 0) / history.length)
}

/**
 * Mini agent card component
 */
export default function MiniAgentCard({ agent, onClick }: MiniAgentCardProps) {
  const abbreviatedName = getAgentAbbreviation(agent.name)
  const statusColor = getStatusColor(agent.status)
  const avgLatency = getAverageLatency(agent.latencyHistory)

  return (
    <button
      onClick={onClick}
      className="relative flex flex-col items-start gap-1 p-2 bg-gray-800 border border-gray-700 rounded hover:bg-gray-750 hover:border-gray-600 transition-colors cursor-pointer text-left w-full"
      aria-label={`${agent.name} health status - Click to view details`}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick?.()
        }
      }}
    >
      {/* Header: Name and Status Dot */}
      <div className="flex items-center justify-between w-full">
        <span className="text-xs font-medium text-white truncate">
          {abbreviatedName}
        </span>
        <div
          className={`w-2 h-2 rounded-full ${statusColor}`}
          aria-label={`Status: ${agent.status}`}
        />
      </div>

      {/* Sparkline and Latency */}
      <div className="flex items-center justify-between w-full gap-2">
        <span className="text-xs text-gray-400">{avgLatency}ms</span>
        {agent.latencyHistory.length > 0 && (
          <SparkLine
            data={agent.latencyHistory}
            width={40}
            height={16}
            className="flex-shrink-0"
          />
        )}
      </div>
    </button>
  )
}
