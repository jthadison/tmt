/**
 * Interactive Price Chart Component - AC1
 * Story 9.4: Advanced price chart with candlestick, line, and volume displays using lightweight-charts
 * 
 * PERFORMANCE: Optimized for real-time updates with <100ms latency requirements
 */

'use client'

import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { 
  createChart, 
  IChartApi, 
  ISeriesApi, 
  CandlestickData, 
  LineData,
  HistogramData,
  ColorType,
  CrosshairMode,
  LineStyle,
  PriceScaleMode
} from 'lightweight-charts'
import {
  ChartConfig,
  ChartType,
  ChartTimeframe,
  OHLCV,
  PriceTick,
  TechnicalIndicator,
  AgentAnnotation,
  WyckoffPattern,
  ChartPerformance
} from '@/types/marketData'
import { useMarketData } from '@/hooks/useMarketData'

/**
 * Props for InteractivePriceChart component
 */
interface InteractivePriceChartProps {
  /** Unique chart identifier */
  chartId: string
  /** Chart configuration */
  config: ChartConfig
  /** Chart container height */
  height?: number
  /** Chart container width */
  width?: number
  /** Performance monitoring callback */
  onPerformanceUpdate?: (metrics: ChartPerformance) => void
  /** Chart event callbacks */
  onCrosshairMove?: (time: number | null, price: number | null) => void
  onVisibleRangeChange?: (from: number, to: number) => void
  onAnnotationClick?: (annotation: AgentAnnotation) => void
  /** Enable chart interactions */
  interactive?: boolean
  /** Compact mode for multi-chart layouts */
  compact?: boolean
}

/**
 * Chart series management
 */
interface ChartSeries {
  candlestick: ISeriesApi<'Candlestick'> | null
  line: ISeriesApi<'Line'> | null
  volume: ISeriesApi<'Histogram'> | null
  indicators: Map<string, ISeriesApi<'Line'>>
}

/**
 * Performance tracking
 */
interface PerformanceTracker {
  lastUpdateTime: number
  renderTimes: number[]
  frameCount: number
  startTime: number
}

/**
 * Chart toolbar for user controls
 */
