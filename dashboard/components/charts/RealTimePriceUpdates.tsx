/**
 * Real-Time Price Updates Component - AC2
 * Story 9.4: Real-time price updates with configurable timeframes and WebSocket integration
 * 
 * PERFORMANCE: Optimized for <100ms latency with efficient state management
 */

'use client'

import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import {
  ChartTimeframe,
  PriceTick,
  OHLCV,
  MarketInstrument,
  ChartConfig
} from '@/types/marketData'
import { useMarketData } from '@/hooks/useMarketData'

/**
 * Real-time price update configuration
 */
interface RealTimePriceConfig {
  /** Instruments to track */
  instruments: string[]
  /** Update frequency in milliseconds */
  updateFrequency: number
  /** Enable tick-by-tick updates */
  enableTickUpdates: boolean
  /** Enable bar updates */
  enableBarUpdates: boolean
  /** Maximum price history to keep */
  maxHistorySize: number
  /** Connection timeout */
  connectionTimeout: number
}

/**
 * Price update statistics
 */
interface PriceUpdateStats {
  /** Total updates received */
  totalUpdates: number
  /** Updates per second */
  updatesPerSecond: number
  /** Average update latency */
  updateLatency: number
  /** Connection status */
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error'
  /** Last update timestamp */
  lastUpdate: number
  /** Missed updates count */
  missedUpdates: number
}

/**
 * Price change indicator
 */
interface PriceChange {
  /** Current price */
  current: number
  /** Previous price */
  previous: number
  /** Change amount */
  change: number
  /** Change percentage */
  changePercent: number
  /** Change direction */
  direction: 'up' | 'down' | 'unchanged'
}

/**
 * Real-time price display component
 */
