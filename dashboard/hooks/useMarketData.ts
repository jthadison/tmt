/**
 * Market Data Hook
 * Story 9.4: React hook for managing market data state, subscriptions, and chart interactions
 * 
 * PERFORMANCE: Optimized for real-time updates with minimal re-renders
 */

'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  MarketInstrument,
  OHLCV,
  PriceTick,
  ChartTimeframe,
  ChartConfig,
  TechnicalIndicator,
  WyckoffPattern,
  AgentAnnotation,
  MarketDataRequest,
  RealtimeSubscription,
  ChartPerformance,
  MultiChartLayout,
  ChartSyncState,
  MarketDataServiceResponse
} from '@/types/marketData'
import { marketDataService } from '@/services/marketDataService'

/**
 * Market data hook state interface
 */
interface UseMarketDataState {
  /** Available instruments */
  instruments: MarketInstrument[]
  /** Historical market data */
  historicalData: Map<string, OHLCV[]>
  /** Real-time price ticks */
  currentTicks: Map<string, PriceTick>
  /** Technical indicators */
  indicators: Map<string, TechnicalIndicator[]>
  /** Wyckoff patterns */
  wyckoffPatterns: Map<string, WyckoffPattern[]>
  /** AI agent annotations */
  aiAnnotations: Map<string, AgentAnnotation[]>
  /** Chart performance metrics */
  performanceMetrics: Map<string, ChartPerformance>
  /** Loading states */
  loading: {
    instruments: boolean
    historicalData: boolean
    indicators: boolean
    patterns: boolean
    annotations: boolean
  }
  /** Error states */
  errors: {
    instruments: string | null
    historicalData: string | null
    indicators: string | null
    patterns: string | null
    annotations: string | null
    realtime: string | null
  }
}

/**
 * Market data hook configuration
 */
