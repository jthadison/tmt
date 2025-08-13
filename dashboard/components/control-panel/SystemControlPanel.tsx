'use client'

import { useState, useEffect } from 'react'
import { SystemControlPanelData, SystemHealthStatus } from '@/types/systemControl'
import { EmergencyStop } from './EmergencyStop'
import { AgentMonitor } from './AgentMonitor'
import { CircuitBreakerPanel } from './CircuitBreakerPanel'
import { TradingControls } from './TradingControls'
import { RiskParameterEditor } from './RiskParameterEditor'
import { SystemLogViewer } from './SystemLogViewer'
import { LoadingSkeleton } from '../ui/LoadingSkeleton'

/**
 * Props for SystemControlPanel component
 */
interface SystemControlPanelProps {
  /** Loading state indicator */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback when data needs refresh */
  onRefresh?: () => void
}

/**
 * Main system control panel for operators to monitor and control the trading system
 * Provides comprehensive controls for emergency situations and system management
 */
export function SystemControlPanel({
  loading = false,
  error,
  onRefresh
}: SystemControlPanelProps) {
  const [controlPanelData, setControlPanelData] = useState<SystemControlPanelData | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'agents' | 'circuit-breakers' | 'trading' | 'risk' | 'logs'>('overview')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval] = useState(5000) // 5 seconds

  // Mock data for development - will be replaced with real API calls
  useEffect(() => {
    const loadControlPanelData = async () => {
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Mock system control panel data
      const mockData: SystemControlPanelData = {
        systemHealth: {
          overallStatus: 'healthy',
          uptime: 7 * 24 * 60 * 60 * 1000, // 7 days
          activeAgents: 8,
          errorAgents: 0,
          activeTradingAccounts: 12,
          pausedTradingAccounts: 1,
          openCircuitBreakers: 0,
          criticalLogs: 2,
          performance: {
            cpu: 45.2,
            memory: 67.8,
            disk: 23.1,
            networkLatency: 12
          }
        },
        emergencyStop: {
          isActive: false,
          affectedAccounts: 0,
          positionsClosing: 0,
          contactsNotified: []
        },
        agents: [
          {
            id: 'agent-circuit-breaker',
            name: 'Circuit Breaker Agent',
            type: 'circuit_breaker',
            status: 'active',
            uptime: 7 * 24 * 60 * 60 * 1000,
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
            status: 'active',
            uptime: 7 * 24 * 60 * 60 * 1000,
            lastHeartbeat: new Date(Date.now() - 1500),
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
            version: '3.2.1'
          },
          {
            id: 'agent-risk-manager',
            name: 'Risk Manager',
            type: 'risk_manager',
            status: 'active',
            uptime: 7 * 24 * 60 * 60 * 1000,
            lastHeartbeat: new Date(Date.now() - 3000),
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
          }
        ],
        circuitBreakers: [
          {
            id: 'cb-api-rate-limit',
            name: 'API Rate Limit Breaker',
            status: 'closed',
            threshold: 100,
            failures: 12,
            successRate: 88.0,
            isManualOverride: false,
            description: 'Protects against API rate limiting',
            category: 'External APIs'
          },
          {
            id: 'cb-position-size',
            name: 'Position Size Breaker',
            status: 'closed',
            threshold: 50,
            failures: 3,
            successRate: 94.0,
            isManualOverride: false,
            description: 'Prevents oversized positions',
            category: 'Risk Management'
          }
        ],
        tradingSessions: [
          {
            accountId: 'acc-001',
            accountName: 'FTMO Challenge #1',
            status: 'active',
            activePositions: 3,
            currentPnL: 1250.00,
            dailyTrades: 12,
            lastTradeTime: new Date(Date.now() - 15 * 60 * 1000)
          },
          {
            accountId: 'acc-002',
            accountName: 'MyForexFunds Live',
            status: 'paused',
            pausedBy: 'operator-001',
            pauseReason: 'Manual review required',
            pausedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
            activePositions: 0,
            currentPnL: -350.00,
            dailyTrades: 5
          }
        ],
        riskParameters: [
          {
            id: 'max-daily-loss',
            name: 'Maximum Daily Loss',
            category: 'drawdown',
            value: 5000,
            minValue: 1000,
            maxValue: 10000,
            unit: 'USD',
            description: 'Maximum loss allowed per day across all accounts',
            lastModified: new Date(Date.now() - 24 * 60 * 60 * 1000),
            modifiedBy: 'admin-001',
            requiresRestart: false
          },
          {
            id: 'max-position-size',
            name: 'Maximum Position Size',
            category: 'position_sizing',
            value: 2.0,
            minValue: 0.1,
            maxValue: 10.0,
            unit: 'lots',
            description: 'Maximum position size per trade',
            lastModified: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
            modifiedBy: 'admin-001',
            requiresRestart: true
          }
        ],
        recentLogs: [
          {
            id: 'log-001',
            timestamp: new Date(Date.now() - 5 * 60 * 1000),
            level: 'info',
            component: 'execution-engine',
            message: 'Trade executed successfully for EUR/USD',
            accountId: 'acc-001',
            requestId: 'req-12345'
          },
          {
            id: 'log-002',
            timestamp: new Date(Date.now() - 10 * 60 * 1000),
            level: 'warn',
            component: 'risk-manager',
            message: 'Daily loss approaching 80% of limit',
            accountId: 'acc-002'
          },
          {
            id: 'log-003',
            timestamp: new Date(Date.now() - 15 * 60 * 1000),
            level: 'error',
            component: 'wyckoff-analyzer',
            message: 'Failed to analyze market structure',
            context: { symbol: 'GBP/USD', error: 'Timeout' }
          }
        ],
        notifications: [
          {
            id: 'notif-001',
            type: 'warning',
            title: 'High CPU Usage',
            message: 'Wyckoff Analyzer agent CPU usage is above 75%',
            timestamp: new Date(Date.now() - 30 * 60 * 1000),
            isRead: false,
            source: 'agent-wyckoff'
          }
        ],
        lastUpdate: new Date()
      }

      setControlPanelData(mockData)
    }

    if (!loading) {
      loadControlPanelData()
    }
  }, [loading])

  // Auto-refresh functionality
  useEffect(() => {
    if (!autoRefresh || loading) return

    const interval = setInterval(() => {
      onRefresh?.()
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, onRefresh, loading])

  const getSystemStatusColor = (status: SystemHealthStatus['overallStatus']): string => {
    switch (status) {
      case 'healthy':
        return 'text-green-400'
      case 'warning':
        return 'text-yellow-400'
      case 'critical':
        return 'text-orange-400'
      case 'emergency':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }

  const getSystemStatusIcon = (status: SystemHealthStatus['overallStatus']): string => {
    switch (status) {
      case 'healthy':
        return '✓'
      case 'warning':
        return '⚠'
      case 'critical':
        return '⚡'
      case 'emergency':
        return '🚨'
      default:
        return '○'
    }
  }

  const formatUptime = (uptime: number): string => {
    const days = Math.floor(uptime / (24 * 60 * 60 * 1000))
    const hours = Math.floor((uptime % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000))
    const minutes = Math.floor((uptime % (60 * 60 * 1000)) / (60 * 1000))
    
    if (days > 0) return `${days}d ${hours}h`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  if (loading || !controlPanelData) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton className="h-20" />
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
        </div>
        <LoadingSkeleton className="h-96" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400 text-xl mb-2">Error Loading Control Panel</div>
        <p className="text-gray-400 mb-4">{error}</p>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
          >
            Try Again
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* System Header */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">System Control Panel</h1>
            <div className="flex items-center gap-3">
              <span className={`text-lg ${getSystemStatusColor(controlPanelData.systemHealth.overallStatus)}`}>
                {getSystemStatusIcon(controlPanelData.systemHealth.overallStatus)}
              </span>
              <span className="text-gray-300 capitalize">
                {controlPanelData.systemHealth.overallStatus}
              </span>
              <span className="text-gray-500">•</span>
              <span className="text-gray-400">
                Uptime: {formatUptime(controlPanelData.systemHealth.uptime)}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-300">Auto-refresh</label>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-600 bg-gray-700 text-blue-600"
              />
            </div>
            <button
              onClick={onRefresh}
              className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors"
            >
              ⟳ Refresh
            </button>
          </div>
        </div>
      </div>

      {/* System Health Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-gray-400 text-sm">Active Agents</div>
              <div className="text-2xl font-bold text-white">
                {controlPanelData.systemHealth.activeAgents}
              </div>
              {controlPanelData.systemHealth.errorAgents > 0 && (
                <div className="text-red-400 text-xs">
                  {controlPanelData.systemHealth.errorAgents} errors
                </div>
              )}
            </div>
            <div className="text-green-400 text-xl">🤖</div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-gray-400 text-sm">Trading Accounts</div>
              <div className="text-2xl font-bold text-white">
                {controlPanelData.systemHealth.activeTradingAccounts}
              </div>
              {controlPanelData.systemHealth.pausedTradingAccounts > 0 && (
                <div className="text-yellow-400 text-xs">
                  {controlPanelData.systemHealth.pausedTradingAccounts} paused
                </div>
              )}
            </div>
            <div className="text-blue-400 text-xl">📊</div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-gray-400 text-sm">Circuit Breakers</div>
              <div className="text-2xl font-bold text-white">
                {controlPanelData.circuitBreakers.length - controlPanelData.systemHealth.openCircuitBreakers}
              </div>
              {controlPanelData.systemHealth.openCircuitBreakers > 0 && (
                <div className="text-red-400 text-xs">
                  {controlPanelData.systemHealth.openCircuitBreakers} open
                </div>
              )}
            </div>
            <div className="text-purple-400 text-xl">⚡</div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-gray-400 text-sm">System Performance</div>
              <div className="text-2xl font-bold text-white">
                {controlPanelData.systemHealth.performance.cpu.toFixed(0)}%
              </div>
              <div className="text-gray-400 text-xs">
                CPU • {controlPanelData.systemHealth.performance.memory.toFixed(0)}% RAM
              </div>
            </div>
            <div className="text-orange-400 text-xl">⚙️</div>
          </div>
        </div>
      </div>

      {/* Emergency Stop - Always Visible */}
      <EmergencyStop
        emergencyStopStatus={controlPanelData.emergencyStop}
        onEmergencyStop={(request) => {
          console.log('Emergency stop triggered:', request)
          // Handle emergency stop
        }}
      />

      {/* Navigation Tabs */}
      <div className="bg-gray-800 rounded-lg">
        <div className="border-b border-gray-700">
          <nav className="flex space-x-8 px-6">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'agents', label: 'Agents' },
              { id: 'circuit-breakers', label: 'Circuit Breakers' },
              { id: 'trading', label: 'Trading Control' },
              { id: 'risk', label: 'Risk Parameters' },
              { id: 'logs', label: 'System Logs' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`
                  py-4 px-2 border-b-2 font-medium text-sm transition-colors
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <AgentMonitor 
                agents={controlPanelData.agents.slice(0, 3)} 
                compact 
                onAgentAction={(request) => console.log('Agent action:', request)}
              />
              <CircuitBreakerPanel 
                circuitBreakers={controlPanelData.circuitBreakers} 
                compact
                onCircuitBreakerAction={(request) => console.log('Circuit breaker action:', request)}
              />
            </div>
          )}

          {activeTab === 'agents' && (
            <AgentMonitor 
              agents={controlPanelData.agents} 
              onAgentAction={(request) => console.log('Agent action:', request)}
            />
          )}

          {activeTab === 'circuit-breakers' && (
            <CircuitBreakerPanel 
              circuitBreakers={controlPanelData.circuitBreakers}
              onCircuitBreakerAction={(request) => console.log('Circuit breaker action:', request)}
            />
          )}

          {activeTab === 'trading' && (
            <TradingControls 
              tradingSessions={controlPanelData.tradingSessions}
              onTradingAction={(request) => console.log('Trading action:', request)}
            />
          )}

          {activeTab === 'risk' && (
            <RiskParameterEditor 
              riskParameters={controlPanelData.riskParameters}
              onParameterUpdate={(update) => console.log('Parameter update:', update)}
            />
          )}

          {activeTab === 'logs' && (
            <SystemLogViewer 
              logEntries={controlPanelData.recentLogs}
              onExportLogs={(filter) => console.log('Log export:', filter)}
            />
          )}
        </div>
      </div>

      {/* System Notifications */}
      {controlPanelData.notifications.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Recent Notifications</h3>
          <div className="space-y-3">
            {controlPanelData.notifications.map((notification) => (
              <div 
                key={notification.id}
                className={`p-3 rounded border-l-4 ${
                  notification.type === 'error' ? 'border-red-500 bg-red-900/20' :
                  notification.type === 'warning' ? 'border-yellow-500 bg-yellow-900/20' :
                  notification.type === 'success' ? 'border-green-500 bg-green-900/20' :
                  'border-blue-500 bg-blue-900/20'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium text-white">{notification.title}</div>
                    <div className="text-sm text-gray-300 mt-1">{notification.message}</div>
                    <div className="text-xs text-gray-500 mt-2">
                      {notification.timestamp.toLocaleString()} • {notification.source}
                    </div>
                  </div>
                  {!notification.isRead && (
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}