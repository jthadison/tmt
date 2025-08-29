'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Users, Activity } from 'lucide-react'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'

interface AgentComparisonDashboardProps {
  accountIds: string[]
  dateRange: { start: Date; end: Date }
  onAgentSelect?: (agentId: string) => void
}

export default function AgentComparisonDashboard({
  accountIds,
  dateRange,
  onAgentSelect
}: AgentComparisonDashboardProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [agents, setAgents] = useState<any[]>([])

  // Fetch agent performance data
  const fetchAgentData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // Fetch live agent performance data
      const agentData = await performanceAnalyticsService.getAgentComparison(
        accountIds,
        dateRange
      )
      
      setAgents(agentData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch agent data')
      
      // Fallback to mock data on error
      console.warn('Using fallback agent data:', err)
      const fallbackAgents = [
        {
          agentId: 'market-analysis',
          agentName: 'Market Analysis Agent',
          totalPnL: 1485.25,
          winRate: 73.1,
          totalTrades: 52,
          sharpeRatio: 1.42,
          maxDrawdown: 95.40
        },
        {
          agentId: 'strategy-analysis', 
          agentName: 'Strategy Analysis Agent',
          totalPnL: 1125.80,
          winRate: 65.9,
          totalTrades: 44,
          sharpeRatio: 1.28,
          maxDrawdown: 115.60
        },
        {
          agentId: 'pattern-detection',
          agentName: 'Pattern Detection Agent',
          totalPnL: 985.45,
          winRate: 63.2,
          totalTrades: 38,
          sharpeRatio: 1.15,
          maxDrawdown: 85.20
        }
      ]
      setAgents(fallbackAgents)
    } finally {
      setLoading(false)
    }
  }, [accountIds, dateRange])

  useEffect(() => {
    fetchAgentData()
  }, [fetchAgentData])

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-800 rounded w-1/3 mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-16 bg-gray-800 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-600 rounded-lg p-6">
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Users className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Agent Performance Comparison</h2>
            <span className="text-sm text-gray-400">
              ({agents.length} agents)
            </span>
          </div>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="p-6">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent, index) => (
            <div
              key={agent.agentId}
              className="bg-gray-800 rounded-lg p-6 border border-gray-700 hover:border-blue-500 transition-colors cursor-pointer"
              onClick={() => onAgentSelect?.(agent.agentId)}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">{agent.agentName}</h3>
                <div className="text-xs bg-blue-600 text-white px-2 py-1 rounded">
                  #{index + 1}
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total P&L:</span>
                  <span className={`font-semibold ${agent.totalPnL > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${agent.totalPnL.toFixed(2)}
                  </span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-gray-400">Win Rate:</span>
                  <span className="text-white font-semibold">{agent.winRate}%</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Trades:</span>
                  <span className="text-white font-semibold">{agent.totalTrades}</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-gray-400">Sharpe Ratio:</span>
                  <span className="text-yellow-400 font-semibold">{agent.sharpeRatio}</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-gray-400">Max Drawdown:</span>
                  <span className="text-red-400 font-semibold">${agent.maxDrawdown.toFixed(2)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Summary */}
      <div className="p-6 border-t border-gray-800 bg-gray-950">
        <div className="text-center text-gray-400">
          <Activity className="w-5 h-5 inline-block mr-2" />
          Agent Comparison Dashboard - Performance metrics and analysis
        </div>
      </div>
    </div>
  )
}