interface UseMarketDataConfig {
  /** Enable real-time subscriptions */
  enableRealtime: boolean
  /** Auto-refresh interval for data */
  refreshInterval: number
  /** Maximum number of bars to keep in memory */
  maxBarsInMemory: number
  /** Performance monitoring enabled */
  enablePerformanceMonitoring: boolean
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG: UseMarketDataConfig = {
  enableRealtime: true,
  refreshInterval: 60000, // 1 minute
  maxBarsInMemory: 5000,
  enablePerformanceMonitoring: true
}

/**
 * Chart configuration management
 */
interface ChartConfigManager {
  /** Chart configurations by ID */
  configs: Map<string, ChartConfig>
  /** Active chart ID */
  activeChartId: string | null
  /** Multi-chart layout */
  layout: MultiChartLayout | null
  /** Synchronization state */
  syncState: ChartSyncState | null
}

/**
 * Market data hook return interface
 */
interface UseMarketDataReturn {
  /** Current state */
  state: UseMarketDataState
  /** Chart configuration manager */
  chartManager: ChartConfigManager
  /** Actions */
  actions: {
    /** Load instruments */
    loadInstruments: () => Promise<void>
    /** Load historical data */
    loadHistoricalData: (request: MarketDataRequest) => Promise<void>
    /** Subscribe to real-time data */
    subscribeToRealtime: (instruments: string[], dataTypes: ('ticks' | 'bars')[]) => Promise<string>
    /** Unsubscribe from real-time data */
    unsubscribe: (subscriptionId: string) => Promise<void>
    /** Load technical indicators */
    loadTechnicalIndicators: (instrument: string, timeframe: ChartTimeframe, indicators: string[]) => Promise<void>
    /** Load Wyckoff patterns */
    loadWyckoffPatterns: (instrument: string, timeframe: ChartTimeframe, from: Date, to: Date) => Promise<void>
    /** Load AI annotations */
    loadAIAnnotations: (instrument: string, from: Date, to: Date) => Promise<void>
    /** Create chart configuration */
    createChart: (config: Partial<ChartConfig>) => string
    /** Update chart configuration */
    updateChart: (chartId: string, updates: Partial<ChartConfig>) => void
    /** Remove chart */
    removeChart: (chartId: string) => void
    /** Set active chart */
    setActiveChart: (chartId: string) => void
    /** Create multi-chart layout */
    createLayout: (layout: Omit<MultiChartLayout, 'id'>) => string
    /** Update chart synchronization */
    updateSyncState: (syncState: Partial<ChartSyncState>) => void
    /** Clear all data */
    clearData: () => void
    /** Refresh all data */
    refreshAll: () => Promise<void>
  }
  /** Real-time subscription management */
  subscriptions: {
    /** Active subscription IDs */
    active: string[]
    /** Subscription status */
    status: Map<string, 'active' | 'pending' | 'paused' | 'stopped'>
  }
  /** Performance utilities */
  performance: {
    /** Get performance metrics for chart */
    getMetrics: (chartId: string) => ChartPerformance | null
    /** Get average update latency */
    getAverageLatency: () => number
    /** Get memory usage */
    getMemoryUsage: () => number
  }
}

/**
 * Market Data Hook Implementation
 */
export function useMarketData(config?: Partial<UseMarketDataConfig>): UseMarketDataReturn {
  const fullConfig = useMemo(() => ({ ...DEFAULT_CONFIG, ...config }), [config])
  
  // State management
  const [state, setState] = useState<UseMarketDataState>({
    instruments: [],
    historicalData: new Map(),
    currentTicks: new Map(),
    indicators: new Map(),
    wyckoffPatterns: new Map(),
    aiAnnotations: new Map(),
    performanceMetrics: new Map(),
    loading: {
      instruments: false,
      historicalData: false,
      indicators: false,
      patterns: false,
      annotations: false
    },
    errors: {
      instruments: null,
      historicalData: null,
      indicators: null,
      patterns: null,
      annotations: null,
      realtime: null
    }
  })

  // Chart configuration management
  const [chartManager, setChartManager] = useState<ChartConfigManager>({
    configs: new Map(),
    activeChartId: null,
    layout: null,
    syncState: null
  })

  // Subscription management
  const subscriptionsRef = useRef(new Map<string, string>())
  const [subscriptionStatus, setSubscriptionStatus] = useState(new Map<string, 'active' | 'pending' | 'paused' | 'stopped'>())

  // Performance monitoring
  const performanceRef = useRef({
    updateTimes: [] as number[],
    lastUpdateTime: 0,
    memoryUsage: 0
  })

  /**
   * Load available instruments
   */
  const loadInstruments = useCallback(async () => {
    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, instruments: true },
      errors: { ...prev.errors, instruments: null }
    }))

    try {
      const response: MarketDataServiceResponse<MarketInstrument[]> = await marketDataService.getInstruments()
      
      if (response.status === 'success') {
        setState(prev => ({
          ...prev,
          instruments: response.data,
          loading: { ...prev.loading, instruments: false }
        }))
      } else {
        throw new Error(response.error || 'Failed to load instruments')
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: { ...prev.loading, instruments: false },
        errors: { ...prev.errors, instruments: error instanceof Error ? error.message : 'Unknown error' }
      }))
    }
  }, [])

  /**
   * Load historical data
   */
  const loadHistoricalData = useCallback(async (request: MarketDataRequest) => {
    const key = `${request.instrument}_${request.timeframe}`
    
    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, historicalData: true },
      errors: { ...prev.errors, historicalData: null }
    }))

    try {
      const startTime = performance.now()
      const response = await marketDataService.getHistoricalData(request)
      
      if (response.status === 'success') {
        setState(prev => {
          const newHistoricalData = new Map(prev.historicalData)
          newHistoricalData.set(key, response.data.data)
          
          return {
            ...prev,
            historicalData: newHistoricalData,
            loading: { ...prev.loading, historicalData: false }
          }
        })

        // Update performance metrics
        if (fullConfig.enablePerformanceMonitoring) {
          const latency = performance.now() - startTime
          updatePerformanceMetrics(key, {
            renderTime: latency,
            updateLatency: latency,
            dataPoints: response.data.data.length,
            lastUpdate: Date.now()
          })
        }
      } else {
        throw new Error(response.error || 'Failed to load historical data')
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: { ...prev.loading, historicalData: false },
        errors: { ...prev.errors, historicalData: error instanceof Error ? error.message : 'Unknown error' }
      }))
    }
  }, [fullConfig.enablePerformanceMonitoring])

  /**
   * Subscribe to real-time data
   */
  const subscribeToRealtime = useCallback(async (
    instruments: string[], 
    dataTypes: ('ticks' | 'bars')[]
  ): Promise<string> => {
    if (!fullConfig.enableRealtime) {
      throw new Error('Real-time subscriptions are disabled')
    }

    try {
      const subscriptionId = await marketDataService.subscribeToRealtimeData({
        instruments,
        dataTypes,
        onUpdate: (data) => {
          const updateTime = performance.now()
          performanceRef.current.lastUpdateTime = updateTime
          performanceRef.current.updateTimes.push(updateTime)
          
          // Keep only last 100 update times for performance calculation
          if (performanceRef.current.updateTimes.length > 100) {
            performanceRef.current.updateTimes = performanceRef.current.updateTimes.slice(-100)
          }

          if ('bid' in data) {
            // Handle tick data
            const tick = data as PriceTick
            setState(prev => {
              const newTicks = new Map(prev.currentTicks)
              newTicks.set(tick.instrument, tick)
              return { ...prev, currentTicks: newTicks }
            })
          } else {
            // Handle bar data
            const bar = data as OHLCV
            const key = `${instruments[0]}_realtime`
            setState(prev => {
              const newHistoricalData = new Map(prev.historicalData)
              const currentData = newHistoricalData.get(key) || []
              
              // Update or append the latest bar
              const updatedData = [...currentData]
              const lastBarIndex = updatedData.length - 1
              
              if (lastBarIndex >= 0 && updatedData[lastBarIndex].timestamp === bar.timestamp) {
                updatedData[lastBarIndex] = bar
              } else {
                updatedData.push(bar)
                
                // Limit memory usage
                if (updatedData.length > fullConfig.maxBarsInMemory) {
                  updatedData.splice(0, updatedData.length - fullConfig.maxBarsInMemory)
                }
              }
              
              newHistoricalData.set(key, updatedData)
              return { ...prev, historicalData: newHistoricalData }
            })
          }
        },
        onError: (error) => {
          setState(prev => ({
            ...prev,
            errors: { ...prev.errors, realtime: error.message }
          }))
          setSubscriptionStatus(prev => new Map(prev).set(subscriptionId, 'stopped'))
        }
      })

      subscriptionsRef.current.set(subscriptionId, instruments.join(','))
      setSubscriptionStatus(prev => new Map(prev).set(subscriptionId, 'active'))
      
      return subscriptionId
    } catch (error) {
      throw new Error(`Failed to subscribe to real-time data: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }, [fullConfig.enableRealtime, fullConfig.maxBarsInMemory])

  /**
   * Unsubscribe from real-time data
   */
  const unsubscribe = useCallback(async (subscriptionId: string) => {
    try {
      await marketDataService.unsubscribe(subscriptionId)
      subscriptionsRef.current.delete(subscriptionId)
      setSubscriptionStatus(prev => {
        const newStatus = new Map(prev)
        newStatus.delete(subscriptionId)
        return newStatus
      })
    } catch (error) {
      console.error('Failed to unsubscribe:', error)
    }
  }, [])

  /**
   * Load technical indicators
   */
  const loadTechnicalIndicators = useCallback(async (
    instrument: string,
    timeframe: ChartTimeframe,
    indicators: string[]
  ) => {
    const key = `${instrument}_${timeframe}`
    
    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, indicators: true },
      errors: { ...prev.errors, indicators: null }
    }))

    try {
      const response = await marketDataService.getTechnicalIndicators(instrument, timeframe, indicators)
      
      if (response.status === 'success') {
        setState(prev => {
          const newIndicators = new Map(prev.indicators)
          newIndicators.set(key, response.data)
          
          return {
            ...prev,
            indicators: newIndicators,
            loading: { ...prev.loading, indicators: false }
          }
        })
      } else {
        throw new Error(response.error || 'Failed to load technical indicators')
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: { ...prev.loading, indicators: false },
        errors: { ...prev.errors, indicators: error instanceof Error ? error.message : 'Unknown error' }
      }))
    }
  }, [])

  /**
   * Load Wyckoff patterns
   */
  const loadWyckoffPatterns = useCallback(async (
    instrument: string,
    timeframe: ChartTimeframe,
    from: Date,
    to: Date
  ) => {
    const key = `${instrument}_${timeframe}`
    
    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, patterns: true },
      errors: { ...prev.errors, patterns: null }
    }))

    try {
      const response = await marketDataService.getWyckoffPatterns(instrument, timeframe, from, to)
      
      if (response.status === 'success') {
        setState(prev => {
          const newPatterns = new Map(prev.wyckoffPatterns)
          newPatterns.set(key, response.data)
          
          return {
            ...prev,
            wyckoffPatterns: newPatterns,
            loading: { ...prev.loading, patterns: false }
          }
        })
      } else {
        throw new Error(response.error || 'Failed to load Wyckoff patterns')
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: { ...prev.loading, patterns: false },
        errors: { ...prev.errors, patterns: error instanceof Error ? error.message : 'Unknown error' }
      }))
    }
  }, [])

  /**
   * Load AI annotations
   */
  const loadAIAnnotations = useCallback(async (
    instrument: string,
    from: Date,
    to: Date
  ) => {
    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, annotations: true },
      errors: { ...prev.errors, annotations: null }
    }))

    try {
      const response = await marketDataService.getAIAnnotations(instrument, from, to)
      
      if (response.status === 'success') {
        setState(prev => {
          const newAnnotations = new Map(prev.aiAnnotations)
          newAnnotations.set(instrument, response.data)
          
          return {
            ...prev,
            aiAnnotations: newAnnotations,
            loading: { ...prev.loading, annotations: false }
          }
        })
      } else {
        throw new Error(response.error || 'Failed to load AI annotations')
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: { ...prev.loading, annotations: false },
        errors: { ...prev.errors, annotations: error instanceof Error ? error.message : 'Unknown error' }
      }))
    }
  }, [])

  /**
   * Update performance metrics
   */
  const updatePerformanceMetrics = useCallback((chartId: string, metrics: Partial<ChartPerformance>) => {
    setState(prev => {
      const newMetrics = new Map(prev.performanceMetrics)
      const existingMetrics = newMetrics.get(chartId) || {
        chartId,
        renderTime: 0,
        updateLatency: 0,
        frameRate: 60,
        memoryUsage: 0,
        dataPoints: 0,
        lastUpdate: Date.now()
      }
      
      newMetrics.set(chartId, { ...existingMetrics, ...metrics })
      return { ...prev, performanceMetrics: newMetrics }
    })
  }, [])

  /**
   * Chart configuration management functions
   */
  const createChart = useCallback((config: Partial<ChartConfig>): string => {
    const chartId = `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    const defaultConfig: ChartConfig = {
      type: 'candlestick',
      timeframe: '1h',
      instrument: 'EUR_USD',
      barsVisible: 100,
      autoScale: true,
      showVolume: true,
      showGrid: true,
      showCrosshair: true,
      colorScheme: 'dark',
      indicators: [],
      showWyckoffPatterns: false,
      showAIAnnotations: true
    }

    const fullConfig = { ...defaultConfig, ...config }
    
    setChartManager(prev => {
      const newConfigs = new Map(prev.configs)
      newConfigs.set(chartId, fullConfig)
      
      return {
        ...prev,
        configs: newConfigs,
        activeChartId: prev.activeChartId || chartId
      }
    })

    return chartId
  }, [])

  const updateChart = useCallback((chartId: string, updates: Partial<ChartConfig>) => {
    setChartManager(prev => {
      const config = prev.configs.get(chartId)
      if (!config) return prev

      const newConfigs = new Map(prev.configs)
      newConfigs.set(chartId, { ...config, ...updates })
      
      return { ...prev, configs: newConfigs }
    })
  }, [])

  const removeChart = useCallback((chartId: string) => {
    setChartManager(prev => {
      const newConfigs = new Map(prev.configs)
      newConfigs.delete(chartId)
      
      return {
        ...prev,
        configs: newConfigs,
        activeChartId: prev.activeChartId === chartId ? 
          (newConfigs.size > 0 ? newConfigs.keys().next().value : null) : 
          prev.activeChartId
      }
    })
  }, [])

  const setActiveChart = useCallback((chartId: string) => {
    setChartManager(prev => ({
      ...prev,
      activeChartId: prev.configs.has(chartId) ? chartId : prev.activeChartId
    }))
  }, [])

  const createLayout = useCallback((layout: Omit<MultiChartLayout, 'id'>): string => {
    const layoutId = `layout_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const fullLayout: MultiChartLayout = { id: layoutId, ...layout }
    
    setChartManager(prev => ({
      ...prev,
      layout: fullLayout
    }))

    return layoutId
  }, [])

  const updateSyncState = useCallback((syncState: Partial<ChartSyncState>) => {
    setChartManager(prev => ({
      ...prev,
      syncState: prev.syncState ? { ...prev.syncState, ...syncState } : null
    }))
  }, [])

  /**
   * Utility functions
   */
  const clearData = useCallback(() => {
    setState({
      instruments: [],
      historicalData: new Map(),
      currentTicks: new Map(),
      indicators: new Map(),
      wyckoffPatterns: new Map(),
      aiAnnotations: new Map(),
      performanceMetrics: new Map(),
      loading: {
        instruments: false,
        historicalData: false,
        indicators: false,
        patterns: false,
        annotations: false
      },
      errors: {
        instruments: null,
        historicalData: null,
        indicators: null,
        patterns: null,
        annotations: null,
        realtime: null
      }
    })
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.all([
      loadInstruments(),
      // Add other refresh operations as needed
    ])
  }, [loadInstruments])

  /**
   * Performance utilities
   */
  const getMetrics = useCallback((chartId: string): ChartPerformance | null => {
    return state.performanceMetrics.get(chartId) || null
  }, [state.performanceMetrics])

  const getAverageLatency = useCallback((): number => {
    const times = performanceRef.current.updateTimes
    if (times.length < 2) return 0
    
    const differences = []
    for (let i = 1; i < times.length; i++) {
      differences.push(times[i] - times[i - 1])
    }
    
    return differences.reduce((sum, diff) => sum + diff, 0) / differences.length
  }, [])

  const getMemoryUsage = useCallback((): number => {
    // Calculate approximate memory usage
    let usage = 0
    
    state.historicalData.forEach(data => {
      usage += data.length * 48 // Approximate bytes per OHLCV record
    })
    
    state.currentTicks.forEach(() => {
      usage += 64 // Approximate bytes per tick
    })
    
    return usage
  }, [state.historicalData, state.currentTicks])

  /**
   * Auto-refresh effect
   */
  useEffect(() => {
    if (fullConfig.refreshInterval > 0) {
      const interval = setInterval(() => {
        // Auto-refresh logic can be implemented here
      }, fullConfig.refreshInterval)

      return () => clearInterval(interval)
    }
  }, [fullConfig.refreshInterval])

  /**
   * Cleanup effect
   */
  useEffect(() => {
    return () => {
      // Cleanup all subscriptions on unmount
      subscriptionsRef.current.forEach(async (_, subscriptionId) => {
        try {
          await marketDataService.unsubscribe(subscriptionId)
        } catch (error) {
          console.error('Error cleaning up subscription:', error)
        }
      })
    }
  }, [])

  return {
    state,
    chartManager,
    actions: {
      loadInstruments,
      loadHistoricalData,
      subscribeToRealtime,
      unsubscribe,
      loadTechnicalIndicators,
      loadWyckoffPatterns,
      loadAIAnnotations,
      createChart,
      updateChart,
      removeChart,
      setActiveChart,
      createLayout,
      updateSyncState,
      clearData,
      refreshAll
    },
    subscriptions: {
      active: Array.from(subscriptionsRef.current.keys()),
      status: subscriptionStatus
    },
    performance: {
      getMetrics,
      getAverageLatency,
      getMemoryUsage
    }
  }
}