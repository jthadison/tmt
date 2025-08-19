/**
 * Trading Controls Hook
 * Story 9.5: Centralized state management for administrator trading controls
 * 
 * SECURITY: All operations require administrator authentication
 */

'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  SystemUser,
  AIAgent,
  AgentControlAction,
  ManualTradeRequest,
  RiskParameters,
  EmergencyStop,
  SystemStatus,
  AuditLogEntry,
  AuditLogFilter,
  ControlsApiResponse
} from '@/types/tradingControls'
import { 
  TradingControlsService,
  SecurityError
} from '@/services/tradingControlsService'

/**
 * Hook state interface
 */
interface UseTradingControlsState {
  // User and authentication
  currentUser: SystemUser | null
  isAuthenticated: boolean
  isLoading: boolean
  
  // Agents
  agents: AIAgent[]
  agentsLoading: boolean
  agentsError: string | null
  
  // System status
  systemStatus: SystemStatus | null
  statusLoading: boolean
  statusError: string | null
  
  // Emergency controls
  emergencyStops: EmergencyStop[]
  emergencyLoading: boolean
  emergencyError: string | null
  
  // Manual trading
  tradeRequests: ManualTradeRequest[]
  tradingLoading: boolean
  tradingError: string | null
  
  // Risk parameters
  riskParameters: RiskParameters[]
  riskLoading: boolean
  riskError: string | null
  
  // Audit logs
  auditLogs: AuditLogEntry[]
  auditLoading: boolean
  auditError: string | null
  
  // General error handling
  lastError: string | null
  lastUpdate: Date | null
}

/**
 * Hook return interface
 */
export interface UseTradingControlsReturn extends UseTradingControlsState {
  // Authentication
  requireAdminAccess: () => void
  logout: () => Promise<void>
  
  // Agent controls
  refreshAgents: () => Promise<void>
  controlAgent: (agentId: string, action: AgentControlAction, justification: string, parameters?: Record<string, any>) => Promise<boolean>
  pauseAgent: (agentId: string, justification: string) => Promise<boolean>
  resumeAgent: (agentId: string, justification: string) => Promise<boolean>
  stopAgent: (agentId: string, justification: string) => Promise<boolean>
  emergencyStopAgent: (agentId: string, justification: string) => Promise<boolean>
  updateAgentParameters: (agentId: string, parameters: Record<string, any>, justification: string) => Promise<boolean>
  
  // System controls  
  refreshSystemStatus: () => Promise<void>
  emergencyStopAll: (justification: string) => Promise<boolean>
  clearEmergencyStop: (stopId: string, justification: string) => Promise<boolean>
  
  // Manual trading
  refreshTradeRequests: () => Promise<void>
  submitTradeRequest: (request: Omit<ManualTradeRequest, 'id' | 'userId' | 'status' | 'createdAt'>) => Promise<string | null>
  approveTradeRequest: (requestId: string, justification: string) => Promise<boolean>
  
  // Risk management
  refreshRiskParameters: () => Promise<void>
  updateRiskParameter: (parameterId: string, newValue: number, justification: string) => Promise<boolean>
  
  // Audit logs
  refreshAuditLogs: (filter?: AuditLogFilter) => Promise<void>
  
  // Utility functions
  clearErrors: () => void
  getAgentById: (agentId: string) => AIAgent | undefined
  getActiveAgents: () => AIAgent[]
  getPausedAgents: () => AIAgent[]
  getErrorAgents: () => AIAgent[]
}

/**
 * Main trading controls hook
 */
