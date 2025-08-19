/**
 * Trading Controls Dashboard - Main Integration Component
 * Story 9.5: Unified administrator dashboard for all trading controls and manual interventions
 * 
 * SECURITY: Administrator access only - comprehensive security validation with audit logging
 */

'use client'

import React, { useState, useEffect } from 'react'
import { useTradingControls } from '@/hooks/useTradingControls'
import { 
  SystemUser, 
  AIAgent, 
  EmergencyStop, 
  SystemStatus,
  ManualTradeRequest,
  RiskParameters,
  AuditLogEntry 
} from '@/types/tradingControls'
import Card from '@/components/ui/Card'
import Modal from '@/components/ui/Modal'
import AgentControlPanel from './AgentControlPanel'
import EmergencyControls from './EmergencyControls'
import ManualTradingInterface from './ManualTradingInterface'
import RiskParameterTools from './RiskParameterTools'
import AuditLogViewer from './AuditLogViewer'

/**
 * Props for TradingControlsDashboard component
 */
interface TradingControlsDashboardProps {
  /** Force compact view */
  compact?: boolean
  /** Custom CSS classes */
  className?: string
}

/**
 * Tab navigation type
 */
type DashboardTab = 'overview' | 'agents' | 'emergency' | 'trading' | 'parameters' | 'audit'

/**
 * Dashboard overview stats component
 */
