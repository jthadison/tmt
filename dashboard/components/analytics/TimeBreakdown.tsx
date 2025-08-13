'use client'

import { useState, useMemo } from 'react'
import { PerformanceReport, CalendarHeatmapData } from '@/types/analytics'

// Simplified interface for time breakdown data
interface SimpleMetrics {
  totalPnL: number
  totalTrades: number
  winRate: number
  totalReturn: number
  sharpeRatio: number
  maxDrawdownPercent: number
  profitFactor: number
}

interface TimeBreakdownType {
  monthly: Record<string, SimpleMetrics>
  weekly: Record<string, SimpleMetrics>
  daily: Record<string, SimpleMetrics>
  quarterly: Record<string, SimpleMetrics>
  yearly: Record<string, SimpleMetrics>
}

/**
 * Props for TimeBreakdown component
 */
interface TimeBreakdownProps {
  /** Performance report data */
  performanceReport?: PerformanceReport
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
}

/**
 * Time-based performance breakdown component
 * Provides monthly, weekly, daily, and calendar analysis
 */
export function TimeBreakdown({
  performanceReport,
  loading = false,
  error
}: TimeBreakdownProps) {
  const [activeView, setActiveView] = useState<'calendar' | 'monthly' | 'weekly' | 'daily' | 'streaks'>('calendar')
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null)

  // Generate mock time breakdown data (would come from API in real implementation)
  const timeBreakdown = useMemo((): TimeBreakdownType | null => {
    if (!performanceReport) return null

    // Generate monthly data for the past 12 months
    const monthlyData: Record<string, SimpleMetrics> = {}
    const now = new Date()
    for (let i = 11; i >= 0; i--) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`
      
      const basePerformance = Math.random() * 10000 - 2000 // Random between -2000 and 8000
      monthlyData[monthKey] = {
        totalPnL: basePerformance,
        totalTrades: Math.floor(Math.random() * 200) + 50,
        winRate: 45 + Math.random() * 35, // Between 45-80%
        totalReturn: (basePerformance / 50000) * 100, // Assuming 50k base
        sharpeRatio: Math.random() * 3,
        maxDrawdownPercent: -(Math.random() * 15),
        profitFactor: 0.8 + Math.random() * 1.7
      }
    }

    // Generate weekly data for the past 13 weeks
    const weeklyData: Record<string, SimpleMetrics> = {}
    for (let i = 12; i >= 0; i--) {
      const date = new Date(now.getTime() - i * 7 * 24 * 60 * 60 * 1000)
      const year = date.getFullYear()
      const week = getWeekNumber(date)
      const weekKey = `${year}-W${week.toString().padStart(2, '0')}`
      
      const basePerformance = Math.random() * 3000 - 500
      weeklyData[weekKey] = {
        totalPnL: basePerformance,
        totalTrades: Math.floor(Math.random() * 50) + 10,
        winRate: 40 + Math.random() * 40,
        totalReturn: (basePerformance / 50000) * 100,
        sharpeRatio: Math.random() * 2.5,
        maxDrawdownPercent: -(Math.random() * 8),
        profitFactor: 0.7 + Math.random() * 1.8
      }
    }

    // Generate daily data for the past 30 days
    const dailyData: Record<string, SimpleMetrics> = {}
    for (let i = 29; i >= 0; i--) {
      const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
      const dayKey = date.toISOString().split('T')[0]
      
      const basePerformance = Math.random() * 1000 - 200
      dailyData[dayKey] = {
        totalPnL: basePerformance,
        totalTrades: Math.floor(Math.random() * 15) + 2,
        winRate: 35 + Math.random() * 45,
        totalReturn: (basePerformance / 50000) * 100,
        sharpeRatio: Math.random() * 2,
        maxDrawdownPercent: -(Math.random() * 5),
        profitFactor: 0.5 + Math.random() * 2
      }
    }

    // Generate quarterly data
    const quarterlyData: Record<string, SimpleMetrics> = {}
    for (let i = 3; i >= 0; i--) {
      const date = new Date(now.getFullYear(), now.getMonth() - i * 3, 1)
      const quarter = Math.floor(date.getMonth() / 3) + 1
      const quarterKey = `${date.getFullYear()}-Q${quarter}`
      
      const basePerformance = Math.random() * 25000 - 5000
      quarterlyData[quarterKey] = {
        totalPnL: basePerformance,
        totalTrades: Math.floor(Math.random() * 500) + 150,
        winRate: 50 + Math.random() * 25,
        totalReturn: (basePerformance / 50000) * 100,
        sharpeRatio: Math.random() * 2.5,
        maxDrawdownPercent: -(Math.random() * 20),
        profitFactor: 0.9 + Math.random() * 1.5
      }
    }

    // Generate yearly data
    const yearlyData: Record<string, SimpleMetrics> = {}
    for (let i = 2; i >= 0; i--) {
      const year = (now.getFullYear() - i).toString()
      
      const basePerformance = Math.random() * 100000 - 20000
      yearlyData[year] = {
        totalPnL: basePerformance,
        totalTrades: Math.floor(Math.random() * 2000) + 500,
        winRate: 55 + Math.random() * 20,
        totalReturn: (basePerformance / 50000) * 100,
        sharpeRatio: Math.random() * 2.8,
        maxDrawdownPercent: -(Math.random() * 25),
        profitFactor: 1.0 + Math.random() * 1.3
      }
    }

    return {
      monthly: monthlyData,
      weekly: weeklyData,
      daily: dailyData,
      quarterly: quarterlyData,
      yearly: yearlyData
    }
  }, [performanceReport])

  // Generate calendar heatmap data
  const calendarData = useMemo((): CalendarHeatmapData[] => {
    if (!timeBreakdown?.daily) return []

    return Object.entries(timeBreakdown.daily).map(([date, data]) => ({
      date: new Date(date),
      value: data.totalPnL,
      trades: data.totalTrades,
      type: data.totalPnL > 0 ? 'profit' : data.totalPnL < 0 ? 'loss' : 'neutral',
      intensity: Math.abs(data.totalPnL) / 1000 // Normalize intensity
    }))
  }, [timeBreakdown?.daily])

  // Helper function to get week number
  function getWeekNumber(date: Date): number {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
    const dayNum = d.getUTCDay() || 7
    d.setUTCDate(d.getUTCDate() + 4 - dayNum)
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
    return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
  }

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

  const formatDate = (dateStr: string, format: 'full' | 'month' | 'short' = 'full'): string => {
    const date = new Date(dateStr)
    if (format === 'month') {
      return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    } else if (format === 'short') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    })
  }

  // Get performance streaks
  const getPerformanceStreaks = () => {
    if (!timeBreakdown?.daily) return { winning: 0, losing: 0, current: 'neutral' }

    const dailyEntries = Object.entries(timeBreakdown.daily)
      .sort(([a], [b]) => new Date(a).getTime() - new Date(b).getTime())

    let currentStreak = 0
    let maxWinningStreak = 0
    let maxLosingStreak = 0
    let currentStreakType: 'winning' | 'losing' | 'neutral' = 'neutral'

    for (let i = 0; i < dailyEntries.length; i++) {
      const [, data] = dailyEntries[i]
      const isProfit = data.totalPnL > 0

      if (i === 0) {
        currentStreak = 1
        currentStreakType = isProfit ? 'winning' : 'losing'
      } else {
        const prevData = dailyEntries[i - 1][1]
        const prevIsProfit = prevData.totalPnL > 0

        if (isProfit === prevIsProfit) {
          currentStreak++
        } else {
          if (prevIsProfit) {
            maxWinningStreak = Math.max(maxWinningStreak, currentStreak)
          } else {
            maxLosingStreak = Math.max(maxLosingStreak, currentStreak)
          }
          currentStreak = 1
          currentStreakType = isProfit ? 'winning' : 'losing'
        }
      }
    }

    // Update final streak
    if (currentStreakType === 'winning') {
      maxWinningStreak = Math.max(maxWinningStreak, currentStreak)
    } else {
      maxLosingStreak = Math.max(maxLosingStreak, currentStreak)
    }

    return {
      winning: maxWinningStreak,
      losing: maxLosingStreak,
      current: currentStreakType,
      currentLength: currentStreak
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-48 mb-4"></div>
          <div className="grid grid-cols-7 gap-1 mb-6">
            {Array.from({ length: 35 }).map((_, i) => (
              <div key={i} className="h-8 bg-gray-700 rounded"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-gray-750 rounded-lg p-6">
                <div className="h-5 bg-gray-700 rounded mb-3"></div>
                <div className="h-8 bg-gray-700 rounded"></div>
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
        <div className="text-red-400 font-medium">Error Loading Time Breakdown</div>
        <div className="text-red-200 text-sm mt-1">{error}</div>
      </div>
    )
  }

  // No data state
  if (!timeBreakdown) {
    return (
      <div className="bg-gray-750 rounded-lg p-8 text-center">
        <div className="text-gray-400 text-lg">No Time Data Available</div>
        <div className="text-gray-500 text-sm mt-2">
          Historical data will appear as trading activity accumulates
        </div>
      </div>
    )
  }

  const streaks = getPerformanceStreaks()

  return (
    <div className="space-y-6">
      {/* Navigation */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Time-Based Performance</h3>
          <p className="text-gray-400 text-sm">
            Historical performance analysis across different time periods
          </p>
        </div>

        <div className="flex bg-gray-700 rounded-lg p-1">
          {[
            { id: 'calendar', label: '📅 Calendar', desc: 'Daily heatmap' },
            { id: 'monthly', label: '📊 Monthly', desc: 'Monthly trends' },
            { id: 'weekly', label: '📈 Weekly', desc: 'Weekly analysis' },
            { id: 'daily', label: '📉 Daily', desc: 'Daily breakdown' },
            { id: 'streaks', label: '🔥 Streaks', desc: 'Performance streaks' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveView(tab.id as typeof activeView)}
              className={`px-3 py-2 rounded text-sm transition-colors ${
                activeView === tab.id 
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

      {/* Calendar Heatmap View */}
      {activeView === 'calendar' && (
        <div className="space-y-6">
          <div className="bg-gray-750 rounded-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h4 className="text-white font-medium">Daily Performance Calendar</h4>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-400">Legend:</span>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-green-500 rounded"></div>
                    <span className="text-gray-300">Profit</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-red-500 rounded"></div>
                    <span className="text-gray-300">Loss</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-gray-600 rounded"></div>
                    <span className="text-gray-300">No Trading</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-1">
              {/* Day headers */}
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
                <div key={day} className="text-center text-gray-400 text-xs font-medium p-2">
                  {day}
                </div>
              ))}
              
              {/* Calendar days */}
              {Array.from({ length: 35 }).map((_, index) => {
                const date = new Date()
                date.setDate(date.getDate() - (34 - index))
                
                const dayData = calendarData.find(d => 
                  d.date.toDateString() === date.toDateString()
                )
                
                const isToday = date.toDateString() === new Date().toDateString()
                const isWeekend = date.getDay() === 0 || date.getDay() === 6
                
                return (
                  <div
                    key={index}
                    className={`
                      relative h-12 rounded cursor-pointer transition-all hover:scale-110
                      ${isToday ? 'ring-2 ring-blue-500' : ''}
                      ${isWeekend ? 'opacity-50' : ''}
                    `}
                    style={{
                      backgroundColor: dayData 
                        ? dayData.type === 'profit' 
                          ? `rgba(34, 197, 94, ${Math.max(0.3, dayData.intensity)})`
                          : dayData.type === 'loss'
                          ? `rgba(239, 68, 68, ${Math.max(0.3, dayData.intensity)})`
                          : 'rgba(107, 114, 128, 0.3)'
                        : 'rgba(75, 85, 99, 0.2)'
                    }}
                    title={dayData 
                      ? `${date.toLocaleDateString()}: ${formatCurrency(dayData.value)}, ${dayData.trades} trades`
                      : `${date.toLocaleDateString()}: No trading`
                    }
                  >
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <div className="text-white text-xs font-medium">
                        {date.getDate()}
                      </div>
                      {dayData && dayData.value !== 0 && (
                        <div className="text-white text-xs">
                          {formatCurrency(dayData.value).replace('$', '').replace('+', '')}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Calendar Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-gray-750 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Profitable Days</div>
              <div className="text-2xl font-bold text-green-400">
                {calendarData.filter(d => d.type === 'profit').length}
              </div>
              <div className="text-gray-500 text-xs">
                {((calendarData.filter(d => d.type === 'profit').length / calendarData.length) * 100).toFixed(1)}% of days
              </div>
            </div>

            <div className="bg-gray-750 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Best Day</div>
              <div className="text-2xl font-bold text-green-400">
                {formatCurrency(Math.max(...calendarData.map(d => d.value)))}
              </div>
              <div className="text-gray-500 text-xs">
                Single day maximum
              </div>
            </div>

            <div className="bg-gray-750 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Worst Day</div>
              <div className="text-2xl font-bold text-red-400">
                {formatCurrency(Math.min(...calendarData.map(d => d.value)))}
              </div>
              <div className="text-gray-500 text-xs">
                Single day minimum
              </div>
            </div>

            <div className="bg-gray-750 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Daily Average</div>
              <div className={`text-2xl font-bold ${
                calendarData.reduce((sum, d) => sum + d.value, 0) >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {formatCurrency(calendarData.reduce((sum, d) => sum + d.value, 0) / calendarData.length)}
              </div>
              <div className="text-gray-500 text-xs">
                Mean daily P&L
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Monthly View */}
      {activeView === 'monthly' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(timeBreakdown.monthly)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([month, data]) => (
                <div
                  key={month}
                  onClick={() => setSelectedMonth(selectedMonth === month ? null : month)}
                  className={`
                    bg-gray-750 rounded-lg p-6 border cursor-pointer transition-all
                    ${selectedMonth === month ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-gray-700 hover:border-gray-600'}
                  `}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h5 className="text-white font-medium">{formatDate(month + '-01', 'month')}</h5>
                      <div className="text-gray-400 text-sm">{data.totalTrades} trades</div>
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
                      <div className="text-gray-400 text-xs">Monthly P&L</div>
                      <div className={`text-xl font-bold ${data.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(data.totalPnL)}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-gray-400 text-xs">Return</div>
                        <div className={`font-medium ${data.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatPercentage(data.totalReturn)}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Sharpe</div>
                        <div className="text-white font-medium">{data.sharpeRatio.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Max DD</div>
                        <div className="text-red-400 font-medium">{formatPercentage(data.maxDrawdownPercent)}</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Profit Factor</div>
                        <div className="text-blue-400 font-medium">{data.profitFactor.toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Weekly View */}
      {activeView === 'weekly' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(timeBreakdown.weekly)
              .sort(([a], [b]) => b.localeCompare(a))
              .slice(0, 12)
              .map(([week, data]) => (
                <div key={week} className="bg-gray-750 rounded-lg p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h5 className="text-white font-medium">Week {week.split('-W')[1]}</h5>
                      <div className="text-gray-400 text-sm">{week.split('-')[0]} • {data.totalTrades} trades</div>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs ${
                      data.totalPnL >= 0 ? 'bg-green-900/30 text-green-400 border border-green-500/30' :
                      'bg-red-900/30 text-red-400 border border-red-500/30'
                    }`}>
                      {data.totalPnL >= 0 ? '+' : ''}{formatCurrency(data.totalPnL)}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-gray-400 text-xs">Return</div>
                      <div className={`font-medium ${data.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercentage(data.totalReturn)}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">Win Rate</div>
                      <div className="text-white font-medium">{data.winRate.toFixed(1)}%</div>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Daily View */}
      {activeView === 'daily' && (
        <div className="space-y-6">
          <div className="bg-gray-750 rounded-lg overflow-hidden">
            <div className="p-4 border-b border-gray-600">
              <h4 className="text-white font-medium">Recent Daily Performance</h4>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">P&L</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Trades</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Win Rate</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Return</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-600">
                  {Object.entries(timeBreakdown.daily)
                    .sort(([a], [b]) => b.localeCompare(a))
                    .slice(0, 15)
                    .map(([date, data]) => (
                      <tr key={date} className="hover:bg-gray-700/50">
                        <td className="px-6 py-4 text-white font-medium">
                          {formatDate(date, 'short')}
                        </td>
                        <td className="px-6 py-4">
                          <div className={`font-medium ${data.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatCurrency(data.totalPnL)}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-white">{data.totalTrades}</td>
                        <td className="px-6 py-4 text-white">{data.winRate.toFixed(1)}%</td>
                        <td className="px-6 py-4">
                          <div className={`${data.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatPercentage(data.totalReturn)}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className={`flex items-center gap-2`}>
                            <div className={`w-2 h-2 rounded-full ${
                              data.totalPnL > 0 ? 'bg-green-400' :
                              data.totalPnL < 0 ? 'bg-red-400' : 'bg-gray-400'
                            }`}></div>
                            <span className="text-gray-300 text-sm">
                              {data.totalPnL > 0 ? 'Profit' : data.totalPnL < 0 ? 'Loss' : 'Neutral'}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Streaks View */}
      {activeView === 'streaks' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-gray-750 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="text-2xl">🔥</div>
                <div>
                  <div className="text-gray-400 text-sm">Current Streak</div>
                  <div className={`text-lg font-bold ${
                    streaks.current === 'winning' ? 'text-green-400' : 
                    streaks.current === 'losing' ? 'text-red-400' : 'text-gray-400'
                  }`}>
                    {streaks.currentLength} {streaks.current} days
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-750 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="text-2xl">📈</div>
                <div>
                  <div className="text-gray-400 text-sm">Longest Win Streak</div>
                  <div className="text-lg font-bold text-green-400">
                    {streaks.winning} days
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-750 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="text-2xl">📉</div>
                <div>
                  <div className="text-gray-400 text-sm">Longest Loss Streak</div>
                  <div className="text-lg font-bold text-red-400">
                    {streaks.losing} days
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-750 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="text-2xl">📊</div>
                <div>
                  <div className="text-gray-400 text-sm">Consistency Score</div>
                  <div className="text-lg font-bold text-blue-400">
                    {((streaks.winning / (streaks.winning + streaks.losing)) * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Streak Timeline */}
          <div className="bg-gray-750 rounded-lg p-6">
            <h4 className="text-white font-medium mb-4">Performance Streak Timeline</h4>
            <div className="flex items-center gap-1 overflow-x-auto">
              {calendarData
                .sort((a, b) => a.date.getTime() - b.date.getTime())
                .map((day, index) => (
                  <div
                    key={index}
                    className={`
                      w-3 h-8 rounded transition-all hover:scale-y-125
                      ${day.type === 'profit' ? 'bg-green-500' :
                        day.type === 'loss' ? 'bg-red-500' : 'bg-gray-600'}
                    `}
                    title={`${day.date.toLocaleDateString()}: ${formatCurrency(day.value)}`}
                  ></div>
                ))}
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-2">
              <span>30 days ago</span>
              <span>Today</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}