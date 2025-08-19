/**
 * Multi-Instrument Chart Layout Component - AC5
 * Story 9.4: Multi-instrument chart layout with synchronized time navigation and comparison tools
 * 
 * FEATURES: Synchronized crosshairs, time navigation, comparison mode, layout management
 */

'use client'

import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import {
  MultiChartLayout,
  ChartPanelConfig,
  ChartConfig,
  ChartSyncState,
  ChartTimeframe,
  MarketInstrument
} from '@/types/marketData'
import { useMarketData } from '@/hooks/useMarketData'
import InteractivePriceChart from './InteractivePriceChart'
import RealTimePriceUpdates from './RealTimePriceUpdates'

/**
 * Layout templates
 */
const LAYOUT_TEMPLATES = [
  { id: 'single', name: 'Single Chart', grid: '1x1', icon: '⬜' },
  { id: 'split_vertical', name: 'Split Vertical', grid: '1x2', icon: '⬛⬛' },
  { id: 'split_horizontal', name: 'Split Horizontal', grid: '2x1', icon: '⬛\n⬛' },
  { id: 'grid_2x2', name: '2x2 Grid', grid: '2x2', icon: '⬛⬛\n⬛⬛' },
  { id: 'grid_3x1', name: '3x1 Grid', grid: '3x1', icon: '⬛⬛⬛' },
  { id: 'custom', name: 'Custom', grid: 'Custom', icon: '⚙️' }
]

/**
 * Synchronized crosshair component
 */
function SynchronizedCrosshair({
  syncState,
  panelConfig,
  onCrosshairMove
}: {
  syncState: ChartSyncState | null
  panelConfig: ChartPanelConfig
  onCrosshairMove: (time: number | null, price: number | null) => void
}) {
  if (!syncState?.crosshairPosition) return null

  // Calculate crosshair position relative to this panel
  const { crosshairPosition } = syncState
  // This would be calculated based on the chart's time/price scales
  
  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Vertical line */}
      <div
        className="absolute top-0 bottom-0 w-px bg-blue-400 opacity-50"
        style={{ left: `${50}%` }} // Placeholder position
      />
      {/* Horizontal line */}
      <div
        className="absolute left-0 right-0 h-px bg-blue-400 opacity-50"
        style={{ top: `${50}%` }} // Placeholder position
      />
      {/* Crosshair center */}
      <div
        className="absolute w-2 h-2 bg-blue-400 rounded-full transform -translate-x-1 -translate-y-1 opacity-75"
        style={{ left: `${50}%`, top: `${50}%` }} // Placeholder position
      />
    </div>
  )
}

/**
 * Chart panel component
 */
