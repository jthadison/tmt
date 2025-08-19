/**
 * Trading Controls and Manual Intervention Types
 * Story 9.5: Administrator-only trading controls with security and audit logging
 */

// ============================================================================
// CORE TYPES
// ============================================================================

/**
 * User role definitions for access control
 */
export type UserRole = 'administrator' | 'trader' | 'viewer' | 'readonly'

/**
 * System user interface
 */
export interface SystemUser {
  id: string
  email: string
  name: string
  role: UserRole
  permissions: UserPermission[]
  lastLogin?: Date
  isActive: boolean
  metadata?: Record<string, any>
}

/**
 * User permissions for granular access control
 */
export type UserPermission = 
  | 'agent_control'
  | 'emergency_stop'
  | 'manual_trading'
  | 'risk_modification'
  | 'system_override'
  | 'audit_access'
  | 'user_management'

/**
 * AI Agent status and control interface
 */
export interface AIAgent {
  id: string
  name: string
  type: AgentType
  status: AgentStatus
  isActive: boolean
  lastHeartbeat: Date
  currentParameters: AgentParameters
  defaultParameters: AgentParameters
  performance: AgentPerformance
  errorCount: number
  lastError?: string
  metadata?: Record<string, any>
}

/**
 * AI Agent types in the system
 */
export type AgentType = 
  | 'circuit_breaker'
  | 'risk_management'
  | 'execution_engine'
  | 'market_analysis'
  | 'portfolio_optimization'
  | 'compliance'
  | 'human_behavior'
  | 'anti_correlation'

/**
 * AI Agent operational status
 */
export type AgentStatus = 
  | 'active'
  | 'paused'
  | 'stopped'
  | 'error'
  | 'maintenance'
  | 'emergency_stop'

/**
 * Agent parameters configuration
 */
export interface AgentParameters {
  riskLevel: number // 0-100
  maxPositionSize: number
  maxDailyLoss: number
  stopLossThreshold: number
  takeProfitThreshold: number
  timeoutSeconds: number
  retryAttempts: number
  customParameters: Record<string, any>
  complianceRules: ComplianceRule[]
}

/**
 * Agent performance metrics
 */
export interface AgentPerformance {
  uptime: number // percentage
  responseTime: number // milliseconds
  successRate: number // percentage
  totalActions: number
  errorRate: number
  lastUpdateTime: Date
}

// ============================================================================
// CONTROL ACTIONS
// ============================================================================

/**
 * Agent control actions available to administrators
 */
export type AgentControlAction = 
  | 'pause'
  | 'resume'
  | 'stop'
  | 'restart'
  | 'emergency_stop'
  | 'update_parameters'
  | 'reset_errors'

/**
 * System-wide control actions
 */
export type SystemControlAction = 
  | 'emergency_stop_all'
  | 'pause_all_agents'
  | 'resume_all_agents'
  | 'system_maintenance_mode'
  | 'force_risk_override'
  | 'global_parameter_update'

/**
 * Manual trading actions
 */
export type ManualTradingAction = 
  | 'market_buy'
  | 'market_sell'
  | 'limit_buy'
  | 'limit_sell'
  | 'close_position'
  | 'close_all_positions'
  | 'cancel_order'
  | 'modify_order'

// ============================================================================
// EMERGENCY CONTROLS
// ============================================================================

/**
 * Emergency stop configuration
 */
export interface EmergencyStop {
  id: string
  type: EmergencyStopType
  isActive: boolean
  triggeredBy: string // user ID
  triggeredAt: Date
  reason: string
  affectedAgents: string[]
  affectedAccounts: string[]
  estimatedDuration?: number // minutes
  overrideRequired: boolean
}

/**
 * Types of emergency stops
 */
export type EmergencyStopType = 
  | 'immediate_halt'
  | 'gradual_shutdown'
  | 'risk_breach'
  | 'system_error'
  | 'manual_intervention'
  | 'compliance_violation'

// ============================================================================
// MANUAL TRADING
// ============================================================================

/**
 * Manual trade request
 */
