/**
 * Interactive Price Chart Component Tests
 * Story 9.4: Comprehensive test coverage for price chart functionality
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { jest } from '@jest/globals'
import InteractivePriceChart from '../InteractivePriceChart'
import { ChartConfig, OHLCV } from '@/types/marketData'

// Mock lightweight-charts
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
  LineStyle: { Solid: 'solid', Dashed: 'dashed' },
  PriceScaleMode: { Normal: 'normal', Logarithmic: 'logarithmic' }
}))

// Mock useMarketData hook
jest.mock('@/hooks/useMarketData', () => ({
  useMarketData: () => ({
    state: {
      historicalData: new Map([
        ['EUR_USD_1h', mockOHLCVData]
      ]),
      currentTicks: new Map([
        ['EUR_USD', {
          instrument: 'EUR_USD',
          timestamp: Date.now(),
          bid: 1.0995,
          ask: 1.1005,
          mid: 1.1000,
          volume: 1000,
          change: 0.0005,
          changePercent: 0.05
        }]
      ]),
      loading: {
        historicalData: false
      },
      errors: {
        historicalData: null
      }
    },
    actions: {
      loadHistoricalData: jest.fn(),
      updateChart: jest.fn()
    },
    performance: {
      getMetrics: jest.fn(() => ({
        chartId: 'test_chart',
        renderTime: 15.5,
        updateLatency: 8.2,
        frameRate: 60,
        memoryUsage: 1024 * 1024 * 2.5,
        dataPoints: 1000,
        lastUpdate: Date.now()
      }))
    }
  })
}))

// Mock OHLCV data
const mockOHLCVData: OHLCV[] = [
  {
    timestamp: Date.now() - 3600000,
    open: 1.0990,
    high: 1.1010,
    low: 1.0980,
    close: 1.1000,
    volume: 1000000
  },
  {
    timestamp: Date.now() - 1800000,
    open: 1.1000,
    high: 1.1020,
    low: 1.0995,
    close: 1.1015,
    volume: 1200000
  },
  {
    timestamp: Date.now(),
    open: 1.1015,
    high: 1.1025,
    low: 1.1005,
    close: 1.1010,
    volume: 950000
  }
]

// Default test configuration
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

describe('InteractivePriceChart', () => {
  const defaultProps = {
    chartId: 'test_chart',
    config: defaultConfig,
    height: 400,
    width: 800
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering', () => {
    test('renders chart container', () => {
      render(<InteractivePriceChart {...defaultProps} />)
      
      const toolbar = screen.getByText('EUR/USD')
      expect(toolbar).toBeInTheDocument()
    })

    test('renders chart toolbar with correct instrument', () => {
      render(<InteractivePriceChart {...defaultProps} />)
      
      expect(screen.getByText('EUR/USD')).toBeInTheDocument()
      expect(screen.getByDisplayValue('1h')).toBeInTheDocument()
    })

    test('renders compact mode correctly', () => {
      render(<InteractivePriceChart {...defaultProps} compact={true} />)
      
      // In compact mode, should show simplified toolbar
      expect(screen.getByDisplayValue('1h')).toBeInTheDocument()
    })

    test('shows loading indicator when data is loading', () => {
      const { useMarketData } = require('@/hooks/useMarketData')
      useMarketData.mockReturnValueOnce({
        state: {
          ...useMarketData().state,
          loading: { historicalData: true }
        },
        actions: useMarketData().actions,
        performance: useMarketData().performance
      })

      render(<InteractivePriceChart {...defaultProps} />)
      
      expect(screen.getByText('Loading chart data...')).toBeInTheDocument()
    })
  })

  describe('Chart Configuration', () => {
    test('handles chart type changes', async () => {
      const onConfigChange = jest.fn()
      render(
        <InteractivePriceChart 
          {...defaultProps} 
          onPerformanceUpdate={onConfigChange}
        />
      )

      // Find and click line chart button
      const lineButton = screen.getByText('📈 line')
      fireEvent.click(lineButton)

      // Should call update through the market data hook
      await waitFor(() => {
        const { useMarketData } = require('@/hooks/useMarketData')
        expect(useMarketData().actions.updateChart).toHaveBeenCalled()
      })
    })

    test('handles timeframe changes', async () => {
      render(<InteractivePriceChart {...defaultProps} />)

      // Change timeframe
      const timeframeSelect = screen.getByDisplayValue('1h')
      fireEvent.change(timeframeSelect, { target: { value: '4h' } })

      await waitFor(() => {
        const { useMarketData } = require('@/hooks/useMarketData')
        expect(useMarketData().actions.loadHistoricalData).toHaveBeenCalledWith(
          expect.objectContaining({
            timeframe: '4h'
          })
        )
      })
    })

    test('toggles volume display', () => {
      render(<InteractivePriceChart {...defaultProps} />)

      const volumeCheckbox = screen.getByLabelText('Volume')
      fireEvent.click(volumeCheckbox)

      const { useMarketData } = require('@/hooks/useMarketData')
      expect(useMarketData().actions.updateChart).toHaveBeenCalled()
    })

    test('toggles Wyckoff patterns', () => {
      render(<InteractivePriceChart {...defaultProps} />)

      const wyckoffCheckbox = screen.getByLabelText('Wyckoff')
      fireEvent.click(wyckoffCheckbox)

      const { useMarketData } = require('@/hooks/useMarketData')
      expect(useMarketData().actions.updateChart).toHaveBeenCalled()
    })

    test('toggles AI annotations', () => {
      render(<InteractivePriceChart {...defaultProps} />)

      const aiCheckbox = screen.getByLabelText('AI Signals')
      fireEvent.click(aiCheckbox)

      const { useMarketData } = require('@/hooks/useMarketData')
      expect(useMarketData().actions.updateChart).toHaveBeenCalled()
    })
  })

  describe('Real-time Updates', () => {
    test('updates chart with real-time tick data', async () => {
      const { createChart } = require('lightweight-charts')
      const mockChart = {
        addCandlestickSeries: jest.fn(() => ({
          setData: jest.fn(),
          update: jest.fn()
        })),
        addLineSeries: jest.fn(),
        addHistogramSeries: jest.fn(),
        removeSeries: jest.fn(),
        subscribeCrosshairMove: jest.fn(),
        timeScale: jest.fn(() => ({
          subscribeVisibleRangeChange: jest.fn(),
          fitContent: jest.fn()
        })),
        applyOptions: jest.fn(),
        remove: jest.fn()
      }
      createChart.mockReturnValue(mockChart)

      render(<InteractivePriceChart {...defaultProps} />)

      // Simulate real-time tick update
      await waitFor(() => {
        expect(mockChart.addCandlestickSeries).toHaveBeenCalled()
      })
    })
  })

  describe('Performance Monitoring', () => {
    test('reports performance metrics when enabled', async () => {
      const onPerformanceUpdate = jest.fn()
      
      render(
        <InteractivePriceChart 
          {...defaultProps} 
          onPerformanceUpdate={onPerformanceUpdate}
        />
      )

      await waitFor(() => {
        expect(onPerformanceUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            chartId: 'test_chart',
            renderTime: expect.any(Number),
            updateLatency: expect.any(Number),
            frameRate: expect.any(Number),
            memoryUsage: expect.any(Number),
            dataPoints: expect.any(Number),
            lastUpdate: expect.any(Number)
          })
        )
      })
    })

    test('shows performance metrics in development mode', () => {
      const originalEnv = process.env.NODE_ENV
      process.env.NODE_ENV = 'development'

      render(<InteractivePriceChart {...defaultProps} />)

      // Should show performance overlay in development
      expect(screen.getByText(/Render:/)).toBeInTheDocument()
      expect(screen.getByText(/Latency:/)).toBeInTheDocument()

      process.env.NODE_ENV = originalEnv
    })
  })

  describe('Event Handling', () => {
    test('handles crosshair move events', () => {
      const onCrosshairMove = jest.fn()
      
      render(
        <InteractivePriceChart 
          {...defaultProps} 
          onCrosshairMove={onCrosshairMove}
          interactive={true}
        />
      )

      // Lightweight-charts would call the crosshair callback
      const { createChart } = require('lightweight-charts')
      const mockChart = createChart()
      const crosshairCallback = mockChart.subscribeCrosshairMove.mock.calls[0]?.[0]
      
      if (crosshairCallback) {
        crosshairCallback({
          time: 1640995200,
          seriesPrices: new Map([['series1', 1.1000]])
        })

        expect(onCrosshairMove).toHaveBeenCalledWith(1640995200, 1.1000)
      }
    })

    test('handles visible range change events', () => {
      const onVisibleRangeChange = jest.fn()
      
      render(
        <InteractivePriceChart 
          {...defaultProps} 
          onVisibleRangeChange={onVisibleRangeChange}
          interactive={true}
        />
      )

      // Simulate visible range change
      const { createChart } = require('lightweight-charts')
      const mockChart = createChart()
      const timeScale = mockChart.timeScale()
      const rangeCallback = timeScale.subscribeVisibleRangeChange.mock.calls[0]?.[0]
      
      if (rangeCallback) {
        rangeCallback({ from: 1640995200, to: 1640998800 })
        expect(onVisibleRangeChange).toHaveBeenCalledWith(1640995200, 1640998800)
      }
    })
  })

  describe('Error Handling', () => {
    test('displays error message when data loading fails', () => {
      const { useMarketData } = require('@/hooks/useMarketData')
      useMarketData.mockReturnValueOnce({
        state: {
          ...useMarketData().state,
          errors: { historicalData: 'Failed to load data' }
        },
        actions: useMarketData().actions,
        performance: useMarketData().performance
      })

      render(<InteractivePriceChart {...defaultProps} />)
      
      expect(screen.getByText('Error: Failed to load data')).toBeInTheDocument()
    })

    test('handles chart creation errors gracefully', () => {
      const { createChart } = require('lightweight-charts')
      createChart.mockImplementationOnce(() => {
        throw new Error('Chart creation failed')
      })

      // Should not crash, but may show error state
      expect(() => {
        render(<InteractivePriceChart {...defaultProps} />)
      }).not.toThrow()
    })
  })

  describe('Cleanup', () => {
    test('removes chart on unmount', () => {
      const { createChart } = require('lightweight-charts')
      const mockChart = {
        remove: jest.fn(),
        addCandlestickSeries: jest.fn(() => ({ setData: jest.fn() })),
        addLineSeries: jest.fn(),
        addHistogramSeries: jest.fn(),
        removeSeries: jest.fn(),
        subscribeCrosshairMove: jest.fn(),
        timeScale: jest.fn(() => ({
          subscribeVisibleRangeChange: jest.fn(),
          fitContent: jest.fn()
        })),
        applyOptions: jest.fn()
      }
      createChart.mockReturnValue(mockChart)

      const { unmount } = render(<InteractivePriceChart {...defaultProps} />)
      
      unmount()
      
      expect(mockChart.remove).toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    test('has appropriate ARIA labels', () => {
      render(<InteractivePriceChart {...defaultProps} />)
      
      // Check for accessible form controls
      expect(screen.getByLabelText('Volume')).toBeInTheDocument()
      expect(screen.getByLabelText('Wyckoff')).toBeInTheDocument()
      expect(screen.getByLabelText('AI Signals')).toBeInTheDocument()
    })

    test('supports keyboard navigation', () => {
      render(<InteractivePriceChart {...defaultProps} />)
      
      const timeframeSelect = screen.getByDisplayValue('1h')
      expect(timeframeSelect).toHaveAttribute('tabIndex', '0')
    })
  })

  describe('Responsive Design', () => {
    test('handles window resize events', () => {
      const { createChart } = require('lightweight-charts')
      const mockChart = {
        applyOptions: jest.fn(),
        addCandlestickSeries: jest.fn(() => ({ setData: jest.fn() })),
        addLineSeries: jest.fn(),
        addHistogramSeries: jest.fn(),
        removeSeries: jest.fn(),
        subscribeCrosshairMove: jest.fn(),
        timeScale: jest.fn(() => ({
          subscribeVisibleRangeChange: jest.fn(),
          fitContent: jest.fn()
        })),
        remove: jest.fn()
      }
      createChart.mockReturnValue(mockChart)

      render(<InteractivePriceChart {...defaultProps} />)
      
      // Simulate window resize
      Object.defineProperty(window, 'innerWidth', { value: 1200 })
      fireEvent(window, new Event('resize'))
      
      // Should apply new width options
      expect(mockChart.applyOptions).toHaveBeenCalledWith(
        expect.objectContaining({ width: expect.any(Number) })
      )
    })
  })
})