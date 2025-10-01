/**
 * Tests for StatusBar component
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import StatusBar, { HealthIndicator, Metric, OandaConnectionIndicator } from '@/components/health/StatusBar'
import { useSystemHealth } from '@/hooks/useSystemHealth'
import { ConnectionStatus } from '@/types/websocket'
import { SystemHealthStatus } from '@/types/health'

// Mock the useSystemHealth hook
jest.mock('@/hooks/useSystemHealth')

const mockUseSystemHealth = useSystemHealth as jest.MockedFunction<typeof useSystemHealth>

describe('StatusBar Component', () => {
  const mockHealthStatus: SystemHealthStatus = {
    overall: 'healthy',
    agents: [
      {
        name: 'Market Analysis',
        status: 'healthy',
        latency: 45,
        lastChecked: new Date(),
      },
      {
        name: 'Execution Engine',
        status: 'healthy',
        latency: 32,
        lastChecked: new Date(),
      },
      {
        name: 'Orchestrator',
        status: 'healthy',
        latency: 55,
        lastChecked: new Date(),
      },
    ],
    totalAgents: 3,
    healthyAgents: 3,
    averageLatency: 44,
    oandaConnected: true,
    lastUpdate: new Date(),
    uptime: 360000,
  }

  const defaultMockReturn = {
    healthStatus: mockHealthStatus,
    isLoading: false,
    error: null,
    connectionStatus: ConnectionStatus.CONNECTED,
    refresh: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseSystemHealth.mockReturnValue(defaultMockReturn)
  })

  describe('Rendering', () => {
    it('should render the status bar with all indicators', () => {
      render(<StatusBar />)

      // Check for overall health indicator
      expect(screen.getByLabelText(/system status: healthy/i)).toBeInTheDocument()

      // Check for agent count
      expect(screen.getByLabelText(/agents: 3\/3/i)).toBeInTheDocument()

      // Check for latency
      expect(screen.getByLabelText(/latency: 44ms/i)).toBeInTheDocument()

      // Check for OANDA connection
      expect(screen.getByLabelText(/oanda connected/i)).toBeInTheDocument()
    })

    it('should render loading state', () => {
      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: null,
        isLoading: true,
      })

      render(<StatusBar />)
      expect(screen.getByText(/loading system health/i)).toBeInTheDocument()
    })

    it('should render error state', () => {
      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: null,
        error: 'Connection failed',
      })

      render(<StatusBar />)
      expect(screen.getByText(/failed to load system health/i)).toBeInTheDocument()
      expect(screen.getByText(/connection failed/i)).toBeInTheDocument()
    })
  })

  describe('Health Status Aggregation', () => {
    it('should display healthy status when all services are healthy', () => {
      render(<StatusBar />)
      expect(screen.getByLabelText(/system status: healthy/i)).toBeInTheDocument()
    })

    it('should display degraded status when some services are degraded', () => {
      const degradedStatus: SystemHealthStatus = {
        ...mockHealthStatus,
        overall: 'degraded',
        healthyAgents: 2,
        agents: [
          ...mockHealthStatus.agents.slice(0, 2),
          {
            name: 'Pattern Detection',
            status: 'degraded',
            latency: 450,
            lastChecked: new Date(),
          },
        ],
      }

      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: degradedStatus,
      })

      render(<StatusBar />)
      expect(screen.getByLabelText(/system status: degraded/i)).toBeInTheDocument()
    })

    it('should display critical status when services are unhealthy', () => {
      const criticalStatus: SystemHealthStatus = {
        ...mockHealthStatus,
        overall: 'critical',
        healthyAgents: 1,
        agents: [
          mockHealthStatus.agents[0],
          {
            name: 'Execution Engine',
            status: 'critical',
            latency: undefined,
            lastChecked: new Date(),
            message: 'Connection timeout',
          },
          {
            name: 'Orchestrator',
            status: 'critical',
            latency: undefined,
            lastChecked: new Date(),
          },
        ],
      }

      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: criticalStatus,
      })

      render(<StatusBar />)
      expect(screen.getByLabelText(/system status: critical/i)).toBeInTheDocument()
    })
  })

  describe('Agent Count Display', () => {
    it('should display green when all agents are healthy', () => {
      render(<StatusBar />)
      const agentCount = screen.getByLabelText(/agents: 3\/3/i)
      expect(agentCount).toBeInTheDocument()
      // Check the value element has the green color class
      const valueElement = agentCount.querySelector('.text-green-400')
      expect(valueElement).toBeInTheDocument()
    })

    it('should display yellow when 6-7 of 8 agents are healthy', () => {
      const partialHealthy: SystemHealthStatus = {
        ...mockHealthStatus,
        totalAgents: 8,
        healthyAgents: 7,
      }

      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: partialHealthy,
      })

      render(<StatusBar />)
      const agentCount = screen.getByLabelText(/agents: 7\/8/i)
      expect(agentCount).toBeInTheDocument()
      const valueElement = agentCount.querySelector('.text-yellow-400')
      expect(valueElement).toBeInTheDocument()
    })

    it('should display red when less than 6 agents are healthy', () => {
      const unhealthyAgents: SystemHealthStatus = {
        ...mockHealthStatus,
        totalAgents: 8,
        healthyAgents: 4,
      }

      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: unhealthyAgents,
      })

      render(<StatusBar />)
      const agentCount = screen.getByLabelText(/agents: 4\/8/i)
      expect(agentCount).toBeInTheDocument()
      const valueElement = agentCount.querySelector('.text-red-400')
      expect(valueElement).toBeInTheDocument()
    })
  })

  describe('Latency Display', () => {
    it('should display green for latency < 100ms', () => {
      render(<StatusBar />)
      const latency = screen.getByLabelText(/latency: 44ms/i)
      expect(latency).toBeInTheDocument()
      const valueElement = latency.querySelector('.text-green-400')
      expect(valueElement).toBeInTheDocument()
    })

    it('should display yellow for latency 100-300ms', () => {
      const mediumLatency: SystemHealthStatus = {
        ...mockHealthStatus,
        averageLatency: 150,
      }

      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: mediumLatency,
      })

      render(<StatusBar />)
      const latency = screen.getByLabelText(/latency: 150ms/i)
      expect(latency).toBeInTheDocument()
      const valueElement = latency.querySelector('.text-yellow-400')
      expect(valueElement).toBeInTheDocument()
    })

    it('should display red for latency > 300ms', () => {
      const highLatency: SystemHealthStatus = {
        ...mockHealthStatus,
        averageLatency: 450,
      }

      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: highLatency,
      })

      render(<StatusBar />)
      const latency = screen.getByLabelText(/latency: 450ms/i)
      expect(latency).toBeInTheDocument()
      const valueElement = latency.querySelector('.text-red-400')
      expect(valueElement).toBeInTheDocument()
    })
  })

  describe('OANDA Connection Status', () => {
    it('should display connected status when OANDA is connected', () => {
      render(<StatusBar />)
      expect(screen.getByLabelText(/oanda connected/i)).toBeInTheDocument()
    })

    it('should display disconnected status when OANDA is disconnected', () => {
      const disconnected: SystemHealthStatus = {
        ...mockHealthStatus,
        oandaConnected: false,
      }

      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: disconnected,
      })

      render(<StatusBar />)
      expect(screen.getByLabelText(/oanda disconnected/i)).toBeInTheDocument()
    })
  })

  describe('WebSocket and Polling', () => {
    it('should display WebSocket status when connected', () => {
      render(<StatusBar />)
      expect(screen.getByText(/websocket/i)).toBeInTheDocument()
    })

    it('should display Reconnecting status', () => {
      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        connectionStatus: ConnectionStatus.RECONNECTING,
      })

      render(<StatusBar />)
      expect(screen.getByText(/reconnecting/i)).toBeInTheDocument()
    })

    it('should display Polling status when WebSocket fails', () => {
      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        connectionStatus: ConnectionStatus.ERROR,
      })

      render(<StatusBar />)
      expect(screen.getByText(/polling/i)).toBeInTheDocument()
    })

    it('should display stale indicator when data is >2 seconds old', () => {
      const staleStatus: SystemHealthStatus = {
        ...mockHealthStatus,
        lastUpdate: new Date(Date.now() - 3000), // 3 seconds ago
      }

      mockUseSystemHealth.mockReturnValue({
        ...defaultMockReturn,
        healthStatus: staleStatus,
      })

      render(<StatusBar />)
      expect(screen.getByText(/stale/i)).toBeInTheDocument()
    })
  })

  describe('Click-to-Expand Functionality', () => {
    it('should call onExpandClick when status bar is clicked', async () => {
      const user = userEvent.setup()
      const onExpandClick = jest.fn()

      render(<StatusBar onExpandClick={onExpandClick} />)

      // Click on the expand button instead of the entire region
      const expandButton = screen.getByLabelText(/expand detailed health panel/i)
      await user.click(expandButton)

      expect(onExpandClick).toHaveBeenCalledTimes(1)
    })

    it('should display expand button when onExpandClick is provided', () => {
      const onExpandClick = jest.fn()
      render(<StatusBar onExpandClick={onExpandClick} />)

      expect(screen.getByLabelText(/expand detailed health panel/i)).toBeInTheDocument()
    })

    it('should not display expand button when onExpandClick is not provided', () => {
      render(<StatusBar />)

      expect(screen.queryByLabelText(/expand detailed health panel/i)).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<StatusBar />)

      expect(screen.getByRole('region', { name: /system health status bar/i })).toBeInTheDocument()
      expect(screen.getByRole('img', { name: /system status: healthy/i })).toBeInTheDocument()
      expect(screen.getByRole('status', { name: /agents: 3\/3/i })).toBeInTheDocument()
    })

    it('should have icons with aria-hidden', () => {
      const { container } = render(<StatusBar />)
      const icons = container.querySelectorAll('[aria-hidden="true"]')
      expect(icons.length).toBeGreaterThan(0)
    })
  })

  describe('Sub-components', () => {
    describe('HealthIndicator', () => {
      it('should render healthy status', () => {
        render(<HealthIndicator status="healthy" />)
        expect(screen.getByLabelText(/system status: healthy/i)).toBeInTheDocument()
      })

      it('should render degraded status', () => {
        render(<HealthIndicator status="degraded" />)
        expect(screen.getByLabelText(/system status: degraded/i)).toBeInTheDocument()
      })

      it('should render critical status', () => {
        render(<HealthIndicator status="critical" />)
        expect(screen.getByLabelText(/system status: critical/i)).toBeInTheDocument()
      })
    })

    describe('Metric', () => {
      it('should render metric with label and value', () => {
        render(<Metric label="Test" value="100" color="text-green-400" />)
        expect(screen.getByLabelText(/test: 100/i)).toBeInTheDocument()
      })

      it('should display tooltip', () => {
        render(<Metric label="Test" value="100" color="text-green-400" tooltip="Test tooltip" />)
        const metric = screen.getByLabelText(/test: 100/i)
        expect(metric).toHaveAttribute('title', 'Test tooltip')
      })
    })

    describe('OandaConnectionIndicator', () => {
      it('should render connected status', () => {
        render(<OandaConnectionIndicator connected={true} />)
        expect(screen.getByLabelText(/oanda connected/i)).toBeInTheDocument()
      })

      it('should render disconnected status', () => {
        render(<OandaConnectionIndicator connected={false} />)
        expect(screen.getByLabelText(/oanda disconnected/i)).toBeInTheDocument()
      })
    })
  })
})