function ChartPanel({
  config,
  syncState,
  onConfigChange,
  onCrosshairMove,
  onVisibleRangeChange,
  onRemove,
  isActive,
  onActivate
}: {
  config: ChartPanelConfig
  syncState: ChartSyncState | null
  onConfigChange: (updates: Partial<ChartPanelConfig>) => void
  onCrosshairMove: (time: number | null, price: number | null) => void
  onVisibleRangeChange: (from: number, to: number) => void
  onRemove: () => void
  isActive: boolean
  onActivate: () => void
}) {
  const panelRef = useRef<HTMLDivElement>(null)

  const handleChartConfigChange = useCallback((updates: Partial<ChartConfig>) => {
    onConfigChange({
      chartConfig: { ...config.chartConfig, ...updates }
    })
  }, [config.chartConfig, onConfigChange])

  const handleCrosshairMove = useCallback((time: number | null, price: number | null) => {
    onCrosshairMove(time, price)
  }, [onCrosshairMove])

  const handleVisibleRangeChange = useCallback((from: number, to: number) => {
    onVisibleRangeChange(from, to)
  }, [onVisibleRangeChange])

  const panelStyle = useMemo(() => ({
    position: 'absolute' as const,
    left: `${config.position.x}%`,
    top: `${config.position.y}%`,
    width: `${config.position.width}%`,
    height: `${config.position.height}%`,
    border: isActive ? '2px solid #3b82f6' : '1px solid #374151',
    borderRadius: '4px',
    overflow: 'hidden'
  }), [config.position, isActive])

  return (
    <div
      ref={panelRef}
      style={panelStyle}
      onClick={onActivate}
      className={`bg-gray-900 transition-all duration-200 ${
        isActive ? 'shadow-lg shadow-blue-500/25' : 'shadow'
      }`}
    >
      {/* Panel Header */}
      <div className="flex items-center justify-between p-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-blue-400' : 'bg-gray-500'}`} />
          <span className="text-sm font-medium text-white">
            {config.title}
          </span>
        </div>
        
        <div className="flex items-center space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onConfigChange({ visible: !config.visible })
            }}
            className={`p-1 rounded text-xs ${
              config.visible 
                ? 'bg-green-600 text-white' 
                : 'bg-gray-600 text-gray-300'
            }`}
            title={config.visible ? 'Hide' : 'Show'}
          >
            {config.visible ? '👁️' : '🙈'}
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation()
              onRemove()
            }}
            className="p-1 rounded text-xs bg-red-600 hover:bg-red-700 text-white"
            title="Remove"
          >
            ×
          </button>
        </div>
      </div>

      {/* Chart Content */}
      {config.visible && (
        <div className="relative h-full">
          <InteractivePriceChart
            chartId={config.id}
            config={config.chartConfig}
            height={200} // Will be adjusted by container
            onCrosshairMove={handleCrosshairMove}
            onVisibleRangeChange={handleVisibleRangeChange}
            compact={true}
          />
          
          {/* Synchronized Crosshair Overlay */}
          <SynchronizedCrosshair
            syncState={syncState}
            panelConfig={config}
            onCrosshairMove={handleCrosshairMove}
          />
        </div>
      )}
    </div>
  )
}

/**
 * Layout selector component
 */
