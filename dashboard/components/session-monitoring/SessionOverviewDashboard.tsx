'use client'

import React from 'react'
import Card from '@/components/ui/Card'
import Grid from '@/components/ui/Grid'

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
  positionSizing: {
    stabilityFactor: number
    validationFactor: number
    volatilityFactor: number
    totalReduction: number
    maxPosition: number
    currentRisk: number
  }
}

interface SessionOverviewDashboardProps {
  sessionData: SessionData[]
  currentSession: TradingSession
  onSessionSelect: (session: TradingSession) => void
}

const SessionOverviewDashboard: React.FC<SessionOverviewDashboardProps> = ({
  sessionData,
  currentSession,
  onSessionSelect
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'border-green-500/50 bg-green-500/10'
      case 'upcoming': return 'border-yellow-500/50 bg-yellow-500/10'
      default: return 'border-gray-500/30 bg-gray-500/5'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return '🟢'
      case 'upcoming': return '🟡'
      default: return '⚫'
    }
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
    <div className="space-y-6">
      {/* Session Cards Grid */}
      <Grid cols={{ default: 1, md: 2, xl: 5 }}>
        {sessionData.map((session) => (
          <Card
            key={session.session}
            title={
              <div className="flex items-center justify-between">
                <span className="text-lg font-bold">{session.name}</span>
                <span className="text-sm">{getStatusIcon(session.status)}</span>
              </div>
            }
            className={`cursor-pointer transition-all hover:scale-105 ${getStatusColor(session.status)} ${
              session.session === currentSession ? 'ring-2 ring-blue-500' : ''
            }`}
            onClick={() => onSessionSelect(session.session)}
          >
            <div className="space-y-3">
              {/* Basic Info */}
              <div className="text-xs text-gray-400">
                <div>{session.hours}</div>
                <div>{session.timezone}</div>
                <div className="capitalize font-medium mt-1 text-white">{session.status}</div>
              </div>

              {/* Key Metrics */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <div className="text-gray-400">Win Rate</div>
                  <div className={`font-bold ${
                    session.metrics.winRate > 70 ? 'text-green-400' :
                    session.metrics.winRate > 60 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {session.metrics.winRate.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Avg R:R</div>
                  <div className="text-blue-400 font-bold">
                    {session.metrics.avgRiskReward.toFixed(1)}:1
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Trades</div>
                  <div className="text-white font-medium">{session.metrics.totalTrades}</div>
                </div>
                <div>
                  <div className="text-gray-400">P.Factor</div>
                  <div className={`font-bold ${
                    session.metrics.profitFactor > 1.5 ? 'text-green-400' :
                    session.metrics.profitFactor > 1.0 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {session.metrics.profitFactor.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* Position Sizing Status */}
              <div className="pt-2 border-t border-gray-700">
                <div className="text-xs text-gray-400 mb-1">Position Reduction</div>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-red-500 h-2 rounded-full transition-all"
                      style={{ width: `${session.metrics.positionSizeReduction}%` }}
                    ></div>
                  </div>
                  <div className="text-xs text-red-400 font-bold">
                    {session.metrics.positionSizeReduction}%
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Phase {session.metrics.currentPhase} • {session.metrics.capitalAllocation}% Capital
                </div>
              </div>
            </div>
          </Card>
        ))}
      </Grid>

      {/* Summary Statistics */}
      <Grid cols={{ default: 1, md: 2, lg: 4 }}>
        <Card title="Best Performing Session">
          <div className="space-y-2">
            {(() => {
              const bestSession = sessionData.reduce((best, current) =>
                current.metrics.profitFactor > best.metrics.profitFactor ? current : best
              )
              return (
                <>
                  <div className="text-xl font-bold text-green-400 capitalize">
                    {bestSession.name}
                  </div>
                  <div className="text-sm text-gray-400">
                    Profit Factor: {bestSession.metrics.profitFactor.toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-400">
                    Win Rate: {bestSession.metrics.winRate.toFixed(1)}%
                  </div>
                </>
              )
            })()}
          </div>
        </Card>

        <Card title="Most Conservative Session">
          <div className="space-y-2">
            {(() => {
              const conservativeSession = sessionData.reduce((most, current) =>
                current.metrics.positionSizeReduction > most.metrics.positionSizeReduction ? current : most
              )
              return (
                <>
                  <div className="text-xl font-bold text-red-400 capitalize">
                    {conservativeSession.name}
                  </div>
                  <div className="text-sm text-gray-400">
                    Size Reduction: {conservativeSession.metrics.positionSizeReduction}%
                  </div>
                  <div className="text-sm text-gray-400">
                    Max Position: {conservativeSession.positionSizing.maxPosition}%
                  </div>
                </>
              )
            })()}
          </div>
        </Card>

        <Card title="Total Trades Today">
          <div className="space-y-2">
            <div className="text-2xl font-bold text-blue-400">
              {sessionData.reduce((sum, session) => sum + session.metrics.totalTrades, 0)}
            </div>
            <div className="text-sm text-gray-400">
              Across all sessions
            </div>
            <div className="text-xs text-gray-500">
              Active: {sessionData.find(s => s.status === 'active')?.metrics.totalTrades || 0} trades
            </div>
          </div>
        </Card>

        <Card title="Average Position Reduction">
          <div className="space-y-2">
            <div className="text-2xl font-bold text-orange-400">
              {(sessionData.reduce((sum, session) => sum + session.metrics.positionSizeReduction, 0) / sessionData.length).toFixed(0)}%
            </div>
            <div className="text-sm text-gray-400">
              Due to forward test metrics
            </div>
            <div className="text-xs text-gray-500">
              Range: {Math.min(...sessionData.map(s => s.metrics.positionSizeReduction))}% - {Math.max(...sessionData.map(s => s.metrics.positionSizeReduction))}%
            </div>
          </div>
        </Card>
      </Grid>

      {/* Session Timeline */}
      <Card title="24-Hour Session Timeline">
        <div className="relative">
          {/* Timeline Bar */}
          <div className="flex h-16 bg-gray-800 rounded-lg overflow-hidden">
            {/* Sydney: 22:00-07:00 GMT (9 hours) */}
            <div className="flex-none bg-purple-600/30 border-r border-gray-600" style={{ width: '37.5%' }}>
              <div className="p-2 h-full flex flex-col justify-center">
                <div className="text-xs font-bold text-purple-300">Sydney</div>
                <div className="text-xs text-gray-400">22:00-07:00</div>
              </div>
            </div>

            {/* Tokyo: 00:00-09:00 GMT (overlaps with Sydney) */}
            <div className="flex-none bg-red-600/30 border-r border-gray-600" style={{ width: '37.5%' }}>
              <div className="p-2 h-full flex flex-col justify-center">
                <div className="text-xs font-bold text-red-300">Tokyo</div>
                <div className="text-xs text-gray-400">00:00-09:00</div>
              </div>
            </div>

            {/* London: 07:00-16:00 GMT */}
            <div className="flex-none bg-green-600/30 border-r border-gray-600" style={{ width: '37.5%' }}>
              <div className="p-2 h-full flex flex-col justify-center">
                <div className="text-xs font-bold text-green-300">London</div>
                <div className="text-xs text-gray-400">07:00-16:00</div>
              </div>
            </div>

            {/* New York: 13:00-22:00 GMT */}
            <div className="flex-none bg-blue-600/30" style={{ width: '37.5%' }}>
              <div className="p-2 h-full flex flex-col justify-center">
                <div className="text-xs font-bold text-blue-300">New York</div>
                <div className="text-xs text-gray-400">13:00-22:00</div>
              </div>
            </div>
          </div>

          {/* Current Time Indicator */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-yellow-400 shadow-lg"
            style={{
              left: `${((new Date().getUTCHours() + new Date().getUTCMinutes() / 60) / 24) * 100}%`
            }}
          >
            <div className="absolute -top-6 -left-8 bg-yellow-400 text-black px-2 py-1 rounded text-xs font-bold">
              NOW
            </div>
          </div>

          {/* Overlap Indicators */}
          <div className="mt-4 flex justify-between text-xs text-gray-400">
            <div>🟢 Active Session</div>
            <div>🟡 Upcoming Session</div>
            <div>⚫ Inactive Session</div>
            <div>📊 High Volume Overlaps: 13:00-16:00, 00:00-02:00 GMT</div>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default SessionOverviewDashboard