export interface ManualTradeRequest {
  id: string
  userId: string
  action: ManualTradingAction
  instrument: string
  quantity: number
  price?: number
  orderType: 'market' | 'limit' | 'stop' | 'stop_limit'
  timeInForce: 'GTC' | 'IOC' | 'FOK' | 'DAY'
  accountId: string
  justification: string
  riskAssessment: RiskAssessment
  complianceCheck: ComplianceCheck
  status: ManualTradeStatus
  createdAt: Date
  executedAt?: Date
  metadata?: Record<string, any>
}

/**
 * Manual trade execution status
 */
export type ManualTradeStatus = 
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'executing'
  | 'executed'
  | 'failed'
  | 'cancelled'

// ============================================================================
// RISK MANAGEMENT
// ============================================================================

/**
 * Risk parameter configuration
 */
export interface RiskParameters {
  id: string
  name: string
  description: string
  category: RiskCategory
  value: number
  unit: string
  minValue: number
  maxValue: number
  currentValue: number
  defaultValue: number
  complianceRequired: boolean
  lastModified: Date
  lastModifiedBy: string
  history: RiskParameterHistory[]
}

/**
 * Risk parameter categories
 */
export type RiskCategory = 
  | 'position_sizing'
  | 'daily_limits'
  | 'drawdown_limits'
  | 'exposure_limits'
  | 'volatility_controls'
  | 'correlation_limits'
  | 'leverage_controls'

/**
 * Risk parameter modification history
 */
export interface RiskParameterHistory {
  id: string
  parameterId: string
  previousValue: number
  newValue: number
  modifiedBy: string
  modifiedAt: Date
  justification: string
  approvedBy?: string
  approvedAt?: Date
}

/**
 * Risk assessment for manual trades
 */
export interface RiskAssessment {
  overall: 'low' | 'medium' | 'high' | 'critical'
  factors: RiskFactor[]
  maxDrawdown: number
  positionImpact: number
  correlationRisk: number
  leverageImpact: number
  recommendations: string[]
  warnings: string[]
  approved: boolean
  assessedBy: string
  assessedAt: Date
}

/**
 * Individual risk factors
 */
export interface RiskFactor {
  name: string
  level: 'low' | 'medium' | 'high'
  description: string
  impact: number // 0-100
  mitigation?: string
}

// ============================================================================
// COMPLIANCE
// ============================================================================

/**
 * Compliance rule definition
 */
export interface ComplianceRule {
  id: string
  name: string
  description: string
  category: ComplianceCategory
  condition: string // JSON condition logic
  action: ComplianceAction
  severity: 'info' | 'warning' | 'error' | 'critical'
  isActive: boolean
  exemptions: string[] // user IDs who can override
  createdAt: Date
  lastUpdated: Date
}

/**
 * Compliance categories
 */
export type ComplianceCategory = 
  | 'position_limits'
  | 'trading_hours'
  | 'instrument_restrictions'
  | 'regional_regulations'
  | 'risk_management'
  | 'reporting_requirements'

/**
 * Compliance actions when rule is violated
 */
export type ComplianceAction = 
  | 'block_trade'
  | 'require_approval'
  | 'log_warning'
  | 'notify_compliance'
  | 'emergency_stop'
  | 'parameter_override'

/**
 * Compliance check result
 */
export interface ComplianceCheck {
  passed: boolean
  violations: ComplianceViolation[]
  warnings: string[]
  overrides: ComplianceOverride[]
  checkedAt: Date
  checkedBy: string
}

/**
 * Compliance violation details
 */
export interface ComplianceViolation {
  ruleId: string
  ruleName: string
  description: string
  severity: 'warning' | 'error' | 'critical'
  canOverride: boolean
  overrideReason?: string
  overriddenBy?: string
  overriddenAt?: Date
}

/**
 * Compliance override record
 */
export interface ComplianceOverride {
  violationId: string
  overriddenBy: string
  overriddenAt: Date
  justification: string
  approvedBy?: string
  approvedAt?: Date
  expiresAt?: Date
}

// ============================================================================
// AUDIT LOGGING
// ============================================================================

/**
 * Audit log entry for all manual interventions
 */
export interface AuditLogEntry {
  id: string
  timestamp: Date
  userId: string
  userEmail: string
  action: AuditAction
  resource: AuditResource
  resourceId: string
  details: Record<string, any>
  justification: string
  approvalRequired: boolean
  approvedBy?: string
  approvedAt?: Date
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  complianceCheck: ComplianceCheck
  sessionId: string
  ipAddress: string
  userAgent: string
  result: 'success' | 'failure' | 'pending'
  errorMessage?: string
}

