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

interface SessionDetailViewProps {
  session: SessionData
  onClose: () => void
}

const SessionDetailView: React.FC<SessionDetailViewProps> = ({
  session,
  onClose
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'trades' | 'risk' | 'settings'>('overview')

  // Mock extended data for the session
  const extendedMetrics = {
    sharpeRatio: 1.42,
    sortinoRatio: 1.89,
    calmarRatio: 2.15,
    maxRunup: 8.3,
    avgWinTime: '2h 45m',
    avgLossTime: '1h 20m',
    largestWin: 450.75,
    largestLoss: -285.20,
    consecutiveWins: 8,
    consecutiveLosses: 3,
    profitabilityByHour: {
      0: 0.65, 1: 0.72, 2: 0.68, 3: 0.71, 4: 0.69, 5: 0.74,
      6: 0.78, 7: 0.82, 8: 0.75, 9: 0.71, 10: 0.69, 11: 0.73
    }
  }

  const instruments = [
    { pair: 'EUR_USD', trades: 87, winRate: 73.5, avgRR: 3.2, pnl: 2450.75 },
    { pair: 'GBP_USD', trades: 65, winRate: 69.2, avgRR: 3.8, pnl: 1890.45 },
    { pair: 'USD_JPY', trades: 92, winRate: 71.7, avgRR: 2.9, pnl: 2103.20 },
    { pair: 'AUD_USD', trades: 43, winRate: 67.4, avgRR: 3.5, pnl: 1205.85 }
  ]

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-400'
      case 'upcoming': return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center space-x-4">
            <div>
              <h2 className="text-2xl font-bold text-white capitalize">{session.name}</h2>
              <div className="flex items-center space-x-4 mt-1">
                <span className="text-sm text-gray-400">{session.hours} • {session.timezone}</span>
                <span className={`text-sm font-medium capitalize ${getStatusColor(session.status)}`}>
                  {session.status}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700">
          {(['overview', 'trades', 'risk', 'settings'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 text-sm font-medium transition-colors capitalize ${
                activeTab === tab
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Key Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <div className="bg-gray-800 p-4 rounded">
                  <div className="text-sm text-gray-400 mb-1">Win Rate</div>
                  <div className="text-2xl font-bold text-green-400">{session.metrics.winRate.toFixed(1)}%</div>
                  <div className="text-xs text-gray-500">Target: {session.metrics.confidenceThreshold}%</div>
                </div>

                <div className="bg-gray-800 p-4 rounded">
                  <div className="text-sm text-gray-400 mb-1">Profit Factor</div>
                  <div className="text-2xl font-bold text-blue-400">{session.metrics.profitFactor.toFixed(2)}</div>
                  <div className="text-xs text-gray-500">Sharpe: {extendedMetrics.sharpeRatio.toFixed(2)}</div>
                </div>

                <div className="bg-gray-800 p-4 rounded">
                  <div className="text-sm text-gray-400 mb-1">Max Drawdown</div>
                  <div className="text-2xl font-bold text-red-400">{session.metrics.maxDrawdown.toFixed(1)}%</div>
                  <div className="text-xs text-gray-500">Max Runup: +{extendedMetrics.maxRunup}%</div>
                </div>

                <div className="bg-gray-800 p-4 rounded">
                  <div className="text-sm text-gray-400 mb-1">Total Trades</div>
                  <div className="text-2xl font-bold text-purple-400">{session.metrics.totalTrades}</div>
                  <div className="text-xs text-gray-500">Avg R:R {session.metrics.avgRiskReward.toFixed(1)}:1</div>
                </div>
              </div>

              {/* Extended Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-800 p-4 rounded">
                  <div className="text-sm text-gray-400 mb-3">Risk-Adjusted Returns</div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Sharpe Ratio:</span>
                      <span className="text-green-400 font-bold">{extendedMetrics.sharpeRatio.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Sortino Ratio:</span>
                      <span className="text-green-400 font-bold">{extendedMetrics.sortinoRatio.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Calmar Ratio:</span>
                      <span className="text-green-400 font-bold">{extendedMetrics.calmarRatio.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-800 p-4 rounded">
                  <div className="text-sm text-gray-400 mb-3">Trade Characteristics</div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Avg Win Time:</span>
                      <span className="text-blue-400 font-bold">{extendedMetrics.avgWinTime}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Avg Loss Time:</span>
                      <span className="text-red-400 font-bold">{extendedMetrics.avgLossTime}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Largest Win:</span>
                      <span className="text-green-400 font-bold">{formatCurrency(extendedMetrics.largestWin)}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-800 p-4 rounded">
                  <div className="text-sm text-gray-400 mb-3">Streaks</div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Max Winning:</span>
                      <span className="text-green-400 font-bold">{extendedMetrics.consecutiveWins} trades</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Max Losing:</span>
                      <span className="text-red-400 font-bold">{extendedMetrics.consecutiveLosses} trades</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Largest Loss:</span>
                      <span className="text-red-400 font-bold">{formatCurrency(extendedMetrics.largestLoss)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Instrument Breakdown */}
              <div className="bg-gray-800 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-300 mb-4">Performance by Instrument</h4>
                <div className="space-y-3">
                  {instruments.map((instrument, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-700 p-3 rounded">
                      <div className="flex items-center space-x-4">
                        <div className="font-bold text-white">{instrument.pair}</div>
                        <div className="text-sm text-gray-400">{instrument.trades} trades</div>
                      </div>
                      <div className="flex items-center space-x-6">
                        <div className="text-sm">
                          <span className="text-gray-400">Win Rate:</span>
                          <span className="ml-1 text-green-400 font-bold">{instrument.winRate.toFixed(1)}%</span>
                        </div>
                        <div className="text-sm">
                          <span className="text-gray-400">Avg R:R:</span>
                          <span className="ml-1 text-blue-400 font-bold">{instrument.avgRR.toFixed(1)}:1</span>
                        </div>
                        <div className="text-sm">
                          <span className="text-gray-400">P&L:</span>
                          <span className={`ml-1 font-bold ${instrument.pnl > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatCurrency(instrument.pnl)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Trades Tab */}
          {activeTab === 'trades' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-white">Recent Trades</h3>
                <div className="flex space-x-2">
                  <select className="bg-gray-800 border border-gray-600 rounded px-3 py-1 text-white text-sm">
                    <option>All Pairs</option>
                    <option>EUR_USD</option>
                    <option>GBP_USD</option>
                    <option>USD_JPY</option>
                  </select>
                  <select className="bg-gray-800 border border-gray-600 rounded px-3 py-1 text-white text-sm">
                    <option>All Outcomes</option>
                    <option>Winners</option>
                    <option>Losers</option>
                  </select>
                </div>
              </div>

              {session.recentTrades.length > 0 ? (
                <div className="space-y-2">
                  {session.recentTrades.map((trade, index) => (
                    <div key={index} className="bg-gray-800 p-4 rounded">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <span className={`px-2 py-1 rounded text-xs font-bold ${
                            trade.type === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                          }`}>
                            {trade.type}
                          </span>
                          <span className="text-white font-medium">{trade.pair}</span>
                          <span className="text-gray-400">{trade.size.toLocaleString()} units</span>
                          <span className="text-gray-500 text-sm">{trade.time}</span>
                        </div>
                        <div className="flex items-center space-x-4">
                          <span className={`font-bold ${trade.pnl > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {trade.pnl > 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                          </span>
                          <button className="text-blue-400 hover:text-blue-300 text-sm">
                            Details
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="text-gray-400">No recent trades for this session</div>
                </div>
              )}
            </div>
          )}

          {/* Risk Tab */}
          {activeTab === 'risk' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-white">Risk Management Settings</h3>

              {/* Position Sizing Breakdown */}
              <div className="bg-gray-800 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-300 mb-4">Position Sizing Factors</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Stability Factor:</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-24 bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-red-500 h-2 rounded-full"
                          style={{ width: `${session.positionSizing.stabilityFactor * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-red-400 font-bold">{(session.positionSizing.stabilityFactor * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Validation Factor:</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-24 bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-red-500 h-2 rounded-full"
                          style={{ width: `${session.positionSizing.validationFactor * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-red-400 font-bold">{(session.positionSizing.validationFactor * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Volatility Factor:</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-24 bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-yellow-500 h-2 rounded-full"
                          style={{ width: `${session.positionSizing.volatilityFactor * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-yellow-400 font-bold">{(session.positionSizing.volatilityFactor * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-gray-700">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-300 font-medium">Total Reduction:</span>
                      <span className="text-red-400 font-bold">
                        -{((1 - session.positionSizing.totalReduction) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Limits */}
              <div className="bg-gray-800 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-300 mb-4">Session Risk Limits</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Max Position Size</div>
                    <div className="text-lg font-bold text-blue-400">{session.positionSizing.maxPosition}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Risk Per Trade</div>
                    <div className="text-lg font-bold text-yellow-400">{session.positionSizing.currentRisk}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Capital Allocation</div>
                    <div className="text-lg font-bold text-orange-400">{session.metrics.capitalAllocation}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Current Phase</div>
                    <div className="text-lg font-bold text-purple-400">Phase {session.metrics.currentPhase}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-white">Session Configuration</h3>

              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded p-4">
                <div className="text-sm text-yellow-400 font-medium mb-2">⚠️ Configuration Notice</div>
                <div className="text-sm text-gray-300">
                  Session settings are managed by the forward test position sizing system.
                  Most parameters are automatically adjusted based on performance metrics.
                </div>
              </div>

              <div className="bg-gray-800 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-300 mb-4">Current Configuration</h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Confidence Threshold:</span>
                    <span className="text-white">{session.metrics.confidenceThreshold}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Required Risk-Reward:</span>
                    <span className="text-white">{session.metrics.avgRiskReward.toFixed(1)}:1 minimum</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Max Concurrent Positions:</span>
                    <span className="text-white">5 positions</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Session Status:</span>
                    <span className={`font-medium capitalize ${getStatusColor(session.status)}`}>
                      {session.status}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex space-x-2">
                <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors">
                  Export Settings
                </button>
                <button className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors">
                  Reset to Defaults
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SessionDetailView