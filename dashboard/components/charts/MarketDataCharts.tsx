/**
 * Market Data Charts Dashboard - Main Component
 * Story 9.4: Comprehensive market data visualization dashboard integrating all chart components
 * 
 * FEATURES: All acceptance criteria integrated with unified interface
 */

'use client'

import React, { useState, useCallback, useMemo } from 'react'
import {
  ChartTimeframe,
  MarketInstrument,
  ChartConfig,
  AgentAnnotation
} from '@/types/marketData'
import { useMarketData } from '@/hooks/useMarketData'
import InteractivePriceChart from './InteractivePriceChart'
import RealTimePriceUpdates from './RealTimePriceUpdates'
import TechnicalIndicators from './TechnicalIndicators'
import AIAgentAnnotations from './AIAgentAnnotations'
import MultiInstrumentLayout from './MultiInstrumentLayout'

/**
 * Dashboard view modes
 */
type ViewMode = 'single' | 'multi' | 'comparison' | 'indicators' | 'annotations'

/**
 * View mode configuration
 */
const VIEW_MODES = [
  { id: 'single', name: 'Single Chart', icon: '📊', description: 'Single instrument detailed view' },
  { id: 'multi', name: 'Multi-Chart', icon: '📈', description: 'Multiple instruments layout' },
  { id: 'comparison', name: 'Comparison', icon: '⚖️', description: 'Side-by-side comparison' },
  { id: 'indicators', name: 'Technical Analysis', icon: '📉', description: 'Focus on technical indicators' },
  { id: 'annotations', name: 'AI Signals', icon: '🤖', description: 'AI agent annotations view' }
]

/**
 * Dashboard toolbar component
 */
