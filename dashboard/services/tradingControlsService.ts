/**
 * Trading Controls Service
 * Story 9.5: Secure administrator-only trading controls with audit logging
 * 
 * CRITICAL SECURITY NOTE: All methods in this service require administrator access
 */

import {
  SystemUser,
  UserRole,
  UserPermission,
  AIAgent,
  AgentControlAction,
  SystemControlAction,
  ManualTradeRequest,
  ManualTradingAction,
  RiskParameters,
  ComplianceCheck,
  AuditLogEntry,
  ApprovalWorkflow,
  EmergencyStop,
  SystemStatus,
  ControlsApiResponse,
  TradingControlsConfig,
  AuditLogFilter,
  RiskAssessment
} from '@/types/tradingControls'

/**
 * Authentication and authorization service
 */
export class AuthenticationService {
  private currentUser: SystemUser | null = null
  private sessionId: string | null = null

  constructor() {
    this.loadCurrentUser()
  }

  private loadCurrentUser(): void {
    // In a real implementation, this would validate JWT tokens and load from secure storage
    // For development, we'll simulate an admin user
    const mockAdminUser: SystemUser = {
      id: 'admin_001',
      email: 'admin@trading-system.com',
      name: 'System Administrator',
      role: 'administrator',
      permissions: [
        'agent_control',
        'emergency_stop', 
        'manual_trading',
        'risk_modification',
        'system_override',
        'audit_access',
        'user_management'
      ],
      lastLogin: new Date(),
      isActive: true,
      metadata: {
        lastPasswordChange: new Date(),
        mfaEnabled: true,
        ipRestrictions: ['192.168.1.0/24']
      }
    }

    this.currentUser = mockAdminUser
    this.sessionId = `session_${Date.now()}`
  }

  getCurrentUser(): SystemUser | null {
    return this.currentUser
  }

  getSessionId(): string | null {
    return this.sessionId
  }

  hasPermission(permission: UserPermission): boolean {
    return this.currentUser?.permissions.includes(permission) || false
  }

  isAdministrator(): boolean {
    return this.currentUser?.role === 'administrator'
  }

  requireAdministrator(): void {
    if (!this.isAdministrator()) {
      throw new SecurityError('Administrator access required for this operation')
    }
  }

  requirePermission(permission: UserPermission): void {
    if (!this.hasPermission(permission)) {
      throw new SecurityError(`Permission '${permission}' required for this operation`)
    }
  }

  validateSession(): boolean {
    // In real implementation, validate JWT token, check expiry, etc.
    return this.currentUser !== null && this.sessionId !== null
  }

  async logout(): Promise<void> {
    this.currentUser = null
    this.sessionId = null
  }
}

/**
 * Custom security error class
 */
export class SecurityError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'SecurityError'
  }
}

/**
 * Audit logging service for all trading control actions
 */
export class AuditService {
  private auth: AuthenticationService

  constructor(auth: AuthenticationService) {
    this.auth = auth
  }

