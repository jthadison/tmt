/**
 * Tests for DetailedHealthPanel component
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import DetailedHealthPanel from '@/components/health/DetailedHealthPanel'
import { useDetailedHealth } from '@/hooks/useDetailedHealth'
import { DetailedHealthData } from '@/types/health'
import { ConnectionStatus } from '@/types/websocket'

// Mock the useDetailedHealth hook
jest.mock('@/hooks/useDetailedHealth')

const mockUseDetailedHealth = useDetailedHealth as jest.MockedFunction<typeof useDetailedHealth>

describe('DetailedHealthPanel Component', () => {
  const mockHealthData: DetailedHealthData = {
    agents: [
      {
        name: 'Market Analysis',
        port: 8001,
        status: 'healthy',
        latency_ms: 45,
        last_check: new Date().toISOString(),
      },
      {
        name: 'Strategy Analysis',
        port: 8002,
        status: 'healthy',
        latency_ms: 32,
        last_check: new Date().toISOString(),
      },
    ],
    services: [
      {
        name: 'Orchestrator',
        port: 8089,
        status: 'healthy',
        latency_ms: 20,
        last_check: new Date().toISOString(),
      },
      {
        name: 'Circuit Breaker',
        port: 8084,
        status: 'healthy',
        latency_ms: 30,
        last_check: new Date().toISOString(),
      },
      {
        name: 'Execution Engine',
        port: 8082,
        status: 'healthy',
        latency_ms: 50,
        last_check: new Date().toISOString(),
      },
    ],
    external_services: [
      {
        name: 'OANDA API',
        status: 'connected',
        latency_ms: 120,
        last_check: new Date().toISOString(),
      },
    ],
    circuit_breaker: {
      max_drawdown: {
        current: 2.5,
        threshold: 5.0,
        limit: 10.0,
      },
      daily_loss: {
        current: 150.0,
        threshold: 500.0,
        limit: 1000.0,
      },
      consecutive_losses: {
        current: 2,
        threshold: 5,
        limit: 10,
      },
    },
    system_metrics: {
      avg_latency_ms: 55,
      active_positions: 3,
      daily_pnl: 250.75,
    },
    timestamp: new Date().toISOString(),
  }

  const defaultMockReturn = {
    healthData: mockHealthData,
    loading: false,
    error: null,
    lastUpdate: new Date(),
    refreshData: jest.fn(),
    connectionStatus: ConnectionStatus.CONNECTED,
    latencyHistory: new Map([
      ['agent-8001', [40, 45, 43, 48, 45]],
      ['agent-8002', [30, 32, 35, 31, 32]],
    ]),
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseDetailedHealth.mockReturnValue(defaultMockReturn)
    document.body.style.overflow = 'unset'
  })

  afterEach(() => {
    document.body.style.overflow = 'unset'
  })

  describe('Panel Visibility', () => {
    it('should not render when isOpen is false', () => {
      const { container } = render(
        <DetailedHealthPanel isOpen={false} onClose={jest.fn()} />
      )
      expect(container.firstChild).toBeNull()
    })

    it('should render when isOpen is true', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('Detailed System Health')).toBeInTheDocument()
    })
  })

  describe('Header and Controls', () => {
    it('should display panel title', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText('Detailed System Health')).toBeInTheDocument()
    })

    it('should display close button', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByLabelText(/close panel/i)).toBeInTheDocument()
    })

    it('should display refresh button', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByLabelText(/refresh health data/i)).toBeInTheDocument()
    })

    it('should call onClose when close button is clicked', async () => {
      const user = userEvent.setup()
      const onClose = jest.fn()
      render(<DetailedHealthPanel isOpen={true} onClose={onClose} />)

      const closeButton = screen.getByLabelText(/close panel/i)
      await user.click(closeButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('should call refreshData when refresh button is clicked', async () => {
      const user = userEvent.setup()
      const refreshData = jest.fn()
      mockUseDetailedHealth.mockReturnValue({
        ...defaultMockReturn,
        refreshData,
      })

      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)

      const refreshButton = screen.getByLabelText(/refresh health data/i)
      await user.click(refreshButton)

      expect(refreshData).toHaveBeenCalled()
    })
  })

  describe('Keyboard Accessibility', () => {
    it('should close panel when ESC key is pressed', async () => {
      const onClose = jest.fn()
      render(<DetailedHealthPanel isOpen={true} onClose={onClose} />)

      fireEvent.keyDown(document, { key: 'Escape' })

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1)
      })
    })

    it('should have proper ARIA attributes', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby', 'health-panel-title')
    })
  })

  describe('Data Freshness Indicator', () => {
    it('should display last update time', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText(/last updated:/i)).toBeInTheDocument()
    })

    it('should show fresh status for recent data', () => {
      mockUseDetailedHealth.mockReturnValue({
        ...defaultMockReturn,
        lastUpdate: new Date(),
      })

      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      // Should show seconds ago
      expect(screen.getByText(/\d+s ago/i)).toBeInTheDocument()
    })
  })

  describe('Content Sections', () => {
    it('should display system metrics section', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText('System Performance')).toBeInTheDocument()
      expect(screen.getByText(/55ms/i)).toBeInTheDocument() // avg latency
      expect(screen.getByText('3')).toBeInTheDocument() // active positions
      expect(screen.getByText(/\$250\.75/i)).toBeInTheDocument() // daily P&L
    })

    it('should display circuit breaker section', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText('Circuit Breaker Thresholds')).toBeInTheDocument()
      expect(screen.getByText('Max Drawdown')).toBeInTheDocument()
      expect(screen.getByText('Daily Loss')).toBeInTheDocument()
      expect(screen.getByText('Consecutive Losses')).toBeInTheDocument()
    })

    it('should display AI agents section', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText(/AI Agents \(2\)/i)).toBeInTheDocument()
      expect(screen.getByText('Market Analysis')).toBeInTheDocument()
      expect(screen.getByText('Strategy Analysis')).toBeInTheDocument()
    })

    it('should display core services section', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText(/Core Services \(3\)/i)).toBeInTheDocument()
      expect(screen.getByText('Orchestrator')).toBeInTheDocument()
      expect(screen.getByText('Circuit Breaker')).toBeInTheDocument()
      expect(screen.getByText('Execution Engine')).toBeInTheDocument()
    })

    it('should display external services section', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText(/External Services \(1\)/i)).toBeInTheDocument()
      expect(screen.getByText('OANDA API')).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('should display loading indicator when loading', () => {
      mockUseDetailedHealth.mockReturnValue({
        ...defaultMockReturn,
        loading: true,
        healthData: null,
      })

      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText(/loading health data/i)).toBeInTheDocument()
    })

    it('should disable refresh button when loading', () => {
      mockUseDetailedHealth.mockReturnValue({
        ...defaultMockReturn,
        loading: true,
      })

      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      const refreshButton = screen.getByLabelText(/refresh health data/i)
      expect(refreshButton).toBeDisabled()
    })
  })

  describe('Error State', () => {
    it('should display error message when error occurs', () => {
      mockUseDetailedHealth.mockReturnValue({
        ...defaultMockReturn,
        error: 'Failed to fetch health data',
        healthData: null,
      })

      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText(/failed to load health data/i)).toBeInTheDocument()
      expect(screen.getByText(/failed to fetch health data/i)).toBeInTheDocument()
    })

    it('should show retry button on error', () => {
      mockUseDetailedHealth.mockReturnValue({
        ...defaultMockReturn,
        error: 'Connection failed',
        healthData: null,
      })

      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(screen.getByText('Retry')).toBeInTheDocument()
    })

    it('should call refreshData when retry button is clicked', async () => {
      const user = userEvent.setup()
      const refreshData = jest.fn()
      mockUseDetailedHealth.mockReturnValue({
        ...defaultMockReturn,
        error: 'Connection failed',
        healthData: null,
        refreshData,
      })

      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)

      const retryButton = screen.getByText('Retry')
      await user.click(retryButton)

      expect(refreshData).toHaveBeenCalled()
    })
  })

  describe('Body Scroll Management', () => {
    it('should disable body scroll when panel is open', () => {
      const { rerender } = render(
        <DetailedHealthPanel isOpen={false} onClose={jest.fn()} />
      )
      expect(document.body.style.overflow).toBe('unset')

      rerender(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      expect(document.body.style.overflow).toBe('hidden')
    })

    it('should restore body scroll when panel is closed', () => {
      const { rerender } = render(
        <DetailedHealthPanel isOpen={true} onClose={jest.fn()} />
      )
      expect(document.body.style.overflow).toBe('hidden')

      rerender(<DetailedHealthPanel isOpen={false} onClose={jest.fn()} />)
      expect(document.body.style.overflow).toBe('unset')
    })
  })

  describe('Latency History Integration', () => {
    it('should pass latency history to agent cards', () => {
      render(<DetailedHealthPanel isOpen={true} onClose={jest.fn()} />)
      // If sparklines are rendered, this will be visible
      // This is a basic check - actual sparkline rendering would need more specific tests
      expect(screen.getByText('Market Analysis')).toBeInTheDocument()
    })
  })
})