/**
 * Audit action types
 */
export type AuditAction = 
  | 'agent_control'
  | 'emergency_stop'
  | 'manual_trade'
  | 'parameter_modification'
  | 'compliance_override'
  | 'system_access'
  | 'data_export'
  | 'configuration_change'

/**
 * Audit resource types
 */
export type AuditResource = 
  | 'agent'
  | 'system'
  | 'trade'
  | 'risk_parameter'
  | 'compliance_rule'
  | 'user_account'
  | 'audit_log'

// ============================================================================
// APPROVAL WORKFLOWS
// ============================================================================

/**
 * Approval workflow for high-risk actions
 */
export interface ApprovalWorkflow {
  id: string
  requestId: string
  requestType: ApprovalRequestType
  requestedBy: string
  requestedAt: Date
  justification: string
  riskAssessment: RiskAssessment
  complianceCheck: ComplianceCheck
  status: ApprovalStatus
  approvers: ApprovalStep[]
  currentStep: number
  finalDecision?: ApprovalDecision
  completedAt?: Date
  metadata?: Record<string, any>
}

/**
 * Types of requests requiring approval
 */
export type ApprovalRequestType = 
  | 'manual_trade'
  | 'risk_parameter_change'
  | 'compliance_override'
  | 'emergency_override'
  | 'system_modification'

/**
 * Approval workflow status
 */
export type ApprovalStatus = 
  | 'pending'
  | 'in_review'
  | 'approved'
  | 'rejected'
  | 'cancelled'
  | 'expired'

/**
 * Individual approval step
 */
export interface ApprovalStep {
  stepNumber: number
  approverId: string
  approverEmail: string
  approverRole: UserRole
  required: boolean
  status: 'pending' | 'approved' | 'rejected' | 'skipped'
  decision?: ApprovalDecision
  decidedAt?: Date
  comments?: string
}

/**
 * Approval decision details
 */
export interface ApprovalDecision {
  decision: 'approve' | 'reject' | 'request_changes'
  comments: string
  conditions?: string[]
  expiresAt?: Date
  decidedBy: string
  decidedAt: Date
}

// ============================================================================
// SERVICE INTERFACES
// ============================================================================

/**
 * Trading controls service configuration
 */
export interface TradingControlsConfig {
  emergencyStopTimeout: number // milliseconds
  approvalTimeout: number // milliseconds  
  maxRiskOverride: number // percentage
  requiredApprovers: number
  auditLogRetention: number // days
  sessionTimeout: number // minutes
  maxConcurrentSessions: number
  ipWhitelist?: string[]
  maintenanceMode: boolean
}

/**
 * System status for trading controls
 */
export interface SystemStatus {
  isHealthy: boolean
  uptime: number // seconds
  activeAgents: number
  pausedAgents: number
  errorAgents: number
  emergencyStopActive: boolean
  maintenanceMode: boolean
  pendingApprovals: number
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  lastHealthCheck: Date
  components: ComponentStatus[]
}

/**
 * Individual component status
 */
export interface ComponentStatus {
  name: string
  status: 'healthy' | 'warning' | 'error' | 'offline'
  lastCheck: Date
  responseTime?: number
  errorMessage?: string
}

// ============================================================================
// API INTERFACES
// ============================================================================

/**
 * API response wrapper for trading controls
 */
export interface ControlsApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  timestamp: Date
  requestId: string
  auditId?: string
}

/**
 * Filter and sort options for audit logs
 */
export interface AuditLogFilter {
  userId?: string
  action?: AuditAction
  resource?: AuditResource
  dateFrom?: Date
  dateTo?: Date
  riskLevel?: 'low' | 'medium' | 'high' | 'critical'
  result?: 'success' | 'failure' | 'pending'
  limit?: number
  offset?: number
  sortBy?: 'timestamp' | 'action' | 'riskLevel'
  sortOrder?: 'asc' | 'desc'
}

/**
 * Export configuration for audit data
 */
export interface AuditExportConfig {
  format: 'csv' | 'json' | 'pdf'
  filter: AuditLogFilter
  includeDetails: boolean
  encryptionRequired: boolean
  destinationEmail?: string
  retentionPeriod: number // days
}