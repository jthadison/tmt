'use client'

import { useState, useMemo } from 'react'
import { PerformanceReport, PatternAnalysis } from '@/types/analytics'

// Simplified interface for trade analysis data
interface SimpleMetrics {
  totalPnL: number
  totalTrades: number
  winRate: number
  avgPnL: number
  volume?: number
}

interface TradeAnalysisType {
  byPattern: PatternAnalysis[]
  byTimeOfDay: Record<number, SimpleMetrics>
  byMarketSession: Record<string, SimpleMetrics>
  bySymbol: Record<string, SimpleMetrics>
  byDayOfWeek: Record<number, SimpleMetrics>
  byDuration: Record<string, SimpleMetrics>
  bySize: Record<string, SimpleMetrics>
}

/**
 * Props for TradeAnalysis component
 */
interface TradeAnalysisProps {
  /** Performance report data */
  performanceReport?: PerformanceReport
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
}

/**
 * Trade analysis dashboard component
 * Provides comprehensive analysis of trading patterns, timing, and performance
 */
export function TradeAnalysis({
  performanceReport,
  loading = false,
  error
}: TradeAnalysisProps) {
  const [activeAnalysis, setActiveAnalysis] = useState<'patterns' | 'timing' | 'sessions' | 'symbols' | 'duration'>('patterns')
  const [selectedPattern, setSelectedPattern] = useState<string | null>(null)

  // Generate mock trade analysis data (would come from API in real implementation)
  const tradeAnalysis = useMemo((): TradeAnalysisType | null => {
    if (!performanceReport) return null

    // Mock pattern analysis data
    const patterns: PatternAnalysis[] = [
      {
        pattern: 'Wyckoff Accumulation',
        count: 127,
        winRate: 73.2,
        avgPnL: 245.50,
        totalPnL: 31179.50,
        trend: 'up',
        rank: 1
      },
      {
        pattern: 'Supply & Demand',
        count: 89,
        winRate: 68.5,
        avgPnL: 198.30,
        totalPnL: 17648.70,
        trend: 'stable',
        rank: 2
      },
      {
        pattern: 'Market Structure Break',
        count: 156,
        winRate: 64.1,
        avgPnL: 112.80,
        totalPnL: 17596.80,
        trend: 'up',
        rank: 3
      },
      {
        pattern: 'Order Block',
        count: 203,
        winRate: 58.6,
        avgPnL: 87.40,
        totalPnL: 17742.20,
        trend: 'down',
        rank: 4
      },
      {
        pattern: 'Fair Value Gap',
        count: 134,
        winRate: 61.2,
        avgPnL: 95.60,
        totalPnL: 12810.40,
        trend: 'stable',
        rank: 5
      },
      {
        pattern: 'Liquidity Sweep',
        count: 78,
        winRate: 55.1,
        avgPnL: 156.20,
        totalPnL: 12183.60,
        trend: 'down',
        rank: 6
      }
    ]

    // Mock time-based analysis
    const hourlyData: Record<number, SimpleMetrics> = {}
    for (let hour = 0; hour < 24; hour++) {
      const baseVolume = hour >= 8 && hour <= 16 ? 1.5 : hour >= 13 && hour <= 21 ? 2.0 : 0.5
      const variance = Math.random() * 0.5
      
      hourlyData[hour] = {
        totalPnL: (baseVolume + variance) * 1000,
        totalTrades: Math.floor((baseVolume + variance) * 20),
        winRate: 50 + (Math.random() * 30),
        avgPnL: (baseVolume + variance) * 50,
        volume: baseVolume + variance
      }
    }

    // Mock session data
    const sessionData = {
      asian: {
        totalPnL: 8420.50,
        totalTrades: 145,
        winRate: 62.1,
        avgPnL: 58.07,
        volume: 1.2
      },
      london: {
        totalPnL: 15670.30,
        totalTrades: 298,
        winRate: 68.5,
        avgPnL: 52.58,
        volume: 2.1
      },
      newyork: {
        totalPnL: 22140.80,
        totalTrades: 387,
        winRate: 65.9,
        avgPnL: 57.22,
        volume: 2.8
      },
      overlap: {
        totalPnL: 31250.60,
        totalTrades: 456,
        winRate: 71.3,
        avgPnL: 68.53,
        volume: 3.5
      }
    }

    // Mock symbol data
    const symbolData = {
      'EURUSD': { totalPnL: 12450.30, totalTrades: 234, winRate: 67.1, avgPnL: 53.21 },
      'GBPUSD': { totalPnL: 8920.50, totalTrades: 156, winRate: 57.2, avgPnL: 57.18 },
      'USDJPY': { totalPnL: 15670.80, totalTrades: 298, winRate: 71.5, avgPnL: 52.58 },
      'AUDUSD': { totalPnL: 6780.20, totalTrades: 134, winRate: 50.6, avgPnL: 50.60 },
      'USDCAD': { totalPnL: 9340.60, totalTrades: 187, winRate: 62.8, avgPnL: 49.95 },
      'NZDUSD': { totalPnL: 4530.90, totalTrades: 98, winRate: 46.3, avgPnL: 46.23 }
    }

    // Mock duration analysis
    const durationData = {
      'scalp': { totalPnL: 8950.30, totalTrades: 456, winRate: 58.3, avgPnL: 19.63 },
      'short': { totalPnL: 24670.80, totalTrades: 298, winRate: 67.8, avgPnL: 82.79 },
      'medium': { totalPnL: 18340.50, totalTrades: 134, winRate: 71.6, avgPnL: 136.87 },
      'long': { totalPnL: 12450.70, totalTrades: 45, winRate: 77.8, avgPnL: 276.68 }
    }

    // Mock day of week data
    const dayOfWeekData: Record<number, SimpleMetrics> = {
      0: { totalPnL: 2340.50, totalTrades: 45, winRate: 53.3, avgPnL: 52.01 }, // Sunday
      1: { totalPnL: 12450.30, totalTrades: 234, winRate: 67.1, avgPnL: 53.21 }, // Monday
      2: { totalPnL: 15670.80, totalTrades: 298, winRate: 71.5, avgPnL: 52.58 }, // Tuesday
      3: { totalPnL: 18920.60, totalTrades: 345, winRate: 69.2, avgPnL: 54.84 }, // Wednesday
      4: { totalPnL: 16780.40, totalTrades: 312, winRate: 65.7, avgPnL: 53.78 }, // Thursday
      5: { totalPnL: 8340.90, totalTrades: 167, winRate: 58.1, avgPnL: 49.95 }, // Friday
      6: { totalPnL: 1240.20, totalTrades: 23, winRate: 47.8, avgPnL: 53.92 }   // Saturday
    }

    return {
      byPattern: patterns,
      byTimeOfDay: hourlyData,
      byMarketSession: sessionData,
      bySymbol: symbolData,
      byDayOfWeek: dayOfWeekData,
      byDuration: durationData,
      bySize: {}
    }
  }, [performanceReport])


  // Format values
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  const formatPercentage = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
      signDisplay: value !== 0 ? 'always' : 'never'
    }).format(value / 100)
  }

  const getTrendIcon = (trend: 'up' | 'down' | 'stable'): string => {
    switch (trend) {
      case 'up': return '📈'
      case 'down': return '📉'
      case 'stable': return '➡️'
      default: return '➡️'
    }
  }

  const getTrendColor = (trend: 'up' | 'down' | 'stable'): string => {
    switch (trend) {
      case 'up': return 'text-green-400'
      case 'down': return 'text-red-400'
      case 'stable': return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-48 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-gray-750 rounded-lg p-6">
                <div className="h-5 bg-gray-700 rounded mb-3"></div>
                <div className="space-y-2">
                  {Array.from({ length: 4 }).map((_, j) => (
                    <div key={j} className="h-4 bg-gray-700 rounded"></div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
        <div className="text-red-400 font-medium">Error Loading Trade Analysis</div>
        <div className="text-red-200 text-sm mt-1">{error}</div>
      </div>
    )
  }

  // No data state
  if (!tradeAnalysis) {
    return (
      <div className="bg-gray-750 rounded-lg p-8 text-center">
        <div className="text-gray-400 text-lg">No Trade Data Available</div>
        <div className="text-gray-500 text-sm mt-2">
          Execute trades to view pattern and timing analysis
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Analysis Navigation */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Trade Analysis Dashboard</h3>
          <p className="text-gray-400 text-sm">
            Comprehensive breakdown of trading patterns and performance
          </p>
        </div>

        <div className="flex bg-gray-700 rounded-lg p-1">
          {[
            { id: 'patterns', label: '🎯 Patterns', desc: 'Trading patterns' },
            { id: 'timing', label: '⏰ Timing', desc: 'Hourly analysis' },
            { id: 'sessions', label: '🌍 Sessions', desc: 'Market sessions' },
            { id: 'symbols', label: '💱 Symbols', desc: 'Currency pairs' },
            { id: 'duration', label: '⏱️ Duration', desc: 'Trade length' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveAnalysis(tab.id as typeof activeAnalysis)}
              className={`px-3 py-2 rounded text-sm transition-colors ${
                activeAnalysis === tab.id 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-300 hover:text-white hover:bg-gray-600'
              }`}
              title={tab.desc}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Pattern Analysis */}
      {activeAnalysis === 'patterns' && (
        <div className="space-y-6">
          <div>
            <h4 className="text-white font-medium mb-4">Trading Pattern Performance</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {tradeAnalysis.byPattern.map((pattern) => (
                <div
                  key={pattern.pattern}
                  onClick={() => setSelectedPattern(selectedPattern === pattern.pattern ? null : pattern.pattern)}
                  className={`
                    bg-gray-750 rounded-lg p-6 border transition-all cursor-pointer
                    ${selectedPattern === pattern.pattern ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-gray-700 hover:border-gray-600'}
                  `}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h5 className="text-white font-medium">{pattern.pattern}</h5>
                      <div className="text-gray-400 text-sm">Rank #{pattern.rank}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={getTrendColor(pattern.trend)}>{getTrendIcon(pattern.trend)}</span>
                      <div className={`px-2 py-1 rounded text-xs ${
                        pattern.winRate >= 70 ? 'bg-green-900/30 text-green-400 border border-green-500/30' :
                        pattern.winRate >= 60 ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-500/30' :
                        'bg-red-900/30 text-red-400 border border-red-500/30'
                      }`}>
                        {pattern.winRate.toFixed(1)}% WR
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-gray-400 text-xs">Total P&L</div>
                      <div className={`font-bold ${pattern.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(pattern.totalPnL)}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">Avg P&L</div>
                      <div className={`font-bold ${pattern.avgPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(pattern.avgPnL)}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">Trade Count</div>
                      <div className="text-white font-bold">{pattern.count}</div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">Win Rate</div>
                      <div className="text-white font-bold">{formatPercentage(pattern.winRate)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {selectedPattern && (
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-6">
              <h5 className="text-blue-400 font-medium mb-3">
                {selectedPattern} - Detailed Analysis
              </h5>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-gray-750 rounded p-4">
                  <div className="text-gray-400 text-sm mb-2">Performance Metrics</div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Success Rate</span>
                      <span className="text-green-400 font-medium">73.2%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Avg Hold Time</span>
                      <span className="text-white font-medium">2h 45m</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Risk/Reward</span>
                      <span className="text-blue-400 font-medium">1:2.4</span>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-750 rounded p-4">
                  <div className="text-gray-400 text-sm mb-2">Best Market Conditions</div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Session</span>
                      <span className="text-white font-medium">London/NY Overlap</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Volatility</span>
                      <span className="text-white font-medium">Medium-High</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Trend Strength</span>
                      <span className="text-blue-400 font-medium">Strong</span>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-750 rounded p-4">
                  <div className="text-gray-400 text-sm mb-2">Risk Analysis</div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Max Drawdown</span>
                      <span className="text-red-400 font-medium">-8.5%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Largest Loss</span>
                      <span className="text-red-400 font-medium">-$1,245</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Consistency</span>
                      <span className="text-green-400 font-medium">High</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Timing Analysis */}
      {activeAnalysis === 'timing' && (
        <div className="space-y-6">
          <div>
            <h4 className="text-white font-medium mb-4">Hourly Performance Analysis</h4>
            
            {/* Hour-by-hour breakdown */}
            <div className="bg-gray-750 rounded-lg p-6 mb-6">
              <div className="grid grid-cols-6 md:grid-cols-12 gap-2">
                {Object.entries(tradeAnalysis.byTimeOfDay)
                  .sort(([a], [b]) => Number(a) - Number(b))
                  .map(([hour, data]) => {
                                    const intensity = Math.abs(data.totalPnL) / 3000 // Normalize
                    const isPositive = data.totalPnL >= 0
                    
                    return (
                      <div
                        key={hour}
                        className={`
                          p-2 rounded text-center transition-all hover:scale-105 cursor-pointer
                          ${isPositive ? 'bg-green-500' : 'bg-red-500'}
                        `}
                        style={{
                          opacity: Math.max(0.3, intensity),
                          backgroundColor: isPositive 
                            ? `rgba(34, 197, 94, ${Math.max(0.3, intensity)})` 
                            : `rgba(239, 68, 68, ${Math.max(0.3, intensity)})`
                        }}
                        title={`${hour}:00 - P&L: ${formatCurrency(data.totalPnL)}, Trades: ${data.totalTrades}`}
                      >
                        <div className="text-white text-xs font-medium">
                          {hour.padStart(2, '0')}
                        </div>
                        <div className="text-white text-xs">
                          {formatCurrency(data.totalPnL).replace('$', '').replace('+', '')}
                        </div>
                      </div>
                    )
                  })}
              </div>
            </div>

            {/* Peak performance hours */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-gray-750 rounded-lg p-6">
                <h5 className="text-green-400 font-medium mb-3">🏆 Best Hours</h5>
                <div className="space-y-2">
                  {Object.entries(tradeAnalysis.byTimeOfDay)
                    .sort(([,a], [,b]) => b.totalPnL - a.totalPnL)
                    .slice(0, 3)
                    .map(([hour, data], index) => (
                      <div key={hour} className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <span className="text-yellow-400">#{index + 1}</span>
                          <span className="text-white">{hour.padStart(2, '0')}:00</span>
                        </div>
                        <div className="text-green-400 font-medium">
                          {formatCurrency(data.totalPnL)}
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              <div className="bg-gray-750 rounded-lg p-6">
                <h5 className="text-blue-400 font-medium mb-3">📊 Busiest Hours</h5>
                <div className="space-y-2">
                  {Object.entries(tradeAnalysis.byTimeOfDay)
                    .sort(([,a], [,b]) => b.totalTrades - a.totalTrades)
                    .slice(0, 3)
                    .map(([hour, data], index) => (
                      <div key={hour} className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <span className="text-yellow-400">#{index + 1}</span>
                          <span className="text-white">{hour.padStart(2, '0')}:00</span>
                        </div>
                        <div className="text-blue-400 font-medium">
                          {data.totalTrades} trades
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              <div className="bg-gray-750 rounded-lg p-6">
                <h5 className="text-yellow-400 font-medium mb-3">🎯 Highest Win Rate</h5>
                <div className="space-y-2">
                  {Object.entries(tradeAnalysis.byTimeOfDay)
                    .sort(([,a], [,b]) => b.winRate - a.winRate)
                    .slice(0, 3)
                    .map(([hour, data], index) => (
                      <div key={hour} className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <span className="text-yellow-400">#{index + 1}</span>
                          <span className="text-white">{hour.padStart(2, '0')}:00</span>
                        </div>
                        <div className="text-yellow-400 font-medium">
                          {data.winRate.toFixed(1)}%
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Market Sessions Analysis */}
      {activeAnalysis === 'sessions' && (
        <div className="space-y-6">
          <div>
            <h4 className="text-white font-medium mb-4">Market Session Performance</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {Object.entries(tradeAnalysis.byMarketSession).map(([session, data]) => (
                <div key={session} className="bg-gray-750 rounded-lg p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h5 className="text-white font-medium capitalize">
                        {session === 'newyork' ? 'New York' : session} Session
                      </h5>
                      <div className="text-gray-400 text-sm">
                        {session === 'asian' && '21:00-06:00 UTC'}
                        {session === 'london' && '07:00-16:00 UTC'}
                        {session === 'newyork' && '12:00-21:00 UTC'}
                        {session === 'overlap' && 'London/NY Overlap'}
                      </div>
                    </div>
                    <div className="text-2xl">
                      {session === 'asian' && '🌏'}
                      {session === 'london' && '🇬🇧'}
                      {session === 'newyork' && '🇺🇸'}
                      {session === 'overlap' && '🌍'}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="text-gray-400 text-xs">Total P&L</div>
                      <div className={`text-xl font-bold ${data.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(data.totalPnL)}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-gray-400 text-xs">Trades</div>
                        <div className="text-white font-medium">{data.totalTrades}</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Win Rate</div>
                        <div className="text-white font-medium">{data.winRate.toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Avg P&L</div>
                        <div className={`font-medium ${data.avgPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatCurrency(data.avgPnL)}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Volume</div>
                        <div className="text-blue-400 font-medium">{(data.volume || 0).toFixed(1)}x</div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Symbol Analysis */}
      {activeAnalysis === 'symbols' && (
        <div className="space-y-6">
          <div>
            <h4 className="text-white font-medium mb-4">Currency Pair Performance</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {Object.entries(tradeAnalysis.bySymbol).map(([symbol, data]) => (
                <div key={symbol} className="bg-gray-750 rounded-lg p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h5 className="text-white font-medium text-lg">{symbol}</h5>
                      <div className="text-gray-400 text-sm">
                        {symbol.slice(0, 3)}/{symbol.slice(3, 6)}
                      </div>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs ${
                      data.winRate >= 65 ? 'bg-green-900/30 text-green-400 border border-green-500/30' :
                      data.winRate >= 55 ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-500/30' :
                      'bg-red-900/30 text-red-400 border border-red-500/30'
                    }`}>
                      {data.winRate.toFixed(1)}% WR
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="text-gray-400 text-xs">Total P&L</div>
                      <div className={`text-xl font-bold ${data.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(data.totalPnL)}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-gray-400 text-xs">Trades</div>
                        <div className="text-white font-medium">{data.totalTrades}</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Avg P&L</div>
                        <div className={`font-medium ${data.avgPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatCurrency(data.avgPnL)}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Duration Analysis */}
      {activeAnalysis === 'duration' && (
        <div className="space-y-6">
          <div>
            <h4 className="text-white font-medium mb-4">Trade Duration Analysis</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {Object.entries(tradeAnalysis.byDuration).map(([duration, data]) => (
                <div key={duration} className="bg-gray-750 rounded-lg p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h5 className="text-white font-medium capitalize">{duration} Term</h5>
                      <div className="text-gray-400 text-sm">
                        {duration === 'scalp' && '< 15 minutes'}
                        {duration === 'short' && '15min - 4 hours'}
                        {duration === 'medium' && '4 - 24 hours'}
                        {duration === 'long' && '> 1 day'}
                      </div>
                    </div>
                    <div className="text-2xl">
                      {duration === 'scalp' && '⚡'}
                      {duration === 'short' && '🏃'}
                      {duration === 'medium' && '🚶'}
                      {duration === 'long' && '🐌'}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="text-gray-400 text-xs">Total P&L</div>
                      <div className={`text-xl font-bold ${data.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(data.totalPnL)}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-gray-400 text-xs">Trades</div>
                        <div className="text-white font-medium">{data.totalTrades}</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Win Rate</div>
                        <div className="text-white font-medium">{data.winRate.toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Avg P&L</div>
                        <div className={`font-medium ${data.avgPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatCurrency(data.avgPnL)}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Frequency</div>
                        <div className="text-blue-400 font-medium">
                          {((data.totalTrades / 1000) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}