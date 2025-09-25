'use client'

import React, { useState, useEffect } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import SessionOverviewDashboard from '@/components/session-monitoring/SessionOverviewDashboard'
import SessionDetailView from '@/components/session-monitoring/SessionDetailView'
import SessionPerformanceMetrics from '@/components/session-monitoring/SessionPerformanceMetrics'
import PositionSizingMonitor from '@/components/session-monitoring/PositionSizingMonitor'
import ForwardTestMetricsPanel from '@/components/session-monitoring/ForwardTestMetricsPanel'
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

const MOCK_SESSION_DATA: SessionData[] = [
  {
    session: 'sydney',
    name: 'Sydney Session',
    timezone: 'AEDT',
    hours: '22:00-07:00 GMT',
    status: 'inactive',
    metrics: {
      winRate: 68.5,
      avgRiskReward: 3.5,
      totalTrades: 142,
      profitFactor: 1.85,
      maxDrawdown: -4.2,
      confidenceThreshold: 78,
      positionSizeReduction: 45,
      currentPhase: 1,
      capitalAllocation: 10
    },
    recentTrades: [],
    positionSizing: {
      stabilityFactor: 0.40,
      validationFactor: 0.20,
      volatilityFactor: 0.85,
      totalReduction: 0.068,
      maxPosition: 15.0,
      currentRisk: 1.5
    }
  },
  {
    session: 'tokyo',
    name: 'Tokyo Session',
    timezone: 'JST',
    hours: '00:00-09:00 GMT',
    status: 'inactive',
    metrics: {
      winRate: 74.2,
      avgRiskReward: 4.0,
      totalTrades: 98,
      profitFactor: 2.12,
      maxDrawdown: -3.8,
      confidenceThreshold: 85,
      positionSizeReduction: 35,
      currentPhase: 1,
      capitalAllocation: 10
    },
    recentTrades: [],
    positionSizing: {
      stabilityFactor: 0.40,
      validationFactor: 0.20,
      volatilityFactor: 0.95,
      totalReduction: 0.076,
      maxPosition: 20.0,
      currentRisk: 1.8
    }
  },
  {
    session: 'london',
    name: 'London Session',
    timezone: 'GMT',
    hours: '07:00-16:00 GMT',
    status: 'active',
    metrics: {
      winRate: 71.8,
      avgRiskReward: 3.2,
      totalTrades: 287,
      profitFactor: 1.94,
      maxDrawdown: -5.1,
      confidenceThreshold: 72,
      positionSizeReduction: 42,
      currentPhase: 1,
      capitalAllocation: 10
    },
    recentTrades: [
      { id: 'LDN_001', pair: 'EUR_USD', type: 'BUY', size: 8500, pnl: 142.50, time: '14:35' },
      { id: 'LDN_002', pair: 'GBP_USD', type: 'SELL', size: 6200, pnl: -85.20, time: '13:22' },
      { id: 'LDN_003', pair: 'USD_JPY', type: 'BUY', size: 9100, pnl: 201.75, time: '12:18' }
    ],
    positionSizing: {
      stabilityFactor: 0.40,
      validationFactor: 0.20,
      volatilityFactor: 0.80,
      totalReduction: 0.064,
      maxPosition: 25.0,
      currentRisk: 2.2
    }
  },
  {
    session: 'new_york',
    name: 'New York Session',
    timezone: 'EST',
    hours: '13:00-22:00 GMT',
    status: 'upcoming',
    metrics: {
      winRate: 69.3,
      avgRiskReward: 2.8,
      totalTrades: 201,
      profitFactor: 1.76,
      maxDrawdown: -6.3,
      confidenceThreshold: 70,
      positionSizeReduction: 48,
      currentPhase: 1,
      capitalAllocation: 10
    },
    recentTrades: [],
    positionSizing: {
      stabilityFactor: 0.40,
      validationFactor: 0.20,
      volatilityFactor: 0.75,
      totalReduction: 0.060,
      maxPosition: 22.0,
      currentRisk: 2.0
    }
  },
  {
    session: 'overlap',
    name: 'Overlap Periods',
    timezone: 'GMT',
    hours: '13:00-16:00, 00:00-02:00',
    status: 'inactive',
    metrics: {
      winRate: 66.4,
      avgRiskReward: 2.8,
      totalTrades: 156,
      profitFactor: 1.68,
      maxDrawdown: -4.9,
      confidenceThreshold: 70,
      positionSizeReduction: 52,
      currentPhase: 1,
      capitalAllocation: 10
    },
    recentTrades: [],
    positionSizing: {
      stabilityFactor: 0.40,
      validationFactor: 0.20,
      volatilityFactor: 0.70,
      totalReduction: 0.056,
      maxPosition: 18.0,
      currentRisk: 1.6
    }
  }
]

