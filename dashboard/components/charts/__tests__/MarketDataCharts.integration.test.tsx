/**
 * Market Data Charts Integration Tests
 * Story 9.4: End-to-end integration testing for complete chart dashboard
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { jest } from '@jest/globals'
import MarketDataCharts from '../MarketDataCharts'
import { MarketInstrument, OHLCV, PriceTick, AgentAnnotation } from '@/types/marketData'

// Mock all chart dependencies
jest.mock('lightweight-charts', () => ({
  createChart: jest.fn(() => ({
    addCandlestickSeries: jest.fn(() => ({
      setData: jest.fn(),
      update: jest.fn()
    })),
    addLineSeries: jest.fn(() => ({
      setData: jest.fn(),
      update: jest.fn()
    })),
    addHistogramSeries: jest.fn(() => ({
      setData: jest.fn(),
      update: jest.fn()
    })),
    removeSeries: jest.fn(),
    subscribeCrosshairMove: jest.fn(),
    timeScale: jest.fn(() => ({
      subscribeVisibleRangeChange: jest.fn(),
      fitContent: jest.fn()
    })),
    applyOptions: jest.fn(),
    remove: jest.fn()
  })),
  ColorType: { Solid: 'solid' },
  CrosshairMode: { Normal: 'normal', Hidden: 'hidden' },
  LineStyle: { Solid: 'solid' },
  PriceScaleMode: { Normal: 'normal' }
}))

// Mock market data service
const mockMarketDataService = {
  getInstruments: jest.fn(),
  getHistoricalData: jest.fn(),
  subscribeToRealtimeData: jest.fn(),
  unsubscribe: jest.fn(),
  getTechnicalIndicators: jest.fn(),
  getWyckoffPatterns: jest.fn(),
  getAIAnnotations: jest.fn()
}

jest.mock('@/services/marketDataService', () => ({
  marketDataService: mockMarketDataService
}))

// Mock instruments data
const mockInstruments: MarketInstrument[] = [
  {
    symbol: 'EUR_USD',
    displayName: 'EUR/USD',
    type: 'forex',
    baseCurrency: 'EUR',
    quoteCurrency: 'USD',
    pipLocation: -4,
    tradingHours: [],
    isActive: true,
    averageSpread: 0.8,
    minTradeSize: 1000,
    maxTradeSize: 10000000
  },
  {
    symbol: 'GBP_USD',
    displayName: 'GBP/USD',
    type: 'forex',
    baseCurrency: 'GBP',
    quoteCurrency: 'USD',
    pipLocation: -4,
    tradingHours: [],
    isActive: true,
    averageSpread: 1.2,
    minTradeSize: 1000,
    maxTradeSize: 10000000
  },
  {
    symbol: 'USD_JPY',
    displayName: 'USD/JPY',
    type: 'forex',
    baseCurrency: 'USD',
    quoteCurrency: 'JPY',
    pipLocation: -2,
    tradingHours: [],
    isActive: true,
    averageSpread: 0.9,
    minTradeSize: 1000,
    maxTradeSize: 10000000
  }
]

// Mock price data
const mockPriceData: OHLCV[] = Array.from({ length: 100 }, (_, i) => ({
  timestamp: Date.now() - (100 - i) * 3600000,
  open: 1.1000 + (Math.random() - 0.5) * 0.01,
  high: 1.1020 + (Math.random() - 0.5) * 0.01,
  low: 1.0980 + (Math.random() - 0.5) * 0.01,
  close: 1.1010 + (Math.random() - 0.5) * 0.01,
  volume: 1000000 + Math.random() * 500000
}))

// Mock real-time ticks
const mockRealTimeTicks: PriceTick[] = [
  {
    instrument: 'EUR_USD',
    timestamp: Date.now(),
    bid: 1.0995,
    ask: 1.1005,
    mid: 1.1000,
    volume: 1000,
    change: 0.0005,
    changePercent: 0.05
  }
]

// Mock AI annotations
const mockAnnotations: AgentAnnotation[] = [
  {
    id: 'ann_001',
    agentId: 'market_analysis',
    agentName: 'Market Analysis Agent',
    type: 'entry',
    timestamp: Date.now() - 1800000,
    price: 1.0980,
    action: 'buy',
    size: 10000,
    confidence: 0.85,
    rationale: 'Strong bullish momentum detected with volume confirmation',
    supportingData: {
      rsi: 35,
      volume_trend: 'increasing',
      wyckoff_phase: 'markup'
    },
    riskAssessment: {
      level: 'medium',
      riskRewardRatio: 2.5,
      stopLossDistance: 50,
      takeProfitDistance: 125,
      maxLoss: 500,
      expectedProfit: 1250
    },
    display: {
      shape: 'triangle',
      color: '#22c55e',
      size: 8,
      label: 'BUY',
      showTooltip: true
    }
  }
]

// Mock useMarketData hook
const mockUseMarketData = {
  state: {
    instruments: mockInstruments,
    historicalData: new Map([
      ['EUR_USD_1h', mockPriceData],
      ['GBP_USD_1h', mockPriceData],
      ['USD_JPY_1h', mockPriceData]
    ]),
    currentTicks: new Map([
      ['EUR_USD', mockRealTimeTicks[0]]
    ]),
    indicators: new Map(),
    wyckoffPatterns: new Map(),
    aiAnnotations: new Map([
      ['EUR_USD', mockAnnotations]
    ]),
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
  },
  actions: {
    loadInstruments: jest.fn(),
    loadHistoricalData: jest.fn(),
    subscribeToRealtime: jest.fn(),
    unsubscribe: jest.fn(),
    loadTechnicalIndicators: jest.fn(),
    loadWyckoffPatterns: jest.fn(),
    loadAIAnnotations: jest.fn(),
    createChart: jest.fn(),
    updateChart: jest.fn(),
    removeChart: jest.fn(),
    setActiveChart: jest.fn(),
    createLayout: jest.fn(),
    updateSyncState: jest.fn(),
    clearData: jest.fn(),
    refreshAll: jest.fn()
  },
  chartManager: {
    configs: new Map(),
    activeChartId: null,
    layout: null,
    syncState: null
  },
  subscriptions: {
    active: [],
    status: new Map()
  },
  performance: {
    getMetrics: jest.fn(() => ({
      chartId: 'test',
      renderTime: 15.5,
      updateLatency: 8.2,
      frameRate: 60,
      memoryUsage: 1024 * 1024 * 2.5,
      dataPoints: 1000,
      lastUpdate: Date.now()
    })),
    getAverageLatency: jest.fn(() => 12.3),
    getMemoryUsage: jest.fn(() => 1024 * 1024 * 3.2)
  }
}

jest.mock('@/hooks/useMarketData', () => ({
  useMarketData: () => mockUseMarketData
}))

describe('MarketDataCharts Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    
    // Setup default service responses
    mockMarketDataService.getInstruments.mockResolvedValue({
      data: mockInstruments,
      status: 'success'
    })
    
    mockMarketDataService.getHistoricalData.mockResolvedValue({
      data: {
        instrument: mockInstruments[0],
        data: mockPriceData,
        totalCount: mockPriceData.length,
        hasMore: false
      },
      status: 'success'
    })
  })

  describe('Dashboard Initialization', () => {
    test('renders main dashboard with toolbar and chart area', async () => {
      render(<MarketDataCharts />)
      
      // Check main elements
      expect(screen.getByText('Market Data Charts')).toBeInTheDocument()
      expect(screen.getByText('Single Chart')).toBeInTheDocument()
      
      // Should load instruments on mount
      await waitFor(() => {
        expect(mockUseMarketData.actions.loadInstruments).toHaveBeenCalled()
      })
    })

    test('displays available view modes', () => {
      render(<MarketDataCharts />)
      
      const viewModes = ['Single Chart', 'Multi-Chart', 'Comparison', 'Technical Analysis', 'AI Signals']
      viewModes.forEach(mode => {
        expect(screen.getByText(mode)).toBeInTheDocument()
      })
    })

    test('shows instrument selector with available instruments', async () => {
      render(<MarketDataCharts />)
      
      await waitFor(() => {
        expect(screen.getByDisplayValue('EUR/USD')).toBeInTheDocument()
      })
    })

    test('shows timeframe selector with available timeframes', () => {
      render(<MarketDataCharts />)
      
      const timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
      timeframes.forEach(tf => {
        expect(screen.getByText(tf)).toBeInTheDocument()
      })
    })
  })

  describe('View Mode Navigation', () => {
    test('switches between view modes', async () => {
      render(<MarketDataCharts />)
      
      // Start in single mode
      expect(screen.getByText('Single Chart')).toHaveClass('bg-blue-600')
      
      // Switch to multi-chart mode
      fireEvent.click(screen.getByText('Multi-Chart'))
      
      await waitFor(() => {
        expect(screen.getByText('Multi-Chart')).toHaveClass('bg-blue-600')
      })
    })

    test('shows appropriate controls for each view mode', async () => {
      render(<MarketDataCharts />)
      
      // Single mode should show instrument selector
      expect(screen.getByText('Instrument:')).toBeInTheDocument()
      
      // Switch to multi-chart mode
      fireEvent.click(screen.getByText('Multi-Chart'))
      
      await waitFor(() => {
        // Multi mode should not show individual instrument selector
        expect(screen.queryByText('Instrument:')).not.toBeInTheDocument()
      })
    })

    test('maintains state when switching view modes', async () => {
      render(<MarketDataCharts />)
      
      // Change timeframe in single mode
      const timeframeButton = screen.getByText('4h')
      fireEvent.click(timeframeButton)
      
      // Switch to comparison mode
      fireEvent.click(screen.getByText('Comparison'))
      
      // Switch back to single mode
      fireEvent.click(screen.getByText('Single Chart'))
      
      await waitFor(() => {
        // Should remember the 4h selection
        expect(screen.getByText('4h')).toHaveClass('bg-blue-600')
      })
    })
  })

  describe('Single Chart Mode', () => {
    test('displays price chart with toolbar', async () => {
      render(<MarketDataCharts initialMode="single" />)
      
      await waitFor(() => {
        expect(screen.getByText('EUR/USD')).toBeInTheDocument()
        expect(screen.getByText('Price Chart')).toBeInTheDocument()
      })
    })

    test('switches between chart tabs', async () => {
      render(<MarketDataCharts initialMode="single" />)
      
      await waitFor(() => {
        // Default to price chart tab
        expect(screen.getByText('Price Chart')).toHaveClass('bg-blue-600')
        
        // Switch to technical analysis tab
        fireEvent.click(screen.getByText('Technical Analysis'))
        expect(screen.getByText('Technical Analysis')).toHaveClass('bg-blue-600')
        
        // Switch to AI signals tab
        fireEvent.click(screen.getByText('AI Signals'))
        expect(screen.getByText('AI Signals')).toHaveClass('bg-blue-600')
      })
    })

    test('handles instrument changes', async () => {
      render(<MarketDataCharts initialMode="single" />)
      
      await waitFor(() => {
        const instrumentSelect = screen.getByDisplayValue('EUR/USD')
        fireEvent.change(instrumentSelect, { target: { value: 'GBP_USD' } })
        
        expect(screen.getByDisplayValue('GBP/USD')).toBeInTheDocument()
      })
    })

    test('handles timeframe changes', async () => {
      render(<MarketDataCharts initialMode="single" />)
      
      const timeframe4h = screen.getByText('4h')
      fireEvent.click(timeframe4h)
      
      await waitFor(() => {
        expect(mockUseMarketData.actions.loadHistoricalData).toHaveBeenCalledWith(
          expect.objectContaining({
            timeframe: '4h'
          })
        )
      })
    })
  })

  describe('Multi-Chart Mode', () => {
    test('displays multi-instrument layout', async () => {
      render(<MarketDataCharts initialMode="multi" />)
      
      await waitFor(() => {
        // Should show layout controls
        expect(screen.getByText('Chart Layout')).toBeInTheDocument()
        expect(screen.getByText('Save Layout')).toBeInTheDocument()
      })
    })

    test('allows layout template selection', async () => {
      render(<MarketDataCharts initialMode="multi" />)
      
      await waitFor(() => {
        const singleLayout = screen.getByText('Single Chart')
        const splitLayout = screen.getByText('Split Vertical')
        const gridLayout = screen.getByText('2x2 Grid')
        
        expect(singleLayout).toBeInTheDocument()
        expect(splitLayout).toBeInTheDocument()
        expect(gridLayout).toBeInTheDocument()
      })
    })
  })

  describe('Comparison Mode', () => {
    test('displays side-by-side charts', async () => {
      render(<MarketDataCharts initialMode="comparison" />)
      
      await waitFor(() => {
        // Should render multiple chart containers
        const charts = screen.getAllByText(/EUR\/USD|GBP\/USD/)
        expect(charts.length).toBeGreaterThan(1)
      })
    })
  })

  describe('Technical Analysis Mode', () => {
    test('displays chart with technical indicators panel', async () => {
      render(<MarketDataCharts initialMode="indicators" />)
      
      await waitFor(() => {
        expect(screen.getByText('Technical Indicators')).toBeInTheDocument()
      })
    })

    test('allows indicator selection and configuration', async () => {
      render(<MarketDataCharts initialMode="indicators" />)
      
      await waitFor(() => {
        // Should show indicator categories
        const trendCategory = screen.getByText('trend')
        expect(trendCategory).toBeInTheDocument()
      })
    })
  })

  describe('AI Signals Mode', () => {
    test('displays chart with AI annotations panel', async () => {
      render(<MarketDataCharts initialMode="annotations" />)
      
      await waitFor(() => {
        expect(screen.getByText('AI Agents')).toBeInTheDocument()
      })
    })

    test('shows available AI agents and annotation counts', async () => {
      render(<MarketDataCharts initialMode="annotations" />)
      
      await waitFor(() => {
        // Should show agent controls
        expect(screen.getByText('market_analysis')).toBeInTheDocument()
      })
    })
  })

  describe('Real-time Updates', () => {
    test('enables/disables real-time updates', async () => {
      render(<MarketDataCharts />)
      
      const realtimeToggle = screen.getByText('ON')
      expect(realtimeToggle).toHaveClass('bg-green-600')
      
      fireEvent.click(realtimeToggle)
      
      await waitFor(() => {
        const offToggle = screen.getByText('OFF')
        expect(offToggle).toHaveClass('bg-gray-600')
      })
    })

    test('displays real-time price updates when enabled', async () => {
      render(<MarketDataCharts enableRealTime={true} />)
      
      await waitFor(() => {
        // Should show real-time price component
        expect(screen.getByText('1.1000')).toBeInTheDocument()
      })
    })

    test('subscribes to real-time data on mount', async () => {
      render(<MarketDataCharts enableRealTime={true} />)
      
      await waitFor(() => {
        expect(mockUseMarketData.actions.subscribeToRealtime).toHaveBeenCalled()
      })
    })
  })

  describe('Performance Monitoring', () => {
    test('shows performance metrics in development mode', () => {
      const originalEnv = process.env.NODE_ENV
      process.env.NODE_ENV = 'development'
      
      render(<MarketDataCharts showPerformanceMetrics={true} />)
      
      expect(screen.getByText('Performance:')).toBeInTheDocument()
      
      process.env.NODE_ENV = originalEnv
    })

    test('toggles performance metrics display', async () => {
      const originalEnv = process.env.NODE_ENV
      process.env.NODE_ENV = 'development'
      
      render(<MarketDataCharts showPerformanceMetrics={false} />)
      
      const performanceToggle = screen.getByText('OFF')
      fireEvent.click(performanceToggle)
      
      await waitFor(() => {
        expect(screen.getByText('ON')).toHaveClass('bg-yellow-600')
      })
      
      process.env.NODE_ENV = originalEnv
    })

    test('displays performance metrics when enabled', async () => {
      render(<MarketDataCharts showPerformanceMetrics={true} />)
      
      await waitFor(() => {
        expect(screen.getByText(/Performance Metrics/)).toBeInTheDocument()
        expect(screen.getByText(/Avg Latency:/)).toBeInTheDocument()
        expect(screen.getByText(/Memory Usage:/)).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    test('displays error messages when data loading fails', async () => {
      // Mock error state
      mockUseMarketData.state.errors.instruments = 'Failed to load instruments'
      
      render(<MarketDataCharts />)
      
      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument()
        expect(screen.getByText('Failed to load instruments')).toBeInTheDocument()
      })
      
      // Reset error state
      mockUseMarketData.state.errors.instruments = null
    })

    test('shows loading overlay during initial data load', async () => {
      // Mock loading state
      mockUseMarketData.state.loading.instruments = true
      
      render(<MarketDataCharts />)
      
      expect(screen.getByText('Loading market data...')).toBeInTheDocument()
      
      // Reset loading state
      mockUseMarketData.state.loading.instruments = false
    })

    test('handles chart component errors gracefully', () => {
      // Mock chart error
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})
      
      render(<MarketDataCharts />)
      
      // Should not crash the entire dashboard
      expect(screen.getByText('Market Data Charts')).toBeInTheDocument()
      
      consoleSpy.mockRestore()
    })
  })

  describe('Data Integration', () => {
    test('loads historical data when instrument or timeframe changes', async () => {
      render(<MarketDataCharts />)
      
      // Change instrument
      await waitFor(() => {
        const instrumentSelect = screen.getByDisplayValue('EUR/USD')
        fireEvent.change(instrumentSelect, { target: { value: 'GBP_USD' } })
      })
      
      expect(mockUseMarketData.actions.loadHistoricalData).toHaveBeenCalledWith(
        expect.objectContaining({
          instrument: 'GBP_USD'
        })
      )
    })

    test('updates charts with real-time price data', async () => {
      render(<MarketDataCharts enableRealTime={true} />)
      
      await waitFor(() => {
        // Should have subscribed to real-time updates
        expect(mockUseMarketData.actions.subscribeToRealtime).toHaveBeenCalled()
      })
    })

    test('loads technical indicators when switching to indicators mode', async () => {
      render(<MarketDataCharts />)
      
      fireEvent.click(screen.getByText('Technical Analysis'))
      
      await waitFor(() => {
        expect(mockUseMarketData.actions.loadTechnicalIndicators).toHaveBeenCalled()
      })
    })

    test('loads AI annotations when switching to annotations mode', async () => {
      render(<MarketDataCharts />)
      
      fireEvent.click(screen.getByText('AI Signals'))
      
      await waitFor(() => {
        expect(mockUseMarketData.actions.loadAIAnnotations).toHaveBeenCalled()
      })
    })
  })

  describe('Responsive Behavior', () => {
    test('adapts layout for different screen sizes', () => {
      // Mock different viewport sizes
      Object.defineProperty(window, 'innerWidth', { value: 768 })
      
      render(<MarketDataCharts />)
      
      // Should show responsive classes
      const toolbar = screen.getByText('Market Data Charts').closest('div')
      expect(toolbar).toHaveClass('flex', 'items-center', 'justify-between')
    })

    test('handles mobile viewport gracefully', () => {
      Object.defineProperty(window, 'innerWidth', { value: 375 })
      
      render(<MarketDataCharts />)
      
      // Should still render main elements
      expect(screen.getByText('Market Data Charts')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    test('provides keyboard navigation support', () => {
      render(<MarketDataCharts />)
      
      // Check that interactive elements are focusable
      const modeButtons = screen.getAllByRole('button')
      modeButtons.forEach(button => {
        expect(button).toHaveAttribute('tabIndex')
      })
    })

    test('provides appropriate ARIA labels', () => {
      render(<MarketDataCharts />)
      
      // Check for accessible selects
      const instrumentSelect = screen.getByDisplayValue('EUR/USD')
      expect(instrumentSelect).toHaveAccessibleName()
    })

    test('supports screen readers with proper semantic structure', () => {
      render(<MarketDataCharts />)
      
      // Check for proper heading hierarchy
      expect(screen.getByRole('heading', { name: 'Market Data Charts' })).toBeInTheDocument()
    })
  })
})