function DashboardToolbar({
  currentMode,
  onModeChange,
  selectedInstrument,
  onInstrumentChange,
  selectedTimeframe,
  onTimeframeChange,
  availableInstruments,
  showPerformance,
  onTogglePerformance,
  enableRealTime,
  onToggleRealTime
}: {
  currentMode: ViewMode
  onModeChange: (mode: ViewMode) => void
  selectedInstrument: string
  onInstrumentChange: (instrument: string) => void
  selectedTimeframe: ChartTimeframe
  onTimeframeChange: (timeframe: ChartTimeframe) => void
  availableInstruments: MarketInstrument[]
  showPerformance: boolean
  onTogglePerformance: () => void
  enableRealTime: boolean
  onToggleRealTime: () => void
}) {
  const timeframes: ChartTimeframe[] = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

  return (
    <div className="flex items-center justify-between p-4 bg-gray-800 border-b border-gray-700">
      {/* Left: View Mode Selector */}
      <div className="flex items-center space-x-4">
        <h2 className="text-xl font-semibold text-white">Market Data Charts</h2>
        
        <div className="flex items-center space-x-1 bg-gray-700 rounded-lg p-1">
          {VIEW_MODES.map(mode => (
            <button
              key={mode.id}
              onClick={() => onModeChange(mode.id as ViewMode)}
              className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
                currentMode === mode.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:text-white hover:bg-gray-600'
              }`}
              title={mode.description}
            >
              <span className="mr-1">{mode.icon}</span>
              <span className="hidden md:inline">{mode.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center space-x-4">
        {/* Instrument Selector */}
        {(currentMode === 'single' || currentMode === 'indicators' || currentMode === 'annotations') && (
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-400">Instrument:</label>
            <select
              value={selectedInstrument}
              onChange={(e) => onInstrumentChange(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm"
            >
              {availableInstruments.map(instrument => (
                <option key={instrument.symbol} value={instrument.symbol}>
                  {instrument.displayName}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Timeframe Selector */}
        {currentMode !== 'multi' && (
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-400">Timeframe:</label>
            <div className="flex space-x-1">
              {timeframes.map(tf => (
                <button
                  key={tf}
                  onClick={() => onTimeframeChange(tf)}
                  className={`px-2 py-1 text-xs rounded ${
                    selectedTimeframe === tf
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Real-time Toggle */}
        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-400">Real-time:</label>
          <button
            onClick={onToggleRealTime}
            className={`px-3 py-1 rounded text-xs font-medium ${
              enableRealTime
                ? 'bg-green-600 text-white'
                : 'bg-gray-600 text-gray-300'
            }`}
          >
            {enableRealTime ? 'ON' : 'OFF'}
          </button>
        </div>

        {/* Performance Monitor Toggle */}
        {process.env.NODE_ENV === 'development' && (
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-400">Performance:</label>
            <button
              onClick={onTogglePerformance}
              className={`px-3 py-1 rounded text-xs font-medium ${
                showPerformance
                  ? 'bg-yellow-600 text-white'
                  : 'bg-gray-600 text-gray-300'
              }`}
            >
              {showPerformance ? 'ON' : 'OFF'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Single chart view component
 */
function SingleChartView({
  instrument,
  timeframe,
  chartConfig,
  onChartConfigChange,
  showPerformance
}: {
  instrument: string
  timeframe: ChartTimeframe
  chartConfig: ChartConfig
  onChartConfigChange: (updates: Partial<ChartConfig>) => void
  showPerformance: boolean
}) {
  const { state } = useMarketData()
  const [activeTab, setActiveTab] = useState<'chart' | 'indicators' | 'annotations'>('chart')

  const chartData = useMemo(() => {
    const key = `${instrument}_${timeframe}`
    return state.historicalData.get(key) || []
  }, [state.historicalData, instrument, timeframe])

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
      <div className="flex space-x-1 bg-gray-700 rounded-lg p-1">
        {[
          { id: 'chart', name: 'Price Chart', icon: '📊' },
          { id: 'indicators', name: 'Technical Analysis', icon: '📉' },
          { id: 'annotations', name: 'AI Signals', icon: '🤖' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:text-white hover:bg-gray-600'
            }`}
          >
            <span className="mr-2">{tab.icon}</span>
            {tab.name}
          </button>
        ))}
      </div>

      {/* Chart Container */}
      <div className="relative">
        <InteractivePriceChart
          chartId="main_chart"
          config={chartConfig}
          height={500}
          onPerformanceUpdate={(metrics) => {
            if (showPerformance) {
              console.log('Chart Performance:', metrics)
            }
          }}
        />
      </div>

      {/* Tab Content */}
      <div className="mt-4">
        {activeTab === 'indicators' && (
          <TechnicalIndicators
            instrument={instrument}
            timeframe={timeframe}
            data={chartData}
            enabledIndicators={chartConfig.indicators.map(i => i.name)}
            enableWyckoffPatterns={chartConfig.showWyckoffPatterns}
            enableVolumeAnalysis={chartConfig.showVolume}
            onIndicatorUpdate={(indicators) =>
              onChartConfigChange({ indicators })
            }
          />
        )}

        {activeTab === 'annotations' && (
          <AIAgentAnnotations
            instrument={instrument}
            timeframe={timeframe}
            chartDimensions={{ width: 800, height: 500 }}
            priceData={chartData}
            visibleRange={{
              from: chartData[0]?.timestamp || Date.now(),
              to: chartData[chartData.length - 1]?.timestamp || Date.now()
            }}
            enabled={chartConfig.showAIAnnotations}
          />
        )}
      </div>
    </div>
  )
}

/**
 * Performance metrics display
 */
function PerformanceMetrics({
  show = false
}: {
  show?: boolean
}) {
  const { performance } = useMarketData()

  if (!show) return null

  return (
    <div className="fixed bottom-4 right-4 bg-gray-900 bg-opacity-90 text-white p-4 rounded-lg border border-gray-600 text-sm">
      <div className="font-medium mb-2">Performance Metrics</div>
      <div className="space-y-1">
        <div>Avg Latency: {performance.getAverageLatency().toFixed(1)}ms</div>
        <div>Memory Usage: {(performance.getMemoryUsage() / 1024 / 1024).toFixed(1)}MB</div>
      </div>
    </div>
  )
}

/**
 * Error boundary for chart components
 */
function ChartErrorBoundary({ 
  children, 
  fallback 
}: { 
  children: React.ReactNode
  fallback?: React.ReactNode 
}) {
  const [hasError, setHasError] = useState(false)

  if (hasError) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-900 rounded-lg border border-gray-700">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-2">Chart Error</div>
          <div className="text-gray-400 text-sm mb-4">
            An error occurred while rendering the chart
          </div>
          <button
            onClick={() => setHasError(false)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

/**
 * Props for MarketDataCharts component
 */
interface MarketDataChartsProps {
  /** Initial view mode */
  initialMode?: ViewMode
  /** Initial instrument */
  initialInstrument?: string
  /** Initial timeframe */
  initialTimeframe?: ChartTimeframe
  /** Enable real-time updates */
  enableRealTime?: boolean
  /** Show performance metrics in development */
  showPerformanceMetrics?: boolean
}

/**
 * Main MarketDataCharts component
 */
export function MarketDataCharts({
  initialMode = 'single',
  initialInstrument = 'EUR_USD',
  initialTimeframe = '1h',
  enableRealTime = true,
  showPerformanceMetrics = false
}: MarketDataChartsProps) {
  const [viewMode, setViewMode] = useState<ViewMode>(initialMode)
  const [selectedInstrument, setSelectedInstrument] = useState(initialInstrument)
  const [selectedTimeframe, setSelectedTimeframe] = useState<ChartTimeframe>(initialTimeframe)
  const [realTimeEnabled, setRealTimeEnabled] = useState(enableRealTime)
  const [showPerformance, setShowPerformance] = useState(showPerformanceMetrics)

  const { state, actions } = useMarketData({
    enableRealtime: realTimeEnabled,
    enablePerformanceMonitoring: showPerformance
  })

  /**
   * Default chart configuration
   */
  const defaultChartConfig: ChartConfig = useMemo(() => ({
    type: 'candlestick',
    timeframe: selectedTimeframe,
    instrument: selectedInstrument,
    barsVisible: 100,
    autoScale: true,
    showVolume: true,
    showGrid: true,
    showCrosshair: true,
    colorScheme: 'dark',
    indicators: [],
    showWyckoffPatterns: false,
    showAIAnnotations: true
  }), [selectedTimeframe, selectedInstrument])

  const [chartConfig, setChartConfig] = useState<ChartConfig>(defaultChartConfig)

  /**
   * Update chart configuration
   */
  const handleChartConfigChange = useCallback((updates: Partial<ChartConfig>) => {
    setChartConfig(prev => ({ ...prev, ...updates }))
  }, [])

  /**
   * Handle mode change
   */
  const handleModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode)
  }, [])

  /**
   * Handle instrument change
   */
  const handleInstrumentChange = useCallback((instrument: string) => {
    setSelectedInstrument(instrument)
    handleChartConfigChange({ instrument })
  }, [handleChartConfigChange])

  /**
   * Handle timeframe change
   */
  const handleTimeframeChange = useCallback((timeframe: ChartTimeframe) => {
    setSelectedTimeframe(timeframe)
    handleChartConfigChange({ timeframe })
  }, [handleChartConfigChange])

  /**
   * Initialize data loading
   */
  React.useEffect(() => {
    actions.loadInstruments()
  }, [actions])

  /**
   * Render view based on current mode
   */
  const renderCurrentView = () => {
    switch (viewMode) {
      case 'single':
        return (
          <SingleChartView
            instrument={selectedInstrument}
            timeframe={selectedTimeframe}
            chartConfig={chartConfig}
            onChartConfigChange={handleChartConfigChange}
            showPerformance={showPerformance}
          />
        )

      case 'multi':
        return (
          <MultiInstrumentLayout
            height={600}
            enableRealTime={realTimeEnabled}
          />
        )

      case 'comparison':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <InteractivePriceChart
                chartId="comparison_1"
                config={{...chartConfig, instrument: selectedInstrument}}
                height={400}
                compact={true}
              />
            </div>
            <div>
              <InteractivePriceChart
                chartId="comparison_2"
                config={{...chartConfig, instrument: 'GBP_USD'}}
                height={400}
                compact={true}
              />
            </div>
          </div>
        )

      case 'indicators':
        const chartData = state.historicalData.get(`${selectedInstrument}_${selectedTimeframe}`) || []
        return (
          <div className="space-y-4">
            <InteractivePriceChart
              chartId="indicators_chart"
              config={chartConfig}
              height={400}
            />
            <TechnicalIndicators
              instrument={selectedInstrument}
              timeframe={selectedTimeframe}
              data={chartData}
              enableWyckoffPatterns={true}
              enableVolumeAnalysis={true}
            />
          </div>
        )

      case 'annotations':
        const annotationData = state.historicalData.get(`${selectedInstrument}_${selectedTimeframe}`) || []
        return (
          <div className="space-y-4">
            <InteractivePriceChart
              chartId="annotations_chart"
              config={{...chartConfig, showAIAnnotations: true}}
              height={400}
            />
            <AIAgentAnnotations
              instrument={selectedInstrument}
              timeframe={selectedTimeframe}
              chartDimensions={{ width: 800, height: 400 }}
              priceData={annotationData}
              visibleRange={{
                from: annotationData[0]?.timestamp || Date.now(),
                to: annotationData[annotationData.length - 1]?.timestamp || Date.now()
              }}
              enabled={true}
            />
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <ChartErrorBoundary>
        {/* Dashboard Toolbar */}
        <DashboardToolbar
          currentMode={viewMode}
          onModeChange={handleModeChange}
          selectedInstrument={selectedInstrument}
          onInstrumentChange={handleInstrumentChange}
          selectedTimeframe={selectedTimeframe}
          onTimeframeChange={handleTimeframeChange}
          availableInstruments={state.instruments}
          showPerformance={showPerformance}
          onTogglePerformance={() => setShowPerformance(!showPerformance)}
          enableRealTime={realTimeEnabled}
          onToggleRealTime={() => setRealTimeEnabled(!realTimeEnabled)}
        />

        {/* Main Content */}
        <div className="p-4">
          {renderCurrentView()}
        </div>

        {/* Real-time Status */}
        {realTimeEnabled && (
          <div className="fixed bottom-4 left-4">
            <RealTimePriceUpdates
              chartConfigs={[chartConfig]}
              onChartConfigChange={(chartId, config) => 
                handleChartConfigChange(config)
              }
              compact={true}
              showStats={false}
            />
          </div>
        )}

        {/* Performance Metrics */}
        <PerformanceMetrics show={showPerformance} />

        {/* Loading Overlay */}
        {state.loading.instruments && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-gray-900 p-6 rounded-lg text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <div className="text-white">Loading market data...</div>
            </div>
          </div>
        )}

        {/* Error Toast */}
        {Object.values(state.errors).some(error => error) && (
          <div className="fixed top-4 right-4 bg-red-900 border border-red-500 text-red-200 p-4 rounded-lg">
            <div className="font-medium">Error</div>
            <div className="text-sm">
              {Object.values(state.errors).find(error => error)}
            </div>
          </div>
        )}
      </ChartErrorBoundary>
    </div>
  )
}

export default MarketDataCharts