export default function SessionMonitoringPage() {
  const [selectedSession, setSelectedSession] = useState<TradingSession | null>(null)
  const [sessionData, setSessionData] = useState<SessionData[]>(MOCK_SESSION_DATA)
  const [refreshInterval, setRefreshInterval] = useState<number>(30)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  // Auto-refresh data
  useEffect(() => {
    const interval = setInterval(() => {
      // In real implementation, this would fetch fresh data from API
      setLastUpdate(new Date())
    }, refreshInterval * 1000)

    return () => clearInterval(interval)
  }, [refreshInterval])

  // Get current session based on GMT time
  const getCurrentSession = (): TradingSession => {
    const now = new Date()
    const hour = now.getUTCHours()

    if (hour >= 22 || hour < 7) {
      if (hour >= 0 && hour < 2) return 'overlap'
      return hour >= 22 ? 'sydney' : 'tokyo'
    } else if (hour >= 7 && hour < 16) {
      return 'london'
    } else if (hour >= 13 && hour < 22) {
      if (hour >= 13 && hour < 16) return 'overlap'
      return 'new_york'
    }
    return 'new_york'
  }

  const currentSession = getCurrentSession()

  // Update session status based on current time
  useEffect(() => {
    const updateSessionStatus = () => {
      const updated = sessionData.map(session => ({
        ...session,
        status: session.session === currentSession ? 'active' as const :
               (session.session === getNextSession() ? 'upcoming' as const : 'inactive' as const)
      }))
      setSessionData(updated)
    }

    updateSessionStatus()
    const interval = setInterval(updateSessionStatus, 60000) // Update every minute

    return () => clearInterval(interval)
  }, [currentSession, sessionData])

  const getNextSession = (): TradingSession => {
    const sessions: TradingSession[] = ['sydney', 'tokyo', 'london', 'new_york', 'overlap']
    const currentIndex = sessions.indexOf(currentSession)
    return sessions[(currentIndex + 1) % sessions.length]
  }

  const handleRefresh = async () => {
    // In real implementation, this would call the API
    setLastUpdate(new Date())
  }

  const activeSessionData = sessionData.find(s => s.session === currentSession)

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className=\"space-y-8\">
          {/* Header */}
          <div className=\"flex items-center justify-between\">
            <div>
              <h1 className=\"text-3xl font-bold text-white mb-2\">Session-Specific Monitoring</h1>
              <p className=\"text-gray-400\">
                Real-time performance tracking and position sizing controls by trading session
              </p>
            </div>
            <div className=\"flex items-center space-x-4\">
              <div className=\"text-sm text-gray-400\">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </div>
              <button
                onClick={handleRefresh}
                className=\"bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors\"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Current Session Alert */}
          {activeSessionData && (
            <Card
              title={`🟢 ${activeSessionData.name} Active`}
              className=\"border-green-500/30 bg-green-500/10\"
            >
              <div className=\"grid grid-cols-1 md:grid-cols-4 gap-4\">
                <div>
                  <p className=\"text-sm text-gray-400\">Time Frame</p>
                  <p className=\"text-white font-medium\">{activeSessionData.hours}</p>
                </div>
                <div>
                  <p className=\"text-sm text-gray-400\">Win Rate</p>
                  <p className=\"text-green-400 font-bold\">{activeSessionData.metrics.winRate.toFixed(1)}%</p>
                </div>
                <div>
                  <p className=\"text-sm text-gray-400\">Avg R:R</p>
                  <p className=\"text-blue-400 font-bold\">{activeSessionData.metrics.avgRiskReward.toFixed(1)}:1</p>
                </div>
                <div>
                  <p className=\"text-sm text-gray-400\">Position Size Reduction</p>
                  <p className=\"text-red-400 font-bold\">{activeSessionData.metrics.positionSizeReduction}%</p>
                </div>
              </div>
            </Card>
          )}

          {/* Session Overview Dashboard */}
          <SessionOverviewDashboard
            sessionData={sessionData}
            currentSession={currentSession}
            onSessionSelect={setSelectedSession}
          />

          {/* Forward Test Metrics */}
          <ForwardTestMetricsPanel />

          {/* Main Content Grid */}
          <Grid cols={{ default: 1, xl: 2 }}>
            {/* Session Performance Metrics */}
            <SessionPerformanceMetrics
              sessionData={sessionData}
              selectedSession={selectedSession || currentSession}
            />

            {/* Position Sizing Monitor */}
            <PositionSizingMonitor
              sessionData={sessionData}
              currentSession={currentSession}
            />
          </Grid>

          {/* Detailed Session View */}
          {selectedSession && (
            <SessionDetailView
              session={sessionData.find(s => s.session === selectedSession)!}
              onClose={() => setSelectedSession(null)}
            />
          )}

          {/* Settings */}
          <Card title=\"Monitoring Settings\">
            <div className=\"grid grid-cols-1 md:grid-cols-3 gap-4\">
              <div>
                <label className=\"block text-sm font-medium text-gray-400 mb-2\">
                  Refresh Interval
                </label>
                <select
                  value={refreshInterval}
                  onChange={(e) => setRefreshInterval(Number(e.target.value))}
                  className=\"w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white\"
                >
                  <option value={10}>10 seconds</option>
                  <option value={30}>30 seconds</option>
                  <option value={60}>1 minute</option>
                  <option value={300}>5 minutes</option>
                </select>
              </div>
              <div>
                <label className=\"block text-sm font-medium text-gray-400 mb-2\">
                  Current Time (GMT)
                </label>
                <div className=\"w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white\">
                  {new Date().toISOString().substr(11, 8)}
                </div>
              </div>
              <div>
                <label className=\"block text-sm font-medium text-gray-400 mb-2\">
                  Next Session
                </label>
                <div className=\"w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white capitalize\">
                  {getNextSession().replace('_', ' ')}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}