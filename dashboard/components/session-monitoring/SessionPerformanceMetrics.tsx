'use client'

import React, { useState } from 'react'
import Card from '@/components/ui/Card'

type TradingSession = 'sydney' | 'tokyo' | 'london' | 'new_york' | 'overlap'

interface SessionData {
  session: TradingSession
  name: string
  timezone: string
  hours: string
  status: 'active' | 'inactive' | 'upcoming'
  metrics: {
    winRate: number
    avgRiskReward: number
    totalTrades: number
    profitFactor: number
    maxDrawdown: number
    confidenceThreshold: number
    positionSizeReduction: number
    currentPhase: number
    capitalAllocation: number
  }
  recentTrades: any[]
  positionSizing: {
    stabilityFactor: number
    validationFactor: number
    volatilityFactor: number
    totalReduction: number
    maxPosition: number
    currentRisk: number
  }
}

interface SessionPerformanceMetricsProps {
  sessionData: SessionData[]
  selectedSession: TradingSession
}

const SessionPerformanceMetrics: React.FC<SessionPerformanceMetricsProps> = ({
  sessionData,
  selectedSession
}) => {
  const [timeframe, setTimeframe] = useState<'1d' | '1w' | '1m' | '3m'>('1w')

  const session = sessionData.find(s => s.session === selectedSession)

  if (!session) return null

  // Generate mock historical data for charts
  const generateChartData = (days: number) => {
    const data = []
    const baseValue = session.metrics.profitFactor

    for (let i = days; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)

      const variation = (Math.random() - 0.5) * 0.3
      const value = Math.max(0.5, baseValue + variation)

      data.push({
        date: date.toISOString().split('T')[0],
        profitFactor: value,
        winRate: Math.max(30, Math.min(90, session.metrics.winRate + (Math.random() - 0.5) * 10)),
        totalPnL: (Math.random() - 0.4) * 1000,
        trades: Math.floor(Math.random() * 20) + 5
      })
    }

    return data
  }

  const getTimeframeDays = () => {
    switch (timeframe) {
      case '1d': return 1
      case '1w': return 7
      case '1m': return 30
      case '3m': return 90
      default: return 7
    }
  }

  const chartData = generateChartData(getTimeframeDays())

  const getMetricColor = (value: number, thresholds: { good: number, ok: number }) => {
    if (value >= thresholds.good) return 'text-green-400'
    if (value >= thresholds.ok) return 'text-yellow-400'
    return 'text-red-400'
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  return (
    <Card
      title={
        <div className="flex items-center justify-between">
          <span>{session.name} Performance Metrics</span>
          <div className="flex space-x-1">
            {(['1d', '1w', '1m', '3m'] as const).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  timeframe === tf
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                {tf.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Key Performance Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 p-3 rounded">
            <div className="text-xs text-gray-400 mb-1">Win Rate</div>
            <div className={`text-lg font-bold ${getMetricColor(session.metrics.winRate, { good: 70, ok: 60 })}`}>
              {session.metrics.winRate.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">
              Target: {session.metrics.confidenceThreshold}%
            </div>
          </div>

          <div className="bg-gray-800 p-3 rounded">
            <div className="text-xs text-gray-400 mb-1">Profit Factor</div>
            <div className={`text-lg font-bold ${getMetricColor(session.metrics.profitFactor, { good: 1.5, ok: 1.2 })}`}>
              {session.metrics.profitFactor.toFixed(2)}
            </div>
            <div className="text-xs text-gray-500">
              Avg R:R {session.metrics.avgRiskReward.toFixed(1)}:1
            </div>
          </div>

          <div className="bg-gray-800 p-3 rounded">
            <div className="text-xs text-gray-400 mb-1">Max Drawdown</div>
            <div className={`text-lg font-bold ${
              session.metrics.maxDrawdown > -5 ? 'text-green-400' :
              session.metrics.maxDrawdown > -10 ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {session.metrics.maxDrawdown.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">
              {session.metrics.totalTrades} trades total
            </div>
          </div>

          <div className="bg-gray-800 p-3 rounded">
            <div className="text-xs text-gray-400 mb-1">Position Reduction</div>
            <div className="text-lg font-bold text-red-400">
              -{session.metrics.positionSizeReduction}%
            </div>
            <div className="text-xs text-gray-500">
              Phase {session.metrics.currentPhase} limits
            </div>
          </div>
        </div>

        {/* Performance Chart (Simulated) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-300">Profit Factor Trend</h4>
            <div className="text-xs text-gray-500">
              {timeframe} timeframe • {chartData.length} data points
            </div>
          </div>

          {/* Simple ASCII Chart */}
          <div className="bg-gray-800 p-4 rounded font-mono text-xs">
            <div className="grid grid-cols-10 gap-1 h-32">
              {chartData.slice(-10).map((point, index) => {
                const height = Math.max(10, (point.profitFactor / 3) * 100)
                return (
                  <div key={index} className="flex flex-col justify-end">
                    <div
                      className={`rounded-t transition-all ${
                        point.profitFactor > 1.5 ? 'bg-green-500' :
                        point.profitFactor > 1.2 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ height: `${Math.min(height, 90)}%` }}
                      title={`${point.date}: ${point.profitFactor.toFixed(2)}`}
                    ></div>
                    <div className="text-center text-gray-500 mt-1">
                      {point.date.slice(-2)}
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="flex justify-between text-gray-500 mt-2 text-xs">
              <span>PF: 0.5</span>
              <span>1.0</span>
              <span>1.5</span>
              <span>2.0+</span>
            </div>
          </div>
        </div>

        {/* Session-Specific Targets */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-300">Session Requirements & Status</h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Confidence Threshold</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{session.metrics.confidenceThreshold}%</span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    session.metrics.winRate >= session.metrics.confidenceThreshold
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}>
                    {session.metrics.winRate >= session.metrics.confidenceThreshold ? 'MET' : 'MISS'}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Risk-Reward Target</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{session.metrics.avgRiskReward.toFixed(1)}:1</span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    session.metrics.avgRiskReward >= 2.5
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {session.metrics.avgRiskReward >= 2.5 ? 'GOOD' : 'FAIR'}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Max Position Size</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{session.positionSizing.maxPosition}%</span>
                  <span className="text-xs text-gray-500">
                    of capital
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Capital Allocation</span>
                <div className="flex items-center space-x-2">
                  <span className="text-orange-400">{session.metrics.capitalAllocation}%</span>
                  <span className="text-xs text-gray-500">
                    Phase {session.metrics.currentPhase}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Current Risk</span>
                <div className="flex items-center space-x-2">
                  <span className="text-blue-400">{session.positionSizing.currentRisk}%</span>
                  <span className="text-xs text-gray-500">
                    per trade
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Total Reduction</span>
                <div className="flex items-center space-x-2">
                  <span className="text-red-400">-{(session.positionSizing.totalReduction * 100).toFixed(1)}%</span>
                  <span className="text-xs text-gray-500">
                    final sizing
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Trades Summary */}
        {session.recentTrades.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-300">Recent Trades</h4>
            <div className="space-y-2">
              {session.recentTrades.slice(0, 3).map((trade, index) => (
                <div key={index} className="flex items-center justify-between bg-gray-800 p-2 rounded text-sm">
                  <div className="flex items-center space-x-3">
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      trade.type === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {trade.type}
                    </span>
                    <span className="text-white font-medium">{trade.pair}</span>
                    <span className="text-gray-400">{trade.size.toLocaleString()} units</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-gray-500">{trade.time}</span>
                    <span className={`font-bold ${
                      trade.pnl > 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {trade.pnl > 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}

export default SessionPerformanceMetrics