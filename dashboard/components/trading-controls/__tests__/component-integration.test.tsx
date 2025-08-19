/**
 * Component Integration Tests for Trading Controls
 * Story 9.5: Comprehensive testing of React components and user interactions
 * 
 * These tests validate:
 * - Component rendering
 * - User interactions
 * - State management
 * - Error handling
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, jest, beforeEach } from '@jest/globals'

import TradingControlsDashboard from '../TradingControlsDashboard'
import AgentControlPanel from '../AgentControlPanel'
import EmergencyControls from '../EmergencyControls'
import ManualTradingInterface from '../ManualTradingInterface'
import RiskParameterTools from '../RiskParameterTools'
import AuditLogViewer from '../AuditLogViewer'

import { TradingControlsProvider } from '@/hooks/useTradingControls'
import { AIAgent, SystemStatus, ManualTradeRequest, RiskParameters, AuditLogEntry } from '@/types/tradingControls'

// Mock data for tests
const mockAgents: AIAgent[] = [
  {
    id: 'agent_001',
    name: 'Risk Management Agent',
    type: 'risk_management',
    status: 'active',
    isActive: true,
    currentParameters: {
      maxPositionSize: 100000,
      riskThreshold: 0.02,
      stopLossPercentage: 0.05
    },
    performance: {
      uptime: 99.5,
      responseTime: 150,
      successRate: 98.2,
      totalActions: 1250,
      errorsResolved: 3
    },
    errorCount: 0,
    lastError: null,
    lastHeartbeat: new Date(Date.now() - 30000), // 30 seconds ago
    createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
    version: '2.1.0'
  },
  {
    id: 'agent_002',
    name: 'Circuit Breaker Agent',
    type: 'circuit_breaker',
    status: 'error',
    isActive: false,
    currentParameters: {
      emergencyThreshold: 0.10,
      cooldownPeriod: 300
    },
    performance: {
      uptime: 95.1,
      responseTime: 85,
      successRate: 96.8,
      totalActions: 892,
      errorsResolved: 12
    },
    errorCount: 2,
    lastError: 'Connection timeout to risk service',
    lastHeartbeat: new Date(Date.now() - 120000), // 2 minutes ago
    createdAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000), // 14 days ago
    version: '1.8.3'
  }
]

const mockSystemStatus: SystemStatus = {
  isHealthy: true,
  uptime: 3600 * 72, // 72 hours
  emergencyStopActive: false,
  riskLevel: 'low',
  activeAgents: 6,
  pausedAgents: 1,
  errorAgents: 1,
  pendingApprovals: 2,
  components: [
    {
      name: 'Database Connection',
      status: 'healthy',
      lastCheck: new Date(),
      responseTime: 25
    },
    {
      name: 'OANDA API',
      status: 'warning',
      lastCheck: new Date(),
      responseTime: 450,
      errorMessage: 'High latency detected'
    }
  ],
  lastUpdated: new Date()
}

const mockTradeRequests: ManualTradeRequest[] = [
  {
    id: 'trade_001',
    userId: 'admin_001',
    action: 'market_buy',
    instrument: 'EUR_USD',
    quantity: 10000,
    accountId: 'account_001',
    justification: 'Strategic position based on market analysis',
    status: 'pending_approval',
    createdAt: new Date(Date.now() - 3600000), // 1 hour ago
    riskAssessment: {
      overall: 'medium',
      factors: [
        {
          name: 'Position Size',
          level: 'medium',
          description: 'Position represents 15% of account balance',
          impact: 40
        }
      ],
      maxDrawdown: 2.5,
      positionImpact: 15.0,
      correlationRisk: 20,
      leverageImpact: 10,
      recommendations: ['Monitor position closely', 'Set stop-loss at 2%'],
      warnings: ['Market volatility is above average'],
      approved: true,
      assessedBy: 'risk_engine',
      assessedAt: new Date()
    },
    complianceCheck: {
      passed: true,
      violations: [],
      warnings: ['Position size approaching daily limit'],
      overrides: [],
      checkedAt: new Date(),
      checkedBy: 'compliance_engine'
    }
  }
]

const mockRiskParameters: RiskParameters[] = [
  {
    id: 'param_001',
    name: 'Maximum Position Size',
    description: 'Maximum size for any single position',
    category: 'position_sizing',
    currentValue: 100000,
    defaultValue: 50000,
    minValue: 10000,
    maxValue: 500000,
    unit: 'USD',
    complianceRequired: true,
    lastModified: new Date(Date.now() - 86400000), // 1 day ago
    lastModifiedBy: 'admin@proptrading.com',
    history: []
  }
]

const mockAuditLogs: AuditLogEntry[] = [
  {
    id: 'audit_001',
    userId: 'admin_001',
    userEmail: 'admin@proptrading.com',
    sessionId: 'session_123',
    action: 'agent_control',
    resource: 'agent',
    resourceId: 'agent_001',
    justification: 'Routine maintenance restart',
    details: {
      agentId: 'agent_001',
      action: 'restart',
      previousStatus: 'error',
      newStatus: 'active'
    },
    result: 'success',
    riskLevel: 'low',
    timestamp: new Date(Date.now() - 1800000), // 30 minutes ago
    ipAddress: '192.168.1.100',
    approvalRequired: false,
    complianceCheck: {
      passed: true,
      violations: [],
      warnings: [],
      overrides: [],
      checkedAt: new Date(),
      checkedBy: 'compliance_engine'
    }
  }
]

// Mock the custom hook
const mockTradingControlsHook = {
  currentUser: {
    id: 'admin_001',
    email: 'admin@proptrading.com',
    role: 'administrator' as const,
    permissions: ['agent_control', 'emergency_stop', 'manual_trading', 'parameter_modification', 'audit_access'],
    isActive: true,
    createdAt: new Date(),
    lastLogin: new Date(),
    sessionId: 'session_123',
    mfaEnabled: true
  },
  isAuthenticated: true,
  agents: mockAgents,
  systemStatus: mockSystemStatus,
  emergencyStops: [],
  tradeRequests: mockTradeRequests,
  riskParameters: mockRiskParameters,
  auditLogs: mockAuditLogs,
  loading: {
    initial: false,
    agents: false,
    emergency: false,
    trading: false,
    parameters: false,
    audit: false,
    refresh: false
  },
  error: null,
  requireAdminAccess: jest.fn(),
  controlAgent: jest.fn().mockResolvedValue(true),
  emergencyStopAll: jest.fn().mockResolvedValue(true),
  clearEmergencyStop: jest.fn().mockResolvedValue(true),
  submitTradeRequest: jest.fn().mockResolvedValue('trade_002'),
  approveTradeRequest: jest.fn().mockResolvedValue(true),
  updateRiskParameter: jest.fn().mockResolvedValue(true),
  refreshAll: jest.fn()
}

jest.mock('@/hooks/useTradingControls', () => ({
  useTradingControls: () => mockTradingControlsHook
}))

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <TradingControlsProvider>
    {children}
  </TradingControlsProvider>
)

describe('TradingControlsDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders dashboard with all tabs', () => {
    render(<TradingControlsDashboard />, { wrapper: TestWrapper })

    expect(screen.getByText('Trading Controls Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Agent Control')).toBeInTheDocument()
    expect(screen.getByText('Emergency')).toBeInTheDocument()
    expect(screen.getByText('Manual Trading')).toBeInTheDocument()
    expect(screen.getByText('Risk Parameters')).toBeInTheDocument()
    expect(screen.getByText('Audit Logs')).toBeInTheDocument()
  })

  it('displays key metrics correctly', () => {
    render(<TradingControlsDashboard />, { wrapper: TestWrapper })

    expect(screen.getByText('6')).toBeInTheDocument() // Active agents
    expect(screen.getByText('1')).toBeInTheDocument() // Error agents
    expect(screen.getByText('2')).toBeInTheDocument() // Pending trades
  })

  it('switches tabs when clicked', async () => {
    const user = userEvent.setup()
    render(<TradingControlsDashboard />, { wrapper: TestWrapper })

    await user.click(screen.getByText('Agent Control'))
    expect(screen.getByText('Agent Control Panel')).toBeInTheDocument()

    await user.click(screen.getByText('Emergency'))
    expect(screen.getByText('Emergency Controls')).toBeInTheDocument()
  })

  it('shows security warning on first load', () => {
    render(<TradingControlsDashboard />, { wrapper: TestWrapper })

    expect(screen.getByText('ADMINISTRATOR ACCESS')).toBeInTheDocument()
    expect(screen.getByText('All actions are logged and audited')).toBeInTheDocument()
  })

  it('refreshes data when refresh button clicked', async () => {
    const user = userEvent.setup()
    render(<TradingControlsDashboard />, { wrapper: TestWrapper })

    const refreshButton = screen.getByText('🔄 Refresh All')
    await user.click(refreshButton)

    expect(mockTradingControlsHook.refreshAll).toHaveBeenCalled()
  })
})

describe('AgentControlPanel', () => {
  const mockOnAgentControl = jest.fn().mockResolvedValue(true)
  const mockOnRefresh = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders agent cards with correct information', () => {
    render(
      <AgentControlPanel
        agents={mockAgents}
        onAgentControl={mockOnAgentControl}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('Risk Management Agent')).toBeInTheDocument()
    expect(screen.getByText('Circuit Breaker Agent')).toBeInTheDocument()
    expect(screen.getByText('99.5%')).toBeInTheDocument() // Uptime
    expect(screen.getByText('150ms')).toBeInTheDocument() // Response time
  })

  it('displays agent status correctly', () => {
    render(
      <AgentControlPanel
        agents={mockAgents}
        onAgentControl={mockOnAgentControl}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('ACTIVE')).toBeInTheDocument()
    expect(screen.getByText('ERROR')).toBeInTheDocument()
  })

  it('shows appropriate control buttons for each agent status', () => {
    render(
      <AgentControlPanel
        agents={mockAgents}
        onAgentControl={mockOnAgentControl}
        onRefresh={mockOnRefresh}
      />
    )

    const agentCards = screen.getAllByTestId(/agent-card/)
    // Active agent should have pause, stop buttons
    // Error agent should have reset errors, restart buttons
    expect(screen.getByText('Pause')).toBeInTheDocument()
    expect(screen.getByText('Reset Errors')).toBeInTheDocument()
  })

  it('opens justification modal when action button clicked', async () => {
    const user = userEvent.setup()
    render(
      <AgentControlPanel
        agents={mockAgents}
        onAgentControl={mockOnAgentControl}
        onRefresh={mockOnRefresh}
      />
    )

    const pauseButton = screen.getByText('Pause')
    await user.click(pauseButton)

    expect(screen.getByText('Confirm Pause - Risk Management Agent')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Explain why you are performing/)).toBeInTheDocument()
  })

  it('calls onAgentControl with correct parameters', async () => {
    const user = userEvent.setup()
    render(
      <AgentControlPanel
        agents={mockAgents}
        onAgentControl={mockOnAgentControl}
        onRefresh={mockOnRefresh}
      />
    )

    const pauseButton = screen.getByText('Pause')
    await user.click(pauseButton)

    const justificationTextarea = screen.getByPlaceholderText(/Explain why you are performing/)
    await user.type(justificationTextarea, 'Routine maintenance pause for system update')

    const confirmButton = screen.getByText('Confirm Pause')
    await user.click(confirmButton)

    expect(mockOnAgentControl).toHaveBeenCalledWith(
      'agent_001',
      'pause',
      'Routine maintenance pause for system update'
    )
  })
})

describe('EmergencyControls', () => {
  const mockOnEmergencyStopAll = jest.fn().mockResolvedValue(true)
  const mockOnClearEmergencyStop = jest.fn().mockResolvedValue(true)
  const mockOnRefresh = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders system status overview', () => {
    render(
      <EmergencyControls
        systemStatus={mockSystemStatus}
        emergencyStops={[]}
        onEmergencyStopAll={mockOnEmergencyStopAll}
        onClearEmergencyStop={mockOnClearEmergencyStop}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('Healthy')).toBeInTheDocument()
    expect(screen.getByText('72h 0m')).toBeInTheDocument() // Formatted uptime
    expect(screen.getByText('✓ Normal')).toBeInTheDocument() // Emergency stop status
  })

  it('shows emergency stop all button', () => {
    render(
      <EmergencyControls
        systemStatus={mockSystemStatus}
        emergencyStops={[]}
        onEmergencyStopAll={mockOnEmergencyStopAll}
        onClearEmergencyStop={mockOnClearEmergencyStop}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('EMERGENCY STOP ALL')).toBeInTheDocument()
    expect(screen.getByText('Immediately halt all AI agents and trading operations')).toBeInTheDocument()
  })

  it('opens confirmation modal when emergency stop clicked', async () => {
    const user = userEvent.setup()
    render(
      <EmergencyControls
        systemStatus={mockSystemStatus}
        emergencyStops={[]}
        onEmergencyStopAll={mockOnEmergencyStopAll}
        onClearEmergencyStop={mockOnClearEmergencyStop}
        onRefresh={mockOnRefresh}
      />
    )

    const emergencyButton = screen.getByText('EMERGENCY STOP ALL')
    await user.click(emergencyButton)

    expect(screen.getByText('EMERGENCY STOP ALL')).toBeInTheDocument()
    expect(screen.getByText('All AI agents will be immediately stopped')).toBeInTheDocument()
  })

  it('calls onEmergencyStopAll with justification', async () => {
    const user = userEvent.setup()
    render(
      <EmergencyControls
        systemStatus={mockSystemStatus}
        emergencyStops={[]}
        onEmergencyStopAll={mockOnEmergencyStopAll}
        onClearEmergencyStop={mockOnClearEmergencyStop}
        onRefresh={mockOnRefresh}
      />
    )

    const emergencyButton = screen.getByText('EMERGENCY STOP ALL')
    await user.click(emergencyButton)

    const justificationTextarea = screen.getByPlaceholderText(/Describe the emergency situation/)
    await user.type(justificationTextarea, 'Critical market anomaly detected requiring immediate halt')

    const confirmButton = screen.getByText('CONFIRM EMERGENCY STOP')
    await user.click(confirmButton)

    expect(mockOnEmergencyStopAll).toHaveBeenCalledWith(
      'Critical market anomaly detected requiring immediate halt'
    )
  })
})

describe('ManualTradingInterface', () => {
  const mockOnSubmitTradeRequest = jest.fn().mockResolvedValue('trade_002')
  const mockOnApproveTradeRequest = jest.fn().mockResolvedValue(true)
  const mockOnRefresh = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders trade request form', () => {
    render(
      <ManualTradingInterface
        tradeRequests={mockTradeRequests}
        onSubmitTradeRequest={mockOnSubmitTradeRequest}
        onApproveTradeRequest={mockOnApproveTradeRequest}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('Submit Manual Trade Request')).toBeInTheDocument()
    expect(screen.getByText('Trading Action')).toBeInTheDocument()
    expect(screen.getByText('Instrument')).toBeInTheDocument()
    expect(screen.getByText('Quantity (Units)')).toBeInTheDocument()
  })

  it('renders existing trade requests', () => {
    render(
      <ManualTradingInterface
        tradeRequests={mockTradeRequests}
        onSubmitTradeRequest={mockOnSubmitTradeRequest}
        onApproveTradeRequest={mockOnApproveTradeRequest}
        onRefresh={mockOnRefresh}
      />
    )

    // Switch to requests tab
    const requestsTab = screen.getByText('Trade Requests')
    fireEvent.click(requestsTab)

    expect(screen.getByText('MARKET_BUY - EUR_USD')).toBeInTheDocument()
    expect(screen.getByText('PENDING_APPROVAL')).toBeInTheDocument()
    expect(screen.getByText('Strategic position based on market analysis')).toBeInTheDocument()
  })

  it('submits trade request with validation', async () => {
    const user = userEvent.setup()
    render(
      <ManualTradingInterface
        tradeRequests={mockTradeRequests}
        onSubmitTradeRequest={mockOnSubmitTradeRequest}
        onApproveTradeRequest={mockOnApproveTradeRequest}
        onRefresh={mockOnRefresh}
      />
    )

    // Fill out form
    const quantityInput = screen.getByPlaceholderText('Enter quantity')
    await user.type(quantityInput, '5000')

    const justificationTextarea = screen.getByPlaceholderText(/Explain the reason for this manual trade/)
    await user.type(justificationTextarea, 'Tactical position adjustment based on breaking news analysis')

    const submitButton = screen.getByText('Submit Trade Request')
    await user.click(submitButton)

    // Should show confirmation modal with risk assessment
    expect(screen.getByText('Confirm Manual Trade Request')).toBeInTheDocument()
    expect(screen.getByText('Risk Assessment')).toBeInTheDocument()
  })
})

describe('RiskParameterTools', () => {
  const mockOnUpdateParameter = jest.fn().mockResolvedValue(true)
  const mockOnRefresh = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders risk parameters with current values', () => {
    render(
      <RiskParameterTools
        riskParameters={mockRiskParameters}
        onUpdateParameter={mockOnUpdateParameter}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('Maximum Position Size')).toBeInTheDocument()
    expect(screen.getByText('$100,000')).toBeInTheDocument() // Current value
    expect(screen.getByText('$50,000')).toBeInTheDocument() // Default value
  })

  it('shows parameter modification controls', () => {
    render(
      <RiskParameterTools
        riskParameters={mockRiskParameters}
        onUpdateParameter={mockOnUpdateParameter}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('Modify Parameter')).toBeInTheDocument()
    expect(screen.getByText('Reset to Default')).toBeInTheDocument()
  })

  it('opens parameter modification modal', async () => {
    const user = userEvent.setup()
    render(
      <RiskParameterTools
        riskParameters={mockRiskParameters}
        onUpdateParameter={mockOnUpdateParameter}
        onRefresh={mockOnRefresh}
      />
    )

    const modifyButton = screen.getByText('Modify Parameter')
    await user.click(modifyButton)

    expect(screen.getByText('Modify Maximum Position Size')).toBeInTheDocument()
    expect(screen.getByText('Current Value')).toBeInTheDocument()
    expect(screen.getByText('New Value')).toBeInTheDocument()
  })

  it('validates parameter changes', async () => {
    const user = userEvent.setup()
    render(
      <RiskParameterTools
        riskParameters={mockRiskParameters}
        onUpdateParameter={mockOnUpdateParameter}
        onRefresh={mockOnRefresh}
      />
    )

    const modifyButton = screen.getByText('Modify Parameter')
    await user.click(modifyButton)

    const valueInput = screen.getByDisplayValue('100000')
    await user.clear(valueInput)
    await user.type(valueInput, '750000') // Above maximum

    const justificationTextarea = screen.getByPlaceholderText(/Explain why this parameter change/)
    await user.type(justificationTextarea, 'Increase limit for new high-volume strategy')

    const updateButton = screen.getByText('Update Parameter')
    await user.click(updateButton)

    // Should show validation error or warning
    expect(screen.getByText(/Value must not exceed/)).toBeInTheDocument()
  })
})

describe('AuditLogViewer', () => {
  const mockOnRefresh = jest.fn()
  const mockOnExport = jest.fn().mockResolvedValue(true)

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders audit log entries', () => {
    render(
      <AuditLogViewer
        auditLogs={mockAuditLogs}
        onRefresh={mockOnRefresh}
        onExport={mockOnExport}
      />
    )

    expect(screen.getByText('Audit Log Viewer')).toBeInTheDocument()
    expect(screen.getByText('AGENT_CONTROL - AGENT')).toBeInTheDocument()
    expect(screen.getByText('admin@proptrading.com')).toBeInTheDocument()
    expect(screen.getByText('Routine maintenance restart')).toBeInTheDocument()
  })

  it('filters audit logs by action type', async () => {
    const user = userEvent.setup()
    render(
      <AuditLogViewer
        auditLogs={mockAuditLogs}
        onRefresh={mockOnRefresh}
        onExport={mockOnExport}
      />
    )

    const actionFilter = screen.getByDisplayValue('All Actions')
    await user.selectOptions(actionFilter, 'agent_control')

    // Should show filtered results
    expect(screen.getByText('AGENT_CONTROL - AGENT')).toBeInTheDocument()
  })

  it('exports audit logs in different formats', async () => {
    const user = userEvent.setup()
    render(
      <AuditLogViewer
        auditLogs={mockAuditLogs}
        onRefresh={mockOnRefresh}
        onExport={mockOnExport}
      />
    )

    const csvButton = screen.getByText('CSV')
    await user.click(csvButton)

    expect(mockOnExport).toHaveBeenCalledWith('csv', {})
  })

  it('shows detailed audit entry in modal', async () => {
    const user = userEvent.setup()
    render(
      <AuditLogViewer
        auditLogs={mockAuditLogs}
        onRefresh={mockOnRefresh}
        onExport={mockOnExport}
      />
    )

    const auditEntry = screen.getByText('AGENT_CONTROL - AGENT')
    await user.click(auditEntry)

    expect(screen.getByText('Audit Log Details')).toBeInTheDocument()
    expect(screen.getByText('Administrator Information')).toBeInTheDocument()
    expect(screen.getByText('Compliance Check')).toBeInTheDocument()
  })
})

describe('Error Handling', () => {
  it('displays error message when service fails', () => {
    const errorMock = {
      ...mockTradingControlsHook,
      error: 'Failed to load trading controls data'
    }

    jest.doMock('@/hooks/useTradingControls', () => ({
      useTradingControls: () => errorMock
    }))

    render(<TradingControlsDashboard />, { wrapper: TestWrapper })

    expect(screen.getByText('⚠ Dashboard Error')).toBeInTheDocument()
    expect(screen.getByText('Failed to load trading controls data')).toBeInTheDocument()
  })

  it('shows loading states appropriately', () => {
    const loadingMock = {
      ...mockTradingControlsHook,
      loading: { ...mockTradingControlsHook.loading, initial: true }
    }

    jest.doMock('@/hooks/useTradingControls', () => ({
      useTradingControls: () => loadingMock
    }))

    render(<TradingControlsDashboard />, { wrapper: TestWrapper })

    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })
})