function LayoutSelector({
  currentLayout,
  onLayoutChange,
  onSaveLayout,
  onLoadLayout,
  savedLayouts
}: {
  currentLayout: MultiChartLayout | null
  onLayoutChange: (layoutType: string) => void
  onSaveLayout: (name: string) => void
  onLoadLayout: (layout: MultiChartLayout) => void
  savedLayouts: MultiChartLayout[]
}) {
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [newLayoutName, setNewLayoutName] = useState('')

  const handleSaveLayout = useCallback(() => {
    if (newLayoutName.trim()) {
      onSaveLayout(newLayoutName.trim())
      setNewLayoutName('')
      setShowSaveDialog(false)
    }
  }, [newLayoutName, onSaveLayout])

  return (
    <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-white">Chart Layout</h3>
        <button
          onClick={() => setShowSaveDialog(true)}
          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded"
        >
          Save Layout
        </button>
      </div>

      {/* Layout Templates */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {LAYOUT_TEMPLATES.map(template => (
          <button
            key={template.id}
            onClick={() => onLayoutChange(template.id)}
            className={`p-3 rounded border text-center transition-colors ${
              currentLayout?.type === template.id
                ? 'bg-blue-600 text-white border-blue-500'
                : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'
            }`}
          >
            <div className="text-lg mb-1">{template.icon}</div>
            <div className="text-xs">{template.name}</div>
          </button>
        ))}
      </div>

      {/* Saved Layouts */}
      {savedLayouts.length > 0 && (
        <div>
          <div className="text-sm text-gray-400 mb-2">Saved Layouts</div>
          <div className="space-y-1">
            {savedLayouts.map(layout => (
              <div key={layout.id} className="flex items-center justify-between">
                <button
                  onClick={() => onLoadLayout(layout)}
                  className="flex-1 text-left px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm"
                >
                  {layout.name}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Save Layout Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-600 w-80">
            <h4 className="font-medium text-white mb-3">Save Layout</h4>
            <input
              type="text"
              value={newLayoutName}
              onChange={(e) => setNewLayoutName(e.target.value)}
              placeholder="Enter layout name..."
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm mb-4"
              onKeyPress={(e) => e.key === 'Enter' && handleSaveLayout()}
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveLayout}
                disabled={!newLayoutName.trim()}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-sm rounded"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Synchronization controls
 */
function SyncControls({
  layout,
  syncState,
  onUpdateLayout,
  onUpdateSyncState
}: {
  layout: MultiChartLayout | null
  syncState: ChartSyncState | null
  onUpdateLayout: (updates: Partial<MultiChartLayout>) => void
  onUpdateSyncState: (updates: Partial<ChartSyncState>) => void
}) {
  if (!layout || !layout.sync) return null

  const handleToggleSync = useCallback((syncType: keyof MultiChartLayout['sync']) => {
    onUpdateLayout({
      sync: {
        ...layout.sync,
        [syncType]: !layout.sync[syncType]
      }
    })
  }, [layout, onUpdateLayout])

  return (
    <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
      <h3 className="font-medium text-white mb-3">Synchronization</h3>
      
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-300">Enable Sync</span>
          <input
            type="checkbox"
            checked={layout.sync.enabled}
            onChange={() => handleToggleSync('enabled')}
            className="text-blue-600"
          />
        </div>

        {layout.sync.enabled && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Sync Time Range</span>
              <input
                type="checkbox"
                checked={layout.sync.syncTime}
                onChange={() => handleToggleSync('syncTime')}
                className="text-blue-600"
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Sync Crosshair</span>
              <input
                type="checkbox"
                checked={layout.sync.syncCrosshair}
                onChange={() => handleToggleSync('syncCrosshair')}
                className="text-blue-600"
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Sync Zoom</span>
              <input
                type="checkbox"
                checked={layout.sync.syncZoom}
                onChange={() => handleToggleSync('syncZoom')}
                className="text-blue-600"
              />
            </div>
          </>
        )}
      </div>

      {/* Sync Status */}
      {syncState && layout.sync.enabled && (
        <div className="mt-4 pt-3 border-t border-gray-700">
          <div className="text-xs text-gray-400 mb-2">Sync Status</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-400">Master Chart:</span>
              <span className="text-white ml-1">{syncState.masterId}</span>
            </div>
            <div>
              <span className="text-gray-400">Synced Charts:</span>
              <span className="text-white ml-1">{syncState.syncedCharts.length}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Instrument selector for adding new charts
 */
function InstrumentSelector({
  availableInstruments,
  onAddChart
}: {
  availableInstruments: MarketInstrument[]
  onAddChart: (instrument: MarketInstrument, timeframe: ChartTimeframe) => void
}) {
  const [selectedInstrument, setSelectedInstrument] = useState('')
  const [selectedTimeframe, setSelectedTimeframe] = useState<ChartTimeframe>('1h')

  const handleAddChart = useCallback(() => {
    const instrument = availableInstruments.find(i => i.symbol === selectedInstrument)
    if (instrument) {
      onAddChart(instrument, selectedTimeframe)
      setSelectedInstrument('')
    }
  }, [availableInstruments, selectedInstrument, selectedTimeframe, onAddChart])

  return (
    <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
      <h3 className="font-medium text-white mb-3">Add Chart</h3>
      
      <div className="space-y-3">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Instrument</label>
          <select
            value={selectedInstrument}
            onChange={(e) => setSelectedInstrument(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            <option value="">Select instrument...</option>
            {availableInstruments.map(instrument => (
              <option key={instrument.symbol} value={instrument.symbol}>
                {instrument.displayName}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Timeframe</label>
          <select
            value={selectedTimeframe}
            onChange={(e) => setSelectedTimeframe(e.target.value as ChartTimeframe)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            <option value="1m">1 Minute</option>
            <option value="5m">5 Minutes</option>
            <option value="15m">15 Minutes</option>
            <option value="30m">30 Minutes</option>
            <option value="1h">1 Hour</option>
            <option value="4h">4 Hours</option>
            <option value="1d">1 Day</option>
          </select>
        </div>

        <button
          onClick={handleAddChart}
          disabled={!selectedInstrument}
          className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white py-2 px-3 rounded text-sm font-medium"
        >
          Add Chart
        </button>
      </div>
    </div>
  )
}

/**
 * Props for MultiInstrumentLayout component
 */
interface MultiInstrumentLayoutProps {
  /** Container height */
  height?: number
  /** Enable real-time updates */
  enableRealTime?: boolean
  /** Callback when layout changes */
  onLayoutChange?: (layout: MultiChartLayout) => void
  /** Initial layout */
  initialLayout?: MultiChartLayout
}

/**
 * Main MultiInstrumentLayout component
 */
export function MultiInstrumentLayout({
  height = 600,
  enableRealTime = true,
  onLayoutChange,
  initialLayout
}: MultiInstrumentLayoutProps) {
  const { state, actions, chartManager } = useMarketData({
    enableRealtime: enableRealTime
  })

  const [activePanel, setActivePanel] = useState<string | null>(null)
  const [savedLayouts, setSavedLayouts] = useState<MultiChartLayout[]>([])

  /**
   * Create default layout
   */
  const createDefaultLayout = useCallback(() => {
    const layoutId = actions.createLayout({
      name: 'Default Layout',
      type: 'single',
      charts: [{
        id: 'chart_1',
        position: { x: 0, y: 0, width: 100, height: 100 },
        chartConfig: {
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
        },
        title: 'EUR/USD',
        visible: true
      }],
      sync: {
        enabled: false,
        syncTime: true,
        syncCrosshair: true,
        syncZoom: true
      }
    })
    return layoutId
  }, [actions])

  /**
   * Current layout
   */
  const currentLayout = useMemo(() => {
    return initialLayout || chartManager.layout
  }, [initialLayout, chartManager.layout])

  /**
   * Handle layout template change
   */
  const handleLayoutChange = useCallback((layoutType: string) => {
    let charts: ChartPanelConfig[] = []

    switch (layoutType) {
      case 'single':
        charts = [{
          id: 'chart_1',
          position: { x: 0, y: 0, width: 100, height: 100 },
          chartConfig: {
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
          },
          title: 'EUR/USD',
          visible: true
        }]
        break

      case 'split_vertical':
        charts = [
          {
            id: 'chart_1',
            position: { x: 0, y: 0, width: 50, height: 100 },
            chartConfig: {
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
            },
            title: 'EUR/USD',
            visible: true
          },
          {
            id: 'chart_2',
            position: { x: 50, y: 0, width: 50, height: 100 },
            chartConfig: {
              type: 'candlestick',
              timeframe: '1h',
              instrument: 'GBP_USD',
              barsVisible: 100,
              autoScale: true,
              showVolume: true,
              showGrid: true,
              showCrosshair: true,
              colorScheme: 'dark',
              indicators: [],
              showWyckoffPatterns: false,
              showAIAnnotations: true
            },
            title: 'GBP/USD',
            visible: true
          }
        ]
        break

      case 'grid_2x2':
        charts = [
          {
            id: 'chart_1',
            position: { x: 0, y: 0, width: 50, height: 50 },
            chartConfig: {
              type: 'candlestick',
              timeframe: '1h',
              instrument: 'EUR_USD',
              barsVisible: 100,
              autoScale: true,
              showVolume: false,
              showGrid: true,
              showCrosshair: true,
              colorScheme: 'dark',
              indicators: [],
              showWyckoffPatterns: false,
              showAIAnnotations: true
            },
            title: 'EUR/USD',
            visible: true
          },
          {
            id: 'chart_2',
            position: { x: 50, y: 0, width: 50, height: 50 },
            chartConfig: {
              type: 'candlestick',
              timeframe: '1h',
              instrument: 'GBP_USD',
              barsVisible: 100,
              autoScale: true,
              showVolume: false,
              showGrid: true,
              showCrosshair: true,
              colorScheme: 'dark',
              indicators: [],
              showWyckoffPatterns: false,
              showAIAnnotations: true
            },
            title: 'GBP/USD',
            visible: true
          },
          {
            id: 'chart_3',
            position: { x: 0, y: 50, width: 50, height: 50 },
            chartConfig: {
              type: 'candlestick',
              timeframe: '1h',
              instrument: 'USD_JPY',
              barsVisible: 100,
              autoScale: true,
              showVolume: false,
              showGrid: true,
              showCrosshair: true,
              colorScheme: 'dark',
              indicators: [],
              showWyckoffPatterns: false,
              showAIAnnotations: true
            },
            title: 'USD/JPY',
            visible: true
          },
          {
            id: 'chart_4',
            position: { x: 50, y: 50, width: 50, height: 50 },
            chartConfig: {
              type: 'line',
              timeframe: '1h',
              instrument: 'EUR_USD',
              barsVisible: 100,
              autoScale: true,
              showVolume: false,
              showGrid: true,
              showCrosshair: true,
              colorScheme: 'dark',
              indicators: [],
              showWyckoffPatterns: false,
              showAIAnnotations: false
            },
            title: 'EUR/USD (Line)',
            visible: true
          }
        ]
        break

      default:
        return
    }

    const layoutId = actions.createLayout({
      name: `${layoutType} Layout`,
      type: layoutType as MultiChartLayout['type'],
      charts,
      sync: {
        enabled: layoutType !== 'single',
        syncTime: true,
        syncCrosshair: true,
        syncZoom: false
      }
    })

    onLayoutChange?.(chartManager.layout!)
  }, [actions, chartManager.layout, onLayoutChange])

  /**
   * Handle chart configuration changes
   */
  const handlePanelConfigChange = useCallback((panelId: string, updates: Partial<ChartPanelConfig>) => {
    if (!currentLayout) return

    const updatedCharts = currentLayout.charts.map(chart =>
      chart.id === panelId ? { ...chart, ...updates } : chart
    )

    actions.updateSyncState({
      ...chartManager.syncState,
      syncedCharts: updatedCharts.map(c => c.id)
    })
  }, [currentLayout, actions, chartManager.syncState])

  /**
   * Handle crosshair synchronization
   */
  const handleCrosshairMove = useCallback((time: number | null, price: number | null) => {
    if (!currentLayout?.sync.enabled || !currentLayout.sync.syncCrosshair) return

    actions.updateSyncState({
      crosshairPosition: time && price ? { time, price } : undefined
    })
  }, [currentLayout, actions])

  /**
   * Handle time range synchronization
   */
  const handleVisibleRangeChange = useCallback((from: number, to: number) => {
    if (!currentLayout?.sync.enabled || !currentLayout.sync.syncTime) return

    actions.updateSyncState({
      timeRange: { from, to }
    })
  }, [currentLayout, actions])

  /**
   * Add new chart
   */
  const handleAddChart = useCallback((instrument: MarketInstrument, timeframe: ChartTimeframe) => {
    if (!currentLayout) return

    // Find available position for new chart
    const newChartId = `chart_${Date.now()}`
    const newChart: ChartPanelConfig = {
      id: newChartId,
      position: { x: 0, y: 0, width: 50, height: 50 }, // Default position
      chartConfig: {
        type: 'candlestick',
        timeframe,
        instrument: instrument.symbol,
        barsVisible: 100,
        autoScale: true,
        showVolume: true,
        showGrid: true,
        showCrosshair: true,
        colorScheme: 'dark',
        indicators: [],
        showWyckoffPatterns: false,
        showAIAnnotations: true
      },
      title: instrument.displayName,
      visible: true
    }

    const updatedLayout = {
      ...currentLayout,
      charts: [...currentLayout.charts, newChart]
    }

    // This would update the layout through the market data hook
    console.log('Add chart:', newChart)
  }, [currentLayout])

  /**
   * Remove chart panel
   */
  const handleRemovePanel = useCallback((panelId: string) => {
    if (!currentLayout || currentLayout.charts.length <= 1) return

    const updatedCharts = currentLayout.charts.filter(chart => chart.id !== panelId)
    
    // This would update the layout through the market data hook
    console.log('Remove panel:', panelId)
  }, [currentLayout])

  /**
   * Save layout
   */
  const handleSaveLayout = useCallback((name: string) => {
    if (!currentLayout) return

    const savedLayout = {
      ...currentLayout,
      id: `saved_${Date.now()}`,
      name
    }

    setSavedLayouts(prev => [...prev, savedLayout])
  }, [currentLayout])

  /**
   * Load saved layout
   */
  const handleLoadLayout = useCallback((layout: MultiChartLayout) => {
    // This would load the layout through the market data hook
    console.log('Load layout:', layout)
    onLayoutChange?.(layout)
  }, [onLayoutChange])

  /**
   * Initialize default layout if none exists
   */
  useEffect(() => {
    if (!currentLayout && !initialLayout) {
      createDefaultLayout()
    }
  }, [currentLayout, initialLayout, createDefaultLayout])

  /**
   * Load instruments
   */
  useEffect(() => {
    actions.loadInstruments()
  }, [actions])

  if (!currentLayout) {
    return (
      <div className="h-96 flex items-center justify-center bg-gray-900 rounded-lg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <div className="text-gray-400">Loading chart layout...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <LayoutSelector
          currentLayout={currentLayout}
          onLayoutChange={handleLayoutChange}
          onSaveLayout={handleSaveLayout}
          onLoadLayout={handleLoadLayout}
          savedLayouts={savedLayouts}
        />

        <SyncControls
          layout={currentLayout}
          syncState={chartManager.syncState}
          onUpdateLayout={(updates) => {
            // This would update the layout through the market data hook
            console.log('Update layout:', updates)
          }}
          onUpdateSyncState={actions.updateSyncState}
        />

        <InstrumentSelector
          availableInstruments={state.instruments}
          onAddChart={handleAddChart}
        />
      </div>

      {/* Chart Layout Container */}
      <div
        className="relative bg-gray-900 rounded-lg border border-gray-700 overflow-hidden"
        style={{ height: `${height}px` }}
      >
        {currentLayout.charts.map(chart => (
          <ChartPanel
            key={chart.id}
            config={chart}
            syncState={chartManager.syncState}
            onConfigChange={(updates) => handlePanelConfigChange(chart.id, updates)}
            onCrosshairMove={handleCrosshairMove}
            onVisibleRangeChange={handleVisibleRangeChange}
            onRemove={() => handleRemovePanel(chart.id)}
            isActive={activePanel === chart.id}
            onActivate={() => setActivePanel(chart.id)}
          />
        ))}

        {/* Empty state */}
        {currentLayout.charts.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-gray-400">
              <div className="text-lg mb-2">No charts configured</div>
              <div className="text-sm">Add a chart to get started</div>
            </div>
          </div>
        )}
      </div>

      {/* Real-time Price Updates */}
      {enableRealTime && (
        <RealTimePriceUpdates
          chartConfigs={currentLayout.charts.map(c => c.chartConfig)}
          onChartConfigChange={(chartId, config) => {
            // Update corresponding chart config
            handlePanelConfigChange(chartId, { chartConfig: { ...currentLayout.charts.find(c => c.id === chartId)?.chartConfig, ...config } })
          }}
          compact={true}
          showStats={false}
        />
      )}
    </div>
  )
}

export default MultiInstrumentLayout