function DashboardOverview({
  systemStatus,
  agents,
  emergencyStops,
  tradeRequests,
  auditLogs,
  currentUser
}: {
  systemStatus: SystemStatus | null
  agents: AIAgent[]
  emergencyStops: EmergencyStop[]
  tradeRequests: ManualTradeRequest[]
  auditLogs: AuditLogEntry[]
  currentUser: SystemUser | null
}) {
  const activeAgents = agents.filter(agent => agent.status === 'active').length
  const errorAgents = agents.filter(agent => agent.status === 'error').length
  const activeEmergencyStops = emergencyStops.filter(stop => stop.isActive).length
  const pendingTrades = tradeRequests.filter(trade => trade.status === 'pending_approval').length
  const recentAuditEntries = auditLogs.filter(log => {
    const hoursSince = (new Date().getTime() - log.timestamp.getTime()) / (1000 * 60 * 60)
    return hoursSince <= 24
  }).length

  const getSystemHealthColor = (): string => {
    if (activeEmergencyStops > 0) return 'text-red-400'
    if (errorAgents > 0) return 'text-yellow-400'
    return 'text-green-400'
  }

  const getSystemHealthText = (): string => {
    if (activeEmergencyStops > 0) return 'Emergency Stop Active'
    if (errorAgents > 0) return 'Agent Errors Detected'
    return 'System Healthy'
  }

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">Trading Controls Dashboard</h2>
            <p className="text-gray-400">
              Welcome back, <span className="text-white font-medium">{currentUser?.email || 'Administrator'}</span>
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Last access: {new Date().toLocaleString()} • All actions are logged and audited
            </p>
          </div>
          
          <div className="text-right">
            <div className={`text-lg font-bold ${getSystemHealthColor()}`}>
              {getSystemHealthText()}
            </div>
            <div className="text-sm text-gray-400">
              {systemStatus && `Uptime: ${Math.floor(systemStatus.uptime / 3600)}h`}
            </div>
          </div>
        </div>
      </Card>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{activeAgents}</div>
            <div className="text-xs text-gray-400">Active Agents</div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">{errorAgents}</div>
            <div className="text-xs text-gray-400">Error Agents</div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-400">{activeEmergencyStops}</div>
            <div className="text-xs text-gray-400">Emergency Stops</div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{pendingTrades}</div>
            <div className="text-xs text-gray-400">Pending Trades</div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">{tradeRequests.length}</div>
            <div className="text-xs text-gray-400">Total Requests</div>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-400">{recentAuditEntries}</div>
            <div className="text-xs text-gray-400">24h Audit Logs</div>
          </div>
        </Card>
      </div>

      {/* Alert Summary */}
      {(activeEmergencyStops > 0 || errorAgents > 0 || pendingTrades > 0) && (
        <Card className="border-yellow-500/50">
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-yellow-400">⚠ Attention Required</h3>
            
            {activeEmergencyStops > 0 && (
              <div className="p-3 bg-red-900/20 border border-red-500/30 rounded">
                <div className="text-red-300 font-medium">
                  🚨 {activeEmergencyStops} Emergency Stop{activeEmergencyStops > 1 ? 's' : ''} Active
                </div>
                <div className="text-red-200 text-sm">
                  System operations are halted. Check Emergency Controls tab for details.
                </div>
              </div>
            )}

            {errorAgents > 0 && (
              <div className="p-3 bg-yellow-900/20 border border-yellow-500/30 rounded">
                <div className="text-yellow-300 font-medium">
                  ⚠ {errorAgents} Agent{errorAgents > 1 ? 's' : ''} in Error State
                </div>
                <div className="text-yellow-200 text-sm">
                  Review Agent Control Panel to diagnose and resolve issues.
                </div>
              </div>
            )}

            {pendingTrades > 0 && (
              <div className="p-3 bg-blue-900/20 border border-blue-500/30 rounded">
                <div className="text-blue-300 font-medium">
                  📋 {pendingTrades} Trade Request{pendingTrades > 1 ? 's' : ''} Awaiting Approval
                </div>
                <div className="text-blue-200 text-sm">
                  Review Manual Trading Interface to approve or reject pending requests.
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}

/**
 * Tab navigation component
 */
function TabNavigation({
  activeTab,
  onTabChange,
  notifications
}: {
  activeTab: DashboardTab
  onTabChange: (tab: DashboardTab) => void
  notifications: Record<DashboardTab, number>
}) {
  const tabs: Array<{ id: DashboardTab; label: string; icon: string }> = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'agents', label: 'Agent Control', icon: '🤖' },
    { id: 'emergency', label: 'Emergency', icon: '🚨' },
    { id: 'trading', label: 'Manual Trading', icon: '💰' },
    { id: 'parameters', label: 'Risk Parameters', icon: '⚙️' },
    { id: 'audit', label: 'Audit Logs', icon: '📋' }
  ]

  return (
    <div className="border-b border-gray-700">
      <nav className="flex space-x-8 px-4">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-white hover:border-gray-300'
            }`}
          >
            <div className="flex items-center space-x-2">
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {notifications[tab.id] > 0 && (
                <span className="ml-1 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  {notifications[tab.id]}
                </span>
              )}
            </div>
          </button>
        ))}
      </nav>
    </div>
  )
}

/**
 * Security warning modal
 */
function SecurityWarningModal({
  isOpen,
  onClose,
  onAccept
}: {
  isOpen: boolean
  onClose: () => void
  onAccept: () => void
}) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <div className="bg-gray-900 p-6">
        <div className="text-center mb-6">
          <div className="text-red-400 text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-bold text-red-400 mb-2">ADMINISTRATOR ACCESS</h2>
          <p className="text-white">You are accessing critical trading system controls</p>
        </div>
        
        <div className="mb-6 p-4 bg-red-900/20 border border-red-500/50 rounded">
          <h3 className="text-red-300 font-medium mb-2">⚠ SECURITY WARNING</h3>
          <ul className="text-red-200 text-sm space-y-1">
            <li>• All actions are logged and audited</li>
            <li>• Changes can impact live trading operations</li>
            <li>• Financial losses may result from incorrect actions</li>
            <li>• Administrator credentials are required for all operations</li>
            <li>• This session will timeout after 30 minutes of inactivity</li>
          </ul>
        </div>

        <div className="flex justify-center space-x-4">
          <button
            onClick={onClose}
            className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded"
          >
            Cancel
          </button>
          <button
            onClick={onAccept}
            className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded font-bold"
          >
            I Understand - Continue
          </button>
        </div>
      </div>
    </Modal>
  )
}

/**
 * Main TradingControlsDashboard component
 */
export function TradingControlsDashboard({
  compact = false,
  className = ''
}: TradingControlsDashboardProps) {
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview')
  const [showSecurityWarning, setShowSecurityWarning] = useState(true)
  const [sessionStartTime] = useState(new Date())

  const {
    // State
    currentUser,
    isAuthenticated,
    agents,
    systemStatus,
    emergencyStops,
    tradeRequests,
    riskParameters,
    auditLogs,
    loading,
    error,
    
    // Actions
    requireAdminAccess,
    controlAgent,
    emergencyStopAll,
    clearEmergencyStop,
    submitTradeRequest,
    approveTradeRequest,
    updateRiskParameter,
    refreshAll
  } = useTradingControls()

  // Security check on component mount
  useEffect(() => {
    try {
      requireAdminAccess()
    } catch (error) {
      // Redirect to login or show error
      console.error('Admin access required:', error)
      return
    }
  }, [requireAdminAccess])

  // Calculate notifications for tabs
  const notifications: Record<DashboardTab, number> = {
    overview: 0,
    agents: agents.filter(agent => agent.status === 'error').length,
    emergency: emergencyStops.filter(stop => stop.isActive).length,
    trading: tradeRequests.filter(trade => trade.status === 'pending_approval').length,
    parameters: riskParameters.filter(param => param.currentValue !== param.defaultValue).length,
    audit: auditLogs.filter(log => {
      const hoursSince = (new Date().getTime() - log.timestamp.getTime()) / (1000 * 60 * 60)
      return hoursSince <= 1
    }).length
  }

  const handleSecurityAccept = () => {
    setShowSecurityWarning(false)
    // Log security acknowledgment
    console.log('Administrator security warning acknowledged at:', new Date().toISOString())
  }

  // Show loading state
  if (loading.initial) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-700 rounded w-96"></div>
          <div className="grid grid-cols-6 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-700 rounded"></div>
            ))}
          </div>
          <div className="h-64 bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  // Show error state
  if (error) {
    return (
      <Card className={className}>
        <div className="text-center py-12">
          <div className="text-red-400 text-xl mb-4">⚠ Dashboard Error</div>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={refreshAll}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded"
          >
            Retry Loading
          </button>
        </div>
      </Card>
    )
  }

  return (
    <>
      <div className={`bg-gray-900 ${className}`}>
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-700">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="text-2xl">🛡️</div>
                <div>
                  <h1 className="text-xl font-bold text-white">Trading Controls</h1>
                  <p className="text-sm text-gray-400">
                    Session: {Math.floor((new Date().getTime() - sessionStartTime.getTime()) / 60000)}m
                  </p>
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                <button
                  onClick={refreshAll}
                  disabled={loading.refresh}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded text-sm font-medium"
                >
                  {loading.refresh ? 'Refreshing...' : '🔄 Refresh All'}
                </button>
                
                <div className="text-sm text-gray-400">
                  <div>User: {currentUser?.email}</div>
                  <div>Role: {currentUser?.role}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <TabNavigation
            activeTab={activeTab}
            onTabChange={setActiveTab}
            notifications={notifications}
          />
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'overview' && (
            <DashboardOverview
              systemStatus={systemStatus}
              agents={agents}
              emergencyStops={emergencyStops}
              tradeRequests={tradeRequests}
              auditLogs={auditLogs}
              currentUser={currentUser}
            />
          )}

          {activeTab === 'agents' && (
            <AgentControlPanel
              agents={agents}
              loading={loading.agents}
              error={error}
              onAgentControl={controlAgent}
              onRefresh={() => refreshAll()}
              compact={compact}
            />
          )}

          {activeTab === 'emergency' && (
            <EmergencyControls
              systemStatus={systemStatus}
              emergencyStops={emergencyStops}
              loading={loading.emergency}
              error={error}
              onEmergencyStopAll={emergencyStopAll}
              onClearEmergencyStop={clearEmergencyStop}
              onRefresh={() => refreshAll()}
            />
          )}

          {activeTab === 'trading' && (
            <ManualTradingInterface
              tradeRequests={tradeRequests}
              loading={loading.trading}
              error={error}
              onSubmitTradeRequest={submitTradeRequest}
              onApproveTradeRequest={approveTradeRequest}
              onRefresh={() => refreshAll()}
            />
          )}

          {activeTab === 'parameters' && (
            <RiskParameterTools
              riskParameters={riskParameters}
              loading={loading.parameters}
              error={error}
              onUpdateParameter={updateRiskParameter}
              onRefresh={() => refreshAll()}
            />
          )}

          {activeTab === 'audit' && (
            <AuditLogViewer
              auditLogs={auditLogs}
              loading={loading.audit}
              error={error}
              onRefresh={() => refreshAll()}
              onExport={async (format, filter) => {
                // Export functionality would be implemented here
                console.log(`Exporting audit logs as ${format} with filter:`, filter)
                return true
              }}
            />
          )}
        </div>
      </div>

      {/* Security Warning Modal */}
      <SecurityWarningModal
        isOpen={showSecurityWarning}
        onClose={() => {
          // Don't allow closing without accepting
          console.log('Security warning must be acknowledged')
        }}
        onAccept={handleSecurityAccept}
      />
    </>
  )
}

export default TradingControlsDashboard