  async logAction(
    action: string,
    resource: string,
    resourceId: string,
    details: Record<string, any>,
    justification: string,
    riskLevel: 'low' | 'medium' | 'high' | 'critical' = 'medium'
  ): Promise<string> {
    const user = this.auth.getCurrentUser()
    if (!user) {
      throw new SecurityError('User authentication required for audit logging')
    }

    const auditEntry: AuditLogEntry = {
      id: `audit_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      userId: user.id,
      userEmail: user.email,
      action: action as any,
      resource: resource as any,
      resourceId,
      details,
      justification,
      approvalRequired: riskLevel === 'high' || riskLevel === 'critical',
      riskLevel,
      complianceCheck: await this.performComplianceCheck(action, details),
      sessionId: this.auth.getSessionId() || 'unknown',
      ipAddress: '192.168.1.100', // Mock IP - would get from request context
      userAgent: 'Trading Dashboard', // Mock - would get from request context
      result: 'success'
    }

    // In real implementation, this would persist to audit database
    console.log('AUDIT LOG:', auditEntry)
    
    return auditEntry.id
  }

  private async performComplianceCheck(action: string, details: Record<string, any>): Promise<ComplianceCheck> {
    // Mock compliance check - real implementation would validate against compliance rules
    return {
      passed: true,
      violations: [],
      warnings: [],
      overrides: [],
      checkedAt: new Date(),
      checkedBy: 'compliance_engine'
    }
  }

  async getAuditLogs(filter: AuditLogFilter): Promise<AuditLogEntry[]> {
    this.auth.requirePermission('audit_access')
    
    // Mock implementation - real version would query audit database
    return []
  }
}

/**
 * Agent control service for managing AI agents
 */
export class AgentControlService {
  private auth: AuthenticationService
  private audit: AuditService
  private agents: Map<string, AIAgent> = new Map()

  constructor(auth: AuthenticationService, audit: AuditService) {
    this.auth = auth
    this.audit = audit
    this.initializeMockAgents()
  }

  private initializeMockAgents(): void {
    const mockAgents: AIAgent[] = [
      {
        id: 'circuit_breaker_001',
        name: 'Circuit Breaker Agent',
        type: 'circuit_breaker',
        status: 'active',
        isActive: true,
        lastHeartbeat: new Date(),
        currentParameters: {
          riskLevel: 75,
          maxPositionSize: 100000,
          maxDailyLoss: 5000,
          stopLossThreshold: 0.02,
          takeProfitThreshold: 0.05,
          timeoutSeconds: 30,
          retryAttempts: 3,
          customParameters: {},
          complianceRules: []
        },
        defaultParameters: {
          riskLevel: 50,
          maxPositionSize: 50000,
          maxDailyLoss: 2500,
          stopLossThreshold: 0.015,
          takeProfitThreshold: 0.03,
          timeoutSeconds: 30,
          retryAttempts: 3,
          customParameters: {},
          complianceRules: []
        },
        performance: {
          uptime: 99.5,
          responseTime: 150,
          successRate: 98.2,
          totalActions: 1247,
          errorRate: 1.8,
          lastUpdateTime: new Date()
        },
        errorCount: 3
      },
      {
        id: 'risk_management_001',
        name: 'Risk Management Agent',
        type: 'risk_management',
        status: 'active',
        isActive: true,
        lastHeartbeat: new Date(Date.now() - 30000),
        currentParameters: {
          riskLevel: 60,
          maxPositionSize: 75000,
          maxDailyLoss: 3000,
          stopLossThreshold: 0.025,
          takeProfitThreshold: 0.04,
          timeoutSeconds: 45,
          retryAttempts: 5,
          customParameters: {},
          complianceRules: []
        },
        defaultParameters: {
          riskLevel: 50,
          maxPositionSize: 50000,
          maxDailyLoss: 2500,
          stopLossThreshold: 0.02,
          takeProfitThreshold: 0.03,
          timeoutSeconds: 30,
          retryAttempts: 3,
          customParameters: {},
          complianceRules: []
        },
        performance: {
          uptime: 97.8,
          responseTime: 210,
          successRate: 96.5,
          totalActions: 892,
          errorRate: 3.5,
          lastUpdateTime: new Date(Date.now() - 60000)
        },
        errorCount: 8
      }
    ]

    mockAgents.forEach(agent => this.agents.set(agent.id, agent))
  }

  async getAgents(): Promise<AIAgent[]> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('agent_control')

    return Array.from(this.agents.values())
  }

  async getAgent(agentId: string): Promise<AIAgent | null> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('agent_control')

    return this.agents.get(agentId) || null
  }

  async controlAgent(
    agentId: string, 
    action: AgentControlAction, 
    justification: string,
    parameters?: Record<string, any>
  ): Promise<ControlsApiResponse<AIAgent>> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('agent_control')

    const agent = this.agents.get(agentId)
    if (!agent) {
      throw new Error(`Agent ${agentId} not found`)
    }

    // Log the control action
    const auditId = await this.audit.logAction(
      'agent_control',
      'agent',
      agentId,
      { action, parameters, previousStatus: agent.status },
      justification,
      action === 'emergency_stop' ? 'critical' : 'medium'
    )

    // Execute the control action
    try {
      const updatedAgent = await this.executeAgentControl(agent, action, parameters)
      this.agents.set(agentId, updatedAgent)

      return {
        success: true,
        data: updatedAgent,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`,
        auditId
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`,
        auditId
      }
    }
  }

  private async executeAgentControl(
    agent: AIAgent, 
    action: AgentControlAction, 
    parameters?: Record<string, any>
  ): Promise<AIAgent> {
    const updatedAgent = { ...agent }

    switch (action) {
      case 'pause':
        updatedAgent.status = 'paused'
        updatedAgent.isActive = false
        break
      
      case 'resume':
        if (updatedAgent.status === 'paused') {
          updatedAgent.status = 'active'
          updatedAgent.isActive = true
        }
        break
      
      case 'stop':
        updatedAgent.status = 'stopped'
        updatedAgent.isActive = false
        break
      
      case 'restart':
        updatedAgent.status = 'active'
        updatedAgent.isActive = true
        updatedAgent.errorCount = 0
        updatedAgent.lastError = undefined
        break
      
      case 'emergency_stop':
        updatedAgent.status = 'emergency_stop'
        updatedAgent.isActive = false
        break
      
      case 'update_parameters':
        if (parameters && typeof parameters === 'object') {
          updatedAgent.currentParameters = {
            ...updatedAgent.currentParameters,
            ...parameters
          }
        }
        break
      
      case 'reset_errors':
        updatedAgent.errorCount = 0
        updatedAgent.lastError = undefined
        if (updatedAgent.status === 'error') {
          updatedAgent.status = 'active'
          updatedAgent.isActive = true
        }
        break
    }

    return updatedAgent
  }
}

/**
 * Emergency controls service for system-wide operations
 */
export class EmergencyControlsService {
  private auth: AuthenticationService
  private audit: AuditService
  private agentControl: AgentControlService
  private emergencyStops: Map<string, EmergencyStop> = new Map()

  constructor(auth: AuthenticationService, audit: AuditService, agentControl: AgentControlService) {
    this.auth = auth
    this.audit = audit
    this.agentControl = agentControl
  }

  async emergencyStopAll(justification: string): Promise<ControlsApiResponse<EmergencyStop>> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('emergency_stop')

    const user = this.auth.getCurrentUser()!
    const emergencyStop: EmergencyStop = {
      id: `emergency_${Date.now()}`,
      type: 'manual_intervention',
      isActive: true,
      triggeredBy: user.id,
      triggeredAt: new Date(),
      reason: justification,
      affectedAgents: [],
      affectedAccounts: [],
      overrideRequired: true
    }

    // Log critical emergency action
    const auditId = await this.audit.logAction(
      'emergency_stop',
      'system',
      'all_agents',
      { stopType: 'emergency_stop_all' },
      justification,
      'critical'
    )

    try {
      // Get all agents and stop them
      const agents = await this.agentControl.getAgents()
      const stopPromises = agents.map(agent => 
        this.agentControl.controlAgent(
          agent.id, 
          'emergency_stop', 
          `Emergency stop triggered: ${justification}`
        )
      )

      await Promise.all(stopPromises)
      
      emergencyStop.affectedAgents = agents.map(a => a.id)
      this.emergencyStops.set(emergencyStop.id, emergencyStop)

      return {
        success: true,
        data: emergencyStop,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`,
        auditId
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Emergency stop failed',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`,
        auditId
      }
    }
  }

  async getActiveEmergencyStops(): Promise<EmergencyStop[]> {
    this.auth.requireAdministrator()
    
    return Array.from(this.emergencyStops.values()).filter(stop => stop.isActive)
  }

  async clearEmergencyStop(stopId: string, justification: string): Promise<ControlsApiResponse<boolean>> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('emergency_stop')

    const emergencyStop = this.emergencyStops.get(stopId)
    if (!emergencyStop) {
      throw new Error(`Emergency stop ${stopId} not found`)
    }

    const auditId = await this.audit.logAction(
      'emergency_stop',
      'system',
      stopId,
      { action: 'clear_emergency_stop' },
      justification,
      'high'
    )

    emergencyStop.isActive = false
    this.emergencyStops.set(stopId, emergencyStop)

    return {
      success: true,
      data: true,
      timestamp: new Date(),
      requestId: `req_${Date.now()}`,
      auditId
    }
  }
}

