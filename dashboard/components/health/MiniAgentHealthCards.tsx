/**
 * MiniAgentHealthCards Component
 * Displays compact health cards for all AI agents
 */

'use client'

import React, { useMemo } from 'react'
import { useDetailedHealth } from '@/hooks/useDetailedHealth'
import { MiniAgentCardData } from '@/types/health'
import MiniAgentCard from './MiniAgentCard'

interface MiniAgentHealthCardsProps {
  onAgentClick?: (agentPort: number) => void
  className?: string
}

/**
 * Mini agent health cards component
 */
export default function MiniAgentHealthCards({
  onAgentClick,
  className = ''
}: MiniAgentHealthCardsProps) {
  const { healthData, loading, latencyHistory } = useDetailedHealth({
    enableWebSocket: false,
    pollingInterval: 5000
  })

  // Transform agent data for mini cards
  const miniAgentData: MiniAgentCardData[] = useMemo(() => {
    if (!healthData?.agents) return []

    return healthData.agents.map((agent) => ({
      name: agent.name,
      status: agent.status,
      port: agent.port,
      latencyHistory: latencyHistory.get(`agent-${agent.port}`)?.slice(-5) || []
    }))
  }, [healthData, latencyHistory])

  // Show loading state
  if (loading && miniAgentData.length === 0) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        role="region"
        aria-label="Mini agent health cards"
      >
        <div className="text-xs text-gray-500">Loading agents...</div>
      </div>
    )
  }

  // Show empty state with region for E2E tests
  if (miniAgentData.length === 0) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        role="region"
        aria-label="Mini agent health cards"
      >
        <div className="text-xs text-gray-500">No agent data available</div>
      </div>
    )
  }

  return (
    <div
      className={`grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 ${className}`}
      role="region"
      aria-label="Mini agent health cards"
    >
      {miniAgentData.map((agent) => (
        <MiniAgentCard
          key={agent.port}
          agent={agent}
          onClick={() => onAgentClick?.(agent.port)}
        />
      ))}
    </div>
  )
}
