/**
 * Story 9.2: AI Agent Status Monitoring Interface - Validation Tests
 * 
 * Tests all acceptance criteria for agent monitoring functionality
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { AgentMonitor } from '@/components/control-panel/AgentMonitor'
import { SystemControlPanel } from '@/components/control-panel/SystemControlPanel'
import { AgentStatusInfo, AgentControlRequest } from '@/types/systemControl'

// Mock data for testing
const mockAgents: AgentStatusInfo[] = [
  {
    id: 'agent-circuit-breaker',
    name: 'Circuit Breaker Agent',
    type: 'circuit_breaker',
    status: 'active',
    uptime: 7 * 24 * 60 * 60 * 1000, // 7 days
    lastHeartbeat: new Date(Date.now() - 2000),
    performanceMetrics: {
      tasksCompleted: 1247,
      errors: 3,
      avgResponseTime: 45,
      successRate: 99.8
    },
    resourceUsage: {
      cpu: 15.2,
      memory: 128,
      memoryPercentage: 12.8
    },
    config: {
      maxConcurrentTasks: 10,
      taskTimeout: 30000,
      restartPolicy: 'on-failure'
    },
    version: '2.1.3'
  },
  {
    id: 'agent-wyckoff',
    name: 'Wyckoff Analyzer',
    type: 'wyckoff_analyzer',
    status: 'error',
    uptime: 7 * 24 * 60 * 60 * 1000,
    lastHeartbeat: new Date(Date.now() - 15000),
    performanceMetrics: {
      tasksCompleted: 8432,
      errors: 12,
      avgResponseTime: 125,
      successRate: 98.9
    },
    resourceUsage: {
      cpu: 78.4,
      memory: 256,
      memoryPercentage: 25.6
    },
    config: {
      maxConcurrentTasks: 5,
      taskTimeout: 60000,
      restartPolicy: 'on-failure'
    },
    lastError: 'Failed to connect to market data feed',
    version: '3.2.1'
  },
  {
    id: 'agent-risk-manager',
    name: 'Risk Manager',
    type: 'risk_manager',
    status: 'idle',
    uptime: 7 * 24 * 60 * 60 * 1000,
    lastHeartbeat: new Date(Date.now() - 5000),
    performanceMetrics: {
      tasksCompleted: 15678,
      errors: 5,
      avgResponseTime: 32,
      successRate: 99.7
    },
    resourceUsage: {
      cpu: 42.1,
      memory: 192,
      memoryPercentage: 19.2
    },
    config: {
      maxConcurrentTasks: 15,
      taskTimeout: 15000,
      restartPolicy: 'always'
    },
    version: '4.1.0'
  },
  {
    id: 'agent-execution',
    name: 'Execution Controller',
    type: 'execution_controller',
    status: 'restarting',
    uptime: 5 * 60 * 1000, // 5 minutes
    lastHeartbeat: new Date(Date.now() - 30000),
    performanceMetrics: {
      tasksCompleted: 2341,
      errors: 1,
      avgResponseTime: 89,
      successRate: 99.9
    },
    resourceUsage: {
      cpu: 25.7,
      memory: 164,
      memoryPercentage: 16.4
    },
    config: {
      maxConcurrentTasks: 8,
      taskTimeout: 45000,
      restartPolicy: 'always'
    },
    version: '1.5.2'
  },
  {
    id: 'agent-anti-correlation',
    name: 'Anti-Correlation Monitor',
    type: 'anti_correlation',
    status: 'stopped',
    uptime: 0,
    lastHeartbeat: new Date(Date.now() - 5 * 60 * 1000),
    performanceMetrics: {
      tasksCompleted: 567,
      errors: 0,
      avgResponseTime: 67,
      successRate: 100.0
    },
    resourceUsage: {
      cpu: 0,
      memory: 0,
      memoryPercentage: 0
    },
    config: {
      maxConcurrentTasks: 3,
      taskTimeout: 20000,
      restartPolicy: 'never'
    },
    version: '1.2.1'
  }
]

describe('Story 9.2: AI Agent Status Monitoring Interface', () => {
  let mockOnAgentAction: jest.Mock<void, [AgentControlRequest]>

  beforeEach(() => {
    mockOnAgentAction = jest.fn()
  })

  /**
   * AC1: Agent status dashboard displaying real-time health, 
   * activity, and performance metrics for all 8 agents
   */
  describe('AC1: Agent Status Dashboard with Real-time Metrics', () => {
    test('displays all agent information with comprehensive metrics', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Verify all agents are displayed
      expect(screen.getByText('Circuit Breaker Agent')).toBeInTheDocument()
      expect(screen.getByText('Wyckoff Analyzer')).toBeInTheDocument()
      expect(screen.getByText('Risk Manager')).toBeInTheDocument()
      expect(screen.getByText('Execution Controller')).toBeInTheDocument()
      expect(screen.getByText('Anti-Correlation Monitor')).toBeInTheDocument()

      // Verify performance metrics are displayed
      expect(screen.getByText('1,247')).toBeInTheDocument() // tasks completed
      expect(screen.getByText('99.8%')).toBeInTheDocument() // success rate
      expect(screen.getByText('45ms')).toBeInTheDocument() // avg response time

      // Verify resource usage is displayed
      expect(screen.getByText('15.2%')).toBeInTheDocument() // CPU usage
      expect(screen.getByText('128MB')).toBeInTheDocument() // Memory usage

      // Verify uptime formatting
      expect(screen.getByText('7d 0h')).toBeInTheDocument() // uptime display
    })

    test('shows agent count summary', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Should show active agent count
      expect(screen.getByText('1 / 5 active')).toBeInTheDocument()
    })

    test('displays system-wide performance summary', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Check for system summary section
      expect(screen.getByText('System Summary')).toBeInTheDocument()
      expect(screen.getByText('Total Tasks')).toBeInTheDocument()
      expect(screen.getByText('Average Success Rate')).toBeInTheDocument()
      expect(screen.getByText('Total Errors')).toBeInTheDocument()
      expect(screen.getByText('Avg Response Time')).toBeInTheDocument()

      // Verify calculated totals
      expect(screen.getByText('28,265')).toBeInTheDocument() // total tasks
      expect(screen.getByText('21')).toBeInTheDocument() // total errors
    })
  })

  /**
   * AC2: Visual indicators for agent states (active, paused, error, maintenance) 
   * with color-coded status displays
   */
  describe('AC2: Visual Status Indicators with Color Coding', () => {
    test('displays correct status badges and colors for each agent state', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Check for status badges
      expect(screen.getByText('ACTIVE')).toBeInTheDocument()
      expect(screen.getByText('ERROR')).toBeInTheDocument()
      expect(screen.getByText('IDLE')).toBeInTheDocument()
      expect(screen.getByText('RESTARTING')).toBeInTheDocument()
      expect(screen.getByText('STOPPED')).toBeInTheDocument()

      // Verify status icons are present
      expect(screen.getByText('✓')).toBeInTheDocument() // active
      expect(screen.getByText('✗')).toBeInTheDocument() // error
      expect(screen.getByText('○')).toBeInTheDocument() // idle
      expect(screen.getByText('↻')).toBeInTheDocument() // restarting
      expect(screen.getByText('■')).toBeInTheDocument() // stopped
    })

    test('applies appropriate CSS classes for status colors', () => {
      const { container } = render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Check for color-coded elements (classes should be applied)
      const activeElements = container.querySelectorAll('.text-green-400')
      const errorElements = container.querySelectorAll('.text-red-400')
      const idleElements = container.querySelectorAll('.text-yellow-400')
      const restartingElements = container.querySelectorAll('.text-blue-400')

      expect(activeElements.length).toBeGreaterThan(0)
      expect(errorElements.length).toBeGreaterThan(0)
      expect(idleElements.length).toBeGreaterThan(0)
      expect(restartingElements.length).toBeGreaterThan(0)
    })
  })

  /**
   * AC3: Agent activity logs showing recent decisions, 
   * trade executions, and system interactions
   */
  describe('AC3: Agent Activity and Configuration Details', () => {
    test('displays agent configuration information', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Check for configuration details
      expect(screen.getByText('Max Tasks: 10')).toBeInTheDocument()
      expect(screen.getByText('Timeout: 30s')).toBeInTheDocument()
      expect(screen.getByText('Restart: on-failure')).toBeInTheDocument()

      // Verify version information
      expect(screen.getByText('v2.1.3')).toBeInTheDocument()
      expect(screen.getByText('v3.2.1')).toBeInTheDocument()
    })

    test('shows last heartbeat timestamps', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Should display heartbeat times (formatted as local time)
      const heartbeatElements = screen.getAllByText(/Last heartbeat:/)
      expect(heartbeatElements.length).toBe(5) // One for each agent
    })

    test('displays error messages when present', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Check for error message display
      expect(screen.getByText('Error: Failed to connect to market data feed')).toBeInTheDocument()
    })
  })

  /**
   * AC4: Performance metrics display including success rates, 
   * response times, and resource utilization
   */
  describe('AC4: Performance Metrics Display', () => {
    test('shows detailed performance metrics for each agent', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Verify success rate color coding
      const highSuccessRates = screen.getAllByText(/99\.[7-9]%/)
      expect(highSuccessRates.length).toBeGreaterThan(0)

      // Check for resource utilization display
      expect(screen.getByText('78.4%')).toBeInTheDocument() // High CPU usage
      expect(screen.getByText('256MB')).toBeInTheDocument() // Memory usage
    })

    test('applies performance-based color coding', () => {
      const { container } = render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // High success rates should be green
      const greenElements = container.querySelectorAll('.text-green-400')
      expect(greenElements.length).toBeGreaterThan(0)

      // High CPU usage should be red
      const redElements = container.querySelectorAll('.text-red-400')
      expect(redElements.length).toBeGreaterThan(0)
    })

    test('formats memory usage correctly', () => {
      const agentWithLargeMemory: AgentStatusInfo = {
        ...mockAgents[0],
        resourceUsage: {
          cpu: 50,
          memory: 2048, // 2GB
          memoryPercentage: 85
        }
      }

      render(
        <AgentMonitor 
          agents={[agentWithLargeMemory]} 
          onAgentAction={mockOnAgentAction}
        />
      )

      expect(screen.getByText('2.0GB')).toBeInTheDocument()
    })
  })

  /**
   * AC5: Alert notifications for agent failures, timeouts, 
   * or performance degradation
   */
  describe('AC5: Agent Control and Alert System', () => {
    test('provides control buttons for each agent', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Should have control buttons for each agent
      const controlButtons = screen.getAllByText('Control')
      expect(controlButtons).toHaveLength(5)
    })

    test('opens agent control dialog when control button is clicked', async () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Click control button for first agent
      const controlButtons = screen.getAllByText('Control')
      fireEvent.click(controlButtons[0])

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText('Agent Control')).toBeInTheDocument()
        expect(screen.getByText('Circuit Breaker Agent')).toBeInTheDocument()
      })
    })

    test('allows agent action selection and execution', async () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Open control dialog
      const controlButtons = screen.getAllByText('Control')
      fireEvent.click(controlButtons[0])

      // Select restart action
      const actionSelect = screen.getByDisplayValue('Restart Agent')
      fireEvent.change(actionSelect, { target: { value: 'restart' } })

      // Enter reason
      const reasonInput = screen.getByPlaceholderText('Explain why this action is necessary...')
      fireEvent.change(reasonInput, { target: { value: 'High memory usage detected' } })

      // Execute action
      const executeButton = screen.getByText('Execute Action')
      fireEvent.click(executeButton)

      // Verify callback was called
      expect(mockOnAgentAction).toHaveBeenCalledWith({
        agentId: 'agent-circuit-breaker',
        action: 'restart',
        reason: 'High memory usage detected'
      })
    })

    test('shows appropriate warnings for dangerous actions', async () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Open control dialog
      const controlButtons = screen.getAllByText('Control')
      fireEvent.click(controlButtons[0])

      // Select stop action
      const actionSelect = screen.getByDisplayValue('Restart Agent')
      fireEvent.change(actionSelect, { target: { value: 'stop' } })

      // Should show caution warning
      await waitFor(() => {
        expect(screen.getByText('🛑 Caution')).toBeInTheDocument()
        expect(screen.getByText(/Agent will stop completely/)).toBeInTheDocument()
      })
    })
  })

  /**
   * Integration with System Control Panel
   */
  describe('Integration with System Control Panel', () => {
    test('agent monitor integrates correctly in system control panel', () => {
      render(<SystemControlPanel />)

      // Should show agents tab
      expect(screen.getByText('Agents')).toBeInTheDocument()

      // Click on agents tab
      fireEvent.click(screen.getByText('Agents'))

      // Should display agent monitor content
      expect(screen.getByText('Agent Monitor')).toBeInTheDocument()
    })

    test('compact mode works correctly in overview tab', () => {
      render(<SystemControlPanel />)

      // Overview tab should show compact agent monitor
      expect(screen.getByText('Agent Monitor (Overview)')).toBeInTheDocument()
    })
  })

  /**
   * Loading and Error States
   */
  describe('Loading and Error States', () => {
    test('displays loading skeleton when loading', () => {
      render(
        <AgentMonitor 
          agents={[]} 
          onAgentAction={mockOnAgentAction}
          loading={true}
        />
      )

      // Should show loading animation
      const loadingElements = document.querySelectorAll('.animate-pulse')
      expect(loadingElements.length).toBeGreaterThan(0)
    })

    test('handles empty agent list gracefully', () => {
      render(
        <AgentMonitor 
          agents={[]} 
          onAgentAction={mockOnAgentAction}
        />
      )

      // Should show 0 active agents
      expect(screen.getByText('0 / 0 active')).toBeInTheDocument()
    })
  })

  /**
   * Compact Mode Functionality
   */
  describe('Compact Mode', () => {
    test('hides detailed metrics in compact mode', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
          compact={true}
        />
      )

      // Should not show detailed performance metrics
      expect(screen.queryByText('Tasks Completed')).not.toBeInTheDocument()
      expect(screen.queryByText('System Summary')).not.toBeInTheDocument()
    })

    test('still shows essential information in compact mode', () => {
      render(
        <AgentMonitor 
          agents={mockAgents} 
          onAgentAction={mockOnAgentAction}
          compact={true}
        />
      )

      // Should still show agent names and statuses
      expect(screen.getByText('Circuit Breaker Agent')).toBeInTheDocument()
      expect(screen.getByText('ACTIVE')).toBeInTheDocument()
    })
  })
})