function ChartToolbar({
  config,
  onConfigChange,
  onTimeframeChange,
  onChartTypeChange,
  onToggleVolume,
  onToggleIndicators,
  onToggleAnnotations,
  compact = false
}: {
  config: ChartConfig
  onConfigChange: (updates: Partial<ChartConfig>) => void
  onTimeframeChange: (timeframe: ChartTimeframe) => void
  onChartTypeChange: (type: ChartType) => void
  onToggleVolume: () => void
  onToggleIndicators: () => void
  onToggleAnnotations: () => void
  compact?: boolean
}) {
  const timeframes: ChartTimeframe[] = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
  const chartTypes: { value: ChartType; label: string }[] = [
    { value: 'candlestick', label: '🕯️' },
    { value: 'line', label: '📈' },
    { value: 'area', label: '🏔️' }
  ]

  if (compact) {
    return (
      <div className="flex items-center justify-between p-2 bg-gray-800 border-b border-gray-700 text-xs">
        <div className="flex items-center space-x-2">
          <select
            value={config.timeframe}
            onChange={(e) => onTimeframeChange(e.target.value as ChartTimeframe)}
            className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-xs"
          >
            {timeframes.map(tf => (
              <option key={tf} value={tf}>{tf}</option>
            ))}
          </select>
          
          <div className="flex space-x-1">
            {chartTypes.map(type => (
              <button
                key={type.value}
                onClick={() => onChartTypeChange(type.value)}
                className={`p-1 rounded ${
                  config.type === type.value 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-700 text-gray-400 hover:text-white'
                }`}
                title={type.label}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex space-x-1">
          <button
            onClick={onToggleVolume}
            className={`px-2 py-1 rounded text-xs ${
              config.showVolume 
                ? 'bg-green-600 text-white' 
                : 'bg-gray-700 text-gray-400 hover:text-white'
            }`}
          >
            Vol
          </button>
          
          <button
            onClick={onToggleAnnotations}
            className={`px-2 py-1 rounded text-xs ${
              config.showAIAnnotations 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-700 text-gray-400 hover:text-white'
            }`}
          >
            AI
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between p-3 bg-gray-800 border-b border-gray-700">
      <div className="flex items-center space-x-4">
        <h3 className="font-semibold text-white">{config.instrument.replace('_', '/')}</h3>
        
        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-400">Timeframe:</label>
          <select
            value={config.timeframe}
            onChange={(e) => onTimeframeChange(e.target.value as ChartTimeframe)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm"
          >
            {timeframes.map(tf => (
              <option key={tf} value={tf}>{tf}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-400">Chart Type:</label>
          <div className="flex space-x-1">
            {chartTypes.map(type => (
              <button
                key={type.value}
                onClick={() => onChartTypeChange(type.value)}
                className={`px-3 py-1 rounded text-sm ${
                  config.type === type.value 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-700 text-gray-400 hover:text-white'
                }`}
              >
                {type.label} {type.value}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="volume"
            checked={config.showVolume}
            onChange={onToggleVolume}
            className="text-blue-600"
          />
          <label htmlFor="volume" className="text-sm text-gray-300">Volume</label>
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="wyckoff"
            checked={config.showWyckoffPatterns}
            onChange={() => onConfigChange({ showWyckoffPatterns: !config.showWyckoffPatterns })}
            className="text-blue-600"
          />
          <label htmlFor="wyckoff" className="text-sm text-gray-300">Wyckoff</label>
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="annotations"
            checked={config.showAIAnnotations}
            onChange={onToggleAnnotations}
            className="text-blue-600"
          />
          <label htmlFor="annotations" className="text-sm text-gray-300">AI Signals</label>
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="crosshair"
            checked={config.showCrosshair}
            onChange={() => onConfigChange({ showCrosshair: !config.showCrosshair })}
            className="text-blue-600"
          />
          <label htmlFor="crosshair" className="text-sm text-gray-300">Crosshair</label>
        </div>
      </div>
    </div>
  )
}

/**
 * Loading indicator for chart data
 */
function ChartLoadingIndicator() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-75 z-10">
      <div className="flex items-center space-x-2 text-white">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
        <span>Loading chart data...</span>
      </div>
    </div>
  )
}

/**
 * Performance metrics display (dev mode)
 */
function PerformanceMetrics({ 
  metrics,
  show = false 
}: { 
  metrics: ChartPerformance | null
  show?: boolean 
}) {
  if (!show || !metrics) return null

  return (
    <div className="absolute top-2 right-2 bg-gray-900 bg-opacity-90 text-white text-xs p-2 rounded z-20">
      <div>Render: {metrics.renderTime.toFixed(1)}ms</div>
      <div>Latency: {metrics.updateLatency.toFixed(1)}ms</div>
      <div>FPS: {metrics.frameRate.toFixed(0)}</div>
      <div>Points: {metrics.dataPoints.toLocaleString()}</div>
      <div>Memory: {(metrics.memoryUsage / 1024 / 1024).toFixed(1)}MB</div>
    </div>
  )
}

/**
 * Main InteractivePriceChart component
 */
export function InteractivePriceChart({
  chartId,
  config,
  height = 400,
  width,
  onPerformanceUpdate,
  onCrosshairMove,
  onVisibleRangeChange,
  onAnnotationClick,
  interactive = true,
  compact = false
}: InteractivePriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ChartSeries>({
    candlestick: null,
    line: null,
    volume: null,
    indicators: new Map()
  })

  const performanceRef = useRef<PerformanceTracker>({
    lastUpdateTime: 0,
    renderTimes: [],
    frameCount: 0,
    startTime: performance.now()
  })

  const [isLoading, setIsLoading] = useState(true)
  const [showPerformance] = useState(process.env.NODE_ENV === 'development')

  const { state, actions, performance } = useMarketData({
    enableRealtime: true,
    enablePerformanceMonitoring: true
  })

  /**
   * Initialize chart
   */
  const initializeChart = useCallback(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      width: width || chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { type: ColorType.Solid, color: config.colorScheme === 'dark' ? '#1f2937' : '#ffffff' },
        textColor: config.colorScheme === 'dark' ? '#e5e7eb' : '#374151'
      },
      grid: {
        vertLines: { visible: config.showGrid, color: '#374151' },
        horzLines: { visible: config.showGrid, color: '#374151' }
      },
      crosshair: {
        mode: config.showCrosshair ? CrosshairMode.Normal : CrosshairMode.Hidden
      },
      rightPriceScale: {
        scaleMargins: { top: 0.1, bottom: config.showVolume ? 0.4 : 0.1 },
        mode: config.autoScale ? PriceScaleMode.Normal : PriceScaleMode.Logarithmic
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: config.timeframe === '1m' || config.timeframe === '5m',
        borderVisible: false
      },
      handleScroll: interactive,
      handleScale: interactive,
      trackingMode: {
        exitMode: 0
      }
    })

    chartRef.current = chart

    // Set up event handlers
    if (interactive) {
      chart.subscribeCrosshairMove((param) => {
        const time = param.time as number | null
        const price = param.seriesPrices?.size > 0 ? 
          Array.from(param.seriesPrices.values())[0] as number : null
        
        onCrosshairMove?.(time, price)
      })

      chart.timeScale().subscribeVisibleRangeChange((range) => {
        if (range) {
          onVisibleRangeChange?.(range.from as number, range.to as number)
        }
      })
    }

    return chart
  }, [config, height, width, interactive, onCrosshairMove, onVisibleRangeChange])

  /**
   * Create chart series based on configuration
   */
  const createSeries = useCallback((chart: IChartApi) => {
    const series = seriesRef.current

    // Clear existing series
    if (series.candlestick) {
      chart.removeSeries(series.candlestick)
      series.candlestick = null
    }
    if (series.line) {
      chart.removeSeries(series.line)
      series.line = null
    }

    // Create main price series
    if (config.type === 'candlestick') {
      series.candlestick = chart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444'
      })
    } else if (config.type === 'line') {
      series.line = chart.addLineSeries({
        color: '#3b82f6',
        lineWidth: 2,
        lineStyle: LineStyle.Solid,
        lineType: 0,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 6
      })
    }

    // Create volume series if enabled
    if (config.showVolume) {
      if (series.volume) {
        chart.removeSeries(series.volume)
      }
      series.volume = chart.addHistogramSeries({
        color: '#6b7280',
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
        scaleMargins: { top: 0.7, bottom: 0 }
      })
    }

    // Create indicator series
    config.indicators.forEach((indicator, index) => {
      const existingSeries = series.indicators.get(indicator.name)
      if (existingSeries) {
        chart.removeSeries(existingSeries)
      }

      if (indicator.display.visible) {
        const indicatorSeries = chart.addLineSeries({
          color: indicator.display.color,
          lineWidth: indicator.display.lineWidth,
          lineStyle: indicator.display.lineStyle === 'solid' ? LineStyle.Solid : LineStyle.Dashed,
          priceScaleId: indicator.display.showOnPrice ? 'right' : `indicator_${index}`,
          title: indicator.name
        })
        
        series.indicators.set(indicator.name, indicatorSeries)
      }
    })
  }, [config.type, config.showVolume, config.indicators])

  /**
   * Update chart data
   */
  const updateChartData = useCallback((data: OHLCV[]) => {
    if (!chartRef.current || data.length === 0) return

    const startTime = performance.now()
    const series = seriesRef.current

    try {
      // Convert OHLCV data to appropriate format
      if (config.type === 'candlestick' && series.candlestick) {
        const candlestickData: CandlestickData[] = data.map(bar => ({
          time: Math.floor(bar.timestamp / 1000) as any,
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close
        }))
        series.candlestick.setData(candlestickData)
      } else if (config.type === 'line' && series.line) {
        const lineData: LineData[] = data.map(bar => ({
          time: Math.floor(bar.timestamp / 1000) as any,
          value: bar.close
        }))
        series.line.setData(lineData)
      }

      // Update volume data
      if (config.showVolume && series.volume) {
        const volumeData: HistogramData[] = data.map(bar => ({
          time: Math.floor(bar.timestamp / 1000) as any,
          value: bar.volume,
          color: bar.close >= bar.open ? '#22c55e' : '#ef4444'
        }))
        series.volume.setData(volumeData)
      }

      // Auto-fit content if enabled
      if (config.autoScale) {
        chartRef.current.timeScale().fitContent()
      }

      // Update performance metrics
      const renderTime = performance.now() - startTime
      performanceRef.current.renderTimes.push(renderTime)
      performanceRef.current.frameCount++

      // Keep only last 100 render times for average calculation
      if (performanceRef.current.renderTimes.length > 100) {
        performanceRef.current.renderTimes = performanceRef.current.renderTimes.slice(-100)
      }

      const currentMetrics: ChartPerformance = {
        chartId,
        renderTime,
        updateLatency: Date.now() - performanceRef.current.lastUpdateTime,
        frameRate: performanceRef.current.frameCount / ((performance.now() - performanceRef.current.startTime) / 1000),
        memoryUsage: performance.getMemoryUsage(),
        dataPoints: data.length,
        lastUpdate: Date.now()
      }

      onPerformanceUpdate?.(currentMetrics)
    } catch (error) {
      console.error('Error updating chart data:', error)
    }
  }, [config.type, config.showVolume, config.autoScale, chartId, onPerformanceUpdate])

  /**
   * Update real-time tick
   */
  const updateRealTimeTick = useCallback((tick: PriceTick) => {
    if (!chartRef.current || tick.instrument !== config.instrument) return

    performanceRef.current.lastUpdateTime = Date.now()
    
    const series = seriesRef.current
    const time = Math.floor(tick.timestamp / 1000) as any

    // Update the last bar with real-time price
    if (config.type === 'candlestick' && series.candlestick) {
      series.candlestick.update({
        time,
        open: tick.mid,
        high: tick.mid,
        low: tick.mid,
        close: tick.mid
      })
    } else if (config.type === 'line' && series.line) {
      series.line.update({
        time,
        value: tick.mid
      })
    }
  }, [config.instrument, config.type])

  /**
   * Handle configuration changes
   */
  const handleConfigChange = useCallback((updates: Partial<ChartConfig>) => {
    actions.updateChart(chartId, updates)
  }, [actions, chartId])

  const handleTimeframeChange = useCallback((timeframe: ChartTimeframe) => {
    handleConfigChange({ timeframe })
    setIsLoading(true)
    
    // Load new data for the selected timeframe
    const now = new Date()
    const from = new Date(now.getTime() - 24 * 60 * 60 * 1000) // 24 hours ago
    
    actions.loadHistoricalData({
      instrument: config.instrument,
      timeframe,
      from,
      to: now,
      includeVolume: config.showVolume
    }).finally(() => setIsLoading(false))
  }, [actions, config.instrument, config.showVolume, handleConfigChange])

  const handleChartTypeChange = useCallback((type: ChartType) => {
    handleConfigChange({ type })
  }, [handleConfigChange])

  const handleToggleVolume = useCallback(() => {
    handleConfigChange({ showVolume: !config.showVolume })
  }, [config.showVolume, handleConfigChange])

  const handleToggleIndicators = useCallback(() => {
    // Toggle indicator visibility
    const updatedIndicators = config.indicators.map(indicator => ({
      ...indicator,
      display: { ...indicator.display, visible: !indicator.display.visible }
    }))
    handleConfigChange({ indicators: updatedIndicators })
  }, [config.indicators, handleConfigChange])

  const handleToggleAnnotations = useCallback(() => {
    handleConfigChange({ showAIAnnotations: !config.showAIAnnotations })
  }, [config.showAIAnnotations, handleConfigChange])

  /**
   * Initialize chart on mount
   */
  useEffect(() => {
    const chart = initializeChart()
    if (chart) {
      createSeries(chart)
      setIsLoading(false)
    }

    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [initializeChart, createSeries])

  /**
   * Update chart when configuration changes
   */
  useEffect(() => {
    if (chartRef.current) {
      createSeries(chartRef.current)
    }
  }, [createSeries])

  /**
   * Load initial data
   */
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      
      const now = new Date()
      const from = new Date(now.getTime() - 24 * 60 * 60 * 1000)
      
      try {
        await actions.loadHistoricalData({
          instrument: config.instrument,
          timeframe: config.timeframe,
          from,
          to: now,
          includeVolume: config.showVolume
        })
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [actions, config.instrument, config.timeframe, config.showVolume])

  /**
   * Update chart data when historical data changes
   */
  useEffect(() => {
    const key = `${config.instrument}_${config.timeframe}`
    const data = state.historicalData.get(key)
    
    if (data && data.length > 0) {
      updateChartData(data)
    }
  }, [state.historicalData, config.instrument, config.timeframe, updateChartData])

  /**
   * Handle real-time updates
   */
  useEffect(() => {
    const tick = state.currentTicks.get(config.instrument)
    if (tick) {
      updateRealTimeTick(tick)
    }
  }, [state.currentTicks, config.instrument, updateRealTimeTick])

  /**
   * Handle window resize
   */
  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: width || chartContainerRef.current.clientWidth
        })
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [width])

  /**
   * Get current performance metrics
   */
  const currentMetrics = useMemo(() => {
    return performance.getMetrics(chartId)
  }, [performance, chartId])

  return (
    <div className={`relative bg-gray-900 rounded-lg overflow-hidden ${compact ? 'border border-gray-700' : ''}`}>
      <ChartToolbar
        config={config}
        onConfigChange={handleConfigChange}
        onTimeframeChange={handleTimeframeChange}
        onChartTypeChange={handleChartTypeChange}
        onToggleVolume={handleToggleVolume}
        onToggleIndicators={handleToggleIndicators}
        onToggleAnnotations={handleToggleAnnotations}
        compact={compact}
      />
      
      <div 
        ref={chartContainerRef} 
        style={{ height: compact ? height - 40 : height }}
        className="relative"
      />
      
      {isLoading && <ChartLoadingIndicator />}
      
      <PerformanceMetrics 
        metrics={currentMetrics} 
        show={showPerformance}
      />
      
      {state.errors.historicalData && (
        <div className="absolute bottom-2 left-2 bg-red-900 bg-opacity-90 text-red-200 text-sm p-2 rounded z-20">
          Error: {state.errors.historicalData}
        </div>
      )}
    </div>
  )
}

export default InteractivePriceChart