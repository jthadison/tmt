/**
 * Agent Comparison Dashboard Component - AC4
 * Story 9.6: Comparative analysis between different agents and strategies
 * 
 * Multi-agent performance comparison and attribution analysis
 */

'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Bar, Radar, Scatter, Line } from 'react-chartjs-2'
import {
  Users,
  Trophy,
  TrendingUp,
  TrendingDown,
  Activity,
  Clock,
  Target,
  Zap,
  BarChart3,
  Filter,
  ArrowUpDown
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { AgentPerformance } from '@/types/performanceAnalytics'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'
import { formatCurrency, formatPercent, formatNumber } from '@/utils/formatters'

interface AgentComparisonDashboardProps {
  accountIds: string[]
  dateRange: { start: Date; end: Date }
  onAgentSelect?: (agentId: string) => void
}

type SortField = 'totalPnL' | 'winRate' | 'sharpeRatio' | 'maxDrawdown' | 'totalTrades' | 'consistency'
type SortDirection = 'asc' | 'desc'

export default function AgentComparisonDashboard({
  accountIds,
  dateRange,
  onAgentSelect
}: AgentComparisonDashboardProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [agents, setAgents] = useState<AgentPerformance[]>([])
  const [selectedAgents, setSelectedAgents] = useState<Set<string>>(new Set())
  const [sortField, setSortField] = useState<SortField>('totalPnL')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [viewMode, setViewMode] = useState<'table' | 'charts' | 'radar'>('table')
  const [filterMinTrades, setFilterMinTrades] = useState(0)

  // Fetch agent performance data
  const fetchAgentData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await performanceAnalyticsService.getAgentComparison(accountIds, dateRange)
      setAgents(data)
      
      // Select top 3 agents by default
      const topAgents = data
        .sort((a, b) => b.totalPnL - a.totalPnL)
        .slice(0, 3)
        .map(a => a.agentId)
      setSelectedAgents(new Set(topAgents))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch agent data')
    } finally {
      setLoading(false)
    }
  }, [accountIds, dateRange])

  useEffect(() => {
    fetchAgentData()
  }, [fetchAgentData])

  // Filter and sort agents
  const filteredAndSortedAgents = useMemo(() => {
    let filtered = agents.filter(agent => agent.totalTrades >= filterMinTrades)
    
    return filtered.sort((a, b) => {
      const aVal = a[sortField] as number
      const bVal = b[sortField] as number
      return sortDirection === 'desc' ? bVal - aVal : aVal - bVal
    })
  }, [agents, filterMinTrades, sortField, sortDirection])

  // Performance comparison chart data
  const performanceComparisonData = useMemo(() => {
    const selectedAgentData = agents.filter(agent => selectedAgents.has(agent.agentId))
    
    return {
      labels: selectedAgentData.map(agent => agent.agentName),
      datasets: [
        {
          label: 'Total P&L',
          data: selectedAgentData.map(agent => agent.totalPnL),
          backgroundColor: 'rgba(59, 130, 246, 0.8)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 1,
          yAxisID: 'y'
        },
        {
          label: 'Win Rate %',
          data: selectedAgentData.map(agent => agent.winRate),
          backgroundColor: 'rgba(16, 185, 129, 0.8)',
          borderColor: 'rgb(16, 185, 129)',
          borderWidth: 1,
          yAxisID: 'y1'
        }
      ]
    }
  }, [agents, selectedAgents])

  // Radar chart data for multi-dimensional comparison
  const radarData = useMemo(() => {
    if (selectedAgents.size === 0) return null

    const selectedAgentData = agents.filter(agent => selectedAgents.has(agent.agentId))
    const maxValues = {
      winRate: Math.max(...agents.map(a => a.winRate)),
      sharpeRatio: Math.max(...agents.map(a => Math.max(0, a.sharpeRatio))),
      consistency: Math.max(...agents.map(a => a.consistency)),
      reliability: Math.max(...agents.map(a => a.reliability)),
      profitFactor: Math.max(...agents.map(a => Math.min(5, a.profitFactor))) // Cap at 5 for visualization
    }

    return {
      labels: ['Win Rate', 'Sharpe Ratio', 'Consistency', 'Reliability', 'Profit Factor'],
      datasets: selectedAgentData.map((agent, index) => ({
        label: agent.agentName,
        data: [
          (agent.winRate / maxValues.winRate) * 100,
          (Math.max(0, agent.sharpeRatio) / maxValues.sharpeRatio) * 100,
          (agent.consistency / maxValues.consistency) * 100,
          (agent.reliability / maxValues.reliability) * 100,
          (Math.min(5, agent.profitFactor) / maxValues.profitFactor) * 100
        ],
        backgroundColor: [
          'rgba(59, 130, 246, 0.2)',
          'rgba(16, 185, 129, 0.2)',
          'rgba(245, 158, 11, 0.2)',
          'rgba(139, 92, 246, 0.2)',
          'rgba(236, 72, 153, 0.2)'
        ][index % 5],
        borderColor: [
          'rgb(59, 130, 246)',
          'rgb(16, 185, 129)',
          'rgb(245, 158, 11)',
          'rgb(139, 92, 246)',
          'rgb(236, 72, 153)'
        ][index % 5],
        pointBackgroundColor: [
          'rgb(59, 130, 246)',
          'rgb(16, 185, 129)',
          'rgb(245, 158, 11)',
          'rgb(139, 92, 246)',
          'rgb(236, 72, 153)'
        ][index % 5],
        borderWidth: 2
      }))
    }
  }, [agents, selectedAgents])

  // Scatter plot for risk-return analysis
  const riskReturnData = useMemo(() => {
    return {
      datasets: [{
        label: 'Agents',
        data: agents.map(agent => ({
          x: agent.performance.volatility,
          y: agent.totalPnL / Math.max(agent.totalTrades, 1), // Avg P&L per trade
          agentName: agent.agentName,
          agentId: agent.agentId
        })),
        backgroundColor: agents.map(agent => 
          selectedAgents.has(agent.agentId) ? 'rgba(59, 130, 246, 0.8)' : 'rgba(107, 114, 128, 0.5)'
        ),
        borderColor: agents.map(agent => 
          selectedAgents.has(agent.agentId) ? 'rgb(59, 130, 246)' : 'rgb(107, 114, 128)'
        ),
        pointRadius: 8,
        pointHoverRadius: 10
      }]
    }
  }, [agents, selectedAgents])

  // Handle sorting
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  // Toggle agent selection
  const toggleAgentSelection = (agentId: string) => {
    const newSelection = new Set(selectedAgents)
    if (newSelection.has(agentId)) {
      newSelection.delete(agentId)
    } else {
      newSelection.add(agentId)
    }
    setSelectedAgents(newSelection)
  }

  // Get rank badge color
  const getRankBadgeColor = (rank: number) => {
    if (rank === 1) return 'bg-yellow-500 text-yellow-900'
    if (rank <= 3) return 'bg-gray-400 text-gray-900'
    if (rank <= 5) return 'bg-amber-600 text-amber-100'
    return 'bg-gray-600 text-gray-300'
  }

  // Performance indicator
  const getPerformanceIndicator = (value: number, type: 'pnl' | 'percent' | 'ratio') => {
    let color = 'text-gray-400'
    let icon = Activity
    
    if (type === 'pnl') {
      color = value > 0 ? 'text-green-400' : value < 0 ? 'text-red-400' : 'text-gray-400'
      icon = value > 0 ? TrendingUp : value < 0 ? TrendingDown : Activity
    } else if (type === 'percent') {
      color = value > 70 ? 'text-green-400' : value > 50 ? 'text-yellow-400' : 'text-red-400'
      icon = value > 60 ? TrendingUp : TrendingDown
    } else if (type === 'ratio') {
      color = value > 1.5 ? 'text-green-400' : value > 1 ? 'text-yellow-400' : 'text-red-400'
      icon = value > 1 ? TrendingUp : TrendingDown
    }
    
    return { color, icon }
  }

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
          
          {/* Selected agents indicator */}
          <div className="text-sm text-gray-400">
            {selectedAgents.size} selected for comparison
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-4 items-center">
          {/* View Mode */}
          <div className="flex gap-1 bg-gray-800 rounded p-1">
            {[
              { key: 'table', label: 'Table', icon: BarChart3 },
              { key: 'charts', label: 'Charts', icon: Activity },
              { key: 'radar', label: 'Radar', icon: Target }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setViewMode(key as any)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm ${
                  viewMode === key
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                } transition-colors`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          {/* Filter by minimum trades */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <label className="text-sm text-gray-400">Min trades:</label>
            <input
              type="number"
              min="0"
              value={filterMinTrades}
              onChange={(e) => setFilterMinTrades(parseInt(e.target.value) || 0)}
              className="w-20 px-2 py-1 bg-gray-800 text-white rounded text-sm"
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {viewMode === 'table' && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left p-3 text-sm font-medium text-gray-400">Rank</th>
                  <th className="text-left p-3 text-sm font-medium text-gray-400">Agent</th>
                  <th 
                    className="text-right p-3 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                    onClick={() => handleSort('totalPnL')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Total P&L
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th 
                    className="text-right p-3 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                    onClick={() => handleSort('winRate')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Win Rate
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th 
                    className="text-right p-3 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                    onClick={() => handleSort('sharpeRatio')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Sharpe
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th 
                    className="text-right p-3 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                    onClick={() => handleSort('totalTrades')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Trades
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th 
                    className="text-right p-3 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                    onClick={() => handleSort('consistency')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Consistency
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="text-center p-3 text-sm font-medium text-gray-400">Compare</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedAgents.map((agent, index) => {
                  const pnlIndicator = getPerformanceIndicator(agent.totalPnL, 'pnl')
                  const winRateIndicator = getPerformanceIndicator(agent.winRate, 'percent')
                  const sharpeIndicator = getPerformanceIndicator(agent.sharpeRatio, 'ratio')
                  
                  return (
                    <motion.tr
                      key={agent.agentId}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className={`border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer ${
                        selectedAgents.has(agent.agentId) ? 'bg-blue-900/20' : ''
                      }`}
                      onClick={() => onAgentSelect?.(agent.agentId)}
                    >
                      <td className="p-3">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                          getRankBadgeColor(index + 1)
                        }`}>
                          #{index + 1}
                        </span>
                      </td>
                      <td className="p-3">
                        <div>
                          <div className="font-medium text-white">{agent.agentName}</div>
                          <div className="text-xs text-gray-400">{agent.agentType}</div>
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <pnlIndicator.icon className={`w-4 h-4 ${pnlIndicator.color}`} />
                          <span className={`font-medium ${pnlIndicator.color}`}>
                            {formatCurrency(agent.totalPnL)}
                          </span>
                        </div>
                        <div className="text-xs text-gray-400">
                          {formatPercent(agent.contribution)}% contribution
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <winRateIndicator.icon className={`w-4 h-4 ${winRateIndicator.color}`} />
                          <span className={`font-medium ${winRateIndicator.color}`}>
                            {formatPercent(agent.winRate)}
                          </span>
                        </div>
                        <div className="text-xs text-gray-400">
                          {agent.winningTrades}W / {agent.losingTrades}L
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <sharpeIndicator.icon className={`w-4 h-4 ${sharpeIndicator.color}`} />
                          <span className={`font-medium ${sharpeIndicator.color}`}>
                            {formatNumber(agent.sharpeRatio, 2)}
                          </span>
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <span className="font-medium text-white">{agent.totalTrades}</span>
                      </td>
                      <td className="p-3 text-right">
                        <div className={`font-medium ${getPerformanceIndicator(agent.consistency, 'percent').color}`}>
                          {formatNumber(agent.consistency, 0)}%
                        </div>
                        <div className="text-xs text-gray-400">
                          Reliability: {formatNumber(agent.reliability, 0)}%
                        </div>
                      </td>
                      <td className="p-3 text-center">
                        <input
                          type="checkbox"
                          checked={selectedAgents.has(agent.agentId)}
                          onChange={() => toggleAgentSelection(agent.agentId)}
                          className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                        />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {viewMode === 'charts' && performanceComparisonData && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-white mb-4">Performance Comparison (bar chart) - Strategy Analysis</h3>
              <div className="h-64">
                <Bar
                  data={performanceComparisonData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        labels: { color: 'rgba(255, 255, 255, 0.7)' }
                      }
                    },
                    scales: {
                      x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: 'rgba(255, 255, 255, 0.5)' }
                      },
                      y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: {
                          color: 'rgba(255, 255, 255, 0.5)',
                          callback: (value) => formatCurrency(value as number)
                        }
                      },
                      y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        ticks: {
                          color: 'rgba(255, 255, 255, 0.5)',
                          callback: (value) => formatPercent(value as number)
                        },
                        grid: { drawOnChartArea: false }
                      }
                    }
                  }}
                />
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium text-white mb-4">Risk-Return Analysis (scatter plot) - Trading Patterns</h3>
              <div className="h-64">
                <Scatter
                  data={riskReturnData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { display: false },
                      tooltip: {
                        callbacks: {
                          label: (context) => {
                            const point = context.raw as any
                            return [
                              point.agentName,
                              `Volatility: ${formatPercent(point.x)}`,
                              `Avg P&L per Trade: ${formatCurrency(point.y)}`
                            ]
                          }
                        }
                      }
                    },
                    scales: {
                      x: {
                        title: {
                          display: true,
                          text: 'Volatility (%)',
                          color: 'rgba(255, 255, 255, 0.7)'
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { 
                          color: 'rgba(255, 255, 255, 0.5)',
                          callback: (value) => formatPercent(value as number)
                        }
                      },
                      y: {
                        title: {
                          display: true,
                          text: 'Avg P&L per Trade',
                          color: 'rgba(255, 255, 255, 0.7)'
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { 
                          color: 'rgba(255, 255, 255, 0.5)',
                          callback: (value) => formatCurrency(value as number)
                        }
                      }
                    }
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {viewMode === 'radar' && radarData && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-white mb-4">Multi-dimensional Comparison</h3>
              <div className="h-96">
                <Radar
                  data={radarData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        labels: { color: 'rgba(255, 255, 255, 0.7)' }
                      }
                    },
                    scales: {
                      r: {
                        angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        pointLabels: { color: 'rgba(255, 255, 255, 0.7)' },
                        ticks: { 
                          color: 'rgba(255, 255, 255, 0.3)',
                          backdropColor: 'transparent'
                        },
                        min: 0,
                        max: 100
                      }
                    }
                  }}
                />
              </div>
            </div>

            {/* Agent details */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents
                .filter(agent => selectedAgents.has(agent.agentId))
                .map(agent => (
                  <div key={agent.agentId} className="bg-gray-800 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-white">{agent.agentName}</h4>
                      <Trophy className={`w-4 h-4 ${
                        agent.totalPnL > 0 ? 'text-yellow-400' : 'text-gray-400'
                      }`} />
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Preferred Symbols:</span>
                        <span className="text-white">
                          {agent.preferredSymbols.slice(0, 2).join(', ')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Strategy Patterns:</span>
                        <span className="text-white">
                          {agent.patterns.slice(0, 2).join(', ')}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500">
                        Analyzes strategy patterns for trading performance
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Active Hours:</span>
                        <span className="text-white">
                          {agent.activeHours.join(', ')}:00
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Best Trade:</span>
                        <span className="text-green-400">
                          {formatCurrency(agent.bestTrade)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Worst Trade:</span>
                        <span className="text-red-400">
                          {formatCurrency(agent.worstTrade)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}