function RealTimePriceDisplay({
  instrument,
  tick,
  priceChange,
  compact = false
}: {
  instrument: MarketInstrument
  tick: PriceTick | null
  priceChange: PriceChange | null
  compact?: boolean
}) {
  const [flashPrice, setFlashPrice] = useState(false)

  // Flash effect when price changes
  useEffect(() => {
    if (priceChange && priceChange.direction !== 'unchanged') {
      setFlashPrice(true)
      const timeout = setTimeout(() => setFlashPrice(false), 200)
      return () => clearTimeout(timeout)
    }
  }, [priceChange])

  if (!tick) {
    return (
      <div className={`${compact ? 'p-2' : 'p-4'} bg-gray-800 rounded border border-gray-700`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
          <div className="h-6 bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  const getPriceColor = () => {
    if (!priceChange) return 'text-gray-400'
    switch (priceChange.direction) {
      case 'up': return 'text-green-400'
      case 'down': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getChangeColor = () => {
    if (!priceChange) return 'text-gray-400'
    return priceChange.change >= 0 ? 'text-green-400' : 'text-red-400'
  }

  if (compact) {
    return (
      <div className="flex items-center justify-between p-2 bg-gray-800 border border-gray-700 rounded">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${
            tick ? 'bg-green-400 animate-pulse' : 'bg-gray-500'
          }`} />
          <span className="text-sm font-medium text-white">
            {instrument.displayName}
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className={`font-mono text-sm font-semibold ${getPriceColor()} ${
            flashPrice ? 'animate-pulse' : ''
          }`}>
            {tick.mid.toFixed(Math.abs(instrument.pipLocation))}
          </span>
          
          {priceChange && (
            <span className={`text-xs ${getChangeColor()}`}>
              {priceChange.change >= 0 ? '+' : ''}{priceChange.change.toFixed(Math.abs(instrument.pipLocation))}
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className={`w-3 h-3 rounded-full ${
            tick ? 'bg-green-400 animate-pulse' : 'bg-gray-500'
          }`} />
          <h3 className="text-lg font-semibold text-white">
            {instrument.displayName}
          </h3>
        </div>
        
        <div className="text-xs text-gray-400">
          {new Date(tick.timestamp).toLocaleTimeString()}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Bid</div>
          <div className="font-mono text-sm font-semibold text-blue-400">
            {tick.bid.toFixed(Math.abs(instrument.pipLocation))}
          </div>
        </div>
        
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Mid</div>
          <div className={`font-mono text-lg font-bold ${getPriceColor()} ${
            flashPrice ? 'animate-pulse' : ''
          }`}>
            {tick.mid.toFixed(Math.abs(instrument.pipLocation))}
          </div>
        </div>
        
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Ask</div>
          <div className="font-mono text-sm font-semibold text-orange-400">
            {tick.ask.toFixed(Math.abs(instrument.pipLocation))}
          </div>
        </div>
      </div>

      {priceChange && (
        <div className="flex items-center justify-between pt-3 border-t border-gray-700">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">Change:</span>
            <span className={`text-sm font-semibold ${getChangeColor()}`}>
              {priceChange.change >= 0 ? '+' : ''}{priceChange.change.toFixed(Math.abs(instrument.pipLocation))}
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className={`text-sm font-semibold ${getChangeColor()}`}>
              {priceChange.changePercent >= 0 ? '+' : ''}{priceChange.changePercent.toFixed(2)}%
            </span>
            <span className="text-lg">
              {priceChange.direction === 'up' ? '↗️' : priceChange.direction === 'down' ? '↘️' : '➡️'}
            </span>
          </div>
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-gray-700">
        <div className="grid grid-cols-2 gap-4 text-xs text-gray-400">
          <div>
            <span>Spread: </span>
            <span className="font-mono">
              {(tick.ask - tick.bid).toFixed(Math.abs(instrument.pipLocation))}
            </span>
          </div>
          <div>
            <span>Volume: </span>
            <span className="font-mono">{tick.volume.toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Connection status indicator
 */
function ConnectionStatusIndicator({
  status,
  stats,
  onReconnect
}: {
  status: PriceUpdateStats['connectionStatus']
  stats: PriceUpdateStats
  onReconnect: () => void
}) {
  const getStatusColor = () => {
    switch (status) {
      case 'connected': return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'connecting': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'disconnected': return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
      case 'error': return 'text-red-400 bg-red-900/20 border-red-500/30'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const getStatusIcon = () => {
    switch (status) {
      case 'connected': return '🟢'
      case 'connecting': return '🟡'
      case 'disconnected': return '⚪'
      case 'error': return '🔴'
      default: return '⚪'
    }
  }

  return (
    <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{getStatusIcon()}</span>
          <span className={`text-sm font-medium px-2 py-1 rounded border ${getStatusColor()}`}>
            {status.toUpperCase()}
          </span>
        </div>
        
        {status === 'disconnected' || status === 'error' ? (
          <button
            onClick={onReconnect}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded"
          >
            Reconnect
          </button>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <span className="text-gray-400">Updates/sec: </span>
          <span className="font-mono text-white">{stats.updatesPerSecond.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-gray-400">Latency: </span>
          <span className="font-mono text-white">{stats.averageLatency.toFixed(0)}ms</span>
        </div>
        <div>
          <span className="text-gray-400">Total: </span>
          <span className="font-mono text-white">{stats.totalUpdates.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-gray-400">Missed: </span>
          <span className="font-mono text-white">{stats.missedUpdates.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Timeframe selector component
 */
function TimeframeSelector({
  currentTimeframe,
  onTimeframeChange,
  availableTimeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
}: {
  currentTimeframe: ChartTimeframe
  onTimeframeChange: (timeframe: ChartTimeframe) => void
  availableTimeframes?: ChartTimeframe[]
}) {
  return (
    <div className="flex items-center space-x-2">
      <span className="text-sm text-gray-400">Timeframe:</span>
      <div className="flex space-x-1">
        {availableTimeframes.map(tf => (
          <button
            key={tf}
            onClick={() => onTimeframeChange(tf)}
            className={`px-3 py-1 text-xs rounded border ${
              currentTimeframe === tf
                ? 'bg-blue-600 text-white border-blue-500'
                : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'
            }`}
          >
            {tf}
          </button>
        ))}
      </div>
    </div>
  )
}

/**
 * Props for RealTimePriceUpdates component
 */
interface RealTimePriceUpdatesProps {
  /** Chart configurations to update */
  chartConfigs: ChartConfig[]
  /** Callback when chart config changes */
  onChartConfigChange: (chartId: string, config: Partial<ChartConfig>) => void
  /** Enable real-time updates */
  enabled?: boolean
  /** Update configuration */
  config?: Partial<RealTimePriceConfig>
  /** Compact display mode */
  compact?: boolean
  /** Show connection stats */
  showStats?: boolean
}

/**
 * Main RealTimePriceUpdates component
 */
export function RealTimePriceUpdates({
  chartConfigs,
  onChartConfigChange,
  enabled = true,
  config: propsConfig,
  compact = false,
  showStats = false
}: RealTimePriceUpdatesProps) {
  const defaultConfig: RealTimePriceConfig = {
    instruments: [],
    updateFrequency: 100, // 100ms updates
    enableTickUpdates: true,
    enableBarUpdates: true,
    maxHistorySize: 1000,
    connectionTimeout: 5000
  }

  const fullConfig = useMemo(() => ({ 
    ...defaultConfig, 
    ...propsConfig,
    instruments: chartConfigs.map(c => c.instrument)
  }), [propsConfig, chartConfigs])

  const { state, actions } = useMarketData({
    enableRealtime: enabled,
    maxBarsInMemory: fullConfig.maxHistorySize
  })

  const [subscriptionId, setSubscriptionId] = useState<string | null>(null)
  const [priceChanges, setPriceChanges] = useState<Map<string, PriceChange>>(new Map())
  const [stats, setStats] = useState<PriceUpdateStats>({
    totalUpdates: 0,
    updatesPerSecond: 0,
    updateLatency: 0,
    connectionStatus: 'disconnected',
    lastUpdate: 0,
    missedUpdates: 0
  })

  const statsRef = useRef({
    updateTimes: [] as number[],
    startTime: Date.now(),
    lastStatsUpdate: Date.now()
  })

  /**
   * Calculate price change
   */
  const calculatePriceChange = useCallback((current: number, previous: number): PriceChange => {
    const change = current - previous
    const changePercent = previous !== 0 ? (change / previous) * 100 : 0
    
    return {
      current,
      previous,
      change,
      changePercent,
      direction: change > 0 ? 'up' : change < 0 ? 'down' : 'unchanged'
    }
  }, [])

  /**
   * Update price change tracking
   */
  const updatePriceChange = useCallback((instrument: string, newTick: PriceTick) => {
    setPriceChanges(prev => {
      const currentChange = prev.get(instrument)
      const previousPrice = currentChange?.current || newTick.mid
      const newChange = calculatePriceChange(newTick.mid, previousPrice)
      
      return new Map(prev).set(instrument, newChange)
    })
  }, [calculatePriceChange])

  /**
   * Update statistics
   */
  const updateStats = useCallback((updateTime: number) => {
    const now = Date.now()
    const times = statsRef.current.updateTimes
    
    times.push(updateTime)
    
    // Keep only last 100 update times
    if (times.length > 100) {
      statsRef.current.updateTimes = times.slice(-100)
    }

    // Update stats every second
    if (now - statsRef.current.lastStatsUpdate > 1000) {
      const totalTime = now - statsRef.current.startTime
      const updatesPerSecond = times.length > 0 ? 
        (times.length / (totalTime / 1000)) : 0
      
      const updateLatency = times.length > 1 ? 
        times.reduce((sum, time, index) => {
          if (index === 0) return sum
          return sum + (time - times[index - 1])
        }, 0) / (times.length - 1) : 0

      setStats(prev => ({
        ...prev,
        totalUpdates: prev.totalUpdates + 1,
        updatesPerSecond,
        updateLatency,
        lastUpdate: now,
        connectionStatus: 'connected'
      }))

      statsRef.current.lastStatsUpdate = now
    }
  }, [])

  /**
   * Handle real-time tick updates
   */
  useEffect(() => {
    state.currentTicks.forEach((tick, instrument) => {
      if (fullConfig.instruments.includes(instrument)) {
        updatePriceChange(instrument, tick)
        updateStats(tick.timestamp)
      }
    })
  }, [state.currentTicks, fullConfig.instruments, updatePriceChange, updateStats])

  /**
   * Subscribe to real-time data
   */
  const subscribe = useCallback(async () => {
    if (!enabled || fullConfig.instruments.length === 0) return

    try {
      setStats(prev => ({ ...prev, connectionStatus: 'connecting' }))
      
      const dataTypes: ('ticks' | 'bars')[] = []
      if (fullConfig.enableTickUpdates) dataTypes.push('ticks')
      if (fullConfig.enableBarUpdates) dataTypes.push('bars')

      const id = await actions.subscribeToRealtime(fullConfig.instruments, dataTypes)
      setSubscriptionId(id)
      
      setStats(prev => ({ ...prev, connectionStatus: 'connected' }))
    } catch (error) {
      console.error('Failed to subscribe to real-time data:', error)
      setStats(prev => ({ 
        ...prev, 
        connectionStatus: 'error',
        missedUpdates: prev.missedUpdates + 1
      }))
    }
  }, [enabled, fullConfig, actions])

  /**
   * Unsubscribe from real-time data
   */
  const unsubscribe = useCallback(async () => {
    if (subscriptionId) {
      await actions.unsubscribe(subscriptionId)
      setSubscriptionId(null)
      setStats(prev => ({ ...prev, connectionStatus: 'disconnected' }))
    }
  }, [subscriptionId, actions])

  /**
   * Reconnect to real-time data
   */
  const reconnect = useCallback(async () => {
    await unsubscribe()
    await subscribe()
  }, [unsubscribe, subscribe])

  /**
   * Handle timeframe changes
   */
  const handleTimeframeChange = useCallback((chartId: string, timeframe: ChartTimeframe) => {
    const chartConfig = chartConfigs.find(c => c.instrument === chartId)
    if (chartConfig) {
      onChartConfigChange(chartId, { timeframe })
    }
  }, [chartConfigs, onChartConfigChange])

  /**
   * Subscribe on mount and when config changes
   */
  useEffect(() => {
    if (enabled) {
      subscribe()
    }

    return () => {
      unsubscribe()
    }
  }, [enabled, subscribe, unsubscribe])

  /**
   * Get instruments data
   */
  const instrumentsData = useMemo(() => {
    return state.instruments.filter(instrument => 
      fullConfig.instruments.includes(instrument.symbol)
    )
  }, [state.instruments, fullConfig.instruments])

  if (!enabled) {
    return (
      <div className="text-center p-8 text-gray-400">
        <div className="text-lg mb-2">Real-time updates disabled</div>
        <div className="text-sm">Enable real-time updates to see live price data</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {showStats && (
        <ConnectionStatusIndicator
          status={stats.connectionStatus}
          stats={stats}
          onReconnect={reconnect}
        />
      )}

      <div className={compact ? "space-y-2" : "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"}>
        {instrumentsData.map(instrument => {
          const tick = state.currentTicks.get(instrument.symbol)
          const priceChange = priceChanges.get(instrument.symbol)
          const chartConfig = chartConfigs.find(c => c.instrument === instrument.symbol)

          return (
            <div key={instrument.symbol} className="space-y-2">
              <RealTimePriceDisplay
                instrument={instrument}
                tick={tick || null}
                priceChange={priceChange || null}
                compact={compact}
              />
              
              {!compact && chartConfig && (
                <TimeframeSelector
                  currentTimeframe={chartConfig.timeframe}
                  onTimeframeChange={(timeframe) => 
                    handleTimeframeChange(instrument.symbol, timeframe)
                  }
                />
              )}
            </div>
          )
        })}
      </div>

      {state.errors.realtime && (
        <div className="p-3 bg-red-900/20 border border-red-500/30 rounded text-red-200 text-sm">
          <div className="font-medium">Real-time Error:</div>
          <div>{state.errors.realtime}</div>
          <button
            onClick={reconnect}
            className="mt-2 px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded"
          >
            Retry Connection
          </button>
        </div>
      )}
    </div>
  )
}

export default RealTimePriceUpdates