/**
 * Manual trading service for direct market intervention
 */
export class ManualTradingService {
  private auth: AuthenticationService
  private audit: AuditService
  private tradeRequests: Map<string, ManualTradeRequest> = new Map()

  constructor(auth: AuthenticationService, audit: AuditService) {
    this.auth = auth
    this.audit = audit
  }

  async submitTradeRequest(request: Omit<ManualTradeRequest, 'id' | 'userId' | 'status' | 'createdAt'>): Promise<ControlsApiResponse<ManualTradeRequest>> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('manual_trading')

    const user = this.auth.getCurrentUser()!
    const tradeRequest: ManualTradeRequest = {
      ...request,
      id: `trade_${Date.now()}`,
      userId: user.id,
      status: 'pending_approval',
      createdAt: new Date()
    }

    // Log manual trade request
    const auditId = await this.audit.logAction(
      'manual_trade',
      'trade',
      tradeRequest.id,
      {
        action: tradeRequest.action,
        instrument: tradeRequest.instrument,
        quantity: tradeRequest.quantity,
        price: tradeRequest.price
      },
      tradeRequest.justification,
      'high'
    )

    this.tradeRequests.set(tradeRequest.id, tradeRequest)

    return {
      success: true,
      data: tradeRequest,
      timestamp: new Date(),
      requestId: `req_${Date.now()}`,
      auditId
    }
  }

  async getTradeRequests(status?: string): Promise<ManualTradeRequest[]> {
    this.auth.requireAdministrator()
    
    const requests = Array.from(this.tradeRequests.values())
    return status ? requests.filter(req => req.status === status) : requests
  }

  async approveTradeRequest(requestId: string, justification: string): Promise<ControlsApiResponse<ManualTradeRequest>> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('manual_trading')

    const request = this.tradeRequests.get(requestId)
    if (!request) {
      throw new Error(`Trade request ${requestId} not found`)
    }

    const auditId = await this.audit.logAction(
      'manual_trade',
      'trade',
      requestId,
      { action: 'approve_trade' },
      justification,
      'high'
    )

    request.status = 'approved'
    // In real implementation, this would trigger actual trade execution
    
    return {
      success: true,
      data: request,
      timestamp: new Date(),
      requestId: `req_${Date.now()}`,
      auditId
    }
  }
}