export function useTradingControls(): UseTradingControlsReturn {
  // Initialize service
  const service = useMemo(() => new TradingControlsService(), [])
  
  // State management
  const [state, setState] = useState<UseTradingControlsState>({
    currentUser: null,
    isAuthenticated: false,
    isLoading: true,
    
    agents: [],
    agentsLoading: false,
    agentsError: null,
    
    systemStatus: null,
    statusLoading: false,
    statusError: null,
    
    emergencyStops: [],
    emergencyLoading: false,
    emergencyError: null,
    
    tradeRequests: [],
    tradingLoading: false,
    tradingError: null,
    
    riskParameters: [],
    riskLoading: false,
    riskError: null,
    
    auditLogs: [],
    auditLoading: false,
    auditError: null,
    
    lastError: null,
    lastUpdate: null
  })

  // Initialize authentication and load initial data
  useEffect(() => {
    initializeAuth()
  }, [])

  const initializeAuth = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true }))
      
      const currentUser = service.authentication.getCurrentUser()
      const isAuthenticated = service.authentication.validateSession()
      
      setState(prev => ({
        ...prev,
        currentUser,
        isAuthenticated,
        isLoading: false,
        lastUpdate: new Date()
      }))
      
      if (isAuthenticated && currentUser?.role === 'administrator') {
        // Load initial data for administrators
        await Promise.all([
          refreshAgents(),
          refreshSystemStatus(),
          refreshRiskParameters()
        ])
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        lastError: error instanceof Error ? error.message : 'Authentication failed'
      }))
    }
  }, [service])

  // Authentication functions
  const requireAdminAccess = useCallback(() => {
    try {
      service.authentication.requireAdministrator()
    } catch (error) {
      setState(prev => ({
        ...prev,
        lastError: error instanceof Error ? error.message : 'Administrator access required'
      }))
      throw error
    }
  }, [service])

  const logout = useCallback(async () => {
    await service.authentication.logout()
    setState(prev => ({
      ...prev,
      currentUser: null,
      isAuthenticated: false,
      agents: [],
      systemStatus: null,
      emergencyStops: [],
      tradeRequests: [],
      riskParameters: [],
      auditLogs: []
    }))
  }, [service])

  // Agent control functions
  const refreshAgents = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, agentsLoading: true, agentsError: null }))
      
      const agents = await service.agents.getAgents()
      
      setState(prev => ({
        ...prev,
        agents,
        agentsLoading: false,
        lastUpdate: new Date()
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        agentsLoading: false,
        agentsError: error instanceof Error ? error.message : 'Failed to load agents'
      }))
    }
  }, [service])

  const controlAgent = useCallback(async (
    agentId: string,
    action: AgentControlAction,
    justification: string,
    parameters?: Record<string, any>
  ): Promise<boolean> => {
    try {
      requireAdminAccess()
      
      const response = await service.agents.controlAgent(agentId, action, justification, parameters)
      
      if (response.success && response.data) {
        // Update agent in state
        setState(prev => ({
          ...prev,
          agents: prev.agents.map(agent => 
            agent.id === agentId ? response.data! : agent
          ),
          lastUpdate: new Date()
        }))
        return true
      } else {
        setState(prev => ({
          ...prev,
          lastError: response.error || 'Agent control failed'
        }))
        return false
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        lastError: error instanceof Error ? error.message : 'Agent control failed'
      }))
      return false
    }
  }, [service, requireAdminAccess])

  const pauseAgent = useCallback((agentId: string, justification: string) => 
    controlAgent(agentId, 'pause', justification), [controlAgent])

  const resumeAgent = useCallback((agentId: string, justification: string) => 
    controlAgent(agentId, 'resume', justification), [controlAgent])

  const stopAgent = useCallback((agentId: string, justification: string) => 
    controlAgent(agentId, 'stop', justification), [controlAgent])

  const emergencyStopAgent = useCallback((agentId: string, justification: string) => 
    controlAgent(agentId, 'emergency_stop', justification), [controlAgent])

  const updateAgentParameters = useCallback((
    agentId: string, 
    parameters: Record<string, any>, 
    justification: string
  ) => controlAgent(agentId, 'update_parameters', justification, parameters), [controlAgent])

  // System control functions
  const refreshSystemStatus = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, statusLoading: true, statusError: null }))
      
      const systemStatus = await service.getSystemStatus()
      
      setState(prev => ({
        ...prev,
        systemStatus,
        statusLoading: false,
        lastUpdate: new Date()
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        statusLoading: false,
        statusError: error instanceof Error ? error.message : 'Failed to load system status'
      }))
    }
  }, [service])

  const emergencyStopAll = useCallback(async (justification: string): Promise<boolean> => {
    try {
      requireAdminAccess()
      setState(prev => ({ ...prev, emergencyLoading: true }))
      
      const response = await service.emergency.emergencyStopAll(justification)
      
      if (response.success && response.data) {
        setState(prev => ({
          ...prev,
          emergencyStops: [...prev.emergencyStops, response.data!],
          emergencyLoading: false,
          lastUpdate: new Date()
        }))
        
        // Refresh agents to show updated status
        await refreshAgents()
        await refreshSystemStatus()
        
        return true
      } else {
        setState(prev => ({
          ...prev,
          emergencyLoading: false,
          lastError: response.error || 'Emergency stop failed'
        }))
        return false
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        emergencyLoading: false,
        lastError: error instanceof Error ? error.message : 'Emergency stop failed'
      }))
      return false
    }
  }, [service, requireAdminAccess, refreshAgents, refreshSystemStatus])

  const clearEmergencyStop = useCallback(async (stopId: string, justification: string): Promise<boolean> => {
    try {
      requireAdminAccess()
      
      const response = await service.emergency.clearEmergencyStop(stopId, justification)
      
      if (response.success) {
        setState(prev => ({
          ...prev,
          emergencyStops: prev.emergencyStops.map(stop => 
            stop.id === stopId ? { ...stop, isActive: false } : stop
          ),
          lastUpdate: new Date()
        }))
        
        await refreshSystemStatus()
        return true
      } else {
        setState(prev => ({
          ...prev,
          lastError: response.error || 'Failed to clear emergency stop'
        }))
        return false
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        lastError: error instanceof Error ? error.message : 'Failed to clear emergency stop'
      }))
      return false
    }
  }, [service, requireAdminAccess, refreshSystemStatus])

  // Manual trading functions
  const refreshTradeRequests = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, tradingLoading: true, tradingError: null }))
      
      const tradeRequests = await service.trading.getTradeRequests()
      
      setState(prev => ({
        ...prev,
        tradeRequests,
        tradingLoading: false,
        lastUpdate: new Date()
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        tradingLoading: false,
        tradingError: error instanceof Error ? error.message : 'Failed to load trade requests'
      }))
    }
  }, [service])

  const submitTradeRequest = useCallback(async (
    request: Omit<ManualTradeRequest, 'id' | 'userId' | 'status' | 'createdAt'>
  ): Promise<string | null> => {
    try {
      requireAdminAccess()
      
      const response = await service.trading.submitTradeRequest(request)
      
      if (response.success && response.data) {
        setState(prev => ({
          ...prev,
          tradeRequests: [...prev.tradeRequests, response.data!],
          lastUpdate: new Date()
        }))
        return response.data.id
      } else {
        setState(prev => ({
          ...prev,
          lastError: response.error || 'Failed to submit trade request'
        }))
        return null
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        lastError: error instanceof Error ? error.message : 'Failed to submit trade request'
      }))
      return null
    }
  }, [service, requireAdminAccess])

  const approveTradeRequest = useCallback(async (requestId: string, justification: string): Promise<boolean> => {
    try {
      requireAdminAccess()
      
      const response = await service.trading.approveTradeRequest(requestId, justification)
      
      if (response.success && response.data) {
        setState(prev => ({
          ...prev,
          tradeRequests: prev.tradeRequests.map(req => 
            req.id === requestId ? response.data! : req
          ),
          lastUpdate: new Date()
        }))
        return true
      } else {
        setState(prev => ({
          ...prev,
          lastError: response.error || 'Failed to approve trade request'
        }))
        return false
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        lastError: error instanceof Error ? error.message : 'Failed to approve trade request'
      }))
      return false
    }
  }, [service, requireAdminAccess])

  // Risk parameter functions
  const refreshRiskParameters = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, riskLoading: true, riskError: null }))
      
      const riskParameters = await service.risk.getRiskParameters()
      
      setState(prev => ({
        ...prev,
        riskParameters,
        riskLoading: false,
        lastUpdate: new Date()
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        riskLoading: false,
        riskError: error instanceof Error ? error.message : 'Failed to load risk parameters'
      }))
    }
  }, [service])

  const updateRiskParameter = useCallback(async (
    parameterId: string,
    newValue: number,
    justification: string
  ): Promise<boolean> => {
    try {
      requireAdminAccess()
      
      const response = await service.risk.updateRiskParameter(parameterId, newValue, justification)
      
      if (response.success && response.data) {
        setState(prev => ({
          ...prev,
          riskParameters: prev.riskParameters.map(param => 
            param.id === parameterId ? response.data! : param
          ),
          lastUpdate: new Date()
        }))
        return true
      } else {
        setState(prev => ({
          ...prev,
          lastError: response.error || 'Failed to update risk parameter'
        }))
        return false
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        lastError: error instanceof Error ? error.message : 'Failed to update risk parameter'
      }))
      return false
    }
  }, [service, requireAdminAccess])

  // Audit log functions
  const refreshAuditLogs = useCallback(async (filter?: AuditLogFilter) => {
    try {
      setState(prev => ({ ...prev, auditLoading: true, auditError: null }))
      
      const auditLogs = await service.auditService.getAuditLogs(filter || {})
      
      setState(prev => ({
        ...prev,
        auditLogs,
        auditLoading: false,
        lastUpdate: new Date()
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        auditLoading: false,
        auditError: error instanceof Error ? error.message : 'Failed to load audit logs'
      }))
    }
  }, [service])

  // Utility functions
  const clearErrors = useCallback(() => {
    setState(prev => ({
      ...prev,
      lastError: null,
      agentsError: null,
      statusError: null,
      emergencyError: null,
      tradingError: null,
      riskError: null,
      auditError: null
    }))
  }, [])

  const getAgentById = useCallback((agentId: string): AIAgent | undefined => {
    return state.agents.find(agent => agent.id === agentId)
  }, [state.agents])

  const getActiveAgents = useCallback((): AIAgent[] => {
    return state.agents.filter(agent => agent.status === 'active')
  }, [state.agents])

  const getPausedAgents = useCallback((): AIAgent[] => {
    return state.agents.filter(agent => agent.status === 'paused')
  }, [state.agents])

  const getErrorAgents = useCallback((): AIAgent[] => {
    return state.agents.filter(agent => agent.status === 'error')
  }, [state.agents])

  // Auto-refresh system status and agents every 30 seconds
  useEffect(() => {
    if (!state.isAuthenticated || state.currentUser?.role !== 'administrator') {
      return
    }

    const interval = setInterval(async () => {
      try {
        await Promise.all([
          refreshSystemStatus(),
          // Only refresh agents if not currently loading
          !state.agentsLoading && refreshAgents()
        ].filter(Boolean))
      } catch (error) {
        // Silently handle auto-refresh errors
        console.warn('Auto-refresh failed:', error)
      }
    }, 30000) // 30 seconds

    return () => clearInterval(interval)
  }, [state.isAuthenticated, state.currentUser, state.agentsLoading, refreshSystemStatus, refreshAgents])

  return {
    ...state,
    
    // Authentication
    requireAdminAccess,
    logout,
    
    // Agent controls
    refreshAgents,
    controlAgent,
    pauseAgent,
    resumeAgent,
    stopAgent,
    emergencyStopAgent,
    updateAgentParameters,
    
    // System controls
    refreshSystemStatus,
    emergencyStopAll,
    clearEmergencyStop,
    
    // Manual trading
    refreshTradeRequests,
    submitTradeRequest,
    approveTradeRequest,
    
    // Risk management
    refreshRiskParameters,
    updateRiskParameter,
    
    // Audit logs
    refreshAuditLogs,
    
    // Utilities
    clearErrors,
    getAgentById,
    getActiveAgents,
    getPausedAgents,
    getErrorAgents
  }
}