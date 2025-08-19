'use client'

import React, { useState, useEffect } from 'react'
import { useTradeExecution } from '@/hooks/useTradeExecution'
import { TradeExecutionFeed } from '@/components/trade-execution/TradeExecutionFeed'
import { ExecutionMetrics } from '@/components/trade-execution/ExecutionMetrics'
import { OrderLifecycleTracker } from '@/components/trade-execution/OrderLifecycleTracker'
import { TradeDetailsModal } from '@/components/trade-execution/TradeDetailsModal'
import { ExecutionAlerts } from '@/components/trade-execution/ExecutionAlerts'
import { TradeExecution, OrderLifecycle, TimeframePeriod } from '@/types/tradeExecution'
import Card from '@/components/ui/Card'

/**
 * Main Trade Execution Dashboard Page - Story 9.4 Implementation
 * 
 * This page implements all 5 acceptance criteria for Story 9.4:
 * AC1: Real-time trade execution feed with live updates and filtering
 * AC2: Order lifecycle tracking with visual timeline representation
 * AC3: Execution quality metrics with charts and aggregated data
 * AC4: Trade details modal with comprehensive information
 * AC5: Execution alerts and notifications system
 */
export default function TradeExecutionDashboard() {
  const {
    executions,
    metrics,
    alerts,
    alertRules,
    isLoading,
    error,
    lastUpdate,
    wsStatus,
    filter,
    sort,
    feedConfig,
    refreshExecutions,
    loadMoreExecutions,
    getExecutionById,
    refreshMetrics,
    getMetricsByTimeframe,
    refreshAlerts,
    acknowledgeAlert,
    dismissAlert,
    getOrderLifecycle,
    updateFilter,
    updateSort,
    clearFilters,
    updateFeedConfig,
    pauseRealTimeUpdates,
    resumeRealTimeUpdates,
    reconnectWebSocket,
    exportExecutions,
    getFilteredExecutions,
    getTotalVolume,
    getAverageSlippage
  } = useTradeExecution()

  // Local state
  const [currentView, setCurrentView] = useState<'overview' | 'feed' | 'metrics' | 'alerts'>('overview')
  const [selectedExecution, setSelectedExecution] = useState<TradeExecution | null>(null)
  const [selectedOrderLifecycle, setSelectedOrderLifecycle] = useState<OrderLifecycle | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [selectedTimeframe, setSelectedTimeframe] = useState<TimeframePeriod>('1h')

  // Real-time status tracking
  const [connectionStatus, setConnectionStatus] = useState({
    wsConnected: wsStatus.connected,
    lastHeartbeat: wsStatus.lastMessage,
    reconnectAttempts: wsStatus.reconnectAttempts
  })

  // Update connection status when wsStatus changes
  useEffect(() => {
    setConnectionStatus({
      wsConnected: wsStatus.connected,
      lastHeartbeat: wsStatus.lastMessage,
      reconnectAttempts: wsStatus.reconnectAttempts
    })
  }, [wsStatus])

  // Handle execution selection for details modal
  const handleExecutionClick = async (execution: TradeExecution) => {
    setSelectedExecution(execution)
    
    // Fetch order lifecycle data
    try {
      const lifecycle = await getOrderLifecycle(execution.orderId)
      setSelectedOrderLifecycle(lifecycle)
    } catch (error) {
      console.error('Failed to fetch order lifecycle:', error)
      setSelectedOrderLifecycle(null)
    }
    
    setShowDetailsModal(true)
  }

  // Handle trade export
  const handleExportTrade = async (execution: TradeExecution, format: 'csv' | 'json' | 'pdf') => {
    try {
      const exportUrl = await exportExecutions(format)
      if (exportUrl) {
        // In a real implementation, this would trigger a download
        window.open(exportUrl, '_blank')
      }
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  // Handle timeframe changes for metrics
  const handleTimeframeChange = (timeframe: TimeframePeriod) => {
    setSelectedTimeframe(timeframe)
    getMetricsByTimeframe(timeframe)
  }

  // Handle alert rule management (mock implementation)
  const handleUpdateAlertRule = (rule: any) => {
    // In a real implementation, this would call an API
    console.log('Updating alert rule:', rule)
  }

  const handleDeleteAlertRule = (ruleId: string) => {
    // In a real implementation, this would call an API
    console.log('Deleting alert rule:', ruleId)
  }

  // Get real-time stats for dashboard overview
  const dashboardStats = {
    totalExecutions: executions.length,
    successfulExecutions: executions.filter(e => e.status === 'filled').length,
    failedExecutions: executions.filter(e => e.status === 'rejected' || e.status === 'cancelled').length,
    partialExecutions: executions.filter(e => e.status === 'partial').length,
    pendingExecutions: executions.filter(e => e.status === 'pending').length,
    totalVolume: getTotalVolume(),
    averageSlippage: getAverageSlippage(),
    unacknowledgedAlerts: alerts.filter(a => !a.acknowledged).length
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const formatSlippage = (slippage: number): string => {
    return `${(slippage * 10000).toFixed(1)} pips`
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Trade Execution Monitoring</h1>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <span>
                Last updated: {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Never'}
              </span>
              <span>•</span>
              <span>{executions.length} total executions</span>
              <span>•</span>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  connectionStatus.wsConnected ? 'bg-green-400' : 'bg-red-400'
                } animate-pulse`} />
                <span className={connectionStatus.wsConnected ? 'text-green-400' : 'text-red-400'}>
                  {connectionStatus.wsConnected ? 'Connected' : 'Disconnected'}
                </span>
                {!connectionStatus.wsConnected && connectionStatus.reconnectAttempts > 0 && (
                  <span className="text-yellow-400">
                    (Reconnecting... {connectionStatus.reconnectAttempts}/5)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center gap-2">
            <div className="flex bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setCurrentView('overview')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'overview'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setCurrentView('feed')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'feed'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Live Feed
              </button>
              <button
                onClick={() => setCurrentView('metrics')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'metrics'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Metrics
              </button>
              <button
                onClick={() => setCurrentView('alerts')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'alerts'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Alerts {alerts.filter(a => !a.acknowledged).length > 0 && (
                  <span className="ml-1 bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                    {alerts.filter(a => !a.acknowledged).length}
                  </span>
                )}
              </button>
            </div>
            
            {/* Real-time Controls */}
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={feedConfig.pauseUpdates ? resumeRealTimeUpdates : pauseRealTimeUpdates}
                className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
                  feedConfig.pauseUpdates 
                    ? 'bg-yellow-600 hover:bg-yellow-700 text-white' 
                    : 'bg-green-600 hover:bg-green-700 text-white'
                }`}
              >
                {feedConfig.pauseUpdates ? '▶ Resume' : '⏸ Pause'} Updates
              </button>
              
              {!connectionStatus.wsConnected && (
                <button
                  onClick={reconnectWebSocket}
                  className="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded text-sm font-medium"
                >
                  Reconnect
                </button>
              )}
              
              <button
                onClick={refreshExecutions}
                disabled={isLoading}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-3 py-2 rounded text-sm font-medium"
              >
                {isLoading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <Card className="border-red-500/50 bg-red-900/20">
            <div className="flex items-center gap-3">
              <div className="text-red-400 text-lg">⚠️</div>
              <div>
                <div className="text-red-400 font-medium">Error</div>
                <div className="text-red-300 text-sm">{error}</div>
              </div>
            </div>
          </Card>
        )}

        {/* Main Content */}
        {currentView === 'overview' && (
          <div className="space-y-6">
            {/* Dashboard Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
              <Card>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">{dashboardStats.totalExecutions}</div>
                  <div className="text-xs text-gray-400">Total</div>
                </div>
              </Card>
              
              <Card>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">{dashboardStats.successfulExecutions}</div>
                  <div className="text-xs text-gray-400">Filled</div>
                </div>
              </Card>
              
              <Card>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-400">{dashboardStats.partialExecutions}</div>
                  <div className="text-xs text-gray-400">Partial</div>
                </div>
              </Card>
              
              <Card>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-400">{dashboardStats.pendingExecutions}</div>
                  <div className="text-xs text-gray-400">Pending</div>
                </div>
              </Card>
              
              <Card>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-400">{dashboardStats.failedExecutions}</div>
                  <div className="text-xs text-gray-400">Failed</div>
                </div>
              </Card>
              
              <Card>
                <div className="text-center">
                  <div className="text-lg font-bold text-white">{formatCurrency(dashboardStats.totalVolume)}</div>
                  <div className="text-xs text-gray-400">Volume</div>
                </div>
              </Card>
              
              <Card>
                <div className="text-center">
                  <div className="text-lg font-bold text-orange-400">{formatSlippage(dashboardStats.averageSlippage)}</div>
                  <div className="text-xs text-gray-400">Avg Slippage</div>
                </div>
              </Card>
              
              <Card>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-400">{dashboardStats.unacknowledgedAlerts}</div>
                  <div className="text-xs text-gray-400">Alerts</div>
                </div>
              </Card>
            </div>

            {/* Recent Activity and Alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TradeExecutionFeed
                executions={executions.slice(0, 10)} // Show last 10 executions
                loading={isLoading}
                error={error}
                onExecutionClick={handleExecutionClick}
                compact={true}
                maxHeight={400}
              />
              
              <ExecutionAlerts
                alerts={alerts}
                alertRules={alertRules}
                loading={isLoading}
                error={error}
                onAcknowledgeAlert={acknowledgeAlert}
                onDismissAlert={dismissAlert}
                compact={true}
              />
            </div>

            {/* Quick Metrics */}
            {metrics && (
              <ExecutionMetrics
                metrics={metrics}
                loading={isLoading}
                error={error}
                onTimeframeChange={handleTimeframeChange}
                onRefresh={refreshMetrics}
                detailed={false}
              />
            )}
          </div>
        )}

        {currentView === 'feed' && (
          <div className="space-y-6">
            <TradeExecutionFeed
              executions={getFilteredExecutions()}
              loading={isLoading}
              error={error}
              filter={filter}
              sort={sort}
              autoScroll={feedConfig.autoScroll}
              onExecutionClick={handleExecutionClick}
              onFilterChange={updateFilter}
              onSortChange={updateSort}
              onLoadMore={loadMoreExecutions}
              hasMore={true}
              maxHeight={800}
            />
          </div>
        )}

        {currentView === 'metrics' && (
          <div className="space-y-6">
            <ExecutionMetrics
              metrics={metrics}
              loading={isLoading}
              error={error}
              onTimeframeChange={handleTimeframeChange}
              onRefresh={refreshMetrics}
              detailed={true}
            />
          </div>
        )}

        {currentView === 'alerts' && (
          <div className="space-y-6">
            <ExecutionAlerts
              alerts={alerts}
              alertRules={alertRules}
              loading={isLoading}
              error={error}
              onAcknowledgeAlert={acknowledgeAlert}
              onDismissAlert={dismissAlert}
              onUpdateAlertRule={handleUpdateAlertRule}
              onDeleteAlertRule={handleDeleteAlertRule}
              showRuleManagement={true}
            />
          </div>
        )}

        {/* Order Lifecycle Tracker (shown when execution is selected) */}
        {selectedExecution && currentView === 'feed' && (
          <div className="mt-6">
            <OrderLifecycleTracker
              orderId={selectedExecution.orderId}
              lifecycle={selectedOrderLifecycle}
              loading={false}
              onFetchLifecycle={getOrderLifecycle}
              showLatency={true}
            />
          </div>
        )}

        {/* Trade Details Modal */}
        <TradeDetailsModal
          isOpen={showDetailsModal}
          onClose={() => {
            setShowDetailsModal(false)
            setSelectedExecution(null)
            setSelectedOrderLifecycle(null)
          }}
          execution={selectedExecution}
          lifecycle={selectedOrderLifecycle}
          loading={false}
          onFetchLifecycle={getOrderLifecycle}
          onExportTrade={handleExportTrade}
          showLifecycle={true}
        />
      </div>
    </div>
  )
}