/**
 * Risk parameter management service
 */
export class RiskParameterService {
  private auth: AuthenticationService
  private audit: AuditService
  private parameters: Map<string, RiskParameters> = new Map()

  constructor(auth: AuthenticationService, audit: AuditService) {
    this.auth = auth
    this.audit = audit
    this.initializeMockParameters()
  }

  private initializeMockParameters(): void {
    const mockParameters: RiskParameters[] = [
      {
        id: 'max_position_size',
        name: 'Maximum Position Size',
        description: 'Maximum allowed position size per trade',
        category: 'position_sizing',
        value: 100000,
        unit: 'USD',
        minValue: 1000,
        maxValue: 1000000,
        currentValue: 100000,
        defaultValue: 50000,
        complianceRequired: true,
        lastModified: new Date(),
        lastModifiedBy: 'system',
        history: []
      },
      {
        id: 'daily_loss_limit',
        name: 'Daily Loss Limit',
        description: 'Maximum allowed daily loss across all positions',
        category: 'daily_limits',
        value: 10000,
        unit: 'USD',
        minValue: 1000,
        maxValue: 50000,
        currentValue: 10000,
        defaultValue: 5000,
        complianceRequired: true,
        lastModified: new Date(),
        lastModifiedBy: 'system',
        history: []
      }
    ]

    mockParameters.forEach(param => this.parameters.set(param.id, param))
  }

  async getRiskParameters(): Promise<RiskParameters[]> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('risk_modification')

    return Array.from(this.parameters.values())
  }

  async updateRiskParameter(
    parameterId: string, 
    newValue: number, 
    justification: string
  ): Promise<ControlsApiResponse<RiskParameters>> {
    this.auth.requireAdministrator()
    this.auth.requirePermission('risk_modification')

    const parameter = this.parameters.get(parameterId)
    if (!parameter) {
      throw new Error(`Risk parameter ${parameterId} not found`)
    }

    // Validate new value
    if (newValue < parameter.minValue || newValue > parameter.maxValue) {
      throw new Error(`Value ${newValue} is outside allowed range [${parameter.minValue}, ${parameter.maxValue}]`)
    }

    const user = this.auth.getCurrentUser()!
    const auditId = await this.audit.logAction(
      'parameter_modification',
      'risk_parameter',
      parameterId,
      {
        previousValue: parameter.currentValue,
        newValue,
        parameter: parameter.name
      },
      justification,
      'high'
    )

    // Update parameter
    const updatedParameter = {
      ...parameter,
      currentValue: newValue,
      value: newValue,
      lastModified: new Date(),
      lastModifiedBy: user.id
    }

    this.parameters.set(parameterId, updatedParameter)

    return {
      success: true,
      data: updatedParameter,
      timestamp: new Date(),
      requestId: `req_${Date.now()}`,
      auditId
    }
  }
}

/**
 * Main trading controls service that coordinates all sub-services
 */
export class TradingControlsService {
  private auth: AuthenticationService
  private audit: AuditService
  private agentControl: AgentControlService
  private emergencyControls: EmergencyControlsService
  private manualTrading: ManualTradingService
  private riskParameters: RiskParameterService

  constructor() {
    this.auth = new AuthenticationService()
    this.audit = new AuditService(this.auth)
    this.agentControl = new AgentControlService(this.auth, this.audit)
    this.emergencyControls = new EmergencyControlsService(this.auth, this.audit, this.agentControl)
    this.manualTrading = new ManualTradingService(this.auth, this.audit)
    this.riskParameters = new RiskParameterService(this.auth, this.audit)
  }

  // Expose sub-services
  get authentication(): AuthenticationService { return this.auth }
  get auditService(): AuditService { return this.audit }
  get agents(): AgentControlService { return this.agentControl }
  get emergency(): EmergencyControlsService { return this.emergencyControls }
  get trading(): ManualTradingService { return this.manualTrading }
  get risk(): RiskParameterService { return this.riskParameters }

  async getSystemStatus(): Promise<SystemStatus> {
    this.auth.requireAdministrator()

    const agents = await this.agentControl.getAgents()
    const emergencyStops = await this.emergencyControls.getActiveEmergencyStops()
    
    const activeAgents = agents.filter(a => a.status === 'active').length
    const pausedAgents = agents.filter(a => a.status === 'paused').length  
    const errorAgents = agents.filter(a => a.status === 'error').length

    return {
      isHealthy: errorAgents === 0 && emergencyStops.length === 0,
      uptime: 99.5, // Mock uptime percentage
      activeAgents,
      pausedAgents,
      errorAgents,
      emergencyStopActive: emergencyStops.length > 0,
      maintenanceMode: false,
      pendingApprovals: 0, // Would count pending approvals in real system
      riskLevel: errorAgents > 0 ? 'high' : emergencyStops.length > 0 ? 'critical' : 'low',
      lastHealthCheck: new Date(),
      components: [
        {
          name: 'Agent Communication',
          status: 'healthy',
          lastCheck: new Date(),
          responseTime: 45
        },
        {
          name: 'Risk Engine',
          status: 'healthy', 
          lastCheck: new Date(),
          responseTime: 120
        },
        {
          name: 'Compliance Engine',
          status: 'healthy',
          lastCheck: new Date(),
          responseTime: 80
        }
      ]
    }
  }
}